# Reviewer independent checks — 28/10/2026 Asia/Saigon

Clean checkout6f59f5e9fb9a8280a46c70aa9ca237b81fb8a023. Runtime source claimed in request/handoff cd25e1ea1f93e9a7eecdb8da951a37c56bf0a624 does not resolve. Actual parent cd25e1e3557e2013e8991b2031a240818ee84c96 matches runtime summary/report and source tree. Review is of actual branch/code/evidence, not the nonexistent SHA. Source-scope/manifest facts and before-report clean status are in integrity.json.

All six requested commands ran independently; exact commands/numeric exits in exits.json. Flutter reviewer3.47.7 vs runtime author3.47.6. Python325,fixture8,Flutter247+1skip,analyze0. New/old semantic auditors0. No new Chromium/heap/SQL measurement; author runtime observations are audited, not relabeled as a reviewer run. No application/backend/DB changes.

Probe replay from repo root:
python docs/reviews/bh07/review_6f59f5e_evidence/probes.py

Probe invokes the current real renderer, oracle and evidence auditor; clones only sanitized author bundle into an owned TemporaryDirectory under ignored build/ and deletes it afterwards. No original source/bundle edit. For missing-payment scenario, it recomputes derived verdict/notes/risks exactly as runner would; regenerates report with real runner.renderReport and recomputes clone manifest. This isolates semantic validation rather than an intentionally broken hash/report. Positive requires0; every listed negative is expected1. Probe itself exits0 to record observations, not claim all controls pass. Actual inner auditor exits/outputs are in probes.json. Current false-cleanup explicit flag control does reject1; omitted receipt/flag/wrong receipt ID and payment never loaded wrongly pass0.

Five bundles audited: new finance3/3 and historical QA/R1/two older3/3 each, all payload bytes equal Git and manifest; generic readonly verify0, before/after hash identical; four old bundles unchanged from base. Original manifests never regenerated. Tracked raw heap file count0. Reviewer does not claim new DB query confirms cleanup; fixture receipt is author evidence with the separate fail-open flaw noted.

Only reviewer logs normalize terminal CR/trailing padding to UTF-8 LF. Own manifest generated separately and verified readonly, staged blob hashes checked. Reviewer wrote only report/status/evidence, no implementation changes. New profile Chưa đạt does not reopen old accepted AT1–AT6 or two-expense-ID runtime gates.
