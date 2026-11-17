# Firefox headed diagnostic source review R1 — CHƯA ĐẠT

Phase1 base1e1a67e; AGY handoff, Codex and separate reviewer each ran17Node controls PASS. No live diagnostic browser run yet. Existing headed FAIL/default UNKNOWN unchanged.

- **FF1 P2:** request guard at probe119-139 accepts POST read-only based on get_/list_/fetch_ prefix and ignores external POST. Reviewer mock reproduces PASS/counter0 for `/rest/v1/rpc/get_unreviewed_mutation`, `list_unreviewed_mutation` and `https://external.invalid/receive`. Require exact known read-RPC origin/path allowlist grounded in this Guest/input flow; every other non-read request must increment failure count, without logging URLs/payloads. Do not add generic name-based exceptions.
- **FF2 P2:** physical click post-state RAF=false is not reflected in status. Reviewer overrides only first Promise.race to false; probe returns PASS/account_tab_clickPASS while post_state.raf_commit=false. Make failed/unknown commit checks fail the measured action/overall diagnostic consistently, including Account/login clicks. Add exact negative controls; preserve real physical actions and observation metadata.

Fix only probe/controls/handoff, no lifecycle/product code yet. Node exact command remains permitted. Leave uncommitted; runtime NOT RUN. Maximum3correction rounds overall then Codex residual repair.

Runtime environment update: combined command including local anon renewal was rejected by policy; not retried through another route. No key renewal applied; anon is expired. No-submit focus/input diagnosis can proceed separately, with no Guest authorization/read-success acceptance. Existing39profile artifacts match prior7614c6a run and HTTP served bytes, deliberately reused; no fresh build claim. Update recipe limitations accordingly rather than requiring blocked renewal as accomplished. Explicit headed launch configs, not UA alone, provide headed provenance.
