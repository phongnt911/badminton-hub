# Review độc lập — Concurrency HTTP/Auth BH-07 tại 2f0aa59

Ngày 22/10/2026; nhánh `feat/bh07-http-concurrency`; review ban đầu, chuyển sửa vòng 1/2 theo AGENTS. Chỉ review gói kiểm chứng local, không sửa triển khai.

- Base: `4da6339a1a92bcf27675f50ca4b785fbb45f1e78`.
- Tested source: `2f0aa5930d8d1d982ced3bcda82b22b899e5881a`.
- Docs/evidence thực tế trên origin khi fetch: **`7aee525c10aa5aa4cc94611350e8b9f614028537`**, con trực tiếp của tested source. SHA `7aee5257545b7966779357d6052be1bb3eef46c2` trong yêu cầu không tồn tại trên origin (`not our ref`); không coi hai full SHA là một. Báo cáo này đánh giá source đã chỉ định và snapshot evidence thực tế vừa nêu, không xác nhận snapshot SHA không tồn tại.
- Checkout detached docs SHA thực tế sạch trước HTTP setup; ba file source khớp byte với tested source ([hash](review_2f0aa59_evidence/source-hashes.json)). Full Flutter/analyze chạy trước probe reviewer; probe là file tạm riêng, đã bỏ khỏi cây `test/` sau chạy. Không sửa migration/RPC/model/repository/provider/UI/contract. Diff base→source chỉ ba file test/script/fixture; source→docs chỉ docs/AGENTS/evidence. [Diff source](review_2f0aa59_evidence/scope-source.txt), [diff docs](review_2f0aa59_evidence/scope-docs.txt); diff main...HEAD chỉ dùng đối chiếu lịch sử, không review lại A/B/C/D.

## Phát hiện còn mở

### H1 — P2: HTTP lỗi chưa commit vẫn được nhận là drop sau commit

- **File:dòng:** `test/integration/bh07_http_auth_test.dart:219`, `:2031`, `:2036`, `:2044`.
- **Cách tái hiện:** probe reviewer import nguyên `DropResponseAfterCommitClient`, gửi RPC qua GoTrue/PostgREST local thật. Wrapper kiểm soát âm chỉ đổi amount lần đầu thành 50.000 khi outstanding đang 40.000 để server thật trả HTTP 400; không mock kết quả RPC. Helper vẫn drain rồi ném `ClientException` và đặt `dropped=true`. DB xác nhận operation của request này bằng **0 trước retry**. Retry với payload hợp lệ tạo operation đầu tiên, confirmed; count sau retry bằng 1. [Probe nguồn](review_2f0aa59_evidence/reviewer_concurrency_probe_test.dart.txt), [log](review_2f0aa59_evidence/probes.log).
- **Kỳ vọng:** bằng chứng phải phân biệt response thành công đã commit rồi mất ở client với RPC bị từ chối chưa commit. Chỉ lần đầu đã commit mới đủ điều kiện chứng minh retry không duplicate.
- **Thực tế:** helper không kiểm `response.statusCode`; mọi HTTP response của path target đều được mô tả là sau commit. Test chỉ đọc payment/ledger/operation **sau retry**, nên không loại trừ trường hợp retry mới là lần mutation đầu tiên. Probe cho kết quả `first_http_status=400`, `transport_caught=true`, `operation_before_retry=0`, `operation_after_retry=1`. Probe không khẳng định lần chạy matrix gốc bị 400; nó chứng minh assertion không bảo vệ tiền đề đã công bố.
- **Ảnh hưởng:** check thứ 76 có thể xanh mà chưa kiểm idempotency sau response mất khi commit đã xảy ra. Handoff nói sau status 200 nhưng source chưa cưỡng chế điều kiện này.
- **Cách sửa:** chỉ đánh dấu drop sau response thành công đúng contract (200 cho RPC này), ghi status/đã drain; non-2xx phải giữ thành lỗi server và không được tính control sau commit. Sau lỗi transport, **trước retry**, dùng service-role read-only xác nhận đúng request/actor/operation đã tồn tại, payment confirmed và đúng một ledger; lấy payment ID/result làm baseline. Retry đúng key+payload rồi so ID và counters không đổi. Thêm negative control non-2xx/no-operation không được vượt qua gate sau commit. Không sửa app/backend.
- **Trạng thái:** FAIL — P2 còn mở.

### H2 — P2: Bộ kiểm lỗi cạnh tranh chấp nhận lỗi domain không liên quan

- **File:dòng:** `test/integration/bh07_http_auth_test.dart:1806`, `:1934`.
- **Cách tái hiện:** probe thứ hai phát lại chính hai predicate bằng chuỗi lỗi `POSTGREST code=P0001 message=FORBIDDEN details=null hint=null`; cả predicate complete và cash đều trả true. [Log](review_2f0aa59_evidence/probes.log). Đây là control của validator, không phải tuyên bố RPC thực tế trả FORBIDDEN trong matrix.
- **Kỳ vọng:** complete competitor chỉ nhận VERSION_CONFLICT/INVALID_STATE theo contract; cash competitor phải bị từ chối vì PAYMENT_EXCEEDS_OUTSTANDING. Một lỗi ACL, validation hoặc server khác phải làm test FAIL dù bên còn lại commit và số dư vẫn đúng.
- **Thực tế:** complete cho phép bất kỳ chuỗi chứa `P0001` hoặc `409`; cash cho phép mọi `P0001`, `22023` hoặc từ `amount`. SQLSTATE chung không chứng minh lỗi domain cần kiểm. Các số đếm/summary vẫn có thể đúng nếu loser thất bại vì lý do khác.
- **Ảnh hưởng:** ma trận không phát hiện hồi quy khi request competitor bị chặn sai ACL/validation thay vì đi qua gate version/outstanding.
- **Cách sửa:** kiểm `PostgrestException` có cấu trúc và code domain chính xác (prefix message/details theo RPC hiện hành), đồng thời đối chiếu SQLSTATE hợp lệ cho từng lỗi. Không chấp nhận SQLSTATE/HTTP status/từ chung độc lập. Thêm control FORBIDDEN, NOT_FOUND, lỗi amount khác, lỗi server/transport phải bị loại. Giữ bằng chứng hai request thực sự gửi qua client độc lập và đúng một winner/loser; không nới contract/backend để làm xanh test.
- **Trạng thái:** FAIL — P2 còn mở.

Không có P0/P1 khác được xác định trong phạm vi diff này. Hai phát hiện là thiếu kiểm chứng trong test, không phải kết luận có lỗi nghiệp vụ ở RPC đã nghiệm thu.

## Kết quả reviewer tự chạy

| Lệnh/kiểm tra | Kết quả | Exit | Bằng chứng |
|---|---|---|---|
| `flutter analyze` | 0 issue | 0 | [analyze.log](review_2f0aa59_evidence/analyze.log) |
| `flutter test` | 240 PASS +1 SKIP | 0 | [flutter.log](review_2f0aa59_evidence/flutter.log) |
| `BH02_TEST_CONTAINER=bh07-http-review-db python docs/reviews/bh07/run_bh07_tests.py` | 23/23 PASS | 0 | [bh07.log](review_2f0aa59_evidence/bh07.log), [JSON](review_2f0aa59_evidence/bh07_test_results_20261022114454.json) |
| Matrix source gốc qua stack Linux thật | 76/76 PASS | 0 | [http-test.log](review_2f0aa59_evidence/http-test.log), [summary](review_2f0aa59_evidence/http-summary.json) |
| Probe reviewer | 2/2 counterexample tái hiện | 0 | [probes.log](review_2f0aa59_evidence/probes.log) |
| Manifest tác giả LF | 21/21 khớp; CRLF=0 | — | [hash check](review_2f0aa59_evidence/author-hash-check.json) |
| Quét secret author/reviewer evidence | Không thấy JWT 3 đoạn, sb_secret/sb_publishable hoặc PEM private key | — | [scan](review_2f0aa59_evidence/secret-scan.json) |
| Diff whitespace source | `git diff --check 4da6339..2f0aa59` exit 0 | 0 | source diff/hash kèm theo |

Full suite skip ma trận HTTP opt-in; ma trận đã được chạy riêng thật, không dùng skip làm kết quả HTTP. Pub ban đầu thiếu network trong sandbox (exit69); reviewer cấp network để `flutter pub get`, chạy lại analyze/full Flutter thành công. Không dùng lần thất bại môi trường làm kết quả kiểm source. Giữ nguyên 70 ID check cũ, thêm đúng 6 ID concurrency ([coverage delta](review_2f0aa59_evidence/coverage-delta.json)); H1 charge0/H2 privacy cũ vẫn nằm trong lần chạy 76. Log/JSON tác giả 76, 240+1, 23 và metadata tested source/dirty=false chỉ dùng đối chiếu, không thay kết quả reviewer. Red 70/76 là thiếu fixture, không phải control chứng minh hai lỗ hổng assertion phía trên; reviewer không chạy lại red của tác giả.

## Khác biệt môi trường

Reviewer chạy Linux/Docker, Flutter 3.47.7; **GoTrue v2.197.0, PostgREST v16.4, Kong 2.8.1, stock PostgreSQL 17.11**. Tác giả Windows/PowerShell, Flutter3.47.6, Supabase custom Postgres17.11.0.004. Linux orchestrator kế thừa recipe reviewer vòng trước, không thay source matrix; lưu [recipe](review_2f0aa59_evidence/run_local_stack.py), [local log](review_2f0aa59_evidence/local-stack.log), [environment](review_2f0aa59_evidence/environment-reviewer.json).

Auth schema do GoTrue tự migrate, user được tạo bằng Admin API rồi đăng nhập password nhận JWT thật. `auth.uid()` bootstrap đọc claims từ JWT được PostgREST xác minh; không SET ROLE/Auth stub trong matrix HTTP. AuthRepository/SessionRepository/FinanceRepository/SupabaseClient thật. Runner 23 DB riêng vẫn dùng Auth stub, không coi là HTTP. Network Docker internal, chỉ Kong bind `127.0.0.1:54321`; secret/JWT local sinh runtime, không publish. Service-role của matrix chỉ đọc counters/fixture. Probe H1 cố ý thay payload ở transport để tạo HTTP 400 thật, không làm thay đổi kết quả matrix gốc đã chạy trước đó. Các container/volume/runtime secret của reviewer được dọn sau kiểm tra.

## Phạm vi sửa tiếp

Chỉ sửa H1/H2 của gói test/script/fixture, test tái hiện đỏ trước sửa rồi xanh; bàn giao sửa vòng 1/2, tối đa 2 vòng theo AGENTS. Không viết lại A/B/C/D, không sửa RPC/migration/app/contract; giữ 70 check cũ và sáu kịch bản đã giao. Báo cáo/bằng chứng/trạng thái không phải bản sửa code.

## NOT RUN

- PowerShell `run.ps1`/full Supabase CLI recipe nguyên bản trên reviewer; đã chạy matrix source gốc qua stack Linux tương đương với khác biệt nêu trên.
- Snapshot docs/evidence full SHA không tồn tại trong yêu cầu; chỉ kiểm snapshot origin thực tế đã ghi đầu báo cáo.
- Kiểm chứng đủ điều kiện **drop sau commit** và **đúng lỗi domain competitor** chưa được ma trận gốc bảo đảm, theo H1/H2; không ghi Đạt hai cổng này từ 76/76.
- Thiết bị/browser UI e2e, offline/reopen/deep link.
- Ngân hàng/VietQR thật, đối soát/webhook.
- Staging/production, backup/restore, rehearsal/pilot; nghiệm thu toàn BH-07.
- Chạy lại 335 DB hồi quy BH-02..06 và BH-06 integration/upgrade trong lượt này (không đổi backend).

**Kết luận: Chưa đạt — gói kiểm chứng Concurrency HTTP/Auth BH-07 tại `2f0aa59`.** H1/H2 P2 cần sửa vòng 1/2. HTTP/Auth local trước tại `f9159dd` và kết luận A/B/C/D giữ nguyên; không merge main, apply DB thật hoặc deploy.
