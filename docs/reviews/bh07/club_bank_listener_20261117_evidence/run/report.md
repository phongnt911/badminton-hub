# BH-07 V2b — AuthProvider -> SessionProvider / ClubProvider Finite Listener Graph

- Gate: V2b — AuthProvider -> SessionProvider / ClubProvider finite listener graph
- Status: **RUN** (verdict: **PASS**)
- Overall listener gate: **PASS**
- SessionProvider gate: **PASS**
- ClubProvider core gate: **PASS**
- ClubProvider currentBankAccount gate: **PASS**
- Claim scope: `auth_provider_rooted_listener_to_session_and_club_provider_selected_fields_only`
- Observation mode: `hybrid_snapshot_plus_readonly_cdp_own_properties` (atomic_claim=false)
- Tested source: `7614c6a79984e3d73653cc5ec4cbd0e4164dd8a5` (git dirty: false)
- Same document across cycles: true
- Source binding sha256: `e061096293c9b0fd742e2325ff3e0c10de177dfb3a8fb61642dc22bc8ac66e57`
- Selected SessionProvider fields: `_currentSessionId`, `_currentSession` (Session0), `_session_provider$_history` (SessionHistoryPage)
- Selected ClubProvider fields: `_currentClubId`, `_currentClub` (Club), `_currentBankAccount` (BankAccount)

## Cycles & Epochs (2 cycles / 8 epochs)

| cycle | actor | same doc | epoch | snap sha12 | overall | session | club core | club bank |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | cohost | true | baseline | dd3a88bc7cca | NOT_RUN_LAZY | PASS | NOT_RUN_LAZY | NOT_RUN_LAZY |
| 1 | cohost | true | owner_active | 84e9e166e94e | PASS | PASS | PASS | PASS |
| 1 | cohost | true | post_logout | 7d7de180f22e | PASS | PASS | PASS | PASS |
| 1 | cohost | true | post_actor | 5af22145d04f | PASS | PASS | PASS | PASS |
| 2 | member | true | baseline | 2bb96f73b1df | PASS | PASS | PASS | PASS |
| 2 | member | true | owner_active | 3002183dca54 | PASS | PASS | PASS | PASS |
| 2 | member | true | post_logout | 6ea3601dd761 | PASS | PASS | PASS | PASS |
| 2 | member | true | post_actor | 8366c34ef169 | PASS | PASS | PASS | PASS |

## Findings

- none

## Cleanup

- {"disposable_instructions_club_id_sha256_12":"ceb740eb0367","disposable_instructions_session_id_sha256_12":"1ff36ab9d958","canary_instr_a_sha256_12":"1c5a7421efc1","canary_instr_b_sha256_12":"f38b63c53e31","disposable_instructions_club_created":true,"disposable_instructions_session_created":true,"disposable_instructions_removed":true,"disposable_instructions_verified_absent":true,"disposable_instructions_cleanup_verified":true,"zero_mutation_verified":true,"baseline_fingerprint_equal":true,"public_rows_schema_roles_equal":true,"auth_rows_excluded":true,"disposable_instructions_club_bank_included":true,"disposable_instructions_club_bank_id_sha256_12":"92c487761e09","disposable_instructions_club_bank_account_number_sha256_12":"4e55b6d64804","disposable_instructions_club_bank_account_name_sha256_12":"f14ff607f8fe","disposable_instructions_club_bank_created":true,"disposable_instructions_club_bank_removed":true,"disposable_instructions_club_bank_verified_absent":true,"mutation_counts":{"payments":0,"club_transactions":0,"audit_events":0,"operation_requests":0},"auth_refresh_sequence":[94,98],"public_tables":21,"public_rows":94,"before_fingerprint_sha256":"5f0ad1a9ff2779ed2f5af832742c0fa6b79923ebcd0823098c37f4ab8da7d1ba","after_fingerprint_sha256":"5fab178fa419c27d3f3da5623100226153b8117c137330bebc837f6bdb717067","recovery_state_retained":false,"dump_dir_outside_repo":true,"raw_snapshots_remaining":0,"dumps_dir_removed":true,"chrome_profile_dir_removed":true,"ok":true}

## Claim Limits

- Covers ONLY AuthProvider -> SessionProvider (`_currentSessionId`, `_currentSession`, `_session_provider$_history`) and AuthProvider -> ClubProvider (`_currentClubId`, `_currentClub`, `_currentBankAccount`) in Chromium/Edge V8 heap + CDP own-properties.
- Does NOT certify uninspected SessionProvider/ClubProvider fields (`_mySessions`, `_publicSessions`, `_currentPlayers`, `_clubs`, `_currentMembers`, `_rosterMembers`), full `auth_listeners`, other providers, or native mobile/desktop VMs.
- Hybrid snapshot + CDP own-property counters are explicitly non-atomic (`atomic_claim: false`).
- If `club_bank_account_gate` is `NOT_RUN`, existing disposable instructions fixture created no `club_bank_accounts` row for its disposable club; do not infer `BankAccount` clear coverage without extending the disposable fixture.
