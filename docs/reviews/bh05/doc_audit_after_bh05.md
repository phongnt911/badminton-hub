# Rà soát tài liệu sau BH-05 — chờ chủ dự án quyết các đề xuất C

Ngày 16/10/2026 (Việt Nam). Vai trò: người cập nhật tài liệu, chỉ đối chiếu tĩnh; không thay kết luận reviewer hoặc chạy lại kiểm thử app/DB.

Nguồn trước cập nhật: `origin/main=5ee6228`, nhánh `docs/audit-after-bh05=390d713`. Bốn blob trong WORK_ORDER đều khớp, working tree sạch, Markdown dùng LF. Chủ dự án xác nhận dùng ba bản nháp trực tiếp trong `doc-update-pack/` và giữ gói đã tự commit; không dùng đường dẫn `drafts/` không tồn tại, không tạo lại nhánh đã có hoặc gỡ gói khỏi Git. Phần A và B1–B9 cập nhật riêng; các đề xuất C dưới đây chỉ báo cáo, chưa sửa hợp đồng, migration hay review có sẵn.

## C1. Hợp đồng §12 so với bốn migration BH-05

Đọc [08_DOMAIN_CONTRACTS.md §12](../../08_DOMAIN_CONTRACTS.md#12-bh-05-đăng-ký--duyệt--huỷ--lời-mời-đã-triển-khai--migration-20261015170500_bh05_registrationssql). Bảng dưới dùng định nghĩa **cuối cùng theo thứ tự migration**, không lấy bản gốc đã bị CREATE OR REPLACE thay thế.

Quy ước kết quả:

- **R**: JSONB `{player_id, session_id, registration_status, attendance_status, participant_type, fee_exempt, agreed_fee_vnd, confirmed_count, capacity, seats_left, session_version}` từ `registration_result`, migration gốc dòng 10–52.
- **I+**: JSONB `{invitation_id, session_id, player_id, status, invited_at, expires_at}`; **I−**: cùng cấu trúc nhưng không có `invited_at`. Không có `invitation_status` hoặc toàn bộ trường R.
- **A**: `REVOKE ALL ON FUNCTION <đúng signature> FROM PUBLIC, anon; GRANT EXECUTE ... TO authenticated`. Cả 10 RPC đều có A, không phải cho mọi authenticated quyền trên mọi buổi; thân hàm kiểm actor và quyền/trạng thái tương ứng. Cả 10 dùng SECURITY DEFINER, search_path public, pg_temp.
- Mã lỗi trong bảng là prefix thông điệp cùng SQLSTATE do thân RPC trực tiếp RAISE. Chín mutation còn có thể truyền `IDEMPOTENCY_CONFLICT/23505` từ `check_idempotency` (migration `20261015140216_bh03_identity_retry_session_fixes.sql`:3–33). Không liệt kê hết lỗi constraint hoặc lỗi hệ thống PostgreSQL.
- `DEFAULT NULL` là mặc định SQL; mutation vẫn bắt buộc request ID khác NULL, thiếu sẽ `INVALID_INPUT/22023`. Tên và thứ tự tham số trong bảng là chính xác; UUID, TEXT, BOOLEAN, TIMESTAMPTZ là kiểu SQL.

| RPC, tham số thực tế | Trả về thực tế | GRANT/REVOKE | Prefix lỗi / SQLSTATE trực tiếp | Định nghĩa cuối |
|---|---|---|---|---|
| `request_join_session(p_session_id UUID, p_contact TEXT DEFAULT NULL, p_request_id UUID DEFAULT NULL)` | JSONB R | A | `UNAUTHENTICATED/42501`, `INVALID_INPUT/22023`, `NOT_FOUND/P0002`, `FORBIDDEN/42501`, `INVALID_STATE/22023`, `DEADLINE_PASSED/22023`, `DUPLICATE_PARTICIPANT/23505` | `20261015170500_bh05_registrations.sql:138` |
| `add_session_player(p_session_id UUID, p_member_id UUID DEFAULT NULL, p_guest_name TEXT DEFAULT NULL, p_contact TEXT DEFAULT NULL, p_fee_exempt BOOLEAN DEFAULT FALSE, p_allow_waitlist BOOLEAN DEFAULT FALSE, p_request_id UUID DEFAULT NULL)` | JSONB R | A | `UNAUTHENTICATED/42501`, `INVALID_INPUT/22023`, `NOT_FOUND/P0002`, `FORBIDDEN/42501`, `INVALID_STATE/22023`, `DUPLICATE_PARTICIPANT/23505`, `CAPACITY_FULL/22023` | `20261016090000_bh05_review_fixes.sql:138` |
| `decide_registration(p_session_id UUID, p_player_id UUID, p_decision TEXT, p_reason TEXT DEFAULT NULL, p_request_id UUID DEFAULT NULL)` | JSONB R | A | `UNAUTHENTICATED/42501`, `INVALID_INPUT/22023`, `NOT_FOUND/P0002`, `FORBIDDEN/42501`, `INVALID_STATE/22023`, `DEADLINE_PASSED/22023`, `CAPACITY_FULL/22023` | `20261016090000_bh05_review_fixes.sql:336` |
| `cancel_registration(p_session_id UUID, p_player_id UUID, p_reason TEXT DEFAULT NULL, p_request_id UUID DEFAULT NULL)` | JSONB R | A | `UNAUTHENTICATED/42501`, `INVALID_INPUT/22023`, `NOT_FOUND/P0002`, `FORBIDDEN/42501`, `INVALID_STATE/22023`, `DEADLINE_PASSED/22023` | `20261016090000_bh05_review_fixes.sql:468` |
| `record_attendance(p_session_id UUID, p_player_id UUID, p_attendance TEXT, p_request_id UUID DEFAULT NULL)` | JSONB R | A | `UNAUTHENTICATED/42501`, `INVALID_INPUT/22023`, `NOT_FOUND/P0002`, `FORBIDDEN/42501`, `INVALID_STATE/22023` | `20261015170500_bh05_registrations.sql:738` |
| `invite_waitlisted_player(p_session_id UUID, p_player_id UUID, p_expires_at TIMESTAMPTZ DEFAULT NULL, p_request_id UUID DEFAULT NULL)` | JSONB I+ | A | `UNAUTHENTICATED/42501`, `INVALID_INPUT/22023`, `NOT_FOUND/P0002`, `FORBIDDEN/42501`, `INVALID_STATE/22023`, `DEADLINE_PASSED/22023` | `20261015170500_bh05_registrations.sql:832` |
| `revoke_waitlist_invitation(p_session_id UUID, p_invitation_id UUID, p_reason TEXT DEFAULT NULL, p_request_id UUID DEFAULT NULL)` | JSONB I− | A | `UNAUTHENTICATED/42501`, `INVALID_INPUT/22023`, `NOT_FOUND/P0002`, `FORBIDDEN/42501`, `INVALID_STATE/22023` | `20261015170500_bh05_registrations.sql:941` |
| `accept_waitlist_invitation(p_session_id UUID, p_invitation_id UUID, p_consent_note TEXT DEFAULT NULL, p_request_id UUID DEFAULT NULL)` | JSONB R + invitation_id, invitation_status=accepted | A | `UNAUTHENTICATED/42501`, `INVALID_INPUT/22023`, `NOT_FOUND/P0002`, `FORBIDDEN/42501`, `INVALID_STATE/22023`, `INVITATION_REVOKED/22023`, `INVITATION_EXPIRED/22023`, `DEADLINE_PASSED/22023`, `CAPACITY_FULL/22023` | `20261016090000_bh05_review_fixes.sql:595` |
| `get_my_waitlist_invitation(p_session_id UUID)` | JSONB I+ hoặc SQL NULL (không có lời mời pending chưa hết hạn của actor; actor NULL cũng trả NULL nếu gọi được thân hàm) | A | Không RAISE trực tiếp; anon bị chặn EXECUTE bởi ACL (42501) | `20261015170500_bh05_registrations.sql:1191` |
| `start_session(p_session_id UUID, p_request_id UUID DEFAULT NULL)` | JSONB projection get_session_public_detail: id, lifecycle, version, can_manage, my_registration…; không phải R | A | `UNAUTHENTICATED/42501`, `INVALID_INPUT/22023`, `NOT_FOUND/P0002`, `FORBIDDEN/42501`, `INVALID_STATE/22023` | `20261016100000_bh05_start_session.sql:13` |

ACL kiểm ở migration gốc dòng 299–300, 826–827, 935–936, 1030–1031, 1231–1232; migration review fixes dòng 330–331, 462–463, 589–590, 752–753; start_session dòng 74–75. Hai helper `registration_result` và `bump_billing_input_version` REVOKE EXECUTE PUBLIC/anon/authenticated ở gốc dòng 52/65. `list_session_players(UUID, INT DEFAULT 100, INT DEFAULT 0)` là RPC mở rộng ngoài danh sách 10, trả JSONB array (rỗng `[]`), A ở dòng 132–133; management được kiểm trong thân hàm. Migration `20261016091000` thay `set_session_lifecycle` để cancel thu hồi pending invitation; đây là RPC BH-04 được sửa bổ sung, không tính thành RPC BH-05 thứ 11.

### Những chỗ lệch cần chủ dự án quyết

| ID / vị trí tài liệu | Tài liệu nói | Bằng chứng thực tế | Đề xuất / ảnh hưởng code và test |
|---|---|---|---|
| C1-01 — `docs/08_DOMAIN_CONTRACTS.md:154`, :161–162 | Mọi mutation trả R; RPC lời mời thêm invitation_id/invitation_status | Migration gốc :919–928 trả I+ cho invite; :1019–1026 trả I− cho revoke; chỉ accept (review fixes :746–747) trả R + invitation_status | Sửa **tài liệu** để tách ba response. Client hiện dùng WaitlistInvitation cho invite/revoke (`lib/data/session_repository.dart:306`, :322), RegistrationResult cho accept (:338). Không đề xuất đổi code/test; consumer mới viết theo tài liệu cũ có thể parse sai. |
| C1-02 — `docs/08_DOMAIN_CONTRACTS.md:150–170` | Chỉ liệt kê 8 mutation + get_my; không có start_session, chỉ dẫn tới migration gốc | Migration start_session :13–75, published→in_progress, management, request ID/replay/audit; trả projection get_session_public_detail (:68), không trả R | Sửa **tài liệu** để bổ sung mutation thứ 9 và liên kết các forward migration. `docs/22:62` đếm 10 RPC là đúng (9 mutation + 1 đọc). Repository.startSession đã có (:183); không đề xuất đổi code/test, tránh người tiếp theo tưởng RPC chưa tồn tại hoặc kỳ vọng response R. |
| C1-03 — `docs/08_DOMAIN_CONTRACTS.md:162` | Revoke chỉ lời mời pending | Migration gốc :994–1028 chặn accepted/expired, nhưng trạng thái revoked cũng trả status=revoked và lưu idempotency, không ghi audit/UPDATE lần nữa | Đề xuất làm rõ **tài liệu**: pending có side effect, revoked là no-op thành công (kể cả request ID mới); accepted/expired lỗi. Nếu muốn từ chối revoked thì cần quyết định đổi migration forward + test; lượt này không sửa. Không chứng minh thêm lỗi runtime. |
| C1-04 — `docs/08_DOMAIN_CONTRACTS.md:157–159`, :163 | Mô tả quyền management/self; §12 chưa nhắc gate finance sau active charge revision | Review fixes :263–268 (add confirmed), :419–423 (decide confirmed), :552–556 (cancel confirmed), :706–711 (accept) bổ sung FORBIDDEN nếu thiếu finance khi có active revision | Đề xuất bổ sung **tài liệu §12**/cross-reference ADR-08, giữ code gate và regression A1 hiện có. Đây là thiếu chi tiết trong mục RPC, không kết luận hợp đồng toàn tài liệu bỏ qua finance; không đề xuất nới quyền để khớp mô tả rút gọn. |

Các tên/thứ tự tham số của 9 RPC đã liệt kê trong §12 khớp migration; mặc định SQL và kiểu cụ thể được bổ sung ở bảng đối chiếu, không coi `p_request_id DEFAULT NULL` là quyền bỏ request ID. `get_my_waitlist_invitation` không lộ token/contact và có thể trả NULL. Quyền execute không lệch mô tả; chưa kiểm ACL thực trên Supabase remote.

## C2. Kiểm tra `docs/22` §3 và §7

### SHA256 và kiểu xuống dòng

Bốn tên migration tại `docs/22:55–58` đều tồn tại. Đo `hashlib.sha256(Path(...).read_bytes())`, đối chiếu `git show HEAD:<file>` và `git ls-files --eol`; cả bốn blob Git và working tree hiện tại đều LF (`i/lf w/lf`), không sửa hay chuẩn hoá file trong repo.

| Migration | SHA256 byte hiện tại = blob Git = chuẩn LF | SHA256 ghi ở handoff | Đối chiếu |
|---|---|---|---|
| `20261015170500_bh05_registrations.sql` | `356f5831649eb4d09efa624402679cce67211056ce44e09cf6088715970ac588` | `2c63e2cb5cf98d7b7c1474ec09e7ada61bc0a6b67130b5776a8ca8f95aaade51` | Khớp khi biểu diễn CRLF, khác byte LF hiện tại |
| `20261016090000_bh05_review_fixes.sql` | `f0e2573c0f95e1108511f78acece37f90eaa0cb7c63093389e25a8878bc5e30e` | `629a0cad48587fe7516f48962d4a5c44fac69c493fb1b1b0f1e42a535ef369a7` | Khớp khi biểu diễn CRLF, khác byte LF hiện tại |
| `20261016091000_bh05_a3_cancel_revokes_invitations.sql` | `8895c9550a2611915b218ab92b5742a37acaca6f3ed8e88c951efc7a7b0fba72` | `5981843750597ec54864bdf99e26a75d920dfb8c889bda0f6a748b60a09a0442` | Khớp khi biểu diễn CRLF, khác byte LF hiện tại |
| `20261016100000_bh05_start_session.sql` | `72474dd0072c74b2b42dcb9a6e5d12621afa4206c13aadb0f2c30ad228309dfc` | `72474dd0072c74b2b42dcb9a6e5d12621afa4206c13aadb0f2c30ad228309dfc` | Khớp LF |

**C2-01 — `docs/22_BH05_HANDOFF.md:55–57`, :69:** ba hash đầu là hash CRLF; ghi chú :69 nói “Tệp trong repo dùng CRLF” không đúng với blob/checkout LF hiện tại. Chuyển **trong bộ nhớ** LF→CRLF tái tạo chính xác cả ba hash cũ, nên không suy ra nội dung SQL bị đổi. JSON hồi quy main `main_3a34883/bh05_test_results_20261016004418.json`, trường `migration_sha256`, khớp cả bốn hash LF ở bảng. Đề xuất chỉ sửa tài liệu để ghi rõ hash blob LF và hash checkout CRLF lịch sử, không sửa migration/bằng chứng. Ảnh hưởng: đối chiếu hash byte theo handoff sẽ báo lệch giả ở ba file; chưa thấy ảnh hưởng hành vi code/test do nội dung SQL từ phép đổi EOL này.

### Bằng chứng và số kiểm thử

Bảng §7 dùng JSON lịch sử tại các commit khác nhau, không phải JSON hồi quy main. Đã kiểm sự tồn tại, total/passed/failed, tested_commit và worktree_dirty (nếu được ghi) của từng tệp; tất cả khớp bảng §7. Sáu tổng cũng khớp [summary hồi quy main](main_3a34883/summary.json) và sáu JSON main tương ứng, nhưng giữ riêng nguồn/commit.

| Bộ | JSON lịch sử được dẫn trong §7 | PASS/FAIL lịch sử | JSON hồi quy main tại 3a34883 | PASS/FAIL main |
|---|---|---|---|---|
| BH-02 RLS | `bh02/rls_test_results_20261016001344.json` | 33/0 | `rls_test_results_20261016004348.json` | 33/0 |
| BH-02 extended | `bh02/extended_results_20261016001344.json` | 14/0 | `extended_results_20261016004348.json` | 14/0 |
| BH-03 | `bh03/bh03_test_results_20261016001354.json` | 48/0 | `bh03_test_results_20261016004353.json` | 48/0 |
| BH-03 retry | `bh03/bh03_retry_results_20261016001354.json` | 22/0 | `bh03_retry_results_20261016004353.json` | 22/0 |
| BH-04 | `bh04/bh04_test_results_20261016001406.json` | 44/0 | `bh04_test_results_20261016004408.json` | 44/0 |
| BH-05 | `bh05/bh05_test_results_20261016001243.json` | 90/0 | `bh05_test_results_20261016004418.json` | 90/0 |

- Tổng 33 + 14 + 48 + 22 + 44 + 90 = **251/251 DB**, sáu runner trong summary.json đều exit 0. BH-05 có 90 kết quả = 45 kịch bản × CLEAN/LEGACY; không phải 90 kịch bản khác nhau.
- §7:122 ghi 137 = 104 + 28 + 5; log main `main_3a34883/flutter.log` kết thúc `+137: All tests passed!`, `analyze.log` có `No issues found!`. summary.json chỉ tổng hợp DB, không chứa số Flutter/analyze; xác minh hai mục này bằng log và review_main_3a34883.
- JSON tái hiện `bh05_test_results_20261016000811.json` tồn tại: 90 tổng, 82 PASS / 8 FAIL, khớp §7:134; không lấy 8 FAIL này làm trạng thái hiện hành.
- `docs/reviews/bh05/run_bh05_tests.py` tồn tại. Mười migration của chuỗi tồn tại, khớp danh sách migration_sha256 của JSON main BH-05; số “10 migration” ở §7:123 không phải 10 migration riêng BH-05.
- Flutter 3.47.6 và container bh02-test-postgres ở §7 là môi trường tác giả lịch sử; review main ghi Flutter 3.47.7/Dart 3.13.5, PostgreSQL 17.11/bh02-review-postgres. Đọc được hai nguồn riêng; không thay môi trường cũ bằng môi trường review. Không khẳng định đã tái dựng toolchain trong lượt docs này.

Không phát hiện lệch tên file hoặc số kiểm thử trong §3/§7 ngoài ghi chú/hash EOL C2-01. Không thay JSON/log/review gốc và không coi kiểm đếm bằng chứng là chạy lại test.

## C3. Quét link tương đối

Phạm vi: `README.md` và toàn bộ 22 file `docs/*.md` (23 file tổng). Script Python tạm `/tmp/check_doc_links.py` (không commit) đọc inline Markdown links/images và reference definitions, bỏ fenced code/code span, bỏ URL có scheme; giải mã URL, resolve theo thư mục file và kiểm file/thư mục đích. Với đích Markdown có fragment, kiểm slug heading (kể cả heading trùng). Không truy cập URL bên ngoài, không diễn giải đường dẫn trong backtick là hyperlink.

Kết quả sau phần A/B: **136 link tương đối, 0 link hỏng** (bao gồm fragment). Riêng ba file phần A: **50 link tương đối, 0 link hỏng** khi kiểm lại trước push. Không sửa link hoặc nội dung tài liệu khác trong phần C. Báo cáo mới này không nằm trong glob `docs/*.md`; các link Markdown trong báo cáo được kiểm thêm riêng trước commit.

## Phạm vi và giới hạn giữ nguyên

- A1–A3 và B1–B9 đã áp dụng; không có mục B bỏ qua vì chưa tick. R1/R4 và nhật ký cũ giữ nguyên; R5 chỉ xác nhận phạm vi DB/validation, chưa xác minh form giữ giờ nhập bằng UI e2e. R6 ghi rõ QR thật thuộc BH-06, chưa làm.
- Ba bản nháp không xung đột số liệu với review/JSON hiện có. Cụm “local/staging” là nhãn mức triển khai tài liệu, **không phải đã apply staging thật**; phần trạng thái/NOT RUN ghi rõ điều này.
- Tám mục lịch sử chuyển nguyên văn từ blob origin/main của docs/00, có kiểm so sánh nội dung; mục cuối STATUS_HISTORY là bổ sung mới. Các file Markdown giữ LF.
- NOT RUN: chạy lại flutter analyze/flutter test/runner DB trong lượt docs; PostgREST HTTP/JWT thật; thiết bị/browser e2e và deep link OS; apply staging/production; backup/restore; concurrency qua HTTP, kể cả host revoke trong lúc client refresh. Số PASS dẫn từ bằng chứng đã lưu, không phải kết quả chạy mới.
- Không sửa code, test, migration, runner, JSON/log bằng chứng hoặc review có sẵn. Không apply DB, merge/push main hoặc xác nhận production-ready. Các đề xuất C1-01..04 và C2-01 chờ chủ dự án quyết; không phải kết luận review lại BH-05.
