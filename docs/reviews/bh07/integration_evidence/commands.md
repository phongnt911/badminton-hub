# Lệnh và kết quả — BH-07D tích hợp

Base D: `b0478a72021a726530c4051b52239a0a22d7fb96`
Tested code: `3d590a8418157cf91b00b9a5503d09be4df069f3`
Nhánh: `feat/bh07-integration`
Môi trường: xem `environment.txt`.

## 1. Baseline trước khi thêm D

Chạy trên base D `b0478a7`, worktree sạch:

```powershell
flutter analyze
# exit 0; No issues found!

flutter test
# exit 0; +230 All tests passed!

python docs/reviews/bh07/run_bh07_tests.py
# exit 0; TỔNG 23 | PASS 23 | FAIL 0
```

Log: `baseline_analyze.log`, `baseline_flutter_test.log`, `baseline_bh07_db_runner.log`
và các file `*_exit.txt` tương ứng.

## 2. Đỏ trước khi sửa lỗi tích hợp

Giữ nguyên test D tại tested code, tạm đưa riêng file UI về base để tái hiện:

```powershell
git checkout HEAD^ -- lib/screens/session_finance_screen.dart
flutter test test/integration/bh07_full_flow_test.dart --plain-name "sau complete"
# exit 1; FAIL đúng 1 ca:
# Expected: no matching candidates
# Actual: Found 1 widget with key <'bh06c-add-expense'>
# tại bh07_full_flow_test.dart:1162
git checkout HEAD -- lib/screens/session_finance_screen.dart
```

Kết luận: sau khi buổi `completed`, UI vẫn hiện `Thêm chi phí` dù
`post_session_expense` từ chối `completed/cancelled`. Đây là lỗi tích hợp sản phẩm,
không phải lỗi test.

Log: `d_red_post_complete_add_expense.log`; exit: `d_red_post_complete_add_expense_exit.txt`.

## 3. Xanh sau khi sửa tối thiểu

```powershell
flutter analyze
# exit 0; No issues found!

flutter test
# exit 0; +240 All tests passed! (230 baseline + 10 D)

$env:TZ='UTC'
flutter test test/integration/bh07_full_flow_test.dart
# exit 0; +10 All tests passed!

$env:TZ='Asia/Ho_Chi_Minh'
flutter test test/integration/bh07_full_flow_test.dart
# exit 0; +10 All tests passed!

$env:TZ='UTC'
flutter test `
  test/screens/session_finance_screen_test.dart `
  test/screens/session_history_screen_test.dart `
  test/screens/session_summary_screen_test.dart `
  test/screens/session_detail_screen_test.dart
# exit 0; +50 All tests passed!

$env:TZ='Asia/Ho_Chi_Minh'
flutter test `
  test/screens/session_finance_screen_test.dart `
  test/screens/session_history_screen_test.dart `
  test/screens/session_summary_screen_test.dart `
  test/screens/session_detail_screen_test.dart
# exit 0; +50 All tests passed!

python docs/reviews/bh07/run_bh07_tests.py
# exit 0; TỔNG 23 | PASS 23 | FAIL 0
# worktree_dirty=false; base_sha=3d590a8418157cf91b00b9a5503d09be4df069f3
```

Log tương ứng: `analyze.log`, `flutter_test_full.log`, `d_targeted_tz_utc.log`,
`d_targeted_tz_asia_hcm.log`, `c_regression_targeted_tz_utc.log`,
`c_regression_targeted_tz_asia_hcm.log`, `bh07_db_runner.log`, cùng các file
`*_exit.txt`. Kết quả DB đầy đủ: `bh07_db_results_3d590a8.json` (runner ghi tên
theo stamp `bh07_test_results_20261021045249.json`, đã đổi tên khi lưu evidence,
không sửa nội dung).

## 4. Phạm vi thay đổi

- `test/integration/bh07_full_flow_test.dart` (mới): 10 ca tích hợp D.
- `lib/screens/session_finance_screen.dart`: ẩn `bh06c-add-expense` khi lifecycle
  `completed`/`cancelled`; giữ chốt lại phí, thu tiền, xác nhận/từ chối thanh toán,
  thu tiền mặt và hoàn tác.

Không đổi migration, RPC, model/repository/provider, contract, dependency, `main`,
staging hoặc production.

## 5. NOT RUN

- HTTP/PostgREST/JWT/Supabase Auth thật.
- Thiết bị/browser thật, offline/reopen, deep link.
- Concurrency qua HTTP thật; ngân hàng/VietQR/webhook thật.
- Staging/production, backup/restore, rehearsal/pilot.
- Hồi quy DB BH-02..06 (335 case): không đổi DB/backend; giữ baseline B.
- Nghiệm thu toàn BH-07; người triển khai không tự ghi Đạt.
