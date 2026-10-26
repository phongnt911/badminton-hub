**Hiện hành 26/10/2026 — V2b Provider tooling Chờ review độc lập sau sửa HP3-C**, tested source `996c4266e6a38324dfc7e3a4b19ee50be101087b`, base review `01bfd160820eb7cda7198da4e0c1bb5d6810b795` (review b7eb881), theo [bàn giao](private_heap_handoff.md). Đã sửa 1 P2 HP3-C: `_parse_json_events` giữ **từng record theo testID** (không khóa theo full name) nên hai test ID cùng tên đầy đủ không bị gộp; validator báo `tests_duplicate` kèm testID, chặn `VERIFIED` → `UNVERIFIED`/`FAIL`, counts vẫn canonical 7, Markdown/JSON/exit dùng chung verdict. 33/33 regression tests (thêm exact-name/different-ID, RED trước sửa); full runner exit0 PASS 7/7 `identity_coverage VERIFIED`, `git_dirty false`, manifest 4/4 strict UTF-8 LF; AST 12/12, verifier 5/5; probe reviewer `duplicate_probe.py` exact-name duplicate nay FAIL/UNVERIFIED exit1 (trước PASS/exit0), `protocol_probe.py` giữ kỳ vọng; analyze 0 issue, 247 Flutter +1 skip. HP3-A/HP3-B và HP1/HP2/HP4/HP5/HP6/HP7 giữ nguyên; app-profile heap **NOT RUN**. **Người triển khai không tự ghi Đạt.** V1/V5b giữ Đạt local; các cổng khác giữ NOT RUN; toàn BH-07 chưa nghiệm thu; không merge main/staging/production/deploy/pilot/BH-08.

**(Lịch sử bàn giao trước review b7eb881) V2b Provider tooling Chờ review độc lập sau sửa HP3 theo ủy quyền ngoại lệ**, tested source `16e5b5116738ab9d4417fe11b651aea794868401`, base review `30feeb981b36473711d5ed4120ba7e14082f95c7` (review cb5bf41), theo [bàn giao](private_heap_handoff.md). Đã sửa 3 P2 HP3-A/B/C: parser đọc JSON event trên toàn stream nên diagnostics/pub output trước JSON không còn hạ verdict xuống text parser; tôn trọng cờ `skipped` thật (success+skipped=true ⇒ NOT_RUN); map strict 7 expected identity nên tên lạ/trùng bị liệt kê và chặn VERIFIED, counts không vượt 7, Markdown/JSON/exit dùng chung verdict. 32/32 regression tests; full runner exit0 suite PASS 7/7 `identity_coverage VERIFIED`, manifest 4/4 strict UTF-8 LF; AST 12/12, verifier 5/5; probe reviewer `protocol_probe.py` exit0 với cả 3 ca đúng kỳ vọng; analyze 0 issue, 247 Flutter +1 skip. HP1/HP2/HP4/HP5/HP6/HP7 giữ nguyên; app-profile heap **NOT RUN**. **Người triển khai không tự ghi Đạt.** V1/V5b giữ Đạt local; các cổng khác giữ NOT RUN; toàn BH-07 chưa nghiệm thu; không merge main/staging/production/deploy/pilot/BH-08.

**(Lịch sử trước chốt vòng2/2) V2b Provider harness Chưa đạt vòng sửa1/2 tại `33ad6e6`**, docs origin thực tế `f40d7798edb4b726dc3dcd7ded2c0e44cbebf79d`, theo [review](review_33ad6e6.md). Đóng HP1 về phân định phạm vi,HP4/HP5; còn HP2/HP3 vàHP6/HP7 mới (4 P2): comment/string dispose,summary subset/no-tests,Git provenance khi git status lỗi vàbase docs sai. Base thực tế `2dac374fd98389b3ec9c54ec11f5781b01d32c77`. Reviewer7/7 heap,analyze0,247 Flutter+1skip,self-controls AST5/verifier5,manifest4/4 readonly PASS; probe cũ nguyên kỳ vọng đã qua,extra controls còn false-green. App-profile heap V2b giữ NOT RUN; không xác định leak thật. Giao sửa tooling/docs vòng2/2,không sửa app/backend. V1/V5b giữ Đạt local; toàn BH-07 chưa nghiệm thu; không merge main/staging/production/deploy/pilot/BH-08.

**(Lịch sử trước review33ad6e6) V2b Chưa đạt tại `ccad24c`**, docs origin thực tế `eb4362bcec70e0922204b6a1040b02cbdb0f0924`, theo [review](review_ccad24c.md). Còn HP1 P1 về phạm vi Provider/mock harness chưa đo heap app profile thật; HP2–HP5 P2 về audit regex bỏ sót, summary hardcode PASS, thiếu heap_test_run.log và verifier bỏ lọt manifest CRLF. Reviewer tự chạy7/7 heap tests,analyze0 issue,247 Flutter+1skip; audit38 file và các fault controls. Bundle tác giả3/4 file,verify exit1; evidence cũ giữ nguyên. Phần app-heap V2b vẫn NOT RUN, chưa xác định leak thật trong app. V1/V5b giữ Đạt local; các cổng khác giữ NOT RUN,toàn BH-07 chưa nghiệm thu. Chỉ giao sửa gói kiểm chứng theo review, không sửa app/backend, không merge main/staging/production/deploy/pilot/BH-08.

**Hiện hành 25/10/2026 — V5b Full Supabase CLI reset Đạt local, đã đóng công việc local**, tested source `8c107e9692b89f4a0aadeafc0ae139736f9b2622`, QA/docs `b036e9e65c3065e90454a6e645960599e633757b`, base thực tế `a55c2d2416f37a0bb8ac985e80bdee579b40774b`, theo [review chốt](review_b036e9e.md). Đóng H6, giữ H1–H5/R1/R2/R3/R5/P2-1..P2-7; không còn P0/P1/P2 mở trong phạm vi. Reviewer tự chạy21/21 Python, analyze0 issue,240 Flutter+1skip,17/17 strict readonly; audit bundle QA2 reset×18 migrations,23 assertion/chu kỳ,HTTP/Auth,Oracle48 bảng schema+số dòng vàcleanup PASS. Full CLI reviewer rerun NOT RUN do thiếu đĩa; kết quả runtime là QA được audit, không đổi thành lần chạy reviewer. Codex từng sửa baseline, giới hạn độc lập được công bố. V1 giữ Đạt local; các cổng V2/V2b/V3/V4/V5/V6/V7/V8 giữ NOT RUN; toàn BH-07 chưa nghiệm thu. Giữ nhánh chưa merge, không merge main/staging/production/deploy/pilot/BH-08.

**(Lịch sử bàn giao trước chốt V5b) Chờ review độc lập sau đính chính H6 và QA runtime**, base review thực tế `a55c2d2416f37a0bb8ac985e80bdee579b40774b` (review [cad3fa0](review_cad3fa0.md)), tested source `8c107e9692b89f4a0aadeafc0ae139736f9b2622`, nhánh `feat/bh07-full-reset-verification`, theo [bàn giao V5b](full_reset_handoff.md) và bundle bằng chứng mới riêng [`full_reset_8c107e9_evidence/`](full_reset_8c107e9_evidence/). Đính chính H6 docs-only: base review thực tế là `a55c2d2416f37a0bb8ac985e80bdee579b40774b` (khắc phục lỗi typo SHA không tồn tại trong handoff cũ), giữ nguyên code H1–H5 đã đóng. QA trên máy đủ đĩa (83GB+) đã chạy full runner trên source sạch `8c107e9` (git_dirty=false), 2 chu kỳ reset 18 migrations từ zero, 23 assertions exact fixture/chu kỳ, Oracle 48 bảng match 100%, HTTP Auth/ACL và negative controls PASS, cleanup 0 container. 21/21 Python tests PASS, analyze 0 issue, 240 Flutter +1 skip; manifest 17/17 strict UTF-8 LF verify exit 0. **Người triển khai/QA không tự ghi Đạt.** Giữ V1 Đạt local; các cổng khác giữ NOT RUN; toàn BH-07 chưa nghiệm thu. Không merge main/staging/production/deploy/pilot/BH-08.

**(Lịch sử trước review 8c107e9) V5b chưa đủ điều kiện chốt tại `8c107e9`**, docs tip `8d48cdc`, theo [review](review_8c107e9.md). Đóng H1–H5 trong phạm vi code/tests/Linux; 21/21 Python, analyze 0 issue, 240 Flutter +1 skip, manifest17/17 strict readonly PASS. Còn H6 P2 docs ghi base SHA không tồn tại; base thực tế `a55c2d2416f37a0bb8ac985e80bdee579b40774b`. Full CLI reviewer với base đúng NOT RUN do chỉ còn khoảng654MB đĩa; runtime tác giả đã audit, không gộp thành lần chạy reviewer. Codex công bố lịch sử từng sửa baseline. Chỉ cần đính chính docs và QA full runtime trên máy đủ đĩa, không viết lại H1–H5. V1 giữ Đạt local; toàn BH-07 chưa nghiệm thu; không merge main/staging/production/deploy/pilot/BH-08.

# Hồ sơ readiness BH-07 — ma trận cổng và kế hoạch kiểm chứng

**Trạng thái: Đạt docs-only vòng2/2 tại31fced4 theo [review chốt](review_31fced4.md); đóng R1–R4. Tài liệu chỉ đọc/ghi docs, không phải nghiệm thu toàn BH-07, không cấp phép merge main, deploy, staging, production hoặc pilot.**

- Base gốc của gói: `b91a350e619529d389af3edf6d4a06408af8d200`; base review vòng sửa R1–R4: `fdf7113ff46517a4c148fbcfcce5fea960686481`.
- Nhánh: `feat/bh07-readiness`.
- Phạm vi: tổng hợp cổng BH-07 đã có bằng chứng, tách rõ **Đạt local** với **NOT RUN**, sửa đủ R1–R4 theo [review bc63673](review_bc63673.md), và lập kế hoạch kiểm chứng phần còn thiếu.
- Không thay đổi app, backend, migration/RPC, contract, script kiểm chứng hoặc bằng chứng cũ trong gói này.
- Quy ước: **Đạt local** chỉ có giá trị trong phạm vi và môi trường được ghi ở từng review; không suy ra nghiệm thu toàn BH-07, không thay thế staging/production/pilot.
- Nguyên tắc phân định quyền hạn: **Reviewer độc lập chốt kết luận kỹ thuật (Đạt / Chưa đạt)** trong phạm vi review dựa trên bằng chứng kiểm chứng độc lập theo `docs/ai/REVIEWER.md`, không hỏi chủ dự án xác nhận kết luận kỹ thuật. **Chủ dự án quyết định phạm vi (scope), chấp nhận rủi ro còn lại (residual-risk acceptance bằng văn bản)** cho các cổng vận hành/môi trường chưa chạy, và phê duyệt các thao tác/cửa sổ trên môi trường riêng (staging/production/pilot). Phê duyệt chấp nhận rủi ro của chủ dự án không đổi NOT RUN thành PASS và không thay thế kết luận kỹ thuật.

## 1. Kết luận điều hành

1. Các phần triển khai BH-07 A, B, C, D đã có kết luận **Đạt local** theo review độc lập, với source/tested SHA riêng.
2. Hai gói kiểm chứng HTTP/Auth và Concurrency HTTP/Auth đã **Đạt local** theo review độc lập; không thay thế kiểm thử tải, staging hoặc production.
3. Browser/Offline/Reopen và hai ca response Owner trả trễ trước đây đóng theo Codex tự review/tự sửa **không độc lập**; lịch sử đó giữ nguyên. Ngày24/10/2026, V1 có [review độc lập mới](review_6283dbb.md) do reviewer khác chạy, đã [chốt Đạt local](v1_acceptance_448c50f.md). Codex điều phối không tự nhận là reviewer UI độc lập của lượt này.
4. Backup/restore cleanup R1 đã **Đạt local vòng 2/2**; review chốt có giới hạn độc lập với lịch sử tác giả. Đây là rehearsal local, không phải backup managed Supabase, PITR, offsite, encryption/retention hoặc restore staging/production.
5. **Toàn BH-07 chưa nghiệm thu.** Các cổng còn NOT RUN được liệt kê ở mục 3; kế hoạch kiểm chứng ở mục 4 chỉ là kế hoạch, không phải bằng chứng đã chạy.
6. Quyền chốt kỹ thuật thuộc về reviewer độc lập; chủ dự án nắm quyền quyết định phạm vi, phê duyệt thao tác môi trường và chấp nhận rủi ro còn lại bằng văn bản. Việc chấp nhận rủi ro không biến một cổng NOT RUN thành PASS và không cấp phép deploy.
7. Không có cơ sở để chuyển BH-08/BH-09, merge main, deploy hoặc mở pilot từ hồ sơ này. Git ref của các nhánh BH-07 được giữ nguyên.

## 2. Ma trận cổng BH-07

| Cổng | Phạm vi đã kiểm | Source/evidence chính | Kết luận và giới hạn |
|---|---|---|---|
| **A — DB/RPC/projection** | Complete/history/summary, gate quyền, công nợ sau complete, projection/ACL, idempotency/audit, dữ liệu nâng cấp | Tested `4512c3a19e7c22f2adc4a9f3269cbabe8acd9d09`; code/runner/migration `c339a47fdcb08e50811079bd89df7a1f9f53908a`; [review](review_4512c3a.md), [evidence](review_4512c3a_evidence/), [audit](bh07a_audit.md) | **Đạt local**, không P0/P1/P2 trong phạm vi. Reviewer tự chạy analyze sạch, 190 Flutter, 335/335 DB hồi quy, 23/23 BH-07, 7 tích hợp, 3 nâng cấp, 9 probe. **Giới hạn:** PostgreSQL cô lập/Auth stub; chưa có HTTP/JWT/Auth thật, UI, thiết bị, backup. |
| **B — model/repository/provider** | Contract A, loading/error/retry, summary/history, cache, isolation, response trễ | Review `d7bac04df0712ab37ab5568900ee2da60b95b612`; tested code `a682007f6cd85931b410ec2930fd40cdd3fc73f4`; base A `fd38838d85fed31603eae99ed363cf202650aeee`; [review](review_d7bac04.md), [evidence](review_d7bac04_evidence/) | **Đạt local**, đóng B1/B2 P2. Reviewer tự chạy analyze sạch, 212 Flutter, 335 DB, 23 BH-07, 7 tích hợp, 3 nâng cấp, 6/6 probe. **Giới hạn:** provider/repository mock tại ranh giới RPC; chưa chứng minh HTTP/RLS/token thật, UI, thiết bị. |
| **C — UI lịch sử/tổng kết/copy** | Lịch sử, filter/pagination/refresh/error, tổng kết theo quyền, copy an toàn, gate complete, ngày UTC+7 | Tested `02a9b857724e9ba031323ad732c90355d7932a39`; base `9b978467316d66c458846ac68c5de8021401fa0c`; [review](review_02a9b85.md), [evidence](review_02a9b85_evidence/), [log phụ lục](review_02a9b85_logs_3d5583b.md) | **Đạt local**, đóng C1/C2/C3 P2. Reviewer tự chạy analyze sạch, 230 Flutter, 57 targeted C dưới UTC và Asia/Ho_Chi_Minh, 23 DB, 5 probe mỗi múi giờ. **Giới hạn:** widget/VM, chưa browser/thiết bị thật; bảy log gốc chỉ được xác nhận bổ sung sau review. |
| **D — tích hợp local** | Start → điểm danh → chốt phí → complete → history/summary; lifecycle; retry/version; privacy; logout/đổi actor | Tested `3d590a8418157cf91b00b9a5503d09be4df069f3`; docs/evidence `ce4522da5dc6785a0487acd1ae19d3ff80014a0c`; [review](review_3d590a8.md), [evidence](review_3d590a8_evidence/), [bàn giao](bh07_integration_handoff.md) | **Đạt tích hợp local**, không P0/P1/P2 trong phạm vi. Reviewer tự chạy analyze sạch, 240 Flutter, 10 D và 50 C mỗi múi giờ, 23 DB, 6 probe. **Giới hạn:** repository mock tại ranh giới client/RPC; cash sau complete chỉ kiểm nút; chưa HTTP/ACL server, browser/mobile, banking. |
| **HTTP/Auth local** | GoTrue/PostgREST/Kong/PostgreSQL thật: auth, ACL, privacy, scope, complete, finance, summary/history; charge 0 và raw privacy | Tested `f9159dd483baf2dd219b2854fd8ab08d1e5f0330`; docs/evidence `0758b72197a4626bd02189c0402deda978fc69fe`; base `593bea86ffb807675387dba6b0276b555fdc87a1`; [review](review_f9159dd.md), [evidence](review_f9159dd_evidence/), [bàn giao](http_auth_handoff.md) | **Đạt local vòng 1/2**, đóng H1/H2 P2. Reviewer tự chạy 70/70 HTTP, analyze sạch, 240 Flutter +1 skip, 23 DB, 4 probe. **Giới hạn:** stack Linux riêng; không tái lập recipe Windows/full Supabase CLI; không gồm concurrency/tải, browser/device, banking, staging/production. |
| **Concurrency HTTP/Auth** | Idempotent replay, competing complete, cash no-overcollect, transport drop sau commit rồi retry | Tested `cbcc46c2e125b156b53f4297ef864cf658855d37`; docs/evidence `bb940280333aec96457dd3014aabba9f66adf4ae`; base thực tế `a0f831af47f98c7649e0c80dce4d5f13004a0db2`; [review](review_cbcc46c_r2.md), [evidence](review_cbcc46c_r2_evidence/), [bàn giao](http_concurrency_handoff.md) | **Đạt local vòng 2/2**, đóng H3/H4; H1/H2 giữ đóng. Reviewer tự audit 19/19 hash/encoding/metadata; kế thừa 76/76 HTTP, 240 Flutter +1 skip, 23 DB, 4 probe. **Giới hạn:** không chạy lại suite ở vòng 2/2; chưa có tải thật, nhiều máy, mạng thật hoặc DB production. |
| **Browser / Offline / Reopen** | Flutter Web trên Chromium thật: start→complete→history/summary; 4 actor; offline/retry; F5/reopen; logout/cache; SPA route | Baseline source `a6d58aff3f1726484146a6c89aa7d559bb684d6d`, tự review local; [self-review](self_review_a6d58af.md), [evidence chính](browser_codex_fix_evidence/), [evidence tự review](self_review_a6d58af_evidence/), [closure](review_c4ce99b.md); gói `a62f509`/[browser_evidence](browser_evidence/) chỉ là lịch sử trước sửa, không dùng làm evidence chính | **Đạt local theo tự review/tự sửa, KHÔNG độc lập.** `browser_codex_fix_evidence/summary.json` xác nhận `tested_source_sha=a6d58aff3f1726484146a6c89aa7d559bb684d6d`; 11/11 browser, 12 ảnh khác hash, analyze sạch, 240 Flutter +1 skip, 23 DB; các control/mutant sau sửa PASS. **Giới hạn:** Chromium/SPA cụ thể; không mobile, browser khác, private Dart heap, deep link OS-level hoặc tải thật. |
| **Browser — response Owner trả trễ** | Owner→Cohost và Owner→Member khi response tài chính về sau login actor mới; privacy/copy/Cohost count-only/Member empty | Late source `c4ce99bcd9a9b02c4b794c8eb5ab51e43c06155a`; source sau sửa control `417ee30cf1fa2da4c64b03e0474d6c8c4a1dca6c`; [review](review_c4ce99b.md), [evidence](late_response_evidence/), [closure evidence](browser_closure_evidence/) | **Đạt local theo tự review/tự sửa, KHÔNG độc lập.** 2/2 ca UI, 21 control +2 mutant, 41 regression, 9 probe, 9 verifier, manifest 52/44 PASS; kế thừa 11 baseline +2 late. **Giới hạn:** chỉ hai lịch trễ cụ thể; không đo private Dart heap; không mobile/browser khác; không bảo đảm mọi cache/RPC/race. |
| **Backup/restore local** | Rehearsal cô lập: source stack, dump/restore PostgreSQL/Auth, ACL/replay smoke, cleanup fail-closed, manifest readonly | Source `282f978ba2afaa58e3f5810f282bdfd0febf334d`; docs/evidence `986baac29d506282740f477a5fb5ba94e15c496b`; base review `f216ae1fb220f140b091abd5acd2969333ec7f53`; [review](review_282f978.md), [evidence](backup_restore_cleanup_r2_evidence/), [runbook](../../26_BH07_OPERATIONS_REHEARSAL.md) | **Đạt local vòng 2/2**, đóng R1 cleanup. Reviewer tự chạy 14/14 control, 13/13 rehearsal Linux, analyze sạch, 240 Flutter +1 skip, 23 DB, manifest 16/16 readonly. **Giới hạn:** review không hoàn toàn độc lập với lịch sử tác giả; local Docker/PostgreSQL fixture; không managed Supabase/PITR/offsite/encryption/retention, concurrent writers, staging/production/restore thật. |
| **V2b — Private Dart heap/cache** | Provider tooling: sửa HP3-C theo ủy quyền ngoại lệ; app profile heap vẫn NOT RUN | Source `996c4266e6a38324dfc7e3a4b19ee50be101087b`; base review `01bfd160820eb7cda7198da4e0c1bb5d6810b795`; [bàn giao](private_heap_handoff.md), [review trước](review_b7eb881.md) | **Chờ review độc lập sau sửa HP3-C** (ủy quyền ngoại lệ). Giữ record theo testID nên exact-name duplicate FAIL/UNVERIFIED kèm testID, counts≤7; 33/33 regression tests; full runner exit0 PASS7/7 VERIFIED, dirty false; AST12/verifier5; probe reviewer exact-name duplicate exit1; analyze0; 247 Flutter+1skip. App-profile heap NOT RUN. Không tự ghi Đạt. |
| **V5b — Full Supabase reset local** | 2 chu kỳ CLI reset,18 migrations/chu kỳ,23 exact assertions,HTTP/Auth,Oracle schema+số dòng48 bảng | Tested source `8c107e9692b89f4a0aadeafc0ae139736f9b2622`; QA/docs `b036e9e65c3065e90454a6e645960599e633757b`; [review chốt](review_b036e9e.md), [QA evidence](full_reset_8c107e9_evidence/), [reviewer evidence](review_b036e9e_evidence/) | **Đạt local**, đóng H6,giữ các gate cũ. Reviewer21 Python/analyze0/240 Flutter+1skip/17hash vàaudit QA; full CLI reviewer rerun NOT RUN do thiếu đĩa. Codex từng sửa baseline, giới hạn độc lập giữ nguyên. Không nghiệm thu toàn BH-07/production. |
| **Hồ sơ readiness (tài liệu này)** | Ma trận cổng, phân biệt local/NOT RUN, kế hoạch kiểm chứng, cập nhật điểm tiếp tục | Base gốc `b91a350e619529d389af3edf6d4a06408af8d200`; base review vòng sửa `fdf7113ff46517a4c148fbcfcce5fea960686481`; nhánh `feat/bh07-readiness` | **Đạt docs-only vòng2/2 theo reviewer** tại31fced4 ([review](review_31fced4.md)). Không có bằng chứng runtime mới; chỉ là tài liệu quyết định. |
| **Toàn BH-07 / pilot** | Nghiệm thu toàn bộ cổng, staging/production, thiết bị, tải, pilot | Chưa có bằng chứng đầy đủ | **NOT RUN / chưa nghiệm thu.** Không được suy từ bất kỳ dòng “Đạt local” phía trên. |

## 3. Phân biệt Đạt local với NOT RUN

Cập nhật24/10/2026: V1 đã Đạt local, được đưa khỏi danh sách NOT RUN bên dưới; các cổng còn lại không đổi.

### 3.1. Những gì đã có bằng chứng local

- **A/B/C/D:** code, migration/RPC, provider và UI đã được review theo từng phần; regression local và DB cô lập đã chạy.
- **HTTP/Auth:** đã có token/JWT/PostgREST/GoTrue thật trên stack Linux cô lập, không dùng mock Auth cho assertion HTTP.
- **Concurrency HTTP:** đã có replay/competition/drop-response trên stack HTTP local.
- **Browser:** đã có Flutter Web + Chromium + Supabase local, thao tác UI thật và control âm; kết luận tự kiểm lịch sử không độc lập; V1 mới đã có review độc lập và chốt local ngày24/10/2026.
- **Backup/restore:** đã có rehearsal local cô lập, restore DB/Auth, smoke ACL/replay và cleanup fail-closed.
- **Full Supabase reset local:** đã chạy lặp lại 2 chu kỳ từ 18 migrations + seed, xác minh schema, HTTP Auth/RPC, 23 DB invariants và Oracle match trên project test CLI cô lập; đang Chờ review độc lập.

### 3.2. Những gì vẫn NOT RUN

| Cổng còn thiếu | Vì sao chưa thể coi là Đạt | Bằng chứng cần có trước khi đóng | Kế hoạch kiểm chứng tương ứng |
|---|---|---|---|
| Mobile iOS/Android thật | Chưa có thiết bị/emulator được nghiệm thu | Build thật, thao tác start→complete→history, offline/reopen, deep link, không rò dữ liệu | V2 (mục 4.3) |
| Browser khác/OS khác | Chỉ có Chromium/SPA cụ thể | Chrome/Firefox/Safari/Edge trên desktop/mobile, tối thiểu matrix đã chốt | V2 (mục 4.3) |
| Offline/reopen/deep link ngoài phạm vi browser đã chạy | Chưa kiểm OS-level, cold start, link trước/sau login | Kịch bản mất mạng, retry cùng intent, F5/cold start, deep link và logout | V2 (mục 4.3) |
| Đo private Dart heap/cache | Đã có test suite Dart VM WeakReference/Finalizer + GC (7/7 PASS), AST memory audit 38 files; đang Chờ review độc lập | Phép đo heap/cache độc lập được reviewer audit phương pháp và kết luận | V2b (mục 4.4) |
| Managed Supabase backup | Chỉ rehearsal PostgreSQL/Auth local | Backup project managed, Storage/Edge/Realtime/external secrets, restore sang project cô lập | V3 (mục 4.5) |
| PITR/offsite/encryption/retention | Chưa cấu hình/chứng minh trên managed service | Bằng chứng PITR, offsite copy, encryption at rest/in transit, retention/rotation và test restore | V3 (mục 4.5) |
| Backup với concurrent writers | Rehearsal dừng writer trước snapshot | Backup dưới tải ghi đồng thời, kiểm tính nhất quán và committed data | V4 (mục 4.6) |
| Staging/production restore thật | Chưa chạy restore/deploy ngoài local | Restore staging trước, sau đó production chỉ khi có phê duyệt riêng; smoke HTTP/ACL/app | V5 (mục 4.7) |
| Banking/VietQR/webhook thật | Ngoài phạm vi BH-07 hiện hành và chưa có sandbox evidence | Sandbox bank/webhook, idempotency, signature, reconciliation; không dùng tiền thật | V6 (mục 4.9) — Ngoài phạm vi |
| Rehearsal tải thật/pilot | Chưa có tải production-like hoặc người dùng pilot | SLO/RTO/RPO, kịch bản lỗi, rollback drill, dữ liệu ẩn danh và sign-off | V7 (mục 4.10) |
| Nghiệm thu toàn BH-07 | Chưa có ma trận đầy đủ với mọi cổng PASS | Tất cả cổng bắt buộc PASS; cổng vận hành chưa chạy phải có văn bản chấp nhận rủi ro còn lại của chủ dự án | V8 (mục 4.11) |

## 4. Kế hoạch kiểm chứng phần còn thiếu

**Không chạy các bước dưới đây trong lượt này.** Mỗi cổng phải có biên bản riêng, source/full SHA, lệnh/exit/count, môi trường, người phụ trách và kết luận của reviewer độc lập. Không dùng production làm môi trường thử.

Nguyên tắc phân định quyền hạn:
- **Reviewer độc lập chốt kết luận kỹ thuật (Đạt/Chưa đạt)** trong phạm vi kiểm chứng được giao, dựa trên bằng chứng độc lập, không hỏi chủ dự án xác nhận kết luận kỹ thuật.
- **Chủ dự án quyết định phạm vi (scope), chấp nhận rủi ro còn lại (residual-risk acceptance)** bằng văn bản chính thức cho các cổng vận hành/môi trường chưa chạy, và phê duyệt các thao tác/cửa sổ can thiệp trên môi trường riêng (staging/production/pilot).
- Phê duyệt chấp nhận rủi ro của chủ dự án **không làm thay đổi kết luận kỹ thuật**, **không đổi trạng thái NOT RUN thành PASS**, và **không thay thế bằng chứng kiểm thử kỹ thuật**.

### 4.1. R0 — Review hồ sơ readiness

- **Môi trường/đầu vào:** checkout sạch `feat/bh07-readiness`; base gốc `b91a350e619529d389af3edf6d4a06408af8d200`, base review vòng sửa `fdf7113ff46517a4c148fbcfcce5fea960686481`; tài liệu này và các tài liệu trạng thái đã cập nhật.
- **Phụ trách:** Reviewer độc lập (Codex) chốt kết luận kỹ thuật (Đạt / Chưa đạt) trong phạm vi tài liệu; chủ dự án quyết định phạm vi (scope), chấp nhận rủi ro còn lại (residual-risk acceptance) và phê duyệt các thao tác trên môi trường riêng (staging/production/pilot). Phê duyệt rủi ro không đổi NOT RUN thành PASS và không thay thế kết luận kỹ thuật của reviewer.
- **PASS:** link và SHA resolve 100%; không có diff app/backend/migration/script; mọi “Đạt local” có review/evidence hợp lệ; NOT RUN không bị che giấu; không có tuyên bố nghiệm thu toàn BH-07 khi chưa đủ điều kiện; stale status đã được đánh dấu lịch sử; sửa đủ 4 phát hiện R1–R4.
- **FAIL:** sai SHA/link, gán sai mức độ độc lập, bỏ sót cổng, hoặc ngụ ý deploy/pilot.
- **Rollback:** revert commit docs trên nhánh; không đụng source/evidence cũ.

### 4.2. V1 — Review độc lập Browser/Offline/Reopen và response trễ

**Trạng thái hiện hành: Đạt local ngày24/10/2026** theo [review](review_6283dbb.md), [chốt điều phối](v1_acceptance_448c50f.md). Các bước dưới đây giữ làm recipe/phạm vi đã kiểm; không đồng nghĩa private heap/device khác/managed Supabase/full reset đã chạy.

- **Môi trường/đầu vào:** checkout sạch source `417ee30cf1fa2da4c64b03e0474d6c8c4a1dca6c` (sau sửa control) và `c4ce99bcd9a9b02c4b794c8eb5ab51e43c06155a` cho hai ca trễ; Flutter Web + Chromium + Supabase local; tài khoản Owner/Cohost/Member/Finance; manifest và control đã công bố.
- **Phụ trách:** Reviewer độc lập/QA chốt kết luận kỹ thuật; người triển khai chỉ hỗ trợ tái lập môi trường, không tự chốt.
- **PASS:** 11/11 baseline + 2/2 ca trễ; 21 control và mutant đúng; offline/retry giữ cùng `request_id`; Cohost count-only/copy an toàn; Member empty/không summary-copy; không lộ contact/bank/secret; ảnh/log/hash khớp.
- **FAIL:** có success giả, rò dữ liệu, duplicate operation/audit, control âm bị bỏ qua, manifest thiếu/hash sai hoặc kết luận dựa vào log tác giả.
- **Rollback:** dừng phiên, giữ nguyên Git ref và evidence; không sửa app/backend để làm test xanh; đóng gói evidence review riêng.

### 4.3. V2 — Mobile/device, browser khác, offline/reopen/deep link

- **Môi trường/đầu vào:** ít nhất một thiết bị iOS và một Android thật (hoặc emulator được chủ dự án chấp thuận), cùng desktop Chrome/Firefox/Safari/Edge; API local/staging; build có ký/không ký theo môi trường; tài khoản test.
- **Phụ trách:** QA mobile/web triển khai; reviewer độc lập kiểm mẫu và chốt kết luận kỹ thuật.
- **PASS:** start→điểm danh→chốt phí→complete→history/summary; mất mạng hiện lỗi thật, retry cùng intent; F5/cold start/reopen giữ phiên; deep link trước/sau login; logout/đổi actor không lộ dữ liệu; copy/QR fallback đúng.
- **FAIL:** crash, màn trắng, success giả, mất operation, rò dữ liệu actor/CLB, hoặc không mở được deep link.
- **Rollback:** gỡ build test, giữ dữ liệu test cô lập; không deploy store/production.

### 4.4. V2b — Đo private Dart heap/cache sau đổi actor

**Trạng thái hiện hành V2b: App-profile heap NOT RUN; gói Provider tooling Chờ review độc lập sau sửa HP3-C theo ủy quyền ngoại lệ**, theo [bàn giao](private_heap_handoff.md) và [review trước](review_b7eb881.md). HP3-A/HP3-B và HP1/HP2/HP4/HP5/HP6/HP7 đóng từ các vòng trước; HP3-C sửa tại source `996c426`: `_parse_json_events` trả record theo testID (không khóa theo full name), validator báo `tests_duplicate` kèm testID và chặn VERIFIED, counts canonical 7. Full runner exit0 PASS7/7 VERIFIED, `git_dirty false`; 33 regression tests; AST12/verifier5; probe reviewer `duplicate_probe.py` exact-name duplicate nay exit1; analyze0; 247 Flutter+1skip. V1/V5b Đạt local; không suy Provider harness thành sạch full app. Người triển khai không tự ghi Đạt; chờ reviewer kết luận.

- **Môi trường/đầu vào:** Flutter Web hoặc Flutter Desktop/Mobile chạy profile mode (kết nối qua Chrome DevTools Protocol / Dart VM service / DevTools Memory Profiler); tài khoản Owner, Cohost, Member; kịch bản: login Owner xem toàn bộ chi tiết tài chính / báo cáo doanh thu -> logout -> login Cohost hoặc Member xem màn hình tương ứng; chụp heap snapshot tại 3 mốc (trước login, khi Owner đang xem, và sau khi đổi sang Cohost/Member).
- **Phụ trách:** Frontend / Flutter engineer phụ trách kỹ thuật; reviewer độc lập audit phương pháp đo và kết quả snapshot.
- **PASS:**
  + Sau khi Owner logout và chuyển sang actor hạn chế quyền (Cohost hoặc Member), không còn bất kỳ retained object (tham chiếu sống) nào trong Dart heap chứa dữ liệu tài chính chi tiết của Owner (STK ngân hàng, số dư cá nhân, doanh thu tổng, ghi chú nội bộ);
  + In-memory cache của session trước bị dọn sạch (`FinanceProvider`/`SessionProvider` giải phóng hoặc reset state hoàn toàn);
  + Không rò rỉ object qua static/singleton/global event listeners hay stream subscriptions;
  + Phép đo memory có phương pháp, oracle xác định, lặp lại được;
  + Dọn dẹp sạch toàn bộ file snapshot/dump bộ nhớ tạm thời sau đo.
- **FAIL:**
  + Phát hiện retained objects hoặc chuỗi tham chiếu sống (reference retention path) giữ dữ liệu tài chính/STK/secrets của actor trước sau khi đã switch actor;
  + Rò rỉ bộ nhớ (memory leak) tăng lũy tiến qua các lần đổi actor;
  + Dữ liệu đo đạc không tái lập, thiếu baseline đối chiếu, hoặc không dọn dẹp artifacts đo.
- **Rollback:** Gỡ bỏ profiling flags/instrumentation; xóa toàn bộ memory dumps và artifacts test tạm; không đẩy build profiling ra môi trường test chung hay production.
- **Điều kiện chấp nhận & giới hạn:** Cổng này thuộc Nhóm 3 (Cổng môi trường/vận hành chuyên sâu). Nếu chưa có môi trường đo heap chuyên sâu trước pilot, cổng này GIỮ NGUYÊN TRẠNG THÁI NOT RUN (không tự chuyển PASS). Để nghiệm thu V8, chủ dự án có thể xem xét ban hành văn bản Chấp nhận rủi ro còn lại (Residual-Risk Acceptance) dựa trên các bằng chứng gián tiếp đã có (unit cache guard, UI/DOM/clipboard/storage clean sau logout ở V1) kèm biện pháp giám sát client.

### 4.5. V3 — Managed Supabase backup, PITR, offsite, encryption, retention

- **Môi trường/đầu vào:** project managed **staging** (không production), project restore cô lập; cấu hình backup/PITR/retention; Storage/Edge/Realtime/external secrets; credential scoped; dataset và mốc thời gian đã biết.
- **Phụ trách:** Infra/DBA triển khai; reviewer độc lập chốt kết luận kỹ thuật; chủ dự án phê duyệt cửa sổ và target.
- **PASS:** restore được sang project cô lập; row count/checksum khớp; Auth/ACL/RPC smoke qua HTTP; PITR chọn đúng mốc; offsite/encryption/retention có bằng chứng cấu hình và kiểm tra; không lộ secret.
- **FAIL:** không restore được, thiếu PITR/offsite, dữ liệu lệch, mã hóa/retention không được enforce, hoặc thao tác chạm production.
- **Rollback:** xóa project/snapshot tạo cho test; không thay đổi backup policy production; ghi rõ nếu test chưa chạy.

### 4.6. V4 — Backup với concurrent writers

- **Môi trường/đầu vào:** DB staging-like, hai hoặc nhiều writer thật (HTTP/PostgREST), backup chạy đồng thời; workload và expected invariants; không dùng production.
- **Phụ trách:** Backend/infra triển khai; QA và reviewer độc lập chốt kết luận kỹ thuật.
- **PASS:** backup nhất quán tại mốc chọn; committed transaction không mất; không duplicate/lost payment, ledger, audit; restore kiểm lại invariant; cleanup sạch.
- **FAIL:** mất dữ liệu committed, vi phạm FK/unique, backup treo quá ngưỡng hoặc restore tạo duplicate.
- **Rollback:** dừng writer/tải, hủy bản backup test, restore snapshot trước test; không đụng production.

### 4.7. V5 — Staging/production restore và deploy

- **Môi trường/đầu vào:** staging trước; production chỉ sau phê duyệt riêng của chủ dự án; release candidate, restore point, runbook, smoke test, snapshot rollback.
- **Phụ trách:** Release owner + infra triển khai; reviewer độc lập chốt kỹ thuật smoke/runbook; chủ dự án phê duyệt production.
- **PASS:** restore/deploy hoàn tất trong cửa sổ; app/HTTP/ACL/RPC smoke PASS; count/invariant khớp; RTO/RPO thực đo và ghi lại; rollback đã thử.
- **FAIL:** lệch dữ liệu, auth/ACL lỗi, quá cửa sổ, không rollback được hoặc có truy cập ngoài phạm vi.
- **Rollback:** khôi phục snapshot trước restore, redeploy build trước, tắt traffic nếu chưa chắc; giữ nguyên chứng cứ.

### 4.8. V5b — Full Supabase reset từ migration trên project test sạch

**Trạng thái hiện hành V5b: Đạt local, đã đóng**, tested source `8c107e9692b89f4a0aadeafc0ae139736f9b2622`, base review `a55c2d2416f37a0bb8ac985e80bdee579b40774b`; [review chốt](review_b036e9e.md), [QA evidence](full_reset_8c107e9_evidence/), [reviewer evidence](review_b036e9e_evidence/). Hai chu kỳ QA có18 migration/23 exact assertions/HTTP/Auth vàOracle48 bảng khớp schema+số dòng; reviewer audit bundle vàtự chạy21 Python/analyze/240 Flutter+1skip/17hash. Reviewer không rerun full CLI vì thiếu đĩa, không tuyên bố độc lập toàn bộ lịch sử Codex. V5b được bỏ khỏi bảng NOT RUN hiện hành; các bước dưới giữ làm recipe/tiêu chí cho lần tái lập. Lịch sử review vàevidence không đổi.

- **Môi trường/đầu vào:** Môi trường local Docker Supabase CLI cô lập hoàn toàn hoặc project test trắng tạo riêng (TUYỆT ĐỐI KHÔNG dùng DB dev/staging/production có dữ liệu chung); thư mục `supabase/migrations/` đầy đủ tuần tự từ ban đầu đến migration mới nhất của BH-07; seed fixture tối thiểu chuẩn hóa.
- **Phụ trách:** Backend / DBA / infra engineer phụ trách kỹ thuật; reviewer độc lập verify exit code và log.
- **PASS:**
  + Lệnh `supabase db reset` (hoặc script dựng lại từ schema rỗng) kết thúc với exit code 0;
  + Toàn bộ migrations được áp dụng tuần tự không có cảnh báo/lỗi DDL;
  + Seed data nạp thành công, không lỗi khóa ngoại (FK) hay ràng buộc toàn vẹn;
  + Chạy suite 23 DB tests BH-07 + smoke HTTP/Auth đạt 100% PASS trên DB vừa dựng;
  + Chạy reset lặp lại lần 2 (`repeat reset oracle`) cho kết quả trạng thái schema và test exit code 0 giống hệt lần 1;
  + Dọn dẹp/tiêu hủy hoàn toàn DB test container hoặc project test sau khi kiểm xong, không để sót tài nguyên.
- **FAIL:**
  + Migration bị lỗi cú pháp, sai thứ tự phụ thuộc migration;
  + Seed thất bại;
  + Bất kỳ test nào trong 23 DB tests hoặc smoke HTTP/Auth bị fail sau reset;
  + Reset lần 2 cho kết quả khác lần 1;
  + Thao tác reset chạm vào container/DB ngoài phạm vi test cô lập.
- **Rollback:** Dừng ngay script; xóa bỏ và hủy toàn bộ container/project test vừa tạo; không ảnh hưởng bất kỳ cơ sở dữ liệu dùng chung nào.
- **Điều kiện chấp nhận & giới hạn:** Cổng này thuộc Nhóm 3. Nếu chưa thực hiện chạy test từ zero trong lượt này, cổng GIỮ NGUYÊN TRẠNG THÁI NOT RUN. Để nghiệm thu V8, chủ dự án có thể xem xét residual-risk acceptance bằng văn bản dựa trên kết quả migration tuần tự và rehearsal backup/restore đã đạt local.

### 4.9. V6 — Banking/VietQR/webhook (ngoài phạm vi BH-07 hiện hành)

- **Môi trường/đầu vào:** sandbox ngân hàng, tài khoản test, webhook sandbox, payload ký, dataset đối soát; không dùng tiền thật.
- **Phụ trách:** finance/integration owner triển khai; reviewer độc lập chốt kỹ thuật.
- **PASS:** QR/trạng thái thanh toán đúng; webhook idempotent, kiểm signature, retry không duplicate; ledger/đối soát khớp; không lộ secret.
- **FAIL:** duplicate/lost payment, nhận webhook sai chữ ký, lệch ledger, hoặc phát sinh giao dịch tiền thật.
- **Rollback:** tắt webhook/keys sandbox, đảo giao dịch test, không deploy production.
- **Lưu ý:** chỉ mở khi chủ dự án mở rộng phạm vi; không tự thêm vào BH-07.

### 4.10. V7 — Rehearsal tải thật và pilot

- **Môi trường/đầu vào:** staging với dữ liệu ẩn danh production-like; load generator; kịch bản start/complete/payment/history/summary; SLO, RTO/RPO, rollback drill; nhóm pilot giới hạn.
- **Phụ trách:** ops + QA triển khai; reviewer độc lập chốt kỹ thuật; chủ dự án phê duyệt mở pilot.
- **PASS:** SLO đạt, không P0/P1, không mất/duplicate dữ liệu, privacy/ACL đúng, rollback drill thành công, support và thông báo pilot sẵn sàng.
- **FAIL:** vượt ngưỡng, lỗi dữ liệu, rò quyền, không rollback được hoặc thiếu người trực.
- **Rollback:** dừng pilot, rollback release/snapshot, thông báo người dùng, giữ log và quyết định.

### 4.11. V8 — Nghiệm thu toàn BH-07

- **Môi trường/đầu vào:** Toàn bộ báo cáo/evidence của V1–V7 (kể cả V2b, V5b) và ma trận này; không chạy lại nếu không cần, nhưng phải chỉ rõ bằng chứng kế thừa.
- **Phân loại cổng kiểm chứng trong V8:**
  1. **Cổng bắt buộc kỹ thuật cốt lõi (Core Mandatory — Không thể miễn trừ/waive):** Gồm các cổng A, B, C, D (logic nghiệp vụ, DB, RPC, UI, tích hợp local); HTTP/Auth local; Concurrency HTTP/Auth local; V1 (Review độc lập Browser / Offline / Reopen và late response); R0 (Review hồ sơ readiness). Các cổng này **bắt buộc phải có kết luận Đạt/PASS từ reviewer độc lập** với bằng chứng đầy đủ. Tuyệt đối không được dùng văn bản chấp nhận rủi ro để thay thế.
  2. **Cổng ngoài phạm vi BH-07 hiện hành (Out-of-Scope):** V6 (Banking / VietQR / webhook thật). Không tính vào điều kiện nghiệm thu BH-07 trừ khi chủ dự án có quyết định mở rộng phạm vi bằng văn bản; giữ nhãn `NOT RUN (ngoài phạm vi)`.
  3. **Cổng môi trường/vận hành cho phép Chấp nhận rủi ro còn lại (Operational/Environmental with Allowed Residual-Risk Acceptance):** Gồm V2 (Mobile đa thiết bị/browser khác), V2b (Đo private Dart heap/cache), V3/V4 (Managed Supabase backup, PITR, retention, concurrent writers), V5/V5b (Staging restore/deploy thật, Full Supabase reset từ zero), V7 (Rehearsal tải thật/pilot). Các cổng này nếu chưa chạy thực tế thì **trạng thái kỹ thuật vẫn giữ nguyên là NOT RUN** (tuyệt đối không đổi thành PASS). Để nghiệm thu toàn BH-07, mỗi cổng chưa chạy trong nhóm này bắt buộc phải có văn bản Chấp nhận rủi ro còn lại (Residual-Risk Acceptance) chính thức từ chủ dự án, nêu rõ lý do, ranh giới rủi ro và biện pháp giảm thiểu.
- **Phụ trách:** Reviewer độc lập chốt kết luận kỹ thuật về tính hợp lệ và đầy đủ của bằng chứng; chủ dự án quyết định phạm vi (scope), ban hành văn bản chấp nhận rủi ro còn lại (nếu có), và quyết định bước tiếp theo của dự án.
- **Tiêu chí PASS (Phải thỏa mãn ĐỒNG THỜI tất cả các điều kiện sau):**
  1. 100% các cổng bắt buộc kỹ thuật cốt lõi (Nhóm 1) có kết luận Đạt/PASS từ reviewer độc lập với đầy đủ bằng chứng kiểm chứng; VÀ
  2. Không có bất kỳ phát hiện P0/P1/P2 nào còn mở trong toàn bộ các cổng đã review; VÀ
  3. Đối với mọi cổng thuộc Nhóm 3 còn ở trạng thái NOT RUN, đã có văn bản Chấp nhận rủi ro còn lại (Residual-Risk Acceptance) hợp lệ do chủ dự án ban hành cho từng cổng; VÀ
  4. Không có bất kỳ cổng nào đã chạy mà có kết luận FAIL (Chưa đạt); VÀ
  5. 100% link Markdown tồn tại, mọi commit SHA resolve chính xác, không mâu thuẫn verdict giữa các tài liệu trạng thái.
- **Tiêu chí FAIL (Rơi vào BẤT KỲ điều kiện nào sau đây):**
  1. Bất kỳ cổng bắt buộc kỹ thuật cốt lõi nào (Nhóm 1) chưa chạy (NOT RUN), chưa có review độc lập, hoặc bị kết luận FAIL / Chưa đạt; HOẶC
  2. Còn bất kỳ phát hiện P0, P1, hoặc P2 nào chưa được khắc phục và đóng bởi reviewer; HOẶC
  3. Bất kỳ cổng nào thuộc Nhóm 3 chưa chạy (NOT RUN) MÀ CHƯA CÓ văn bản Chấp nhận rủi ro còn lại hợp lệ từ chủ dự án; HOẶC
  4. Bất kỳ cổng nào khi kiểm chứng thực tế bị kết luận FAIL (lỗi dữ liệu, rò rỉ quyền/bí mật, vi phạm invariants, vượt ngưỡng SLO, hoặc lỗi rollback); HOẶC
  5. Phát hiện commit SHA không resolve, link Markdown gãy, manifest sai lệch, hoặc có mâu thuẫn về trạng thái/verdict giữa các văn bản.
- **Rollback:** Giữ ref chưa merge, không merge main, không deploy, không mở pilot; lập danh sách đúng các cổng thiếu hoặc lỗi để giao triển khai lại.
- **Quy tắc bất biến:** Việc chủ dự án chấp nhận rủi ro bằng văn bản cho một cổng Nhóm 3 KHÔNG ĐƯỢC biến cổng đó thành PASS trên ma trận kỹ thuật (vẫn ghi NOT RUN kèm ghi chú chấp nhận rủi ro). Chấp nhận rủi ro chỉ là điều kiện quản trị để giải phóng nghiệm thu, không thay thế kiểm thử kỹ thuật và không cấp quyền tự động deploy hay chuyển BH-08.

## 5. Thứ tự thực hiện đề xuất

1. **R0:** review hồ sơ này, chốt các trạng thái và điểm tiếp tục.
2. **V1 và V5b đã Đạt local** theo hồ sơ chốt riêng; [chốt V5b](review_b036e9e.md). Bước local tiếp theo có thể giao V2b đo private Dart heap theo mục4.4, không suy từ UI; chưa tự mở gate trong lượt chốt.
3. **V3/V4:** managed backup/PITR/retention và concurrent writers — cổng vận hành còn trống lớn nhất.
4. **V5:** staging restore/deploy cần môi trường và phê duyệt riêng; production không được thử tự động. **V5b full CLI reset đã đóng local**, không đồng nghĩa V5 đã chạy.
5. **V2/V2b:** mobile/browser khác/offline/deep link và đo heap/cache — có thể chạy song song V3/V4 nếu đủ thiết bị/công cụ.
6. **V6:** banking/webhook chỉ khi mở rộng phạm vi.
7. **V7:** load rehearsal/pilot.
8. **V8:** nghiệm thu toàn BH-07.

## 6. Rủi ro và biện pháp

| Rủi ro | Tác động | Biện pháp |
|---|---|---|
| Đọc “Đạt local” thành “Đạt BH-07” | Merge/deploy/pilot sớm | Giữ nhãn **local** và bảng NOT RUN ở mọi tài liệu trạng thái; reviewer kiểm lại |
| Browser final không độc lập | Bỏ sót lỗi privacy/retry/ACL | V1 đã có reviewer khác tự chạy và chốt local24/10/2026; giữ giới hạn, không suy sang private heap/device khác |
| Backup local không đại diện managed Supabase | Mất dữ liệu/PITR khi sự cố thật | V3/V4 trên managed staging và restore cô lập trước production |
| Nhầm lẫn quyền chốt review và quyền duyệt rủi ro | Bỏ qua vai trò reviewer hoặc tự động hóa quyền deploy | Quy định rõ: reviewer độc lập chốt kỹ thuật Đạt/Chưa đạt; chủ dự án duyệt scope, acceptance rủi ro và môi trường |
| Biến chấp nhận rủi ro thành test PASS giả | Giảm tiêu chuẩn chất lượng khi deploy | Khẳng định bất biến: acceptance rủi ro không đổi NOT RUN thành PASS trên ma trận kỹ thuật |
| Stale “Chờ review” trong tài liệu | Hiểu sai điểm tiếp tục | Đánh dấu lịch sử, cập nhật đầu docs/00, 09, 25, 26, AGENTS, README, STATUS_HISTORY và handoff backup/restore |
| Môi trường Linux/Windows khác nhau | Kết quả không tái lập | Ghi rõ stack, lệnh, exit; không tuyên bố recipe chưa chạy là PASS |
| Scope creep sang BH-08/BH-09/banking | Trộn cổng, tăng rủi ro | Chỉ mở khi chủ dự án giao; giữ ngoài ma trận BH-07 hiện hành |

## 7. Đối chiếu SHA đầy đủ

| Mốc | SHA đầy đủ | Ghi chú |
|---|---|---|
| Base readiness gốc | `b91a350e619529d389af3edf6d4a06408af8d200` | Review chốt backup/restore local |
| Base review vòng sửa R1–R4 | `fdf7113ff46517a4c148fbcfcce5fea960686481` | Review readiness vòng 1/2 của Codex |
| Tested readiness trước sửa | `bc63673cd58ce0f83bc783cb33375a6aba9e6576` | Hồ sơ ban đầu trước review bc63673 |
| A — tested | `4512c3a19e7c22f2adc4a9f3269cbabe8acd9d09` | Code/runner/migration `c339a47fdcb08e50811079bd89df7a1f9f53908a` |
| A — base main | `62d2c67dc66d512cf7f6f19932e2131ae060e2e9` | Nhánh `feat/bh07a-db` |
| B — review | `d7bac04df0712ab37ab5568900ee2da60b95b612` | Tested code `a682007f6cd85931b410ec2930fd40cdd3fc73f4` |
| B — base A | `fd38838d85fed31603eae99ed363cf202650aeee` | Nhánh `feat/bh07b-data` |
| C — tested | `02a9b857724e9ba031323ad732c90355d7932a39` | Docs/evidence `f63e5a4e58303a698017e8a46f91fcd3d79227f4` |
| C — base | `9b978467316d66c458846ac68c5de8021401fa0c` | Nhánh `feat/bh07c-ui` |
| D — tested | `3d590a8418157cf91b00b9a5503d09be4df069f3` | Docs/evidence `ce4522da5dc6785a0487acd1ae19d3ff80014a0c` |
| D — base | `b0478a72021a726530c4051b52239a0a22d7fb96` | Nhánh `feat/bh07-integration` |
| HTTP/Auth — tested | `f9159dd483baf2dd219b2854fd8ab08d1e5f0330` | Docs/evidence `0758b72197a4626bd02189c0402deda978fc69fe` |
| HTTP/Auth — base | `593bea86ffb807675387dba6b0276b555fdc87a1` | Nhánh `feat/bh07-http-verification` |
| Concurrency — tested | `cbcc46c2e125b156b53f4297ef864cf658855d37` | Base thực tế `a0f831af47f98c7649e0c80dce4d5f13004a0db2` |
| Concurrency — docs/evidence | `bb940280333aec96457dd3014aabba9f66adf4ae` | Nhánh `feat/bh07-http-concurrency` |
| Browser — baseline source | `a6d58aff3f1726484146a6c89aa7d559bb684d6d` | Tự review local; evidence chính tại `browser_codex_fix_evidence/` |
| Browser — baseline docs/evidence | `994ebfeb98c7c76815c2b8e0e6519fbe735ab1af` | Tự review đính kèm `self_review_a6d58af_evidence/` |
| Browser — response trễ | `c4ce99bcd9a9b02c4b794c8eb5ab51e43c06155a` | Hai ca UI local |
| Browser — control fix | `417ee30cf1fa2da4c64b03e0474d6c8c4a1dca6c` | Sửa negative control |
| Browser — closure docs | `74305bb343fbaf548cb5eea38a77475cc3a21b39` | Đóng nhánh browser |
| Browser — lịch sử trước sửa (Chưa đạt) | `a62f509986f65592da3fb5bccebe7b7c246ff7b7` | Review `02cd0ed`; `browser_evidence/` là bằng chứng cũ |
| Browser — docs/evidence trước sửa | `02cd0edbb9b1f77213c6788474984686895e125c` | Commit review `02cd0ed` |
| Backup — tested | `282f978ba2afaa58e3f5810f282bdfd0febf334d` | Cleanup R1 vòng 2/2 |
| Backup — docs/evidence | `986baac29d506282740f477a5fb5ba94e15c496b` | Review chốt local |
| Backup — base review | `f216ae1fb220f140b091abd5acd2969333ec7f53` | Review R1 vòng 1/2 |
| V5b — tested | `0392e2166bc0c33b3170e6919d86470d193d6301` | Runner/fixture reset local trên project test cô lập |

## 8. Kiểm tra tính nhất quán trong lượt này

- Base/current branch: `feat/bh07-readiness`, base review vòng sửa R1–R4 `fdf7113ff46517a4c148fbcfcce5fea960686481` (base gốc `b91a350e619529d389af3edf6d4a06408af8d200`); không merge main, không deploy, không chạy staging/production/pilot.
- `git diff --stat fdf7113` chỉ được chứa tài liệu; không có thay đổi `lib/`, `test/`, `supabase/`, `scripts/` hoặc evidence cũ.
- Các SHA nêu trong mục 7 được kiểm bằng `git cat-file -e <sha>^{commit}` trong lượt này.
- Ngoài mục 7, `docs/25` còn giữ SHA lịch sử `a0f831ae3f47e305608bfa0dff19ae035b31f798` đã được đính chính thành `a0f831af47f98c7649e0c80dce4d5f13004a0db2`; không dùng SHA cũ làm base.
- Link tương đối trong tài liệu này và các link trạng thái được kiểm bằng script đọc Markdown; đường dẫn evidence cũ giữ nguyên.
- Trạng thái hiện hành được cập nhật ở `AGENTS.md`, `README.md`, `docs/00_START_HERE.md`, `docs/09_IMPLEMENTATION_PLAN.md`, `docs/25_BH07_IMPLEMENTATION_HANDOFF.md`, `docs/26_BH07_OPERATIONS_REHEARSAL.md`, `docs/STATUS_HISTORY.md`; các mục “Chờ review” cũ được đánh dấu lịch sử.
- Không có kết quả runtime mới trong gói docs-only này; mọi số test trong ma trận là số kế thừa từ review/evidence tương ứng, không phải lần chạy mới.

## 9. Tài liệu liên quan

- [Review readiness BH-07 vòng 1/2](review_bc63673.md)
- [Đầu bài BH-07 và các cổng A/B/C/D](../../25_BH07_IMPLEMENTATION_HANDOFF.md)
- [Runbook vận hành/backup local](../../26_BH07_OPERATIONS_REHEARSAL.md)
- [Kế hoạch triển khai và trạng thái](../../09_IMPLEMENTATION_PLAN.md)
- [Điểm bắt đầu](../../00_START_HERE.md)
- [Lịch sử trạng thái](../../STATUS_HISTORY.md)
- [Review backup/restore local](review_282f978.md)
- [Review Browser/response trễ](review_c4ce99b.md)
