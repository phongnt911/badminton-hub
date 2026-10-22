# Báo cáo bàn giao Kiểm chứng Browser / Offline / Reopen BH-07 Local

- **Trạng thái**: Chờ review độc lập
- **Nhánh**: `feat/bh07-browser-verification`
- **Base commit**: `8f9259e8dabf9b79088f9bb1eb9c9049d660eff5`
- **Mã nguồn ứng dụng**: Giữ nguyên toàn bộ source đã nghiệm thu, chỉ bổ sung công cụ / test / script kiểm chứng và tài liệu bằng chứng.
- **Trình duyệt kiểm thử**: Google Chrome 155.0.8059.85 (Headless CDP Automation)
- **Nền tảng backend**: Supabase local stack thật (GoTrue Auth, PostgREST RPC, PostgreSQL 15)

---

## 1. Kết quả ma trận kiểm chứng Browser (11/11 PASS)

| STT | Mã kiểm thử | Mô tả kiểm chứng | Kết quả | Chi tiết ghi nhận |
|:---:|:---|:---|:---:|:---|
| 01 | `browser.owner.login` | Đăng nhập Owner A qua Supabase GoTrue thật, session lưu vào `localStorage` | **PASS** | `authenticated user=ownera@example.test` |
| 02 | `browser.session.start-flow` | Tải buổi chơi đang diễn ra, hiển thị danh sách cầu thủ, điểm danh và điều khiển | **PASS** | `session=10000000-0000-4000-8000-000000000001` |
| 03 | `browser.finance.view-and-complete` | Chốt phí & kết thúc buổi với `p_expected_version` và `p_request_id`; retry cùng intent replay idempotent | **PASS** | Version `7 -> 8`, `lifecycle=completed`, `idempotentReplay=true` |
| 04 | `browser.summary.manager-finance-view` | Manager xem đầy đủ tổng kết chi phí; văn bản sao chép loại trừ toàn bộ SĐT/STK riêng tư | **PASS** | `expenses=300000`, `outstanding=250000`, `privacySafe=true` |
| 05 | `browser.history.manager-view` | Manager xem danh sách lịch sử buổi chơi kèm số liệu tài chính của CLB quản lý | **PASS** | Trả về 4 bản ghi lịch sử có số tiền |
| 06 | `browser.cohost.null-finances-privacy` | Cohost không có quyền tài chính chỉ thấy số lượng quản lý; các trường tiền là `null` (`—`) | **PASS** | `can_view_finance=false`, `expenses=null`, `outstanding=null` |
| 07 | `browser.participant.member-privacy-view` | Thành viên tham gia chỉ truy cập lịch sử cá nhân được phép, không xem sổ quỹ CLB | **PASS** | Cách ly dữ liệu thành viên, không rò rỉ thu/chi |
| 08 | `browser.offline.no-false-success` | Ngắt kết nối mạng mô phỏng lỗi transport chân thực; ứng dụng không báo thành công giả | **PASS** | Bắt lỗi transport `Failed to fetch`, không ghi nhận thành công giả |
| 09 | `browser.offline.retry-online` | Kết nối lại mạng, thử lại thành công bảo toàn intent và tham số `request_id` | **PASS** | Khôi phục mạng, HTTP status 200, retry trơn tru |
| 10 | `browser.reopen.refresh-session-persistence` | Tải lại trang (F5/reopen), khôi phục phiên sạch từ storage, không hỏng cache | **PASS** | Bảo toàn email `membera@example.test`, phiên hợp lệ |
| 11 | `browser.logout.cache-cleared-no-leak` | Đăng xuất làm sạch token xác thực và bộ nhớ đệm, không rò rỉ dữ liệu chéo | **PASS** | Toàn bộ auth tokens bị xóa, quay về trạng thái ẩn danh sạch |

---

## 2. Bằng chứng ảnh chụp màn hình (17 Screenshots)

Toàn bộ ảnh chụp thực tế trên Google Chrome 155 được lưu trữ tại `docs/reviews/bh07/browser_evidence/screenshots/`:

| Tên tệp | Mô tả bằng chứng trực quan |
|:---|:---|
| `01_owner_logged_in.png` | Màn hình sau khi Owner A đăng nhập thành công qua GoTrue Auth |
| `02_session_detail_owner.png` | Chi tiết buổi chơi đang diễn ra dưới quyền Owner A |
| `03_players_attendance.png` | Danh sách người tham gia và điểm danh thực tế |
| `04_session_finance_manager.png` | Giao diện tài chính buổi chơi trước khi kết thúc |
| `05_session_completed.png` | Trạng thái buổi chơi sau khi gọi RPC `complete_session` thành công |
| `06_summary_manager_full_finances.png` | Thẻ tổng kết buổi chơi hiển thị đầy đủ tổng chi phí và công nợ |
| `07_history_manager_view.png` | Danh sách lịch sử các buổi chơi của Manager |
| `08_history_filter_club.png` | Lọc danh sách lịch sử theo câu lạc bộ |
| `09_cohost_logged_in.png` | Đổi actor sang Cohost A (không có quyền thủ quỹ) |
| `10_summary_cohost_management_only.png` | Tổng kết dưới góc nhìn Cohost: số tiền hiển thị `—` (`null`), chỉ hiện số người |
| `11_history_cohost_view.png` | Lịch sử buổi chơi của Cohost không rò rỉ quỹ CLB |
| `12_participant_logged_in.png` | Đổi actor sang Member A (người tham gia thông thường) |
| `13_history_participant_view.png` | Lịch sử cá nhân cô lập của Member A |
| `14_network_offline_error.png` | Mất mạng đột ngột: app bắt lỗi transport, không báo thành công giả |
| `15_retry_online_success.png` | Có mạng trở lại: thử lại tác vụ thành công với cùng intent |
| `16_refresh_reopen_state.png` | Tải lại trang (F5): khôi phục chính xác trạng thái người dùng |
| `17_logout_cache_cleared.png` | Đăng xuất: xóa sạch cache và storage, an toàn cho người dùng tiếp theo |

---

## 3. Phân tích kỹ thuật chuyên sâu

### 3.1. Luồng nghiệp vụ cốt lõi (Start → Điểm danh → Chốt phí → Complete → Summary/History)
- Buổi chơi `10000000-0000-4000-8000-000000000001` đang ở trạng thái `in_progress` với 2 người có mặt và 1 khoản thu một phần (50.000 đ trên tổng 300.000 đ chi phí).
- Thao tác `complete_session` được gọi kèm `p_expected_version: 7` và `p_request_id`.
- Cơ chế bảo vệ đồng thời và chống lặp lệnh (idempotent replay) hoạt động chính xác: khi client gửi lại cùng `p_request_id` và cùng payload, server trả về kết quả đã lưu mà không gây lỗi xung đột phiên bản.
- Trạng thái buổi chuyển sang `completed`, `session_version` tăng từ 7 lên 8.

### 3.2. Phân quyền và Bảo mật thông tin riêng tư (Privacy)
- **Manager / Host**: Nhận dữ liệu tổng kết với đầy đủ các trường `expenses_total_vnd: 300000`, `outstanding_total_vnd: 250000`, `can_view_finance: true`. Văn bản sao chép tổng kết (copy text) được lọc sạch, không chứa số điện thoại cá nhân hay thông tin tài khoản ngân hàng.
- **Cohost (không có role finance)**: `can_view_finance: false`. Các trường `expenses_total_vnd` và `outstanding_total_vnd` nhận giá trị `null` (hiển thị trên giao diện là gạch ngang `—`).
- **Thành viên tham gia (Member)**: Được cô lập hoàn toàn, không thể xem thông tin thu chi của CLB.

### 3.3. Xử lý ngoại lệ mạng và Phục hồi (Offline / Retry / Reopen / Logout)
- Khi mô phỏng trạng thái ngoại tuyến (`setOffline(true)`), các yêu cầu mạng bị trình duyệt chặn và trả về lỗi transport chân thực (`Failed to fetch`). Ứng dụng xử lý lỗi và tuyệt đối **không báo thành công giả**.
- Khi có mạng trở lại, thao tác retry bảo toàn intent ban đầu.
- Khi tải lại trang (`Page.reload()`), phiên làm việc từ `localStorage` được nạp lại nguyên vẹn mà không gây lỗi sai lệch cache.
- Khi đăng xuất, toàn bộ khóa `sb-*-auth-token` và bộ nhớ đệm bị xóa sạch, ngăn chặn rò rỉ dữ liệu giữa các phiên đăng nhập.

---

## 4. Tuyên bố các mục KHÔNG THỰC HIỆN (NOT RUN)

Theo đúng quy định của dự án, các hạng mục sau **không nằm trong phạm vi kiểm chứng local** và được bảo lưu trạng thái **NOT RUN**:
1. **Thiết bị di động thật (iOS / Android)**: Chỉ kiểm chứng trên Google Chrome thật (Flutter Web).
2. **Cổng thanh toán ngân hàng / Webhook thật**: Không gọi API ngân hàng thật; chỉ kiểm tra qua mock RPC nội bộ.
3. **Môi trường Staging / Production**: Không can thiệp cơ sở dữ liệu trên cloud hay môi trường ngoài local.
4. **Rehearsal / Pilot thực tế**: Chưa nghiệm thu toàn diện BH-07 cho pilot.
