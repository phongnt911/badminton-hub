# V2b — app-profile heap / in-memory retention after actor switch

- Gate: V2b — app-profile Dart heap / in-memory retention after actor switch
- Reference: docs/reviews/bh07/bh07_readiness.md §4.4
- Status: **RUN** (verdict PASS)
- Tested source: `bb2d2130276ad31824acc650a02ecee4b6ba95a6` (git dirty: false)
- Measurement surface: Flutter Web profile build + Chrome DevTools Protocol HeapProfiler (V8 heap snapshot)
- Oracle: fixture sentinel strings counted in live V8 heap snapshots; no class-name dependency
- Build: {"mode":"profile","build_ms":44925}
- Chrome: Chrome/155.0.8059.85; Flutter: Flutter 3.47.6 • channel stable • https://github.com/flutter/flutter.git

## Sentinels (values never published)

| sentinel | kind | length | sha256[:12] |
| --- | --- | --- | --- |
| bank | club bank account number (Owner-private) | 10 | 65dce15efcc4 |
| expense | posted session expense title (Owner-private) | 16 | 41a394dd2dcd |
| probe | detector sanity marker set on window | 25 | 16d8da2f71d6 |

## Cycles

| cycle | actor path | same document | epoch | snapshot bytes | snapshot sha256[:12] | present sentinels |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Owner -> logout -> cohost | true | baseline | 58337657 | b7af1df93088 | probe |
| 1 | Owner -> logout -> cohost | true | owner_active | 83644962 | 58ea5804d674 | bank, probe |
| 1 | Owner -> logout -> cohost | true | post_logout | 69240102 | 1a4010b7fe12 | probe |
| 1 | Owner -> logout -> cohost | true | post_actor | 81355237 | d10fbe9d3980 | probe |
| 2 | Owner -> logout -> member | true | baseline | 58329272 | fe25f6852289 | probe |
| 2 | Owner -> logout -> member | true | owner_active | 84345277 | 1a179ca49760 | bank, probe |
| 2 | Owner -> logout -> member | true | post_logout | 69743938 | 1f7fb2a4ff68 | probe |
| 2 | Owner -> logout -> member | true | post_actor | 73929215 | 97cd99659c71 | probe |

## Findings

- none

## Cleanup

- {"dump_dir_outside_repo":true,"raw_snapshots_remaining":0,"dumps_dir_removed":true,"chrome_profile_dir_removed":true,"ok":true}

## Limitations

- Web *profile* build measures the dart2js/V8 heap, not the Dart VM heap of a desktop/mobile build;
  no Visual Studio or Android SDK is installed on this machine, so the VM-service path is NOT RUN.
- Sentinels prove that specific Owner-private values are no longer reachable; they do not enumerate
  every retained object of the financial models.
- Raw heap snapshots are written outside the repository, scanned once and deleted; only counts and
  short hashes are published.
