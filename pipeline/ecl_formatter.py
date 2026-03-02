# EVA-FEATURE: F16-04
# EVA-STORY: F16-04-001
# EVA-STORY: F16-04-002
# EVA-STORY: F16-04-003
# EVA-STORY: F16-04-004
# EVA-STORY: F16-06-001
# EVA-STORY: F16-06-002
# EVA-STORY: F16-06-003
# EVA-STORY: F16-07-001
# EVA-STORY: F16-07-002
# EVA-STORY: F16-09-001
# EVA-STORY: F16-09-002
# EVA-STORY: F16-09-003
# EVA-STORY: F16-11-001
# EVA-STORY: F16-11-002
# EVA-STORY: F16-11-003
# EVA-STORY: F16-14-001
# EVA-STORY: F16-14-002
"""
================================================================================
MODULE: ecl_formatter.py
VERSION: 2.2.1
DATE: 2026-02-01 20:00:00
AUTHOR: EVA Foundation - Project 16
================================================================================

PURPOSE:
ECL v2.2 formatting engine. Transforms CaseRecord objects into standardized
plain-text documents with 18-line metadata headers and micro-header injection.

PIPELINE ROLE:
┌──────────────────────────────────────────────────────────────────────┐
│ FORMATTER (Content Transformation)                                   │
│                                                                      │
│ [ecl_formatter.py] ◄── YOU ARE HERE                                 │
│    ├► Called by: generate_ecl_v2.py                                │
│    ├► Inputs: CaseRecord from db_loader.py                        │
│    ├► Processes: Header building + micro-header injection         │
│    └► Outputs: ECL v2.1/v2.2 formatted string (ready to write)   │
└──────────────────────────────────────────────────────────────────────┘

KEY FEATURES:
1. ECL v2.2 Format (NEW)
   - 18-line metadata header (v2.2 adds RETRIEVAL_ANCHOR)
   - RETRIEVAL_ANCHOR: Non-authoritative discovery field (≤900 chars)
   - Boilerplate detection for cleaner anchor extraction
   - Designed for EVA DA physical pre-filtering (5-folder layout)
   
2. ECL v2.1 Format (supported for compatibility)
   - 17-line metadata header (vs 16 in v2.0)
   - New fields: ECL_VERSION, CONTENT_HASH, KEYWORDS, GENERATED
   - ASCII-safe delimiter lines (80 chars)
   
3. Micro-Header Injection (EPIC 6)
   - Sequential counter system (MH00000, MH00001, MH00002...)
   - v2.2: Compact YYYYMMDD date format + 160-char limit enforcement
   - v2.1: Standard YYYY-MM-DD date format
   - Injected every ~1,500 characters
   - Word-boundary aware (searches backward 100 chars)
   - Ensures chunks are self-describing for RAG
   
4. Content Enrichment
   - RETRIEVAL_ANCHOR extraction (v2.2): Boilerplate-free discovery snippet
   - Keyword extraction (frequency-based, bilingual stopwords)
   - Content hashing (SHA256, 16-char truncated)
   - Generated timestamp (ISO 8601 format)
   
5. Validation
   - validate_ecl_format() - Checks header structure
   - Ensures all required fields present
   - Validates delimiter lines

MICRO-HEADER FORMAT (v2.2):
[ECL|MH00000|EN|SCC|R1|20070531|2007 SCC 22|scc_2007-SCC-22_2362_en]
        │     │  │   │  │        │            │
        │     │  │   │  │        │            └─ File stem
        │     │  │   │  │        └─ Citation
        │     │  │   │  └─ Decision date (YYYYMMDD)
        │     │  │   └─ Tribunal rank
        │     │  └─ Tribunal code
        │     └─ Language
        └─ Sequential counter

KEY FUNCTIONS:
- format_ecl_v22()                   - Main v2.2 formatting (18-line header)
- format_ecl_v2()                    - v2.1 formatting (17-line header)
- extract_retrieval_anchor()         - Extract discovery snippet (v2.2)
- build_micro_header_v22()           - Create compact v2.2 micro-header
- build_micro_header()               - Create v2.1 micro-header
- inject_micro_headers_with_counter() - Inject with sequential counters
- extract_keywords()                 - Frequency-based keyword extraction
- compute_content_hash()             - SHA256 hash (16-char truncated)
- validate_ecl_format()              - Post-formatting validation
- get_sample_preview()               - Generate preview snippet

INPUTS:
- case: CaseRecord object from db_loader
- config: CONFIG dict with micro-header settings

OUTPUTS:
- str: Complete ECL v2.1 formatted document

DEPENDENCIES:
- db_loader.CaseRecord: Input data structure
- hashlib: Content hashing
- collections.Counter: Keyword frequency analysis
- datetime: Timestamp generation
- re: Text processing

EPIC MAPPING:
- EPIC 4: Canonical Text Schema (ECL v2.1 format)
- EPIC 6: Chunk Engineering (Micro-header injection with counters)
- EPIC 8: Validation (Format validation)

SOURCE STRATEGY (SC-1):
- Text: SQLite pages.content_text (JSON-extracted)
- PDFs: Referenced by BLOB_PATH, PDF_LINK (not extracted)
- Future: Can switch to PDF extraction without format changes

CHANGELOG:
- v2.2.1 (2026-02-01): Enhanced RETRIEVAL_ANCHOR (substance-first) + EI-aware KEYWORDS
- v2.2.0 (2026-02-01): Added RETRIEVAL_ANCHOR field (18-line header) + v2.2 micro-headers
- v2.1.0 (2026-02-01): Sequential counter micro-headers (MH00000...)
- v2.0.0 (2026-01-28): ECL v2.1 format (17 fields, +4 new fields)
- v1.5.0 (2026-01-25): Keyword extraction + content hashing
- v1.0.0 (2026-01-15): Initial ECL v2.0 formatter
================================================================================
"""

# Note: This module implements SC-1 strategy:
# - Text comes from SQLite pages.content_text (JSON-extracted)
# - PDF is referenced by blob path/link (no PDF extraction)
# - Micro-headers with sequential counters injected for chunk self-description

from typing import Optional, Tuple, Dict, List, Set
import re
import hashlib
import logging
from collections import Counter
from datetime import datetime
from db_loader import CaseRecord


# ============================================================================
# MODULE-LEVEL REGEX PATTERNS (compiled once at import time)
# Performance: Avoids 330K+ regex compilations for 22K files
# ============================================================================
RE_MULTIPLE_NEWLINES = re.compile(r'\n\n+')
RE_LEADING_TRAILING_SPACE = re.compile(r'^\s+|\s+$', re.MULTILINE)
RE_BOILERPLATE_PATTERNS = re.compile(
    r'(Supreme Court Judgments|Décisions de la Cour suprême|'
    r'Federal Court of Appeal|Cour d\'appel fédérale|'
    r'Social Security Tribunal|Tribunal de la sécurité sociale)',
    re.IGNORECASE
)
RE_WHITESPACE = re.compile(r'\s+')
RE_NON_ALPHANUMERIC = re.compile(r'[^a-z0-9\s]')
RE_MULTIPLE_SPACES = re.compile(r' +')

# Additional patterns for extract_keywords
RE_URL = re.compile(r'https?://\S+')
RE_WWW = re.compile(r'www\.\S+')
RE_EMAIL = re.compile(r'\S+@\S+')
RE_WORD_TOKEN = re.compile(
    r'\b[a-zàâäæçèéêëïîôœùûüÿ][a-zàâäæçèéêëïîôœùûüÿ0-9]*\b',
    re.UNICODE
)

# Patterns for validation/parsing
RE_MICROHEADER_START = re.compile(r'\[ECL\|MH00000\|')
RE_MICROHEADER_EXTRACT = re.compile(r'\[ECL\|MH(\d{5})\|')
RE_MICROHEADER_LAST = re.compile(r'\[ECL\|MH\d{5}\|[^\]]+\](?![\s\S]*\[ECL\|MH)')

# v2.2.1: Substantive content detection patterns
RE_NUMBERED_PARA_1 = re.compile(r'\n\s*\[1\]')
RE_PARA_SYMBOL_1 = re.compile(r'\n\s*¶\s*1\b')
RE_PARA_DOT_1 = re.compile(r'\n\s*para\.\s*1\b', re.IGNORECASE)
RE_NUMBERED_SENTENCE = re.compile(r'\n\s*\d+\.\s+[A-Z]')
RE_SECTION_HEADING = re.compile(
    r'\n\s*(Issues?|Questions?|Facts?|Background|Reasons?|Analysis|Motifs?|Analyse)\s*\n',
    re.IGNORECASE
)
RE_BOILERPLATE_END_MARKERS = re.compile(
    r'(REASONS FOR JUDGMENT|MOTIFS DU JUGEMENT|JUDGMENT DELIVERED|JUGEMENT RENDU|Heard at .+?, on \w+ \d+, \d{4})',
    re.IGNORECASE
)
RE_PARAGRAPH_START = re.compile(r'\n\s*\n\s*([A-Z\[])')

# v2.2.1: Boilerplate paragraph patterns
RE_DOCKET_LINE = re.compile(r'^\s*Dockets?:\s*[A-Z0-9\-\s]+$', re.IGNORECASE)
RE_CORAM_LINE = re.compile(r'^\s*CORAM:\s*[A-Z\.\s]+$', re.IGNORECASE)
RE_HEARD_AT = re.compile(r'^\s*Heard at\s+.+?,\s+on\s+\w+\s+\d+,\s+\d{4}\.?\s*$', re.IGNORECASE)
RE_JUDGMENT_DELIVERED = re.compile(r'^\s*Judgment delivered at\s+.+?,\s+on\s+\w+\s+\d+,\s+\d{4}\.?\s*$', re.IGNORECASE)
RE_CITATION_LINE = re.compile(r'^\s*CITATION:\s*\d+\s+\w+\s+\d+\s*$', re.IGNORECASE)
RE_BETWEEN_LINE = re.compile(r'^\s*BETWEEN:\s*$', re.IGNORECASE)
RE_COURT_BILINGUAL = re.compile(r'^\s*Federal Court of Appeal\s+Cour d\'appel fédérale\s*$', re.IGNORECASE)
RE_DATE_LINE = re.compile(r'^\s*Date:\s+\d{8}\s*$', re.IGNORECASE)

# Get logger
logger = logging.getLogger('ecl_formatter')


# ============================================================================
# v2.2.1: RETRIEVAL_ANCHOR HELPER FUNCTIONS
# ============================================================================

def _find_substantive_start(text: str) -> int:
    """
    Find the position where substantive legal content begins.
    
    Hierarchy of detection:
    1. Numbered paragraphs: [1], ¶1, para. 1
    2. Section headings: Issues, Facts, Background, Reasons, Analysis
    3. First paragraph after last boilerplate block
    
    Args:
        text: Full document content
    
    Returns:
        Character position of substantive start (0 if not found)
    """
    # Priority 1: Numbered paragraphs
    numbered_patterns = [RE_NUMBERED_PARA_1, RE_PARA_SYMBOL_1, RE_PARA_DOT_1, RE_NUMBERED_SENTENCE]
    
    for pattern in numbered_patterns:
        match = pattern.search(text)
        if match:
            return match.start() + 1  # Skip the \n
    
    # Priority 2: Section headings
    match = RE_SECTION_HEADING.search(text)
    if match:
        return match.end()  # Start after the heading
    
    # Priority 3: End of boilerplate block
    match = RE_BOILERPLATE_END_MARKERS.search(text)
    if match:
        last_boilerplate_pos = match.end()
        # Find first paragraph after boilerplate (skip empty lines)
        remaining = text[last_boilerplate_pos:]
        para_match = RE_PARAGRAPH_START.search(remaining)
        if para_match:
            return last_boilerplate_pos + para_match.start() + 2
    
    # Fallback: return 0 (start from beginning with old logic)
    return 0


def _strip_boilerplate_paragraphs(text: str, substantive_start: int) -> str:
    """
    Remove entire paragraphs containing only boilerplate.
    
    Paragraph-level filtering is more aggressive than line-level.
    A paragraph is boilerplate if it contains only procedural metadata.
    
    Args:
        text: Text to filter
        substantive_start: Position to start from (0 = full text)
    
    Returns:
        Filtered text with boilerplate paragraphs removed
    """
    # Start from substantive position
    working_text = text[substantive_start:] if substantive_start > 0 else text
    
    # Split into paragraphs (double newline separated)
    paragraphs = re.split(r'\n\s*\n', working_text)
    
    # Boilerplate paragraph indicators (pre-compiled patterns)
    boilerplate_patterns = [
        RE_DOCKET_LINE, RE_CORAM_LINE, RE_HEARD_AT, RE_JUDGMENT_DELIVERED,
        RE_CITATION_LINE, RE_BETWEEN_LINE, RE_COURT_BILINGUAL, RE_DATE_LINE
    ]
    
    filtered_paras = []
    for para in paragraphs:
        para_stripped = para.strip()
        
        # Skip empty paragraphs
        if not para_stripped:
            continue
        
        # Check if paragraph is pure boilerplate
        is_boilerplate = any(
            pattern.match(para_stripped)
            for pattern in boilerplate_patterns
        )
        
        # Check if paragraph is mostly judge names (>50% uppercase words)
        if not is_boilerplate:
            words = para_stripped.split()
            if words:
                uppercase_ratio = sum(1 for w in words if w.isupper() or w.istitle()) / len(words)
                if uppercase_ratio > 0.5 and len(para_stripped) < 200:
                    is_boilerplate = True
        
        if not is_boilerplate:
            filtered_paras.append(para_stripped)
    
    return ' '.join(filtered_paras)


def _truncate_on_sentence(text: str, max_chars: int) -> str:
    """
    Truncate text to max_chars on sentence boundary.
    
    Args:
        text: Text to truncate
        max_chars: Maximum length
    
    Returns:
        Truncated text ending on sentence boundary
    """
    if len(text) <= max_chars:
        return text
    
    # Find last sentence ending before max_chars
    sentence_endings = ['.', '!', '?']
    truncate_pos = max_chars
    
    # Search backward from max_chars up to 200 chars
    for i in range(max_chars - 1, max(0, max_chars - 200), -1):
        if i < len(text) and text[i] in sentence_endings:
            # Include the punctuation
            truncate_pos = i + 1
            break
    
    return text[:truncate_pos].strip()


# ============================================================================
# v2.2.1: KEYWORD EXTRACTION HELPER FUNCTIONS
# ============================================================================

def _extract_statute_references(text: str, patterns: List[str]) -> List[str]:
    """
    Extract statute references from text.
    
    Args:
        text: Document content
        patterns: Regex patterns from config
    
    Returns:
        List of unique statute references found
    """
    references = []
    for pattern in patterns:
        try:
            matches = re.findall(pattern, text, re.IGNORECASE)
            references.extend(matches)
        except Exception as e:
            logger.warning(f"Statute pattern failed: {pattern} - {e}")
    
    # Deduplicate and normalize
    unique_refs = list(set([ref.lower().strip() for ref in references]))
    return unique_refs


def _extract_phrases(text: str, phrases_with_weights: Dict[str, float]) -> Dict[str, Tuple[int, float]]:
    """
    Extract multi-word phrases before tokenization.
    
    Args:
        text: Document content
        phrases_with_weights: Dict of {phrase: weight}
    
    Returns:
        Dict of {phrase: (count, weight)} for found phrases
    """
    found_phrases = {}
    text_lower = text.lower()
    
    for phrase, weight in phrases_with_weights.items():
        if ' ' in phrase:  # Multi-word phrase only
            count = text_lower.count(phrase)
            if count > 0:
                found_phrases[phrase] = (count, weight)
    
    return found_phrases


def _is_likely_name(word: str, name_patterns: List[str], ei_lexicon: Dict[str, float], 
                     judge_surnames: Set[str]) -> bool:
    """
    Check if word is likely a person name (judge, party).
    
    Args:
        word: Word to check
        name_patterns: Regex patterns from config
        ei_lexicon: EI terms dictionary
        judge_surnames: Set of common judge surnames
    
    Returns:
        True if likely a name (should be filtered)
    """
    word_lower = word.lower()
    
    # Allow if in EI lexicon (case-insensitive)
    if word_lower in ei_lexicon:
        return False
    
    # Check if in judge surnames list
    if word_lower in judge_surnames:
        return True
    
    # Check name patterns
    for pattern in name_patterns:
        try:
            if re.match(pattern, word):
                return True
        except Exception:
            pass
    
    return False


def _score_keyword_candidate(word: str, word_count: int, text: str, 
                              ei_lexicon: Dict[str, float], statute_refs: List[str]) -> float:
    """
    Score keyword candidate using multiple signals.
    
    Scoring formula:
    - Base score: word frequency (count)
    - EI concept boost: +frequency * (ei_weight - 1.0)
    - Statute reference bonus: +10.0 if word appears in statute reference
    
    Args:
        word: Candidate keyword
        word_count: Frequency of word in document
        text: Full document text (for statute matching)
        ei_lexicon: EI terms with weights
        statute_refs: List of statute references found
    
    Returns:
        Keyword score (higher = more relevant)
    """
    score = float(word_count)  # Base: frequency
    
    # EI concept boost (if word in lexicon)
    word_lower = word.lower()
    if word_lower in ei_lexicon:
        ei_weight = ei_lexicon[word_lower]
        score += word_count * (ei_weight - 1.0)
    
    # Statute reference bonus (check if word is part of any statute ref)
    for ref in statute_refs:
        if word_lower in ref.lower():
            score += 10.0  # Statute terms are highly relevant
            break
    
    return score


def extract_keywords(text: str, config: Optional[Dict] = None, max_keywords: int = 7) -> str:
    """
    Extract keywords from text using EI-aware scoring (v2.2.1 enhanced).
    
    ENHANCEMENTS v2.2.1:
    1. EI lexicon boost: Domain-specific terms weighted higher
    2. Statute reference extraction: Legal citations identified
    3. Name filtering: Judge/party names removed
    4. Expanded stopwords: Cover page terms excluded
    5. Phrase extraction: Multi-word EI terms recognized
    
    Strategy:
    - Extract multi-word phrases first (employment insurance, good cause)
    - Tokenize text (lowercase, alphanumeric)
    - Filter stopwords (common + legal + cover page terms)
    - Score candidates: frequency + EI boost + statute bonus - name penalty
    - Return top N by score (minimum frequency threshold)
    
    Args:
        text: Document text
        config: CONFIG dict (for lexicons and patterns)
        max_keywords: Maximum keywords to extract (default: 7)
    
    Returns:
        Comma-separated keywords string
    """
    # Use config if provided, else use empty defaults
    if config is None:
        config = {}
    
    ei_lexicon_en = config.get('ei_lexicon_en', {})
    ei_lexicon_fr = config.get('ei_lexicon_fr', {})
    statute_patterns = config.get('statute_reference_patterns', [])
    additional_stopwords = config.get('additional_stopwords', set())
    name_patterns = config.get('name_filter_patterns', [])
    judge_surnames = config.get('common_judge_surnames', set())
    
    # Merge lexicons (bilingual support)
    ei_lexicon = {**ei_lexicon_en, **ei_lexicon_fr}
    
    # Common stopwords (from original + additional)
    stopwords = {
        # Original stopwords
        'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'i',
        'it', 'for', 'not', 'on', 'with', 'he', 'as', 'you', 'do', 'at',
        'this', 'but', 'his', 'by', 'from', 'they', 'we', 'say', 'her', 'she',
        'or', 'an', 'will', 'my', 'one', 'all', 'would', 'there', 'their',
        'was', 'were', 'been', 'has', 'had', 'is', 'are', 'am', 'being',
        'le', 'la', 'les', 'de', 'des', 'un', 'une', 'et', 'à', 'en',
        'du', 'dans', 'pour', 'que', 'qui', 'il', 'elle', 'ce', 'se',
        'ne', 'pas', 'sur', 'par', 'plus', 'avec', 'son', 'sa', 'ses',
        'au', 'aux', 'dont', 'tout', 'tous', 'peut', 'être', 'était',
        'court', 'cour', 'case', 'cause', 'appeal', 'appel', 'judgment',
        'jugement', 'decision', 'décision', 'section', 'article', 'paragraph',
        'paragraphe', 'act', 'loi', 'statute', 'règlement', 'federal', 'fédéral',
        'http', 'https', 'www', 'com', 'org', 'net', 'ca', 'gc', 'gov',
        'lexum', 'qweri', 'calegis', 'canlii', 'decisions', 'document',
        'item', 'index', 'fragment', 'shtml', 'html', 'aspx', 'para', 'paras'
    }
    stopwords.update(additional_stopwords)
    
    # PRE-PROCESS: Remove URLs and email addresses
    text_clean = RE_URL.sub('', text)
    text_clean = RE_WWW.sub('', text_clean)
    text_clean = RE_EMAIL.sub('', text_clean)
    
    # v2.2.1: Extract multi-word phrases BEFORE tokenization
    phrase_scores = {}
    found_phrases = _extract_phrases(text_clean, ei_lexicon)
    for phrase, (count, weight) in found_phrases.items():
        score = count * weight
        phrase_scores[phrase.replace(' ', '-')] = score  # Hyphenate for output
    
    # Extract statute references BEFORE tokenization (preserve multi-word phrases)
    statute_refs = _extract_statute_references(text_clean, statute_patterns)
    
    # Tokenize: EXCLUDE hyphens to split legislative refs
    words = RE_WORD_TOKEN.findall(text_clean.lower())
    
    # Filter: remove stopwords, short words (< 4), pure digits, names
    filtered = [
        w for w in words 
        if w not in stopwords 
        and len(w) >= 4 
        and not w.isdigit()
        and not _is_likely_name(w, name_patterns, ei_lexicon, judge_surnames)
    ]
    
    # Count frequency
    word_counts = Counter(filtered)
    
    # Score each candidate (single words only)
    scored_keywords = []
    for word, count in word_counts.items():
        if count >= 2:  # Minimum frequency threshold
            score = _score_keyword_candidate(word, count, text_clean, ei_lexicon, statute_refs)
            scored_keywords.append((word, score))
    
    # Add phrase scores (already computed)
    for phrase, score in phrase_scores.items():
        scored_keywords.append((phrase, score))
    
    # Sort by score (descending) and take top N
    scored_keywords.sort(key=lambda x: x[1], reverse=True)
    top_keywords = [word for word, score in scored_keywords[:max_keywords]]
    
    return ', '.join(top_keywords) if top_keywords else 'none'


def compute_content_hash(text: str) -> str:
    """
    Compute SHA256 hash of content for deduplication.
    
    Truncated to 16 characters for compactness while maintaining
    sufficient uniqueness for corpus of ~20K documents.
    
    Args:
        text: Document content
    
    Returns:
        First 16 characters of SHA256 hex digest
    """
    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:16]


def extract_retrieval_anchor(text: str, max_chars: int = 900) -> str:
    """
    Extract RETRIEVAL_ANCHOR from content for EVA DA discovery (v2.2.1 enhanced).
    
    ENHANCEMENTS v2.2.1:
    1. Substance-first extraction:
       - Detect numbered paragraphs [1], ¶1
       - Detect section headings (Issues, Facts, Background)
       - Skip cover page boilerplate entirely
    2. Paragraph-level filtering:
       - Remove entire boilerplate paragraphs (not just lines)
       - Filter judge name paragraphs
    3. Smart truncation:
       - Truncate on sentence boundary within 200 chars of target
    
    The anchor is a non-authoritative text snippet (≤900 chars) designed
    for semantic discovery and initial relevance assessment.
    
    Args:
        text: Full document content
        max_chars: Maximum anchor length (default 900)
    
    Returns:
        Extracted anchor text, starting from substantive content
    """
    try:
        # Step 1: Find substantive start (skip cover page)
        substantive_start = _find_substantive_start(text)
        
        # Step 2: Strip boilerplate paragraphs from substantive section
        clean_text = _strip_boilerplate_paragraphs(text, substantive_start)
        
        # Step 3: Normalize whitespace
        clean_text = RE_MULTIPLE_SPACES.sub(' ', clean_text).strip()
        
        # Step 4: Fallback if no content after filtering
        if not clean_text or len(clean_text) < 100:
            # Try original text with old logic (safety net)
            logger.debug(f"Fallback to original text: clean_text too short ({len(clean_text)} chars)")
            clean_text = text[substantive_start:] if substantive_start > 0 else text
            clean_text = RE_MULTIPLE_SPACES.sub(' ', clean_text).strip()
        
        # Step 5: Truncate on sentence boundary
        return _truncate_on_sentence(clean_text, max_chars)
    
    except Exception as e:
        logger.warning(f"RETRIEVAL_ANCHOR extraction failed: {e}. Using fallback.")
        # Ultimate fallback: use old logic
        clean_text = RE_MULTIPLE_SPACES.sub(' ', text).strip()
        return _truncate_on_sentence(clean_text, max_chars)


def sanitize_for_microheader(value: str) -> str:
    """
    Remove characters that break micro-header format.
    
    Replaces:
    - Pipe | (field delimiter) with forward slash /
    - Right bracket ] (end marker) with right paren )
    - Left bracket [ (start marker) with left paren (
    
    Args:
        value: String to sanitize
    
    Returns:
        Sanitized string safe for micro-header
    """
    if not value:
        return ''
    return value.replace('|', '/').replace(']', ')').replace('[', '(')


def build_micro_header(case: CaseRecord, counter: int, max_counter: int = 99999) -> str:
    """
    Build numbered micro-header for repeated injection in content.
    
    Format: [ECL|MH{CTR}|{LANG}|{TRIBUNAL}|R{RANK}|{DATE}|{CITATION}|{FILE_STEM}]
    
    Counter must be 5 digits (00000-99999) for sequential tracking.
    
    Args:
        case: CaseRecord object
        counter: Sequential counter value (0-99999)
    
    Returns:
        Single-line micro-header with counter
    
    Example:
        [ECL|MH00000|EN|SCC|R1|2007-05-31|2007 SCC 22|scc_2007-SCC-22_2362_en]
    """
    # Check counter overflow
    if counter > max_counter:
        raise ValueError(
            f"Counter overflow: {counter} exceeds {max_counter}. "
            f"Document too large for micro-header format (>150MB estimated)."
        )
    
    # Build compact signature with counter
    ctr = f"{counter:05d}"  # 5-digit zero-padded counter
    lang = case.language.upper()
    tribunal = sanitize_for_microheader(case.tribunal.upper())
    rank = case.tribunal_rank
    date = case.publication_date or ''
    citation = sanitize_for_microheader(case.citation or '').strip()
    stem = sanitize_for_microheader(case.file_stem)
    
    micro = f"[ECL|MH{ctr}|{lang}|{tribunal}|R{rank}|{date}|{citation}|{stem}]"
    
    return micro


def build_micro_header_v22(case: CaseRecord, counter: int, max_counter: int = 99999, max_length: int = 160) -> str:
    """
    Build numbered micro-header for ECL v2.2 with compact YYYYMMDD date format.
    
    Format: [ECL|MH{CTR}|{LANG}|{TRIBUNAL}|R{RANK}|{YYYYMMDD}|{CITATION}|{FILE_STEM}]
    
    v2.2 enhancements:
    - YYYYMMDD date format (compact, 8 chars instead of 10)
    - 160-char max length enforcement (truncate citation + stem if needed)
    - Missing dates represented as 99999999 (sorts to bottom)
    
    Counter must be 5 digits (00000-99999) for sequential tracking.
    
    Args:
        case: CaseRecord object
        counter: Sequential counter value (0-99999)
        max_counter: Maximum counter value (default: 99999)
        max_length: Maximum micro-header length (default: 160)
    
    Returns:
        Single-line micro-header with counter (≤160 chars)
    
    Example:
        [ECL|MH00000|EN|SCC|R1|20070531|2007 SCC 22|scc_2007-SCC-22_2362_en]
    """
    # Check counter overflow
    if counter > max_counter:
        raise ValueError(
            f"Counter overflow: {counter} exceeds {max_counter}. "
            f"Document too large for micro-header format (>150MB estimated)."
        )
    
    # Build compact signature with counter
    ctr = f"{counter:05d}"  # 5-digit zero-padded counter
    lang = case.language.upper()
    tribunal = sanitize_for_microheader(case.tribunal.upper())
    rank = case.tribunal_rank
    
    # Convert date to YYYYMMDD format (or use 99999999 for missing)
    date_str = case.publication_date or ''
    if date_str:
        # Assume date_str is in YYYY-MM-DD format, convert to YYYYMMDD
        try:
            from db_loader import normalize_date_for_filename
            date_compact = normalize_date_for_filename(date_str, default='99999999')
        except:
            # Fallback: strip hyphens
            date_compact = date_str.replace('-', '')[:8]
    else:
        date_compact = '99999999'
    
    citation = sanitize_for_microheader(case.citation or '').strip()
    stem = sanitize_for_microheader(case.file_stem)
    
    # Build preliminary micro-header
    micro = f"[ECL|MH{ctr}|{lang}|{tribunal}|R{rank}|{date_compact}|{citation}|{stem}]"
    
    # Enforce max_length by truncating citation and stem if needed
    if len(micro) > max_length:
        # Calculate fixed overhead: [ECL|MH00000|EN|XXX|R0|00000000||]
        # Approximate: 35 chars for structure, plus tribunal length
        fixed_overhead = 35 + len(tribunal)
        available_for_var = max_length - fixed_overhead
        
        # Split available space between citation and stem (60/40 split)
        citation_budget = int(available_for_var * 0.6)
        stem_budget = available_for_var - citation_budget
        
        # Truncate if needed
        if len(citation) > citation_budget:
            citation = citation[:max(citation_budget, 10)]  # Min 10 chars for citation
        if len(stem) > stem_budget:
            stem = stem[:max(stem_budget, 20)]  # Min 20 chars for stem
        
        # Rebuild micro-header
        micro = f"[ECL|MH{ctr}|{lang}|{tribunal}|R{rank}|{date_compact}|{citation}|{stem}]"
    
    return micro


def find_word_boundary(text: str, pos: int, search_backward: int = 100) -> int:
    """
    Find nearest whitespace boundary before pos to avoid splitting words.
    
    Args:
        text: Text to search
        pos: Target position
        search_backward: Max chars to search backward (default from config)
    
    Returns:
        Position of nearest prior whitespace, or pos if none found
    """
    if pos <= 0 or pos >= len(text):
        return pos
    
    # Search backward for whitespace
    search_start = max(0, pos - search_backward)
    segment = text[search_start:pos]
    
    # Find last whitespace in segment
    match = None
    for m in re.finditer(r'\s', segment):
        match = m
    
    if match:
        return search_start + match.end()
    
    return pos  # No whitespace found, use original position


def inject_micro_headers_with_counter(text: str, case: CaseRecord, every_chars: int) -> Tuple[str, int]:
    """
    Inject numbered micro-headers throughout text with sequential counters.
    
    Strategy:
    1. Start with MH00000 at beginning
    2. Insert MH00001, MH00002... every N chars at word boundaries
    3. Add final micro-header with next counter at end
    
    Args:
        text: Original case text (must be non-empty)
        case: CaseRecord for building micro-headers
        every_chars: Insert frequency in characters (must be > 0)
    
    Returns:
        Tuple of (engineered_content, final_counter)
    
    Raises:
        ValueError: If text is empty or every_chars is invalid
    """
    # Validate inputs
    if not text:
        raise ValueError(
            f"Cannot inject micro-headers into empty text for case: {case.file_stem}"
        )
    if every_chars <= 0:
        raise ValueError(
            f"Invalid every_chars: {every_chars}. Must be positive integer."
        )
    
    chunks = []
    counter = 0
    pos = 0
    
    # Add initial micro-header MH00000
    mh_initial = build_micro_header(case, counter)
    chunks.append(f"{mh_initial}\n\n")
    counter += 1
    
    # Process body text with injections
    while pos < len(text):
        # Calculate next boundary (try to avoid word splits)
        target_end = min(pos + every_chars, len(text))
        
        if target_end < len(text):
            # Not at end - find word boundary
            actual_end = find_word_boundary(text, target_end)
        else:
            # At end of text
            actual_end = target_end
        
        # Extract chunk
        chunk = text[pos:actual_end]
        chunks.append(chunk)
        
        pos = actual_end
        
        # Add micro-header before next chunk (unless we're at the end)
        if pos < len(text):
            mh = build_micro_header(case, counter)
            chunks.append(f"\n\n{mh}\n\n")
            counter += 1
    
    # Add final micro-header at end
    mh_final = build_micro_header(case, counter)
    chunks.append(f"\n{mh_final}")
    
    return ''.join(chunks), counter


def format_ecl_v2(case: CaseRecord, enable_micro_headers: bool = True, micro_every_chars: int = 1500) -> str:
    """
    Format a case record as ECL v2.1 plain text document with enhanced metadata.
    
    ECL v2.1 format (SC-1 strategy):
    - 16-line metadata header (ASCII-safe)
      NEW in v2.1: ECL_VERSION, GENERATED, CONTENT_HASH, KEYWORDS
    - One blank line
    - MH00000 micro-header + blank line
    - Body text with numbered micro-headers (MH00001, MH00002...) every N characters
    - Final micro-header at end with next counter value
    
    Text source: SQLite pages.content_text (JSON-extracted)
    PDF involvement: Referenced only (blob path + PDF_LINK), no extraction
    
    Args:
        case: CaseRecord object with case data
        enable_micro_headers: Inject numbered micro-headers for chunk self-description
        micro_every_chars: Injection frequency in characters (default: 1500)
    
    Returns:
        Formatted ECL v2.1 document as string
    """
    # Compute hash and extract keywords (v2.1 features)
    content_hash = compute_content_hash(case.content)
    keywords = extract_keywords(case.content, max_keywords=7)
    
    # Build header (ASCII-safe, 16 lines with v2.1 enhancements)
    header_lines = [
        "DOC_CLASS: ECL",
        "ECL_VERSION: 2.1",
        f"GENERATED: {datetime.now().isoformat()}",
        f"CONTENT_HASH: {content_hash}",
        f"FILE_STEM: {case.file_stem}",
        f"LANG: {case.language.upper()}",
        f"TRIBUNAL: {case.tribunal.upper()}",
        f"TRIBUNAL_RANK: {case.tribunal_rank}",
        f"DECISION_DATE: {case.publication_date or ''}",
        f"CITATION: {case.citation or ''}",
        f"KEYWORDS: {keywords}",
        f"PDF_LINK: {case.pdf_link or ''}",
        f"WEB_LINK: {case.web_link or ''}",
        f"BLOB_PATH: {case.metadata_relpath or ''}",
        f"SOURCE_NAME: {case.source_name or ''}",
        f"PAGE_COUNT: {case.page_count}",
        f"CONTENT_LENGTH: {len(case.content)}"
    ]
    
    header = "\n".join(header_lines)
    
    # Apply numbered micro-header injection for chunk self-description
    if enable_micro_headers:
        engineered_content, final_counter = inject_micro_headers_with_counter(
            case.content, case, micro_every_chars
        )
    else:
        engineered_content = case.content
    
    # Assemble document: header + blank line + engineered content (with micro-headers)
    document = f"{header}\n\n{engineered_content}"
    
    return document


def format_ecl_v22(case: CaseRecord, enable_micro_headers: bool = True, micro_every_chars: int = 1500, retrieval_anchor_max_chars: int = 900) -> str:
    """
    Format a case record as ECL v2.2 plain text document with RETRIEVAL_ANCHOR.
    
    ECL v2.2 format (EVA DA-ready):
    - 18-line metadata header (ASCII-safe)
      NEW in v2.2: RETRIEVAL_ANCHOR (≤900 chars non-authoritative discovery field)
    - One blank line
    - MH00000 micro-header + blank line
    - Body text with numbered micro-headers (MH00001, MH00002...) every N characters
    - Final micro-header at end with next counter value
    
    v2.2 designed for EVA DA physical pre-filtering via 5-folder layout:
    - output/{en|fr}/{scc|fca|fc|sst|unknown}/
    - Filename template: {LANGIDX}_{rank-tribunal}_{YYYYMMDD}_{CASEID}_{DOCID}.ecl.txt
    
    Text source: SQLite pages.content_text (JSON-extracted)
    PDF involvement: Referenced only (blob path + PDF_LINK), no extraction
    
    Args:
        case: CaseRecord object with case data
        enable_micro_headers: Inject numbered micro-headers for chunk self-description
        micro_every_chars: Injection frequency in characters (default: 1500)
        retrieval_anchor_max_chars: Max length for RETRIEVAL_ANCHOR (default: 900)
    
    Returns:
        Formatted ECL v2.2 document as string
    """
    # v2.2.1: Import config for EI-aware keywords
    try:
        from config import CONFIG
    except ImportError:
        logger.warning("Could not import CONFIG, using default keyword extraction")
        CONFIG = {}
    
    # Compute hash, keywords, and retrieval anchor (v2.2 features)
    content_hash = compute_content_hash(case.content)
    keywords = extract_keywords(case.content, config=CONFIG, max_keywords=7)
    retrieval_anchor = extract_retrieval_anchor(case.content, max_chars=retrieval_anchor_max_chars)
    
    # VALIDATE: Ensure RETRIEVAL_ANCHOR meets length constraint
    if len(retrieval_anchor) > retrieval_anchor_max_chars:
        logger = logging.getLogger('ecl_generator')
        logger.warning(
            f"RETRIEVAL_ANCHOR exceeded limit: {len(retrieval_anchor)} > {retrieval_anchor_max_chars} "
            f"chars for case {case.file_stem}. Truncating to sentence boundary."
        )
        # Hard truncate at max_chars, then trim to last complete word
        retrieval_anchor = retrieval_anchor[:retrieval_anchor_max_chars].rsplit(' ', 1)[0] + '...'
    
    # Build header (ASCII-safe, 18 lines with v2.2 RETRIEVAL_ANCHOR)
    header_lines = [
        "DOC_CLASS: ECL",
        "ECL_VERSION: 2.2",
        f"GENERATED: {datetime.now().isoformat()}",
        f"CONTENT_HASH: {content_hash}",
        f"FILE_STEM: {case.file_stem}",
        f"LANG: {case.language.upper()}",
        f"TRIBUNAL: {case.tribunal.upper()}",
        f"TRIBUNAL_RANK: {case.tribunal_rank}",
        f"DECISION_DATE: {case.publication_date or ''}",
        f"CITATION: {case.citation or ''}",
        f"KEYWORDS: {keywords}",
        f"RETRIEVAL_ANCHOR: {retrieval_anchor}",
        f"PDF_LINK: {case.pdf_link or ''}",
        f"WEB_LINK: {case.web_link or ''}",
        f"BLOB_PATH: {case.metadata_relpath or ''}",
        f"SOURCE_NAME: {case.source_name or ''}",
        f"PAGE_COUNT: {case.page_count}",
        f"CONTENT_LENGTH: {len(case.content)}"
    ]
    
    header = "\n".join(header_lines)
    
    # Apply numbered micro-header injection for chunk self-description
    if enable_micro_headers:
        engineered_content, final_counter = inject_micro_headers_with_counter(
            case.content, case, micro_every_chars
        )
    else:
        engineered_content = case.content
    
    # Assemble document: header + blank line + engineered content (with micro-headers)
    document = f"{header}\n\n{engineered_content}"
    
    return document


def format_header_only(case: CaseRecord) -> str:
    """
    Format only the ECL v2.1 header (for validation/preview).
    
    Args:
        case: CaseRecord object
    
    Returns:
        Header lines as string (16 lines)
    """
    # Compute hash and extract keywords (v2.1 features)
    content_hash = compute_content_hash(case.content)
    keywords = extract_keywords(case.content, max_keywords=7)
    
    header_lines = [
        "DOC_CLASS: ECL",
        "ECL_VERSION: 2.1",
        f"GENERATED: {datetime.now().isoformat()}",
        f"CONTENT_HASH: {content_hash}",
        f"FILE_STEM: {case.file_stem}",
        f"LANG: {case.language.upper()}",
        f"TRIBUNAL: {case.tribunal.upper()}",
        f"TRIBUNAL_RANK: {case.tribunal_rank}",
        f"DECISION_DATE: {case.publication_date or ''}",
        f"CITATION: {case.citation or ''}",
        f"KEYWORDS: {keywords}",
        f"PDF_LINK: {case.pdf_link or ''}",
        f"WEB_LINK: {case.web_link or ''}",
        f"BLOB_PATH: {case.metadata_relpath or ''}",
        f"SOURCE_NAME: {case.source_name or ''}",
        f"PAGE_COUNT: {case.page_count}",
        f"CONTENT_LENGTH: {len(case.content)}"
    ]
    
    return "\n".join(header_lines)


def validate_ecl_format(document: str, min_content_length: int = 1000, check_micro_headers: bool = True) -> bool:
    """
    Validate that a document conforms to ECL v2.1 format with numbered micro-headers.
    
    Validation checks:
    1. Finds header/body boundary by first blank line
    2. Confirms required front-matter fields exist (including v2.1 fields)
    3. Confirms MH00000 exists immediately after front matter
    4. Confirms micro-header counters are sequential (MH00000, MH00001, MH00002...)
    5. Confirms final micro-header exists at end of document
    6. Body text meets minimum length
    
    Args:
        document: ECL v2.1 document string
        min_content_length: Minimum body length required
        check_micro_headers: Validate micro-header sequence
    
    Returns:
        True if valid, False otherwise
    """
    if not document:
        return False
    
    lines = document.split('\n')
    
    # Find first blank line (header/body boundary)
    blank_line_idx = None
    for i, line in enumerate(lines):
        if line.strip() == '':
            blank_line_idx = i
            break
    
    if blank_line_idx is None:
        return False  # No blank separator found
    
    # Extract header and body
    header_lines = lines[:blank_line_idx]
    body_lines = lines[blank_line_idx + 1:]
    
    # Validate header has required fields (including v2.1 fields)
    header_text = '\n'.join(header_lines)
    required_fields = [
        'DOC_CLASS: ECL',
        'ECL_VERSION: 2.1',
        'CONTENT_HASH:',
        'KEYWORDS:',
        'FILE_STEM:',
        'LANG:',
        'TRIBUNAL:',
        'TRIBUNAL_RANK:',
        'CONTENT_LENGTH:'
    ]
    
    for field in required_fields:
        if field not in header_text:
            return False
    
    # Validate body exists and meets minimum length
    body_text = '\n'.join(body_lines)
    if len(body_text) < min_content_length:
        return False
    
    # Validate micro-header sequence if enabled
    if check_micro_headers:
        # Check for MH00000 immediately after front matter
        if not body_lines or not RE_MICROHEADER_START.match(body_lines[0]):
            return False
        
        # Extract all micro-headers
        micro_headers = RE_MICROHEADER_EXTRACT.findall(body_text)
        
        if not micro_headers:
            return False
        
        # Verify sequential counters
        for i, counter_str in enumerate(micro_headers):
            expected = i
            actual = int(counter_str)
            if actual != expected:
                return False  # Counter sequence broken
        
        # Verify final micro-header exists at end
        last_mh_match = RE_MICROHEADER_LAST.search(body_text)
        if not last_mh_match:
            return False
        
        # Check that final micro-header is near the end (within last 200 chars)
        if len(body_text) - last_mh_match.end() > 200:
            return False
    
    return True


def get_sample_preview(case: CaseRecord, content_lines: int = 30) -> str:
    """
    Generate a preview of an ECL v2 document (header + first N lines).
    
    Args:
        case: CaseRecord object
        content_lines: Number of content lines to include
    
    Returns:
        Preview string
    """
    header = format_header_only(case)
    content_preview = '\n'.join(case.content.split('\n')[:content_lines])
    
    preview = f"{header}\n\n{content_preview}\n\n[... content continues ...]"
    
    return preview
