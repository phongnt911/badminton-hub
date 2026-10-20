# Quy tắc cho Antigravity và các AI tham gia dự án

> **Hiện hành 20/10/2026:** Áp dụng nhiệm vụ hiện hành, không chạy lại AG-00/BH-01 hoặc ticket cũ vì đọc snapshot lịch sử. BH-06 Đạt tích hợp local tại `318bc52` ([review](reviews/bh06/review_318bc52.md)), đã merge vào main tại `e7f7627`; docs/ai đã có trên main (`eaeb209`). Baseline review: analyze sạch, 190 Flutter +335 DB, 7 tích hợp +3 nâng cấp +2 probe PASS. BH-07A **Đạt phần A local tại `4512c3a`** theo [review độc lập](reviews/bh07/review_4512c3a.md); B/C/D và pilot chưa nghiệm thu, không tự chuyển phần tiếp theo. Chưa nghiệm thu HTTP/JWT/Auth thật, thiết bị/ngân hàng thật, staging/production, backup/restore hoặc concurrency HTTP; merge code không phải deploy.

## 1. Nguồn yêu cầu

Bắt đầu tại `docs/00_START_HERE.md`, đọc PRD, kiến trúc, database, domain contracts, backlog và screen flows. Các file 01/02/03/08/09/10 là đặc tả đích chuẩn. 07 là rà soát lịch sử. SQL 05/06 là legacy, không chạy để dựng schema mới. Nếu yêu cầu mới của chủ dự án khác tài liệu, ưu tiên yêu cầu mới và cập nhật các tài liệu liên quan.

Phân biệt rõ đã có code, đã kiểm thử và yêu cầu tương lai. Không ghi hoàn thành 100% từ việc có giao diện. Người phát triển cần giải thích tiếng Việt dễ hiểu, file/command cụ thể và kết quả kiểm tra có bằng chứng.

## 2. Cách triển khai

- Làm từng ticket tại 09_IMPLEMENTATION_PLAN, hoàn thành một luồng có thể kiểm thử trước khi mở rộng.
- Đọc code/schema thực tế; nêu phạm vi và các file sẽ sửa trước khi thực hiện. Không tự áp dụng DB remote vì tài liệu có schema.
- Giữ Flutter + Provider + Supabase. Cấu trúc đích theo 02_ARCHITECTURE; thêm model/repository dần theo ticket, không tạo nhiều scaffold rỗng hoặc đổi framework.
- Không tự thêm dependency mới khi chưa thảo luận với chủ dự án. Có thể dùng thư viện hiện có và SDK chính thức đã được cài.
- Mọi network state có loading/error/empty, mutation có submitting và chống bấm trùng. Không nuốt lỗi rồi báo thành công.
- Quyền nằm tại RLS/RPC; ẩn nút chỉ là trải nghiệm. Client không ghi bộ đếm, số dư, role, confirmed_by hoặc audit actor tùy ý.
- Tiền nguyên VNĐ; thời gian UTC/timestamptz, hiển thị giờ Việt Nam. QR không xác nhận đã thu tiền.
- Không tự gộp tên/SĐT thành người dùng hoặc chủ CLB. Không đưa service-role/secrets vào source/client/log.
- Comment tiếng Việt tại logic tiền, slot và phân quyền; code đầy đủ, không placeholder giả thành tính năng hoạt động.

## 3. Kiểm thử và báo cáo

Chạy kiểm tra phù hợp ticket, ưu tiên quyền chéo CLB, hai đăng ký slot cuối, retry không trùng, chia tiền chính xác và quỹ nhất quán. Test thật luồng được sửa; không thay bằng widget Text giả. Test DB ở local/staging, không dùng tài chính hay thông tin thật trong fixture. Nếu thiếu toolchain/backend, báo rõ phần chưa chạy.

Kết thúc ticket: liệt kê thay đổi, tiêu chí nghiệm thu đạt/chưa đạt, lệnh đã chạy, việc cấu hình ngoài code và cập nhật trạng thái backlog có bằng chứng. Không thay đổi DB production, auth settings, billing hoặc deploy nếu phạm vi chức năng chưa bao gồm hành động đó. Không tự xóa dữ liệu để sửa migration; chuẩn bị kế hoạch chuyển đổi có đối chiếu.

## 4. Đồng bộ

Commit thay đổi liên quan, không gộp sửa ngoài phạm vi. Trước push kiểm tra remote và tránh ghi đè thay đổi người khác. Khi làm trên nhánh khác main, nói rõ nhánh để chủ dự án mở đúng trong Antigravity. Chỉ merge/deploy khi nằm trong yêu cầu được giao.

## 5. Điều kiện v1.1 cho Antigravity

Đọc ADR và prompt pack 11/12. Không chữa bộ đếm bằng public UPDATE policy; không chạy truy vấn bằng postgres rồi kết luận role app đúng. So sánh schema live với migrations, không giả định clubs/quỹ đã có. billing_state stale phải được bảo vệ bằng RPC, không chỉ UI. Không tạo lớp domain/use-case/adapter cho CRUD nếu chưa có trách nhiệm thực.

Prompt pack giao việc từng phạm vi; thiếu local/staging thì tiếp tục chuẩn bị code/test và báo phần chưa chạy, không tự dùng production để test. Khi task là tài liệu, không áp dụng migration. Trạng thái review gồm "đã đặc tả cách sửa" và "đã triển khai/kiểm thử", không gộp làm done.

## 6. Ghi nhận xác nhận của chủ dự án

Khi chủ dự án xác nhận đề xuất, ghi lại mục được duyệt, phạm vi và trạng thái áp dụng trong tài liệu liên quan ngay trong cùng thay đổi; đồng bộ entrypoint, backlog và handoff để phiên sau tiếp tục đúng ticket. Giữ review/JSON/log theo thời điểm đã kiểm chứng; dùng bản ghi theo dõi mới để kết nối quyết định hiện hành với snapshot cũ. Chỉ đánh dấu đã áp dụng khi thay đổi cụ thể có trong diff; không dùng sự đồng ý làm bằng chứng test đã chạy hoặc production đã triển khai.
