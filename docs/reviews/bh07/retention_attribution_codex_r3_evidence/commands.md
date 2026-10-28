# Codex direct implementation/self-check, authorized round3

Owner explicitly authorized “mở vòng 3 sửa” after review5226a3d. Codex wrote the previous review and now implements the fix: this is NOT independent review. Base a35c219d7c8f61742ad0753359681e72c9bf5a32; source f11d20f6c5025f7f774c266298bc0309fcd0de0c. No app/backend/contract or historical bundle changes.

TDD: the two new unittest methods ran against old source before changes; red exit1,8 failing assertions (some subcontrols already blocked). red.log/red_exit.json kept. targeted7/7 then passes. Source commit created after targeted verification; full Python/Flutter runs start on source commit with dirty_before_run empty, stored in provenance.json. Source hashes distinguish the implementation under test from inherited runtime QA b13e468. No new runtime browser/build/SQL claimed.

Commands:
- python -m unittest tests.test_bh07_retention_attribution.TestRetentionAttribution.test_round_two_closure_probe_is_fail_closed tests.test_bh07_retention_attribution.TestRetentionAttribution.test_cycle_actor_and_record_links_are_validated -v
- python -m unittest tests.test_bh07_retention_attribution -v
- python -X utf8 -m unittest discover -s tests
- /workspace/toolchains/flutter-review-3.47.7/bin/flutter analyze
- /workspace/toolchains/flutter-review-3.47.7/bin/flutter test
- python docs/reviews/bh07/review_37b4954_evidence/probes.py
- python docs/reviews/bh07/review_eda1ead_evidence/extra_controls.py
- python docs/reviews/bh07/review_5226a3d_evidence/closure_controls.py
- python -X utf8 scripts/bh07_appheap/audit_retention_attribution.py --out-dir /workspace/scratch/attribution-fix3/audit_output

Original three reviewer probe files were run unedited, input/expectations unchanged. Probe process exit0 publishes observations; control_exits.json stores actual inner CLI exits:3 positive0,10 mutant1. Mutants use owned temp inputs/outputs, not DB/application mutations. New tests additionally reject wrong actor,risk root/class mismatch,scan ok=false,frame/hash mismatch and rendered scope mismatch.

The attribution auditor reads the original sanitized QA summary; generated attribution_audit.json therefore still names runtime QA sourceb13e468. provenance.json and summary.json identify actual modified auditor sourcef11d20f6. This is not a new heap measurement or retagged old runtime.

Generic verifier on five old bundles:exit0 and before/after identical hashes. Semantic QA/R1:exit0; two obsolete bundles:exit1 deliberately. Outputs/exits in integrity.json. No author manifest regenerated. Own new bundle manifest only, verified readonly; hashes also compared with staged Git blobs before final commit.

Reviewer Flutter3.47.7 differs from original QA3.47.6; no new build parity claim. Published self-check logs normalize terminal CR/padding to strict UTF-8 LF. Original historical bundles unchanged. Regression numeric exits recorded directly. No new DB suite run: app/backend/DB unchanged. NOT RUN remains in handoff.
