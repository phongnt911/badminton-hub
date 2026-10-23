# Review Browser / Offline / Reopen BH-07 — vòng 2/2

Ngày 23/10/2026. Nhánh `feat/bh07-browser-verification`.

- Base: `465b46607c8fd5d1566e7eca8688af09fc557e34`.
- Tested source: **`51cb3b124533ecc4abce00609a5f0bbbd6309221`**.
- Docs/evidence: **`eadb5c71b5f8194e15188e977dbf85a954761e75`**.
- Checkout sạch trước setup. Diff base→source chỉ bốn script kiểm chứng/fixture; tested source→HEAD chỉ docs/evidence/trạng thái. Không đổi lib/, unit test, migration/RPC, model/repository/provider/UI/contract, pubspec. [Diff source](review_eadb5c7_evidence/scope-source.txt), [diff docs](review_eadb5c7_evidence/scope-docs.txt), [hash source](review_eadb5c7_evidence/source-hashes.json).

## Trạng thái BR1–BR5

| Mục cũ | Kết luận vòng2/2 |
|---|---|
| BR1 P2 — điểm danh | **Đóng trong phạm vi kiểm chứng:** pre/post DB đúng player; no-op control bị loại; UI thật và DB reviewer xác nhận present, checked_in_at có giá trị. |
| BR2 P1 — retry | **Đóng lỗi P1** về POST/payload/thiếu request/exactly-once; còn **BR2 P2** về gate lỗi UI offline dưới đây. |
| BR3 P2 — clipboard/history | **Còn mở P2**: thêm expense200k và thao tác filter thật, nhưng gate vẫn lọt aggregate/null/field cấm/row không được phép. |
| BR4 P2 — actor cùng instance | **Đóng ca chuyển Owner→Cohost cùng SPA được giao:** Back/tab UI, không reload trước assertion, mất thẻ tài chính và clipboard chỉ count; F5 được tách riêng. Response owner trả trễ chưa được thử, giữ NOT RUN, không coi comment “late response test” là bằng chứng. |
| BR5 P2 — evidence/controls/verifier | **Còn mở P2**: đủ21 file, readonly thiếu/hash/sb_secret control đúng; nhưng scanner/encoding, negative runner và metadata/exits vẫn có lỗi dưới đây. |

Các kết luận trên dựa trên lần chạy độc lập, không chỉ đọc summary tác giả. Không phát hiện P0/P1 còn mở trong phạm vi sửa; có ba nhóm P2 còn lại.

## Phát hiện còn mở

### BR2 — P2: Không bắt buộc UI hiển thị lỗi offline nên lỗi bị nuốt vẫn có thể PASS

- **File:dòng:** `scripts/bh07_browser/run_browser_verification.js:587`, `:594`, `:683`.
- **Thực tế:** gate chỉ kiểm không có chuỗi success và DB còn in_progress. Không assert thông báo lỗi transport xuất hiện/route vẫn đúng. Nếu app im lặng bỏ lỗi nhưng retry sau đó thành công thì TC05 vẫn PASS.
- **Tái hiện:** reviewer chạy nguyên TC05 với negative control semantics trả tập rỗng ở bước offline (không có cả lỗi lẫn success), hai POST cùng intent và DB counters hợp lệ. Kết quả **PASS**, trong khi tiêu chí “bắt lỗi trên UI” yêu cầu FAIL. [Probe nguồn](review_eadb5c7_evidence/offline_error_probe.js), [JSON](review_eadb5c7_evidence/offline-error-control.json).
- **Ảnh hưởng:** hồi quy nuốt lỗi/không hướng dẫn retry trên UI không bị bộ test phát hiện. Không khẳng định app thật hiện có lỗi này: screenshot/lần chạy thật reviewer có lỗi và retry đúng.
- **Cách sửa đề nghị chủ dự án xem xét:** assert dấu lỗi UI ổn định cùng route/lifecycle khi offline, loại rõ control không-error/no-success; giữ POST và DB guards đã sửa. Không cần đổi app/provider để sửa gate test.
- **Trạng thái:** FAIL — P2 còn mở, đã giảm từ P1 cũ do phần idempotency chính được khắc phục.

### BR3 — P2: “Có200k ở đâu đó” chưa kiểm aggregate; cohost/member còn lọt dữ liệu cấm

- **File:dòng:** `scripts/bh07_browser/run_browser_verification.js:735`, `:738`, `:850`, `:1007`, `:1010`.
- **Thực tế:** manager chỉ tìm một substring200k bất kỳ, không gắn từng giá trị vào field tương ứng. Cohost không loại đủ field tài chính nếu không có số tiền/nhãn nằm trong regex. Member chỉ cấm chữ “Ba Ngòi”, “Quỹ CLB”, “Số dư”, không assert tập IDs/empty theo contract; seeded club B có tên/title HTTP Club B/HTTP club B history, không phải Ba Ngòi.
- **Tái hiện:** bốn control lấy trực tiếp gate source đều bị nhận nhầm **PASS**:
  1. Tổng chi phí200k nhưng tổng phải thu/đã thu/outstanding999.
  2. Tên buổi chứa200000 nhưng tiền là “—”.
  3. Clipboard cohost vẫn có field “Tổng phải thu: —”.
  4. Member được đưa row HTTP club B history/HTTP Club B cùng “Còn phải thu:200k”.
  [Nguồn](review_eadb5c7_evidence/independent_controls.js), [JSON](review_eadb5c7_evidence/independent-controls.json). Đây là synthetic negative controls, không phải rò dữ liệu được quan sát ở API/app thật.
- **Ảnh hưởng:** mục tiêu chặn số tiền sai/null giả và lịch sử ngoài scope của BR3 chưa được nghiệm thu dù clipboard thật và happy path đúng.
- **Cách sửa đề nghị:** so từng field UI/clipboard với aggregate/expected contract của fixture (expense200k, due200k, paid0, outstanding200k), không suy outstanding client. Cohost chỉ cho phần count được phép, loại mọi finance field kể cả “—”. Assert tập IDs/empty/denylist và error state của history theo actor, không dùng vài chữ ví dụ làm ACL gate. Giữ thao tác dropdown đã sửa.
- **Trạng thái:** FAIL — P2 còn mở.

### BR5 — P2: Negative runner báo GREEN mà bỏ ca; verifier chưa chặn JWT/UTF-8 lỗi; provenance vẫn gán cứng

- **File:dòng:** `scripts/bh07_browser/run_negative_controls.js:60`, `:76`, `:89`; `scripts/bh07_browser/clean_and_manifest.py:39`, `:46`, `:50`; `scripts/bh07_browser/run_browser_verification.js:1140`, `:1163`.
- **Negative runner:** marker TC03 không còn khớp source mới; block rỗng/async không được await/ghi kết quả, lỗi bị nuốt. Output thực tế chỉ4 predicate +3 coverage, **không phải8 ca đã chạy**. Manager control chỉ tìm regex của gate cũ; không thấy regex thì tự kết luận FAIL mong đợi mà không thực thi predicate mới. Reviewer thay gate manager thành `if(true)` trên **bản sao dùng một lần**, script vẫn exit0/GREEN. [Mutant control](review_eadb5c7_evidence/mutant-negative-control.json), [log](review_eadb5c7_evidence/mutant-negative-controls.log). Không sửa script thật hoặc app để tạo control này.
- **Verifier:** thiếu file/hash sai/sb_secret giả đều bị loại và manifest không đổi, đã xác nhận. Nhưng JWT giả có payload base64 claim `service_role` không chứa chuỗi role plaintext bị bỏ lọt; scanner tìm role trong text/token mã hóa thay vì parse claim hoặc reject JWT ngoài allowlist. Văn bản UTF-8 không hợp lệ cũng bị nhận vì `errors='replace'`. Reviewer tạo hai control **không chức năng** trên bản sao, cập nhật hash hợp lệ để tách khỏi hash mismatch: cả hai `--verify` exit0. [Các control readonly](review_eadb5c7_evidence/verifier-controls.json), [JWT control log](review_eadb5c7_evidence/fake_service_role_JWT-verify.log), [UTF8 control log](review_eadb5c7_evidence/invalid_UTF8-verify.log). Không có credential thật trong control và không phát hiện privileged secret thực trong snapshot tác giả.
- **Provenance/exits:** `is_dirty:false`, `web_build:0`, `db_reset:0` còn gán cứng trong runner; source hashes đã thêm và khớp thật, nhưng không biến cờ/exit gán cứng thành phép đo. Không kết luận tác giả đã chạy thất bại; chỉ xác định runner chưa thể báo trung thực nếu những điều kiện đó thay đổi.
- **Ảnh hưởng:** “8/8”, “0 secret”, “100%UTF-8”, dirty/exits có thể xanh khi control thực tế sai. Đây là phần BR5 còn lại, không phải yêu cầu mở rộng tính năng app.
- **Cách sửa đề nghị:** await và assert đủ số ca, marker thiếu/lỗi harness phải fail; chạy predicate hiện hành và thêm positive control, không tự coi không match source là test thành công. Decode UTF-8 strict; nhận diện JWT bằng cấu trúc/claim hoặc reject token ngoài allowlist public rõ ràng, không dò substring chữ role trong base64. Đo dirty trước run và exit từ lệnh thực; nếu không chạy bước đó thì ghi NOT RUN/nguồn kết quả, không đặt0.
- **Trạng thái:** FAIL — P2 còn mở.

## Kết quả reviewer tự chạy

| Hạng mục | Kết quả | Exit | Bằng chứng |
|---|---|---|---|
| `clean_and_manifest.py --verify` trên checkout gốc |21/21 hash, đủ4 log, readonly |0 |[log](review_eadb5c7_evidence/verifier.log), [audit](review_eadb5c7_evidence/artifact-audit.json) |
| `run_negative_controls.js` gốc |Tự báo GREEN; lỗi harness theo BR5 |0 |[log](review_eadb5c7_evidence/author-negative-controls.log) |
| Flutter analyze |0 issue |0 |[log](review_eadb5c7_evidence/analyze.log) |
| Toàn bộ Flutter test |240 PASS +1 SKIP |0 |[log](review_eadb5c7_evidence/flutter.log) |
| Python runner BH-07 |23/23 PASS |0 |[log](review_eadb5c7_evidence/bh07.log), [JSON](review_eadb5c7_evidence/bh07_test_results_20261023005255.json) |
| Flutter Web build local |Thành công |0 |[log](review_eadb5c7_evidence/build-web.log) |
| Browser matrix UI thật, nguyên assertion |11/11 PASS |0 |[log](review_eadb5c7_evidence/browser-stdout.log), [JSON](review_eadb5c7_evidence/browser-summary.json) |
| POST/DB đọc độc lập |Cùng toàn payload; completed v3;1 operation/1 audit; Member A present và checked_in; expense200k |— |[trace](review_eadb5c7_evidence/network-observer.json), [audit](review_eadb5c7_evidence/post-retry-audit.json) |
| Reviewer control hiện hành |13 ca:9 đúng kỳ vọng,4 nhận nhầm PASS theo BR3; thêm silent-error control nhận nhầm PASS theo BR2 |1 |[controls](review_eadb5c7_evidence/independent-controls.json), [offline control](review_eadb5c7_evidence/offline-error-control.json) |
| Verifier fault controls |Baseline PASS; missing/hash/sb_secret FAIL; JWT/UTF8 bị nhận nhầm PASS; **tất cả giữ nguyên manifest/files** |— |[JSON](review_eadb5c7_evidence/verifier-controls.json) |

Reviewer độc lập tái lập đủ8 **control cũ** bằng harness có await/positive baseline: cả8 lỗi ban đầu đã bị chặn;4 trường hợp BR3 còn lọt nêu trên vẫn vi phạm mục tiêu sửa field/scope. Không dùng việc8 payload cũ đã xanh để coi toàn bộ validator đã đúng. Scan text hiện có/đối chiếu hash độc lập không phát hiện privileged secret thực; demo anon trong commands là public local fixture.

## Môi trường và phạm vi chưa kiểm

Reviewer Linux, Flutter3.47.7, Chromium154.0.8037.57; GoTrue v2.197.0/PostgREST v16.4/Kong2.8.1/stock PostgreSQL17.11. Tác giả Windows/Chrome155/PostgreSQL15 theo handoff. Stack và SQL fixture cùng nội dung, URL chỉ loopback54321/8088. Build dùng renderer asset local `--no-web-resources-cdn`, không đổi app. Auth UI/password/JWT và RPC thật; runner DB23 riêng dùng Auth stub.

Adaptation chỉ cấu hình Chrome/project/output path, Linux flags, container name, đường đọc source-hash và bỏ seed Windows vì cùng SQL đã nạp vào stack reviewer; **không đổi selector/expectation**. [Recipe stack](review_eadb5c7_evidence/run_local_stack.py), [build](review_eadb5c7_evidence/build_web.py), [adapter](review_eadb5c7_evidence/prepare_browser.py). Observer chỉ lưu method/payload không token và dấu UI/timeOrigin. TC07 đi Back/tab cùng document theo source và log; TC10 reload riêng. [Observer](review_eadb5c7_evidence/document-observer.json). Không tuyên bố observer đã thấy mọi thời điểm owner finance đầu tiên; lần sampling bắt đầu sau đó, kết luận SPA còn dựa chuỗi thao tác source/log.

Verifier fault/mutant/predicate probes chạy trên bản sao hoặc mocked **negative control**; không thay green browser bằng mock. Snapshot tác giả/manifest gốc không bị normalize/ghi đè. Đã dọn container/volume/server/runtime secret của reviewer.

NOT RUN:
- Recipe Windows/Chrome155 nguyên bản trên reviewer; thiết bị mobile thật, deep link.
- Response owner trả trễ sau đổi actor; comment đầu runner có nhắc nhưng không có control đó. Chỉ đóng BR4 happy path SPA, không coi là chứng minh mọi race/cache.
- Ngân hàng/VietQR thật/webhook, staging/production, backup/restore, rehearsal/pilot, nghiệm thu toàn BH-07.
- Chạy lại76 HTTP/Auth/concurrency,335 DB BH-02..06 và BH-06 integration/upgrade trong lượt này; app/backend không đổi.

## Kết luận và giới hạn hai vòng

**Chưa đạt — gói Browser / Offline / Reopen BH-07 vòng 2/2 tại `51cb3b1`, docs/evidence `eadb5c7`.** Đóng BR1 và ca SPA BR4; BR2 giảm xuống P2; BR3/BR5 P2 còn mở. Không có P0/P1 mở; không có kết luận lỗi nghiệp vụ ứng dụng từ các lỗi gate này.

Theo **AGENTS.md, mục Quy trình hai AI**: “**Sửa theo review: viết test tái hiện lỗi trước, sửa toàn bộ phát hiện P0/P1/P2 được nêu (kể cả P2), tối đa 2 vòng. Còn lỗi sau 2 vòng thì dừng và báo chủ dự án.**” Vì đã hết2 vòng, **dừng gói ở trạng thái Chưa đạt/chờ quyết định chủ dự án**, không tự mở vòng3 hoặc giao sửa tiếp. Các cách sửa phía trên là đề nghị để chủ dự án quyết định phạm vi, không phải ủy quyền triển khai. Giữ A/B/C/D và HTTP/Auth/concurrency Đạt local trước; không merge main, apply DB thật, deploy hoặc chuyển pilot.
