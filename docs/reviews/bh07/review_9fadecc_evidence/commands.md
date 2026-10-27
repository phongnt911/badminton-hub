# Reviewer commands

Clean checkout9fadecc3fe27a305072e5027bf00ba41b34fe6ca;tested source66bda0e7e3e1c2e983110e26a6300f6685c3a450.

- python -X utf8 -m unittest discover -s tests : exit0,258 tests,no skip
- python -X utf8 scripts/bh07_appheap/heap_oracle.py self-test : exit0,32/32;owned temporary fixture directory removed
- flutter analyze : exit0,no issues,with pub resolution
- flutter test : exit0,247 pass+1 skip,with pub resolution
- python -X utf8 scripts/bh07_appheap/verify_evidence.py --dir /workspace/badminton-hub/docs/reviews/bh07/retained_path_evidence : exit0
- python -X utf8 scripts/bh07_appheap/verify_evidence.py --dir /workspace/badminton-hub/docs/reviews/bh07/app_profile_heap_evidence : exit1 expected old contract rejection
- PYTHONPATH=. python docs/reviews/bh07/review_9fadecc_evidence/probes.py : exit0,observations of requested mutants and additional faults;not an all-negative-controls-passed suite
- node docs/reviews/bh07/review_9fadecc_evidence/fixture_probe.js : exit0,in-memory HTTP stub only,no DB traffic;preexisting row deleted by current helper
- node scripts/bh07_appheap/run_app_profile_heap.js : NOT RUN,local API absent and disk insufficient;no DB mutation attempted
- live query confirming fixture row absence : NOT RUN,no local database/API

All original/new author bundle hashes match Git blobs after checks;old bundle unchanged from base. Reviewer logs terminal CR/padding normalized for publication only. Reviewer Linux Flutter3.47.7;author Windows Flutter3.47.6 Chrome155. UI source and Flutter engine cache source read-only inspection;no source/app/backend/DB changes.
