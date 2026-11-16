# SC7/probe and login guard review — 16/11/2026

AGY correction3/3 repaired deliberate detector-probe assignment. Codex then directly repaired the remaining login dictionary issue under standing post-three-round authorization; no AGY round4. Publication secrets must remain distinct from intentionally permitted UI inputs.

Codex RED: new real-login control against inherited `loginActor` with the runner's full secret dictionary throws `refusing to inject canary (owner_password, cohost_password, member_password)`. Minimal `loginMeasuredActor` excludes those three keys only for login input guards and retains every fixture/control/anon guard. Both default Owner and post-actor calls use it. Real private-fixture input remains rejected. Detector assignment helper similarly excludes only the dedicated probe and retains full publication redaction.

Codex reran `node scripts/bh07_appheap/session_club_auth_listener_controls.js`:exit0,ALL_SESSION_CLUB_AUTH_LISTENER_CONTROLS_PASS. Separate reviewer examined the two-file delta against7c79880 and independently ran the Node controls:exit0; no P0/P1/P2 in this delta. Python scanner unchanged since Codex52PASS. This is source/control review, not independent browser/DB runtime QA.

The first clean runtime at7c79880 remains FAIL/baseline_probe; its original bundle is preserved in session_club_auth_listener_20261116_evidence/failed-r1 with cleanupPASS and root DB comparison21tables/94rows/Auth88->88. New runtime is NOT RUN at this checkpoint. No full auth_listeners/V2b/BH-07/V8 acceptance or main merge/deployment/pilot/BH-08.
