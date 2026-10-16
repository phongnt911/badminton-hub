# PRD — Badminton Hub

> **Hiện hành 16/10/2026:** Đây là yêu cầu đích; phạm vi tài chính/QR/pilot vẫn thuộc BH-06 trở đi. BH-05 đạt review tích hợp tại `d769531`; hồi quy main `3a34883`: analyze sạch, 137 Flutter + 251 DB. Tiếp theo BH-06. Chỉ kiểm thử local/PostgreSQL cô lập; chưa apply staging/production, chưa HTTP/JWT thật, thiết bị/browser e2e, backup/restore hoặc concurrency qua HTTP. [Trạng thái và xác nhận sau audit](23_DOC_AUDIT_FOLLOWUP.md).

Phiên bản 1.1 · 14/10/2026. Đây là yêu cầu đích, không phải báo cáo hoàn thành.

## 1. Định vị và mục tiêu

Công cụ giúp host cầu lông vận hành CLB, tổ chức buổi định kỳ, tuyển vãng lai, điểm danh và chốt thu/chi. Pilot tại Nha Trang. Giữ miễn phí trong pilot và chưa đưa quảng cáo vào luồng vận hành/thu tiền. Nguồn thu tài trợ/affiliate hoặc gói host nâng cao chỉ xem xét sau khi đo được sử dụng; chưa thay đổi cam kết thương mại hiện tại.

Host đang tổng hợp đăng ký qua tin nhắn, khó biết ai sẽ đến và ai còn nợ. App phải giúp hoàn thành những việc này nhanh và có lịch sử đối chiếu. Người chơi không phải học một hệ thống quản lý đầy đủ để đăng ký một buổi.

## 2. Người dùng

| Người dùng | Nhu cầu |
|---|---|
| Host/chủ CLB | Lịch, sức chứa, đăng ký, điểm danh, thu tiền |
| Đồng host | Vận hành các buổi được giao |
| Thủ quỹ | Khoản phải thu, khoản đã thu, sổ quỹ |
| Thành viên cố định | Biết lịch, xác nhận từng buổi, xem công nợ riêng |
| Vãng lai | Xem kèo, trình độ/phí, gửi yêu cầu và biết trạng thái |
| Người xem | Xem thông tin công khai và danh bạ sân |

Một người có vai trò khác nhau ở các CLB. Vai trò/quyền chi tiết tại 03_DATABASE. Admin ứng dụng không được mặc định đọc mọi số điện thoại và giao dịch.

## 3. Phạm vi MVP và yêu cầu

| ID | Yêu cầu | Tiêu chí chính |
|---|---|---|
| FR-01 | Đăng nhập/đăng xuất/khôi phục tài khoản | Email xác nhận; phiên hết hạn có hướng dẫn đăng nhập lại; không mất buổi khi quay lại |
| FR-02 | Tạo và quản lý CLB | Owner có thể sửa CLB, thêm thành viên và cấp vai trò; không tự nhận sở hữu CLB khác |
| FR-03 | Quản lý thành viên chưa có account | Host nhập tên/liên hệ; ID ổn định; liên kết account chỉ sau xác nhận; không gộp theo tên |
| FR-04 | Tạo, sửa, nhân bản buổi | Ngày/giờ/sân/sức chứa/trình độ/phí; nhân bản chỉ lấy cấu hình, không lấy đăng ký/thanh toán |
| FR-05 | Chia sẻ buổi | Link theo ID và nội dung sao chép cho Zalo/Facebook; riêng tư không xuất hiện trong tìm kiếm |
| FR-06 | Đăng ký, duyệt, hủy và chờ | Không vượt sức chứa, không thêm trùng, trạng thái rõ; host thêm người từ Zalo dùng cùng kiểm tra slot |
| FR-07 | Điểm danh | Chỉ confirmed được ghi present/no_show; thêm khách đến trực tiếp qua đăng ký hợp lệ |
| FR-08 | Chốt phí | Phí fixed hoặc split_actual, tổng tiền chính xác; mọi người thấy khoản riêng sau chốt |
| FR-09 | QR và thu tiền | Đúng người nhận, số tiền và mã tham chiếu; hỗ trợ tiền mặt/chuyển khoản và trả nhiều lần |
| FR-10 | Quỹ và công nợ | Tổng tính từ giao dịch đã ghi; liên kết thu/chi buổi không ghi hai lần; điều chỉnh có lý do |
| FR-11 | Kết thúc/lịch sử | Completed vẫn giữ công nợ; các thao tác tài chính cần quyền và lưu lịch sử |
| FR-12 | Danh bạ sân | Xem/gọi điện/chỉ đường; chỉ quyền danh bạ được cập nhật dữ liệu sân |

## 4. Vòng đời

Buổi: draft → published → in_progress → completed; draft/published được cancelled. Hủy buổi đang diễn ra cần hành động riêng có lý do và xử lý phần đã chơi, không đổi trạng thái lặng lẽ. Published có thể hết chỗ nhưng vẫn published. Completed không có nghĩa đã thu đủ.

Đăng ký: pending → confirmed/rejected/waitlisted; confirmed → cancelled trước hạn hủy; host có thể hủy sau hạn với lý do. Waitlisted được host mời lại, người chơi chấp nhận rồi DB kiểm tra slot trước confirmed. Người bị rejected chỉ gửi lại khi host mở lại yêu cầu. Người đã cancelled có thể đăng ký lại nếu chưa quá hạn, dùng lại cùng ID.

Chỉ confirmed chiếm slot. Pending/waitlisted không giữ chỗ. Số chỗ được tính từ DB. Host chỉ chiếm chỗ nếu có đăng ký confirmed của chính mình. Có mặt là trạng thái riêng với đăng ký. Không tự đánh dấu no_show chỉ dựa trên giờ.

## 5. Quy tắc lịch và phí

- Lưu thời gian UTC bằng timestamptz; hiển thị Asia/Ho_Chi_Minh. Chọn ngày tương lai và giờ bằng form. ends_at > starts_at; sức chứa > 0; số sân > 0. Buổi qua nửa đêm dùng ngày kết thúc đúng.
- Deadline đăng ký không sau ends_at; deadline hủy không sau starts_at. Không chấp nhận tự đăng ký khi cancelled/completed hoặc đã hết hạn. In_progress chỉ host được thêm người đến trực tiếp.
- Không hạ capacity thấp hơn số confirmed. Đổi sân/giờ/phí sau khi có đăng ký cần hiển thị cảnh báo, ghi audit và thông báo trong app cho người liên quan; MVP không hứa push/SMS tự động.
- Fixed: mức phí của từng người được chốt khi confirmed, dựa trên thành viên/khách và miễn giảm đã thống nhất; khi chốt buổi chỉ tính người present. MVP no_show/cancelled có phí 0; phạt hủy/no-show và thu phí tháng để giai đoạn sau.
- Split_actual: tổng chi phí đã duyệt chia cho người present và không được miễn phí. Không có người chịu phí thì báo lỗi cần xử lý, không chia cho 1.
- Tiền là số nguyên VNĐ. Đề xuất phân dư: q = total // n, r = total % n; r người đầu theo thứ tự ID đăng ký tăng dần trả q+1, người còn lại q. Hiển thị minh bạch phần chênh 1đ.
- Phải thu được version hóa; không sửa âm thầm khi đã có thanh toán. Re-finalize cần lý do và tổng phải thu mới của mỗi người không thấp hơn tiền đã xác nhận; hoàn tiền vượt mức là giai đoạn sau, MVP báo cần xử lý trước.
- QR chỉ hỗ trợ chuyển khoản. Người chơi bấm đã chuyển là chờ xác nhận; host/thủ quỹ mới xác nhận đã thu. Không tạo khoản thu khi chỉ mở QR.
- Chi phí và khoản thu của buổi CLB tự liên kết sổ quỹ một lần khi được ghi nhận; không thêm giao dịch quỹ trùng bằng tay. Buổi độc lập có thu/chi riêng và không vào quỹ CLB.

## 6. Trải nghiệm và yêu cầu phi chức năng

- Mobile là chính; web phải mở link buổi trực tiếp và dùng được trên màn hình điện thoại. Kiểm tra Flutter web thực tế trước pilot.
- Mọi dữ liệu mạng có loading/error/empty; thao tác ghi có trạng thái đang gửi, chống bấm lặp và thông báo kết quả rõ.
- Trạng thái thành công chỉ hiển thị sau khi server xác nhận. Request timeout có thể đã ghi DB: thử lại với cùng idempotency key.
- Lưu dữ liệu vận hành ở server, không chỉ state màn hình. Mất mạng: hiển thị lỗi/dữ liệu gần nhất có nhãn; MVP không ghi offline tự đồng bộ.
- Phân quyền kiểm tra ở DB/API, không chỉ ẩn nút; số điện thoại, ngân hàng và tài chính không đi vào payload công khai, logs hoặc analytics.
- Danh sách phân trang, lọc theo ngày/CLB/trạng thái; không tải toàn bộ session lịch sử khi mở trang chủ.
- Sao lưu theo khả năng Supabase của dự án; ghi rõ quy trình phục hồi đã thử trước pilot. Chưa cam kết SLA khi chưa kiểm thử tải.

## 7. Sau MVP

BH-08 bổ sung gợi ý xoay tua từ người có mặt và lưu trạng thái trận; BH-09 bổ sung kèo giao lưu tự nguyện (nước/cầu) gắn với trận. Không gộp giao lưu với khoản phí/quỹ; không giữ tiền cược hoặc tự thu tiền theo thắng thua. Elo, giải đấu, lớp học, chat, ví, phí thành viên tháng, đặt sân trực tuyến và feed cộng đồng chưa thuộc MVP.

## 8. Pilot và đo lường

Đề xuất 3–5 host trong 4 tuần. Đo số host tạo buổi đầu và quay lại tuần sau, thời gian tổng hợp danh sách/chốt tiền trước và sau, tỷ lệ đăng ký qua link, số lần sửa tay và phản ánh. Mục tiêu thử nghiệm: ít nhất 3/5 host dùng 3 tuần liên tiếp, báo giảm việc tổng hợp; các ca kiểm tra quyền/slot/quỹ đều đạt. Chưa được ghi hoàn thành 100% chỉ vì có màn hình.

## 9. Những điều cần xác nhận khi tiếp cận host

Thu phí theo buổi hay tháng; số sân/người; cách đăng ký; thành viên/khách có phí khác nhau không; ai là thủ quỹ; quy tắc hủy và khách đến muộn; mong muốn thực tế với kèo độ. Quyết định mới phải cập nhật tài liệu liên quan trước khi code phần bị ảnh hưởng.

## 10. Quy tắc bổ sung từ review v1.1

- Public chỉ thấy projection thông tin buổi/sân; không đọc contacts, cờ thanh toán hoặc bảng người chơi gốc. Client không có direct write cho đăng ký/điểm danh/tiền/quyền. RPC trả trạng thái và kết quả thật, UI không suy ra thành công từ HTTP không lỗi hoặc UPDATE 0 hàng.
- Mỗi thay đổi input ảnh hưởng khoản phải thu tăng billing_input_version của buổi. Bản chốt phí chỉ được dùng khi source_version bằng phiên bản hiện tại. Khi lỗi thời, vẫn xem lịch sử/phí cũ có nhãn, nhưng không tạo QR, nộp/xác nhận thu tiền mặt/chuyển khoản hoặc complete trước khi chốt lại. Không xóa tiền đã xác nhận; outstanding cũ không được trình bày là số phải trả cuối cùng.
- Buổi miễn phí cũng phải có revision hợp lệ với charges 0; không bỏ qua quy tắc phiên bản bằng nút xác nhận miễn phí.
- Danh sách chờ không giữ slot. Host/cohost phát hành lời mời có hạn; người được mời chấp nhận rồi DB kiểm tra lại slot. Không được chấp nhận khi chưa được mời, lời mời hết hạn/thu hồi hoặc sai người. Khách không account được host ghi nhận sự đồng ý và chấp nhận thay, có audit; không biến host-added guest thành tài khoản giả.
- Deadline mời mặc định 30 phút, không vượt registration_deadline/starts_at. Nếu không còn cửa sổ hợp lệ, host dùng luồng thêm khách trực tiếp khi buổi in_progress, không kéo dài lời mời lặng lẽ.
- Mất mạng/quyền/schema thiếu phải hiện lỗi và retry; không coi lỗi là empty, không giữ spinner vô hạn. Cập nhật giao diện chỉ sau kết quả DB được xác nhận; retry giữ request_id.

## 11. Bổ sung nghiên cứu Vmito/Vụt ngày 15/10/2026

Nguồn là hai báo cáo phân tích tĩnh do chủ dự án cung cấp, không chứng minh hành vi runtime. [14_PRODUCT_LEARNINGS_VMITO_VUT.md](14_PRODUCT_LEARNINGS_VMITO_VUT.md) ghi rõ bằng chứng/giới hạn và quyết định PD-01..06.

Bổ sung cho ticket hiện có: link theo tài nguyên có login-return và validation (BH-04), lọc public theo khu vực/ngày-giờ/còn chỗ/fee mode với card rõ phí dự kiến (BH-04), đăng ký pending/confirmed/waitlist rõ ràng (BH-05), QR có fallback và xác nhận thủ công (BH-06), lịch sử/permission-denied/release tests (BH-07). Không mở rộng schema/migration hoặc triển khai feature trong lượt nghiên cứu.

MVP cho phép chọn khu vực và mở map link mà không xin GPS; hiển thị QR không cần camera; chưa thêm chat, audio, overlay, push provider hoặc bank webhook. Push opt-in là đề xuất BH-10 sau pilot, cần đặc tả riêng nếu được giao. Giữ host-first và ưu tiên đúng tiền/slot/quyền trước quy mô khám phá cộng đồng.
