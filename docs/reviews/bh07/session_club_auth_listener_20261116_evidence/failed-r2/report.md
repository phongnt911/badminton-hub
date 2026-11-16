# BH-07 V2b — AuthProvider -> SessionProvider / ClubProvider Finite Listener Graph

- Gate: V2b — AuthProvider -> SessionProvider / ClubProvider finite listener graph
- Status: **FAIL** (verdict: **FAIL**)
- Overall listener gate: **FAIL**
- SessionProvider gate: **FAIL**
- ClubProvider core gate: **FAIL**
- ClubProvider currentBankAccount gate: **FAIL**
- Claim scope: `auth_provider_rooted_listener_to_session_and_club_provider_selected_fields_only`
- Observation mode: `hybrid_snapshot_plus_readonly_cdp_own_properties` (atomic_claim=false)
- Tested source: `e9af8d7b53c878e2d31deefbc7e6579ca2038c98` (git dirty: false)
- Same document across cycles: false
- Source binding sha256: `e061096293c9b0fd742e2325ff3e0c10de177dfb3a8fb61642dc22bc8ac66e57`
- Selected SessionProvider fields: `_currentSessionId`, `_currentSession` (Session0), `_session_provider$_history` (SessionHistoryPage)
- Selected ClubProvider fields: `_currentClubId`, `_currentClub` (Club), `_currentBankAccount` (BankAccount)

## Cycles & Epochs (2 cycles / 8 epochs)

| cycle | actor | same doc | epoch | snap sha12 | overall | session | club core | club bank |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | cohost | true | baseline | 74c27c467b34 | NOT_RUN_LAZY | PASS | NOT_RUN_LAZY | NOT_RUN_LAZY |
| 1 | cohost | true | owner_active | 647a26018798 | PASS | PASS | PASS | NOT_RUN |
| 1 | cohost | true | post_logout | 83451db7ee66 | PASS | PASS | PASS | PASS |
| 1 | cohost | true | post_actor | 699a590971a6 | FAIL | FAIL | FAIL | FAIL |

## Findings

- cycle 1 post_actor listener_graph FAIL: slot_3_invalid_prototype_method_flags

## Cleanup

- {"disposable_instructions_club_id_sha256_12":"e94e6a82b5cf","disposable_instructions_session_id_sha256_12":"ed0f1adf1dff","canary_instr_a_sha256_12":"ff66c72c5d4e","canary_instr_b_sha256_12":"9f75ac536d06","disposable_instructions_club_created":true,"disposable_instructions_session_created":true,"disposable_instructions_removed":true,"disposable_instructions_verified_absent":true,"disposable_instructions_cleanup_verified":true,"zero_mutation_verified":true,"baseline_fingerprint_equal":true,"public_rows_schema_roles_equal":true,"auth_rows_excluded":true,"mutation_counts":{"payments":0,"club_transactions":0,"audit_events":0,"operation_requests":0},"auth_refresh_sequence":[88,90],"public_tables":21,"public_rows":94,"before_fingerprint_sha256":"c465cdb928bcada8edeb08363e3660a4b6d7999deada2342363ce7d536352e49","after_fingerprint_sha256":"10c0e38a53d75f03434ecfee8f936df68bbd41bc916aba4319110bf7bd988a55","recovery_state_retained":false,"dump_dir_outside_repo":true,"raw_snapshots_remaining":0,"dumps_dir_removed":true,"chrome_profile_dir_removed":true,"ok":true}

## Claim Limits

- Covers ONLY AuthProvider -> SessionProvider (`_currentSessionId`, `_currentSession`, `_session_provider$_history`) and AuthProvider -> ClubProvider (`_currentClubId`, `_currentClub`, `_currentBankAccount`) in Chromium/Edge V8 heap + CDP own-properties.
- Does NOT certify uninspected SessionProvider/ClubProvider fields (`_mySessions`, `_publicSessions`, `_currentPlayers`, `_clubs`, `_currentMembers`, `_rosterMembers`), full `auth_listeners`, other providers, or native mobile/desktop VMs.
- Hybrid snapshot + CDP own-property counters are explicitly non-atomic (`atomic_claim: false`).
- If `club_bank_account_gate` is `NOT_RUN`, existing disposable instructions fixture created no `club_bank_accounts` row for its disposable club; do not infer `BankAccount` clear coverage without extending the disposable fixture.
