# PaymentInstructions heap — review triển khai đầu, 13/11/2026

**CHƯA ĐẠT; chưa chạy smoke/DB/browser.** Base159d896, new companion tooling/test từ Anti `gemini-4-hydrogen-high`, `--print-timeout0`. Codex tự chạy13Python và5Node control groups PASS, nhưng không dùng các test đó để bỏ qua phát hiện review.

Reviewer riêng và Codex phát hiện:

| ID | Mức | Phát hiện | Gate sửa |
|---|---|---|---|
| IH1 | P1 | dumps_dir ngoài repo có sẵn vẫn được dùng rồi xóa recursive; snapshot output cũng có thể overwrite | Chỉ claim thư mục/file mới thuộc run, kiểm canonical path/link/ownership trước xóa; giữ nguyên dữ liệu có sẵn |
| IH2 | P2 | progress.finished có thể đến trước snapshot chunks; code ngừng nhận chunk quá sớm | Nhận tới takeHeapSnapshot command completion rồi drain writer; cap/write failures fail-closed |
| IH3 | P2 | same_document_across_cycles=false/missing bỏ qua so sánh timeOrigin | Bắt buộc true, so sánh mọi cycle/epoch thực tế; control origins1/2 từng được chấp nhận sai |
| IH4 | P2 | Một substring receiverSnapshot/FinanceProvider bất kỳ đủ gán DTO attribution | Ordered app property path và source binding hoặc giữ UNKNOWN; control XHR-buffer label từng được chấp nhận sai |
| IH5 | P1 | DB cleanup thất bại vẫn xóa fixture_state; state write không atomic như handoff | Giữ state phục hồi riêng tư khi DB cleanup lỗi, raw dump vẫn xóa; persist atomic trước INSERT |
| IH6 | P2 | Thiếu baseline vẫn baseline_equal=true; bỏ qua mọi auth sequence | Thiếu baseline fail receipt, vẫn dọn row có sở hữu; chỉ loại biến đổi refresh-token sequence đã khai báo |

Đã giao sửa vòng1/3, chỉ sáu file mới đã giao. Không sửa app/schema/bundle cũ. Kết quả review là source/control, không phải independent runtime. Full V2b/BH-07/V8 chưa nghiệm thu; không merge/deploy/pilot/BH-08.

## Sau sửa vòng1

Codex và reviewer chạy riêng17Python/5Node groups PASS. Reviewer xác nhận IH1–IH4 đã sửa cấu trúc; missing baseline fail-closed, state phục hồi nằm ngoài raw dump và giữ lại khi DB cleanup lỗi. Còn IH5 P2: unlink state lỗi nhưng cleanup predicate bỏ qua recoveryStateRetained vẫn có thể PASS. Đã giao vòng2 yêu cầu state absence bắt buộc khi cleanup thành công; lỗi thì FAIL và giữ receipt phục hồi. Root bổ sung yêu cầu bảo toàn partial-cycle scans và tránh dùng biến document origin ngoài scope trong finally. Runtime vẫn NOT RUN.

## Sau sửa vòng2 — source/control gate

Codex19Python/8Node groups PASS; reviewer chạy riêng19Python/8Node PASS. IH5 đóng trong runner/CLI/verifier: state còn hoặc unlink báo lỗi thì cleanup FAIL; DB cleanup lỗi vẫn giữ state phục hồi riêng tư. Partial-cycle scans/failure stage được giữ, origin scope an toàn và incomplete cycles không thể PASS. Reviewer không thấy P0/P1/P2 mới trong correction delta; đủ gate cho Codex smoke local. Không phải independent runtime hoặc DTO attribution đã đo; runtime tại checkpoint source này vẫn NOT RUN.
