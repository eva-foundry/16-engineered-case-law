<!-- foundation-memory-checkpoint -->
# [16-engineered-case-law] Agent Wake-Up Checkpoint

**Generated**: 2026-03-15 00:29:17 UTC
**Purpose**: Local continuity aid only. Governance truth lives in the Data Model API.
**Authoritative State**: https://msub-eva-data-model.victoriousgrass-30debbd3.canadacentral.azurecontainerapps.io

## Wake-Up Order

1. Load workspace and project governance files.
2. Bootstrap session.guide and session.userGuide from the API.
3. Query authoritative project state from projects, project_work, sprints, and evidence.
4. Read local continuity notes in .memories/session/.
5. Reconcile conflicts by trusting API state over local notes.
6. Start the next D3PDCA loop with explicit scope and evidence targets.

## Governance Refresh

    $workspacePolicies = Get-Content ".github/copilot-instructions.md" -Raw
    $projectPlan = Get-Content "PLAN.md" -Raw -ErrorAction SilentlyContinue
    $projectStatus = Get-Content "STATUS.md" -Raw -ErrorAction SilentlyContinue

## API Bootstrap

    $base = "https://msub-eva-data-model.victoriousgrass-30debbd3.canadacentral.azurecontainerapps.io"
    $health = Invoke-RestMethod "https://msub-eva-data-model.victoriousgrass-30debbd3.canadacentral.azurecontainerapps.io/health" -TimeoutSec 10
    $session = @{
        base = $base
        initialized_at = Get-Date
        guide = Invoke-RestMethod "https://msub-eva-data-model.victoriousgrass-30debbd3.canadacentral.azurecontainerapps.io/model/agent-guide" -TimeoutSec 10
        userGuide = Invoke-RestMethod "https://msub-eva-data-model.victoriousgrass-30debbd3.canadacentral.azurecontainerapps.io/model/user-guide" -TimeoutSec 10
    }

## Authoritative Queries

    $project = Invoke-RestMethod "https://msub-eva-data-model.victoriousgrass-30debbd3.canadacentral.azurecontainerapps.io/model/projects/16-engineered-case-law"
    $projectWork = Invoke-RestMethod "https://msub-eva-data-model.victoriousgrass-30debbd3.canadacentral.azurecontainerapps.io/model/project_work/?project_id=16-engineered-case-law"
    $sprints = Invoke-RestMethod "https://msub-eva-data-model.victoriousgrass-30debbd3.canadacentral.azurecontainerapps.io/model/sprints/?project_id=16-engineered-case-law"
    $evidence = Invoke-RestMethod "https://msub-eva-data-model.victoriousgrass-30debbd3.canadacentral.azurecontainerapps.io/model/evidence/?project_id=16-engineered-case-law"

## Local Continuity Rules

- Local files in .memories/session/ are prompts for fast recovery, not sources of truth.
- Do not create or update sprint_N_config.json here.
- Do not persist project_work, sprint, or evidence truth locally.
- If local notes disagree with the API, update the local note after confirming the API record.

## WS06 Learning Loop

- Emit execution events and lessons as immutable evidence in the API workflow, not as hidden local truth.
- Record local observations only as short handoff notes for the next agent wake-up.
- Promote stable patterns into shared memory or Foundation docs after validation.

## Session Opening Checklist

- [ ] Governance files loaded
- [ ] API health verified
- [ ] agent-guide and user-guide loaded
- [ ] Project state queried from API
- [ ] Local continuity notes reviewed
- [ ] Next D3PDCA scope defined

## Suggested Local Files

- phase-1-kickoff-checkpoint.md
- phase-1-blockers.md
- phase-1-handoff-summary.md

**Status**: [PASS] READY FOR AGENT WAKE-UP
