# Review tích hợp BH-06 vòng sửa 1 — 318bc52

Ngày 20/10/2026 (Việt Nam). Tested HEAD `318bc52e0afad7ed60117120d31f9f319d754c52`, nhánh `feat/bh06-integration`, code/test/migration trùng `31a553c`; base `a9c7edb`, ancestry chứa A `706bd73`, B `5e62007`, C `b31f988`. Theo `docs/ai/REVIEWER.md` trên `chore/ai-roles` = `07b31d4`, AGENTS, docs/04/08 và cổng tích hợp docs/09/24. Đọc diff main...HEAD, đối chiếu sửa sau review `c0cf69a`. Không sửa code tác giả, migration hoặc test triển khai.

## Phát hiện P0/P1/P2

Không còn phát hiện cần mở trong phạm vi kiểm chứng lượt này. Đóng **I1 P1 và I2 P2** của [review_afeff39](review_afeff39.md) tại tested HEAD; giữ báo cáo/bằng chứng trước làm lịch sử.

## Kiểm chứng độc lập

[Summary/hash](review_318bc52_evidence/summary.json), [analyze](review_318bc52_evidence/analyze.log), [Flutter](review_318bc52_evidence/flutter.log), [exit các runner](review_318bc52_evidence/regression-exits.json), [orchestrator](review_318bc52_evidence/run_regression.py). Các JSON/log mới của từng runner trong cùng thư mục bằng chứng, không dùng log tác giả làm kết quả reviewer.

| Nhóm | Reviewer tự chạy |
|---|---|
| Flutter 3.47.7 / Dart 3.13.5 analyze --no-pub | 0 issue, exit 0 |
| flutter test --no-pub, không tính probe reviewer | 190/190 PASS, exit 0 |
| BH-02 + extended | 33 +14 PASS |
| BH-03 + retry/concurrency | 48 +22 PASS |
| BH-04 | 44 PASS |
| BH-05 | 90 PASS |
| BH-06 | 84 PASS |
| Tổng hồi quy DB | 335/335 PASS; mọi runner exit 0 |
| Runner tích hợp | 7/7 PASS, exit 0 |
| Runner nâng cấp | 3/3 PASS, exit 0 |
| Probe reviewer I1, buổi host đã chốt phí trước nâng cấp | PASS, exit 0 |
| Probe reviewer I2, conflict → refresh → chốt lại | PASS, exit 0 |

I1: [source](review_318bc52_evidence/upgrade_probe.py), [log](review_318bc52_evidence/upgrade-probe.log). I2: [source](review_318bc52_evidence/version_probe.dart.txt), [log](review_318bc52_evidence/version-probe.log). [Log nâng cấp](review_318bc52_evidence/run_upgrade_tests.log) và [log tích hợp](review_318bc52_evidence/run_integration_tests.log).

Probe I1 từ review trước được cập nhật để seed dữ liệu dưới các migration trước receiver, rồi apply toàn bộ họ forward migration sau đó, gồm backfill mới; không chỉ apply file receiver cũ. Giữ yêu cầu receiver phải có ngay sau nâng cấp, không thêm mutation session/bank để lách lỗi. Kết quả host session đã chốt phí: has_receiver=true, can_pay=true, outstanding 100.000, đúng tài khoản host. Runner nâng cấp kiểm thêm trường hợp CLB có bank active, không có bank thì vẫn NULL và snapshot/FK cũ bất biến.

Probe I2 giữ route version 3, server version 4, lần đầu conflict rồi gọi callback refresh như trước; fixture DTO nay trả session_version 3 ở lần đọc đầu và 4 khi refresh, đúng contract DB đã bổ sung. Giữ kỳ vọng lần gửi sau dùng 4; kiểm thêm chuỗi [3,4] và thông báo chốt phí thành công sau khi snackbar lỗi trước hết thời gian. Không dùng fixture thiếu key mới rồi kết luận bản sửa còn lỗi, cũng không tuyên bố chạy nguyên văn probe cũ PASS. Runner DB thứ 7 kiểm nguồn session_version từ sessions.version và việc version cũ conflict/version mới chốt được; model test kiểm parse key này.

Đối chiếu hàm get_session_finance cũ/mới xác nhận thay đổi projection chỉ thêm s.version/session_version; giữ ACL, điều kiện quyền và các phần phân trang/tổng tiền cũ. Forward backfill dùng lại resolver/helper, chỉ quét buổi đủ điều kiện còn snapshot NULL; migration đã chia sẻ không bị sửa.

DB runner dùng PostgreSQL17 Docker cô lập --network none, dữ liệu giả, Auth stub và SET ROLE app. Nhóm hồi quy/integration/upgrade dùng DB riêng; extended/retry chạy sau runner nền tương ứng. Probe I1 dùng DB nâng cấp riêng; probe I2 dùng widget/provider thật và mock FinanceRepository, chạy tạm dưới test/screens rồi chuyển ra .dart.txt. Không sửa source triển khai trong lượt chạy. JSON/probe tạm có thể làm metadata worktree dirty; hash nguồn và tested HEAD lưu trong summary. 335 hồi quy, 7 tích hợp, 3 nâng cấp và hai probe là các nhóm riêng, không gộp thành số test HTTP/e2e.

## Kết luận

**Đạt tích hợp BH-06 tại `318bc52`** sau vòng sửa 1, trong phạm vi code và bằng chứng local/PostgreSQL cô lập nêu trên. Đóng I1/I2; các phát hiện C1–C4 đã đóng ở review phần C, giữ lịch sử theo tested SHA. Không còn phát hiện mở từ các review BH-06 trong phạm vi đã kiểm chứng.

Kết luận không cho phép deploy production hoặc thay thế các cổng chưa chạy. Không tự merge main, chuyển BH-07 hay deploy. Báo cáo Chưa đạt/Chờ review trước đó giữ làm lịch sử.

**NOT RUN:** repository/SupabaseClient nối DB qua HTTP/PostgREST/JWT/Supabase Auth thật; thiết bị/browser e2e/deep link; tải ảnh VietQR và ngân hàng/chuyển khoản thật; apply staging/production, backup/restore và concurrency qua HTTP. Widget mock repository và PostgreSQL/Auth stub không thay các kiểm chứng này.
