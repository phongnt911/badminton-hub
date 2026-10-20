# BH-06C — sửa theo review vòng 1 (C1/C2)

Ngày 20/10/2026 (Việt Nam). Nhánh `feat/bh06c-ui`. Review nguồn: [review_af31e7b.md](review_af31e7b.md) tại commit review `7c23bbb` (tested `af31e7b`); dependency B `f28fd0f` (Đạt `5e62007`); main `c35dd27`. Đây là **vòng sửa 1** (tối đa 2 vòng theo [docs/ai/IMPLEMENTER.md](../ai/IMPLEMENTER.md)).

Phạm vi: chỉ hai phát hiện **P1 (C1, C2)** được nêu. Không sửa C3 (P2 — chưa có chỉ định của chủ dự án), không đổi migration/RPC/RLS của A, không viết lại model/repository/provider của B, không merge `main`, không deploy, không thêm dependency.

## C1 — gửi auth user ID thay vì ID đăng ký (P1)

- Nguyên nhân: nút gửi lấy `AuthProvider.currentUser.id` làm `playerId`, trong khi `submit_payment` tra `session_players.id` rồi mới so `user_id` với actor (`supabase/migrations/20261016120000_bh06_payments_ledger.sql:44–53`). Hai ID độc lập nên người chơi thật nhận NOT_FOUND.
- Sửa (`lib/screens/session_finance_screen.dart`): dùng `PaymentInstructions.playerId` (bản hướng dẫn đúng người/buổi) làm `playerId`; khoá nút gửi khi `playerId` rỗng kèm thông báo; bỏ hẳn phụ thuộc `AuthProvider` khỏi màn tài chính (UI không cần đọc auth).
- Test hồi quy: `C1: thiếu registration ID thì không bật nút gửi`; và ca người chơi có auth `u1` nhưng registration `registration-p1` — verify repository nhận `playerId: registration-p1`.

## C2 — mã QR cố định chặn gửi thanh toán mới sau từ chối (P1)

- Nguyên nhân: UI truyền `instructions.reference` (mã cố định theo đăng ký, `20261016140000_bh06a_review_round1.sql:88`) vào `p_reference`; `payments.reference` là UNIQUE và RPC không tái dùng reference của bản bị rejected → lần gửi mới lỗi `INVALID_INPUT: Mã tham chiếu đã tồn tại`.
- Sửa: tách **mã nội dung chuyển khoản** (vẫn là `description` của VietQR và dòng “Nội dung” để người chơi ghi vào ngân hàng) khỏi **định danh payment**; không truyền `p_reference` để RPC tự sinh `PAY-<uuid>` cho từng intent (`..._bh06_payments_ledger.sql:83`). Request ID vẫn ổn định cho retry cùng intent và xoay sau thành công (đã có ở B).
- Không bỏ ràng buộc UNIQUE, không đổi key mỗi retry để né lỗi.
- Test hồi quy: ca người chơi verify `reference: null` và vẫn thấy mã nội dung `BH06 S1 U1` trên QR; ca `C2: gửi lại sau từ chối dùng request ID mới và reference RPC sinh` (hai intent liên tiếp, request ID khác nhau, đều `reference: null`).

## Commit

- `498d4d8` — thêm test tái hiện (3 ca FAIL) + cập nhật ca người chơi sang contract đúng.
- `8e3cd83` — sửa code (analyze sạch, test xanh).

## Bằng chứng

- Trước sửa (`498d4d8`): `flutter test test/screens/session_finance_screen_test.dart` → **3 FAIL** (`C1: thiếu registration ID...`, `C2: gửi lại sau từ chối...`, `người chơi: ... gửi đúng registration ID...`).
- Sau sửa (`8e3cd83`): `flutter analyze` → **0 issue**; `flutter test` → **183/183 PASS** (= 181 trước + 2 ca mới; 1 ca cũ được cập nhật contract).
- Không đổi DB/migration nên runner DB BH-06 **không chạy lại** ở lượt này.

### Phát lại probe độc lập của reviewer

- Probe C1 (`review_af31e7b_evidence/widget_probe.dart.txt`, ca `review distinct auth and registration IDs`): chạy **nguyên văn** nay FAIL **chỉ** tại matcher `reference: 'BH06 S1 U1'` — vì probe được viết trước khi C2 đổi contract nên stub/verify của nó còn mã cố định. Log lời gọi cho thấy phần kỳ vọng C1 đã đạt: `submitPayment(playerId: registration-p1, reference: null)`. Chạy lại với **đúng một chỗ đổi** (`reference` trong stub/verify thành `null`, giữ nguyên phần còn lại): **PASS**.
- Probe C3 (`review pagination`): vẫn **FAIL** như dự kiến (`Còn phải thu: 100,000 VNĐ` thay vì `0`) — P2 chưa sửa.

## Chưa sửa

- **C3 (P2):** chưa có chỉ định của chủ dự án nên giữ nguyên; đây là phép tính khoản nợ theo người từ một trang payment phân trang (C3 thuộc P2, ngoài phạm vi bắt buộc của vòng sửa này). Nếu chủ dự án giao, hướng xử lý đã nêu trong review (lấy từ nguồn tổng hợp phía server hoặc chỉ hiển thị/prefill khi đã có dữ liệu đầy đủ).

## NOT RUN

HTTP/PostgREST/JWT/Supabase Auth thật; thiết bị/browser e2e; tải ảnh VietQR và chuyển khoản/ngân hàng thật; apply staging/production, backup/restore; concurrency qua HTTP; ca trả thêm sau refinalize của C2 (chỉ mô phỏng ở mức UI/provider, chưa chạy RPC local).

Bằng chứng trên là phía tác giả; reviewer cần tự chạy lại trên đúng SHA. Người triển khai ghi **Chờ review vòng 2**, không tự ghi Đạt.
