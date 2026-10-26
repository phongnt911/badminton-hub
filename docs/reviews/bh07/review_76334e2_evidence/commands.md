# Reviewer commands

Clean docs checkout 76334e21e41e6f9c018778d1f7b8d0a526012f3d; tested runtime source130af7d103cdea22c2f9ac9e4cb000f74ec02590.

- python -X utf8 -m unittest tests.test_bh07_app_heap_oracle tests.test_bh07_app_heap_evidence tests.test_bh07_app_heap_build_guard tests.test_bh07_app_heap_review_controls tests.test_bh07_app_heap_links : exit0,104 tests,no skips
- node scripts/bh07_appheap/build_guard.js --self-test : exit0,8/8
- python -X utf8 scripts/bh07_appheap/verify_evidence.py : exit0
- PYTHONPATH=. python -X utf8 docs/reviews/bh07/review_57ec02c_evidence/extra_controls.py : exit0, prior negative cases rejected,positive valid PASS
- python -X utf8 docs/reviews/bh07/review_8914b2f_evidence/probes.py : exit0, prior negative cases rejected
- python docs/reviews/bh07/review_57ec02c_evidence/link_audit.py : exit0,[]
- node docs/reviews/bh07/review_8914b2f_evidence/build_probe.js : exit1,expected reuse rejection
- flutter analyze --no-pub : exit0
- flutter test --no-pub : exit0,247 pass+1 skip
- node --check scripts/bh07_appheap/run_app_profile_heap.js : exit0
- PYTHONPATH=. python docs/reviews/bh07/review_76334e2_evidence/closure_controls.py : exit0,records adversarial observations; false-green AH7/AH8,not a passing assertion suite
- node scripts/bh07_appheap/run_app_profile_heap.js --cycles 2 : NOT RUN,no Supabase local API and insufficient disk

All original reviewer probes unchanged. Author bundle not regenerated or modified. Four author file hashes match Git blobs after all commands. Reviewer Linux Node24.19.0 Flutter3.47.7; author runtime Windows Node24.21.0 Flutter3.47.6. Reviewer Flutter progress CR normalized to LF for publication only; trailing terminal padding trimmed from reviewer analyze.log. No app/backend/DB changes.
