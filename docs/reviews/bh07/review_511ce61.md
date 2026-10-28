# Review FH1–FH4 finance heap coverage — 511ce61

- Ngày: 28/10/2026, Asia/Saigon.
- Reviewer: Codex; review độc lập bản sửa vòng 1/2 của Antigravity. Không sửa source triển khai, app/backend/DB hoặc bundle lịch sử. Codex từng sửa AT1 attribution ở giai đoạn trước; không triển khai mở rộng payment hay bản sửa FH1–FH4 này.
- Nhánh: `feat/bh07-finance-heap-coverage`.
- Base: `303a6ccf4374e28188ff0d924fd39d2c8ab674dc`.
- Tested code/docs: `511ce612cb8bcc5757a6735ee14d0bacd9433721`; checkout sạch trước kiểm tra (ngoại trừ file reviewer tạm được tạo sau đó).
- Runtime evidence kế thừa: `cd25e1e3557e2013e8991b2031a240818ee84c96`; không retag thành runtime tại 511ce61.

## Kết luận

**Đạt bản sửa FH1–FH4 trong phạm vi tooling và tài liệu finance heap coverage local.** Không còn P0/P1/P2 mở trong phạm vi diff 303a6cc..511ce61 đã review. Đóng gói sửa vòng 1/2; không giao sửa vòng 2 khi chưa có phát hiện mới.

Đây không phải nghiệm thu toàn V2b/BH-07 và không phải lần đo heap độc lập mới. Quan sát payment trong bundle gốc vẫn thuộc runtime tác giả cd25e1e. Không merge main/staging/production, deploy, pilot hoặc chuyển BH-08.

## Kiểm chứng độc lập

Lệnh, exit code và log nguyên kết quả được lưu tại [review_511ce61_evidence/](review_511ce61_evidence/), xem [exits.json](review_511ce61_evidence/exits.json).

| Kiểm tra | Kết quả reviewer |
| --- | --- |
| Python unittest discover | exit 0; 331/331 |
| Flutter analyze | exit 0; no issues |
| Flutter test | exit 0; 247 passed, 1 skipped (HTTP/Auth integration opt-in) |
| Fixture controls | exit 0; 8/8 |
| Auditor finance_heap_evidence | exit 0 |
| Auditor review_runtime_b13e468_evidence | exit 0; legacy không khai payment vẫn tương thích |
| Sáu reviewer semantic controls | positive exit 0; năm negative cases đều exit 1 |

Các semantic controls phát lại nguyên `review_6f59f5e_evidence/probes.py`. Adapter chỉ đổi cách ghi clone sang UTF-8 LF trên Windows; không sửa script gốc hay bundle gốc. Lệnh inline Python bị lean-ctx chặn trước thực thi, nên lần chạy thực tế dùng adapter script `.tmp/review511_controls.py`; bản tái lập nằm tại [replay_controls.py](review_511ce61_evidence/replay_controls.py).

Case `payment_never_loaded`: oracle trả FAIL; auditor phát hiện payment_id không được gate ở cả hai chu kỳ. Các case bỏ receipt, bỏ created flag kèm cleanup error, removed=false, sai receipt hash đều bị auditor bác với finding đúng nguyên nhân. Case payment hiện diện ở baseline được kiểm tra bởi unit test `test_mutant_2b_payment_id_seen_at_baseline_fails_precondition` trong suite reviewer đã chạy.

Đối chiếu source xác nhận `_check_cycles` đòi mọi sentinel finance unrendered/distinctive được khai báo và available phải được gate ở owner_active; không còn nhận hai expense IDs thay cho payment đã khai báo. `_check_cleanup` xác định requirement từ payment metadata/scan/fixture declaration, đòi created/removed/verified_absent là true, receipt hash khớp payment_id và không có cleanup error.

SHA runtime trong handoff/map resolve đúng cd25e1e3557e2013e8991b2031a240818ee84c96 và khớp provenance gốc; tài liệu payment đã thu hẹp về chuỗi sentinel V8, đúng owner path length 21/20, không dùng absence của ID làm proof toàn model/native sạch. `payment_ref` giữ unattributed residual risk.

Readonly: adapter hash trước/sau 1.596 file evidence tracked, không đổi byte. Diff 303a6cc..511ce61 không thay file trong các bundle evidence lịch sử; không có diff lib/test/supabase. Reviewer chỉ thêm báo cáo/evidence và cập nhật trạng thái tài liệu.

## NOT RUN và giới hạn

- Runtime Chromium/heap snapshot mới và truy vấn DB xác nhận cleanup của reviewer: NOT RUN. Receipt/log được audit không thay cho lần kiểm tra DB mới.
- Đo runtime bằng validator mới trên source 511ce61: NOT RUN; runtime bundle hiện có vẫn source cd25e1e.
- Toàn FinanceCharge/FinancePayment object graph, listener Web graph, app-wide retention: UNKNOWN/NOT RUN.
- Bank/receiver/ledger/payment instructions, các field ngoài sentinel đã đo: NOT RUN.
- Dart VM desktop/mobile, browser khác, tải thật, staging/production, ngân hàng/webhook, pilot và nghiệm thu toàn BH-07: NOT RUN.

**Đạt riêng bản sửa FH1–FH4 local; toàn V2b/BH-07 chưa nghiệm thu.**
