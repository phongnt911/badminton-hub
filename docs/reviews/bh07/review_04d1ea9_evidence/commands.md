# Reviewer R2 commands

Clean docs checkout04d1ea988574d120f52ba773b88dea3326bc89b6;code tested6b530c52e8020f778a1caa86890ea3ba87fb084f. Runtime bundle remains source86181de1df03e11b3ad537f1024405724db83bfb;not a runtime measurement of6b530c5.

- node docs/reviews/bh07/review_4184faf_evidence/redaction_probe.js : exit0,full/prefix20/40/60 redacted completely
- node docs/reviews/bh07/review_4184faf_evidence/publication_probe.js : exit0,FAIL artifact no longer has private fragment
- PYTHONPATH=. python -X utf8 docs/reviews/bh07/review_9fadecc_evidence/probes.py : exit0,previous RP observations preserved
- node docs/reviews/bh07/review_9fadecc_evidence/fixture_probe.js : exit0,collision no POST/DELETE
- python -X utf8 -m unittest discover -s tests : exit0,310/310,no skip
- node scripts/bh07_appheap/fixture_controls.js --self-test : exit0,6/6
- python -X utf8 scripts/bh07_appheap/heap_oracle.py self-test : exit0,34/34;owned temp fixture dir removed
- auditor absolute path retained_path_r1_evidence : exit0
- auditor absolute paths retained_path_evidence and app_profile_heap_evidence : exit1 each,explicitly checked
- flutter analyze : exit0,no issues,with pub resolution
- flutter test : exit0,247pass+1skip,with pub resolution
- node --check scripts/bh07_appheap/run_app_profile_heap.js : exit0
- node docs/reviews/bh07/review_04d1ea9_evidence/json_structure_probe.js : exit0 observations;ordinary canary produces valid JSON,true/false string canaries produce SyntaxError (expected valid JSON)
- new-source Chrome runtime/live DB query : NOT RUN,no local API and insufficient disk

Original probes unchanged. All runtime bundles unchanged from base;oracle/auditor/app/backend unchanged. New JSON probe uses actual writer in temp with synthetic strings and removes output after observation;no app/HTTP/DB call. Logs reviewer CR/padding normalized for publication only. Reviewer Linux Flutter3.47.7,author Windows Flutter3.47.6 Chrome155.
