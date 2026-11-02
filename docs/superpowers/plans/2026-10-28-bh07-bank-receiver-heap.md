**Completed locally 2026-11-02:** source a095a45, RUN/PASS and independent auditor0; owner integration decision remains pending. [Final review](../../reviews/bh07/bank_receiver_heap_final_review.md). No merge/push or next task.

# BH-07 Bank/Receiver Heap Coverage Implementation Plan

> For agentic workers: Antigravity is the implementation worker, exclusively Gemini 3.8 Flash (High); Codex coordinates and independently reviews. Execute the following steps in order; do not spawn another implementer or substitute a model.

**Goal:** Add an opt-in, fail-closed bank/receiver coverage profile without changing app/backend.
**Architecture:** Reuse existing runner, oracle, auditor and fixture ownership patterns, with a disposable club/account and an explicit required coverage contract.
**Tech stack:** Existing Node built-ins, Python unittest, Flutter Web profile/CDP and local Supabase fixtures; no new dependencies.
**Spec:** ../specs/2026-10-28-bh07-bank-receiver-heap-design.md
**Baseline:** 94fd997 on feat/bh07-bank-receiver-heap; inherited tooling source 511ce61, runtime history cd25e1e. Baseline suites freshly passed: 331 Python, analyze0, 247 Flutter +1skip, fixture8/8.

## Constraints and review focus

Only scripts/bh07_appheap/, new/related Python tests, bank-specific controls and docs may change. Do not overwrite old evidence or modify app/backend/config. Preserve ownership under ID collision, lost POST acknowledgement and delete failure; distinguish rendered strings from unrendered IDs; reject missing/contradictory bank contract metadata; preserve payment gates and legacy audit; redact every publication field and fixture cleanup error.

### Task 1: Implement profile and controls

- [x] Read the spec and inspect the real schema/UI; use actual existing test paths under tests/, not the nonexistent tests/scripts/... proposed during reconnaissance.
- [x] Add failing controls in tests/test_bh07_bank_heap_coverage.py and an appropriate bank fixture control file under scripts/bh07_appheap/. Cover: positive, missing Owner load, baseline collision, retained unrendered bank ID, dropped required metadata, forged rendered/scope flags, missing cleanup, wrong receipt hash, pre-existing club/bank ID collision, partial creation, lost POST response, delete error, child-first cleanup, and rendered residual risk attribution.
- [x] Implement the minimal opt-in `--bank-coverage` runner path and disposable fixture helper. Use actual bank UI semantic labels and exact disposable club selection. Include path/metadata publication sanitization and a separate fresh bank_receiver_heap_evidence output; never reuse the default evidence directory for this profile.
- [x] Extend oracle/auditor only enough to enforce the versioned bank contract and matched cleanup receipts. Default legacy behavior and FH1–FH4 gates must remain.
- [x] Return a concise handoff with changed files, exact test commands, any blockers and observed failures; do not claim tests you could not run. Only flutter analyze/test are currently preallowed shell actions for Antigravity. Other checks are run by Codex; do not request new permissions or route through alternative tools to evade denial.

### Task 2: Independent review and local runtime

- [x] Codex reviews implementation diff and runs targeted/full Python tests, fixture controls, analyze/test and old evidence auditors with readonly hash checks.
- [x] Codex reports all P0/P1/P2 together; Antigravity fixes under the user's three-round exception followed by the explicitly authorized fourth correction round on 2026-11-02; see the round-four authorization and final review. Codex does not rewrite implementation. Other tasks retain the repository's two-round default.
- [x] After tooling review permits runtime, preserve a clean local feature-source checkpoint and run the explicit bank profile locally. Verify fresh served build, 2 actors ×4 same-document epochs, bank Owner load/baseline controls, unrendered ID absence, rendered residual risks and exact fixture absence. No credential output.
- [x] Independently audit the fresh evidence and preserve all historical bundle bytes. If app behavior fails the new gate, stop and report; do not silently expand into app fixes.

### Task 3: Close and request integration

- [x] Antigravity prepares bank-specific handoff/coverage map with accurate source hashes and NOT RUN boundaries; Codex writes final review and updates entrypoints.
- [x] Report the concrete result and ask the user before integration/merge main. Do not start another task automatically.
