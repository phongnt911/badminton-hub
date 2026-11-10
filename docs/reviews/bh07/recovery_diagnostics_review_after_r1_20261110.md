# Review sau sửa diagnostics vòng1/3 — 10/11/2026

**Chưa đạt, còn RD3 P2 về kiểu metadata và hướng dẫn probe.** Base `15f981b`, Anti cùng conversation `ae525d38-c7e1-4e4c-910a-5d740ba08648`, đã bàn giao không timeout. RD1 đã đóng:50 runtime-collection PASS (không còn7AttributeError), source/target login hook đúng và test không sleep20s. RD2 đã đóng trong boundary mới: predefined error labels, reviewer control4markerpublication đều false. V5b22test PASS, production V5b không đổi.

## Phần cần sửa vòng2/3

- **RD3 P2 — runner:274,312,853,862,868,880,885,891,1752,1770:** phép membership trong frozenset cần kiểm kiểu chuỗi trước. `err.operation=[]` qua main gây TypeError “unhashable type:list” trong error handler thay vì persisted staged FAIL; validator có cùng lỗi với operation/stage dạng list/dict. Reviewer subagent tái hiện độc lập. Yêu cầu kiểm type trước membership tại resolver/sink/validator; invalid list/dict/number/bool phải tạo finding hoặc safe fallback, không ném exception trong reporting. Metadata alias `failed_operation` nếu giữ thì kiểu không phải dict phải bị từ chối, không bỏ qua. Thêm control cho các vị trí public metadata; không nới gate.
- **RD4 P2 — handoff:34–37,87–88:** đã ghi probe lịch sử và test mới đều truyền prefix, nhưng vẫn hướng dẫn chạy probe cũ kỳ vọng0failure. Reviewer chạy thực có16errors,0assertionfailures vì duplicate-prefix, không phải replay PASS. Giữ file lịch sử nguyên byte, ghi rõ không tương thích; dùng16control mới hoặc probe thích ứng mới (kwargs prefix chỉ được truyền một lần). Không khẳng định probe cũ đã xác minh code hiện tại.

## Kiểm chứng và provenance

Codex50V4 runtime-collection,22V5b,56concurrency,6supplemental PASS (=134test),49probe controls PASS. Reviewer riêng50V4+22V5b PASS và direct unhashable metadata/probe-compatibility controls như trên. Log `.build/recovery-diagnostics-after-r1-*.log`; full suite đang chờ kết thúc khi lập báo cáo, không suy targeted xanh là full xanh hoặc runtime.

Source hash SHA-256: runner `4e385664379e21da8110a9b06898b55639b715cef8bb3bee4b00a6e6d05fa7c5`; runtime tests `cc93b90cf538f116e2de2ff802c3d210feb9ec4076eb33d7fea875bdeed43115`; V5b tests `22a60786a8843acfef5248654b3039fd7a823f1af8685edce5edb0604fc57bfe`. Không có Docker mới. Toàn BH-07/V8 chưa nghiệm thu; chỉ giao sửa scope hẹp và đợi bàn giao trước review.
