# V2b — PaymentInstructions synthetic receiverSnapshot heap retention

- Gate: V2b — PaymentInstructions synthetic receiverSnapshot heap retention
- Status: **RUN** (verdict PASS)
- Scoped verdict: **PASS_NARROW_RPC_PAYLOAD_ONLY**
- PaymentInstructions coverage gate: UNKNOWN/NOT_RUN
- Attribution: root_reachability_measured=true; dto_attribution_proven=false (unproven_under_minification)
- Claim scope: narrow_rpc_payload_retention_only (synthetic receiverSnapshot keys only; no whole-model claim)
- Tested source: `39302fe81e9c7494d54338eaa4f27de1bc4c8705` (git dirty: false)
- Same document across cycles: true

## Sentinels (values never published)

| sentinel | scope | rendered | distinctive | length | sha256[:12] |
| --- | --- | --- | --- | --- | --- |
| canary_instr_a | finance | false | true | 36 | 5fb28e6e56e7 |
| canary_instr_b | finance | false | true | 36 | d100d94fcf17 |
| probe | control | false | true | 23 | 53a44762c0f3 |

## Cycles (8 epochs total across 2 cycles)

| cycle | actor | same document | timeOrigin | epoch | bytes | sha256[:12] | present |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | cohost | true | 1794581989440.7 | baseline | 60454575 | 40cf8be50615 | probe |
| 1 | cohost | true | 1794581989440.7 | owner_active | 84455929 | cd246fc5d935 | canary_instr_a, canary_instr_b, probe |
| 1 | cohost | true | 1794581989440.7 | post_logout | 69272752 | b5116689c43f | probe |
| 1 | cohost | true | 1794581989440.7 | post_actor | 82736509 | 3c9b4b5128d0 | probe |
| 2 | member | true | 1794581989440.7 | baseline | 71555486 | 3e80bf655f1b | probe |
| 2 | member | true | 1794581989440.7 | owner_active | 85756186 | 09ffa94cf6ae | canary_instr_a, canary_instr_b, probe |
| 2 | member | true | 1794581989440.7 | post_logout | 70229302 | 69977008bfe6 | probe |
| 2 | member | true | 1794581989440.7 | post_actor | 76013208 | deae923d2ff0 | probe |

## Findings

- none

## Cleanup

- {"disposable_instructions_club_id_sha256_12":"f13044b76f77","disposable_instructions_session_id_sha256_12":"48929c359009","canary_instr_a_sha256_12":"5fb28e6e56e7","canary_instr_b_sha256_12":"d100d94fcf17","disposable_instructions_club_created":true,"disposable_instructions_session_created":true,"disposable_instructions_removed":true,"disposable_instructions_verified_absent":true,"disposable_instructions_cleanup_verified":true,"zero_mutation_verified":true,"baseline_fingerprint_equal":true,"public_rows_schema_roles_equal":true,"auth_rows_excluded":true,"mutation_counts":{"payments":0,"club_transactions":0,"audit_events":0,"operation_requests":0},"auth_refresh_sequence":[75,79],"public_tables":21,"public_rows":94,"before_fingerprint_sha256":"eb423faef3b7f7c5f154450c98ae0acffe3050a217e1dac43caec9e2dced9f5f","after_fingerprint_sha256":"1577a6301a15c6fab27a0abbeafbb0f62bf9e1f392c31ed96112c9b264523555","recovery_state_retained":false,"dump_dir_outside_repo":true,"raw_snapshots_remaining":0,"dumps_dir_removed":true,"chrome_profile_dir_removed":true,"ok":true}

## Limitations

- Covers ONLY synthetic non-rendered JSON keys (`canary_instr_a`, `canary_instr_b`) carried via `get_payment_instructions` into `receiverSnapshot`.
- Rendered strings (`bank_code`, `account_number`, `account_name`, `reference`) remain unattributed.
- Under dart2js minification, V8 strong-root reachability does not by itself prove Dart-level DTO attribution unless unminified retainer frames (`PaymentInstructions`, `FinanceProvider`, `_instructions`, `receiverSnapshot`) are observed.
- Does not cover `AuthProvider` listener graphs, Dart VM desktop/mobile, Firefox, or Safari.
