# Review độc lập — Browser / Offline / Reopen BH-07

Ngày 22/10/2026; nhánh `feat/bh07-browser-verification`.

Base `8f9259e8dabf9b79088f9bb1eb9c9049d660eff5`; tested source/docs `c8a8e7f672fcf9f27bdac22d48fbcdac74446b1b`. Checkout sạch trước kiểm tra. Diff chỉ thêm script kiểm chứng và docs/evidence/trạng thái; `lib/`, `test/`, migrations/RPC, model/repository/provider/UI/contract và pubspec không đổi. [Diff](review_c8a8e7f_evidence/scope-source.txt), [hash source](review_c8a8e7f_evidence/source-hashes.json). Không review lại A/B/C/D hoặc gói HTTP/Auth/concurrency đã Đạt local.

## Phát hiện

### BR1 — P1: Runner không kiểm luồng UI nhưng vẫn ghi PASS trên màn hình khách/trắng

- **File:dòng:** `scripts/bh07_browser/run_browser_verification.js:238`, `:307`, `:339`, `:347`, `:366`, `:418`; `docs/reviews/bh07/browser_handoff.md:16`.
- **Tái hiện/thực tế:** 17 ảnh tác giả **giống hệt nhau theo SHA-256**, đều là một ảnh màn khách “Bạn đang xem dưới dạng khách”, nút Đăng nhập; không phải các màn attendance/finance/summary/history như nhãn. [Audit ảnh tác giả](review_c8a8e7f_evidence/screenshot-audit.json), [ảnh summary tác giả](review_c8a8e7f_evidence/author-summary-screen.png).
- Runner lấy session bằng Node fetch rồi tự ghi localStorage; chỉ kiểm email ở khóa vừa ghi. TC02 đổi hash URL, chụp ảnh, đọc document.title rồi ghi PASS không kiểm đúng route/session/control. Không nhấn start, điểm danh hoặc chốt phí; fixture SQL vốn đã in_progress, attendance present và revision current. TC03 gọi `fetch(complete_session)` từ JavaScript ngoài app với version gán cứng7; không đi qua finance screen/confirmation/provider. “Finance before complete” còn được chụp sau RPC. HTTP retry `res2` không được kiểm `ok` và `idempotentReplay` chỉ là chuỗi detail, không tham gia gate PASS.
- **Reviewer tự tái lập:** Chromium thật + Flutter Web build source nguyên vẹn + GoTrue/PostgREST thật; chỉ đổi path/key/seed/output cho hạ tầng Linux, không đổi assertion. Runner báo **11/11 PASS, exit0** trong khi 17 ảnh lại giống nhau và là **trang trắng chưa render UI**. [Log](review_c8a8e7f_evidence/browser-stdout.log), [summary](review_c8a8e7f_evidence/browser-summary.json), [audit ảnh reviewer](review_c8a8e7f_evidence/reviewer-screenshot-audit.json), [ảnh reviewer](review_c8a8e7f_evidence/reviewer-summary-screen.png). Không quy trang trắng môi trường reviewer thành lỗi app; đây là counterexample chứng minh test không yêu cầu UI sẵn sàng.
- **Kỳ vọng/ảnh hưởng:** app chưa authenticated/render/đúng trang phải FAIL; các request trực tiếp không chứng minh Flutter UI hoạt động. Toàn bộ chuỗi Start→attendance→finalize→complete→history/summary hiện chưa được nghiệm thu browser.
- **Cách sửa:** đăng nhập qua UI thật; chờ và assert semantics/actor/route/session/lifecycle trước mỗi bước; thao tác các nút/confirmation thật, quan sát request của app và state DB. Seed buổi ở trạng thái trước start để thực hiện đủ chuỗi. Gate PASS bằng kết quả và state cụ thể, không bằng ảnh/title/tồn tại storage. Thêm control sai route/guest/app không render phải FAIL; chụp ảnh sau assertion đúng màn. Không dùng direct RPC thay UI; nếu giữ RPC control phải ghi là kiểm API riêng.
- **Trạng thái:** FAIL.

### BR2 — P1: Offline/retry kiểm một fetch đọc độc lập, không kiểm intent/request_id của mutation

- **File:dòng:** `scripts/bh07_browser/run_browser_verification.js:679`, `:697`, `:734`, `:752`; `docs/reviews/bh07/browser_handoff.md:23`.
- **Thực tế:** TC08 ngắt mạng rồi chạy JS fetch `list_my_session_history`, tự catch `Failed to fetch`. TC09 bật mạng rồi fetch cùng RPC đọc bằng payload limit/offset; request offline không có Authorization còn retry có. Cả hai không có request_id, không đi qua handler/error/retry của Flutter. Vì vậy không kiểm được “app không báo thành công giả”, cùng mutation intent/key, submitting hay side effect không trùng. Reviewer vẫn nhận PASS khi UI trắng.
- **Kỳ vọng:** tạo mutation qua UI (ví dụ complete/thu tiền theo quyền), lỗi transport phải hiện đúng trên UI; phục hồi và retry chính intent đó giữ nguyên request_id/payload, chỉ commit một lần.
- **Cách sửa:** điều khiển offline ở transport thật nhưng thao tác qua UI, ghi request body từ network của app trước/sau retry, assert request_id/payload bằng nhau. Kiểm lỗi/success/route trên UI và counters/result DB; request đọc khi online chỉ là control kết nối, không gọi là idempotent retry. Có control mutation thất bại không được báo success.
- **Trạng thái:** FAIL.

### BR3 — P2: Privacy/copy và participant ACL có thể PASS mà chưa kiểm dữ liệu app

- **File:dòng:** `scripts/bh07_browser/run_browser_verification.js:479`, `:484`, `:491`, `:544`, `:598`, `:654`.
- **Thực tế:** copyText được tự dựng trong runner, không nhấn Copy hoặc đọc clipboard của app. Dùng sai field `paid_total_vnd` (RPC trả `total_paid_vnd`) nhưng vẫn PASS vì không assert số đã thu. Cohost chỉ kiểm vài raw field API, không kiểm hiển thị/copy UI. History manager chỉ cần array nonempty; “lọc CLB” chỉ chụp ảnh, payload không có filter. Participant TC07 ghi PASS vô điều kiện sau fetch/json; dữ liệu chứa buổi cấm, trường tiền riêng, hoặc JSON error có length undefined cũng không bị gate từ chối. Không có expected allowlist/denylist.
- **Ảnh hưởng:** test không bắt được lỗi clipboard lộ private data, UI hiển thị tiền sai quyền hoặc history không cô lập; không thể chốt các yêu cầu phân quyền từ11 PASS này.
- **Cách sửa:** kiểm số liệu/null/count trên UI theo từng actor; nhấn Copy và kiểm clipboard thực tế với marker contact/bank/receiver giả có sẵn trong DB. Assert đủ expected totals từ aggregate server (không suy outstanding), và cohost không copy tiền. Kiểm history/filter bằng expected IDs và scope hợp đồng, assert HTTP success/type trước nội dung; negative control buổi/trường cấm hoặc error object phải FAIL. Nếu member không được management history theo contract thì assert chính xác tập rỗng, không PASS bất kỳ payload nào.
- **Trạng thái:** FAIL.

### BR4 — P2: Reopen/logout tự thao tác storage nên không kiểm auth/cache lifecycle của app

- **File:dòng:** `scripts/bh07_browser/run_browser_verification.js:256`, `:780`, `:817`, `:830`.
- **Thực tế:** TC10 chỉ kiểm email của khóa storage mà runner đã tự ghi; UI trắng/guest vẫn PASS. TC11 gọi helper tự xóa `sb-*`, reload trang để mất toàn bộ memory, rồi assert những khóa vừa xóa không còn. Không nhấn logout, không gọi/quan sát luồng signOut của app, không kiểm finance/history cache khi đổi actor trong cùng app đang sống.
- **Ảnh hưởng:** không chứng minh app khôi phục authenticated state sau F5 hoặc xóa cache/token đúng khi logout; reload trước kiểm đã che lỗi cache memory nếu có. Không kết luận có lỗi cache thật ở ứng dụng từ thiếu kiểm chứng này.
- **Cách sửa:** sau login UI, F5/reopen và assert actor + màn dữ liệu được phép thực tế, không chỉ storage. Logout bằng UI, kiểm auth state/token và sensitive widgets đã mất trước reload; login actor khác trong cùng context, kiểm không hiện dữ liệu cũ, kể cả response trễ. Storage seeding/removal nếu cần reset fixture phải tách khỏi thao tác đang được nghiệm thu.
- **Trạng thái:** FAIL.

### BR5 — P2: Thiếu log trong manifest và bằng chứng tái lập/provenance không đủ

- **File:dòng:** `docs/reviews/bh07/browser_evidence/hashes.sha256:2`; `docs/reviews/bh07/browser_evidence/summary.json:7`; `scripts/bh07_browser/run_browser_verification.js:883`; `docs/reviews/bh07/browser_evidence/commands.md:40`.
- **Thực tế:** manifest23 mục chỉ **22 khớp**, `browser_runner.log` không được commit. Node verifier trong đề bài sẽ lỗi ENOENT ở mục này. Raw analyze/full Flutter/DB command logs cũng không có trong gói, dù có tự báo số đếm. Summary gắn tested_checkout_sha=`8f9259e` là commit chưa có ba script browser, không ghi dirty/source hash của script đang chạy; không được sửa lịch sử thành c8a8e7f giả. Exits web_build/db_reset được gán cứng0 trong script, không đo lệnh thực tế. Recipe gọi `node scripts/bh07_db_runner.js`, file không tồn tại; runner đúng là Python dưới docs/reviews/bh07.
- **Ảnh hưởng:** không tái lập được recipe đầy đủ hoặc đối chiếu nguồn browser/script/exit với bằng chứng công bố; không đủ23/23 như yêu cầu. Reviewer tự chạy xanh các suite không thay thế log còn thiếu của snapshot tác giả.
- **Cách sửa:** sau sửa BR1–4, commit test/script trước, chạy từ checkout rõ SHA và ghi dirty/diff/source hashes trung thực; publish đủ log gốc với `git add -f` nếu ignore. Thu exit thật cho từng lệnh, sửa command DB, tính/verify manifest trên checkout sạch. Nếu giữ log cũ thì ghi đúng working-tree provenance, không đổi tested SHA để giả lịch sử; gói mới phải có bằng chứng mới tương ứng. Chuẩn UTF-8 no BOM/LF và scan secret trước commit.
- **Trạng thái:** FAIL.

Không có P0 được xác định. BR1–BR5 là lỗi/thiếu sót của gói kiểm chứng, chưa phải kết luận app có năm lỗi tương ứng.

## Kiểm chứng reviewer tự chạy

| Hạng mục | Kết quả | Exit | Bằng chứng |
|---|---|---|---|
| Flutter analyze | 0 issue | 0 | [log](review_c8a8e7f_evidence/analyze.log) |
| Toàn bộ Flutter test | 240 PASS +1 SKIP | 0 | [log](review_c8a8e7f_evidence/flutter.log) |
| Python DB runner BH-07 | 23/23 PASS | 0 | [log](review_c8a8e7f_evidence/bh07.log), [JSON](review_c8a8e7f_evidence/bh07_test_results_20261022133653.json) |
| Flutter Web build local | Thành công | 0 | [log](review_c8a8e7f_evidence/build-web.log) |
| Browser matrix, assertion tác giả trên Chromium thật | Tự báo11/11, nhưng **không hợp lệ làm bằng chứng UI** theo BR1–4 | 0 | [log](review_c8a8e7f_evidence/browser-stdout.log), [JSON](review_c8a8e7f_evidence/browser-summary.json) |
| Manifest tác giả | 22/23 khớp, thiếu browser_runner.log | FAIL | [audit](review_c8a8e7f_evidence/manifest-check.json) |
| UTF-8 no BOM/LF của text hiện có | PASS | — | [audit text/secret](review_c8a8e7f_evidence/text-secret-audit.json) |
| Secret scan text hiện có | Không thấy privileged key/private key; JWT có mặt là local demo **anon**, không phải service-role/user access token | — | cùng audit trên |

Một skip của full Flutter là matrix HTTP opt-in, không được tính làm browser. Các suite hồi quy không chứng minh các assertion browser đúng.

## Môi trường, adaptation và NOT RUN

Reviewer Linux, Flutter3.47.7, **Chromium154.0.8037.57**, GoTrue v2.197.0/PostgREST v16.4/Kong2.8.1/stock PostgreSQL17.11. Tác giả Windows11, Chrome155, PostgreSQL15 theo handoff. Không dùng môi trường remote.

Dựng stack cô lập như các lượt reviewer trước; CORS cho origin8088, local-only URL127.0.0.1:54321. GoTrue tạo7 user và đăng nhập password thật, JWT thật. Build source app nguyên vẹn với APP_ENV=test; phục vụ loopback8088. Bản runner tạm chỉ đổi Chrome path/flag Linux, project/output path, local anon fixture key và bỏ bước seed Windows để dùng cùng SQL đã seed vào stack reviewer; **không đổi expectation hoặc thay assertion UI bằng assertion khác**. [Recipe chuẩn bị](review_c8a8e7f_evidence/prepare_browser.py), [recipe stack](review_c8a8e7f_evidence/run_local_stack.py), [setup log](review_c8a8e7f_evidence/local-stack.log). Runner gốc không sửa. Matrix dùng API thật; runner DB23 riêng vẫn có Auth stub.

App trên reviewer không render được UI trong lượt này; không chẩn đoán nguyên nhân renderer để quy lỗi sản phẩm. Runner vẫn xanh trên trang trắng là control thất bại của chính bộ test. Ảnh tác giả có render nhưng chỉ là guest screen, đã xem trực tiếp và kiểm17 hash giống nhau. Không được dùng hai lần chạy này để kết luận UI đạt.

NOT RUN / chưa kiểm chứng đạt:
- Luồng **Flutter UI thật** start/attendance/finalize/complete/history/summary, clipboard, role UI, mutation offline retry/request_id, authenticated reopen và app logout/cache như phạm vi yêu cầu — BR1–4.
- Recipe Windows/Chrome155 nguyên bản; mobile/device thật, deep link.
- Ngân hàng/VietQR thật, đối soát/webhook; staging/production, backup/restore, rehearsal/pilot và nghiệm thu toàn BH-07.
- Chạy lại76 HTTP/Auth/concurrency,335 DB BH-02..06 và BH-06 integration/upgrade trong lượt này; source/backend không đổi.

Đã dọn stack/container/volume, server web và runtime key reviewer. Không sửa app, không merge main, apply DB thật hay deploy. Chỉ sửa gói kiểm chứng vòng1/2, viết control đỏ trước sửa và chạy lại đầy đủ; tối đa2 vòng theo AGENTS. Nếu gặp lỗi app thực tế, bàn giao tái hiện riêng trước khi sửa ngoài phạm vi.

**Kết luận: Chưa đạt — gói Browser / Offline / Reopen BH-07 local tại `c8a8e7f`.** BR1/BR2 P1, BR3/BR4/BR5 P2 còn mở. Giữ A/B/C/D, HTTP/Auth/concurrency đã Đạt local; toàn BH-07/pilot chưa nghiệm thu.
