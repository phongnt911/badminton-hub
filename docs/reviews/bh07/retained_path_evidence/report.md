# V2b — app-profile heap / in-memory retention after actor switch

- Gate: V2b — app-profile Dart heap / in-memory retention after actor switch
- Reference: docs/reviews/bh07/bh07_readiness.md §4.4
- Status: **RUN** (verdict PASS)
- Tested source: `66bda0e7e3e1c2e983110e26a6300f6685c3a450` (git dirty: false)
- Measurement surface: Flutter Web profile build + Chrome DevTools Protocol HeapProfiler (V8 heap snapshot)
- Oracle: fixture sentinel strings counted in live V8 heap snapshots; no class-name dependency
- Build: mode=profile reused=false artifacts=39 served_match=true
- Chrome: Chrome/155.0.8059.85; Flutter: Flutter 3.47.6 • channel stable • https://github.com/flutter/flutter.git

## Sentinels (values never published)

| sentinel | kind | class | length | sha256[:12] |
| --- | --- | --- | --- | --- |
| bank | club bank account number (Owner-private, digits only) | bank, not rendered, not distinctive | 10 | 65dce15efcc4 |
| receiver | bank account holder name (loaded by payment instructions, not the Owner surface) | bank, not rendered, distinctive | 21 | bd84fa404410 |
| expense | posted session expense title rendered as widget text | finance, rendered, distinctive | 18 | 8473a1c91ea5 |
| expense_id | posted session expense id returned by get_session_finance (never rendered) | finance, not rendered, distinctive | 36 | f6a217367f6d |
| expense2 | second posted expense title rendered as widget text (run-only fixture row) | finance, rendered, distinctive | 16 | 41a394dd2dcd |
| expense_id_2 | second posted expense id from get_session_finance (never rendered) | finance, not rendered, distinctive | 36 | 7b5ed5cb05a0 |
| player_a | session player id of the seeded roster (never rendered) | identity, not rendered, distinctive | 36 | e3382947f391 |
| player_b | second session player id of the seeded roster (never rendered) | identity, not rendered, distinctive | 36 | c5383f9762b9 |
| probe | detector sanity marker set on window | control, not rendered, distinctive | 25 | 10e11151dc4b |

## Cycles

| cycle | actor path | same document | epoch | snapshot bytes | snapshot sha256[:12] | present sentinels |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Owner -> logout -> cohost | true | baseline | 58341314 | 2f271097f7be | probe |
| 1 | Owner -> logout -> cohost | true | owner_active | 84449162 | bfe6cc8346df | bank, expense, expense_id, expense2, expense_id_2, player_a, player_b, probe |
| 1 | Owner -> logout -> cohost | true | post_logout | 69536305 | 40f499398324 | expense, expense2, probe |
| 1 | Owner -> logout -> cohost | true | post_actor | 81180305 | 75edf92e4dd9 | expense, expense2, player_a, player_b, probe |
| 2 | Owner -> logout -> member | true | baseline | 58482251 | 3750289c63e9 | probe |
| 2 | Owner -> logout -> member | true | owner_active | 84571686 | 484c3cfd5dad | bank, expense, expense_id, expense2, expense_id_2, player_a, player_b, probe |
| 2 | Owner -> logout -> member | true | post_logout | 69363418 | 4eb7e48694f4 | expense, expense2, probe |
| 2 | Owner -> logout -> member | true | post_actor | 73761306 | a70477e32d12 | expense, expense2, probe |

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
| 2 | owner_active | expense_id | true | gc_roots | 21 | df330cdc441d |
| 2 | owner_active | expense_id_2 | true | gc_roots | 21 | df330cdc441d |
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

Rendered text the Owner saw can stay in the web engine’s segmentation LRU after the app
dropped it. That retainer is engine-internal (flutter/engine web_ui text_fragmenter.dart),
so it is published here and never counted as app state by the gate.

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
- cycle 1: post_actor: sentinel player_a is shared-club identity data that the current actor is authorized to fetch; it is reported with its path and never gated
- cycle 1: post_actor: sentinel player_b is shared-club identity data that the current actor is authorized to fetch; it is reported with its path and never gated
- cycle 2: owner_active: sentinel bank is not distinctive; a hit can be a substring of an unrelated value, so it is reported and never gated

## Findings

- none

## Cleanup

- {"dump_dir_outside_repo":true,"raw_snapshots_remaining":0,"dumps_dir_removed":true,"chrome_profile_dir_removed":true,"extra_expense_removed":true,"ok":true}

## Limitations

- Web *profile* build measures the dart2js/V8 heap, not the Dart VM heap of a desktop/mobile build;
  no Visual Studio or Android SDK is installed on this machine, so the VM-service path is NOT RUN.
- Only *unrendered, distinctive, finance-scoped* values gate the verdict. Rendered text is
  retained by the web engine’s segmentation LRU after the app drops it, so gating on it would
  measure the engine, and a short digit run can match inside an unrelated fixture UUID (see the
  `bank` notes). Shared-club roster ids are values the new actor may fetch, so they are published
  with their paths instead of being asserted absent.
- The bank account holder name is only fetched by the player payment-instructions surface, so the
  Owner path never loads it; it is measured and reported as not loaded, not as coverage.
- Sentinels prove that specific Owner-private values are no longer reachable; they do not enumerate
  every retained object of the financial models.
- Raw heap snapshots are written outside the repository, scanned once and deleted; only counts and
  short hashes are published.
