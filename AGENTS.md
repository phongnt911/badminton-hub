# Hướng dẫn cho AI làm việc trong repo

Đọc `docs/00_START_HERE.md` trước khi triển khai. Sau đó đọc các tài liệu chuẩn theo thứ tự được liệt kê và tuân thủ `docs/04_LLM_RULES.md`.

Dự án đang chuyển từ demo sang công cụ quản lý CLB/buổi cho host. Tài liệu v1.1 mô tả đích, không khẳng định code/DB đã triển khai. Làm từng ticket trong `docs/09_IMPLEMENTATION_PLAN.md`, giữ Flutter + Provider + Supabase.

Không chạy SQL legacy 05/06 như migration mới, không gộp dữ liệu theo tên/SĐT, không ghi bộ đếm/số dư từ client. Không tự thay đổi Supabase production khi nhiệm vụ chỉ là viết code/tài liệu. Mỗi thay đổi cần kiểm thử phù hợp và báo cáo tiếng Việt, nêu phần chưa kiểm chứng.

Đọc thêm `docs/11_ARCHITECTURE_DECISIONS.md` và `docs/12_ANTIGRAVITY_PROMPTS.md` cho v1.1. Với checkout mới chưa có bằng chứng, bắt đầu AG-00 để ghi baseline và môi trường test; checkout đã có nghiệm thu tiếp tục theo trạng thái hiện hành trong docs/00, không chạy lại AG-00/BH-01. Các phát hiện P1/P2 chưa được sửa bằng việc publish tài liệu.

## Quy trình hai AI (từ BH-05)

Vai trò: DeepSeek/Antigravity = người triển khai. Codex (GPT-6.1 Sol) = người review độc lập.

- Người triển khai KHÔNG tự ghi "Done". Chỉ ghi "Chờ review" kèm lệnh đã chạy và bằng chứng. Chỉ người review ghi kết luận Đạt/Chưa đạt.
- Mỗi ticket chia phần nhỏ (A: DB/RPC, B: model/repository/provider, C: UI), mỗi phần một nhánh `feat/bh05a-...`, commit riêng.
- Trước khi gửi review phải xanh: `flutter analyze`, `flutter test`, và runner DB của ticket (nếu có đổi DB).
- Review nằm ở `docs/reviews/<ticket>/review_<sha>.md`, mỗi phát hiện ghi: file:dòng, mức P0/P1/P2, cách sửa.
- Sửa theo review: viết test tái hiện lỗi trước, chỉ sửa P0/P1 được nêu, tối đa 2 vòng. Còn lỗi sau 2 vòng thì dừng và báo chủ dự án.
- Người review không viết lại code, trừ khi chủ dự án giao rõ.

## Trạng thái và xác nhận hiện hành

Ngày 16/10/2026: BH-05 đạt review tích hợp `d769531`, hồi quy main `3a34883` đạt analyze sạch, 137 Flutter +251 DB. Điểm tiếp tục BH-06; chưa apply staging/production hoặc kiểm full HTTP/JWT/thiết bị thật. Cập nhật docs sau audit đã được chủ dự án duyệt B1–B9 và C1/C2, xem `docs/23_DOC_AUDIT_FOLLOWUP.md`. Giữ review/bằng chứng cũ theo tested commit.

Sau khi chủ dự án xác nhận thay đổi, ghi quyết định/phạm vi vào tài liệu và bảng trạng thái liên quan trong cùng lượt, đối chiếu bằng chứng, rồi commit/push theo ủy quyền. Không để mục đã được duyệt tiếp tục mang trạng thái chờ quyết định; không biến duyệt tài liệu thành nghiệm thu code hoặc deploy.
