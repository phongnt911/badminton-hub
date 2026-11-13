# Finance Auth listener — review triển khai đầu

**Chưa đạt source gate; live runtime NOT RUN.** Base de644c3. Anti triển khai5file mới, Codex chạy5Python và Node controls PASS; reviewer chạy riêng5Python nhưng semantic scratch controls tìm false-PASS. Không dùng test xanh thay review.

| ID | Mức | Phát hiện | Gate sửa |
|---|---|---|---|
| FL1 | P2 | Wrapper/mocks dùng sai response HeapProfiler.getObjectByHeapObjectId (`object` thay `result`) | Wire-shape control thực tế và remote class/type binding |
| FL2 | P2 | Auditor tin count/flag tổng hợp dù slot receiver/method sai | Tái tính từng active slot, index duy nhất/liên tục, receiver identity và method prototype chính xác |
| FL3 | P2 | CDP time origins thiếu vẫn được chấp nhận; metadata currentUser thiếu có thể coi non-null | Bắt buộc typed finite origins/metadata và đối chiếu epoch; không bool-coerce |
| FL4 | P2 | Node name của string sai kiểu có thể được công bố như class_name | Chỉ metadata cấu trúc được phép, raw string không xuất hiện cả artifact FAIL |

Root yêu cầu giữ diagnostics an toàn của failed epoch thay vì mất khi hook throw trước khi runner lưu scan. Đã giao Anti sửa vòng1/3; chưa chạy DB/browser. Scope chỉ Auth→FinanceProvider và2field _instructions/_finance; full Auth listeners/V2b/BH-07/V8 chưa nghiệm thu. Không merge/deploy/pilot/BH-08.

## 14/11 — Sau sửa vòng1

Codex và reviewer chạy riêng9Python và Node controls PASS. Reviewer xác nhận FL1–FL4 đóng, failed epoch diagnostics được giữ an toàn. Handoff đã được hoàn tất đúng file có ngày sau khi Anti bị từ chối ghi nhầm tên ngoài phạm vi; không mở quyền ngoài5file được giao.

Root và reviewer pure-bind trên actual main.dart.js SHA a20b3d22… đều tái hiện P2 `FinanceProvider_prototype_unclosed`: prototype lớn hơn budget32KiB của helper constructor dùng lại. Live runtime chưa chạy. Đã giao sửa vòng2 với budget prototype riêng có giới hạn/controls, giữ nguyên constructor cap và helper cũ; không nới data gate.

## 14/11 — Sau sửa vòng2, chờ vòng3

Root10Python/Node controls PASS. Prototype budget riêng đã qua điểm lỗi cũ, nhưng actual binding tiếp tục FAIL `finance_field_ambiguous_or_missing:[]`: matcher dựa trên dạng synthetic `new SessionFinance` trong provider, trong khi artifact dùng `$async$self._finance = finance` sau repository await. Factory wiring thật có các câu khởi tạo authUserId giữa new provider và addListener nên pattern liền kề cũng chưa tương thích. Đã giao Anti vòng3/3 hỗ trợ data flow/alias/factory thực tế với source-bound identity và negative controls; không fallback chấp nhận tên field cứng hoặc chỉ thấy RPC string. Live runtime vẫn NOT RUN; không retag test synthetic thành runtime.

## 14/11 — Vòng3 và Codex sửa trực tiếp

Actual build binding R3 PASS trên main.dart.js a20b3d22…; root/reviewer11Python và Node controls PASS. Reviewer tìm P2 resume parameter bị ghi đè vẫn binding ok=true. Codex thêm control tái hiện RED, trực tiếp chặn reassignment/compound/update của result parameter và alias; không giao Anti vòng4. Actual bind sau sửa exit0. Runtime vẫn NOT RUN tại checkpoint source; chưa kết luận toàn listener graph/BH-07.
