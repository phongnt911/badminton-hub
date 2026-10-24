# Review độc lập V1 — Browser/Offline/Reopen và response Owner trả trễ (BH-07)

Ngày 24/10/2026. Người review/QA **không tham gia viết hoặc sửa gói Browser**. Lượt này chỉ chạy kiểm chứng độc lập trên checkout sạch, không sửa app/backend/script và không ghi đè bằng chứng cũ.

- Nhánh: `feat/bh07-browser-independent-review`, tạo từ `6283dbb`.
- Tested checkout: `6283dbb3b1ae217e87130acb4ed5efae5bf170c7`, `is_dirty=false` trước và sau khi chạy.
- Mốc đối chiếu: baseline `a6d58af`, response trễ `c4ce99b`, control sau sửa `417ee30`.
- Cây app không đổi giữa bốn mốc (đã kiểm bằng tree hash): `lib` `520a38be…`, `test` `8d3574a6…`, `supabase` `a2de8edc…`. `git diff 417ee30 6283dbb -- lib test supabase scripts/bh07_browser` rỗng.
- Bằng chứng của lượt này: [review_6283dbb_evidence/](review_6283dbb_evidence/), manifest `48/48` file, `0` secret/JWT ngoài allowlist, UTF-8 LF.

## 1. Môi trường độc lập

Stack local cô lập `bh07v1-*` (PostgreSQL 17.11, GoTrue 2.197.0, PostgREST 16.4, Kong 2.8.1), gateway `http://127.0.0.1:55422`, web `http://127.0.0.1:8088`. Stack này tách khỏi Supabase của dự án ở `54321` và khỏi stack `bh07ir-*` ở `55421`. Đã nạp 18 migration trong `supabase/migrations`, `scripts/bh07_http/seed.sql`, fixture UI của `seed_setup.js` và tạo 7 user Auth. Mật khẩu/JWT/anon key chỉ nằm ngoài repo, không công bố.

Máy chạy: Windows, Flutter 3.47.6 / Dart 3.13.5, Chrome 155.0.8059.85, Node 24.21.0, Python 3.12.7. Khác môi trường tác giả (Linux, Chromium 154, Flutter 3.47.7) — xem mục 5.

Chỉ sửa đường dẫn/port hạ tầng trong **bản sao dùng một lần**; assertion và selector giữ nguyên. Toàn bộ khác biệt nằm trong [runner-infra.patch](review_6283dbb_evidence/runner-infra.patch).

## 2. Lệnh đã chạy và kết quả

| Bước | Lệnh (rút gọn) | Exit | Kết quả |
|---|---|---|---|
| Analyze | `flutter analyze` | 0 | 0 issue |
| Unit/widget | `flutter test` | 0 | 240 pass, 1 skip |
| Web build | `flutter build web --no-pub --no-web-resources-cdn --dart-define=APP_ENV=test --dart-define=SUPABASE_URL=… --dart-define=SUPABASE_ANON_KEY=…` | 0 | `build/web` |
| Baseline UI | `node browser_runner.js` | 0 | **11/11 PASS**, 12 ảnh, 12 hash khác nhau, 240,8 s |
| Response trễ | `node late_runner.js` | 0 | **2/2 PASS**, 4 ảnh |
| Negative controls | `node run_negative_controls.js` (worktree sạch `6283dbb`) | 0 | **41/41** đúng kỳ vọng (8 PASS + 33 FAIL), 0 HARNESS_ERROR |
| Late controls | `node run_late_response_controls.js` | 0 | **21/21**, bắt 2 mutant cô lập |
| Verifier controls | `python run_verifier_controls.py` | 0 | **9/9**, mọi case readonly |
| Mutant manager gate | `python run_mutant_controls.py` | 0 | baseline exit 0, mutant `if (true)` exit 1 |
| Manifest tác giả | `clean_and_manifest.py --verify` × 2 | 0 | **52/52** và **44/44**, không đổi file |

Baseline và late chạy trên cùng checkout; DB sau baseline: `sessions = completed|3`, `operation_requests = 4`, đúng 1 `SESSION_COMPLETED`, 1 `START_SESSION`, 1 `BILLING_FINALIZED`, 1 `RECORD_ATTENDANCE`.

## 3. Đối chiếu yêu cầu V1

**11 ca baseline** (`browser_summary.json`): login Owner, start session, attendance check-in, finalize charges, offline-retry, manager clipboard privacy, cohost count-only, history filter theo CLB, member isolation, reopen/F5, logout sạch — tất cả PASS trong lần chạy của reviewer, không dùng log tác giả.

**2 ca response trễ** (`late_summary.json`): POST `get_session_summary` thật của Owner bị giữ ở biên response, status 200, `can_view_finance=true`, `expenses_total_vnd=200000`; thả sau khi logout và login actor mới. `bodyHash = deliveredHash = d36f071e…` cho cả hai ca; `performance.timeOrigin` trước/sau bằng nhau (`1792813503808.2`), tức cùng document. Cohost: clipboard đúng 4 dòng count-only, không nhãn/số tiền, có nút copy. Member: history rỗng, không entry tổng kết, không nút copy. 4 sample UI sau release không thấy card tài chính, không thấy profile Owner.

**Privacy/clipboard**: predicate dùng chung giữa runner và negative controls; 33 control âm tính bị từ chối đúng, gồm field tiền lạ, regex VNĐ/đ, dòng clipboard ngoài allowlist và rò rỉ contact/bank.

**Offline/retry/`request_id`**: đúng 2 POST `complete_session`, cùng `p_request_id`, cùng `p_session_id`, cùng `p_expected_version`, toàn payload canonical bằng nhau; UI hiện đúng thông báo lỗi transport khi offline; DB giữ `in_progress` trong lúc lỗi và chỉ `completed|3` sau retry; `operation_requests` theo `request_id` = 1 và `SESSION_COMPLETED` = 1.

**Same-SPA**: được assert trực tiếp bằng `performance.timeOrigin` trong cả hai ca response trễ ([run_late_response.js:80,143](../../../scripts/bh07_browser/run_late_response.js)). Log baseline không có `Page.navigate`/`Page.reload` giữa TC01–TC09; chỉ TC10 reload cho ca reopen.

**Provenance**: `lib/test/supabase` giống nhau ở cả bốn SHA; `scripts/bh07_browser` ở `6283dbb` khớp `417ee30` (hash từng file trong [source_hashes.json](review_6283dbb_evidence/source_hashes.json)); bằng chứng tác giả `browser_codex_fix_evidence` mô tả đúng run `a6d58af`, `late_response_evidence` mô tả đúng run `c4ce99b`, còn bằng chứng control `417ee30` nằm ở `browser_closure_evidence` (khớp `review_c4ce99b.md`).

**Manifest readonly**: verify hai gói tác giả exit 0, `git status` trước/sau giống nhau (rỗng); không dùng `--generate` trên bằng chứng bàn giao.

## 4. Phát hiện

**Không có P0/P1/P2 mở trong phạm vi V1 local.** Không có lỗi app quan sát được trên các bề mặt đã chạy; không có control nào bị nhận PASS sai; không có khác biệt giữa kết quả reviewer và tuyên bố của tác giả (11/11, 2/2, 41, 21+2 mutant, 9, 52/44).

## 5. Hạn chế và khác biệt đã ghi nhận (không mở P2)

1. **Môi trường khác tác giả**: Windows/Chrome 155/Flutter 3.47.6 thay vì Linux/Chromium 154/Flutter 3.47.7. Cây app trùng hash nên khác biệt chỉ ở tầng chạy.
2. **`api_url` là hằng số, không phải quan sát**: [run_browser_verification.js:1248](../../../scripts/bh07_browser/run_browser_verification.js) ghi cứng `http://127.0.0.1:54321`. Bản sao của reviewer đổi literal này thành `55422` (metadata, xem patch); backend thực được xác nhận gián tiếp qua response 200 thật và side-effect DB.
3. **Baseline không tự assert định danh document**: TC07 ([run_browser_verification.js:799-806](../../../scripts/bh07_browser/run_browser_verification.js)) chỉ không gọi navigate/reload. Bằng chứng same-SPA độc lập của lượt này là assert `timeOrigin` trong runner response trễ, cộng log không navigate/reload giữa TC01–TC09.
4. **`web_build`/`db_reset` ghi `NOT RUN` trong `exits.json` của driver**: build và seed fixture chạy ngoài driver, exit 0 ghi tại [web_build_exit.txt](review_6283dbb_evidence/web_build_exit.txt) và [environment.json](review_6283dbb_evidence/environment.json).
5. **`late_response_evidence/regression_controls.json:3` ghi `source_sha: "UNKNOWN"`** (chạy trong bản sao tạm). Provenance bù bằng `environment.json` của gói (hash khớp `c4ce99b`); lượt reviewer ghi đúng `6283dbb`.
6. **Ảnh Member trước/sau release trùng byte** (cả gói tác giả và lượt reviewer). Việc response được thả chứng minh bằng `heldAt/loginAt/releaseAt/deliveredAt` và body hash, không bằng delta ảnh.
7. **`base_sha` trong baseline summary là `1fc7e2e`** (base lịch sử của nhánh), không phải checkout `6283dbb`; trường `tested_checkout_sha` mới là SHA đã chạy.

## 6. NOT RUN

- Mobile/thiết bị khác, browser khác Chromium/Chrome đã dùng.
- Đo private Dart heap/cache sau đổi actor.
- Banking/VietQR/webhook thật.
- Staging/production, managed Supabase, backup/PITR/offsite/encryption/retention, concurrent writers.
- `supabase db reset` từ zero và full Supabase stack dựng bằng CLI (máy reviewer không có CLI; stack local dựng thủ công).
- Rehearsal tải thật/pilot.

## 7. Kết luận

**Đạt — trong phạm vi V1 local được giao** (Browser/Offline/Reopen 11 ca + response Owner trả trễ 2 ca + controls + provenance + manifest readonly), theo kiểm chứng độc lập của reviewer, không dùng log tác giả.

Kết luận này **không nghiệm thu toàn BH-07**, không đổi trạng thái các cổng NOT RUN ở mục 6, không thay thế chấp nhận rủi ro của chủ dự án, và không cho phép merge `main`, staging/production, deploy hoặc pilot. Bằng chứng cũ giữ nguyên; không sửa app/backend/script trong lượt này.
