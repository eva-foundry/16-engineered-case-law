# SQLite Artifact Bridge for Engineered Case Law Pipeline

**Design Document**  
**Date**: January 31, 2026, 07:01  
**Status**: Proposed Architecture

---

## Executive Summary

This document describes how the Engineered Case Law pipeline will leverage the **existing `juris_inventory.sqlite` database** as the artifact acquisition source, enabling immediate pipeline execution without requiring CDC infrastructure or PDF downloads.

**Key Decision**: Use existing SQLite data as a **pre-materialized snapshot** that bridges EPIC 1-3 (Inventory, Artifacts, Extraction) while maintaining compatibility with the future CDC-driven architecture.

---

## 1. Context and Problem

### Current State

The Engineered Case Law README describes a CDC-driven pipeline:

```
CanLII Inventory Snapshot (EPIC 1)
        ↓
CDC Diff (new / changed cases)
        ↓
Artifact Acquisition (EPIC 2 - PDF + HTML download)
        ↓
Text Extraction (EPIC 3 - PDF → OCR only if needed)
        ↓
Canonical Case Text (EPIC 4)
        ↓
...
```

**Reality**: We have a mature SQLite database from Project 05 that already contains:
- **~25k case records** with extracted text
- **Metadata**: citations, dates, tribunals, PDF/HTML links
- **Blob references**: Azure Storage paths to existing PDFs
- **Structure**: `pages_en`, `pages_fr`, `blobs` tables

### The Opportunity

Rather than starting from scratch with CanLII API integration, we can **bridge the existing SQLite data** into the pipeline as a pre-processed artifact source. This enables:

1. **Immediate execution** - no API integration needed
2. **Cost avoidance** - skip redundant PDF downloads and text extraction
3. **Quality validation** - existing text already vetted by Project 05
4. **CDC readiness** - architecture designed for future CDC integration

---

## 2. SQLite Database Schema (Source System)

### Location
```
c:\Users\marco.presta\OneDrive - ESDC EDSC\Documents\AICOE\EVA-JP-v1.2\docs\eva-foundation\system-analysis\inventory\SPO-Data-Analysis\juris_inventory.sqlite
```

### Tables and Structure

#### Table: `pages_en` / `pages_fr`

**Purpose**: Page-level records with extracted text

| Column | Type | Description |
|--------|------|-------------|
| `id` | TEXT | Unique page ID (e.g., `jurisprudence_12345_pages_1`) |
| `citation` | TEXT | Case citation (e.g., `2024 SST 1234`) |
| `publication_date` | TEXT | Decision date (ISO format) |
| `source_name` | TEXT | Tribunal code (`fc`, `fca`, `sst`) |
| `pdf_link` | TEXT | CanLII PDF URL |
| `web_link` | TEXT | CanLII HTML page URL |
| `metadata_storage_path` | TEXT | Azure Blob Storage full URL |
| `metadata_relpath` | TEXT | Relative blob path |
| `metadata_storage_last_modified` | TEXT | Blob timestamp |
| `metadata_storage_size` | INTEGER | Blob size in bytes |
| `metadata_storage_content_type` | TEXT | MIME type |
| `metadata_storage_content_md5` | TEXT | Content hash |
| `content` | TEXT | **Extracted text content** |

**Key Pattern**: Multiple rows per case (one per page), identified by suffix `_pages_N`

**Example Record**:
```
id: jurisprudence_12345_en_pages_1
citation: 2024 SST 1234
publication_date: 2024-01-15
source_name: sst
pdf_link: https://canlii.ca/.../en/12345/1/document.do
metadata_storage_path: https://infoasststoredev2.blob.core.windows.net/bdm-landing/jurisprudence/english/sst/case_12345_en.pdf
content: [Extracted text from page 1...]
```

#### Table: `blobs`

**Purpose**: Blob inventory (diagnostic/join purposes)

| Column | Type | Description |
|--------|------|-------------|
| `name` | TEXT | Blob name/path |
| Additional metadata columns...

### Data Characteristics

- **Case Count**: ~25,000 cases
- **Page Granularity**: Multiple page records per case
- **Languages**: Separate tables for EN/FR
- **Text Quality**: Already extracted and validated by Project 05
- **Blob Storage**: References existing Azure Blob Storage (`bdm-landing` container)

---

## 3. Bridge Architecture

### 3.1 Conceptual Mapping

| CDC Pipeline Stage | SQLite Bridge Equivalent |
|-------------------|-------------------------|
| **EPIC 1: CanLII Inventory Snapshot** | Treat entire SQLite as a snapshot |
| **EPIC 1: CDC Diff** | All records = "new" (first run), skip diff |
| **EPIC 2: Artifact Acquisition** | Use blob storage paths (no download) |
| **EPIC 3: Text Extraction** | Use existing `content` field with quality gates |
| **EPIC 4: Canonical Text Selection** | Aggregate pages → case-level canonical text |

### 3.2 Module: `sqlite_artifact_bridge.py`

**Purpose**: Adapter layer that reads SQLite and produces artifact/extraction records compatible with downstream pipeline stages (EPIC 4+).

#### Core Components

```python
class SQLiteArtifactBridge:
    """
    Bridges juris_inventory.sqlite to Engineered Case Law pipeline.
    
    Responsibilities:
    - Read case records from pages_en/pages_fr
    - Aggregate pages per case (case_id + language)
    - Track blob storage references (no downloads)
    - Apply quality gates to existing text
    - Produce canonical text records with lineage
    """
    
    def __init__(self, sqlite_path: Path, output_db_path: Path):
        """
        Args:
            sqlite_path: Path to juris_inventory.sqlite
            output_db_path: Path to engineered case law tracking DB
        """
    
    def import_snapshot(self, max_cases: Optional[int] = None) -> SnapshotSummary:
        """
        Import SQLite records as a snapshot.
        
        Returns summary with:
        - total_cases_discovered
        - cases_by_tribunal
        - cases_by_language
        """
    
    def generate_canonical_text_records(self) -> Generator[CanonicalTextRecord]:
        """
        Iterate over cases and produce canonical text records.
        
        Each record represents one case+language with:
        - case_id
        - language (en/fr)
        - aggregated_text (pages concatenated)
        - metadata (citation, date, tribunal)
        - blob_reference (Azure Storage path)
        - quality_score
        - extraction_method = "sqlite_json"
        """
```

#### Key Functions

**1. Case ID Derivation**

Reuse Project 05 logic:

```python
def derive_case_id(pdf_link: str, metadata_relpath: str) -> str:
    """
    Extract case_id from:
    - PDF link: /decisions/en/12345/1/document.do → 12345
    - Blob path: case_12345_en.pdf → 12345
    """
```

**2. Page Aggregation**

```python
def aggregate_pages_for_case(
    pages: List[PageRow], 
    case_id: str, 
    lang_code: str
) -> str:
    """
    Concatenate page content with provenance markers.
    
    Example output:
    [p.1] Page 1 content...
    
    [p.2] Page 2 content...
    """
```

**3. Quality Gates**

Apply same gates as EPIC 3 text extraction:

```python
def apply_quality_gates(text: str, page_count: int) -> QualityResult:
    """
    Quality gates:
    1. Non-empty content
    2. Minimum length (100 chars)
    3. Readable character distribution (80%+ printable)
    4. Multi-page coverage (200 chars/page average)
    
    Returns:
        QualityResult with score 0.0-1.0 and pass/fail flags
    """
```

**4. Language Detection**

```python
def detect_language(text: str) -> str:
    """
    Detect language: 'en', 'fr', or 'bi' (bilingual).
    
    Uses heuristics:
    - French indicators: 'le ', 'la ', 'les ', 'une ', 'des '
    - English indicators: 'the ', 'and ', 'of ', 'to '
    - Bilingual if mixed or ambiguous
    """
```

### 3.3 Output Schema

#### Table: `canonical_cases`

Engineered case law tracking database.

| Column | Type | Description |
|--------|------|-------------|
| `case_id` | TEXT | Derived case identifier |
| `language` | TEXT | `en`, `fr`, or `bi` |
| `citation` | TEXT | Official citation |
| `tribunal` | TEXT | Court/tribunal code |
| `decision_date` | TEXT | ISO date |
| `blob_storage_path` | TEXT | Azure Blob reference |
| `text_source` | TEXT | Always `sqlite_json` |
| `canonical_text` | TEXT | Aggregated page content |
| `quality_score` | REAL | 0.0-1.0 quality metric |
| `page_count` | INTEGER | Number of pages |
| `char_count` | INTEGER | Total characters |
| `quality_flags` | TEXT | JSON dict of gate results |
| `import_timestamp` | TEXT | ISO timestamp |
| `sqlite_source_rows` | TEXT | JSON list of source page IDs |

---

## 4. Implementation Approach

### Phase 1: SQLite Bridge Module (Immediate)

**Goal**: Enable EPIC 4+ using existing SQLite data

**Tasks**:
1. Create `sqlite_artifact_bridge.py`
2. Implement case ID derivation (reuse Project 05 logic)
3. Implement page aggregation
4. Apply quality gates to existing text
5. Generate `canonical_cases` table
6. Add language detection
7. Track blob storage references (no downloads)

**Output**: Canonical text records ready for chunking (EPIC 6)

**Estimated Effort**: 2-3 days

### Phase 2: Chunking Integration (Next)

**Goal**: Generate engineered chunks from canonical text

**Tasks**:
1. Implement deterministic chunking (EPIC 6)
2. Enrich chunks with case metadata
3. Generate chunk IDs (stable, deterministic)
4. Store chunks in preparation for indexing

**Output**: Engineered case law chunks

**Estimated Effort**: 3-4 days

### Phase 3: EVA DA Ingestion (Validation)

**Goal**: Ingest chunks and validate retrieval

**Tasks**:
1. Implement Azure AI Search upsert (EPIC 7)
2. Configure index schema
3. Execute controlled ingestion (100-1000 cases)
4. Run gold-set queries (EPIC 8)
5. Measure retrieval quality

**Output**: Working EVA DA integration

**Estimated Effort**: 3-5 days

### Phase 4: CDC Migration Path (Future)

**Goal**: Enable incremental updates via CDC

**Tasks**:
1. Implement CanLII API polling (EPIC 1)
2. Add CDC diff computation
3. Migrate from "snapshot import" to "incremental sync"
4. Keep SQLite bridge as fallback/bootstrap mechanism

**Output**: Full CDC-driven pipeline

**Estimated Effort**: 1-2 weeks

---

## 5. Quality Gates and Validation

### 5.1 Text Quality Assessment

Apply EPIC 3 quality gates to existing SQLite text:

| Gate | Threshold | Pass Rate (Estimated) |
|------|-----------|----------------------|
| Non-empty content | > 0 chars | ~99.5% |
| Minimum length | ≥ 100 chars | ~99% |
| Readable chars | ≥ 80% printable | ~98% |
| Multi-page coverage | ≥ 200 chars/page | ~95% |

**Expected Outcome**: 95%+ of SQLite records pass quality gates without requiring OCR.

### 5.2 Reject Handling

Cases failing quality gates:

1. **Log rejection reason** with case_id
2. **Export reject report** (CSV)
3. **Optional**: Flag for OCR processing (future enhancement)
4. **Do not block pipeline** - continue with passing cases

### 5.3 Validation Metrics

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| **Import Success Rate** | > 95% | Cases passing quality gates / total cases |
| **Case ID Derivation** | 100% | Verify deterministic case_id for all records |
| **Language Detection** | > 98% | Spot-check EN/FR/BI classification |
| **Blob Reference Validity** | 100% | Validate Azure Storage path format |
| **Aggregation Consistency** | 100% | Re-run produces identical canonical text |

---

## 6. Benefits and Trade-offs

### Benefits

| Benefit | Impact |
|---------|--------|
| **Immediate Execution** | Skip months of API integration work |
| **Cost Avoidance** | No redundant PDF downloads or OCR charges |
| **Proven Data Quality** | Text already validated by Project 05 |
| **Deterministic Processing** | SQLite query order is stable |
| **CDC-Ready Architecture** | Bridge layer is swappable |
| **Audit Trail** | Full lineage from SQLite → canonical text → chunks |

### Trade-offs

| Trade-off | Mitigation |
|-----------|-----------|
| **Static Snapshot** | Accept as baseline; CDC adds incremental updates later |
| **No Real-time Sync** | Acceptable for initial ingestion and validation |
| **Corpus Completeness** | Known limitation (acknowledged in README § 11) |
| **Blob Storage Dependency** | PDFs already exist in Azure; no new dependency |

---

## 7. Migration Path to CDC

### Current State (SQLite Bridge)

```
SQLite Import (snapshot)
        ↓
Canonical Text Generation
        ↓
Deterministic Chunking
        ↓
EVA DA Index Upsert
```

### Future State (CDC-Driven)

```
CanLII API Polling
        ↓
CDC Diff Computation
        ↓
[OPTION A: Use SQLite Bridge for existing cases]
[OPTION B: Download new PDFs + extract text]
        ↓
Canonical Text Generation
        ↓
Deterministic Chunking
        ↓
EVA DA Index Upsert
```

**Key Design**: The `canonical_cases` table schema remains identical, enabling seamless transition.

### Transition Strategy

1. **Phase 1 (Now)**: Use SQLite bridge for all cases
2. **Phase 2 (Months 1-2)**: Add CDC polling, but continue using SQLite for bulk corpus
3. **Phase 3 (Month 3+)**: CDC handles new cases; SQLite is dormant but available for re-bootstrap

---

## 8. Implementation Checklist

### Module Development

- [ ] Create `sqlite_artifact_bridge.py`
- [ ] Implement `SQLiteArtifactBridge` class
- [ ] Add `derive_case_id()` function
- [ ] Add `aggregate_pages_for_case()` function
- [ ] Add `apply_quality_gates()` function
- [ ] Add `detect_language()` function
- [ ] Create `canonical_cases` table schema
- [ ] Implement `import_snapshot()` method
- [ ] Implement `generate_canonical_text_records()` generator
- [ ] Add logging and progress tracking

### Testing

- [ ] Unit tests for case ID derivation
- [ ] Unit tests for page aggregation
- [ ] Unit tests for quality gates
- [ ] Integration test: Import 100 cases
- [ ] Integration test: Re-run produces identical output
- [ ] Validate blob storage path format
- [ ] Verify language detection accuracy
- [ ] Generate reject report for failing cases

### Documentation

- [ ] Update pipeline README with SQLite bridge usage
- [ ] Add example usage in pipeline/README.md
- [ ] Document quality gate thresholds
- [ ] Create troubleshooting guide
- [ ] Add CDC migration guide

### Integration

- [ ] Connect bridge output to EPIC 6 (chunking)
- [ ] Verify chunk IDs are deterministic
- [ ] Test end-to-end: SQLite → chunks → index
- [ ] Run gold-set evaluation queries

---

## 9. Example Usage

### Python API

```python
from pathlib import Path
from pipeline.sqlite_artifact_bridge import SQLiteArtifactBridge

# Initialize bridge
bridge = SQLiteArtifactBridge(
    sqlite_path=Path("c:/path/to/juris_inventory.sqlite"),
    output_db_path=Path("data/canonical_cases.db")
)

# Import snapshot (all cases)
summary = bridge.import_snapshot()
print(f"Imported {summary.total_cases} cases")
print(f"EN: {summary.cases_by_language['en']}, FR: {summary.cases_by_language['fr']}")

# Generate canonical text records
for record in bridge.generate_canonical_text_records():
    print(f"Case: {record.case_id} ({record.language})")
    print(f"Quality: {record.quality_score:.2f}")
    print(f"Pages: {record.page_count}, Chars: {record.char_count}")
    
    # Pass to chunking pipeline...
```

### CLI Tool

```powershell
# Import SQLite snapshot
python -m pipeline.sqlite_artifact_bridge import `
  --sqlite "c:\path\to\juris_inventory.sqlite" `
  --output "data\canonical_cases.db" `
  --max-cases 1000

# Generate canonical text (dry-run)
python -m pipeline.sqlite_artifact_bridge generate `
  --output "data\canonical_cases.db" `
  --dry-run

# Export reject report
python -m pipeline.sqlite_artifact_bridge report `
  --output "data\canonical_cases.db" `
  --rejects "rejects.csv"
```

---

## 10. Success Criteria

The SQLite bridge implementation is successful when:

1. ✅ **95%+ import success rate** - Most cases pass quality gates
2. ✅ **Deterministic output** - Re-runs produce identical canonical text
3. ✅ **100% case ID coverage** - All records get valid case_id
4. ✅ **Blob references tracked** - Azure Storage paths preserved
5. ✅ **Lineage preserved** - SQLite source rows recorded per case
6. ✅ **Ready for chunking** - Canonical text format matches EPIC 6 input
7. ✅ **CDC-compatible** - Output schema works with future CDC integration

---

## 11. Next Steps

1. **Implement `sqlite_artifact_bridge.py`** (2-3 days)
2. **Run pilot import** (100 cases) - validate quality
3. **Connect to chunking pipeline** (EPIC 6)
4. **Execute full import** (~25k cases)
5. **Proceed to EVA DA ingestion** (EPIC 7)

---

## 12. Conclusion

The SQLite artifact bridge provides a **pragmatic path to immediate pipeline execution** while maintaining the architectural vision of CDC-driven ingestion. By leveraging existing, validated data from Project 05, we can:

- Start generating engineered case law **today**
- Validate the chunking and ingestion pipeline **without external dependencies**
- Prove retrieval quality **with real data**
- Migrate to CDC incrementally **when ready**

This approach exemplifies the core principle: **"Start ingestion immediately, using existing PDFs and JSON"** (README § 12).

---

**Document Owner**: Engineering Team  
**Review Status**: Pending Approval  
**Implementation Target**: February 2026
