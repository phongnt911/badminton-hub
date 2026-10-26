# Reviewer verification commands

Clean checkout5f2b5a6883295554353ce5301eeb58539e6b88d1; runtime sourcec04ce551a4cb7fa8cbddcd5f06dbc790a39889f6.

- python -X utf8 -m unittest tests.test_bh07_app_heap_oracle tests.test_bh07_app_heap_evidence tests.test_bh07_app_heap_build_guard tests.test_bh07_app_heap_review_controls tests.test_bh07_app_heap_links : exit0,146/146,no skips
- python -X utf8 scripts/bh07_appheap/heap_oracle.py self-test : exit0,15/15,owned temp fixture dir removed
- node scripts/bh07_appheap/build_guard.js --self-test : exit0,8/8
- python -X utf8 scripts/bh07_appheap/verify_evidence.py : exit0
- PYTHONPATH=. python docs/reviews/bh07/review_0f11bb4_evidence/count_controls.py : exit0 of observation probe;positive accepted,all four negative fixtures rejected;actual mutant CLI exit1 with contradicts and empty stderr
- PYTHONPATH=. python docs/reviews/bh07/review_76334e2_evidence/closure_controls.py : exit0,prior expectations preserved
- PYTHONPATH=. python docs/reviews/bh07/review_57ec02c_evidence/extra_controls.py : exit0,prior expectations preserved
- python docs/reviews/bh07/review_8914b2f_evidence/probes.py : exit0,prior negative cases rejected
- node docs/reviews/bh07/review_8914b2f_evidence/build_probe.js : exit1 expected reuse rejection
- python docs/reviews/bh07/review_57ec02c_evidence/link_audit.py : exit0,[]
- PYTHONPATH=. python docs/reviews/bh07/review_5f2b5a6_evidence/reviewer_relation_controls.py : exit0,5/5 assertions matched
- flutter analyze --no-pub : exit0
- flutter test --no-pub : exit0,247pass+1skip
- node --check scripts/bh07_appheap/run_app_profile_heap.js : exit0
- node scripts/bh07_appheap/run_app_profile_heap.js --cycles 2 : NOT RUN,no local API and insufficient disk

Original reviewer probes unchanged;all author file hashes match Git blobs after commands. No author bundle regeneration,writes,DB/app/backend changes. Reviewer Linux Node24.19.0 Flutter3.47.7;author Windows Node24.21.0 Flutter3.47.6 Chrome155. Reviewer terminal CR/padding normalized for publication only. Groups of controls are listed per command,not a combined count of runtime scenarios.
