# BH-07 V2 Web Extension Handoff — 13/11/2026

**Trạng thái: CHỜ CODEX CHẠY VÀ REVIEW (`NOT RUN`). Chưa đo runtime mới; không tuyên bố V2 PASS hoặc nghiệm thu toàn BH-07/V8.**

Tài liệu này bàn giao kịch bản Web mở rộng [web_reopen_scenario.js](../../../scripts/bh07_browser/web_reopen_scenario.js) để kiểm chứng đóng/mở lại tab trong cùng profile trình duyệt ngay sau [web_matrix_scenario.js](../../../scripts/bh07_browser/web_matrix_scenario.js), đồng thời kiểm kê rõ phần đã phủ so với các hàng V2 còn thiếu theo [readiness §4.3](bh07_readiness.md#43-v2--mobiledevice-browser-khác-offlinereopendeep-link).

## 1. Phạm vi kịch bản mới

[web_reopen_scenario.js](../../../scripts/bh07_browser/web_reopen_scenario.js) là biểu thức `async page => { ... }` tối giản cho `playwright-cli run-code` (không import, không `process`, không `body.innerText`, không chèn backend/API), chạy tiếp trong **cùng context** ngay sau khi `web_matrix_scenario.js` kết thúc ở trạng thái đã đăng nhập `membera@example.test`:

1. **Origin guard & identity ban đầu:** Xác nhận `new URL(page.url()).origin === 'http://127.0.0.1:8088'`, kích hoạt Flutter semantics, điều hướng về màn hình gốc bằng nút `Back` thật và kiểm tra tab `Tài Khoản` hiển thị `membera@example.test` kèm `Đã xác thực`.
2. **Mở tab neo trống & đóng tab gốc trước khi tải lại app:** Tạo một tab mới trống (`about:blank`) làm safety anchor trong cùng context và gắn listener `console`/`pageerror`; kiểm tra context có ít nhất 2 page (`pages_before_close >= 2`); đóng tab gốc (`page.close()`) và xác nhận `page.isClosed() === true` cùng `pages_after_close >= 1` (`pages_after_close < pages_before_close`). Nếu lỗi trước bước đóng này, tab gốc được giữ nguyên; trong mọi trường hợp lỗi sớm, không bao giờ đóng page cuối cùng.
3. **Mở lại app trên tab mới sau khi tab gốc đã đóng & kiểm tra Member:** Chỉ sau khi kiểm tra `page.isClosed() === true` ngay trước `goto`, mới điều hướng tab mới trống tới `http://127.0.0.1:8088/#/sessions/10000000-0000-4000-8000-000000000099` cho lần tải app đầu tiên trên tab mới và ghi nhận `destination_loaded_after_original_closed = true`. Sau đó kiểm tra origin, kích hoạt semantics, xác nhận chi tiết buổi chơi của Member (`UI Flow Session published to complete`, `Phần phí của tôi`), vắng mặt `Tài chính & thu tiền` / `Tổng kết buổi` / `Tài chính tổng hợp`, mở `Phần phí của tôi` và đối chiếu `Phải trả`, `Đã trả`, `Còn lại` bằng regex dựng động từ `EXPECTED_FEE` (định dạng `.toLocaleString('en-US')` + `VNĐ` kèm ranh giới chữ số). Lưu ý: tab gốc đã đóng trước các assertion đích; nếu assertion đích lỗi, tab mới (page cuối cùng) vẫn được giữ nguyên.
4. **Khôi phục identity trên tab mới & đăng xuất:** Điều hướng từ tab mới về `Tài Khoản`, xác nhận vẫn là `membera@example.test` (`Đã xác thực`), sau đó đăng xuất qua UI thật (`Đăng xuất` → `Đăng Xuất`), chờ trạng thái khách (`Bạn đang xem dưới dạng khách`, `Đăng Nhập / Đăng Ký`) và xác nhận số lượng auth key trong `localStorage`/`sessionStorage` bằng `0` (chỉ đếm key, không đọc giá trị).
5. **Deep link khi là khách:** Điều hướng trực tiếp tab mới tới `/#/sessions/10000000-0000-4000-8000-000000000099`, xác nhận tiêu đề công khai và CTA `Đăng nhập để đăng ký`, đồng thời không lộ `Tổng kết buổi`, `Tài chính & thu tiền`, `Phần phí của tôi`, `Phần phí của bạn`, `Tài chính tổng hợp`, `200,000`, `100,000`.
6. **Dọn dẹp & kết quả:** Khối `finally` luôn khôi phục `context.setOffline(false)`, gỡ listener và không nuốt lỗi dọn dẹp. Chỉ trả về boolean, số đếm kỳ vọng và trạng thái (`tab_reopen.status = 'PASS'` chỉ khi `original_tab_closed`, `destination_loaded_after_original_closed` và toàn bộ assertion đích đạt; `browser_cold_restart`, `clipboard`, `qr` gắn nhãn `NOT_RUN`), giữ thông báo lỗi cố định an toàn và không trả raw snapshot, text riêng tư, token hay dữ liệu ngân hàng.

## 2. Kiểm kê độ phủ Web hiện có so với các hàng V2 còn thiếu

| Hạng mục V2 (theo [§4.3](bh07_readiness.md#43-v2--mobiledevice-browser-khác-offlinereopendeep-link)) | Trạng thái hiện tại | Bằng chứng / Ghi chú |
|---|---|---|
| **Luồng đọc Web read-only** (Guest deep link, Owner summary, F5 reload, cùng-document Owner → Cohost → Member, offline refresh + online retry HTTP 200, Member own fee) | Đã đo local trên Edge & Playwright Firefox headless | [web_matrix_runtime_20261111.md](web_matrix_runtime_20261111.md), [manifest.json](web_matrix_20261111_evidence/manifest.json); không ghi nhận thao tác ghi DB. |
| **Workflow writes trên Web** (Member báo chuyển khoản → Owner xác nhận payment + ledger entry, QR fallback, Cohost clipboard) | Chỉ có lượt Chrome kế thừa (không độc lập QA #2); **NOT RUN** trên Edge/Firefox matrix mới | [web_local_runtime_20261110.md](web_local_runtime_20261110.md) (`e0fd485`). Kịch bản matrix mới và `web_reopen_scenario.js` là **read-only**, không thay thế kiểm thử ghi/write-retry trên Edge/Firefox. |
| **Same-profile tab close/reopen + guest deep link sau logout** | **NOT RUN** (vừa bàn giao script) | [web_reopen_scenario.js](../../../scripts/bh07_browser/web_reopen_scenario.js); chờ Codex chạy nối tiếp trong cùng named session. |
| **Full browser cold restart** (tắt hẳn tiến trình trình duyệt rồi mở lại profile) | **NOT RUN** | Kịch bản mới chỉ kiểm same-profile tab close/reopen; đánh dấu tường minh `browser_cold_restart: NOT_RUN`. |
| **Firefox headed (có cửa sổ)** | **UNKNOWN / NOT RUN** | Chưa xác minh hình ảnh Flutter ở chế độ có cửa sổ ([web_matrix_runtime_20261111.md](web_matrix_runtime_20261111.md)); chỉ chụp ảnh màn hình ở trạng thái **guest** sau khi hoàn tất reopen/logout (tránh chụp tại màn hình phí Member có dữ liệu ngân hàng). |
| **Safari / macOS** | **NOT RUN** | Chưa có môi trường macOS/Safari trong chuỗi đo Windows hiện tại. |
| **Mobile / Native (Android & iOS thật)** | **NOT RUN** | Android đã dừng theo yêu cầu chuyển sang Web ([web_local_runtime_20261110.md](web_local_runtime_20261110.md)); iOS chưa chạy. |

## 3. Lệnh gợi ý cho Codex (named sessions, cùng context)

Chạy nối tiếp `web_matrix_scenario.js` rồi `web_reopen_scenario.js` trong **cùng named session** (`-s=...`) trên bản Flutter Web profile phục vụ tại `http://127.0.0.1:8088` và stack local đang chạy:

### Edge (headless / mặc định)

```powershell
playwright-cli -s=bh07-edge-v2 open about:blank --browser=msedge
playwright-cli -s=bh07-edge-v2 run-code --filename=scripts/bh07_browser/web_matrix_scenario.js
playwright-cli -s=bh07-edge-v2 run-code --filename=scripts/bh07_browser/web_reopen_scenario.js
playwright-cli -s=bh07-edge-v2 close
```

### Firefox headless

```powershell
playwright-cli -s=bh07-ff-headless-v2 open about:blank --browser=firefox
playwright-cli -s=bh07-ff-headless-v2 run-code --filename=scripts/bh07_browser/web_matrix_scenario.js
playwright-cli -s=bh07-ff-headless-v2 run-code --filename=scripts/bh07_browser/web_reopen_scenario.js
playwright-cli -s=bh07-ff-headless-v2 close
```

### Firefox headed (chỉ chụp ảnh màn hình guest sau reopen/logout; tránh chụp màn hình phí Member)

```powershell
playwright-cli -s=bh07-ff-headed-v2 open about:blank --browser=firefox --headed
playwright-cli -s=bh07-ff-headed-v2 run-code --filename=scripts/bh07_browser/web_matrix_scenario.js
playwright-cli -s=bh07-ff-headed-v2 run-code --filename=scripts/bh07_browser/web_reopen_scenario.js
playwright-cli -s=bh07-ff-headed-v2 screenshot --filename=ff_headed_guest_after_reopen.png
playwright-cli -s=bh07-ff-headed-v2 close
```

*(Lưu ý cho Codex khi thực thi và lập gói bằng chứng: thu nhận trước/sau DB fingerprint và giữ nguyên quy tắc không lưu raw snapshot, token hoặc thông tin ngân hàng riêng tư vào artifact.)*
