# BH-02: bàn giao sau review và kiểm thử RLS

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
