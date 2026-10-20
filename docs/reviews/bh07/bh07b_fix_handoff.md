# BH-07B — bàn giao sửa review vòng 1/2 (20/10/2026)

> **Kết luận hiện hành reviewer 20/10/2026: Đạt B local tại `d7bac04`**, tested code `a682007`, đóng B1/B2 vòng 1/2. [Review/bằng chứng](review_d7bac04.md). Nội dung bàn giao và kết luận cũ bên dưới giữ làm lịch sử; không tự chuyển C/D, merge main hoặc deploy.


**Trạng thái: Chờ review BH-07B vòng 1.** Người triển khai không tự ghi Đạt/Done, không chuyển C/D, không merge main hoặc deploy.

- Nhánh: `feat/bh07b-data`
- Review công bố: `135ff2316c8ee9b83bd9797b3257136256aea7ce` (`review_1298490.md`)
- Base A: `fd38838d85fed31603eae99ed363cf202650aeee`
- Tested code vòng 0: `89e1d8f5d2b8658a36b32ef80f3c77b82d798f80`
- **Tested code vòng 1: `a682007f6cd85931b410ec2930fd40cdd3fc73f4`**
- Worktree lúc chạy DB runner: sạch (`worktree_dirty=false`), trước khi ghi bằng chứng tài liệu.
- Không sửa migration/RPC A; không làm UI C/D.

## 1. B1 — FORBIDDEN không được giữ summary/quyền finance cũ

Đã sửa `FinanceProvider.fetchSessionSummary`:

- Lỗi transport tạm thời cùng scope: giữ aggregate cũ kèm `summaryErrorMessage`, không đổi tiền thành 0.
- Server trả `FORBIDDEN`: đặt `_sessionSummary = null` (nên `hasSummary=false`) và giữ `summarySessionId` để C có thể retry; giữ lỗi domain rõ ràng, không coi là empty thành công.
- Thêm `domainErrorCode` trong `lib/core/domain_error.dart` để phân biệt mã domain với lỗi transport; `domainErrorMessage` dùng chung helper.
- Không suy hay ghi đè tiền; response trễ/đổi actor vẫn bị serial/generation chặn.

Test tái hiện nằm trong `test/providers/finance_provider_test.dart` (trước sửa FAIL ở kỳ vọng `sessionSummary == null`; sau sửa PASS), gồm cả control transport giữ cache.

## 2. B2 — trang lịch sử chồng lấn không được nhân đôi

Đã sửa `SessionProvider`:

- Thêm `_historyRawOffset` theo số dòng thô server đã tiêu thụ, không theo số ID sau dedupe.
- Khi ghép trang, dedupe theo `Session.id`, giữ thứ tự cũ trước rồi mới thêm ID mới.
- Trang đầu và trang nối đều dedupe; `_historyHasMore` và `SessionHistoryPage.hasMoreOverride` giữ kết luận của trang thô để không kết thúc phân trang sai khi dedupe làm ngắn danh sách.
- Filter/actor/serial/loading và response trễ giữ nguyên hành vi cũ.
- Test mới dùng ba offset `[0,2,4]`, dữ liệu `[D,C] → [C,B] → [A]`, kỳ vọng `[D,C,B,A]` và offset vẫn `[0,2,4]`. Trước sửa FAIL do `[D,C,C,B,A]`; sau sửa PASS.

## 3. Kiểm thử mới

- Test-first: `docs/reviews/bh07/bh07b_fix_evidence/prefix.log` — exit 1, 2 FAIL đúng B1/B2 (`summary...FORBIDDEN...`, `history...dedupe...`).
- Targeted sau sửa: `postfix_targeted.log` — **58/58 PASS**, exit 0.
- Phát lại probe reviewer: `reviewer_probe_replay.log` — **6/6 PASS**, exit 0. Chỉ đổi đường dẫn fixture trong bản sao probe sang `docs/reviews/bh07/review_1298490_evidence/rpc-fixture.json`; không đổi kỳ vọng.
- Control transport error/response trễ/complete `VERSION_CONFLICT`/`BILLING_STALE`/request ID vẫn PASS trong probe và suite.

## 4. Lệnh, exit, kết quả tại `a682007`

Môi trường: Windows, Flutter 3.47.6 / Dart 3.13.5, PostgreSQL 17 trong Docker `bh02-test-postgres`, `BH02_TEST_CONTAINER=bh02-test-postgres`, Auth stub + `SET ROLE`.

| Lệnh | Exit | Kết quả |
|---|---:|---|
| `flutter analyze --no-pub` | 0 | No issues found |
| `flutter test --no-pub` | 0 | **212/212 PASS** |
| `python docs\\reviews\\bh07\\run_bh07_tests.py` | 0 | **23/23 PASS** (21 CLEAN + 2 upgrade) |
| `python docs\\reviews\\bh02\\run_rls_tests.py` | 0 | **33/33 PASS** |
| `python docs\\reviews\\bh02\\extended_tests_15ef59b.py` | 0 | **14/14 PASS** |
| `python docs\\reviews\\bh03\\run_bh03_tests.py` | 0 | **48/48 PASS** |
| `python docs\\reviews\\bh03\\run_bh03_retry_tests.py` | 0 | **22/22 PASS** |
| `python docs\\reviews\\bh04\\run_bh04_tests.py` | 0 | **44/44 PASS** |
| `python docs\\reviews\\bh05\\run_bh05_tests.py` | 0 | **90/90 PASS** |
| `python docs\\reviews\\bh06\\run_bh06_tests.py` | 0 | **84/84 PASS** |
| `python docs\\reviews\\bh06\\integration_evidence\\run_integration_tests.py` | 0 | **7/7 PASS** |
| `python docs\\reviews\\bh06\\integration_evidence\\run_upgrade_tests.py` | 0 | **3/3 PASS** |

Tổng hồi quy DB BH-02..06 lần chạy này: **335/335**, cộng **7/7 tích hợp** và **3/3 nâng cấp BH-06**. BH-07 JSON ghi `base_sha=a682007f...`, `worktree_dirty=false`.

## 5. Bằng chứng

Thư mục [bh07b_fix_evidence](bh07b_fix_evidence/):

- `prefix.log` — FAIL trước sửa.
- `postfix_targeted.log` — targeted PASS sau sửa.
- `reviewer_probe_replay.log`, `provider_probe_replay.dart.txt` — phát lại probe reviewer.
- `flutter_analyze.log`, `flutter_test.log` — analyze + 212 Flutter.
- `bh07_final_run.log`, `bh07_test_results_20261020143256.json` — BH-07 23/23.
- `regression_bh02*.log`, `regression_bh03*.log`, `regression_bh04.log`, `regression_bh05.log`, `regression_bh06*.log` — hồi quy.
- JSON regression tương ứng, `regression-exits.json`, `summary.json`.

## 6. NOT RUN / giới hạn

- HTTP/PostgREST/JWT/Supabase Auth thật; repository qua HTTP thật/RLS qua token thật.
- UI C, màn hình lịch sử/tổng kết/copy, thiết bị/browser/deep link/offline/reopen.
- Ngân hàng/VietQR/webhook/chuyển tiền thật.
- Staging/production, apply DB, backup/restore rehearsal, concurrency HTTP.
- Pilot D và nghiệm thu toàn BH-07.

Các kết quả trên chỉ có hiệu lực trong Flutter test + PostgreSQL local + Auth stub. Mock repository/probe không thay HTTP/JWT/Auth thật và không cho phép kết luận pilot hoặc deploy.
