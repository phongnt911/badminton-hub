# V2b — app-profile heap / in-memory retention after actor switch

- Gate: V2b — app-profile Dart heap / in-memory retention after actor switch
- Reference: docs/reviews/bh07/bh07_readiness.md §4.4
- Status: **NOT RUN**
- Tested source: `0f1209504381490b0c7856ba3d1b7bb03cf836fc` (git dirty: false)
- Measurement surface: Flutter Web profile build + Chrome DevTools Protocol HeapProfiler (V8 heap snapshot)
- Oracle: fixture sentinel strings counted in live V8 heap snapshots; no class-name dependency
- Build: mode=n/a reused=false artifacts=0 served_match=false
- Chrome: n/a; Flutter: n/a

## Sentinels (values never published)

| sentinel | kind | class | length | sha256[:12] |
| --- | --- | --- | --- | --- |

## Cycles

| cycle | actor path | same document | epoch | snapshot bytes | snapshot sha256[:12] | present sentinels |
| --- | --- | --- | --- | --- | --- | --- |

## Retained paths

| cycle | epoch | sentinel | reachable | root kind | path length | path sha256[:12] |
| --- | --- | --- | --- | --- | --- | --- |

## Residual risks

Rendered text the Owner saw can stay in the web engine’s segmentation LRU after the app
dropped it. That retainer is engine-internal (flutter/engine web_ui text_fragmenter.dart),
so it is published here and never counted as app state by the gate.

| cycle | epoch | sentinel | root kind | path length | path sha256[:12] |
| --- | --- | --- | --- | --- | --- |
| none | n/a | n/a | n/a | n/a | n/a |

## Notes

- none

## Findings

- heap dump, browser profile or run-only fixture cleanup not verified
- run aborted: PostgREST POST session_expenses: 400

## Cleanup

- {"dumps_dir_removed":true,"chrome_profile_dir_removed":true,"extra_expense_removed":true,"ok":false}

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
