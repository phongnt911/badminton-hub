# V2b — app-profile heap / in-memory retention after actor switch

- Gate: V2b — app-profile Dart heap / in-memory retention after actor switch
- Reference: docs/reviews/bh07/bh07_readiness.md §4.4
- Status: **RUN** (verdict PASS)
- Tested source: `86181de1df03e11b3ad537f1024405724db83bfb` (git dirty: false)
- Measurement surface: Flutter Web profile build + Chrome DevTools Protocol HeapProfiler (V8 heap snapshot)
- Oracle: fixture sentinel strings counted in live V8 heap snapshots; no class-name dependency
- Build: mode=profile reused=false artifacts=39 served_match=true
- Chrome: Chrome/155.0.8059.85; Flutter: Flutter 3.47.6 • channel stable • https://github.com/flutter/flutter.git

## Sentinels (values never published)

| sentinel | kind | class | length | sha256[:12] |
| --- | --- | --- | --- | --- |
| bank | club bank account number (Owner-private, digits only) | bank, not rendered, not distinctive | 10 | 65dce15efcc4 |
| receiver | bank account holder name (loaded by payment instructions, not the Owner surface) | bank, not rendered, distinctive | 21 | bd84fa404410 |
| expense | posted session expense title rendered as widget text | finance, rendered, distinctive | 16 | 41a394dd2dcd |
| expense_id | posted session expense id returned by get_session_finance (never rendered) | finance, not rendered, distinctive | 36 | 7b5ed5cb05a0 |
| expense2 | second posted expense title rendered as widget text (run-only fixture row) | finance, rendered, distinctive | 24 | 411b6a441fb6 |
| expense_id_2 | second posted expense id from get_session_finance (never rendered) | finance, not rendered, distinctive | 36 | f4c5b2af20ea |
| player_a | session player id of the seeded roster (never rendered) | identity, not rendered, distinctive | 36 | e3382947f391 |
| player_b | second session player id of the seeded roster (never rendered) | identity, not rendered, distinctive | 36 | c5383f9762b9 |
| probe | detector sanity marker set on window | control, not rendered, distinctive | 25 | 99a38e1332e8 |

## Cycles

| cycle | actor path | same document | epoch | snapshot bytes | snapshot sha256[:12] | present sentinels |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Owner -> logout -> cohost | true | baseline | 58402838 | dd0e6dbc6c67 | probe |
| 1 | Owner -> logout -> cohost | true | owner_active | 84385807 | 5b58af247f11 | bank, expense, expense_id, expense2, expense_id_2, player_a, player_b, probe |
| 1 | Owner -> logout -> cohost | true | post_logout | 68893891 | b97b6e9e8fa9 | expense, expense2, probe |
| 1 | Owner -> logout -> cohost | true | post_actor | 81936710 | 4533c589b318 | expense, expense2, player_a, player_b, probe |
| 2 | Owner -> logout -> member | true | baseline | 58297272 | 41bd14f71d0d | probe |
| 2 | Owner -> logout -> member | true | owner_active | 84565723 | 722d2baa57a6 | bank, expense, expense_id, expense2, expense_id_2, player_a, player_b, probe |
| 2 | Owner -> logout -> member | true | post_logout | 69018719 | a39b7ce1b592 | expense, expense2, probe |
| 2 | Owner -> logout -> member | true | post_actor | 73428861 | 65769a814483 | expense, expense2, probe |

## Retained paths

| cycle | epoch | sentinel | reachable | root kind | path length | path sha256[:12] |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | baseline | bank | false | n/a | n/a | n/a |
| 1 | baseline | expense | false | n/a | n/a | n/a |
| 1 | baseline | expense2 | false | n/a | n/a | n/a |
| 1 | baseline | expense_id | false | n/a | n/a | n/a |
| 1 | baseline | expense_id_2 | false | n/a | n/a | n/a |
| 1 | baseline | player_a | false | n/a | n/a | n/a |
| 1 | baseline | player_b | false | n/a | n/a | n/a |
| 1 | baseline | probe | true | gc_roots | 5 | 04b7b0cc3e88 |
| 1 | baseline | receiver | false | n/a | n/a | n/a |
| 1 | owner_active | bank | true | gc_roots | 17 | aff8ab376c6c |
| 1 | owner_active | expense | true | gc_roots | 12 | 5ae7d1eb096c |
| 1 | owner_active | expense2 | true | gc_roots | 12 | 5ae7d1eb096c |
| 1 | owner_active | expense_id | true | gc_roots | 20 | 66ec3dae6c33 |
| 1 | owner_active | expense_id_2 | true | gc_roots | 20 | 66ec3dae6c33 |
| 1 | owner_active | player_a | true | gc_roots | 18 | 9d37b9ebd8c4 |
| 1 | owner_active | player_b | true | gc_roots | 18 | 9d37b9ebd8c4 |
| 1 | owner_active | probe | true | gc_roots | 5 | 7d0081a8c5d4 |
| 1 | owner_active | receiver | false | n/a | n/a | n/a |
| 1 | post_logout | bank | false | n/a | n/a | n/a |
| 1 | post_logout | expense | true | gc_roots | 12 | 5ae7d1eb096c |
| 1 | post_logout | expense2 | true | gc_roots | 12 | 5ae7d1eb096c |
| 1 | post_logout | expense_id | false | n/a | n/a | n/a |
| 1 | post_logout | expense_id_2 | false | n/a | n/a | n/a |
| 1 | post_logout | player_a | false | n/a | n/a | n/a |
| 1 | post_logout | player_b | false | n/a | n/a | n/a |
| 1 | post_logout | probe | true | gc_roots | 5 | 7d0081a8c5d4 |
| 1 | post_logout | receiver | false | n/a | n/a | n/a |
| 1 | post_actor | bank | false | n/a | n/a | n/a |
| 1 | post_actor | expense | true | gc_roots | 12 | 5ae7d1eb096c |
| 1 | post_actor | expense2 | true | gc_roots | 12 | 5ae7d1eb096c |
| 1 | post_actor | expense_id | false | n/a | n/a | n/a |
| 1 | post_actor | expense_id_2 | false | n/a | n/a | n/a |
| 1 | post_actor | player_a | true | gc_roots | 18 | 9d37b9ebd8c4 |
| 1 | post_actor | player_b | true | gc_roots | 18 | 9d37b9ebd8c4 |
| 1 | post_actor | probe | true | gc_roots | 5 | 7d0081a8c5d4 |
| 1 | post_actor | receiver | false | n/a | n/a | n/a |
| 2 | baseline | bank | false | n/a | n/a | n/a |
| 2 | baseline | expense | false | n/a | n/a | n/a |
| 2 | baseline | expense2 | false | n/a | n/a | n/a |
| 2 | baseline | expense_id | false | n/a | n/a | n/a |
| 2 | baseline | expense_id_2 | false | n/a | n/a | n/a |
| 2 | baseline | player_a | false | n/a | n/a | n/a |
| 2 | baseline | player_b | false | n/a | n/a | n/a |
| 2 | baseline | probe | true | gc_roots | 5 | 04b7b0cc3e88 |
| 2 | baseline | receiver | false | n/a | n/a | n/a |
| 2 | owner_active | bank | true | gc_roots | 17 | aff8ab376c6c |
| 2 | owner_active | expense | true | gc_roots | 12 | 5ae7d1eb096c |
| 2 | owner_active | expense2 | true | gc_roots | 12 | 5ae7d1eb096c |
| 2 | owner_active | expense_id | true | gc_roots | 20 | 66ec3dae6c33 |
| 2 | owner_active | expense_id_2 | true | gc_roots | 20 | 66ec3dae6c33 |
| 2 | owner_active | player_a | true | gc_roots | 18 | 9d37b9ebd8c4 |
| 2 | owner_active | player_b | true | gc_roots | 18 | 9d37b9ebd8c4 |
| 2 | owner_active | probe | true | gc_roots | 5 | 7d0081a8c5d4 |
| 2 | owner_active | receiver | false | n/a | n/a | n/a |
| 2 | post_logout | bank | false | n/a | n/a | n/a |
| 2 | post_logout | expense | true | gc_roots | 12 | 5ae7d1eb096c |
| 2 | post_logout | expense2 | true | gc_roots | 12 | 5ae7d1eb096c |
| 2 | post_logout | expense_id | false | n/a | n/a | n/a |
| 2 | post_logout | expense_id_2 | false | n/a | n/a | n/a |
| 2 | post_logout | player_a | false | n/a | n/a | n/a |
| 2 | post_logout | player_b | false | n/a | n/a | n/a |
| 2 | post_logout | probe | true | gc_roots | 5 | 7d0081a8c5d4 |
| 2 | post_logout | receiver | false | n/a | n/a | n/a |
| 2 | post_actor | bank | false | n/a | n/a | n/a |
| 2 | post_actor | expense | true | gc_roots | 12 | 5ae7d1eb096c |
| 2 | post_actor | expense2 | true | gc_roots | 12 | 5ae7d1eb096c |
| 2 | post_actor | expense_id | false | n/a | n/a | n/a |
| 2 | post_actor | expense_id_2 | false | n/a | n/a | n/a |
| 2 | post_actor | player_a | false | n/a | n/a | n/a |
| 2 | post_actor | player_b | false | n/a | n/a | n/a |
| 2 | post_actor | probe | true | gc_roots | 5 | 7d0081a8c5d4 |
| 2 | post_actor | receiver | false | n/a | n/a | n/a |

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
| 1 | post_logout | expense | gc_roots | 12 | 5ae7d1eb096c |
| 1 | post_logout | expense2 | gc_roots | 12 | 5ae7d1eb096c |
| 1 | post_actor | expense | gc_roots | 12 | 5ae7d1eb096c |
| 1 | post_actor | expense2 | gc_roots | 12 | 5ae7d1eb096c |
| 2 | post_logout | expense | gc_roots | 12 | 5ae7d1eb096c |
| 2 | post_logout | expense2 | gc_roots | 12 | 5ae7d1eb096c |
| 2 | post_actor | expense | gc_roots | 12 | 5ae7d1eb096c |
| 2 | post_actor | expense2 | gc_roots | 12 | 5ae7d1eb096c |

## Notes

- cycle 1: owner_active: sentinel bank is not distinctive; a hit can be a substring of an unrelated value, so it is reported and never gated
- cycle 1: post_actor: sentinel player_a is retained after the actor switch; whether the new actor is entitled to fetch it is not established by this measurement, so it is published with its path and never gated
- cycle 1: post_actor: sentinel player_b is retained after the actor switch; whether the new actor is entitled to fetch it is not established by this measurement, so it is published with its path and never gated
- cycle 2: owner_active: sentinel bank is not distinctive; a hit can be a substring of an unrelated value, so it is reported and never gated

## Findings

- none

## Cleanup

- {"dump_dir_outside_repo":true,"raw_snapshots_remaining":0,"dumps_dir_removed":true,"chrome_profile_dir_removed":true,"run_only_fixture_created":true,"run_only_fixture_id_sha256_12":"f4c5b2af20ea","extra_expense_removed":true,"extra_expense_verified_absent":true,"ok":true}

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
