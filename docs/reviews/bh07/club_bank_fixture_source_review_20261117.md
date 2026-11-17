# Club bank fixture source/control review after R1

AGY Gemini4Hydrogen(XHigh) implements default-off opt-in fixture on baseeb6f197; one correction round closes CB1 parent-cascade race. No app/backend/migration/remote changes. Default-off private state/SQL/metadata/receipts remain compatible; opt-in bank UUID/account state is persisted before atomic insert, verified on readback, guarded by exact ownership and active status, explicitly removed before parent deletion and verified absent.

Fresh Codex: `python -X utf8 -m unittest scripts.bh07_appheap.test_payment_instructions_heap scripts.bh07_appheap.test_session_club_auth_listener_graph scripts.bh07_appheap.test_finance_auth_listener_graph`60PASS/61.359s/exit0; Session/Club Node controls exit0. Separate reviewer independently ran27initial Python tests, found CB1 despite green tests, then inspected R1 and ran15lifecycle tests PASS. No P0/P1/P2 remains in the reviewed delta.

Parent club FOR UPDATE and ordered bank-row FOR UPDATE now precede all transaction ownership guards/deletes and remain held through COMMIT. Mock interleavings verify generated SQL/control behavior, not PostgreSQL multi-connection semantics. Separate reviewer read Codex's proposed actual-SQL advisory-gated local probe and found it suitable for bounded verification; actual DB probe and browser runtime are NOT RUN at this checkpoint.

Public bank metadata/receipts use hashes/booleans. Four mutation counters cover payments/club_transactions/audit_events/operation_requests, not arbitrary bank-state history. Full model/listener/native/BH-07/V8 acceptance remains open. No main merge/deploy/pilot/BH-08 or owner risk acceptance.
