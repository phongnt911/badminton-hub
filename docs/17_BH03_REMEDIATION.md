# Khắc phục BH-03 sau review 88dd247

Ngày 15/10/2026. Baseline review [C1–C5](reviews/bh03/review_88dd247.md). Thay đổi lần này gồm SQL forward migration, app, tests và tài liệu; **không apply Supabase production**. Môi trường DB kiểm thử là PostgreSQL 17.11 tắt mạng với Auth stub tối thiểu, chưa tương đương full Supabase/PostgREST.

## Các lỗi được xử lý

| ID | Khắc phục | Bằng chứng |
|---|---|---|
| C1 account linking không consent | add_club_member từ chối user_id khác NULL; guest mới luôn chưa account, không giả acceptance | 2 ca clean/legacy từ chối liên kết account có sẵn |
| C2 concurrent replay tạo hai CLB | check_idempotency khóa transaction theo actor+operation+request trước side effects; replay kiểm lại hash dưới lock | Same payload/concurrent cùng UUID trả cùng club; payload khác một conflict, chỉ 1 club; kiểm cả clean/legacy |
| C3 private data sau logout | ClubProvider đăng ký listener AuthProvider tại root; đổi user/logout clear private state, tăng generation; response read/mutation phiên cũ bị bỏ; dispose hủy listener | Tests cached list, pending list, member/bank response trễ, mutation trễ sau logout |
| C4 UI không gửi request ID | Provider tạo UUID v4 bằng thư viện chuẩn cho mỗi ý định, giữ cùng payload qua lỗi/timeout; success hoặc đổi payload dùng key mới; repository yêu cầu key, RPC từ chối key thiếu | Tests retry UUID bằng nhau, ý định mới UUID khác, DB thiếu key bị chặn |
| C5 hash bỏ trường | 7 mutation BH-03 hash JSONB array đầy đủ params, gồm scope/notes/account_name và ranh giới NULL/field; helper nội bộ không mở EXECUTE | Đổi note/name hoặc field có dấu ':' cùng key bị conflict, clean/legacy |

Request key retry hiện giữ trong bộ nhớ provider cho phiên ứng dụng; không có offline queue/persistence qua force-kill. Nếu user đóng app khi request timeout, cần đối chiếu danh sách trước tạo lại; lưu pending intents bền vững chỉ khi có yêu cầu. Key cần thiết cho mọi API caller, không chỉ Flutter. Không được sửa client khác gửi mutation thiếu key sau khi rollout.

## Migration và triển khai

File mới: `supabase/migrations/20261015140216_bh03_identity_retry_session_fixes.sql`. Không sửa hai migration đã chia sẻ. Chạy toàn chuỗi theo timestamp trên local/staging trước release. Mutation signatures giữ default nullable để tương thích khai báo SQL, nhưng body từ chối NULL theo contract. REVOKE EXECUTE PUBLIC/anon và cấp authenticated; helpers check/record/audit tiếp tục private theo ACL.

Các operation_requests đã tạo bằng hash format cũ có thể trả IDEMPOTENCY_CONFLICT khi replay cùng key sau nâng cấp; không xóa ledger/record hoặc tự tạo key mới để bỏ qua. Nếu có traffic cũ cần đối chiếu kết quả đã lưu và rollout có kiểm soát; môi trường test mới giữ canonical format mới. DB live/migration state chưa được thay đổi trong lượt này.

ClubProvider sử dụng AuthProvider thực khi bootstrap app. Null requestId từ UI được chuyển thành key ổn định ở provider trước repository. Caller tự truyền requestId chịu trách nhiệm giữ key qua retry, vẫn bị DB kiểm payload/cạnh tranh. Không thêm dependency hay đổi SDK constraint; Flutter 3.47.7/Dart 3.13.5 dùng để chạy tests tương thích pubspec.

## Kết quả kiểm thử

- Flutter toàn suite: **61/61 PASS** (56 cũ + 5 session/retry regression).
- flutter analyze: **No issues found**.
- BH-03 baseline: **48/48 PASS**, 24 ca thực sự chạy ở từng DB clean và legacy.
- BH-03 retry/consent mới: **14/14 PASS**, gồm hai request đồng thời, khác payload, key bắt buộc và canonical hash.
- BH-02 regression với toàn chuỗi migrations: **33/33 + 14/14 PASS**.
- Tổng PostgreSQL checks lần cuối: **109/109 PASS** (47 BH-02 + 62 BH-03), không phải phần trăm bảo mật của toàn app.

Bằng chứng timestamp trong docs/reviews/bh02 và docs/reviews/bh03; report BH-03 có HEAD lúc kiểm thử, worktree_dirty và SHA-256 từng migration. Test được chạy trước commit nên dirty=true là đúng; không sửa evidence để gắn SHA chưa tồn tại. Runner mới thử nguyên chuỗi SQL thay vì chỉ baseline. Test concurrency dùng trigger test-only trì hoãn tại INSERT rồi gỡ sau khi kiểm.

## Lệnh tái hiện

Dùng container PostgreSQL cô lập đã bootstrap roles theo hướng dẫn BH-02; trên máy Windows chọn container test đúng tên, không trỏ live.

```bash
flutter pub get
flutter test
flutter analyze
# Cùng BH02_TEST_CONTAINER nếu tên khác mặc định runner.
python docs/reviews/bh03/run_bh03_tests.py
python docs/reviews/bh03/run_bh03_retry_tests.py
python docs/reviews/bh02/run_rls_tests.py
python docs/reviews/bh02/extended_tests_15ef59b.py
```

run_bh03_tests mặc định dùng bh02-test-postgres; hai runner còn lại dùng bh02-review-postgres. Đặt BH02_TEST_CONTAINER thống nhất ở môi trường shell trước khi chạy; lượt này dùng bh02-review-postgres. Mỗi runner tạo DB test timestamp; không xóa DB/container bất kỳ ngoài phạm vi test. Dữ liệu giả, email/phone/account không phải thông tin người dùng thật.

## Giới hạn và công việc tiếp

Chưa kiểm PostgREST HTTP/JWT trên Supabase local/staging đầy đủ, thiết bị thật, persistence sau force-kill hoặc apply production. DB tests dùng auth.uid từ claim fixture, không chứng minh gateway xác minh JWT. C1–C5 đã có code và regression tương ứng; không diễn giải đây là cho phép deploy production không cần rehearsal.

Antigravity pull main, đọc tài liệu này và summary BH-03; giữ forward migration khi triển khai, không quay về nhận user_id tùy ý hoặc key nullable. Tiếp theo kiểm tích hợp full Supabase và phần hạn chế được ghi trước khi nghiệm thu rollout; không làm lại BH-03 đã có chỉ vì baseline report mô tả lỗi lịch sử.
