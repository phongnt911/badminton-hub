# Hướng dẫn cho AI làm việc trong repo

Đọc `docs/00_START_HERE.md` trước khi triển khai. Sau đó đọc các tài liệu chuẩn theo thứ tự được liệt kê và tuân thủ `docs/04_LLM_RULES.md`.

Dự án đang chuyển từ demo sang công cụ quản lý CLB/buổi cho host. Tài liệu v1.1 mô tả đích, không khẳng định code/DB đã triển khai. Làm từng ticket trong `docs/09_IMPLEMENTATION_PLAN.md`, giữ Flutter + Provider + Supabase.

Không chạy SQL legacy 05/06 như migration mới, không gộp dữ liệu theo tên/SĐT, không ghi bộ đếm/số dư từ client. Không tự thay đổi Supabase production khi nhiệm vụ chỉ là viết code/tài liệu. Mỗi thay đổi cần kiểm thử phù hợp và báo cáo tiếng Việt, nêu phần chưa kiểm chứng.

Đọc thêm `docs/11_ARCHITECTURE_DECISIONS.md` và `docs/12_ANTIGRAVITY_PROMPTS.md` cho v1.1. Với checkout mới chưa có bằng chứng, bắt đầu AG-00 để ghi baseline và môi trường test; checkout đã có nghiệm thu tiếp tục theo trạng thái hiện hành trong docs/00, không chạy lại AG-00/BH-01. Các phát hiện P1/P2 chưa được sửa bằng việc publish tài liệu.

## Quy trình hai AI (từ BH-05)

Vai trò: DeepSeek/Antigravity = người triển khai. Codex (GPT-6.1 Sol) = người review độc lập.

- Người triển khai KHÔNG tự ghi "Done". Chỉ ghi "Chờ review" kèm lệnh đã chạy và bằng chứng. Chỉ người review ghi kết luận Đạt/Chưa đạt.
- Mỗi lần bàn giao phải gửi kèm prompt reviewer trực tiếp trong chat (không tạo file prompt riêng). Prompt ghi base/tested SHA, docs SHA nếu khác, phạm vi, rủi ro cần kiểm, lệnh reviewer phải tự chạy, đường dẫn báo cáo và mẫu phát hiện P0/P1/P2/NOT RUN.
- Mỗi ticket chia phần nhỏ (A: DB/RPC, B: model/repository/provider, C: UI), mỗi phần một nhánh `feat/bh05a-...`, commit riêng.
- Trước khi gửi review phải xanh: `flutter analyze`, `flutter test`, và runner DB của ticket (nếu có đổi DB).
- Review nằm ở `docs/reviews/<ticket>/review_<sha>.md`, mỗi phát hiện ghi: file:dòng, mức P0/P1/P2, cách sửa.
- Sửa theo review: viết test tái hiện lỗi trước, sửa toàn bộ phát hiện P0/P1/P2 được nêu (kể cả P2), tối đa 2 vòng. Còn lỗi sau 2 vòng thì dừng và báo chủ dự án.
- Người review không viết lại code, trừ khi chủ dự án giao rõ.

Vai trò làm việc: xem docs/ai/IMPLEMENTER.md (người triển khai) và docs/ai/REVIEWER.md (người review). Chỉ làm đúng vai trò được giao trong yêu cầu.

## Trạng thái và xác nhận hiện hành

Ngày 22/10/2026: Gói kiểm chứng **Concurrency HTTP/Auth BH-07 ở trạng thái Chờ review vòng 1/2 tại `cbcc46c`** trên nhánh `feat/bh07-http-concurrency` từ base `a0f831a`. Đã sửa toàn bộ phát hiện H1/H2 P2 trong review `2f0aa59`: H1 chỉ drop sau HTTP 200, kiểm chứng DB server đã commit trước khi retry, thêm negative control HTTP 400 không vượt gate; H2 kiểm domain error có cấu trúc (VERSION_CONFLICT/INVALID_STATE 22023/409, PAYMENT_EXCEEDS_OUTSTANDING 22023), thêm negative controls loại bỏ FORBIDDEN/NOT_FOUND/amount/transport. Red probe ghi nhận 3 FAIL trước sửa, green probe 5/5 PASS sau sửa. Kết quả độc lập: **76/76 HTTP checks PASS**, analyze sạch, **240 Flutter +1 skip**, **23/23 BH-07 DB PASS**. Manifest 19/19 khớp LF, quét sạch secret. Giữ HTTP/Auth `f9159dd` và A/B/C/D đã Đạt local. **Toàn BH-07/pilot chưa nghiệm thu**; thiết bị/browser/offline, ngân hàng, staging/production/backup và rehearsal/pilot vẫn NOT RUN. Không merge main/apply DB thật/deploy.

(Lịch sử review) Ngày 22/10/2026: Gói kiểm chứng **Concurrency HTTP/Auth BH-07 Chưa đạt tại `2f0aa59`** theo [review độc lập](docs/reviews/bh07/review_2f0aa59.md): H1/H2 P2 về tiền đề drop sau commit và validator lỗi cạnh tranh quá rộng. Reviewer tự chạy **76/76 HTTP**, analyze sạch, **240 Flutter +1 skip**, **23/23 DB**; hai probe tái hiện xanh giả. Manifest tác giả 21/21 khớp LF, không thấy secret theo scan. Đã chuyển sang sửa gói kiểm chứng vòng 1/2.

(Lịch sử bàn giao) Ngày 21/10/2026: Gói kiểm chứng **Concurrency HTTP/Auth BH-07 đang ở trạng thái Chờ review** trên nhánh `feat/bh07-http-concurrency` từ base `4da6339`. Đã bổ sung 6 check concurrency: idempotent replay complete/tiền, competing complete conflict, competing cash payment no-overcollect, transport drop response sau commit rồi retry. Kết quả: **76/76 HTTP check local**, analyze sạch, **240 Flutter +1 skip**, **23/23 BH-07 DB PASS**; red run trước khi nạp fixture ghi nhận **70/76** (đúng 6 FAIL concurrency). Manifest 21/21 khớp LF, quét sạch secret. Toàn BH-07/pilot vẫn chưa nghiệm thu; các cổng thiết bị/browser/offline, ngân hàng, staging/production/backup và rehearsal/pilot vẫn NOT RUN; không tự merge/apply DB thật/deploy.

Sau khi chủ dự án xác nhận thay đổi, ghi quyết định/phạm vi vào tài liệu và bảng trạng thái liên quan trong cùng lượt, đối chiếu bằng chứng, rồi commit/push theo ủy quyền. Không để mục đã được duyệt tiếp tục mang trạng thái chờ quyết định; không biến duyệt tài liệu thành nghiệm thu code hoặc deploy.
