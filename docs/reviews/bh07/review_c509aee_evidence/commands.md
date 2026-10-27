# Reviewer commands / provenance

Checkout c509aeeebf9e978992e93f7ac79f2aa677f0ffac, clean before review. Source 29f44a8e8f86ff68e3ebe54f981cbb73ea5ceb2b; base ba90ac5c0a5b76d06d3d9d9cefce6249f24c8682. Linux, Node 24.19.0, Flutter reviewer 3.47.7 (author runtime 3.47.6).

Commands and actual exits: control_exits.json and regression_exits.json. The immutable probes were executed without editing their files/expectations. Graph probe needs PYTHONPATH=/workspace/badminton-hub; the first invocation without it exited 1 (ModuleNotFoundError: tests), then retried successfully with that environment. A first sandboxed socket preflight raised PermissionError; the read-only loopback preflight was repeated with granted local socket access. Neither failure is counted as an implementation test failure or hidden runtime PASS.

The initial regression run reported 312 Python tests / analyze clean / 247 Flutter +1 skipped, but its shell session exit output was unavailable after context compaction. Regression was repeated with a Python subprocess wrapper persisting numeric exit codes to regression_exits.json. Published logs are the latter run, without substituting author logs.

- python -X utf8 -m unittest discover -s tests
- /workspace/toolchains/flutter-review-3.47.7/bin/flutter analyze
- /workspace/toolchains/flutter-review-3.47.7/bin/flutter test
- node scripts/bh07_appheap/fixture_controls.js --self-test
- python -X utf8 scripts/bh07_appheap/heap_oracle.py self-test
- node --check scripts/bh07_appheap/run_app_profile_heap.js
- PYTHONPATH=/workspace/badminton-hub python -X utf8 docs/reviews/bh07/review_9fadecc_evidence/probes.py
- node docs/reviews/bh07/review_9fadecc_evidence/fixture_probe.js
- node docs/reviews/bh07/review_4184faf_evidence/redaction_probe.js
- node docs/reviews/bh07/review_4184faf_evidence/publication_probe.js
- node docs/reviews/bh07/review_04d1ea9_evidence/json_structure_probe.js
- python -X utf8 scripts/bh07_appheap/verify_evidence.py --dir <absolute bundle directory>

The R1 bundle passes; the two older bundles must exit 1. Each bundle has three payload hashes plus its manifest. Integrity audit compares disk payload bytes against the manifest and Git blobs, and requires no bundle changes from base. See integrity.json. No author manifest was regenerated. Review artifacts use UTF-8 LF; reviewer terminal carriage returns, if present, are normalized to LF and terminal trailing padding is trimmed when copied for publication.

Real runtime/DB query NOT RUN: see preflight.json. No stack was created, no fixture/DB mutation was performed. Source 29f44a8 has no new runtime here; inherited runtime remains source 86181de. Synthetic probes use temporary publication output and stub fixture requests, not real Auth/HTTP evidence.
