# Review HTTP/Auth BH-07 — f9159dd — vòng 1/2

Ngày21/10/2026 (Việt Nam). Nhánh `feat/bh07-http-verification`, base `593bea86ffb807675387dba6b0276b555fdc87a1`, **tested source `f9159dd483baf2dd219b2854fd8ab08d1e5f0330`**, **docs/evidence HEAD `0758b72197a4626bd02189c0402deda978fc69fe`**. Fetch trực tiếp ref nhánh, checkout detached đúng docs HEAD, ban đầu sạch. Theo AGENTS, docs/ai/REVIEWER, review_3ad25a4 và bàn giao vòng1/2. Chỉ review bản sửa H1/H2 và test/evidence liên quan; không sửa code, không đánh dấu toàn ticket BH-07 hoàn thành.

Diff từ review công bố bd747a4 đến tested source chỉ đổi seed.sql và test HTTP. Diff tested source..docs HEAD chỉ AGENTS/docs/evidence. Migration/RPC/model/repository/provider/UI/contract giữ nguyên từ base. Nguồn thực thi của docs HEAD trùng tested source và hash trước/sau tự chạy không đổi. A/B/C/D local giữ kết luận theo SHA trước.

## Phát hiện và đóng review cũ

| Mức/trạng thái | file:dòng | Đối chiếu phát hiện cũ | Sửa tiếp |
|---|---|---|---|
| **H1 P2 — ĐẠT, đã đóng** | `scripts/bh07_http/seed.sql:204`; `test/integration/bh07_http_auth_test.dart:1214`, dòng1301 | Đúng một charge0 cho freePlayer/freeRevision. Precondition kiểm confirmed/present/exempt, revision ID/no/source/current, version, đúng một DTO charge0. Sau complete/retry, DTO và DB đều giữ đúng một revision active, đúng một charge0 của player/revision đó. | Không cần sửa thêm H1. |
| **H2 P2 — ĐẠT, đã đóng** | `test/integration/bh07_http_auth_test.dart:142`, dòng154,734,764,824,855,920 | Whitelist chính xác raw summary finance/cohost và mọi history row; cohost có đủ tám finance key với giá trị null; private key được kiểm đệ quy. Negative controls bao phủ top-level, nested và row[1]; fixture có contact/bank/account/receiver giả và kiểm nguồn tồn tại. | Không cần sửa thêm H2. |

**Không có phát hiện P0/P1/P2 còn mở trong phạm vi bản sửa được giao.**

H1 được xác minh bằng ma trận HTTP nguyên bản và [audit SQL read-only](review_f9159dd_evidence/fixture-audit.json): một present player/một charge row. JSON HTTP kiểm trước complete: charges1, đúng player/revision, due0; sau complete/retry: version4, current, revisionRows1/chargeRows1, đúng active/source1/player/revision/due0. Không dùng tổng0 của tập rỗng làm bằng chứng.

H2 được xác minh thêm bằng [bốn probe reviewer](review_f9159dd_evidence/validator-probes.log), [source](review_f9159dd_evidence/review_bh07_http_validator_probe_test.dart.txt): lấy nguyên helper mới, phát lại ba counterexample cũ (bank_account dòng đầu, phone dòng sau, receiver/account lồng nhau), đều bị từ chối; control whitelist hợp lệ vẫn được chấp nhận. Đây là unit probe validator, không phải response giả thay server trong ma trận HTTP.

[Probe raw HTTP](review_f9159dd_evidence/raw-privacy-probe.json), [script](review_f9159dd_evidence/raw_privacy_probe.py) đọc summary/history thật: tám finance field của cohost có mặt và null; toàn bộ12 marker giả có trong nguồn DB và không xuất hiện dưới dạng giá trị scalar trong projection finance/cohost/history. Nguồn private chỉ đọc bằng service-role cho audit fixture; functional RPC/ACL vẫn chạy actor thật. Không có dấu hiệu rò dữ liệu trong lượt này, không sửa quyền để làm test xanh.

## Reviewer tự chạy

[Summary](review_f9159dd_evidence/summary.json), [hash nguồn](review_f9159dd_evidence/source-hashes.json), [môi trường](review_f9159dd_evidence/environment-reviewer.json), [scope diff](review_f9159dd_evidence/scope-changes.txt).

| Hạng mục | Kết quả độc lập |
|---|---|
| Ma trận HTTP/Auth nguyên bản | **70/70 PASS**, exit0 ([log](review_f9159dd_evidence/http-test.log), [JSON](review_f9159dd_evidence/http-summary.json)) |
| `flutter analyze` | **0 issue**, exit0 ([log](review_f9159dd_evidence/analyze.log)) |
| `flutter test` toàn bộ, không bật opt-in HTTP | **240 PASS +1 SKIP**, exit0 ([log](review_f9159dd_evidence/flutter.log)) |
| `BH02_TEST_CONTAINER=bh02-review-bh06 python3 docs/reviews/bh07/run_bh07_tests.py` | **23/23 PASS**, exit0 ([log](review_f9159dd_evidence/bh07.log), JSON reviewer trong cùng thư mục) |
| Probe validator bổ sung | **4/4 PASS**, exit0; không cộng vào70 HTTP check |
| Probe raw marker/NULL | PASS; không thay hoặc cộng vào ma trận70 |

[Đối chiếu coverage](review_f9159dd_evidence/coverage-delta.json): giữ đủ65 check cũ, thêm5 check, không xóa control cũ. Nhóm70: auth8, ACL9, privacy5, scope4, complete11, finance16, summary5, history11, list1. Full Flutter tự skip test HTTP khi chưa opt-in; không gọi skip này là lần HTTP chạy thành công, ma trận đã chạy riêng.

AuthRepository/SessionRepository/FinanceRepository/SupabaseClient thật, bảy password login GoTrue/JWT thật, PostgREST thực thi RPC theo token actor. Không mock Auth/repository, không SET ROLE trong các assertion HTTP. Service-role chỉ đọc fixture/side effect trong test; GoTrue Admin API dùng service-role để tạo Auth user ở bước setup, không thay actor trong application mutation hoặc ACL check. Các control complete/free/stale/version/retry, anonymous function privilege42501 và counter idempotency confirmPayment giữ nguyên; không dùng alreadyConfirmed làm chứng cứ idempotency.

## Khác biệt môi trường và tái lập

Reviewer Linux dùng lại [orchestrator](review_f9159dd_evidence/run_local_stack.py) đã công bố ở vòng0, chỉ đổi thư mục output và SHA metadata; nguyên seed/test mới được chạy không sửa. Stack riêng gồm **GoTrue v2.197.0, PostgREST v16.4, Kong2.8.1, stock PostgreSQL17.11**. DB/Auth/REST trên Docker network internal; chỉ Kong publish loopback127.0.0.1:54321. GoTrue tự migrate schema Auth và tạo user thật; bootstrap auth.uid chuẩn đọc claims đã được PostgREST xác thực. [Bootstrap](review_f9159dd_evidence/bootstrap-public.sql.txt). Không Auth stub, không dùng database ứng dụng đang có hay môi trường remote.

Máy không có PowerShell/ComSpec. Không chạy nguyên run.ps1/full Supabase CLI custom image17.11.0.004; vòng trước đường CLI image đã lỗi dung lượng. Lần này dùng đường Linux tương đương được chủ dự án cho phép; không thử hoặc tuyên bố recipe Windows đã được xác minh. Khác biệt image/bootstrap ghi trong environment-reviewer.json. Flutter reviewer3.47.7/Dart3.13.5.

Checkout0758b72 sạch khi bắt đầu setup HTTP, worktree_dirty_before_HTTP_setup=false; source hash trùngf9159dd. Kết quả DB và probe tạm sinh sau được gom vào evidence, không coi toàn worktree sạch suốt giai đoạn gom tài liệu. Probe Dart tạm đã chuyển khỏi test/ sang .dart.txt. Không thay source ứng dụng, fixture hay test được review.

## Evidence và secret

[Audit manifest tác giả](review_f9159dd_evidence/author-hash-check.json): đủ21 path, **21/21 khớp SHA-256 sau chuẩn hóa CRLF→LF**, không còn entry DB JSON dùng quy ước CRLF khác vòng trước. Environment tác giả ghi đúng f9159dd/dirty=false; DB JSON cũng đúng f9159dd/dirty=false,23 PASS; exits green0, matrix70/70. Đây là đối chiếu dữ liệu đã bàn giao, không chứng thực độc lập lịch sử máy tác giả.

Red evidence tác giả có67/70, đúng3 FAIL: privacy.fixture-private-data, complete.free-current.precondition, complete.free-current.charge-preserved. Theo handoff, đó là new test + old seed, không phải rerun validator cũ; không dùng red làm green hoặc nói reviewer đã tự chạy red. H1/H2 được quyết định bằng source diff, lượt HTTP70 mới và probe counterexample riêng của reviewer.

[Secret scan](review_f9159dd_evidence/secret-scan.json) không tìm thấy mẫu JWT ba đoạn, sb_secret/sb_publishable key hoặc PEM private key trong evidence tác giả; scan lại evidence reviewer trước publish cũng sạch theo các mẫu đó. Không đưa runtime key/env files vào git. Giữ nguyên handoff/evidence tác giả được manifest hash; báo cáo và trạng thái hiện hành nằm ở tài liệu reviewer mới.

## Kết luận

**ĐẠT** — riêng gói kiểm chứng **HTTP/Auth local BH-07 vòng1/2** tại tested sourcef9159dd, docs/evidence0758b72; H1/H2 P2 đã đóng, không có P0/P1/P2 mới trong phạm vi sửa. Không đánh dấu toàn ticket BH-07 hoàn thành; A/B/C/D giữ kết luận local trước. Không tự merge main, apply DB thật, deploy hoặc mở pilot.

**NOT RUN:** nguyên recipe PowerShell/full Supabase CLI custom image trên máy reviewer; concurrency HTTP/PostgREST và timeout sau server commit; browser/device/offline/reopen/deep link; ngân hàng thật/VietQR/webhook; staging/production/backup/restore; rehearsal/pilot/nghiệm thu toàn BH-07; chạy lại335 hồi quy DB BH-02..06 và BH-06 integration/upgrade. Các cổng này không được suy PASS từ70 check local.
