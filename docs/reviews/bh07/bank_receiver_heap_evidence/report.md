# V2b — app-profile heap / in-memory retention after actor switch

- Gate: V2b — app-profile Dart heap / in-memory retention after actor switch
- Reference: docs/reviews/bh07/bh07_readiness.md §4.4
- Status: **NOT RUN**
- Tested source: `c73bc4404cb6992141797ace13e1009db83342b0` (git dirty: false)
- Measurement surface: Flutter Web profile build + Chrome DevTools Protocol HeapProfiler (V8 heap snapshot)
- Oracle: fixture sentinel strings counted in live V8 heap snapshots; no class-name dependency
- Build: mode=profile reused=false artifacts=39 served_match=true
- Chrome: Chrome/155.0.8059.85; Flutter: Flutter 3.47.6 • channel stable • https://github.com/flutter/flutter.git

## Sentinels (values never published)

| sentinel | kind | class | length | sha256[:12] |
| --- | --- | --- | --- | --- |
| bank | disposable club bank account number rendered as widget text | bank, rendered, distinctive | 16 | 2fcd7f6a38f2 |
| receiver | disposable club bank account holder name rendered as widget text | bank, rendered, distinctive | 22 | c7f21924332a |
| expense | posted session expense title rendered as widget text | finance, rendered, distinctive | 16 | 41a394dd2dcd |
| expense_id | posted session expense id returned by get_session_finance (never rendered) | finance, not rendered, distinctive | 36 | 7b5ed5cb05a0 |
| expense2 | second posted expense title rendered as widget text (run-only fixture row) | finance, rendered, distinctive | 24 | 743e1e4255d7 |
| expense_id_2 | second posted expense id from get_session_finance (never rendered) | finance, not rendered, distinctive | 36 | b85d1a100889 |
| payment_id | submitted session payment id from get_session_finance (never rendered) | finance, not rendered, distinctive | 36 | ee689bbad9ca |
| payment_ref | submitted session payment reference rendered as widget text | finance, rendered, distinctive | 20 | 7327c30347d9 |
| player_a | session player id of the seeded roster (never rendered) | identity, not rendered, distinctive | 36 | e3382947f391 |
| player_b | second session player id of the seeded roster (never rendered) | identity, not rendered, distinctive | 36 | c5383f9762b9 |
| probe | detector sanity marker set on window | control, not rendered, distinctive | 25 | c1455a1ad806 |
| bank_account_id | disposable club bank account ID from club_bank_accounts (never rendered) | finance, not rendered, distinctive | 36 | c7c6b1ad2ee6 |

## Cycles

| cycle | actor path | same document | epoch | snapshot bytes | snapshot sha256[:12] | present sentinels |
| --- | --- | --- | --- | --- | --- | --- |

## Retained paths

| cycle | epoch | sentinel | reachable | root kind | path length | path sha256[:12] |
| --- | --- | --- | --- | --- | --- | --- |

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
| none | n/a | n/a | n/a | n/a | n/a |

## Notes

- none

## Findings

- heap dump, browser profile or run-only fixture cleanup not verified
- run aborted: Could not find semantic element to click for: Clubs tab

## Cleanup

- {"dumps_dir_removed":true,"chrome_profile_dir_removed":false,"run_only_fixture_created":true,"run_only_fixture_id_sha256_12":"b85d1a100889","extra_expense_removed":true,"extra_expense_verified_absent":true,"run_only_payment_created":true,"run_only_payment_id_sha256_12":"ee689bbad9ca","extra_payment_removed":true,"extra_payment_verified_absent":true,"disposable_club_id_sha256_12":"1e591d2bb5a7","disposable_bank_id_sha256_12":"c7c6b1ad2ee6","disposable_club_created":true,"disposable_bank_created":true,"disposable_club_removed":true,"disposable_bank_removed":true,"disposable_club_verified_absent":true,"disposable_bank_verified_absent":true,"ok":false}

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
