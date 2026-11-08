# Review BH-07 Windows UTF-8 test helpers — 51a6eda

2026-11-08. Base `e994b06a1752e6301d8733aa084d675fde7a877c`; reviewed code `51a6edaccfdc4e0381511d499996fc2445e1ece8`, branch `feat/bh07-completion-local`.

## P0/P1/P2

Không có phát hiện P0/P1/P2 trong phạm vi hai helper kiểm thử. Diff chỉ thêm `encoding='utf-8'` cho stdout/stderr Node; không đổi assertion, xử lý lỗi, dữ liệu kỳ vọng hay code app/backend.

## Kiểm chứng độc lập

Antigravity CLI (Gemini 3.8 Flash High, conversation `080a8fcc-c7cc-4879-b7c3-9fda9c7297dd`) sửa code. Codex chạy các lệnh bên dưới; một Code Reviewer riêng kiểm tra diff/caller và không có phát hiện, không sửa file hay chạy lại suite. Anti không chạy lệnh vì quyền command của headless bị từ chối; không gán kiểm chứng của Codex thành tự kiểm của Anti.

| Lần kiểm | Kết quả thật | Archive lean-ctx |
|---|---|---|
| Trước sửa: `python -m unittest discover -s tests`, Windows mặc định | 375 tests; 1 failure, 3 errors, exit 1; mojibake và lỗi decode CP1252 | `33216b2726738ee1` |
| Control, source chưa sửa: cùng lệnh với `PYTHONUTF8=1` | 375 tests PASS, exit 0 | `dca1d55ca819597d` |
| Sau sửa: `python -m unittest tests.test_bh07_app_heap_build_guard tests.test_bh07_bank_navigation_cleanup -v` | 20 tests PASS, exit 0, không override encoding môi trường | `48ecc6e242175a0c` |
| Sau sửa: `python -m unittest discover -s tests` | 375 tests PASS, exit 0, không override encoding môi trường | `1471e2836a9dbef4` |
| `flutter analyze` trong lượt này | 0 issues, exit 0 | `ebe7ea3338942102` |
| `flutter test --reporter compact` trong lượt này | 247 PASS + 1 SKIP, exit 0 | `cca2f894441a6acd` |

Các kiểm thử sau sửa chạy trên working tree sau đó được commit nguyên diff hai file thành `51a6eda`; không tuyên bố đây là lần chạy từ Git checkout sạch. Flutter chạy trước thay đổi Python; source app/Dart không đổi, không chạy lại để tăng count. `git diff --cached --check` sạch trước commit.

[Metadata kiểm chứng](review_51a6eda_evidence/results.json). Archive là tham chiếu log local của phiên công cụ, không phải bundle runtime có manifest mới.

## NOT RUN và ranh giới

Không có phép đo heap/browser/DB mới trong bản sửa này; không retag runtime bank/receiver `a095a45` thành runtime `51a6eda`. Không thay đổi, làm mới hoặc phê duyệt lại gói main tooling v4. Không có merge, push, deploy hoặc pilot. Người dùng xác nhận chưa có staging hay thiết bị Android/iOS test; các cổng tương ứng vẫn NOT RUN.

**Đạt trong phạm vi sửa encoding của hai helper kiểm thử Windows. Toàn BH-07/V8 chưa nghiệm thu.**
