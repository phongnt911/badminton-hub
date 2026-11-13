# V2b — PaymentInstructions synthetic receiverSnapshot heap retention

- Gate: V2b — PaymentInstructions synthetic receiverSnapshot heap retention
- Status: **RUN** (verdict PASS)
- Scoped verdict: **PASS_DTO_ATTRIBUTED**
- PaymentInstructions coverage gate: PASS
- Attribution: root_reachability_measured=true; dto_attribution_proven=true (proven_artifact_bound)
- Source binding: verified (main.dart.js a20b3d22a011, FinanceProvider._instructions, PaymentInstructions.receiverSnapshot)
- Claim scope: payment_instructions_receiver_snapshot_only (synthetic receiverSnapshot keys only; no whole-model claim)
- Tested source: `70a71ba0ceb1602d0be24cc56952e24ee11d4dfb` (git dirty: false)
- Same document across cycles: true

## Sentinels (values never published)

| sentinel | scope | rendered | distinctive | length | sha256[:12] |
| --- | --- | --- | --- | --- | --- |
| canary_instr_a | finance | false | true | 36 | 502bf35607c1 |
| canary_instr_b | finance | false | true | 36 | 999ca9a1fd6d |
| probe | control | false | true | 23 | 319552717d73 |

## Cycles (8 epochs total across 2 cycles)

| cycle | actor | same document | timeOrigin | epoch | bytes | sha256[:12] | present |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | cohost | true | 1794609265225.2 | baseline | 60414787 | e98289380ab3 | probe |
| 1 | cohost | true | 1794609265225.2 | owner_active | 84269993 | 3fe9e7b24311 | canary_instr_a, canary_instr_b, probe |
| 1 | cohost | true | 1794609265225.2 | post_logout | 69312091 | 10449f439828 | probe |
| 1 | cohost | true | 1794609265225.2 | post_actor | 82616491 | 1f25e5355bac | probe |
| 2 | member | true | 1794609265225.2 | baseline | 71276249 | 47f01d99b270 | probe |
| 2 | member | true | 1794609265225.2 | owner_active | 86578282 | b6084be47e88 | canary_instr_a, canary_instr_b, probe |
| 2 | member | true | 1794609265225.2 | post_logout | 71005377 | 6c35e1437df2 | probe |
| 2 | member | true | 1794609265225.2 | post_actor | 75848338 | 8405b85fde11 | probe |

## Findings

- none

## Cleanup

- {"disposable_instructions_club_id_sha256_12":"02209a642f32","disposable_instructions_session_id_sha256_12":"51f79bd5b737","canary_instr_a_sha256_12":"502bf35607c1","canary_instr_b_sha256_12":"999ca9a1fd6d","disposable_instructions_club_created":true,"disposable_instructions_session_created":true,"disposable_instructions_removed":true,"disposable_instructions_verified_absent":true,"disposable_instructions_cleanup_verified":true,"zero_mutation_verified":true,"baseline_fingerprint_equal":true,"public_rows_schema_roles_equal":true,"auth_rows_excluded":true,"mutation_counts":{"payments":0,"club_transactions":0,"audit_events":0,"operation_requests":0},"auth_refresh_sequence":[84,88],"public_tables":21,"public_rows":94,"before_fingerprint_sha256":"d640fd961dc008682af4d6bf5734fb1730845764091e0f604806bb6134da35e4","after_fingerprint_sha256":"c465cdb928bcada8edeb08363e3660a4b6d7999deada2342363ce7d536352e49","recovery_state_retained":false,"dump_dir_outside_repo":true,"raw_snapshots_remaining":0,"dumps_dir_removed":true,"chrome_profile_dir_removed":true,"ok":true}

## Limitations

- Covers ONLY synthetic non-rendered JSON keys (`canary_instr_a`, `canary_instr_b`) carried via `get_payment_instructions` into `receiverSnapshot` (no whole-model clean claim).
- Rendered strings (`bank_code`, `account_number`, `account_name`, `reference`) remain unattributed.
- Under dart2js compilation, V8 strong-root reachability proves Dart-level DTO attribution ONLY when served-artifact source binding (`main.dart.js` SHA + constructor/field validation) verifies an exact ordered retainer chain (`_provider$_value` -> bound instructions field -> bound `receiverSnapshot` field -> map edges).
- Does not cover `AuthProvider` listener graphs, Dart VM desktop/mobile, Firefox, or Safari.
