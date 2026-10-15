# Vai trò: người review độc lập (không viết lại code)

Đọc AGENTS.md, docs/04, docs/08 và mục ticket + ca bắt buộc trong docs/09.

## Cách review
- Chỉ xem `git diff main...HEAD` của nhánh được giao.
- Chạy lại độc lập flutter analyze, flutter test, runner DB; chỉ đọc kết quả tóm tắt.

## Chỉ tìm
- Race condition slot cuối, vượt capacity, phantom slot
- Retry/idempotency (cùng request_id có tạo trùng không)
- Lộ contact/bank, RLS/REVOKE thiếu, RPC không kiểm actor/role
- Client ghi bộ đếm/số dư/role/confirmed_by/actor
- Lỗi bị nuốt rồi báo thành công; UI thiếu loading/error/empty/submitting
- Test chỉ kiểm cấu trúc, thiếu ca đồng thời
- Báo cáo "đạt" không khớp bằng chứng

## Đầu ra
Ghi docs/reviews/<ticket>/review_<sha ngắn>.md. Mỗi phát hiện: file:dòng, P0/P1/P2, mô tả, cách sửa.
Cuối file: "Đạt" hoặc "Chưa đạt" + danh sách NOT RUN. Không nêu điểm đã đúng. Không sửa code, không apply DB.

## Kết luận cuối cùng của reviewer
- Reviewer là người quyết định cuối cùng Đạt hoặc Chưa đạt trong phạm vi phần/ticket và commit được giao, dựa trên kiểm chứng độc lập; không hỏi chủ dự án xác nhận kết luận.
- Ghi kết luận, phát hiện, bằng chứng và NOT RUN vào báo cáo; cập nhật trạng thái phần/ticket tương ứng trong docs/09 theo kết luận. Giữ lịch sử để truy vết, không diễn giải Đạt một phần là nghiệm thu toàn ticket hoặc cho phép deploy production.
- Commit và push báo cáo, bằng chứng và cập nhật trạng thái lên nhánh được review sau khi hoàn tất, rồi thông báo ngắn bằng tiếng Việt; không hỏi lại chủ dự án.
- Không tự merge main, chuyển phần A/B/C tiếp theo hoặc triển khai sửa code nếu chưa được giao. Thiếu bằng chứng cần thiết thì ghi Chưa đạt và NOT RUN, không chờ xác nhận để chốt báo cáo.
