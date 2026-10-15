# Kết quả kiểm thử RLS BH-02

Ngày 15/10/2026. Commit được kiểm thử: `3fa3cdae72ef08895d3ad62f3a31e95dc5b7fa35`.

Đã chạy 33 ca: **18 PASS, 15 FAIL**. FAIL nghĩa hành vi thực tế không đáp ứng quyền/read contract mong đợi, không phải lỗi runner. Cả migration DB sạch và nhánh tạo cột legacy chạy SQL thành công; hành vi quyền và payload đích còn lỗi.

## Môi trường và giới hạn

- Container PostgreSQL 17.11 `bh02-review-postgres`, network none, không publish cổng, data tmpfs.
- Hai database test riêng: `bh02_clean_20261015105343` và `bh02_legacy_20261015105343`.
- Roles anon/authenticated, auth.users và auth.uid được mô phỏng tối thiểu. Gán role thật bằng SET LOCAL ROLE và UUID claim cho từng ca. Không chỉ chạy quyền postgres rồi kết luận RLS đạt.
- Fixture host, cohost, treasurer, player và outsider; hai CLB, public/private/unlisted draft sessions, hai confirmed players, charge 70.000đ và paid 20.000đ. Tất cả email/phone/bank là giả.
- Nhánh legacy mô phỏng schema ba bảng; dữ liệu đăng ký giả được seed sau migration, giữ nguyên cột phone_number và NOT NULL cũ để kiểm tra tương thích client mới. Đây chưa phải bài rehearsal chuyển đổi đầy đủ dữ liệu production.
- Mỗi ca chạy trong BEGIN/ROLLBACK; lỗi psql đóng connection cũng rollback. Không thao tác DB Supabase live.
- Không phải Supabase stack đầy đủ: chưa thử PostgREST HTTP/JWT verification, chưa test đồng thời hoặc RPC BH-05/BH-06 chưa được triển khai. ACL mặc định function trong PostgreSQL mô phỏng có thể khác cấu hình live; explicit GRANT authenticated trong migration vẫn được kiểm tra.

## Lỗi đã tái hiện

| Nhóm | Kết quả thực tế | Đánh giá |
|---|---|---|
| F1 helper ghi | anon và outsider ghi audit giả; user preseed result=true qua record_idempotency/check_idempotency | P1 xác nhận trong DB cô lập |
| F2 raw sessions | outsider đọc được snapshot ngân hàng và liệt kê unlisted draft | P1 xác nhận |
| F3 public summary | anon permission denied sessions; outsider count=0, player count=1, host count=2 cho cùng buổi 2 người | P1 xác nhận |
| F4 legacy | payload session đích lỗi NOT NULL venue_name; payload player đích lỗi NOT NULL player_name | P1 xác nhận |
| F5 outstanding | player nhận 0 hàng; host thấy đúng 70000/20000/50000 | P2 xác nhận |
| F6 bank reads | host/owner/treasurer đều permission denied khi đọc account thuộc quyền | P2 xác nhận |
| F7 contact legacy | treasurer đọc được 2 hàng có phone_number từ bảng session_players cũ dù bảng contacts mới chặn | P1 bổ sung |

## Phát hiện bổ sung F7

File migration, dòng 1048–1053: policy session_players cho has_session_finance_access đọc toàn hàng. Nhánh legacy không chuyển/cách ly/gỡ cột phone_number, trong khi grant SELECT toàn bảng ở dòng 917. Vì vậy người có finance nhưng không management vẫn đọc được SĐT qua cột cũ; policy session_player_contacts riêng không bảo vệ bản sao này. Runner xác nhận treasurer không đọc contacts mới nhưng đọc được cả 2 contact legacy.

Cần chuyển dữ liệu riêng sang bảng được bảo vệ và đóng đường đọc cột legacy bằng projection/column grants hoặc cách ly legacy trước release; không xóa dữ liệu chưa đối chiếu và không chỉ ẩn phone trong UI. Thêm regression test này vào nhánh upgrade, không chỉ schema sạch.

## Chi tiết từng ca

| Ca | DB | Role / actor | Kết quả |
|---|---|---|
| anon venues active read | clean | anon / None | PASS |
| anon raw player denied | clean | anon / None | PASS |
| outsider player rows hidden | clean | authenticated / 3 | PASS |
| player sees own row | clean | authenticated / 2 | PASS |
| player cannot see other row | clean | authenticated / 2 | PASS |
| cohost sees session roster | clean | authenticated / 5 | PASS |
| outsider contacts hidden | clean | authenticated / 3 | PASS |
| player only own contact | clean | authenticated / 2 | PASS |
| treasurer cannot read contacts | clean | authenticated / 4 | PASS |
| outsider ledger hidden | clean | authenticated / 3 | PASS |
| treasurer reads ledger | clean | authenticated / 4 | PASS |
| player cannot self elevate | clean | authenticated / 2 | PASS |
| player cannot direct insert paid flag | clean | authenticated / 2 | PASS |
| outsider cannot update private profile | clean | authenticated / 3 | PASS |
| anon cannot forge audit | clean | anon / None | FAIL |
| outsider cannot forge foreign audit | clean | authenticated / 3 | FAIL |
| client cannot preseed idempotency | clean | authenticated / 3 | FAIL |
| outsider cannot read bank snapshot | clean | authenticated / 3 | FAIL |
| outsider cannot list unlisted drafts | clean | authenticated / 3 | FAIL |
| anon public summary correct count | clean | anon / None | FAIL |
| outsider public summary correct count | clean | authenticated / 3 | FAIL |
| player public summary correct count | clean | authenticated / 2 | FAIL |
| host public summary correct count | clean | authenticated / 1 | PASS |
| player sees own outstanding | clean | authenticated / 2 | FAIL |
| host sees player outstanding | clean | authenticated / 1 | PASS |
| host can read own bank | clean | authenticated / 1 | FAIL |
| owner can read club bank | clean | authenticated / 1 | FAIL |
| treasurer can read club bank | clean | authenticated / 4 | FAIL |
| public detail hides private fields | clean | anon / None | PASS |
| outsider private detail blocked | clean | authenticated / 3 | PASS |
| new schema session insert into legacy | legacy | postgres / 1 | FAIL |
| new schema player insert into legacy | legacy | postgres / 1 | FAIL |
| treasurer cannot read legacy contact | legacy | authenticated / 4 | FAIL |

## Chạy lại và bước tiếp theo

Kết quả đầy đủ gồm expected/actual: [rls_test_results.json](rls_test_results.json).

Runner tái hiện nằm tại [run_rls_tests.py](run_rls_tests.py); hướng dẫn dựng lại và chạy ở [13_BH02_REVIEW_HANDOFF.md](../../13_BH02_REVIEW_HANDOFF.md). Không giả định container Codex tồn tại trên máy Windows.

BH-02 chưa đạt acceptance. Ưu tiên F1/F2/F7, sau đó F3/F4 và F5/F6; sửa migration/quyền/read contracts và chạy lại cùng ca. Không đổi expected để biến FAIL thành PASS. Lượt kiểm thử không sửa code; báo cáo được publish trong lượt tài liệu sau đó.
