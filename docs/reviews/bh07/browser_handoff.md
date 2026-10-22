# Báo cáo bàn giao Kiểm chứng Browser / Offline / Reopen BH-07 Local (Vòng 2/2)

- **Trạng thái**: Chờ review độc lập (Vòng 2/2)
- **Nhánh**: `feat/bh07-browser-verification`
- **Base commit**: `465b46607c8fd5d1566e7eca8688af09fc557e34`
- **Tested source commit**: `51cb3b124533ecc4abce00609a5f0bbbd6309221`
- **Mã nguồn ứng dụng**: Giữ nguyên toàn bộ 100% source app (`lib/`, `test/`), DB migrations, RPC và contracts; chỉ cập nhật công cụ/test kiểm chứng, fixture và tài liệu bằng chứng.
- **Trình duyệt kiểm thử**: Google Chrome 155.0.8059.85 (Headless CDP Automation với thao tác chuột, bàn phím và cây ngữ nghĩa Semantics thật)
- **Nền tảng backend**: Supabase local stack thật (GoTrue Auth, PostgREST RPC, PostgreSQL 15 trên Docker `supabase_db_badminton-hub`)

---

## 1. Khắc phục triệt để 5 phát hiện Review Độc lập Vòng 1/2 (BR1 – BR5)

| Mã | Mức | Phát hiện trong `review_b00b580.md` | Giải pháp và kết quả khắc phục vòng 2/2 | Trạng thái |
|:---|:---:|:---|:---|:---:|
| **BR1** | **P2** | Điểm danh PASS chỉ vì click xong; không assert đúng player/attendance/count sau mutation. | Kiểm tra tiền đề (`not_checked_in`), click UI "Có mặt" đúng thành viên `Member A`, assert hậu đề hiển thị `present` ("Có mặt"), đối chiếu trực tiếp cơ sở dữ liệu `session_players` chuyển sang `present` và `checked_in_at` có giá trị. | **Đã sửa** |
| **BR2** | **P1** | Lọc POST bị trộn lẫn OPTIONS; thiếu request vẫn PASS; payload match bỏ qua version; không assert transport error khi offline, completed khi online và side effects 1 lần. | Bổ sung bộ lọc POST nghiêm ngặt (`req.method === 'POST'`), bắt buộc có đủ 2 request (1 offline, 1 online retry); so khớp sâu `p_request_id` và toàn bộ payload (bao gồm cả `p_expected_version`); assert lỗi transport offline không có false success; sau khi online assert session chuyển `completed`, version tăng lên 3, `operation_requests` đếm đúng 1 và `audit_events` với action `SESSION_COMPLETED` đếm đúng 1. | **Đã sửa** |
| **BR3** | **P2** | Clipboard validator còn lọt số tiền sai / zero giả; Cohost chỉ cấm 2 nhãn; History filter không thao tác dropdown chọn CLB và không assert IDs. | Fixture được bổ sung chi phí sân 200.000 VNĐ để tránh zero giả; Manager clipboard assert chính xác các dòng tài chính (`200,000 VNĐ`) và quét sạch SĐT/STK/secrets; Cohost assert thẻ "Chỉ xem số lượng", ẩn hoàn toàn thẻ tài chính, clipboard bị chặn toàn diện bằng regex tiền tệ, SĐT, STK; History thao tác mở dropdown chọn CLB A thật qua UI, assert xuất hiện buổi của CLB A và loại trừ hoàn toàn các buổi của CLB B; Member A cách ly lịch sử cá nhân. | **Đã sửa** |
| **BR4** | **P2** | Chưa kiểm cache đổi actor trong cùng instance vì `Page.navigate` / reload reset toàn bộ app trước assertion. | Chuyển đổi actor từ Owner sang Cohost hoàn toàn trong **CÙNG 1 document/instance SPA** bằng các nút Back (`clickBack`) trên AppBar và tab bar navigation của Flutter Web (không gọi `Page.navigate` hay reload trang); sau khi đăng nhập Cohost, assert thẻ tài chính của Owner bị xóa sạch khỏi view/cache và clipboard Cohost không còn số tiền nào; duy trì ca reload (F5) riêng ở TC10 để kiểm tra session persistence. | **Đã sửa** |
| **BR5** | **P2** | Thiếu 4 file log gốc; `clean_and_manifest.py` tự ý ghi đè manifest bằng file hiện có xóa dấu vết thiếu file; scanner lọt secret giả `sb_secret_`; exits hardcode. | Xuất bản đầy đủ 4 file log gốc (`analyze.log`, `flutter_test.log`, `bh07_db_runner.log`, `browser_runner.log`) bằng `git add -f`; tách biệt script thành 2 mode rõ ràng: `--generate` (chuẩn hóa LF, tính hash) và `--verify` (readonly, kiểm tra tính toàn vẹn, secret, exit khác 0 nếu thiếu file/hash sai, KHÔNG sửa file); scanner bao phủ `sb_secret_` và JWT service role; đo lường exit code thực tế từ process; ghi nhận SHA, dirty status (`false`), source hashes; bổ sung kịch bản `run_negative_controls.js` tái lập 8/8 probes của reviewer (đỏ trước sửa, xanh sau sửa). | **Đã sửa** |

---

## 2. Kết quả Ma trận Kiểm chứng Trình duyệt Thật (11/11 PASS)

Runner tự động thực thi 11 kịch bản tương tác UI thực tế trên Google Chrome 155 thật qua CDP:

| STT | Mã kiểm thử | Mô tả kịch bản UI thật | Kết quả | Chi tiết ghi nhận |
|:---:|:---|:---|:---:|:---|
| 01 | `browser.ui.login-owner` | Owner A đăng nhập qua form UI (`AuthScreen`), nhập email/pass, xác nhận badge đã xác thực trên `AccountScreen` | **PASS** | auth form submitted, verified badge present, guest mode cleared |
| 02 | `browser.ui.start-session` | Owner A mở buổi chơi đã công bố (`published`), click nút "Bắt đầu buổi chơi", chuyển lifecycle sang "Đang diễn ra" | **PASS** | lifecycle updated to `in_progress` |
| 03 | `browser.ui.attendance-checkin` | Điểm danh Member A qua nút bấm "Có mặt": assert precondition `not_checked_in`, click UI, assert postcondition `present` và kiểm DB | **PASS** | Member A attendance status successfully updated from not_checked_in to present |
| 04 | `browser.ui.finalize-charges` | Mở màn tài chính, bấm nút "Chốt phí", nhập lý do trong dialog, chuyển trạng thái phí sang "Đang hiệu lực" (`current`) | **PASS** | billing state is now current (Đang hiệu lực) |
| 05 | `browser.mutation.offline-retry-intent` | Mô phỏng offline: bấm "Kết thúc buổi chơi" trong dialog, bắt lỗi transport, UI không báo thành công giả; bật online và retry thành công | **PASS** | captured=2 reqIdMatch=true payloadMatch=true exactly_once_verified |
| 06 | `browser.clipboard.manager-privacy` | Mở màn "Tổng kết buổi", bấm "Sao chép tổng kết", đọc clipboard thật: xác nhận tổng tiền 200,000 VNĐ, sạch SĐT/STK/secrets | **PASS** | real clipboard read successfully, privacy clean (no phone/bank), finance totals present and verified >0 |
| 07 | `browser.cohost.null-finance-ui` | Điều hướng bằng UI trong cùng document SPA, đăng nhập Cohost A: xem tổng kết có thẻ "Chỉ xem số lượng", ẩn thẻ tài chính, clipboard không số tiền | **PASS** | management only card verified, finance card hidden, clipboard money fields clean in same document instance |
| 08 | `browser.history.ui-filter-club` | Mở tab "Buổi Chơi", mở lịch sử buổi, thao tác dropdown chọn HTTP Club A: assert xuất hiện buổi CLB A, loại trừ buổi CLB B | **PASS** | history screen filtered by HTTP Club A: Club A sessions present, Club B sessions excluded |
| 09 | `browser.participant.member-isolation-ui` | Đăng xuất qua UI, đăng nhập Member A: mở lịch sử cá nhân cô lập, không rò rỉ thông tin quỹ hay tài chính CLB | **PASS** | member history rendered in isolation, no club treasury leak |
| 10 | `browser.reopen.session-persistence-ui` | Tải lại trang (F5/reload) khi đang là Member A, xác nhận phiên đăng nhập được khôi phục nguyên vẹn từ storage | **PASS** | `membera@example.test` session preserved across reload |
| 11 | `browser.logout.cache-cleared-no-leak` | Bấm "Đăng xuất" qua UI, xác nhận dialog: UI lập tức trở về khách, `localStorage` bị xóa sạch toàn bộ auth tokens | **PASS** | guest view restored, storage tokens purged completely |

---

## 3. Danh mục 12 Ảnh Chụp Màn Hình Thật (Screenshots)

Toàn bộ ảnh chụp thực tế được lưu tại `docs/reviews/bh07/browser_evidence/screenshots/`, phản ánh đúng từng bước nghiệp vụ và kích thước thực tế:

| Tên tệp ảnh | Kích thước | Mô tả bằng chứng trực quan |
|:---|:---:|:---|
| `01_owner_ui_authenticated.png` | 33,985 B | Owner A đăng nhập thành công qua form UI, màn hình hồ sơ đã xác thực |
| `02_session_ui_started.png` | 82,010 B | Buổi chơi chuyển sang trạng thái "Đang diễn ra" sau khi bấm nút "Bắt đầu buổi chơi" |
| `03_player_attendance_checked.png` | 81,000 B | Điểm danh Member A thành công qua nút bấm trên UI, badge hiển thị "Có mặt" |
| `04_session_finance_finalized.png` | 58,348 B | Chốt phí thành công qua dialog, chip trạng thái hiển thị "Đang hiệu lực" |
| `05_offline_mutation_error.png` | 59,766 B | Lỗi transport khi ngắt mạng: app bắt lỗi chính xác, không báo thành công giả |
| `06_retry_mutation_success.png` | 81,288 B | Kết nối mạng trở lại và retry: buổi chơi kết thúc thành công (lifecycle `completed`) |
| `07_summary_manager_clipboard.png` | 59,831 B | Màn hình tổng kết của Manager: đầy đủ tài chính (200k), sạch thông tin riêng tư |
| `08_cohost_summary_null_finances.png` | 50,253 B | Góc nhìn Cohost trong cùng SPA instance: thẻ "Chỉ xem số lượng", không thẻ tài chính, clipboard không số tiền |
| `09_history_filtered_club.png` | 35,123 B | Màn hình lịch sử lọc theo HTTP Club A thật qua dropdown, buổi của CLB A xuất hiện |
| `10_member_isolated_history.png` | 24,043 B | Lịch sử cá nhân cách ly của người chơi Member A |
| `11_reopen_persisted_session.png` | 34,281 B | Tải lại trang (F5): khôi phục chính xác trạng thái đã đăng nhập của Member A |
| `12_logout_clean_guest_state.png` | 35,290 B | Đăng xuất qua UI: quay về màn hình khách, storage token bị xóa sạch hoàn toàn |

---

## 4. Đo lường Mã Thoát Thực tế (Exit Codes)

Tất cả các lệnh kiểm tra được đo lường thực tế từ process và ghi nhận trong `docs/reviews/bh07/browser_evidence/exits.json`:

```json
{
  "web_build": 0,
  "db_reset": 0,
  "seed_setup": 0,
  "browser_matrix": 0,
  "flutter_analyze": 0,
  "flutter_test": 0,
  "bh07_db_runner": 0,
  "negative_controls": 0
}
```

- `flutter analyze`: `No issues found! (ran in 1.1s)` → Exit 0 (lưu tại `analyze.log`).
- `flutter test`: `240 passed, 1 skipped` → Exit 0 (lưu tại `flutter_test.log`).
- `python -u docs/reviews/bh07/run_bh07_tests.py`: `TỔNG 23 | PASS 23 | FAIL 0` → Exit 0 (lưu tại `bh07_db_runner.log`).
- `node scripts/bh07_browser/run_browser_verification.js`: `11/11 PASS` → Exit 0 (lưu tại `browser_runner.log`).
- `node scripts/bh07_browser/run_negative_controls.js`: `8/8 negative controls properly rejected` → Exit 0.

---

## 5. Tuyên bố các mục KHÔNG THỰC HIỆN (NOT RUN)

Theo đúng quy định của dự án, các hạng mục sau **không nằm trong phạm vi kiểm chứng local** và được bảo lưu trạng thái **NOT RUN**:
1. **Thiết bị di động thật (iOS / Android)**: Chỉ kiểm chứng trên Google Chrome thật (Flutter Web qua CDP).
2. **Cổng thanh toán ngân hàng / Webhook thật**: Không gọi API ngân hàng thật; chỉ kiểm tra qua mock RPC nội bộ.
3. **Môi trường Staging / Production**: Không can thiệp cơ sở dữ liệu trên cloud hay môi trường ngoài local.
4. **Rehearsal / Pilot thực tế**: Chưa nghiệm thu toàn diện BH-07 cho pilot.
