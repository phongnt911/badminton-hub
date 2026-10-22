# Review Browser / Offline / Reopen BH-07 — vòng 1/2

Ngày 22/10/2026; nhánh `feat/bh07-browser-verification`.

- Base: `86c464293f796d5f3b0890acc8bb33a85f7d4897`.
- Tested runner/seed: **`b00b58062b7ccc4b8051165d763bcd016e158e4e`**.
- Docs/evidence thực tế fetch từ origin: **`d01e3692b6b07f145f603565a91ea6f629016ba1`**. Full SHA `d01e369b76c8c1e847a76c88894df051f50f4fa6` trong tin nhắn không resolve; không đồng nhất hai full SHA theo tiền tố. Báo cáo xác nhận source đã chỉ định và HEAD thực tế của nhánh.
- Checkout sạch trước setup. Base→tested source chỉ sửa hai script browser runner/seed. Tested→docs thêm `clean_and_manifest.py` cùng docs/evidence/trạng thái; script audit này không có trong tested source b00b580. `lib/`, `test/`, migrations/RPC, model/repository/provider/UI/contract và pubspec giữ nguyên. [Diff source](review_b00b580_evidence/scope-source.txt), [diff evidence](review_b00b580_evidence/scope-evidence.txt), [hash source](review_b00b580_evidence/source-hashes.json).

## Kết luận xử lý BR1–BR5

Đã xác nhận cải thiện: runner thao tác form/nút UI thật, có guard guest/render,12 ảnh khác nhau, đọc clipboard thật, login/logout và F5 thật; app giữ cùng intent trong lần chạy reviewer. Tuy nhiên **chưa đóng trọn BR1–BR5** vì các gate kiểm chứng còn thiếu. BR1 giảm từ P1 xuống P2; BR2 giữ P1; BR3/BR4/BR5 giữ P2. Không có P0/P1 khác được xác định; các phát hiện dưới đây thuộc gói kiểm chứng, không phải kết luận app có lỗi tương ứng.

### BR1 — P2: Điểm danh vẫn PASS chỉ vì click xong, không kiểm player/state sau mutation

- **File:dòng:** `scripts/bh07_browser/run_browser_verification.js:442`, `:448`, `:449`.
- **Thực tế:** TC03 chọn nút “Có mặt” bất kỳ, đợi rồi chụp ảnh/ghi PASS. Không assert đúng player, attendance mới, count thay đổi hoặc lỗi UI/request. Nếu handler trả về lỗi/no-op thì vẫn PASS. Guard render/login và start/finalize UI đã cải thiện, nên hạ mức lỗi này từ P1 cũ xuống P2.
- **Tái hiện độc lập:** probe chạy nguyên block TC03 trích từ source với control click hoàn tất nhưng không tạo side effect; block vẫn PASS. Đây là mock **negative control** của gate, không dùng thay matrix thật. [Nguồn](review_b00b580_evidence/coverage_probes.js), [kết quả](review_b00b580_evidence/coverage-probes.json).
- **Ảnh hưởng:** chưa phát hiện được hồi quy điểm danh hoặc click sai người. Reviewer quan sát DB thật có1 present trong lần chạy xanh; không đồng nghĩa gate đã bảo vệ tiền đề đó.
- **Cách sửa:** định vị row đúng ID/player, assert precondition chưa điểm danh và postcondition present/count chính xác; kiểm UI error/state và đối chiếu response/DB khi cần. Control request lỗi/no-op/sai player phải FAIL, không chỉ so ảnh.
- **Trạng thái:** FAIL, còn mở P2.

### BR2 — P1: Gate idempotency cố ý không chặn request thiếu/sai và trộn OPTIONS với POST

- **File:dòng:** `scripts/bh07_browser/run_browser_verification.js:518`, `:547`, `:576`, `:579`, `:582`, `:588`.
- **Thực tế:** capture mọi URL complete_session, không lọc method. Chỉ lấy2 entry đầu (có thể chứa preflight); tính reqIdMatch/payloadMatch nhưng luôn ghi PASS, kể cả false hoặc không đủ request. `payloadMatch` chỉ so session_id, bỏ expected_version. Chỉ kiểm không thấy success text, không bắt buộc thấy lỗi transport/giữ route/lifecycle khi offline; sau online không assert completed hay counters side effect.
- **Bằng chứng tác giả:** `browser_evidence/summary.json` TC05 ghi **`captured=4 reqIdMatch=false payloadMatch=false` nhưng PASS**. Không được dùng dòng này để kết luận app đổi request_id.
- **Tái hiện độc lập:**4 control trích nguyên gate source:0 request; khác key/session; cùng key/session nhưng khác version; null postData/preflight. Cả4 **bị nhận nhầm PASS** (probe exit1). [Nguồn](review_b00b580_evidence/predicate_probes.js), [JSON](review_b00b580_evidence/predicate-probes.json).
- **Đối chiếu app thật:** observer riêng lọc POST cho thấy2 POST giữ cùng request_id **và toàn payload**, OPTIONS nằm xen kẽ; DB completed v3, đúng1 operation và1 audit. [POST audit](review_b00b580_evidence/post-retry-audit.json), [trace an toàn](review_b00b580_evidence/network-observer.json), [DB](review_b00b580_evidence/side-effects.json). Do đó lỗi đang xác định là bộ test, **không phải lỗi retry của app**.
- **Cách sửa:** lọc POST có postData đúng RPC, thiếu quan sát phải FAIL; assert key và toàn payload (gồm expected_version) bằng nhau, không chỉ log boolean. Assert lỗi transport/route/lifecycle khi offline, success/completed khi online và exactly-once audit/operation/version. Thêm control bốn ca sai trên phải đỏ, giữ same-intent positive control. Không sửa provider/backend để “làm xanh”.
- **Trạng thái:** FAIL, còn mở P1.

### BR3 — P2: Clipboard đã thật nhưng validator tiền/privacy còn lọt; history/filter chưa assert scope

- **File:dòng:** `scripts/bh07_browser/run_browser_verification.js:642`, `:648`, `:735`, `:774`, `:783`, `:845`.
- **Thực tế:** manager clipboard chỉ cần có nhãn “Tổng chi phí”/“Còn phải thu”, không so totals/null với aggregate. Fixture UI không có expense, green toàn0 nên không kiểm được zero giả/số tiền sai. Cohost chỉ cấm hai nhãn đó; “Đã thu:50000 VNĐ” hoặc phone/STK vẫn lọt gate. TC08 chỉ mở history và chờ title, không chọn CLB hoặc assert IDs/filter/request; ảnh09 vẫn “Tất cả CLB”. TC09 member cũng chỉ chờ title rồi PASS, không kiểm empty/list đúng contract hoặc rows/trường bị cấm.
- **Tái hiện độc lập:**3 controls của gate clipboard hiện tại nhận nhầm PASS: manager số tiền999 bất kỳ; cohost còn “Đã thu”; cohost chứa phone/STK giả. [Probe](review_b00b580_evidence/coverage-probes.json). Không có phát hiện app thật làm rò dữ liệu từ những payload synthetic này.
- **Ảnh hưởng:** bộ kiểm chứng chưa bắt được sai aggregate, lộ field ngoài hai nhãn hoặc history bị nới quyền/lọc sai, dù screenshot hiện tại nhìn đúng.
- **Cách sửa:** dùng fixture có số tiền khác0 và marker private giả có thật ở nguồn; so giá trị/null UI/clipboard với aggregate server/expected text theo contract, không tự suy outstanding. Cohost kiểm toàn bộ finance/private field hoặc whitelist phần count được copy. Thực sự chọn filter CLB/ngày và assert request + tập IDs cho từng actor; member rỗng nếu contract yêu cầu phải assert rỗng và không có rows cấm. Error/loading/title-only và các leak control phải FAIL.
- **Trạng thái:** FAIL, còn mở P2.

### BR4 — P2: Chưa kiểm cache đổi actor trong cùng instance vì Page.navigate reset app

- **File:dòng:** `scripts/bh07_browser/run_browser_verification.js:235`, `:662`, `:712`, `:763`, `:806`, `:835`, `:937`.
- **Thực tế:** login/logout UI, guest trước reload, token mất và F5 khôi phục profile đã được kiểm thật, không còn tự sửa storage. Nhưng `navigateToHome`/`navigateToSession` là **Page.navigate** (tải lại document), được dùng trước logout và trước xem dữ liệu actor kế tiếp; finance/history provider cũ bị reset trước khi cần kiểm invalidation. Gate logout chỉ kiểm guest/token, không kiểm dữ liệu finance/history cũ hoặc response trễ ở cùng instance.
- **Ảnh hưởng:** phần “không rò cache chéo actor” trong BR4 cũ vẫn chưa được chứng minh. Việc token/logout/F5 hiện xanh không chứng minh provider đang sống đã xóa dữ liệu riêng tư.
- **Cách sửa:** tạo một ca giữ nguyên document/instance, load dữ liệu riêng owner, điều hướng bằng Flutter UI/back/tab, logout/login cohost/member mà không Page.navigate/reload trước assertion cache. Assert không còn dữ liệu owner, kể cả một response owner trả trễ; giữ một ca F5 riêng để kiểm persistence. Không yêu cầu sửa app khi chưa tái hiện lỗi app.
- **Trạng thái:** FAIL, còn mở P2; phần form/logout/F5 đã kiểm, phần cache chưa đủ.

### BR5 — P2: Còn thiếu4 log; cleaner tự ghi lại manifest và có thể báo sạch sai

- **File:dòng:** `docs/reviews/bh07/browser_evidence/hashes.sha256:1`, `:3`, `:4`, `:8`; `scripts/bh07_browser/run_browser_verification.js:993`; `scripts/bh07_browser/clean_and_manifest.py:30`, `:56`, `:78`, `:88`.
- **Thực tế checkout:** manifest21 mục chỉ **17/21** tồn tại/khớp, thiếu `analyze.log`, `bh07_db_runner.log`, `browser_runner.log`, `flutter_test.log` (vẫn bị ignore/chưa publish). `clean_and_manifest.py` được đưa làm lệnh verify nhưng thực tế normalize rồi **ghi đè manifest bằng file đang tồn tại** trước khi verify. Chạy trên bản sao thiếu4 log vẫn exit0 và báo17/17, xóa dấu vết thiếu file. [Audit nguyên manifest](review_b00b580_evidence/manifest-check.json), [control cleaner](review_b00b580_evidence/cleaner-behavior.json), [log](review_b00b580_evidence/cleaner-original.log).
- Secret scanner không có pattern Supabase `sb_secret`/JWT và chỉ cảnh báo rồi vẫn thành công khi tìm thấy pattern. Control key **giả, không chức năng** `sb_secret_...` trên bản sao vẫn báo0 secret/exit0. [Log control](review_b00b580_evidence/cleaner-negative-control.log). Reviewer scan file hiện có không thấy privileged secret; JWT trong commands là demo anon public, không coi là secret.
- Exits `web_build`/`db_reset` vẫn gán cứng0; environment/summary có đúng tested SHA nhưng không ghi dirty status/source hashes như bàn giao. Recipe DB đã sửa đúng. Không khẳng định exit tác giả sai thực tế, chỉ xác định script chưa đo hai exit đó.
- **Cách sửa:** publish đủ log gốc (`git add -f` nếu cần), đo exit từ process thực và ghi provenance/dirty/source hashes trước run. Tách generate/normalize khỏi **readonly verify**; verifier phải fail khi thiếu/thừa/hash sai so manifest đã publish, không rewrite trước check. Scan strict UTF-8, bao phủ secret liên quan, phân biệt anon public bằng metadata và fail exit khác0 khi có secret. Thêm controls thiếu log/hash mismatch/secret giả phải FAIL, tính lại manifest và kiểm trên checkout sạch.
- **Trạng thái:** FAIL, còn mở P2.

## Reviewer tự chạy

| Hạng mục | Kết quả | Exit | Bằng chứng |
|---|---|---|---|
| Flutter analyze | 0 issue | 0 | [log](review_b00b580_evidence/analyze.log) |
| Toàn bộ Flutter test | 240 PASS +1 SKIP | 0 | [log](review_b00b580_evidence/flutter.log) |
| Python runner BH-07 | 23/23 PASS | 0 | [log](review_b00b580_evidence/bh07.log), [JSON](review_b00b580_evidence/bh07_test_results_20261022144315.json) |
| Flutter Web build | Thành công | 0 | [log](review_b00b580_evidence/build-web.log) |
| Browser UI matrix giữ nguyên assertion | Tự báo11/11 PASS;12 ảnh khác nhau | 0 | [log](review_b00b580_evidence/browser-stdout.log), [JSON](review_b00b580_evidence/browser-summary.json), [ảnh audit](review_b00b580_evidence/reviewer-screenshot-audit.json) |
| POST retry + side effects reviewer | Cùng key/toàn payload; completed,1 operation/1 audit | — | [audit](review_b00b580_evidence/post-retry-audit.json) |
| Negative controls gate BR1/BR2/BR3 | **8/8 payload/ca sai vẫn bị nhận PASS** | 1 mỗi probe runner | [4 intent probes](review_b00b580_evidence/predicate-probes.json), [4 coverage probes](review_b00b580_evidence/coverage-probes.json) |
| Manifest/LF/text/secret file hiện có |17/21 hash; text hiện có UTF-8/LF; không privileged secret | — | [manifest](review_b00b580_evidence/manifest-check.json), [artifact audit](review_b00b580_evidence/author-artifact-audit.json) |

12 ảnh tác giả lần này cũng khác nhau và đã xem trực tiếp offline/summary/history. Đây là cải thiện thực tế so vòng0; không dùng ảnh để thay assertion còn thiếu. Full Flutter skip matrix HTTP opt-in, không coi là browser. Không dùng log tác giả thay lần chạy reviewer. Source hash runner/seed khớp tested source, không sửa triển khai.

## Môi trường, adaptation, NOT RUN

Reviewer Linux, Flutter3.47.7, Chromium154.0.8037.57, GoTrue v2.197.0/PostgREST v16.4/Kong2.8.1/stock PostgreSQL17.11. Tác giả Windows/Chrome155/PostgreSQL15 theo handoff. Stack isolated, Kong chỉ bind127.0.0.1:54321, server Web chỉ loopback8088. User/password/JWT và repository/app thật; DB23 riêng dùng Auth stub.

Build `--no-web-resources-cdn` để phục vụ renderer local, không thay app source. Adapt runner chỉ path Chrome/project/output, flags sandbox/software-renderer cho Linux và skip seed Windows vì cùng SQL fixture đã nạp local; không đổi selector/expectation. [Setup recipe](review_b00b580_evidence/run_local_stack.py), [build](review_b00b580_evidence/build_web.py), [adaptation](review_b00b580_evidence/prepare_browser.py), [observer không token](review_b00b580_evidence/observe_network.js). Attempt1 vướng cấu hình CORS local reviewer thiếu `x-supabase-api-version`, chưa qua login, fixture còn published; đã dừng, thêm đúng header hạ tầng và chạy lại toàn bộ thành công. Không tính attempt hạ tầng bị dừng là lỗi app. [Attempt1](review_b00b580_evidence/browser-attempt1.log).

Cleaner mutates input nên reviewer chỉ chạy trên **bản sao** evidence; manifest tác giả gốc không bị normalize/ghi đè. Secret control fake không phải credential thật. Đã dọn container/volume/server web/runtime key reviewer.

NOT RUN/chưa được gói chứng minh đầy đủ:
- Cache/response trễ trong cùng app instance sau đổi actor (BR4); negative gate mutation/privacy/history còn lỗi BR1–3.
- Recipe Windows/Chrome155 nguyên bản; thiết bị mobile thật, offline/reopen đa thiết bị/deep link.
- Ngân hàng/VietQR thật, đối soát/webhook; staging/production, backup/restore, rehearsal/pilot và nghiệm thu toàn BH-07.
- Chạy lại76 HTTP/concurrency,335 DB BH-02..06 và BH-06 integration/upgrade trong lượt này; app/backend không đổi.

**Kết luận: Chưa đạt — Browser / Offline / Reopen BH-07 vòng 1/2 tại `b00b580`, docs/evidence thực tế `d01e3692b6b07f145f603565a91ea6f629016ba1`.** Sửa phần còn lại BR1 P2, BR2 P1, BR3/BR4/BR5 P2 ở vòng2/2; tối đa2 vòng theo AGENTS, còn lỗi sau vòng2 thì dừng/báo chủ dự án. Giữ các kết luận A/B/C/D và HTTP/Auth/concurrency Đạt local. Không sửa app/migration/RPC/contract, merge main/apply DB thật/deploy hoặc chuyển pilot.
