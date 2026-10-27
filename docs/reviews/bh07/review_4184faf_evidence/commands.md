# Reviewer R1 commands

Clean checkout12e0aa0313c876aea0c0bf0f71544778b8c713a9;docs4184fafac7c19ff764e9f41a94a219f4a54c35ed;tested source86181de1df03e11b3ad537f1024405724db83bfb.

- PYTHONPATH=. python -X utf8 docs/reviews/bh07/review_9fadecc_evidence/probes.py : exit0,unchanged original;prior observations updated
- node docs/reviews/bh07/review_9fadecc_evidence/fixture_probe.js : exit0,unchanged original;collision no POST/DELETE
- node scripts/bh07_appheap/fixture_controls.js --self-test : exit0,6/6
- python -X utf8 -m unittest discover -s tests : exit0,302/302,no skip
- python -X utf8 scripts/bh07_appheap/heap_oracle.py self-test : exit0,34/34;owned temp fixture dir removed
- python -X utf8 scripts/bh07_appheap/verify_evidence.py --dir /workspace/badminton-hub/docs/reviews/bh07/retained_path_r1_evidence : exit0
- same auditor abs path retained_path_evidence and app_profile_heap_evidence : exit1 each expected old contract rejection
- flutter analyze : exit0,no issues,with pub resolution
- flutter test : exit0,247pass+1skip,with pub resolution
- node docs/reviews/bh07/review_4184faf_evidence/redaction_probe.js : exit0,observations show prefix40/60 leftover fragments;positive full/prefix20 fully masked
- node docs/reviews/bh07/review_4184faf_evidence/publication_probe.js : exit0,actual writer to temp;FAIL verdict but run.log still has private canary fragment;temp output removed
- node scripts/bh07_appheap/run_app_profile_heap.js : NOT RUN,local API absent and disk insufficient
- live DB row absence query : NOT RUN,no local DB/API

New probes are observations,not passing negative-control suites. Only synthetic canaries/stubs;no source/app/backend/DB mutation. All author bundle hashes match Git after commands;old bundles unchanged from base. Reviewer terminal CR/padding normalized for publication;author bytes unchanged. Reviewer Linux Flutter3.47.7,author Windows Flutter3.47.6 Chrome155.
