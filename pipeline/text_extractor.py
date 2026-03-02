"""
================================================================================
MODULE: text_extractor.py
VERSION: 1.0.0 (PLANNED - Not Used in PoC)
DATE: 2026-02-01 12:00:00
AUTHOR: EVA Foundation - Project 16
================================================================================

STATUS: ⏳ PLANNED - NOT USED IN POC PHASE 1

PURPOSE:
Text extraction from PDF and HTML artifacts with quality gates and selective
OCR. Implements smart extraction strategy with fallback mechanisms.

PIPELINE ROLE:
┌──────────────────────────────────────────────────────────────────────┐
│ TEXT EXTRACTOR (PDF/HTML Processing) - FUTURE USE                   │
│                                                                      │
│ [text_extractor.py] ◄── YOU ARE HERE (NOT ACTIVE)                  │
│    ├► Planned for: If Phase 3 selects PDF/HTML source             │
│    ├► Extracts: Text from PDFs (PyPDF2 or OCR)                    │
│    ├► Quality Gates: Length, char distribution, page coverage     │
│    └► Fallback: OCR via Azure Document Intelligence if needed     │
└──────────────────────────────────────────────────────────────────────┘

KEY FEATURES (PLANNED):
1. Multi-Strategy Extraction
   - Primary: PyPDF2 text extraction (fast, free)
   - Secondary: Azure Document Intelligence OCR (accurate, cost)
   - Tertiary: HTML parsing (if available)
   
2. Quality Gates
   - Min text length check (1000+ chars)
   - Character distribution (max 80% non-alphanumeric)
   - Page coverage (text on >50% of pages)
   - Language detection (EN/FR validation)
   
3. OCR Decisioning
   - Auto-detect image-only PDFs (no extractable text)
   - Trigger OCR selectively (cost optimization)
   - Track OCR usage metrics
   
4. Extraction Metadata
   - extraction_method: 'pdf_text', 'ocr', 'html'
   - quality_score: 0.0 to 1.0 (composite quality metric)
   - quality_flags: Dict of pass/fail per gate
   - page_count, char_count: Basic statistics

DATA STRUCTURES:
- ExtractionResult: Dataclass with text, metadata, quality metrics
- QualityGates: Configuration for thresholds

KEY FUNCTIONS (PLANNED):
- extract_text_from_pdf()     - Primary extraction logic
- apply_quality_gates()       - Validate extraction quality
- extract_via_ocr()           - Azure DI OCR fallback
- extract_from_html()         - HTML parsing
- compute_quality_score()     - Composite quality metric

POC STRATEGY:
**Phase 1 (Current)**: NOT USED - Using SQLite JSON content
**Phase 2**: Backend ingestion testing
**Phase 3**: Source quality analysis (compare JSON vs PDF vs HTML)
**Phase 4**: Activate this module IF PDF/HTML selected as canonical
**Phase 5**: CDC integration with extraction

WHY DEFERRED:
- PoC uses SQLite JSON content (pre-extracted)
- Phase 3 will determine if PDF extraction needed
- JSON quality may be sufficient (avoids extraction complexity)
- OCR costs avoided during PoC

FUTURE ACTIVATION:
IF Phase 3 determines PDF/HTML extraction needed:
1. Install dependencies: PyPDF2, azure-ai-documentintelligence
2. Configure Azure DI credentials (for OCR)
3. Implement quality gate configuration
4. Add extracted_text table to database
5. Integrate with db_loader.py to use extracted text

QUALITY GATES (PLANNED):
1. Min length: 1000 characters
2. Max non-alphanumeric ratio: 80%
3. Min page coverage: 50%
4. Language match: Detected language = expected language
5. No null bytes or encoding errors
6. Max repeated char ratio: 20%

INPUTS (PLANNED):
- artifact_path: Path to PDF or HTML file
- case_id: Case identifier
- expected_language: 'en' or 'fr'
- ocr_enabled: Bool to allow OCR fallback

OUTPUTS (PLANNED):
- ExtractionResult: Text + metadata + quality scores
- Extraction logs: Method used, quality gates, timing
- OCR usage metrics: Count, cost estimate

DEPENDENCIES:
- PyPDF2: PDF text extraction (optional)
- azure-ai-documentintelligence: OCR (optional)
- BeautifulSoup4: HTML parsing (optional)
- sqlite3: Metadata persistence

EPIC MAPPING:
- EPIC 3: PDF Inspection & OCR Decisioning
- EPIC 4: Canonical Text Schema (text quality for ECL)
- EPIC 9: Governance (Quality metrics, cost tracking)

CHANGELOG:
- v1.0.0 (2026-01-19): Initial module structure (not activated)
================================================================================
"""

import io
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict
import sqlite3
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False
    logger.warning("PyPDF2 not installed. PDF text extraction disabled.")

try:
    from azure.ai.documentintelligence import DocumentIntelligenceClient
    from azure.core.credentials import AzureKeyCredential
    AZURE_DI_AVAILABLE = True
except ImportError:
    AZURE_DI_AVAILABLE = False
    logger.warning("Azure Document Intelligence SDK not installed. OCR disabled.")


@dataclass
class ExtractionResult:
    """Result of text extraction attempt"""
    case_id: str
    artifact_id: str
    extraction_method: str  # 'pdf_text', 'ocr', 'html'
    text_content: str
    language: str  # 'en', 'fr', 'bi'
    quality_score: float  # 0.0 to 1.0
    page_count: int
    char_count: int
    quality_flags: Dict[str, bool]  # Pass/fail for quality gates
    extraction_timestamp: str
    
    def __post_init__(self):
        if self.extraction_timestamp is None:
            self.extraction_timestamp = datetime.utcnow().isoformat()


class TextExtractor:
    """Handles PDF text extraction with quality gates and OCR fallback"""
    
    def __init__(
        self,
        db_path: Path,
        azure_di_endpoint: Optional[str] = None,
        azure_di_key: Optional[str] = None
    ):
        """
        Initialize text extractor
        
        Args:
            db_path: Path to SQLite database
            azure_di_endpoint: Azure Document Intelligence endpoint (for OCR)
            azure_di_key: Azure Document Intelligence API key
        """
        self.db_path = Path(db_path)
        self.azure_di_endpoint = azure_di_endpoint
        self.azure_di_key = azure_di_key
        self._init_database()
        
        if azure_di_endpoint and azure_di_key and AZURE_DI_AVAILABLE:
            self.di_client = DocumentIntelligenceClient(
                endpoint=azure_di_endpoint,
                credential=AzureKeyCredential(azure_di_key)
            )
        else:
            self.di_client = None
    
    def _init_database(self):
        """Initialize extraction tracking database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS extractions (
                extraction_id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id TEXT NOT NULL,
                artifact_id TEXT NOT NULL,
                extraction_method TEXT NOT NULL,
                language TEXT NOT NULL,
                quality_score REAL NOT NULL,
                page_count INTEGER NOT NULL,
                char_count INTEGER NOT NULL,
                quality_flags TEXT NOT NULL,
                extraction_timestamp TEXT NOT NULL,
                text_blob_path TEXT NOT NULL
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_extraction_case ON extractions(case_id)
        """)
        
        conn.commit()
        conn.close()
    
    def extract_pdf_text(self, pdf_bytes: bytes) -> Optional[str]:
        """
        Extract embedded text from PDF (no OCR)
        
        Returns:
            Extracted text or None if extraction fails
        """
        if not PYPDF2_AVAILABLE:
            return None
        
        try:
            pdf_file = io.BytesIO(pdf_bytes)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            text_parts = []
            for page in pdf_reader.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)
            
            return "\n\n".join(text_parts) if text_parts else None
            
        except Exception as e:
            logger.error(f"PDF text extraction failed: {e}")
            return None
    
    def apply_quality_gates(self, text: str, page_count: int) -> Dict[str, bool]:
        """
        Apply quality gates to extracted text
        
        Returns:
            Dict of gate_name -> passed (bool)
        """
        gates = {}
        
        # Gate 1: Non-empty content
        gates["non_empty"] = bool(text and text.strip())
        
        # Gate 2: Reasonable length (at least 100 chars)
        gates["min_length"] = len(text) >= 100
        
        # Gate 3: Readable character distribution
        # Check that at least 80% are printable ASCII or common Unicode
        if text:
            printable_count = sum(1 for c in text if c.isprintable() or c.isspace())
            gates["readable_chars"] = (printable_count / len(text)) >= 0.8
        else:
            gates["readable_chars"] = False
        
        # Gate 4: Coverage beyond first page
        # Heuristic: at least 200 chars per page on average
        gates["multi_page_coverage"] = (len(text) / max(page_count, 1)) >= 200
        
        return gates
    
    def detect_language(self, text: str) -> str:
        """
        Detect language of text
        
        Returns:
            'en', 'fr', or 'bi' (bilingual)
        
        Note: Simple heuristic - can be improved with langdetect or Azure Text Analytics
        """
        if not text:
            return "en"  # default
        
        # Count French-specific words/patterns
        french_indicators = ['le ', 'la ', 'les ', 'une ', 'des ', 'dans ', 'avec ']
        english_indicators = ['the ', 'and ', 'of ', 'to ', 'in ', 'for ']
        
        text_lower = text.lower()
        french_count = sum(text_lower.count(word) for word in french_indicators)
        english_count = sum(text_lower.count(word) for word in english_indicators)
        
        # Simple threshold-based detection
        if french_count > english_count * 2:
            return "fr"
        elif english_count > french_count * 2:
            return "en"
        else:
            return "bi"  # Bilingual or ambiguous
    
    def ocr_pdf(self, pdf_bytes: bytes, case_id: str) -> Optional[str]:
        """
        Perform OCR on PDF using Azure Document Intelligence
        
        Args:
            pdf_bytes: PDF file bytes
            case_id: Case identifier (for logging)
        
        Returns:
            OCR-extracted text or None
        """
        if not self.di_client:
            logger.error(f"OCR not available for {case_id}")
            return None
        
        try:
            # Submit PDF for OCR
            poller = self.di_client.begin_analyze_document(
                model_id="prebuilt-read",
                analyze_request=pdf_bytes,
                content_type="application/pdf"
            )
            
            result = poller.result()
            
            # Extract text from all pages
            text_parts = []
            for page in result.pages:
                page_text = " ".join([line.content for line in page.lines])
                text_parts.append(page_text)
            
            return "\n\n".join(text_parts)
            
        except Exception as e:
            logger.error(f"OCR failed for {case_id}: {e}")
            return None
    
    def extract(
        self,
        case_id: str,
        artifact_id: str,
        pdf_bytes: bytes,
        page_count: Optional[int] = None
    ) -> ExtractionResult:
        """
        Extract text from PDF with quality gates and OCR fallback
        
        Returns:
            ExtractionResult with extraction metadata
        """
        # Attempt PDF text extraction first
        text = self.extract_pdf_text(pdf_bytes)
        extraction_method = "pdf_text"
        
        # Estimate page count if not provided
        if page_count is None and PYPDF2_AVAILABLE:
            try:
                pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
                page_count = len(pdf_reader.pages)
            except:
                page_count = 1
        
        # Apply quality gates
        quality_flags = self.apply_quality_gates(text or "", page_count or 1)
        gates_passed = all(quality_flags.values())
        
        # Fallback to OCR if quality gates fail
        if not gates_passed and self.di_client:
            logger.info(f"[OCR] Quality gates failed for {case_id}, attempting OCR...")
            ocr_text = self.ocr_pdf(pdf_bytes, case_id)
            if ocr_text:
                text = ocr_text
                extraction_method = "ocr"
                # Re-evaluate quality gates
                quality_flags = self.apply_quality_gates(text, page_count or 1)
        
        # Detect language
        language = self.detect_language(text or "")
        
        # Compute quality score
        quality_score = sum(quality_flags.values()) / len(quality_flags)
        
        result = ExtractionResult(
            case_id=case_id,
            artifact_id=artifact_id,
            extraction_method=extraction_method,
            text_content=text or "",
            language=language,
            quality_score=quality_score,
            page_count=page_count or 1,
            char_count=len(text or ""),
            quality_flags=quality_flags,
            extraction_timestamp=datetime.utcnow().isoformat()
        )
        
        # Store extraction result
        self._save_extraction(result)
        
        return result
    
    def _save_extraction(self, result: ExtractionResult):
        """Save extraction result to database"""
        import json
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Save text to separate blob
        text_blob_path = Path(self.db_path).parent / "text_blobs" / f"{result.artifact_id}.txt"
        text_blob_path.parent.mkdir(parents=True, exist_ok=True)
        text_blob_path.write_text(result.text_content, encoding='utf-8')
        
        cursor.execute("""
            INSERT INTO extractions 
            (case_id, artifact_id, extraction_method, language, quality_score,
             page_count, char_count, quality_flags, extraction_timestamp, text_blob_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            result.case_id, result.artifact_id, result.extraction_method,
            result.language, result.quality_score, result.page_count,
            result.char_count, json.dumps(result.quality_flags),
            result.extraction_timestamp, str(text_blob_path)
        ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"[SAVED] Extraction for {result.case_id}: "
                   f"{result.extraction_method}, quality={result.quality_score:.2f}")


# Example usage
if __name__ == "__main__":
    extractor = TextExtractor(db_path=Path("extractions.db"))
    
    # Example: Extract from PDF
    # pdf_path = Path("sample.pdf")
    # pdf_bytes = pdf_path.read_bytes()
    # result = extractor.extract(
    #     case_id="2024sst123",
    #     artifact_id="abc123",
    #     pdf_bytes=pdf_bytes
    # )
    # logger.info(f"Extracted: {result.char_count} chars, method={result.extraction_method}")
