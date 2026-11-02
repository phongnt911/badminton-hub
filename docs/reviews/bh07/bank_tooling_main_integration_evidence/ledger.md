# SDD ledger — plan: docs/superpowers/plans/2026-11-02-bh07-main-integration.md

Ruling: this is review/packaging preparation, not production implementation. Use a pinned main export under ignored build output and `git apply --directory` there; no linked worktree, branch checkout, rebase or main mutation is needed. The owner approved preparation only.

Ruling: existing tests verify copied source; do not write implementation-mirroring tests for the packaging helper. Source/test bytes must match the pinned source, and all original main bytes must remain unchanged.

Task 1: complete. Source 57cd2c4, main/remote62d2c67. Runtime dependencies include BH-07 history/summary UI and get_session_summary/list_my_session_history migration, outside the package.

Task 2: complete. v1 passed but over-collected output directories. Ruling: output sinks are not input dependencies; v2 removes them and the unused standalone attribution tool. v2 has58 additions; apply/check0,311Python,fixture8/8,three historical audits0,pub offline0,analyze0,190Flutter.629 baseline files preserved and Git refs unchanged. Historical replay never becomes a main runtime claim.

Additional required gate: v2 actual clone/index checkout under core.autocrlf=true changed all58 files exclusively by CRLF conversion; 307 tests ran with fixture/graph failures. The export/static review had not exercised this boundary. v2 is withdrawn.

Ruling: add one generated exact-path .gitattributes file to v3, preserving all payload bytes and enforcing LF source without changing any global Git setting or original app/backend file. Git metadata adaptation belongs to this packaging scope; original product/tool implementation stays byte-identical. The patch must stage attributes first, include all six ignored logs and pass fresh-checkout tests under core.autocrlf=true.

Task 3: pending v3 checkout validation and fresh reviewer addendum. Keep failed v2 diagnosis and the requested package/export for owner inspection; do not delete them as generic scratch cleanup. Owner merge decision remains pending.

No merge/push/deployment/live DB/browser run. All future Git operations require the owner's exact scope decision.

Task 3: complete after v4 addendum. All59 execution/export hashes match under autocrlf=true;629 base files unchanged,311Python/three audits/fixture pass. Ruling: cached apply plus forced index checkout only in a freshly created clean private workspace; build setup is a prerequisite. No source/test/fixture rewrite and no global config change. v2/v3 remain failed historical drafts. Owner merge decision pending.
