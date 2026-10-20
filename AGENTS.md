# Hướng dẫn cho AI làm việc trong repo

Đọc `docs/00_START_HERE.md` trước khi triển khai. Sau đó đọc các tài liệu chuẩn theo thứ tự được liệt kê và tuân thủ `docs/04_LLM_RULES.md`.

Dự án đang chuyển từ demo sang công cụ quản lý CLB/buổi cho host. Tài liệu v1.1 mô tả đích, không khẳng định code/DB đã triển khai. Làm từng ticket trong `docs/09_IMPLEMENTATION_PLAN.md`, giữ Flutter + Provider + Supabase.

Không chạy SQL legacy 05/06 như migration mới, không gộp dữ liệu theo tên/SĐT, không ghi bộ đếm/số dư từ client. Không tự thay đổi Supabase production khi nhiệm vụ chỉ là viết code/tài liệu. Mỗi thay đổi cần kiểm thử phù hợp và báo cáo tiếng Việt, nêu phần chưa kiểm chứng.

Đọc thêm `docs/11_ARCHITECTURE_DECISIONS.md` và `docs/12_ANTIGRAVITY_PROMPTS.md` cho v1.1. Bắt đầu AG-00 để ghi baseline và môi trường test; triển khai từng prompt. Các phát hiện P1/P2 chưa được sửa bằng việc publish tài liệu.

## Quy trình hai AI (từ BH-05)

Vai trò: DeepSeek/Antigravity = người triển khai. Codex (GPT-6.1 Sol) = người review độc lập.

- Người triển khai KHÔNG tự ghi "Done". Chỉ ghi "Chờ review" kèm lệnh đã chạy và bằng chứng. Chỉ người review ghi kết luận Đạt/Chưa đạt.
- Mỗi ticket chia phần nhỏ (A: DB/RPC, B: model/repository/provider, C: UI), mỗi phần một nhánh `feat/bh05a-...`, commit riêng.
- Trước khi gửi review phải xanh: `flutter analyze`, `flutter test`, và runner DB của ticket (nếu có đổi DB).
- Review nằm ở `docs/reviews/<ticket>/review_<sha>.md`, mỗi phát hiện ghi: file:dòng, mức P0/P1/P2, cách sửa.
- Sửa theo review: viết test tái hiện lỗi trước, sửa toàn bộ phát hiện P0/P1/P2 được nêu (kể cả P2), tối đa 2 vòng. Còn lỗi sau 2 vòng thì dừng và báo chủ dự án.
- Người review không viết lại code, trừ khi chủ dự án giao rõ.
Vai trò làm việc: xem docs/ai/IMPLEMENTER.md (người triển khai) và docs/ai/REVIEWER.md (người review). Chỉ làm đúng vai trò được giao trong yêu cầu.
