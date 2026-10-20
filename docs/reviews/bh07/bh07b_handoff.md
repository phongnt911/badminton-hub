# BH-07B — bàn giao Chờ review (20/10/2026)

**Trạng thái: Chờ review BH-07B.** Người triển khai không tự ghi Đạt/Done và không chuyển C/D.

- Nhánh: `feat/bh07b-data`
- Base: `fd38838d85fed31603eae99ed363cf202650aeee` (commit công bố review BH-07A trên `origin/feat/bh07a-db`, sau `4512c3a`)
- Tested code SHA: `1c3acab2eb10f6914b466129a46ac9447e6c21c5`
- Worktree tại lúc chạy DB runner: sạch (`worktree_dirty=false`), trước khi ghi bằng chứng tài liệu
- Phạm vi: chỉ B — model/repository/provider. Không sửa migration/RPC của A, không làm UI C, không pilot D, không merge main, không apply staging/production.

## 1. Thay đổi

1. **Model typed**
   - `lib/models/finance.dart`: `SessionSummary` ánh xạ `get_session_summary`. Các trường tiền (`expenses_total_vnd`, `amount_due_total_vnd`, `total_paid_vnd`, `outstanding_total_vnd`) và billing/revision là nullable; `null` được giữ nguyên khi management-only, không đổi thành `0`. `0` thật của server vẫn là `0`.
   - `lib/models/session.dart`: `SessionHistoryFilter` (CLB/ngày) và `SessionHistoryPage` ánh xạ mảng JSONB của `list_my_session_history`, dùng lại `Session` đã review ở A.
2. **Repository đúng signature A**
   - `FinanceRepository.getSessionSummary(sessionId)` gọi `get_session_summary` với `p_session_id`.
   - `SessionRepository.listMySessionHistory(...)` gọi `list_my_session_history` với `p_limit`, `p_offset`, `p_club_id`, `p_from`, `p_to`; kẹp limit 1..100, offset >= 0, đổi ngày sang UTC ISO-8601. Không đọc bảng raw, không tự quyết định ACL.
3. **Provider**
   - `SessionProvider`: state lịch sử có `loading`/`loading-more`/`error`/`empty`/`hasMore`, filter CLB/ngày, refresh, `loadMoreHistory`, `refreshHistoryIfLoaded`. Đổi filter/CLB xoá trang cũ trước khi tải; lỗi cùng scope giữ trang cũ; response trễ bị bỏ bằng serial + generation. Logout/đổi actor gọi `clearAll` và xoá state.
   - `FinanceProvider`: state tổng kết có load/error/empty (`hasSummary`)/retry, đổi buổi xoá aggregate cũ, response trễ bị bỏ, logout/đổi actor xoá state. Mutation tiền/complete đang mở summary sẽ làm mới summary qua `_refreshSessionReads`; lỗi refresh không biến mutation thành thất bại.
   - Không suy `outstanding` từ `due - paid`, không cộng một trang payment bị cắt, không đổi tiền NULL thành 0.
4. **Complete/idempotency**
   - Giữ nguyên `completeSession` và cơ chế `_runMutation`/`request_id`/`expectedVersion` hiện có. Không sửa DB/RPC A.
   - Test xác nhận `VERSION_CONFLICT` trả `null` + lỗi domain, không báo thành công; retry cùng intent dùng lại UUID; chỉ sau thành công mới xoay UUID.

## 2. Kiểm thử mới

Đã thêm 19 test Flutter (190 → 209):

- Parse DTO `SessionSummary`/`SessionHistoryPage`, tiền NULL/0, billing state, session version.
- Lịch sử: pagination/offset, filter, empty/error/retry, refresh, đổi CLB, logout/đổi actor và response đến sai thứ tự.
- Tổng kết: load/error/retry, management-only giữ NULL, đổi buổi, logout/đổi actor, refresh sau mutation tiền đúng scope.
- Complete stale/version không thành công, retry giữ `request_id`, xoay key sau thành công.

## 3. Lệnh, exit, kết quả

Môi trường: Windows, Flutter 3.47.7 / Dart 3.13.5, PostgreSQL 17 trong Docker `bh02-test-postgres`, `BH02_TEST_CONTAINER=bh02-test-postgres`, Auth stub + `SET ROLE`. Không phải HTTP/PostgREST/JWT/Auth thật.

| Lệnh | Exit | Kết quả |
|---|---:|---|
| `flutter analyze --no-pub` | 0 | No issues found |
| `flutter test --no-pub` | 0 | **209/209 PASS** |
| `python docs\reviews\bh07\run_bh07_tests.py` | 0 | **23/23 PASS** (21 CLEAN + 2 upgrade) |
| `python docs\reviews\bh02\run_rls_tests.py` | 0 | **33/33 PASS** |
| `python docs\reviews\bh02\extended_tests_15ef59b.py` | 0 | **14/14 PASS** |
| `python docs\reviews\bh03\run_bh03_tests.py` | 0 | **48/48 PASS** |
| `python docs\reviews\bh03\run_bh03_retry_tests.py` | 0 | **22/22 PASS** |
| `python docs\reviews\bh04\run_bh04_tests.py` | 0 | **44/44 PASS** |
| `python docs\reviews\bh05\run_bh05_tests.py` | 0 | **90/90 PASS** |
| `python docs\reviews\bh06\run_bh06_tests.py` | 0 | **84/84 PASS** |
| `python docs\reviews\bh06\integration_evidence\run_integration_tests.py` | 0 | **7/7 PASS** |
| `python docs\reviews\bh06\integration_evidence\run_upgrade_tests.py` | 0 | **3/3 PASS** |

Tổng hồi quy DB BH-02..06 lần chạy này: **335/335** (33+14+48+22+44+90+84), cộng **7/7 tích hợp** và **3/3 nâng cấp BH-06**. BH-07 **23/23**. Đây là kết quả mới tại tested code `1c3acab`, không dùng kết quả lịch sử 190/335 của A thay cho lần chạy này.

## 4. Bằng chứng

Thư mục [bh07b_evidence](bh07b_evidence/):

- `flutter_analyze.log`, `flutter_test.log` (209/209).
- `bh07_final_run.log`, `bh07_test_results_20261020115007.json` (23/23, `base_sha=1c3acab`, `worktree_dirty=false`).
- `regression_bh02.log`, `regression_bh02_extended.log`, `regression_bh03.log`, `regression_bh03_retry.log`, `regression_bh04.log`, `regression_bh05.log`, `regression_bh06.log`.
- `regression_bh06_integration.log`, `regression_bh06_upgrade.log`.
- JSON kết quả regression tương ứng và `regression-exits.json`.
- `summary.json`: base/tested SHA, kết quả và NOT RUN.

## 5. Trọng tâm reviewer

1. `SessionSummary` không làm mất phân biệt `null` (không quyền) và `0` (server trả 0); không tự tính outstanding.
2. `list_my_session_history` gửi đúng parameter, offset sau trang hiện có, filter đổi thì xoá scope cũ; response trễ/khác actor không khôi phục state.
3. Provider không coi lỗi đọc là rỗng/0; retry phục hồi; logout/đổi actor/đổi buổi/CLB dọn đúng state.
4. Complete stale/version không báo thành công; retry cùng intent giữ `request_id`; không sửa gate DB/RPC A.
5. Không có UI C trong phạm vi này.

## 6. NOT RUN / giới hạn

- HTTP/PostgREST/JWT/Supabase Auth thật; repository qua HTTP thật; RLS qua token thật.
- UI C, màn hình lịch sử/tổng kết, copy/share, deep link, offline/reopen, thiết bị/browser.
- Ngân hàng/VietQR/webhook/chuyển tiền thật.
- Staging/production, apply DB, backup/restore rehearsal, concurrency qua HTTP.
- Pilot D và nghiệm thu toàn BH-07.

Các kết quả trên chỉ có hiệu lực trong Flutter test + PostgreSQL local + Auth stub. Mock repository không thay HTTP/JWT/Auth thật và không cho phép kết luận pilot hoặc deploy.
