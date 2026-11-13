# Handoff: BH-07 V2b PaymentInstructions Synthetic `receiverSnapshot` Heap Tooling (Task 1, Round 2)

- **Date:** 2026-11-13
- **Role:** Antigravity (Task 1 companion tooling & correction round 2)
- **Plan:** [2026-11-13-bh07-instructions-heap.md](../../superpowers/plans/2026-11-13-bh07-instructions-heap.md)
- **Feasibility spec:** [payment_instructions_heap_feasibility_20261113.md](payment_instructions_heap_feasibility_20261113.md)
- **Review basis:** [payment_instructions_heap_review_r1_20261113.md](payment_instructions_heap_review_r1_20261113.md) (left untouched)
- **Runtime / Browser / DB / Docker status:** **NOT RUN** (implementation & pure unit/control verification only; no runtime `PASS` claimed).

## 1. Owned Deliverables (6 Files Only)

1. `scripts/bh07_appheap/disposable_instructions_fixture.py` — Isolated disposable private-club (`clubs`, `club_members`), unlisted completed session (`sessions` with two synthetic non-rendered UUIDv4 values in `receiver_snapshot.canary_instr_a` and `canary_instr_b`), unpaid confirmed guest `session_players` (`user_id = NULL`), active `charge_revisions` matching `sessions.billing_input_version`, and `session_charges` (`amount_due_vnd = 100000`). Enforces outside-repo non-symlink `--state` validation, exclusive pre-INSERT recovery file write + atomic updates, missing/empty/malformed baseline fail-closed receipt (while still cleaning owned rows), Auth sequence scoping allowing ONLY `auth.refresh_tokens_id_seq.last_value` + Auth rows to differ, and `finalize_cli_cleanup` failing closed (exit `1`, `recovery_state_retained: true`, `recovery_state_error`) if state unlinking fails after DB cleanup.
2. `scripts/bh07_appheap/run_payment_instructions_heap.js` — Companion CDP heap runner reusing `CdpClient` from `scripts/bh07_browser/run_browser_verification.js`, `build_guard.js`, `owned_browser_cleanup.js`, and `heap_oracle.py`. Measures **2 cycles x 4 epochs (`baseline`, `owner_active`, `post_logout`, `post_actor` — 8 epochs total)** in one same-document browser session (`runMeasurement` + `main`). Round 2 fixes:
   - **IH5 P2 (`finalizeRunResources` + `buildCleanupSummary`):** Successful cleanup now requires `recovery_state_retained === false` and no `recovery_state_error`. If DB cleanup succeeds but `unlinkSync(statePath)` fails, raw dumps are still deleted, `statePath` stays on disk, `recovery_state_retained` is `true`, sanitized `recovery_state_error` is recorded (no raw canaries), `cleanup.ok` is `false`, and run verdict is `FAIL`. Failed DB cleanup retains `statePath` and fails as before.
   - **`origin0` scope & post-cycle failure safety:** Hoisted `let origin0 = null` before `try` and replaced the `finally` out-of-scope reference with `computeSameDocumentAcrossCycles(summary.cycles, origin0)`, so failures before or after cycles complete (including before attribution) write a `FAIL` summary and cleanup receipt instead of throwing `ReferenceError`.
   - **Progressive cycle evidence & fail-closed incomplete gate:** Each cycle entry (`cycle`, `actor`, `epochs: {}`, `verdict: FAIL incomplete`) is appended to `summary.cycles` before work and updated as each epoch finishes (`baseline`, `owner_active`, `post_logout`, `post_actor`), preserving already-measured epochs and sanitized `failure.stage` / `failure.epoch` on mid-cycle aborts without raw DOM, canary, or receiver values. Incomplete cycles are forced `FAIL` (including `attribution_assessment.scoped_verdict = 'FAIL'`).
   - **Startup semantics placeholder inspection & pre-wait (`waitForFlutterSemanticsReady` + `waitForStartupAndGuestBaseline`):** Inspected `CdpClient.waitForSemantic` in `scripts/bh07_browser/run_browser_verification.js` — it calls `findSemantic` -> `getAllSemantics` -> `enableFlutterSemantics()` (clicking `flt-semantics-placeholder` and waiting 1s per poll). Added a bounded pre-wait for `flt-semantics-placeholder` / `flt-semantics-host` before calling `waitForSemantic(..., 'Guest baseline UI', 30000)` to avoid wasted early clicks and separate startup placeholder failures from Guest baseline UI assertions without relaxing the UI spec.
3. `scripts/bh07_appheap/verify_payment_instructions_heap.py` — Offline fail-closed auditor (`--dir`, optional `--require-dto-attribution`) requiring `same_document_across_cycles=True`, unconditional cross-cycle + per-epoch `time_origin` equality across exact unique cycles `{1: 'cohost', 2: 'member'}` and exact 4 epochs (`baseline`, `owner_active`, `post_logout`, `post_actor`), strict `heap_oracle.py` PASS, `cleanup.recovery_state_retained is False` and absent `recovery_state_error`, zero-mutation/baseline equality receipts, and strict ordered DTO property-edge validation (`_finance_provider$_instructions` -> `receiverSnapshot` -> map -> string leaf).
4. `scripts/bh07_appheap/test_payment_instructions_heap.py` — Pure Python unit, mutant, and positive control tests (19 tests total) covering IH3, IH4, IH5 (including `recovery_state_retained`/`recovery_state_error` verifier rejection and `finalize_cli_cleanup` failed-unlink vs failed-DB behavior), IH6, fixture lifecycle, and oracle/verifier gates.
5. `scripts/bh07_appheap/instructions_heap_controls.js` — Pure Node controls (8 checks total) covering IH1, IH2, IH4, IH5 (`ih5_cleanup_unlink_failure_vs_db_failure`), post-cycle + mid-cycle partial `runMeasurement` failure robustness (`run_measurement_post_cycles_failure_and_partial_cycle_evidence`), startup semantics placeholder pre-wait (`startup_semantics_placeholder_prewait`), config guards, canary injection blocks, and served build verification.
6. `docs/reviews/bh07/payment_instructions_heap_handoff_20261113.md` — This handoff document.

Untouched shared assets preserved as-is: `heap_oracle.py`, `verify_evidence.py`, `run_app_profile_heap.js`, `lib/**`, `supabase/**`, existing evidence bundles, `docs/reviews/bh07/payment_instructions_heap_review_r1_20261113.md`, and the running `http://127.0.0.1:8088` server.

## 2. Pure Unit / Control Results Observed

Observed final runs after all Round 2 code edits:

- `node scripts/bh07_appheap/instructions_heap_controls.js` -> **exit 0, `controls: 8/8 passed`** (`config_rejects_non_loopback_or_wrong_container_and_bad_dumps_cap`, `canary_never_in_evaluate_or_insert_text`, `served_build_verification_full_match_and_mismatch`, `snapshot_streaming_outside_repo_cap_and_write_error`, `owner_precondition_and_attribution_and_raw_leak`, `ih5_cleanup_unlink_failure_vs_db_failure`, `run_measurement_post_cycles_failure_and_partial_cycle_evidence`, `startup_semantics_placeholder_prewait`).
- `python -m unittest scripts.bh07_appheap.test_payment_instructions_heap` -> **exit 0, `Ran 19 tests in 15.005s`, `OK`** (17 existing tests + `test_mutant_recovery_state_retained_or_error_fails_verifier` + `test_cli_cleanup_unlink_failure_vs_db_failure`).
- Prior RED check before production fixes confirmed new tests failed on old code (`controls: 5/8 passed`; Python `Ran 19 tests ... FAILED (failures=1, errors=1)`).

## 3. Private Local Config Example (With Placeholders)

Store this outside published evidence (for example `%TEMP%\bh07_instr_private_config.json`) and never commit real credentials:

```json
{
  "docker_exe": "docker",
  "db_container": "bh07-android-db",
  "supabase_url": "http://127.0.0.1:54321",
  "supabase_anon_key": "<SUPABASE_LOCAL_ANON_KEY>",
  "web_url": "http://127.0.0.1:8088",
  "reuse_existing_server": true,
  "provenance_path": "<ABS_PATH_TO_OUTSIDE_REPO_BUILD_PROVENANCE_JSON>",
  "browser_exe": "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  "debug_port": 9338,
  "dumps_dir": "C:\\Users\\<USER>\\AppData\\Local\\Temp\\bh07_instr_dumps_<UNIQUE_RUN_ID>",
  "state_path": "C:\\Users\\<USER>\\AppData\\Local\\Temp\\bh07_instr_recovery\\state_<UNIQUE_RUN_ID>.json",
  "max_snapshot_bytes": 536870912,
  "out_dir": "C:\\Users\\<USER>\\Documents\\GitHub\\badminton-hub\\docs\\reviews\\bh07\\payment_instructions_heap_evidence",
  "owner_email": "<OWNER_EMAIL>",
  "owner_password": "<OWNER_PASSWORD>",
  "cohost_email": "<COHOST_EMAIL>",
  "cohost_password": "<COHOST_PASSWORD>",
  "member_email": "<MEMBER_EMAIL>",
  "member_password": "<MEMBER_PASSWORD>"
}
```

Notes:
- `dumps_dir` (optional; auto-generated unique temp dir if omitted) **must not already exist**, must be outside the repo, must not be a root/repo-ancestor, and must not traverse symlinks/junctions. The runner atomically claims it with an ownership token before use and verifies both canonical path and token before deleting it.
- `state_path` (optional; auto-generated outside both repo and `dumps_dir` if omitted) must be strictly outside both the repo and `dumps_dir`. If DB cleanup fails, raw snapshot dumps are still deleted while the private `state_path` file is preserved for recovery IDs.
- `max_snapshot_bytes` must be a positive safe integer `<= 536870912` (512 MiB).
- `provenance_path` JSON must supply `{ "mode": "profile", "tested_source_sha": "<40-char-sha>", "started_at": "<iso8601>", "artifacts": { ... } }` matching every file hashed in `build/web/` and served by `http://127.0.0.1:8088`.
- `db_container` is pinned strictly to `bh07-android-db`, and `supabase_url` is pinned strictly to loopback port `54321`. No `npx supabase status` is executed.

## 4. Actual 8-Epoch Measurement Contract & Attribution Boundaries

Per cycle (`1: cohost`, `2: member`), the runner executes and captures exactly 4 epochs:
1. `baseline` — Guest baseline before actor login (probe present; `canary_instr_a`/`canary_instr_b` absent & unreachable).
2. `owner_active` — Owner logs in, triggers `get_payment_instructions` via `Thu tiền mặt`, opens cash dialog, cancels via `Huỷ` with zero DB payment/ledger/audit/operation mutation (`canary_instr_a` & `canary_instr_b` both present & root-reachable).
3. `post_logout` — Owner logs out (`canary_instr_a` & `canary_instr_b` absent & unreachable).
4. `post_actor` — `cohost` (cycle 1, opening `Tổng kết buổi`) or `member` (cycle 2, opening `Lịch sử buổi`) (`canary_instr_a` & `canary_instr_b` absent & unreachable).

Attribution & verdict rule:
- To prove DTO-level attribution (`dto_attribution_proven = true`, `scoped_verdict = PASS_DTO_ATTRIBUTED`, `payment_instructions_coverage_gate = PASS`), all 4 `owner_active` paths must contain an un-truncated, ordered `property` edge chain starting from `'root'` through `property:_finance_provider$_instructions -> object` immediately to `property:receiverSnapshot -> object` and non-string map edges to the leaf `string`/`concatenated string`/`sliced string` node (rejecting XHR/string/script labels, non-`property` edges, reverse order, fragments, or `...` truncation).
- If `heap_oracle.py` (which stays untouched) cannot emit that ordered property chain under `main.dart.js` compilation/minification or frame truncation, `dto_attribution_proven` stays `false`, `scoped_verdict` stays `PASS_NARROW_RPC_PAYLOAD_ONLY`, and `payment_instructions_coverage_gate` stays `UNKNOWN/NOT_RUN`. `--require-dto-attribution` on the verifier fails closed (`exit 1`) in that state.

## 5. Root Runtime & Verification CLI Commands (For Root Execution Only)

1. Optional standalone fixture lifecycle check:
```powershell
python -X utf8 scripts/bh07_appheap/disposable_instructions_fixture.py create --config <PRIVATE_CONFIG_JSON> --state <PRIVATE_STATE_JSON_OUTSIDE_REPO>
python -X utf8 scripts/bh07_appheap/disposable_instructions_fixture.py check --config <PRIVATE_CONFIG_JSON> --state <PRIVATE_STATE_JSON_OUTSIDE_REPO>
python -X utf8 scripts/bh07_appheap/disposable_instructions_fixture.py cleanup --config <PRIVATE_CONFIG_JSON> --state <PRIVATE_STATE_JSON_OUTSIDE_REPO>
```

2. End-to-end 2-cycle / 8-epoch CDP heap measurement:
```powershell
node scripts/bh07_appheap/run_payment_instructions_heap.js --config <PRIVATE_CONFIG_JSON> --out docs/reviews/bh07/payment_instructions_heap_evidence
```

3. Offline fail-closed audit:
```powershell
python -X utf8 scripts/bh07_appheap/verify_payment_instructions_heap.py --dir docs/reviews/bh07/payment_instructions_heap_evidence
python -X utf8 scripts/bh07_appheap/verify_payment_instructions_heap.py --dir docs/reviews/bh07/payment_instructions_heap_evidence --require-dto-attribution
```
