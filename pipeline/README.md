# Engineered Case Law Pipeline Implementation

## Overview

This directory contains the implementation of the CDC-driven pipeline for ingesting CanLII jurisprudence into EVA Domain Assistant.

## Module Structure

### 1. `canlii_inventory.py` (EPIC 1)
**CanLII Inventory & CDC Foundation**

- Creates snapshots of CanLII case inventory
- Computes CDC diffs (new/changed/unchanged cases)
- Tracks change events for downstream processing

**Key Classes:**
- `CanLIIInventoryManager`: Main orchestrator
- `CaseInventoryRecord`: Represents a case in inventory
- `SnapshotMetadata`: Snapshot tracking

**Database Schema:**
- `snapshots`: Inventory snapshot metadata
- `case_inventory`: Case records per snapshot
- `change_events`: CDC diff results

### 2. `artifact_manager.py` (EPIC 2)
**Artifact Acquisition (PDF + HTML)**

- Downloads PDFs and HTML from CanLII
- Implements content-based deduplication (hash-based)
- Manages local blob storage (simulates Azure Blob)
- Rate-limited fetching to respect CanLII

**Key Classes:**
- `ArtifactManager`: Download and storage orchestrator
- `ArtifactRecord`: Artifact metadata

**Database Schema:**
- `artifacts`: Downloaded artifact tracking with hashes

### 3. `text_extractor.py` (EPIC 3)
**PDF Inspection & OCR Decisioning**

- Attempts PDF text extraction (no OCR first)
- Applies quality gates:
  - Non-empty content
  - Minimum length (100 chars)
  - Readable character distribution (80%+)
  - Multi-page coverage (200 chars/page)
- Triggers Azure Document Intelligence OCR on quality gate failures
- Language detection (EN/FR/BI)

**Key Classes:**
- `TextExtractor`: Extraction orchestrator
- `ExtractionResult`: Extraction metadata and quality metrics

**Database Schema:**
- `extractions`: Extraction attempts with quality scores

## Installation

```powershell
# Navigate to pipeline directory
cd I:\EVA-JP-v1.2\docs\eva-foundation\projects\16-engineered-case-law\pipeline

# Create virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

## Configuration

Create `.env` file with Azure credentials (if using OCR):

```bash
# Azure Document Intelligence (for OCR)
AZURE_DI_ENDPOINT=https://your-di-resource.cognitiveservices.azure.com/
AZURE_DI_KEY=your-key-here

# Azure OpenAI (for embeddings - future)
AZURE_OPENAI_ENDPOINT=https://your-openai.openai.azure.com/
AZURE_OPENAI_KEY=your-key-here
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-ada-002
```

## Usage Examples

### Example 1: Create CanLII Inventory Snapshot

```python
from pathlib import Path
from canlii_inventory import CanLIIInventoryManager, CaseInventoryRecord

# Initialize manager
manager = CanLIIInventoryManager(db_path=Path("data/inventory.db"))

# Create snapshot (manual for now - fetching TBD)
cases = [
    CaseInventoryRecord(
        case_id="2024sst1234",
        url="https://canlii.ca/t/...",
        title="Appellant v. Minister",
        tribunal="sst",
        decision_date="2024-01-15",
        language="en",
        content_hash="abc123"
    )
]

snapshot_id = manager.create_snapshot(cases, scope_id="sst")
print(f"Created: {snapshot_id}")

# Compute CDC diff
diff = manager.compute_diff(snapshot_id, scope_id="sst")
print(f"New: {len(diff['new'])}, Changed: {len(diff['changed'])}")
```

### Example 2: Download Artifacts

```python
from pathlib import Path
from artifact_manager import ArtifactManager

# Initialize manager
manager = ArtifactManager(
    db_path=Path("data/artifacts.db"),
    blob_storage_path=Path("data/blobs")
)

# Fetch PDF
artifact_id = manager.fetch_artifact(
    case_id="2024sst1234",
    url="https://canlii.ca/t/.../download.pdf",
    artifact_type="pdf",
    language="en"
)

# Check stats
stats = manager.get_statistics()
print(f"Total artifacts: {stats['total_artifacts']}")
```

### Example 3: Extract Text with Quality Gates

```python
from pathlib import Path
from text_extractor import TextExtractor

# Initialize extractor
extractor = TextExtractor(
    db_path=Path("data/extractions.db"),
    azure_di_endpoint="...",  # Optional - for OCR
    azure_di_key="..."
)

# Extract text from PDF
pdf_bytes = Path("document.pdf").read_bytes()
result = extractor.extract(
    case_id="2024sst1234",
    artifact_id="abc123",
    pdf_bytes=pdf_bytes
)

print(f"Method: {result.extraction_method}")
print(f"Quality: {result.quality_score:.2f}")
print(f"Language: {result.language}")
print(f"Chars: {result.char_count}")
```

## Next Steps (Future EPICs)

### EPIC 4: Canonical Text Selection
- Choose best text source (PDF vs existing JSON)
- Implement provenance tracking

### EPIC 5: Bilingual Handling
- Deterministic EN/FR splitting
- Explicit bilingual tagging

### EPIC 6: Chunk Engineering
- Deterministic chunking with stable IDs
- Legal metadata enrichment
- Embedding generation

### EPIC 7: EVA DA Ingestion
- Upsert to Azure Cognitive Search
- Metadata-only updates
- Soft-delete withdrawn cases

### EPIC 8: Validation
- Retrieval quality metrics (Precision@K)
- Citation correctness validation

### EPIC 9: Governance
- Coverage and freshness metrics
- Audit trail reporting

## Testing

```powershell
# Unit tests (to be created)
pytest tests/

# Integration test (manual for now)
python -m pipeline.canlii_inventory
python -m pipeline.artifact_manager
python -m pipeline.text_extractor
```

## Database Location

All SQLite databases stored in `data/`:
- `data/inventory.db` - CanLII inventory snapshots
- `data/artifacts.db` - Downloaded artifacts
- `data/extractions.db` - Text extractions
- `data/blobs/` - Binary artifact storage

## Notes

1. **CanLII Fetching**: Currently placeholder - needs decision on API vs sitemap/scraping approach
2. **OCR**: Requires Azure Document Intelligence credentials - gracefully degrades without
3. **Rate Limiting**: Default 1-second delay between CanLII requests - adjust as needed
4. **Storage**: Using local filesystem to simulate Azure Blob - can be swapped with `azure-storage-blob` SDK

## Implementation Status

**Completed:**
- [DONE] EPIC 1: CDC Foundation - **IMPLEMENTED**
- [DONE] EPIC 2: Artifact Acquisition - **IMPLEMENTED**
- [DONE] EPIC 3: Text Extraction - **IMPLEMENTED**

**Pending:**
- [PENDING] EPIC 4-9: Awaiting implementation
