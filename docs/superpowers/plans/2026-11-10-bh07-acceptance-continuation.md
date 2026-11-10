# BH-07 Acceptance Continuation Implementation Plan

> **For agentic workers:** Anti CLI implements, Codex reviews. Use the existing supervised test-first workflow. Owner explicitly authorizes Codex to repair remaining findings after three Anti correction rounds. Do not infer permission to merge/deploy/pilot/BH-08 or sign risk acceptance.

**Goal:** Clear local technical failures and complete an evidence-backed BH-07/V8 decision using the existing acceptance rules.

**Architecture:** Preserve isolated, UUID-owned Docker rehearsal resources and strong snapshot/HTTP/restore/replay/cleanup predicates. Add safe stage diagnostics before choosing recovery fixes; classify V5b mocked commands by exact argument tokens. Inherited accepted core gates retain provenance; missing operational evidence remains NOT RUN until measured or individually accepted by the owner.

**Tech Stack:** Existing Python unittest/stdlib, PostgreSQL17 Docker, GoTrue, PostgREST, existing Flutter/Supabase application (unchanged unless a demonstrated in-scope defect requires repair).

**Spec:** `docs/reviews/bh07/bh07_readiness.md` §4.11; `docs/reviews/bh07/codex_bounded_runtime_review_20261110.md`; latest owner instruction recorded in AGENTS.md.

## Global Constraints

- Anti CLI `--print-timeout 0`, no interruption solely for elapsed time; review only after handoff.
- Anti implements; Codex reviews three correction rounds, then repairs remaining concrete findings under new standing authorization.
- Commands local to authorized work may run automatically within environment permissions; no permission bypass/global auto-approve policy changes.
- No weakening overlap, actual snapshot visibility, relational consistency, idempotency, privacy, ownership or verified cleanup.
- Keep historical evidence bytes and verdicts. No managed project/paid resources/production operation without their specific authorization.
- Core acceptance cannot be waived; unrun operational gates require actual evidence or a per-gate owner risk decision. Existing FAIL cannot be waived.

## Review Focus

- Substring command detection misidentifies workdirs as DB resets: deterministic path controls must discriminate exact tokens.
- Error diagnostics accidentally serialize secrets/command args: only predefined stage and command identity plus exit/type are permitted.
- Docker service startup dies before network/port lookup: record safe stage; never infer health from container creation alone.
- Restore rows/padding match does not prove final replay: retain full final relational/state receipts and fail incomplete runs.
- Missing staging/mobile/native evidence must remain explicit; no broad authorization substitutes for owner residual-risk decisions.

## Task 1: Deterministic V5b test command classification

**Files:** `tests/test_v5b_runner_flaws.py`; new Anti handoff under `docs/reviews/bh07/`.

**Interface:** Existing fake `command(args, **kwargs)` and final reset-call assertion recognize adjacent exact `db`, `reset` tokens; no production V5b changes.

- [x] Add controls for temp paths with `db`, `reset`, both, and neutral names; fake start/inventory must not count as reset.
- [x] Keep all inventory-error/missing-inventory rejection assertions and actual reset-boundary exception.
- [x] Codex runs22targeted V5b tests and full552suite (548PASS+4SKIP). Historical probe is immutable and incompatible with the updated prefix-taking harness;16new path/inventory subtests verify the same property without duplicate-prefix errors. [Review](../../reviews/bh07/recovery_diagnostics_review_after_r2_20261110.md).

## Task 2: Safe post-restore V4 diagnostics

**Files:** `scripts/bh07_backup/run_v4_concurrent_rehearsal.py`, `tests/test_bh07_v4_runtime_collection.py`, new handoff.

**Interface:** Summary retains a predefined execution stage and, on command failure, safe command identity/exit without arbitrary args/env/stdout/stderr. Failure stays FAIL and owned cleanup still runs.

- [x] Add main-orchestration failure controls for target Auth start, PostgREST start, network connect, port discovery and replay collection boundaries.
- [x] Record predefined stage before each boundary, preserve original error type and new safe metadata, never infer or hardcode a successful service.
- [x] Use secret markers in mocked args/stdout/stderr to prove publication exclusion. No raw CLI argument dumping. Reviewer controls reject free-text/unlisted/non-int and unhashable metadata after two corrections.
- [x] Codex review/targeted/full checks; clean candidate791bcf7 ran Docker and identified port_discovery; a read-only diagnostic wrapper then verified target Auth exited1 due missing SITE_URL. [Diagnosis](../../reviews/bh07/recovery_site_url_diagnosis_20261110.md).

## Task 3: Repair actual recovery failure

**Files:** Only the minimal runner/test/fixture files implicated by Task2 runtime, exact ownership assigned before edits.

- [x] Diagnose from new stage plus bounded service-health metadata; add regression for actual target env. Missing SITE_URL fix reviewed,53targeted PASS; root retrospective baseline replay1FAIL. [Review](../../reviews/bh07/recovery_site_url_review_20261110.md).
- [ ] Anti implements; Codex reviews and runs checks. After three corrections Codex directly repairs concrete residual findings under standing owner authorization.
- [ ] Run clean-source Docker and independent artifact review. Require final oracle/HTTP replay and cleanup, not just overlap or row counts.

## Task 4: Acceptance matrix and owner decision packet

**Files:** new current completion status/review and per-gate decision packet under `docs/reviews/bh07/`; current headers in AGENTS/docs00/docs09 and relevant entry points.

- [ ] Inventory available connected staging/mobile/browser/native tools without changing remote projects.
- [ ] Check accepted core links/SHAs and scope; preserve inherited counts rather than rerunning unrelated evidence.
- [ ] Execute feasible missing local checks. For unavailable operational gates, prepare concrete per-gate risk/mitigation/remaining-work entries for owner decision.
- [ ] Independently review V8 prerequisites. Mark complete only when every required acceptance condition is actually met; otherwise record exact outstanding environment/decision blockers, never sign for owner.
