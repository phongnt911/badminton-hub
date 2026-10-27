# V2b — app-profile heap / in-memory retention after actor switch

- Gate: V2b — app-profile Dart heap / in-memory retention after actor switch
- Reference: docs/reviews/bh07/bh07_readiness.md §4.4
- Status: **FAIL** (verdict FAIL)
- Tested source: `0ce0bf85dfe19ad75089f22c816b674890236041` (git dirty: false)
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
| player_a | session player id of the seeded roster (never rendered) | identity, not rendered, distinctive | 36 | e3382947f391 |
| player_b | second session player id of the seeded roster (never rendered) | identity, not rendered, distinctive | 36 | c5383f9762b9 |
| probe | detector sanity marker set on window | control, not rendered, distinctive | 25 | 0d8589bb4012 |

## Cycles

| cycle | actor path | same document | epoch | snapshot bytes | snapshot sha256[:12] | present sentinels |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Owner -> logout -> cohost | true | baseline | 58338720 | e9e2d95d4a44 | probe |
| 1 | Owner -> logout -> cohost | true | owner_active | 84723811 | e3afcca2f15a | bank, expense, expense_id, player_a, player_b, probe |
| 1 | Owner -> logout -> cohost | true | post_logout | 68972819 | 971acfb1e51f | expense, probe |
| 1 | Owner -> logout -> cohost | true | post_actor | 82025091 | b43332e01f8c | expense, player_a, player_b, probe |
| 2 | Owner -> logout -> member | true | baseline | 58812619 | 6cdb3b8aadf1 | probe |
| 2 | Owner -> logout -> member | true | owner_active | 84319578 | 3f8478e4e391 | bank, expense, expense_id, player_a, player_b, probe |
| 2 | Owner -> logout -> member | true | post_logout | 69505320 | 20d8072c1993 | expense, probe |
| 2 | Owner -> logout -> member | true | post_actor | 73859725 | 373ebaf0b57e | expense, probe |

## Retained paths

| cycle | epoch | sentinel | reachable | root kind | path length | path sha256[:12] |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | baseline | bank | false | n/a | n/a | n/a |
| 1 | baseline | expense | false | n/a | n/a | n/a |
| 1 | baseline | expense_id | false | n/a | n/a | n/a |
| 1 | baseline | player_a | false | n/a | n/a | n/a |
| 1 | baseline | player_b | false | n/a | n/a | n/a |
| 1 | baseline | probe | true | gc_roots | 5 | 04b7b0cc3e88 |
| 1 | baseline | receiver | false | n/a | n/a | n/a |
| 1 | owner_active | bank | true | gc_roots | 17 | aff8ab376c6c |
| 1 | owner_active | expense | true | gc_roots | 12 | 37adcafa523e |
| 1 | owner_active | expense_id | true | gc_roots | 20 | 66ec3dae6c33 |
| 1 | owner_active | player_a | true | gc_roots | 18 | 9d37b9ebd8c4 |
| 1 | owner_active | player_b | true | gc_roots | 18 | 9d37b9ebd8c4 |
| 1 | owner_active | probe | true | gc_roots | 5 | 7d0081a8c5d4 |
| 1 | owner_active | receiver | false | n/a | n/a | n/a |
| 1 | post_logout | bank | false | n/a | n/a | n/a |
| 1 | post_logout | expense | true | gc_roots | 12 | 37adcafa523e |
| 1 | post_logout | expense_id | false | n/a | n/a | n/a |
| 1 | post_logout | player_a | false | n/a | n/a | n/a |
| 1 | post_logout | player_b | false | n/a | n/a | n/a |
| 1 | post_logout | probe | true | gc_roots | 5 | 7d0081a8c5d4 |
| 1 | post_logout | receiver | false | n/a | n/a | n/a |
| 1 | post_actor | bank | false | n/a | n/a | n/a |
| 1 | post_actor | expense | true | gc_roots | 12 | 37adcafa523e |
| 1 | post_actor | expense_id | false | n/a | n/a | n/a |
| 1 | post_actor | player_a | true | gc_roots | 18 | 9d37b9ebd8c4 |
| 1 | post_actor | player_b | true | gc_roots | 18 | 9d37b9ebd8c4 |
| 1 | post_actor | probe | true | gc_roots | 5 | 7d0081a8c5d4 |
| 1 | post_actor | receiver | false | n/a | n/a | n/a |
| 2 | baseline | bank | false | n/a | n/a | n/a |
| 2 | baseline | expense | false | n/a | n/a | n/a |
| 2 | baseline | expense_id | false | n/a | n/a | n/a |
| 2 | baseline | player_a | false | n/a | n/a | n/a |
| 2 | baseline | player_b | false | n/a | n/a | n/a |
| 2 | baseline | probe | true | gc_roots | 5 | 04b7b0cc3e88 |
| 2 | baseline | receiver | false | n/a | n/a | n/a |
| 2 | owner_active | bank | true | gc_roots | 17 | aff8ab376c6c |
| 2 | owner_active | expense | true | gc_roots | 12 | 37adcafa523e |
| 2 | owner_active | expense_id | true | gc_roots | 20 | 66ec3dae6c33 |
| 2 | owner_active | player_a | true | gc_roots | 18 | 9d37b9ebd8c4 |
| 2 | owner_active | player_b | true | gc_roots | 18 | 9d37b9ebd8c4 |
| 2 | owner_active | probe | true | gc_roots | 5 | 7d0081a8c5d4 |
| 2 | owner_active | receiver | false | n/a | n/a | n/a |
| 2 | post_logout | bank | false | n/a | n/a | n/a |
| 2 | post_logout | expense | true | gc_roots | 12 | 37adcafa523e |
| 2 | post_logout | expense_id | false | n/a | n/a | n/a |
| 2 | post_logout | player_a | false | n/a | n/a | n/a |
| 2 | post_logout | player_b | false | n/a | n/a | n/a |
| 2 | post_logout | probe | true | gc_roots | 5 | 7d0081a8c5d4 |
| 2 | post_logout | receiver | false | n/a | n/a | n/a |
| 2 | post_actor | bank | false | n/a | n/a | n/a |
| 2 | post_actor | expense | true | gc_roots | 12 | 37adcafa523e |
| 2 | post_actor | expense_id | false | n/a | n/a | n/a |
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
| 1 | post_logout | expense | gc_roots | 12 | 37adcafa523e |
| 1 | post_actor | expense | gc_roots | 12 | 37adcafa523e |
| 2 | post_logout | expense | gc_roots | 12 | 37adcafa523e |
| 2 | post_actor | expense | gc_roots | 12 | 37adcafa523e |

## Notes

- cycle 1: owner_active: sentinel bank is not distinctive; a hit can be a substring of an unrelated value, so it is reported and never gated
- cycle 2: owner_active: sentinel bank is not distinctive; a hit can be a substring of an unrelated value, so it is reported and never gated

## Findings

- cycle 1: post_actor: sentinel player_a expected absent, got True
- cycle 1: post_actor: sentinel player_b expected absent, got True
- cycle 1: post_actor: sentinel player_a still reachable from a GC root via gc_roots (18 edges)
- cycle 1: post_actor: sentinel player_b still reachable from a GC root via gc_roots (18 edges)
- raw sentinel value reached the publication step (bank, expense); redacted, run failed

## Cleanup

- {"dump_dir_outside_repo":true,"raw_snapshots_remaining":0,"dumps_dir_removed":true,"chrome_profile_dir_removed":true,"ok":true}

## Limitations

- Web *profile* build measures the dart2js/V8 heap, not the Dart VM heap of a desktop/mobile build;
  no Visual Studio or Android SDK is installed on this machine, so the VM-service path is NOT RUN.
- Only *unrendered, distinctive* values gate the verdict. Rendered text is retained by the web
  engine’s segmentation LRU after the app drops it, so gating on it would measure the engine, and
  a short digit run can match inside an unrelated fixture UUID (measured for `<redacted>`).
- The bank account holder name is only fetched by the player payment-instructions surface, so the
  Owner path never loads it; it is measured and reported as not loaded, not as coverage.
- Sentinels prove that specific Owner-private values are no longer reachable; they do not enumerate
  every retained object of the financial models.
- Raw heap snapshots are written outside the repository, scanned once and deleted; only counts and
  short hashes are published.
