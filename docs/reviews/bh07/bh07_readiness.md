**Hiện hành 28/10/2026 — Mở rộng finance heap coverage Chưa đạt**,source thực `cd25e1e3557e2013e8991b2031a240818ee84c96`,docs `6f59f5e9fb9a8280a46c70aa9ca237b81fb8a023`,theo [review](review_6f59f5e.md);còn FH1 P1(payment khôngloaded vẫnPASS) vàFH2–FH4 P2(cleanup receipt cóthểbỏqua/saiID,SHAhandoff khôngresolve,claimmodel sạch vượt sentinel). Reviewer325Python,analyze0,247Flutter+1skip,fixture8/8,auditornew/old0 nhưng semantic controls tái hiện fail-open. Giao sửa vòng1/2 chỉ script/test/fixture/docs;không sửa app/backend. Giữ Đạt AT1–AT6/RP3-C,QA2expense-ID b13e468,V1,V5b;payment observations tác giả giữ nguyên,không gọi là verdict chốt mới. Full V2b/BH-07 chưa nghiệm thu,bank/receiver/ledger/instructions/listener Web graph/native vàruntime reviewer mới NOT RUN;không merge/deploy/pilot/BH-08.

**(Lịch sử trước review finance heap) 28/10/2026 — Đạt trong phạm vi AT1–AT6 retention attribution & coverage map tooling sau review độc lập vòng3**,tested source `f11d20f6c5025f7f774c266298bc0309fcd0de0c`,docs/handoff `41c1ea184835b0678504c6bc012c711871351d38`,base `a35c219d`,theo [review chốt](review_41c1ea1.md). Đóng AT1 P1,giữ AT2–AT6 đã đóng;không còn P0/P1/P2 mở trong phạm vi tooling. Reviewer độc lập tự chạy319/319 Python,analyze0,247Flutter+1skip;3probe gốc(3positive0/10mutant1) và12control AT1 bổ sung đều exit1 fail-closed;auditor `--out-dir` tạm exit0;10bundle lịch sử readonly100% hash,bundle reviewer14/14 verify0. Runtime QA tham chiếu vẫn `b13e468` (hai expense-ID Đạt local),không có runtime/DB mới;8rendered-title residual risk giữ `unattributed`,app-wide retention `UNKNOWN`,coverage ngoài2expense ID/listener Web graph/Dart VM desktop-mobile vàcác cổng khác `NOT RUN`;toàn V2b/BH-07 chưa nghiệm thu,không merge/deploy/pilot/BH-08. **Điều phối đã audit/chốt** reviewer commit2d567789 theo [hồ sơ](review_2d56778.md):11bundle readonly,reviewer14/14,3probe replay khớp;Codex từng sửa AT1,không nhận lượt audit này là review độc lập mới. Công việc tooling hoàn tất;điểm tiếp đề xuất coverage charges/payments Web profile local,chưa triển khai.

**(Lịch sử bàn giao trước review41c1ea1) 28/10/2026 — Chờ reviewer độc lập sau Codex sửa trực tiếp AT1 vòng3 theo ủy quyền “mở vòng 3 sửa”**,source `f11d20f6c5025f7f774c266298bc0309fcd0de0c`,base a35c219d,theo [bàn giao](codex_retention_attribution_r3_handoff.md). **Codex tự sửa/tự kiểm,KHÔNG phải review độc lập**;kiểm cycle/actor duy nhất vàscan/count/path/risk/hash nhất quán,không sửa app/backend. Red2method8fail→green targeted7;self-check319Python,analyze0,247Flutter+1skip;3positive0/10mutant1. AT2–AT6 giữ đóng theo review trước;AT1 chờ chốt,không tự ghi Đạt. Bundle cũ giữ byte,runtime tham chiếu vẫn b13e468;không có runtime/DB mới. QA hai expense-ID,RP3-C,V1,V5b giữ Đạt local;title residual risk unattributed,full V2b/BH-07 chưa nghiệm thu,các giới hạn/native/cổng khác NOT RUN;không merge/deploy/pilot/BH-08.

**(Lịch sử dừng trước ủy quyền sửa trực tiếp vòng3) 28/10/2026 — Retention attribution Chưa đạt vòng2/2 tại5226a3df,DỪNG theo AGENTS**,theo [review](review_5226a3d.md);đóng AT2,giữ AT3–AT6,còn AT1 P1(payload cycle lặp,scan/path presence mâu thuẫn,risk/path hash lệch vẫnCLI0). Báo chủ dự án,không tự mở vòng3/sửa source. Reviewer317Python,analyze0,247Flutter+1skip;7mutant cũ chặn đúng,3closure mutant chưa chặn,bundle5/5 readonly. QA runtime local hai expense-ID b13e468,tooling RP3-C,V1,V5b giữ Đạt;title residual risk unattributed,full V2b/BH-07 chưa nghiệm thu,các giới hạn/runtime/native còn NOT RUN;không merge/deploy/pilot/BH-08.

**(Lịch sử trước chốt attribution vòng2/2) 28/10/2026 — Retention attribution Chưa đạt vòng1/2 tại eda1eadd**,theo [review](review_eda1ead.md);AT3–AT6 đóng,còn AT1 P1(validate chưa đủ8record/thiếu count) và AT2 P2(JSON app sạch mâu thuẫn limits). Ba mutant cũ chặn đúng,bốn control mới vẫnCLI0;reviewer317Python,analyze0,247Flutter+1skip,bundle5/5 readonly. Giao sửa vòng2/2 chỉ script/test/docs;không sửa app/backend. QA runtime hai expense-ID b13e468,RP3-C,V1,V5b giữ Đạt local;residual title unattributed,full V2b/BH-07 chưa nghiệm thu,các phần coverage/runtime/native còn NOT RUN;không merge/deploy/pilot/BH-08.

**(Lịch sử trước review attribution vòng1/2) 28/10/2026 — Retention attribution/coverage Chưa đạt tại37b4954**,theo [review](review_37b4954.md);còn AT1 P1 vàAT2–AT6 P2:CLI fail-open,kết luận engine/app/native vượt bằng chứng,map field/listener sai,thiếu run.log,link máy riêng,sentinel thô trong docs. Giao sửa vòng1/2 chỉ script/test/docs;không sửa app/backend. **Giữ Đạt QA runtime local hai expense-ID b13e468 và tooling RP3-C**;residual rendered-title vẫn unattributed,full V2b/BH-07 chưa nghiệm thu. Reviewer316Python,analyze0,247Flutter+1skip;control mutant vẫn kết luận sai,manifest tác giả4/5 exit1. Runtime/DB mới,coverage rộng/Dart VM và các cổng khác giữ NOT RUN;V1,V5b giữ Đạt local;không merge/deploy/pilot/BH-08.

**(Lịch sử trước review attribution) 28/10/2026 — Đạt QA runtime độc lập local retained-path, đã chốt điều phối**, runtime source `b13e468d33e0d96437b58bb2da6088bff689b9eb` (publisher29f44a8), docs/evidence QA `3b393d33dd3dd773a92c1e4f2f4cbfd27af259e6`, theo [chốt điều phối](review_3b393d3.md). Hai chu kỳ Owner→logout→Cohost/Member,8snapshot/16finance-ID record,hai expense ID mất reachable sau logout/đổi actor;build profile mới39artifact,fixture cleanup xác minh theo QA. Điều phối tự verify5bundle3/3 readonly,source không đổi;không chạy runtime/SQL mới và không nhận count suite QA thiếu log riêng là lần chạy mới. **Toàn V2b/BH-07 chưa nghiệm thu**:8 residual rendered-title risk unattributed,identity quyền chưa xác lập,coverage ngoài2expense ID/Dart VM/mobile/browser khác/tải/staging/production vẫn NOT RUN. Bước tiếp: điều tra attribution title retained và lập coverage map,không tự sửa app/backend. Tooling RP3-C,Provider,V1,V5b giữ Đạt local;không merge/deploy/pilot/BH-08.

**(Lịch sử trước chốt runtime retained-path) 27/10/2026 — Đạt bản sửa RP3-C trong phạm vi retained-path tooling**, source `29f44a8e8f86ff68e3ebe54f981cbb73ea5ceb2b`, docs `c509aeeebf9e978992e93f7ac79f2aa677f0ffac`, theo [review độc lập](review_c509aee.md). Không còn P0/P1/P2 mở trong phạm vi sửa publisher; RP1/RP2/RP3-B/RP4/RP5/RP6 giữ kết luận đã đóng. Reviewer312 Python, fixture6/self34, analyze0,247 Flutter+1skip, probe JSON3/3 hợp lệ; bundle R1 verify0, hai bundle cũ reject1, bytes lịch sử giữ nguyên. **Runtime mới source29f44a8 và query DB reviewer NOT RUN**; runtime kế thừa vẫn source86181de, không retag. Bước tiếp: QA độc lập retained-path runtime trên máy đủ môi trường, giữ giới hạn hai expense ID và residual risk unattributed. **Toàn V2b/BH-07 chưa nghiệm thu**; Provider/tooling,V1,V5b giữ Đạt local, các cổng khác giữ NOT RUN; không merge/deploy/pilot/BH-08.

**(Lịch sử trước chốt RP3-C) 27/10/2026 — V2b §4.4 retained paths + finance coverage Chờ review độc lập vòng 1/2 sau sửa RP1–RP6**; chi tiết ở [mục 4.4](#44-v2b--đo-private-dart-heapcache-sau-đổi-actor), [bàn giao](retained_path_handoff.md) và [evidence](retained_path_r1_evidence/). Toàn BH-07 chưa nghiệm thu; các cổng khác giữ NOT RUN; không merge/deploy/pilot/BH-08.

**(Lịch sử 26/10/2026) V2b app-profile heap Chờ review sau khi sửa AH9 theo ủy quyền bổ sung (review 0f11bb4)**, tested source `c04ce55` (`git_dirty: false`), base review `a1263548cf06732475fe75577d141b0eedd75210` ([review 0f11bb4](review_0f11bb4.md)), nhánh `feat/bh07-app-profile-heap-verification`, theo [bàn giao](app_profile_heap_handoff.md) và [evidence](app_profile_heap_evidence/). **AH9** (P2): thêm **validator dùng chung** `heap_oracle.scan_problems(scan)` — scan `ok=true` bắt buộc `occurrences` là `int` thật không âm, `present` là `bool` thật và **`present == (occurrences > 0)`**; scan hỏng không được khai presence. `decide()` gọi validator trước khi so kỳ vọng và auditor gọi lại cho từng mốc, nên count mâu thuẫn hay sai kiểu ⇒ FAIL/exit 1 có finding thay vì được gọi "internally consistent". AH1–AH8 và AH4/AH5 giữ nguyên; probe reviewer cũ phát lại đúng kỳ vọng. Runtime mới trên source sạch `c04ce55`: `status=RUN verdict=PASS`, 2 chu kỳ × 4 mốc trong cùng document, bank sentinel **có** khi Owner xem và **mất** sau logout/đổi actor, 24 record count/presence nhất quán, build profile 32,7 s, 39 artifact, cleanup xác minh. **146/146 test Python** (48 oracle, 88 auditor, 4 guard+sanitizer, 3 phát lại probe, 3 link); 18 control đỏ trước sửa; `count_controls.py` của reviewer nay đúng (positive `[]`, 4 mutant count có finding, CLI exit 1 kèm `contradicts`); `closure_controls.py`/`extra_controls.py`/`probes.py` giữ kỳ vọng, `build_probe.js` exit 1, analyze 0 issue, 247 Flutter +1 skip. **Giới hạn:** heap V8/dart2js của web profile; **Dart VM desktop/mobile NOT RUN**; runtime **reviewer** NOT RUN nên đây là lần chạy tác giả; AH9 là lỗi fail-open của validator trên dữ liệu scan, **không** kết luận app leak; nhánh `available:false` chỉ kiểm bằng unit test. **Người triển khai không tự ghi Đạt.** Provider/tooling, V1, V5b giữ Đạt local; V2b chưa đóng, toàn BH-07 chưa nghiệm thu; các cổng khác NOT RUN; không merge main/staging/production/deploy/pilot/BH-08.

**(Lịch sử bàn giao trước review 0f11bb4) V2b app-profile heap Chờ review sau khi sửa AH7/AH8 theo ủy quyền ngoại lệ**, tested source `c3ca02e`, base review `268735ccd071936bada7cbcdf81fad6c87187e00`: presence đếm trên string table đã decode (literal = escaped) và metadata nhận diện sentinel bắt buộc; 123/123 test Python, runtime `RUN/PASS` 2 chu kỳ. Review 0f11bb4 sau đó đóng AH7/AH8 và mở AH9 P2 về count/presence không được kiểm.

**(Lịch sử bàn giao trước review 76334e2) V2b app-profile heap Chờ review độc lập vòng 2/2 sau sửa AH1, AH2-A/B, AH3-A/B, AH6**, tested source `130af7d` (`git_dirty: false`), base review `8c02605bad98edd9c55f44f57fdfea18c2ecac68`; oracle là grammar gate, auditor fail-closed, runtime `status=RUN verdict=PASS` 2 chu kỳ, 104/104 test Python. Review 76334e2 sau đó mở AH7/AH8 P2 và dừng vòng 2/2 theo AGENTS.

**(Lịch sử bàn giao trước review 57ec02c) V2b app-profile heap Chờ review độc lập vòng 1/2 sau sửa AH1–AH5**, tested source `249f12ed5b8ba042de1d48e9d5e06ffe7c125ada`, base review `a972ecd73ab2339306f80b081823057c5935819c` (review 8914b2f); oracle chứng minh cấu trúc V8, auditor tự tính lại verdict, manifest/secret/LF, `--reuse-build` bị từ chối; 66/66 test Python, runtime `status=RUN verdict=PASS` trên `249f12e`. Sau đó review 57ec02c mở lại AH1 P1 và AH2-A/B, AH3-A/B, AH6 P2.

**(Lịch sử bàn giao trước review 8914b2f) V2b app-profile heap Chờ review độc lập**, tested source `bb2d2130276ad31824acc650a02ecee4b6ba95a6`, base `3b30e4941058c0cfebec06b377abfc53f19576a4`, nhánh `feat/bh07-app-profile-heap-verification`, theo [bàn giao V2b app-profile](app_profile_heap_handoff.md) và [evidence](app_profile_heap_evidence/). Đã chạy phép đo thật trên **build web profile** của app + Chrome CDP `HeapProfiler`: 2 chu kỳ `Owner → logout → Cohost` và `Owner → logout → Member`, mỗi chu kỳ 4 mốc (`baseline`, `owner_active`, `post_logout`, `post_actor`) trong **cùng một document** (không reload/navigate, kiểm bằng `performance.timeOrigin`), `git_dirty false`, build profile 44,9 s. Sentinel `club_bank_accounts.account_number` của Club A **có** khi Owner đang xem và **mất** sau logout và sau khi đổi actor ở cả 2 chu kỳ; oracle từ chối snapshot hỏng/thiếu mốc/`probe` chết/build không profile/cleanup chưa xác minh. `verify_evidence.py` PASS (hash khớp, không raw heap, không secret, LF), 18/18 test Python, analyze 0 issue, 247 Flutter +1 skip, cleanup heap dump + profile Chrome đã xoá và kiểm lại. **Giới hạn:** đây là heap V8/dart2js của bản web profile; **Dart VM heap desktop/mobile NOT RUN** (máy không có Visual Studio/Android SDK), sentinel không liệt kê đủ mọi retained object. **Người triển khai không tự ghi Đạt.** Gói Provider/tooling đã Đạt giữ nguyên; V1/V5b giữ Đạt local; các cổng khác NOT RUN; toàn BH-07 chưa nghiệm thu; không merge main/staging/production/deploy/pilot/BH-08.

**(Lịch sử trước bàn giao app-profile) Đạt gói Provider/tooling bổ trợ V2b, đóng HP3-C**, tested source `996c4266e6a38324dfc7e3a4b19ee50be101087b`, docs/evidence `c63e43f113e95d8cf56ff79504802e249f38d4a7`, theo [review chốt](review_c63e43f.md). Không còn P0/P1/P2 mở trong phạm vi này; HP3-A/B vàHP1/HP2/HP4/HP5/HP6/HP7 giữ nguyên. Reviewer full runner source sạch PASS7/7 VERIFIED,33/33 Python,AST12/verifier5,analyze0,247 Flutter+1skip,author bundle4/4 readonly PASS; exact duplicate ID999 bị FAIL/UNVERIFIED,Markdown negative,main-boundary1,parser giữ8 records trước validator. **App-profile heap V2b khi đó vẫn NOT RUN**, không suy gói bổ trợ thành Đạt toàn cổng. Đóng phần sửa tooling trên nhánh,giữ V1/V5b Đạt local,các cổng khác NOT RUN,toàn BH-07 chưa nghiệm thu. Không merge main/staging/production/deploy/pilot/BH-08.

**(Lịch sử bàn giao trước chốt review c63e43f) V2b Provider tooling Chờ review độc lập sau sửa HP3-C**, tested source `996c4266e6a38324dfc7e3a4b19ee50be101087b`, base review `01bfd160820eb7cda7198da4e0c1bb5d6810b795` (review b7eb881), theo [bàn giao](private_heap_handoff.md). Đã sửa 1 P2 HP3-C: `_parse_json_events` giữ **từng record theo testID** (không khóa theo full name) nên hai test ID cùng tên đầy đủ không bị gộp; validator báo `tests_duplicate` kèm testID, chặn `VERIFIED` → `UNVERIFIED`/`FAIL`, counts vẫn canonical 7, Markdown/JSON/exit dùng chung verdict. 33/33 regression tests (thêm exact-name/different-ID, RED trước sửa); full runner exit0 PASS 7/7 `identity_coverage VERIFIED`, `git_dirty false`, manifest 4/4 strict UTF-8 LF; AST 12/12, verifier 5/5; probe reviewer `duplicate_probe.py` exact-name duplicate nay FAIL/UNVERIFIED exit1 (trước PASS/exit0), `protocol_probe.py` giữ kỳ vọng; analyze 0 issue, 247 Flutter +1 skip. HP3-A/HP3-B và HP1/HP2/HP4/HP5/HP6/HP7 giữ nguyên; app-profile heap **NOT RUN**. **Người triển khai không tự ghi Đạt.** V1/V5b giữ Đạt local; các cổng khác giữ NOT RUN; toàn BH-07 chưa nghiệm thu; không merge main/staging/production/deploy/pilot/BH-08.

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
| **V2b — Private Dart heap/cache** | Đạt runtime local hai expense-ID; toàn cổng chưa đóng | QA sourceb13e468,docs3b393d3;[chốt](review_3b393d3.md),[QA](review_runtime_b13e468.md),[evidence](review_runtime_b13e468_evidence/) | Hai chu kỳ cùng SPA,ID không còn reachable sau logout/đổi actor;8 rendered risk unattributed. Điều phối audit readonly,không runtime mới;coverage rộng/Dart VM NOT RUN. |
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
| Đo private Dart heap/cache của app profile | QA runtime Web profile hai expense-ID Đạt theo [chốt](review_3b393d3.md);full coverage/Dart VM NOT RUN | Điều tra attribution title retained,coverage map và phép đo bổ sung riêng;không suy từ hai ID sang toàn cache/model | V2b (mục 4.4) |
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

**Trạng thái hiện hành V2b: tooling AT1–AT6 vàQA2expense-ID giữ Đạt;finance heap expansion Chưa đạt**,theo [review](review_6f59f5e.md),còn FH1 P1/FH2–FH4 P2,giao sửa vòng1/2. Payment observations giữ nguyên nhưngprofile gate chưa đủ;full coverage/Dart VM/toàn V2b/BH-07 chưa nghiệm thu.

**(Lịch sử bàn giao trước review41c1ea1)** **Trạng thái V2b khi đó: QA runtime hai expense-ID giữ Đạt;AT1 Chờ reviewer độc lập sau Codex sửa trực tiếp vòng3 được chủ dự án ủy quyền**,source f11d20f6,theo [bàn giao](codex_retention_attribution_r3_handoff.md). Tự sửa/tự kiểm KHÔNG độc lập;AT2–AT6 giữ đóng. Full coverage/Dart VM/toàn V2b/BH-07 chưa nghiệm thu,residual title unattributed.

**(Lịch sử bàn giao trước review04d1ea9)** **Trạng thái hiện hành V2b: retained-path Chưa đạt vòng1/2,còn RP3-B P2**,theo [review](review_4184faf.md). Đóng RP1,RP2,RP4,RP5,RP6 và oracle-label redaction;publication sanitizer còn để sót fragment trong failed artifact. Reviewer302/302 Python,fixture6/self34,analyze0,247Flutter+1skip;bundle mới PASS,2bundle cũ reject,bytes giữ nguyên. Runtime/DB query reviewer NOT RUN do thiếu stack/đĩa;coverage ngoài2expense id,bank field thật,Dart VM/mobile/browser khác/tải/staging/production NOT RUN. Giao sửa vòng2/2 chỉ RP3-B;không sửa app/backend/DB,không merge/deploy/pilot/BH-08;full V2b/BH-07 chưa nghiệm thu.

**(Lịch sử bàn giao trước review4184faf)** **Trạng thái hiện hành V2b: retained paths + finance coverage Chờ review độc lập vòng 1/2 sau sửa RP1–RP6**,tested source `86181de1df03e11b3ad537f1024405724db83bfb` (`git_dirty: false`),base review `47b1e92` ([review 9fadecc](review_9fadecc.md)),nhánh `feat/bh07-retained-path-verification`,theo [bàn giao](retained_path_handoff.md) và [evidence](retained_path_r1_evidence/). Sửa đủ 1 P1 + 5 P2: RP1 fixture dùng một lần có UUID mới mỗi lần chạy + guard endpoint local + preflight từ chối collision + sở hữu đọc lại sau POST không trả lời + chỉ DELETE dòng mình tạo + xác minh vắng mặt theo id;RP2 reachability trên **mọi** node khớp,walk vượt budget/cycle là record `error` ⇒ FAIL (không phải unreachable);RP3 đọc **nguyên** nhãn trước khi cắt và sanitizer coi tiền tố ≥20 ký tự của giá trị riêng là private;RP4 auditor đối chiếu `rendered/distinctive/scope` giữa metadata ↔ **mọi** scan ↔ bảng declaration trong report;RP5 residual risk `attribution: unattributed`,note identity "not established",bỏ suy engine/authorized;RP6 contract cleanup created/removed/absent/sha12 + receipt JSON trong report phải bằng `summary.cleanup`. Runtime mới: `status=RUN verdict=PASS`,2 chu kỳ ×4 mốc cùng document,2 finance id **có** khi Owner xem và **không còn reachable** sau logout/đổi actor (cả 2 chu kỳ),title chi phí còn → residual risk unattributed,roster Cohost → note "not established",build profile 27 s/39 artifact,fixture `f4c5b2af20ea` created+removed+verified absent,DB local còn **0** dòng fixture. Lần chạy đầu của vòng này **FAIL do title fixture chứa chính id** (đã huỷ,không công bố) → title độc lập + control. **34/34 self-test**,**69** control path,**116** auditor,**5** ownership,**302/302 test Python**,`verify_evidence.py` PASS,analyze0,247 Flutter+1skip. **Giới hạn:** heap **V8/dart2js của web profile**;**Dart VM desktop/mobile NOT RUN**;runtime **reviewer** NOT RUN;sentinel không liệt kê đủ mọi retained object,chỉ 1 path/giá trị;residual risk **không quy được** cho engine hay app. **Người triển khai không tự ghi Đạt.** Provider/tooling,V1,V5b giữ Đạt local,toàn BH-07 chưa nghiệm thu;giữ nhánh chưa merge,không merge/deploy/pilot/BH-08.

**(Lịch sử review 9fadecc) Trạng thái V2b khi đó: retained paths + finance coverage Chưa đạt**,theo [review](review_9fadecc.md):RP1 P1 và RP2–RP6(5P2) còn mở. Reviewer258/258 Python,self32,analyze0,247Flutter+1skip;bundle mới verify0,cũ reject1,bytes cũ giữ nguyên. Runtime reviewer/query DB fixture vắng NOT RUN. Giao sửa công cụ vòng1/2,không sửa app/backend. Bank cũ chỉ xác nhận pattern,không dùng UUID collision làm coverage STK thật;rendered retainer/identity ngoài gate chưa được tự suy benign/authorized ở mọi actor. Full V2b§4.4,retained paths toàn model,Dart VM desktop/mobile chưa đóng;Provider/tooling,V1,V5b giữ Đạt local,toàn BH-07 chưa nghiệm thu;không merge/deploy/pilot/BH-08.

**(Lịch sử bàn giao trước review9fadecc)** **Trạng thái hiện hành V2b: retained paths + finance coverage đo thật trên web profile local, Chờ review độc lập**,tested source `66bda0e7e3e1c2e983110e26a6300f6685c3a450` (`git_dirty: false`),base `56e86accf2943ab2c7a79ebb0d6373b0dbcf0ef1`,nhánh `feat/bh07-retained-path-verification`,theo [bàn giao](retained_path_handoff.md) và [evidence](retained_path_evidence/). Oracle nay đi **graph từ GC root** trên cạnh mạnh để trả lời "còn reachable không, qua root nào" thay cho count string-table; sentinel được **khai lớp theo giá trị** (`rendered`/`distinctive`/`scope`) và **chỉ finance** không render, distinctive mới gate,bắt buộc **2** giá trị finance. Kết quả 2 chu kỳ `Owner→logout→Cohost/Member` × 4 mốc cùng document: hai finance id (`expense_id`,`expense_id_2`) **có** khi Owner xem và **không còn reachable** sau logout/đổi actor; bank digits chỉ khớp đuôi fixture UUID (`exact:false`,note,không gate); title chi phí còn trong **LRU segmentation của web engine** → `Residual risks`,không tính state app; roster id CLB mà Cohost **được phép fetch lại** → `Notes`,không gate. Lần chạy đầu **tự bắt 2 lỗi công bố** (nhãn cạnh engine chứa nguyên title; literal 10 chữ số trong report) và đã sửa trong oracle + control. **32/32 self-test**,**50** control path,**96** auditor,**258/258 test Python**,`verify_evidence.py` PASS,analyze0,247 Flutter+1skip,cleanup dump/profile/fixture dùng một lần đã xác minh. **Giới hạn:** heap **V8/dart2js của web profile**;**Dart VM desktop/mobile NOT RUN**;runtime **reviewer** NOT RUN nên đây là lần chạy tác giả;sentinel không liệt kê đủ mọi retained object nên cổng này **thu hẹp**,không đóng toàn bộ §4.4;residual risk engine **chưa** được loại bỏ. **Người triển khai không tự ghi Đạt.** Provider/tooling,V1,V5b giữ Đạt local,toàn BH-07 chưa nghiệm thu;giữ nhánh chưa merge,không merge/deploy/pilot/BH-08.

**(Lịch sử chốt điều phối trước bàn giao retained-path) Trạng thái V2b khi đó: Đạt gói công cụ V8 và QA runtime độc lập local của bank sentinel**,theo [chốt điều phối](review_2d16369.md),[QA report](review_runtime_97d0e7e.md),[QA evidence](review_runtime_97d0e7e_evidence/). Runtime QA tested97d0e7e/source công cục04ce55,QA docs2d16369;2cycle/8snapshot/24record nhất quán;điều phối audit2bundle3/3 readonly,khớp log/source/provenance. Codex không chạy Chrome lại;gói công cụ/AH1–AH9 giữ Đạt. **V2b §4.4 đầy đủ chưa đóng**: retained graph/paths toàn model/cache/listener và Dart VM desktop/mobile NOT RUN. Bank sentinel không chứng minh toàn app sạch. Provider/tooling,V1,V5b giữ Đạt local,toàn BH-07 chưa nghiệm thu;giữ nhánh chưa merge,không merge/deploy/pilot/BH-08.

**(Lịch sử chốt công cụ trước QA runtime)** **Trạng thái hiện hành V2b: Đạt bản sửa AH9 và gói công cụ V8/web-profile local**,theo [review chốt](review_5f2b5a6.md). Đóng AH9,giữ AH1–AH8;không có P0/P1/P2 mở trong phạm vi công cụ. Reviewer146/146 Python,self15/guard8/relation5,analyze0,247Flutter+1skip;count CLI mutant exit1 có contradicts,probes cũ giữ kỳ vọng,bundle3/3 readonly. Đóng phần sửa công cụ,giữ nhánh chưa merge. **Cổng V2b §4.4 đầy đủ chưa đóng**: runtime Chrome reviewer,retained paths/toàn model/cache/listener,Dart VM desktop/mobile NOT RUN;runtime tác giả không thay phép đo độc lập. Provider/tooling,V1,V5b giữ Đạt local,toàn BH-07 chưa nghiệm thu;không merge/deploy/pilot/BH-08.

**(Lịch sử bàn giao trước review5f2b5a6)** **Trạng thái hiện hành V2b: app-profile heap Chờ review sau khi sửa AH9 theo ủy quyền bổ sung**, theo [bàn giao](app_profile_heap_handoff.md): validator scan dùng chung bắt buộc `occurrences` int không âm, `present` bool và `present == (occurrences > 0)`, scan hỏng không được khai presence; count mâu thuẫn ⇒ FAIL/exit 1 (CLI in `contradicts`); 18 control đỏ trước sửa, **146/146 xanh**; runtime tác giả `RUN/PASS` 2 chu kỳ trên `c04ce55` (`git_dirty false`), build 32,7 s, 24 record nhất quán. AH1–AH8, AH4/AH5 giữ. **Runtime reviewer NOT RUN**; retained paths/toàn app, AH7 trên Chrome thật và Dart VM desktop/mobile NOT RUN. **Người triển khai không tự ghi Đạt.** Provider/tooling, V1, V5b giữ Đạt local; toàn BH-07 chưa nghiệm thu; không merge/deploy/pilot/BH-08.

**(Lịch sử bàn giao trước review0f11bb4)** **Trạng thái hiện hành V2b: app-profile heap Chờ review sau khi sửa AH7/AH8 theo ủy quyền ngoại lệ**, theo [bàn giao](app_profile_heap_handoff.md): presence đếm trên string table đã decode (literal = escaped, retained escaped ⇒ FAIL) và metadata nhận diện sentinel là bắt buộc (thiếu `length`/`sha256_12` ⇒ finding, `available:false` phải tường minh và không bị scan claim); 12 control đỏ trước sửa, **123/123 xanh**; runtime tác giả `RUN/PASS` 2 chu kỳ trên `c3ca02e` (`git_dirty false`), build 46,7 s. AH1–AH6, AH4/AH5 giữ. **Runtime reviewer NOT RUN**; retained paths/toàn app, AH7 trên Chrome thật và Dart VM desktop/mobile NOT RUN. **Người triển khai không tự ghi Đạt.** Provider/tooling, V1, V5b giữ Đạt local; toàn BH-07 chưa nghiệm thu; không merge/deploy/pilot/BH-08.

**(Lịch sử bàn giao trước review76334e2)** **Trạng thái hiện hành V2b: app-profile heap Chờ review vòng 2/2 sau sửa AH1, AH2-A/B, AH3-A/B, AH6**, theo [bàn giao](app_profile_heap_handoff.md): oracle nay là **grammar gate** (parse toàn bộ JSON, từ chối khóa trùng, đúng thứ tự/khớp count), auditor fail-closed với summary rỗng/sai kiểu + parse từng hàng report + cấm symlink/junction + bắt raw sentinel bằng `length`+`sha256_12`; 24 control đỏ trước sửa, **104/104 xanh** sau sửa; runtime tác giả `status=RUN verdict=PASS` 2 chu kỳ trên source sạch `130af7d` (`git_dirty false`), build profile 61,3 s, cleanup xác minh. AH4/AH5 giữ. **Runtime reviewer vẫn NOT RUN**; retained paths/toàn app và Dart VM desktop/mobile NOT RUN. **Người triển khai không tự ghi Đạt.** Provider/tooling, V1, V5b giữ Đạt local; toàn BH-07 chưa nghiệm thu; không merge/deploy/pilot/BH-08.

**(Lịch sử bàn giao trước review57ec02c)** **Trạng thái hiện hành V2b: app-profile heap Chờ review vòng 1/2 sau sửa AH1–AH5**, theo [review độc lập 8914b2f](review_8914b2f.md): đã sửa đủ AH1 P1 + AH2–AH5 P2 và bổ sung control tái hiện; runtime mới trên source sạch `249f12e` (`status=RUN verdict=PASS`, 2 chu kỳ × 4 mốc, `git_dirty false`, provenance build profile + `served_match`), 66/66 test Python, auditor PASS, probe reviewer nguyên bản nay bị chặn, analyze 0 issue, 247 Flutter +1 skip. **Người triển khai không tự ghi Đạt.** Gói Provider/tooling bổ trợ giữ Đạt; V1/V5b giữ Đạt local. Giới hạn bank sentinel không đủ chứng minh toàn bộ retained objects/paths; Dart VM desktop/mobile NOT RUN; runtime reviewer vẫn NOT RUN. Không merge/deploy/pilot/BH-08.

**(Lịch sử bàn giao trước review 8914b2f)** **Trạng thái hiện hành V2b: app-profile heap đã đo thật (web profile + CDP), Chờ review độc lập; gói Provider/tooling bổ trợ đã Đạt**, theo [bàn giao app-profile](app_profile_heap_handoff.md), [evidence](app_profile_heap_evidence/), [review chốt c63e43f](review_c63e43f.md). Phép đo: build `flutter build web --profile` của app thật, Chrome thật qua CDP `HeapProfiler.takeHeapSnapshot`, 2 chu kỳ `Owner → logout → Cohost/Member`, 4 mốc/chu kỳ trong cùng một document; sentinel STK ngân hàng Club A có khi Owner đang xem, mất sau logout và sau đổi actor; `status=RUN verdict=PASS`, `git_dirty false`, cleanup dump/profile đã xác minh, auditor bundle PASS, 18/18 test Python, analyze 0 issue, 247 Flutter +1 skip. **Giới hạn:** V8/dart2js heap của bản web profile — **Dart VM heap desktop/mobile NOT RUN** (máy không có Visual Studio/Android SDK), sentinel không liệt kê đủ mọi retained object. Người triển khai không tự ghi Đạt; V1/V5b giữ Đạt local; không merge/deploy/pilot/BH-08.

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
2. **V1 và V5b giữ Đạt local**. Tooling AT1–AT6/QA2expense-ID giữ Đạt;finance heap cd25e1e Chưa đạt theo [review](review_6f59f5e.md),giao FH1–FH4 vòng1/2,không mở gate khác.
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
