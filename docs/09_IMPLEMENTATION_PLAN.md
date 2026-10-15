# Backlog triển khai và nghiệm thu

Trạng thái khởi đầu: mọi ticket dưới đây **chưa triển khai theo đặc tả v1.1**. Code demo có sẵn được tận dụng sau khi đối chiếu. Mỗi ticket cần commit riêng hoặc nhóm thay đổi có liên quan; không triển khai toàn bộ app trong một prompt.

## Thứ tự và phụ thuộc

BH-01 → BH-02 → BH-03 → BH-04 → BH-05 → BH-06 → BH-07. BH-08/BH-09 sau pilot. BH-02 dựng nền schema/RLS và các kiểm tra quyền; RPC chi tiết hoàn thiện theo từng ticket, không gọi function chưa tồn tại từ UI.

| Ticket | Phạm vi | Đầu ra / nghiệm thu |
|---|---|---|
| BH-01 | Auth và cấu hình | Email login/signup/reset/logout, callback đúng môi trường; auth provider/repository, route return; analyze + test auth state/guard; public read vẫn mở được; không nối test production |
| BH-02 | Schema nền, migrations và quyền | Từ điển 03_DATABASE được ánh xạ thành migration versioned, RLS/projection/helpers/idempotency/audit; dựng DB local/staging từ đầu; A không đọc/sửa B; anonymous không ghi; không chạy legacy SQL |
| BH-03 | CLB/thành viên/ngân hàng | Tạo club+owner atomic, member không account, role/contact private, config receiver; owner cấp quyền nhưng member không tự nâng quyền; dữ liệu cũ cần ownership reconciliation |
| BH-04 | Buổi/lịch/chia sẻ | Create/edit/duplicate/publish; ngày tương lai, qua nửa đêm, version conflict; link mở đúng ID trước/sau login; duplicate không sao chép người/tiền; phân trang/empty/error |
| BH-05 | Đăng ký/duyệt/hủy/điểm danh | DB RPC và UI; slot cuối 2 người tối đa 1 confirmed; retry không trùng; member cố định vẫn đăng ký từng buổi; guest host-added; contact không lộ; cancel deadline và capacity bảo vệ |
| BH-06 | Phí/thu tiền/quỹ | Expenses/revision/charges/payment/ledger atomic; QR thật, cash/transfer manual confirmation; phân dư chính xác, n=0 lỗi đúng; thu nhiều lần không dư; refinalize/đảo không trùng; quyền finance |
| BH-07 | Buổi hoàn chỉnh và pilot | start/complete/lịch sử, công nợ còn sau complete; sao chép tổng kết; test end-to-end trên mobile/web, mất mạng, mở lại app; tài liệu vận hành/migration/backup có kết quả rehearsal |
| BH-08 | Xoay tua và trận | Từ present, gợi ý → bắt đầu → kết thúc; nhiều sân không trùng người; số trận tăng sau finish; lưu server, override host; test thuật toán thực |
| BH-09 | Kèo giao lưu | Gắn match và participant IDs, vật phẩm/số lượng tự nguyện, kết quả versioned/hoàn tác; không trộn quỹ; tách bảng điểm phong trào và quy tắc giải chính thức |

## Checklist mỗi ticket

1. Đọc yêu cầu/contract, xem code và schema có thật, nêu phạm vi/file cần sửa.
2. Viết code/migration hoàn chỉnh và tests kiểm chứng hành vi có rủi ro.
3. Chạy flutter analyze/tests liên quan; nếu đổi DB, DB quyền/RPC/transaction tests tại local/staging.
4. Thử các trạng thái loading/error/empty/submitting và dữ liệu của user khác.
5. Ghi kết quả/lệnh/giới hạn, cập nhật trạng thái trong phần nhật ký dưới đây.
6. Commit/push khi được yêu cầu; tách deploy production khỏi việc có migration trong repo.

## Ca nghiệm thu xuyên suốt

- Host A tạo CLB, thêm 5 thành viên từ Zalo và tạo buổi tuần sau, 2 sân/12 người. Host chỉ chiếm slot khi tự đăng ký.
- Người chơi B mở link không login, thấy thông tin đúng; login rồi gửi yêu cầu; host duyệt. B không thấy phone của C và không sửa buổi/quỹ.
- Host thêm khách từ Zalo; một người hủy trước hạn; hai người tranh slot cuối; DB vẫn đúng capacity, không phantom slot.
- Host start, điểm danh present/no_show, ghi sân 300.000đ + cầu 150.000đ. Chia cho 7 người chịu phí ra tổng đúng 450.000đ; người miễn phí được ghi 0.
- Người chơi gửi chuyển khoản chưa thành confirmed; finance xác nhận, thu phần còn lại bằng cash; outstanding về 0; không tạo income kép khi retry.
- Host kết thúc dù còn một người nợ; lịch sử vẫn hiển thị outstanding. Đổi tab/khởi động lại không mất dữ liệu.
- Chủ CLB đọc quỹ: expenses/payments xuất hiện đúng một lần. Cohost thiếu finance không chỉnh tiền. Người ngoài không đọc ledger qua API.

## Cổng trước pilot

Không còn policy public write trên bảng nghiệp vụ; các ca đồng thời/permission/tiền đạt; callback/link đúng; account receiver được host kiểm tra; backup/restore staging đã thử; dữ liệu legacy chưa xác minh được cách ly; không có secret trong repo; các lỗi đọc/ghi có retry rõ.

## Nhật ký

| Ngày | Ticket | Trạng thái | Bằng chứng |
|---|---|---|---|
| 14/10/2026 | Bộ đặc tả v1.1 | Đã soạn tài liệu | 00/01/02/03/04/08/09/10; chưa triển khai app/DB |
| 14/10/2026 | BH-01 | Đã hoàn thành (Done) | AuthRepository, AuthProvider, AuthScreen, AccountScreen, AuthGuard, AppConfig; 28 tests passed (unit + widget); flutter analyze clean 0 issues; scripts/supabase_client.dart kết nối trực tiếp thành công. Giới hạn: Deep link scheme trên thiết bị di động thật và migration DB mới (thuộc BH-02) chưa kiểm chứng trên production. |
| 15/10/2026 | BH-02 | Hoàn thành file migration & schema unit test (Live DB tests: NOT RUN) | File migration `20261015051808_init_schema_v1_1.sql` (21 bảng, RLS, projections, idempotency, audit trail, compatibility cho 3 bảng legacy). 9/9 schema unit tests passed trong `test/schema/schema_v1_1_migration_test.dart`; toàn bộ 37 flutter tests passed; analyze 0 issues. Kiểm thử RLS trực tiếp trên DB live/staging: NOT RUN (Nguyên nhân: Môi trường Windows chưa có Docker để chạy `supabase start`, không có Postgres local, và không được phép tự ý apply migration lên production). |

AI chỉ ghi ticket done sau khi đạt nghiệm thu hoặc ghi rõ ngoại lệ đã được chủ dự án chấp nhận. Không xóa nhật ký để giả tiến độ.

## Xử lý phát hiện review P1/P2

Snapshot 14/10/2026, code c8e5428 trước cập nhật tài liệu: public DB có venues/sessions/session_players, không thấy clubs/quỹ; grants anon/authenticated SELECT/INSERT/UPDATE nhưng RLS chỉ có SELECT/INSERT cho sessions/players. Contacts và flags nằm trong bảng player. Chưa có trigger/check/unique registration được liệt kê. Không lấy số rows ước tính để khẳng định DB trống; chưa thử writes hoặc test quyền HTTP bằng dữ liệu thật.

| Review | Ưu tiên | Ticket / cổng nghiệm thu | Trạng thái |
|---|---|---|---|
| R1 public contact/direct inserts | P1 | BH-02: anon không đọc contacts/flags, không insert nghiệp vụ; A không đọc/sửa B; grants+RLS+RPC+projection tests | Migration v1.1 & schema tests hoàn thành; chờ apply staging/live khi có môi trường |
| R2 insert player rồi update count bị policy chặn/không atomic | P1 | BH-05: RPC một transaction, 2 request slot cuối, retry/rollback, count khớp; không mở public UPDATE | Đã đặc tả, chưa sửa code/DB |
| R3 code gọi clubs/quỹ chưa có | P1 | BH-02/03: migration staging tạo đủ nền; schema error khác empty; CRUD club+owner có test | Đã đặc tả, chưa sửa code/DB |
| R4 charges lỗi thời | P1 | BH-06: billing version/source version và gate server QR/thu mới/complete; free cũng revision current; paid/history giữ nguyên | Đã sửa khoảng trống đặc tả, chưa triển khai |
| R5 form bỏ qua giờ nhập/ngày tương lai | P2 | BH-04: ngày mai/giờ thực/qua nửa đêm/validation | Đã đặc tả, chưa sửa code |
| R6 lỗi loading/update/QR mẫu | P2 | BH-04/05/06: lỗi/retry/route mounted, mutation trả ID/state, role đúng, QR thật | Đã đặc tả, chưa sửa code |
| R7 lời mời waitlist thiếu contract | P2 | BH-05: issue/revoke/accept, đúng người/expiry/capacity/consent guest, test retry | Đã bổ sung schema/contract, chưa triển khai |

### Ca mới bắt buộc

- Chốt split 450.000đ, thêm 70.000đ expense: billing stale; không phát QR/thu mới/complete, chốt lại đúng tổng 520.000đ rồi mới tiếp tục. Đổi attendance/roster/exemption có cùng gate.
- Retry cùng request_id của payment đã committed sau khi billing stale: trả kết quả trước đó với quyền hợp lệ, không ghi income lần hai.
- Free session phải có revision current/charges 0; sửa input sau đó không được bỏ qua gate bằng nút miễn phí.
- Waitlisted chưa được mời, lời mời sai người/hết hạn/thu hồi: không accept. Khi đầy, accept không vượt capacity; retry accepted không thêm slot. Guest host_recorded có consent/audit.
- Cấu hình lỗi hoặc tables/functions thiếu: UI error+retry, không fake dữ liệu/success và không mở quyền.

Đầu vào trực tiếp cho Antigravity ở [12_ANTIGRAVITY_PROMPTS.md](12_ANTIGRAVITY_PROMPTS.md). ADR chuẩn ở [11_ARCHITECTURE_DECISIONS.md](11_ARCHITECTURE_DECISIONS.md). Trạng thái review chỉ đóng khi test implementation đạt; sửa tài liệu không đóng lỗi live.

| Ngày | Ticket | Trạng thái | Bằng chứng |
|---|---|---|---|
| 14/10/2026 | Đặc tả v1.1 sau review | Đã cập nhật tài liệu | P1/P2 → contract/tests; ADR-01..09; prompt AG-00..07; chưa thay app/DB |
