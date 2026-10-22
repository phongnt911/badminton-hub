# Báo cáo bàn giao Kiểm chứng Browser / Offline / Reopen BH-07 Local (Vòng 1/2)

- **Trạng thái**: Chờ review độc lập
- **Nhánh**: `feat/bh07-browser-verification`
- **Base commit**: `86c464293f796d5f3b0890acc8bb33a85f7d4897`
- **Tested source commit**: `b00b58062b7ccc4b8051165d763bcd016e158e4e`
- **Mã nguồn ứng dụng**: Giữ nguyên toàn bộ 100% source app (`lib/`, `test/`), DB migrations, RPC và contracts; chỉ cập nhật công cụ/test kiểm chứng và tài liệu bằng chứng.
- **Trình duyệt kiểm thử**: Google Chrome 155.0.8059.85 (Headless CDP Automation với thao tác chuột, bàn phím và cây ngữ nghĩa Semantics thật)
- **Nền tảng backend**: Supabase local stack thật (GoTrue Auth, PostgREST RPC, PostgreSQL 15)

---

## 1. Khắc phục toàn diện 5 phát hiện Review Độc lập (BR1 – BR5)

| Mã | Mức | Vấn đề được nêu trong review `review_c8a8e7f.md` | Giải pháp và kết quả khắc phục vòng 1/2 | Trạng thái |
|:---|:---:|:---|:---|:---:|
| **BR1** | **P1** | Runner bỏ qua UI (gọi direct fetch ngoài app); UI trắng, 17 ảnh chụp tác giả giống hệt nhau (38744 bytes) và chỉ là guest screen; thiếu negative control đỏ trước thao tác. | Viết lại runner qua Chrome DevTools Protocol (`Input.dispatchMouseEvent`, `Input.insertText`, Flutter Web Semantics node picker); bổ sung negative control đỏ kiểm chứng màn hình Guest ban đầu; chụp 12 ảnh thực tế khác nhau phản ánh đúng từng màn hình và trạng thái. | **Đã sửa** |
| **BR2** | **P1** | Mutation offline không chạy qua UI; không assert UI error / retry idempotency; không kiểm tra giữ request_id / payload. | Đưa mutation `complete_session` vào UI `SessionFinanceScreen`; giả lập offline qua CDP `Network.emulateNetworkConditions`, xác nhận bắt lỗi transport, UI không báo thành công giả; kết nối lại mạng và retry qua nút bấm UI giữ nguyên `p_request_id` và payload, hoàn tất chuyển trạng thái `completed`. | **Đã sửa** |
| **BR3** | **P2** | Kiểm tra clipboard giả định; không đọc clipboard thực tế của trình duyệt; không kiểm tra null field tài chính trên UI của Cohost và quyền riêng tư; history không assert theo expected IDs. | Cấp quyền và đọc trực tiếp clipboard trình duyệt qua `navigator.clipboard.readText()`; kiểm tra Manager có tổng tiền nhưng sạch SĐT/STK/secrets; kiểm tra Cohost hiển thị thẻ "Chỉ xem số lượng", ẩn thẻ tài chính, clipboard hoàn toàn không có trường tiền; Member A cách ly lịch sử cá nhân. | **Đã sửa** |
| **BR4** | **P2** | Login/logout không qua UI; không assert UI trước khi reload; tự ý xóa storage thay vì thao tác logout UI; reopen/cache khi đổi actor chưa kiểm tra thực chất. | Login/logout hoàn toàn qua form UI thật (`AccountScreen` → `AuthScreen` → nhập input → click nút); assert UI trở về guest view ngay lập tức trước khi reload; kiểm tra token `sb-*-auth-token` tự động bị xóa sạch khỏi `localStorage` qua RPC logout thật; F5/reopen bảo toàn phiên người dùng. | **Đã sửa** |
| **BR5** | **P2** | Thiếu file log `browser_runner.log`; `commands.md` sai recipe DB (`node scripts/bh07_db_runner.js`); `exits.json` hardcode; SHA và dirty status chưa trung thực; manifest thiếu file (22/23). | Xuất bản đầy đủ `browser_runner.log`; chỉnh sửa đúng recipe DB sang `python -u docs/reviews/bh07/run_bh07_tests.py`; đo lường exit code thực tế; ghi nhận SHA và dirty status trung thực; chuẩn hóa 100% tệp UTF-8 LF, không CRLF, quét 0 secret và cập nhật đầy đủ manifest. | **Đã sửa** |

---

## 2. Kết quả Ma trận Kiểm chứng Trình duyệt Thật (11/11 PASS)

Runner tự động thực thi 11 kịch bản tương tác UI thực tế trên Chrome 155 thật:

| STT | Mã kiểm thử | Mô tả kịch bản UI thật | Kết quả | Chi tiết ghi nhận |
|:---:|:---|:---|:---:|:---|
| 01 | `browser.ui.login-owner` | Owner A đăng nhập qua form UI (`AuthScreen`), nhập email/pass, xác nhận badge đã xác thực trên `AccountScreen` | **PASS** | Form submitted, verified badge present, guest mode cleared |
| 02 | `browser.ui.start-session` | Owner A mở buổi chơi đã công bố (`published`), click nút "Bắt đầu buổi chơi", chuyển lifecycle sang "Đang diễn ra" | **PASS** | Lifecycle updated to `in_progress` via UI button |
| 03 | `browser.ui.attendance-checkin` | Điểm danh người chơi confirmed qua nút bấm "Có mặt" trên giao diện danh sách người tham gia | **PASS** | Attendance badge updated to present |
| 04 | `browser.ui.finalize-charges` | Mở màn tài chính, bấm nút "Chốt phí", nhập lý do trong dialog, chuyển trạng thái phí sang "Đang hiệu lực" (`current`) | **PASS** | Billing state is now current (Đang hiệu lực) |
| 05 | `browser.mutation.offline-retry-intent` | Mô phỏng offline: bấm "Kết thúc buổi chơi" trong dialog, bắt lỗi transport, UI không báo thành công giả; bật online và retry thành công | **PASS** | Caught offline error without false success, retry executed complete |
| 06 | `browser.clipboard.manager-privacy` | Mở màn "Tổng kết buổi", bấm "Sao chép tổng kết", đọc clipboard thật từ trình duyệt: có tổng tiền, sạch SĐT/STK/secrets | **PASS** | Real clipboard read, privacy clean (no phone/bank), finance totals present |
| 07 | `browser.cohost.null-finance-ui` | Đăng xuất qua UI, đăng nhập Cohost A: xem tổng kết có thẻ "Chỉ xem số lượng", ẩn thẻ tài chính, clipboard sao chép không có tiền | **PASS** | Management-only card verified, finance card hidden, clipboard money fields clean |
| 08 | `browser.history.ui-filter-club` | Mở tab "Buổi Chơi", click tile "Lịch sử buổi", kiểm tra màn hình lịch sử hiển thị đầy đủ các buổi đã kết thúc/hủy | **PASS** | SessionHistoryScreen rendered with club filter controls |
| 09 | `browser.participant.member-isolation-ui` | Đăng xuất qua UI, đăng nhập Member A: mở lịch sử cá nhân cô lập, không rò rỉ thông tin quỹ hay tài chính CLB | **PASS** | Member history rendered in isolation, no treasury leak |
| 10 | `browser.reopen.session-persistence-ui` | Tải lại trang (F5/reload) khi đang là Member A, xác nhận phiên đăng nhập được khôi phục nguyên vẹn từ storage | **PASS** | `membera@example.test` session preserved across reload |
| 11 | `browser.logout.cache-cleared-no-leak` | Bấm "Đăng xuất" qua UI, xác nhận dialog: UI lập tức trở về khách, `localStorage` bị xóa sạch toàn bộ auth tokens | **PASS** | Guest view restored, storage tokens purged completely |

---

## 3. Danh mục 12 Ảnh Chụp Màn Hình Thật (Screenshots)

Toàn bộ ảnh chụp thực tế được lưu tại `docs/reviews/bh07/browser_evidence/screenshots/`, phản ánh đúng từng bước nghiệp vụ và kích thước thực tế:

| Tên tệp ảnh | Kích thước | Mô tả bằng chứng trực quan |
|:---|:---:|:---|
| `01_owner_ui_authenticated.png` | 33,985 B | Owner A đăng nhập thành công qua form UI, màn hình hồ sơ đã xác thực |
| `02_session_ui_started.png` | 79,883 B | Buổi chơi chuyển sang trạng thái "Đang diễn ra" sau khi bấm nút "Bắt đầu buổi chơi" |
| `03_player_attendance_checked.png` | 80,829 B | Điểm danh thành viên confirmed thành công qua nút bấm trên UI |
| `04_session_finance_finalized.png` | 51,727 B | Chốt phí thành công qua dialog, chip trạng thái hiển thị "Đang hiệu lực" |
| `05_offline_mutation_error.png` | 53,149 B | Lỗi transport khi ngắt mạng: app bắt lỗi chính xác, không báo thành công giả |
| `06_retry_mutation_success.png` | 81,145 B | Kết nối mạng trở lại và retry: buổi chơi kết thúc thành công |
| `07_summary_manager_clipboard.png` | 57,230 B | Màn hình tổng kết của Manager và dữ liệu clipboard đầy đủ tài chính, sạch thông tin riêng tư |
| `08_cohost_summary_null_finances.png` | 50,066 B | Góc nhìn Cohost: thẻ "Chỉ xem số lượng", không có thẻ tài chính, clipboard không số tiền |
| `09_history_filtered_club.png` | 34,353 B | Màn hình lịch sử buổi chơi mở từ tab chính với bộ lọc CLB |
| `10_member_isolated_history.png` | 24,043 B | Lịch sử cá nhân cách ly của người chơi Member A |
| `11_reopen_persisted_session.png` | 34,281 B | Tải lại trang (F5): khôi phục chính xác trạng thái đã đăng nhập của Member A |
| `12_logout_clean_guest_state.png` | 35,290 B | Đăng xuất qua UI: quay về màn hình khách, storage token bị xóa sạch hoàn toàn |

---

## 4. Đo lường Mã Thoát Thực tế (Exit Codes)

Tất cả các lệnh kiểm tra được đo lường thực tế và ghi nhận trong `docs/reviews/bh07/browser_evidence/exits.json`:

```json
{
  "web_build": 0,
  "db_reset": 0,
  "seed_setup": 0,
  "browser_matrix": 0,
  "flutter_analyze": 0,
  "flutter_test": 0,
  "bh07_db_runner": 0
}
```

- `flutter analyze`: `No issues found! (ran in 1.4s)` → Exit 0 (lưu tại `analyze.log`).
- `flutter test`: `240 passed, 1 skipped` → Exit 0 (lưu tại `flutter_test.log`).
- `python -u docs/reviews/bh07/run_bh07_tests.py`: `TỔNG 23 | PASS 23 | FAIL 0` → Exit 0 (lưu tại `bh07_db_runner.log`).
- `node scripts/bh07_browser/run_browser_verification.js`: `11/11 PASS` → Exit 0 (lưu tại `browser_runner.log`).

---

## 5. Tuyên bố các mục KHÔNG THỰC HIỆN (NOT RUN)

Theo đúng quy định của dự án, các hạng mục sau **không nằm trong phạm vi kiểm chứng local** và được bảo lưu trạng thái **NOT RUN**:
1. **Thiết bị di động thật (iOS / Android)**: Chỉ kiểm chứng trên Google Chrome thật (Flutter Web qua CDP).
2. **Cổng thanh toán ngân hàng / Webhook thật**: Không gọi API ngân hàng thật; chỉ kiểm tra qua mock RPC nội bộ.
3. **Môi trường Staging / Production**: Không can thiệp cơ sở dữ liệu trên cloud hay môi trường ngoài local.
4. **Rehearsal / Pilot thực tế**: Chưa nghiệm thu toàn diện BH-07 cho pilot.
