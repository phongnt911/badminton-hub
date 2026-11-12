# Staging security triage — 2026-11-12

Source `c960c2d`, hosted staging `mxqpukhfiugdwsjsbihj`. No fixture users/rows created.

## Anti CLI read permission

Initial read-only CLI conversation `3bc580f5-6098-468e-aa7c-d25c57881508` returned no analysis because headless `read_file` was denied. No bypass was used. Owner then explicitly approved headless file reads. A session-only allow rule scoped to this repository was added to the untracked local settings file; no global settings or unrestricted tool approvals were changed.

Conversation `e73b8044-5918-455d-a3f9-a6e80d09606c` reports successful native source read of migration lines543–782 and dependency analysis. It returned a substantive proposal but final CLI status ERROR due upstream connection failure; this is reconnaissance, not a completed implementation or passing test. Supplied-source analysis `71736ede-874e-4320-96f0-4b24e9a215c8` completed separately without native reads. Do not treat either as independent runtime QA.

## Codex HTTP baseline

Four actual requests using the project publishable key; no privileged key or user token. Only status/type/count/code retained, not response data or keys:

| Probe | HTTP | Observation |
|---|---|---|
| public_session_summary SELECT id limit1 | 200 | empty array |
| player_outstanding SELECT session_player_id limit1 | 401 | PostgreSQL42501 |
| is_app_admin(zero UUID) | 200 | boolean false |
| get_host_bank_account() | 401 | PostgreSQL42501 |

These are empty-project permission controls, not proof of populated-row isolation or end-to-end Auth. The helper response confirms unauthenticated RPC executability; source accepts an arbitrary user UUID and reads protected role tables without caller binding. Known UUIDs could be queried for membership/role relationships when populated. Do not claim that this test demonstrated real user disclosure.

## Proposed bounded repair

- Forward migration revokes PUBLIC/anon EXECUTE for the ten authorization helpers, retaining authenticated EXECUTE required by RLS. Verify every helper signature and guest-call dependency before applying.
- Pin both legacy sync trigger search paths as hardening; bodies remain unchanged. Current bodies are invoker functions and use qualified table names, so the advisor notice alone is not proof of an exploitable privilege escalation.
- Keep the two filtered security-barrier views unchanged. Public session projection is intentionally public; outstanding rows use caller predicates. These observations do not waive the advisor or substitute for populated isolation tests.
- Re-run HTTP baseline, guest RPC controls, role grants, and advisor after a reviewed change. Any migration is restricted to the approved test staging, not the older project or production.

No security finding is closed by this reconnaissance. V3/V5/V7 and full BH-07/V8 remain unaccepted.

## Subsequent local candidate review

[Final review](staging_hardening_review_final_20261112.md) closes local candidate/test/handoff findings after Anti correction2/3. [Runtime report](staging_hardening_local_runtime_20261112.md) records Codex42focused+21DB PASS and verified isolated cleanup, with two earlier verifier failures preserved. This supplements the reconnaissance; hosted helper grants have not changed, other advisor notices remain open, and full BH-07/V8 remains unaccepted.
