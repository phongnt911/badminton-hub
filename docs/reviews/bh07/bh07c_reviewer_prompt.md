# Prompt reviewer BH-07C

Bạn là **reviewer độc lập** cho BH-07C. Không viết lại code triển khai, không sửa migration/RPC, không merge `main`, không deploy/apply staging/production.

## Phạm vi và SHA

- Nhánh: `feat/bh07c-ui`.
- Base: `cf95d76855acf1f394b1976ebab54087b4d7bba9`.
- **Tested code cần review: `15ae1af0d9d39678f4b9d99fabc9e9e22cb860ba`** (`feat: add BH-07C history summary and complete UI`).
- Docs/evidence BH-07C: `65ce0f45fe9782184717ac52ba09a992e960d920`; các commit docs sau đó chỉ chứa prompt/quy trình, không chứa code C.
- Chỉ review phần C (UI). A giữ Đạt tại `4512c3a`; B giữ Đạt tại `d7bac04`, tested code `a682007`.

Đọc trước:

1. `AGENTS.md`, `docs/04_LLM_RULES.md`, `docs/ai/REVIEWER.md`.
2. `docs/09_IMPLEMENTATION_PLAN.md`, `docs/25_BH07_IMPLEMENTATION_HANDOFF.md`, `docs/10_SCREEN_FLOWS.md`.
3. `docs/reviews/bh07/bh07c_handoff.md`.
4. Log/evidence trong `docs/reviews/bh07/bh07c_evidence/`.

## Việc phải kiểm

### 1. Kết thúc buổi

- Nút complete chỉ hiện/bật khi:
  - actor `canManage`;
  - buổi `in_progress`;
  - phí `canCollect`/current;
  - có `sessionVersion` lấy từ DTO tài chính (không lấy cảm tính từ `Session` route nếu DTO có version).
- Có xác nhận trước khi gọi `complete_session`.
- Lỗi/domain error/version conflict không pop route, không báo thành công; nút bị khoá khi submitting.
- Thành công trả kết quả về chi tiết, chi tiết tải lại session và refresh lịch sử nếu đang mở; không tạo duplicate hoặc tự tính công nợ.
- Không thay đổi hành vi start hiện có.

### 2. Summary và copy

- Chỉ dùng aggregate server từ `get_session_summary`; không tự tính `outstanding` từ `due - paid`.
- `canViewFinance = false`: không hiện, không copy phần tiền; chỉ số lượng.
- `canViewFinance = true`: hiện/copy đúng các trường aggregate; trường `null` giữ `—`, không đổi thành `0`.
- Copy không chứa tên/điện thoại người chơi, receiver/bank/account number hoặc dữ liệu ngoài scope.
- Không hiển thị summary cũ của buổi khác; xử lý `FORBIDDEN`/transport error đúng, có retry.
- Lối vào summary chỉ cho `canManage || canViewFinance`.

### 3. Lịch sử

- Filter CLB/khoảng ngày gửi đúng contract B; không lọc lại client làm sai phân trang.
- Loading, empty, error/retry, refresh, tải thêm và offset thô đúng; không trùng ID khi trang chồng lấn.
- Mở chi tiết rồi quay lại refresh hợp lý; guest/auth state không gọi dữ liệu sai quyền.
- Lỗi tải CLB không làm mất khả năng lọc ngày hoặc hiển thị lịch sử.

### 4. Test và bằng chứng

- Tự chạy lại `flutter analyze`, `flutter test`, runner BH-07 ở môi trường phù hợp; không chỉ đọc log tác giả.
- Đối chiếu **225/225 Flutter**, **23/23 BH-07 DB**, targeted C 52/52; kiểm log/JSON có khớp code tại tested SHA.
- Xác nhận C không sửa migration/RPC A, model/repository/provider B hoặc contract; 335 DB hồi quy không chạy lại là chấp nhận được nếu không đổi DB/backend.
- Kiểm test không chỉ kiểm cấu trúc: có ca quyền, null, copy, complete success/error/version, history pagination/error.

## Đầu ra

- Ghi báo cáo tại `docs/reviews/bh07/review_15ae1af.md`.
- Mỗi phát hiện ghi `file:dòng`, mức **P0/P1/P2**, mô tả và cách sửa.
- Cuối báo cáo ghi **Đạt** hoặc **Chưa đạt** + NOT RUN.
- Nếu Chưa đạt: chỉ rõ phạm vi sửa, test tái hiện cần có; tuân thủ tối đa 2 vòng sửa theo AGENTS.
- Cập nhật trạng thái BH-07C trong docs/09 theo kết luận; không tự merge main, chuyển D hoặc deploy.
- Không viết lại code, không apply DB, không dùng production thay môi trường test.
