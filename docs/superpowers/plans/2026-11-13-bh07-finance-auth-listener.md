# BH-07 Finance Auth listener finite-state probe

**Goal:** Verify the rooted AuthProvider listener tearoff bound to FinanceProvider, and the two loaded fields `_instructions` / `_finance` across the existing Owner→logout→Cohost/Member cycles. This is a finite subgraph check, not full auth_listeners acceptance.

**Spec:** `docs/reviews/bh07/auth_listener_heap_feasibility_20261113.md`, including Codex calibration corrections; Guest calibration shows numeric counters require supplemental own-property CDP reads. Standing AGENTS authorizes Anti implementation, up to3 correction rounds then Codex direct repair, local runtime and commit. No app/schema/remote/release/risk acceptance.

## Scope and ownership

Anti owns only four new tooling/test files and handoff specified in its task. Reuse `run_payment_instructions_heap.js` via existing `runMeasurement` capture hook, `heap_oracle` parse/layout/strong-root BFS, constructor binding and cleanup. Do not change those existing sources or historical bundles. No packages/framework/refactor.

Baseline may have FinanceProvider absent due lazy instantiation; Owner must have exactly one rooted FinanceProvider and one AuthProvider, exactly one matching active tearoff, both selected model fields loaded. Post-logout must keep the live registration and clear these two fields. Other actors may reload permitted state; do not infer a leak from unrelated legitimate models. Other providers/fields/native/full listener graph remain UNKNOWN/NOT RUN.

## Tasks

- [x] New pure RED controls: missing Owner load, duplicate rooted Auth/Finance/registration, wrong receiver/method, weak-only vs rooted target, unknown layout/cap, mismatched source binding, non-null post-logout selected field, counter disagreement/non-quiescent state, remote handle release failure. Observe RED before implementation.
- [x] Minimal offline graph scanner: enumerate all rooted target instances; exact array slot mapping including backing array, tearoff prototype method plus `_receiver` identity; field object/null metadata only. Numeric values are not in snapshot and must never be invented from slots or node type.
- [x] New wrapper uses existing runner capture hook, streams once per epoch, runs existing oracle and graph scanner before dump deletion. Read scoped own-property scalars against exact heap IDs, release object groups on every path; require repeated counters consistent and snapshot/CDP selected-field descriptors agree. Explicitly label observations hybrid/nearby, not atomic.
- [x] Companion auditor delegates existing strict artifact/canary verification then validates every listener epoch and the positive Owner/post-logout contract. No clean verdict from missing provider or unimplemented branches.
- [x] Anti handoff pure controls, Codex/reviewer source review and bounded fixes. Commit source, run fresh local2cycles/8epochs; preserve all failed attempts, exact source/build provenance, DB/fixture/profile/dump/state and observer cleanup receipts.
- [x] Independent source/control/artifact review; publish only structural metadata, update scope/status, commit. No independent runtime claim unless actually rerun by reviewer.

## Review focus

Lazy instantiation; slot/capacity vs active count; prototype method vs provider prototype; all instances rather than first match; snapshot↔scalar races; remote handles pinning private models; own-property reads must not invoke getters; observer failure and partial artifacts; Owner load vs zero/null from never loading; no raw bank/reference/UUID/user/token publication; no whole-model/listener claim.

## Completed 14/11/2026

Source70a71ba clean runtime PASS finite Finance/twofield gate;14Python/Node controls PASS, strictauditor0. R1/R2 FAIL preserved; twoCodex runtime compatibility repairs and source result-overwrite guard reviewed. Reviewer21hashes/auditor0/missingbuildreject1, no independent runtime. Report finance_auth_listener_runtime_20261114.md. Full Auth graph/BH07 unaccepted.
