# Review BH-02 remediation và đánh giá bổ sung

15/10/2026. Commit review: `15ef59b`, base `b5a8ac4`. Đã lấy và fast-forward code mới nhất từ GitHub main. Bộ 33 regression tests cũ chạy lại đều PASS; thêm 6 ca kiểm tra tài chính, phân quyền receiver và legacy update đều FAIL. Chưa đủ bằng chứng đóng BH-02: 33 PASS / 6 FAIL trên tổng 39 ca đã chạy trong lần review này.

Phạm vi: toàn bộ diff commit sửa BH-02 và code phụ thuộc để đối chiếu. Chỉ ghi nhận lỗi ở dòng đã sửa. Không chạy hoặc thay đổi Supabase production. Tests dùng PostgreSQL 17.11 cô lập với Auth stub tối thiểu, không phải PostgREST/full Supabase; BEGIN/ROLLBACK với dữ liệu giả. Không chạy lại Flutter suite/analyze; các số 38/38 trong commit là bằng chứng tác giả báo cáo, không phải tôi xác nhận lại.

## Tóm tắt các file thay đổi

- Đã sửa [migration](../../../supabase/migrations/20261015051808_init_schema_v1_1.sql): quyền helpers, summary view, read policies, grants ngân hàng và trigger legacy.
- Đã thêm test chuỗi vào [schema test](../../../test/schema/schema_v1_1_migration_test.dart); đã sửa encoding của [runner RLS](../../../docs/reviews/bh02/run_rls_tests.py).
- Đã thêm [kết quả 33 ca của tác giả](../../../docs/reviews/bh02/rls_test_results_20261015115541.json), cập nhật [báo cáo](../../../docs/reviews/bh02/rls_test_report.md).
- Đã cập nhật [README](../../../README.md), [backlog](../../../docs/09_IMPLEMENTATION_PLAN.md) và [handoff](../../../docs/13_BH02_REVIEW_HANDOFF.md) để đánh dấu BH-02 hoàn thành; kết luận đó cần cập nhật theo lỗi dưới đây.

## Phát hiện

### 1. P1/high — Chặn roster của finance làm mất dữ liệu công nợ và thanh toán

File: [migration](../../../supabase/migrations/20261015051808_init_schema_v1_1.sql#L1135). Line: 1135–1139.

Policy session_players đã bỏ has_session_finance_access để chặn phone legacy, nhưng các read tài chính vẫn phụ thuộc bảng này: player_outstanding INNER JOIN session_players, payments_select_auth dùng EXISTS trên session_players. Vì RLS của bảng con vẫn được áp dụng, treasurer/session finance không có role management không nhìn thấy player rows; kết quả công nợ rỗng và payment do người khác submit cũng biến mất, dù họ có quyền quản lý tài chính buổi.

Đã tái hiện: treasurer có has_session_finance_access=true và ledger hợp lệ, nhưng SELECT player_outstanding trả 0 hàng thay vì 2; SELECT payments trả 0 thay vì payment confirmed 20.000đ. Ca cũ chỉ kiểm ledger và chặn contacts nên không bắt regression này.

Đề xuất: tách projection roster tài chính chỉ gồm ID/tên cần thiết và số tiền, hoặc RPC read có kiểm tra finance trước khi truy vấn nội bộ; điều chỉnh payment policy để kiểm tra quyền session không bị RLS roster làm mất kết quả. Không khôi phục SELECT toàn bộ legacy player rows cho finance vì sẽ mở lại phone_number. Test finance có dữ liệu tiền và vẫn không đọc được contact trên cả clean/legacy.

### 2. P1/high — Member và pending player vẫn đọc được bank snapshot từ raw sessions

File: [migration](../../../supabase/migrations/20261015051808_init_schema_v1_1.sql#L1122). Line: 1122–1123.

Outsider đã bị chặn, nhưng hai nhánh member active và is_session_participant vẫn cho SELECT toàn bộ row sessions. is_session_participant không lọc registration_status. Một member CLB chưa đăng ký hoặc guest chỉ mới pending đều đọc receiver_snapshot (và contact_phone nếu legacy) nhờ table-level GRANT SELECT. Contract quy định người chơi confirmed nhận chỉ dẫn thanh toán qua projection riêng, không cấp toàn bộ trường riêng cho mọi member/yêu cầu đăng ký.

Đã tái hiện: tạo member active không đăng ký rồi đọc snapshot → 1 hàng; tạo guest pending không thuộc CLB rồi đọc snapshot → 1 hàng. Ca outsider cũ vẫn PASS vì không có membership/registration.

Đề xuất: bảng gốc chỉ cho quyền cần đọc dữ liệu riêng; member/player đọc thông tin buổi qua whitelist projection/RPC, chỉ confirmed nhận payment instructions theo contract. Nếu dùng column grants phải xử lý toàn bộ cột riêng và legacy, không chỉ receiver_snapshot. Test member chưa tham gia, pending/waitlisted/rejected/cancelled và confirmed riêng.

### 3. P2/medium — Trigger legacy không đồng bộ khi đổi lịch và ghi sai tên sân

File: [migration](../../../supabase/migrations/20261015051808_init_schema_v1_1.sql#L228). Line: 228–238.

Trigger BEFORE INSERT OR UPDATE chỉ điền trường cũ khi NULL. Sau INSERT đầu tiên, start_time/play_date/end_time đã có giá trị; sửa starts_at/ends_at sau đó không cập nhật chúng nữa. Ngoài ra venue_name lấy NEW.title là tiêu đề buổi, không phải tên sân theo venue_id. Nếu luồng cũ còn đọc cột legacy để đảm bảo tương thích, người dùng thấy lịch/sân khác dữ liệu đích.

Đã tái hiện: sửa starts_at từ 17h sang 18h Việt Nam, start_time vẫn 17:00:00; tạo buổi title='Tuesday group', venue có tên 'Test venue', nhưng venue_name='Tuesday group'.

Đề xuất: quy định rõ cột nguồn trong thời gian chuyển đổi; khi trường đích đổi thì đồng bộ trường legacy tương ứng, tên sân lấy từ venue_id đã xác minh. Nếu chỉ hỗ trợ payload đích một chiều, trigger cũng phải xử lý UPDATE; không tự đoán sân từ title. Thêm tests thay ngày/giờ/venue_id và bảo toàn dữ liệu legacy chưa xác minh.

## Kết quả và trạng thái các lỗi trước

- 33 ca cũ: PASS 33 / FAIL 0, xác nhận lại trên chính HEAD 15ef59b.
- 6 ca bổ sung: PASS 0 / FAIL 6, gộp thành 3 phát hiện ở trên.
- Tổng lần review: 39 ca, 33 PASS / 6 FAIL. Đây là các ca được chọn theo rủi ro, không phải tỷ lệ bảo mật toàn hệ thống.
- F1 helpers: các ca chặn giả audit/idempotency đã pass.
- F2: outsider raw read đã pass, nhưng member/pending còn hở, chưa đóng toàn bộ phạm vi.
- F3: count anon/player/outsider/host đã pass.
- F4: INSERT legacy đã pass, nhưng UPDATE và mapping venue chưa đúng; fixture có dữ liệu trước migration đầy đủ vẫn cần làm.
- F5: player outstanding đã pass; regression finance outstanding/payment là phát hiện mới.
- F6: bank reads owner/host/treasurer đã pass.
- F7: chặn phone finance đã pass, nhưng không được đánh đổi bằng việc mất quyền xem tiền.

Bằng chứng độc lập: [baseline_results.json](verification_15ef59b_baseline.json), [extended_results.json](verification_15ef59b_extended.json), [runner bổ sung](extended_tests_15ef59b.py).

Kết quả 33 ca do tác giả commit ghi tested_commit=b5a8ac4 vì chạy trên worktree trước khi commit remediation; nó chưa có content hash của migration. Lần chạy độc lập này ghi đúng 15ef59b. Khi publish bằng chứng tiếp theo nên ghi thêm migration hash hoặc trạng thái worktree để tránh nhầm SHA cũ với SQL đang kiểm thử.

## Khuyến nghị

Sửa các nhánh quyền/read tài chính và quyền member/pending trước; tiếp đó sửa trigger compatibility. Bổ sung các ca này vào regression suite, giữ các ca chặn phone trước đó. Cập nhật trạng thái BH-02 thành pending remediation cho tới khi tests mới pass và cổng Supabase local/staging được xác minh; chưa nên coi 33/33 là đủ đóng mọi quyền.

Không cần đổi kiến trúc hoặc mở rộng sang BH-03 để chữa lỗi. Lượt review chưa sửa SQL/Dart hoặc apply migration live. Báo cáo được publish trong lượt cập nhật tài liệu tiếp theo.
