# Handoff: BH-07 V2b PaymentInstructions Synthetic `receiverSnapshot` Heap Tooling (Task 1, Round 3/3 — Scoped Source-Only)

**Codex supplemental repair after final Anti round:** reviewer found commented JavaScript could satisfy source binding. Codex added inert-code controls (Python RED4subcases; Node RED7/8) and conservative offset-preserving lexical masking; final21Python/8Node PASS. Actual profile artifact produces identical independently extracted Node/Python binding. Original R1 narrow-verdict bundle remains unchanged; fresh runtime pending this source checkpoint. This is Codex implementation/self-check, not independent runtime.

- **Date:** 2026-11-13
- **Role:** Antigravity (Task 1 final correction round 3/3; scoped source-only)
- **Plan:** [2026-11-13-bh07-instructions-heap.md](../../superpowers/plans/2026-11-13-bh07-instructions-heap.md)
- **Feasibility spec:** [payment_instructions_heap_feasibility_20261113.md](payment_instructions_heap_feasibility_20261113.md)
- **Review & R1 runtime basis (untouched):** [payment_instructions_heap_review_r1_20261113.md](payment_instructions_heap_review_r1_20261113.md), [payment_instructions_heap_runtime_20261113.md](payment_instructions_heap_runtime_20261113.md), and `docs/reviews/bh07/instructions_heap_r1_20261113_evidence/run/summary.json` (source `39302fe` remains `PASS_NARROW_RPC_PAYLOAD_ONLY` / `payment_instructions_coverage_gate: UNKNOWN/NOT_RUN`; original 4 bytes not rewritten or retagged).
- **Round 3 Runtime / Browser / DB / Docker status:** **NOT RUN** (scoped source-only tooling + pure unit/control verification; Root decides whether to run a fresh clean runtime after review).

## 1. Owned Deliverables (6 Files Only)

1. `scripts/bh07_appheap/disposable_instructions_fixture.py` — Unchanged in Round 3. Isolated disposable private-club (`clubs`, `club_members`), unlisted completed session (`sessions` with two synthetic non-rendered UUIDv4 values in `receiver_snapshot.canary_instr_a` and `canary_instr_b`), unpaid confirmed guest `session_players` (`user_id = NULL`), active `charge_revisions` matching `sessions.billing_input_version`, and `session_charges` (`amount_due_vnd = 100000`). Enforces outside-repo non-symlink `--state` validation, exclusive pre-INSERT recovery file write + atomic updates, missing/empty/malformed baseline fail-closed receipt (while still cleaning owned rows), Auth sequence scoping allowing ONLY `auth.refresh_tokens_id_seq.last_value` + Auth rows to differ, and `finalize_cli_cleanup` failing closed (exit `1`, `recovery_state_retained: true`, `recovery_state_error`) if state unlinking fails after DB cleanup.
2. `scripts/bh07_appheap/run_payment_instructions_heap.js` — Companion CDP heap runner reusing `CdpClient`, `build_guard.js`, `owned_browser_cleanup.js`, and `heap_oracle.py` (`2 cycles x 4 epochs = 8 epochs`). Round 3 adds artifact-bound source mapping (`extractJsConstructor`, `extractAndValidateSourceBinding`) and strict ordered chain matching (`hasOrderedDtoRetainerChain`):
   - Validates `build_dir/main.dart.js` non-symlink file SHA-256 against `summary.environment.build.artifacts['main.dart.js']` (`cfg.build_dir || hooks.buildDir || BUILD_DIR`).
   - Extracts unique `FinanceProvider` and `PaymentInstructions` constructor definitions via balanced brace scanning (`<= 32768` bytes each), parses chained assignments (`_.a = _.b = ... = rhs`) including unmangled `_instructions` or mangled `_*$_instructions` ONLY when proven in that artifact (never hardcoding `_instructions` fallback when unverified), verifies `FinanceProvider` non-null/null assignments + reads + `fetchPaymentInstructions` + `get_payment_instructions`, `PaymentInstructions` `receiverSnapshot` parameter assignment + reads + `receiver_snapshot`, and `_provider$_value` holder write/read usage.
   - Publishes sanitized binding metadata (`summary.json` -> `attribution_assessment.source_binding`, canonical `binding_sha256`) and companion bounded `source_binding.json` (`<= 65536` bytes, constructor + compact field-use snippets only, full `main.dart.js` SHA provenance, hashed into `hashes.sha256`, screened for secrets/canaries, never publishing full `main.dart.js` or API keys).
   - `hasOrderedDtoRetainerChain` and `assessPathAttribution` require all 4 `owner_active` paths to have `exact === true`, no `'...'` truncation, `path_len === frames.length - 1`, matching `path_sha256_12`, no forbidden XHR/script words, `_provider$_value -> object` immediately followed by `property:<bound_instructions_field> -> object` immediately followed by `property:<bound_receiver_snapshot_field> -> object`, followed by valid `JsLinkedHashMap` edges (`_strings -> canary_instr_a|b -> hashMapCellValue -> string` or `_first|_last -> (_next|_previous)* -> hashMapCellValue -> string` or `_nums|_rest` -> container edges -> `hashMapCellValue -> string`). Missing/contradictory binding leaves `dto_attribution_proven = false`, `scoped_verdict = PASS_NARROW_RPC_PAYLOAD_ONLY`, `payment_instructions_coverage_gate = UNKNOWN/NOT_RUN`.
3. `scripts/bh07_appheap/verify_payment_instructions_heap.py` — Offline fail-closed auditor (`--dir`, optional `--build-dir`, optional `--require-dto-attribution`). Preserves legacy 4-file `PASS_NARROW_RPC_PAYLOAD_ONLY` bundles cleanly while enforcing Round 3 strict validation:
   - Whenever `dto_attribution_proven=True` (with or without `--require-dto-attribution`), requires valid `attribution_assessment.source_binding`, companion `source_binding.json` in bundle & `hashes.sha256` (bounded, snippet SHAs verified, no secrets/raw canaries), AND `--build-dir` containing non-symlink `main.dart.js` whose SHA-256 equals `environment.build.artifacts['main.dart.js']` and independently recomputes `extract_and_validate_source_binding` from the actual `main.dart.js` artifact (never trusting snippets alone).
   - Validates all 4 `owner_active` path records (`exact`, `path_len`, `path_sha256_12`, bound ordered chain) and `proven_frames`. Any missing `--build-dir`, hash mismatch, missing/mismatched binding, or chain mismatch fails closed with `payment_instructions_coverage_gate = UNKNOWN/NOT_RUN` (never `PASS`).
4. `scripts/bh07_appheap/test_payment_instructions_heap.py` — Pure Python unit, positive, and mutant tests (20 tests total), including `test_positive_dto_attributed_with_exact_source_binding`, `test_mutant_absent_binding_and_hash_mismatch_rejected`, and `test_mutant_xhr_script_reverse_fragment_wrongfield_mismatchpayload_rejected` (`--build-dir` enforcement, constructor/artifact hash mismatch, absent binding, XHR/script labels, reverse order, missing `_provider$_value`, wrong `_finance_provider$_instructions` / `_instructionsPlayerId` fields, truncated `'...'`, `exact=False`, bad `path_sha256_12`, wrong canary map key).
5. `scripts/bh07_appheap/instructions_heap_controls.js` — Pure Node controls (8 checks total), updated in `owner_precondition_and_attribution_and_raw_leak` to test `extractAndValidateSourceBinding`, 4-path positive exact binding, mangled-vs-unmangled binding separation, and strict rejection of absent binding, hash mismatch, marker-only/no-field-use, wrong field, missing `_provider$_value`, reverse chain, wrong canary payload, XHR/script labels, and truncated `'...'` paths.
6. `docs/reviews/bh07/payment_instructions_heap_handoff_20261113.md` — This Round 3 handoff document.

Untouched shared assets preserved as-is: `heap_oracle.py`, `verify_evidence.py`, `run_app_profile_heap.js`, `lib/**`, `supabase/**`, `docs/reviews/bh07/instructions_heap_r1_20261113_evidence/`, `docs/reviews/bh07/payment_instructions_heap_review_r1_20261113.md`, `docs/reviews/bh07/payment_instructions_heap_runtime_20261113.md`.

## 2. Pure Unit / Control Results Observed

Observed RED -> GREEN runs on the Round 3 implementation:

- Initial RED before Round 3 implementation:
  - `node scripts/bh07_appheap/instructions_heap_controls.js` -> exit `1` (`controls: 7/8 passed`, `runner.extractAndValidateSourceBinding is not a function`).
  - `python -m unittest scripts.bh07_appheap.test_payment_instructions_heap` -> exit `1` (`Ran 20 tests`, `FAILED (errors=3)`, `TypeError: verify() got an unexpected keyword argument 'build_dir'`).
- Final GREEN runs verified after final Round 3 edits:
  - `node scripts/bh07_appheap/instructions_heap_controls.js` -> **exit `0`, `controls: 8/8 passed`**.
  - `python -m unittest scripts.bh07_appheap.test_payment_instructions_heap` -> **exit `0`, `Ran 20 tests`, `OK`**.

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
- To prove DTO-level attribution (`dto_attribution_proven = true`, `scoped_verdict = PASS_DTO_ATTRIBUTED`, `payment_instructions_coverage_gate = PASS`), `attribution_assessment.source_binding` and companion `source_binding.json` must bind `summary.environment.build.artifacts['main.dart.js']` to a verified `build_dir/main.dart.js` (`--build-dir` on the verifier) with validated `FinanceProvider` & `PaymentInstructions` constructors and field uses, and all 4 `owner_active` paths must contain an un-truncated (`exact = true`, no `'...'`, matching `path_len` and `path_sha256_12`), ordered `property` edge chain starting from `'root'` through `property:_provider$_value -> object` immediately to `property:<bound_instructions_field> -> object` immediately to `property:<bound_receiver_snapshot_field> -> object` and valid `JsLinkedHashMap` edges to the leaf `string`/`concatenated string`/`sliced string` node (`hashMapCellValue`, matching canary key when `_strings`, rejecting XHR/string/script labels, non-`property` edges, reverse order, fragments, or hash mismatches). This covers **synthetic `receiverSnapshot` map values only** and makes **no claim that the full `PaymentInstructions` model is clean**.
- If source binding is missing/contradictory, `--build-dir` lacks an exact matching `main.dart.js`, or any owner path fails the bound chain contract, `dto_attribution_proven` stays `false`, `scoped_verdict` stays `PASS_NARROW_RPC_PAYLOAD_ONLY`, and `payment_instructions_coverage_gate` stays `UNKNOWN/NOT_RUN`. `--require-dto-attribution` on the verifier fails closed (`exit 1`) in that state.

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

3. Offline fail-closed audit (pass `--build-dir build/web` so verifier independently recomputes source binding against the exact `main.dart.js`):
```powershell
python -X utf8 scripts/bh07_appheap/verify_payment_instructions_heap.py --dir docs/reviews/bh07/payment_instructions_heap_evidence --build-dir build/web
python -X utf8 scripts/bh07_appheap/verify_payment_instructions_heap.py --dir docs/reviews/bh07/payment_instructions_heap_evidence --build-dir build/web --require-dto-attribution
```
