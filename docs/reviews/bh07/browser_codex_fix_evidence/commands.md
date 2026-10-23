# Codex tự sửa/tự kiểm — không phải review độc lập

Source/base và hash trong environment.json; exit process thật trong exits.json.
Recipe Linux và patch runner đi kèm. Không đổi assertion/selectors cho hạ tầng.

Lệnh chạy trên source commit sạch:
- Flutter3.47.7: flutter analyze; flutter test
- BH02_TEST_CONTAINER=bh07-http-review-db python -u docs/reviews/bh07/run_bh07_tests.py
- python run_local_stack.py (recipe local, chạy trước DB/build/browser)
- python build_web.py (runtime public anon riêng; no-web-resources-cdn)
- python -m http.server 8088 --bind 127.0.0.1 --directory build/web
- python prepare_browser.py; node /tmp/bh07-http-review-runtime/browser_runner.js
- node run_negative_controls.js trên copy ngoài repo, 41 case
- python run_verifier_controls.py trên copy; fault manifests chỉ generate trên copy tạm
- python run_mutant_controls.py trên copy
- node extra_controls.js: nguyên probe reviewer, chỉ đổi đường dẫn output

Đóng gói: clean_and_manifest.py --generate --evidence-dir docs/reviews/bh07/browser_codex_fix_evidence
Reviewer chỉ chạy: clean_and_manifest.py --verify --evidence-dir docs/reviews/bh07/browser_codex_fix_evidence
Snapshot toàn bộ file trước/sau verify phải giống nhau; không --generate khi review.
Raw output/JSON ở đây là lần chạy mới của Codex; bằng chứng cũ không bị ghi đè.
