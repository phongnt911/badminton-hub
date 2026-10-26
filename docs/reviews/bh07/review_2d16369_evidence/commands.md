# Coordinator audit commands

Checkout2d16369bee16bd2a98a356dab962ec1d3ad20762 clean before audit. QA runtime tested97d0e7e3be59fa8504d7ec0d6b55a0e67495ebff;code tree equals acceptedc04ce551a4cb7fa8cbddcd5f06dbc790a39889f6.

- python -X utf8 scripts/bh07_appheap/verify_evidence.py --dir docs/reviews/bh07/review_runtime_97d0e7e_evidence : exit1,relative path formatter ValueError after semantic verification;not counted as PASS
- python -X utf8 scripts/bh07_appheap/verify_evidence.py --dir /workspace/badminton-hub/docs/reviews/bh07/review_runtime_97d0e7e_evidence : exit0
- python -X utf8 scripts/bh07_appheap/verify_evidence.py : exit0 author bundle
- python scripts/bh07_browser/clean_and_manifest.py --verify --evidence-dir docs/reviews/bh07/review_runtime_97d0e7e_evidence : exit0,3/3
- python scripts/bh07_browser/clean_and_manifest.py --verify --evidence-dir docs/reviews/bh07/app_profile_heap_evidence : exit0,3/3
- python docs/reviews/bh07/review_2d16369_evidence/audit_runtime_bundle.py : exit0,QA metadata/log/Git/manifest reconciliation
- QA report bytes/secret/raw-sentinel scan : PASS
- git diff --check 97d0e7e..2d16369b : exit0

No Flutter/Python suite or Chrome runtime replay in this coordinator turn: QA delta is docs/evidence only. Prior coordinator review_5f2b5a6 contains independently run146 Python/247 Flutter+1skip;do not attribute those to fresh QA runtime. QA reports suite replays but its4-file runtime bundle does not contain individual suite stdout logs. All QA/author hashes match original Git blobs after audits;all old artifacts unchanged,no generate,source/DB changes.
