"""
================================================================================
MODULE: logger.py
VERSION: 2.1.0
DATE: 2026-02-01 12:00:00
AUTHOR: EVA Foundation - Project 16
================================================================================

PURPOSE:
Structured logging infrastructure for ECL v2.1 generator. Provides dual-handler
logging (console + file) with context managers for operation tracking.

PIPELINE ROLE:
┌──────────────────────────────────────────────────────────────────────┐
│ LOGGER (Observability)                                               │
│                                                                      │
│ [logger.py] ◄── YOU ARE HERE                                        │
│    ├► Used by: All pipeline modules                                │
│    ├► Console: Simple format (timestamp, level, message)          │
│    ├► File: Detailed format (function, line number, full context) │
│    └► Context: LogContext manager for operation blocks            │
└──────────────────────────────────────────────────────────────────────┘

KEY FEATURES:
1. Dual Handlers
   - Console: INFO+ with simple format (HH:MM:SS | LEVEL | message)
   - File: DEBUG+ with detailed format (includes function, line number)
   
2. LogContext Manager
   - Wraps operations with "Starting: X" / "Completed: X" logs
   - Exception-safe with proper __exit__ handling
   - Useful for tracking pipeline stages
   
3. Automatic Directory Creation
   - Creates log directory if missing
   - UTF-8 encoding for international characters
   - Append mode for log files
   
4. Configurable Levels
   - Default: INFO (console), DEBUG (file)
   - Override via level parameter
   - Supports: DEBUG, INFO, WARNING, ERROR, CRITICAL

LOG FORMATS:
Console: 12:34:56 | INFO     | Generated 419 ECL files
File:    2026-02-01 12:34:56 | ecl_generator | INFO     | main:123 | Generated 419 ECL files

KEY FUNCTIONS:
- setup_logger()  - Configure logger with handlers
- LogContext      - Context manager for operation blocks

USAGE:
```python
logger = setup_logger('ecl_generator', log_file=Path('logs/run.log'))

with LogContext(logger, 'Database loading'):
    cases = load_cases_from_db(...)  # Auto-logs start/complete

logger.info('Generated 419 files')
logger.warning('No citation for case X')
logger.error('Database connection failed')
```

INPUTS:
- name: Logger name (e.g., 'ecl_generator')
- log_file: Optional Path to log file
- level: Log level string (default 'INFO')

OUTPUTS:
- logging.Logger: Configured logger instance
- Log files: Timestamp-based log files in logs/ directory

DEPENDENCIES:
- logging: Python standard library
- pathlib: Log file path handling

EPIC MAPPING:
- EPIC 9: Governance (Structured logging, audit trail)

CHANGELOG:
- v2.1.0 (2026-02-01): Production PoC logging
- v1.0.0 (2026-01-15): Initial logging infrastructure
================================================================================
"""

import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logger(
    name: str = 'ecl_generator',
    log_file: Optional[Path] = None,
    level: str = 'INFO'
) -> logging.Logger:
    """
    Configure structured logger with file and console handlers.
    
    Args:
        name: Logger name
        log_file: Path to log file (optional)
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Console handler with simple format
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%H:%M:%S'
    )
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)
    
    # File handler with detailed format
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_format = logging.Formatter(
            '%(asctime)s | %(name)s | %(levelname)-8s | %(funcName)s:%(lineno)d | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_format)
        logger.addHandler(file_handler)
    
    return logger


class LogContext:
    """Context manager for logging operation blocks."""
    
    def __init__(self, logger: logging.Logger, operation: str):
        self.logger = logger
        self.operation = operation
    
    def __enter__(self):
        self.logger.info(f"Starting: {self.operation}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.logger.info(f"Completed: {self.operation}")
        else:
            self.logger.error(f"Failed: {self.operation} - {exc_val}")
        return False  # Don't suppress exceptions
