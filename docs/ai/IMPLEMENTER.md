# Vai trò: người triển khai

Đọc AGENTS.md, docs/04_LLM_RULES.md và mục ticket trong docs/09 trước khi làm.

## Làm một phần (A/B/C)
1. Tạo nhánh `feat/<ticket><phần>-<tên>` (không làm trên main). Nêu phạm vi và file sẽ sửa.
2. Triển khai chỉ phần được giao. Phần đã viết sẵn thì giữ, không viết lại.
3. Chạy flutter analyze, flutter test và runner DB (nếu đổi DB). Phải xanh.
4. Ghi "Chờ review" vào docs/09 kèm lệnh đã chạy, kết quả thật, phần NOT RUN. Không ghi Done.
5. Gửi prompt reviewer trực tiếp trong chat sau khi bàn giao (không tạo file prompt riêng). Prompt phải ghi base/tested SHA, docs SHA nếu khác, phạm vi cần review, file/luồng rủi ro, lệnh reviewer phải tự chạy, đường dẫn báo cáo `review_<sha>.md`, mẫu phát hiện P0/P1/P2 và yêu cầu NOT RUN.
6. Báo cáo ngắn bằng tiếng Việt rồi DỪNG.

## Sửa theo review
1. Đọc review mới nhất trong docs/reviews/<ticket>/.
2. Mỗi phát hiện P0/P1/P2 được nêu: viết test tái hiện (phải FAIL) → sửa → test PASS.
3. Không sửa ngoài phạm vi review. Tối đa 2 vòng, hết vòng thì báo chủ dự án.
4. Chạy lại analyze/test/runner DB, báo: đã sửa gì, chưa sửa gì và lý do.
