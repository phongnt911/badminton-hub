# Review BH-07 HTTP/Auth local — 3ad25a4

Ngày 21/10/2026 (Việt Nam). Nhánh `feat/bh07-http-verification`, base `593bea86ffb807675387dba6b0276b555fdc87a1`, **tested source `3ad25a4ac8c2ee1beaa76b3810860ecde514d86e`**, **docs/evidence HEAD `c54b004d881ecf408447d2f1f4385d4a3b49f233`**. Fetch trực tiếp nhánh, checkout detached đúng c54b004, ban đầu sạch. Theo AGENTS, docs/ai/REVIEWER, contracts và yêu cầu kiểm chứng cụ thể của chủ dự án. Không sửa code. A/B/C/D giữ kết luận trước theo SHA; không merge main hoặc apply/deploy DB thật.

Diff source..docs chỉ AGENTS/docs/evidence. Diff base..source chỉ run.ps1, seed.sql và test HTTP mới; migration/RPC/model/repository/provider/UI/contract không đổi. Nguồn trước/sau tự chạy trùng hash, cây mã c54b004 trùng tested source ở các file thực thi.

## Phát hiện

| Mức | file:dòng | Phát hiện | Cách sửa |
|---|---|---|---|
| **P2 — H1** | `scripts/bh07_http/seed.sql:170`; assertion `test/integration/bh07_http_auth_test.dart:933` | Fixture free-current có một player confirmed/present/fee_exempt, active revision allocation0, nhưng **không có charge0 cho player đó**. INSERT charges bỏ qua v_rev_free/v_player_free_guest. Check precondition chỉ xem current/allocation/outstanding0, nên empty charge set cũng PASS. Ma trận vì thế chưa chứng minh complete trên snapshot miễn phí đầy đủ như finalize thật tạo ra. | Thêm charge0 đúng player/revision hoặc tạo snapshot qua finalize RPC; assert đúng player, charge_count1, amount_due0, revision/source_version/current trước complete; sau complete/retry giữ nguyên charge. Không sửa gate/RPC A để chấp nhận fixture sai. |
| **P2 — H2** | `test/integration/bh07_http_auth_test.dart:643` và dòng 619 | Privacy history chỉ kiểm key của **dòng đầu**, chỉ chặn contact/phone, bỏ bank/account/receiver và các dòng còn lại. Privacy summary chỉ blacklist key mức đầu, nên `receiver_snapshot: {account_number: ...}` vẫn PASS; cohost chỉ kiểm model đã parse nên field lạ bị bỏ có thể không được phát hiện. Các assertion chưa bảo vệ đầy đủ projection được tuyên bố. | Kiểm raw payload theo whitelist projection A cho mọi history row và raw summary của finance/cohost; kiểm finance fields cohost có mặt và null. Thêm negative control cho bank/account/receiver/nested private fields và dòng sau; nên seed marker contact/bank giả để kiểm không xuất hiện trong response. Giữ nguyên repository thật/HTTP/Auth và contract. |

### H1 — cách tái hiện và ảnh hưởng

Chạy nguyên seed và ma trận không sửa: **65/65 PASS**, trong đó free-current precondition và success đều PASS. [Audit SQL read-only](review_3ad25a4_evidence/fixture-audit.json) trên DB reviewer sau ma trận: free_present_players=1, free_charge_rows=0, revision seeded không đổi. Source seed cho thấy ngay từ trước complete không có row0. Finalize hiện hành dựng tập tất cả confirmed/present, kể cả fee_exempt, rồi INSERT charge0 cho người miễn phí (`20261016110000_bh06_expenses_finalize.sql`, tập present và INSERT tại dòng 468); contract buổi miễn phí vẫn có revision current/charges0.

Đây là thiếu precondition của fixture/test, **không kết luận complete RPC bị hỏng** và không mở lại A. Không được dùng tổng0 từ tập rỗng thay bằng chứng snapshot có khoản0. Người triển khai thêm test đỏ cho số charge đúng player trước khi sửa seed.

### H2 — cách tái hiện và ảnh hưởng

[Probe/assertion counterexamples](review_3ad25a4_evidence/privacy-probe.json), [script](review_3ad25a4_evidence/privacy_probe.py) giữ đúng logic predicate hiện tại:

- Summary có receiver_snapshot chứa account_number: predicate mức đầu vẫn true.
- History dòng đầu có bank_account: predicate chỉ contact/phone vẫn true.
- History dòng thứ hai có phone: predicate chỉ đọc dòng đầu vẫn true.

Đây là **payload giả lập để kiểm assertion**, không phải response bị thay thế trong 65 check, không phải bằng chứng server hiện lộ dữ liệu. Probe đọc raw response thật qua HTTP cho cohost và toàn bộ history hiện đều không có private key; toàn bộ tám trường tài chính của cohost có mặt và null. Vấn đề là suite được bàn giao có thể xanh khi projection sau này vi phạm yêu cầu đã nêu. Viết negative tests cho validator/assertions và kiểm raw HTTP toàn bộ payload, không chỉ model đã loại field.

Không có phát hiện P0/P1. H1/H2 P2 còn mở trong phạm vi fixture/assertion kiểm chứng được giao.

## Reviewer tự chạy

[Summary](review_3ad25a4_evidence/summary.json), [hash source](review_3ad25a4_evidence/source-hashes.json), [môi trường reviewer](review_3ad25a4_evidence/environment-reviewer.json), [scope diff](review_3ad25a4_evidence/scope-source-docs.txt).

| Hạng mục | Kết quả độc lập |
|---|---|
| Ma trận HTTP/Auth nguyên bản, repository/Auth thật | **65/65 PASS**, Flutter test exit0 ([log](review_3ad25a4_evidence/http-test.log), [JSON](review_3ad25a4_evidence/http-summary.json)) |
| Phân nhóm | auth8, ACL9, privacy4, scope4, complete10, finance16, summary3, history10, list1 |
| `flutter analyze` | 0 issue, exit0 ([log](review_3ad25a4_evidence/analyze.log)) |
| `flutter test`, không bật BH07_HTTP_TEST cho toàn suite | **240 PASS +1 SKIP**, exit0 ([log](review_3ad25a4_evidence/flutter.log)); skip chính ma trận opt-in, không gọi đó là HTTP đã chạy trong full suite |
| `BH02_TEST_CONTAINER=bh02-review-bh06 python3 docs/reviews/bh07/run_bh07_tests.py` | **23/23 PASS**, exit0 ([log](review_3ad25a4_evidence/bh07.log), JSON mới cùng thư mục) |
| Probe fixture/privacy | H1 thiếu charge0; ba counterexample H2 được predicate hiện tại chấp nhận; raw server hiện an toàn |

### Khác biệt môi trường và giới hạn tái lập

Máy reviewer Linux không có powershell/pwsh; run.ps1 gọi ComSpec/cmd.exe nên không thể chạy nguyên lệnh Windows. CLI Supabase2.121.0 start đã thử với các dịch vụ cần thiết; sau lỗi registry ECR, chính CLI thử GHCR, tải được GoTrue/PostgREST/Kong nhưng image supabase/postgres17.11.0.004 lỗi đăng ký layer **no space left on device**. Đã dừng retry, không reset/chạm DB ứng dụng đang có. [Log CLI thất bại đã redacted](review_3ad25a4_evidence/supabase-cli-start-failed.log).

Để vẫn kiểm độc lập HTTP, reviewer dựng stack mới: **GoTrue v2.197.0 + PostgREST v16.4 + Kong2.8.1 + stock PostgreSQL17.11**, mạng Docker riêng; chỉ Kong publish loopback127.0.0.1:54321, DB/Auth/REST trên mạng internal. Khác image PostgreSQL Supabase CLI, không phải cùng recipe triển khai Windows. GoTrue tự migrate schema Auth và tạo bảy user qua Admin API; bootstrap auth.uid đọc claims JWT do PostgREST đã xác thực, không SET ROLE/Auth stub. Role/config bootstrap nằm ngoài migration ứng dụng. [Orchestrator Linux](review_3ad25a4_evidence/run_local_stack.py), [bootstrap](review_3ad25a4_evidence/bootstrap-public.sql.txt), [log lượt cuối](review_3ad25a4_evidence/local-stack-final.log). Không publish env files/JWT/password runtime.

Áp nguyên migration và seed vào **DB mới chỉ chứa fixture**, chạy nguyên file Dart không sửa qua HTTP loopback. Không dùng repository mock, không thay RPC hay expectation. Lượt cuối setup từ checkout sạch c54b004: worktree_dirty_before_HTTP_setup=false; source trùng 3ad25a4. Lần bootstrap thử ban đầu đã được khắc phục thứ tự GoTrue migration/helper và network publish trước lượt cuối; không tính các lần lỗi setup thành PASS. Điều này xác minh 65 check trên stack component thật của reviewer, **không** xác nhận nguyên run.ps1/full Supabase CLI recipe đã tái lập thành công trên máy reviewer.

## Đối chiếu các rủi ro được giao

AuthRepository.signInWithEmail, SessionRepository và FinanceRepository dùng SupabaseClient thật; test bỏ HttpOverrides giả của Flutter. Bảy mật khẩu đăng nhập GoTrue/JWT thật; PostgREST kiểm JWT và thực thi RPC theo actor. Service-role trong matrix chỉ SELECT side-effect tables, không dùng để thực thi application mutation hay ACL. Service-role tạo user Auth trong bước setup GoTrue Admin API là tách biệt với actor chạy ma trận. Seed SQL trực tiếp chỉ dựng fixture; H1 nêu precondition chưa đầy đủ.

confirmPayment retry không dựa alreadyConfirmed: cùng payment ID/status, memberPaymentCount=2 (gồm payment seed đã reversed và payment mới), ledger=1, operation_requests=1, outstanding100000; [JSON reviewer](review_3ad25a4_evidence/http-summary.json) kiểm đúng các giá trị này. Cờ alreadyConfirmed=false không phủ định idempotency khi những side effect trên không trùng.

Anonymous complete trả SQLSTATE42501/permission denied for function complete_session: hợp lệ vì anon không có EXECUTE, bị chặn trước thân RPC; không bắt buộc lỗi UNAUTHENTICATED của thân hàm. list_session_players dùng ownerA có management, không dùng treasurer. Cohost chỉ management được đọc count và tiền null; finance đọc aggregate theo server. Các assertion privacy cần tăng cường theo H2, không sửa ACL/RPC.

## Evidence, hash và secret

[Kiểm manifest](review_3ad25a4_evidence/author-hash-check.json): đủ path; mọi entry khớp sau LF normalization, **trừ bản DB JSON đặt ngoài evidence có hash CRLF**; tái dựng CRLF khớp hash và JSON ngữ nghĩa giống bản bh07_db_runner_results.json trong evidence. Đây là một entry dùng quy ước xuống dòng khác, không phải dữ liệu DB khác. Không gọi manifest là hoàn toàn LF nhất quán.

Summary tác giả có đúng65 check/65 PASS theo nhóm; environment/DB JSON đều ghi tested3ad25a4 và dirty=false, đúng metadata được báo. Kiểm count/exit/log/hash nhất quán; không chứng thực độc lập thời điểm hoặc lịch sử worktree máy tác giả. Kết quả reviewer dùng checkout c54b004 với source hash trùng3ad25a4. JSON hồi quy mới sinh trong repo được chuyển sang scratch trước lượt HTTP cuối để setup lại trên checkout sạch.

[Secret scan](review_3ad25a4_evidence/secret-scan.json) không phát hiện JWT ba đoạn, sb_secret/sb_publishable key hoặc PEM private key trong evidence tác giả, gồm start.log. Scan lại evidence reviewer trước publish cũng không có các mẫu đó. Chỉ publish key/token placeholder; local runtime credentials không đưa vào git. Đây là kiểm mẫu và rà các log liên quan, không khẳng định phát hiện được mọi loại secret tùy ý.

## Kết luận

**Chưa đạt** — riêng **gói kiểm chứng HTTP/Auth local** tại tested source3ad25a4, docs/evidence c54b004: H1/H2 P2 cần sửa fixture/assertion dù 65 check hiện xanh. Không có P0/P1 và chưa phát hiện bằng chứng lộ dữ liệu thực tế hoặc lỗi idempotency trong lượt chạy này. Người triển khai viết test đỏ, sửa cả H1/H2 trong gói kiểm chứng; giữ nguyên migration/RPC/model/repository/provider/UI/contract, giữ các check/control cũ. Vòng sửa tiếp là1/2 theo AGENTS; tối đa hai vòng. Không mở lại nghiệm thu A/B/C/D local hoặc suy thành nghiệm thu toàn BH-07.

**NOT RUN:** nguyên lệnh PowerShell run.ps1/full Supabase CLI image recipe trên máy reviewer; concurrency HTTP/PostgREST và timeout sau server commit; browser/device/offline/reopen/deep link; ngân hàng thật/VietQR/webhook; staging/production/apply DB thật/backup/restore; rehearsal/pilot/nghiệm thu toàn BH-07; chạy lại335 hồi quy DB BH-02..06 và BH-06 integration/upgrade. Không merge main hoặc deploy.
