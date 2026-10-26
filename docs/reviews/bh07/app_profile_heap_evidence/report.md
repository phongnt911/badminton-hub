# V2b — app-profile heap / in-memory retention after actor switch

- Gate: V2b — app-profile Dart heap / in-memory retention after actor switch
- Reference: docs/reviews/bh07/bh07_readiness.md §4.4
- Status: **RUN** (verdict PASS)
- Tested source: `249f12ed5b8ba042de1d48e9d5e06ffe7c125ada` (git dirty: false)
- Measurement surface: Flutter Web profile build + Chrome DevTools Protocol HeapProfiler (V8 heap snapshot)
- Oracle: fixture sentinel strings counted in live V8 heap snapshots; no class-name dependency
- Build: mode=profile reused=false artifacts=39 served_match=true
- Chrome: Chrome/155.0.8059.85; Flutter: Flutter 3.47.6 • channel stable • https://github.com/flutter/flutter.git

## Sentinels (values never published)

| sentinel | kind | length | sha256[:12] |
| --- | --- | --- | --- |
| bank | club bank account number (Owner-private) | 10 | 65dce15efcc4 |
| expense | posted session expense title (Owner-private) | 16 | 41a394dd2dcd |
| probe | detector sanity marker set on window | 25 | 3d6cdcd6437c |

## Cycles

| cycle | actor path | same document | epoch | snapshot bytes | snapshot sha256[:12] | present sentinels |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Owner -> logout -> cohost | true | baseline | 58414388 | 35fd5a35e3ca | probe |
| 1 | Owner -> logout -> cohost | true | owner_active | 84037436 | f49ae02f751f | bank, probe |
| 1 | Owner -> logout -> cohost | true | post_logout | 69258978 | 99ba1a5b2d49 | probe |
| 1 | Owner -> logout -> cohost | true | post_actor | 82317587 | 3852b92e2732 | probe |
| 2 | Owner -> logout -> member | true | baseline | 58326149 | 4062854ebdfe | probe |
| 2 | Owner -> logout -> member | true | owner_active | 83941045 | 3b75780647e9 | bank, probe |
| 2 | Owner -> logout -> member | true | post_logout | 69379107 | 67446555bb72 | probe |
| 2 | Owner -> logout -> member | true | post_actor | 73596863 | 7a4d6d280731 | probe |

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
