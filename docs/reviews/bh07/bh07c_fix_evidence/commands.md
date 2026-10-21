# Lệnh và kết quả — BH-07C sửa vòng 1/2

Base: `9b978467316d66c458846ac68c5de8021401fa0c`
Tested code: `02a9b857724e9ba031323ad732c90355d7932a39`

## 1. Đỏ trước khi sửa production

Giữ nguyên test mới, tạm đưa ba file production về base để tái hiện lỗi:

```powershell
flutter test --no-pub test/screens/session_finance_screen_test.dart test/screens/session_history_screen_test.dart
# exit 1; 3 FAIL đúng phạm vi:
# - manager: thiếu sessionVersion DTO thì nút kết thúc bị khoá dù route có version
# - cache rỗng không che lỗi refresh; có retry
# - ngày lọc là ngày Việt Nam và gửi mốc UTC+7
```

Log: `red_targeted.log`; exit: `red_targeted_exit.txt`.

## 2. Xanh sau khi sửa

```powershell
flutter analyze --no-pub
# exit 0; No issues found!

flutter test --no-pub
# exit 0; +230 All tests passed!

$env:TZ='UTC'
flutter test --no-pub `
  test/core/session_summary_text_test.dart `
  test/core/time_utils_test.dart `
  test/screens/session_summary_screen_test.dart `
  test/screens/session_history_screen_test.dart `
  test/screens/session_finance_screen_test.dart `
  test/screens/session_detail_screen_test.dart `
  test/screens/sessions_screen_test.dart
# exit 0; +57 All tests passed!

$env:TZ='Asia/Ho_Chi_Minh'
flutter test --no-pub `
  test/core/session_summary_text_test.dart `
  test/core/time_utils_test.dart `
  test/screens/session_summary_screen_test.dart `
  test/screens/session_history_screen_test.dart `
  test/screens/session_finance_screen_test.dart `
  test/screens/session_detail_screen_test.dart `
  test/screens/sessions_screen_test.dart
# exit 0; +57 All tests passed!

python docs/reviews/bh07/run_bh07_tests.py
# exit 0; TỔNG 23 | PASS 23 | FAIL 0
```

Log tương ứng: `flutter_analyze.log`, `flutter_test.log`, `targeted_utc.log`,
`targeted_vietnam.log`, `bh07_db_runner.log`.
Kết quả DB: `bh07_test_results_20261021020900.json`.

## 3. Phạm vi thay đổi

Chỉ C1/C2/C3 và test C:

- `lib/screens/session_finance_screen.dart`: complete dùng `finance.sessionVersion`, thiếu DTO thì khoá nút và hướng dẫn tải lại.
- `lib/screens/session_history_screen.dart`: lỗi refresh hiện cả khi cache rỗng; ngày lọc là ngày lịch Việt Nam, đổi sang UTC+7 khi gọi provider.
- `lib/core/time_utils.dart`: helper mốc ngày Việt Nam.
- `test/core/time_utils_test.dart`, `test/screens/session_finance_screen_test.dart`,
  `test/screens/session_history_screen_test.dart`: test tái hiện/kiểm chứng.

Không đổi migration, RPC, model/repository/provider B, contract, `main`, staging
hoặc production.

## 4. NOT RUN

- HTTP/PostgREST/JWT/Supabase Auth thật.
- Thiết bị/browser thật, offline/reopen, deep link, QR ngân hàng/VietQR/webhook.
- Staging/production, backup/restore, concurrency qua HTTP.
- Pilot D và nghiệm thu toàn BH-07.
- Hồi quy DB BH-02..06 (335 case): không đổi DB/backend; giữ baseline B.
