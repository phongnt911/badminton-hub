# Review tích hợp BH-05 A+B+C — c7ed6d5

Ngày 16/10/2026 (Việt Nam). Nhánh feat/bh05-integration, tested HEAD `c7ed6d5`. Theo docs/ai/REVIEWER.md trên chore/ai-roles (`163bc45`); đọc AGENTS/04/08, BH05/R2/R7 và ca nghiệm thu xuyên suốt ở 09. Không sửa code hoặc apply DB remote.

## Phạm vi

Diff `git diff origin/main...HEAD`, main remote da1285d. Review chỗ nối RPC ↔ repository ↔ provider ↔ UI sau merge A/B/C, không chỉ lặp kết quả từng phần. Lượt review bắt đầu ở 53832de, sau steering cập nhật sang c7ed6d5; `git diff 53832de c7ed6d5 -- lib test supabase` rỗng. Đã chạy lại analyze/Flutter và runner BH05 tại c7ed6d5; các probe bổ sung dùng cùng application/migration tree.

## I1 — P1: luồng điểm danh không có đường start buổi từ published

**File:dòng:** `lib/screens/session_detail_screen.dart:608-631` (management actions không có start); `supabase/migrations/20261015170500_bh05_registrations.sql:790-794` (RPC attendance bắt buộc in_progress); `docs/reviews/bh05/run_bh05_tests.py:427,438` (fixture cập nhật lifecycle trực tiếp).

**Mô tả:** app tạo draft→publish, nhưng toàn chuỗi migrations và client không có start_session hoặc action start cho set_session_lifecycle. UI chỉ hiện nút điểm danh khi session.isInProgress; không có đường hợp lệ đưa buổi vừa tạo vào trạng thái này. Ca nghiệm thu docs/09 “Host start, điểm danh present/no_show” vì vậy không chạy được từ app. Test record_attendance PASS nhờ postgres UPDATE sessions SET lifecycle='in_progress', không qua quyền actor/mutation thật. Đây là lỗ hổng tích hợp lifecycle kế thừa BH04 nối vào attendance BH05, không phải bug mapping tham số record_attendance.

**Bằng chứng:** truy vấn pg_proc không có public.start_session. Bridge local với SessionRepository thật tạo/publish/duyệt rồi gọi recordAttendance trả lỗi INVALID_STATE ở DB; widget probe host published không có đường bắt đầu. Probe widget không chỉ ra đúng tên nút là bắt buộc: đối chiếu cả source/UI/RPC xác nhận không có hành động start tương đương.

**Cách sửa:** bổ sung đường chuyển published→in_progress có kiểm actor/management, khóa session, request_id/hash/replay/audit/ACL; nối repository/provider/UI để host start. Không mở direct UPDATE và không bỏ guard in_progress của attendance. Viết ca tích hợp create→publish→join→approve→start→present/no_show, sai actor bị chặn, retry không lặp. Nếu chủ dự án chủ động hoãn start sang ticket khác, chưa thể nghiệm thu attendance xuyên suốt BH05; phải ghi phụ thuộc này rõ thay vì coi SQL fixture là hoàn tất luồng.

## I2 — P2: sau hủy không có đường đăng ký lại dù RPC hỗ trợ

**File:dòng:** `lib/screens/session_detail_screen.dart:654-700` (nút join chỉ khi reg==null), `:702-704,778-783` (cancelled/rejected không active và không có hành động thay thế).

**Mô tả:** sau cancel thành công, provider refresh nhận myRegistration.registrationStatus='cancelled', không phải null. Card rơi vào nhánh có registration nhưng không có join/cancel/accept, khiến người dùng không thể đăng ký lại dù buổi published còn chỗ và còn hạn. Backend request_join_session tái sử dụng đúng player_id cho cancelled/rejected; tính năng không đi được tới UI. Đây là khoảng trống chuyển trạng thái giữa các thao tác, không phải capacity hoặc idempotency lỗi ở DB.

**Bằng chứng:** real repository/provider/SQL bridge chạy cancel→requestJoin thành công và giữ player ID; widget với chính trạng thái cancelled đó không có đường gọi join (probe FAIL).

**Cách sửa:** có hành động đăng ký lại cho trạng thái được server cho phép, trong lifecycle/hạn phù hợp; gửi ý định mới qua provider, để DB giữ ID và kiểm slot/deadline. Thêm widget/integration test join→approve→cancel→rejoin cùng ID, error/retry và submitting; không xóa registration để làm UI hiện nút.

## Kiểm thử và bằng chứng độc lập

- Flutter3.47.7/Dart3.13.5 tại c7ed6d5: `flutter analyze --no-pub` → No issues found, exit 0; `flutter test --no-pub` → **132/132 PASS**, exit 0.
- `BH02_TEST_CONTAINER=bh02-review-postgres python docs/reviews/bh05/run_bh05_tests.py`: **84/84 PASS**, exit 0, [JSON tại c7ed6d5](bh05_test_results_20261015190239.json). PostgreSQL17.11 clean/legacy, Auth stub, toàn chuỗi migrations.
- Hai probe widget cho I1/I2: **0 PASS/2 FAIL**, [log](review_c7ed6d5_ui_probes.txt).
- Kiểm tra boundary dùng **SessionRepository + SessionProvider thật**, SupabaseClient thật gọi HTTP bridge loopback, bridge gọi RPC SQL dưới SET ROLE authenticated và actor giả trên DB test `bh05_clean_20261015185715`: **1/1 PASS**, [log](review_c7ed6d5_bridge.txt). Kiểm pending→approve→confirmed→cancel→rejoin giữ ID và xác nhận attendance bị chặn ở published. Test PASS có nghĩa xác nhận hiện trạng cả lỗi I1, không phải nghiệm thu end-to-end thành công.
- Bridge không thay PostgREST/JWT: header actor chỉ fixture local, không kiểm token; không gọi remote. Cây migrations DB bridge giống c7ed6d5. Các file test bổ sung chỉ đặt tạm để chạy, đã chuyển sang `/workspace/scratch/bh05-integration-review/`; không giữ thay đổi implementation trong repo.

## NOT RUN

- Full Supabase HTTP/PostgREST/JWT thật, thiết bị/browser e2e, staging/production apply; không có chứng nhận production-ready.
- Không chạy lại riêng runner BH02/BH03/BH04 trong lượt này. Tổng 245/245 ở handoff là evidence tác giả; kết quả tự chạy DB lượt này là 84/84 BH05, không gọi chúng tương đương.
- Luồng attendance từ UI xuyên qua start chưa chạy được vì I1; không tính postgres UPDATE fixture là bước start hợp lệ.
- Không kiểm thực nghiệm mới mọi luồng invitation/host_recorded consent hoặc mọi lịch mạng/cạnh tranh khác ngoài runner BH05. Bridge chỉ kiểm chuỗi đăng ký/duyệt/hủy và ranh giới attendance, không full UI xuyên mạng.

## Kết luận

**Chưa đạt tích hợp BH-05 A+B+C** tại `c7ed6d5`: còn I1 (P1), I2 (P2). Các kết luận Đạt riêng A/B/C là lịch sử trong phạm vi mỗi phần, không được suy ra nghiệm thu xuyên suốt. Reviewer tự chốt/cập nhật trạng thái, không hỏi xác nhận; không sửa code, merge main hoặc apply remote DB. Hai vòng sửa trước thuộc review phần C; lượt này ghi nhận phạm vi tích hợp mới, không tự mở vòng sửa C thứ ba hoặc triển khai sửa.
