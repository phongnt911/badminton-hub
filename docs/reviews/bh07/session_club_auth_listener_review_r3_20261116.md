# Session/Club listener clean runtime failure — correction3/3

Clean source7c79880d9cae405131207c8e1d62385a403d9f3c (git_dirtyfalse), fresh profile artifacts/served binding succeeded, Edge launched. Runtime aborted at cycle1 `baseline_probe`: `refusing to inject canary (probe) via evaluate or input`. No heap epochs completed; verdictFAIL remains immutable.

**SC7 P2:** `run_session_club_auth_listener.js:819,828` passes the whole `secretValues` dictionary (including deliberate detector `probe`) to safeEvaluate while assigning that exact probe to window. Guard correctly rejects. Existing instructions runner passes private canaries only for this deliberate control injection. Separate publication secrets from the injection guard: omit only the synthetic detector probe for the two intentional probe assignments, retain every actual private fixture/canary/credential in guard, and keep probe redaction in all output. Do not add a generic unsafe evaluate bypass or disable canary assertions.

Add a Node control exercising the real safeEvaluate path for intended control injection and proving actual private fixture/canary injection still rejects. Existing performEpochAction mock had hidden the integration error. Run exact permitted Python and Node control commands, preserve all existing positive/negative cases. Minimal helper/export for this dedicated assignment is acceptable; avoid unrelated changes.

Codex root DB comparison after failure:21public tables/94rows/schema/roles/other sequences unchanged, Auth88->88; fixture cleanup verified, zero payment/ledger/audit/operation mutation, profile/dumps/state removed. Root source remains NOT RUN for listener coverage despite cleanupPASS. Historical bytes/verdict must stay intact.

This is AGY correction3/3 under existing authorization. Codex fixes remaining concrete findings afterward; no AGY round4. No app/backend/schema/remote/main merge/deploy/pilot/BH-08 or risk acceptance.
