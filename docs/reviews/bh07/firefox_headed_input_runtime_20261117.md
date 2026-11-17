# Firefox headed input diagnostic — 17/11/2026

**PARTIAL / cause UNKNOWN; V2 remains open.** AGY Gemini4Hydrogen(XHigh) implemented the diagnostic and one correction round; Codex ran the browser experiments. Clean diagnostic source `8c7b8eca8ff68b09e6abf1d7408a3b3947031118`. Separate source/control review found no remaining P1/P2 in that delta; this is not independent browser QA.

Installed Playwright CLI0.1.22, Firefox cached distribution firefox-1553, Windows; eight fresh named headed contexts, run sequentially and closed. Explicit launcher headless=false plus CLI --headed establish headed provenance. Same39 existing profile artifacts from7614c6a verified on disk and over loopback HTTP; intentionally no fresh build. Configs, source/driver hashes, parsed results, screenshots and receipts are in [evidence](firefox_headed_input_20261117_evidence/manifest.json).

| Isolated launch / focus | Result | Account click |
|---|---|---|
| Default / baseline | FAIL | zero trusted click; RAF timeout |
| Default / bringToFront | FAIL | zero trusted click; RAF timeout |
| Software WebRender / baseline | PASS | trusted click and RAF commit |
| Software WebRender / bringToFront | FAIL | trusted down only; no up/click, RAF timeout |
| Default + occlusion tracking=false / baseline, three fresh contexts | 3 PASS | trusted clicks/input and RAF commits |
| Default + occlusion tracking=true / baseline, intervening control | PASS | trusted clicks/input and RAF commits |

PASS means physical Account→login-dialog clicks, benign synthetic email/password typing and Tab blur retained values, without submitting. Flutter semantics-placeholder bootstrap is recorded separately. No forced or DOM app-action clicks. All eight cases observed zero auth/mutation requests and zero auth storage keys; observer cleanup passed.19/19 Node controls passed, including fail-closed unexpected RPC/external POST and false/unknown RAF outcomes.

The three failed cases had visible/focused DOM state, an enabled in-viewport target and exact elementFromPoint hit, yet screenshots were white and RAF failed. Successful screenshots render the Flutter UI. Thus DOM focus/hit tests alone do not establish usable rendering. bringToFront is not a demonstrated fix. Mozilla documents [Windows occlusion-related automation failures](https://bugzilla.mozilla.org/show_bug.cgi?id=1802473) and [occluded-window refresh throttling](https://bugzilla.mozilla.org/show_bug.cgi?id=1688997); these motivated a hypothesis only. The enabled control also passed, so these runs do **not** establish occlusion as the root cause or justify changing the lifecycle scenario. Launch ordering, native occlusion/compositor state and reproducibility remain unmeasured. No speculative lifecycle/app fix was applied.

Root DB fingerprint before/after matches:21 public tables/94 rows, schema/roles/other sequences unchanged, Auth98→98. No business fixture or credentials submitted. All eight owned sessions closed, CLI inventory empty, owned loopback server stopped and four containers restored to their initially stopped state. Ignored raw console/CLI logs and benign diagnostic files retained; published artifacts contain synthetic input only.

Environment policy rejected the preparation command containing local anon-key renewal. No renewal was applied or retried through another route; expired local anon remains. This limits the experiment to no-submit UI input: no Guest authorization/read-success or authenticated lifecycle/offline/retry acceptance. Historical13Nov FAIL/UNKNOWN and their evidence remain unchanged. Next work is controlled reproduction with native window/compositor observations, then a justified tooling correction if evidence supports one. Full V2/V2b/BH-07/V8 remains unaccepted; no main merge/deploy/pilot/BH-08 or owner risk signature.
