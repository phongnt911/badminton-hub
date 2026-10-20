# Review BH-06C vòng sửa 2 — a0f7255

Ngày 20/10/2026 (Việt Nam). Tested HEAD `a0f7255c733afb053aab81d8fb42abd3ebcd3e71`, nhánh `feat/bh06c-ui`, code sửa cuối `5174e9d`, dependency B `f28fd0f` (Đạt tại `5e62007`), main `c35dd27`. Theo `docs/ai/REVIEWER.md` trên `chore/ai-roles` = `07b31d4` và AGENTS hiện hành (sửa toàn bộ P0/P1/P2, tối đa hai vòng). Đọc diff main...HEAD, đối chiếu phần sửa sau review `7c23bbb`. Source/test/migration sau `5174e9d` không đổi. Không sửa code triển khai/migration/test tác giả.

## Phát hiện còn mở

### C4 — P2: lựa chọn “Nước” gửi category mà RPC từ chối

`lib/screens/session_finance_screen.dart:38`, payload tại dòng 229. Hộp thoại “Thêm chi phí” cho chọn Nước (`water`), rồi gửi nguyên key này vào `post_session_expense`. RPC chỉ chấp nhận `court`, `shuttle`, `other` (`supabase/migrations/20261016110000_bh06_expenses_finalize.sql:173`). Host/finance nhập nội dung và số tiền hợp lệ vẫn luôn nhận INVALID_INPUT, không ghi được khoản chi đã chọn. Đây là lỗi UI C đã có từ bản đầu, chưa được phát hiện trong review trước; không phải hồi quy do sửa C1/C2/C3.

Bằng chứng: widget probe đi qua mở dialog → chọn Nước → nhập nội dung/10.000 → ghi; repository nhận `water`, kỳ vọng category thuộc contract thất bại. Probe riêng gọi RPC thực bằng app role trong buổi fixture do actor quản lý: exit 3, `INVALID_INPUT: Loại chi phí không hợp lệ`. Fixture/mock không phải nguồn duy nhất để kết luận.

Hướng sửa tối thiểu: ánh xạ lựa chọn Nước vào `other` và giữ nội dung chi phí, hoặc bỏ lựa chọn chưa được contract hỗ trợ. Không mở rộng schema/migration chỉ để hợp thức hóa key UI. Viết test luồng chọn từng loại để kiểm đúng payload được RPC hỗ trợ. Do đã hết hai vòng sửa theo AGENTS, dừng vòng tự động và báo chủ dự án; reviewer không tự viết bản sửa hay mở vòng thứ ba.

## Đối chiếu phát hiện trước

Đóng C1/C2/C3 của [review_af31e7b](review_af31e7b.md) tại tested HEAD trong phạm vi bằng chứng dưới đây. C1/C2 dùng registration ID/reference NULL; probe RPC kiểm intent sau reject, cùng key trả cùng response, trả thêm 50.000 sau refinalize và payment reference riêng, trong khi mã nội dung QR giữ ổn định. C3 dùng nhãn phí revision khi trang đầy; đọc outstanding từ RPC trước prefill; các ca đã trả đủ, lỗi quyền, loading/bấm trùng, outstanding 30.000 và lịch sử đầy đủ được kiểm riêng.

Probe cũ C3 do reviewer viết có hai assertion mâu thuẫn (vừa đòi hiện 100.000 sai, vừa đòi hiện 0); đó là lỗi thiết kế probe. Không dùng kết quả FAIL nguyên văn đó để giữ C3 mở. Probe hiện tại bỏ assertion sai, kiểm hướng thay thế mà review ban đầu cho phép: không khẳng định khoản nợ khi lịch sử thiếu, và kiểm RPC trước prefill. Matcher reference của C1 cũng đổi sang NULL theo contract sửa C2; mã QR trong fixture giữ nguyên. Bản cũ giữ nguyên làm lịch sử, không tuyên bố chạy nguyên văn rồi PASS.

## Kiểm chứng độc lập

[Summary/hash](review_a0f7255_evidence/summary.json), [analyze](review_a0f7255_evidence/analyze.log), [Flutter](review_a0f7255_evidence/flutter.log), [DB JSON](review_a0f7255_evidence/db-results.json), [DB log](review_a0f7255_evidence/bh06.log), [widget source](review_a0f7255_evidence/widget_probe.dart.txt), [widget log](review_a0f7255_evidence/probes.log), [RPC C2 source](review_a0f7255_evidence/reference_probe.py), [RPC C2 log](review_a0f7255_evidence/reference-probe.log), [RPC C4 source](review_a0f7255_evidence/expense_probe.py), [RPC C4 log](review_a0f7255_evidence/expense-probe.log).

| Nhóm | Kết quả reviewer |
|---|---|
| Flutter 3.47.7 / Dart 3.13.5 analyze --no-pub | 0 issue, exit 0 |
| flutter test --no-pub trước khi thêm probe | 186/186 PASS, exit 0 |
| Runner DB BH-06 CLEAN/LEGACY | 84/84 PASS, exit 0 |
| Widget probe --plain-name 'review ' | 7 PASS / 1 FAIL (C4), exit 1 |
| RPC C2, 5 kiểm tra retry/reject/refinalize/reference | 5 PASS, exit 0 |
| RPC C4, chi phí Nước | FAIL, probe exit 1 / psql exit 3 |

Widget/provider thật với repository fixture; probe tạm chạy dưới test/screens rồi lưu .dart.txt, không để lại thay đổi source/test tác giả. RPC/runner dùng PostgreSQL17 Docker cô lập `--network none`, dữ liệu giả, Auth stub và SET ROLE authenticated. RPC probe chạy sau runner; không gọi production. Số 186 PASS không gồm probe C4 FAIL. Không chạy riêng lại BH-02..05; số 335 DB của A là bằng chứng lịch sử. Các script RPC tham chiếu helper của runner, hash runner lưu cùng summary.

Fetch: remote.origin.fetch của checkout chỉ bao gồm main. Lượt này dùng refspec trực tiếp để xác nhận/pull đúng a0f7255; nhận định trước rằng nhánh remote chưa đổi dựa trên ref cũ không còn áp dụng.

## Kết luận

**Chưa đạt phần C BH-06 tại `a0f7255` sau vòng sửa 2/2.** Đóng C1/C2/C3, mở C4 P2. Dừng vòng sửa tự động theo AGENTS và báo chủ dự án; không tự mở vòng 3, viết code sửa, chuyển tích hợp, merge main hoặc deploy. A/B giữ kết luận theo tested SHA trước. Báo cáo cũ và các trạng thái bàn giao giữ làm lịch sử.

**NOT RUN:** HTTP/PostgREST/JWT/Supabase Auth thật; thiết bị/browser e2e; ảnh VietQR và chuyển khoản/ngân hàng thật; staging/production, backup/restore, concurrency HTTP, pilot/nghiệm thu tích hợp A+B+C. C3 dùng fixture tương ứng contract phân trang; chưa dựng luồng 51 payment qua HTTP. RPC refinalize C2 đã chạy local trong lượt này, không còn thuộc NOT RUN local.
