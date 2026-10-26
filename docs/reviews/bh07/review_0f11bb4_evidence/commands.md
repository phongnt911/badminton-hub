# Reviewer verification commands

Clean checkout0f11bb4239f2aedd1fe17a789b34474026e06577; tested runtime sourcec3ca02e4f4a17cea7ac48526c398b212ab1445a9.

- python -X utf8 -m unittest tests.test_bh07_app_heap_oracle tests.test_bh07_app_heap_evidence tests.test_bh07_app_heap_build_guard tests.test_bh07_app_heap_review_controls tests.test_bh07_app_heap_links : exit0,123/123,no skips
- node scripts/bh07_appheap/build_guard.js --self-test : exit0,8/8
- python -X utf8 scripts/bh07_appheap/verify_evidence.py : exit0 on author bundle
- PYTHONPATH=. python -X utf8 docs/reviews/bh07/review_76334e2_evidence/closure_controls.py : exit0,escaped/literal equal,retained cycle FAIL,missing metadata rejected
- PYTHONPATH=. python -X utf8 docs/reviews/bh07/review_57ec02c_evidence/extra_controls.py : exit0,old negative cases rejected
- python -X utf8 docs/reviews/bh07/review_8914b2f_evidence/probes.py : exit0,old negative cases rejected
- node docs/reviews/bh07/review_8914b2f_evidence/build_probe.js : exit1 expected reuse rejection
- python docs/reviews/bh07/review_57ec02c_evidence/link_audit.py : exit0,[]
- flutter analyze --no-pub : exit0
- flutter test --no-pub : exit0,247 pass+1 skip
- node --check scripts/bh07_appheap/run_app_profile_heap.js : exit0
- PYTHONPATH=. python docs/reviews/bh07/review_0f11bb4_evidence/count_controls.py : exit0,records count/presence false-green; not a passing assertion suite. Mutant auditor CLI exit0 is unexpected acceptance.
- node scripts/bh07_appheap/run_app_profile_heap.js --cycles 2 : NOT RUN,local API absent,disk insufficient

Author bundle preserved byte-for-byte; all file hashes match Git blobs after commands. Original reviewer probes unchanged. Reviewer Linux Node24.19.0/Flutter3.47.7,author Windows Node24.21.0/Flutter3.47.6/Chrome155. Reviewer logs normalize progress CR to LF and trim terminal padding. App/backend/DB untouched.
