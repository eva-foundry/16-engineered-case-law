# 16-engineered-case-law -- Implementation Status

**Last Updated**: 2026-03-03 by agent:copilot
**Data Model**: GET http://localhost:8010/model/projects/16-engineered-case-law
**Veritas Trust**: Run `get_trust_score` MCP tool for current MTI score

---

<!-- eva-primed-status -->

## EVA Ecosystem Live Status

Query these endpoints to get live project state before starting any work:

```powershell
$base = "http://localhost:8010"

# Project facts
Invoke-RestMethod "$base/model/projects/16-engineered-case-law" | Select-Object id, maturity, phase, pbi_total, pbi_done

# Health
Invoke-RestMethod "$base/health" | Select-Object status, store, version

# One-call summary (all layer counts)
Invoke-RestMethod "$base/model/agent-summary"
```

For 29-foundry agent assistance:
```python
import sys
from pathlib import Path
foundry_path = Path("C:/eva-foundry/eva-foundation/29-foundry")
sys.path.insert(0, str(foundry_path))
from tools.search import EVASearchClient
```

For veritas audit:
```
MCP tool: audit_repo  repo_path=C:\eva-foundry\16-engineered-case-law
MCP tool: get_trust_score  repo_path=C:\eva-foundry\16-engineered-case-law
```

---

## Session Log

### 2026-03-03 -- Initial Prime by agent:copilot

**Activity**: Project primed by foundation-primer workflow.
**Template**: copilot-instructions-template.md v3.1.0
**Governance docs created**: PLAN.md, STATUS.md, ACCEPTANCE.md, README (updated)
**Data model record**: http://localhost:8010/model/projects/16-engineered-case-law
**Veritas audit**: pending (run audit_repo to establish baseline)

---

## Test / Build State

> Update this section after each test run.

| Command | Status | Last Run |
|---------|--------|----------|
| (add project test command here) | PENDING | (date) |

---

## Blockers

> Log any blockers here with discovery date and resolution.

(none at prime time)

---

## Next Steps

1. Run veritas audit: `audit_repo` MCP tool, repo_path = C:\eva-foundry\16-engineered-case-law
2. Check data model record: GET /model/projects/16-engineered-case-law
3. Update PLAN.md with actual sprint stories
4. Fill ACCEPTANCE.md gate table with project-specific criteria
5. Commit first evidence: PUT /model/projects/16-engineered-case-law with updated notes
