# V2b — PaymentInstructions synthetic receiverSnapshot heap retention

- Gate: V2b — PaymentInstructions synthetic receiverSnapshot heap retention
- Status: **FAIL** (verdict FAIL)
- Scoped verdict: **FAIL**
- PaymentInstructions coverage gate: UNKNOWN/NOT_RUN
- Attribution: root_reachability_measured=false; dto_attribution_proven=false (unproven_ordered_chain_mismatch)
- Source binding: verified (main.dart.js a20b3d22a011, FinanceProvider._instructions, PaymentInstructions.receiverSnapshot)
- Claim scope: narrow_rpc_payload_retention_only (synthetic receiverSnapshot keys only; no whole-model claim)
- Tested source: `c83764d79ccbc201f5bf603509b1c7316852fe87` (git dirty: false)
- Same document across cycles: false

## Sentinels (values never published)

| sentinel | scope | rendered | distinctive | length | sha256[:12] |
| --- | --- | --- | --- | --- | --- |
| canary_instr_a | finance | false | true | 36 | 2f65a979671c |
| canary_instr_b | finance | false | true | 36 | 96f1a7fb59ae |
| probe | control | false | true | 23 | 44f7ad608f24 |

## Cycles (8 epochs total across 2 cycles)

| cycle | actor | same document | timeOrigin | epoch | bytes | sha256[:12] | present |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | cohost | true | 1794608981351.9 | baseline | 60454522 | 37e912c139c2 | probe |
| 1 | cohost | true | 1794608981351.9 | owner_active | 84018433 | a6aee0a276d1 | canary_instr_a, canary_instr_b, probe |

## Findings

- cycle 1 owner_active listener_graph FAIL: finance_listener_wrong_method,finance_match_count:0!=expected:1

## Cleanup

- {"disposable_instructions_club_id_sha256_12":"0464a0f1ffa9","disposable_instructions_session_id_sha256_12":"6e1f9ad1175d","canary_instr_a_sha256_12":"2f65a979671c","canary_instr_b_sha256_12":"96f1a7fb59ae","disposable_instructions_club_created":true,"disposable_instructions_session_created":true,"disposable_instructions_removed":true,"disposable_instructions_verified_absent":true,"disposable_instructions_cleanup_verified":true,"zero_mutation_verified":true,"baseline_fingerprint_equal":true,"public_rows_schema_roles_equal":true,"auth_rows_excluded":true,"mutation_counts":{"payments":0,"club_transactions":0,"audit_events":0,"operation_requests":0},"auth_refresh_sequence":[83,84],"public_tables":21,"public_rows":94,"before_fingerprint_sha256":"a97bc62f61ec8c6c05a81a0fffce77ec9f4ed8b900ee0238b57c7bd6a276efae","after_fingerprint_sha256":"d640fd961dc008682af4d6bf5734fb1730845764091e0f604806bb6134da35e4","recovery_state_retained":false,"dump_dir_outside_repo":true,"raw_snapshots_remaining":0,"dumps_dir_removed":true,"chrome_profile_dir_removed":true,"ok":true}

## Limitations

- Covers ONLY synthetic non-rendered JSON keys (`canary_instr_a`, `canary_instr_b`) carried via `get_payment_instructions` into `receiverSnapshot` (no whole-model clean claim).
- Rendered strings (`bank_code`, `account_number`, `account_name`, `reference`) remain unattributed.
- Under dart2js compilation, V8 strong-root reachability proves Dart-level DTO attribution ONLY when served-artifact source binding (`main.dart.js` SHA + constructor/field validation) verifies an exact ordered retainer chain (`_provider$_value` -> bound instructions field -> bound `receiverSnapshot` field -> map edges).
- Does not cover `AuthProvider` listener graphs, Dart VM desktop/mobile, Firefox, or Safari.
