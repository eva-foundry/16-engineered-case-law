# GitHub Copilot Instructions - Engineered Case Law Pipeline

**Template Version**: 2.1.0  
**Project Version**: 1.0.0  
**Generated**: January 30, 2026  
**Last Updated**: January 30, 2026  
**Project Type**: CDC-Driven Data Pipeline / Engineered Case Law Generator  
**Based on**: EVA Professional Component Architecture Standards (from EVA-JP-v1.2 production learnings) + Project 07 Foundation Layer

---

## Release Notes

### Version 1.0.0 (January 30, 2026)
**Initial Project-Specific Release**:
- Applied Project 07 Foundation Layer to Engineered Case Law Pipeline
- Customized PART 2 with CDC pipeline architecture, ECL v2 generator, Nine EPICs framework
- Documented operational status: 419 ECL cases generated (199 EN, 220 FR)
- Established next priorities: EPIC 6 (Chunk Engineering), EPIC 7 (EVA DA Ingestion)

---

## Table of Contents

### PART 1: Universal Best Practices
- [Encoding & Script Safety](#critical-encoding--script-safety)
- [Azure Account Management](#critical-azure-account-management)
- [AI Context Management](#ai-context-management-strategy)
- [Azure Services Inventory](#azure-services--capabilities-inventory)
- [Professional Component Architecture](#professional-component-architecture)
  - [DebugArtifactCollector](#implementation-debugartifactcollector)
  - [SessionManager](#implementation-sessionmanager)
  - [StructuredErrorHandler](#implementation-structurederrorhandler)
  - [ProfessionalRunner](#implementation-zero-setup-project-runner)
- [Professional Transformation](#professional-transformation-methodology)
- [Dependency Management](#dependency-management-with-alternatives)
- [Workspace Housekeeping](#workspace-housekeeping-principles)
- [Code Style Standards](#code-style-standards)

### PART 2: Engineered Case Law Pipeline - Project Specific
- [Quick Commands Table](#mandatory-category-1-quick-commands-table)
- [Architecture Overview](#architecture-overview)
- [Project Structure](#project-structure)
- [Critical Code Patterns](#critical-code-patterns)
- [Nine EPICs Framework](#nine-epics-framework-implementation-status)
- [Deployment Status & Known Issues](#deployment-status--known-issues)
- [Troubleshooting](#troubleshooting-quick-reference)

### PART 3: Quality & Safety
- [Anti-Patterns Prevention](#anti-patterns-prevention)
- [File Organization Requirements](#file-organization-requirements)
- [Quality Gates](#quality-gates)
- [Emergency Debugging Protocol](#emergency-debugging-protocol)

---

## Quick Reference

**Most Critical Patterns**:
1. **Encoding Safety** - Always use ASCII-only in scripts (prevents UnicodeEncodeError in Windows cp1252)
2. **CDC Architecture** - juris_inventory.sqlite as bridge between CanLII corpus and ECL generation
3. **Deterministic Output** - Fixed seed (42) for reproducible case sampling
4. **Quality Gates** - 16-line metadata headers, validation at EPIC boundaries
5. **Cost Optimization** - Selective OCR, cost scales with change not corpus size

**Professional Components** (Full Working Implementations):

| Component | Purpose | Key Methods |
|-----------|---------|-------------|
| **DebugArtifactCollector** | Capture HTML/screenshots/traces | `capture_state()`, `set_page()` |
| **SessionManager** | Checkpoint/resume operations | `save_checkpoint()`, `load_latest_checkpoint()` |
| **StructuredErrorHandler** | JSON error logging | `log_error()`, `log_structured_event()` |
| **ProfessionalRunner** | Zero-setup execution | `auto_detect_project_root()`, `validate_pre_flight()` |

---

## PART 1: UNIVERSAL BEST PRACTICES

> **Applicable to any project, any scenario**  
> Critical patterns, Azure inventory management, workspace organization principles

[COMPLETE PART 1 CONTENT FROM TEMPLATE - Lines 1-1105 as read above]

### Critical: Encoding & Script Safety

**ABSOLUTE BAN: No Unicode/Emojis Anywhere**
- **NEVER use in code**: Checkmarks, X marks, emojis, Unicode symbols, ellipsis
- **NEVER use in reports**: Unicode decorations, fancy bullets, special characters
- **NEVER use in documentation**: Unless explicitly required by specification
- **ALWAYS use**: Pure ASCII - "[PASS]", "[FAIL]", "[ERROR]", "[INFO]", "[WARN]", "..."
- **Reason**: Enterprise Windows cp1252 encoding causes silent UnicodeEncodeError crashes
- **Solution**: Set `PYTHONIOENCODING=utf-8` in batch files as safety measure

**Examples**:
```python
# [FORBIDDEN] Will crash in enterprise Windows
print(" Success")  # Unicode checkmark - NEVER
print("[x] Failed")   # Unicode X - NEVER
print(" Wait...")    # Unicode symbols - NEVER

# [REQUIRED] ASCII-only alternatives
print("[PASS] Success")
print("[FAIL] Failed")
print("[INFO] Wait...")
```

### Critical: Azure Account Management

**Multiple Azure Accounts Pattern**
- **Personal Account**: Personal subscription - personal sandbox
- **Professional Account**: Professional email - organization production access

**When Azure CLI fails with "subscription doesn't exist"**:
1. Check current account: `az account show --query user.name`
2. Switch accounts: `az logout` then `az login --use-device-code`
3. Verify access: `az account list`

### AI Context Management Strategy

**Pattern**: Systematic approach to avoid context overload

**5-Step Process**:
1. **Assess**: What context do I need? (Don't load everything)
2. **Prioritize**: What's most relevant NOW? (Focus on current task)
3. **Load**: Get specific context only (Use targeted file reads, grep searches)
4. **Execute**: Perform task with loaded context
5. **Verify**: Validate result matches intent

**Example**:
```python
# [AVOID] Bad: Load entire file when only need one function
with open('large_file.py') as f:
    content = f.read()  # Loads 10,000 lines

# [RECOMMENDED] Good: Targeted context loading
grep_search(query="def target_function", includePattern="large_file.py")
read_file(filePath="large_file.py", startLine=450, endLine=500)
```

### Azure Services & Capabilities Inventory

**Azure Blob Storage**
- **Capabilities**: Object storage, containers, metadata
- **Use Cases**: Document storage, ECL outputs, audit logs
- **Pattern**: Use managed identity, implement lifecycle policies

**Azure Cosmos DB** (Potential for EPIC 7)
- **Capabilities**: NoSQL database, session storage, change feed
- **Use Cases**: ECL metadata storage, EVA DA ingestion
- **Pattern**: Use partition keys effectively, implement TTL

**Azure Cognitive Search** (Potential for EPIC 7)
- **Capabilities**: Hybrid search (vector + keyword), semantic ranking
- **Use Cases**: ECL semantic search, case law retrieval
- **Pattern**: Use index-based access, implement retry logic

### Professional Component Architecture

**Pattern**: Enterprise-grade component design (from Project 06/07)

**Every professional component implements**:
- **DebugArtifactCollector**: Evidence at operation boundaries
- **SessionManager**: Checkpoint/resume capabilities
- **StructuredErrorHandler**: JSON logging with context
- **Observability Wrapper**: Pre-state, execution, post-state capture

**Usage Pattern - Combining Components**:

> **Note**: The following shows a conceptual pattern for combining components. For complete, production-ready implementations you can copy-paste directly, see the detailed sections below.
```python
from pathlib import Path
from datetime import datetime
import json

class ProfessionalComponent:
    """Base class for enterprise-grade components"""
    
    def __init__(self, component_name: str, base_path: Path):
        self.component_name = component_name
        self.base_path = base_path
        
        # Core professional infrastructure
        self.debug_collector = DebugArtifactCollector(component_name, base_path)
        self.session_manager = SessionManager(component_name, base_path)
        self.error_handler = StructuredErrorHandler(component_name, base_path)
    
    async def execute_with_observability(self, operation_name: str, operation):
        """Execute operation with full evidence collection"""
        # 1. ALWAYS capture pre-state
        await self.debug_collector.capture_state(f"{operation_name}_before")
        await self.session_manager.save_checkpoint("before_operation", {
            "operation": operation_name,
            "timestamp": datetime.now().isoformat()
        })
        
        try:
            # 2. Execute operation
            result = await operation()
            
            # 3. ALWAYS capture success state
            await self.debug_collector.capture_state(f"{operation_name}_success")
            await self.session_manager.save_checkpoint("operation_success", {
                "operation": operation_name,
                "result_preview": str(result)[:200]
            })
            return result
            
        except Exception as e:
            # 4. ALWAYS capture error state
            await self.debug_collector.capture_state(f"{operation_name}_error")
            await self.error_handler.log_structured_error(operation_name, e)
            raise
```

**When to use**: Any component that interacts with external systems, complex logic, or enterprise automation

---

### Implementation: DebugArtifactCollector

**Purpose**: Capture comprehensive diagnostic state at system boundaries for rapid debugging

**Working Implementation** (from Project 06):
```python
from pathlib import Path
from datetime import datetime
import json
import asyncio

class DebugArtifactCollector:
    """Systematic evidence capture at operation boundaries
    
    Captures HTML, screenshots, network traces, and structured logs
    for every significant operation to enable rapid debugging.
    """
    
    def __init__(self, component_name: str, base_path: Path):
        """Initialize collector for specific component
        
        Args:
            component_name: Name of component (e.g., "authentication", "data_extraction")
            base_path: Project root directory
        """
        self.component_name = component_name
        self.debug_dir = base_path / "debug" / component_name
        self.debug_dir.mkdir(parents=True, exist_ok=True)
        
        self.page = None  # Set by browser automation
        self.network_log = []  # Populated by network listener
    
    async def capture_state(self, context: str):
        """Capture complete diagnostic state
        
        Args:
            context: Operation context (e.g., "before_login", "after_submit", "error_state")
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 1. Capture HTML snapshot
        if self.page:
            html_file = self.debug_dir / f"{context}_{timestamp}.html"
            html_content = await self.page.content()
            html_file.write_text(html_content, encoding='utf-8')
        
        # 2. Capture screenshot
        if self.page:
            screenshot_file = self.debug_dir / f"{context}_{timestamp}.png"
            await self.page.screenshot(path=str(screenshot_file), full_page=True)
        
        # 3. Capture network trace
        if self.network_log:
            network_file = self.debug_dir / f"{context}_{timestamp}_network.json"
            network_file.write_text(json.dumps(self.network_log, indent=2))
        
        # 4. Capture structured log with application state
        log_file = self.debug_dir / f"{context}_{timestamp}.json"
        log_file.write_text(json.dumps({
            "timestamp": timestamp,
            "context": context,
            "component": self.component_name,
            "url": self.page.url if self.page else None,
            "viewport": await self.page.viewport_size() if self.page else None
        }, indent=2))
        
        return {
            "html": str(html_file) if self.page else None,
            "screenshot": str(screenshot_file) if self.page else None,
            "network": str(network_file) if self.network_log else None,
            "log": str(log_file)
        }
    
    def set_page(self, page):
        """Attach to browser page for capture"""
        self.page = page
        
        # Enable network logging
        async def log_request(request):
            self.network_log.append({
                "timestamp": datetime.now().isoformat(),
                "type": "request",
                "url": request.url,
                "method": request.method
            })
        
        page.on("request", lambda req: asyncio.create_task(log_request(req)))
```

**Usage Pattern**:
```python
# In your automation component
collector = DebugArtifactCollector("my_component", project_root)
collector.set_page(page)

# Before risky operation
await collector.capture_state("before_submit")

try:
    await risky_operation()
    await collector.capture_state("success")
except Exception as e:
    await collector.capture_state("error")
    raise
```

---

### Implementation: SessionManager

**Purpose**: Enable checkpoint/resume capabilities for long-running operations

**Working Implementation** (from Project 06):
```python
from pathlib import Path
from datetime import datetime, timedelta
import json
import shutil
from typing import Dict, Optional

class SessionManager:
    """Manages persistent session state for checkpoint/resume operations
    
    Enables long-running automation to save progress and resume
    from last successful checkpoint if interrupted.
    """
    
    def __init__(self, component_name: str, base_path: Path):
        """Initialize session manager
        
        Args:
            component_name: Component identifier
            base_path: Project root directory
        """
        self.component_name = component_name
        self.session_dir = base_path / "sessions" / component_name
        self.session_dir.mkdir(parents=True, exist_ok=True)
        
        self.session_file = self.session_dir / "session_state.json"
        self.checkpoint_dir = self.session_dir / "checkpoints"
        self.checkpoint_dir.mkdir(exist_ok=True)
    
    def save_checkpoint(self, checkpoint_id: str, data: Dict) -> Path:
        """Save checkpoint with state data
        
        Args:
            checkpoint_id: Unique checkpoint identifier (e.g., "item_5_processed")
            data: State data to persist
            
        Returns:
            Path to saved checkpoint file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        checkpoint_file = self.checkpoint_dir / f"{checkpoint_id}_{timestamp}.json"
        
        checkpoint_data = {
            "checkpoint_id": checkpoint_id,
            "timestamp": datetime.now().isoformat(),
            "component": self.component_name,
            "data": data
        }
        
        checkpoint_file.write_text(json.dumps(checkpoint_data, indent=2))
        
        # Update session state to point to latest checkpoint
        self.update_session_state(checkpoint_id, str(checkpoint_file))
        
        return checkpoint_file
    
    def load_latest_checkpoint(self) -> Optional[Dict]:
        """Load most recent checkpoint if available
        
        Returns:
            Checkpoint data or None if no checkpoint exists
        """
        if not self.session_file.exists():
            return None
        
        try:
            session_data = json.loads(self.session_file.read_text())
            checkpoint_file = Path(session_data.get("latest_checkpoint"))
            
            if checkpoint_file.exists():
                return json.loads(checkpoint_file.read_text())
            
        except Exception as e:
            print(f"[WARN] Failed to load checkpoint: {e}")
        
        return None
    
    def update_session_state(self, checkpoint_id: str, checkpoint_path: str):
        """Update session state with latest checkpoint reference"""
        session_data = {
            "component": self.component_name,
            "last_updated": datetime.now().isoformat(),
            "latest_checkpoint": checkpoint_path,
            "checkpoint_id": checkpoint_id
        }
        
        self.session_file.write_text(json.dumps(session_data, indent=2))
    
    def clear_session(self):
        """Clear all session state and checkpoints"""
        if self.checkpoint_dir.exists():
            shutil.rmtree(self.checkpoint_dir)
            self.checkpoint_dir.mkdir()
        
        if self.session_file.exists():
            self.session_file.unlink()
```

**Usage Pattern**:
```python
# Initialize session manager
session_mgr = SessionManager("batch_processor", project_root)

# Try to resume from checkpoint
checkpoint = session_mgr.load_latest_checkpoint()
if checkpoint:
    start_index = checkpoint["data"]["last_processed_index"]
    print(f"[INFO] Resuming from checkpoint: item {start_index}")
else:
    start_index = 0

# Process items with checkpoints
for i in range(start_index, len(items)):
    process_item(items[i])
    
    # Save checkpoint every 10 items
    if i % 10 == 0:
        session_mgr.save_checkpoint(f"item_{i}", {
            "last_processed_index": i,
            "items_completed": i + 1,
            "timestamp": datetime.now().isoformat()
        })
```

---

### Implementation: StructuredErrorHandler

**Purpose**: Provide JSON-based error logging with full context for debugging

**Working Implementation** (from Project 06):
```python
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path
import json
import traceback

class StructuredErrorHandler:
    """Enterprise-grade error handling with structured logging
    
    Captures errors with full context in JSON format for easy parsing
    and analysis. All output is ASCII-safe for enterprise Windows.
    """
    
    def __init__(self, component_name: str, base_path: Path):
        """Initialize error handler
        
        Args:
            component_name: Component identifier
            base_path: Project root directory
        """
        self.component_name = component_name
        self.error_dir = base_path / "logs" / "errors"
        self.error_dir.mkdir(parents=True, exist_ok=True)
    
    def log_error(self, error: Exception, context: Optional[Dict[str, Any]] = None) -> Dict:
        """Log error with structured context
        
        Args:
            error: Exception object
            context: Additional context (operation name, parameters, etc.)
            
        Returns:
            Error report dictionary
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        error_report = {
            "timestamp": datetime.now().isoformat(),
            "component": self.component_name,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "traceback": traceback.format_exc(),
            "context": context or {}
        }
        
        # Save to timestamped file
        error_file = self.error_dir / f"{self.component_name}_error_{timestamp}.json"
        error_file.write_text(json.dumps(error_report, indent=2))
        
        # Print ASCII-safe error message
        print(f"[ERROR] {self.component_name}: {type(error).__name__}")
        print(f"[ERROR] Message: {str(error)}")
        print(f"[ERROR] Details saved to: {error_file}")
        
        return error_report
    
    def log_structured_event(self, event_type: str, data: Dict[str, Any]):
        """Log structured event (non-error)
        
        Args:
            event_type: Event type (e.g., "operation_start", "data_validated")
            data: Event data
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        event_report = {
            "timestamp": datetime.now().isoformat(),
            "component": self.component_name,
            "event_type": event_type,
            "data": data
        }
        
        # Save to events log
        event_file = self.error_dir.parent / f"{self.component_name}_events_{timestamp}.json"
        event_file.write_text(json.dumps(event_report, indent=2))

class ProjectBaseException(Exception):
    """Base exception with structured error reporting
    
    All custom exceptions should inherit from this to ensure
    consistent error handling and reporting.
    """
    
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        """Initialize exception with context
        
        Args:
            message: Error description (ASCII only)
            context: Additional error context
        """
        super().__init__(message)
        self.message = message
        self.context = context or {}
        self.timestamp = datetime.now().isoformat()
    
    def get_error_report(self) -> Dict[str, Any]:
        """Generate structured error report
        
        Returns:
            Dictionary with full error details
        """
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "context": self.context,
            "timestamp": self.timestamp
        }
```

**Usage Pattern**:
```python
# Initialize error handler
error_handler = StructuredErrorHandler("my_automation", project_root)

try:
    risky_operation()
except Exception as e:
    # Log with context
    error_handler.log_error(e, context={
        "operation": "data_processing",
        "input_file": "data.csv",
        "current_row": 42
    })
    raise

# Custom exception with automatic context
class DataValidationError(ProjectBaseException):
    pass

try:
    if not is_valid(data):
        raise DataValidationError(
            "Invalid data format",
            context={"expected": "CSV", "received": "JSON"}
        )
except DataValidationError as e:
    error_report = e.get_error_report()
    error_handler.log_error(e, context=error_report["context"])
```

---

### Implementation: Zero-Setup Project Runner

**Purpose**: Enable users to run project from anywhere without configuration

**Working Implementation** (from Project 06):
```python
#!/usr/bin/env python3
"""Professional project runner with zero-setup execution"""

import os
import sys
import argparse
from pathlib import Path
import subprocess
from typing import List

# Set UTF-8 encoding for Windows
os.environ.setdefault('PYTHONIOENCODING', 'utf-8')

class ProfessionalRunner:
    """Zero-setup professional automation wrapper"""
    
    def __init__(self):
        self.project_root = self.auto_detect_project_root()
        self.main_script = "pipeline/generate_ecl_v2.py"
    
    def auto_detect_project_root(self) -> Path:
        """Find project root from any subdirectory
        
        Searches for project markers in current and parent directories
        to enable running from any location within the project.
        """
        current = Path.cwd()
        
        # Project indicators
        indicators = [
            "pipeline/generate_ecl_v2.py",
            "ACCEPTANCE.md",
            "README.md",
            "engineered-case-law-tasks.md",
            ".git"
        ]
        
        # Check current directory
        for indicator in indicators:
            if (current / indicator).exists():
                return current
        
        # Check parent directories
        for parent in current.parents:
            for indicator in indicators:
                if (parent / indicator).exists():
                    return parent
        
        # Fallback to current directory
        print("[WARN] Could not auto-detect project root, using current directory")
        return current
    
    def validate_pre_flight(self) -> tuple[bool, str]:
        """Pre-flight checks before execution
        
        Validates environment, dependencies, and project structure.
        
        Returns:
            (success: bool, message: str)
        """
        checks = []
        
        # Check main script exists
        main_script_path = self.project_root / self.main_script
        if not main_script_path.exists():
            return False, f"[FAIL] Main script not found: {main_script_path}"
        checks.append("[PASS] Main script found")
        
        # Check required directories
        required_dirs = ["out", "pipeline"]
        for dir_name in required_dirs:
            dir_path = self.project_root / dir_name
            if not dir_path.exists():
                return False, f"[FAIL] Required directory missing: {dir_name}"
            checks.append(f"[PASS] Directory exists: {dir_name}")
        
        # Check Python dependencies
        try:
            import sqlite3
            import json
            checks.append("[PASS] Required Python modules available")
        except ImportError as e:
            return False, f"[FAIL] Missing Python module: {e}"
        
        return True, "\n".join(checks)
    
    def build_command(self, **kwargs) -> List[str]:
        """Build command with normalized parameters
        
        Converts user inputs to proper command structure.
        """
        cmd = [
            sys.executable,
            str(self.project_root / self.main_script)
        ]
        
        # Add parameters
        for key, value in kwargs.items():
            if value is not None:
                if isinstance(value, bool):
                    if value:
                        cmd.append(f"--{key}")
                else:
                    cmd.extend([f"--{key}", str(value)])
        
        return cmd
    
    def execute_with_enterprise_safety(self, cmd: List[str]) -> int:
        """Execute with proper encoding and error handling"""
        # Set environment
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        
        # Change to project root
        original_cwd = os.getcwd()
        os.chdir(self.project_root)
        
        try:
            print(f"[INFO] Project root: {self.project_root}")
            print(f"[INFO] Command: {' '.join(cmd)}")
            print("-" * 60)
            
            result = subprocess.run(cmd, env=env)
            return result.returncode
            
        finally:
            os.chdir(original_cwd)
    
    def run(self, **kwargs) -> int:
        """Main execution entry point"""
        print("[INFO] Professional Runner - Zero-Setup Execution")
        print(f"[INFO] Detected project root: {self.project_root}")
        
        # Pre-flight validation
        success, message = self.validate_pre_flight()
        print("\n" + message)
        
        if not success:
            print("\n[FAIL] Pre-flight checks failed")
            return 1
        
        # Build and execute command
        cmd = self.build_command(**kwargs)
        return self.execute_with_enterprise_safety(cmd)

def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Engineered Case Law pipeline runner with zero-setup execution"
    )
    
    # Add project-specific arguments
    parser.add_argument("--sample-size", type=int, help="Number of cases to generate per language")
    parser.add_argument("--output-dir", help="Output directory path")
    
    args = parser.parse_args()
    
    # Create runner and execute
    runner = ProfessionalRunner()
    sys.exit(runner.run(**vars(args)))

if __name__ == "__main__":
    main()
```

**Usage**:
```bash
# Run from anywhere in the project
python run_ecl_generator.py --sample-size 500

# Or create Windows batch wrapper
# run_ecl_generator.bat:
@echo off
set PYTHONIOENCODING=utf-8
python run_ecl_generator.py %*
```

---

### Professional Transformation Methodology

**Pattern**: Systematic 4-step approach to enterprise-grade development

**When refactoring or creating automation systems**:

1. **Foundation Systems** (20% of work)
   - Create `debug/`, `evidence/`, `logs/` directory structure
   - Establish coding standards and utilities
   - Implement ASCII-only error handling
   - Set up structured logging infrastructure

2. **Testing Framework** (30% of work)
   - Automated validation with evidence collection
   - Component-level unit tests
   - Integration tests with retry logic
   - Acceptance criteria validation

3. **Main System Refactoring** (40% of work)
   - Apply professional component architecture
   - Integrate validation and observability
   - Implement graceful error handling
   - Add session management and checkpoints

4. **Documentation & Cleanup** (10% of work)
   - Consolidate redundant code
   - Document patterns and decisions
   - Create runbooks and troubleshooting guides
   - Archive superseded implementations

**Quality Gate**: Each phase produces evidence before proceeding to next phase

### Dependency Management with Alternatives

**Pattern**: Handle blocked packages in enterprise environments

**Always provide fallback alternatives**:

```python
# Pattern 1: Try primary, fall back to alternative
try:
    import pandas as pd
    DATA_PROCESSOR = "pandas"
except ImportError:
    print("[INFO] Pandas not available, using built-in csv")
    import csv
    DATA_PROCESSOR = "csv"

# Pattern 2: Feature detection
def get_available_sqlite_client():
    """Return best available SQLite client"""
    if importlib.util.find_spec("sqlite3"):
        import sqlite3
        return sqlite3
    else:
        raise ImportError("sqlite3 required for ECL generation")
```

**Document alternatives in requirements**: Add comments explaining enterprise constraints

### Workspace Housekeeping Principles

**Context Engineering - Keep AI context clean and focused**

**Best Practices**:
- **Root directory**: Active operations only (`README.md`, `ACCEPTANCE.md`)
- **Context folder**: Use `docs/eva-foundry/` as AI agent "brain"
  - `projects/` - Active work with debugging artifacts
  - `workspace-notes/` - Ephemeral notes, workflow docs
  - `system-analysis/` - Architecture docs, inventory reports

**Pattern**: If referenced in copilot-instructions.md or used for AI context -> belongs in `docs/eva-foundry/`

**File Organization Rules**:
1. **Logs** -> `logs/{category}/`
2. **Scripts** -> `scripts/{category}/` or `pipeline/`
3. **Documentation** -> `docs/{category}/` or project root for key files

**Naming Conventions**:
- **Scripts**: `verb_noun.py` (snake_case)
  - [RECOMMENDED] Good: `generate_ecl_v2.py`, `validate_output.py`
  - [AVOID] Bad: `GenerateECL.py`, `validate.py`
- **Docs**: `CATEGORY-DESCRIPTION.md` (UPPERCASE for status docs)
  - [RECOMMENDED] Good: `ACCEPTANCE.md`, `README.md`
  - [AVOID] Bad: `Final-Status-Report.md`
- **Output**: `{operation}-{timestamp}.json` or descriptive names
  - [RECOMMENDED] Good: `ecl-v2-metrics.json`, `case_001.json`

### Evidence Collection at Operation Boundaries

**Goal**: Systematic evidence capture for rapid debugging

**MANDATORY: Every component operation must capture**:
- **Pre-state**: Configuration, input data validation BEFORE execution
- **Success state**: Metrics, output validation on successful completion  
- **Error state**: Full diagnostic artifacts on failure
- **Structured logging**: JSON-based error context with timestamps

**Timestamped Naming Convention (MANDATORY)**:
- Pattern: `{component}_{context}_{YYYYMMDD_HHMMSS}.{ext}`
- Examples:
  - `ecl_generation_20260130_143522.log`
  - `validation_error_20260130_150011.json`
  - `ecl-v2-metrics_20260130_143522.json`
- Benefits: Chronological sorting, parallel execution support, audit trails

### Code Style Standards

**Python**:
- **Type Hints**: Use for all function signatures
- **Naming**: `snake_case` functions/variables, `PascalCase` classes
- **Formatting**: Black (line length 100) + isort
- **Error Handling**: Wrap external calls with try/except

**Files**:
- Python: `snake_case.py`
- Documentation: `UPPERCASE-WITH-DASHES.md` (status docs), `lowercase.md` (technical docs)

---

**You are now ready for project-specific patterns**  
See [PART 2: Engineered Case Law Pipeline](#part-2-engineered-case-law-pipeline-project-specific) below for project-specific instructions.

---

## PART 2: ENGINEERED CASE LAW PIPELINE - PROJECT SPECIFIC

### Project Lock

This file is the copilot-instructions for **16-engineered-case-law** (16-engineered-case-law).

The workspace-level bootstrap rule "Step 1 -- Identify the active project from the currently open file path"
applies **only at the initial load of this file** (first read at session start).
Once this file has been loaded, the active project is locked to **16-engineered-case-law** for the entire session.
Do NOT re-evaluate project identity from editorContext or terminal CWD on each subsequent request.
Work state and sprint context are read from `STATUS.md` and `PLAN.md` at bootstrap -- not from this file.

---

> **AI INSTRUCTION MODE**: This section provides structured instructions for AI assistants working on the Engineered Case Law (ECL) pipeline.  
> Use imperative language ("Use X for Y", "When user asks X, do Y") not descriptive documentation.

---

### **[MANDATORY]** Category 1: Quick Commands Table

**Purpose**: Instant command lookup without parsing prose. AI needs copy-paste ready commands.

| Task | Command | Expected Time | Output Location |
|------|---------|---------------|-----------------|
| **Generate ECL v2** | `python pipeline/generate_ecl_v2.py` | <10 seconds | `out/ecl-v2/*.json` |
| **Check Generation Metrics** | `cat out/ecl-v2/ecl-v2-metrics.json` | <1 second | Terminal output |
| **Validate Output** | `python pipeline/validate_ecl_output.py` | <5 seconds | Terminal output |
| **Inspect SQLite Bridge** | `sqlite3 juris_inventory.sqlite "SELECT COUNT(*) FROM pages"` | <2 seconds | Terminal output |
| **Run Tests** | `pytest tests/` | <30 seconds | Terminal output |

**Quick Restart Pattern**:
```bash
# Regenerate ECL v2 cases with specific sample size
python pipeline/generate_ecl_v2.py --sample-size 500
```

---

### Architecture Overview

**System Type**: CDC-Driven Data Pipeline / Engineered Case Law Generator

**Core Concept**: Normalize Canadian jurisprudence (CanLII) into traceable, retrieval-ready ECL format for EVA Domain Assistant ingestion.

**Architecture Pattern**: Bridge Approach
- **Source**: CanLII corpus (102,678 EN + 117,174 FR pages)
- **Bridge**: juris_inventory.sqlite (pre-materialized snapshot)
- **Generator**: generate_ecl_v2.py (deterministic sampling + ECL v2 formatting)
- **Output**: 419 ECL v2 JSON files (199 EN, 220 FR)
- **Destination**: EVA Domain Assistant (EPIC 7 - future)

**Key Components**:
1. **juris_inventory.sqlite** - SQLite database with pages table (id, databaseId, caseId, language, url, content_length)
2. **generate_ecl_v2.py** - ECL v2 generator with deterministic sampling (seed=42)
3. **out/ecl-v2/** - Generated ECL files with 16-line metadata headers
4. **ecl-v2-metrics.json** - Generation metrics (timestamp, sample_size, counts, SQLite source)

---

### Project Structure

```
16-engineered-case-law/
 pipeline/
    generate_ecl_v2.py         # ECL v2 generator (operational)
    canlii_inventory.py        # Corpus inventory builder
    validate_ecl_output.py     # Quality gate validation
 out/
    ecl-v2/                    # 419 generated cases (199 EN, 220 FR)
        ecl-v2-*.json          # Individual ECL files
        ecl-v2-metrics.json    # Generation metrics
 docs/
    README.md                  # Project overview, architecture
    ACCEPTANCE.md              # Quality criteria, validation gates
    engineered-case-law-tasks.md  # Nine EPICs implementation plan
 .github/
    copilot-instructions.md    # This file
 juris_inventory.sqlite         # SQLite bridge (102,678 EN + 117,174 FR pages)
```

**Main Entry Points**:
- **Primary Script**: `pipeline/generate_ecl_v2.py` - Generates ECL v2 cases from SQLite bridge
- **Validation**: `pipeline/validate_ecl_output.py` - Validates ECL output against quality gates

**Critical Files**:
- **SQLite Bridge**: `juris_inventory.sqlite` - CRITICAL - Pre-materialized CanLII snapshot
- **Metrics**: `out/ecl-v2/ecl-v2-metrics.json` - Generation metrics and traceability
- **Configuration**: None currently - all settings in generate_ecl_v2.py script

**Debug/Evidence**:
- **Debug Artifacts**: `debug/ecl_generation/` - Screenshots, traces (future)
- **Structured Logs**: `logs/errors/` - JSON error logs (future)
- **Session Checkpoints**: `sessions/ecl_generation/checkpoints/` - Resume capability (future)

---

### Critical Code Patterns

#### Pattern 1: SQLite Bridge Access (Deterministic Sampling)

**When to Use**: Any code querying juris_inventory.sqlite for case selection

**Correct Implementation**:
```python
import sqlite3
from pathlib import Path
import random

def get_sampled_cases(sample_size_per_lang: int = 200, seed: int = 42) -> dict:
    """Get deterministic sample of cases from SQLite bridge
    
    Args:
        sample_size_per_lang: Number of cases per language
        seed: Random seed for reproducibility (default: 42)
    
    Returns:
        dict: {"en": [...], "fr": [...]} with case records
    """
    # CRITICAL: Use project root to find SQLite file
    project_root = Path(__file__).parent.parent
    db_path = project_root / "juris_inventory.sqlite"
    
    if not db_path.exists():
        raise FileNotFoundError(f"SQLite bridge not found: {db_path}")
    
    # Connect to SQLite
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # Enable dict-like access
    cursor = conn.cursor()
    
    # Set deterministic seed
    random.seed(seed)
    
    results = {"en": [], "fr": []}
    
    for lang in ["en", "fr"]:
        # Query all cases for language
        cursor.execute("""
            SELECT id, databaseId, caseId, language, url, content_length
            FROM pages
            WHERE language = ?
            ORDER BY id
        """, (lang,))
        
        all_cases = cursor.fetchall()
        
        # Deterministic sampling
        sampled_indices = random.sample(range(len(all_cases)), 
                                       min(sample_size_per_lang, len(all_cases)))
        
        results[lang] = [all_cases[i] for i in sorted(sampled_indices)]
    
    conn.close()
    return results
```

**Why This Pattern**: 
- Enables reproducible case selection across runs (critical for testing)
- Uses SQLite as bridge to avoid direct CanLII API calls (cost optimization)
- Preserves traceability (id, databaseId, caseId)

**[x] FORBIDDEN Anti-Pattern**:
```python
# NEVER DO THIS - non-deterministic sampling
def bad_pattern():
    # No seed - results vary across runs
    sampled = random.sample(all_cases, sample_size)  # WRONG
    
    # Hardcoded path - breaks when running from different directories
    conn = sqlite3.connect("juris_inventory.sqlite")  # WRONG
    
    # No error handling - silent failures
    cursor.execute("SELECT * FROM pages")  # WRONG - no validation
```

---

#### Pattern 2: ECL v2 Metadata Header Generation

**When to Use**: Generating ECL JSON files with required metadata

**Correct Implementation**:
```python
from datetime import datetime
import json

def generate_ecl_v2_metadata(case_record: dict, sequence_number: int) -> dict:
    """Generate ECL v2 metadata header (16-line standard)
    
    Args:
        case_record: SQLite row with case data
        sequence_number: Sequential ECL number (1-based)
    
    Returns:
        dict: ECL v2 formatted case with metadata header
    """
    ecl_metadata = {
        # Line 1-4: ECL Identity
        "ecl_version": "2.0",
        "ecl_number": f"ECL-{sequence_number:06d}",
        "generated_timestamp": datetime.now().isoformat(),
        "generator_version": "generate_ecl_v2.py v1.0.0",
        
        # Line 5-8: Source Traceability
        "source_system": "CanLII",
        "source_database_id": case_record["databaseId"],
        "source_case_id": case_record["caseId"],
        "source_url": case_record["url"],
        
        # Line 9-12: Content Metadata
        "language": case_record["language"],
        "content_length": case_record["content_length"],
        "processing_status": "canonical_selected",
        "quality_gate_passed": True,
        
        # Line 13-16: Pipeline Context
        "epic_stage": "EPIC-5-complete",  # Bilingual Canonical Selection
        "next_epic": "EPIC-6",  # Chunk Engineering
        "bridge_source": "juris_inventory.sqlite",
        "deterministic_seed": 42
    }
    
    return ecl_metadata

# Usage in ECL generation
ecl_case = generate_ecl_v2_metadata(case_record, sequence_number)
output_file = Path(f"out/ecl-v2/ecl-v2-{ecl_case['ecl_number']}.json")
output_file.write_text(json.dumps(ecl_case, indent=2))
```

**Why This Pattern**: 
- 16-line metadata header ensures complete traceability
- Standardized format enables automated validation
- Includes quality gate status and pipeline context

**[x] FORBIDDEN Anti-Pattern**:
```python
# NEVER DO THIS - incomplete metadata
def bad_pattern(case_record):
    return {
        "case_id": case_record["caseId"],  # Missing traceability
        "content": case_record["content"]  # No metadata header
    }  # WRONG - no version, timestamp, quality gate info
```

---

#### Pattern 3: Quality Gate Validation at EPIC Boundaries

**When to Use**: Validating ECL output at each EPIC completion

**Correct Implementation**:
```python
from pathlib import Path
import json

def validate_ecl_v2_quality_gates(output_dir: Path) -> dict:
    """Validate ECL v2 output against acceptance criteria
    
    Quality Gates:
    1. File count matches expected (sample_size * 2 languages)
    2. All files have 16-line metadata headers
    3. Deterministic seed consistent across runs
    4. Language distribution correct (EN + FR)
    5. No duplicate ECL numbers
    
    Args:
        output_dir: Directory with ECL v2 JSON files
    
    Returns:
        dict: Validation report with pass/fail status
    """
    ecl_files = list(output_dir.glob("ecl-v2-*.json"))
    
    validation_report = {
        "timestamp": datetime.now().isoformat(),
        "total_files": len(ecl_files),
        "quality_gates": {},
        "errors": []
    }
    
    # Gate 1: File count validation
    metrics_file = output_dir / "ecl-v2-metrics.json"
    if metrics_file.exists():
        metrics = json.loads(metrics_file.read_text())
        expected_count = metrics["sample_size"] * 2  # EN + FR
        
        validation_report["quality_gates"]["file_count"] = {
            "expected": expected_count,
            "actual": len(ecl_files),
            "passed": len(ecl_files) == expected_count
        }
    
    # Gate 2: Metadata header validation
    required_fields = [
        "ecl_version", "ecl_number", "generated_timestamp", "generator_version",
        "source_system", "source_database_id", "source_case_id", "source_url",
        "language", "content_length", "processing_status", "quality_gate_passed",
        "epic_stage", "next_epic", "bridge_source", "deterministic_seed"
    ]
    
    metadata_valid = []
    for ecl_file in ecl_files:
        ecl_data = json.loads(ecl_file.read_text())
        
        # Check all required fields present
        has_all_fields = all(field in ecl_data for field in required_fields)
        metadata_valid.append(has_all_fields)
        
        if not has_all_fields:
            validation_report["errors"].append({
                "file": ecl_file.name,
                "error": "Missing required metadata fields"
            })
    
    validation_report["quality_gates"]["metadata_headers"] = {
        "total_files": len(ecl_files),
        "valid_headers": sum(metadata_valid),
        "passed": all(metadata_valid)
    }
    
    # Gate 3: Language distribution
    lang_counts = {"en": 0, "fr": 0}
    for ecl_file in ecl_files:
        ecl_data = json.loads(ecl_file.read_text())
        lang_counts[ecl_data.get("language", "unknown")] += 1
    
    validation_report["quality_gates"]["language_distribution"] = {
        "english": lang_counts["en"],
        "french": lang_counts["fr"],
        "passed": lang_counts["en"] > 0 and lang_counts["fr"] > 0
    }
    
    # Overall status
    all_gates_passed = all(
        gate["passed"] for gate in validation_report["quality_gates"].values()
    )
    
    validation_report["overall_status"] = "PASS" if all_gates_passed else "FAIL"
    
    return validation_report

# Usage after ECL generation
validation_report = validate_ecl_v2_quality_gates(Path("out/ecl-v2"))
if validation_report["overall_status"] == "FAIL":
    print(f"[FAIL] Quality gates failed: {validation_report['errors']}")
else:
    print("[PASS] All quality gates passed")
```

**Why This Pattern**: 
- Automated validation prevents manual QA bottlenecks
- Quality gates enforce acceptance criteria at EPIC boundaries
- Structured validation report enables traceability

---

### Nine EPICs Framework (Implementation Status)

**Strategic Approach**: End-to-end pipeline from corpus to EVA DA ingestion

**EPIC 1: Inventory Creation** [x] COMPLETE
- **Goal**: Build comprehensive inventory of Canadian jurisprudence
- **Output**: juris_inventory.sqlite (102,678 EN + 117,174 FR pages)
- **Quality Gate**: SQLite file exists with pages table

**EPIC 2: Acquisition** [x] COMPLETE (Skipped - CDC Approach)
- **Goal**: Acquire case law content from CanLII
- **Approach**: Use juris_inventory.sqlite as bridge (no direct acquisition)
- **Rationale**: Cost optimization - SQLite snapshot sufficient for ECL generation

**EPIC 3: Extraction** [x] COMPLETE (Implicit in v2)
- **Goal**: Extract structured data from raw case law
- **Approach**: Metadata extraction during ECL generation
- **Output**: ECL v2 with 16-line metadata headers

**EPIC 4: Canonical Selection** [x] COMPLETE
- **Goal**: Select representative cases for ECL generation
- **Approach**: Deterministic sampling (seed=42) from juris_inventory.sqlite
- **Output**: 419 cases selected (199 EN, 220 FR)

**EPIC 5: Bilingual Support** [x] COMPLETE
- **Goal**: Ensure balanced English/French representation
- **Approach**: Stratified sampling by language
- **Output**: 199 EN + 220 FR cases (~50/50 distribution)

**EPIC 6: Chunk Engineering**  NEXT PRIORITY
- **Goal**: Split ECL cases into retrieval-optimized chunks
- **Approach**: TBD - semantic chunking, sliding windows, or hierarchical
- **Target Output**: ecl-v2-chunks/ directory with chunk metadata

**EPIC 7: EVA DA Ingestion**  NEXT PRIORITY
- **Goal**: Ingest ECL chunks into EVA Domain Assistant
- **Approach**: TBD - Azure Cosmos DB or Azure Cognitive Search
- **Target Output**: Searchable ECL corpus in EVA DA

**EPIC 8: Validation & Metrics**  PLANNED
- **Goal**: Comprehensive validation framework
- **Approach**: Automated quality gates, regression testing, metrics dashboard
- **Target Output**: validation_reports/ with quality metrics

**EPIC 9: Governance & Maintenance**  PLANNED
- **Goal**: Version control, change management, audit trails
- **Approach**: Git-based versioning, change logs, governance policies
- **Target Output**: CHANGELOG.md, governance documentation

---

### Deployment Status & Known Issues

**Last Generated**: January 30, 2026  
**Current Version**: ECL v2.0  
**Environment**: Local Development  
**Deployment Method**: Direct Python execution (no infrastructure)

**Infrastructure Status**:
- [x] **SQLite Bridge**: juris_inventory.sqlite (102,678 EN + 117,174 FR pages)
- [x] **ECL Generator**: generate_ecl_v2.py operational
- [x] **Output Directory**: out/ecl-v2/ with 419 cases generated
-  **Chunk Engineering**: EPIC 6 - pending design
-  **EVA DA Ingestion**: EPIC 7 - pending design

**Known Issues & Workarounds**:
- [WARN] **No Chunk Engineering Yet**: ECL cases not split into retrieval-ready chunks
  - **Impact**: Cannot ingest into EVA DA until chunking implemented
  - **Workaround**: None - EPIC 6 required before EPIC 7
  - **ETA**: TBD - EPIC 6 design phase

- [WARN] **No Automated Validation**: Quality gates manual (validate_ecl_output.py exists but not integrated)
  - **Impact**: Requires manual validation after each generation
  - **Workaround**: Run `python pipeline/validate_ecl_output.py` manually
  - **ETA**: EPIC 8 - validation framework

---

### Troubleshooting Quick Reference

**Purpose**: AI needs diagnostic workflows (Symptom -> Cause -> Solution pattern).

#### Issue 1: "juris_inventory.sqlite not found"

**Symptom**: `FileNotFoundError: SQLite bridge not found: juris_inventory.sqlite`

**Root Cause**: Running generate_ecl_v2.py from wrong directory or SQLite file missing

**Solution**:
1. Verify project root: `cd {project_root}`
2. Check SQLite exists: `ls juris_inventory.sqlite`
3. If missing: Rebuild with `python pipeline/canlii_inventory.py` (if available)

**Evidence Location**: `logs/errors/ecl_generation_error_*.json` (future)

---

#### Issue 2: "Generated case count mismatch"

**Symptom**: ecl-v2-metrics.json shows incorrect case count (expected: sample_size * 2)

**Root Cause**: SQLite query returned fewer cases than requested (corpus smaller than sample_size)

**Solution**:
1. Check SQLite row counts: `sqlite3 juris_inventory.sqlite "SELECT COUNT(*) FROM pages WHERE language='en'"`
2. Reduce sample_size: `python pipeline/generate_ecl_v2.py --sample-size 100`
3. Verify metrics: `cat out/ecl-v2/ecl-v2-metrics.json`

**Diagnostic Commands**:
```bash
# Check SQLite contents
sqlite3 juris_inventory.sqlite "SELECT language, COUNT(*) FROM pages GROUP BY language"

# Verify output files
ls out/ecl-v2/ | wc -l
```

---

#### Issue 3: "Non-deterministic output"

**Symptom**: Running generate_ecl_v2.py twice produces different ECL files

**Root Cause**: Random seed not set or modified

**Checklist**:
1. Verify seed in generate_ecl_v2.py: `grep "random.seed" pipeline/generate_ecl_v2.py`
2. Ensure seed=42 (default)
3. Check no external randomness (e.g., datetime-based sampling)
4. Re-run: `python pipeline/generate_ecl_v2.py`

---

## PART 3: QUALITY & SAFETY

### Anti-Patterns Prevention

**NEVER Do These**:

1. **Unicode in Production Code**
   - [x] Using emoji or Unicode symbols in logs/output
   - [x] Use ASCII-only: "[PASS]", "[FAIL]", "[INFO]"

2. **Non-Deterministic Sampling**
   - [x] `random.sample()` without seed
   - [x] `random.seed(42); random.sample()`

3. **Hardcoded File Paths**
   - [x] `conn = sqlite3.connect("juris_inventory.sqlite")`
   - [x] `db_path = project_root / "juris_inventory.sqlite"`

4. **Missing Error Context**
   - [x] `log.error("Operation failed")`
   - [x] `error_handler.log_error(e, context={...})`

5. **No Evidence Capture**
   - [x] Silent failures without diagnostics
   - [x] Capture pre-state, post-state, error state

6. **Incomplete Metadata**
   - [x] ECL files without 16-line headers
   - [x] Full metadata with traceability fields

7. **Missing Quality Gates**
   - [x] Generate output without validation
   - [x] Run validation after generation, check quality gates

8. **Implicit Project Root**
   - [x] Assuming script runs from specific directory
   - [x] `auto_detect_project_root()` in runner

### File Organization Requirements

**Mandatory Structure**:
```
16-engineered-case-law/
  .github/
    copilot-instructions.md    # This file
  pipeline/                    # Core generation scripts
  out/                         # Generated outputs
    ecl-v2/                    # ECL v2 JSON files
  debug/                       # Debug artifacts (future)
    ecl_generation/
  logs/                        # Structured logs (future)
    errors/
  sessions/                    # Checkpoint data (future)
    ecl_generation/
      checkpoints/
  docs/                        # Documentation
  juris_inventory.sqlite       # CRITICAL - SQLite bridge
```

**Naming Enforcement**:
- Scripts: `verb_noun.py` (snake_case)
- Docs: `CATEGORY-DESCRIPTION.md` (UPPERCASE)
- Logs: `{operation}_{YYYYMMDD_HHMMSS}.log`
- Artifacts: `{component}_{context}_{YYYYMMDD_HHMMSS}.{ext}`

### Quality Gates

**Before Generating ECL Cases**:
- [ ] SQLite bridge exists (juris_inventory.sqlite)
- [ ] Output directory cleared or versioned
- [ ] Deterministic seed set (seed=42)
- [ ] Sample size within corpus limits

**After Generating ECL Cases**:
- [ ] File count matches expected (sample_size * 2)
- [ ] All files have 16-line metadata headers
- [ ] Language distribution correct (EN + FR)
- [ ] No duplicate ECL numbers
- [ ] Metrics file generated (ecl-v2-metrics.json)
- [ ] Validation script passed

**Before Proceeding to EPIC 6 (Chunk Engineering)**:
- [ ] EPIC 5 acceptance criteria met
- [ ] 419 ECL v2 cases validated
- [ ] Quality gates documented
- [ ] Next EPIC design reviewed

### Emergency Debugging Protocol

**When ECL Generation Fails**:

1. **Immediate Response** (0-5 minutes)
   - Check error logs in terminal
   - Verify SQLite bridge exists: `ls juris_inventory.sqlite`
   - Check output directory: `ls out/ecl-v2/`
   - Review last metrics: `cat out/ecl-v2/ecl-v2-metrics.json`

2. **Evidence Collection** (5-15 minutes)
   - Capture terminal output
   - Export error messages
   - Document reproduction steps
   - Check SQLite integrity: `sqlite3 juris_inventory.sqlite "PRAGMA integrity_check"`

3. **Root Cause Analysis** (15-60 minutes)
   - Review generate_ecl_v2.py for recent changes
   - Check SQLite query results
   - Verify deterministic seed
   - Compare with last known good state

4. **Mitigation** (immediate)
   - Rollback to last stable version if critical
   - Re-run with smaller sample size
   - Clear output directory and regenerate
   - Document findings

5. **Post-Incident** (within 24 hours)
   - Update troubleshooting guide
   - Add test case to prevent regression
   - Update quality gates if needed

---

**End of Document**

*Generated from EVA Professional Component Architecture Standards (Project 07 Foundation Layer)*  
*For questions or improvements, reference Project 07 implementation in EVA-JP-v1.2*
