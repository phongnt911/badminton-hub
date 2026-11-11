# BH-07 Web browser matrix implementation plan

**Goal:** Extend measured Web coverage from Chrome to Edge and Playwright Firefox, using the current local fixture without resetting data.

**Architecture:** One small Playwright CLI `run-code` function expression; real UI, real local Auth/PostgREST, explicit semantic assertions and recorded results. No product changes, browser-state injection, hidden REST replacement or new dependency/framework. Owner already authorized continued local execution and Anti coding with Codex review; routine implementation choices proceed without another permission question.

**Spec:** `docs/reviews/bh07/bh07_readiness.md` §4.3 and current `web_local_runtime_20261110.md`. This extends Web evidence, does not close all V2/native/Safari or V2b heap gates.

**Result, 11 November:** Edge and Firefox headless passed the local scenario after the product fix described in the amendment below. Firefox headed remains UNKNOWN. The final results, source review scope, database comparison and browser limits are recorded in [the runtime report](../../reviews/bh07/web_matrix_runtime_20261111.md).

## Task and ownership

Anti owns only `scripts/bh07_browser/web_matrix_scenario.js` and `docs/reviews/bh07/web_matrix_scenario_handoff_20261110.md`. Codex owns this plan, runtime execution, evidence publication and current matrix updates. Existing feature branch is isolated from main; no additional checkout/copy or shared evidence rewrite is needed for two new files. Anti is not alone and must not revert other edits.

- [ ] Anti writes the UI scenario as a test, not product implementation; no shell/runtime/delegation. Explicit local URL and fixed fixture, guard against nonlocal browser URL, fail on missing/contradictory expected result.
- [ ] Review source after handoff; up to3correction rounds then Codex fixes residual concrete findings under standing owner authorization.
- [ ] Codex exercises a wrong-expected-aggregate negative control to show oracle rejection, then runs real Edge and Firefox positives in separate browser profiles.
- [ ] Cover public deep link before login; Owner login/deep link/summary200000due+100000paid+100000outstanding,2present/0absent/2confirmed; F5 session restore; same-document logout→Cohost count-only summary; offline read refresh/error/online recovery; Member own-fee boundaries. No write retry/heap claim.
- [ ] Use Flutter semantics through Playwright locators/ariaSnapshot, not document.body.innerText. Blur text fields with Tab; bounded state-based waits, avoid navigation Back races. Restore online in finally. Clipboard only if browser supports requested permissions; report unsupported as NOT RUN rather than inventing PASS.
- [ ] Publish only sanitized results/snapshots, build/browser versions, exact source/served hash and before/after fixture state; keep old bundles byte-identical. Independent source/artifact review and truthful acceptance matrix.

Current fixture: session0099 completed/version3/billing_input_version3,1active revision, total200000; Member A charge100000 paid100000, Guest A charge100000 paid0; one confirmed payment and one payment-ledger entry. Entire scenario should be read-only apart from Auth session records. Do not click the public “Đăng nhập để đăng ký” CTA because it also attempts registration; use root Account login UI, then authenticated deep link.

## Evidence-driven amendment: pending summary read

After Anti corrections1/2/3, Codex directly fixed navigation/input/row-selection races under the standing owner instruction. Edge R3 completed; subsequent Firefox headless reached summary refresh but the UI RPC stayed pending, even after navigator.onLine returned true. Refresh stayed disabled through15s scenario wait and30s diagnostic wait. Host same-Cohost RPC independently returned200 in24.01ms, counts2/0/2. App `fetchSessionSummary` awaits a repository Future with no deadline; this is a remaining BH-07 read-liveness finding, not a request to add features or relax the test.

Codex owns the minimal direct fix after3rounds: `lib/providers/finance_provider.dart` summary-read await only, plus regression cases in existing provider/screen test files. Add15s read deadline, preserve cached values and current generation/serial guards, show existing error/retry UI. No mutation/DB/RPC/schema changes, no new dependency, no assertion that Future.timeout cancels underlying HTTP. Existing evidence remains byte-identical; rebuild profile and rerun browser checks on new app hash.

- [x] Add pending-read regressions first and run targeted RED.
- [x] Add the read deadline, verify targeted and full suites and analysis, and review the source independently.
- [x] Rebuild the served Web profile, rerun Edge and Firefox headless, and verify source and served hashes and data fingerprints.
