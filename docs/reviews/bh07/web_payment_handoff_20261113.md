# BH-07 V2 Web Payment (Submit → Confirm → Verify Guest) Handoff — 13/11/2026

**Trạng thái: `NOT_RUN` — Kịch bản kiểm thử thanh toán mới [web_payment_scenario.js](../../../scripts/bh07_browser/web_payment_scenario.js) và tài liệu bàn giao này vừa được tạo; chưa chạy runtime trình duyệt/DB, không tự nhận Đạt, không tuyên bố clipboard, heap, native, ngân hàng/VietQR live, idempotent-replay, full V2 hoặc nghiệm thu BH-07/V8.**

Lượt này chỉ tạo mới 2 tệp được giao (`scripts/bh07_browser/web_payment_scenario.js` và `docs/reviews/bh07/web_payment_handoff_20261113.md`); không sửa các công cụ/bằng chứng đã nghiệm thu trước đây, mã nguồn ứng dụng, backend, migration, test hay cấu hình agent.

## 1. Cấu trúc kịch bản và quy tắc thay thế cấu hình

[web_payment_scenario.js](../../../scripts/bh07_browser/web_payment_scenario.js) là một biểu thức `async page => { ... }` duy nhất (không dấu `;` cuối, không `import`/`require`, không `process`, không gọi REST trực tiếp hay chèn state, chỉ abort ngoài `https://img.vietqr.io/**`, không mock local API).

Các hằng số cấu hình ở đầu file để Codex thay trong **bản driver copy nằm trong thư mục gitignored** (ví dụ `.build/`):

```js
const SESSION_ID = '__BH07_SESSION_ID__';
const GUEST_PLAYER_ID = '__BH07_PLAYER_ID__';
const PAYMENT_ID = null;
const PHASE = 'submit';
const EXPECTED_AMOUNT = 100000;
```

Quy tắc kiểm tra đầu vào trong script:
- `SESSION_ID` và `GUEST_PLAYER_ID` bắt buộc khớp regex UUID (từ chối placeholder và chuỗi không phải UUID mà không so sánh chuỗi placeholder theo nghĩa đen sau thay thế toàn cục).
- `PHASE` chỉ nhận `'submit' | 'confirm' | 'verify_guest'`.
- `PAYMENT_ID`: bắt buộc UUID hợp lệ khi `PHASE === 'confirm'`; cho phép `null` hoặc UUID hợp lệ ở `'submit'` / `'verify_guest'`.
- `EXPECTED_AMOUNT`: bắt buộc số nguyên dương an toàn (`> 0`).
- `TITLE = 'BH07 V2 isolated payment'`, `BASE_URL = 'http://127.0.0.1:8088'`, origin API `http://127.0.0.1:54321`; guard kiểm tra origin của `page.url()` ban đầu và sau mọi `goto`.
- Đầu ra chỉ trả JSON an toàn (boolean, UUID, số đếm console/pageerror, `request_payload` an toàn gồm UUID/amount/method/null/`p_request_id`); tuyệt đối không trả snapshot thô, `reference`, thông tin ngân hàng, headers, token hay mật khẩu.

## 2. Điều kiện fixture sở hữu của root Codex (mỗi trình duyệt một bộ ID mới)

Root Codex tạo fixture tổng hợp riêng theo từng trình duyệt (preflight không trùng ID, đánh dấu sở hữu, không đụng session `0099` kế thừa):
- **Session:** `SESSION_ID` mới, `title = 'BH07 V2 isolated payment'`, `lifecycle = 'completed'`, `version = 3`, thuộc CLB của `ownera@example.test` với `receiver_snapshot` kế thừa từ fixture tổng hợp (không dùng dữ liệu ngân hàng thật).
- **Người chơi:** 2 đăng ký `confirmed` + `attendance_status = 'present'`: `Guest A` (`guesta@example.test`, `session_players.id = GUEST_PLAYER_ID`) và `Member A` (`membera@example.test`).
- **Tài chính ban đầu:** 1 `charge_revisions` `active` ở trạng thái `current` (`source_version = billing_input_version`), `session_expenses` `posted` tổng `200000`, 2 `session_charges` `100000` VNĐ mỗi người (tổng `200000`), **`0` bản ghi `payments`** và **`0` bản ghi `club_transactions` nguồn payment**.

## 3. Ba pha kiểm thử và điều kiện đạt UI

Mỗi pha chạy trên một **fresh browser profile** (`open about:blank` → `run-code --filename=...` → `close`) và đăng nhập UI thật qua tab gốc `Tài Khoản` (vòng lặp `enableAccessibility()` đến khi tab `Tài Khoản` hiển thị, tối đa 20s; nhập bàn phím + `requestAnimationFrame` + `Tab` blur; mật khẩu fixture `bh07-http-pass-123456`).

### Pha 1 — `PHASE = 'submit'` (`guesta@example.test`)
1. Đăng nhập `guesta@example.test`, cài `page.route('https://img.vietqr.io/**', ...)` chỉ abort ảnh VietQR ngoài (local API giữ nguyên).
2. Mở `http://127.0.0.1:8088/#/sessions/<SESSION_ID>`, kiểm tra vắng quản lý/tổng kết (`Tổng kết buổi`, `Tài chính & thu tiền`, `Tài chính tổng hợp`, `Danh sách đăng ký`).
3. Mở `Phần phí của tôi` → yêu cầu `Phần phí của bạn`, `Đang hiệu lực`, fallback QR `Không tải được ảnh QR. Dùng thông tin bên dưới để chuyển khoản.`, thông báo không tự xác nhận, `routeAbortCount >= 1`, `Phải trả` `100,000 VNĐ`, `Đã trả` `0 VNĐ`, `Còn lại` `100,000 VNĐ` (khớp nhãn và biên số).
4. Bấm `Tôi đã chuyển khoản` → hộp thoại `Xác nhận đã chuyển khoản` → chuẩn bị `page.waitForResponse` trước khi bấm `Đồng ý`.
5. Bắt mọi `POST` tới `http://127.0.0.1:54321/rest/v1/rpc/submit_payment` (không âm thầm bỏ qua request lệch target), yêu cầu đúng `1` request, body chỉ gồm đúng 5 khóa: `p_player_id == GUEST_PLAYER_ID`, `p_amount_vnd == EXPECTED_AMOUNT`, `p_method == 'bank_transfer'`, `p_reference === null`, `p_request_id` là UUID; HTTP `200`, JSON trả về `payment_id` UUID, `player_id`, `session_id`, `amount_vnd`, `status == 'submitted'`.
6. Chờ snackbar `Đã ghi nhận, chờ ban quản lý xác nhận.` và xác nhận UI vẫn giữ `Đã trả: 0 VNĐ`, `Còn lại: 100,000 VNĐ`, không hiện `Bạn đã trả đủ.`. Trả về `{ ok, phase, session_id, submission_ui_verified: true, submitted_not_counted_paid: true, attempts: 1, rpc_status: 200, payment_id, responseId, request_payload, recorded_console_summary }` (không trả `reference`).

### Pha 2 — `PHASE = 'confirm'` (`ownera@example.test`, `PAYMENT_ID` từ Pha 1)
1. Đăng nhập `ownera@example.test`, mở `http://127.0.0.1:8088/#/sessions/<SESSION_ID>` → `Tài chính & thu tiền`.
2. Yêu cầu `Đang hiệu lực`, phần `Thanh toán` có đúng **1** bản ghi `100,000 VNĐ — bank_transfer` với trạng thái `Chờ xác nhận`; định vị duy nhất row qua `getByRole('group', { name: ... })` khớp Flutter semantics (không `nth`, không click text toàn cục), kiểm tra toàn màn chỉ có đúng 1 nút `Xác nhận` nằm trong chính row đó.
3. Bấm `Xác nhận` trên row → hộp thoại `Xác nhận thanh toán` → chuẩn bị `page.waitForResponse` trước khi bấm `Đồng ý`.
4. Bắt mọi `POST` tới `http://127.0.0.1:54321/rest/v1/rpc/confirm_payment`, yêu cầu đúng `1` request, body chỉ gồm `p_payment_id == PAYMENT_ID` và `p_request_id` UUID; HTTP `200`, JSON trả về `payment_id == PAYMENT_ID`, `session_id == SESSION_ID`, `player_id == GUEST_PLAYER_ID`, `amount_vnd == EXPECTED_AMOUNT`, `status == 'confirmed'`, `ledger_id` UUID.
5. Chờ snackbar `Đã xác nhận thanh toán.`, row chuyển `Đã xác nhận`, nút `Xác nhận` biến mất, `Tổng còn phải thu` còn `200000 - EXPECTED_AMOUNT` (`100,000 VNĐ`).
6. Bấm `Back` về `Chi tiết buổi chơi`, mở `Tổng kết buổi`: yêu cầu số lượt `Có mặt: 2`, `Vắng: 0`, `Đã xác nhận: 2` (`2/0/2`), `Tổng chi phí: 200,000 VNĐ`, `Tổng phải thu: 200,000 VNĐ`, `Đã thu: 100,000 VNĐ`, `Còn phải thu: 100,000 VNĐ`. Trả về `{ ok, phase, session_id, confirmation_ui_verified: true, summary_verified: true, attempts: 1, rpc_status: 200, payment_id, ledger_id, request_payload, recorded_console_summary }`.

### Pha 3 — `PHASE = 'verify_guest'` (`guesta@example.test`)
1. Đăng nhập `guesta@example.test`, mở `http://127.0.0.1:8088/#/sessions/<SESSION_ID>` → `Phần phí của tôi`.
2. Yêu cầu `Bạn đã trả đủ.`, `Phải trả: 100,000 VNĐ`, `Đã trả: 100,000 VNĐ`, `Còn lại: 0 VNĐ`, không có nút `Tôi đã chuyển khoản`, không có khối chuyển khoản/QR (`Chuyển khoản để thanh toán`, `Ngân hàng`, `Số tài khoản`, `Chủ tài khoản`, `Nội dung`, `Mã QR chỉ là hướng dẫn`), không có quản lý/tổng kết, `routeAbortCount === 0`, và không phát sinh mutation RPC nào.

## 4. Cổng DB bắt buộc của root Codex

### Giữa Pha 1 (`submit`) và Pha 2 (`confirm`)
- `payments` cho `session_player_id = <GUEST_PLAYER_ID>`: `submitted = 1`, `confirmed = 0`; dòng `id = <payment_id>` có `status = 'submitted'`, `amount_vnd = 100000`, `method = 'bank_transfer'`, `submitted_by = <guesta_user_id>`, `confirmed_by IS NULL`, `confirmed_at IS NULL`.
- `club_transactions` (ledger) với `source_payment_id = <payment_id>`: count = **`0`**.
- `operation_requests` với `request_id = <submit_p_request_id>`, `operation = 'submit_payment'`, `actor_id = <guesta_user_id>`: count = **`1`**.
- `audit_events` với `session_id = <SESSION_ID>`, `entity_type = 'payment'`, `entity_id = <payment_id>`, `action = 'PAYMENT_SUBMITTED'`, `request_id = <submit_p_request_id>`, `actor_id = <guesta_user_id>`: count = **`1`**.

### Sau Pha 2 (`confirm`) và giữ nguyên sau Pha 3 (`verify_guest`)
- `payments` với `id = <payment_id>`: count = **`1`**, `status = 'confirmed'`, `amount_vnd = 100000`, `confirmed_by = <ownera_user_id>`, `confirmed_at IS NOT NULL`.
- `club_transactions` với `id = <ledger_id>`: count = **`1`**, `direction = 'income'`, `amount_vnd = 100000`, `source_type = 'payment'`, `source_payment_id = <payment_id>`, `created_by = <ownera_user_id>`.
- `audit_events` cho `session_id = <SESSION_ID>` và `entity_id = <payment_id>`:
  - `action = 'PAYMENT_SUBMITTED'` (`request_id = <submit_p_request_id>`, `actor_id = <guesta_user_id>`): count = **`1`**.
  - `action = 'PAYMENT_CONFIRMED'` (`request_id = <confirm_p_request_id>`, `actor_id = <ownera_user_id>`): count = **`1`**.
- `operation_requests`:
  - `request_id = <submit_p_request_id>` (`operation = 'submit_payment'`, `actor_id = <guesta_user_id>`): count = **`1`**.
  - `request_id = <confirm_p_request_id>` (`operation = 'confirm_payment'`, `actor_id = <ownera_user_id>`): count = **`1`**.
- Sau `verify_guest`: toàn bộ các count `payments` / `club_transactions` / `audit_events` / `operation_requests` ở trên giữ nguyên không tăng.

## 5. Lệnh chạy `playwright-cli` gợi ý (driver copy trong `.build/`)

Với mỗi trình duyệt (`msedge` hoặc `firefox`), dùng `SESSION_ID` và `GUEST_PLAYER_ID` riêng; thay các hằng số ở đầu bản driver copy trong `.build/` theo từng pha:

```powershell
# Pha 1: submit (SESSION_ID, GUEST_PLAYER_ID, PAYMENT_ID=null, PHASE='submit')
playwright-cli -s=bh07-edge-pay-submit open about:blank --browser=msedge
playwright-cli -s=bh07-edge-pay-submit run-code --filename=.build/bh07_edge_pay_submit.js
playwright-cli -s=bh07-edge-pay-submit close

# [Codex kiểm tra cổng DB sau submit, lấy payment_id tạo driver confirm]

# Pha 2: confirm (SESSION_ID, GUEST_PLAYER_ID, PAYMENT_ID=<payment_id>, PHASE='confirm')
playwright-cli -s=bh07-edge-pay-confirm open about:blank --browser=msedge
playwright-cli -s=bh07-edge-pay-confirm run-code --filename=.build/bh07_edge_pay_confirm.js
playwright-cli -s=bh07-edge-pay-confirm close

# [Codex kiểm tra cổng DB sau confirm]

# Pha 3: verify_guest (SESSION_ID, GUEST_PLAYER_ID, PAYMENT_ID=null, PHASE='verify_guest')
playwright-cli -s=bh07-edge-pay-verify open about:blank --browser=msedge
playwright-cli -s=bh07-edge-pay-verify run-code --filename=.build/bh07_edge_pay_verify.js
playwright-cli -s=bh07-edge-pay-verify close
```

Với Playwright Firefox headless, lặp lại quy trình 3 pha tương tự bằng `--browser=firefox` với bộ `SESSION_ID` / `GUEST_PLAYER_ID` và tên session `-s=bh07-ff-pay-*` riêng.

## 6. Dọn dẹp sở hữu và phạm vi giới hạn

- **Dọn dẹp DB theo thứ tự FK ngược:** xóa đúng các bản ghi sở hữu của từng lượt thử gồm `audit_events`, `operation_requests` (theo đúng `submit_p_request_id` và `confirm_p_request_id` đã bắt), `club_transactions` (cả bút toán `income` theo `ledger_id`/`source_payment_id` và bút toán `session_expense` của fixture), `payments`, `session_charges`, `charge_revisions`, `session_expenses`, `session_players`, `sessions`; xác minh absent 0 dòng và đối chiếu fingerprint bảng/dòng/schema/role/sequence với baseline (riêng `auth.refresh_tokens_id_seq` có thể tăng do các lượt login thật).
- **Dọn môi trường:** xóa các file driver copy tạm trong `.build/`, đóng toàn bộ named browser session và xác nhận inventory không còn browser tồn đọng.
- **Không tuyên bố ngoài phạm vi:** tài liệu và script hiện đang **`NOT_RUN`**; không kiểm chứng clipboard, heap retention, mobile native, VietQR/ngân hàng live, replay idempotent hay nghiệm thu full V2 / BH-07 / V8.
