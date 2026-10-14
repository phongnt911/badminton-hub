# Badminton Hub — điểm bắt đầu cho Antigravity

Phiên bản đặc tả: 1.0 · 14/10/2026 · trạng thái: đặc tả đích để triển khai.

## Mục tiêu

Xây công cụ cho host quản lý CLB và buổi cầu lông tại Nha Trang. Người chơi tham gia qua link host chia sẻ. Hoàn thiện một buổi chơi từ đăng ký đến thu tiền trước khi mở rộng khám phá cộng đồng.

## Thứ tự đọc

1. [Quy tắc làm việc](04_LLM_RULES.md).
2. [Yêu cầu sản phẩm](01_PRD_SPEC.md).
3. [Kiến trúc](02_ARCHITECTURE.md).
4. [Cơ sở dữ liệu và phân quyền](03_DATABASE.md).
5. [Hợp đồng thao tác nghiệp vụ](08_DOMAIN_CONTRACTS.md).
6. [Backlog và nghiệm thu](09_IMPLEMENTATION_PLAN.md).
7. [Luồng màn hình](10_SCREEN_FLOWS.md).

[07_HOST_FIRST_REVIEW.md](07_HOST_FIRST_REVIEW.md) là bằng chứng rà soát và tham khảo Vmito, không thay thế các đặc tả trên. `05_DB_V2_UPDATE.sql` và `06_SEED_VENUES.sql` là tài liệu SQL cũ; không chạy làm schema mới. Bộ tài liệu này chưa chứa migration production đã kiểm thử.

## Hiện trạng và đích

| Hiện trạng code | Đích triển khai |
|---|---|
| Flutter + Supabase + Provider, các màn hình mẫu | Giữ stack, triển khai dần |
| Không có luồng đăng nhập/phân quyền host | Auth và RLS trước pilot |
| CLB, session và người chơi chưa liên kết đủ | Schema tại 03_DATABASE |
| Bộ đếm/số dư cập nhật từ client | DB xử lý nguyên tử, client chỉ gửi ý định |
| QR chi tiết buổi là icon, tiện ích lưu tạm | QR thật, dữ liệu gắn ID buổi/người |
| Test tĩnh, chưa chứng minh luồng app | Kiểm thử quyền, cạnh tranh slot, tiền và luồng thực |

Không được diễn giải tài liệu đích là chức năng đã tồn tại. Chưa kiểm tra Supabase live hoặc chạy app trong đợt lập tài liệu. Lần này chỉ cập nhật tài liệu, chưa triển khai chức năng hoặc thay đổi DB remote.

## Quyết định mặc định cho MVP

- Miễn phí trong pilot; Nha Trang là thị trường đầu tiên.
- Host đăng nhập bằng email/mật khẩu; xác nhận email và khôi phục mật khẩu. Google login/OTP điện thoại để sau.
- Người xem không cần đăng nhập; người chơi tự đăng ký cần tài khoản. Host có thể thêm khách chưa có tài khoản đã đăng ký qua Zalo. Đăng ký khách tự phục vụ bằng token là giai đoạn sau.
- CLB có owner/host/treasurer/member. Host buổi độc lập được phép tạo buổi không thuộc CLB.
- Vãng lai mặc định cần host duyệt; host có thể chọn tự xác nhận nếu còn slot. Danh sách chờ được mời lại, không tự ép xác nhận.
- Phí cố định hoặc chia chi phí thực tế; quỹ và thanh toán được xác nhận thủ công. Không có webhook ngân hàng ở MVP.
- Không tự đóng buổi chỉ vì hết giờ; host chốt kết thúc.
- Các mặc định này là lựa chọn thiết kế để bắt đầu, có thể được chủ dự án điều chỉnh trong yêu cầu chức năng sau.

## Prompt bắt đầu gợi ý

> Đọc AGENTS.md và docs/00_START_HERE.md, rồi toàn bộ tài liệu chuẩn theo thứ tự. Triển khai BH-01 trong docs/09_IMPLEMENTATION_PLAN.md. Kiểm tra code/schema hiện có, nêu file cần sửa, làm riêng phạm vi BH-01 và chạy các kiểm thử trong tiêu chí nghiệm thu. Không chạy SQL cũ hoặc tự deploy Supabase production. Báo rõ thay đổi, kết quả kiểm thử và việc cần cấu hình ngoài code.

Khi đổi yêu cầu: cập nhật PRD → model/schema → hợp đồng DB → màn hình/backlog trong cùng thay đổi. Không tự suy ra chủ CLB hoặc gộp người từ tên/SĐT.
