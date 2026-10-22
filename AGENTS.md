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

Ngày 22/10/2026: Gói kiểm chứng **Browser / Offline / Reopen BH-07 đang ở trạng thái Chờ review vòng 1/2** trên nhánh `feat/bh07-browser-verification`, tested source `b00b580` từ base `86c464293f796d5f3b0890acc8bb33a85f7d4897`. Đã khắc phục triệt để BR1–BR5: tương tác UI thật qua Chrome CDP với mouse/keyboard/semantics và negative control đỏ; offline mutation qua UI bắt lỗi transport, retry bảo toàn intent/payload; kiểm tra clipboard thực tế `navigator.clipboard.readText()`, lọc sạch SĐT/STK/secrets, ẩn thẻ tài chính của Cohost; login/logout qua form UI thật, xóa sạch `localStorage` token, bảo toàn phiên qua F5/reload; bổ sung `browser_runner.log`, sửa recipe DB trong `commands.md`, đo lường exit code thật và cập nhật manifest 100% UTF-8 LF. Kết quả: **11/11 browser UI checks PASS**, analyze sạch, **240 Flutter +1 skip PASS**, **23/23 BH-07 DB PASS**. Toàn BH-07/pilot vẫn chưa nghiệm thu; các cổng thiết bị di động thật, ngân hàng/webhook thật, staging/production/backup và rehearsal/pilot vẫn NOT RUN; không tự merge/apply DB thật/deploy.

(Lịch sử review) Ngày 22/10/2026: Gói kiểm chứng **Browser / Offline / Reopen BH-07 Chưa đạt tại `c8a8e7f`** theo [review độc lập](docs/reviews/bh07/review_c8a8e7f.md). Mở **BR1/BR2 P1, BR3–BR5 P2**: runner bỏ qua UI, không kiểm mutation offline/request_id, copy/privacy/ACL và auth/cache chưa đủ, thiếu log/provenance. Reviewer tự chạy analyze sạch, **240 Flutter +1 skip**, **23 DB**, build Web thành công. Runner trên Chromium thật tự báo 11/11 nhưng UI trắng; 17 ảnh tác giả giống nhau và chỉ là guest screen, nên **không nghiệm thu browser UI**. Manifest chỉ 22/23, thiếu browser_runner.log. Chuyển sang sửa gói kiểm chứng vòng 1/2.

(Lịch sử review) Ngày 22/10/2026: Gói kiểm chứng **Concurrency HTTP/Auth BH-07 Đạt local vòng2/2**, tested source `cbcc46c`, docs/evidence thực tế `bb940280333aec96457dd3014aabba9f66adf4ae`, theo [review độc lập](docs/reviews/bh07/review_cbcc46c_r2.md). **Đóng H3/H4**, giữ H1/H2 đã đóng; không còn P0/P1/P2 mở trong gói. Reviewer tự audit **19/19 hash**, UTF-8 không BOM, CR/CRLF=0, nội dung log và metadata lịch sử bảo toàn, scan không thấy secret theo mẫu kiểm; source không đổi. Vòng2/2 không chạy lại suite; kế thừa kết quả reviewer vòng1/2: **76 HTTP, 240 Flutter +1 skip, 23 DB, 4 probe PASS**, analyze sạch. Giữ A/B/C/D và HTTP/Auth nền Đạt local; **toàn BH-07/pilot chưa nghiệm thu**. Thiết bị/browser/offline, ngân hàng/webhook, staging/production/backup, rehearsal/pilot vẫn NOT RUN; không merge/apply DB thật/deploy.

(Lịch sử review) Ngày 22/10/2026: Gói kiểm chứng **Concurrency HTTP/Auth BH-07 Chưa đạt vòng 1/2 tại `cbcc46c`**, docs/evidence `b23df5e`, theo [review độc lập](docs/reviews/bh07/review_cbcc46c.md): Đóng H1/H2 P2; mở H3/H4 P2 về log UTF-16/CRLF trái công bố LF và full base SHA sai. Reviewer tự chạy 76/76 HTTP, analyze sạch, 240 Flutter +1 skip, 23/23 DB, 4/4 probe PASS. Manifest 19/19 khớp raw bytes; secret scan sạch sau decode. Chuyển sang sửa tài liệu/bằng chứng vòng 2/2.

(Lịch sử review) Ngày 22/10/2026: Gói kiểm chứng **Concurrency HTTP/Auth BH-07 Chưa đạt tại `2f0aa59`** theo [review độc lập](docs/reviews/bh07/review_2f0aa59.md): H1/H2 P2 về tiền đề drop sau commit và validator lỗi cạnh tranh quá rộng. Reviewer tự chạy **76/76 HTTP**, analyze sạch, **240 Flutter +1 skip**, **23/23 DB**; hai probe tái hiện xanh giả. Manifest tác giả 21/21 khớp LF, không thấy secret theo scan. Đã chuyển sang sửa gói kiểm chứng vòng 1/2.

(Lịch sử bàn giao) Ngày 21/10/2026: Gói kiểm chứng **Concurrency HTTP/Auth BH-07 đang ở trạng thái Chờ review** trên nhánh `feat/bh07-http-concurrency` từ base `4da6339`. Đã bổ sung 6 check concurrency: idempotent replay complete/tiền, competing complete conflict, competing cash payment no-overcollect, transport drop response sau commit rồi retry. Kết quả: **76/76 HTTP check local**, analyze sạch, **240 Flutter +1 skip**, **23/23 BH-07 DB PASS**; red run trước khi nạp fixture ghi nhận **70/76** (đúng 6 FAIL concurrency). Manifest 21/21 khớp LF, quét sạch secret. Toàn BH-07/pilot vẫn chưa nghiệm thu; các cổng thiết bị/browser/offline, ngân hàng, staging/production/backup và rehearsal/pilot vẫn NOT RUN; không tự merge/apply DB thật/deploy.

Sau khi chủ dự án xác nhận thay đổi, ghi quyết định/phạm vi vào tài liệu và bảng trạng thái liên quan trong cùng lượt, đối chiếu bằng chứng, rồi commit/push theo ủy quyền. Không để mục đã được duyệt tiếp tục mang trạng thái chờ quyết định; không biến duyệt tài liệu thành nghiệm thu code hoặc deploy.
