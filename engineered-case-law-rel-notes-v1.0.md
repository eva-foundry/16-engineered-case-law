# Engineered Case Law (ECL) - Release Notes v1.0

**Version**: ECL v2.1.0 (PoC Phase 1)  
**Date**: 2026-02-01  
**Status**: Production PoC Complete  
**Project**: 16-engineered-case-law

---

## The Core Concept

**ECL (Engineered Case Law)** is a **structured plain-text format** designed to transform Canadian legal case documents into **RAG-optimized** (Retrieval-Augmented Generation) content for AI applications like EVA DA (Digital Assistant).

Think of it as **"case law engineering"** - taking raw legal decisions and restructuring them to be maximally useful for AI retrieval and question-answering systems.

---

## The Problem It Solves

### Before ECL:
❌ **PDF-first approach**
- Case text trapped in PDFs (inconsistent extraction quality)
- No standardized metadata structure
- Chunks lack context (AI doesn't know which case a chunk belongs to)
- Multi-page documents split arbitrarily
- No tribunal hierarchy information embedded
- Hard to search/filter efficiently

### After ECL:
✅ **RAG-optimized plain text**
- Consistent structure (17-line metadata header)
- Self-describing chunks (micro-headers every ~1,500 chars)
- Embedded context (citation, tribunal, rank, date in every chunk)
- Multi-language support (EN/FR)
- Quality-controlled extraction
- Search-boost keywords included

---

## ECL v2.1 Format Structure

### Part 1: 17-Line Metadata Header
```
================================================================================
FILE_STEM: scc_2007-SCC-22_2362_en
CITATION: 2007 SCC 22
DECISION_DATE: 2007-05-31
TRIBUNAL: SCC
TRIBUNAL_RANK: 1
LANGUAGE: EN
METADATA_PATH: scc-csc_en/scc-csc_2007_22_2362_en.json
PDF_URI: https://canlii.ca/.../scc-csc_2007_22_2362_en.pdf
WEB_URI: https://canlii.ca/t/1rqhw
SOURCE_NAME: Supreme Court of Canada
BLOB_PATH: /canlii/decisions/scc/2007/22/en
ECL_VERSION: 2.1.0
CONTENT_HASH: 7a3f9e2b1c8d5a4f
KEYWORDS: employment, insurance, misconduct, voluntary, claimant, eligibility, benefits
GENERATED: 2026-02-01T10:30:45Z
PAGE_COUNT: 42
BLOB_SIZE: 1847293
================================================================================
```

### Part 2: Content with Micro-Headers
```
[MH00000|EN|SCC|R1|2007-05-31|2007 SCC 22|scc_2007-SCC-22_2362_en]

Employment Insurance Act — Disqualification — Misconduct — Whether employee 
who was dismissed for cause from her employment is disqualified from receiving 
employment insurance benefits under s. 30 of the Employment Insurance Act...

[approximately 1,500 characters of content]

[MH00001|EN|SCC|R1|2007-05-31|2007 SCC 22|scc_2007-SCC-22_2362_en]

The question in this case is whether the claimant was dismissed from her 
employment for "misconduct" within the meaning of s. 30 of the Employment 
Insurance Act. The Social Security Tribunal found that she was...

[approximately 1,500 characters of content]

[MH00002|EN|SCC|R1|2007-05-31|2007 SCC 22|scc_2007-SCC-22_2362_en]

[...continues with sequential micro-headers throughout the entire case text...]
```

---

## Key Innovation: Micro-Headers with Sequential Counters

### Why This Matters for RAG:

**Problem**: When EVA DA chunks a document (e.g., every 500-1000 tokens), chunks lose their original context.

**ECL Solution**: Inject **self-describing micro-headers** every ~1,500 characters with sequential counters:

```
[MH00042|EN|SCC|R1|2007-05-31|2007 SCC 22|scc_2007-SCC-22_2362_en]
     │     │   │   │   │          │          │
     │     │   │   │   │          │          └─ Unique file identifier
     │     │   │   │   │          └─ Human-readable citation
     │     │   │   │   └─ Decision date
     │     │   │   └─ Tribunal rank (1=highest precedence)
     │     │   └─ Tribunal code
     │     └─ Language
     └─ Sequential counter (which chunk in the case)
```

**Result**: Every chunk retrieved by EVA DA contains:
- **What case** it's from (citation + file stem)
- **Which court** decided it (tribunal + rank)
- **When** it was decided (date)
- **What language** (EN/FR)
- **Where in the case** it appears (counter MH00042 means 43rd chunk)

This allows the AI to:
1. **Cite properly** ("According to paragraph 42 of 2007 SCC 22...")
2. **Rank by precedence** (SCC rank 1 > FCA rank 2 > FC rank 3 > SST rank 4)
3. **Filter by recency** (2024 cases more relevant than 2005)
4. **Show bilingual results** (FR query → FR cases)

---

## The Nine EPICs Architecture

ECL is part of a **comprehensive case law pipeline**:

### Phase 1 (PoC) - ✅ Complete:
- **EPIC 4**: Canonical Text Schema → ECL v2.1 format implemented
- **EPIC 6**: Chunk Engineering → Micro-headers with counters operational
- **EPIC 8**: Validation → 12 pre-flight checks + record validation
- **EPIC 9**: Governance → Logging, metrics, manifest generation

### Phase 2-5 (Pending):
- **EPIC 1**: CanLII Inventory & CDC (deferred - using static snapshot)
- **EPIC 2**: Artifact Acquisition (deferred - using JSON convenience data)
- **EPIC 3**: PDF Inspection & OCR (deferred - source quality TBD)
- **EPIC 5**: Multi-Language Support (implemented - EN/FR filtering)
- **EPIC 7**: Backend Ingestion (Phase 2 current priority)

---

## Current Status: 419 ECL v2.1 Cases

**Generated in PoC**:
- 199 English cases
- 220 French cases
- From 4 tribunals: SCC (Supreme Court), FCA (Federal Court of Appeal), FC (Federal Court), SST (Social Security Tribunal)
- Focus area: **Employment Insurance (EI) jurisprudence**

**Source**: SQLite database with JSON-extracted content (from CanLII)

---

## Why "Engineered" Case Law?

The term **"Engineered"** emphasizes that this isn't just:
- ❌ Raw case text copy-paste
- ❌ PDF extraction dumps
- ❌ Unstructured HTML scraping

It's **deliberately designed** with:
- ✅ **Metadata standards** (17 required fields)
- ✅ **Chunk self-description** (micro-headers every 1,500 chars)
- ✅ **Quality gates** (12 validation checks)
- ✅ **Semantic enrichment** (keywords extracted, content hashed)
- ✅ **Retrieval optimization** (tribunal ranks, language codes)
- ✅ **Version control** (ECL_VERSION field for schema evolution)

---

## Real-World Use Case: EVA DA

**Scenario**: User asks "Can I get EI benefits if I quit my job?"

**Without ECL**:
1. EVA DA searches PDF index
2. Retrieves chunk: "The claimant voluntarily left employment..."
3. ❌ No citation, no tribunal, no date, no context
4. Can't verify source or assess precedence

**With ECL v2.1**:
1. EVA DA searches ECL index
2. Retrieves chunk with micro-header:
   ```
   [MH00015|EN|SCC|R1|2012-03-15|2012 SCC 18|scc_2012-SCC-18_4521_en]
   
   The claimant voluntarily left employment. Under s. 29 of the 
   Employment Insurance Act, a claimant who voluntarily leaves 
   employment is disqualified from receiving benefits unless they 
   had just cause...
   ```
3. ✅ EVA DA knows:
   - **Source**: 2012 SCC 18 (Supreme Court of Canada)
   - **Authority**: Rank 1 (binding on all lower courts)
   - **Recency**: 2012 decision (still current law)
   - **Location**: Chunk 15 of the case
4. EVA DA responds: "According to the Supreme Court of Canada in 2012 SCC 18, voluntary leaving disqualifies you from EI benefits unless you had just cause..."

---

## Technical Achievement

**What makes ECL v2.1 production-ready**:

1. **Format Stability**: 17-line header schema defined and validated
2. **Micro-Header System**: Sequential counters (MH00000...) ensure chunk traceability
3. **Multi-Page Aggregation**: Handles _pages_1, _pages_2... correctly
4. **Stratified Sampling**: Balanced representation across tribunals
5. **Quality Validation**: 12 pre-flight checks catch data issues early
6. **Keyword Extraction**: Frequency-based with bilingual stopwords
7. **Content Hashing**: SHA256 for deduplication and change detection
8. **Tribunal Ranking**: Judicial hierarchy embedded (SCC=1, SST=4)
9. **Bilingual Support**: EN/FR cases with language-specific filtering
10. **Logging & Metrics**: Full audit trail and statistics

---

## Pipeline Implementation

### Active Scripts (6 modules, 2,393 lines):

1. **generate_ecl_v2.py** (569 lines) - Main orchestrator
2. **config.py** (108 lines) - Configuration management
3. **db_loader.py** (422 lines) - Database access + multi-page aggregation
4. **ecl_formatter.py** (462 lines) - ECL v2.1 formatting + micro-headers
5. **validators.py** (337 lines) - 12 pre-flight checks + record validation
6. **logger.py** (75 lines) - Structured logging

### Usage:
```bash
python generate_ecl_v2.py --limit-per-lang 50
python generate_ecl_v2.py --dry-run --limit-per-lang 3
python generate_ecl_v2.py --language en --limit-per-lang 50
python generate_ecl_v2.py --clean
```

### Outputs:
- ECL v2.1 files: `out/ecl-v2/*.ecl.txt`
- Manifest: `ecl-v2-manifest.csv`
- Metrics: `ecl-v2-metrics.json`
- Sample: `ecl-v2-sample.txt`
- Logs: Timestamp-based log files

---

## PoC Strategy

### ✅ Phase 1: ECL Pipeline (Complete)
- Implemented ECL v2.1 format with micro-headers
- Generated 419 test cases from SQLite convenience data
- Validated format stability and quality gates

### 🔄 Phase 2: Backend Ingestion (Current)
- Load ECL files into EVA DA backend programmatically
- Validate backend processing and indexing
- Test UI content management display
- Smoke test retrieval quality

### ⏳ Phase 3: Source Quality Analysis (Critical Decision)
- Compare SQLite JSON vs PDF vs HTML content quality
- Apply quality gates to sample cases
- **Decision Point**: Select canonical source based on evidence

### ⏳ Phase 4: Production Source Implementation
- Implement selected source extraction pipeline
- Regenerate ECL corpus with canonical source
- Validate no quality regression

### ⏳ Phase 5: CDC Integration
- Activate CanLII inventory snapshotting
- Implement incremental ingestion
- Configure freshness monitoring
- Production cutover

---

## Key Design Decisions

### 1. Source Strategy (SC-1)
**Current**: SQLite JSON content (CanLII-extracted, 2023 snapshot)  
**Future**: May switch to PDF/HTML extraction after Phase 3 analysis  
**Rationale**: ECL format stays the same regardless of source

### 2. Micro-Header Interval
**Choice**: Every ~1,500 characters (word-boundary aware)  
**Rationale**: Balances chunk self-description vs content density  
**Implementation**: Searches backward 100 chars for word boundaries

### 3. Tribunal Ranking
**Hierarchy**: SCC(1) > FCA(2) > FC(3) > SST(4) > Unknown(99)  
**Rationale**: Reflects Canadian judicial precedence  
**Impact**: Enables precedence-aware retrieval ranking

### 4. Header Fields (17)
**v2.1 Additions**: ECL_VERSION, CONTENT_HASH, KEYWORDS, GENERATED  
**Rationale**: Schema evolution support, deduplication, search boost, audit trail

### 5. Validation Gates (12)
**Philosophy**: Fail fast with clear error messages  
**Coverage**: Database, paths, schema, content quality, metadata formats  
**Result**: 100% of generated cases pass all gates

---

## Performance Metrics

**Generation Speed**: ~419 cases in <5 minutes  
**Average Case Size**: ~50KB plain text  
**Average Micro-Headers per Case**: ~30-40 (depends on length)  
**Validation Pass Rate**: 100% (12/12 gates pass)  
**Multi-Page Aggregation**: 100% success rate  
**Stratified Sampling**: Balanced across 4 tribunals

---

## Known Limitations (PoC Phase 1)

1. **Static Snapshot**: Using 2023 SQLite data (no CDC yet)
2. **Source Quality Unknown**: JSON quality not validated vs PDF/HTML
3. **Limited Scope**: 419 cases (EI domain only)
4. **No Backend Integration**: Format validated, ingestion pending Phase 2
5. **No Gold Set Testing**: Retrieval quality untested in production
6. **OCR Unknown**: % of image-only PDFs not assessed

---

## What's Next

### Immediate (Phase 2):
1. Create `ingest_to_evada.py` for programmatic backend loading
2. Validate backend parsing of ECL v2.1 format
3. Inspect UI content management interface
4. Run retrieval smoke tests (5 EI domain queries)
5. **Decision**: Go/No-Go for Phase 3

### Critical Path (Phase 3):
1. Compare JSON vs PDF vs HTML content quality (sample 100-500 cases)
2. Apply quality gates: length, char distribution, OCR artifacts
3. Assess OCR requirements (% image-only PDFs)
4. **Decision**: Select canonical source (JSON vs PDF vs HTML vs mixed)

### Production Path (Phase 4-5):
1. Implement canonical source extraction
2. Regenerate full corpus with selected source
3. Activate CDC for incremental updates
4. Scale to full CanLII EI inventory (estimated 10,000+ cases)

---

## Bottom Line

**ECL is about transforming messy, unstructured legal documents into AI-ready, self-describing, context-rich plain text that makes RAG systems actually useful for legal research.**

It's the difference between an AI saying:
- ❌ "I found something about voluntary leaving..." (useless)
- ✅ "The Supreme Court of Canada held in 2012 SCC 18..." (actionable)

**Success Criteria**: Phase 2 will validate this format works end-to-end when ingested into EVA DA backend and retrieved through the UI. If retrieval quality is promising, we proceed to Phase 3 source quality analysis to select the production source strategy.

---

## References

- **README.md**: Project overview and architecture
- **ACCEPTANCE.md**: Quality gates and DoD criteria
- **PHASE-2-BACKEND-INGESTION.md**: Next phase tactical guide
- **PIPELINE-SCRIPTS-INVENTORY.md**: Complete script catalog
- **pipeline/**: 6 active Python modules implementing ECL generation

---

**Document Version**: 1.0  
**Last Updated**: 2026-02-01 12:00:00  
**Status**: Release notes for ECL v2.1.0 PoC Phase 1
