# BH-07 V2 Web Write/Offline-Retry Lifecycle Handoff — 13/11/2026

**Trạng thái (Correction 3/3 — r3): Chờ kiểm thử runtime trên Firefox (`r3` `NOT_RUN`). Trong lượt chạy `r2` do Codex thực hiện, Edge đã đạt COMPLETE PASS (gồm đủ `prepare_offline`, `retry_online`, cổng DB/audit `0 -> 1`, khớp payload/body, giữ nguyên `performance.timeOrigin` và dọn fixture), nhưng Firefox headed software WebRender cold first load `FAIL` ở bước bootstrap trong ~4s (`Navigation failed: neither "Tài Khoản" tab nor "Back" button is visible` tại `performOwnerLogin -> navigateBackToMain`) khi tiêu đề trang ban đầu còn là `badminton_hub` trước khi semantics màn hình Guest home sẵn sàng (snapshot bổ sung do Codex lấy sau đó cho thấy màn hình Guest home bình thường với đầy đủ các tab gồm `Tài Khoản` và tiêu đề `Badminton Nha Trang Hub`; chưa có mutation nào xảy ra và fixture vẫn ở trạng thái `published`). Bản `r3` chỉ bổ sung bước chờ sẵn sàng có giới hạn (`waitForCondition`, giới hạn `20000 ms`) ở đầu pha `prepare_offline` (sau `goto` trang gốc/origin guard và trước `performOwnerLogin`), gọi lặp `enableAccessibility()` đến khi tab `Tài Khoản` ở gốc thực sự hiển thị (`isVisible()`), giữ nguyên toàn bộ logic request/row/cleanup/oracle và `performOwnerLogin`. Đây là vòng sửa cuối của Anti (3/3); mọi phát hiện source còn lại (nếu có) do root Codex xử lý trực tiếp theo ủy quyền hiện hành. Không tự nhận Đạt, không tuyên bố full V2, BH-07/V8, native, clipboard, QR hay cold restart.**

Tài liệu này bàn giao kịch bản kiểm thử hai pha trên cùng document [web_lifecycle_scenario.js](../../../scripts/bh07_browser/web_lifecycle_scenario.js) để Codex cấp fixture UUID sạch riêng cho từng trình duyệt, chạy qua `playwright-cli run-code --filename=...`, kiểm chứng các cổng DB giữa hai pha và sau pha retry, rồi dọn dữ liệu thử nghiệm.

## 1. Phạm vi kịch bản mới

[web_lifecycle_scenario.js](../../../scripts/bh07_browser/web_lifecycle_scenario.js) là một biểu thức `async page => { ... }` duy nhất (không dấu `;` cuối, không `import`/`require`, không `process`, không gọi REST trực tiếp hay chèn state, không trả snapshot thô/mật khẩu/token/dữ liệu ngân hàng/ngoại lệ thô):

- **Hằng số cấu hình ở đầu file:**
  - `SESSION_ID = '__BH07_SESSION_ID__'` (bắt buộc thay bằng UUID hợp lệ trong bản driver gitignored; script từ chối placeholder hoặc chuỗi không phải UUID).
  - `TITLE = 'BH07 V2 isolated lifecycle'`
  - `PHASE = 'prepare_offline'` (`'prepare_offline'` hoặc `'retry_online'`)
  - `FIRST_COMPLETE_PAYLOAD = null` (ở pha `'retry_online'`, thay bằng đúng JSON object parsed từ output pha 1).
- **Guard môi trường:**
  - Kiểm tra `page.url()` ban đầu có origin chính xác `http://127.0.0.1:8088` (`about:blank` chỉ được phép ở đầu pha `'prepare_offline'`, bị từ chối ở `'retry_online'`).
  - Lọc chính xác `POST http://127.0.0.1:54321/rest/v1/rpc/complete_session` (loại `OPTIONS`), parse JSON nghiêm ngặt, chỉ nhận request có `p_session_id === SESSION_ID`.
- **Pha 1 (`prepare_offline`):**
  1. Mở `http://127.0.0.1:8088/#/`, kiểm tra origin loopback, chờ bootstrap Guest home sẵn sàng trong giới hạn `20000 ms` bằng `waitForCondition` (gọi `enableAccessibility()` cho tới khi tab gốc `Tài Khoản` thực sự `isVisible()`, không coi trạng thái vắng mặt là đạt), rồi gọi `performOwnerLogin()` kiểm tra trạng thái khách trên tab `Tài Khoản` và đăng nhập UI thật `ownera@example.test` / `bh07-http-pass-123456` bằng helper bàn phím + `requestAnimationFrame` + `Tab` blur.
  2. Điều hướng tới `http://127.0.0.1:8088/#/sessions/<SESSION_ID>`, ghi `performance.timeOrigin`, kiểm tra `TITLE` và chip `Đã công bố`, xác nhận `Member A` và `Guest A` đang ở `Đã xác nhận · Chưa điểm danh`.
  3. Bấm `Bắt đầu buổi chơi` → xác nhận `Đang diễn ra`.
  4. Điểm danh cả `Member A` và `Guest A` theo ngữ cảnh màn hình chi tiết (`Chi tiết buổi chơi` / `group "Danh sách đăng ký"`), định vị duy nhất từng hàng qua `getByRole('group', { name: /^M Member A Đã xác nhận · / })` và `/^G Guest A Đã xác nhận · /` (không dùng tọa độ/`boundingBox` hay `nth` mù), xác nhận hậu tố `Chưa điểm danh` ở trạng thái `Đã công bố` (chưa có nút `Có mặt`) và khi mới `Đang diễn ra` (mỗi hàng có nút `Có mặt`), rồi bấm `row.getByRole('button', { name: 'Có mặt', exact: true })` cho từng người để chuyển sang hậu tố `Có mặt` và nút `Có mặt` của chính hàng đó biến mất.
  5. Mở `Tài chính & thu tiền`, xác nhận chi phí đã ghi `200,000 VNĐ`, trạng thái `Chưa chốt phí`, `Chưa có thanh toán.`. Bấm `Chốt phí` → nhập ô `Lý do *` bằng bàn phím + `Tab` blur → `Xác nhận` → yêu cầu `Đang hiệu lực`, `Chốt lại phí`, `Tổng còn phải thu` `200,000 VNĐ`, hai khoản `100,000 VNĐ` cho `Member A` và `Guest A`, không có thanh toán.
  6. Bật `context.setOffline(true)`, bấm `Kết thúc buổi chơi` → `Đồng ý`. Yêu cầu snackbar lỗi chính xác `Đã xảy ra lỗi. Vui lòng thử lại sau.`, không hiện `Đã kết thúc buổi chơi.`, nút `Kết thúc buổi chơi` vẫn bật, bắt được đúng **1** `POST complete_session` với `p_session_id = SESSION_ID`, `p_expected_version = 2`, `p_request_id` là UUID.
  7. Khối `finally` luôn gọi `context.setOffline(false)`, gỡ mọi listener, không nuốt lỗi dọn dẹp và **không tự bấm retry** sau khi khôi phục mạng. Trả về object sạch gồm `FIRST_COMPLETE_PAYLOAD` (chỉ 3 trường `p_session_id`, `p_expected_version`, `p_request_id`) để Codex giữ trong bản log gitignored và truyền sang pha 2 (chỉ công bố bản đã sanitize).
- **Pha 2 (`retry_online`):**
  1. Kiểm tra `FIRST_COMPLETE_PAYLOAD` có đủ khóa/kiểu hợp lệ trước mọi thao tác; **không** login lại, **không** `reload`, **không** `goto` để giữ nguyên provider pending request intent và document (`performance.timeOrigin`).
  2. Yêu cầu màn `Tài chính buổi`, `Đang hiệu lực`, `Chốt lại phí`, nút `Kết thúc buổi chơi` đang bật.
  3. Gắn listener request và chuẩn bị `page.waitForResponse` (`POST`, HTTP `200`, đúng path + `p_session_id`) trước khi bấm `Kết thúc buổi chơi` → `Đồng ý`.
  4. Xác nhận chuyển về chi tiết buổi `Đã kết thúc` kèm mục `Tổng kết buổi`, bắt được đúng **1** request retry, `p_request_id` trùng và canonical JSON khớp hoàn toàn `FIRST_COMPLETE_PAYLOAD`.
  5. Mở `Tổng kết buổi`, xác nhận số lượt `2 / 0 / 2` và tài chính `200,000 / 200,000 / 0 / 200,000` VNĐ, `performance.timeOrigin` không đổi. Trả về kết quả sạch (không kèm full payload).

## 2. Yêu cầu fixture & cổng DB của root Codex (mỗi trình duyệt một UUID riêng)

### Điều kiện fixture trước Pha 1 (mỗi trình duyệt)
- Tạo một buổi mới với `SESSION_ID` UUID ngẫu nhiên riêng, `host_user_id` là `ownera@example.test`, `title = 'BH07 V2 isolated lifecycle'`, `lifecycle = 'published'`, `version = 1`, `billing_input_version = 1`.
- Hai người chơi đã xác nhận: `Member A` (`confirmed`, `not_checked_in`) và `Guest A` (`confirmed`, `not_checked_in`).
- Một chi phí đã ghi: `amount_vnd = 200000`, `status = 'posted'`; không có bản ghi `payments` hay `charge_revisions`.

### Cổng DB giữa Pha 1 và Pha 2 (sau `prepare_offline`, trước `retry_online`)
- `sessions`: `lifecycle = 'in_progress'`, `version = 2` (tăng từ bước `Bắt đầu buổi chơi`, **không phải** do chốt phí; `billing_input_version` tăng riêng theo các thao tác điểm danh/chi phí; **không** chuyển sang `completed` khi offline).
- `session_players`: cả `Member A` và `Guest A` đều có `attendance_status = 'present'`.
- `charge_revisions` / `session_charges`: có 1 revision `current` (hoặc active) gồm 2 khoản `100000` VND; `payments` = `0`.
- `operation_requests` với `request_id = <FIRST_COMPLETE_PAYLOAD.p_request_id>` có count = `0`.
- `audit_events` với `session_id = <SESSION_ID>` và `action = 'SESSION_COMPLETED'` có count = `0`.

### Cổng DB sau Pha 2 (sau `retry_online`)
- `sessions`: `lifecycle = 'completed'`, `version = 3`.
- `SELECT count(*) FROM operation_requests WHERE request_id = '<p_request_id>'` = `1`.
- `SELECT count(*) FROM audit_events WHERE session_id = '<SESSION_ID>' AND action = 'SESSION_COMPLETED'` = `1`.
- Đối chiếu fingerprint DB trước/sau khi đã dọn các dòng fixture tạm (không để lại fixture thử nghiệm).

## 3. Công thức thay thế & lệnh `--filename` cho Codex

> Lưu ý: Tạo bản driver tạm trong thư mục gitignored (ví dụ `.build/bh07_driver_<browser>_p1.js` và `_p2.js`) để không sửa file gốc trong `scripts/bh07_browser/web_lifecycle_scenario.js`. Không dùng chung một `SESSION_ID` cho nhiều trình duyệt.

### Quy trình thay thế mỗi trình duyệt
1. **Driver Pha 1** (`p1.js`): sao chép `scripts/bh07_browser/web_lifecycle_scenario.js`, thay:
   - `const SESSION_ID = '<FRESH_BROWSER_UUID>';`
   - Giữ `const PHASE = 'prepare_offline';` và `const FIRST_COMPLETE_PAYLOAD = null;`
2. Chạy Pha 1, lấy `FIRST_COMPLETE_PAYLOAD` (chỉ `{ p_session_id, p_expected_version, p_request_id }`) và `document_time_origin` từ output trong vùng ignored; kiểm tra các cổng DB giữa hai pha.
3. **Driver Pha 2** (`p2.js`): sao chép `scripts/bh07_browser/web_lifecycle_scenario.js`, thay:
   - `const SESSION_ID = '<SAME_BROWSER_UUID>';`
   - `const PHASE = 'retry_online';`
   - `const FIRST_COMPLETE_PAYLOAD = <PARSED_FIRST_COMPLETE_PAYLOAD_JSON>;`
4. Chạy Pha 2 trên **cùng named session** (`-s=...`), kiểm tra `document_time_origin` trùng Pha 1, chạy cổng DB cuối và dọn fixture.

### Lệnh `playwright-cli` theo trình duyệt

#### Edge headless
```powershell
playwright-cli -s=bh07-edge-lifecycle open about:blank --browser=msedge
playwright-cli -s=bh07-edge-lifecycle run-code --filename=.build/bh07_edge_lifecycle_p1.js
# [Codex kiểm tra cổng DB giữa Pha 1 và Pha 2, dựng p2.js từ FIRST_COMPLETE_PAYLOAD]
playwright-cli -s=bh07-edge-lifecycle run-code --filename=.build/bh07_edge_lifecycle_p2.js
playwright-cli -s=bh07-edge-lifecycle close
```

#### Firefox headless
```powershell
playwright-cli -s=bh07-ff-headless-lifecycle open about:blank --browser=firefox
playwright-cli -s=bh07-ff-headless-lifecycle run-code --filename=.build/bh07_ff_headless_lifecycle_p1.js
# [Codex kiểm tra cổng DB giữa Pha 1 và Pha 2, dựng p2.js từ FIRST_COMPLETE_PAYLOAD]
playwright-cli -s=bh07-ff-headless-lifecycle run-code --filename=.build/bh07_ff_headless_lifecycle_p2.js
playwright-cli -s=bh07-ff-headless-lifecycle close
```

#### Firefox software WebRender headed (chỉ khi cần kiểm tra có cửa sổ; bắt buộc `--config` bật `gfx.webrender.software=true`, không chụp màn hình chứa dữ liệu nhạy cảm)
```powershell
playwright-cli -s=bh07-ff-soft-lifecycle open about:blank --browser=firefox --headed --config=docs/reviews/bh07/web_v2_20261113_evidence/firefox-software-config.json
playwright-cli -s=bh07-ff-soft-lifecycle run-code --filename=.build/bh07_ff_soft_lifecycle_p1.js
# [Codex kiểm tra cổng DB giữa Pha 1 và Pha 2, dựng p2.js từ FIRST_COMPLETE_PAYLOAD]
playwright-cli -s=bh07-ff-soft-lifecycle run-code --filename=.build/bh07_ff_soft_lifecycle_p2.js
playwright-cli -s=bh07-ff-soft-lifecycle close
```

## 4. Các hạng mục đã đo và vẫn `NOT_RUN` / `UNKNOWN`

- **Edge `r1` (lịch sử trước `r2`):** Bắt đầu buổi chơi, điểm danh cả `Member A` / `Guest A` và chốt phí (`Chốt phí` → `Đang hiệu lực`) chạy đúng nhưng dừng tại `chargesHeader` (`getByText('Khoản phải thu theo người', { exact: true })`).
- **Edge `r2` (đã đo bởi Codex):** **COMPLETE PASS** gồm đầy đủ `prepare_offline` + `retry_online`, `operation_requests` và `audit_events` tăng chính xác `0 -> 1`, payload/body retry khớp hoàn toàn, `performance.timeOrigin` giữ nguyên và đã dọn fixture.
- **Firefox headed software WebRender cold first load `r2` (đã đo bởi Codex):** **`FAIL`** tại bước bootstrap đầu pha `prepare_offline` trong ~4s (`Navigation failed: neither "Tài Khoản" tab nor "Back" button is visible` từ `performOwnerLogin -> navigateBackToMain`) khi tiêu đề trang ban đầu còn là `badminton_hub` trước khi semantics Guest home sẵn sàng; snapshot bổ sung do Codex lấy sau đó thấy màn hình Guest home đầy đủ tab `Tài Khoản` và tiêu đề `Badminton Nha Trang Hub`, không có mutation nào xảy ra và fixture vẫn ở `published`.
- **Runtime bản `r3` trên Firefox (sau sửa bootstrap-readiness `waitForCondition` 20s trong `prepare_offline`):** **`NOT_RUN`** (chờ Codex kiểm chứng runtime trên Firefox; giữ nguyên workflow/oracles đã PASS trên Edge).
- Luồng ghi thanh toán (Member gửi chuyển khoản, Owner xác nhận/tiền mặt, ledger entry): **`NOT_RUN`** trên Edge/Firefox bởi kịch bản này.
- Clipboard, VietQR, full browser cold restart: **`NOT_RUN`** trong kịch bản này.
- Firefox headed mặc định: **`UNKNOWN`** về hiển thị; Safari/macOS, iOS/Android native: **`NOT_RUN`**.
- Toàn V2, V2b, V3, V5, V7, V8 và BH-07: **chưa nghiệm thu** (Edge được Codex đo xong không đồng nghĩa nghiệm thu full V2).
