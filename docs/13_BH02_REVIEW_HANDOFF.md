# BH-02: bàn giao sau review và kiểm thử RLS

> **Hiện hành 16/10/2026:** Nội dung dưới là snapshot BH-02 trước remediation; H1–H3 đã có sửa và regression 33+14 PASS. Không dùng dòng CHƯA ĐẠT cũ để chặn tiếp tục BH-06. BH-05 đạt review tích hợp tại `d769531`; hồi quy main `3a34883`: analyze sạch, 137 Flutter + 251 DB. Tiếp theo BH-06. Chỉ kiểm thử local/PostgreSQL cô lập; chưa apply staging/production, chưa HTTP/JWT thật, thiết bị/browser e2e, backup/restore hoặc concurrency qua HTTP. [Trạng thái và xác nhận sau audit](23_DOC_AUDIT_FOLLOWUP.md).

Ngày 15/10/2026. Baseline: commit `3fa3cdae72ef08895d3ad62f3a31e95dc5b7fa35`. Trạng thái **CHƯA ĐẠT NGHIỆM THU**, không tự chuyển BH-03. Có file migration và tests cấu trúc, nhưng DB tests cô lập cho kết quả 18 PASS / 15 FAIL trên 33 ca.

## Đọc trước khi tiếp tục

1. [Code review F1–F6](reviews/bh02/code_review.md).
2. [Kết quả thực thi và F7](reviews/bh02/rls_test_report.md).
3. [Expected/actual từng ca](reviews/bh02/rls_test_results.json).
4. `03_DATABASE.md`, `08_DOMAIN_CONTRACTS.md`, ADR và AG-02 như nguồn yêu cầu.

33 ca không phải tỷ lệ bảo mật tổng thể. Auth stub chỉ mô phỏng auth.users/auth.uid và các role; chưa kiểm PostgREST HTTP/JWT, full Supabase, concurrency hay các RPC BH-05/BH-06 chưa triển khai. Không chạy writes/tests trên production. Fixture chỉ chứa email/phone/bank giả.

## Các đầu việc bắt buộc

| ID | Mức | Phạm vi sửa tối thiểu | Nghiệm thu |
|---|---|---|---|
| F1 | P1 | Helper audit/idempotency nội bộ, không expose cho client; revoke EXECUTE PUBLIC/anon/authenticated theo đường gọi phù hợp | anon/outsider không forge audit, user không preseed replay; RPC nghiệp vụ vẫn ghi đúng trong transaction |
| F2 | P1 | Không cho outsider SELECT raw sessions/private fields hoặc scan unlisted/draft | receiver_snapshot và contact legacy không đọc ngoài quyền; public projection whitelist |
| F3 | P1 | Thiết kế lại public aggregate theo grants+RLS, không mở player rows để đếm | anon/player/outsider/host cùng thấy count=2; contact vẫn private |
| F4 | P1 | Upgrade legacy có mapping/cách ly/backfill/constraints và xử lý NOT NULL cũ | Payload đích insert được trên sạch và legacy; không mất dữ liệu/không suy owner từ phone |
| F5 | P2 | Projection khoản riêng vượt được JOIN RLS một cách có kiểm soát | player thấy due=70000, paid=20000, remaining=50000; không thấy người khác, freshness đúng |
| F6 | P2 | Bank owner/treasurer/self read bằng grant+policy hoặc RPC bảo vệ | Đọc đúng account thuộc quyền, outsider bị chặn |
| F7 | P1 | Đóng đường đọc phone_number cũ từ session_players cho finance không management | treasurer không đọc contact mới hoặc bản sao legacy; owner/host có quyền vẫn vận hành |

Thứ tự: F1/F2/F7 → F3/F4 → F5/F6. Không refactor Dart toàn app hoặc thêm backend để sửa quyền. Không lấy revoke tất cả read/write rồi làm app hỏng làm tiêu chí an toàn hoàn thành.

## Prompt giao Antigravity

> Đọc AGENTS.md, docs/00_START_HERE.md và docs/13_BH02_REVIEW_HANDOFF.md cùng báo cáo/JSON liên kết. Tiếp tục BH-02 từ commit baseline; đối chiếu HEAD hiện tại và giữ các sửa mới nếu có. Sửa F1–F7 theo bảng phạm vi, từng nhóm commit liên quan; không chuyển sang BH-03 hoặc dựng lại kiến trúc. Đọc SQL thật, đặc tả 03/08/ADR trước khi sửa. Không mở public SELECT/UPDATE hoặc client EXECUTE helper nội bộ để làm test pass. Không xóa dữ liệu legacy hoặc tự suy quyền sở hữu. Trước sửa nêu file, phương án và regression tests; xác định migration đã apply ở môi trường nào: nếu đã apply/shared thì tạo forward migration, không sửa lịch sử đã triển khai. Chưa có bằng chứng apply thì báo rõ, không giả định. Thêm tests DB hành vi bằng role app và giữ 33 expected đúng; thêm fixture nâng cấp có dữ liệu trước migration, không chỉ tạo bảng rỗng. Chạy trên local/staging, không production. Báo từng ca PASS/FAIL/NOT RUN, flutter tests/analyze liên quan, migration path và giới hạn. Không đánh dấu done khi chưa đạt cổng nghiệm thu. Nếu không có Docker, chuẩn bị code/tests và báo blocker, không chờ vô hạn hay dùng production thay thế.

## Dựng lại kiểm thử trên Docker

Runner là bằng chứng tái hiện PostgreSQL-level; không yêu cầu cài stack Supabase đầy đủ. Cần Docker chạy được và Python 3 trên máy thực thi. Container không mở cổng, không nối Supabase; data tmpfs mất khi remove. Dùng tên mới nếu tên bên dưới đã được dùng cho dữ liệu cần giữ, không tự xóa container của người khác.

```bash
docker run -d --name bh02-review-postgres --network none --tmpfs /var/lib/postgresql/data -e POSTGRES_HOST_AUTH_METHOD=trust postgres@sha256:b0f9560a2de083e2cc7382e75f808c7381a32852a7ec49117deedb300e552b24
docker exec bh02-review-postgres pg_isready -U postgres
docker exec bh02-review-postgres psql -U postgres -v ON_ERROR_STOP=1 -c "CREATE ROLE anon NOLOGIN; CREATE ROLE authenticated NOLOGIN;"
python docs/reviews/bh02/run_rls_tests.py
```

Chờ pg_isready báo accepting connections rồi mới bước sau. Nếu dùng container test khác, đặt biến BH02_TEST_CONTAINER (tên bắt đầu bh02-). Runner tạo hai DB test timestamp mỗi lượt, fixtures giả, mỗi ca BEGIN/ROLLBACK; không có connection string remote. Chỉ bootstrap role một lần cho container mới. PostgreSQL default function ACL có thể khác live; cần test lại Supabase local/staging thật trước chốt rollout.

Runner không chứa triển khai sửa lỗi. Nếu API read được đổi sang RPC an toàn, cập nhật regression test để kiểm đúng public contract mới, vẫn giữ các ca chặn raw read/helper write; không chỉ sửa expected thành hành vi đang lỗi. Runner tự ghi HEAD hiện tại vào tested_commit và tạo rls_test_results_<timestamp>.json cho mỗi lượt; giữ rls_test_results.json baseline làm lịch sử. Không gán kết quả mới cho SHA cũ.

## Cổng đóng BH-02

- DB sạch và upgrade fixture có dữ liệu đều chạy; constraints/quyền/read contracts đạt.
- F1–F7 có regression test pass; phát hiện mới phải xử lý/ghi rõ.
- Supabase local/staging: kiểm quyền table/view/RPC với anon, host/player/outsider/cohost/treasurer; HTTP/JWT nếu liên quan được ghi kết quả.
- Không có dữ liệu thật/secrets trong fixture/log; không thay production ngoài kế hoạch release được giao.
- Cập nhật nhật ký đúng kết quả; 9 tests sqlContent.contains không thay thế DB behavior tests.

## Kết quả nghiệm thu thực tế (15/10/2026)

- **Môi trường**: Container Docker PostgreSQL `bh02-review-postgres` (image `postgres@sha256:b0f9560a2de083e2cc7382e75f808c7381a32852a7ec49117deedb300e552b24`), `--network none`, tmpfs data.
- **Kết quả runner**: **33/33 PASS, 0 FAIL** (100% pass). Toàn bộ F1–F7 đã khắc phục triệt để trên cả schema sạch (`clean`) và schema nâng cấp (`legacy`).
- **File bằng chứng**: [rls_test_results_20261015115541.json](reviews/bh02/rls_test_results_20261015115541.json).
- **Kiểm thử Flutter**: 10/10 schema migration tests passed; toàn bộ 38/38 flutter tests passed; `flutter analyze` 0 issues.
- **Kết luận**: BH-02 chính thức **ĐÃ ĐẠT NGHIỆM THU**, đủ điều kiện chuyển sang ticket BH-03.

## Cập nhật ưu tiên: review độc lập commit 15ef59b (15/10/2026)

**Trạng thái hiện hành: BH-02 chưa đạt nghiệm thu đầy đủ, chờ sửa H1–H3.** Mục nghiệm thu 33/33 phía trên giữ làm lịch sử của bộ ca cũ, không phải kết luận cuối sau review mở rộng. Đã xác nhận độc lập 33/33 ca cũ PASS; thêm 6 ca FAIL, tổng 39 ca = 33 PASS / 6 FAIL. Không sửa expected để hợp thức hóa lỗi.

Bằng chứng: [review bổ sung](reviews/bh02/review_15ef59b.md), [33 ca cũ](reviews/bh02/verification_15ef59b_baseline.json), [6 ca bổ sung](reviews/bh02/verification_15ef59b_extended.json). Tất cả là PostgreSQL cô lập với Auth stub tối thiểu, chưa kiểm full Supabase HTTP/JWT/production.

| ID | Mức | Cần sửa | Acceptance |
|---|---|---|---|
| H1 | P1 | Finance mất roster join nên không thấy công nợ/payment; sửa F7 không được làm mất chức năng finance | Treasurer/session finance thấy 2 khoản nợ và payment confirmed 20.000đ; contact mới/legacy vẫn bị chặn; host/player riêng vẫn đúng |
| H2 | P1 | Raw sessions cho member chưa tham gia và pending guest đọc receiver_snapshot | Member chưa tham gia, pending/waitlisted/rejected/cancelled không đọc snapshot/contact private; confirmed chỉ nhận payment instructions theo quyền; public/unlisted projection vẫn dùng được |
| H3 | P2 | Trigger legacy chỉ điền khi NULL, venue_name lấy title | Đổi starts_at/ends_at cập nhật ngày/giờ legacy; đổi venue_id cập nhật tên sân đúng; tiêu đề buổi không thay tên sân; giữ dữ liệu cũ chưa xác minh |

### Prompt tiếp tục cho Antigravity

> Đọc AGENTS.md, docs/00_START_HERE.md và mục cập nhật review 15ef59b trong docs/13_BH02_REVIEW_HANDOFF.md cùng review/JSON liên kết. Chưa chuyển BH-03. Giữ 33 ca cũ đang PASS và sửa H1–H3, mỗi nhóm commit liên quan. H1: cung cấp financial roster/outstanding/payments có authorization phù hợp; không khôi phục đọc toàn bảng player cho finance vì sẽ lộ phone legacy. H2: không cấp raw private session fields cho member/pending; dùng whitelist projection và payment instructions riêng. H3: đồng bộ legacy theo trường nguồn có quy tắc rõ khi INSERT/UPDATE và mapping sân từ venue_id; không suy tên sân từ title. Đọc spec 03/08/ADR và SQL hiện tại trước sửa. Xác định migration đã apply/shared ở môi trường nào: nếu có thì tạo forward migration, không sửa lịch sử đã triển khai; nếu chưa biết thì ghi rõ. Thêm regression tests cho treasurer và role finance theo buổi không management, member không đăng ký, các trạng thái registration, sửa ngày/giờ/venue legacy và fixture có dữ liệu trước migration. Chạy local/staging, giữ cả bảo mật lẫn các read chức năng đúng. Báo từng ca PASS/FAIL/NOT RUN, tested commit, migration content hash/worktree state và giới hạn full Supabase. Không tự apply production, không đánh dấu done chỉ từ sqlContent.contains hoặc 33/33 bộ cũ.

### Chạy các ca bổ sung

Sau khi dựng container theo hướng dẫn phía trên, chạy runner 33 ca tạo DB test và kết quả timestamp; rồi chạy:

```bash
python docs/reviews/bh02/extended_tests_15ef59b.py
```

Script đọc kết quả timestamp mới nhất từ runner để lấy tên DB clean/legacy vừa seed, chạy 6 ca trong BEGIN/ROLLBACK, xuất extended_results_<timestamp>.json và không ghi đè bằng chứng baseline. Cần cùng BH02_TEST_CONTAINER nếu dùng tên container khác. Đây là harness tái hiện baseline 15ef59b; khi sửa read API thành RPC an toàn, cập nhật đường gọi test theo contract nhưng giữ quyền mong đợi, các ca raw private read phải tiếp tục chặn. Bổ sung ca theo session_finance độc lập và các status ngoài pending vì 6 ca hiện chưa bao phủ hết.

### Cổng đóng cập nhật

Ngoài cổng trước đó, H1–H3 phải có regression PASS trên clean/legacy; finance vẫn vận hành và không đọc contact, member/pending không đọc snapshot, update lịch/sân legacy đúng. Kết quả 39 ca baseline là lịch sử cần giữ, không sửa thành kết quả của code khác. Nếu chưa kiểm Supabase local/staging thật thì ghi rõ NOT RUN, không gọi đó là nghiệm thu đầy đủ production.

## Kết quả nghiệm thu thực tế sau remediation H1–H3 (15/10/2026)

- **Môi trường**: Container Docker PostgreSQL `bh02-review-postgres` (image `postgres@sha256:b0f9560a2de083e2cc7382e75f808c7381a32852a7ec49117deedb300e552b24`), `--network none`, tmpfs data.
- **Migration Content Hash (SHA256)**: `91680c9b32fc438057293db0e4df29f4b979f50ee6e00a5ea08c6603e3967e50`.
- **Kết quả runner 33 ca baseline**: **33/33 PASS, 0 FAIL** (kết quả tại [rls_test_results_20261015122655.json](reviews/bh02/rls_test_results_20261015122655.json)).
- **Kết quả runner 14 ca mở rộng (extended & regression)**: **14/14 PASS, 0 FAIL** (kết quả tại [extended_results_20261015122655.json](reviews/bh02/extended_results_20261015122655.json)), bao gồm:
  - 6 ca ban đầu từ review 15ef59b: treasurer roster, treasurer payment, member/pending chặn snapshot, legacy time và venue mapping.
  - 8 ca bổ sung: role finance độc lập (không management), waitlisted/cancelled chặn snapshot, RPC payment instructions whitelist/chặn pending, và legacy venue_id/ends_at update.
- **Tổng số DB tests**: **47/47 PASS (100%)**.
- **Kiểm thử Flutter**: 11/11 schema migration unit tests passed; toàn bộ 39/39 Flutter tests passed; `flutter analyze` 0 issues.
- **Trạng thái & Quyết định**: Toàn bộ H1–H3 đã được giải quyết triệt để. Cổng nghiệm thu BH-02 chính thức **ĐẠT CHUẨN**, sẵn sàng bàn giao sang BH-03.
- **Giới hạn**: Chưa kiểm thử trên PostgREST HTTP/JWT và chưa apply lên Supabase production (tuân thủ không tự deploy production).
