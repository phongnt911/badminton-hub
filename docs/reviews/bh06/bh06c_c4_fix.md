# BH-06C — sửa C4 theo chỉ định của chủ dự án (LẦN 2)

> Reviewer 20/10/2026 kết luận **Đạt phần C tại `b31f988`**, đóng C4 theo [review và bằng chứng](review_b31f988.md). Đã chạy lại 84 DB và RPC C4 local thành công; các lệnh/NOT RUN/Chờ review bên dưới là lịch sử phía tác giả. Các cổng HTTP/thiết bị/ngân hàng thật và nghiệm thu tích hợp vẫn chưa chạy.

Ngày 20/10/2026. Nhánh `feat/bh06c-ui`, tiếp sau review [review_a0f7255](review_a0f7255.md) (commit review `0868287`). Reviewer đã đóng C1/C2/C3 và mở **C4 (P2)**; theo AGENTS reviewer dừng vòng tự động, nhưng chủ dự án giao tiếp **LẦN 2** nên người triển khai sửa C4. Không đổi migration/RPC của A, không viết lại B, không merge `main`.

## 1. Phát hiện C4

UI “Thêm chi phí” cho chọn **Nước** (`_expenseCategories['water']`) rồi gửi nguyên `category: 'water'` vào `post_session_expense`, trong khi RPC chỉ nhận `court`, `shuttle`, `other` (`supabase/migrations/20261016110000_bh06_expenses_finalize.sql:173`). Host nhập hợp lệ vẫn luôn nhận `INVALID_INPUT: Loại chi phí không hợp lệ`.

## 2. Test tái hiện trước (test-first)

Commit `bfbd8f6` — `test/screens/session_finance_screen_test.dart:643`:

- Đi qua dialog cho từng lựa chọn `Sân`, `Cầu`, `Nước`, `Khác`, ghi chi phí, thu payload repository.
- Kỳ vọng mọi `category` thuộc `{court, shuttle, other}`; riêng **Nước** gửi `other` và giữ nội dung.
- Trước khi sửa: **FAIL** tại `everyElement(isIn(accepted))` — `has value 'water' ... at index 2`; đồng thời `calls[2]['category']` là `water`.

## 3. Sửa

Commit `bd17a95` — `lib/screens/session_finance_screen.dart`:

- dòng 45: `_expenseRpcCategory` ánh xạ `water → other`, các loại khác giữ nguyên.
- dòng 236: payload `postExpense` dùng `_expenseRpcCategory(category)`.
- Giữ lựa chọn **Nước** cho host (đỡ phải tự gõ), nội dung chi phí vẫn do người nhập quyết định. Khoản đã ghi hiển thị theo category DB (`other` → “Khác”) kèm nội dung; đây là giới hạn schema hiện có, không mở migration.

## 4. Bằng chứng

Trên cây `bd17a95` (sạch):

- `flutter analyze` → **No issues found!** (0 issue)
- `flutter test` → **187/187 PASS** (186 trước + 1 test C4)
- Không đổi DB/migration → runner DB BH-06 **không chạy lại**.

## 5. Probe C4 của reviewer

Probe `review_a0f7255_evidence/expense_probe.py` gọi RPC thật với category do UI gửi. Sau sửa, UI gửi `other` cho lựa chọn Nước nên payload nằm trong contract; test widget của tác giả kiểm đúng điều này. **Không chạy lại probe RPC/Docker trong lượt này** (NOT RUN) — đề nghị reviewer chạy lại trên SHA mới.

## 6. NOT RUN

- Chạy lại probe RPC C4/Docker PostgreSQL và runner DB BH-06 (không đổi DB).
- HTTP/PostgREST/JWT/Auth thật; thiết bị/browser e2e; ảnh VietQR/bank thật; staging/production; backup/restore; concurrency HTTP.

## 7. Trạng thái

**Chờ review** (lượt sửa C4 theo chỉ định chủ dự án). Người triển khai không tự ghi Đạt; chưa chuyển tích hợp.
