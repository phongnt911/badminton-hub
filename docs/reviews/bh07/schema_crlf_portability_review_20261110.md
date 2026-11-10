# Schema test CRLF portability — 10/11/2026

**Đạt trong phạm vi test-loader một dòng; không phải sửa app/migration/runtime.** Base HEAD `cd4bcbf`; candidate thay duy nhất `readAsStringSync()` thành `readAsStringSync().replaceAll('\r\n', '\n')` trong `test/schema/schema_v1_1_migration_test.dart`. Anti triển khai sau Codex xác định nguyên nhân; reviewer độc lập review source/log, không chạy lại Flutter.

Root fresh Windows full suite ban đầu245PASS+1SKIP+2FAIL; targeted schema9PASS+2FAIL. Failures tại hai assertion multiline LF-only đối với security_barrier views, file SQL có1316CRLF/0bareLF. Các chuỗi assertion đã có đủ sau chuẩn hóa CRLF→LF; migration không thiếu clause.

Sau sửa:

- Targeted schema11/11PASS: `.build/schema-crlf-green-r1.log`.
- Cùng11assertion đầy đủ phát lại trên bản sao SQL LF và CRLF:22/22PASS, `.build/schema-portability-controls.log`. Bản sao ở `.build/schema-portability`; chỉ đường dẫn fixture trong bản sao test thay đổi.
- Full Flutter247PASS+1SKIP, exit0: `.build/web-matrix-flutter-green-r1.log`.

Reviewer không phát hiện P0/P1/P2 hay assertion security bị nới lỏng. SQL trên đĩa không sửa; việc chuẩn hóa chỉ ở chuỗi test vừa đọc. Không nhận suite cũ là lần chạy mới; các log trên thuộc lượt kiểm chứng máy hiện tại.

Đây không đóng V2 đa browser/device hoặc V2b heap. Kịch bản browser matrix đang sửa riêng, không suy kết quả của nó từ bộ Flutter test này. Toàn BH-07/V8 chưa nghiệm thu.
