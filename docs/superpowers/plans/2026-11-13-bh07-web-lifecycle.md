# BH-07 Web lifecycle and retry continuation

**Goal:** Measure start/check-in/finalize/offline-complete/retry/summary on local Edge and Firefox without altering the inherited completed fixture or weakening V2 acceptance.

**Authorization/spec:** Owner “tiếp tục”; AGENTS standing Anti implementation/Codex review up to three corrections then direct repair. Readiness §4.3 and the remaining rows in `web_v2_extension_runtime_20261113.md`. No merge/deploy/pilot/BH-08, remote changes or risk acceptance.

**Approach:** Reuse existing Flutter profile build and local four-container stack. Anti owns only `scripts/bh07_browser/web_lifecycle_scenario.js` and its handoff. Codex owns runtime fixture/oracle/evidence orchestration. Existing branch is isolated from main; preserve all inherited evidence. No application/backend/schema changes unless a demonstrated defect requires a separately recorded repair.

## Task 1: Two-phase UI scenario

- Anti writes a small Playwright CLI expression, using actual Owner login and real buttons, with loopback/session guards and explicit fixed expectations.
- Prepare phase starts a fresh published fixture, checks in both players, finalizes 200000 total, attempts completion offline and requires a real error. Return only safe fixture request data to ignored capture.
- Codex reads DB between phases: in_progress/version2, current revision, two charges100000, no completed audit/operation.
- Retry phase uses the same page/provider intent, exact first body, matching request UUID/full payload, POST200 and actual completed UI/summary.
- Codex reads DB: completed/version3, exactly one completion operation/audit matching captured request ID. Negative controls must reject malformed request/payload or wrong expected total.
- Review after handoff, no timeout/interruption solely for duration. Maximum three Anti correction rounds before Codex direct repairs under standing authorization.

## Task 2: Owned runtime and cleanup

- Record baseline fingerprint before seeding. One fresh UUID set per browser; collision preflight, transaction inserts without upsert, persisted ownership marker and readback.
- Run Edge and Firefox in separate profiles; Firefox software headed uses the previously measured configuration and foreground operation. Default headed remains UNKNOWN unless new evidence supports a changed conclusion.
- Cleanup only owned session/children and attributable operation/audit rows; verify absence and baseline public/schema/roles fingerprints. Auth activity and sequence changes are separately disclosed.
- Keep historical artifacts byte-identical; new bundle has exact source/build/served hashes, safe results, DB receipts, cleanup and manifest. Independent reviewer checks source/artifact only unless they actually rerun runtime.

## Task 3: Report and checkpoint

- Update the current matrix with measured scope and all remaining NOT RUN/UNKNOWN rows. Clipboard/QR and Firefox default investigation remain distinct from lifecycle evidence.
- Do not report whole V2 or BH-07/V8 accepted. Commit only the reviewed local delta.

## Read-only follow-up: copy and QR fallback

Owner continuation also covers the remaining browser copy/QR rows. Anti separately owns `web_copy_qr_scenario.js` and its handoff, with a separate correction counter. Use the inherited completed fixture: Cohost count-only clipboard and unpaid Guest A fee/receiver instructions. Expected receiver values come from a read-only local DB transaction into ignored configuration. Abort only the external QR image request to test the actual UI fallback; never replace the local API or submit a payment. Clipboard permission unsupported remains NOT RUN, while unexpected grant/read/mismatch errors must fail. Publish no raw receiver/reference/clipboard content. Final fingerprint comparison includes this follow-up.
