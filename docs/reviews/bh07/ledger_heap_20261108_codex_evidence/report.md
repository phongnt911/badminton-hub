# V2b — app-profile heap / in-memory retention after actor switch

- Gate: V2b — app-profile Dart heap / in-memory retention after actor switch
- Reference: docs/reviews/bh07/bh07_readiness.md §4.4
- Status: **RUN** (verdict PASS)
- Tested source: `b25aaef1878b42e625c93d247b246237ba5cfd9b` (git dirty: false)
- Measurement surface: Flutter Web profile build + Chrome DevTools Protocol HeapProfiler (V8 heap snapshot)
- Oracle: fixture sentinel strings counted in live V8 heap snapshots; no class-name dependency
- Build: mode=profile reused=false artifacts=39 served_match=true
- Chrome: Chrome/156.0.8078.80; Flutter: Flutter 3.47.6 • channel stable • https://github.com/flutter/flutter.git

## Sentinels (values never published)

| sentinel | kind | class | length | sha256[:12] |
| --- | --- | --- | --- | --- |
| bank | disposable club bank account number rendered as widget text | bank, rendered, distinctive | 16 | 6474ebc415b2 |
| receiver | disposable club bank account holder name rendered as widget text | bank, rendered, distinctive | 22 | 6219f64bbb47 |
| expense | posted session expense title rendered as widget text | finance, rendered, distinctive | 16 | 41a394dd2dcd |
| expense_id | posted session expense id returned by get_session_finance (never rendered) | finance, not rendered, distinctive | 36 | 7b5ed5cb05a0 |
| expense2 | second posted expense title rendered as widget text (run-only fixture row) | finance, rendered, distinctive | 24 | 6af2bba958d0 |
| expense_id_2 | second posted expense id from get_session_finance (never rendered) | finance, not rendered, distinctive | 36 | bec63693f431 |
| payment_id | submitted session payment id from get_session_finance (never rendered) | finance, not rendered, distinctive | 36 | 54552c72b5d6 |
| payment_ref | submitted session payment reference rendered as widget text | finance, rendered, distinctive | 20 | 77c6cb2a59e6 |
| player_a | session player id of the seeded roster (never rendered) | identity, not rendered, distinctive | 36 | e3382947f391 |
| player_b | second session player id of the seeded roster (never rendered) | identity, not rendered, distinctive | 36 | c5383f9762b9 |
| probe | detector sanity marker set on window | control, not rendered, distinctive | 25 | d770882dd872 |
| bank_account_id | disposable club bank account ID from club_bank_accounts (never rendered) | finance, not rendered, distinctive | 36 | ca6c776e96fa |
| ledger_transaction_id | disposable club ledger transaction ID from club_transactions (never rendered) | finance, not rendered, distinctive | 36 | 377c66b4a07a |

## Cycles

| cycle | actor path | same document | epoch | snapshot bytes | snapshot sha256[:12] | present sentinels |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Owner -> logout -> cohost | true | baseline | 60130252 | bea55866a5b5 | probe |
| 1 | Owner -> logout -> cohost | true | owner_active | 78115635 | d54bfc4002ee | bank, receiver, expense, expense_id, expense2, expense_id_2, payment_id, payment_ref, player_a, player_b, probe, bank_account_id, ledger_transaction_id |
| 1 | Owner -> logout -> cohost | true | post_logout | 71306786 | d82b0dc6e7f2 | bank, receiver, expense, expense2, payment_ref, probe |
| 1 | Owner -> logout -> cohost | true | post_actor | 84121726 | b0ab0367467d | bank, receiver, expense, expense2, payment_ref, player_a, player_b, probe |
| 2 | Owner -> logout -> member | true | baseline | 60125217 | e970d039b6bc | probe |
| 2 | Owner -> logout -> member | true | owner_active | 78045089 | 6c7c11f2a9f2 | bank, receiver, expense, expense_id, expense2, expense_id_2, payment_id, payment_ref, player_a, player_b, probe, bank_account_id, ledger_transaction_id |
| 2 | Owner -> logout -> member | true | post_logout | 71278930 | 10f279d5c356 | bank, receiver, expense, expense2, payment_ref, probe |
| 2 | Owner -> logout -> member | true | post_actor | 76536860 | 3cb6db8f655f | bank, receiver, expense, expense2, payment_ref, probe |

## Retained paths

| cycle | epoch | sentinel | reachable | root kind | path length | path sha256[:12] |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | baseline | bank | false | n/a | n/a | n/a |
| 1 | baseline | bank_account_id | false | n/a | n/a | n/a |
| 1 | baseline | expense | false | n/a | n/a | n/a |
| 1 | baseline | expense2 | false | n/a | n/a | n/a |
| 1 | baseline | expense_id | false | n/a | n/a | n/a |
| 1 | baseline | expense_id_2 | false | n/a | n/a | n/a |
| 1 | baseline | ledger_transaction_id | false | n/a | n/a | n/a |
| 1 | baseline | payment_id | false | n/a | n/a | n/a |
| 1 | baseline | payment_ref | false | n/a | n/a | n/a |
| 1 | baseline | player_a | false | n/a | n/a | n/a |
| 1 | baseline | player_b | false | n/a | n/a | n/a |
| 1 | baseline | probe | true | gc_roots | 5 | 04b7b0cc3e88 |
| 1 | baseline | receiver | false | n/a | n/a | n/a |
| 1 | owner_active | bank | true | gc_roots | 12 | 5ae7d1eb096c |
| 1 | owner_active | bank_account_id | true | gc_roots | 18 | 6a327da19ff1 |
| 1 | owner_active | expense | true | gc_roots | 12 | 5ae7d1eb096c |
| 1 | owner_active | expense2 | true | gc_roots | 12 | 5ae7d1eb096c |
| 1 | owner_active | expense_id | true | gc_roots | 21 | df330cdc441d |
| 1 | owner_active | expense_id_2 | true | gc_roots | 21 | df330cdc441d |
| 1 | owner_active | ledger_transaction_id | true | gc_roots | 18 | 4609c34fec22 |
| 1 | owner_active | payment_id | true | gc_roots | 21 | 57e3b232e780 |
| 1 | owner_active | payment_ref | true | gc_roots | 12 | 5ae7d1eb096c |
| 1 | owner_active | player_a | true | gc_roots | 19 | bbdb767b01ab |
| 1 | owner_active | player_b | true | gc_roots | 19 | bbdb767b01ab |
| 1 | owner_active | probe | true | gc_roots | 5 | 7d0081a8c5d4 |
| 1 | owner_active | receiver | true | gc_roots | 12 | 5ae7d1eb096c |
| 1 | post_logout | bank | true | gc_roots | 12 | 5ae7d1eb096c |
| 1 | post_logout | bank_account_id | false | n/a | n/a | n/a |
| 1 | post_logout | expense | true | gc_roots | 12 | 5ae7d1eb096c |
| 1 | post_logout | expense2 | true | gc_roots | 12 | 5ae7d1eb096c |
| 1 | post_logout | expense_id | false | n/a | n/a | n/a |
| 1 | post_logout | expense_id_2 | false | n/a | n/a | n/a |
| 1 | post_logout | ledger_transaction_id | false | n/a | n/a | n/a |
| 1 | post_logout | payment_id | false | n/a | n/a | n/a |
| 1 | post_logout | payment_ref | true | gc_roots | 12 | 5ae7d1eb096c |
| 1 | post_logout | player_a | false | n/a | n/a | n/a |
| 1 | post_logout | player_b | false | n/a | n/a | n/a |
| 1 | post_logout | probe | true | gc_roots | 5 | 7d0081a8c5d4 |
| 1 | post_logout | receiver | true | gc_roots | 12 | 5ae7d1eb096c |
| 1 | post_actor | bank | true | gc_roots | 12 | 5ae7d1eb096c |
| 1 | post_actor | bank_account_id | false | n/a | n/a | n/a |
| 1 | post_actor | expense | true | gc_roots | 12 | 5ae7d1eb096c |
| 1 | post_actor | expense2 | true | gc_roots | 12 | 5ae7d1eb096c |
| 1 | post_actor | expense_id | false | n/a | n/a | n/a |
| 1 | post_actor | expense_id_2 | false | n/a | n/a | n/a |
| 1 | post_actor | ledger_transaction_id | false | n/a | n/a | n/a |
| 1 | post_actor | payment_id | false | n/a | n/a | n/a |
| 1 | post_actor | payment_ref | true | gc_roots | 12 | 5ae7d1eb096c |
| 1 | post_actor | player_a | true | gc_roots | 18 | 9d37b9ebd8c4 |
| 1 | post_actor | player_b | true | gc_roots | 18 | 9d37b9ebd8c4 |
| 1 | post_actor | probe | true | gc_roots | 5 | 7d0081a8c5d4 |
| 1 | post_actor | receiver | true | gc_roots | 12 | 5ae7d1eb096c |
| 2 | baseline | bank | false | n/a | n/a | n/a |
| 2 | baseline | bank_account_id | false | n/a | n/a | n/a |
| 2 | baseline | expense | false | n/a | n/a | n/a |
| 2 | baseline | expense2 | false | n/a | n/a | n/a |
| 2 | baseline | expense_id | false | n/a | n/a | n/a |
| 2 | baseline | expense_id_2 | false | n/a | n/a | n/a |
| 2 | baseline | ledger_transaction_id | false | n/a | n/a | n/a |
| 2 | baseline | payment_id | false | n/a | n/a | n/a |
| 2 | baseline | payment_ref | false | n/a | n/a | n/a |
| 2 | baseline | player_a | false | n/a | n/a | n/a |
| 2 | baseline | player_b | false | n/a | n/a | n/a |
| 2 | baseline | probe | true | gc_roots | 5 | 04b7b0cc3e88 |
| 2 | baseline | receiver | false | n/a | n/a | n/a |
| 2 | owner_active | bank | true | gc_roots | 12 | 5ae7d1eb096c |
| 2 | owner_active | bank_account_id | true | gc_roots | 18 | 6a327da19ff1 |
| 2 | owner_active | expense | true | gc_roots | 12 | 5ae7d1eb096c |
| 2 | owner_active | expense2 | true | gc_roots | 12 | 5ae7d1eb096c |
| 2 | owner_active | expense_id | true | gc_roots | 20 | 66ec3dae6c33 |
| 2 | owner_active | expense_id_2 | true | gc_roots | 20 | 66ec3dae6c33 |
| 2 | owner_active | ledger_transaction_id | true | gc_roots | 18 | 4609c34fec22 |
| 2 | owner_active | payment_id | true | gc_roots | 20 | ed1a89da694e |
| 2 | owner_active | payment_ref | true | gc_roots | 12 | 5ae7d1eb096c |
| 2 | owner_active | player_a | true | gc_roots | 19 | bbdb767b01ab |
| 2 | owner_active | player_b | true | gc_roots | 19 | bbdb767b01ab |
| 2 | owner_active | probe | true | gc_roots | 5 | 7d0081a8c5d4 |
| 2 | owner_active | receiver | true | gc_roots | 12 | 5ae7d1eb096c |
| 2 | post_logout | bank | true | gc_roots | 12 | 5ae7d1eb096c |
| 2 | post_logout | bank_account_id | false | n/a | n/a | n/a |
| 2 | post_logout | expense | true | gc_roots | 12 | 5ae7d1eb096c |
| 2 | post_logout | expense2 | true | gc_roots | 12 | 5ae7d1eb096c |
| 2 | post_logout | expense_id | false | n/a | n/a | n/a |
| 2 | post_logout | expense_id_2 | false | n/a | n/a | n/a |
| 2 | post_logout | ledger_transaction_id | false | n/a | n/a | n/a |
| 2 | post_logout | payment_id | false | n/a | n/a | n/a |
| 2 | post_logout | payment_ref | true | gc_roots | 12 | 5ae7d1eb096c |
| 2 | post_logout | player_a | false | n/a | n/a | n/a |
| 2 | post_logout | player_b | false | n/a | n/a | n/a |
| 2 | post_logout | probe | true | gc_roots | 5 | 7d0081a8c5d4 |
| 2 | post_logout | receiver | true | gc_roots | 12 | 5ae7d1eb096c |
| 2 | post_actor | bank | true | gc_roots | 12 | 5ae7d1eb096c |
| 2 | post_actor | bank_account_id | false | n/a | n/a | n/a |
| 2 | post_actor | expense | true | gc_roots | 12 | 5ae7d1eb096c |
| 2 | post_actor | expense2 | true | gc_roots | 12 | 5ae7d1eb096c |
| 2 | post_actor | expense_id | false | n/a | n/a | n/a |
| 2 | post_actor | expense_id_2 | false | n/a | n/a | n/a |
| 2 | post_actor | ledger_transaction_id | false | n/a | n/a | n/a |
| 2 | post_actor | payment_id | false | n/a | n/a | n/a |
| 2 | post_actor | payment_ref | true | gc_roots | 12 | 5ae7d1eb096c |
| 2 | post_actor | player_a | false | n/a | n/a | n/a |
| 2 | post_actor | player_b | false | n/a | n/a | n/a |
| 2 | post_actor | probe | true | gc_roots | 5 | 7d0081a8c5d4 |
| 2 | post_actor | receiver | true | gc_roots | 12 | 5ae7d1eb096c |

## Residual risks

Values still reachable after the Owner session ended. They are published **without
attribution**: this walk proves a value is retained, not which component retained it.

- `class: rendered` only records that the value is laid out as widget text. The shared web
  engine does keep a text segmentation cache, but this measurement does not prove that cache
  — rather than an app provider or controller — is the retainer.
- `class: identity` records shared-club data (roster ids) still reachable after the switch. It
  does not show that the new actor, or the signed-out Guest screen, was entitled to fetch it.

| cycle | epoch | sentinel | root kind | path length | path sha256[:12] |
| --- | --- | --- | --- | --- | --- |
| 1 | post_logout | bank | gc_roots | 12 | 5ae7d1eb096c |
| 1 | post_logout | expense | gc_roots | 12 | 5ae7d1eb096c |
| 1 | post_logout | expense2 | gc_roots | 12 | 5ae7d1eb096c |
| 1 | post_logout | payment_ref | gc_roots | 12 | 5ae7d1eb096c |
| 1 | post_logout | receiver | gc_roots | 12 | 5ae7d1eb096c |
| 1 | post_actor | bank | gc_roots | 12 | 5ae7d1eb096c |
| 1 | post_actor | expense | gc_roots | 12 | 5ae7d1eb096c |
| 1 | post_actor | expense2 | gc_roots | 12 | 5ae7d1eb096c |
| 1 | post_actor | payment_ref | gc_roots | 12 | 5ae7d1eb096c |
| 1 | post_actor | receiver | gc_roots | 12 | 5ae7d1eb096c |
| 2 | post_logout | bank | gc_roots | 12 | 5ae7d1eb096c |
| 2 | post_logout | expense | gc_roots | 12 | 5ae7d1eb096c |
| 2 | post_logout | expense2 | gc_roots | 12 | 5ae7d1eb096c |
| 2 | post_logout | payment_ref | gc_roots | 12 | 5ae7d1eb096c |
| 2 | post_logout | receiver | gc_roots | 12 | 5ae7d1eb096c |
| 2 | post_actor | bank | gc_roots | 12 | 5ae7d1eb096c |
| 2 | post_actor | expense | gc_roots | 12 | 5ae7d1eb096c |
| 2 | post_actor | expense2 | gc_roots | 12 | 5ae7d1eb096c |
| 2 | post_actor | payment_ref | gc_roots | 12 | 5ae7d1eb096c |
| 2 | post_actor | receiver | gc_roots | 12 | 5ae7d1eb096c |

## Notes

- cycle 1: post_actor: sentinel player_a is retained after the actor switch; whether the new actor is entitled to fetch it is not established by this measurement, so it is published with its path and never gated
- cycle 1: post_actor: sentinel player_b is retained after the actor switch; whether the new actor is entitled to fetch it is not established by this measurement, so it is published with its path and never gated

## Findings

- none

## Cleanup

- {"dump_dir_outside_repo":true,"raw_snapshots_remaining":0,"dumps_dir_removed":true,"chrome_profile_dir_removed":true,"ok":true,"run_only_fixture_created":true,"run_only_fixture_id_sha256_12":"bec63693f431","extra_expense_removed":true,"extra_expense_verified_absent":true,"run_only_payment_created":true,"run_only_payment_id_sha256_12":"54552c72b5d6","extra_payment_removed":true,"extra_payment_verified_absent":true,"disposable_ledger_id_sha256_12":"377c66b4a07a","disposable_ledger_created":true,"disposable_ledger_removed":true,"disposable_ledger_verified_absent":true,"disposable_club_id_sha256_12":"211ecfa0f3de","disposable_bank_id_sha256_12":"ca6c776e96fa","disposable_club_created":true,"disposable_bank_created":true,"disposable_club_removed":true,"disposable_bank_removed":true,"disposable_club_verified_absent":true,"disposable_bank_verified_absent":true}

## Limitations

- Web *profile* build measures the dart2js/V8 heap, not the Dart VM heap of a desktop/mobile build;
  no Visual Studio or Android SDK is installed on this machine, so the VM-service path is NOT RUN.
- Only *unrendered, distinctive, finance-scoped* values gate the verdict. Rendered text is
  published as an unattributed residual risk instead of being gated, and a short digit run can
  match inside an unrelated fixture UUID (see the `bank` notes). Shared-club roster ids are
  published with their paths; this measurement does not establish which actor may fetch them.
- The bank account holder name is only fetched by the player payment-instructions surface, so the
  Owner path never loads it; it is measured and reported as not loaded, not as coverage.
- Sentinels prove that specific Owner-private values are no longer reachable; they do not enumerate
  every retained object of the financial models, and only one path per value is published.
- Raw heap snapshots are written outside the repository, scanned once and deleted; only counts and
  short hashes are published.
