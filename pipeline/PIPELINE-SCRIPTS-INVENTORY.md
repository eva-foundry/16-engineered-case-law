# Pipeline Scripts Inventory

**Date**: 2026-02-01 12:00:00  
**Project**: 16-engineered-case-law  
**Pipeline Version**: ECL v2.1.0 (PoC Phase 1)

---

## Overview

This document inventories all Python scripts in the ECL v2.1 pipeline, documenting their versions, roles, status, and interdependencies.

---

## Active Production Scripts

### 1. generate_ecl_v2.py
**Version**: 2.1.0  
**Status**: ✅ Production (PoC Phase 1)  
**Role**: Main orchestrator - entry point for ECL generation  
**Lines**: 569  
**EPIC Mapping**: EPIC 4, 6, 8, 9

**Purpose**: Coordinates all pipeline steps from database query through ECL file generation, validation, and metrics.

**Key Functions**:
- `clean_output_directory()` - Remove existing ECL files safely
- `write_ecl_files()` - Write formatted ECL documents
- `write_manifest()` - Create CSV index of cases
- `write_metrics()` - Generate JSON statistics
- `write_sample()` - Create preview sample file
- `main()` - Command-line interface

**Dependencies**: config.py, logger.py, validators.py, db_loader.py, ecl_formatter.py

**Usage**:
```bash
python generate_ecl_v2.py --limit-per-lang 50
python generate_ecl_v2.py --dry-run --limit-per-lang 3
python generate_ecl_v2.py --language en --limit-per-lang 50
python generate_ecl_v2.py --clean
```

---

### 2. config.py
**Version**: 2.1.0  
**Status**: ✅ Production (PoC Phase 1)  
**Role**: Configuration management (foundation layer)  
**Lines**: 108  
**EPIC Mapping**: EPIC 9

**Purpose**: Centralized configuration with environment variable support and validation.

**Key Exports**:
- `CONFIG` - Main configuration dictionary
- `validate_config()` - Path and setting validation
- `print_config()` - Pretty-print configuration

**Configuration Categories**:
1. Database Settings (db_path)
2. Output Settings (output_dir, filenames)
3. Selection Criteria (cases_per_language, min_content_length)
4. Format Settings (micro_header settings)
5. Tribunal Precedence (tribunal_ranks)

**Environment Variables**:
- `ECL_DB_PATH`, `ECL_OUTPUT_DIR`, `ECL_CASES_PER_LANG`, `ECL_MIN_CONTENT`, `ECL_SEED`

---

### 3. db_loader.py
**Version**: 2.1.0  
**Status**: ✅ Production (PoC Phase 1)  
**Role**: Database access layer  
**Lines**: 422  
**EPIC Mapping**: EPIC 4, 5, 9

**Purpose**: Queries juris_inventory.sqlite, handles multi-page aggregation, stratified sampling, and CaseRecord construction.

**Key Features**:
1. Multi-page aggregation (_pages_1, _pages_2 → single CaseRecord)
2. Stratified sampling (SHA256-based deterministic selection)
3. Tribunal derivation (citation → tribunal code + rank)
4. Quality filtering (min length, non-null citation)

**Key Functions**:
- `load_cases_from_db()` - Main query + sampling logic
- `get_database_stats()` - Database inventory statistics
- `derive_tribunal()` - Extract tribunal from citation
- `_extract_page_number()` - Parse page number from ID
- `_strip_page_suffix()` - Remove _pages_N from ID

**Data Structure**: `CaseRecord` dataclass with 15+ fields

---

### 4. ecl_formatter.py
**Version**: 2.1.0  
**Status**: ✅ Production (PoC Phase 1)  
**Role**: ECL v2.1 formatting engine  
**Lines**: 462  
**EPIC Mapping**: EPIC 4, 6, 8

**Purpose**: Transforms CaseRecord objects into ECL v2.1 plain-text with 17-line headers and sequential micro-header injection.

**Key Features**:
1. ECL v2.1 format (17 fields: +ECL_VERSION, +CONTENT_HASH, +KEYWORDS, +GENERATED)
2. Micro-header injection with sequential counters (MH00000, MH00001...)
3. Keyword extraction (frequency-based, bilingual stopwords)
4. Content hashing (SHA256, 16-char truncated)
5. Format validation

**Micro-Header Format**:
```
[MH00000|EN|SCC|R1|2007-05-31|2007 SCC 22|scc_2007-SCC-22_2362_en]
```

**Key Functions**:
- `format_ecl_v2()` - Main formatting orchestration
- `build_micro_header()` - Create micro-header string
- `inject_micro_headers_with_counter()` - Inject with sequential counters
- `extract_keywords()` - Frequency-based keyword extraction
- `compute_content_hash()` - SHA256 hash (16-char)
- `validate_ecl_format()` - Post-formatting validation
- `get_sample_preview()` - Generate preview snippet

**Source Strategy**: SC-1 (SQLite JSON content, PDF referenced but not extracted)

---

### 5. validators.py
**Version**: 2.1.0  
**Status**: ✅ Production (PoC Phase 1)  
**Role**: Validation framework (quality gates)  
**Lines**: 337  
**EPIC Mapping**: EPIC 8, 9

**Purpose**: Implements 12 pre-flight checks and record-level validation to ensure data quality.

**Pre-Flight Checks (12 Gates)**:
1. Database file exists
2. Database readable/writable
3. Output directory exists
4. Output directory writable
5. Database schema valid (pages table)
6. Database has content (>0 records)
7. Database has EN records
8. Database has FR records
9. Sample content quality check
10. Sample citation format check
11. Sample metadata completeness
12. Sample date format validation

**Record-Level Validation**:
- Required fields (id, content, metadata_relpath)
- Content length (min 1000 chars)
- Content encoding (UTF-8, no null bytes)
- Content quality (max 80% non-alphanumeric)
- Citation format (court regex patterns)
- Date format (ISO 8601)
- URL format (http/https)

**Key Functions**:
- `preflight_checks()` - Run all 12 gates
- `print_preflight_report()` - Pretty-print results
- `CaseRecordValidator.validate_record()` - Record checks

**Validation Severity**: CRITICAL, WARNING, INFO

---

### 6. logger.py
**Version**: 2.1.0  
**Status**: ✅ Production (PoC Phase 1)  
**Role**: Structured logging infrastructure  
**Lines**: 75  
**EPIC Mapping**: EPIC 9

**Purpose**: Dual-handler logging (console + file) with context managers for operation tracking.

**Key Features**:
1. Dual handlers (console INFO+, file DEBUG+)
2. LogContext manager (wraps operations with start/complete logs)
3. Automatic directory creation
4. UTF-8 encoding for international characters

**Log Formats**:
- Console: `12:34:56 | INFO     | Generated 419 ECL files`
- File: `2026-02-01 12:34:56 | ecl_generator | INFO     | main:123 | Generated 419 ECL files`

**Key Functions**:
- `setup_logger()` - Configure logger with handlers
- `LogContext` - Context manager for operation blocks

**Usage**:
```python
logger = setup_logger('ecl_generator', log_file=Path('logs/run.log'))
with LogContext(logger, 'Database loading'):
    cases = load_cases_from_db(...)
```

---

## Planned/Future Scripts

### 7. artifact_manager.py
**Version**: 1.0.0 (PLANNED)  
**Status**: ⏳ NOT USED IN POC PHASE 1  
**Role**: Artifact acquisition and blob storage management  
**Lines**: 313  
**EPIC Mapping**: EPIC 2, 9

**Purpose**: Downloads PDFs/HTML from CanLII, manages Azure Blob Storage, implements deduplication.

**Activation Trigger**: IF Phase 3 determines PDF/HTML extraction needed

**Key Features (Planned)**:
1. HTTP downloads with retry/rate limiting
2. Azure Blob Storage uploads
3. Content hash deduplication (SHA256)
4. Metadata tracking (ArtifactRecord)

**WHY DEFERRED**: PoC uses SQLite JSON content; source quality validation pending Phase 3.

---

### 8. canlii_inventory.py
**Version**: 1.0.0 (PLANNED)  
**Status**: ⏳ NOT USED IN POC PHASE 1  
**Role**: Inventory management and CDC foundation  
**Lines**: 341  
**EPIC Mapping**: EPIC 1, 9

**Purpose**: Takes snapshots of CanLII case inventory, computes CDC diffs for incremental updates.

**Activation Trigger**: Phase 5 (Production CDC integration)

**Key Features (Planned)**:
1. CanLII API inventory snapshots
2. CDC diff computation (new/updated/deleted)
3. Content hashing for change detection
4. Scope management (multiple subsets)

**WHY DEFERRED**: PoC uses static SQLite snapshot; CDC not needed for validation.

---

### 9. text_extractor.py
**Version**: 1.0.0 (PLANNED)  
**Status**: ⏳ NOT USED IN POC PHASE 1  
**Role**: PDF/HTML text extraction with quality gates  
**Lines**: 343  
**EPIC Mapping**: EPIC 3, 4, 9

**Purpose**: Extracts text from PDFs/HTML with quality gates and selective OCR.

**Activation Trigger**: IF Phase 3 selects PDF/HTML as canonical source

**Key Features (Planned)**:
1. Multi-strategy extraction (PyPDF2 → Azure DI OCR → HTML)
2. Quality gates (length, char distribution, page coverage)
3. OCR decisioning (auto-detect image-only PDFs)
4. Extraction metadata tracking

**WHY DEFERRED**: PoC uses SQLite JSON content; Phase 3 will compare quality vs PDF/HTML.

---

## Deprecated Scripts

### 10. ecl_formatter_NEW.py
**Version**: 1.0.0 (DEPRECATED)  
**Status**: 🗄️ ARCHIVED - DO NOT USE  
**Role**: Early ECL v2 formatter prototype  
**Lines**: 238  
**Replaced By**: ecl_formatter.py v2.1.0

**Purpose**: Early prototype without sequential counter micro-headers.

**WHY DEPRECATED**: Lacked sequential counters (MH00000, MH00001...) needed for robust chunk self-description.

**Migration**: All functionality in ecl_formatter.py v2.1.0

---

## Pipeline Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                     ECL v2.1 GENERATION PIPELINE                    │
└─────────────────────────────────────────────────────────────────────┘

[User Command Line]
        │
        ▼
┌───────────────────────────────────────────────────────────────────┐
│ generate_ecl_v2.py (ORCHESTRATOR)                                 │
│ - Parse CLI arguments                                             │
│ - Setup logging (logger.py)                                       │
│ - Load configuration (config.py)                                  │
└───────────────────────────────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────────────────────────────┐
│ validators.py (PRE-FLIGHT CHECKS)                                 │
│ - 12 quality gates                                                │
│ - Database connectivity                                           │
│ - Output directory validation                                     │
└───────────────────────────────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────────────────────────────┐
│ db_loader.py (DATA LOADING)                                       │
│ - Query juris_inventory.sqlite                                    │
│ - Multi-page aggregation                                          │
│ - Stratified sampling by tribunal                                 │
│ - Build CaseRecord objects                                        │
└───────────────────────────────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────────────────────────────┐
│ ecl_formatter.py (FORMATTING)                                     │
│ - Build 17-line ECL v2.1 headers                                  │
│ - Extract keywords (frequency-based)                              │
│ - Compute content hash (SHA256)                                   │
│ - Inject micro-headers with sequential counters                   │
│ - Validate ECL format                                             │
└───────────────────────────────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────────────────────────────┐
│ generate_ecl_v2.py (OUTPUT WRITING)                               │
│ - Write .ecl.txt files                                            │
│ - Generate manifest CSV                                           │
│ - Generate metrics JSON                                           │
│ - Generate sample preview                                         │
└───────────────────────────────────────────────────────────────────┘
        │
        ▼
   [419 ECL v2.1 Files Generated]
```

---

## Future Pipeline Extensions

### Phase 2: Backend Ingestion (Current Priority)
**New Script**: `ingest_to_evada.py` (to be created)
- Load ECL files into EVA DA backend programmatically
- Validate backend processing and indexing
- Test UI content management display

### Phase 3: Source Quality Analysis
**New Scripts**: 
- `compare_source_quality.py` (to be created)
- Compare JSON vs PDF vs HTML content quality
- Apply quality gates to sample cases
- Generate decision matrix for canonical source

### Phase 4: Production Source Implementation
**Activate**:
- `artifact_manager.py` (if PDF/HTML selected)
- `text_extractor.py` (if PDF/HTML selected)
- Update `db_loader.py` to use extracted text

### Phase 5: CDC Integration
**Activate**:
- `canlii_inventory.py`
- Implement incremental refresh workflow
- Configure freshness monitoring

---

## Dependencies Matrix

| Script | config.py | logger.py | validators.py | db_loader.py | ecl_formatter.py | sqlite3 | hashlib | re | dataclasses |
|--------|-----------|-----------|---------------|--------------|------------------|---------|---------|----|----|
| generate_ecl_v2.py | ✓ | ✓ | ✓ | ✓ | ✓ | - | - | - | - |
| config.py | - | - | - | - | - | - | - | - | - |
| db_loader.py | ✓ | - | - | - | - | ✓ | ✓ | ✓ | ✓ |
| ecl_formatter.py | - | - | - | ✓ | - | - | ✓ | ✓ | - |
| validators.py | - | - | - | - | - | ✓ | - | ✓ | ✓ |
| logger.py | - | - | - | - | - | - | - | - | - |

---

## Version History

### v2.1.0 (2026-02-01) - Current Production PoC
- **generate_ecl_v2.py**: Sequential counter micro-headers, clean mode
- **ecl_formatter.py**: MH00000... counters, keyword extraction, content hashing
- **db_loader.py**: Multi-page aggregation, tribunal ranking
- **validators.py**: 12 pre-flight checks
- **config.py**: Micro-header configuration parameters
- **logger.py**: Dual handlers with context managers

### v2.0.0 (2026-01-28) - ECL v2.1 Format Upgrade
- Added 4 new header fields (ECL_VERSION, CONTENT_HASH, KEYWORDS, GENERATED)
- 16 → 17 line headers

### v1.0.0 (2026-01-15) - Initial ECL v2.0 Implementation
- Basic ECL format with 16-line headers
- SQLite database queries
- Simple micro-header injection (no counters)

---

## Key Metrics

**Total Active Scripts**: 6 (2,393 lines of Python)  
**Total Planned Scripts**: 3 (997 lines of Python)  
**Deprecated Scripts**: 1 (238 lines)  
**PoC Completion**: Phase 1 complete, Phase 2 current priority

**Generated in PoC**:
- 419 ECL v2.1 files (199 EN, 220 FR)
- 17-line headers with micro-headers (MH00000...)
- Manifest CSV, Metrics JSON, Sample preview

---

**Document Version**: 1.0  
**Last Updated**: 2026-02-01 12:00:00  
**Status**: Active - reflects current pipeline state
