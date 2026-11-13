# V2b — PaymentInstructions synthetic receiverSnapshot heap retention

- Gate: V2b — PaymentInstructions synthetic receiverSnapshot heap retention
- Status: **RUN** (verdict PASS)
- Scoped verdict: **PASS_DTO_ATTRIBUTED**
- PaymentInstructions coverage gate: PASS
- Attribution: root_reachability_measured=true; dto_attribution_proven=true (proven_artifact_bound)
- Source binding: verified (main.dart.js a20b3d22a011, FinanceProvider._instructions, PaymentInstructions.receiverSnapshot)
- Claim scope: payment_instructions_receiver_snapshot_only (synthetic receiverSnapshot keys only; no whole-model claim)
- Tested source: `4433b153e86a3ede7ac3362c1da2b5125c6777cd` (git dirty: false)
- Same document across cycles: true

## Sentinels (values never published)

| sentinel | scope | rendered | distinctive | length | sha256[:12] |
| --- | --- | --- | --- | --- | --- |
| canary_instr_a | finance | false | true | 36 | 25ddb89c22f1 |
| canary_instr_b | finance | false | true | 36 | 1593c4c1734c |
| probe | control | false | true | 23 | 92f72f08ff0a |

## Cycles (8 epochs total across 2 cycles)

| cycle | actor | same document | timeOrigin | epoch | bytes | sha256[:12] | present |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | cohost | true | 1794583580226.2 | baseline | 60519248 | 3642780bc8fa | probe |
| 1 | cohost | true | 1794583580226.2 | owner_active | 84193693 | 1659c36c1c72 | canary_instr_a, canary_instr_b, probe |
| 1 | cohost | true | 1794583580226.2 | post_logout | 69036080 | e30a6747d303 | probe |
| 1 | cohost | true | 1794583580226.2 | post_actor | 82403508 | c71b039d25ac | probe |
| 2 | member | true | 1794583580226.2 | baseline | 71162490 | 9458c67fd160 | probe |
| 2 | member | true | 1794583580226.2 | owner_active | 86278564 | ae7d5432fea3 | canary_instr_a, canary_instr_b, probe |
| 2 | member | true | 1794583580226.2 | post_logout | 70938085 | 7d57f6aee03f | probe |
| 2 | member | true | 1794583580226.2 | post_actor | 75757104 | 859bea15781c | probe |

## Findings

- none

## Cleanup

- {"disposable_instructions_club_id_sha256_12":"da2472659554","disposable_instructions_session_id_sha256_12":"4b48494d7018","canary_instr_a_sha256_12":"25ddb89c22f1","canary_instr_b_sha256_12":"1593c4c1734c","disposable_instructions_club_created":true,"disposable_instructions_session_created":true,"disposable_instructions_removed":true,"disposable_instructions_verified_absent":true,"disposable_instructions_cleanup_verified":true,"zero_mutation_verified":true,"baseline_fingerprint_equal":true,"public_rows_schema_roles_equal":true,"auth_rows_excluded":true,"mutation_counts":{"payments":0,"club_transactions":0,"audit_events":0,"operation_requests":0},"auth_refresh_sequence":[79,83],"public_tables":21,"public_rows":94,"before_fingerprint_sha256":"1577a6301a15c6fab27a0abbeafbb0f62bf9e1f392c31ed96112c9b264523555","after_fingerprint_sha256":"a97bc62f61ec8c6c05a81a0fffce77ec9f4ed8b900ee0238b57c7bd6a276efae","recovery_state_retained":false,"dump_dir_outside_repo":true,"raw_snapshots_remaining":0,"dumps_dir_removed":true,"chrome_profile_dir_removed":true,"ok":true}

## Limitations

- Covers ONLY synthetic non-rendered JSON keys (`canary_instr_a`, `canary_instr_b`) carried via `get_payment_instructions` into `receiverSnapshot` (no whole-model clean claim).
- Rendered strings (`bank_code`, `account_number`, `account_name`, `reference`) remain unattributed.
- Under dart2js compilation, V8 strong-root reachability proves Dart-level DTO attribution ONLY when served-artifact source binding (`main.dart.js` SHA + constructor/field validation) verifies an exact ordered retainer chain (`_provider$_value` -> bound instructions field -> bound `receiverSnapshot` field -> map edges).
- Does not cover `AuthProvider` listener graphs, Dart VM desktop/mobile, Firefox, or Safari.
