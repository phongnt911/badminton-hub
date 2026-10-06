# BỘ QUY TẮC DÀNH CHO CÁC AI/LLM THAM GIA DỰ ÁN

Tài liệu này là BẮT BUỘC ĐỌC đối với mọi LLM (ChatGPT, Claude, Gemini, Copilot...) trước khi đọc mã nguồn hoặc tạo/chỉnh sửa code.

## 1. Thông tin Chủ dự án
- Người phát triển là người mới bắt đầu (Beginner / Non-tech). 
- Mục tiêu: Code chuẩn mực, sạch sẽ, dễ bảo trì, giải thích bằng Tiếng Việt dễ hiểu.
- KHÔNG dùng từ ngữ quá hàn lâm, không refactor phức tạp khi chưa được yêu cầu.

## 2. Nguyên tắc Code
- **Chậm mà chắc:** Làm từng tính năng một. Không viết code dở dang hoặc tạo quá nhiều file cùng lúc.
- **Bảo toàn cấu trúc:** Tuân thủ 100% cấu trúc thư mục quy định tại `docs/02_ARCHITECTURE.md`. Không tự ý tạo thư mục hay kiến trúc riêng.
- **Thư viện (Dependencies):** Không tự tiện thêm thư viện mới vào `pubspec.yaml` nếu không thảo luận trước với người dùng.
- **Comment Tiếng Việt:** Viết chú thích rõ ràng ở các hàm logic quan trọng (đặc biệt là tính tiền, tạo VietQR, tính điểm).
- **Xử lý ngoại lệ (Error Handling):** Mọi chức năng gọi mạng hoặc CSDL phải có đủ 3 trạng thái: Đang tải (Loading), Lỗi (Error), và Không có dữ liệu (Empty).

## 3. Quy trình làm việc khi nhận yêu cầu mới
1. Đọc lại `docs/01_PRD_SPEC.md` để hiểu nghiệp vụ.
2. Nêu rõ kế hoạch: Sẽ tạo/sửa những file nào, mục đích là gì.
3. Cung cấp mã nguồn trọn vẹn (không viết tắt `// code cũ ở đây...` gây nhầm lẫn cho người mới).
4. Hướng dẫn người dùng cách kiểm thử (Test) trên thiết bị.