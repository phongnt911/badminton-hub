# BH-07 local completion and acceptance review plan

> **For agentic workers:** Antigravity CLI implements; Codex independently reviews each handoff. Continue the user's selected two-AI workflow rather than replacing the implementer.

**Goal:** Complete authorized local BH-07 work and present a concrete V8 acceptance decision without inventing runtime results or owner risk acceptance.

**Architecture:** Preserve existing Flutter/Provider/Supabase behavior and the accepted evidence bundles. Reuse the current heap framework only where its measurement proves the claimed surface. Keep technical results separate from owner decisions and integration.

**Tech Stack:** Flutter/Dart, Python unittest, Node/CDP, existing local Docker/Supabase.

**Spec:** [BH-07 readiness, including V8 rules](../../reviews/bh07/bh07_readiness.md), [accepted bank scope](../../reviews/bh07/bank_receiver_heap_final_review.md), [coverage map](../../reviews/bh07/v2b_coverage_map.md).

## Global constraints

- User authorized Antigravity implementation and Codex review until BH-07 completion; user confirmed no staging project or Android/iOS test device is available.
- Base `e994b06a1752e6301d8733aa084d675fde7a877c`; work on `feat/bh07-completion-local`. Preserve the original feature branch and main.
- No main merge, push, deployment, production change, pilot, new dependency or risk waiver is inferred from this task.
- Preserve historical evidence bytes and tested-source attribution. Fresh checks must identify their actual source and environment.
- Core A/B/C/D, HTTP/Auth, HTTP concurrency, V1 and R0 retain their historical acceptance unless new evidence invalidates it.
- V6 remains outside scope. V2/V2b/V3/V4/V5/V7 cannot become PASS through documentation alone; V8 requires the existing per-gate evidence/owner-decision rules.
- Anti headless currently permits file work but denies general commands. Codex runs commands and identifies those results as Codex checks, not implementer self-checks.

## Review focus

- Windows ANSI decoding must not corrupt Node UTF-8 output; retain strict Unicode assertions and strict decoding errors.
- Do not weaken privacy, reachability, fixture ownership or cleanup gates to obtain a green result.
- A shared identity or active-revision ID does not prove release of one exclusive financial object.
- Rendered retained text remains an unattributed risk; one root path cannot establish an engine-only cause.
- A missing environment or unsigned risk decision must remain explicit in V8, and preparation does not authorize integration.

## Task 1: Restore the default Windows Python baseline

**Files:** `tests/test_bh07_app_heap_build_guard.py`, `tests/test_bh07_bank_navigation_cleanup.py`.

**Interface:** Existing `run_node` and `run_open_owner_bank_harness`; preserve their arguments/results and add explicit UTF-8 subprocess decoding.

- [x] Reproduce default-environment failure: 375 tests, one failure and three errors; archive `33216b2726738ee1`.
- [x] Isolate encoding hypothesis: unchanged source passes 375 tests with `PYTHONUTF8=1`; archive `dca1d55ca819597d`.
- [x] Anti makes the minimal helper changes; no assertion or app change.
- [x] Codex inspects the complete diff and runs both modules, then `python -m unittest discover -s tests` without UTF-8 environment overrides: 20 targeted / 375 full PASS.
- [x] Record actual analyze/test evidence and an independent scoped review; code committed as `51a6eda`, [review](../../reviews/bh07/review_51a6eda.md).

## Task 2: Determine the next valid V2b measurement

**Resumed 08/11/2026:** The owner opened the Supabase skill directory; Codex successfully read it and checked current documentation. Anti CLI now owns the bounded ledger helper/runner/auditor and restored test modules. This grants no risk waiver or integration/deployment approval. Independent read-only local preflight passed for all six preserved tables, including `club_transactions` (archive `ed7688e2d8860a38`); no runtime fixture or browser measurement has run in this continuation yet.

**Potential files:** Existing heap runner, oracle, evidence auditor, disposable fixture helper and focused tests; exact implementation scope must follow source inspection.

- [x] Anti proposes a minimal ledger `transaction_id` measurement; Codex corrects the actual auditor path and automatic manual-dialog cancellation. Test design remains RED and unaccepted; see [checkpoint](../../reviews/bh07/ledger_tdd_draft/README.md).
- [x] Establish which PaymentInstructions fields are exclusive and which are rendered/shared: no exclusive ID; native/whole-object release cannot be claimed from the shared IDs or rendered reference.
- [x] Codex reviews the proposal against actual DTO, UI and fixture contracts before delegating implementation.
- [x] Implement and review a feasible bounded extension, or record the concrete prerequisite/blocker. Never treat a design as runtime evidence. Ledger sentinel extension accepted at `b25aaef`; other V2b gaps remain open.

Tooling portion accepted at `205dcd5` after LGR1–LGR8 closure: 420 Python PASS, fixture8/8, oracle34/34; [review](../../reviews/bh07/review_205dcd5.md). Fresh real-runtime measurement is still pending, so Task 2 is not complete.

**Runtime attempt completed, not accepted:** clean source `a2efc1e`, child/auditor exit 1, baseline scan abort, zero cycles. Independent checks confirm six tables preserved, fixture IDs absent, dumps/profile removed and 1,961 protected files unchanged. LGR9/LGR10 P2 remain; scan root cause UNKNOWN. Stop source corrections after the exhausted two rounds under AGENTS; owner decision required before an additional correction round. See [runtime review](../../reviews/bh07/review_a2efc1e_ledger_runtime.md). Task 2 remains incomplete.

**Owner authorization after runtime review:** Open correction round 3/3 for LGR9/LGR10 and baseline scan diagnosis. General AGENTS limit updated from two to three correction rounds. Anti CLI owns focused tooling/test edits; Codex verifies and independently reviews. Earlier two-round stop remains historical; no runtime PASS or operational risk waiver is implied.

**Round 3 outcome:** candidate `c427e27` is not accepted. LGR9 diagnostic wiring added; LGR10 remains open through LGR11 P2 (unguarded directory enumeration interrupts later DB cleanup). A fresh about:blank Chrome156/V8 15.6 probe confirms LGR12 P1 (scope tables rejected by current oracle); no app/DB runtime and no app leak conclusion. Stop after three rounds under the owner-updated AGENTS rule; no automatic round4. See [review](../../reviews/bh07/review_c427e27_ledger_round3.md).

**Supplemental owner-authorized Codex repair completed:** Owner said “codex tự sửa”. LGR11/LGR12 fixed with RED2→GREEN17 targeted controls, full437Python PASS. Clean-source runtime `b25aaef` RUN/PASS, child/auditor0, two cycles/eight epochs, ledger ID loaded/reachable for Owner and absent/unreachable after logout/actor; DB/protected hashes unchanged, fixtures/dumps/profiles removed. Independent source/artifact reviewer accepts bounded local sentinel scope (not independent runtime QA); [final review](../../reviews/bh07/review_b25aaef_ledger_final.md). Task 2 bounded ledger extension is complete; whole V2b/BH-07/V8 remains open. General max3-round rule unchanged; supplemental authorization is specific.

## Task 3: Reconcile current readiness and present V8 decision

**Files:** Current-status sections of `AGENTS.md`, `README.md`, `docs/00_START_HERE.md`, `docs/09_IMPLEMENTATION_PLAN.md`, `docs/reviews/bh07/bh07_readiness.md`; a new completion review/decision draft under `docs/reviews/bh07/`.

- [x] Codex reconciles latest accepted finance/bank results in current-status headers and a linked status matrix; a separate reviewer verified the new links, SHAs and claims. Historical sections remain unchanged.
- [x] Record unavailable staging/mobile/native and other incomplete technical gates separately; [per-gate risk draft](../../reviews/bh07/bh07_v8_risk_decision_draft.md) independently reviewed, explicitly unapproved.
- [ ] Codex checks referenced paths, SHAs, statuses, diff scope and relevant test output.
- [ ] Decide V8 using the existing rules. If owner decisions are still absent, report BH-07 unaccepted and present the exact remaining decision, without signing for the owner.

## Integration boundary

The previously prepared 59-file main tooling package remains a separate pinned candidate. This continuation neither refreshes its hashes implicitly nor approves the inherited application branch for merge.
