# ECL v2.2 Quick Reference Card

**Version**: 2.2.1 | **Date**: February 1, 2026 | **Status**: Production Ready

---

## 🎯 What's New in v2.2.1

### 🆕 Substance-First RETRIEVAL_ANCHOR
- **Problem Solved**: v2.2.0 anchors started with 600+ chars of boilerplate ("Dockets: A-353-09... CORAM: LÉTOURNEAU...")
- **Solution**: Hierarchical detection
  - Priority 1: Numbered paragraphs `[1]`, `¶1` (85% success)
  - Priority 2: Section headings (Issues, Facts, Reasons) (12% success)
  - Priority 3: Boilerplate end markers (3% success)
- **Result**: 97% substantive-first anchors, 572-char avg boilerplate reduction
- **Quality**: Starts at legal issues, not cover pages

### 🆕 EI-Aware KEYWORDS
- **Problem Solved**: v2.2.0 included generic terms ("person", "which") and judge names ("pelletier", "nadon")
- **Solution**: Multi-signal scoring
  - 60-term bilingual EI lexicon (weights 1.5-3.0×)
  - Multi-word phrase extraction ("employment-insurance")
  - Statute reference detection (+10 bonus)
  - Judge name filtering (24 surnames + patterns)
- **Result**: 68% EI term coverage, 0.02% judge names (vs 12% in v2.2.0)
- **Quality**: Domain-specific keywords ("claimant", "umpire", "benefits")

### 📊 Quality Metrics
- ✅ 22,356 files generated in 5 min 3 sec (4,427 files/min)
- ✅ Zero performance degradation vs v2.2.0
- ✅ 8/8 unit tests passed
- ✅ 4× improvement in keyword domain relevance

---

## 🔧 v2.2 Core Features

### 1. RETRIEVAL_ANCHOR (v2.2.1 Enhanced)
- **Purpose**: Non-authoritative 900-char text snippet for semantic search pre-filtering
- **Extraction**: Boilerplate removal (judgment headers, case headers, procedural text)
- **Truncation**: Sentence boundary (searches backward 200 chars for `.`, `!`, `?`)
- **Use Case**: Quick relevance assessment, vector search, user previews
- **⚠️ Non-Authoritative**: For discovery only — always cite from full content

### 2. Enhanced Keywords (v2.2.1 EI-Aware)
- **Algorithm**: Multi-signal scoring with EI domain intelligence
- **Output**: 7 keywords max, comma-separated
- **Features**:
  - **NEW**: EI lexicon scoring (60 terms, weights 1.5-3.0×)
  - **NEW**: Multi-word phrase extraction ("employment-insurance")
  - **NEW**: Statute reference bonus (+10 score)
  - **NEW**: Judge name filtering (24 surnames)
  - Bilingual stopwords (50+ EN/FR)
  - Minimum 4 characters
  - Frequency threshold: ≥2 occurrences
- **Quality**: 68% EI term coverage, 0.02% judge names

### 3. Physical File Organization (5-Folder Layout)
```
out/ecl-v2/
├── en/
│   ├── scc/       # Supreme Court (R1) - 31 cases
│   ├── fca/       # Federal Court of Appeal (R2) - 249 cases
│   ├── fc/        # Federal Court (R3) - 0 cases
│   ├── sst/       # Social Security Tribunal (R4) - 10,483 cases (94%)
│   └── unknown/   # Unclassified (R5)
└── fr/ [same structure] — 11,593 cases total
```

### 4. Compact Micro-Headers
```
[ECL|MH00000|EN|SCC|R1|20070531|2007 SCC 22|scc_2007-SCC-22_2362_en]
```
- Date format: **YYYYMMDD** (8 chars instead of 10)
- Max length: **160 chars**
- Sequential counter: MH00000 → MH99999

---

## 📋 18-Line Metadata Header

```
ECL_VERSION: 2.2                    ← Schema version
CASE_ID: scc_2007-SCC-22_2362_en    ← Unique identifier
TITLE: Dunsmuir v. New Brunswick    ← Case title
LANGUAGE: EN                         ← EN or FR
TRIBUNAL: scc                        ← Court code
TRIBUNAL_RANK: R1                    ← Precedence (R1=highest)
CITATION: 2007 SCC 22                ← Neutral citation
DECISION_DATE: 2007-05-31            ← YYYY-MM-DD
PUBLICATION_DATE: 2007-05-31         ← YYYY-MM-DD
PUBLICATION_STATUS: published        ← Status
SOURCE_URL: https://canlii.org/...   ← CanLII URL
BLOB_PATH: /scc/2007-SCC-22/...      ← Azure blob (if available)
PDF_LINK: https://storage...         ← Direct PDF (if available)
CONTENT_HASH: a3f4b9c2d1e8f7a6       ← SHA256 (16 chars, deduplication)
PAGE_COUNT: 42                       ← Multi-page documents
KEYWORDS: judicial, review, ...      ← 7 keywords (NEW: enhanced)
RETRIEVAL_ANCHOR: The standard...    ← 900-char snippet (NEW in v2.2)
GENERATED: 2026-02-01T15:23:52Z      ← ISO 8601 timestamp
================================================================================
```

---

## 🚀 Quick Commands

```bash
# Generate full corpus (22,356 files)
python generate_ecl_v2.py --use-v22 --limit-per-lang 999999 --clean

# Generate 100 cases per language (test sample)
python generate_ecl_v2.py --use-v22 --limit-per-lang 100 --clean

# Filter by year (e.g., 2025 cases only)
python generate_ecl_v2.py --use-v22 --year 2025 --limit-per-lang 100 --clean

# Check output metrics
cat out/ecl-v2/ecl-v2-metrics.json | python -m json.tool

# Inspect sample case
head -30 out/ecl-v2/ecl-v2-sample.txt

# Validate manifest
python -c "import pandas as pd; print(pd.read_csv('out/ecl-v2/ecl-v2-manifest.csv').info())"
```

---

## 📊 Corpus Statistics

| Metric | Value |
|--------|-------|
| **Total Cases** | 22,356 |
| **English** | 10,763 (48.2%) |
| **French** | 11,593 (51.8%) |
| **Temporal Coverage** | 1978-2026 (48 years) |
| **Avg Content Length** | 19,741 chars |
| **Content Range** | 5,553 - 70,358 chars |

**Tribunal Distribution**:
- **SST** (Social Security Tribunal): 20,951 cases (93.7%)
- **FCA** (Federal Court of Appeal): 870 cases (3.9%)
- **FC** (Federal Court): 473 cases (2.1%)
- **SCC** (Supreme Court): 62 cases (0.3%)

---

## 🏗️ Pipeline Architecture

```
SQLite DB → db_loader.py → ecl_formatter.py → generate_ecl_v2.py → Output
   ↓            ↓                ↓                    ↓              ↓
pages_en   Query +       18-line header      5-folder layout    22,356
pages_fr   Aggregate     + micro-headers     + manifest.csv     ECL files
           multi-page    + keywords          + metrics.json
                        + anchor             + sample.txt
```

---

## 🔧 Key Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `ecl_version` | 2.2.0 | Schema version |
| `micro_header_every_chars` | 1500 | Injection interval |
| `micro_header_max_length` | 160 | Character limit |
| `retrieval_anchor_max_chars` | 900 | Discovery snippet size |
| `min_content_length` | 100 | Minimum case size (chars) |
| `random_seed` | eva-ecl-v2-fixed-seed | Deterministic sampling |

---

## 📁 Output Files

1. **ECL Files**: `out/ecl-v2/{lang}/{tribunal}/{filename}.ecl.txt`
   - Filename template: `{LANGIDX}_{rank-tribunal}_{YYYYMMDD}_{CASEID}_{DOCID}.ecl.txt`
   - Example: `EN_1-scc_20070531_2007-SCC-22_2362.ecl.txt`

2. **Manifest**: `out/ecl-v2/ecl-v2-manifest.csv`
   - 19 columns (all header fields)
   - Use for bulk loading, analysis, deduplication

3. **Metrics**: `out/ecl-v2/ecl-v2-metrics.json`
   - Summary statistics
   - Tribunal distribution
   - Content length stats
   - Validation errors (if any)

4. **Sample**: `out/ecl-v2/ecl-v2-sample.txt`
   - Example case for format inspection

---

## 🎨 Tribunal Precedence Hierarchy

| Rank | Tribunal | Code | Count (EN/FR) | Authority Level |
|------|----------|------|---------------|-----------------|
| **R1** | Supreme Court of Canada | scc | 31 / 31 | ⭐⭐⭐⭐⭐ Highest |
| **R2** | Federal Court of Appeal | fca | 249 / 621 | ⭐⭐⭐⭐ High |
| **R3** | Federal Court | fc | 0 / 473 | ⭐⭐⭐ Medium |
| **R4** | Social Security Tribunal | sst | 10,483 / 10,468 | ⭐⭐ Administrative |
| **R5** | Unknown | unknown | varies | ⭐ Unclassified |

**Use Cases**:
- Physical pre-filtering (folder-based queries)
- Precedence-based sorting (R1 highest authority)
- Court-specific analysis

---

## 🔍 Integration Patterns

### Azure AI Search Query
```python
# Physical pre-filtering + precedence sorting
results = search_client.search(
    search_text="employment insurance eligibility",
    filter="tribunal eq 'fca' and language eq 'EN'",
    order_by="tribunal_rank asc, decision_date desc",
    top=10
)
```

### Hybrid Search (Keyword + Vector)
```python
# Use retrieval_anchor for vector embeddings
results = search_client.search(
    search_text="judicial review standard",
    vector_queries=[{
        "vector": query_vector,  # from anchor embedding
        "k": 10,
        "fields": "content_vector"
    }],
    select="case_id,citation,retrieval_anchor",
    top=10
)
```

### RAG Context Injection
```python
# Micro-headers enable chunk citation
context = f"""
[Chunk from {case['citation']}]
{case['micro_header_00042']}
{chunk_text}
"""
```

---

## ⚠️ Important Notes

### RETRIEVAL_ANCHOR Status
- ✅ **Use for**: Discovery, pre-filtering, semantic search, previews
- ❌ **Do NOT use for**: Legal citation, authoritative references
- 🎯 **Always cite**: Full content or specific micro-header locations

### Micro-Header Usage
- ✅ **Use for**: Chunk identification, traceability, RAG context
- ❌ **Do NOT cite as**: Legal authority (cite CITATION field instead)
- 🎯 **Format**: `[ECL|MH00042|EN|SCC|R1|20070531|2007 SCC 22|case_id]`

### Content Hash (Deduplication)
- 16-char truncated SHA256
- Sufficient uniqueness for 22K corpus
- Use for: Detecting duplicates, content changes, integrity checks

---

## 📚 Documentation Links

| Document | Purpose |
|----------|---------|
| [ECL-COMPREHENSIVE-GUIDE.md](./ECL-COMPREHENSIVE-GUIDE.md) | Complete technical reference |
| [engineered-case-law.instructions.md](./engineered-case-law.instructions.md) | Copilot/AI assistant guidelines |
| [pipeline/README.md](./pipeline/README.md) | Pipeline implementation details |
| [IMPLEMENTATION_COMPLETE_v2.md](./IMPLEMENTATION_COMPLETE_v2.md) | Implementation summary |
| [pipeline/AUDIT-REPORT-2026-02-01.md](./pipeline/AUDIT-REPORT-2026-02-01.md) | Code audit findings |

---

## ✅ Quality Assurance

### Pre-Flight Checks (12 validations)
- Database existence & readability
- Output directory permissions
- Content availability (EN/FR)
- Index presence (performance)
- Table existence

### Format Validation
- 18-line header structure
- Delimiter lines (80 `=` chars)
- All required fields present
- Micro-header format (`[ECL|MH00000|...`)
- Version declaration (`ECL_VERSION: 2.2`)

### Metrics Tracking
- Total cases generated
- Language distribution (EN/FR)
- Tribunal distribution
- Content length statistics (min/max/avg)
- Validation errors (logged to JSON)

---

## 🚨 Troubleshooting

| Issue | Solution |
|-------|----------|
| "No content found" | Check `pages_en`/`pages_fr` tables, verify content_text NOT NULL |
| Micro-header > 160 chars | Long citation/case_id — update `sanitize_for_microheader()` to truncate |
| Manifest path mismatch | Ensure filename builder consistency between `write_files()` and `write_manifest()` |
| Missing RETRIEVAL_ANCHOR | Verify boilerplate patterns not too aggressive, check fallback logic |
| Performance slow | Add indexes: `CREATE INDEX idx_case_id ON pages_en(case_id)` |

---

**Version**: ECL v2.2.0  
**Last Updated**: February 1, 2026  
**Project**: EVA Foundation - Project 16  
**Repo**: `i:\EVA-JP-v1.2\docs\eva-foundation\projects\16-engineered-case-law`
