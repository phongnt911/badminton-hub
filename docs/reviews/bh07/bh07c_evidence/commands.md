# Lệnh đã chạy

```powershell
flutter analyze
# exit 0, No issues found!

flutter test
# exit 0, +225 All tests passed

flutter test test/core/session_summary_text_test.dart test/screens/session_summary_screen_test.dart test/screens/session_history_screen_test.dart test/screens/session_finance_screen_test.dart test/screens/session_detail_screen_test.dart test/screens/sessions_screen_test.dart
# exit 0, +52 All tests passed

python docs\reviews\bh07\run_bh07_tests.py
# exit 0, TỔNG 23 | PASS 23 | FAIL 0
```

Log tương ứng nằm cùng thư mục. `flutter_test.log` và `flutter_analyze.log` được chạy lại sau khi hoàn tất code C, trước commit code. DB runner chạy lại sau commit code trên cùng migration.
