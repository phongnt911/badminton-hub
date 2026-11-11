# Bàn giao Sửa đổi Vòng 3/3: Kịch bản Web Trình duyệt BH-07 — 10/11/2026

- **Ngày thực hiện:** 10/11/2026, Asia/Saigon.
- **Bên triển khai:** Anti CLI (thực hiện theo `.build/anti-web-matrix-r3-task.txt` kế thừa lịch sử vòng 1 & 2).
- **Bên nhận bàn giao:** Root Codex / Reviewer độc lập điều phối.
- **Phạm vi file bàn giao vòng 3:**
  1. [`scripts/bh07_browser/web_matrix_scenario.js`](../../../scripts/bh07_browser/web_matrix_scenario.js) (khắc phục CLI trailing semicolon, RPC stage 5 predicate strict origins/body, và console error classifier)
  2. [`docs/reviews/bh07/web_matrix_scenario_handoff_20261110.md`](web_matrix_scenario_handoff_20261110.md) (tài liệu bàn giao cập nhật lệnh phiên định danh canonical)
  *(File [`test/schema/schema_v1_1_migration_test.dart`](../../../test/schema/schema_v1_1_migration_test.dart) đã đạt 247 PASS + 1 SKIP và đã được commit tại `1717451`, giữ nguyên).*
- **Kỷ luật thực thi:** Anti **không** chạy lệnh shell, Docker, browser Playwright runtime, `flutter test`, subagents, commit/push; **không** đọc tài liệu ngoài phạm vi; **không** thay đổi bất kỳ file SQL migration hay logic backend/app nào; **không** ngụy tạo kết quả kiểm thử. Root Codex giữ toàn quyền chạy runtime kiểm chứng và test suite sau bàn giao.

---

## 1. Chi tiết Khắc phục Vòng 3/3 (`web_matrix_scenario.js`)

### Sửa 1: Chuẩn hóa Giao diện CLI — Gỡ bỏ dấu chấm phẩy cuối file
- **Vấn đề:** File kết thúc bằng `};`. Khi `playwright-cli run-code` thực thi, CLI bọc toàn bộ mã nguồn dạng `( ... \n)` rồi `eval()`. Cú pháp `( async page => { ... }; )` gây lỗi `SyntaxError: Unexpected token ';'` ngay trước khi tương tác ứng dụng.
- **Khắc phục:** Đổi dòng kết thúc file thành duy nhất `}` (single async function expression, không có dấu chấm phẩy ở câu lệnh ngoài cùng). Các dấu chấm phẩy nội bộ bên trong hàm được giữ nguyên vẹn.

### Sửa 2: Khép chặt Bộ lọc `waitForResponse` RPC Stage 5
- **Vấn đề:** Predicate cũ chấp nhận port sai (`wrongPortAccepted=true`), nuốt lỗi khi parse JSON hoặc thiếu session (`missingSessionAccepted=true`, `invalidJsonAccepted=true`).
- **Khắc phục:**
  - Giới hạn tuyệt đối `url.origin` chỉ chấp nhận `http://127.0.0.1:54321` hoặc `http://localhost:54321`.
  - Khớp chính xác `url.pathname === '/rest/v1/rpc/get_session_summary'`.
  - Xác nhận method `POST` và status `200`.
  - Kiểm tra body nghiêm ngặt:
    ```javascript
    try {
      return req.postDataJSON()?.p_session_id === SESSION_ID;
    } catch (_) {
      return false;
    }
    ```
  - Bác bỏ triệt để cả 3 trường hợp mutant: parse JSON lỗi trả về `false`, thiếu `p_session_id` trả về `false`, sai port trả về `false`.

### Sửa 3: Chuẩn hóa Bộ phân loại Console (Console Classifier)
- **Khắc phục:** Không gom mọi lỗi chứa `net::` thành lỗi mất mạng.
  - Chỉ chuỗi rõ ràng `ERR_INTERNET_DISCONNECTED` mới tăng `offline_resource_errors`.
  - Chuỗi chứa `vietqr` hoặc `CORS` tăng `qr_cors_errors`.
  - Các lỗi khác chỉ được tính vào biến đếm chung `error_count`, không ghi nhận URL hay text thô.

---

## 2. Lịch sử Khắc phục Vòng 1 & 2 (Đã được Codex xác minh)

### Vòng 2: Khép kín Fail-closed Cleanup & Đồng bộ RPC Recovery
1. Khối `finally` nội bộ Stage 5 và Outer finally đều ném lỗi cố định an toàn khi `setOffline(false)` thất bại; bảo đảm listeners `page.off` luôn luôn được thực thi trong khối `finally`.
2. Đồng bộ `Promise.all([page.waitForResponse(...), retryBtn.click()])` với bounded timeout 15000ms; gọi lại `verifyCohostSummary()` và kiểm tra vắng mặt banner lỗi sau response.

### Vòng 1: Oracle Regex Boundaries & Schema CRLF
1. WM1: Regex ràng buộc biên `(?!\d)` cho kiểm tra số lượng và công nợ; clipboard đổi thành `status: 'NOT_RUN'`.
2. WM2: Nhãn lỗi cố định, console summary an toàn, bảo vệ dữ liệu private Member.
3. WM3: Guard loopback origin và xử lý điều hướng an toàn sau reload F5.
4. SC1: Chuẩn hóa CRLF thành LF trong `test/schema/schema_v1_1_migration_test.dart` (commit `1717451`).

---

## 3. Lệnh Thực thi Kiểm chứng cho Root Codex (Canonical Named Sessions)

Sử dụng phiên định danh riêng biệt `-s` cho từng trình duyệt:

### 1. Phiên Edge (`bh07-web-edge-matrix`)
```powershell
playwright-cli -s=bh07-web-edge-matrix open http://127.0.0.1:8088 --browser=msedge
playwright-cli -s=bh07-web-edge-matrix run-code --filename=scripts/bh07_browser/web_matrix_scenario.js
```

### 2. Phiên Firefox (`bh07-web-firefox-matrix`)
```powershell
playwright-cli -s=bh07-web-firefox-matrix open http://127.0.0.1:8088 --browser=firefox
playwright-cli -s=bh07-web-firefox-matrix run-code --filename=scripts/bh07_browser/web_matrix_scenario.js
```

### 3. Kiểm chứng Suite Test Schema
```powershell
flutter test test/schema/schema_v1_1_migration_test.dart
```

---

## 4. Trạng thái Nghiệm thu

- Anti đã hoàn tất đúng các dòng chỉnh sửa tối thiểu của vòng 3/3 theo đúng đặc tả.
- Anti **không** chạy shell/runtime/docker/test; không ngụy tạo kết quả kiểm thử.
- Đợt kiểm tra wrong-due của Root trước đó dừng ở lỗi cú pháp dấu chấm phẩy và chưa chạy tới assertion; nay đã được khắc phục hoàn toàn.
- Toàn bộ kết quả kiểm thử runtime và xác minh test suite thuộc trách nhiệm thực thi của Root Codex.
- Toàn bộ BH-07/V8 tiếp tục giữ trạng thái **Chưa nghiệm thu**.
