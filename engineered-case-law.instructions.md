---
applyTo: '16-engineered-case-law/**'
---

# Copilot Instructions: Engineered Case Law (ECL) v2.2 Pipeline

## Context & Purpose

You are working with the **Engineered Case Law (ECL) v2.2 pipeline**, a production-grade system for transforming Canadian jurisprudence into AI-optimized legal documents. ECL is **not raw case documents** — it's a governed, normalized, retrieval-ready representation designed for RAG systems.

### Key Principles

1. **Canonical Identity**: One case = one `case_id`, multi-page documents aggregated
2. **Deterministic Processing**: Fixed seed for reproducible sampling
3. **Source Lineage**: Every case traces to authoritative artifacts (PDF/HTML/JSON)
4. **Quality First**: Validation at every stage, auditability built-in
5. **EVA DA Integration**: Optimized for Azure AI Search + RAG workflows

---

## ECL v2.2 Format Specification

### 18-Line Metadata Header

```
ECL_VERSION: 2.2
CASE_ID: scc_2007-SCC-22_2362_en
TITLE: Dunsmuir v. New Brunswick
LANGUAGE: EN
TRIBUNAL: scc
TRIBUNAL_RANK: R1
CITATION: 2007 SCC 22
DECISION_DATE: 2007-05-31
PUBLICATION_DATE: 2007-05-31
PUBLICATION_STATUS: published
SOURCE_URL: https://www.canlii.org/en/ca/scc/doc/2007/2007scc22/2007scc22.html
BLOB_PATH: /scc/2007-SCC-22/2007-SCC-22-EN.pdf
PDF_LINK: https://storage.example.com/cases/scc/2007-SCC-22.pdf
CONTENT_HASH: a3f4b9c2d1e8f7a6
PAGE_COUNT: 42
KEYWORDS: judicial, review, standard, reasonableness, correctness, deference, administrative
RETRIEVAL_ANCHOR: The standard of review analysis determines the degree of deference a reviewing court should show to an administrative decision-maker's interpretation of law...
GENERATED: 2026-02-01T15:23:52Z
================================================================================
```

### Critical Fields (NEW in v2.2)

- **RETRIEVAL_ANCHOR**: Non-authoritative discovery snippet (≤900 chars)
  - Boilerplate-free extraction
  - Sentence-boundary truncation
  - Used for semantic pre-filtering
  - **NOT** a legal citation source (full content is authoritative)

- **ENHANCED KEYWORDS**: Frequency-based, bilingual stopword filtering
  - 7 keywords max
  - Minimum 4 characters
  - Frequency threshold: ≥2 occurrences
  - Hyphen-splitting for legislative refs (e.g., `RSC-1985-c-B-3`)

### Micro-Header Format (v2.2 Compact)

```
[ECL|MH00000|EN|SCC|R1|20070531|2007 SCC 22|scc_2007-SCC-22_2362_en]
```

**Format**: `[ECL|MH{CTR}|{LANG}|{TRIBUNAL}|R{RANK}|{YYYYMMDD}|{CITATION}|{CASE_ID}]`

**Injection Rules**:
- Every ~1,500 characters
- Word boundary detection (searches backward 100 chars)
- Max length: 160 chars
- Sequential counter: MH00000 → MH99999
- Final tolerance: 200 chars from end

---

## File Organization (5-Folder Layout)

```
out/ecl-v2/
├── en/
│   ├── scc/       # Supreme Court (R1) - Highest precedence
│   ├── fca/       # Federal Court of Appeal (R2)
│   ├── fc/        # Federal Court (R3)
│   ├── sst/       # Social Security Tribunal (R4) - ~94% of corpus
│   └── unknown/   # Unclassified tribunals (R5)
├── fr/
│   └── [same structure]
├── ecl-v2-manifest.csv      # 19 columns, all header fields
├── ecl-v2-metrics.json      # Summary statistics
└── ecl-v2-sample.txt        # Example case
```

### Filename Template

`{LANGIDX}_{rank-tribunal}_{YYYYMMDD}_{CASEID}_{DOCID}.ecl.txt`

**Example**: `EN_1-scc_20070531_2007-SCC-22_2362.ecl.txt`

**Components**:
- `LANGIDX`: EN or FR (uppercase)
- `rank-tribunal`: e.g., `1-scc`, `2-fca`, `4-sst`
- `YYYYMMDD`: Decision date (8 digits, sorts chronologically)
- `CASEID`: Citation slug (e.g., `2007-SCC-22`)
- `DOCID`: Database doc_id (unique identifier)

---

## Pipeline Architecture

### Module Hierarchy

```
generate_ecl_v2.py         (Main orchestrator)
    ├── config.py          (Configuration, env vars)
    ├── preflight.py       (12 validation checks)
    ├── db_loader.py       (Database access, multi-page aggregation)
    │   └── CaseRecord     (Data structure)
    └── ecl_formatter.py   (ECL v2.2 formatting)
        ├── format_ecl_v22()              (18-line header)
        ├── extract_retrieval_anchor()    (Boilerplate removal)
        ├── extract_keywords()            (Frequency analysis)
        ├── inject_micro_headers_with_counter()
        └── validate_ecl_format()         (Post-generation check)
```

### Data Flow

1. **Source**: SQLite `pages_en` / `pages_fr` tables
2. **Load**: Query with filters (year, min_content, tribunal)
3. **Aggregate**: Multi-page documents by `case_id`
4. **Format**: Build 18-line header + inject micro-headers
5. **Write**: Organize into 5-folder layout
6. **Manifest**: CSV with all metadata (19 columns)
7. **Metrics**: JSON summary statistics

---

## Critical Implementation Rules

### 1. Content Hashing

```python
# SHA256, 16-char truncated for deduplication
content_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()[:16]
```

**Use Cases**:
- Deduplication across languages (EN vs FR)
- Detect content changes in CDC
- Manifest integrity checks

### 2. Boilerplate Detection (RETRIEVAL_ANCHOR)

**Patterns to Remove** (standalone headers only):
```regex
^\s*JUDGMENT\s*$
^\s*JUGEMENT\s*$
^\s*BETWEEN:\s*$
^\s*ENTRE:\s*$
^\s*CITATION:\s+\d+\s+\w+
^\s*CORAM:\s*$
^\s*COURT FILE NO\.:\s*\d+
```

**Truncation Strategy**:
1. Remove boilerplate lines
2. Reconstruct text with spaces
3. Normalize whitespace
4. Find last sentence ending before 900 chars
5. Search backward 200 chars for `.`, `!`, `?`
6. Include punctuation, strip trailing space

### 3. Keyword Extraction (Bilingual)

**Stopwords** (50+ each language):
```python
# English
stopwords_en = {
    "the", "and", "that", "this", "with", "from", "have", "been",
    "was", "were", "are", "for", "not", "but", "can", "will", ...
}

# French
stopwords_fr = {
    "le", "la", "les", "de", "et", "des", "un", "une",
    "dans", "pour", "que", "qui", "est", "sont", "avec", ...
}
```

**Algorithm**:
```python
1. Remove URLs, emails, special chars
2. Tokenize with hyphen-splitting (preserve legislative refs)
3. Lowercase + filter stopwords
4. Minimum length: 4 chars
5. Frequency threshold: ≥2 occurrences
6. Select top 7 keywords
```

### 4. Micro-Header Injection

**Counter System** (v2.2):
```python
counter = 0  # Start at MH00000
while position < len(content):
    # Insert micro-header at current position
    micro_header = f"[ECL|MH{counter:05d}|{lang}|{tribunal}|R{rank}|{date_compact}|{citation}|{case_id}]"
    
    # Find word boundary (search backward 100 chars)
    boundary = find_word_boundary(content, position, search_distance=100)
    
    # Inject and advance
    content = content[:boundary] + micro_header + content[boundary:]
    position += target_interval + len(micro_header)
    counter += 1
```

**Validation**:
- Max length: 160 chars (raise error if exceeded)
- Counter limit: 99999 (5 digits)
- Final tolerance: No micro-header within 200 chars of end

---

## Command-Line Usage

### Happy Path (Simple)

```bash
# Generate 100 cases per language
python generate_ecl_v2.py --use-v22 --limit-per-lang 100 --clean

# Generate all cases (full corpus: 22,356 files)
python generate_ecl_v2.py --use-v22 --limit-per-lang 999999 --clean

# Filter by year
python generate_ecl_v2.py --use-v22 --year 2025 --limit-per-lang 100 --clean

# Filter by year range (multiple generations)
python generate_ecl_v2.py --use-v22 --year 2024 --limit-per-lang 999999 --clean
python generate_ecl_v2.py --use-v22 --year 2025 --limit-per-lang 999999 --clean
```

### Advanced Path (Optional)

```bash
# [ADVANCED] Stratified sampling by tribunal
python generate_ecl_v2.py --use-v22 --stratify-by tribunal --per-group 25

# [ADVANCED] Stratified sampling with year filter
python generate_ecl_v2.py --use-v22 --year 2025 --stratify-by tribunal --per-group 10
```

### Key Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `--use-v22` | Flag | False | **REQUIRED** for v2.2 format (18 fields + RETRIEVAL_ANCHOR) |
| `--limit-per-lang` | int | 50 | Max cases per language (use 999999 for full corpus) |
| `--year` | int | None | Filter by publication year (e.g., 2025) |
| `--min-content` | int | 100 | Minimum content length (chars) |
| `--clean` | Flag | False | Delete existing files before generation |
| `--stratify-by` | str | None | **[ADVANCED]** Group by: tribunal, year |
| `--per-group` | int | None | **[ADVANCED]** Cases per stratification group |

---

## Database Schema Reference

### Tables: `pages_en`, `pages_fr`

**Key Fields**:
```sql
doc_id          INTEGER    -- Document identifier (unique per page)
case_id         TEXT       -- Case identifier (aggregation key)
citation        TEXT       -- Neutral citation (e.g., "2007 SCC 22")
tribunal        TEXT       -- Court code: scc, fca, fc, sst
decision_date   TEXT       -- YYYY-MM-DD or YYYYMMDD
publication_date TEXT      -- YYYY-MM-DD or YYYYMMDD
content_text    TEXT       -- Full text (JSON-extracted)
content_length  INTEGER    -- Character count
title           TEXT       -- Case title
source_url      TEXT       -- CanLII URL
blob_path       TEXT       -- Azure blob path (if available)
pdf_link        TEXT       -- Direct PDF link (if available)
```

**Indexes**: `case_id`, `publication_date`, `tribunal`

### Query Pattern (Multi-Page Aggregation)

```python
# Load all pages for a case
pages = db.execute("""
    SELECT * FROM pages_en 
    WHERE case_id = ?
    ORDER BY doc_id
""", (case_id,))

# Concatenate content_text
full_content = '\n\n'.join(page['content_text'] for page in pages)

# Create CaseRecord with aggregated content + page count
case = CaseRecord(
    case_id=case_id,
    content=full_content,
    page_count=len(pages),
    ...
)
```

---

## Quality Assurance

### Pre-Flight Checks (12 Validations)

**Must Pass** (pipeline exits on failure):
- `db_exists`: Database file found
- `db_readable`: SQLite valid
- `output_dir_writable`: Write permissions OK
- `pages_en_with_content`: EN content available
- `pages_fr_with_content`: FR content available
- `table_pages_en`: Table exists
- `table_pages_fr`: Table exists

**Warnings** (logged, pipeline continues):
- `pages_en_indexed`: case_id index missing (performance impact)
- `python_version_ok`: Python < 3.8
- `table_blobs`: Missing blob reference table
- `tribunal_folders_valid`: Folder config incomplete
- `random_seed_set`: Non-deterministic sampling

### Format Validation (`validate_ecl_format`)

**Checks**:
1. 18 header lines present (v2.2)
2. Delimiter line: `=` × 80 chars
3. All required fields present (no missing values)
4. `ECL_VERSION: 2.2` declared
5. Micro-headers start with `[ECL|MH00000|`
6. Content follows header

### Metrics Tracking (JSON)

```json
{
  "generation_timestamp": "2026-02-01T15:23:52Z",
  "total_cases": 22356,
  "english_cases": 10763,
  "french_cases": 11593,
  "tribunal_distribution": {
    "scc": 62,
    "fca": 870,
    "fc": 473,
    "sst": 20951
  },
  "content_statistics": {
    "min_length": 5553,
    "max_length": 70358,
    "avg_length": 19741
  },
  "validation_errors": [],
  "configuration": {
    "ecl_version": "2.2.0",
    "min_content_length": 100,
    "random_seed": "eva-ecl-v2-fixed-seed"
  }
}
```

---

## Common Tasks & Patterns

### Task: Add New Field to ECL Header

1. **Update `config.py`**:
   ```python
   CONFIG['new_field_config'] = 'value'
   ```

2. **Update `ecl_formatter.py`**:
   ```python
   def format_ecl_v22(case, config):
       header_lines = [
           f"ECL_VERSION: {config['ecl_version']}",
           # ... existing fields ...
           f"NEW_FIELD: {compute_new_field(case)}",  # Add here
           f"GENERATED: {timestamp}"
       ]
   ```

3. **Update manifest writer** in `generate_ecl_v2.py`:
   ```python
   manifest_row = [
       case.case_id, case.title, ...,
       compute_new_field(case)  # Add to CSV columns
   ]
   ```

4. **Update validation** in `ecl_formatter.py`:
   ```python
   required_fields = [
       'ECL_VERSION', 'CASE_ID', ..., 'NEW_FIELD', 'GENERATED'
   ]
   ```

### Task: Modify RETRIEVAL_ANCHOR Extraction

**Location**: `ecl_formatter.py::extract_retrieval_anchor()`

**Example**: Add new boilerplate pattern
```python
boilerplate_patterns = [
    r'^\s*JUDGMENT\s*$',
    r'^\s*NEW_PATTERN_TO_REMOVE\s*$',  # Add here
    # ... existing patterns ...
]
```

**Testing**:
```bash
# Generate sample and inspect anchor
python generate_ecl_v2.py --use-v22 --limit-per-lang 1 --clean
cat out/ecl-v2/ecl-v2-sample.txt | grep -A 5 "RETRIEVAL_ANCHOR"
```

### Task: Change Filename Format

**Location**: `generate_ecl_v2.py` (filename generation section)

**Current Template**: `{LANGIDX}_{rank-tribunal}_{YYYYMMDD}_{CASEID}_{DOCID}.ecl.txt`

**To Modify**:
```python
# Update filename template in config.py
CONFIG['filename_template_fields'] = ['langidx', 'tribunal', 'date', 'caseid']

# Update filename builder in generate_ecl_v2.py
def build_filename(case, config):
    langidx = case.language.upper()
    rank = config['tribunal_ranks'].get(case.tribunal, 5)
    date = case.decision_date.replace('-', '')
    caseid = sanitize_for_filename(case.citation)
    
    # New format: EN_scc_20070531_2007-SCC-22.ecl.txt
    return f"{langidx}_{case.tribunal}_{date}_{caseid}.ecl.txt"
```

### Task: Query Database for Specific Cases

```python
from db_loader import load_cases_from_db

# Load all 2025 cases
cases = load_cases_from_db(
    db_path='path/to/juris_inventory.sqlite',
    language='EN',
    limit=999999,
    year_filter=2025,
    min_content_length=100
)

# Load SCC cases only (requires custom query modification)
# See db_loader.py::load_cases_from_db() for filter options
```

---

## Integration with EVA DA

### Azure AI Search Index Schema

```json
{
  "name": "ecl-v2-index",
  "fields": [
    {"name": "case_id", "type": "Edm.String", "key": true},
    {"name": "title", "type": "Edm.String", "searchable": true},
    {"name": "language", "type": "Edm.String", "filterable": true},
    {"name": "tribunal", "type": "Edm.String", "filterable": true},
    {"name": "tribunal_rank", "type": "Edm.String", "sortable": true},
    {"name": "citation", "type": "Edm.String", "searchable": true, "facetable": true},
    {"name": "decision_date", "type": "Edm.DateTimeOffset", "sortable": true, "filterable": true},
    {"name": "keywords", "type": "Collection(Edm.String)", "searchable": true},
    {"name": "retrieval_anchor", "type": "Edm.String", "searchable": true},
    {"name": "content", "type": "Edm.String", "searchable": true},
    {"name": "content_vector", "type": "Collection(Edm.Single)", "dimensions": 1536, "vectorSearchProfile": "ecl-vector-profile"}
  ],
  "vectorSearch": {
    "profiles": [
      {"name": "ecl-vector-profile", "algorithm": "ecl-hnsw"}
    ],
    "algorithms": [
      {"name": "ecl-hnsw", "kind": "hnsw"}
    ]
  }
}
```

### Bulk Loading Pattern

```python
from azure.search.documents import SearchClient
import pandas as pd

# Load manifest
manifest = pd.read_csv('out/ecl-v2/ecl-v2-manifest.csv')

# Prepare documents for indexing
documents = []
for _, row in manifest.iterrows():
    # Read ECL file
    file_path = f"out/ecl-v2/{row['output_path']}"
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract content (skip header)
    content_start = content.find('=' * 80) + 81
    case_content = content[content_start:].strip()
    
    # Generate embedding from retrieval_anchor
    anchor_vector = embed_text(row['retrieval_anchor'])
    
    documents.append({
        'case_id': row['case_id'],
        'title': row['title'],
        'language': row['language'],
        'tribunal': row['tribunal'],
        'tribunal_rank': row['tribunal_rank'],
        'citation': row['citation'],
        'decision_date': row['decision_date'],
        'keywords': row['keywords'].split(', '),
        'retrieval_anchor': row['retrieval_anchor'],
        'content': case_content,
        'content_vector': anchor_vector
    })

# Batch upload (1000 docs/batch)
search_client.upload_documents(documents[:1000])
```

### Query Examples

```python
# Physical pre-filtering (folder-based)
results = search_client.search(
    search_text="employment insurance",
    filter="tribunal eq 'sst' and language eq 'EN'",
    top=20
)

# Precedence-based ranking
results = search_client.search(
    search_text="judicial review",
    order_by="tribunal_rank asc, decision_date desc",
    top=10
)

# Hybrid search (keyword + vector)
results = search_client.search(
    search_text="standard of review",
    vector_queries=[{
        "vector": query_vector,
        "k": 10,
        "fields": "content_vector"
    }],
    select="case_id,citation,title,retrieval_anchor",
    top=10
)
```

---

## Troubleshooting

### Issue: "No content found" error

**Cause**: `pages_en` or `pages_fr` table empty or content_text NULL

**Fix**:
```sql
-- Check content availability
SELECT COUNT(*) FROM pages_en WHERE content_text IS NOT NULL AND content_length > 100;
SELECT COUNT(*) FROM pages_fr WHERE content_text IS NOT NULL AND content_length > 100;

-- Verify specific case
SELECT case_id, content_length FROM pages_en WHERE case_id = 'target_case_id';
```

### Issue: Micro-header length exceeds 160 chars

**Cause**: Long citation or case_id

**Fix**: Update `sanitize_for_microheader()` to truncate:
```python
def build_micro_header_v22(case, counter, max_length=160):
    # Build header
    header = f"[ECL|MH{counter:05d}|{lang}|{tribunal}|R{rank}|{date_compact}|{citation}|{case_id}]"
    
    # Validate length
    if len(header) > max_length:
        # Truncate case_id to fit
        overflow = len(header) - max_length
        case_id_truncated = case_id[:-(overflow + 3)] + '...'
        header = f"[ECL|MH{counter:05d}|{lang}|{tribunal}|R{rank}|{date_compact}|{citation}|{case_id_truncated}]"
    
    return header
```

### Issue: Manifest output_path doesn't match actual files

**Cause**: Filename template changed without updating manifest writer

**Fix**: Ensure consistency between:
1. `generate_ecl_v2.py::write_files()` (actual filename)
2. `generate_ecl_v2.py::write_manifest()` (manifest output_path)

```python
# Both must use same filename builder
filename = build_filename(case, config)
output_path = f"{lang}/{tribunal}/{filename}"
```

### Issue: Duplicate case_ids across languages

**Expected Behavior**: EN and FR versions of same case have different `case_id`:
- EN: `scc_2007-SCC-22_2362_en`
- FR: `scc_2007-SCC-22_2362_fr`

**Validation**:
```bash
# Check for duplicates in manifest
cut -d',' -f1 ecl-v2-manifest.csv | sort | uniq -d
# Should return empty (no duplicates)
```

---

## Performance Optimization

### Current Benchmarks (22,356 files)

- Database loading: ~11 seconds total
- File writing: ~4 minutes total
- Manifest generation: ~2 minutes
- **Total pipeline**: ~7 minutes (3,200 files/minute)

### Optimization Strategies

1. **Parallel Processing** (future enhancement):
   ```python
   from concurrent.futures import ProcessPoolExecutor
   
   with ProcessPoolExecutor(max_workers=4) as executor:
       executor.map(write_ecl_file, cases)
   ```

2. **Batch Database Queries**:
   ```python
   # Current: One query per language
   # Optimized: Single query with UNION
   query = """
   SELECT *, 'EN' as lang FROM pages_en WHERE ...
   UNION ALL
   SELECT *, 'FR' as lang FROM pages_fr WHERE ...
   """
   ```

3. **Lazy Manifest Writing**:
   ```python
   # Write manifest rows incrementally (CSV append mode)
   with open('manifest.csv', 'a') as f:
       for case in cases:
           f.write(format_manifest_row(case))
   ```

---

## Version Compatibility

### ECL v2.2 → v2.1 Downgrade

**Header Conversion** (remove RETRIEVAL_ANCHOR):
```python
def downgrade_to_v21(v22_file):
    with open(v22_file, 'r') as f:
        lines = f.readlines()
    
    # Remove RETRIEVAL_ANCHOR line (line 17)
    v21_header = lines[:16] + lines[17:]
    
    # Update version
    v21_header[0] = "ECL_VERSION: 2.1\n"
    
    return ''.join(v21_header)
```

### Micro-Header Compatibility

- **v2.2**: Compact format (YYYYMMDD dates)
- **v2.1**: Standard format (YYYY-MM-DD dates)

**Backward Compatibility**: v2.1 micro-headers can be parsed by v2.2 readers (date format auto-detected).

---

## Best Practices for AI Assistants

### When Generating Code

1. **Always validate ECL format** after modifications
2. **Test with small sample** before full corpus generation
3. **Check micro-header length** constraints (160 chars)
4. **Preserve deterministic behavior** (fixed seed)
5. **Log exceptions** to metrics.json validation_errors

### When Modifying Pipeline

1. **Update pre-flight checks** if adding dependencies
2. **Document config changes** in config.py
3. **Update manifest schema** if adding header fields
4. **Test both EN and FR** language paths
5. **Verify 5-folder layout** remains intact

### When Answering Questions

1. **Reference specific line numbers** when discussing code
2. **Cite ECL format specification** for header questions
3. **Explain boilerplate patterns** when discussing RETRIEVAL_ANCHOR
4. **Clarify non-authoritative status** of anchors and micro-headers
5. **Link to comprehensive guide** for detailed explanations

---

## Quick Reference Commands

```bash
# Generate full corpus (production)
python generate_ecl_v2.py --use-v22 --limit-per-lang 999999 --clean

# Generate test sample
python generate_ecl_v2.py --use-v22 --limit-per-lang 10 --clean

# Filter by year
python generate_ecl_v2.py --use-v22 --year 2025 --limit-per-lang 100

# Check metrics
cat out/ecl-v2/ecl-v2-metrics.json | python -m json.tool

# Validate manifest
python -c "import pandas as pd; df = pd.read_csv('out/ecl-v2/ecl-v2-manifest.csv'); print(df.info())"

# Count files per tribunal
find out/ecl-v2/en/ -type f | cut -d'/' -f4 | sort | uniq -c

# Inspect sample case
head -30 out/ecl-v2/ecl-v2-sample.txt
```

---

## Related Documentation

- **Comprehensive Guide**: `ECL-COMPREHENSIVE-GUIDE.md` (this file's companion)
- **Pipeline README**: `pipeline/README.md`
- **Audit Reports**: `pipeline/AUDIT-REPORT-2026-02-01.md`
- **Implementation Status**: `IMPLEMENTATION_COMPLETE_v2.md`
- **Project README**: `README.md` (high-level overview)

---

## Contact & Support

**Project**: EVA Foundation - Project 16  
**Pipeline Version**: ECL v2.2.0  
**Last Updated**: February 1, 2026  
**Documentation**: `i:\EVA-JP-v1.2\docs\eva-foundation\projects\16-engineered-case-law`
