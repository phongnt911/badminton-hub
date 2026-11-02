# BKR8/BKR9 — exceptional round 4 independent review

2026-11-02. Authorized by the owner to resume Antigravity fixes after the round-three stop. Antigravity implemented exclusively with Gemini 3.8 Flash (High); Codex reviewed and ran the checks. Base `a22a657`, branch `feat/bh07-bank-receiver-heap`. Source hashes are recorded in the evidence; this is not a fresh clean-source bank heap run.

## Changes and verification

BKR8: `openOwnerBank` now selects the real `CLB & Quỹ` destination. Six production fake-CDP tests cover the actual label, aria/text variants, wrong label and wrong role. Full bank UI traversal has not been repeated.

BKR9: startup refuses an occupied debug port or preexisting PID-derived profile before creating a directory or spawning Chrome. Async spawn errors and readiness requests are bounded. Both cycle and finally paths await an owned-browser shutdown helper, which retains fail-closed cleanup status and retries exact-profile deletion. No Stop-Process/taskkill command or unrelated browser termination was added.

Two independent real-browser failures exposed gaps missed by the initial unit tests:

1. Browser-root `CdpClient.send()` serialized `sessionId: null`; Chrome returned `-32600: Message may have string 'sessionId' property`. A root request omitting that property succeeded. The private shutdown connection now uses `sessionId = undefined`, preserving the shared CDP driver.
2. The spawned Windows launcher had already exited with code 0 while browser descendants still held the profile. The helper now calls the owned browser-close callback even when that launcher has exited, rather than equating launcher exit with browser shutdown. A regression covers an exited launcher plus a still-locked browser profile.

The final real-Chrome probe passes: fresh profile created, launcher observed exited, browser closed, profile verified absent, historical profile existence preserved. This test used a fresh free port and no app/DB fixture. Failed probe results remain in the evidence alongside the successful result.

Final independent checks: **375/375 Python tests**, fixture controls **8/8**, finance and legacy b13e468 auditors exit 0. All **1,719** protected evidence/app/backend files remain byte-identical. No app/backend/schema/config change. Flutter was not rerun for this JS/Python tooling-only correction; the earlier 247+1skip/analyze0 results are historical, not new claims.

Evidence: [results](bank_receiver_heap_round4_evidence/results.json), command logs, real-browser receipts, protocol diagnosis and SHA-256 manifest.

## Runtime and cleanup blockers

The full two-actor/eight-epoch bank heap run remains **NOT RUN** for this revision. Historical failed bundle `bank_receiver_heap_evidence` is unchanged. Chrome from profile `bh07_appheap_chrome_84440` still runs on the default debug port, and startup must refuse it. This browser was not closed through another tool after the earlier lean-ctx Stop-Process block.

The two fresh failed reviewer probes (`bh07_appheap_chrome_96928` and `bh07_appheap_chrome_98756`) were gracefully closed through their individually verified CDP endpoints; OS inspection confirmed no matching processes remained. Their leftover directories could not be removed: lean-ctx blocked `Remove-Item` as a destructive cmdlet before execution. No alternative deletion tool was used for those directories. The final successful probe leaves no new profile behind.

Outstanding exact directories under `C:\Users\POTA\AppData\Local\Temp` are 84440, 96928 and 98756. Re-identify processes from exact profile command lines before any shutdown; do not reuse historical PIDs. Cleanup is a prerequisite to the full fresh bank run, not evidence that run has passed.

## Decision

The corrections pass their code/unit and focused real-Chrome checks. **The full task is not accepted and not ready to merge**, because new bank UI/heap/runtime evidence is still missing and historical cleanup remains blocked. Preserve UNKNOWN/NOT RUN for app-wide/model retention, listener graph, native and all unmeasured gates. No merge, push, deployment, pilot or BH-08. Do not start another task; obtain the required cleanup access, run a fresh separately named bundle on a clean source checkpoint, and independently audit it before requesting integration.
