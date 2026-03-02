This is a 4-phase wrapper:

1. **Pre-flight Quality Gate** (static + contract checks)
2. **Flight Runbook** (controlled execution + acceptance criteria)
3. **The payload** 
	**PAYLOAD START**
	* Context: …
	* Goal: …
	* Files: …
	* Constraints: …
	* Success criteria: …
	* Make changes using the Pre-flight gate + Flight runbook below.
	* Output: diff/patch + Gate Report + Run Report + Evidence paths.
	**PAYLOAD END**
4. **Post-flight Audit Miner** (turn failures into permanent gate rules)


How to run it:
1. Run Pre-flight Quality Gate (A–E hard fail; F/G per policy).
	a. Output Gate Report + unified diff/patch (no invisible edits).
2. Run Flight Runbook: snapshot → smoke → real run → validate outputs.
	a. Output Run Report with acceptance criteria results + evidence paths.
3. Run Post-flight Audit Miner: extract events → promote rules → update gate list.



---

# 1) Pre-flight Quality Gate

## 1.1 Inputs (must be provided by the assistant)

* **Target artifact(s):** file paths it will touch
* **Intent:** what it’s trying to change (one paragraph)
* **Constraints:** platform (Windows-only vs cross-platform), PowerShell version, required tools (az, git, etc.)
* **Evidence folder:** where outputs/logs will be written (timestamped)

## 1.2 “No Invisible Edits” rule (non-negotiable)

If the assistant proposes modifications, it must output **one** of:

* **Unified diff** (preferred)
* **Full rewritten file content**
* **Patch file** in `git apply` format

If it cannot produce a diff/content, **the step fails** and must not proceed to execution.

## 1.3 Static checks (PowerShell example)

### Gate A — Syntax & parse (hard fail)

**Pass condition:** 0 parse errors.

* PSParser tokenize errors count == 0

### Gate B — Lint & style (hard fail unless waived)

**Pass condition:** `Invoke-ScriptAnalyzer` has **0 Errors**, and **0 Warnings** unless explicitly waived with rationale.

### Gate C — External command safety (hard fail)

For each native command call (`az`, `git`, `curl`, etc.), one of:

* A wrapper function is used (e.g., `Invoke-Native`, `Invoke-AzJson`)
* Or `$LASTEXITCODE` is checked immediately after the call with fail-fast behavior

**Pass condition:** no raw native calls without exit-code handling.

### Gate D — Output parsing robustness (hard fail)

If command output is parsed:

* Prefer JSON output (`--output json`) and parse via `ConvertFrom-Json`
* Validate non-empty output and expected shape

**Pass condition:** no fragile parsing of human text when machine output exists.

### Gate E — Path determinism (hard fail)

* Use `Join-Path`, `Resolve-Path`, `Split-Path`
* No hard-coded separators unless Windows-only is declared

**Pass condition:** script runs regardless of working directory (or explicitly declares it requires one).

### Gate F — Markdown / report integrity (soft or hard depending on your choice)

If script generates Markdown:

* Code fences are emitted as **three backticks** in the output file
* Tables are consistent
* No nested-fence ambiguity

**Pass condition:** report generation cannot break due to accidental fence termination.

### Gate G — Performance guard (soft by default)

If building large strings:

* Use `StringBuilder` or arrays + `-join` for large outputs

**Pass condition:** no obvious O(n²) concatenation patterns in large loops.

## 1.4 Pre-flight Gate Report (required output format)

The assistant must produce this every time:

* **Files in scope:** …
* **Edits mode:** (diff | full file | patch)
* **Gate results:**

  * A Syntax: PASS/FAIL + evidence
  * B ScriptAnalyzer: PASS/FAIL + evidence
  * C Native command handling: PASS/FAIL + evidence
  * D Parsing robustness: PASS/FAIL + evidence
  * E Paths: PASS/FAIL + evidence
  * F Markdown integrity: PASS/FAIL + evidence
  * G Performance: PASS/FAIL + evidence
* **If FAIL:** Minimal patch plan (what exactly changes)
* **If PASS:** Go/no-go = GO

### Pre-flight Acceptance Criteria

* ✅ Every gate A–E is PASS (F/G per your policy)
* ✅ Changes are visible (diff/full content/patch)
* ✅ Evidence artifacts are named + timestamped

---

# 2) Flight Runbook

This is the “controlled execution” phase. It forces the assistant to stop claiming “95% confidence” and instead produce **observable results**.

## 2.1 Run conditions (declared up front)

* **Shell:** `pwsh` version
* **Working directory:** declared (and why)
* **Authentication prerequisites:** e.g., `az login`, subscription set, tenant
* **Dry-run mode:** if supported, define it (`-WhatIf` or `-DryRun`)

## 2.2 Execution steps (template)

### Step 0 — Create run folder (timestamped)

* `evidence/run-YYYYMMDD-HHMMSS/`
* Store: command transcript, environment snapshot, outputs

### Step 1 — Environment snapshot

Capture:

* `pwsh --version`
* `az version`
* `az account show` (redact if needed)
* `Get-Location`
* Key env vars used by script (names only if sensitive)

### Step 2 — Smoke run (no side effects)

* Run with `-WhatIf` / dry-run if available
* Or run in “read-only” mode (verification only)
* Capture stdout/stderr to file

### Step 3 — Real run (if smoke passes)

* Run actual command
* Capture stdout/stderr to file
* Ensure exit code is checked

### Step 4 — Validate outputs

* Confirm expected output files exist
* Validate markdown file renders (simple checks: code fences balanced, required headings present)
* Validate key sections present

## 2.3 Flight Acceptance Criteria (example, customize per script)

**AC-1 Execution success**

* Script returns exit code 0
* No unhandled exceptions
* No “ERROR:” markers in log (unless explicitly expected)

**AC-2 Evidence produced**

* Evidence folder created
* Expected output artifact(s) exist (e.g., verification report)
* Output contains required sections (e.g., Summary / Findings / Next steps)

**AC-3 Deterministic behavior**

* Running twice with same inputs produces:

  * same structure of outputs
  * same checks executed
  * no dependence on current working directory (unless declared)

**AC-4 Failure clarity**

* If something fails, the log includes:

  * the failing command
  * exit code
  * captured stderr
  * a single-line remediation hint

## 2.4 Flight Run Report (required)

Assistant must output:

* Commands run (copy/paste exact)
* Pass/fail against each AC
* Links/paths to evidence artifacts

---

# 3) The Payload
	**PAYLOAD START**
	* Context: …
	* Goal: …
	* Files: …
	* Constraints: …
	* Success criteria: …
	* Make changes using the Pre-flight gate + Flight runbook below.
	* Output: diff/patch + Gate Report + Run Report + Evidence paths.
	**PAYLOAD END**

---

# 4) Post-flight Audit Miner

This is where your process becomes self-hardening.

## 4.1 Inputs

* Pre-flight Gate Report
* Flight logs (stdout/stderr)
* Produced artifacts (reports)
* Any manual notes (“what surprised me”)

## 4.2 Normalize logs into “events”

Parse the run logs into structured event types:

* `SyntaxError` (line, message)
* `NativeCommandFailed` (cmd, exit code, stderr excerpt)
* `AzEmptyOutput` (cmd, expected output missing)
* `JsonParseFailed` (cmd/output, exception)
* `PathResolutionFailed` (path, working dir)
* `MarkdownIntegrityFailed` (unbalanced fences, broken table)
* `TimeoutOrSlowStep` (step name, duration)
* `UnexpectedDependency` (missing module/tool/version mismatch)

## 4.3 Event → Rule promotion (the learning loop)

A deterministic promotion policy:

* If an event occurs **once**: create a **watch item**
* If an event occurs **twice**: promote to a **new gate rule**
* If an event occurs **3+ times**: require a **wrapper function/pattern** and block raw usage

Each promoted rule must include:

* **Rule statement**
* **Detection method** (how to catch it pre-flight)
* **Preferred fix pattern** (snippet or wrapper)
* **Test** (micro-check to confirm)

## 4.4 Post-flight outputs (required)

* **Audit Summary:** top events + root causes
* **New/updated gate rules:** (with detection + fix pattern)
* **Backlog items:** stories/tasks created from recurring issues
* **Process delta:** what changes in the template next run

## 4.5 Post-flight Acceptance Criteria

* ✅ Every failure mode is captured as an event
* ✅ At least 1 concrete gate improvement identified (if any issues occurred)
* ✅ The next run would prevent the same issue earlier (“shift-left proof”)

---


1. Run Pre-flight Quality Gate (A–E hard fail; F/G per policy).
2. Output Gate Report + unified diff/patch (no invisible edits).
3. Run Flight Runbook: snapshot → smoke → real run → validate outputs.
4. Output Run Report with acceptance criteria results + evidence paths.
5. Run Post-flight Audit Miner: extract events → promote rules → update gate list.

