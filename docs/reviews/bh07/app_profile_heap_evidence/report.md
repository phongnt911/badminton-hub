# V2b — app-profile heap / in-memory retention after actor switch

- Gate: V2b — app-profile Dart heap / in-memory retention after actor switch
- Reference: docs/reviews/bh07/bh07_readiness.md §4.4
- Status: **RUN** (verdict PASS)
- Tested source: `130af7d103cdea22c2f9ac9e4cb000f74ec02590` (git dirty: false)
- Measurement surface: Flutter Web profile build + Chrome DevTools Protocol HeapProfiler (V8 heap snapshot)
- Oracle: fixture sentinel strings counted in live V8 heap snapshots; no class-name dependency
- Build: mode=profile reused=false artifacts=39 served_match=true
- Chrome: Chrome/155.0.8059.85; Flutter: Flutter 3.47.6 • channel stable • https://github.com/flutter/flutter.git

## Sentinels (values never published)

| sentinel | kind | length | sha256[:12] |
| --- | --- | --- | --- |
| bank | club bank account number (Owner-private) | 10 | 65dce15efcc4 |
| expense | posted session expense title (Owner-private) | 16 | 41a394dd2dcd |
| probe | detector sanity marker set on window | 25 | 6a6f00ce03bd |

## Cycles

| cycle | actor path | same document | epoch | snapshot bytes | snapshot sha256[:12] | present sentinels |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Owner -> logout -> cohost | true | baseline | 58357152 | 23a453ada885 | probe |
| 1 | Owner -> logout -> cohost | true | owner_active | 84919680 | 5cd7c1851c11 | bank, probe |
| 1 | Owner -> logout -> cohost | true | post_logout | 68961793 | 60cd377c1904 | probe |
| 1 | Owner -> logout -> cohost | true | post_actor | 81734053 | 210c30ad5aeb | probe |
| 2 | Owner -> logout -> member | true | baseline | 58512742 | 5d1d6294517f | probe |
| 2 | Owner -> logout -> member | true | owner_active | 84204480 | da2833705279 | bank, probe |
| 2 | Owner -> logout -> member | true | post_logout | 68819082 | 2d45678f9529 | probe |
| 2 | Owner -> logout -> member | true | post_actor | 73199374 | 2b570260287a | probe |

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
