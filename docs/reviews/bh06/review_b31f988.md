# Review BH-06C sau sửa C4 — b31f988

Ngày 20/10/2026 (Việt Nam). Tested HEAD `b31f988637fae8f8a01e3694b8cfccbeff50f5a2`, nhánh `feat/bh06c-ui`, code sửa `bd17a95`, test tái hiện `bfbd8f6`; dependency B `f28fd0f` (Đạt tại `5e62007`), main `c35dd27`. Source/test/migration tại HEAD trùng cây `bd17a95`. Theo `docs/ai/REVIEWER.md` trên `chore/ai-roles` = `07b31d4`; đọc diff main...HEAD và đối chiếu sửa sau review `0868287`.

Tiếp nhận bản sửa C4 theo yêu cầu review mới của chủ dự án; không tự mở vòng sửa code sau giới hạn AGENTS. Tên người dùng nhập `feat/bh06c-u` không có trên remote; nhánh khớp công việc trước và có bản sửa mới là `feat/bh06c-ui`, đã kiểm trực tiếp bằng ls-remote và fetch refspec nhánh. Không sửa triển khai, migration hoặc test tác giả.

## Phát hiện P0/P1/P2

Không còn phát hiện cần mở trong phạm vi kiểm chứng lượt này. Đóng **C4 P2** của [review_a0f7255](review_a0f7255.md) tại tested HEAD. C1/C2/C3 đã đóng ở lượt trước, giữ lịch sử và phát lại các probe liên quan.

## Kiểm chứng độc lập

[Summary/hash](review_b31f988_evidence/summary.json), [analyze](review_b31f988_evidence/analyze.log), [Flutter](review_b31f988_evidence/flutter.log), [DB JSON](review_b31f988_evidence/db-results.json), [DB log](review_b31f988_evidence/bh06.log), [widget source](review_b31f988_evidence/widget_probe.dart.txt), [widget log](review_b31f988_evidence/probes.log), [RPC C2 source](review_b31f988_evidence/reference_probe.py), [RPC C2 log](review_b31f988_evidence/reference-probe.log), [RPC C4 source](review_b31f988_evidence/expense_probe.py), [RPC C4 log](review_b31f988_evidence/expense-probe.log).

| Nhóm | Kết quả reviewer |
|---|---|
| Flutter 3.47.7 / Dart 3.13.5 analyze --no-pub | 0 issue, exit 0 |
| flutter test --no-pub, trước khi thêm probe | 187/187 PASS, exit 0 |
| Runner DB BH-06 CLEAN/LEGACY, PostgreSQL17 | 84/84 PASS, exit 0 |
| Widget probe --plain-name 'review ' | 8/8 PASS, exit 0 |
| RPC C2: retry/reject/refinalize/reference | 5 kiểm tra PASS, exit 0 |
| RPC C4: ghi category đã ánh xạ, đọc lại DB | PASS, exit 0; `other|Nuoc fixture|10000` |

Tám probe UI kiểm ID đăng ký khác auth ID, trang payment bị cắt, đã trả đủ, lỗi quyền, loading/chống bấm trùng, prefill từ RPC, lịch sử đầy đủ và thao tác chọn Nước. Probe C4 từ lượt trước được cập nhật stub để phản ánh contract thực: nhận court/shuttle/other, từ chối key khác; kiểm cụ thể UI gửi other, giữ title/amount và hiện thành công. RPC C4 đổi đầu vào water lỗi trước đây sang other đúng theo payload đã quan sát trên UI, rồi đọc lại bản ghi để xác nhận category/title/amount. Đây là probe theo contract sửa, không tuyên bố probe gửi cứng water nguyên văn nay PASS. Không bỏ ràng buộc DB hay sửa kỳ vọng để chấp nhận water.

RPC C2 chạy lại cùng nguồn probe trước, kiểm cùng request trả cùng response, intent mới sau reject, trả thêm 50.000 sau refinalize, ba reference payment riêng và mã nội dung QR ổn định. Hash đối chiếu với lượt trước xác nhận trong lib/test/migration chỉ màn session finance và test của màn này thay đổi.

Widget/provider thật với repository fixture; probe tạm chạy dưới test/screens rồi chuyển sang .dart.txt. Runner/RPC dùng PostgreSQL17 Docker cô lập `--network none`, dữ liệu giả, Auth stub và SET ROLE authenticated; RPC probe chạy sau runner. Metadata dirty có thể bao gồm probe/JSON tạm; source triển khai giữ nguyên tested HEAD. Không apply DB thật. Không chạy riêng lại BH-02..05; số 335 DB của A là bằng chứng lịch sử, không phải số chạy lại lượt này.

## Kết luận

**Đạt phần C BH-06 tại `b31f988`** trong phạm vi UI và bằng chứng trên; đóng C4, không còn C1/C2/C3/C4 mở từ các review trước. Giữ báo cáo và trạng thái cũ để truy vết. A/B giữ kết luận theo tested SHA trước. Đây không phải nghiệm thu tích hợp toàn BH-06 hoặc cho phép deploy; không tự chuyển phần tích hợp, merge main hay deploy.

**NOT RUN:** HTTP/PostgREST/JWT/Supabase Auth thật; thiết bị/browser e2e; tải ảnh VietQR và chuyển khoản/ngân hàng thật; staging/production, backup/restore, concurrency HTTP và pilot/nghiệm thu tích hợp A+B+C. Widget fixture và PostgreSQL/Auth stub không thay các cổng này.
