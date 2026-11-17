# Club bank opt-in fixture review R1 — CHƯA ĐẠT

Baseeb6f197, AGY initial handoff. Separate reviewer independently ran27Python PASS; Codex Node controls PASS. No new bank browser/DB runtime yet. Existing PARTIAL evidence unchanged.

**CB1 P1:** cleanup transaction uses plain SELECT ownership/absence guards before DELETE clubs, without locking parent/children. Interleaving: A completes bank absence DO; B inserts another bank into fixture.club_id and commits; A deletes club and FK CASCADE deletes B's unowned bank. Post-cleanup absence/baseline may still match because B's row was created and destroyed entirely between captures. Account predicates on the explicit bank DELETE do not protect the parent cascade.

Fix minimally in opt-in path only: after BEGIN, acquire/hold parent club row FOR UPDATE before ownership checks and all deletes, and lock relevant bank rows before their mutable ownership checks; transaction guards must re-evaluate after locks, through COMMIT. Parent FOR UPDATE must block foreign-key KEY SHARE insert/reparent until club deletion/commit. Preserve default-off SQL/state behavior. Add an honest interleaving control plus ordering checks; do not claim FakeDb proves PostgreSQL concurrency. Codex will run a controlled local two-connection probe before browser runtime.

Contract note: initial readback requires active status, but ownership/delete currently omit status. Either consistently include status='active' in exact bank identity/tamper checks with a test, or explicitly narrow handoff's claim that all altered columns are rejected. Avoid broad zero-bank-mutation claims when only payment/ledger/audit/operation counters are checked.

Correction1/3 is scoped to the two fixture/test files and handoff, not app/schema/remote or historical evidence. Same exact Python/Node commands permitted. Leave uncommitted; no browser/DB/remote, commit/push or subagents. Runtime NOT RUN until new source/control and local concurrency verification.
