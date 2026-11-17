# Club BankAccount listener precondition continuation

Owner requested continuation on17/11. Base47750dd, feature branch clean and synced. Continue the measured BankAccount NOT RUN item from session_club_auth_listener_runtime_20261116.md; AGY Gemini4Hydrogen(XHigh) implements, Codex reviews/runs local runtime, maximum3correction rounds then Codex repairs concrete residuals. No app/schema/remote/main merge/deploy/pilot/BH-08 or risk acceptance.

**Architecture:** Add a default-off `include_club_bank` opt-in to existing disposable instructions fixture/config. Persist UUID/synthetic account state before attempted atomic insertion, verify exact bank ownership/readback, delete owned bank child before club and verify absence plus unchanged baseline. Reuse existing Session/Club runner with --require-bank-account; no new scanner or runner framework. Existing default-off behavior/old private states and bundles remain compatible.

**AGY ownership:** scripts/bh07_appheap/disposable_instructions_fixture.py, focused tests in test_payment_instructions_heap.py (or one small dedicated fixture test file if needed), handoff docs/reviews/bh07/club_bank_listener_handoff_20261117.md. You are not alone; preserve others' edits. No other source files without a demonstrated need and handoff explanation.

- [x] Read actual bank schema/triggers and fixture/FakeDb contracts. Select synthetic bank values only, no payment/network/bank integration.
- [x] RED->GREEN controls: opt-in creation/state reload/readback, bank UUID collision, uncertain commit recovery, foreign bank ownership/reparenting/refusal, child-first cleanup/absence/baseline failure, malformed flag and old state/default-off compatibility. Never rely solely on FK cascade for bank absence or delete unowned rows.
- [x] Implement minimal optional fixture path in one transaction and CLI config handling. Public receipts expose hashes/booleans only for bank values. Keep actual canaries separate, no sensitive output.
- [x] Run focused Python fixture/legacy tests and existing Session/Club Node controls; handoff exact commands/results and runtime NOT RUN.
- [x] Codex reviews/tests, commits clean source and runs Edge two cycles/eight same-document epochs with include_club_bank=true and --require-bank-account. Require Owner BankAccount populated and null after logout, correct listener receiver, strict auditor with real build, zero payment mutations, complete fixture/profile/dump/state cleanup and independent root DB before/after receipt.
- [x] Publish separate dated evidence/report; preserve prior PARTIAL/FAIL bytes, update current status and sync feature. Any PASS remains bounded to selected fields, not full auth_listeners/V2b/BH-07/V8.

Use --print-timeout0. Per-session command permissions only for exact local Python/Node control commands. If denied, continue file-only and report; never bypass policy or change global settings.

**Outcome:** clean7614c6a required-bank RUN/PASS with strict auditor; controlled lock probe and root DB/cleanup verification passed. See ../../reviews/bh07/club_bank_listener_runtime_20261117.md. This closes only bounded selected fields, not full BH-07/V8.
