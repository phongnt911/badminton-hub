# Review Concurrency HTTP/Auth BH-07 — vòng sửa 1/2

Ngày 22/10/2026. Nhánh `feat/bh07-http-concurrency`.

- Tested source: **`cbcc46c2e125b156b53f4297ef864cf658855d37`**.
- Docs/evidence: **`b23df5ee77fda4633be6ac8c572db583cbe9a532`**.
- Base thực tế (cha trực tiếp của tested source): **`a0f831af47f98c7649e0c80dce4d5f13004a0db2`**. Full SHA base khác trong yêu cầu/handoff không tồn tại ở checkout; xem H4.
- Checkout docs SHA sạch trước HTTP setup, source test khớp byte với tested SHA ([hash](review_cbcc46c_evidence/source-hashes.json)). Diff base thực tế→source chỉ `test/integration/bh07_http_auth_test.dart`; source→docs chỉ tài liệu/bằng chứng. Không đổi app/migration/RPC/model/repository/provider/UI/contract. [Diff source](review_cbcc46c_evidence/scope-source.txt), [diff docs](review_cbcc46c_evidence/scope-docs.txt), [diff main đối chiếu](review_cbcc46c_evidence/scope-main.txt). Không review lại A/B/C/D.

## Xử lý phát hiện cũ

| Phát hiện | Kết luận | Kiểm chứng độc lập |
|---|---|---|
| H1 P2 — nhận nhầm HTTP lỗi là drop sau commit | **Đóng** | Matrix thật kiểm HTTP200/drained, operation đúng actor/request, payment confirmed + ledger + outstanding trước retry; baseline ID khớp sau retry. Phát lại HTTP400 thật: không còn ClientException/drop, operation trước retry=0; retry mới tạo operation. Control status 201/204/400/401/403/404/409/500 đều được trả nguyên trạng; 200 mới drop. |
| H2 P2 — chấp nhận lỗi competitor không liên quan | **Đóng** | Probe `FORBIDDEN/P0001` cũ bị loại ở cả hai predicate. Positive controls domain/SQLSTATE hợp lệ và negative ACL/NOT_FOUND/INVALID_INPUT/sai SQLSTATE/transport đều đúng. Matrix thật vẫn kiểm đúng loser domain và số dư. |

Bốn probe reviewer PASS, import helper source thật, không chép lại predicate cũ. [Nguồn probe](review_cbcc46c_evidence/reviewer_concurrency_probe_test.dart.txt), [log](review_cbcc46c_evidence/probes.log). Probe H1 thay payload lần đầu để server thật trả400 là control riêng sau matrix; không mock kết quả nghiệp vụ của matrix. Mock status chỉ dùng control helper, không được coi là HTTP/Auth thật.

## Phát hiện còn mở

### H3 — P2: Công bố manifest LF nhưng sáu log là UTF-16 có CRLF

- **File:dòng:** `docs/reviews/bh07/http_concurrency_handoff.md:48`; `docs/reviews/bh07/http_concurrency_evidence/hashes.sha256:2`, `:7`, `:9`, `:10`, `:11`, `:16`.
- **Tái hiện:** đọc BOM, decode đúng UTF-16 rồi đếm `\r\n`; không dùng phép tìm byte ASCII `b'\r\n'` trực tiếp trên UTF-16. [Kết quả từng file](review_cbcc46c_evidence/author-hash-check.json).
- **Thực tế:** `bh07_db_runner.log` có32 CRLF; `flutter_analyze.log`2; `flutter_test_full.log`250; `green_probe.log`7; `red_probe.log`37; `seed.log`1. Tất cả sáu file có BOM UTF-16. Manifest19/19 khớp **raw bytes**, nhưng không chứng minh “CRLF=0”/text LF như handoff công bố. Thay byte ASCII CRLF trên UTF-16 không loại được chuỗi `0d 00 0a 00`.
- **Ảnh hưởng:** bộ bằng chứng không đáp ứng chuẩn LF đã bàn giao; công cụ đọc text/quét secret UTF-8 có thể bỏ lọt nội dung UTF-16. Reviewer đã decode trước khi scan; không phát hiện secret theo các mẫu đã kiểm, không khẳng định có rò secret.
- **Cách sửa:** giữ nguyên nội dung log, decode đúng encoding nguồn, chuẩn hóa kết thúc dòng ở cấp text rồi ghi UTF-8/LF nhất quán và tính lại manifest. Kiểm lại theo decoded text và kiểm encoding, không chỉ thay byte CRLF. Sửa tuyên bố handoff/trạng thái theo kết quả thật; có thể lưu raw gốc riêng kèm hash nếu cần. Không sửa test/backend để xử lý vấn đề này.
- **Trạng thái:** FAIL — P2 còn mở.

### H4 — P2: Metadata base SHA không trỏ tới commit thực tế

- **File:dòng:** `docs/reviews/bh07/http_concurrency_handoff.md:3`, `:75`; `docs/reviews/bh07/http_concurrency_evidence/environment.json:26`; `docs/reviews/bh07/http_concurrency_evidence/summary.json:6`.
- **Tái hiện:** `git cat-file -t a0f831ae3f47e305608bfa0dff19ae035b31f798` thất bại; `git rev-parse cbcc46c^` trả **`a0f831af47f98c7649e0c80dce4d5f13004a0db2`**. Git log và source diff kèm bằng chứng dùng base thực tế.
- **Thực tế:** thông tin base sai từ yêu cầu ban đầu đã được truyền vào `-BaseSha` rồi lưu nguyên trong JSON/handoff. Tiền tố ngắn giống nhau không làm hai full SHA thành một. Đây là metadata sai, không phải bằng chứng source test sai SHA.
- **Ảnh hưởng:** không tái lập được diff/ancestry bằng thông số bàn giao; truy vết evidence không chính xác.
- **Cách sửa:** ghi chú đính chính base thực tế trong handoff và các metadata kết quả, giữ dấu vết giá trị ban đầu thay vì giả vờ lịch sử đã chạy tham số khác; cập nhật command tái lập và tính lại hash. Nếu chạy lại, truyền full SHA thực tế. Không cần thay logic ứng dụng hoặc chạy lại toàn bộ suite chỉ vì sửa metadata.
- **Trạng thái:** FAIL — P2 còn mở.

Không phát hiện P0/P1 khác trong phạm vi được giao. H1/H2 đã đóng; H3/H4 chỉ yêu cầu sửa gói tài liệu/bằng chứng. Reviewer không sửa source triển khai hay evidence tác giả để tự đóng phát hiện.

## Kết quả reviewer tự chạy

| Kiểm tra | Kết quả | Exit | Bằng chứng |
|---|---|---|---|
| `flutter analyze` | 0 issue | 0 | [log](review_cbcc46c_evidence/analyze.log) |
| `flutter test` | 240 PASS +1 SKIP | 0 | [log](review_cbcc46c_evidence/flutter.log) |
| `BH02_TEST_CONTAINER=bh07-http-review-db python docs/reviews/bh07/run_bh07_tests.py` | 23/23 PASS | 0 | [log](review_cbcc46c_evidence/bh07.log), [JSON](review_cbcc46c_evidence/bh07_test_results_20261022123722.json) |
| Source matrix qua stack HTTP/Auth Linux thật | 76/76 PASS | 0 | [log](review_cbcc46c_evidence/http-test.log), [JSON](review_cbcc46c_evidence/http-summary.json) |
| Probe reviewer | 4/4 PASS | 0 | [log](review_cbcc46c_evidence/probes.log) |
| Manifest tác giả | 19/19 raw hash khớp; chuẩn LF FAIL theo H3 | — | [hash check](review_cbcc46c_evidence/author-hash-check.json) |
| Secret scan, decode UTF-16 trước scan | Không thấy JWT3 đoạn, sb_secret/sb_publishable, PEM private key | — | [scan](review_cbcc46c_evidence/secret-scan.json) |

Full suite skip HTTP opt-in; matrix76 đã chạy riêng thật. Giữ đủ76 ID cũ, gồm70 HTTP/Auth nền và6 concurrency ([coverage](review_cbcc46c_evidence/coverage-delta.json)). H1/H2 charge0/privacy của HTTP/Auth nền vẫn nằm trong matrix; không thay bằng mock.

`git diff --check a0f831a..cbcc46c` exit0. Author environment ghi `worktree_dirty_before_run=true`, liệt kê chỉ docs/evidence; DB JSON cũng dirty=true. Reviewer không đổi nhãn thành clean hay coi dirty metadata là source đã thay. Reviewer tự chạy từ checkout sạch trước setup; DB runner sau đó tạo JSON untracked; probe reviewer chỉ được tạo sau full Flutter, rồi chuyển ra khỏi cây test. Tác giả red probe3 FAIL/green5 PASS được decode để đọc nhưng không thay kết quả reviewer; không có source probe tác giả lưu kèm nên chưa tái lập nguyên recipe red đó.

## Môi trường và giới hạn

Reviewer Linux/Docker, Flutter3.47.7; GoTrue **v2.197.0**, PostgREST **v16.4**, Kong2.8.1, stock PostgreSQL **17.11**. Tác giả Windows/PowerShell, Flutter3.47.6, custom Supabase Postgres17.11.0.004. [Environment](review_cbcc46c_evidence/environment-reviewer.json), [recipe local](review_cbcc46c_evidence/run_local_stack.py), [log setup](review_cbcc46c_evidence/local-stack.log).

GoTrue tự migrate auth schema; bảy actor đăng nhập password nhận JWT thật. AuthRepository/SessionRepository/FinanceRepository/SupabaseClient giữ nguyên, PostgREST xác minh JWT; auth.uid bootstrap đọc claims thật. Matrix không SET ROLE/Auth stub; runner DB23 riêng có Auth stub. Network Docker internal, chỉ Kong bind127.0.0.1:54321. Service-role matrix chỉ đọc fixture/counters. Container, volume và runtime secret reviewer đã được dọn; không dùng staging/production.

## NOT RUN

- PowerShell/full Supabase CLI recipe nguyên bản trên reviewer; đã chạy source matrix qua stack Linux tương đương, không coi hai recipe hoàn toàn giống nhau.
- Tái lập nguyên source/recipe red probe tác giả (source probe không nằm trong gói); reviewer đã chạy controls riêng và matrix mới.
- Thiết bị/browser e2e, offline/reopen/deep link.
- Ngân hàng/VietQR thật, đối soát/webhook.
- Staging/production, backup/restore, rehearsal/pilot, nghiệm thu toàn BH-07.
- Chạy lại335 DB hồi quy BH-02..06 và BH-06 integration/upgrade trong lượt này; không đổi backend.

**Kết luận: Chưa đạt — gói kiểm chứng Concurrency HTTP/Auth BH-07 vòng 1/2 tại `cbcc46c`, docs/evidence `b23df5e`.** Đóng H1/H2 P2; sửa H3/H4 P2 về evidence/metadata trong vòng2/2, không đổi logic test đã kiểm. Giữ kết luận HTTP/Auth `f9159dd` và A/B/C/D local; không merge main/deploy/apply DB thật hoặc chuyển pilot.
