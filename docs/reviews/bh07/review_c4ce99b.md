# Review, tự sửa và đóng công việc feat/bh07-browser-verification

Ngày23/10/2026. **Đạt trong phạm vi kiểm chứng local Browser / Offline / Reopen và hai lịch response Owner trả trễ được giao; đóng công việc trên nhánh.**

Chủ dự án giao trực tiếp Codex review, tự sửa và đóng gói. **Codex vừa triển khai vừa review/tự sửa: KHÔNG phải review độc lập.** Không mở vòng bàn giao/chờ review tiếp cho gói này. Không nghiệm thu toàn BH-07/production/pilot.

- Review đầu vào: docs/evidence `7839bba99e09ba06e72bc88b9ff5648da5ff59db`.
- Source hai ca browser trễ: `c4ce99bcd9a9b02c4b794c8eb5ab51e43c06155a`; mốc baseline/Flutter khác được bảo lưu trong [bàn giao](late_response_handoff.md).
- Source sau sửa control để đóng: `417ee30cf1fa2da4c64b03e0474d6c8c4a1dca6c`.
- Phần sửa trong lượt này: chỉ `scripts/bh07_browser/run_late_response_controls.js`; không thay app, backend, helper assertion hay runner browser.

## Phát hiện và sửa

### P0 / P1

Không phát hiện trong phạm vi review.

### P2 — hai negative control chưa cô lập lỗi (đã sửa)

- **File:dòng hiện hành:** `scripts/bh07_browser/run_late_response_controls.js:33`, `:37`; mutation check tại `:52`.
- **Trước sửa:** control Member có nút copy kế thừa surface Cohost (không phải lịch sử rỗng) và thiếu summaryEntry=false. Control finance-card leak có hai sample rỗng, thiếu các flag bắt buộc. Vì thế guard copy hoặc finance-card bị bỏ vẫn bị lỗi khác làm test FAIL, che mất hồi quy của đúng guard cần kiểm.
- **Tái hiện:** lấy control cũ từ blob7839bba, chạy helper thật với lần lượt một guard bị vô hiệu trong VM. Cả2 mutant không bị control tương ứng phát hiện; probe báo exit1, dù bộ control cũ vẫn đúng21 kỳ vọng.
- **Cách sửa đã làm:** dùng một Member positive fixture đầy đủ, chỉ đổi copyAvailable=true; dùng sample hợp lệ hoàn chỉnh, chỉ đổi đúng financeCard của sample đầu. Thêm mutation checks chạy helper thật bị thay một guard trong bộ nhớ, bắt buộc đúng control tương ứng phát hiện hồi quy. Không thay expectation hoặc logic ứng dụng.
- **Sau sửa:**21/21 control giữ đúng kỳ vọng; hai mutant đều được đúng ca tương ứng phát hiện. **Đóng cả2 P2 về độ mạnh test.** [Red](browser_closure_evidence/red_controls.log), [green/mutants](browser_closure_evidence/controls.log), [probe](browser_closure_evidence/red_control_probe.js).

Không còn P0/P1/P2 mở trong phạm vi chốt này. Không xem các cổng ngoài phạm vi là lỗi app đã được chứng minh.

## Kiểm chứng và giới hạn kết luận

**Chạy mới trong lượt review/tự sửa chốt:**21 control +2 mutant riêng,41 regression controls,9 probe reviewer cũ,9 verifier fault controls trên copy gói52 file,manager-gate mutant. Verify trực tiếp hai manifest52/52 và44/44; snapshot toàn bộ file/manifest không đổi. [Bằng chứng mới](browser_closure_evidence/), [audit](browser_closure_evidence/audit.json).

**Kế thừa kết quả tự chạy trước trên đúng app/driver/helper không đổi**, không gắn lại SHA hoặc coi là lần chạy mới: analyze0 issue,240 Flutter+1skip,Web build PASS,11/11 baseline browser và2/2 browser response trễ. Hai response POST Owner200 được giữ khoảng44,7/40,5 giây, thả sau login Cohost/Member; body hash nguyên vẹn, timeOrigin không đổi,4 sample mỗi ca. Cohost giữ count-only và clipboard không tiền; Member giữ empty history và không có summary/copy trên bề mặt đã thử. Các mốc thực chạy0a2b95f/c4ce99b và tree hash app được giữ trong [environment](late_response_evidence/environment.json).

Đã rà đường CDP Fetch→HTTP status/body→delivery, chỉ POST (không lấy OPTIONS), temporal guard, same-document guard, actual Owner positive/negative, UI/copy sau delivery, xử lý lỗi và source provenance. Đổi mới chỉ ở dữ liệu control nên không dựng lại stack/không chạy lại Flutter/HTTP/DB trong lượt chốt. Không có app/lib/test/supabase thay đổi so với base1ed4f3e; các bundle evidence cũ không bị sửa.

## Đóng công việc / trạng thái Git

- **Đóng công việc trên feat/bh07-browser-verification; Đạt local theo review và tự sửa của Codex.** Không để trạng thái Chờ review hiện hành cho gói này.
- Git ref của nhánh được giữ vì chưa merge; không xóa phần chưa tích hợp. Không merge main/deploy/apply DB thật.
- Không tìm thấy PR khớp nhánh qua GitHub connector; không tạo/đóng/merge PR. `gh` trực tiếp bị network Forbidden; connector read-only là đường kiểm tra thay thế.
- Giữ toàn bộ lịch sử Chưa đạt/Chờ review và bằng chứng theo mốc; trạng thái mới không sửa kết luận lịch sử.

## NOT RUN

Review độc lập; đo trực tiếp private Dart heap trong browser;mobile/thiết bị/browser khác;ngân hàng/VietQR/webhook;staging/production/backup/restore;rehearsal/pilot;nghiệm thu toàn BH-07;full Supabase db reset.23/335 DB regressions không chạy lại trong scope không đổi backend.

Cache được đánh giá qua hành vi UI/copy và unit provider guard đã có; không coi empty Member UI là phép đo private heap. Không suy hai lịch response cụ thể thành bảo đảm cho mọi cache/RPC/race. Các giới hạn này được giữ khi đóng công việc local.

**Kết luận: Đạt local — đã đóng công việc trên nhánh, tự review/tự sửa, không độc lập.**
