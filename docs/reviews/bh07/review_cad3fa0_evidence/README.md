# Reviewer evidence cad3fa0

Read report ../review_cad3fa0.md. Linux reviewer; prior baseline authorship disclosed.
No full CLI runtime created. environment_and_exits.json states commands and limits.

Reproduce from repo root:
- python docs/reviews/bh07/review_cad3fa0_evidence/run_isolated_tests.py
- python docs/reviews/bh07/review_cad3fa0_evidence/probes.py
- python docs/reviews/bh07/review_cad3fa0_evidence/timeout_resistance.py
- python docs/reviews/bh07/review_cad3fa0_evidence/audit_bundles.py

The first command contains the dangerous unchanged unit test in a new session.
The resistance supervisor kills only its own probe group after a bounded deadline.
probes.py changes AST in memory for controls; no implementation file is edited.
Output logs are UTF-8 LF; terminal progress carriage returns were normalized.
No old bundle or manifest was regenerated. Missing historical logs are inherited.
