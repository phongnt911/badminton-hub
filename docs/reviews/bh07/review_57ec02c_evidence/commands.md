# Reviewer commands and provenance

Checkout docs 57ec02c856f7e14f36aaa5a7add0356f1496c1f1 was clean. Tested runtime source is 249f12ed5b8ba042de1d48e9d5e06ffe7c125ada.

- node scripts/bh07_appheap/build_guard.js --self-test : exit0,8/8
- node docs/reviews/bh07/review_8914b2f_evidence/build_probe.js : exit1 expected reuse rejection
- python -X utf8 docs/reviews/bh07/review_8914b2f_evidence/probes.py : exit0, old cases rejected
- python -X utf8 scripts/bh07_appheap/verify_evidence.py : exit0 on author bundle
- python -X utf8 -m unittest tests.test_bh07_app_heap_oracle tests.test_bh07_app_heap_evidence tests.test_bh07_app_heap_build_guard tests.test_bh07_app_heap_review_controls : first exit1 (sandbox listen EPERM); same command with loopback permission exit0,66 tests
- flutter analyze --no-pub : exit0
- flutter test --no-pub : exit0,247 pass+1 skip
- node --check scripts/bh07_appheap/run_app_profile_heap.js : exit0
- PYTHONPATH=. python docs/reviews/bh07/review_57ec02c_evidence/extra_controls.py : exit0, records adversarial false-green observations; not an all-controls-PASS assertion suite
- python docs/reviews/bh07/review_57ec02c_evidence/link_audit.py : exit0, prints ten broken links at docs checkout before report
- node scripts/bh07_appheap/run_app_profile_heap.js --cycles 2 : NOT RUN, API absent and insufficient disk

Author bundle not regenerated or modified. Existing reviewer probes run unchanged. Hashes after commands match all four Git blobs of docs checkout. Reviewer Flutter progress CR normalized to LF in published log only. Linux Node24.19.0,Flutter3.47.7; author runtime Windows Node24.21.0,Flutter3.47.6. One initial local canary-fixture call omitted its summary argument; corrected reviewer fixture before recording final output; implementation and expectations unchanged.
