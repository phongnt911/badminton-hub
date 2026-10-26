# Reviewer commands

Checkout: 8914b2ffb7f24d37c007e46a5973fbd4a8923a51, clean before commands.

- python -X utf8 scripts/bh07_appheap/verify_evidence.py : exit 0
- python -m unittest tests.test_bh07_app_heap_oracle tests.test_bh07_app_heap_evidence -v : exit 0, 18 tests
- node --check scripts/bh07_appheap/run_app_profile_heap.js : exit 0
- /workspace/toolchains/flutter-review-3.47.7/bin/flutter analyze --no-pub : exit 0
- /workspace/toolchains/flutter-review-3.47.7/bin/flutter test --no-pub : exit 0,247 pass,1 skip
- python docs/reviews/bh07/review_8914b2f_evidence/probes.py : exit 0; observed adversarial results, not an all-PASS assertion suite
- node docs/reviews/bh07/review_8914b2f_evidence/build_probe.js : exit 0; isolated source branch, not Chrome
- node scripts/bh07_appheap/run_app_profile_heap.js --cycles 2 : NOT RUN, local API absent and disk insufficient (see runtime_preflight.json)

Author bundle hashes before/after equal; no generate or runtime writes in author bundle. Reviewer Flutter progress CR converted to LF during packaging. Review probes operate on temporary clones and leave source/author bundle unchanged.
