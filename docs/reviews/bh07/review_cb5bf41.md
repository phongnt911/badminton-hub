# Review V2b — cb5bf41 — vòng2/2

## Kết luận

**Chưa đạt gói tooling Provider harness vòng2/2. HP3 còn mở với3 P2; đóng HP2/HP6/HP7 trong phạm vi được giao.** Không xác định P0/P1 mới. HP1/HP4/HP5 và giới hạn Provider harness giữ nguyên; **app-profile heap V2b vẫn NOT RUN**, không kết luận app có leak thực tế.

- Ngày:26/10/2026 (Asia/Saigon).
- Base review:`b74860c756b1d56c4f24e5bc0221678c67b57bd6` ([review33ad6e6](review_33ad6e6.md)).
- Tested source:`f7922ed63f7594ace19daa8b999712fd849f0dbe`.
- Docs/evidence:`cb5bf41b8fa68b1d0500ed6671098aa2abe3d3a5` (đúng origin khi fetch).
- Reviewer không sửa source. Full runner chạy ở worktree reviewer riêng, detached sourcef7922ed sạch trước chạy; original checkout/bundle tác giả giữ nguyên. Không sửa app/backend/migration/contract, không nới kỳ vọng probe cũ.

## Rà soát bốn điểm

| Điểm | Kết luận |
|---|---|
| HP2 | **Đóng**:12 self-controls,24 regression tests và replay nguyên probe/extra controls cũ; comment/string/block-comment không tính là dispose, real cancel NONE, brace trong string không cắt thân hàm. Vẫn là lexical heuristic, không phải full Dart parser/retention-path proof. |
| HP3 | **Còn mở**: legacy cases cũ đã sửa, nhưng full runner thật exit1 ở checkout mới và hai protocol/coverage controls còn false-green (bên dưới). Không dùng24/24 tests để thay yêu cầu thực tế. |
| HP6 | **Đóng** trong đường chạy hiện hành: status/rev-parse lỗi trả UNKNOWN/UNKNOWN_SHA, provenance_errors chặn main success/report; positive clean/dirty và error/hash controls chạy trong24 tests, probe cũ status error không còn false-clean. |
| HP7 | **Đóng**:mọi3 SHA40-hex trong handoff resolve bằng Git; base review đúng b74860c, base vòng1 đúng2dac374fd98389b3ec9c54ec11f5781b01d32c77; link commit tuyệt đối. |

## Phát hiện còn mở thuộc HP3

### HP3-A — P2: Full runner đọc sai stream khi Flutter in dependency output trước JSON

- File:dòng:`scripts/bh07_heap/run_heap_verification.py:271`.
- Tái hiện: checkout sạch sourcef7922ed vào worktree mới (chưa có package_config), đặt Flutter SDK trên PATH, chạy nguyên `python scripts/bh07_heap/run_heap_verification.py`. Lượt reviewer đã tự chạy và lưu [full_runner.log](review_cb5bf41_evidence/full_runner.log), [raw JSON/output](review_cb5bf41_evidence/runner_output/heap_test_run.log), [summary](review_cb5bf41_evidence/runner_output/summary.json).
- Kỳ vọng: nhận diện7 test JSON identities khi stream có diagnostic/pub output; verdict/count/Markdown/exit phản ánh7 success. Không phải thay bằng --no-pub để che parser bug.
- Thực tế: Flutter in `Resolving dependencies...`/`Got dependencies!` trước các JSON events. `output.lstrip().startswith('{')` sai nên dùng text parser: **suite FAIL,0 passed,7 missing,identity_coverage NONE,runner exit1**. Raw stream có đủ7 expected testDone success/skipped=false và done.success=true. Cùng stream lọc riêng JSON lines rồi gọi parser thì **PASS7/7 VERIFIED** — positive comparison chỉ thay một biến đầu vào, không sửa source/kỳ vọng.
- Cách sửa: nhận diện/parse các JSON event hợp lệ theo từng dòng trên toàn stream, giữ diagnostics riêng; không quyết định chế độ bằng ký tự đầu output. Có regression prefix diagnostic +7 events, mixed lines và malformed/incomplete protocol; giữ legacy positive đã được yêu cầu, không làm JSON event thiếu thành PASS.

### HP3-B — P2: Bỏ qua cờ skipped thật, test không chạy vẫn PASS

- File:dòng:`scripts/bh07_heap/run_heap_verification.py:188`, `scripts/bh07_heap/run_heap_verification.py:205`; fixture regression `tests/test_bh07_heap_controls.py:55`.
- Tái hiện: `python docs/reviews/bh07/review_cb5bf41_evidence/protocol_probe.py`, case one_real_protocol_skip. Reviewer còn chạy `flutter test --no-pub --reporter json test/integration/bh07_http_auth_test.dart` để ghi [event skip thật](review_cb5bf41_evidence/real_skipped_events.log) — HTTP test bị tắt mặc định, không gọi backend.
- Kỳ vọng: một expected test skipped → owned control NOT_RUN, tests_skipped1, suite không PASS, report không ghi7/7.
- Thực tế: Flutter protocol thực có **`result: "success", skipped: true`**. Parser chỉ lấy result/hidden, bỏ skipped; đổi M1 trong7 real identities sang event skip đúng protocol vẫn trả **PASS7/7,skipped0,VERIFIED**, control M1 PASS và Markdown7/7 PASS. Regression hiện tại tự tạo result='skipped' nên không tái hiện protocol này.
- Cách sửa: normalize skipped boolean từ event trước result mapping/count/coverage, ưu tiên skip metadata đúng protocol; sử dụng raw event fixture thật trong regression. Test success/skipped=false là positive, success/skipped=true là NOT_RUN và không được xanh toàn suite. Không thay kỳ vọng để chấp nhận test không chạy.

### HP3-C — P2: Test identity lạ bổ sung được nhận VERIFIED, counts và Markdown mâu thuẫn

- File:dòng:`scripts/bh07_heap/run_heap_verification.py:213`, `scripts/bh07_heap/run_heap_verification.py:203`, `scripts/bh07_heap/run_heap_verification.py:371`.
- Tái hiện: protocol_probe.py, case unknown_extra_identity: giữ nguyên7 expected real success events, thêm1 visible testStart/testDone success với tên không nằm trong expected set.
- Kỳ vọng: kiểm strict expected identity/coverage; không báo đúng7/7 khi có8 visible results hoặc identity chưa được giải thích. Tên lạ không được dùng để tăng count/success và mọi trường report phải thống nhất.
- Thực tế: **suite PASS,tests_passed8,tests_expected7,identity_coverage VERIFIED,missing[]**, controls toàn PASS, Markdown vẫn claim **7/7 Provider test PASS** (suite_claim còn tính8/7). Chỉ kiểm missing expected names, không xác minh unexpected/duplicate identities và không so exact cardinality. Control unknown-only cũ bị từ chối đúng nhưng không bao phủ trường hợp bổ sung này.
- Cách sửa: canonical expected identity mapping, phân loại loader/hidden events hợp lệ và từ chối/ghi rõ visible unknown/duplicate; exact coverage/counts cùng nguồn để quyết định gate/Markdown/exit. Thêm7+unknown,duplicate và mismatched-count controls; không đổi expected set để làm xanh negative fixture.

## Reviewer tự chạy

Evidence riêng:[review_cb5bf41_evidence/](review_cb5bf41_evidence/).

| Lệnh/kiểm tra | Kết quả mới |
|---|---|
| Full runner nguyên lệnh | **Exit1**, worktree sourcef7922ed sạch lúc capture; AST CLEAN,manifest generated4/4 PASS, nhưng suite FAIL do HP3-A. Bảy expected tests thực sự success trong raw events, không gán full runner PASS. |
| python -m unittest tests.test_bh07_heap_controls -v | **Exit0,24/24 OK** |
| audit_ast_memory.py --test-controls | **Exit0,12/12** |
| clean_and_manifest.py --test-controls | **Exit0,5/5**, expected verify error output của negative fixtures được giữ |
| clean_and_manifest.py --verify (bundle tác giả) | **Exit0,4/4**, fingerprint trước/sau bằng nhau, source hashes4/4 khớp Git blob/sourcef7922ed |
| review_ccad24c_evidence/probes.py | **Exit0**, nguyên file; old patterns được bắt, verifier positive/CRLF/mismatch/missing/extra đúng trên Linux |
| review_33ad6e6_evidence/extra_controls.py | **Exit0**, nguyên file; dispose real NONE/comment/string HIGH; subset FAIL,no-tests NOT_RUN,unknown git state UNKNOWN; legacy full-positive COUNT_ONLY giữ nguyên |
| flutter analyze --no-pub | **Exit0,0 issue** |
| flutter test --no-pub | **Exit0,247 PASS+1 skip** |
| Real skipped protocol capture | **Exit0**, result success +skipped true; không HTTP/Auth call |
| Protocol replay controls | Exit0 của probe; output công bố HP3-A/B/C, không gọi false-green là gate PASS. JSON-only7 real successes positive giữ PASS. |
| Scope/SHA | f7922ed..cb5bf41 runtime tree không đổi; lib/backend/Provider heap suite giữ nguyên từ base;3 handoff SHA resolve, commit URLs tuyệt đối. |

Reviewer Linux Flutter3.47.7, khác tác giả Windows3.47.6. Full runner gọi Flutter thật, qua PATH SDK hiện có; không thay command/assertion bằng wrapper. Package resolution diễn ra bình thường trong worktree mới và là diagnostic cần được parser xử lý. Full regression/analyze chạy --no-pub như yêu cầu, local loopback harness. Full runner artifacts reviewer ở runner_output là lượt mới, **không phải bundle tác giả**; manifest gốc của lượt đó được giữ nguyên bytes dưới tên original_manifest.txt để tránh bộ verify recursive bỏ qua nested hashes.sha256.

Bundle tác giả private_heap_evidence4/4 được audit, không regenerate/normalize hay ghi đè. Thư mục log phụ private_heap_r2_evidence trên Git chỉ có exit_codes.json tại docs tip; không dùng các log phụ chưa có để thay lần chạy reviewer. HP4 vẫn giữ đóng cho bundle chính4/4 theo phạm vi yêu cầu. Reviewer logs đóng gói UTF-8 LF; không có raw heap snapshot.

## NOT RUN

- App-profile heap/snapshots/retained paths, widget/Auth/SupabaseClient graph thật: **NOT RUN** theo phạm vi giữ nguyên, không đổi thành PASS từ Provider harness.
- Real HTTP/JWT/Auth/DB/migration/backup/managed Supabase/PITR/offsite/encryption/retention/concurrent writers trong lượt tooling này.
- Device/browser khác/offline/deep link,banking/webhook,staging/production restore/deploy,load rehearsal/pilot và nghiệm thu toàn BH-07.
- Các log tác giả phụ không được track không thể audit; không tạo log giả để bổ sung.

## Dừng sau vòng2/2

[AGENTS.md:66](../../../AGENTS.md) quy định: **“Sửa theo review: viết test tái hiện lỗi trước, sửa toàn bộ phát hiện P0/P1/P2 được nêu (kể cả P2), tối đa 2 vòng. Còn lỗi sau 2 vòng thì dừng và báo chủ dự án.”**

Đã hoàn tất review; **dừng gói tooling, báo chủ dự án quyết định**, không tự giao vòng3 hoặc sửa source. Ba tình huống HP3 ở trên đã có log/control/cách sửa cụ thể để dùng nếu có ủy quyền riêng sau này. Giữ V1/V5b Đạt local, các cổng khác NOT RUN, toàn BH-07 chưa nghiệm thu; không merge main/staging/production/deploy/pilot/BH-08.

**Kết luận cuối: Chưa đạt gói tooling V2b vòng2/2; HP3 còn3 P2.**
