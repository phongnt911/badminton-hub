# BH-07 Web synthetic payment continuation

**Goal:** Measure Guest submit → Owner confirm → Guest paid-state read on Edge and Firefox local, including DB/audit/ledger boundaries.

**Authorization/spec:** Owner “tiếp tục”, AGENTS standing Anti implementation/Codex review up to three corrections then direct repair. Readiness §4.3 and remaining payment row after `web_lifecycle_copy_runtime_20261113.md`. No real transfer, bank integration, remote environment, merge/deploy/pilot/BH-08 or risk acceptance.

**Ownership:** Anti owns only `web_payment_scenario.js` and its handoff. Codex owns disposable fixture, runtime/DB oracle, controls, report/evidence and status updates. Existing branch is isolated from main. Preserve inherited evidence and source.

1. Create a UUID-owned completed/current fixture per browser, with two100000 charges and synthetic receiver, payments0/ledger0. This setup is not a measured lifecycle transition. Collision preflight, transaction without upsert, readback ownership and baseline fingerprint.
2. Run three UI phases in fresh profiles: Guest submit, Owner confirm, Guest reads paid state. Capture exact local RPC bodies/IDs and bind DB checks to them; never publish reference/receiver/token/snapshots. Submitted must not count as paid and must not create ledger.
3. Confirm must create precisely one income ledger for the same payment and correct actor/request audits/operations. Guest afterwards sees100000/100000/0, no new-payment/QR CTA. No mutation-replay or offline-payment claim.
4. Negative controls reject wrong target/amount/status/actor/request/ledger/paid boundaries; review source and runtime receipts. Correct up to three Anti rounds, then Codex directly fixes residual concrete findings.
5. Cleanup only owned ledger/audit/operation/session children, verify absent and full public/schema/roles baseline equality with Auth activity separately recorded. Independent source/control/artifact review; no independent runtime claim unless rerun.
6. Publish exact source/build/served hashes, safe receipts and manifest; update current matrix without closing full V2/BH-07/V8. Commit reviewed local delta.
