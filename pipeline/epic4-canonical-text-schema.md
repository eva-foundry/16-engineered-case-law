# EPIC 4: Canonical Case Text Schema

**Detailed Schema Design**  
**Date**: January 31, 2026  
**Status**: Design Specification

---

## Overview

EPIC 4 establishes the **canonical case text representation** - the single source of truth for each case decision before chunking. This schema bridges the SQLite artifact source to the downstream chunking and indexing pipeline.

### Core Principle

**One canonical text record per case+language** with complete provenance, quality metrics, and legal metadata.

---

## 1. Database Schema

### Table: `canonical_cases`

Primary storage for canonical case text records.

```sql
CREATE TABLE canonical_cases (
    -- Primary Key
    canonical_id TEXT PRIMARY KEY,  -- Format: {case_id}_{lang}_{version_hash[0:8]}
    
    -- Case Identity
    case_id TEXT NOT NULL,          -- Derived case identifier (e.g., "12345", "2024sst1234")
    language TEXT NOT NULL,         -- 'en', 'fr', or 'bi' (bilingual)
    
    -- Legal Metadata
    citation TEXT,                  -- Official citation (e.g., "2024 SST 1234")
    tribunal TEXT NOT NULL,         -- Court/tribunal code ('fc', 'fca', 'sst')
    decision_date TEXT,             -- ISO date (YYYY-MM-DD)
    decision_year INTEGER,          -- Extracted year for filtering
    
    -- Content
    canonical_text TEXT NOT NULL,   -- Aggregated case text with provenance markers
    text_preview TEXT,              -- First 500 chars for display
    
    -- Quality Metrics
    quality_score REAL NOT NULL,    -- 0.0-1.0 composite quality score
    quality_flags TEXT NOT NULL,    -- JSON: {"non_empty": true, "min_length": true, ...}
    quality_warnings TEXT,          -- JSON: ["short_page_3", "low_char_density"]
    
    -- Size Metrics
    page_count INTEGER NOT NULL,    -- Number of source pages
    char_count INTEGER NOT NULL,    -- Total characters
    word_count INTEGER,             -- Estimated word count
    avg_chars_per_page REAL,        -- char_count / page_count
    
    -- Provenance
    text_source TEXT NOT NULL,      -- 'sqlite_json', 'pdf_text', 'ocr', 'html'
    extraction_method TEXT NOT NULL,-- 'aggregate_pages', 'pdf_extract', 'ocr_full', 'ocr_partial'
    content_hash TEXT NOT NULL,     -- SHA256 of canonical_text
    version_num INTEGER DEFAULT 1,  -- Version counter for reprocessing
    
    -- Source Tracking
    sqlite_source_table TEXT,       -- 'pages_en' or 'pages_fr'
    sqlite_source_rows TEXT NOT NULL,-- JSON: ["id1", "id2", ...] - source page IDs
    blob_storage_path TEXT,         -- Azure Blob Storage reference
    blob_storage_container TEXT,    -- 'bdm-landing'
    blob_content_hash TEXT,         -- PDF MD5 from SQLite
    
    -- Processing Metadata
    import_timestamp TEXT NOT NULL, -- ISO timestamp when created
    updated_timestamp TEXT,         -- ISO timestamp when updated
    processing_duration_ms INTEGER, -- Time to process (milliseconds)
    
    -- Flags
    is_validated BOOLEAN DEFAULT 0, -- Passed quality gates
    is_bilingual BOOLEAN DEFAULT 0, -- Language = 'bi'
    has_warnings BOOLEAN DEFAULT 0, -- quality_warnings is not empty
    requires_review BOOLEAN DEFAULT 0, -- Failed critical quality gates
    
    -- Indexes for queries
    UNIQUE(case_id, language, version_num)
);

-- Indexes for efficient queries
CREATE INDEX idx_canonical_case_id ON canonical_cases(case_id);
CREATE INDEX idx_canonical_tribunal ON canonical_cases(tribunal);
CREATE INDEX idx_canonical_decision_date ON canonical_cases(decision_date);
CREATE INDEX idx_canonical_language ON canonical_cases(language);
CREATE INDEX idx_canonical_quality ON canonical_cases(quality_score);
CREATE INDEX idx_canonical_validated ON canonical_cases(is_validated);
CREATE INDEX idx_canonical_import ON canonical_cases(import_timestamp);
CREATE INDEX idx_canonical_citation ON canonical_cases(citation);
```

---

## 2. Data Structures (Python)

### 2.1 CanonicalCaseRecord

In-memory representation during processing.

```python
from dataclasses import dataclass
from typing import Optional, List, Dict
from datetime import datetime

@dataclass
class CanonicalCaseRecord:
    """
    Canonical case text record with complete metadata.
    
    Represents one case decision in one language with full provenance.
    """
    # Identity
    case_id: str
    language: str  # 'en', 'fr', 'bi'
    
    # Legal Metadata
    citation: Optional[str]
    tribunal: str
    decision_date: Optional[str]  # ISO format YYYY-MM-DD
    
    # Content
    canonical_text: str
    
    # Quality Metrics
    quality_score: float  # 0.0 to 1.0
    quality_flags: Dict[str, bool]  # Gate results
    quality_warnings: List[str]  # Warning messages
    
    # Size Metrics
    page_count: int
    char_count: int
    word_count: int
    
    # Provenance
    text_source: str  # 'sqlite_json', 'pdf_text', 'ocr', 'html'
    extraction_method: str
    content_hash: str  # SHA256
    
    # Source Tracking
    sqlite_source_table: Optional[str]
    sqlite_source_rows: List[str]  # Source page IDs
    blob_storage_path: Optional[str]
    blob_content_hash: Optional[str]
    
    # Processing
    import_timestamp: str  # ISO format
    processing_duration_ms: int
    
    # Computed Properties
    @property
    def canonical_id(self) -> str:
        """Generate deterministic canonical ID."""
        hash_prefix = self.content_hash[:8]
        return f"{self.case_id}_{self.language}_{hash_prefix}"
    
    @property
    def decision_year(self) -> Optional[int]:
        """Extract year from decision_date."""
        if self.decision_date:
            try:
                return int(self.decision_date[:4])
            except (ValueError, IndexError):
                return None
        return None
    
    @property
    def text_preview(self) -> str:
        """First 500 characters for display."""
        return self.canonical_text[:500]
    
    @property
    def avg_chars_per_page(self) -> float:
        """Average characters per page."""
        return self.char_count / max(self.page_count, 1)
    
    @property
    def is_validated(self) -> bool:
        """Passed all quality gates."""
        return all(self.quality_flags.values())
    
    @property
    def is_bilingual(self) -> bool:
        """Language is bilingual."""
        return self.language == 'bi'
    
    @property
    def has_warnings(self) -> bool:
        """Has quality warnings."""
        return len(self.quality_warnings) > 0
    
    @property
    def requires_review(self) -> bool:
        """Failed critical quality gates."""
        critical_gates = ['non_empty', 'min_length']
        return not all(self.quality_flags.get(gate, False) for gate in critical_gates)
```

### 2.2 QualityMetrics

Quality assessment results.

```python
@dataclass
class QualityMetrics:
    """
    Quality assessment results for canonical text.
    """
    # Quality Flags (Pass/Fail)
    non_empty: bool          # Content exists
    min_length: bool         # >= 100 chars
    readable_chars: bool     # >= 80% printable
    multi_page_coverage: bool # >= 200 chars/page
    
    # Composite Score
    quality_score: float     # 0.0 to 1.0 (average of flags)
    
    # Warnings
    warnings: List[str]      # ["short_page_3", "low_density_page_5"]
    
    @classmethod
    def from_text(cls, text: str, page_count: int) -> 'QualityMetrics':
        """
        Compute quality metrics from text.
        
        Args:
            text: Canonical text content
            page_count: Number of pages
            
        Returns:
            QualityMetrics instance
        """
        warnings = []
        
        # Gate 1: Non-empty
        non_empty = bool(text and text.strip())
        if not non_empty:
            warnings.append("empty_content")
        
        # Gate 2: Minimum length
        min_length = len(text) >= 100
        if not min_length:
            warnings.append(f"short_content_{len(text)}_chars")
        
        # Gate 3: Readable characters
        if text:
            printable_count = sum(1 for c in text if c.isprintable() or c.isspace())
            readable_ratio = printable_count / len(text)
            readable_chars = readable_ratio >= 0.8
            if not readable_chars:
                warnings.append(f"low_readability_{readable_ratio:.2f}")
        else:
            readable_chars = False
        
        # Gate 4: Multi-page coverage
        chars_per_page = len(text) / max(page_count, 1)
        multi_page_coverage = chars_per_page >= 200
        if not multi_page_coverage:
            warnings.append(f"sparse_pages_{chars_per_page:.0f}_cpp")
        
        # Composite score
        flags = [non_empty, min_length, readable_chars, multi_page_coverage]
        quality_score = sum(flags) / len(flags)
        
        return cls(
            non_empty=non_empty,
            min_length=min_length,
            readable_chars=readable_chars,
            multi_page_coverage=multi_page_coverage,
            quality_score=quality_score,
            warnings=warnings
        )
    
    def to_dict(self) -> Dict[str, bool]:
        """Convert flags to dictionary."""
        return {
            'non_empty': self.non_empty,
            'min_length': self.min_length,
            'readable_chars': self.readable_chars,
            'multi_page_coverage': self.multi_page_coverage
        }
```

### 2.3 SourceLineage

Tracks provenance from SQLite to canonical text.

```python
@dataclass
class SourceLineage:
    """
    Lineage tracking from source to canonical text.
    """
    # SQLite Source
    sqlite_db_path: str
    sqlite_table: str        # 'pages_en' or 'pages_fr'
    sqlite_row_ids: List[str] # Source page IDs
    sqlite_query_timestamp: str
    
    # Blob Reference
    blob_storage_path: Optional[str]
    blob_container: Optional[str]
    blob_content_hash: Optional[str]
    
    # Aggregation Metadata
    pages_aggregated: int
    aggregation_method: str  # 'sequential', 'sorted_by_page_num'
    
    # Processing
    processing_timestamp: str
    processing_duration_ms: int
    
    def to_json(self) -> Dict:
        """Serialize to JSON for storage."""
        return {
            'sqlite': {
                'db_path': self.sqlite_db_path,
                'table': self.sqlite_table,
                'row_ids': self.sqlite_row_ids,
                'query_timestamp': self.sqlite_query_timestamp
            },
            'blob': {
                'storage_path': self.blob_storage_path,
                'container': self.blob_container,
                'content_hash': self.blob_content_hash
            },
            'aggregation': {
                'pages_aggregated': self.pages_aggregated,
                'method': self.aggregation_method
            },
            'processing': {
                'timestamp': self.processing_timestamp,
                'duration_ms': self.processing_duration_ms
            }
        }
```

---

## 3. Processing Pipeline

### 3.1 Canonical Text Generation Flow

```
SQLite Pages (pages_en/pages_fr)
        ↓
[Group by case_id + language]
        ↓
[Aggregate pages with provenance markers]
        ↓
[Apply quality gates]
        ↓
[Compute metadata (tribunal, date, citation)]
        ↓
[Generate content hash]
        ↓
[Create CanonicalCaseRecord]
        ↓
[Store in canonical_cases table]
```

### 3.2 Page Aggregation Algorithm

```python
def aggregate_pages_for_case(
    pages: List[PageRow],
    case_id: str,
    lang_code: str
) -> str:
    """
    Aggregate page content with provenance markers.
    
    Pages are sorted by page number and concatenated with markers.
    
    Args:
        pages: List of PageRow objects for one case
        case_id: Derived case identifier
        lang_code: Language code ('en' or 'fr')
        
    Returns:
        Aggregated text with [p.N] markers
        
    Example Output:
        [p.1] First page content...
        
        [p.2] Second page content...
        
        [p.3] Third page content...
    """
    # Sort by page number
    sorted_pages = sorted(
        pages,
        key=lambda p: extract_page_num(p.id) or 999999
    )
    
    parts = []
    for page in sorted_pages:
        page_num = extract_page_num(page.id)
        content = (page.content or "").strip()
        
        if not content:
            continue  # Skip empty pages
        
        # Add provenance marker
        marker = f"[p.{page_num}] " if page_num else ""
        parts.append(marker + content)
    
    # Join with double newlines
    return "\n\n".join(parts)
```

### 3.3 Canonical ID Generation

```python
import hashlib

def generate_canonical_id(
    case_id: str,
    language: str,
    content: str
) -> str:
    """
    Generate deterministic canonical ID.
    
    Format: {case_id}_{lang}_{content_hash[0:8]}
    
    Args:
        case_id: Case identifier
        language: Language code
        content: Canonical text content
        
    Returns:
        Deterministic canonical ID
        
    Example:
        "12345_en_a3f7b2c1"
    """
    content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
    hash_prefix = content_hash[:8]
    return f"{case_id}_{language}_{hash_prefix}"
```

---

## 4. Quality Gates Implementation

### 4.1 Quality Gate Thresholds

| Gate | Threshold | Rationale |
|------|-----------|-----------|
| **Non-empty** | > 0 chars | Basic validity |
| **Min length** | ≥ 100 chars | Substantive content |
| **Readable chars** | ≥ 80% printable | Text extraction quality |
| **Multi-page coverage** | ≥ 200 chars/page | Adequate page density |

### 4.2 Quality Score Calculation

```python
def calculate_quality_score(flags: Dict[str, bool]) -> float:
    """
    Calculate composite quality score.
    
    Simple average of gate pass/fail results.
    
    Args:
        flags: Dictionary of gate results
        
    Returns:
        Score from 0.0 (all fail) to 1.0 (all pass)
        
    Example:
        {"non_empty": True, "min_length": True, "readable_chars": False, "multi_page_coverage": True}
        → 0.75 (3 out of 4 passed)
    """
    if not flags:
        return 0.0
    
    return sum(1 for v in flags.values() if v) / len(flags)
```

### 4.3 Warning Generation

```python
def generate_warnings(
    text: str,
    page_count: int,
    quality_flags: Dict[str, bool]
) -> List[str]:
    """
    Generate quality warnings for diagnostic purposes.
    
    Args:
        text: Canonical text
        page_count: Number of pages
        quality_flags: Quality gate results
        
    Returns:
        List of warning messages
    """
    warnings = []
    
    if not quality_flags.get('non_empty'):
        warnings.append("CRITICAL: Empty content")
    
    if not quality_flags.get('min_length'):
        warnings.append(f"Short content: {len(text)} chars")
    
    if not quality_flags.get('readable_chars'):
        printable_ratio = sum(1 for c in text if c.isprintable()) / max(len(text), 1)
        warnings.append(f"Low readability: {printable_ratio:.1%}")
    
    if not quality_flags.get('multi_page_coverage'):
        cpp = len(text) / max(page_count, 1)
        warnings.append(f"Sparse pages: {cpp:.0f} chars/page (threshold: 200)")
    
    return warnings
```

---

## 5. Language Detection

### 5.1 Detection Algorithm

```python
def detect_language(text: str) -> str:
    """
    Detect language of canonical text.
    
    Uses frequency-based heuristics for common words.
    
    Args:
        text: Canonical text content
        
    Returns:
        'en', 'fr', or 'bi' (bilingual)
        
    Logic:
        - If French indicators >> English: 'fr'
        - If English indicators >> French: 'en'
        - Otherwise: 'bi' (bilingual or ambiguous)
    """
    if not text:
        return 'en'  # Default
    
    text_lower = text.lower()
    
    # French indicators
    french_words = ['le ', 'la ', 'les ', 'une ', 'des ', 'dans ', 'avec ', 'pour ', 'par ']
    french_count = sum(text_lower.count(word) for word in french_words)
    
    # English indicators
    english_words = ['the ', 'and ', 'of ', 'to ', 'in ', 'for ', 'with ', 'that ', 'this ']
    english_count = sum(text_lower.count(word) for word in english_words)
    
    # Threshold-based classification
    if french_count > english_count * 2:
        return 'fr'
    elif english_count > french_count * 2:
        return 'en'
    else:
        return 'bi'  # Bilingual or ambiguous
```

### 5.2 Language Validation

```python
def validate_language_consistency(
    detected_lang: str,
    sqlite_table: str
) -> bool:
    """
    Validate detected language matches source table.
    
    Args:
        detected_lang: Detected language code
        sqlite_table: Source table name ('pages_en' or 'pages_fr')
        
    Returns:
        True if consistent, False if mismatch
        
    Note:
        - Mismatches generate warnings but don't block ingestion
        - Bilingual ('bi') is always accepted
    """
    if detected_lang == 'bi':
        return True  # Bilingual always valid
    
    expected_lang = 'en' if 'en' in sqlite_table else 'fr'
    return detected_lang == expected_lang
```

---

## 6. Metadata Extraction

### 6.1 Tribunal Mapping

```python
TRIBUNAL_MAP = {
    'fca': {
        'name': 'FCA (Federal Court of Appeal)',
        'type': 'Appellate',
        'precedence': 1  # Highest
    },
    'fc': {
        'name': 'FC (Federal Court)',
        'type': 'Trial',
        'precedence': 2
    },
    'sst': {
        'name': 'SST (Social Security Tribunal)',
        'type': 'Tribunal',
        'precedence': 3
    }
}

def normalize_tribunal(source_name: str) -> str:
    """
    Normalize tribunal code.
    
    Args:
        source_name: Raw tribunal code from SQLite
        
    Returns:
        Normalized lowercase tribunal code
    """
    code = (source_name or '').strip().lower()
    return code if code in TRIBUNAL_MAP else 'unknown'
```

### 6.2 Citation Validation

```python
import re

CITATION_PATTERN = re.compile(r'\d{4}\s+(SST|FC|FCA)\s+\d+', re.IGNORECASE)

def validate_citation(citation: str) -> bool:
    """
    Validate citation format.
    
    Expected format: YYYY TRIBUNAL NNNN
    Example: 2024 SST 1234
    
    Args:
        citation: Citation string
        
    Returns:
        True if valid format
    """
    if not citation:
        return False
    
    return bool(CITATION_PATTERN.search(citation))
```

---

## 7. Storage and Retrieval

### 7.1 Insert Canonical Record

```python
import sqlite3
import json
from datetime import datetime

def insert_canonical_record(
    conn: sqlite3.Connection,
    record: CanonicalCaseRecord
) -> None:
    """
    Insert canonical case record into database.
    
    Args:
        conn: SQLite connection
        record: CanonicalCaseRecord to insert
    """
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO canonical_cases (
            canonical_id, case_id, language,
            citation, tribunal, decision_date, decision_year,
            canonical_text, text_preview,
            quality_score, quality_flags, quality_warnings,
            page_count, char_count, word_count, avg_chars_per_page,
            text_source, extraction_method, content_hash, version_num,
            sqlite_source_table, sqlite_source_rows,
            blob_storage_path, blob_storage_container, blob_content_hash,
            import_timestamp, processing_duration_ms,
            is_validated, is_bilingual, has_warnings, requires_review
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        record.canonical_id,
        record.case_id,
        record.language,
        record.citation,
        record.tribunal,
        record.decision_date,
        record.decision_year,
        record.canonical_text,
        record.text_preview,
        record.quality_score,
        json.dumps(record.quality_flags),
        json.dumps(record.quality_warnings),
        record.page_count,
        record.char_count,
        record.word_count,
        record.avg_chars_per_page,
        record.text_source,
        record.extraction_method,
        record.content_hash,
        1,  # version_num
        record.sqlite_source_table,
        json.dumps(record.sqlite_source_rows),
        record.blob_storage_path,
        'bdm-landing',  # container
        record.blob_content_hash,
        record.import_timestamp,
        record.processing_duration_ms,
        record.is_validated,
        record.is_bilingual,
        record.has_warnings,
        record.requires_review
    ))
    
    conn.commit()
```

### 7.2 Query Patterns

```python
def get_canonical_by_case_id(
    conn: sqlite3.Connection,
    case_id: str,
    language: Optional[str] = None
) -> List[CanonicalCaseRecord]:
    """
    Retrieve canonical records by case ID.
    
    Args:
        conn: SQLite connection
        case_id: Case identifier
        language: Optional language filter
        
    Returns:
        List of matching records
    """
    cursor = conn.cursor()
    
    if language:
        cursor.execute("""
            SELECT * FROM canonical_cases
            WHERE case_id = ? AND language = ?
            ORDER BY version_num DESC
        """, (case_id, language))
    else:
        cursor.execute("""
            SELECT * FROM canonical_cases
            WHERE case_id = ?
            ORDER BY language, version_num DESC
        """, (case_id,))
    
    # Convert rows to CanonicalCaseRecord objects
    # (implementation details omitted)
    return []  # Placeholder

def get_validated_cases(
    conn: sqlite3.Connection,
    tribunal: Optional[str] = None,
    limit: int = 100
) -> List[CanonicalCaseRecord]:
    """
    Retrieve validated cases for processing.
    
    Args:
        conn: SQLite connection
        tribunal: Optional tribunal filter
        limit: Maximum records to return
        
    Returns:
        List of validated records
    """
    cursor = conn.cursor()
    
    query = """
        SELECT * FROM canonical_cases
        WHERE is_validated = 1
    """
    params = []
    
    if tribunal:
        query += " AND tribunal = ?"
        params.append(tribunal)
    
    query += " ORDER BY decision_date DESC LIMIT ?"
    params.append(limit)
    
    cursor.execute(query, params)
    
    # Convert rows to records
    return []  # Placeholder
```

---

## 8. Validation and Testing

### 8.1 End-to-End Validation

```python
def validate_canonical_pipeline(
    sqlite_path: str,
    output_db_path: str,
    test_case_ids: List[str]
) -> Dict[str, bool]:
    """
    Validate canonical text generation pipeline.
    
    Tests:
    1. Deterministic case_id derivation
    2. Consistent text aggregation
    3. Quality gates applied correctly
    4. Lineage tracking complete
    5. Re-run produces identical results
    
    Args:
        sqlite_path: Path to source SQLite DB
        output_db_path: Path to canonical cases DB
        test_case_ids: List of case IDs to test
        
    Returns:
        Dictionary of test results
    """
    results = {
        'case_id_derivation': False,
        'text_aggregation': False,
        'quality_gates': False,
        'lineage_tracking': False,
        'idempotency': False
    }
    
    # Test implementation...
    
    return results
```

### 8.2 Quality Metrics Report

```python
def generate_quality_report(
    conn: sqlite3.Connection
) -> Dict:
    """
    Generate quality metrics report for canonical cases.
    
    Returns:
        Dictionary with:
        - total_cases
        - validated_cases
        - avg_quality_score
        - cases_by_tribunal
        - cases_by_language
        - quality_distribution
        - common_warnings
    """
    cursor = conn.cursor()
    
    report = {}
    
    # Total cases
    cursor.execute("SELECT COUNT(*) FROM canonical_cases")
    report['total_cases'] = cursor.fetchone()[0]
    
    # Validated cases
    cursor.execute("SELECT COUNT(*) FROM canonical_cases WHERE is_validated = 1")
    report['validated_cases'] = cursor.fetchone()[0]
    
    # Average quality score
    cursor.execute("SELECT AVG(quality_score) FROM canonical_cases")
    report['avg_quality_score'] = cursor.fetchone()[0]
    
    # Cases by tribunal
    cursor.execute("""
        SELECT tribunal, COUNT(*) 
        FROM canonical_cases 
        GROUP BY tribunal
    """)
    report['cases_by_tribunal'] = dict(cursor.fetchall())
    
    # Cases by language
    cursor.execute("""
        SELECT language, COUNT(*) 
        FROM canonical_cases 
        GROUP BY language
    """)
    report['cases_by_language'] = dict(cursor.fetchall())
    
    return report
```

---

## 9. Usage Examples

### 9.1 Generate Canonical Text from SQLite

```python
from pathlib import Path
from pipeline.sqlite_artifact_bridge import SQLiteArtifactBridge

# Initialize bridge
bridge = SQLiteArtifactBridge(
    sqlite_path=Path("c:/path/to/juris_inventory.sqlite"),
    output_db_path=Path("data/canonical_cases.db")
)

# Import and generate canonical text
summary = bridge.import_snapshot(max_cases=1000)

print(f"Imported: {summary.total_cases} cases")
print(f"Validated: {summary.validated_cases}")
print(f"Avg Quality: {summary.avg_quality_score:.2f}")

# Retrieve specific case
records = bridge.get_canonical_text(case_id="12345", language="en")
for record in records:
    print(f"\nCase: {record.citation}")
    print(f"Tribunal: {record.tribunal}")
    print(f"Quality: {record.quality_score:.2f}")
    print(f"Pages: {record.page_count}")
    print(f"Preview: {record.text_preview}...")
```

### 9.2 Query and Filter

```python
# Get all FCA cases
fca_cases = bridge.query_cases(
    tribunal='fca',
    validated_only=True,
    limit=100
)

# Get bilingual cases
bilingual_cases = bridge.query_cases(
    language='bi',
    limit=50
)

# Get cases requiring review
review_cases = bridge.query_cases(
    requires_review=True
)

print(f"Found {len(review_cases)} cases requiring review")
```

---

## 10. Success Criteria

EPIC 4 is complete when:

- ✅ **Canonical cases database created** with complete schema
- ✅ **All SQLite records processed** with case_id derivation
- ✅ **Quality gates applied** to all records
- ✅ **Language detection** implemented and tested
- ✅ **Metadata extraction** working (tribunal, citation, date)
- ✅ **Lineage tracking** complete (SQLite → canonical text)
- ✅ **95%+ validation rate** achieved
- ✅ **Deterministic processing** verified (re-run = identical output)
- ✅ **Ready for EPIC 6** (chunking input validated)

---

## 11. Next Steps

After EPIC 4 completion:

1. **EPIC 5**: Implement bilingual detection and splitting
2. **EPIC 6**: Develop deterministic chunking algorithm
3. **EPIC 7**: Integrate with Azure AI Search
4. **EPIC 8**: Run retrieval quality validation

---

**Document Owner**: Engineering Team  
**Review Status**: Design Complete  
**Implementation Target**: February 2026
