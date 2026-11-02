# Bank tooling — scoped main integration preparation

2026-11-02. **Preparation complete; owner merge decision pending.** No merge, push, deployment, app/backend edit or live DB/browser run. Current branch remains `feat/bh07-bank-receiver-heap`.

## Exact candidate

- Source: `57cd2c40e7659715ac0c6b55787d197df5ac1c6c`.
- Base main: `62d2c67dc66d512cf7f6f19932e2131ae060e2e9`; read-only origin/main lookup matches.
- Final revision: **v4**, 59 new files, 1,070,255-byte patch.
- [Exact patch](../../../build/bh07-main-integration-62d2c67-57cd2c4-v4/tooling-only.patch), SHA-256 `b5bf79b1f03aed56ad7e7efd0a7985f7eb5abe714a36295c28859399cee4c1f8`.
- [Portable draft ZIP](../../../build/bh07-main-integration-62d2c67-57cd2c4-v4/bank-tooling-main-62d2c67-57cd2c4.zip) includes patch, manifest, checks, logs, generator snapshots and reviews. [Artifact hashes](bank_tooling_main_integration_evidence/artifact.json).
- No existing main file changes; do not merge the whole inherited feature branch.

## Dependency boundary

| Included layer | Files | Purpose |
|---|---:|---|
| Source/support | 13 | Heap oracle/auditor/runner, build and ownership guards, fixture controls, reused CDP driver and its referenced assertion/seed/cleaning helpers plus seed SQL |
| Python regression modules | 12 | Bank, oracle/path/evidence, publication/build and finance controls |
| Historical bundles/probes | 32 | Six complete reference bundles plus eight reviewer probes needed by offline checks; keep original tested-source attribution |
| Scope notice | 1 | Explicit main-runtime and approval boundary |
| Scoped .gitattributes | 1 | Exact root-anchored rules for these59 paths only; audited fixture bytes preserved, source/probes LF; no global Git setting changes |

All copied source/test/fixture files retain pinned-source bytes. Only the notice and Git line-ending policy are generated packaging metadata. No `lib/`, `supabase/`, Dart `test/`, `web/` or pubspec edits are included.

## Checks on main plus this candidate

| Check | Actual result |
|---|---|
| Apply check and exported candidate | Exit0; applied only under ignored build output |
| Selected Python suite | 311 passed on export and on a separate actual Git clone |
| Fixture controls | 8/8 on both contexts |
| Historical finance, b13e468 and bank auditors | All exit0 in both contexts; historical replay only |
| Offline dependencies / Flutter analyze | pub get offline exit0; zero issues on export |
| Main Flutter tests | 190 passed on export |
| Git staging | Exactly59 additions, including all six ignored run.log files |
| Git fresh checkout | core.autocrlf=true; zero working-tree or index-export hash mismatches |
| Existing main content | All629 export files unchanged; all629 actual-clone files unchanged before/after staging/checkout |
| Active repository | HEAD/main refs unchanged by package verification; existing worktrees preserved |

The feature branch's 375 Python / 247 Flutter + one skip are different results, not counts claimed for main. No bank runtime was executed against main.

## Windows checkout finding and closure

v1 over-collected output paths and was narrowed. v2 export checks passed but real Git checkout converted all58 paths to CRLF under core.autocrlf=true; strict fixture checks failed. v3 introduced scoped attributes and its index export became byte-exact, but initial working-tree files still reflected pre-apply attributes; the clone also lacked the ignored build directory needed by a reviewer probe.

v4 closes this packaging P2 with exact anchored attributes, **cached application then index checkout**, and documented build setup. Original production code, tests and fixture payloads were not changed to force green. Failed v2/v3 diagnosis is retained alongside the final [checkout result](bank_tooling_main_integration_evidence/checkout_smoke.json). The reused CDP driver emits two inherited trailing-space warnings during patch application; its bytes are intentionally preserved rather than silently adapted.

## Required integration procedure after owner approval

1. Recheck the pinned main revision and create a **new clean private integration workspace**. Never use the forced checkout below in an active/user-modified workspace.
2. Inspect the manifest and patch hash, run apply check, then stage with `git apply --cached tooling-only.patch`.
3. Materialize that staged tree using `git checkout-index --all --force` only in the new workspace. This lets the new attributes govern every added path and retains ignored fixture logs.
4. Confirm exactly59 staged additions and all manifest hashes. Create ignored `build/` before Python replay (PowerShell: `New-Item -ItemType Directory -Path build -Force`). Repeat the recorded tests/audits and inspect the exact staged diff.
5. Perform only the owner-approved local tooling merge from the new integration branch. Keep the original `feat/bh07-bank-receiver-heap` branch and its unmerged application history intact; do not mark or delete it as merged. Push requires separate authorization.

## Live prerequisites excluded from this scope

**Bank runtime on main remains NOT RUN.** The accepted two-cycle/eight-snapshot result belongs to `a095a45` on the feature branch. Copying/auditing its bundle does not certify main.

Main lacks BH-07 history/summary screens (`session_history_screen.dart`, `session_summary_screen.dart`), `session_summary_text.dart`, and related session/finance model, repository, provider and navigation changes. It also lacks `supabase/migrations/20261020180000_bh07_reads.sql`, which provides `get_session_summary` and `list_my_session_history`. Those capabilities and local fixture setup are prerequisites for the Owner/Cohost/Member runtime flow.

Their separate local review history is not approved by this preparation. V2b/BH-07 still has NOT RUN/UNKNOWN gates and unattributed rendered-text risks. Do not validate this candidate against a feature-configured database and call it validation of main's migrations.

## Review and recommendation

[Fresh independent review](bank_tooling_main_integration_evidence/independent_review.md) closes the checkout P2 on v4 and reports no remaining P0/P1/P2 in the preparation scope. The reviewer inspected configuration/evidence; the coordinator ran the suites and hash checks. [Manifest](bank_tooling_main_integration_evidence/manifest.json), [results](bank_tooling_main_integration_evidence/results.json) and logs record the exact scope.

Recommendation: integrate **only this59-file offline tooling foundation** after explicit owner approval, keeping app/migration integration separate. It changes no product behavior and is not a complete BH-07 acceptance or runtime certification. If the owner wants BH-07 application features on main, prepare a separate A→B→C→D dependency/acceptance review; do not merge the179-commit source history under this tooling approval. No additional implementation task has started.
