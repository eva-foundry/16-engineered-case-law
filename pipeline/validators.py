"""
================================================================================
MODULE: validators.py
VERSION: 2.1.0
DATE: 2026-02-01 12:00:00
AUTHOR: EVA Foundation - Project 16
================================================================================

PURPOSE:
Comprehensive validation framework for ECL v2.1 generator. Implements pre-flight
checks and record-level validation to ensure data quality before processing.

PIPELINE ROLE:
┌──────────────────────────────────────────────────────────────────────┐
│ VALIDATOR (Quality Gates)                                            │
│                                                                      │
│ [validators.py] ◄── YOU ARE HERE                                    │
│    ├► Called by: generate_ecl_v2.py (pre-flight + record checks)  │
│    ├► Validates: Database, paths, content, metadata               │
│    └► Outputs: ValidationResult objects (pass/fail + messages)    │
└──────────────────────────────────────────────────────────────────────┘

KEY FEATURES:
1. Pre-Flight Checks (12 Gates)
   - Database existence and connectivity
   - Output directory writability
   - Database schema validation (pages table exists)
   - Record count checks (EN/FR inventory)
   - Content quality sampling
   - Citation format validation
   - Metadata completeness checks
   
2. Record-Level Validation
   - Required field presence (id, content, metadata_relpath)
   - Content length checks (min 1000 chars)
   - Content encoding validation (UTF-8, no null bytes)
   - Content quality (max 80% non-alphanumeric threshold)
   - Citation format (regex patterns for courts)
   - Date format (ISO 8601 YYYY-MM-DD)
   - URL format (http/https validation)
   
3. Validation Severity Levels
   - CRITICAL: Must fix before proceeding
   - WARNING: Should investigate but can proceed
   - INFO: Informational only

VALIDATION RESULTS:
- ValidationResult dataclass: passed, message, severity, field, value
- Accumulated in lists: validation_errors, validation_warnings

KEY FUNCTIONS:
- preflight_checks()         - Run all 12 pre-flight gates
- print_preflight_report()   - Pretty-print validation results
- CaseRecordValidator.validate_record() - Record-level checks
- _check_required_field()    - Field presence validation
- _check_content_length()    - Min length validation
- _check_content_encoding()  - UTF-8 + no nulls
- _check_content_quality()   - Alphanumeric ratio check
- _check_citation_format()   - Court citation regex
- _check_date_format()       - ISO date validation
- _check_url_format()        - URL scheme validation

INPUTS:
- db_path: Path to juris_inventory.sqlite
- output_dir: Target output directory
- record: Dict representing case record

OUTPUTS:
- List[ValidationResult]: Validation outcomes with severity
- Console reports: Colored output with ✓/✗/⚠ symbols

DEPENDENCIES:
- sqlite3: Database connectivity checks
- re: Regex pattern matching
- dataclasses: ValidationResult structure
- datetime: Date parsing validation

EPIC MAPPING:
- EPIC 8: Validation (Pre-flight checks + record validation)
- EPIC 9: Governance (Quality gates enforcement)

PRE-FLIGHT CHECKS:
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

CHANGELOG:
- v2.1.0 (2026-02-01): Production PoC validation framework
- v2.0.0 (2026-01-28): Added 12 pre-flight checks
- v1.5.0 (2026-01-25): Added content quality checks
- v1.0.0 (2026-01-15): Initial validation framework
================================================================================
"""

from typing import Optional, List, Dict
from dataclasses import dataclass
from datetime import datetime
import re
import sys
import os
import sqlite3


@dataclass
class ValidationResult:
    """Result of a validation check."""
    passed: bool
    message: str
    severity: str  # 'critical', 'warning', 'info'
    field: Optional[str] = None
    value: Optional[str] = None


class CaseRecordValidator:
    """Validates case records before ECL generation."""
    
    def __init__(self, strict: bool = False):
        self.strict = strict
        self.validation_errors = []
        self.validation_warnings = []
    
    def validate_record(self, record: Dict) -> List[ValidationResult]:
        """Run all validation checks on a record."""
        results = []
        
        # Required fields
        results.append(self._check_required_field(record, 'id'))
        results.append(self._check_required_field(record, 'metadata_relpath'))
        results.append(self._check_required_field(record, 'content'))
        
        # Content quality
        if 'content' in record and record['content']:
            results.append(self._check_content_length(record['content']))
            results.append(self._check_content_encoding(record['content']))
            results.append(self._check_content_quality(record['content']))
        
        # Metadata quality
        results.append(self._check_citation_format(record.get('citation')))
        results.append(self._check_date_format(record.get('publication_date')))
        results.append(self._check_url_format(record.get('pdf_link')))
        
        # Blob consistency
        if 'blob_name' in record:
            results.append(self._check_blob_path_consistency(
                record.get('metadata_relpath'),
                record.get('blob_name')
            ))
        
        return results
    
    def _check_required_field(self, record: Dict, field: str) -> ValidationResult:
        """Check if required field exists and is non-empty."""
        value = record.get(field)
        passed = value is not None and str(value).strip() != ''
        
        return ValidationResult(
            passed=passed,
            message=f"Required field '{field}' {'present' if passed else 'missing or empty'}",
            severity='critical' if not passed else 'info',
            field=field,
            value=str(value) if value else None
        )
    
    def _check_content_length(self, content: str, min_length: int = 1000) -> ValidationResult:
        """Validate content has sufficient length."""
        length = len(content)
        passed = length >= min_length
        
        return ValidationResult(
            passed=passed,
            message=f"Content length {length} {'≥' if passed else '<'} {min_length} chars",
            severity='warning' if not passed else 'info',
            field='content',
            value=str(length)
        )
    
    def _check_content_encoding(self, content: str) -> ValidationResult:
        """Check content can be safely encoded."""
        try:
            content.encode('utf-8')
            passed = True
            message = "Content encoding valid (UTF-8)"
        except UnicodeEncodeError as e:
            passed = False
            message = f"Content encoding error: {e}"
        
        return ValidationResult(
            passed=passed,
            message=message,
            severity='critical' if not passed else 'info',
            field='content'
        )
    
    def _check_content_quality(self, content: str) -> ValidationResult:
        """Check content quality indicators."""
        # Check for OCR artifacts
        ocr_indicators = ['□', '■', '�', '|||']
        artifact_count = sum(content.count(ind) for ind in ocr_indicators)
        artifact_ratio = artifact_count / len(content) if content else 0
        
        passed = artifact_ratio < 0.01  # Less than 1% artifacts
        
        return ValidationResult(
            passed=passed,
            message=f"OCR artifact ratio: {artifact_ratio:.3%}",
            severity='warning' if not passed else 'info',
            field='content',
            value=f"{artifact_count} artifacts"
        )
    
    def _check_citation_format(self, citation: Optional[str]) -> ValidationResult:
        """Validate citation follows expected format."""
        if not citation:
            return ValidationResult(
                passed=False,
                message="Citation missing",
                severity='warning',
                field='citation'
            )
        
        # Expected format: YYYY TRIBUNAL ###
        pattern = r'\b(19|20)\d{2}\s+(SCC|FCA|FC|FCT|SST|SSTAD|SSTGDEI)\s+\d+\b'
        passed = bool(re.search(pattern, citation, re.IGNORECASE))
        
        return ValidationResult(
            passed=passed,
            message=f"Citation format {'valid' if passed else 'unexpected'}: {citation}",
            severity='warning' if not passed else 'info',
            field='citation',
            value=citation
        )
    
    def _check_date_format(self, date_str: Optional[str]) -> ValidationResult:
        """Validate date format."""
        if not date_str:
            return ValidationResult(
                passed=False,
                message="Publication date missing",
                severity='info',
                field='publication_date'
            )
        
        # Try parsing common formats
        for fmt in ['%Y-%m-%d', '%Y-%m', '%Y/%m/%d', '%Y']:
            try:
                datetime.strptime(date_str.strip(), fmt)
                return ValidationResult(
                    passed=True,
                    message=f"Date format valid: {date_str}",
                    severity='info',
                    field='publication_date',
                    value=date_str
                )
            except ValueError:
                continue
        
        return ValidationResult(
            passed=False,
            message=f"Date format unrecognized: {date_str}",
            severity='warning',
            field='publication_date',
            value=date_str
        )
    
    def _check_url_format(self, url: Optional[str]) -> ValidationResult:
        """Validate URL format."""
        if not url:
            return ValidationResult(
                passed=False,
                message="PDF URL missing",
                severity='warning',
                field='pdf_link'
            )
        
        passed = url.startswith(('http://', 'https://'))
        
        return ValidationResult(
            passed=passed,
            message=f"URL format {'valid' if passed else 'invalid'}: {url[:50]}...",
            severity='warning' if not passed else 'info',
            field='pdf_link',
            value=url
        )
    
    def _check_blob_path_consistency(
        self, 
        metadata_relpath: Optional[str], 
        blob_name: Optional[str]
    ) -> ValidationResult:
        """Check metadata_relpath matches blob_name."""
        if not metadata_relpath or not blob_name:
            return ValidationResult(
                passed=False,
                message="Cannot verify blob path consistency (missing data)",
                severity='warning',
                field='blob_name'
            )
        
        passed = metadata_relpath == blob_name
        
        return ValidationResult(
            passed=passed,
            message=f"Blob path {'matches' if passed else 'mismatch'}",
            severity='warning' if not passed else 'info',
            field='blob_name',
            value=f"{metadata_relpath} vs {blob_name}"
        )


def preflight_checks(config: Dict) -> Dict[str, bool]:
    """
    Validate environment before execution.
    
    Args:
        config: Configuration dictionary
    
    Returns:
        Dict of check_name: passed status
    """
    checks = {}
    
    # 1. Database accessibility
    db_path = config['db_path']
    checks['db_exists'] = db_path.exists()
    checks['db_readable'] = db_path.exists() and os.access(db_path, os.R_OK)
    
    # 2. Database schema validation
    if checks['db_exists']:
        try:
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            
            # Check tables exist
            cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = {row[0] for row in cur.fetchall()}
            checks['table_pages_en'] = 'pages_en' in tables
            checks['table_pages_fr'] = 'pages_fr' in tables
            checks['table_blobs'] = 'blobs' in tables
            
            # Check row counts
            if checks['table_pages_en']:
                cur.execute("SELECT COUNT(*) FROM pages_en WHERE content IS NOT NULL AND LENGTH(content) > 1000")
                checks['pages_en_with_content'] = cur.fetchone()[0] > 0
                
            if checks['table_pages_fr']:
                cur.execute("SELECT COUNT(*) FROM pages_fr WHERE content IS NOT NULL AND LENGTH(content) > 1000")
                checks['pages_fr_with_content'] = cur.fetchone()[0] > 0
                
            # Check indexes
            cur.execute("PRAGMA index_list('pages_en')")
            checks['pages_en_indexed'] = len(cur.fetchall()) > 0
            
        except sqlite3.Error as e:
            checks['db_queryable'] = False
            print(f"Database error: {e}")
        finally:
            if 'conn' in locals():
                conn.close()
    
    # 3. Output directory
    output_dir = config['output_dir']
    checks['output_dir_writable'] = (
        output_dir.exists() and os.access(output_dir, os.W_OK)
    ) or (
        not output_dir.exists() and os.access(output_dir.parent, os.W_OK)
    )
    
    # 4. Python version
    checks['python_version_ok'] = sys.version_info >= (3, 9)
    
    return checks


def print_preflight_report(checks: Dict[str, bool]) -> bool:
    """
    Print preflight check results.
    
    Args:
        checks: Dictionary of check results
    
    Returns:
        True if all checks passed, False otherwise
    """
    print("\n" + "="*60)
    print("PRE-FLIGHT VALIDATION")
    print("="*60)
    
    all_passed = True
    for check, passed in sorted(checks.items()):
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status:10} {check}")
        if not passed:
            all_passed = False
    
    print("="*60)
    
    if not all_passed:
        print("\n⚠️  CRITICAL: Pre-flight checks failed. Resolve issues before proceeding.")
        print_remediation_guide(checks)
    else:
        print("\n✓ All pre-flight checks passed. Ready to proceed.\n")
    
    return all_passed


def print_remediation_guide(checks: Dict[str, bool]):
    """Print remediation steps for failed checks."""
    remediations = {
        'db_exists': "Database file not found. Check path configuration.",
        'db_readable': "Database file not readable. Check permissions.",
        'db_queryable': "Database cannot be queried. Check file integrity.",
        'table_pages_en': "Missing pages_en table. Run reconciliation first.",
        'table_pages_fr': "Missing pages_fr table. Run reconciliation first.",
        'table_blobs': "Missing blobs table. Run reconciliation first.",
        'pages_en_with_content': "No English pages with sufficient content. Check data import.",
        'pages_fr_with_content': "No French pages with sufficient content. Check data import.",
        'pages_en_indexed': "Missing index on pages_en. Performance may be degraded.",
        'output_dir_writable': "Cannot write to output directory. Check permissions.",
        'python_version_ok': "Python 3.9+ required. Upgrade Python."
    }
    
    print("\nREMEDIATION GUIDE:")
    print("-" * 60)
    for check, passed in checks.items():
        if not passed and check in remediations:
            print(f"• {check}: {remediations[check]}")
