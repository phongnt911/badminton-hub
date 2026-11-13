# V2 Web — synthetic payment, 13/11/2026

**Đạt local trong phạm vi Guest gửi → Owner xác nhận → Guest đọc lại trên Edge/Firefox headless; toàn V2/BH-07/V8 chưa nghiệm thu.** Base `4c48b86` trên `feat/bh07-completion-local`; working tree có test/tooling/docs mới. Anti CLI dùng `gemini-4-hydrogen-high`, `--print-timeout 0`; Codex review và chạy UI/DB. Không sửa app/backend/migration, không chuyển tiền thật hay gọi ngân hàng/webhook.

## Kết quả mới

| Mốc | Edge157 headless | Playwright Firefox156 headless |
|---|---|---|
| Guest A gửi100000 qua UI thật | PASS: một POST submit_payment200, payment submitted, đúng player/request/amount/method | PASS cùng gate |
| DB ngay sau submit | PASS: paid0, outstanding100000, ledger0; đúng Guest, confirmed_by/confirmed_at NULL; đúng request có một operation và một PAYMENT_SUBMITTED audit | PASS cùng gate |
| Owner xác nhận đúng payment qua UI | PASS: một POST confirm_payment200, payment confirmed, response ledger UUID hợp lệ | PASS cùng gate |
| DB sau confirm | PASS: đúng Owner và timestamp, một income ledger100000 liên kết đúng payment/club/actor/response ledger ID; từng request submit/confirm có một operation/audit đúng entity_type/payment | PASS cùng gate |
| Owner tổng kết | PASS: số lượt2/0/2, chi phí/phải thu/đã thu/còn thu200000/200000/100000/100000 | PASS cùng kỳ vọng |
| Guest đăng nhập mới đọc lại | PASS: due100000/paid100000/outstanding0, không còn submit CTA/QR, không quản lý/tổng kết | PASS cùng kỳ vọng |

Hai browser dùng fixture UUID khác nhau, mỗi pha dùng profile thử mới. Fixture được **seed trực tiếp ở completed/current**, có hai charge100000 và receiver giả sao chép từ fixture local kế thừa; không sao chép payments/ledger. Đây không phải lần đo start/chốt phí/lifecycle mới, không chứng minh chuyển actor trong cùng document. Luồng lifecycle/actor trước giữ theo [báo cáo kế thừa](web_lifecycle_copy_runtime_20261113.md).

Test chỉ abort ảnh QR ngoài để tránh tải thông tin chuyển khoản ra dịch vụ ngoài; local API không bị mock. “Tôi đã chuyển khoản” chỉ ghi ý định thanh toán giả trong DB thử. Submitted chưa được tính là paid; ledger chỉ xuất hiện sau xác nhận của Owner. Không đo offline-payment, replay sau commit, cash/reject/reverse hoặc ngân hàng live trong lượt này.

## Oracle và các lần lỗi

- Wrong-expected-amount100001 bị UI oracle từ chối **trước submit**; đọc DB xác nhận fixture vẫn payments0/audits0/operations0. Bản đúng100000 chạy qua. Source controls kiểm 9 payload mutant, 3 money cases, 4 JSON cases, target/method/origin và mutation không mong đợi bằng chính helper đang chạy.
- Reviewer source/control phát hiện P2 trong oracle DB của Codex: thiếu kiểm NULL/timestamp confirmation và entity_type audit. Ba control metadata tái hiện RED trước sửa, sau sửa 6 test methods (các mutant theo nhóm) PASS; reviewer tự chạy lại controls và chốt P2 đã đóng. Không cần sửa scenario Anti qua vòng correction.
- Review cuối không còn P0/P1/P2 trong delta: reviewer tự xác minh **22/22 manifest hash**, source/provider/build hash, **6/6 driver hash và template**, sáu kết quả UI, bốn gate DB, hai cleanup receipt và baseline fingerprint. Reviewer không chạy lại browser/DB/HTTP served hash; independent runtime giữ NOT RUN.
- Lượt Owner Edge đầu **FAIL** ở home-semantics bootstrap, trước login/confirm. Probe sau đó thấy root tab đã có, visible/focused; chưa xác lập nguyên nhân. Đóng các browser submit đã dùng và profile Owner lỗi, kiểm DB vẫn submitted/ledger0, rồi profile Owner mới chạy cùng source PASS. Giữ lần lỗi trong attempt history; không tự nhận nguyên nhân do tải máy hoặc retag lần đầu thành PASS.
- Pageerror của sáu pha cuối bằng0. Console có lỗi dự kiến từ ảnh QR bị abort; không tuyên bố console tuyệt đối sạch. Không chạy lại Flutter suite/analyze/build vì không đổi product source; dùng lại profile build và kiểm hash HTTP phục vụ trùng file build.

## Dữ liệu và bằng chứng

Hai fixture có preflight không trùng ID, transaction không upsert, marker sở hữu đọc lại. Cleanup xóa đúng ledger thuộc payment của fixture trước khi xóa session/children, audit và operation liên quan; hai receipt xác minh absent. Sau cleanup, **21 bảng public/94 dòng, schema, roles và mọi sequence khác khớp baseline**; riêng Auth refresh-token sequence **68→75** do login. Auth rows không nằm trong phép so. Không thay fixture `0099` hoặc payment/ledger cũ.

[Bundle manifest](web_payment_20261113_evidence/manifest.json) gồm22artifact: sáu kết quả UI đã bỏ UUID thô/request payload, bốn gate DB gắn hash request/payment, setup/cleanup, đối chiếu baseline, controls đỏ/xanh, provenance và recipe. Hai log control giữ nguyên whitespace của PowerShell; attributes chỉ bỏ trailing-space check cho chúng, không sửa byte đã review. Recipe là tooling Windows của máy đo, không tuyên bố runner portable.

Các browser thử đã đóng, inventory không còn browser; backend/server loopback giữ chạy. Sau review đã dọn các raw phase log/driver thử và console log thuộc lượt này có receiver/reference, kiểm tra vắng mặt và quét bundle không có giá trị receiver thô. Không công bố raw bank/reference/token/clipboard/snapshot. [Bàn giao Anti](web_payment_handoff_20261113.md) ghi trạng thái trước runtime; báo cáo này là kết quả mới hơn.

## Giới hạn nghiệm thu

Full V2/BH-07/V8 chưa đóng: Firefox headed mặc định vẫn UNKNOWN, headed input attempt cũ giữ FAIL, Firefox clipboard NOT RUN; Safari/macOS/iOS/Android và phần matrix khác chưa đủ. V2b/V3/V5/V7/V8 theo [ma trận hiện hành](bh07_completion_status_20261110.md). Không ký residual-risk acceptance thay owner, không merge/deploy/pilot/BH-08.
