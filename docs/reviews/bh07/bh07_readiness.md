# Hồ sơ readiness BH-07 — ma trận cổng và kế hoạch kiểm chứng

**Trạng thái: Chờ review độc lập. Tài liệu chỉ đọc/ghi docs, không phải nghiệm thu toàn BH-07, không cấp phép merge main, deploy, staging, production hoặc pilot.**

- Base của gói: `b91a350e619529d389af3edf6d4a06408af8d200`.
- Nhánh: `feat/bh07-readiness`.
- Phạm vi: tổng hợp cổng BH-07 đã có bằng chứng, tách rõ **Đạt local** với **NOT RUN**, và lập kế hoạch kiểm chứng phần còn thiếu.
- Không thay đổi app, backend, migration/RPC, contract, script kiểm chứng hoặc bằng chứng cũ trong gói này.
- Quy ước: **Đạt local** chỉ có giá trị trong phạm vi và môi trường được ghi ở từng review; không suy ra nghiệm thu toàn BH-07, không thay thế staging/production/pilot.

## 1. Kết luận điều hành

1. Các phần triển khai BH-07 A, B, C, D đã có kết luận **Đạt local** theo review độc lập, với source/tested SHA riêng.
2. Hai gói kiểm chứng HTTP/Auth và Concurrency HTTP/Auth đã **Đạt local** theo review độc lập; không thay thế kiểm thử tải, staging hoặc production.
3. Browser/Offline/Reopen và hai ca response Owner trả trễ đã **đóng công việc local**, nhưng kết luận cuối do Codex tự review/tự sửa, **không độc lập**. Đây là giới hạn phải giữ khi đọc ma trận.
4. Backup/restore cleanup R1 đã **Đạt local vòng 2/2**; review chốt có giới hạn độc lập với lịch sử tác giả. Đây là rehearsal local, không phải backup managed Supabase, PITR, offsite, encryption/retention hoặc restore staging/production.
5. **Toàn BH-07 chưa nghiệm thu.** Các cổng còn NOT RUN được liệt kê ở mục 3; kế hoạch kiểm chứng ở mục 4 chỉ là kế hoạch, không phải bằng chứng đã chạy.
6. Không có cơ sở để chuyển BH-08/BH-09, merge main, deploy hoặc mở pilot từ hồ sơ này. Git ref của các nhánh BH-07 được giữ nguyên.

## 2. Ma trận cổng BH-07

| Cổng | Phạm vi đã kiểm | Source/evidence chính | Kết luận và giới hạn |
|---|---|---|---|
| **A — DB/RPC/projection** | Complete/history/summary, gate quyền, công nợ sau complete, projection/ACL, idempotency/audit, dữ liệu nâng cấp | Tested `4512c3a19e7c22f2adc4a9f3269cbabe8acd9d09`; code/runner/migration `c339a47fdcb08e50811079bd89df7a1f9f53908a`; [review](review_4512c3a.md), [evidence](review_4512c3a_evidence/), [audit](bh07a_audit.md) | **Đạt local**, không P0/P1/P2 trong phạm vi. Reviewer tự chạy analyze sạch, 190 Flutter, 335/335 DB hồi quy, 23/23 BH-07, 7 tích hợp, 3 nâng cấp, 9 probe. **Giới hạn:** PostgreSQL cô lập/Auth stub; chưa có HTTP/JWT/Auth thật, UI, thiết bị, backup. |
| **B — model/repository/provider** | Contract A, loading/error/retry, summary/history, cache, isolation, response trễ | Review `d7bac04df0712ab37ab5568900ee2da60b95b612`; tested code `a682007f6cd85931b410ec2930fd40cdd3fc73f4`; base A `fd38838d85fed31603eae99ed363cf202650aeee`; [review](review_d7bac04.md), [evidence](review_d7bac04_evidence/) | **Đạt local**, đóng B1/B2 P2. Reviewer tự chạy analyze sạch, 212 Flutter, 335 DB, 23 BH-07, 7 tích hợp, 3 nâng cấp, 6/6 probe. **Giới hạn:** provider/repository mock tại ranh giới RPC; chưa chứng minh HTTP/RLS/token thật, UI, thiết bị. |
| **C — UI lịch sử/tổng kết/copy** | Lịch sử, filter/pagination/refresh/error, tổng kết theo quyền, copy an toàn, gate complete, ngày UTC+7 | Tested `02a9b857724e9ba031323ad732c90355d7932a39`; base `9b978467316d66c458846ac68c5de8021401fa0c`; [review](review_02a9b85.md), [evidence](review_02a9b85_evidence/), [log phụ lục](review_02a9b85_logs_3d5583b.md) | **Đạt local**, đóng C1/C2/C3 P2. Reviewer tự chạy analyze sạch, 230 Flutter, 57 targeted C dưới UTC và Asia/Ho_Chi_Minh, 23 DB, 5 probe mỗi múi giờ. **Giới hạn:** widget/VM, chưa browser/thiết bị thật; bảy log gốc chỉ được xác nhận bổ sung sau review. |
| **D — tích hợp local** | Start → điểm danh → chốt phí → complete → history/summary; lifecycle; retry/version; privacy; logout/đổi actor | Tested `3d590a8418157cf91b00b9a5503d09be4df069f3`; docs/evidence `ce4522da5dc6785a0487acd1ae19d3ff80014a0c`; [review](review_3d590a8.md), [evidence](review_3d590a8_evidence/), [bàn giao](bh07_integration_handoff.md) | **Đạt tích hợp local**, không P0/P1/P2 trong phạm vi. Reviewer tự chạy analyze sạch, 240 Flutter, 10 D và 50 C mỗi múi giờ, 23 DB, 6 probe. **Giới hạn:** repository mock tại ranh giới client/RPC; cash sau complete chỉ kiểm nút; chưa HTTP/ACL server, browser/mobile, banking. |
| **HTTP/Auth local** | GoTrue/PostgREST/Kong/PostgreSQL thật: auth, ACL, privacy, scope, complete, finance, summary/history; charge 0 và raw privacy | Tested `f9159dd483baf2dd219b2854fd8ab08d1e5f0330`; docs/evidence `0758b72197a4626bd02189c0402deda978fc69fe`; base `593bea86ffb807675387dba6b0276b555fdc87a1`; [review](review_f9159dd.md), [evidence](review_f9159dd_evidence/), [bàn giao](http_auth_handoff.md) | **Đạt local vòng 1/2**, đóng H1/H2 P2. Reviewer tự chạy 70/70 HTTP, analyze sạch, 240 Flutter +1 skip, 23 DB, 4 probe. **Giới hạn:** stack Linux riêng; không tái lập recipe Windows/full Supabase CLI; không gồm concurrency/tải, browser/device, banking, staging/production. |
| **Concurrency HTTP/Auth** | Idempotent replay, competing complete, cash no-overcollect, transport drop sau commit rồi retry | Tested `cbcc46c2e125b156b53f4297ef864cf658855d37`; docs/evidence `bb940280333aec96457dd3014aabba9f66adf4ae`; base thực tế `a0f831af47f98c7649e0c80dce4d5f13004a0db2`; [review](review_cbcc46c_r2.md), [evidence](review_cbcc46c_r2_evidence/), [bàn giao](http_concurrency_handoff.md) | **Đạt local vòng 2/2**, đóng H3/H4; H1/H2 giữ đóng. Reviewer tự audit 19/19 hash/encoding/metadata; kế thừa 76/76 HTTP, 240 Flutter +1 skip, 23 DB, 4 probe. **Giới hạn:** không chạy lại suite ở vòng 2/2; chưa có tải thật, nhiều máy, mạng thật hoặc DB production. |
| **Browser / Offline / Reopen** | Flutter Web trên Chromium thật: start→complete→history/summary; 4 actor; offline/retry; F5/reopen; logout/cache; SPA route | Baseline source `a6d58aff3f1726484146a6c89aa7d559bb684d6d`, tự review local; [self-review](self_review_a6d58af.md), [evidence](browser_evidence/), [closure](review_c4ce99b.md) | **Đạt local theo tự review/tự sửa, KHÔNG độc lập.** 11/11 browser, 12 ảnh khác hash, analyze sạch, 240 Flutter +1 skip, 23 DB; các control/mutant sau sửa PASS. **Giới hạn:** Chromium/SPA cụ thể; không mobile, browser khác, private Dart heap, deep link OS-level hoặc tải thật. |
| **Browser — response Owner trả trễ** | Owner→Cohost và Owner→Member khi response tài chính về sau login actor mới; privacy/copy/Cohost count-only/Member empty | Late source `c4ce99bcd9a9b02c4b794c8eb5ab51e43c06155a`; source sau sửa control `417ee30cf1fa2da4c64b03e0474d6c8c4a1dca6c`; [review](review_c4ce99b.md), [evidence](late_response_evidence/), [closure evidence](browser_closure_evidence/) | **Đạt local theo tự review/tự sửa, KHÔNG độc lập.** 2/2 ca UI, 21 control +2 mutant, 41 regression, 9 probe, 9 verifier, manifest 52/44 PASS; kế thừa 11 baseline +2 late. **Giới hạn:** chỉ hai lịch trễ cụ thể; không đo private Dart heap; không mobile/browser khác; không bảo đảm mọi cache/RPC/race. |
| **Backup/restore local** | Rehearsal cô lập: source stack, dump/restore PostgreSQL/Auth, ACL/replay smoke, cleanup fail-closed, manifest readonly | Source `282f978ba2afaa58e3f5810f282bdfd0febf334d`; docs/evidence `986baac29d506282740f477a5fb5ba94e15c496b`; base review `f216ae1fb220f140b091abd5acd2969333ec7f53`; [review](review_282f978.md), [evidence](backup_restore_cleanup_r2_evidence/), [runbook](../../26_BH07_OPERATIONS_REHEARSAL.md) | **Đạt local vòng 2/2**, đóng R1 cleanup. Reviewer tự chạy 14/14 control, 13/13 rehearsal Linux, analyze sạch, 240 Flutter +1 skip, 23 DB, manifest 16/16 readonly. **Giới hạn:** review không hoàn toàn độc lập với lịch sử tác giả; local Docker/PostgreSQL fixture; không managed Supabase/PITR/offsite/encryption/retention, concurrent writers, staging/production/restore thật. |
| **Hồ sơ readiness (tài liệu này)** | Ma trận cổng, phân biệt local/NOT RUN, kế hoạch kiểm chứng, cập nhật điểm tiếp tục | Base `b91a350e619529d389af3edf6d4a06408af8d200`; nhánh `feat/bh07-readiness` | **Chờ review độc lập**, không tự ghi Đạt. Không có bằng chứng runtime mới; chỉ là tài liệu quyết định. |
| **Toàn BH-07 / pilot** | Nghiệm thu toàn bộ cổng, staging/production, thiết bị, tải, pilot | Chưa có bằng chứng đầy đủ | **NOT RUN / chưa nghiệm thu.** Không được suy từ bất kỳ dòng “Đạt local” phía trên. |

## 3. Phân biệt Đạt local với NOT RUN

### 3.1. Những gì đã có bằng chứng local

- **A/B/C/D:** code, migration/RPC, provider và UI đã được review theo từng phần; regression local và DB cô lập đã chạy.
- **HTTP/Auth:** đã có token/JWT/PostgREST/GoTrue thật trên stack Linux cô lập, không dùng mock Auth cho assertion HTTP.
- **Concurrency HTTP:** đã có replay/competition/drop-response trên stack HTTP local.
- **Browser:** đã có Flutter Web + Chromium + Supabase local, thao tác UI thật và control âm; kết luận cuối không độc lập.
- **Backup/restore:** đã có rehearsal local cô lập, restore DB/Auth, smoke ACL/replay và cleanup fail-closed.

### 3.2. Những gì vẫn NOT RUN

| Cổng còn thiếu | Vì sao chưa thể coi là Đạt | Bằng chứng cần có trước khi đóng |
|---|---|---|
| Review độc lập gói Browser/response trễ | Kết luận cuối do Codex tự review/tự sửa | Reviewer độc lập tự chạy lại baseline, 2 ca trễ, control/mutant, kiểm privacy/ACL và provenance |
| Mobile iOS/Android thật | Chưa có thiết bị/emulator được nghiệm thu | Build thật, thao tác start→complete→history, offline/reopen, deep link, không rò dữ liệu |
| Browser khác/OS khác | Chỉ có Chromium/SPA cụ thể | Chrome/Firefox/Safari/Edge trên desktop/mobile, tối thiểu matrix đã chốt |
| Offline/reopen/deep link ngoài phạm vi browser đã chạy | Chưa kiểm OS-level, cold start, link trước/sau login | Kịch bản mất mạng, retry cùng intent, F5/cold start, deep link và logout |
| Đo private Dart heap/cache | Chưa đo trực tiếp; chỉ suy từ UI/copy và unit guard | Phép đo heap/cache hoặc phân tích memory có phương pháp, lặp lại được |
| Managed Supabase backup | Chỉ rehearsal PostgreSQL/Auth local | Backup project managed, Storage/Edge/Realtime/external secrets, restore sang project cô lập |
| PITR/offsite/encryption/retention | Chưa cấu hình/chứng minh trên managed service | Bằng chứng PITR, offsite copy, encryption at rest/in transit, retention/rotation và test restore |
| Backup với concurrent writers | Rehearsal dừng writer trước snapshot | Backup dưới tải ghi đồng thời, kiểm tính nhất quán và committed data |
| Staging/production restore thật | Chưa chạy restore/deploy ngoài local | Restore staging trước, sau đó production chỉ khi có phê duyệt riêng; smoke HTTP/ACL/app |
| Full Supabase reset từ migration | Chưa dựng lại toàn bộ DB local/staging từ zero trong gói này | Project sạch, migration + seed, 23 DB + HTTP smoke, reset lặp lại được; xóa project test |
| Banking/VietQR/webhook thật | Ngoài phạm vi BH-07 hiện hành và chưa có sandbox evidence | Sandbox bank/webhook, idempotency, signature, reconciliation; không dùng tiền thật |
| Rehearsal tải thật/pilot | Chưa có tải production-like hoặc người dùng pilot | SLO/RTO/RPO, kịch bản lỗi, rollback drill, dữ liệu ẩn danh và sign-off |
| Nghiệm thu toàn BH-07 | Chưa có ma trận đầy đủ với mọi cổng PASS | Tất cả cổng bắt buộc PASS hoặc residual risk được chủ dự án chấp nhận bằng văn bản |

## 4. Kế hoạch kiểm chứng phần còn thiếu

**Không chạy các bước dưới đây trong lượt này.** Mỗi cổng phải có biên bản riêng, source/full SHA, lệnh/exit/count, môi trường, người phụ trách và kết luận của reviewer độc lập. Không dùng production làm môi trường thử.

### 4.1. R0 — Review hồ sơ readiness

- **Môi trường/đầu vào:** checkout sạch `feat/bh07-readiness`; base `b91a350`; tài liệu này và các tài liệu trạng thái đã cập nhật.
- **Phụ trách:** reviewer độc lập (Codex); chủ dự án quyết định kết luận.
- **PASS:** link và SHA resolve; không có diff app/backend/migration/script; mọi “Đạt local” có review/evidence; NOT RUN không bị che; không có tuyên bố nghiệm thu toàn BH-07; stale status đã được đánh dấu lịch sử.
- **FAIL:** sai SHA/link, gán sai mức độ độc lập, bỏ sót cổng, hoặc ngụ ý deploy/pilot.
- **Rollback:** revert commit docs trên nhánh; không đụng source/evidence cũ.

### 4.2. V1 — Review độc lập Browser/Offline/Reopen và response trễ

- **Môi trường/đầu vào:** checkout sạch source `417ee30` (sau sửa control) và `c4ce99b` cho hai ca trễ; Flutter Web + Chromium + Supabase local; tài khoản Owner/Cohost/Member/Finance; manifest và control đã công bố.
- **Phụ trách:** reviewer độc lập/QA; người triển khai chỉ hỗ trợ tái lập, không tự chốt.
- **PASS:** 11/11 baseline + 2/2 ca trễ; 21 control và mutant đúng; offline/retry giữ cùng `request_id`; Cohost count-only/copy an toàn; Member empty/không summary-copy; không lộ contact/bank/secret; ảnh/log/hash khớp.
- **FAIL:** có success giả, rò dữ liệu, duplicate operation/audit, control âm bị bỏ qua, manifest thiếu/hash sai hoặc kết luận dựa vào log tác giả.
- **Rollback:** dừng phiên, giữ nguyên Git ref và evidence; không sửa app/backend để làm test xanh; đóng gói evidence review riêng.

### 4.3. V2 — Mobile/device, browser khác, offline/reopen/deep link

- **Môi trường/đầu vào:** ít nhất một thiết bị iOS và một Android thật (hoặc emulator được chủ dự án chấp thuận), cùng desktop Chrome/Firefox/Safari/Edge; API local/staging; build có ký/không ký theo môi trường; tài khoản test.
- **Phụ trách:** QA mobile/web; reviewer độc lập kiểm mẫu.
- **PASS:** start→điểm danh→chốt phí→complete→history/summary; mất mạng hiện lỗi thật, retry cùng intent; F5/cold start/reopen giữ phiên; deep link trước/sau login; logout/đổi actor không lộ dữ liệu; copy/QR fallback đúng.
- **FAIL:** crash, màn trắng, success giả, mất operation, rò dữ liệu actor/CLB, hoặc không mở được deep link.
- **Rollback:** gỡ build test, giữ dữ liệu test cô lập; không deploy store/production.

### 4.4. V3 — Managed Supabase backup, PITR, offsite, encryption, retention

- **Môi trường/đầu vào:** project managed **staging** (không production), project restore cô lập; cấu hình backup/PITR/retention; Storage/Edge/Realtime/external secrets; credential scoped; dataset và mốc thời gian đã biết.
- **Phụ trách:** infra/DBA + reviewer độc lập; chủ dự án phê duyệt cửa sổ và target.
- **PASS:** restore được sang project cô lập; row count/checksum khớp; Auth/ACL/RPC smoke qua HTTP; PITR chọn đúng mốc; offsite/encryption/retention có bằng chứng cấu hình và kiểm tra; không lộ secret.
- **FAIL:** không restore được, thiếu PITR/offsite, dữ liệu lệch, mã hóa/retention không được enforce, hoặc thao tác chạm production.
- **Rollback:** xóa project/snapshot tạo cho test; không thay đổi backup policy production; ghi rõ nếu test chưa chạy.

### 4.5. V4 — Backup với concurrent writers

- **Môi trường/đầu vào:** DB staging-like, hai hoặc nhiều writer thật (HTTP/PostgREST), backup chạy đồng thời; workload và expected invariants; không dùng production.
- **Phụ trách:** backend/infra + QA.
- **PASS:** backup nhất quán tại mốc chọn; committed transaction không mất; không duplicate/lost payment, ledger, audit; restore kiểm lại invariant; cleanup sạch.
- **FAIL:** mất dữ liệu committed, vi phạm FK/unique, backup treo quá ngưỡng hoặc restore tạo duplicate.
- **Rollback:** dừng writer/tải, hủy bản backup test, restore snapshot trước test; không đụng production.

### 4.6. V5 — Staging/production restore và deploy

- **Môi trường/đầu vào:** staging trước; production chỉ sau phê duyệt riêng; release candidate, restore point, runbook, smoke test, snapshot rollback; nếu được giao, chạy full Supabase reset từ migration trên project sạch.
- **Phụ trách:** release owner + infra + reviewer; chủ dự án phê duyệt production.
- **PASS:** restore/deploy hoàn tất trong cửa sổ; app/HTTP/ACL/RPC smoke PASS; count/invariant khớp; RTO/RPO thực đo và ghi lại; rollback đã thử.
- **FAIL:** lệch dữ liệu, auth/ACL lỗi, quá cửa sổ, không rollback được hoặc có truy cập ngoài phạm vi.
- **Rollback:** khôi phục snapshot trước restore, redeploy build trước, tắt traffic nếu chưa chắc; giữ nguyên chứng cứ.

### 4.7. V6 — Banking/VietQR/webhook (ngoài phạm vi BH-07 hiện hành)

- **Môi trường/đầu vào:** sandbox ngân hàng, tài khoản test, webhook sandbox, payload ký, dataset đối soát; không dùng tiền thật.
- **Phụ trách:** finance/integration owner + reviewer.
- **PASS:** QR/trạng thái thanh toán đúng; webhook idempotent, kiểm signature, retry không duplicate; ledger/đối soát khớp; không lộ secret.
- **FAIL:** duplicate/lost payment, nhận webhook sai chữ ký, lệch ledger, hoặc phát sinh giao dịch tiền thật.
- **Rollback:** tắt webhook/keys sandbox, đảo giao dịch test, không deploy production.
- **Lưu ý:** chỉ mở khi chủ dự án mở rộng phạm vi; không tự thêm vào BH-07.

### 4.8. V7 — Rehearsal tải thật và pilot

- **Môi trường/đầu vào:** staging với dữ liệu ẩn danh production-like; load generator; kịch bản start/complete/payment/history/summary; SLO, RTO/RPO, rollback drill; nhóm pilot giới hạn.
- **Phụ trách:** chủ dự án + ops + QA + reviewer độc lập.
- **PASS:** SLO đạt, không P0/P1, không mất/duplicate dữ liệu, privacy/ACL đúng, rollback drill thành công, support và thông báo pilot sẵn sàng.
- **FAIL:** vượt ngưỡng, lỗi dữ liệu, rò quyền, không rollback được hoặc thiếu người trực.
- **Rollback:** dừng pilot, rollback release/snapshot, thông báo người dùng, giữ log và quyết định.

### 4.9. V8 — Nghiệm thu toàn BH-07

- **Môi trường/đầu vào:** toàn bộ báo cáo/evidence của V1–V7 và ma trận này; không chạy lại nếu không cần, nhưng phải chỉ rõ bằng chứng kế thừa.
- **Phụ trách:** chủ dự án + reviewer độc lập.
- **PASS:** mọi cổng bắt buộc có kết luận PASS hoặc residual risk được chấp nhận bằng văn bản; không P0/P1; NOT RUN đã đóng hoặc được chấp nhận; sign-off rõ.
- **FAIL:** còn cổng NOT RUN, evidence không tái lập, xung đột SHA/verdict hoặc có P0/P1.
- **Rollback:** giữ ref chưa merge, không deploy; mở lại kế hoạch và giao đúng phần còn thiếu.

## 5. Thứ tự thực hiện đề xuất

1. **R0:** review hồ sơ này, chốt các trạng thái và điểm tiếp tục.
2. **V1:** review độc lập browser/response trễ — rủi ro cao nhất vì kết luận hiện tại không độc lập.
3. **V3/V4:** managed backup/PITR/retention và concurrent writers — cổng vận hành còn trống lớn nhất.
4. **V5:** staging restore/deploy; production chỉ sau phê duyệt riêng.
5. **V2:** mobile/browser khác/offline/deep link — có thể chạy song song V3/V4 nếu đủ thiết bị.
6. **V6:** banking/webhook chỉ khi mở rộng phạm vi.
7. **V7:** load rehearsal/pilot.
8. **V8:** nghiệm thu toàn BH-07.

## 6. Rủi ro và biện pháp

| Rủi ro | Tác động | Biện pháp |
|---|---|---|
| Đọc “Đạt local” thành “Đạt BH-07” | Merge/deploy/pilot sớm | Giữ nhãn **local** và bảng NOT RUN ở mọi tài liệu trạng thái; reviewer kiểm lại |
| Browser final không độc lập | Bỏ sót lỗi privacy/retry/ACL | V1 bắt buộc reviewer độc lập tự chạy lại, không dựa log tác giả |
| Backup local không đại diện managed Supabase | Mất dữ liệu/PITR khi sự cố thật | V3/V4 trên managed staging và restore cô lập trước production |
| Stale “Chờ review” trong tài liệu | Hiểu sai điểm tiếp tục | Đánh dấu lịch sử, cập nhật đầu docs/00, 09, 25, 26, AGENTS, README, STATUS_HISTORY và handoff backup/restore |
| Môi trường Linux/Windows khác nhau | Kết quả không tái lập | Ghi rõ stack, lệnh, exit; không tuyên bố recipe chưa chạy là PASS |
| Scope creep sang BH-08/BH-09/banking | Trộn cổng, tăng rủi ro | Chỉ mở khi chủ dự án giao; giữ ngoài ma trận BH-07 hiện hành |

## 7. Đối chiếu SHA đầy đủ

| Mốc | SHA đầy đủ | Ghi chú |
|---|---|---|
| Base readiness | `b91a350e619529d389af3edf6d4a06408af8d200` | Review chốt backup/restore local |
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
| Browser — baseline | `a6d58aff3f1726484146a6c89aa7d559bb684d6d` | Tự review local |
| Browser — response trễ | `c4ce99bcd9a9b02c4b794c8eb5ab51e43c06155a` | Hai ca UI local |
| Browser — control fix | `417ee30cf1fa2da4c64b03e0474d6c8c4a1dca6c` | Sửa negative control |
| Browser — closure docs | `74305bb343fbaf548cb5eea38a77475cc3a21b39` | Đóng nhánh browser |
| Backup — tested | `282f978ba2afaa58e3f5810f282bdfd0febf334d` | Cleanup R1 vòng 2/2 |
| Backup — docs/evidence | `986baac29d506282740f477a5fb5ba94e15c496b` | Review chốt local |
| Backup — base review | `f216ae1fb220f140b091abd5acd2969333ec7f53` | Review R1 vòng 1/2 |

## 8. Kiểm tra tính nhất quán trong lượt này

- Base/current branch: `feat/bh07-readiness`, tách từ `b91a350`; không merge main, không deploy, không chạy staging/production/pilot.
- `git diff --stat b91a350` chỉ được chứa tài liệu; không có thay đổi `lib/`, `test/`, `supabase/`, `scripts/` hoặc evidence cũ.
- Các SHA nêu trong mục 7 được kiểm bằng `git rev-parse`/`git cat-file` trong lượt này.
- Ngoài mục 7, `docs/25` còn giữ SHA lịch sử `a0f831ae3f47e305608bfa0dff19ae035b31f798` đã được đính chính thành `a0f831af47f98c7649e0c80dce4d5f13004a0db2`; không dùng SHA cũ làm base.
- Link tương đối trong tài liệu này và các link trạng thái được kiểm bằng script đọc Markdown; đường dẫn evidence cũ giữ nguyên.
- Trạng thái hiện hành được cập nhật ở `AGENTS.md`, `README.md`, `docs/00_START_HERE.md`, `docs/09_IMPLEMENTATION_PLAN.md`, `docs/25_BH07_IMPLEMENTATION_HANDOFF.md`, `docs/26_BH07_OPERATIONS_REHEARSAL.md`, `docs/STATUS_HISTORY.md`; các mục “Chờ review” cũ được đánh dấu lịch sử.
- Không có kết quả runtime mới trong gói docs-only này; mọi số test trong ma trận là số kế thừa từ review/evidence tương ứng, không phải lần chạy mới.

## 9. Tài liệu liên quan

- [Đầu bài BH-07 và các cổng A/B/C/D](../../25_BH07_IMPLEMENTATION_HANDOFF.md)
- [Runbook vận hành/backup local](../../26_BH07_OPERATIONS_REHEARSAL.md)
- [Kế hoạch triển khai và trạng thái](../../09_IMPLEMENTATION_PLAN.md)
- [Điểm bắt đầu](../../00_START_HERE.md)
- [Lịch sử trạng thái](../../STATUS_HISTORY.md)
- [Review backup/restore local](review_282f978.md)
- [Review Browser/response trễ](review_c4ce99b.md)
