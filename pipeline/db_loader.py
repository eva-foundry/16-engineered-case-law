"""
================================================================================
MODULE: db_loader.py
VERSION: 2.2.0
DATE: 2026-02-01 18:00:00
AUTHOR: EVA Foundation - Project 16
================================================================================

PURPOSE:
Database access layer for querying juris_inventory.sqlite. Handles multi-page
document aggregation, stratified sampling, and CaseRecord construction.

PIPELINE ROLE:
┌──────────────────────────────────────────────────────────────────────┐
│ DATA LOADER (Database Interface)                                     │
│                                                                      │
│ [db_loader.py] ◄── YOU ARE HERE                                     │
│    ├► Called by: generate_ecl_v2.py                                │
│    ├► Queries: juris_inventory.sqlite (pages table)               │
│    ├► Aggregates: Multi-page documents into single CaseRecord     │
│    └► Outputs: List[CaseRecord] ready for formatting              │
└──────────────────────────────────────────────────────────────────────┘

KEY FEATURES:
1. Multi-Page Aggregation
   - Identifies pages from same case (_pages_1, _pages_2, etc.)
   - Concatenates in numeric order (handles _pages_2, _pages_10 correctly)
   - Computes total page_count per case
   
2. Stratified Sampling
   - Groups cases by tribunal (SCC, FCA, FC, SST)
   - SHA256-based deterministic selection
   - Target: ~13 cases per tribunal per language
   
3. Tribunal Derivation
   - Extracts tribunal from citation (e.g., "2007 SCC 22" → "scc")
   - Maps to precedence rank (SCC=1, SST=4)
   - Fallback to metadata_relpath parsing
   
4. Quality Filtering
   - Min content length check (1000 chars)
   - Non-null citation preferred
   - Valid metadata_relpath required

DATA STRUCTURES:
- CaseRecord: Dataclass with 15+ fields (id, citation, content, etc.)
- Aggregation: Multi-page documents merged into single CaseRecord

KEY FUNCTIONS:
- load_cases_from_db()       - Main query + sampling logic
- get_database_stats()       - Database inventory statistics
- derive_tribunal()          - Extract tribunal from citation
- _extract_page_number()     - Parse page number from ID
- _strip_page_suffix()       - Remove _pages_N from ID

INPUTS:
- db_path: Path to juris_inventory.sqlite
- language: 'en', 'fr', or None (both)
- limit: Max cases per language
- min_content_length: Filter threshold
- random_seed: Deterministic sampling seed

OUTPUTS:
- List[CaseRecord]: Fully aggregated, sampled case objects

DEPENDENCIES:
- sqlite3: Database queries
- hashlib: Deterministic sampling (SHA256)
- re: Regex for page number extraction
- dataclasses: CaseRecord structure

EPIC MAPPING:
- EPIC 4: Canonical Text Schema (CaseRecord structure)
- EPIC 5: Multi-Language Support (EN/FR filtering)
- EPIC 9: Governance (Database statistics)

CHANGELOG:
- v2.2.0 (2026-02-01): Added ECL v2.2 helpers (extract_case_id, normalize_date, sanitize_for_filename)
- v2.1.0 (2026-02-01): Production PoC with multi-page aggregation
- v2.0.0 (2026-01-28): Added tribunal derivation and ranking
- v1.0.0 (2026-01-15): Initial database loader
================================================================================
"""

import sqlite3
import hashlib
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import logging

# Pre-compiled regex patterns for performance
_PAGE_NUMBER_PATTERN = re.compile(r'_pages_(\d+)$', re.IGNORECASE)
_PAGE_SUFFIX_PATTERN = re.compile(r'_pages_\d+$', re.IGNORECASE)


@dataclass
class CaseRecord:
    """
    Structured representation of a jurisprudence case (all pages concatenated).
    
    Attributes:
        id: Unique record identifier (base, without _pages_N suffix)
        citation: Case citation (e.g., "2001 SCC 89")
        publication_date: Decision publication date (ISO format)
        tribunal: Court/tribunal code (scc, fca, fc, sst)
        tribunal_rank: Precedence rank (1=highest)
        language: Language code (en, fr)
        content: Full case text (all pages concatenated in order)
        metadata_relpath: Relative path in blob storage
        pdf_link: Direct link to PDF
        web_link: Web decision link
        source_name: Source tribunal name
        blob_name: Blob storage name
        blob_size: Size of PDF in bytes
        file_stem: Filename without extension
        page_count: Number of pages concatenated
    """
    id: str
    citation: Optional[str]
    publication_date: Optional[str]
    tribunal: str
    tribunal_rank: int
    language: str
    content: str
    metadata_relpath: str
    pdf_link: Optional[str]
    web_link: Optional[str]
    source_name: Optional[str]
    blob_name: str
    blob_size: Optional[int]
    file_stem: str
    page_count: int = 1


def _extract_page_number(record_id: str) -> int:
    """
    Extract page number from record ID using pre-compiled pattern.
    
    The ID format is: {hash}_pages_{page_number}
    Example: df01d46ff6e4_..._pages_12 -> 12
    
    Args:
        record_id: Database record ID
    
    Returns:
        Page number (0 if not found)
    """
    match = _PAGE_NUMBER_PATTERN.search(record_id)
    if match:
        return int(match.group(1))
    return 0


def _strip_page_suffix(record_id: str) -> str:
    """
    Remove _pages_N suffix from record ID to get base case ID using pre-compiled pattern.
    
    Args:
        record_id: Database record ID
    
    Returns:
        Base ID without page suffix
    """
    return _PAGE_SUFFIX_PATTERN.sub('', record_id)


def derive_tribunal(citation: Optional[str], metadata_relpath: str, pdf_link: Optional[str]) -> str:
    """
    Derive tribunal code from available metadata.
    
    Args:
        citation: Case citation
        metadata_relpath: Relative blob path
        pdf_link: PDF URL
    
    Returns:
        Tribunal code (scc, fca, fc, sst, unknown)
    """
    candidates = [
        citation or '',
        metadata_relpath or '',
        pdf_link or ''
    ]
    text = " ".join(candidates).lower()
    
    # Pattern matching with priority order
    patterns = [
        (r'\bscc\b|supreme court', 'scc'),
        (r'\bfca\b|federal court of appeal|caf\b', 'fca'),
        (r'\bfct?\b|federal court', 'fc'),
        (r'\bsst\b|social security|tss\b', 'sst'),
        (r'/scc/', 'scc'),
        (r'/fca/', 'fca'),
        (r'/fc/', 'fc'),
        (r'/sst/', 'sst'),
    ]
    
    for pattern, code in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return code
    
    return 'unknown'


def derive_file_stem(metadata_relpath: str) -> str:
    """
    Extract filename stem from metadata path.
    
    Args:
        metadata_relpath: Relative blob path
    
    Returns:
        Filename without extension
    """
    path = Path(metadata_relpath)
    return path.stem


def derive_language(metadata_relpath: str) -> str:
    """
    Derive language from path.
    
    Args:
        metadata_relpath: Relative blob path
    
    Returns:
        Language code (en, fr, unknown)
    """
    path_lower = metadata_relpath.lower()
    
    if '/english/' in path_lower or path_lower.endswith('_en.pdf'):
        return 'en'
    elif '/french/' in path_lower or path_lower.endswith('_fr.pdf'):
        return 'fr'
    
    return 'unknown'


# ============================================================================
# ECL v2.2 Helper Functions
# ============================================================================

def extract_case_id(case: 'CaseRecord') -> str:
    """
    Extract stable case identifier for ECL v2.2 filename.
    
    Fallback hierarchy:
    1. Citation (e.g., "2007 SCC 22" → "2007-SCC-22")
    2. First part of file_stem before language suffix
    3. CaseRecord.id (full, truncated if too long)
    
    Args:
        case: CaseRecord object
    
    Returns:
        ASCII-safe case ID suitable for filename
    """
    if case.citation:
        # Normalize: "2007 SCC 22" → "2007-SCC-22"
        normalized = re.sub(r'\s+', '-', case.citation.strip())
        # Remove special chars except dash, keep alphanumeric
        normalized = re.sub(r'[^A-Za-z0-9-]', '', normalized)
        if normalized:
            return normalized[:50]  # Truncate if too long
    
    # Fallback: parse file_stem (e.g., "scc_2007-SCC-22_2362_en" → "2007-SCC-22_2362")
    if case.file_stem:
        # Remove tribunal prefix and language suffix
        parts = case.file_stem.split('_')
        if len(parts) >= 2:
            # Take middle parts (skip tribunal prefix, skip lang suffix)
            case_id = '_'.join(parts[1:-1]) if len(parts) > 2 else parts[1]
            if case_id:
                return case_id[:50]
    
    # Last resort: use full id (truncate if too long)
    return case.id[:50]


def normalize_date_for_filename(date_str: Optional[str], default: str = '99999999') -> str:
    """
    Normalize decision date to YYYYMMDD format for filename.
    
    Args:
        date_str: ISO date string (YYYY-MM-DD) or None
        default: Default value for missing dates (99999999 sorts to bottom)
    
    Returns:
        YYYYMMDD string (8 digits, zero-padded)
    """
    if not date_str:
        return default
    
    # Remove dashes: "2007-05-31" → "20070531"
    normalized = date_str.replace('-', '').replace('/', '').strip()
    
    # Validate format (must be 8 digits)
    if re.match(r'^\d{8}$', normalized):
        return normalized
    
    # Invalid format, use default
    return default


def sanitize_for_filename(text: str, max_length: int = 50) -> str:
    """
    Sanitize text for use in filename.
    
    Rules:
    - Lowercase
    - Replace spaces with dashes
    - Keep only [a-z0-9._-]
    - Truncate to max_length
    
    Args:
        text: Text to sanitize
        max_length: Maximum length
    
    Returns:
        ASCII-safe filename segment
    """
    if not text:
        return 'unknown'
    
    # Lowercase and replace spaces
    sanitized = text.lower().replace(' ', '-')
    
    # Keep only safe characters
    sanitized = re.sub(r'[^a-z0-9._-]', '', sanitized)
    
    # Remove consecutive dashes
    sanitized = re.sub(r'-+', '-', sanitized)
    
    # Strip leading/trailing dashes
    sanitized = sanitized.strip('-')
    
    # Truncate
    return sanitized[:max_length] if sanitized else 'unknown'


def load_cases_from_db(
    db_path: Path,
    language: str,
    limit: int = 50,
    min_content_length: int = 1000,
    seed: Optional[str] = None,
    tribunal_ranks: Optional[Dict[str, int]] = None,
    year_filter: Optional[int] = None
) -> Tuple[List[CaseRecord], Dict[str, int]]:
    """
    Load stratified case records from SQLite database.
    
    CRITICAL: Each database row represents ONE PAGE of a web document.
    This function:
    1. Groups rows by metadata_relpath (unique per case)
    2. Sorts pages by numeric page number extracted from ID (_pages_0, _pages_1, etc.)
    3. Concatenates all pages in correct order
    4. Returns ONE CaseRecord per complete case (not per page)
    
    Args:
        db_path: Path to juris_inventory.sqlite
        language: 'en' or 'fr'
        limit: Maximum cases to return
        min_content_length: Minimum total content length per case
        seed: Random seed for reproducibility (optional)
        tribunal_ranks: Dictionary mapping tribunal codes to precedence ranks
        year_filter: Filter cases by specific year (e.g., 2025). If None, all years included.
    
    Returns:
        Tuple of (list of CaseRecord objects, metadata dict with counts)
    
    Raises:
        sqlite3.Error: If database query fails
        ValueError: If language is invalid
    """
    if language not in ('en', 'fr'):
        raise ValueError(f"Invalid language: {language}. Must be 'en' or 'fr'.")
    
    if tribunal_ranks is None:
        tribunal_ranks = {'scc': 1, 'fca': 2, 'fc': 3, 'sst': 4, 'unknown': 5}
    
    logger = logging.getLogger('ecl_generator')
    logger.info(f"Loading {limit} {language.upper()} cases from {db_path} (will concatenate multi-page documents)")
    
    table_name = f"pages_{language}"
    
    # Build WHERE clause with optional year filter
    where_clauses = [
        "p.content IS NOT NULL",
        "LENGTH(p.content) >= 100",
        "p.citation IS NOT NULL"
    ]
    
    if year_filter is not None:
        where_clauses.append(f"SUBSTR(p.publication_date, 1, 4) = '{year_filter}'")
        logger.info(f"Filtering cases by year: {year_filter}")
    
    where_clause = " AND ".join(where_clauses)
    
    # Query: Get all pages for cases that have both JSON content and PDF blobs
    # We'll group and concatenate in Python for better control
    query = f"""
    SELECT 
        p.id,
        p.citation,
        p.publication_date,
        p.source_name,
        p.pdf_link,
        p.web_link,
        p.metadata_relpath,
        p.content,
        b.name AS blob_name,
        b.length AS blob_size
    FROM {table_name} p
    INNER JOIN blobs b ON p.metadata_relpath = b.name
    WHERE 
        {where_clause}
    ORDER BY p.metadata_relpath, p.id
    """
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        logger.debug(f"Fetching all pages for language={language}")
        cur.execute(query)
        
        rows = cur.fetchall()
        logger.info(f"Retrieved {len(rows)} page records from database")
        
        # Group pages by metadata_relpath (one per case)
        from collections import defaultdict
        cases_by_relpath = defaultdict(list)
        
        for row in rows:
            relpath = row['metadata_relpath']
            page_num = _extract_page_number(row['id'])
            
            cases_by_relpath[relpath].append({
                'id': row['id'],
                'page_num': page_num,
                'citation': row['citation'],
                'publication_date': row['publication_date'],
                'source_name': row['source_name'],
                'pdf_link': row['pdf_link'],
                'web_link': row['web_link'],
                'metadata_relpath': row['metadata_relpath'],
                'content': row['content'],
                'blob_name': row['blob_name'],
                'blob_size': row['blob_size']
            })
        
        logger.info(f"Grouped {len(rows)} pages into {len(cases_by_relpath)} unique cases")
        
        # Concatenate pages for each case
        complete_cases = []
        filtered_count = 0
        
        for relpath, pages in cases_by_relpath.items():
            # Sort pages by page number (numeric, not alphabetic)
            pages_sorted = sorted(pages, key=lambda p: p['page_num'])
            
            # Concatenate content with double newlines between pages
            concatenated_content = '\n\n'.join(p['content'] for p in pages_sorted if p['content'])
            
            # Skip if total content too short
            if len(concatenated_content) < min_content_length:
                filtered_count += 1
                continue
            
            # Use first page for metadata
            first_page = pages_sorted[0]
            
            # Derive tribunal
            tribunal = derive_tribunal(
                first_page['citation'],
                first_page['metadata_relpath'],
                first_page['pdf_link']
            )
            tribunal_rank = tribunal_ranks.get(tribunal, 99)
            
            # Remove _pages_N suffix from base ID
            base_id = _strip_page_suffix(first_page['id'])
            file_stem = derive_file_stem(first_page['metadata_relpath'])
            
            case = CaseRecord(
                id=base_id,
                citation=first_page['citation'],
                publication_date=first_page['publication_date'],
                tribunal=tribunal,
                tribunal_rank=tribunal_rank,
                language=language,
                content=concatenated_content,
                metadata_relpath=first_page['metadata_relpath'],
                pdf_link=first_page['pdf_link'],
                web_link=first_page['web_link'],
                source_name=first_page['source_name'],
                blob_name=first_page['blob_name'],
                blob_size=first_page['blob_size'],
                file_stem=file_stem,
                page_count=len(pages_sorted)
            )
            
            complete_cases.append(case)
        
        logger.info(f"Assembled {len(complete_cases)} complete cases from pages")
        if filtered_count > 0:
            logger.warning(
                f"Filtered {filtered_count} cases below minimum content length "
                f"({min_content_length} chars)"
            )
        
        # Apply stratified sampling if needed
        if seed and len(complete_cases) > limit:
            # Deterministic sampling using hash
            def case_hash(case: CaseRecord) -> int:
                """Generate deterministic hash for case sampling."""
                h = hashlib.sha256((seed + case.metadata_relpath).encode('utf-8')).hexdigest()
                return int(h[:8], 16)
            
            # Group by tribunal for stratified sampling
            by_tribunal = defaultdict(list)
            for case in complete_cases:
                by_tribunal[case.tribunal].append(case)
            
            # Sample from each tribunal proportionally
            cases_per_tribunal = (limit + len(by_tribunal) - 1) // len(by_tribunal)
            
            sampled_cases = []
            for tribunal, tribunal_cases in by_tribunal.items():
                # Sort by hash for deterministic selection
                sorted_cases = sorted(tribunal_cases, key=lambda c: case_hash(c))
                sampled = sorted_cases[:cases_per_tribunal]
                sampled_cases.extend(sampled)
                logger.debug(f"Sampled {len(sampled)}/{len(tribunal_cases)} cases from {tribunal}")
            
            complete_cases = sampled_cases[:limit]
        else:
            # Just take first N cases
            complete_cases = complete_cases[:limit]
        
        # Count tribunal distribution
        tribunal_counts = {}
        for case in complete_cases:
            tribunal_counts[case.tribunal] = tribunal_counts.get(case.tribunal, 0) + 1
        
        metadata = {
            'total_cases': len(complete_cases),
            'language': language,
            'min_content_length': min_content_length,
            'tribunal_distribution': tribunal_counts
        }
        
        logger.info(f"Returning {len(complete_cases)} cases: {tribunal_counts}")
        
        return complete_cases, metadata
        
    except sqlite3.Error as e:
        logger.error(
            f"Database error loading cases: {e}\n"
            f"Parameters: language={language}, limit={limit}, min_content_length={min_content_length}",
            exc_info=True
        )
        raise sqlite3.Error(
            f"Failed to load {language} cases: {e}"
        ) from e
    finally:
        # Ensure connection is always closed
        if 'conn' in locals():
            conn.close()
            logger.debug("Database connection closed")


def load_cases_stratified(
    db_path: Path,
    language: str,
    per_group_limit: int,
    group_by: str,
    min_content_length: int = 1000,
    seed: str = 'ecl-stratified',
    tribunal_ranks: Dict[str, int] = None,
    year_filter: Optional[int] = None
) -> Tuple[List[CaseRecord], Dict]:
    """
    Load cases using stratified sampling - X cases per group.
    
    Stratification ensures balanced representation across dimensions:
    - 'tribunal': X cases per tribunal (SCC, FCA, FC, SST)
    - 'year': X cases per publication year
    - 'tribunal_year': X cases per (tribunal, year) combination
    
    CRITICAL: Each database row represents ONE PAGE. This function:
    1. Uses SQL window functions to stratify pages
    2. Groups pages by metadata_relpath
    3. Concatenates pages in correct order per case
    4. Returns ONE CaseRecord per complete case
    
    Args:
        db_path: Path to juris_inventory.sqlite
        language: 'en' or 'fr'
        per_group_limit: Cases to sample per group (e.g., 10)
        group_by: Grouping dimension ('tribunal', 'year', 'tribunal_year')
        min_content_length: Minimum content length filter
        seed: Random seed for reproducibility
        tribunal_ranks: Tribunal precedence mapping
        year_filter: Filter cases by specific year (e.g., 2025). If None, all years included.
    
    Returns:
        Tuple of (cases, metadata) where metadata includes:
        - group_distribution: {group_key: count}
        - total_cases: Total cases returned
        - groups_found: Number of unique groups
        - stratification_method: group_by value
    
    Example:
        # Get 10 cases per tribunal
        cases, meta = load_cases_stratified(
            db_path, 'en', per_group_limit=10, group_by='tribunal'
        )
        # Returns ~40 cases (10 SCC + 10 FCA + 10 FC + 10 SST)
    """
    # SECURITY: Validate inputs to prevent SQL injection
    if language not in ('en', 'fr'):
        raise ValueError(f"Invalid language: {language}. Must be 'en' or 'fr'.")
    
    VALID_GROUP_BY = {'tribunal', 'year', 'tribunal_year'}
    if group_by not in VALID_GROUP_BY:
        raise ValueError(
            f"Invalid group_by parameter: {group_by}. "
            f"Must be one of: {', '.join(sorted(VALID_GROUP_BY))}"
        )
    
    if tribunal_ranks is None:
        tribunal_ranks = {'scc': 1, 'fca': 2, 'fc': 3, 'sst': 4, 'unknown': 5}
    
    logger = logging.getLogger('ecl_generator')
    logger.info(f"Loading stratified sample: {per_group_limit} cases per {group_by} for {language.upper()}")
    
    table_name = f"pages_{language}"
    
    # Build base WHERE clauses
    base_where_clauses = ["content IS NOT NULL", "LENGTH(content) >= 100", "citation IS NOT NULL"]
    if year_filter is not None:
        base_where_clauses.append(f"SUBSTR(publication_date, 1, 4) = '{year_filter}'")
        logger.info(f"Filtering cases by year: {year_filter}")
    base_where = " AND ".join(base_where_clauses)
    
    # Build stratified query based on group_by
    if group_by == 'tribunal':
        # Sample X case IDs per tribunal (derive tribunal from citation/metadata)
        query = f"""
        WITH case_ids AS (
            SELECT DISTINCT 
                metadata_relpath, 
                source_name,
                citation,
                pdf_link,
                -- Derive tribunal from available metadata (matches derive_tribunal() logic)
                CASE
                    WHEN LOWER(COALESCE(citation, '') || ' ' || COALESCE(source_name, '') || ' ' || COALESCE(pdf_link, '')) LIKE '%scc%' 
                         OR LOWER(COALESCE(citation, '') || ' ' || COALESCE(source_name, '') || ' ' || COALESCE(pdf_link, '')) LIKE '%supreme court%'
                         OR LOWER(pdf_link) LIKE '%/scc/%' THEN 'scc'
                    WHEN LOWER(COALESCE(citation, '') || ' ' || COALESCE(source_name, '') || ' ' || COALESCE(pdf_link, '')) LIKE '%fca%' 
                         OR LOWER(COALESCE(citation, '') || ' ' || COALESCE(source_name, '') || ' ' || COALESCE(pdf_link, '')) LIKE '%federal court of appeal%'
                         OR LOWER(COALESCE(citation, '') || ' ' || COALESCE(source_name, '') || ' ' || COALESCE(pdf_link, '')) LIKE '%caf%'
                         OR LOWER(pdf_link) LIKE '%/fca/%' THEN 'fca'
                    WHEN (LOWER(COALESCE(citation, '') || ' ' || COALESCE(source_name, '') || ' ' || COALESCE(pdf_link, '')) LIKE '%fc%' 
                          OR LOWER(COALESCE(citation, '') || ' ' || COALESCE(source_name, '') || ' ' || COALESCE(pdf_link, '')) LIKE '%federal court%')
                         AND LOWER(COALESCE(citation, '') || ' ' || COALESCE(source_name, '') || ' ' || COALESCE(pdf_link, '')) NOT LIKE '%fca%'
                         OR LOWER(pdf_link) LIKE '%/fc/%' THEN 'fc'
                    WHEN LOWER(COALESCE(citation, '') || ' ' || COALESCE(source_name, '') || ' ' || COALESCE(pdf_link, '')) LIKE '%sst%' 
                         OR LOWER(COALESCE(citation, '') || ' ' || COALESCE(source_name, '') || ' ' || COALESCE(pdf_link, '')) LIKE '%social security%'
                         OR LOWER(COALESCE(citation, '') || ' ' || COALESCE(source_name, '') || ' ' || COALESCE(pdf_link, '')) LIKE '%tss%'
                         OR LOWER(pdf_link) LIKE '%/sst/%' THEN 'sst'
                    ELSE 'unknown'
                END AS derived_tribunal
            FROM {table_name}
            WHERE {base_where}
        ),
        ranked_cases AS (
            SELECT 
                metadata_relpath,
                derived_tribunal,
                ROW_NUMBER() OVER (
                    PARTITION BY derived_tribunal
                    ORDER BY RANDOM()
                ) as rn
            FROM case_ids
        ),
        selected_cases AS (
            SELECT metadata_relpath
            FROM ranked_cases
            WHERE rn <= ?
        )
        SELECT 
            p.id,
            p.citation,
            p.publication_date,
            p.source_name,
            p.pdf_link,
            p.web_link,
            p.metadata_relpath,
            p.content,
            b.name AS blob_name,
            b.length AS blob_size
        FROM {table_name} p
        INNER JOIN blobs b ON p.metadata_relpath = b.name
        WHERE p.metadata_relpath IN (SELECT metadata_relpath FROM selected_cases)
        ORDER BY p.metadata_relpath, p.id
        """
        params = (per_group_limit,)
    
    elif group_by == 'year':
        query = f"""
        WITH case_ids AS (
            SELECT DISTINCT 
                metadata_relpath, 
                SUBSTR(publication_date, 1, 4) as year
            FROM {table_name}
            WHERE {base_where}
              AND publication_date IS NOT NULL
        ),
        ranked_cases AS (
            SELECT 
                metadata_relpath,
                year,
                ROW_NUMBER() OVER (
                    PARTITION BY year
                    ORDER BY RANDOM()
                ) as rn
            FROM case_ids
        ),
        selected_cases AS (
            SELECT metadata_relpath
            FROM ranked_cases
            WHERE rn <= ?
        )
        SELECT 
            p.id,
            p.citation,
            p.publication_date,
            p.source_name,
            p.pdf_link,
            p.web_link,
            p.metadata_relpath,
            p.content,
            b.name AS blob_name,
            b.length AS blob_size
        FROM {table_name} p
        INNER JOIN blobs b ON p.metadata_relpath = b.name
        WHERE p.metadata_relpath IN (SELECT metadata_relpath FROM selected_cases)
        ORDER BY p.metadata_relpath, p.id
        """
        params = (per_group_limit,)
    
    else:  # tribunal_year
        query = f"""
        WITH case_ids AS (
            SELECT DISTINCT 
                metadata_relpath,
                source_name,
                SUBSTR(publication_date, 1, 4) as year
            FROM {table_name}
            WHERE {base_where}
              AND publication_date IS NOT NULL
        ),
        ranked_cases AS (
            SELECT 
                metadata_relpath,
                source_name,
                year,
                ROW_NUMBER() OVER (
                    PARTITION BY source_name, year
                    ORDER BY RANDOM()
                ) as rn
            FROM case_ids
        ),
        selected_cases AS (
            SELECT metadata_relpath
            FROM ranked_cases
            WHERE rn <= ?
        )
        SELECT 
            p.id,
            p.citation,
            p.publication_date,
            p.source_name,
            p.pdf_link,
            p.web_link,
            p.metadata_relpath,
            p.content,
            b.name AS blob_name,
            b.length AS blob_size
        FROM {table_name} p
        INNER JOIN blobs b ON p.metadata_relpath = b.name
        WHERE p.metadata_relpath IN (SELECT metadata_relpath FROM selected_cases)
        ORDER BY p.metadata_relpath, p.id
        """
        params = (per_group_limit,)
    
    # Execute query
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        logger.debug(f"Executing stratified query for group_by={group_by}")
        cur.execute(query, params)
        
        rows = cur.fetchall()
        logger.info(f"Retrieved {len(rows)} page records from database")
        
        # Group pages by metadata_relpath (reuse existing logic)
        from collections import defaultdict
        cases_by_relpath = defaultdict(list)
        
        for row in rows:
            relpath = row['metadata_relpath']
            page_num = _extract_page_number(row['id'])
            
            cases_by_relpath[relpath].append({
                'id': row['id'],
                'page_num': page_num,
                'citation': row['citation'],
                'publication_date': row['publication_date'],
                'source_name': row['source_name'],
                'pdf_link': row['pdf_link'],
                'web_link': row['web_link'],
                'metadata_relpath': row['metadata_relpath'],
                'content': row['content'],
                'blob_name': row['blob_name'],
                'blob_size': row['blob_size']
            })
        
        logger.info(f"Grouped {len(rows)} pages into {len(cases_by_relpath)} unique cases")
        
        # Concatenate pages for each case
        complete_cases = []
        group_distribution = {}
        filtered_count = 0
        
        for relpath, pages in cases_by_relpath.items():
            # Sort pages by page number
            pages_sorted = sorted(pages, key=lambda x: x['page_num'])
            
            # Concatenate all page content
            full_content = '\n\n'.join(page['content'] for page in pages_sorted)
            
            # Filter by min_content_length
            if len(full_content) < min_content_length:
                filtered_count += 1
                continue
            
            # Use metadata from first page (they should all be same)
            first_page = pages_sorted[0]
            
            # Derive fields
            tribunal = derive_tribunal(
                first_page['source_name'],
                first_page['metadata_relpath'],
                first_page['pdf_link']
            )
            tribunal_rank = tribunal_ranks.get(tribunal, 5)
            file_stem = derive_file_stem(first_page['metadata_relpath'])
            lang_code = derive_language(first_page['metadata_relpath'])
            
            # Create CaseRecord
            case = CaseRecord(
                id=first_page['id'],
                citation=first_page['citation'],
                publication_date=first_page['publication_date'],
                language=lang_code,
                content=full_content,
                pdf_link=first_page['pdf_link'],
                web_link=first_page['web_link'],
                metadata_relpath=first_page['metadata_relpath'],
                blob_name=first_page['blob_name'],
                blob_size=first_page['blob_size'],
                source_name=first_page['source_name'],
                page_count=len(pages_sorted),
                file_stem=file_stem,
                tribunal=tribunal,
                tribunal_rank=tribunal_rank
            )
            
            complete_cases.append(case)
            
            # Track group distribution
            if group_by == 'tribunal':
                group_key = tribunal
            elif group_by == 'year':
                group_key = first_page['publication_date'][:4] if first_page['publication_date'] else 'unknown'
            else:  # tribunal_year
                year = first_page['publication_date'][:4] if first_page['publication_date'] else 'unknown'
                group_key = f"{tribunal}_{year}"
            
            group_distribution[group_key] = group_distribution.get(group_key, 0) + 1
        
        conn.close()
        
        logger.info(f"Stratified sampling complete: {len(complete_cases)} cases from {len(group_distribution)} groups")
        logger.info(f"Filtered out {filtered_count} cases below minimum content length")
        logger.info(f"Group distribution: {dict(group_distribution)}")
        
        # Count tribunals for metadata (compatible with original load_cases_from_db)
        tribunal_counts = {}
        for case in complete_cases:
            tribunal_counts[case.tribunal] = tribunal_counts.get(case.tribunal, 0) + 1
        
        metadata = {
            'total_cases': len(complete_cases),
            'groups_found': len(group_distribution),
            'group_distribution': group_distribution,
            'per_group_limit': per_group_limit,
            'stratification_method': group_by,
            'total_page_records': len(rows),
            'filtered_count': filtered_count,
            'tribunal_distribution': tribunal_counts
        }
        
        return complete_cases, metadata
    
    except sqlite3.Error as e:
        logger.error(
            f"Database error during stratified sampling: {e}\n"
            f"Query parameters: group_by={group_by}, per_group_limit={per_group_limit}, "
            f"language={language}, table={table_name}",
            exc_info=True
        )
        raise sqlite3.Error(
            f"Stratified sampling failed for {language} (group_by={group_by}): {e}"
        ) from e


def get_database_stats(db_path: Path) -> Dict:
    """
    Get database statistics for reporting.
    
    Args:
        db_path: Path to database
    
    Returns:
        Dictionary with database statistics
    """
    logger = logging.getLogger('ecl_generator')
    
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        stats = {}
        
        # Total rows per table
        for table in ['pages_en', 'pages_fr', 'blobs']:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            stats[f'{table}_total'] = cur.fetchone()[0]
        
        # Pages with content
        for lang in ['en', 'fr']:
            cur.execute(f"SELECT COUNT(*) FROM pages_{lang} WHERE content IS NOT NULL AND LENGTH(content) > 1000")
            stats[f'pages_{lang}_with_content'] = cur.fetchone()[0]
        
        # Matched records (with blobs)
        for lang in ['en', 'fr']:
            cur.execute(f"""
                SELECT COUNT(*) 
                FROM pages_{lang} p
                INNER JOIN blobs b ON p.metadata_relpath = b.name
                WHERE p.content IS NOT NULL
            """)
            stats[f'pages_{lang}_with_blob'] = cur.fetchone()[0]
        
        conn.close()
        
        logger.debug(f"Database stats: {stats}")
        return stats
        
    except sqlite3.Error as e:
        logger.error(f"Failed to get database stats: {e}")
        return {}
