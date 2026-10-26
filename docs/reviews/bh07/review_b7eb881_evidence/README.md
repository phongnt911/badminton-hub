# Reviewer evidence — V2b b7eb881

Read ../review_b7eb881.md. No implementation files changed.
Full runner executed at clean source16e5b51 in a temporary worktree: real PASS7/7 VERIFIED.
Tests32, AST12, verifier5, analyze0, Flutter247+1skip, author bundle4/4 completed separately.
Old reviewer probes were replayed unchanged, including protocol_probe.py.

Replay exact-duplicate controls from repo root:
python docs/reviews/bh07/review_b7eb881_evidence/duplicate_probe.py

The negative fixtures mutate protocol data only. Main-boundary exit is a stubbed external-command control, not a second real runner.
The real Flutter log separately proves two distinct test IDs may have identical full names.
Its source fixture is stored as duplicate_names_fixture.txt; copy it to a temporary .dart file to rerun Flutter without changing app/test source.
runner_output is the new reviewer full run; original manifest bytes preserved as original_manifest.txt for recursive verifier compatibility.
No author bundle was regenerated or overwritten. Logs normalized UTF-8 LF. App-profile heap remains NOT RUN.
