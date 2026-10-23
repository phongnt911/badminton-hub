# Reproduction — local only, Codex self-verification

See late_response_handoff.md for complete sequence and source-SHA distinctions.
1. Start isolated stack with run_local_stack.py (adjust scratch path only); seed original fixture SQL.
2. flutter analyze; flutter test; build_web.py (runtime local public anon; no-web-resources-cdn).
3. python -m http.server 8088 --bind 127.0.0.1 --directory build/web
4. prepare_browser.py; node /tmp/bh07-http-review-runtime/browser_runner.js — original11 gates, produces completed fixture.
5. BH07_BROWSER_DRIVER=/tmp/bh07-http-review-runtime/browser_runner.js BH07_LATE_EVIDENCE=<scratch> node scripts/bh07_browser/run_late_response.js
6. node scripts/bh07_browser/run_late_response_controls.js —21 controls.
7. run_negative_controls.js on disposable script copy —41 controls, keep original evidence unchanged.
8. Reviewer: python scripts/bh07_browser/clean_and_manifest.py --verify --evidence-dir docs/reviews/bh07/late_response_evidence
Never --generate on handed-off evidence during review. Author generated manifest at packaging time.
Initial refresh selector attempt exit1 is retained; fixed selector reads semantic text as well as aria. Not an app finding.
