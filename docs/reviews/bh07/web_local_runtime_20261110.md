# Web local runtime — 10/11/2026

**Đã thực hiện kiểm thử Web local bổ sung; chưa nghiệm thu V2/V2b/BH-07/V8.** Owner yêu cầu ngừng kiểm thử Android và chuyển webapp, ủy quyền chạy lệnh kiểm thử/Playwright. Codex trực tiếp thao tác UI Chrome bằng Playwright CLI và đọc SQL local. Chưa nhận đây là runtime QA độc lập thứ hai.

**Review độc lập source/artifact đã chốt:** không phát hiện P0/P1/P2 trong phạm vi smoke test và claim giới hạn này; reviewer tự xác minh15/15manifest hash, xem ảnh và snapshot, đối chiếu hai SQL artifact, không chạy Chrome/Android lại. Codex cũng kiểm44relative file links tồn tại, main.dart.js served hash khớp observations và hai payment state nhất quán. Một câu trạng thái Android cũ được đánh dấu lịch sử theo góp ý; không đổi kết luận kỹ thuật hoặc nghiệm thu các cổng còn thiếu.

## Môi trường và phạm vi

Source HEAD `e0fd485`; khi build có pending docs và generated plugin line-ending changes của Flutter, không có diff app/backend/migration source. Generated files đã đối chiếu nội dung HEAD rồi khôi phục CRLF. Flutter3.47.9 profile Web, Chrome157, server chỉ bind `http://127.0.0.1:8088`; build cuối49.0s, không wrapper thay app. Hash `main.dart.js` trong [observations](web_local_20261110_evidence/observations.json).

Backend dùng tiếp4container local `bh07-android-*` và dataset Android vừa thử, **không reset/seed lại**. Buổi fixture `10000000-0000-4000-8000-000000000099` đã completed/version3, một active revision với tổng200000VND. Không sử dụng remote Supabase. Public anon key local hết hạn được gia hạn24h, reload Kong rồi kiểm Auth/REST200 và build lại web; lần probe ngay sau reload nhận401 trước khi worker mới sẵn sàng, lần sau200. Không đưa secret/service-role vào frontend.

Điện thoại đã ngắt USB khi chuyển nhiệm vụ. Lệnh force-stop và gỡ reverse trả device-not-found; không tuyên bố đã force-stop app trên điện thoại. Không còn thao tác/chụp màn hình/đo Android sau yêu cầu chuyển Web.

## Quan sát và đối chiếu

| Kiểm tra | Bằng chứng/kết quả |
|---|---|
| Owner login → history → summary | UI login thành công. [History](web_local_20261110_evidence/owner_history.yml) có buổi completed. [Summary trước payment](web_local_20261110_evidence/owner_summary_before_payment.yml): có mặt2, vắng0, confirmed2; chi phí200000, phải thu200000, đã thu0, còn200000VND. |
| F5 | [Account sau F5](web_local_20261110_evidence/owner_account_after_f5.yml) vẫn Owner xác thực. Không kết luận route summary được giữ sau F5; app trở về màn gốc. |
| Logout và cùng-document actor switch | [Guest sau logout](web_local_20261110_evidence/logged_out.yml), auth storage entries0. [Cohost account](web_local_20261110_evidence/cohost_account.yml) và [summary](web_local_20261110_evidence/cohost_summary.yml) chỉ số lượng2/0/2, không có group tài chính của Owner. `performance.timeOrigin=1794317947066.6` giữ nguyên từ trước logout Owner qua Cohost và Member. |
| Cohost clipboard | Sau click nút sao chép, đọc clipboard của profile riêng:150ký tự, có attendance count và không có mẫu số tiền100000/200000 hoặc VNĐ/VND. Đây là check hẹp, không suy thành toàn bộ dữ liệu private/heap sạch. |
| Offline read refresh → online retry | Browser context offline thật. [UI offline](web_local_20261110_evidence/cohost_offline.yml) báo “Chưa làm mới được tổng kết” và dữ liệu lần tải trước; [Thử lại sau online](web_local_20261110_evidence/cohost_recovered.yml) tải lại count-only. Không thử write-retry/idempotency trong lượt này. |
| Deep link đã có auth | `/#/sessions/...0099` mở đúng chi tiết cho Cohost và Member. Không coi là cold-start/pre-login deep-link matrix. |
| Member | Account Member xác thực trong cùng document. History quản lý trống; deep link mở buổi tham gia, chỉ có phần phí của mình, không có nút tổng kết/quản lý thu tiền. Phải trả100000, đã trả0, còn100000VND. |
| QR fallback | Fixture dùng bank giả; request ảnh VietQR gặp CORS/resource error. UI hiển thị lỗi ảnh và thông tin thay thế/copy. Không chứng minh QR bank thật hay V6; không có giao dịch ngân hàng thật. [Snapshot đã redact](web_local_20261110_evidence/member_fee_submitted_redacted.yml). |
| Member báo đã chuyển khoản | Chỉ tạo một payment submitted100000, confirmed_paid0 và payment ledger entries0, [SQL](web_local_20261110_evidence/member_submitted_db.json). Không giả thành đã nhận tiền. |
| Owner xác nhận khoản thử | [UI đã redact](web_local_20261110_evidence/owner_payment_confirmed_redacted.yml) và [SQL](web_local_20261110_evidence/owner_confirmed_db.json): một payment confirmed100000, một payment-ledger entry; Member còn0, Guest còn100000. |
| Tổng kết cuối | [Snapshot](web_local_20261110_evidence/owner_final_summary.yml), [ảnh đã xem](web_local_20261110_evidence/owner_final_summary.png): tổng phải thu200000, đã thu100000, còn100000VND. |

## Bằng chứng và giới hạn

[Manifest](web_local_20261110_evidence/manifest.json) hash15file.12artifact được sao nguyên byte;2snapshot Member/Owner payment được redact bank/receiver/reference và ghi rõ tên, không nhận là bản sao raw. `observations.json` là ghi chép kết quả các lệnh/quan sát trong hội thoại, không phải một runner tự động chạy toàn bộ rồi tự kết luận PASS. Không commit raw auth/network log, password, private env, JWT hoặc browser storage.

Trong lượt này có lỗi resource offline dự kiến và2lỗi QR CORS/resource; một warning Noto thiếu glyph, đã xem ảnh tổng kết không thấy lỗi bố cục chính. Không ghi “console sạch” cho toàn lượt. Một số thử tự động Back/field/identity locator timeout do navigation/Flutter semantics, đã dùng snapshot và thao tác field riêng để tiếp tục; không tính những script lỗi là test PASS hoặc khẳng định app lỗi từ timeout đó. Phép đọc `document.body.innerText` không dùng làm bằng chứng privacy vì Flutter semantics có shadow DOM; dùng snapshot và clipboard check nêu trên.

Đây là một Chrome/local dataset, không thay matrix Firefox/Edge/Safari/iOS, write-retry/late-response suite hoặc toàn heap/listener/instructions/native. Không sửa source product và không rerun full suites không liên quan; giữ các kết quả suite kế thừa theo source của chúng. Backend/server/Chrome profile riêng giữ chạy để owner tiếp tục thử, profile đã online; không xóa dataset đang dùng. Reviewer sẽ audit source/artifact/phương pháp, không nhận là đã chạy Chrome lại.

[Ma trận hiện hành](bh07_completion_status_20261110.md), [quyết định môi trường/rủi ro còn thiếu](bh07_v8_risk_decision_packet_20261110.md). Không merge/deploy/pilot/BH-08 hoặc ký thay owner.
