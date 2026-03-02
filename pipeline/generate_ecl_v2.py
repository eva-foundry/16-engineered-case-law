#!/usr/bin/env python3
"""
================================================================================
SCRIPT: generate_ecl_v2.py
VERSION: 2.2.0
DATE: 2026-02-01 19:00:00
AUTHOR: EVA Foundation - Project 16
================================================================================

PURPOSE:
Main orchestration script for ECL v2.1 generation. Coordinates all pipeline
steps from database query through ECL file generation, validation, and metrics.

PIPELINE ROLE:
┌──────────────────────────────────────────────────────────────────────┐
│ ORCHESTRATOR (Entry Point)                                          │
│                                                                      │
│ [generate_ecl_v2.py] ◄── YOU ARE HERE                              │
│    ├► config.py           (Load configuration)                     │
│    ├► logger.py           (Setup logging)                          │
│    ├► validators.py       (Pre-flight checks)                      │
│    ├► db_loader.py        (Query SQLite, load cases)              │
│    ├► ecl_formatter.py    (Format ECL v2.1, inject micro-headers)  │
│    └► Output              (Write .ecl.txt files + metrics)         │
└──────────────────────────────────────────────────────────────────────┘

INPUTS:
- juris_inventory.sqlite (102,678 EN + 117,174 FR pages)
- Command-line arguments (language, limit, dry-run, clean)
- Environment variables (ECL_DB_PATH, ECL_OUTPUT_DIR, etc.)

OUTPUTS:
- ECL v2.1 files: out/ecl-v2/*.ecl.txt (419 cases in PoC)
- Manifest: ecl-v2-manifest.csv (metadata index)
- Metrics: ecl-v2-metrics.json (statistics)
- Sample: ecl-v2-sample.txt (first 3 cases preview)
- Logs: Generate timestamp-based log file

KEY FUNCTIONS:
- clean_output_directory()  - Remove existing ECL files safely
- write_ecl_files()         - Write formatted ECL documents
- write_manifest()          - Create CSV index of cases
- write_metrics()           - Generate JSON statistics
- write_sample()            - Create preview sample file
- main()                    - Command-line interface

DEPENDENCIES:
- config.py        (Configuration management)
- logger.py        (Structured logging)
- validators.py    (Pre-flight validation)
- db_loader.py     (Database queries)
- ecl_formatter.py (ECL v2.1 formatting)

EPIC MAPPING:
- EPIC 4: Canonical Text Schema (ECL v2.1 format implementation)
- EPIC 6: Chunk Engineering (Micro-header injection)
- EPIC 8: Validation (Pre-flight checks + record validation)
- EPIC 9: Governance (Logging, metrics, manifest)

USAGE:
    python generate_ecl_v2.py --limit-per-lang 50
    python generate_ecl_v2.py --dry-run --limit-per-lang 3
    python generate_ecl_v2.py --language en --limit-per-lang 50
    python generate_ecl_v2.py --clean  # Remove existing files first

CHANGELOG:
- v2.1.0 (2026-02-01): Production PoC version with micro-headers
- v2.0.0 (2026-01-28): ECL v2.1 format upgrade (16→17 header fields)
- v1.0.0 (2026-01-15): Initial ECL v2.0 implementation
================================================================================
"""

import argparse
import csv
import json
import re
import sys
import os
import sqlite3
from pathlib import Path
from typing import List, Dict
from datetime import datetime

# Import both v2.1 and v2.2 formatters
from ecl_formatter import format_ecl_v2, format_ecl_v22

# Local imports
from config import CONFIG, validate_config, print_config
from logger import setup_logger, LogContext
from validators import (
    preflight_checks, 
    print_preflight_report,
    CaseRecordValidator
)
from db_loader import (
    load_cases_from_db,
    load_cases_stratified,
    get_database_stats,
    CaseRecord,
    extract_case_id,
    normalize_date_for_filename,
    sanitize_for_filename
)
from ecl_formatter import format_ecl_v2, format_ecl_v22, get_sample_preview
import shutil


def clean_output_directory(output_dir: Path, logger) -> Dict[str, int]:
    """
    Clean output directory by removing ALL generated content.
    
    Complete cleanup strategy:
    - Removes entire en/ and fr/ directory trees (all files and subdirs)
    - Removes manifest, metrics, and sample files
    - Ensures clean slate to prevent mixed old/new data on crash recovery
    
    Safety features:
    - Only removes known output patterns
    - Preserves other files (logs, docs, etc.)
    - Returns statistics for logging
    
    Args:
        output_dir: Output directory path
        logger: Logger instance
    
    Returns:
        Dictionary with cleanup statistics
    """
    stats = {
        'files_removed': 0,
        'dirs_removed': 0,
        'bytes_freed': 0
    }
    
    if not output_dir.exists():
        logger.info("Output directory does not exist, nothing to clean")
        return stats
    
    logger.info(f"Scanning output directory: {output_dir}")
    
    # Remove language directories (en/, fr/) completely to avoid mixed old/new files
    for lang_dir in output_dir.iterdir():
        if lang_dir.is_dir() and lang_dir.name in ('en', 'fr'):
            try:
                # Count files before removal
                all_files = list(lang_dir.glob('**/*'))
                file_count = sum(1 for f in all_files if f.is_file())
                total_size = sum(f.stat().st_size for f in all_files if f.is_file())
                
                # Remove entire tree
                shutil.rmtree(lang_dir)
                
                stats['files_removed'] += file_count
                stats['dirs_removed'] += 1
                stats['bytes_freed'] += total_size
                logger.info(f"Removed {lang_dir.name}/ directory: {file_count} files, {total_size / 1024 / 1024:.2f} MB")
            except PermissionError as e:
                logger.warning(f"Cannot remove {lang_dir.name}/: Files may be open in another program")
            except OSError as e:
                logger.error(f"Failed to remove {lang_dir}: {e}")
    
    # Remove manifest, metrics, and sample files
    cleanup_files = [
        'ecl-v2-manifest.csv',
        'ecl-v2-metrics.json',
        'ecl-v2-sample.txt'
    ]
    
    for filename in cleanup_files:
        file_path = output_dir / filename
        if file_path.exists():
            try:
                file_size = file_path.stat().st_size
                file_path.unlink()
                stats['files_removed'] += 1
                stats['bytes_freed'] += file_size
                logger.debug(f"Removed {filename}")
            except PermissionError:
                logger.warning(f"Cannot remove {filename}: File may be open in another program")
            except OSError as e:
                logger.error(f"Failed to remove {filename}: {e}")
    
    if stats['files_removed'] > 0:
        logger.info(
            f"Cleanup complete: {stats['files_removed']} files removed, "
            f"{stats['bytes_freed'] / 1024 / 1024:.2f} MB freed, "
            f"{stats['dirs_removed']} directory trees removed"
        )
    else:
        logger.info("Output directory was already clean")
    
    return stats


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description='Generate ECL v2 documents from juris_inventory.sqlite',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--db',
        type=Path,
        default=CONFIG['db_path'],
        help=f"Path to juris_inventory.sqlite (default: {CONFIG['db_path']})"
    )
    
    parser.add_argument(
        '--out',
        type=Path,
        default=CONFIG['output_dir'],
        help=f"Output directory (default: {CONFIG['output_dir']})"
    )
    
    parser.add_argument(
        '--limit-per-lang',
        type=int,
        default=CONFIG['cases_per_language'],
        help=f"Cases per language (default: {CONFIG['cases_per_language']})"
    )
    
    parser.add_argument(
        '--min-content-length',
        type=int,
        default=CONFIG['min_content_length'],
        help=f"Minimum content length (default: {CONFIG['min_content_length']})"
    )
    
    parser.add_argument(
        '--seed',
        type=str,
        default=CONFIG['random_seed'],
        help=f"Random seed for reproducibility (default: {CONFIG['random_seed']})"
    )
    
    parser.add_argument(
        '--language',
        type=str,
        choices=['en', 'fr', 'both'],
        default='both',
        help="Generate for specific language or both (default: both)"
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help="Preview operation without writing files"
    )
    
    parser.add_argument(
        '--strict',
        action='store_true',
        help="Enable strict validation (fail on warnings)"
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help="Enable verbose logging"
    )
    
    parser.add_argument(
        '--clean',
        action='store_true',
        help="Clean output directory before generation (removes all existing .ecl.txt files)"
    )
    
    parser.add_argument(
        '--stratify-by',
        type=str,
        choices=['tribunal', 'year', 'tribunal_year', 'none'],
        default='none',
        help="Stratified sampling dimension: 'tribunal' (X per tribunal), 'year' (X per year), 'tribunal_year' (X per tribunal+year combo), or 'none' for random sampling (default: none)"
    )
    
    parser.add_argument(
        '--per-group',
        type=int,
        default=10,
        help="Cases per group when using --stratify-by (default: 10). Ignored if --stratify-by=none"
    )
    
    parser.add_argument(
        '--use-v22',
        action='store_true',
        help="Use ECL v2.2 format (18 fields with RETRIEVAL_ANCHOR + 5-folder layout)"
    )
    
    parser.add_argument(
        '--year',
        type=int,
        default=None,
        help="Filter cases by specific year (e.g., --year 2025). If not specified, all years are included."
    )
    
    return parser.parse_args()


def write_ecl_files(cases: List[CaseRecord], output_dir: Path, logger, config: Dict, use_v22: bool = False) -> List[Path]:
    """
    Write ECL v2.1 or v2.2 files to disk with micro-header injection.
    
    v2.2 Changes:
    - 5-folder structure: {en|fr}/{scc|fca|fc|sst|unknown}/
    - Filename template: {LANGIDX}_{rank-tribunal}_{YYYYMMDD}_{CASEID}_{DOCID}.ecl.txt
    - Collision detection with sequential suffix
    - 18-field header with RETRIEVAL_ANCHOR
    
    Args:
        cases: List of CaseRecord objects
        output_dir: Base output directory
        logger: Logger instance
        config: Configuration dict
        use_v22: Use ECL v2.2 format and naming (default: False = v2.1)
    
    Returns:
        List of written file paths
    """
    # INPUT VALIDATION
    if not cases:
        logger.warning("No cases provided to write_ecl_files(), returning empty list")
        return []
    
    required_config_keys = [
        'enable_micro_headers', 'micro_header_every_chars', 
        'tribunal_folders', 'default_date_for_missing'
    ]
    if use_v22:
        required_config_keys.append('retrieval_anchor_max_chars')
    
    missing_keys = [k for k in required_config_keys if k not in config]
    if missing_keys:
        raise ValueError(f"Missing required config keys: {missing_keys}")
    
    if not output_dir.exists():
        logger.info(f"Creating output directory: {output_dir}")
        output_dir.mkdir(parents=True, exist_ok=True)
    
    written_files = []
    filename_tracker = {}  # Track filenames for collision detection
    
    for case in cases:
        if use_v22:
            # ============= ECL v2.2: 5-folder layout + deterministic filenames =============
            
            # Determine tribunal folder (scc, fca, fc, sst, or unknown)
            tribunal_lower = case.tribunal.lower()
            tribunal_folders = config.get('tribunal_folders', ['scc', 'fca', 'fc', 'sst', 'unknown'])
            
            if tribunal_lower in tribunal_folders:
                tribunal_folder = tribunal_lower
            else:
                tribunal_folder = 'unknown'
                logger.warning(f"Unknown tribunal '{case.tribunal}' for case {case.file_stem}, using 'unknown' folder")
            
            # Build 5-folder path: output_dir/{en|fr}/{tribunal}/
            file_dir = output_dir / case.language / tribunal_folder
            file_dir.mkdir(parents=True, exist_ok=True)
            
            # Build v2.2 filename: {LANGIDX}_{rank-tribunal}_{YYYYMMDD}_{CASEID}_{DOCID}.ecl.txt
            lang_idx = case.language.upper()  # EN or FR
            rank_tribunal = f"{case.tribunal_rank}-{tribunal_folder}"
            
            # Normalize date to YYYYMMDD
            date_str = normalize_date_for_filename(
                case.publication_date, 
                default=config.get('default_date_for_missing', '99999999')
            )
            
            # Extract case ID
            case_id = sanitize_for_filename(extract_case_id(case), max_length=30)
            
            # Doc ID: extract numeric ID from file_stem (e.g., "fca_2006-FCA-27_34996_en" → "34996")
            # Fallback to last 12 chars of case.id if extraction fails
            doc_id_match = re.search(r'_(\d+)_[a-z]{2}$', case.file_stem)
            if doc_id_match:
                doc_id = doc_id_match.group(1)
            else:
                doc_id = sanitize_for_filename(str(case.id)[-12:], max_length=12)
            
            # Build base filename
            base_filename = f"{lang_idx}_{rank_tribunal}_{date_str}_{case_id}_{doc_id}"
            
            # Collision detection: add suffix if filename exists
            collision_key = f"{file_dir}/{base_filename}"
            if collision_key in filename_tracker:
                filename_tracker[collision_key] += 1
                suffix = filename_tracker[collision_key]
                filename = f"{base_filename}_v{suffix}.ecl.txt"
                logger.warning(f"Filename collision detected, using: {filename}")
            else:
                filename_tracker[collision_key] = 1
                filename = f"{base_filename}.ecl.txt"
            
            file_path = file_dir / filename
            
            # Generate ECL v2.2 document
            document = format_ecl_v22(
                case,
                enable_micro_headers=config.get('enable_micro_headers', True),
                micro_every_chars=config.get('micro_header_every_chars', 1500),
                retrieval_anchor_max_chars=config.get('retrieval_anchor_max_chars', 900)
            )
        else:
            # ============= ECL v2.1: Original behavior =============
            
            # Build output path: output_dir/language/tribunal/stem.ecl.txt
            file_dir = output_dir / case.language / case.tribunal
            file_dir.mkdir(parents=True, exist_ok=True)
            
            # Validate file path length (Windows: 260 char limit)
            max_path_len = config.get('max_file_path_length', 250)
            file_stem = case.file_stem
            
            # Check initial path length
            test_path = file_dir / f"{file_stem}.ecl.txt"
            if len(str(test_path)) > max_path_len:
                logger.warning(
                    f"File path too long ({len(str(test_path))} chars): {test_path}"
                )
                # Truncate file stem to fit
                max_stem_len = max_path_len - len(str(file_dir)) - len(".ecl.txt") - 10
                file_stem = file_stem[:max_stem_len]
                logger.info(f"Truncated file stem to: {file_stem}")
            
            file_path = file_dir / f"{file_stem}.ecl.txt"
            
            # Generate ECL v2.1 document
            document = format_ecl_v2(
                case,
                enable_micro_headers=config.get('enable_micro_headers', True),
                micro_every_chars=config.get('micro_header_every_chars', 1500)
            )
        
        # Write to disk (same for both versions)
        try:
            file_path.write_text(document, encoding='utf-8')
            written_files.append(file_path)
            logger.debug(f"Wrote: {file_path}")
        except (IOError, OSError, UnicodeEncodeError) as e:
            logger.error(f"Failed to write {file_path}: {e}")
            raise
    
    return written_files


def write_manifest(
    cases_en: List[CaseRecord],
    cases_fr: List[CaseRecord],
    output_dir: Path,
    logger,
    use_v22: bool = False
) -> Path:
    """
    Write CSV manifest with ALL ECL v2.2 header fields for comprehensive logging.
    
    Enhanced in v2.2.1: Includes all 18 ECL header fields matching the file format exactly.
    This enables complete metadata analysis without opening individual files.
    
    Args:
        cases_en: English cases
        cases_fr: French cases
        output_dir: Output directory
        logger: Logger instance
        use_v22: Use ECL v2.2 format
    
    Returns:
        Path to manifest file
    """
    from datetime import datetime
    from ecl_formatter import compute_content_hash, extract_keywords, extract_retrieval_anchor
    
    manifest_path = output_dir / CONFIG['manifest_filename']
    
    # Enhanced fieldnames matching all ECL v2.2 header fields (lowercase for CSV)
    fieldnames = [
        'doc_class',
        'ecl_version',
        'generated',
        'content_hash',
        'file_stem',
        'lang',
        'tribunal',
        'tribunal_rank',
        'decision_date',
        'citation',
        'keywords',
        'retrieval_anchor',
        'pdf_link',
        'web_link',
        'blob_path',
        'source_name',
        'page_count',
        'content_length',
        'output_path',
        'exceptions'  # Track edge cases and data quality issues
    ]
    
    with open(manifest_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for case in cases_en + cases_fr:
            # Compute ECL v2.2 metadata fields
            content_hash = compute_content_hash(case.content)
            keywords = extract_keywords(case.content, max_keywords=7)
            retrieval_anchor = extract_retrieval_anchor(
                case.content,
                max_chars=CONFIG.get('retrieval_anchor_max_chars', 900)
            )
            
            # Truncate retrieval anchor if needed (same logic as formatter)
            max_anchor_len = CONFIG.get('retrieval_anchor_max_chars', 900)
            if len(retrieval_anchor) > max_anchor_len:
                retrieval_anchor = retrieval_anchor[:max_anchor_len].rsplit(' ', 1)[0] + '...'
            
            # Build correct filename based on version
            if use_v22:
                lang_idx = case.language.upper()
                rank_tribunal = f"{case.tribunal_rank}-{case.tribunal}"
                date_str = normalize_date_for_filename(
                    case.publication_date,
                    default='99999999'
                )
                case_id = sanitize_for_filename(extract_case_id(case), max_length=30)
                doc_id = sanitize_for_filename(str(case.id), max_length=20)
                filename = f"{lang_idx}_{rank_tribunal}_{date_str}_{case_id}_{doc_id}.ecl.txt"
            else:
                filename = f"{case.file_stem}.ecl.txt"
            
            output_path = output_dir / case.language / case.tribunal / filename
            
            # Detect exceptions and edge cases
            exceptions = []
            if not case.pdf_link:
                exceptions.append('MISSING_PDF_LINK')
            if not case.web_link:
                exceptions.append('MISSING_WEB_LINK')
            if not case.citation:
                exceptions.append('MISSING_CITATION')
            if not case.publication_date:
                exceptions.append('MISSING_DATE')
            if len(case.content) < 1000:
                exceptions.append('SHORT_CONTENT')
            if case.page_count == 0:
                exceptions.append('ZERO_PAGES')
            if not keywords.strip():
                exceptions.append('NO_KEYWORDS')
            
            exceptions_str = '|'.join(exceptions) if exceptions else ''
            
            # Write row with all ECL v2.2 fields
            writer.writerow({
                'doc_class': 'ECL',
                'ecl_version': '2.2' if use_v22 else '2.1',
                'generated': datetime.now().isoformat(),
                'content_hash': content_hash,
                'file_stem': case.file_stem,
                'lang': case.language.upper(),
                'tribunal': case.tribunal.upper(),
                'tribunal_rank': case.tribunal_rank,
                'decision_date': case.publication_date or '',
                'citation': case.citation or '',
                'keywords': keywords,
                'retrieval_anchor': retrieval_anchor[:100] + '...' if len(retrieval_anchor) > 100 else retrieval_anchor,  # Truncate for CSV readability
                'pdf_link': case.pdf_link or '',
                'web_link': case.web_link or '',
                'blob_path': case.metadata_relpath or '',
                'source_name': case.source_name or '',
                'page_count': case.page_count,
                'content_length': len(case.content),
                'output_path': str(output_path.relative_to(output_dir)),
                'exceptions': exceptions_str
            })
    
    logger.info(f"Wrote manifest: {manifest_path}")
    return manifest_path


def generate_metrics(
    cases_en: List[CaseRecord],
    cases_fr: List[CaseRecord],
    db_stats: Dict,
    output_dir: Path,
    logger
) -> Path:
    """
    Generate metrics report in JSON format.
    
    Args:
        cases_en: English cases
        cases_fr: French cases
        db_stats: Database statistics
        output_dir: Output directory
        logger: Logger instance
    
    Returns:
        Path to metrics file
    """
    metrics_path = output_dir / CONFIG['metrics_filename']
    
    # Calculate metrics
    all_cases = cases_en + cases_fr
    
    tribunal_dist = {}
    for case in all_cases:
        tribunal_dist[case.tribunal] = tribunal_dist.get(case.tribunal, 0) + 1
    
    content_lengths = [len(case.content) for case in all_cases]
    
    metrics = {
        'generation_timestamp': datetime.now().isoformat(),
        'total_cases': len(all_cases),
        'english_cases': len(cases_en),
        'french_cases': len(cases_fr),
        'tribunal_distribution': tribunal_dist,
        'content_statistics': {
            'min_length': min(content_lengths) if content_lengths else 0,
            'max_length': max(content_lengths) if content_lengths else 0,
            'avg_length': sum(content_lengths) // len(content_lengths) if content_lengths else 0
        },
        'database_statistics': db_stats,
        'configuration': {
            'min_content_length': CONFIG['min_content_length'],
            'random_seed': CONFIG['random_seed']
        }
    }
    
    with open(metrics_path, 'w', encoding='utf-8') as f:
        json.dump(metrics, f, indent=2)
    
    logger.info(f"Wrote metrics: {metrics_path}")
    return metrics_path


def write_sample_file(cases: List[CaseRecord], output_dir: Path, logger, use_v22: bool = False) -> Path:
    """
    Write one complete sample ECL file for validation.
    
    Args:
        cases: List of cases
        output_dir: Output directory
        logger: Logger instance
        use_v22: If True, use ECL v2.2 format with RETRIEVAL_ANCHOR field
    
    Returns:
        Path to sample file
    """
    if not cases:
        return None
    
    sample_path = output_dir / CONFIG['sample_filename']
    
    # Use first SCC case if available, otherwise first case
    sample_case = next((c for c in cases if c.tribunal == 'scc'), cases[0])
    
    # Use same format as main generation (v2.1 or v2.2)
    if use_v22:
        document = format_ecl_v22(
            sample_case,
            enable_micro_headers=CONFIG.get('enable_micro_headers', True),
            micro_every_chars=CONFIG.get('micro_header_every_chars', 1500),
            retrieval_anchor_max_chars=CONFIG.get('retrieval_anchor_max_chars', 900)
        )
    else:
        document = format_ecl_v2(sample_case)
    
    sample_path.write_text(document, encoding='utf-8')
    
    logger.info(f"Wrote sample: {sample_path} ({sample_case.file_stem})")
    return sample_path


def main():
    """Main execution function."""
    args = parse_args()
    
    # Update config from args
    CONFIG['db_path'] = args.db
    CONFIG['output_dir'] = args.out
    CONFIG['cases_per_language'] = args.limit_per_lang
    CONFIG['min_content_length'] = args.min_content_length
    CONFIG['random_seed'] = args.seed
    CONFIG['strict_validation'] = args.strict
    CONFIG['log_level'] = 'DEBUG' if args.verbose else 'INFO'
    
    # Setup logger
    logger = setup_logger(
        name='ecl_generator',
        log_file=CONFIG['log_file'],
        level=CONFIG['log_level']
    )
    
    logger.info("="*60)
    logger.info("ECL v2 GENERATOR STARTING")
    logger.info("="*60)
    
    # Validate configuration
    if not validate_config(CONFIG):
        logger.error("Configuration validation failed")
        sys.exit(1)
    
    print_config(CONFIG)
    
    # Pre-flight checks
    checks = preflight_checks(CONFIG)
    if not print_preflight_report(checks):
        logger.error("Pre-flight checks failed")
        sys.exit(1)
    
    # Get database stats
    with LogContext(logger, "Gathering database statistics"):
        db_stats = get_database_stats(CONFIG['db_path'])
    
    # Determine languages to process
    languages = ['en', 'fr'] if args.language == 'both' else [args.language]
    
    cases_en = []
    cases_fr = []
    
    # Load cases for each language (stratified or random sampling)
    for lang in languages:
        with LogContext(logger, f"Loading {lang.upper()} cases"):
            try:
                if args.stratify_by != 'none':
                    # Stratified sampling
                    cases, metadata = load_cases_stratified(
                        db_path=CONFIG['db_path'],
                        language=lang,
                        per_group_limit=args.per_group,
                        group_by=args.stratify_by,
                        min_content_length=args.min_content_length,
                        seed=args.seed,
                        tribunal_ranks=CONFIG['tribunal_ranks'],
                        year_filter=args.year
                    )
                    logger.info(f"Stratified sampling: {metadata['groups_found']} groups found")
                else:
                    # Random sampling (original behavior)
                    cases, metadata = load_cases_from_db(
                        db_path=CONFIG['db_path'],
                        language=lang,
                        limit=args.limit_per_lang,
                        min_content_length=args.min_content_length,
                        seed=args.seed,
                        tribunal_ranks=CONFIG['tribunal_ranks'],
                        year_filter=args.year
                    )
                
                if lang == 'en':
                    cases_en = cases
                else:
                    cases_fr = cases
                
                logger.info(f"Loaded {len(cases)} {lang.upper()} cases")
                logger.info(f"Tribunal distribution: {metadata['tribunal_distribution']}")
                
            except (sqlite3.Error, ValueError, IOError) as e:
                logger.error(f"Failed to load {lang.upper()} cases: {e}")
                if args.strict:
                    raise
                sys.exit(1)
    
    # Validate cases
    if args.strict:
        with LogContext(logger, "Validating case records"):
            validator = CaseRecordValidator(strict=True)
            validation_failed = False
            
            for case in cases_en + cases_fr:
                case_dict = {
                    'id': case.id,
                    'citation': case.citation,
                    'publication_date': case.publication_date,
                    'content': case.content,
                    'metadata_relpath': case.metadata_relpath,
                    'pdf_link': case.pdf_link,
                    'blob_name': case.blob_name
                }
                
                results = validator.validate_record(case_dict)
                
                for result in results:
                    if not result.passed and result.severity == 'critical':
                        logger.error(f"Validation failed for {case.file_stem}: {result.message}")
                        validation_failed = True
            
            if validation_failed:
                logger.error("Validation failed. Aborting.")
                sys.exit(1)
    
    # Dry run: show preview and exit
    if args.dry_run:
        logger.info("DRY RUN MODE - No files will be written")
        
        if cases_en:
            logger.info("\nSample EN case preview:")
            print("\n" + "="*60)
            print(get_sample_preview(cases_en[0], content_lines=20))
            print("="*60)
        
        if cases_fr:
            logger.info("\nSample FR case preview:")
            print("\n" + "="*60)
            print(get_sample_preview(cases_fr[0], content_lines=20))
            print("="*60)
        
        logger.info("\nDry run complete. Use without --dry-run to generate files.")
        sys.exit(0)
    
    # Create output directory
    CONFIG['output_dir'].mkdir(parents=True, exist_ok=True)
    
    # Clean output directory if requested
    if args.clean:
        with LogContext(logger, "Cleaning output directory"):
            cleanup_stats = clean_output_directory(CONFIG['output_dir'], logger)
            if cleanup_stats['files_removed'] > 0:
                logger.warning(
                    f"Removed {cleanup_stats['files_removed']} existing files "
                    f"({cleanup_stats['bytes_freed'] / 1024 / 1024:.2f} MB)"
                )
            else:
                logger.info("Output directory was already clean")
    
    # Write ECL files
    with LogContext(logger, "Writing ECL v2 files"):
        all_files = []
        format_ver = "v2.2" if args.use_v22 else "v2.1"
        logger.info(f"Using ECL {format_ver} format")
        
        if cases_en:
            files_en = write_ecl_files(cases_en, CONFIG['output_dir'], logger, CONFIG, use_v22=args.use_v22)
            all_files.extend(files_en)
            logger.info(f"Wrote {len(files_en)} EN files")
        
        if cases_fr:
            files_fr = write_ecl_files(cases_fr, CONFIG['output_dir'], logger, CONFIG, use_v22=args.use_v22)
            all_files.extend(files_fr)
            logger.info(f"Wrote {len(files_fr)} FR files")
    
    # Write manifest
    with LogContext(logger, "Writing manifest"):
        manifest_path = write_manifest(cases_en, cases_fr, CONFIG['output_dir'], logger, use_v22=args.use_v22)
    
    # Generate metrics
    with LogContext(logger, "Generating metrics"):
        metrics_path = generate_metrics(cases_en, cases_fr, db_stats, CONFIG['output_dir'], logger)
    
    # Write sample file
    with LogContext(logger, "Writing sample file"):
        sample_path = write_sample_file(cases_en + cases_fr, CONFIG['output_dir'], logger, use_v22=args.use_v22)
    
    # Final summary
    print("\n" + "="*60)
    print("ECL v2 GENERATION COMPLETE")
    print("="*60)
    print(f"Total files:    {len(all_files)}")
    print(f"English:        {len(cases_en)}")
    print(f"French:         {len(cases_fr)}")
    print(f"Output dir:     {CONFIG['output_dir']}")
    print(f"Manifest:       {manifest_path.name}")
    print(f"Metrics:        {metrics_path.name}")
    if sample_path:
        print(f"Sample:         {sample_path.name}")
    print("="*60 + "\n")
    
    logger.info("ECL v2 generation completed successfully")


if __name__ == '__main__':
    main()
