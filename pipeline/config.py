"""
================================================================================
MODULE: config.py
VERSION: 2.2.1
DATE: 2026-02-01 20:00:00
AUTHOR: EVA Foundation - Project 16
================================================================================

PURPOSE:
Centralized configuration management for ECL v2.2 generator. Provides
environment-aware settings with sensible defaults and validation.

PIPELINE ROLE:
┌──────────────────────────────────────────────────────────────────────┐
│ CONFIGURATION (Foundation Layer)                                     │
│                                                                      │
│ [config.py] ◄── YOU ARE HERE                                        │
│    ├► Loaded by: generate_ecl_v2.py, db_loader.py, validators.py  │
│    ├► Provides: CONFIG dict, path resolution, tribunal ranks      │
│    └► Validates: Paths exist, values are sane                     │
└──────────────────────────────────────────────────────────────────────┘

CONFIGURATION CATEGORIES:
1. Database Settings
   - db_path: Location of juris_inventory.sqlite
   
2. Output Settings
   - output_dir: ECL file output directory
   - manifest_filename: CSV manifest file name
   - metrics_filename: JSON metrics file name
   
3. Selection Criteria
   - cases_per_language: Target cases per language (EN/FR)
   - min_content_length: Minimum content characters (100)
   - random_seed: Deterministic sampling seed
   - target_cases_per_tribunal: Cases per tribunal for stratification
   
4. Format Settings
   - enable_micro_headers: Enable micro-header injection (True)
   - micro_header_every_chars: Injection interval (1500 chars)
   - micro_header_max_counter: Maximum counter value (99999)
   
5. Tribunal Precedence
   - tribunal_ranks: Judicial hierarchy mapping (SCC=1, SST=4)

ENVIRONMENT VARIABLES:
- ECL_DB_PATH: Override default database path
- ECL_OUTPUT_DIR: Override output directory
- ECL_CASES_PER_LANG: Override cases per language
- ECL_MIN_CONTENT: Override minimum content length
- ECL_SEED: Override random seed

EXPORTED OBJECTS:
- CONFIG: Dict[str, Any] - Main configuration dictionary
- validate_config() - Validates paths and settings
- print_config() - Pretty-print configuration to console

DEPENDENCIES:
- pathlib: Path resolution and validation
- os: Environment variable access

EPIC MAPPING:
- EPIC 9: Governance (Configuration management)

CHANGELOG:
- v2.2.0 (2026-02-01): EVA DA 5-folder layout + filename template + RETRIEVAL_ANCHOR
- v2.1.0 (2026-02-01): Added micro-header configuration parameters
- v2.0.0 (2026-01-28): Added tribunal_ranks, max_file_path_length
- v1.0.0 (2026-01-15): Initial configuration module
================================================================================
"""

from pathlib import Path
from typing import Dict
import os

# Base paths
PROJECT_ROOT = Path(__file__).parent
DB_DEFAULT_PATH = PROJECT_ROOT / "../../05-Extract-Cases/data/SPO-Data-Analysis/juris_inventory.sqlite"
OUTPUT_DEFAULT_DIR = PROJECT_ROOT.parent / "out/ecl-v2"

# Generation parameters
CONFIG: Dict = {
    # Database
    'db_path': Path(os.getenv('ECL_DB_PATH', DB_DEFAULT_PATH)),
    
    # Output
    'output_dir': Path(os.getenv('ECL_OUTPUT_DIR', OUTPUT_DEFAULT_DIR)),
    'manifest_filename': 'ecl-v2-manifest.csv',
    'metrics_filename': 'ecl-v2-metrics.json',
    'sample_filename': 'ecl-v2-sample.txt',
    
    # Selection
    'cases_per_language': int(os.getenv('ECL_CASES_PER_LANG', '50')),
    'min_content_length': int(os.getenv('ECL_MIN_CONTENT', '100')),
    'random_seed': os.getenv('ECL_SEED', 'eva-ecl-v2-fixed-seed'),
    'target_cases_per_tribunal': 13,  # ~50 cases / 4 tribunals
    
    # Format
    'ecl_version': '2.2.1',
    'encoding': 'utf-8',
    'enable_micro_headers': True,
    'micro_header_every_chars': 1500,  # Inject metadata every N characters
    'micro_header_max_counter': 99999,  # Maximum counter value (5 digits)
    'micro_header_max_length': 160,  # Maximum micro-header length (chars)
    'micro_header_search_backward_chars': 100,  # Word boundary search distance
    'micro_header_final_tolerance_chars': 200,  # Max chars after final micro-header
    'max_file_path_length': 250,  # Windows-safe path length (260 - buffer)
    
    # ECL v2.2: RETRIEVAL_ANCHOR
    'retrieval_anchor_max_chars': 900,  # Hard limit for discovery anchor
    'retrieval_anchor_min_useful_chars': 100,  # Fallback threshold
    
    # ECL v2.2.1: EI-aware keyword extraction
    'ei_lexicon_en': {
        # Core EI concepts (weight: 3.0)
        'employment insurance': 3.0, 'ei act': 3.0, 'benefits': 2.5, 'claimant': 2.5,
        'eligibility': 2.5, 'availability': 2.5, 'disentitlement': 2.5,
        # Issue types (weight: 2.5)
        'misconduct': 2.5, 'voluntary leaving': 2.5, 'quit': 2.5, 'allocation': 2.5,
        'antedate': 2.5, 'earnings': 2.5, 'insurable employment': 2.5,
        'benefit period': 2.5, 'limitation': 2.5, 'reconsideration': 2.5,
        # Legal terms (weight: 2.0)
        'commission': 2.0, 'umpire': 2.0, 'board of referees': 2.0,
        'qualifying period': 2.0, 'insurable hours': 2.0, 'good cause': 2.0,
        'just cause': 2.0, 'reasonable alternative': 2.0, 'labour dispute': 2.0,
        # Common terms (weight: 1.5)
        'employer': 1.5, 'employee': 1.5, 'ceased employment': 1.5,
        'reason': 1.5, 'circumstances': 1.5, 'tribunal': 1.5
    },
    'ei_lexicon_fr': {
        # Core EI concepts (weight: 3.0)
        'assurance-emploi': 3.0, 'loi sur l\'assurance-emploi': 3.0, 'prestations': 2.5,
        'prestataire': 2.5, 'admissibilité': 2.5, 'disponibilité': 2.5, 'inadmissibilité': 2.5,
        # Issue types (weight: 2.5)
        'inconduite': 2.5, 'départ volontaire': 2.5, 'quitter': 2.5, 'répartition': 2.5,
        'antidater': 2.5, 'rémunération': 2.5, 'emploi assurable': 2.5,
        'période de prestations': 2.5, 'prescription': 2.5, 'révision': 2.5,
        # Legal terms (weight: 2.0)
        'commission': 2.0, 'juge-arbitre': 2.0, 'conseil arbitral': 2.0,
        'période de référence': 2.0, 'heures assurables': 2.0, 'motif valable': 2.0,
        'juste motif': 2.0, 'solution de rechange': 2.0, 'conflit collectif': 2.0,
        # Common terms (weight: 1.5)
        'employeur': 1.5, 'employé': 1.5, 'cessation d\'emploi': 1.5,
        'motif': 1.5, 'circonstances': 1.5, 'tribunal': 1.5
    },
    'statute_reference_patterns': [
        r'Employment Insurance Act', r'EI Act', r'Loi sur l\'assurance-emploi',
        r'section\s+\d+', r's\.\s*\d+',
        r'subsection\s+\d+\([a-z0-9]+\)', r'ss\.\s*\d+\([a-z0-9]+\)',
        r'paragraph\s+\d+\([a-z0-9]+\)\([a-z0-9]+\)',
        r'article\s+\d+', r'paragraphe\s+\d+\([a-z0-9]+\)',
        r'alinéa\s+\d+\([a-z0-9]+\)\([a-z0-9]+\)'
    ],
    'additional_stopwords': {
        'docket', 'dockets', 'coram', 'heard', 'reasons', 'applicant', 'applicants',
        'respondent', 'respondents', 'appellant', 'appellants', 'between', 'entre',
        'issue', 'issues', 'order', 'matter', 'because', 'therefore', 'however',
        'pursuant', 'person', 'persons', 'which', 'where', 'when', 'while',
        'these', 'those', 'such', 'other', 'more', 'some'
    },
    'name_filter_patterns': [
        r'^[A-Z]{2,}$',  # All caps
        r'^[A-Z][a-zàâäæçèéêëïîôœùûüÿ]+$'  # Title case
    ],
    'common_judge_surnames': {
        'létourneau', 'nadon', 'pelletier', 'stratas', 'webb', 'chartier',
        'mainville', 'gauthier', 'sexton', 'leblanc', 'rennie', 'dawson',
        'boivin', 'near', 'roy', 'locke', 'gleason', 'woods', 'rivoalen',
        'abella', 'moldaver', 'karakatsanis', 'wagner', 'gascon', 'côté',
        'brown', 'rowe', 'martin', 'kasirer', 'jamal', 'obomsawin'
    },
    
    # ECL v2.2: Filename template
    # {LANGIDX}_{rank-tribunal}_{YYYYMMDD}_{CASEID}_{DOCID}.ecl.txt
    'filename_template_fields': ['langidx', 'court', 'date', 'caseid', 'docid'],
    'default_date_for_missing': '99999999',  # Sorts to bottom when descending
    
    # ECL v2.2: Tribunal folders (5 folders: scc, fca, fc, sst, unknown)
    'tribunal_folders': ['scc', 'fca', 'fc', 'sst', 'unknown'],
    
    # Tribunal precedence (SCC=1 highest, SST=4 lowest, unknown=5 for unclassified)
    'tribunal_ranks': {
        'scc': 1,   # Supreme Court of Canada
        'fca': 2,   # Federal Court of Appeal
        'fc': 3,    # Federal Court
        'sst': 4,   # Social Security Tribunal
        'unknown': 5  # Unclassified/unrecognized tribunals
    },
    
    # Logging
    'log_level': os.getenv('LOG_LEVEL', 'INFO'),
    'log_file': OUTPUT_DEFAULT_DIR / 'ecl-v2-generation.log',
    
    # Validation
    'strict_validation': os.getenv('ECL_STRICT', 'false').lower() == 'true',
    'fail_on_validation_error': False,
}


def validate_config(config: Dict) -> bool:
    """
    Validate configuration parameters.
    
    Args:
        config: Configuration dictionary
    
    Returns:
        True if configuration is valid, False otherwise
    """
    errors = []
    
    if not config['db_path'].exists():
        errors.append(f"Database not found: {config['db_path']}")
    
    if config['cases_per_language'] < 1:
        errors.append(f"Invalid cases_per_language: {config['cases_per_language']}")
    
    if config['min_content_length'] < 100:
        errors.append(f"min_content_length too low: {config['min_content_length']}")
    
    if config['encoding'] not in ('utf-8', 'ascii'):
        errors.append(f"Unsupported encoding: {config['encoding']}")
    
    if errors:
        print("\n❌ Configuration errors:")
        for err in errors:
            print(f"  • {err}")
        return False
    
    return True


def print_config(config: Dict):
    """Print current configuration."""
    print("\n" + "="*60)
    print(f"ECL v{config['ecl_version']} GENERATOR CONFIGURATION")
    print("="*60)
    print(f"Database:           {config['db_path']}")
    print(f"Output Directory:   {config['output_dir']}")
    print(f"Cases per Language: {config['cases_per_language']}")
    print(f"Min Content Length: {config['min_content_length']}")
    print(f"Random Seed:        {config['random_seed']}")
    print(f"Retrieval Anchor:   {config['retrieval_anchor_max_chars']} chars max")
    print(f"Tribunal Folders:   {', '.join(config['tribunal_folders'])}")
    print(f"Strict Validation:  {config['strict_validation']}")
    print(f"Log Level:          {config['log_level']}")
    print("="*60 + "\n")
