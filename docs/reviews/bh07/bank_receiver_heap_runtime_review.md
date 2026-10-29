# Bank/receiver heap — runtime review failed; STOP after round 3/3

2026-10-29. Tested source `c73bc4404cb6992141797ace13e1009db83342b0`, clean workspace (`git_dirty: false`), branch `feat/bh07-bank-receiver-heap`. This is a fresh reviewer runtime attempt, not a successful heap coverage measurement. No fourth corrective round is authorized.

## BKR8 — P2: bank navigation does not match the actual app destination

`scripts/bh07_appheap/run_app_profile_heap.js:555` looks for tab text `Câu Lạc Bộ`. The actual navigation destination is `CLB & Quỹ` in `lib/main.dart:121`. The fresh profile build completes, and cycle 1 baseline snapshot is scanned, but navigation aborts with the exact error:

```text
Could not find semantic element to click for: Clubs tab
```

The bundle records `status: NOT RUN`, no completed cycles and no verdict. No Owner bank load, logout transition or second actor bank cycle was verified. This is a tooling navigation failure; it does not establish an application retention leak or a successful absence gate.

## BKR9 — P2: Chrome profile cleanup remains incomplete

The runner records `dumps_dir_removed: true`, `chrome_profile_dir_removed: false`, `cleanup.ok: false`. Read-only OS inspection confirms the dedicated directory `C:\Users\POTA\AppData\Local\Temp\bh07_appheap_chrome_84440` remains and Chrome processes reference this exact profile. At inspection the matching process IDs were 85720 (parent 90108), 81020, 91976, 93292, 95864, 92048, 92236 and 92452. Do not assume these IDs remain valid later; re-identify by the exact profile command line before cleanup.

An attempted `Stop-Process` for those verified dedicated processes was blocked before execution by lean-ctx: `PowerShell cmdlet 'Stop-Process' uses a destructive verb and is not auto-allowed`. No alternative process-killing tool was used. Profile cleanup therefore remains outstanding. The profile contents were not inspected, copied or published. The process-lifecycle cause has not been isolated; do not infer it solely from the cleanup flag.

## Preservation and evidence

All owned disposable club/bank and run-only expense/payment receipts record created, removed and verified absent. An independent wrapper queried full rows before and after for clubs, club_members, club_bank_accounts, session_expenses and payments: every count and SHA-256 fingerprint matches. It separately confirms the two disposable receipt IDs absent. Thus existing rows are preserved and the created DB fixtures are gone.

All 1,606 historical evidence files and 87 app/backend files remain byte-identical. The failed fresh bundle is preserved unchanged at [bank_receiver_heap_evidence](bank_receiver_heap_evidence/report.md). Auditor exit 1 correctly rejects missing completed cycles/verdict and failed cleanup. Independent DB/hash checks are in [runtime review evidence](bank_receiver_heap_runtime_review_evidence/results.json).

Prior tooling checks remain valid: 358 Python tests, analyze zero issues, 247 Flutter passes + one skip, fixture controls 8/8 and independent graph/HTTP/publication probes. Those checks did not cover the real navigation label or Windows Chrome profile cleanup and cannot override the failed runtime.

## Decision

Task NOT ACCEPTED after the three-round maximum. BKR1–BKR7 tooling fixes remain closed in their tested scope; BKR8/BKR9 are open. Stop implementation and request the project owner's decision before any additional corrective round. No merge/integration request is made. Full V2b/BH-07 remains unaccepted; bank/receiver runtime coverage NOT RUN, app-wide/model retention UNKNOWN, listener/native/other unmeasured gates NOT RUN. No app/backend change, push, merge, deploy, pilot or BH-08.
