# Chốt diagnostics + V5b source/test sau sửa vòng2/3 — 10/11/2026

**Đạt trong delta Tasks1+2, không có P0/P1/P2 còn mở trong phạm vi đã review.** Base `15f981b`, Anti triển khai conversation `ae525d38-c7e1-4e4c-910a-5d740ba08648`, không timeout. Codex review/chạy test; reviewer subagent riêng không triển khai đọc delta và kiểm chứng độc lập. Chưa có Docker runtime mới, không nghiệm thu V4/BH-07/V8.

## Kết quả sửa

- V5b fake command và assertion dùng đúng cặp token liền kề db/reset;16path/inventory controls giữ gate nghiêm, production V5b không đổi.
- Stage mới chỉ nhận hằng tiền định; command failure có structured identity/exit, sink kiểm whitelist/kiểu int thật. Không parse danh tính từ text lỗi tự do; new-stage error_message là label tiền định.
- Raw-operation dạng list/dict và các metadata sai kiểu được từ chối trước membership; validator tạo finding thay vì TypeError. Alias failed_operation sai kiểu không bị bỏ qua.
- Test main nằm trong class có harness, source login thành công trước khi hook target login thất bại; không sleep20s trong mock test.
- Handoff ghi probe lịch sử không tương thích vì duplicate-prefix16errors; không sửa byte probe cũ,16subtests mới kiểm cùng điều kiện. Codex chuẩn hóa link file máy riêng thành relative portable trong tài liệu bàn giao.

## Bằng chứng

Codex candidate sau vòng2:52runtime-collection+22V5b+56concurrency+6supplemental =**136PASS**, probe49/49PASS, exit0. Reviewer độc lập chạy52/52V4PASS và replay4publication controls: raw command message, replay message, unlisted operation, non-int exit đều không được công bố; source hash-before/after trùng. Reviewer xác nhận RD3/RD4 đóng, không còn P0/P1/P2 trong delta và scoped GO cho diagnostic runtime.

Runner SHA-256 `d9fe381d5d54837cb579caf00212baed53b4a244afdb20ca436f4ce635cc5205`. Log `.build/recovery-diagnostics-after-r2-*.log`; reviewer script `.build/recovery-diagnostics-r1-controls.py`. Full R1source550test/546PASS+4SKIP,135.904s thuộc trước hai test/type guards mới. Full candidate vòng2 đã kết thúc riêng: **552test/548PASS+4SKIP**, exit0,160.534s; source code không thay trong lượt chạy này.

## Giới hạn và bước kế

Chỉ diagnostics an toàn và harness được sửa. Không đo service health hoặc sửa cấu hình recovery từ suy đoán. V4 runtime mới nhất46c9d98 vẫn FAIL sau restored fingerprints/padding check; stage mới cần được chạy trên candidate sạch để xác định boundary lỗi thực. Không gọi source/test xanh là oracle/replay PASS. Flutter mới NOT RUN, app/schema không đổi.

Theo ủy quyền mới owner, nếu phần sửa recovery tiếp theo còn lỗi sau3vòng Anti thì Codex tự sửa; không dừng để hỏi lại chuyển vai. Điều này không cấp quyền risk acceptance/merge/deploy/pilot/BH-08.
