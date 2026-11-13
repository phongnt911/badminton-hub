# BH-07 V2 Web Copy & QR Fallback Handoff — 13/11/2026

**Trạng thái: SỬA VÒNG 2/3 — CHỜ CODEX CHẠY LẠI KIỂM CHỨNG VÀ REVIEW (`NOT RUN` cho bản sửa vòng 2/3). Các quan sát r1 từ lượt chạy trước được giữ nguyên (kể cả lỗi bootstrap lạnh ban đầu trên Edge `guest_qr`); chưa chạy lại runtime trên bản sửa vòng 2/3 và không tuyên bố full V2, xác minh ngân hàng/VietQR thật, luồng ghi thanh toán (V6) hoặc nghiệm thu toàn BH-07/V8.**

Tài liệu này bàn giao kịch bản Web read-only mới [web_copy_qr_scenario.js](../../../scripts/bh07_browser/web_copy_qr_scenario.js) để kiểm chứng tách biệt hai ca còn thiếu trên trình duyệt:
1. `cohost_copy`: Cohost xem tổng kết chỉ đếm số lượng và sao chép nội dung không lộ tài chính/liên hệ/người chơi.
2. `guest_qr`: Guest A (`guesta@example.test`, không phải `membera@example.test` đã trả đủ) mở phần phí còn nợ `100,000 VNĐ`, ép lỗi tải ảnh QR ngoài (`https://img.vietqr.io/**`) để kiểm tra fallback thủ công, thông báo không tự xác nhận và sao chép số tài khoản / nội dung chuyển khoản khi trình duyệt hỗ trợ cấp quyền clipboard.

Không chỉnh sửa `web_lifecycle_scenario.js`, mã nguồn app, backend, migration hay chạy lệnh trình duyệt/Docker trong lượt bàn giao này.

## 1. Quy tắc thay thế cấu hình cho Codex (chỉ trong driver copy bị ignore)

Không sửa trực tiếp thông số fixture nhạy cảm vào file tracked; Codex tạo các bản driver copy trong thư mục ignored (ví dụ `.build/`) rồi thay đúng hai hằng số ở đầu [web_copy_qr_scenario.js](../../../scripts/bh07_browser/web_copy_qr_scenario.js):

### Ca A — `cohost_copy`
- `const MODE = 'cohost_copy';`
- `const EXPECTED_RECEIVER = null;`

### Ca B — `guest_qr`
1. Trước khi chạy, root Codex đọc giá trị receiver và payment reference thực tế từ DB local cho buổi fixture `10000000-0000-4000-8000-000000000099` và tài khoản `guesta@example.test` (tránh `membera@example.test` vốn đã `outstanding = 0`).
2. Chỉ thay vào bản driver copy bị ignore (không ghi giá trị thô vào tracked docs, artifact hoặc error/log):
   - `const MODE = 'guest_qr';`
   - `const EXPECTED_RECEIVER = { bank_code: '<db_bank_code>', account_number: '<db_account_number>', account_name: '<db_account_name>', reference: '<db_reference>' };`
   - Cả 4 trường `bank_code`, `account_number`, `account_name`, `reference` đều bắt buộc là chuỗi không rỗng.

## 2. Cơ chế và điều kiện đạt của kịch bản

- **Guard & bootstrap sạch (cập nhật vòng 2/3):** Kiểm tra `BASE_URL` đúng `http://127.0.0.1:8088`, URL khởi đầu là `about:blank` hoặc cùng origin `http://127.0.0.1:8088`. Trong `bootstrapFreshGuestAndLogin`, sau khi mở `http://127.0.0.1:8088/#/` và xác nhận origin loopback, kịch bản lặp gọi `enableAccessibility()` theo chu kỳ poll ngắn (`400 ms`) với hạn mức cố định `20s` (lỗi timeout an toàn cố định `'Guest home bootstrap timed out waiting for visible "Tài Khoản" tab'`) cho đến khi tab gốc `Tài Khoản` hiển thị thực sự, tránh trường hợp `Promise.race` kích hoạt placeholder quá sớm trước khi Flutter hoàn tất dựng cây UI/semantics. Khi tab `Tài Khoản` đã hiển thị, luồng xác nhận trạng thái khách (`Bạn đang xem dưới dạng khách`) và đăng nhập qua UI thật giữ nguyên một lượt (không retry đăng nhập hay mutation; không chèn token/API/state).
- **Quyền clipboard thật:** Đặt `permissionsAttempted = true` **trước** khi gọi `context.grantPermissions(['clipboard-read', 'clipboard-write'], { origin: 'http://127.0.0.1:8088' })`.
  - Chỉ báo `clipboard.status = 'NOT_RUN'` (với lý do cố định và các cờ xác minh clipboard ở `false`) khi lỗi khớp đúng thông báo Playwright không hỗ trợ quyền clipboard: `Unknown permission: clipboard-read` hoặc `Unknown permission: clipboard-write` (có thể có dấu nháy đơn hoặc nháy kép). Tuyệt đối không giả lập passed hay tự ghi clipboard.
  - Mọi lỗi cấp quyền bất ngờ khác (như đóng trình duyệt/context, timeout, permission denied) đều ném `Error('Clipboard permission grant failed unexpectedly')` cố định, không chuyển thành `NOT_RUN` và không rò rỉ thông báo lỗi thô.
  - Nếu grant thành công: click nút sao chép thật trên UI, chờ snackbar xác nhận của Flutter, đọc lại bằng `navigator.clipboard.readText()` qua `page.evaluate`. Mọi lỗi đọc clipboard hoặc lệch nội dung đều **FAIL** ngay (không bắt lỗi thành skip).
- **`cohost_copy`:** Đăng nhập `cohosta@example.test`, mở `UI Flow Session published to complete` → `Tổng kết buổi`. Xác nhận `Chỉ xem số lượng`, số đếm `2/0/2`, vắng nhóm `Tài chính tổng hợp` và các nhãn/số tiền `200,000`/`100,000`/`VNĐ`/`VND`. Nếu clipboard được cấp quyền: click `Sao chép tổng kết`, chờ snackbar `Đã sao chép tổng kết buổi.`, kiểm tra clipboard chứa đúng tiêu đề buổi và đạt `hasExactCohostCounts(copiedText)` (khớp chính xác dòng/kết thúc dòng `👥 Có mặt: 2 · Vắng: 0 · Đã xác nhận: 2`, từ chối mọi chữ số dư sau số `2` cuối như `20`/`23`/`200`), đồng thời từ chối mọi `VNĐ`/`VND`, nhãn tài chính, trường ngân hàng, thông tin liên hệ và tên `Member A` / `Guest A`.
- **`guest_qr`:** Đăng nhập `guesta@example.test`, đăng ký route chặn **duy nhất** `https://img.vietqr.io/**` (`route.abort()` và tăng bộ đếm, giữ nguyên toàn bộ local API). Mở buổi fixture, xác nhận vắng `Tổng kết buổi` và `Tài chính & thu tiền`, mở `Phần phí của tôi`. Xác nhận `Phải trả 100,000 VNĐ`, `Đã trả 0 VNĐ`, `Còn lại 100,000 VNĐ`, thông báo fallback chính xác `Không tải được ảnh QR. Dùng thông tin bên dưới để chuyển khoản.`, `route_abort_count >= 1`, đủ 5 trường thủ công `Ngân hàng`/`Số tài khoản`/`Chủ tài khoản`/`Số tiền`/`Nội dung` khớp `EXPECTED_RECEIVER`, và thông báo `Mã QR chỉ là hướng dẫn chuyển khoản, KHÔNG tự xác nhận đã thu. Ban quản lý xác nhận thủ công sau khi nhận tiền.`. **Tuyệt đối không click `Tôi đã chuyển khoản`.** Nếu clipboard được cấp quyền: click `Sao chép Số tài khoản` → chờ snackbar `Đã sao chép Số tài khoản` → `readText()` khớp chính xác `EXPECTED_RECEIVER.account_number`; click `Sao chép Nội dung` → chờ snackbar `Đã sao chép Nội dung` → `readText()` khớp chính xác `EXPECTED_RECEIVER.reference`.
- **Dọn dẹp & đầu ra an toàn:** `finally` luôn gọi `context.setOffline(false)`, gọi `context.clearPermissions()` cho mọi lần đã thử cấp quyền (`permissionsAttempted === true`, kể cả khi cấp quyền không được hỗ trợ hoặc lỗi một phần), gỡ đúng handler `https://img.vietqr.io/**` đã đăng ký và gỡ listener `console`/`pageerror`, không nuốt lỗi dọn dẹp. Chỉ trả về boolean, số đếm và trạng thái; không áp dụng ngưỡng cứng `error_count === 0` vì ảnh VietQR bị chủ động abort. Không trả về raw snapshot, clipboard, chuỗi ngân hàng/reference, hash số tài khoản dễ vét cạn, token hay mật khẩu.

## 3. Lệnh chạy gợi ý cho Codex (`playwright-cli` với `--filename`)

Mỗi ca chạy trên một **fresh guest named session** riêng (`open about:blank` → `run-code --filename=...` → `close`) với bản driver copy trong thư mục ignored (ví dụ `.build/`):

### Edge (có hỗ trợ grant clipboard)

```powershell
playwright-cli -s=bh07-edge-cohost-copy open about:blank --browser=msedge
playwright-cli -s=bh07-edge-cohost-copy run-code --filename=.build/web_copy_cohost_driver.js
playwright-cli -s=bh07-edge-cohost-copy close

playwright-cli -s=bh07-edge-guest-qr open about:blank --browser=msedge
playwright-cli -s=bh07-edge-guest-qr run-code --filename=.build/web_qr_guest_driver.js
playwright-cli -s=bh07-edge-guest-qr close
```

### Firefox (headless hoặc software WebRender headed — lưu ý clipboard grant không hỗ trợ → `NOT_RUN`)

```powershell
playwright-cli -s=bh07-ff-cohost-copy open about:blank --browser=firefox
playwright-cli -s=bh07-ff-cohost-copy run-code --filename=.build/web_copy_cohost_driver.js
playwright-cli -s=bh07-ff-cohost-copy close

playwright-cli -s=bh07-ff-guest-qr open about:blank --browser=firefox
playwright-cli -s=bh07-ff-guest-qr run-code --filename=.build/web_qr_guest_driver.js
playwright-cli -s=bh07-ff-guest-qr close
```

*(Đối chứng âm khuyến nghị: thay một ký tự trong `EXPECTED_RECEIVER.account_number` hoặc `EXPECTED_RECEIVER.reference` trên driver copy ignored của `guest_qr` để xác nhận kịch bản FAIL đóng cả ở kiểm tra UI semantics lẫn kiểm tra clipboard.)*

## 4. Kết quả đo r1 đã ghi nhận (giữ nguyên để truy vết trước runtime r2)

- **Edge `cohost_copy` (r1):** PASS UI chỉ đếm số lượng và clipboard thật.
- **Edge `guest_qr` (r1 — lần chuẩn bị lạnh đầu tiên):** **FAIL** tại `accountTab.waitFor({ state: 'visible', timeout: 15000 })` do `enableAccessibility()` ban đầu race sớm trên placeholder trước khi UI Flutter sẵn sàng; snapshot tường minh sau đó xác nhận màn hình Guest home bình thường. Lỗi bootstrap ban đầu này được giữ nguyên trong hồ sơ.
- **Edge `guest_qr` (r1 — chạy lại trên cùng trạng thái Guest Auth sạch sau khi semantics sẵn sàng):** **PASS** toàn bộ: ép fallback QR khi chặn `https://img.vietqr.io/**`, khớp thông tin thủ công từ DB, đối chiếu phí `100,000 / 0 / 100,000` VNĐ và clipboard thật cho Số tài khoản / Nội dung chuyển khoản; không có thao tác ghi tài chính.
- **Firefox headless `cohost_copy` (r1):** PASS phần UI Cohost; quyền clipboard được nhận diện là không hỗ trợ và trả `NOT_RUN` đúng thiết kế.

## 5. Giới hạn và không tuyên bố ngoài phạm vi

- **Trạng thái hiện tại:** **CHỜ CHẠY RUNTIME VÒNG 2/3 (`NOT RUN` trên bản sửa r2)**. Bản sửa vòng 2/3 chỉ bổ sung vòng lặp kích hoạt `enableAccessibility()` trong `bootstrapFreshGuestAndLogin` cho đến khi tab gốc `Tài Khoản` hiển thị (deadline `20s`, poll `400 ms`), giữ nguyên quyền, bộ đếm, oracle, QR regex, dọn dẹp và không chỉnh sửa `web_lifecycle_scenario.js`, mã nguồn app hay backend.
- Kịch bản này là kiểm thử **read-only**: không nhấn `Tôi đã chuyển khoản`, không tạo payment intent, không thử xác nhận thu tiền của Owner hay kiểm tra bảng `payments`/`payment_ledger` (thuộc V6 / write workflow).
- Việc chặn `https://img.vietqr.io/**` chỉ kiểm tra đường fallback khi ảnh QR không tải được và đối chiếu dữ liệu hiển thị/sao chép với DB local; không chứng minh kết nối VietQR live, chuyển khoản ngân hàng thật, full V2 (như Firefox `guest_qr`, Safari/macOS, mobile native, Firefox headed mặc định) hoặc nghiệm thu BH-07/V8. Toàn bộ V2 và BH-07/V8 vẫn chưa nghiệm thu.
