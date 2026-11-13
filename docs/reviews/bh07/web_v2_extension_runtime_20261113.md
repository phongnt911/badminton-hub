# V2 Web local bổ sung — 13/11/2026

**Đạt trong phạm vi luồng đọc, tab reopen và Edge cold restart đã đo; toàn V2/BH-07/V8 chưa nghiệm thu.** Source nền `aa755b5` trên `feat/bh07-completion-local`; working tree có kịch bản reopen và tài liệu mới. Không sửa app/backend/migration. Anti CLI dùng `gemini-4-hydrogen-high`, Codex review một vòng sửa và trực tiếp chạy runtime. Reviewer riêng chỉ review source/artifact, không có lần runtime QA độc lập thứ hai.

## Kết quả và giới hạn

| Ca | Kết quả mới |
|---|---|
| Edge 157 headless: Guest deep link → Owner summary → F5 → Cohost → offline/retry → Member | PASS; tổng 200000/100000/100000, số lượt 2/0/2, retry đúng RPC/phiên HTTP 200 và UI phục hồi |
| Firefox Playwright 156 headed, software WebRender, đưa trang ra trước | PASS cùng matrix; không có page error |
| Đóng tab ứng dụng, tải lại ứng dụng ở tab mới cùng profile | PASS trên Edge và Firefox software headed; tab gốc thực sự đóng trước lần tải ứng dụng mới |
| Member được khôi phục, phí riêng 100000/100000/0; logout rồi guest deep link | PASS trên hai trình duyệt; auth storage key count = 0, không hiện quản lý/tổng kết/phí riêng ở Guest |
| Đóng hẳn Edge rồi mở lại đúng profile thử | PASS; 8 tiến trình cũ đã vắng trước khi mở lại, 8 tiến trình mới không trùng PID; xác nhận Member/phí qua UI trước khi logout |
| Firefox headed mặc định | UNKNOWN về hiển thị; screenshot Flutter trắng dù semantics có nội dung. WebGL control đọc pixel có màu, nhưng vùng canvas trong screenshot trắng |
| Firefox cold process restart, Safari/macOS, iOS/Android, workflow ghi/write-retry trên Edge/Firefox | NOT RUN trong lượt bổ sung này |
| Clipboard/QR | Không đo mới; giữ bằng chứng Chrome kế thừa và giới hạn từng browser |

Firefox software dùng cấu hình riêng `gfx.webrender.software=true`, không thay profile hay cấu hình Firefox của người dùng. Đây là cấu hình được đo, không chứng minh Firefox headed mặc định đã hết vấn đề. Lượt software đầu dừng ở `Login input frame commit timed out`; phiên sạch được `bringToFront` trước khi chạy đã PASS. Chưa xác lập nguyên nhân của lần timeout đó. Các trạng thái này được giữ trong [controls](web_v2_20261113_evidence/controls.json), không biến lần lỗi thành PASS.

Đây là luồng đọc trên fixture đã completed. Không dùng nó để nhận start→điểm danh→chốt phí→complete/write-retry đã chạy mới trên Edge/Firefox. Bằng chứng Web Chrome, Firefox headless và nghiệp vụ cũ giữ nguyên phạm vi theo [11/11](web_matrix_runtime_20261111.md) và [10/11](web_local_runtime_20261110.md).

## Kiểm chứng

- Kịch bản mới [web_reopen_scenario.js](../../../scripts/bh07_browser/web_reopen_scenario.js) compile đúng giao diện function expression của Playwright CLI. Origin ngoài loopback bị từ chối trước tương tác. Đối chứng đổi kỳ vọng phí thành 100001 dừng đúng tại oracle Member; bản đúng 100000 PASS. Review vòng 1 sửa thứ tự đóng/tải tab và nối oracle với `EXPECTED_FEE`.
- Reviewer riêng không thấy P0/P1/P2 trong delta source/handoff/artifact; tự xác minh **20/20 manifest hash**, source/build hash, ảnh mặc định trắng/software hiển thị, receipt cold restart và fingerprint DB. Reviewer không chạy lại browser/Docker hoặc HTTP served hash. Runtime do Codex thực hiện; không gọi review source/artifact là QA runtime độc lập.
- Build Flutter Web profile thành công 46.7s; hash `main.dart.js` build và HTTP phục vụ trùng. Bảy generated plugin file chỉ đổi line ending, đã đối chiếu HEAD rồi khôi phục CRLF. Không chạy lại Flutter suite/analyze vì không đổi product source; số test cũ không được nhận là lần chạy mới.
- Fingerprint trước/sau giữ nguyên 21 bảng public, 94 dòng, schema, roles và mọi sequence khác. Chỉ `auth.refresh_tokens_id_seq.last_value` tăng **45 → 55** do đăng nhập. Comparator strict ban đầu exit 1; phép so sánh bổ sung chỉ loại đúng trường này rồi xác nhận các phần còn lại trùng. Auth rows không nằm trong phép đo. [Đối chiếu DB](web_v2_20261113_evidence/database-comparison.json).
- Backend được khởi động lại từ đúng bốn container fixture hiện có, không reset/seed. Auth lần đầu thoát vì PostgreSQL đang startup; khởi động lại sau DB đã sẵn sàng khôi phục Auth/REST 200. Public anon key local được làm mới 24h và build lại; không đưa service-role/secret vào frontend hay evidence.
- Sau kiểm thử, các named browser của lượt này đã đóng; Playwright inventory không còn browser. Profile explicit Edge cold đã xóa sau khi xác minh đúng đường dẫn workspace, `Test-Path=False`. Backend fixture và server loopback giữ chạy để tiếp tục công việc local; không dọn resource khác.

[Gói bằng chứng](web_v2_20261113_evidence/manifest.json) gồm kết quả đã bỏ raw snapshot, provenance/source/build/browser hash, đối chứng, ảnh Guest/diagnostic và recipe cold restart. Raw log chứa mã kịch bản/config local chỉ ở ignored `.build`, không công bố. [Bàn giao Anti](web_v2_extension_handoff_20261113.md) ghi trạng thái tại lúc giao, trước runtime; kết quả hiện hành là báo cáo này.

## Việc còn lại

Chưa đóng full V2 theo [§4.3](bh07_readiness.md#43-v2--mobiledevice-browser-khác-offlinereopendeep-link): còn browser/OS/native ngoài môi trường hiện có, Firefox headed mặc định, các ca nghiệp vụ ghi/retry/copy/QR chưa được đo trên từng browser. Không ký chấp nhận rủi ro thay owner, không merge/deploy/pilot/BH-08. V2b/V3/V5/V7/V8 giữ theo [ma trận hiện hành](bh07_completion_status_20261110.md).
