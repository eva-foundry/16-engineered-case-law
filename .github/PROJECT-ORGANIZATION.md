<!-- eva-primed-organization -->
<!-- Placeholders: 16-engineered-case-law = project folder name | 2026-03-15 = YYYY-MM-DD format | agent:copilot = agent:name or human:name -->

# 16-engineered-case-law - Organization Standards

**Version**: v5.0.0 (Session 44 - Governance Template Consolidation)
**Primed**: 2026-03-15 by agent:copilot
**Status**: Canonical scaffold for folder structure and file placement

---

## Root-Level Rules

Keep root minimal. Use root for governance and entry-point files only:
- `README.md`, `PLAN.md`, `STATUS.md`, `ACCEPTANCE.md`
- `requirements.txt`, `.gitignore`, `Dockerfile` (if applicable)
- `.github/`, `docs/`, `scripts/`, `tests/`, `evidence/`

Move operational outputs out of root:
- Temporary logs -> `artifacts/logs/`
- One-off outputs -> `artifacts/outputs/`
- Historical backups -> `archives/`
**Veritas Integration**: Projects using eva-veritas (Project 48) for MTI scoring must have:
- `evidence/` at root with naming pattern: `{STORY-ID}-{description}.{ext}`
- `.eva/` directory (auto-generated) containing discovery.json, reconciliation.json, trust.json
- Source files tagged with `# EVA-STORY: {ID}` or `// EVA-STORY: {ID}` comments
---

## Target Folder Structure

```text
docs/
  library/        # Stable reference docs
  sessions/       # Time-bound session notes and reports
  architecture/   # ADRs, diagrams, design patterns

scripts/
  deployment/     # Deploy and environment provisioning
  seed/           # Data/model initialization
  validation/     # Validation and quality checks
  sync/           # External/internal synchronization
  analysis/       # Analysis and reporting scripts
  testing/        # Test helpers and smoke checks
  migration/      # Migration and recovery utilities
  admin/          # Administrative scripts

evidence/         # EVA-veritas evidence files: {STORY-ID}-{description}.{ext}

.eva/             # Auto-generated veritas audit artifacts (gitignored)
  discovery.json
  reconciliation.json
  trust.json

archives/
  logs/
  backups/

artifacts/
  logs/
  outputs/
```

---

## Fractal DPDCA For Project Implementation

Apply DPDCA at **every granularity level**: project phases, features, components, and operations.

### Example: Multi-Phase Project Structure

**Phase 1: Foundation (Template)**
- **DISCOVER**: Identify core requirements, dependencies, and constraints
- **PLAN**: Design architecture, select technologies, define acceptance criteria
- **DO**: Implement minimal viable foundation
- **CHECK**: Validate basic functionality, verify integration points
- **ACT**: Document architecture decisions, lessons learned

**Phase 2: Core Implementation (Template)**
- **DISCOVER**: Analyze feature requirements and edge cases
- **PLAN**: Break down into components with clear interfaces
- **DO**: Implement one component at a time with per-component validation
- **CHECK**: Verify component behavior, integration with Phase 1
- **ACT**: Update documentation with implementation details

**Phase 3: Enhancement & Integration (Template)**
- **DISCOVER**: Identify optimization opportunities and integration gaps
- **PLAN**: Prioritize enhancements, design integration patterns
- **DO**: Execute enhancements with continuous validation
- **CHECK**: Validate performance, security, maintainability
- **ACT**: Document patterns, update standards

**Phase 4: Production Readiness (Template)**
- **DISCOVER**: Audit against production requirements (observability, security, scalability)
- **PLAN**: Define deployment strategy, monitoring, and runbooks
- **DO**: Implement production features (logging, alerts, health checks)
- **CHECK**: Validate against quality gates (MTI score, coverage, compliance)
- **ACT**: Publish runbooks, handoff documentation

### For Reorganization Tasks

1. **DISCOVER**: Inventory current files and classify by type
2. **PLAN**: Define target destination for each file group
3. **DO**: Move one file group at a time
4. **CHECK**: Validate links, script paths, and references after each move
5. **ACT**: Update docs and standards with actual changes

---

## Hybrid Paperless Governance (REQUIRED)

This project uses **mandatory hybrid governance** with Data Model API:

**Pre-Flight Requirement**:
- Priming requires EVA Data Model API to be available
- Pre-flight check: `GET https://msub-eva-data-model.victoriousgrass-30debbd3.canadacentral.azurecontainerapps.io/health`
- Priming fails if API unavailable (10-second timeout)

**File-Based (Backward Compatible)**:
- Local PLAN.md, STATUS.md, ACCEPTANCE.md files created
- Traditional git-based workflow preserved
- Works offline after initial prime

**API-First (Mandatory Sync)**:
- Project record synced to EVA Data Model API during prime
- Step 7: Data Model API sync (cannot be skipped)
- Evidence tracked: `API-SYNC:CREATED` | `API-SYNC:EXISTS`

**Priming Behavior**:
1. Pre-flight: Check API availability (REQUIRED)
2. Steps 1-6: Create all governance files
3. Step 7: Sync project record to API (REQUIRED)
4. Evidence: `.eva/prime-evidence.json` with 7-step audit trail

**Why Hybrid**:
- Enables gradual paperless transition without breaking workflows
- Files provide offline reference and git history
- API provides live query/sync for veritas tools
- Future: Full paperless (API-only, files become optional)

**Veritas Integration**:
- `eva sync_repo` reads governance from API + writes MTI back
- `eva get_trust_score` queries API for MTI score
- `eva audit_repo` combines file + API evidence

---

## Placement Rules

1. `SESSION-*.md` belongs in `docs/sessions/`.
2. Ad-hoc scripts (debug, analysis, fixes) belong in `scripts/*/` subfolders.
3. Generated JSON, reports, and command output belong in `artifacts/outputs/`.
4. Historical exports and backups belong in `archives/` with timestamped folders.
5. Root should never accumulate disposable execution artifacts.

---

## Key Architecture Decisions

Document major technical choices with rationale. Examples:

### 1. [Decision Title]
**Choice**: [Technology/Pattern/Approach selected]

**Rationale**: [Why this choice over alternatives]

**Trade-offs**: [What you gained vs. what you gave up]

**Example Template**:
```
### 1. Technology Stack Selection
**Choice**: Python 3.12 + FastAPI + Cosmos DB NoSQL

**Rationale**: 
- Python 3.12: Team expertise, rich ecosystem for data processing
- FastAPI: Auto-generated OpenAPI docs, async support, type hints
- Cosmos DB: Serverless scaling, 99.999% SLA, JSON-native

**Trade-offs**: 
- Python GIL limits CPU-bound parallelism (mitigated with async I/O)
- Cosmos DB cost at scale (mitigated with RU optimization, TTL policies)
```

### 2. [Add More Decisions As Project Evolves]

---

## Integration Patterns

Document how this project integrates with other systems or components.

### Pattern 1: [Pattern Name]
**Purpose**: [What this pattern solves]

**Flow**:
```
[ASCII diagram or description]
Component A → Component B → Component C
```

**Code Example** (if applicable):
```python
# Example integration code
def integrate_with_system():
    # Placeholder implementation
    pass
```

### Pattern 2: [Add More Integration Patterns]

**Example Template**:
```
### Pattern 1: Event-Driven Processing
**Purpose**: Decouple producers from consumers for scalability

**Flow**:
```
Producer → Event Grid → Function App (Consumer) → Cosmos DB
```

**Code Example**:
```python
# Azure Function with Event Grid trigger
@app.function_name("ProcessEvent")
@app.event_grid_trigger(arg_name="event")
def process_event(event: func.EventGridEvent):
    data = event.get_json()
    # Process event data
    save_to_cosmos(data)
```
```

---

## Standards Compliance

**Template Version**: v5.0.0 (Session 44 - Bootstrap Enforcement)
**Bootstrap Protocol**: Mandatory API-first with fail-closed semantics
**Path References**: No eva-foundation\ or 29-foundry references  
**Documentation**: Session artifacts in `docs/sessions/` or `sessions/`, evidence in `evidence/` or `artifacts/`
**Governance**: PLAN.md, STATUS.md, ACCEPTANCE.md (v5.0.0 format)

**Project-Specific Compliance** (Update as needed):
- **Language/Runtime**: Project-specific 
- **Key Dependencies**: See README.md, PLAN.md, and project_work records in the data model.
- **Cloud Provider**: Azure
- **Security Standards**: Workspace governance, RBAC, and evidence-backed verification
- **Data Residency**: Canada Central unless project-specific requirements state otherwise

---

## Lessons Learned

Document project-specific insights as they emerge. Update this section after each sprint/phase.

### [Session/Date]: [Topic]
**Issue**: [What went wrong or what was discovered]

**Root Cause**: [Why it happened]

**Solution**: [How it was resolved]

**Prevention**: [How to avoid in future]

**Example Template**:
```
### 2026-03-05: API Timeout During Bulk Operations
**Issue**: Bulk import of 10K records timed out after 30 seconds

**Root Cause**: Single-threaded processing with 10ms latency per record = 100 seconds total

**Solution**: Batch processing (100 records/batch) with concurrent requests (5 threads) = 2 seconds total

**Prevention**: 
- Set batch size guideline: max 100 records per request
- Document performance benchmarks in README.md
- Add timeout tests to CI/CD pipeline
```

### [Add More Lessons As Project Evolves]

1. **[Lesson 1]**: [Brief description]
2. **[Lesson 2]**: [Brief description]
3. **[Lesson 3]**: [Brief description]

---

## Verification Checklist

- [ ] Root contains only approved files/folders
- [ ] `docs/sessions/` contains session reports
- [ ] Scripts are grouped by operational purpose
- [ ] Archive and artifact folders are used for non-source outputs
- [ ] No broken paths after reorganization
- [ ] Architecture decisions documented with rationale
- [ ] Integration patterns documented with examples
- [ ] Lessons learned captured after each sprint/phase

---

*Template v5.0.0 (Session 44 - Bootstrap Enforcement & Governance Consolidation)*
