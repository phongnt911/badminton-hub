# Bank/receiver Web-profile coverage — independent local acceptance

2026-11-02. **Accepted within this task's tooling and local sentinel coverage scope.** Antigravity implemented exclusively with Gemini 3.8 Flash (High); Codex independently reviewed, ran the real measurement and audited the evidence. Tested source: `a095a457f2f12e8d65fe69ba5a3ca3ddb79ea110`, `git_dirty: false`, branch `feat/bh07-bank-receiver-heap`. This acceptance does not close all of V2b/BH-07 or authorize merge/deployment.

## Runtime evidence

Fresh Flutter Web **profile** build, 39 hashed artifacts, served bytes match the build. Two actor paths, Owner → logout → Cohost and Owner → logout → Member, each preserve one document across four epochs: **eight snapshots total**. Runner `RUN/PASS`, independent auditor exit 0.

For `bank_account_id`, `bank` and `receiver`, both baseline scans are absent/unreachable and both Owner scans are present/reachable. The unrendered distinctive `bank_account_id` becomes absent/unreachable after logout and after actor switch in both cycles. This establishes the measured V8 string-sentinel result, not complete Dart-object or app-wide release.

Rendered `bank` and `receiver` remain reachable after logout/actor switch: four records each. They are explicitly **unattributed residual risks**, not absence gates or proof of an engine-only cause. Existing expense titles and payment reference also produce four residual records each, for 20 total unattributed records. No residual risk is silently accepted on the owner's behalf.

Evidence: [runtime report](bank_receiver_heap_r4_runtime_evidence/report.md), [independent checks](bank_receiver_heap_r4_runtime_review_evidence/results.json), [closure metadata](bank_receiver_heap_r4_runtime_review_evidence/closure_checks.json). Historical failed bundle is unchanged.

## Cleanup and verification

All owned disposable club/bank and run-only expense/payment receipts are created, removed and verified absent. Full-row counts and SHA-256 fingerprints for clubs, members, bank accounts, expenses and payments match before/after. Independent receipt-ID checks confirm disposable IDs absent. Raw snapshots and this run's Chrome profile are removed; cleanup.ok is true. The three historical reviewer profiles were separately identified and removed after the owner added the required lean-ctx permissions; no matching profile directories remain.

The implementation still matches the four source/test hashes from the round-four review. All 1,719 protected historical evidence/app/backend files and all 16 payloads in the prior round-four bundle remain unchanged. No app/backend/schema change or credential publication.

Validation: **375 Python tests**, fixture **8/8**, current and legacy finance auditors pass; fresh `flutter analyze` zero issues; fresh Flutter tests **247 pass + one skip**. Python results refer to the already-reviewed identical source, not an invented rerun after documentation edits. Fresh Flutter tool archives and runtime/source/hash details are recorded in closure metadata.

Fresh-bundle controls use cloned bundles, regenerate matching report/manifests and invoke the real auditor: the positive control exits 0; seven mutants (missing bank-created receipt, wrong bank receipt hash, club not removed, bank not verified absent, missing contract, missing bank-ID metadata, wrong contract version) each exit 1 with the expected specific finding. Original bundle bytes are untouched. Reviewer scripts are recorded alongside the results; receipt-control replay defaults to an ignored build output directory.

BKR1–BKR9 have no remaining P0/P1/P2 findings in this task's tested scope. The earlier profile-cleanup failures and protocol/launcher probes remain preserved as historical evidence rather than rewritten as success.

Antigravity authored the handoff/coverage updates. Its final documentation correction call timed out after saving the edits; Codex inspected the actual diff and confirmed the requested scope, units, Flutter results and unattributed-risk wording independently. CLI success was not used as a substitute for file or runtime verification.

## Remaining boundaries and integration decision

App-wide/model retention remains UNKNOWN. Payment instructions, ledger, listener object graph, Dart VM desktop/mobile, other browsers/load/staging/production and all unmeasured gates remain NOT RUN. Full V2b/BH-07 is not accepted; no pilot or BH-08.

Task code commits since base `94fd997`: `bf6ac99`, `c73bc44`, `a22a657`, `a095a45`, followed by this documentation/evidence publication. At the tested source checkpoint the feature branch is **178 commits ahead of local main** and its full diff includes 1,851 files. This task review does not approve all inherited changes or their prerequisites. Before merging main, prepare and review the exact integration scope and dependencies; do not blindly merge the whole feature branch or cherry-pick without required tooling foundations.

Read-only integration inspection confirms local main has no `scripts/bh07_appheap` tree. The task's code delta from `94fd997` touches six scripts and five Python test files, with no `lib` or `supabase` changes. Its edits to the existing oracle/runner/auditor therefore cannot be treated as a standalone patch on main: the inherited heap framework, driver and test/fixture prerequisites must first be inventoried and reviewed. The proposed next step is a scoped dependency/integration plan for owner approval, not an immediate whole-branch merge. No additional implementation task has been started.

No merge, push, deployment or next-task implementation has occurred. Ask the owner to approve the integration scope before proceeding.
