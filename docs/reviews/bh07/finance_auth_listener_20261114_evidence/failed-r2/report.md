# V2b — PaymentInstructions synthetic receiverSnapshot heap retention

- Gate: V2b — PaymentInstructions synthetic receiverSnapshot heap retention
- Status: **FAIL** (verdict FAIL)
- Scoped verdict: **FAIL**
- PaymentInstructions coverage gate: UNKNOWN/NOT_RUN
- Attribution: root_reachability_measured=false; dto_attribution_proven=false (unproven_ordered_chain_mismatch)
- Source binding: verified (main.dart.js a20b3d22a011, FinanceProvider._instructions, PaymentInstructions.receiverSnapshot)
- Claim scope: narrow_rpc_payload_retention_only (synthetic receiverSnapshot keys only; no whole-model claim)
- Tested source: `de00926ce2aa6013cba7bd95cf65c59557123d57` (git dirty: false)
- Same document across cycles: false

## Sentinels (values never published)

| sentinel | scope | rendered | distinctive | length | sha256[:12] |
| --- | --- | --- | --- | --- | --- |
| canary_instr_a | finance | false | true | 36 | b8ea344fe585 |
| canary_instr_b | finance | false | true | 36 | 20a621c0a01f |
| probe | control | false | true | 23 | 3e52026c24fb |

## Cycles (8 epochs total across 2 cycles)

| cycle | actor | same document | timeOrigin | epoch | bytes | sha256[:12] | present |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | cohost | false | 1794609164759.2 | baseline | 60336945 | 1033341298d8 | probe |

## Findings

- cycle 1 baseline listener_graph FAIL: slot_1_invalid_prototype_method_flags

## Cleanup

- {"disposable_instructions_club_id_sha256_12":"226c0aaf5a74","disposable_instructions_session_id_sha256_12":"216727015103","canary_instr_a_sha256_12":"b8ea344fe585","canary_instr_b_sha256_12":"20a621c0a01f","disposable_instructions_club_created":true,"disposable_instructions_session_created":true,"disposable_instructions_removed":true,"disposable_instructions_verified_absent":true,"disposable_instructions_cleanup_verified":true,"zero_mutation_verified":true,"baseline_fingerprint_equal":true,"public_rows_schema_roles_equal":true,"auth_rows_excluded":true,"mutation_counts":{"payments":0,"club_transactions":0,"audit_events":0,"operation_requests":0},"auth_refresh_sequence":[84,84],"public_tables":21,"public_rows":94,"before_fingerprint_sha256":"d640fd961dc008682af4d6bf5734fb1730845764091e0f604806bb6134da35e4","after_fingerprint_sha256":"d640fd961dc008682af4d6bf5734fb1730845764091e0f604806bb6134da35e4","recovery_state_retained":false,"dump_dir_outside_repo":true,"raw_snapshots_remaining":0,"dumps_dir_removed":true,"chrome_profile_dir_removed":true,"ok":true}

## Limitations

- Covers ONLY synthetic non-rendered JSON keys (`canary_instr_a`, `canary_instr_b`) carried via `get_payment_instructions` into `receiverSnapshot` (no whole-model clean claim).
- Rendered strings (`bank_code`, `account_number`, `account_name`, `reference`) remain unattributed.
- Under dart2js compilation, V8 strong-root reachability proves Dart-level DTO attribution ONLY when served-artifact source binding (`main.dart.js` SHA + constructor/field validation) verifies an exact ordered retainer chain (`_provider$_value` -> bound instructions field -> bound `receiverSnapshot` field -> map edges).
- Does not cover `AuthProvider` listener graphs, Dart VM desktop/mobile, Firefox, or Safari.
