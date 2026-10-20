# Review tích hợp BH-06 — afeff39

Ngày 20/10/2026 (Việt Nam). Tested HEAD `afeff390c4f8d4d46c201768afab509d25f8e7c7`, nhánh `feat/bh06-integration`, code/test/migration trùng `8af7be5`, base `a9c7edb`; ancestry chứa A `706bd73`, B `5e62007`, C `b31f988`. Theo `docs/ai/REVIEWER.md` trên `chore/ai-roles` = `07b31d4`, AGENTS, docs/04, docs/08 và cổng tích hợp docs/09/24. Đọc diff main...HEAD, tập trung thay đổi tích hợp sau tip C. Không sửa code tác giả, migration hoặc test triển khai.

## Phát hiện

### I1 — P1: migration không sửa receiver cho buổi đã tồn tại

`supabase/migrations/20261020100000_bh06_integration_receiver.sql:212` (kết thúc cài trigger tại 215, thiếu bước backfill). Migration chỉ cài trigger cho lần ghi sessions/bank sau đó. Khi nâng cấp DB đã có tài khoản active và buổi in_progress đã chốt phí với receiver NULL, migration không chạy resolver/fill cho các hàng cũ. Các RPC hướng dẫn chỉ đọc; UI vẫn nhận has_receiver=false và chặn QR/gửi chuyển khoản. Người dùng phải tạo thêm một mutation không liên quan mới kích hoạt trigger. Các test tích hợp hiện tại dựng DB mới rồi cấu hình bank/publish nên không bao phủ đường nâng cấp này.

Probe độc lập dựng DB theo toàn bộ migration trước bản tích hợp, cấu hình bank bằng app RPC, tạo/publish/start/điểm danh/ghi chi phí/chốt phí; sau đó chỉ apply migration mới. Đọc hướng dẫn bằng role người chơi: outstanding 100.000, can_pay=true, has_receiver=false, receiver_snapshot=null. Kỳ vọng receiver đã được điền FAIL, exit 1.

Sửa: thêm forward migration backfill có giới hạn cho các buổi đủ điều kiện còn thiếu snapshot, dùng cùng quy tắc resolver; giữ nguyên snapshot/FK đã chốt, không buộc người dùng sửa buổi hoặc cấu hình lại bank. Thêm test nâng cấp từ dữ liệu trước migration: buổi đã in_progress/chốt phí, bank active có sẵn, buổi không có bank, và snapshot cũ phải bất biến. Không sửa migration đã chia sẻ.

### I2 — P2: refresh không khôi phục được chốt phí sau VERSION_CONFLICT

`lib/screens/session_finance_screen.dart:507`, refresh tại 408–409. Expected version luôn lấy từ widget.session nhận lúc mở route. Refresh chỉ tải SessionFinance, không cập nhật Session/version dùng cho finalize. Nếu manager khác start/cập nhật buổi sau khi route đã mở, DB trả VERSION_CONFLICT; người dùng làm theo thông báo “Vui lòng tải lại” nhưng mọi lần chốt sau vẫn gửi version cũ. Phải đóng/mở lại màn hình mới thoát được. Đây là lỗi phục hồi UI được bàn giao nêu ở §6, không chỉ rủi ro lý thuyết; phát hiện trong review tích hợp, không sửa lại lịch sử kết luận C theo tested SHA trước.

Probe widget/provider thật, repository fixture server version 4, route version 3: lần đầu conflict, gọi đúng callback RefreshIndicator, xác nhận finance đã được tải lại, chốt lần nữa vẫn gửi 3 thay vì 4. Probe FAIL, exit 1. Không có bằng chứng hỏng số tiền do RPC vẫn chặn version cũ.

Sửa: refresh cả dữ liệu Session/version hiện hành dùng cho finalize, hoặc trả và sử dụng session version có nguồn rõ trong DTO tài chính; cập nhật sau conflict trước khi cho thử lại. Giữ gate optimistic concurrency và request ID theo intent/payload, không bỏ expectedVersion hoặc tự tăng version ở client. Test manager khác start/cập nhật, conflict → refresh → chốt thành công mà không rời route.

## Kiểm chứng độc lập

[Summary/hash](review_afeff39_evidence/summary.json), [analyze](review_afeff39_evidence/analyze.log), [Flutter](review_afeff39_evidence/flutter.log), [exit các runner](review_afeff39_evidence/regression-exits.json), [orchestrator](review_afeff39_evidence/run_regression.py). Các JSON/log runner và probe trong cùng thư mục bằng chứng, không dùng log phía tác giả làm kết quả reviewer.

| Nhóm | Reviewer tự chạy |
|---|---|
| Flutter 3.47.7 / Dart 3.13.5 analyze --no-pub | 0 issue, exit 0 |
| flutter test --no-pub trước khi thêm probe | 189/189 PASS, exit 0 |
| BH-02 + extended | 33 +14 PASS |
| BH-03 + retry/concurrency | 48 +22 PASS |
| BH-04 | 44 PASS |
| BH-05 | 90 PASS |
| BH-06 | 84 PASS |
| Tổng hồi quy DB | 335/335 PASS, tất cả runner exit 0 |
| Runner tích hợp mới | 6/6 PASS, exit 0 |
| Probe nâng cấp độc lập I1 | FAIL, exit 1 |
| Probe widget conflict/refresh I2 | FAIL, exit 1 |
| Probe publish/bank hai kết nối + control start | PASS, exit 0; không mở finding |

I1: [source](review_afeff39_evidence/upgrade_probe.py), [log](review_afeff39_evidence/upgrade-probe.log). I2: [source](review_afeff39_evidence/version_probe.dart.txt), [log](review_afeff39_evidence/version-probe.log). Race/control: [source](review_afeff39_evidence/race_probe.py), [log](review_afeff39_evidence/race-probe.log).

Race probe giữ publish của cohost chưa commit, cấu hình host bank trên kết nối khác rồi commit publish: snapshot tạm NULL. Control start sau đó điền snapshot trước đường chốt phí, nên không suy diễn đó là lỗi thanh toán bị chặn vĩnh viễn và không mở thêm finding từ ca này. Hai probe FAIL là bằng chứng riêng, không gộp vào 189 Flutter/335 DB/6 tích hợp PASS.

DB runner dùng PostgreSQL17 Docker cô lập --network none, dữ liệu giả, Auth stub và SET ROLE app. Năm nhóm hồi quy và runner tích hợp dùng DB riêng; extended/retry chạy sau runner nền tương ứng. Probe nâng cấp/race dùng DB fixture riêng. Widget probe dùng widget/provider thật và mock FinanceRepository, chạy tạm trong test/screens rồi lưu .dart.txt. Hai widget test tác giả cũng mock FinanceRepository, không thực thi FinanceRepository/SupabaseClient thật; chúng không phải kiểm chứng nối UI→repository→HTTP→DB. Không thay thiếu kiểm HTTP bằng kết quả mock. Các JSON tạm/probe có thể làm metadata worktree dirty; nguồn triển khai giữ nguyên tested HEAD.

## Phân loại các quan sát bàn giao

- Gửi nhiều pending với các intent mới: chưa mở finding chặn tích hợp từ quan sát này. Replay cùng request và chặn tổng confirmed quá outstanding đã được kiểm DB; chưa có bằng chứng race thu dư mới. Cải thiện hiển thị pending là phần UX cần phân biệt với lỗi idempotency/confirmed.
- Version snapshot: mở I2 P2 theo probe phục hồi thất bại ở trên.
- Nút kết thúc buổi: giữ phạm vi BH-07 theo docs/24, không yêu cầu mở rộng UI trong review này.

## Kết luận

**Chưa đạt tích hợp BH-06 tại `afeff39`**: I1 P1, I2 P2 còn mở. A/B/C giữ các kết luận lịch sử theo tested SHA; không suy các phần riêng Đạt thành tích hợp Đạt. Người triển khai viết test tái hiện trước và sửa toàn bộ P theo AGENTS, tối đa hai vòng sửa của lượt tích hợp. Không tự sửa code, merge main, chuyển BH-07 hoặc deploy.

**NOT RUN:** HTTP/PostgREST/JWT/Supabase Auth thật, repository/SupabaseClient nối DB qua HTTP, thiết bị/browser e2e/deep link, tải ảnh VietQR và ngân hàng/chuyển khoản thật, apply staging/production, backup/restore và concurrency qua HTTP. Probe race dùng hai kết nối PostgreSQL thật với app role; không coi là kiểm concurrency HTTP hay toàn bộ race tài chính.
