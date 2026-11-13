# BH-07 Finance Auth-Listener Probe — Handoff (Correction 3/3: Actual-Shape Async & Factory Source Binding)

**Status:** Correction 3/3 source-binding updates & pure offline verification complete (**NOT a live runtime PASS** — Root read-only `bind --build-dir build/web` check and live Chrome/DB runtime measurement remain `NOT RUN`, and full Auth-listener / V2b / BH-07 / V8 gates remain `NOT RUN`). All FL1–FL4 contracts, constructor cap (`32768`), prototype budget (`262144`), and fail-closed gates remain intact and await Root verification/review.

## Scope & Claim Boundaries

- **Included finite scope:** `AuthProvider` strong-root-reachable listener graph edge to `FinanceProvider` only (`ChangeNotifier__listeners` / `internal:elements` FixedArray normalization, generated tearoff prototype `BoundClosure` chain + `$_name === '_onAuthChanged$0'`, exact `_receiver` pointing to the single rooted `FinanceProvider` instance), plus selected field state on `FinanceProvider` (`_instructions` -> `PaymentInstructions`, `_finance` -> `SessionFinance`).
- **Observation contract:** `hybrid_snapshot_plus_readonly_cdp_own_properties` with `atomic_claim: false` and typed finite positive `time_origin` recorded across snapshot capture and read-only CDP own-property scalar/metadata reads (`HeapProfiler.getObjectByHeapObjectId`, `Runtime.getProperties({ownProperties: true, generatePreview: false})`, and `Runtime.releaseObjectGroup` in `finally`). Never calls getters, evaluates expressions on DTO instances, injects new canaries, or persists raw CDP `objectId` handles / UUIDs / bank / reference / token values.
- **Epoch contract:**
  - `baseline`: if `FinanceProvider` count is `0` (lazy before Owner instructions open, expected in Cycle 1), reports `NOT_RUN_LAZY` (never false `PASS`); if `FinanceProvider` count is `1` (same-document Cycle 2), requires live tearoff registration and both `_instructions` and `_finance` `is_null == true` (`PASS`).
  - `owner_active`: requires `1` rooted `AuthProvider`, `1` rooted `FinanceProvider`, exact `1` matching `_onAuthChanged$0` tearoff targeting that exact `FinanceProvider` node, `_currentUser` non-null, `_instructions` (`PaymentInstructions`), and `_finance` (`SessionFinance`) non-null.
  - `post_logout`: requires same live provider registration (`1` matching tearoff -> `1` `FinanceProvider`) with `_currentUser`, `_instructions`, and `_finance` all `is_null == true`.
  - `post_actor`: record-only for legitimate actor refetches (allows valid non-null DTO class or `null` without failing on legitimate refetch), while still gating single-root cardinality, no duplicate Finance registration, and CDP counter/quiescence integrity.
- **Explicitly `NOT RUN / UNKNOWN`:** Actual `build/web` `bind` execution result (deferred to Root), live Chromium 2-cycle heap/CDP runtime, `ClubProvider`, `SessionProvider`, UI listener internals beyond structural observation counts, other DTO/provider fields, full app-wide `AuthProvider` listener graph, Dart VM desktop/mobile, Firefox, Safari, staging/production, and BH-08.

## Correction 3/3 Fixes (Actual-Shape Async Repository Binding, Chained Alias Reset & Bounded Factory Wiring)

Addresses R2 closure findings (`finance_field_ambiguous_or_missing:[]` and bounded factory wiring mismatch against compiled dart2js structure) without loosening string matching or hardcoding fallback field names:

- **Prototype span & method parser (`finance_auth_listener_graph.py`):**
  - `_extract_prototype_span` (keeping `_extract_prototype_block` 2-tuple return compatible with existing budget tests) + `_extract_prototype_methods` parse top-level prototype methods within the bounded prototype block (`MAX_PROTOTYPE_BLOCK_BYTES = 262144`) using offset-preserving masked executable source (`pi_verifier._executable_source`) and `_find_closing_brace`.
  - Verified `this` alias resolution (`_verified_this_aliases`) accepts explicit `this` aliases (such as `var _this = this` and `$async$self = this`) only when never reassigned to a non-`this` value anywhere in the method, and rejects substring spoofs (`_this` without verified `= this`) via identifier-boundary lookbehinds.
- **Source-bound async repository-return binding & retained legacy direct form (`finance_auth_listener_graph.py`):**
  - `_verify_repo_session_finance_method` follows direct `FinanceRepository` delegation (e.g. `getSessionFinance$3$limit$offset` -> `getSessionFinance$body$FinanceRepository`) and requires an executable `.rpc*("get_session_finance", ...)` call (checking aligned masked `exe_code` and `js_text` offsets so string/comment decoys cannot pass) plus a non-reassigned `new A.SessionFinance(...)` return (`return A._asyncReturn(rvar, ...)` or direct return).
  - `_derive_async_repo_finance_candidates` binds inside `fetchSessionFinance*`: single `A._wrapJsFunctionForAsync(function(err, $async$result) { ... })`, verified `this` alias on `.<repository_field>.<repo_method>(...)`, matching callback variable and resume `case <N>:` from the preceding `$async$goto = <N>;`, non-reassigned result variable trace (`$async$result` -> `finance`), and exact provider field write (`$async$self.<field> = finance`), rejecting `instructions_field` and requiring ctor `null` initialization (`_._finance = _._financeSessionId = null`).
  - `_derive_direct_session_finance_candidates` retains proven direct `new A.SessionFinance(...)` inside `fetchSessionFinance*` when explicitly assigned on a verified `this` alias in executable code.
- **Chained aliased null reset & optional inlined getters (`finance_auth_listener_graph.py`):**
  - `_has_aliased_null_reset` and `_verify_finance_reset_and_optional_getter` verify aliased chained null resets (`_this._finance = _this._financeSessionId = null;`) in `reg_method` (`_onAuthChanged$0`) or a directly called non-fetch reset helper, and do not require tree-shaken/inlined `get$finance` / `get$sessionFinance` (while still rejecting any present `get$finance` / `get$sessionFinance` that returns a different field).
- **Bounded factory wiring with intervening initialization (`finance_auth_listener_graph.py`):**
  - `_find_enclosing_function_bounds` and `_verify_factory_listener_wiring` locate `new A.FinanceProvider(...)` at brace depth 0 of its enclosing factory function, derive `auth` and `<repository_field>` parameter positions from the parsed `FinanceProvider` ctor, verify the `auth` argument variable comes from `A.Provider_of(..., type$.AuthProvider)` or `new A.AuthProvider(...)` without reassignment (and `FinanceRepository` ctor when async repo path is active), allow intervening property/auth initialization (`t2._finance_provider$_authUserId = t3;`), and require `authVar.addListener$1(finVar.<reg_getter>())` + `return finVar` within that same factory body without receiver reassignment, control-flow breaks (`return`/`throw`/`.removeListener`), moved wiring, or commented/stringified code.
- **Portable actual-shape contract & negative controls (`test_finance_auth_listener_graph.py`, `finance_auth_listener_controls.js`):**
  - `TestFinanceAuthListenerBinding.test_actual_shape_async_factory_binding_contract_and_negative_controls` exercises synthetic `> 32 KiB` prototype actual-shape async/factory positive binding plus 22 fail-closed negative controls (`wrongreceiver_*`, `wrongauth_*`, `alias_*` including `_this = otherObj`, `RPCresult_*`, `field_*`, `ambiguous_two_fields`, `reset_*`, `method_*`, `comment_*`, `literal_*`, `optional_getter_mismatch`) with zero dependency on untracked `build/web`.
  - `testExtractListenerBinding` in `finance_auth_listener_controls.js` adds positive and `factoryReceiverReplaced` negative checks on synthetic actual-shape JS via Python `extract_listener_source_binding`.

## Preserved Correction 1 & 2 Foundations

- **FL1–FL4 (`run_finance_auth_listener.js`, `finance_auth_listener_graph.py`, `finance_auth_listener_controls.js`):** Real CDP `{ result: RemoteObject }` validation (FL1), full `active_slots` recomputation in strict auditor (FL2), strict typed finite `time_origin` and scalar/metadata validation without bool coercion (FL3), structural allowlist sanitization on both `PASS` and `FAIL` (FL4), and safe failed-epoch diagnostics remain intact.
- **Budgets & Untouched Baseline Helpers:** `verify_payment_instructions_heap.py` (`MAX_CONSTRUCTOR_SNIPPET_BYTES = 32768`), `Closure_fromTearOff` 32 KiB cap, and `run_finance_auth_listener.js` remain completely untouched.

## Owned Files (Exact 5 Paths; No App Code, Schema, Old Helper, or Bundles Modified)

1. [scripts/bh07_appheap/finance_auth_listener_graph.py](../../../scripts/bh07_appheap/finance_auth_listener_graph.py) — stdlib source-binding validator (`bind` with Correction 3/3 async/reset/factory checks), single-parse snapshot structural scanner (`scan`), CDP hybrid counter/field evaluator (`apply-cdp`), and strict independent auditor (`verify`).
2. [scripts/bh07_appheap/run_finance_auth_listener.js](../../../scripts/bh07_appheap/run_finance_auth_listener.js) — companion runner (untouched in Corrections 2 & 3).
3. [scripts/bh07_appheap/test_finance_auth_listener_graph.py](../../../scripts/bh07_appheap/test_finance_auth_listener_graph.py) — Python unit tests including FL2–FL4, >32 KiB prototype budget, and actual-shape async/factory + 22 negative binding controls.
4. [scripts/bh07_appheap/finance_auth_listener_controls.js](../../../scripts/bh07_appheap/finance_auth_listener_controls.js) — Node FL1/FL3/FL4, `extractListenerBinding` (including actual-shape positive/negative controls), and mocked 2-cycle controls.
5. [docs/reviews/bh07/finance_auth_listener_handoff_20261113.md](finance_auth_listener_handoff_20261113.md) — this handoff note.

## Pure Offline Verification Results (Observed in Correction 3/3, 2026-11-14)

- `python -m unittest scripts.bh07_appheap.test_finance_auth_listener_graph` -> `Ran 11 tests in 10.335s`, `OK` (exit code 0)
- `node scripts/bh07_appheap/finance_auth_listener_controls.js` -> `ALL_FINANCE_AUTH_LISTENER_CONTROLS_PASS` (exit code 0)
- **Live `bind --build-dir build/web` & Live Chrome/DB runtime:** `NOT RUN` (awaiting Root read-only `bind` check, review, and local runtime verification).

## Root Execution Commands (For Read-Only Bind Check + Local Runtime + Audit)

Run read-only bind check against `build/web`, then live profile measurement using existing private fixture/profile config and inspect strict audit (do not reuse an unrelated output directory):

```bash
python -X utf8 scripts/bh07_appheap/finance_auth_listener_graph.py bind --build-dir build/web --expected-main-js-sha a20b3d22a011fb511a76ee4daa11167410a6a61a2aba3f796f8ae0e1e65fe83e
node scripts/bh07_appheap/run_finance_auth_listener.js --config <PRIVATE_BH07_CONFIG_JSON> --out <PRIVATE_OR_SCOPED_OUT_DIR>
python -X utf8 scripts/bh07_appheap/finance_auth_listener_graph.py verify <OUT_DIR> --build-dir build/web
```
