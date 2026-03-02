# ECL v2 Generator

Generate Engineered Case Law (ECL) v2 documents from `juris_inventory.sqlite` for ingestion into Azure AI Search RAG pipelines.

## Quick Start

```bash
# Generate 50 EN + 50 FR cases (default)
python generate_ecl_v2.py

# Preview without writing files
python generate_ecl_v2.py --dry-run --limit-per-lang 3

# Generate only English cases
python generate_ecl_v2.py --language en --limit-per-lang 50

# Custom database and output paths
python generate_ecl_v2.py \
  --db "../../05-Extract-Cases/data/SPO-Data-Analysis/juris_inventory.sqlite" \
  --out "../out/ecl-v2" \
  --limit-per-lang 50
```

## Output Structure

```
out/ecl-v2/
├── en/
│   ├── scc/
│   │   └── scc_2001-SCC-89_1931_en.ecl.txt
│   ├── fca/
│   ├── fc/
│   └── sst/
├── fr/
│   ├── scc/
│   ├── fca/
│   ├── fc/
│   └── sst/
├── ecl-v2-manifest.csv
├── ecl-v2-metrics.json
├── ecl-v2-sample.txt
└── ecl-v2-generation.log
```

## ECL v2 Format

Each file contains:
- 10 lines of compact metadata header (ASCII)
- 1 blank line
- Full case text (UTF-8, unmodified)

Example:
```
DOC_CLASS: ECL
FILE_STEM: scc_2001-SCC-89_1931_en
LANG: EN
TRIBUNAL: SCC
TRIBUNAL_RANK: 1
DECISION_DATE: 2001-11-29
CITATION: 2001 SCC 89
PDF_URI: https://sabdmeiajpdatadev.blob.core.windows.net/...
SOURCE_NAME: scc
CONTENT_LENGTH: 45890

[Full case text follows...]
```

## Configuration

Environment variables (optional):
```bash
export ECL_DB_PATH="path/to/juris_inventory.sqlite"
export ECL_OUTPUT_DIR="path/to/output"
export ECL_CASES_PER_LANG=50
export ECL_MIN_CONTENT=1000
export ECL_SEED="custom-seed"
export ECL_STRICT=true
export LOG_LEVEL=DEBUG
```

## Command-Line Options

```
--db PATH                 Database path (default: auto-detect)
--out PATH                Output directory (default: ../out/ecl-v2)
--limit-per-lang N        Cases per language (default: 50)
--min-content-length N    Minimum content length (default: 1000)
--seed STRING             Random seed for reproducibility
--language {en,fr,both}   Generate specific language (default: both)
--dry-run                 Preview without writing files
--strict                  Enable strict validation
--verbose                 Enable verbose logging
```

## Pre-Flight Checks

The script validates:
- ✓ Database exists and is readable
- ✓ Required tables present (pages_en, pages_fr, blobs)
- ✓ Sufficient cases with content
- ✓ Output directory writable
- ✓ Python 3.9+ installed

## Validation

Strict mode (`--strict`) validates:
- Required fields present
- Content length >= minimum
- UTF-8 encoding valid
- Citation format correct
- Date format parseable
- URL format valid
- Blob path consistency

## Output Files

### ecl-v2-manifest.csv
CSV with columns:
- file_stem, language, tribunal, tribunal_rank
- decision_date, citation, pdf_uri
- blob_name, content_length, output_path

### ecl-v2-metrics.json
JSON with:
- Total cases, language distribution
- Tribunal distribution
- Content statistics (min/max/avg length)
- Database statistics
- Generation configuration

### ecl-v2-sample.txt
One complete ECL file for validation

### ecl-v2-generation.log
Detailed execution log

## Tribunal Precedence

Cases are stratified by tribunal with precedence ranks:
- SCC (Supreme Court): Rank 1
- FCA (Federal Court of Appeal): Rank 2
- FC (Federal Court): Rank 3
- SST (Social Security Tribunal): Rank 4

## Reproducibility

Use `--seed` for deterministic results:
```bash
python generate_ecl_v2.py --seed "eva-ecl-v2-fixed" --limit-per-lang 50
```

Same seed + same database = identical output files.

## Architecture

```
generate_ecl_v2.py    # Main CLI script
├── config.py         # Configuration management
├── logger.py         # Structured logging
├── validators.py     # Pre-flight & data validation
├── db_loader.py      # SQLite queries
└── ecl_formatter.py  # ECL v2 formatting
```

## Error Handling

Script exits with:
- Code 0: Success
- Code 1: Configuration invalid, pre-flight failed, or validation error (strict mode)

All errors logged to console and file.

## Best Practices

1. **Test first**: Use `--dry-run` to preview
2. **Check logs**: Review `ecl-v2-generation.log` for issues
3. **Validate output**: Inspect `ecl-v2-sample.txt`
4. **Verify manifest**: Check `ecl-v2-manifest.csv` for completeness
5. **Use same seed**: Ensure reproducibility across runs

## Dependencies

- Python 3.9+
- Standard library only (no pip installs required)

## Integration

Generated ECL files are ready for:
- Azure AI Search ingestion
- Chunking analysis (use with chunking probe)
- RAG pipeline testing
- Semantic search indexing

## Support

For issues or questions, see:
- [ACCEPTANCE.md](../ACCEPTANCE.md)
- [engineered-case-law-tasks.md](../engineered-case-law-tasks.md)
- [README.md](../README.md)
