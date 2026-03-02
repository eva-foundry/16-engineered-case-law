"""
================================================================================
MODULE: ecl_formatter_NEW.py
VERSION: 1.0.0 (DEPRECATED - Replaced by ecl_formatter.py v2.1.0)
DATE: 2026-01-25 (Archived)
AUTHOR: EVA Foundation - Project 16
================================================================================

STATUS: 🗄️ ARCHIVED - DO NOT USE

PURPOSE:
Early prototype of ECL v2 formatter without sequential counter micro-headers.
This module has been superseded by ecl_formatter.py v2.1.0.

PIPELINE ROLE:
┌──────────────────────────────────────────────────────────────────────┐
│ DEPRECATED FORMATTER (Archive Only)                                  │
│                                                                      │
│ [ecl_formatter_NEW.py] ◄── DEPRECATED                               │
│    ├► Status: Archived prototype                                   │
│    ├► Replaced by: ecl_formatter.py v2.1.0                        │
│    ├► Limitation: No sequential counters in micro-headers         │
│    └► Reason: v2.1.0 has superior chunk self-description          │
└──────────────────────────────────────────────────────────────────────┘

WHY ARCHIVED:
This module was an experimental implementation of ECL v2 formatting that
injected repeated micro-headers without sequential counters. It was replaced
by ecl_formatter.py v2.1.0 which implements:

1. Sequential counter system (MH00000, MH00001, MH00002...)
2. Better chunk self-description for RAG pipelines
3. Word-boundary aware injection
4. Final chunk validation (ensures no chunk exceeds tolerance)

MIGRATION PATH:
All functionality now in ecl_formatter.py v2.1.0
- build_micro_header() → Same signature, enhanced output
- inject_micro_headers() → inject_micro_headers_with_counter()
- format_ecl_v2() → Enhanced with CONTENT_HASH, KEYWORDS, GENERATED

DO NOT USE THIS MODULE:
- Import from ecl_formatter.py instead
- Sequential counters required for Phase 2 (backend ingestion)
- This version lacks necessary metadata for chunk tracking

HISTORICAL CONTEXT:
Created during EPIC 6 exploration (2026-01-25) as prototype for micro-header
injection. Tested basic concept but lacked robustness for production RAG.
Preserved for reference only.

IF YOU SEE IMPORTS FROM THIS MODULE:
Replace with: from ecl_formatter import ...
Update code to use inject_micro_headers_with_counter() instead of
inject_micro_headers() for sequential counter support.

EPIC MAPPING:
- EPIC 6: Chunk Engineering (Prototype phase - superseded)

CHANGELOG:
- v1.0.0 (2026-01-25): Initial prototype (now deprecated)
- Replaced by ecl_formatter.py v2.1.0 (2026-02-01)
================================================================================
"""

# DEPRECATION WARNING: Do not use this module.
# Use ecl_formatter.py v2.1.0 instead for production ECL generation.

from typing import Optional
from db_loader import CaseRecord


def build_micro_header(case: CaseRecord) -> str:
    """
    Build compact micro-header for repeated injection in content.
    
    Format: [ECL|{LANG}|{TRIBUNAL}|R{RANK}|{DATE}|{CITATION}|{FILE_STEM}]
    
    This ensures most chunks contain case metadata even when EVA DA
    chunking strategy is unknown.
    
    Args:
        case: CaseRecord object
    
    Returns:
        Single-line micro-header (<=120 chars, ASCII-safe)
    
    Example:
        [ECL|EN|SCC|R1|2007-05-31|2007 SCC 22|scc_2007-SCC-22_2362_en]
    """
    # Build compact signature
    lang = case.language.upper()
    tribunal = case.tribunal.upper()
    rank = case.tribunal_rank
    date = case.publication_date or ''
    citation = (case.citation or '').replace('|', '/').strip()  # Avoid pipe conflicts
    stem = case.file_stem
    
    micro = f"[ECL|{lang}|{tribunal}|R{rank}|{date}|{citation}|{stem}]"
    
    return micro


def inject_micro_headers(text: str, micro: str, every_chars: int) -> str:
    """
    Inject micro-header repeatedly throughout text for chunk self-description.
    
    Inserts micro-header + blank line every N characters to ensure
    most chunks (regardless of chunking strategy) contain metadata.
    
    Args:
        text: Original case text
        micro: Micro-header string from build_micro_header()
        every_chars: Insert frequency in characters (default: 1500)
    
    Returns:
        Text with micro-headers injected
    """
    if not text or every_chars <= 0:
        return text
    
    # Split into insertion points
    chunks = []
    pos = 0
    
    while pos < len(text):
        # Take next chunk
        end = min(pos + every_chars, len(text))
        chunk = text[pos:end]
        
        # Add micro-header before chunk (except first chunk)
        if pos > 0:
            chunks.append(f"{micro}\n\n{chunk}")
        else:
            chunks.append(chunk)
        
        pos = end
    
    return ''.join(chunks)


def format_ecl_v2(case: CaseRecord, enable_micro_headers: bool = True, micro_every_chars: int = 1500) -> str:
    """
    Format a case record as ECL v2 plain text document with engineered metadata injection.
    
    ECL v2 format (SC-1 strategy):
    - 13-line metadata header (ASCII only)
    - One blank line
    - Body text with repeated micro-headers injected every N characters
      (ensures most chunks are self-describing regardless of chunking strategy)
    
    Text source: SQLite pages.content_text (JSON-extracted)
    PDF involvement: Referenced only (blob path + PDF_URI), no extraction
    
    Args:
        case: CaseRecord object with case data
        enable_micro_headers: Inject micro-headers for chunk self-description
        micro_every_chars: Injection frequency in characters (default: 1500)
    
    Returns:
        Formatted ECL v2 document as string
    """
    # Build header (ASCII-safe, 13 lines)
    header_lines = [
        "DOC_CLASS: ECL",
        f"FILE_STEM: {case.file_stem}",
        f"LANG: {case.language.upper()}",
        f"TRIBUNAL: {case.tribunal.upper()}",
        f"TRIBUNAL_RANK: {case.tribunal_rank}",
        f"DECISION_DATE: {case.publication_date or ''}",
        f"CITATION: {case.citation or ''}",
        f"PDF_URI: {case.pdf_link or ''}",
        f"WEB_URI: {case.web_link or ''}",
        f"BLOB_PATH: {case.metadata_relpath or ''}",
        f"SOURCE_NAME: {case.source_name or ''}",
        f"PAGE_COUNT: {case.page_count}",
        f"CONTENT_LENGTH: {len(case.content)}"
    ]
    
    header = "\n".join(header_lines)
    
    # Apply micro-header injection for chunk self-description
    if enable_micro_headers:
        micro = build_micro_header(case)
        engineered_content = inject_micro_headers(case.content, micro, micro_every_chars)
    else:
        engineered_content = case.content
    
    # Assemble document: header + blank line + engineered content
    document = f"{header}\n\n{engineered_content}"
    
    return document


def format_header_only(case: CaseRecord) -> str:
    """
    Format only the ECL v2 header (for validation/preview).
    
    Args:
        case: CaseRecord object
    
    Returns:
        Header lines as string (13 lines)
    """
    header_lines = [
        "DOC_CLASS: ECL",
        f"FILE_STEM: {case.file_stem}",
        f"LANG: {case.language.upper()}",
        f"TRIBUNAL: {case.tribunal.upper()}",
        f"TRIBUNAL_RANK: {case.tribunal_rank}",
        f"DECISION_DATE: {case.publication_date or ''}",
        f"CITATION: {case.citation or ''}",
        f"PDF_URI: {case.pdf_link or ''}",
        f"WEB_URI: {case.web_link or ''}",
        f"BLOB_PATH: {case.metadata_relpath or ''}",
        f"SOURCE_NAME: {case.source_name or ''}",
        f"PAGE_COUNT: {case.page_count}",
        f"CONTENT_LENGTH: {len(case.content)}"
    ]
    
    return "\n".join(header_lines)


def validate_ecl_format(document: str, min_content_length: int = 1000) -> bool:
    """
    Validate that a document conforms to ECL v2 format.
    
    Does NOT assume fixed line numbers - finds header/body boundary
    by locating the first blank line separator.
    
    Args:
        document: ECL v2 document string
        min_content_length: Minimum body length required
    
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
    
    # Validate header has required fields
    header_text = '\n'.join(header_lines)
    required_fields = [
        'DOC_CLASS: ECL',
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
