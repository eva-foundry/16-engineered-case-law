# ECL v2.3 Specification - Unified SST Retrieval Model

**Version**: 2.3  
**Date**: February 1, 2026  
**Status**: Proposed Specification  
**Target**: SST Employment Insurance Decisions (EN + FR)  
**Constraint**: Zero EVA DA downstream changes required

---

## Executive Summary

ECL v2.3 introduces a **structured RETRIEVAL_ANCHOR** for SST decisions that combines:

1. **EI_TOPIC** - Controlled vocabulary classification (14 issue types)
2. **Enhanced KEYWORDS** - Already implemented in v2.2.1 (3-7 domain terms)
3. **Structured RETRIEVAL_ANCHOR** - Formatted extractive summary (≤900 chars)

**Key principle**: This is **not metadata filtering or legal classification**. It functions as a **non-authoritative discovery aid**, comparable to library subject headings or case abstracts in legal publishing.

**Format Impact**: No schema change (remains 18-line header). Enhancement happens within existing RETRIEVAL_ANCHOR field through structured formatting.

---

## Table of Contents

1. [Core Principles](#core-principles)
2. [EI Topic Lexicon](#ei-topic-lexicon)
3. [Keywords Enhancement](#keywords-enhancement)
4. [Structured RETRIEVAL_ANCHOR](#structured-retrieval_anchor)
5. [Implementation Strategy](#implementation-strategy)
6. [Governance & Justification](#governance--justification)
7. [Code Changes Required](#code-changes-required)
8. [Testing & Validation](#testing--validation)
9. [Migration Path](#migration-path)

---

## Core Principles

### 1. Applies Identically to EN and FR

This model uses **language-specific text** with a **shared conceptual framework**:
- SST English decisions → English structured anchor
- SST French decisions → French structured anchor
- Same EI_TOPIC codes, translated labels
- Same structure, translated field names

### 2. One Primary EI_TOPIC Per Case

Each SST decision is classified into **exactly one EI_TOPIC** from a closed vocabulary of 14 issue types. No multi-tagging. No free-text topics.

### 3. Discovery Aid, Not Legal Classification

The structured anchor and EI topic function as:
- ✅ Non-authoritative discovery aids
- ✅ Comparable to library subject headings
- ✅ Deterministic, extractive, rule-based
- ❌ Not legal interpretation or AI reasoning
- ❌ Not citable, not authoritative
- ❌ Not replacement for decision text

### 4. Zero Schema Change

Enhancement happens **within** the existing RETRIEVAL_ANCHOR field using structured text formatting. Header remains 18 lines. No EVA DA parser changes required.

---

## EI Topic Lexicon

**Single source of truth** for SST EI retrieval classification.

| Code | EN | FR |
|------|----|----|
| **EI-AVAIL** | Availability for work | Disponibilité pour travailler |
| **EI-ANTEDATE** | Antedate / Backdating | Antidatation |
| **EI-DELAY** | Delay / Good cause | Retard / Motif valable |
| **EI-DISENTITLE** | Disentitlement / Inadmissibility | Exclusion / Inadmissibilité |
| **EI-LABOUR** | Labour dispute | Conflit collectif |
| **EI-EARNINGS** | Earnings allocation | Répartition des gains |
| **EI-MISCONDUCT** | Misconduct | Inconduite |
| **EI-VOLUNTARY** | Voluntary leaving | Départ volontaire |
| **EI-QUALIFY** | Qualifying period | Période de qualification |
| **EI-BENEFIT-PERIOD** | Benefit period | Période de prestations |
| **EI-RECONSIDERATION** | Reconsideration | Réexamen |
| **EI-APPEAL-LEAVE** | Leave to appeal | Permission d'appel |
| **EI-PROCEDURAL** | Procedural fairness | Équité procédurale |
| **EI-JURISDICTION** | Jurisdiction | Compétence |

### Classification Rules

**Hierarchy**: If multiple issues present, classify by most substantive:
1. Substantive EI issues (MISCONDUCT, VOLUNTARY, AVAIL, etc.) > Procedural
2. Primary issue addressed in decision > Secondary mentions
3. Issue that drove outcome > Contextual issues

**Detection Logic** (Keyword-based, deterministic):
```python
ei_topic_patterns = {
    'EI-MISCONDUCT': [
        r'\bmisconduct\b',
        r'\binconduite\b',
        r'\bwilful misconduct\b',
        r'\bfaute volontaire\b',
        r'\bs\.?30\(1\)\(b\)\b'  # Section 30(1)(b)
    ],
    'EI-VOLUNTARY': [
        r'\bvoluntary leaving\b',
        r'\bdépart volontaire\b',
        r'\bquit without just cause\b',
        r'\ba quitté.*sans motif valable\b',
        r'\bs\.?30\(1\)\(c\)\b'  # Section 30(1)(c)
    ],
    'EI-AVAIL': [
        r'\bavailability\b',
        r'\bdisponibilité\b',
        r'\bavailable for work\b',
        r'\bdisponible pour travailler\b',
        r'\bs\.?18\b'  # Section 18
    ],
    'EI-ANTEDATE': [
        r'\bantedate\b',
        r'\bantidatation\b',
        r'\bbackdating\b',
        r'\bs\.?10\(4\)\b'  # Section 10(4)
    ],
    'EI-DELAY': [
        r'\bgood cause\b',
        r'\bmotif valable\b',
        r'\bdelay in filing\b',
        r'\bretard.*demande\b'
    ],
    # ... (patterns for all 14 topics)
}
```

**Confidence Scoring**: Count pattern matches, assign topic with highest score.

**Fallback**: If no patterns match (rare for SST), use `EI-PROCEDURAL` or `EI-JURISDICTION`.

---

## Keywords Enhancement

### Status: ✅ Already Implemented in v2.2.1

The v2.2.1 keyword extraction already implements these rules:
- 3-7 keywords maximum
- EI lexicon weighting (60 terms, 1.5-3.0×)
- Multi-word phrase extraction
- Statute reference detection
- Judge name filtering

### Additional Rules for v2.3

**Language-correct keywords**:
- EN cases → EN keywords only
- FR cases → FR keywords only
- No code-switching within keyword list

**Priority order**:
1. EI topic-specific terms (from matched patterns)
2. Statute references (section numbers)
3. High-frequency EI concepts
4. Contextual terms

### Examples

**SST Antedate case (EN)**:
```
KEYWORDS: antedate, good cause, delay, employment insurance, section 10(4)
```

**SST Availability case (EN)**:
```
KEYWORDS: availability, disentitlement, seasonal, employment insurance
```

**SST Labour dispute case (FR)**:
```
KEYWORDS: conflit collectif, inadmissibilité, arrêt de travail, section 36
```

---

## Structured RETRIEVAL_ANCHOR

### Format Specification

**English Template**:
```
RETRIEVAL_ANCHOR:
EI_TOPIC: {CODE}
QUESTION: {What legal question is being decided?}
CONTEXT: {Brief case context, 1-2 sentences}
DECISION: {Outcome in 1 sentence}
YEAR: {Decision year}
```

**French Template**:
```
RETRIEVAL_ANCHOR:
EI_TOPIC: {CODE}
QUESTION: {Quelle question juridique est tranchée?}
CONTEXTE: {Bref contexte, 1-2 phrases}
DÉCISION: {Résultat en 1 phrase}
ANNÉE: {Année de décision}
```

### Field Constraints

| Field | Max Length | Extraction Logic |
|-------|-----------|------------------|
| **EI_TOPIC** | 20 chars | Automated classification via keyword patterns |
| **QUESTION** | 200 chars | Extract from first substantive paragraph or Issues section |
| **CONTEXT** | 300 chars | Extract 1-2 sentences after question, before analysis |
| **DECISION** | 250 chars | Extract from conclusion paragraph or Appeal allowed/dismissed |
| **YEAR** | 4 chars | From DECISION_DATE field |

**Total**: ≤900 chars (enforced with truncation on sentence boundaries)

### Extraction Strategy

#### Step 1: Find Substantive Start
Use v2.2.1 hierarchical detection:
1. Numbered paragraph `[1]`, `¶1`
2. Section heading (Issues, Question, Facts)
3. End of procedural boilerplate

#### Step 2: Extract QUESTION
```python
def extract_question(text: str, substantive_start: int) -> str:
    """
    Look for question indicators:
    - "The question is..."
    - "Did the claimant..."
    - "Whether..."
    - French: "La question est...", "Est-ce que..."
    """
    region = text[substantive_start:substantive_start + 500]
    
    question_patterns = [
        r'[Tt]he question(?:\s+(?:raised|presented|is))?\s*:?\s*(.+?)(?:\?|\n)',
        r'[Ww]hether\s+(.+?)(?:\?|\n)',
        r'[Dd]id\s+the\s+(?:claimant|appellant)\s+(.+?)(?:\?|\n)',
        r'[Ll]a question\s+(?:soulevée|présentée|est)\s*:?\s*(.+?)(?:\?|\n)',
        r'[Ee]st-ce que\s+(.+?)(?:\?|\n)',
    ]
    
    for pattern in question_patterns:
        match = re.search(pattern, region, re.IGNORECASE)
        if match:
            return _truncate_on_sentence(match.group(1), 200)
    
    # Fallback: First sentence from substantive start
    return _extract_first_sentence(region, max_chars=200)
```

#### Step 3: Extract CONTEXT
```python
def extract_context(text: str, question_end: int) -> str:
    """
    Extract 1-2 sentences immediately after question,
    before analysis section.
    """
    region = text[question_end:question_end + 500]
    
    # Skip analysis markers
    analysis_patterns = [
        r'\n\s*Analysis\s*\n',
        r'\n\s*Reasons?\s*\n',
        r'\n\s*Analyse\s*\n',
        r'\n\s*Motifs?\s*\n',
    ]
    
    for pattern in analysis_patterns:
        match = re.search(pattern, region)
        if match:
            region = region[:match.start()]
            break
    
    # Extract 1-2 sentences
    sentences = _extract_sentences(region, count=2)
    return _truncate_on_sentence(sentences, 300)
```

#### Step 4: Extract DECISION
```python
def extract_decision(text: str) -> str:
    """
    Find outcome statement, typically in conclusion paragraph.
    """
    decision_patterns = [
        r'[Tt]he appeal is (allowed|dismissed)\.?(.{0,200})',
        r'[Ll]\'appel est (accueilli|rejeté)\.?(.{0,200})',
        r'[Aa]ppeal (allowed|dismissed)\.?(.{0,200})',
        r'[Dd]ecision:?\s*(.{0,200})',
    ]
    
    for pattern in decision_patterns:
        match = re.search(pattern, text[-1000:], re.IGNORECASE)
        if match:
            return _truncate_on_sentence(match.group(0), 250)
    
    # Fallback: Last substantive paragraph
    return _extract_last_paragraph(text, max_chars=250)
```

### Example Outputs

#### Example 1: SST Antedate (EN)

**Input**: 2023 SST decision on backdating claim

**Output**:
```
RETRIEVAL_ANCHOR:
EI_TOPIC: EI-ANTEDATE
QUESTION: Did the claimant establish good cause for the delay in filing the claim?
CONTEXT: Claim for benefits filed 8 months after alleged start date. Personal reasons and lack of knowledge invoked.
DECISION: Appeal dismissed. No good cause established under section 10(4) of the Employment Insurance Act.
YEAR: 2023
```

#### Example 2: SST Misconduct (FR)

**Input**: 2024 SST decision on misconduct dismissal

**Output**:
```
RETRIEVAL_ANCHOR:
EI_TOPIC: EI-MISCONDUCT
QUESTION: Le prestataire a-t-il perdu son emploi en raison d'une inconduite au sens de la Loi?
CONTEXTE: Congédiement pour absence non autorisée. L'employeur a invoqué une violation des politiques.
DÉCISION: Appel accueilli. Absence ne constitue pas une inconduite au sens de l'article 30(1)(b).
ANNÉE: 2024
```

#### Example 3: SST Availability (EN)

**Input**: 2025 SST decision on availability for work

**Output**:
```
RETRIEVAL_ANCHOR:
EI_TOPIC: EI-AVAIL
QUESTION: Was the claimant available for work while pursuing full-time education?
CONTEXT: Claimant enrolled in college program. Commission found disentitlement under section 18.
DECISION: Appeal dismissed. Evidence does not support availability for work during academic year.
YEAR: 2025
```

---

## Implementation Strategy

### Phase 1: Detection Engine (1-2 hours)

**File**: `pipeline/ecl_formatter.py`

```python
# New module-level configuration
EI_TOPIC_PATTERNS = {
    'EI-MISCONDUCT': [
        r'\bmisconduct\b',
        r'\binconduite\b',
        r'\bs\.?30\(1\)\(b\)\b',
    ],
    'EI-VOLUNTARY': [
        r'\bvoluntary leaving\b',
        r'\bdépart volontaire\b',
        r'\bs\.?30\(1\)\(c\)\b',
    ],
    # ... all 14 topics
}

def detect_ei_topic(text: str) -> str:
    """
    Classify SST decision into one EI_TOPIC.
    
    Returns:
        EI topic code (e.g., 'EI-MISCONDUCT')
        Fallback: 'EI-PROCEDURAL' if no match
    """
    scores = defaultdict(int)
    text_lower = text.lower()
    
    for topic, patterns in EI_TOPIC_PATTERNS.items():
        for pattern in patterns:
            matches = len(re.findall(pattern, text_lower, re.IGNORECASE))
            scores[topic] += matches
    
    if not scores:
        return 'EI-PROCEDURAL'
    
    return max(scores.items(), key=lambda x: x[1])[0]
```

### Phase 2: Structured Extraction (2-3 hours)

**File**: `pipeline/ecl_formatter.py`

```python
def extract_structured_retrieval_anchor(
    text: str,
    case_date: str,
    language: str,
    max_chars: int = 900
) -> str:
    """
    Extract structured RETRIEVAL_ANCHOR for SST decisions.
    
    Format (EN):
        EI_TOPIC: {code}
        QUESTION: {question}
        CONTEXT: {context}
        DECISION: {outcome}
        YEAR: {year}
    """
    # Step 1: Detect EI topic
    ei_topic = detect_ei_topic(text)
    
    # Step 2: Find substantive start (reuse v2.2.1 logic)
    start_offset = _find_substantive_start(text)
    
    # Step 3: Extract components
    question = _extract_question(text, start_offset)
    question_end = start_offset + len(question) + 100
    context = _extract_context(text, question_end)
    decision = _extract_decision(text)
    year = case_date[:4] if case_date else 'N/A'
    
    # Step 4: Format based on language
    if language == 'FR':
        anchor = (
            f"EI_TOPIC: {ei_topic}\n"
            f"QUESTION: {question}\n"
            f"CONTEXTE: {context}\n"
            f"DÉCISION: {decision}\n"
            f"ANNÉE: {year}"
        )
    else:  # EN
        anchor = (
            f"EI_TOPIC: {ei_topic}\n"
            f"QUESTION: {question}\n"
            f"CONTEXT: {context}\n"
            f"DECISION: {decision}\n"
            f"YEAR: {year}"
        )
    
    # Step 5: Enforce max_chars constraint
    if len(anchor) > max_chars:
        # Truncate context field first, then decision
        # Preserve EI_TOPIC, QUESTION, and YEAR
        anchor = _truncate_structured_anchor(anchor, max_chars)
    
    return anchor
```

### Phase 3: Integration (1 hour)

**File**: `pipeline/ecl_formatter.py`

```python
def extract_retrieval_anchor(
    text: str,
    max_chars: int = 900,
    tribunal: Optional[str] = None,
    case_date: Optional[str] = None,
    language: Optional[str] = None
) -> str:
    """
    Extract RETRIEVAL_ANCHOR with tribunal-specific logic.
    
    v2.3: Use structured format for SST decisions.
    v2.2.1: Use substance-first format for FCA/FC/SCC.
    """
    # v2.3 logic: Structured anchor for SST
    if tribunal and tribunal.lower() == 'sst':
        if not case_date or not language:
            logger.warning("SST case missing date/language, using v2.2.1 logic")
        else:
            return extract_structured_retrieval_anchor(
                text, case_date, language, max_chars
            )
    
    # v2.2.1 logic: Substance-first for all other tribunals
    start_offset = _find_substantive_start(text)
    text_clean = _strip_boilerplate_paragraphs(text, start_offset)
    anchor = text_clean[:max_chars + 200]
    return _truncate_on_sentence(anchor, max_chars)
```

### Phase 4: Testing (2-3 hours)

**File**: `pipeline/test_v23.py`

```python
def test_ei_topic_detection():
    """Test EI topic classification on sample cases."""
    test_cases = [
        ("misconduct case text...", "EI-MISCONDUCT"),
        ("voluntary leaving case text...", "EI-VOLUNTARY"),
        ("antedate case text...", "EI-ANTEDATE"),
    ]
    
    for text, expected_topic in test_cases:
        detected = detect_ei_topic(text)
        assert detected == expected_topic, f"Expected {expected_topic}, got {detected}"

def test_structured_anchor_format():
    """Test structured anchor extraction and formatting."""
    # Sample SST case text
    text = """
    [1] The question is whether the claimant established good cause for 
    the delay in filing the claim. The claim was filed 8 months after 
    the alleged start date. Personal reasons were invoked.
    
    [5] The appeal is dismissed. No good cause established under 
    section 10(4) of the Employment Insurance Act.
    """
    
    anchor = extract_structured_retrieval_anchor(
        text, case_date='2023-05-15', language='EN'
    )
    
    assert 'EI_TOPIC:' in anchor
    assert 'QUESTION:' in anchor
    assert 'CONTEXT:' in anchor
    assert 'DECISION:' in anchor
    assert 'YEAR: 2023' in anchor
    assert len(anchor) <= 900

def test_language_specific_formatting():
    """Test French vs English field labels."""
    text_fr = "[1] La question est de savoir si..."
    
    anchor_fr = extract_structured_retrieval_anchor(
        text_fr, case_date='2024-01-01', language='FR'
    )
    
    assert 'CONTEXTE:' in anchor_fr  # French label
    assert 'DÉCISION:' in anchor_fr  # French label
    assert 'CONTEXT:' not in anchor_fr  # No English

def test_v221_fallback():
    """Test that non-SST cases still use v2.2.1 logic."""
    text = "Federal Court of Appeal decision..."
    
    anchor = extract_retrieval_anchor(
        text, tribunal='fca', case_date='2023-01-01', language='EN'
    )
    
    # Should not have structured format
    assert 'EI_TOPIC:' not in anchor
    assert 'QUESTION:' not in anchor
```

---

## Governance & Justification

### Legal Positioning

**Use this verbatim statement if challenged**:

> *The retrieval anchor and EI topic label function as non-authoritative discovery aids, comparable to abstracts or subject headings used in legal publishing and libraries. They are not cited, do not replace the decision text, and do not paraphrase judicial reasoning. The decision text remains the sole legal authority.*

### What This Is NOT

❌ **Metadata filtering** - No database queries on EI_TOPIC  
❌ **Legal classification** - Not creating precedential categories  
❌ **AI interpretation** - Deterministic, keyword-based extraction  
❌ **Judicial reasoning** - No paraphrasing of holdings or analysis  
❌ **Authority** - Not citable, not quotable, discovery only

### What This IS

✅ **Deterministic extraction** - Rule-based keyword matching  
✅ **Bilingual discovery aid** - Helps users find relevant cases  
✅ **Tribunal-aware enhancement** - Specialized for SST EI patterns  
✅ **Library-style metadata** - Comparable to subject headings  
✅ **Non-authoritative preview** - Quick relevance assessment

### Comparable Precedents

1. **CanLII Headnotes**: Non-authoritative summaries at top of cases
2. **Library of Congress Subject Headings**: Controlled vocabulary for discovery
3. **Legal Publisher Abstracts**: Case summaries in Quicklaw, WestLaw
4. **Jurisprudence Indexes**: Topic-based navigation (e.g., Canadian Abridgment)

None of these are "authoritative" or "legal classification." They're discovery tools.

---

## Code Changes Required

### Files Modified

| File | Lines Changed | Purpose |
|------|---------------|---------|
| `config.py` | +100 | Add EI_TOPIC_PATTERNS dictionary |
| `ecl_formatter.py` | +200 | Add detection + structured extraction |
| `ecl_formatter.py` | +30 | Update extract_retrieval_anchor() with tribunal logic |
| `generate_ecl_v2.py` | +5 | Pass tribunal, date, language to formatter |
| `test_v23.py` | +150 | New test suite for v2.3 |

**Total new code**: ~485 lines  
**Effort estimate**: 6-8 hours development + 3-4 hours testing

### Configuration Addition

**File**: `pipeline/config.py`

```python
# v2.3: EI Topic Classification Patterns
'ei_topic_patterns': {
    'EI-MISCONDUCT': [
        r'\bmisconduct\b',
        r'\binconduite\b',
        r'\bwilful misconduct\b',
        r'\bfaute volontaire\b',
        r'\bs\.?\s*30\(1\)\(b\)\b',
    ],
    'EI-VOLUNTARY': [
        r'\bvoluntary leaving\b',
        r'\bvolontarily left\b',
        r'\bdépart volontaire\b',
        r'\ba quitté volontairement\b',
        r'\bs\.?\s*30\(1\)\(c\)\b',
    ],
    'EI-AVAIL': [
        r'\bavailability\b',
        r'\bavailable for work\b',
        r'\bdisponibilité\b',
        r'\bdisponible pour travailler\b',
        r'\bs\.?\s*18\b',
    ],
    'EI-ANTEDATE': [
        r'\bantedate\b',
        r'\bantedating\b',
        r'\bantidatation\b',
        r'\bbackdating\b',
        r'\bs\.?\s*10\(4\)\b',
    ],
    'EI-DELAY': [
        r'\bgood cause\b',
        r'\bmotif valable\b',
        r'\bdelay in filing\b',
        r'\bretard\b',
    ],
    'EI-DISENTITLE': [
        r'\bdisentitlement\b',
        r'\binadmissibility\b',
        r'\bexclusion\b',
        r'\binadmissibilité\b',
    ],
    'EI-LABOUR': [
        r'\blabour dispute\b',
        r'\bwork stoppage\b',
        r'\bconflit collectif\b',
        r'\barrêt de travail\b',
        r'\bs\.?\s*36\b',
    ],
    'EI-EARNINGS': [
        r'\bearnings\b',
        r'\ballocation\b',
        r'\bgains\b',
        r'\brépartition\b',
        r'\bs\.?\s*35\b',
    ],
    'EI-QUALIFY': [
        r'\bqualifying period\b',
        r'\bpériode de qualification\b',
        r'\binsurable hours\b',
        r'\bheures d\'assurance\b',
    ],
    'EI-BENEFIT-PERIOD': [
        r'\bbenefit period\b',
        r'\bpériode de prestations\b',
    ],
    'EI-RECONSIDERATION': [
        r'\breconsideration\b',
        r'\bréexamen\b',
        r'\bs\.?\s*112\b',
    ],
    'EI-APPEAL-LEAVE': [
        r'\bleave to appeal\b',
        r'\bpermission d\'appel\b',
    ],
    'EI-PROCEDURAL': [
        r'\bprocedural fairness\b',
        r'\bnatural justice\b',
        r'\béquité procédurale\b',
        r'\bjustice naturelle\b',
    ],
    'EI-JURISDICTION': [
        r'\bjurisdiction\b',
        r'\bcompétence\b',
    ],
},

# v2.3: EI Topic Labels (for display/logging)
'ei_topic_labels': {
    'en': {
        'EI-AVAIL': 'Availability for work',
        'EI-ANTEDATE': 'Antedate / Backdating',
        'EI-DELAY': 'Delay / Good cause',
        'EI-DISENTITLE': 'Disentitlement / Inadmissibility',
        'EI-LABOUR': 'Labour dispute',
        'EI-EARNINGS': 'Earnings allocation',
        'EI-MISCONDUCT': 'Misconduct',
        'EI-VOLUNTARY': 'Voluntary leaving',
        'EI-QUALIFY': 'Qualifying period',
        'EI-BENEFIT-PERIOD': 'Benefit period',
        'EI-RECONSIDERATION': 'Reconsideration',
        'EI-APPEAL-LEAVE': 'Leave to appeal',
        'EI-PROCEDURAL': 'Procedural fairness',
        'EI-JURISDICTION': 'Jurisdiction',
    },
    'fr': {
        'EI-AVAIL': 'Disponibilité pour travailler',
        'EI-ANTEDATE': 'Antidatation',
        'EI-DELAY': 'Retard / Motif valable',
        'EI-DISENTITLE': 'Exclusion / Inadmissibilité',
        'EI-LABOUR': 'Conflit collectif',
        'EI-EARNINGS': 'Répartition des gains',
        'EI-MISCONDUCT': 'Inconduite',
        'EI-VOLUNTARY': 'Départ volontaire',
        'EI-QUALIFY': 'Période de qualification',
        'EI-BENEFIT-PERIOD': 'Période de prestations',
        'EI-RECONSIDERATION': 'Réexamen',
        'EI-APPEAL-LEAVE': 'Permission d\'appel',
        'EI-PROCEDURAL': 'Équité procédurale',
        'EI-JURISDICTION': 'Compétence',
    }
}
```

---

## Testing & Validation

### Test Suite Requirements

**Unit Tests** (8 tests):
1. `test_ei_topic_detection_misconduct()` - Misconduct classification
2. `test_ei_topic_detection_voluntary()` - Voluntary leaving classification
3. `test_ei_topic_detection_antedate()` - Antedate classification
4. `test_structured_anchor_format_en()` - English formatting
5. `test_structured_anchor_format_fr()` - French formatting
6. `test_structured_anchor_truncation()` - 900-char limit enforcement
7. `test_v221_fallback_fca()` - FCA cases use v2.2.1 logic
8. `test_v221_fallback_scc()` - SCC cases use v2.2.1 logic

**Integration Tests**:
- Generate 10 SST cases (5 EN, 5 FR) with v2.3 formatting
- Verify all have structured anchors
- Verify FCA/SCC cases still use v2.2.1 format

**Corpus Test**:
- Generate all 22,356 cases with v2.3 logic
- Measure SST coverage: % with structured anchors
- Measure EI_TOPIC distribution across 14 categories
- Validate no format errors

### Success Metrics

| Metric | Target |
|--------|--------|
| **SST cases with structured anchors** | > 95% |
| **Anchor length violations (>900 chars)** | 0% |
| **Non-SST cases affected** | 0% (must use v2.2.1) |
| **EI_TOPIC detection confidence** | > 90% match human classification |
| **Generation time increase** | < 10% vs v2.2.1 |
| **Format errors** | 0 |

---

## Migration Path

### Option A: Immediate v2.3 (Recommended)

**Timeline**: 1 week

1. **Day 1-2**: Implement detection + structured extraction
2. **Day 3**: Write test suite, validate on samples
3. **Day 4**: Test on full corpus (22K cases)
4. **Day 5**: Documentation updates, code review
5. **Day 6-7**: EVA DA integration testing (optional, since no schema change)

**Advantage**: Get structured anchors immediately, no waiting

### Option B: Phased Rollout

**Timeline**: 2-3 weeks

1. **Week 1**: Implement v2.3, test on 100-case sample
2. **Week 2**: Gather user feedback on structured format
3. **Week 3**: Full corpus generation if validated

**Advantage**: Lower risk, user validation first

### Option C: v2.2.1 + v2.3 Parallel

**Timeline**: 1 week

1. Generate v2.2.1 corpus (already done ✅)
2. Generate v2.3 SST subset separately
3. Compare quality metrics
4. Choose winner, regenerate full corpus

**Advantage**: Direct A/B comparison

---

## Recommendation

**Ship v2.3 using Option A (Immediate)** because:

1. **No schema change** - Still 18 lines, no parser breakage
2. **High value for SST** - 94% of corpus is SST cases
3. **Low risk** - Deterministic extraction, fallback to v2.2.1 for non-SST
4. **Production ready in 1 week** - Implementation is straightforward
5. **User feedback can happen post-launch** - Format is extractive, not generative

---

## Appendix: Version History Comparison

| Version | Date | Features | Schema | SST Enhancement |
|---------|------|----------|--------|-----------------|
| **v2.2.0** | Feb 1 AM | Basic anchor + keywords | 18 lines | Starts with boilerplate |
| **v2.2.1** | Feb 1 PM | Substance-first anchor, EI keywords | 18 lines | Generic extractive |
| **v2.3** | Proposed | Structured SST anchor, EI_TOPIC | 18 lines | Structured + classified |

**Key insight**: v2.3 is an **enhancement within the anchor field**, not a new field. No schema change, no coordination overhead.

---

## Support & Questions

**Documentation**:
- This spec: `ECL-V2.3-SPECIFICATION.md`
- v2.2.1 implementation: `ECL-V2.2.1-IMPLEMENTATION-GUIDE.md`
- Comprehensive guide: `ECL-COMPREHENSIVE-GUIDE.md`

**Code**:
- Pipeline: `16-engineered-case-law/pipeline/`
- Tests: `16-engineered-case-law/pipeline/test_v23.py`

**Status**: Specification complete, ready for implementation approval.

**Last Updated**: February 1, 2026
