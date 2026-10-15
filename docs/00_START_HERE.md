# Badminton Hub — điểm bắt đầu cho Antigravity

Phiên bản đặc tả: 1.1 · 14/10/2026 · trạng thái: đặc tả đích để triển khai.

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
8. [Quyết định ADR](11_ARCHITECTURE_DECISIONS.md).
9. [Prompt và cổng nghiệm thu cho Antigravity](12_ANTIGRAVITY_PROMPTS.md).

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

## Cập nhật sau review v1.1

Ngày 14/10/2026 đã đọc metadata DB thật qua connector: public chỉ thấy venues/sessions/session_players; SELECT/INSERT policy hai bảng nghiệp vụ mở cho PUBLIC, không có UPDATE policy; code CLB/quỹ gọi bảng chưa có. Chi tiết và hành động ở [backlog xử lý review](09_IMPLEMENTATION_PLAN.md#xử-lý-phát-hiện-review-p1p2). Đây là snapshot đọc, không phải xác nhận app hoạt động hoặc quyền đã được sửa.

Bắt đầu bằng prompt AG-00 để ghi nhận baseline local/staging và kế hoạch. Sau đó triển khai từng ticket, không mở UPDATE policy cho tất cả như cách chữa bộ đếm. v1.1 bổ sung bảo vệ bản chốt phí lỗi thời, lời mời waitlist và ADR. Việc cập nhật tài liệu không đồng nghĩa R1–R7 đã được sửa trong code/DB.

## Ưu tiên sau review BH-02 ngày 15/10/2026

Đọc [13_BH02_REVIEW_HANDOFF.md](13_BH02_REVIEW_HANDOFF.md) và thực hiện prompt sửa F1–F7 trước khi sang BH-03. Đây là cập nhật mới hơn nhật ký soạn migration: 33 ca RLS cô lập có 18 PASS / 15 FAIL; chưa đạt nghiệm thu. Không chạy lại AG-00/BH-01 từ đầu nếu đã có bằng chứng triển khai.

## Ưu tiên mới sau commit 15ef59b

Review độc lập ngày 15/10/2026 xác nhận 33 ca cũ PASS nhưng 6 ca bổ sung FAIL. Tiếp tục **H1–H3** ở cuối [13_BH02_REVIEW_HANDOFF.md](13_BH02_REVIEW_HANDOFF.md), chưa chuyển BH-03. Hướng dẫn này mới hơn mục nghiệm thu 33/33 trong lịch sử; không chạy lại AG-00/BH-01.

## Tham khảo sản phẩm: Vmito và Vụt

[14_PRODUCT_LEARNINGS_VMITO_VUT.md](14_PRODUCT_LEARNINGS_VMITO_VUT.md) là bản áp dụng hai báo cáo REA do chủ dự án cung cấp. Đọc phần PD tương ứng khi thực hiện BH-03..07; giữ các giới hạn static/runtime, không thêm dependency/schema theo danh sách thư viện đối thủ. Đây là tài liệu bổ sung yêu cầu, không thay lịch sử kiểm thử hoặc xác nhận sửa BH-02.

## Tiếp tục BH-03

Chủ dự án yêu cầu chuyển sang BH-03 sau remediation 11aaec7. Dùng [15_BH03_IMPLEMENTATION_HANDOFF.md](15_BH03_IMPLEMENTATION_HANDOFF.md) làm đầu bài cụ thể cho CLB/member/bank, giữ regression BH-02; không chạy lại AG-00/BH-01. Những mục chờ H1–H3 phía trên là lịch sử trước remediation; việc chấp nhận bước tiếp theo không thay cho báo cáo môi trường/giới hạn test thực tế.

## Cập nhật BH-03 sau review C1–C5

Đọc [17_BH03_REMEDIATION.md](17_BH03_REMEDIATION.md): đã có forward migration và regression cho consent, concurrent idempotency, request keys và logout/session isolation. Giữ lịch sử review 88dd247 như baseline; không lặp lại các lỗi đã sửa. Production chưa apply, full Supabase integration vẫn cần kiểm chứng theo giới hạn trong báo cáo.
