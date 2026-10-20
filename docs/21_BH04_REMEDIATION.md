# BH-04 — sửa review R1–R4

> **Hiện hành 20/10/2026:** Nội dung dưới là snapshot lịch sử; không dùng lỗi hoặc prompt cũ để triển khai lại ticket đã nghiệm thu. BH-06 Đạt tích hợp local tại `318bc52` ([review](reviews/bh06/review_318bc52.md)), đã merge vào main tại `e7f7627`; docs/ai đã có trên main (`eaeb209`). Baseline review: analyze sạch, 190 Flutter +335 DB, 7 tích hợp +3 nâng cấp +2 probe PASS. BH-07A **Đạt phần A local tại `4512c3a`** theo [review độc lập](reviews/bh07/review_4512c3a.md); B/C/D và pilot chưa nghiệm thu, không tự chuyển phần tiếp theo. Chưa nghiệm thu HTTP/JWT/Auth thật, thiết bị/ngân hàng thật, staging/production, backup/restore hoặc concurrency HTTP; merge code không phải deploy.

Ngày 15/10/2026 (Việt Nam). Baseline `dd5c1e6`; [review gốc](reviews/bh04/review_dd5c1e6.md) là lịch sử trước bản sửa.

## Đã sửa

- **R1:** forward migration `20261015163001_bh04_review_fixes.sql` hash lifecycle theo session_id/action, không theo version DB thay đổi sau commit. Retry cùng key trả kết quả đã lưu. File tạo qua Supabase CLI rồi sắp timestamp sau migration BH04 đã có (file trước mang thời gian tương lai so với thời điểm chạy CLI); không sửa lịch sử.
- **R2:** MaterialApp nhận `/sessions/:id` và `/clubs/:id` qua onGenerateRoute. Chia sẻ URL đầy đủ bằng APP_BASE_URL, hoặc origin web hiện tại. Mobile phải cấu hình APP_BASE_URL cho web triển khai. Không còn báo sao chép thành công khi clipboard/config lỗi. Chặn URI không scheme nhưng có authority và scheme không authority trong parser. Luồng đăng nhập từ trang lỗi quyền tải lại chi tiết sau thành công.
- **R3:** xóa pending key sau response mutation thành công, trước refresh danh sách; timeout/lỗi vẫn giữ key. Ý định mới cùng payload được key mới. Cache vẫn trong bộ nhớ, không tồn tại qua force-kill.
- **R4:** roster có loading/error/retry riêng, không hiển thị empty/dữ liệu cũ như kết quả tải thành công khi RPC lỗi. Response trễ vẫn chịu generation/serial/session guard.

## Kiểm thử tự chạy

- Flutter 3.47.7/Dart 3.13.5: **104/104 PASS**; analyze **No issues found**.
- Có test app thật `BadmintonHubApp` khởi động với initial route `/sessions/UUID`, mở login và quay về đúng ID; test URL có origin, parser; test lỗi roster rồi retry; test key mới sau thành công cùng payload và giữ key qua timeout.
- PostgreSQL17.11 container cô lập `bh02-review-postgres`, Auth stub: BH04 **44/44**, BH03 **48/48 +22/22**, BH02 **33/33 +14/14** = **161/161 PASS**.
- BH04 có publish replay cùng request và cancel replay; cả clean/legacy. Toàn bộ chuỗi migrations áp trên DB test mới; JSON timestamp 20261015162618 (BH04), 20261015162632 (BH03), 20261015162645 (BH02). Metadata ghi baseline/worktree dirty và hash migrations; không gọi baseline dd5c1e6 là mã đã sửa.
- Log Flutter/analyze và hash manifest nằm trong reviews/bh04/remediation.

## Triển khai và giới hạn

Không apply Supabase production hoặc staging. Chưa kiểm HTTP/PostgREST/JWT thật, browser e2e/reload hosting hoặc OS App Links/Universal Links. Widget initial-route không chứng minh cấu hình web server: hosting phải trả index.html cho `/sessions/*` và `/clubs/*`. Dùng domain sở hữu và APP_BASE_URL của web đã triển khai; sửa allowlist host nếu dùng domain khác với các host hiện tại trong AppRoutes. Chưa tự triển khai domain/site.

Các operation_requests lifecycle được tạo bằng hash cũ (nếu có trên môi trường đã triển khai) không tự chuyển sang hash mới. Kiểm tra lịch sử apply/request trước rollout; đối chiếu kết quả thực tế cho request cũ, không xóa record hoặc tự retry bằng key mới để né conflict. Migration không xóa dữ liệu.

## Tiếp tục BH-05

Đọc AGENTS.md, 00_START_HERE, tài liệu này và 20_BH04_HANDOFF, sau đó AG-05/spec 03/08/09/10/11. Giữ regression **104 Flutter +161 DB**, triển khai đăng ký/duyệt/hủy/waitlist bằng RPC atomic và idempotency. Không tái mở direct write hoặc tự apply production. Cổng HTTP/JWT, thiết bị thật và migration rehearsal vẫn cần trước pilot.
