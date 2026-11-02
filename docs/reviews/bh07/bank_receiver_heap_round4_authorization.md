# BKR8/BKR9 — exceptional correction round 4

2026-11-02: the project owner explicitly requested continuing Antigravity fixes after the round-three stop. Treat this as authorization for one additional corrective round, limited to BKR8 navigation and BKR9 owned-browser lifecycle/cleanup. It does not reset the round counter or authorize further automatic rounds.

Antigravity implements exclusively using Gemini 3.8 Flash (High); Codex independently reviews and verifies. Base `a22a657`, branch `feat/bh07-bank-receiver-heap`, initially clean. Keep app/backend/schema/config and all historical evidence unchanged. No merge, push, deployment, pilot or BH-08. Ask the owner before integrating accepted work into main.

Verify the actual navigation label against the app; fix the runner selector and test production navigation through fake CDP. Diagnose owned-Chrome exit and Windows profile cleanup before fixing. Shutdown must be awaited and bounded, fail closed, preserve unrelated processes/profiles, handle startup failure and refuse an occupied debug port. Do not evade the lean-ctx Stop-Process block.

Run targeted/full tests and a fresh, separately named runtime bundle only after tooling review. Preserve the failed historical bank bundle. No successful bank coverage or cleanup is claimed at authorization time. The old `bh07_appheap_chrome_84440` directory still exists at read-only inspection; do not reuse historical process IDs or silently claim it has been removed.
