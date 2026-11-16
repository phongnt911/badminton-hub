# BH-07 Session/Club listener continuation

**Authorization:** Owner on 16/11/2026 requested continuation and assigned coding to AGY Gemini 4 Hydrogen (XHigh). Existing three-correction-round and local-only constraints remain. This continues the next step in finance_auth_listener_runtime_20261114.md, not a new product feature.

**Base:** 51013c7, reconciled local runtime and remote staging history. No main integration, remote DDL, deployment, pilot or BH-08.

**Goal:** Extend bounded Web listener evidence to AuthProvider -> SessionProvider/ClubProvider and explicitly selected state reset contracts. Whole graph/model/native acceptance remains open.

**Architecture:** Reuse calibrated snapshot traversal, artifact constructor/field/factory binding and read-only CDP own-property observations from Finance tooling. Keep Finance CLI, contracts and historical bundles compatible. Prefer a small companion using existing helpers; do not copy the whole scanner or build a generic query framework. Python stdlib/Node and installed browser tooling only.

## AGY ownership

AGY owns new Session/Club companion scanner, runner, controls and tests under scripts/bh07_appheap, a handoff under docs/reviews/bh07, and only necessary backward-compatible exports/hooks in existing Finance/instructions tooling. No lib/, migrations/, supabase/, existing evidence or remote operations. Other work exists: do not revert others' changes. Codex owns integration, review and runtime evidence.

- [ ] Inspect actual Dart clearAll/constructor wiring and compiled executable bindings. Write a precise selected-field table in handoff. Session currentSession/currentSessionId and Club currentClub/currentClubId/currentBankAccount are minimum candidates; do not infer entire state from those fields.
- [ ] Add RED controls for wrong receiver/method, duplicate rooted provider/listener, zero provider after required load, lazy baseline, stale selected field at logout, mismatched snapshot/CDP identity/counter/timeOrigin, getter/descriptor rejection, missing artifact binding and secret-safe publication.
- [ ] Implement minimal artifact-bound scanning and hybrid observations. Inspect all rooted target instances, exactly one listener per instantiated target, method/prototype binding and receiver identity. Lazy baseline is NOT_RUN_LAZY; missing required Owner/logout instance fails. Logout selected fields must clear while registration remains; post-actor legitimate refetch must be explicit, not silently treated as stale/private leak or empty state.
- [ ] Runner must exercise real UI loading preconditions before Owner capture, same-document two cycles/eight epochs, preserve fixture/browser/objectgroup/temp cleanup, never invoke getters or mutate app state through CDP. If existing fixture cannot populate Club fields, report that gate NOT RUN and specify the smallest needed local fixture extension rather than fake PASS.
- [ ] Run new and existing Finance/instructions Python and Node controls. Give exact commands/results, RED/GREEN evidence, source paths, claim limits and runnable runtime instructions. Runtime NOT RUN until Codex actually measures. No completion/acceptance claim.

## Codex ownership after handoff

- [ ] Review actual delta and run focused tests independently; return concrete findings to AGY at most three corrections, then fix remaining findings under standing authorization.
- [ ] Execute feasible clean-source local runtime with disposable fixture, privacy-safe artifacts and DB before/after/cleanup receipts. Keep FAIL/UNKNOWN/NOT RUN honest if environment or preconditions fail.
- [ ] Record source-bound evidence and update current status. No risk acceptance on owner's behalf.

**AGY invocation:** gemini-4-hydrogen-xhigh, --effort xhigh, --print-timeout 0. No permission-policy bypass or global settings changes; monitor process and await handoff before reviewing edits.
