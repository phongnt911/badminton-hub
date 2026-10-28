# Reviewer 28/10/2026 Asia/Saigon

Clean checkout eda1eadd (full SHA in integrity.json), base272bb29d. No implementation changes.

- Original reviewer probe: python docs/reviews/bh07/review_37b4954_evidence/probes.py > probes.json (exit0 observations; positive CLI0, three mutant CLI1).
- New reviewer probe: python docs/reviews/bh07/review_eda1ead_evidence/extra_controls.py > extra_controls.json. Probe publishes observations and exits0; each underlying CLI exit is stored. Positive0; four additional incomplete/mismatched-evidence mutants incorrectly exit0. Temporary input/output owned by probe is removed; QA bundle is read-only.
- python -X utf8 -m unittest discover -s tests
- Flutter reviewer3.47.7 analyze / test (with pub), numeric exits stored in exits.json; author Flutter3.47.6 runtime remains inherited, not a new browser run.
- Generic clean_and_manifest.py --verify on five bundles. Author current5/5 and historical3/3 each; hashes before/after and Git blobs audited, original bundles not regenerated. Semantic QA verifier exit0 was checked separately; it does not validate the new attribution wrapper's CLI mutant behavior.
- Link audit84 relative Markdown targets exist in the three updated author docs. A first ad-hoc audit asserted no file:/// text at all and stopped on the handoff's literal description of a removed URL; corrected audit checks actual Markdown destinations. This is not an author link failure. A first ad-hoc wrapper also aborted before saving its result; the reproducible integrity_audit.py replay is the published completed audit.

Only reviewer logs are normalized to UTF-8 LF with terminal carriage returns/trailing padding trimmed. No raw heap, real credentials or source sentinel values published in reviewer probes. No DB/browser/runtime mutation. Own manifest only, verify readonly.
