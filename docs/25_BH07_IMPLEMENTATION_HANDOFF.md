**Hiện hành 25/10/2026 — V5b Full Supabase CLI reset Đạt local, đã đóng công việc local**, tested source `8c107e9692b89f4a0aadeafc0ae139736f9b2622`, QA/docs `b036e9e65c3065e90454a6e645960599e633757b`, base thực tế `a55c2d2416f37a0bb8ac985e80bdee579b40774b`, theo [review chốt](reviews/bh07/review_b036e9e.md). Đóng H6, giữ H1–H5/R1/R2/R3/R5/P2-1..P2-7; không còn P0/P1/P2 mở trong phạm vi. Reviewer tự chạy21/21 Python, analyze0 issue,240 Flutter+1skip,17/17 strict readonly; audit bundle QA2 reset×18 migrations,23 assertion/chu kỳ,HTTP/Auth,Oracle48 bảng schema+số dòng vàcleanup PASS. Full CLI reviewer rerun NOT RUN do thiếu đĩa; kết quả runtime là QA được audit, không đổi thành lần chạy reviewer. Codex từng sửa baseline, giới hạn độc lập được công bố. V1 giữ Đạt local; các cổng V2/V2b/V3/V4/V5/V6/V7/V8 giữ NOT RUN; toàn BH-07 chưa nghiệm thu. Giữ nhánh chưa merge, không merge main/staging/production/deploy/pilot/BH-08.

# BH-07 — buổi hoàn chỉnh, lịch sử, tổng kết và pilot

**(Lịch sử trước chốt V5b) Theo ủy quyền bổ sung “giao reviewer sửa”, Codex đã sửa trực tiếp R1/R2 tại `8e26e06`**, base `6a13901`; [bàn giao tự kiểm](reviews/bh07/codex_v5b_fix_handoff.md). Codex tự sửa/tự kiểm, **KHÔNG phải review độc lập**. Inventory sau start lỗi/trống bị chặn trước reset; mỗi run dùng project UUID riêng; gateway chỉ nhận tuple đã whitelist.11/11 tests,14 scenario controls và3 mutant gates đúng;analyze sạch,240 Flutter+1skip. Evidence cũ12/10/8/8 verify readonly không đổi. **V5b Chờ kiểm chứng sau bản sửa trực tiếp; full CLI runtime source8e26e06 NOT RUN do thiếu đĩa**, không retag evidence runtime cũ. Đây là ủy quyền trực tiếp sau dừng hai vòng,không tự mở vòng3. V1 giữ Đạt local; toàn BH-07 chưa nghiệm thu,các cổng khác giữ NOT RUN. Không merge main/staging/production/deploy/pilot/BH-08.

**(Lịch sử dừng trước ủy quyền trực tiếp) V5b Chưa đạt vòng2/2 tại `3b515f2` — DỪNG theo AGENTS**, docs/evidence `5df6c62`, theo [review chốt](reviews/bh07/review_3b515f2.md). Còn1 P1 R1 (owned inventory sau start lỗi vẫn reset) và1 P2 R2 (gateway variant nhận code SQL ngoài whitelist). Đóng R3/R5, giữ R4 packaging/count/trung thực dirty; runtime tác giả là b4b1f9f dirty source/tests, không tự gán thành clean3b515f2. Reviewer tự chạy8/8 tests,mutant suite8 test bắt3 FAIL,analyze sạch,240 Flutter+1skip,manifest12/12 readonly vàAST probes. Full CLI runtime NOT RUN do thiếu đĩa. **Không tự mở vòng3/sửa source; báo chủ dự án quyết định bước tiếp.** Giữ V1 Đạt local; toàn BH-07 chưa nghiệm thu,các cổng khác giữ NOT RUN. Không merge main/staging/production/deploy/pilot/BH-08.

**(Lịch sử review vòng1/2) V5b reset local Chưa đạt bản sửa vòng1/2 tại `19ab207`**, docs origin thực tế `e53f9944d3d599cf4183dfdbfb7d206306bb8e23`, theo [review](reviews/bh07/review_19ab207.md). **Đóng R4**:manifest12/12,đủ48 bảng/cycle,23 assertion vàdirty files trung thực. **Còn1 P1 R1 và3 P2 R2/R3/R5**:Docker returncode bị bỏ qua/ownership cleanup,positive giả +error-domain quá rộng,final inspect fail-open/che primary error,test không kiểm hành vi. Reviewer tự chạy tests4/4,analyze sạch,240 Flutter+1skip vàAST fault/mutant probes; full CLI runtime NOT RUN vìhost chỉ còn khoảng661MB. Giao AI triển khai sửa R1–R3/R5 vòng2/2; không sửa source trong vai reviewer. Giữ V1 Đạt local; toàn BH-07 chưa nghiệm thu; các cổng khác giữ NOT RUN. Không merge main/staging/production/deploy/pilot/BH-08.

**V5b Full Supabase CLI reset local: Chưa đạt tại source `0392e21`**, review ngày24/10/2026 theo [review](reviews/bh07/review_0392e21.md). Docs/evidence origin thực tế `c3cda7108809037ee884ca9c769a7264f13a9530` (SHA dài trong yêu cầu không tồn tại). Còn1 P1 về ownership trước reset/stop và3 P2 về negative error codes,cleanup vàevidence/provenance:manifest thiếu7/12 log. Reviewer tự chạy CLI2.122.0 trong worktree sạch nhưng start fail do hết đĩa,0 reset cycle hoàn tất; không coi log tác giả là kết quả reviewer. Probe AST tái hiện faults; không sửa source. **Giữ V1 Đạt local; toàn BH-07 chưa nghiệm thu.** Giao AI triển khai sửa R1–R4, chưa đóng V5b/chuyển bước kế; không merge main/staging/production/deploy/pilot/BH-08.

**V1 Browser/Offline/Reopen và response Owner trả trễ Đạt local, đã chốt điều phối ngày24/10/2026**, reviewer tested `6283dbb`, report/evidence `448c50f`, theo [chốt V1](reviews/bh07/v1_acceptance_448c50f.md) và [review độc lập](reviews/bh07/review_6283dbb.md). Điều phối verify52/52,44/44,48/48 readonly, đối chiếu source/hash/driver recipe và kết quả reviewer11 baseline+2late,41negative,21+2mutant,9verifier. Codex điều phối từng sửa baseline, không gọi lượt chốt này là review UI độc lập mới; bằng chứng V1 mới do reviewer/QA khác chạy. Giữ lịch sử browser tự review không độc lập. **Toàn BH-07 chưa nghiệm thu.** V2/V2b/V3/V4/V5/V5b/V6/V7/V8 giữ NOT RUN; không merge main/staging/production/deploy/pilot/BH-08. Điểm tiếp đề xuất giao AI triển khai V5b full reset trên project local test sạch, không môi trường dùng chung.

**(Lịch sử chốt readiness 23/10/2026) Hồ sơ readiness BH-07 Đạt docs-only vòng2/2 tại `31fced4`**, đóng R1–R4 theo [review chốt](reviews/bh07/review_31fced4.md). Reviewer kiểm406 link,31 SHA mục7,13/13 dòng NOT RUN map kế hoạch; diff9 file docs-only, whitespace sạch. Không chạy runtime mới, không đổi verdict/evidence cũ; Browser final vẫn không độc lập, backup giữ giới hạn lịch sử tác giả. **Toàn BH-07 chưa nghiệm thu.** Điểm tiếp: giao V1 cho reviewer/QA không tham gia sửa Browser tự kiểm baseline/response trễ local; không phải mở lại sửa readiness. Các cổng V1–V8 chưa chạy giữ NOT RUN; acceptance không biến test thành PASS. Không merge main/deploy/pilot/BH-08.

**(Lịch sử bàn giao trước chốt) Hồ sơ readiness BH-07 (docs-only) đang Chờ review độc lập vòng 2/2 sau sửa R1–R4 theo review bc63673**, base review `fdf7113ff46517a4c148fbcfcce5fea960686481` (base gốc `b91a350`), nhánh `feat/bh07-readiness`; ma trận cổng, tách Đạt local/NOT RUN và kế hoạch kiểm chứng tại [hồ sơ](reviews/bh07/bh07_readiness.md). Không nghiệm thu toàn BH-07, không merge main/deploy/pilot, không tự chuyển BH-08; các cổng NOT RUN chỉ mở khi chủ dự án giao và có môi trường được phép.

**(Lịch sử 23/10/2026 — accepted backup/restore local)** **Backup/restore cleanup R1 Đạt local vòng2/2 — đã đóng công việc backup/restore local**, source `282f978`, docs/evidence `986baac`, theo [review chốt](reviews/bh07/review_282f978.md). Codex tự chạy14/14 control,13/13 rehearsal Linux,analyze sạch,240 Flutter+1skip,23/23 DB,manifest16/16 readonly; inspect context/daemon/permission/transport và cleanup lỗi đều bị chặn, không còn P0/P1/P2 mở trong phạm vi. Probe reviewer cũ giữ nguyên exit1 do assertion lịch sử; output thực xác nhận context đã bị chặn. Không đổi app/backend/source triển khai trong review; evidence cũ giữ nguyên. **Giữ Git ref chưa merge, không merge main/deploy/pilot.** Toàn BH-07 chưa nghiệm thu; managed Supabase/PITR/offsite/encryption/retention,concurrent writers,staging/production/restore thật,browser/device ở lượt này,banking/webhook,rehearsal tải thật/pilot vẫn NOT RUN. **Sau bước này, hồ sơ readiness BH-07 (docs-only) đã được lập và đang Chờ review; không chạy môi trường thật hoặc tự chuyển BH-08.**

**(Lịch sử bàn giao trước chốt) R1 cleanup vòng2/2: Chờ review độc lập tại source `282f978`.** Base review `f216ae1`, nhánh `feat/bh07-backup-rehearsal`; evidence mới `reviews/bh07/backup_restore_cleanup_r2_evidence/`. Người triển khai tự kiểm, **không phải review độc lập**. `resource_present` chỉ chấp nhận thông báo vắng mặt đúng kind/tên; lỗi context/daemon/permission/transport đều ghi cleanup error, FAIL/exit1, không xóa mù. Probe14/14 control (5 cũ + inspect trước/sau remove, network remove failure, remove trả0 còn resource), rehearsal thật13/13 exit0, analyze sạch,240 Flutter+1skip,23/23 DB, manifest16/16 verify readonly PASS. Probe reviewer giữ nguyên file exit1 do assertion cũ yêu cầu false success; output chứng minh lỗi context đã bị chặn. Chưa đóng backup/restore/chuyển bước kế; browser giữ Đạt local. Không merge main/deploy/pilot.

**(Lịch sử) Review R1 vòng1/2 tại `6d00e9c` Chưa đạt P2**: inspect Docker context bị nhận nhầm resource vắng mặt, không gọi rm nhưng vẫn PASS/exit0. [Kết luận](reviews/bh07/review_6d00e9c.md). Evidence cũ giữ nguyên. [Runbook](26_BH07_OPERATIONS_REHEARSAL.md), [bàn giao](reviews/bh07/backup_restore_handoff.md). Bàn giao ban đầu tại `b626a78` từ base browser `74305bb`, tự kiểm không độc lập: 13/13 recovery, analyze sạch,240 Flutter+1skip,23/23 DB,manifest11/11; sau đó review độc lập mở R1 P2 về cleanup.

> **(Lịch sử) 23/10/2026:** Gói **Browser / Offline / Reopen và response Owner trả trễ BH-07 Đạt local, đã đóng công việc trên nhánh `feat/bh07-browser-verification`** theo yêu cầu chủ dự án. Codex review/tự sửa, **không độc lập**; [kết luận](reviews/bh07/review_c4ce99b.md). Source browser trễ `c4ce99b`, source control chốt `417ee30`; đã sửa2 P2 về negative control bị lỗi khác che,21 control và2 mutant riêng PASS;41 regression,9 probe,9 verifier,manager mutant vàmanifest52/44 PASS. Kế thừa analyze sạch,240 Flutter+1skip,11 baseline+2 late browser trên app/driver/helper không đổi; không giả thành lần chạy mới. Không còn P0/P1/P2 mở trong phạm vi local được giao; không mở vòng Chờ review tiếp. **Giữ Git ref chưa merge; không xóa/merge main/deploy.** App/backend/contract và evidence cũ giữ nguyên. Toàn BH-07/production/pilot chưa nghiệm thu; private Dart heap/mobile/browser khác/banking/webhook/staging/production/backup/rehearsal/pilot vẫn có giới hạn/NOT RUN. **Chủ dự án đã giao tiếp bước kế: tài liệu vận hành và backup/restore rehearsal local cô lập**, trên nhánh mới; không production/pilot.

> **(Lịch sử bàn giao trước chốt browser)** Gói **kiểm chứng response tài chính Owner trả trễ sau đổi actor BH-07 Chờ review**, source `c4ce99bcd9a9b02c4b794c8eb5ab51e43c06155a`, base `1ed4f3e6b42b853f51add79279fe3daf8168e360`. Codex triển khai/tự kiểm, **không độc lập**. Hai ca UI thật cùng SPA **Owner→Cohost và Owner→Member PASS**: giữ POST summary200 khoảng44,7/40,5 giây, thả sau login actor mới, delivered body hash trùng, timeOrigin không đổi; Cohost vẫn count-only/copy an toàn,Member empty/không summary-copy. **21 control mới**,41 control cũ,11 browser baseline,analyze sạch,240 Flutter+1skip,44/44 manifest. Không thấy lỗi app ở bề mặt đã thử; chưa tự ghi Đạt cho gói mới. [Bàn giao](reviews/bh07/late_response_handoff.md). Private Dart heap không đo trực tiếp;giữ unit cache guard bổ sung và nêu giới hạn. Không đổi app/unit/backend/contract. Giữ Browser trước Đạt tự review local cùng A/B/C/D/HTTP/Auth/concurrency; toàn BH-07/production/pilot chưa nghiệm thu. Review độc lập,mobile/browser khác,banking/webhook,staging/production/backup,rehearsal/pilot vẫn NOT RUN. Không merge/apply DB thật/deploy/chuyển pilot.

> **(Lịch sử kết luận browser trước gói response trễ)** Gói **Browser / Offline / Reopen BH-07 Đạt theo Codex tự review local**, source `a6d58aff3f1726484146a6c89aa7d559bb684d6d`, evidence `994ebfeb98c7c76815c2b8e0e6519fbe735ab1af`, theo [kết luận tự review](reviews/bh07/self_review_a6d58af.md). Chủ dự án yêu cầu trực tiếp tự review và chốt; **KHÔNG phải review độc lập**. Đóng BR3-1/BR3-2/BR3-3 theo tự review; không có P0/P1/P2 còn mở trong phạm vi được giao. Phát lại9 probe,41 negative,9 verifier,mutant và52/52 manifest đều đúng; kế thừa tự kiểm cùng SHA: analyze sạch,240 Flutter+1skip,23 DB,11 browser,12 ảnh khác hash. Chỉ3 script kiểm chứng đổi; app/backend/contract và bằng chứng cũ giữ nguyên. **Toàn BH-07/production/pilot chưa nghiệm thu.** Review độc lập, mobile/browser khác, response trễ sau đổi actor, banking/webhook, staging/production/backup, rehearsal/pilot và full Supabase reset vẫn NOT RUN. Không merge/apply DB thật/deploy/chuyển pilot.

> **(Lịch sử bàn giao Codex trước tự review)** Gói **Browser / Offline / Reopen BH-07 Chờ review độc lập sau Codex tự sửa/tự kiểm**, tested source `a6d58aff3f1726484146a6c89aa7d559bb684d6d`, base `1fc7e2eb171acd6c7afbc16e9f1053f9b3cb21c3`. Chủ dự án giao trực tiếp Codex sửa **BR3-1/BR3-2/BR3-3** sau review `02cd0ed`; Codex bổ sung whitelist Manager, guard tiền Unicode và status/body/privacy lịch sử. **KHÔNG phải review độc lập; chưa tự ghi Đạt hay xác nhận đóng P2.** Tự chạy analyze sạch, **240 Flutter +1 skip**, **23 DB**, **11/11 browser**, **9/9 probe cũ giữ nguyên kỳ vọng**, **41/41 negative**, **9/9 verifier readonly**, mutant PASS, **52/52 manifest**; checkout browser sạch. [Bàn giao](reviews/bh07/browser_codex_fix_handoff.md). Chỉ3 script kiểm chứng thay đổi; giữ gate BR1/BR2/BR4/BR5, app/unit test/backend/contract và bằng chứng cũ. Giữ A/B/C/D và HTTP/Auth/concurrency Đạt local; toàn BH-07/pilot chưa nghiệm thu. Mobile/browser khác, response trễ sau đổi actor, banking/webhook, staging/production/backup, rehearsal/pilot và full Supabase reset vẫn NOT RUN. Không merge/apply DB thật/deploy/chuyển pilot.

> **(Lịch sử review lần sửa cuối)** Gói **Browser / Offline / Reopen BH-07 Chưa đạt lần sửa cuối theo ủy quyền bổ sung** tại source `a62f509986f65592da3fb5bccebe7b7c246ff7b7`, docs/evidence `02cd0edbb9b1f77213c6788474984686895e125c`, theo [review độc lập](reviews/bh07/review_02cd0ed.md). **Đóng BR2/BR5; BR3 còn ba P2**: field tiền lạ của Manager, regex VNĐ/đ của Cohost và gate response/privacy lịch sử Member. Reviewer tự chạy analyze sạch, **240 Flutter +1 skip**, **23 DB**, **11/11 browser**, **27/27 negative**, **9/9 verifier readonly**, mutant PASS, **33/33 manifest**; nhưng **5 negative input bổ sung bị nhận PASS sai**, cùng4 positive baseline đúng. Giữ BR1 và ca SPA BR4; app/backend không đổi. **Bàn giao phần sửa kiểm chứng còn lại cho Codex theo ủy quyền chủ dự án; kết quả Codex tự sửa/tự kiểm phải ghi không độc lập. Lượt review này không sửa triển khai.** Giữ A/B/C/D và HTTP/Auth/concurrency Đạt local; toàn BH-07/pilot chưa nghiệm thu. Mobile/browser khác, response trễ sau đổi actor, banking/webhook, staging/production/backup, rehearsal/pilot và full Supabase reset vẫn NOT RUN. Không merge/apply DB thật/deploy.

> **(Lịch sử bàn giao lần sửa cuối)** Gói **Browser / Offline / Reopen BH-07 đang ở trạng thái Chờ review lần sửa cuối theo ủy quyền bổ sung** tại source `a62f509986f65592da3fb5bccebe7b7c246ff7b7`, theo [bàn giao](reviews/bh07/browser_handoff.md). BR1 và ca SPA BR4 giữ nguyên; đã bổ sung gate cho BR2/BR3/BR5 P2: lỗi offline thật, đúng 2 POST cùng payload/`request_id`, aggregate/cohost privacy/history ID chính xác, verifier read-only, 27 negative control, 9 verifier control và mutant `if (true)`. Bằng chứng local: analyze sạch, **240 Flutter +1 skip**, **23 DB**, **11/11 browser**, **27/27 negative case đúng kỳ vọng**, **9/9 verifier control**, mutant PASS, **33/33 manifest**, `is_dirty=false`, Web build PASS. App/backend không đổi; giữ A/B/C/D và HTTP/Auth/concurrency Đạt local. Toàn BH-07/pilot chưa nghiệm thu; mobile, delayed response sau đổi actor, banking/webhook, staging/production/backup, rehearsal/pilot và `supabase db reset` vẫn NOT RUN. Không merge/apply DB thật/deploy; người triển khai không tự ghi Đạt.

(Lịch sử review) Gói kiểm chứng **Browser / Offline / Reopen BH-07 Chưa đạt tại `c8a8e7f`** theo [review độc lập](reviews/bh07/review_c8a8e7f.md). Mở **BR1/BR2 P1, BR3–BR5 P2**: runner bỏ qua UI, không kiểm mutation offline/request_id, copy/privacy/ACL và auth/cache chưa đủ, thiếu log/provenance. Đã chuyển sang sửa gói kiểm chứng vòng 1/2.

(Lịch sử review) Gói kiểm chứng **Concurrency HTTP/Auth BH-07 Đạt local vòng2/2**, tested source `cbcc46c`, docs/evidence thực tế `bb940280333aec96457dd3014aabba9f66adf4ae`, theo [review độc lập](reviews/bh07/review_cbcc46c_r2.md).

## 1. Nền bắt buộc

- BH-06 Đạt tích hợp local tại `318bc52`, công bố review tại `b3bcfbb`: [review và bằng chứng](reviews/bh06/review_318bc52.md). I1/I2 đã đóng; giữ lịch sử các review theo tested SHA.
- `chore/ai-roles` đã merge vào main tại `eaeb209`; BH-06 merge vào main tại `e7f7627`. Checkout mới dùng main mới nhất, ghi full base SHA và kiểm nó chứa cả hai merge này. Không bắt đầu BH-07 từ main BH-05 cũ hoặc cherry-pick lại BH-06.
- Baseline reviewer BH-06: analyze sạch, **190 Flutter +335 DB hồi quy** (33+14+48+22+44+90+84), **7 tích hợp +3 nâng cấp +2 probe PASS**. [Xác minh merge main](reviews/bh06/main_merge_e7f7627.md) phân biệt kiểm tra mới trên main với bằng chứng DB trước merge.
- Đọc [IMPLEMENTER](ai/IMPLEMENTER.md), [REVIEWER](ai/REVIEWER.md), AGENTS, docs/00, docs/04, [backlog](09_IMPLEMENTATION_PLAN.md), [contract](08_DOMAIN_CONTRACTS.md), [flows](10_SCREEN_FLOWS.md) và [ADR](11_ARCHITECTURE_DECISIONS.md).

## 2. Phạm vi BH-07 và các cổng

Hoàn chỉnh start → complete → lịch sử/tổng kết, giữ công nợ sau complete; sao chép tổng kết đúng quyền; kiểm mất mạng/retry/mở lại app; end-to-end mobile/web và rehearsal vận hành/migration/backup. Không mở BH-08/BH-09, push/chat hoặc tích hợp ngân hàng/webhook.

| Phần | Phạm vi | Cổng chuyển phần |
|---|---|---|
| A | Rà soát/bổ sung DB/RPC/projection, kiểm quyền và complete/history/debt | Reviewer Đạt A trước khi giao B |
| B | Model/repository/provider đúng contract A, loading/error/retry/isolation | Reviewer Đạt B trước khi giao C |
| C | UI start/complete/lịch sử/tổng kết/copy theo role | Reviewer Đạt C trước tích hợp |
| D | Tích hợp, HTTP/JWT/Auth, mobile/web, offline/reopen, rehearsal vận hành | Review độc lập; thiếu cổng thì chưa nghiệm thu pilot |

**Phần A trên `feat/bh07a-db` đã Đạt local tại 4512c3a.** Không triển khai lại A chỉ vì đọc đầu bài; các yêu cầu A dưới đây giữ làm contract/tiêu chí đã kiểm. **B đã Đạt local tại `d7bac04`, tested code `a682007`, đóng B1/B2 vòng 1/2**; **C đã Đạt local tại `02a9b85`**; **D đã Đạt tích hợp local tại `3d590a8`**; **HTTP/Auth local đã Đạt tại `f9159dd`**; **Concurrency đã Đạt tại `cbcc46c`**; **Browser/backup/restore đã đóng local**; **hồ sơ readiness đang Chờ review** theo [bh07_readiness.md](reviews/bh07/bh07_readiness.md). Không tự làm hết A/B/C/D. Nếu A không cần đổi DB, chứng minh bằng test và contract audit; không tạo migration hoặc lớp trừu tượng chỉ để đủ tên phần.

## 3. BH-07A — kiểm code trước, chỉ bổ sung phần thiếu

1. Lập bảng đã có/thiếu, signature/response/error/ACL/caller và file dự kiến sửa. `start_session`, `complete_session`, repository/provider tương ứng và gate current đã có từ BH-05/06; không viết lại hoặc gọi RPC chưa tồn tại.
2. Rà complete: management đúng scope, session version từ nguồn server, chỉ in_progress và billing current. Chưa chốt hoặc stale bị chặn; buổi miễn phí vẫn cần revision current. **Không bắt buộc thu đủ tiền mới complete.**
3. Rà quyền đọc lịch sử/chi tiết/tổng kết sau complete, cả list và detail; không để session biến mất đối với actor có quyền chỉ vì projection cho buổi đang mở. Chỉ thêm endpoint/projection nếu nguồn hiện có chưa đáp ứng; ghi contract thực tế, không tự mở toàn bộ raw tables.
4. Công nợ/tiền đã thu/lịch sử payment-ledger không mất hoặc bị zero giả khi complete. Kiểm các thao tác tài chính sau complete theo contract hiện hành; không tự nới quyền, bypass stale hoặc cho sửa trực tiếp số dư để làm luồng chạy được. Nếu contract có khoảng trống nghiệp vụ, nêu đúng điểm trước khi mở rộng.
5. Tổng kết/copy chỉ lấy dữ liệu server đúng scope; không tính số dư từ trang lịch sử bị cắt, không lộ contact/bank của người khác. Việc bố trí UI/copy thực hiện ở C; A chuẩn bị contract cần thiết.
6. Mutation nguyên tử, actor lấy từ auth.uid(), request ID bền qua retry, cùng key/payload replay một kết quả, khác payload conflict; version conflict và audit có kiểm chứng. Forward migration mới nếu cần; không sửa migration đã chia sẻ hoặc chạy SQL legacy.

## 4. Kiểm thử và bằng chứng A

- Complete: quyền sai/actor khác/anonymous bị chặn; chưa chốt/stale bị chặn; current/free current được phép; còn nợ vẫn complete.
- Retry cùng request, payload khác, version cũ; lỗi transaction rollback; không tạo lifecycle/audit/payment/ledger lặp.
- Sau complete: đọc detail/history/summary theo đúng vai trò, công nợ còn nguyên; các đường thu/confirm/reject/reverse được phép theo contract không làm mất lịch sử hoặc thu dư.
- Phân trang/empty/error, quyền chéo CLB/buổi và không lộ dữ liệu riêng; dữ liệu cũ nếu có thêm migration.
- Viết test tái hiện trước khi sửa lỗi. Chạy analyze + toàn bộ Flutter test + runner BH-07 và hồi quy BH-02..06; giữ kiểm tra tích hợp/nâng cấp BH-06 phù hợp thay đổi. Nếu chỉ audit không đổi DB, nêu rõ những runner đã chạy, không dùng kết quả lịch sử làm kết quả mới.
- SET ROLE/Auth stub và widget mock không thay HTTP/JWT/Auth thật. Thiếu môi trường vẫn chuẩn bị phần độc lập, ghi NOT RUN và tác động đến cổng nghiệm thu; không dùng production thay môi trường test.

Bằng chứng mới đặt `docs/reviews/bh07/`: base/full tested SHA, diff, migration/RPC, lệnh/exit/count, JSON/log, môi trường, PASS/FAIL/NOT RUN, cấu hình ngoài code. Cập nhật docs/00, docs/09 và bàn giao thành **Chờ review BH-07A**, gửi prompt reviewer trực tiếp trong chat (không tạo file riêng), rồi commit/push nhánh và dừng để Codex review. Không tự ghi Đạt/Done; sửa toàn bộ P0/P1/P2 theo review, tối đa hai vòng theo AGENTS.

## 5. Giới hạn môi trường và triển khai

BH-06 mới Đạt trong phạm vi local/PostgreSQL cô lập. **Cập nhật 23/10/2026:** HTTP/PostgREST/JWT/Supabase Auth đã **Đạt local tại `f9159dd`** với 70/70 HTTP; concurrency **Đạt local tại `cbcc46c`** với 76/76 HTTP; browser/response trễ và backup/restore local đã đóng theo giới hạn trong [hồ sơ readiness](reviews/bh07/bh07_readiness.md). Hồ sơ readiness docs-only đang **Chờ review độc lập**. Thiết bị/browser khác/deep link, tải ảnh VietQR/ngân hàng thật, managed Supabase/PITR, staging/production, concurrent writers và rehearsal tải/pilot vẫn chưa nghiệm thu/NOT RUN. BH-07D phải báo bằng chứng thực tế cho các cổng pilot được yêu cầu, không kết luận pilot Đạt từ unit/widget test hoặc DB fixture.

Viết tài liệu vận hành và chạy rehearsal trên môi trường cô lập được phép; không apply staging/production, thay Auth settings, chuyển tiền/ngân hàng hoặc deploy nếu chưa được giao. Không tự merge main hoặc chuyển phần tiếp theo.

## 6. Bàn giao BH-07A — Chờ review (20/10/2026)

- Nhánh `feat/bh07a-db`, base `62d2c67dc66d512cf7f6f19932e2131ae060e2e9`, tested code `c339a47fdcb08e50811079bd89df7a1f9f53908a`. **Chờ review BH-07A**, không tự ghi Đạt.
- Migration `20261020180000_bh07_reads.sql` thêm `get_session_summary` và `list_my_session_history`; không sửa gate complete/billing/payment/ledger, không thêm cột/bảng/backfill.
- Runner `docs/reviews/bh07/run_bh07_tests.py`: **23/23 PASS** (21 CLEAN + 2 upgrade); test-first 9 PASS/13 FAIL trước migration. Analyze sạch, 190 Flutter, 335 DB hồi quy, 7 tích hợp, 3 nâng cấp PASS.
- [Audit/contract](reviews/bh07/bh07a_audit.md); [bàn giao, lệnh/exit/bằng chứng/NOT RUN](reviews/bh07/bh07a_handoff.md). Không chuyển B/C/D, không merge main, không deploy. HTTP/JWT/Auth thật, thiết bị/ngân hàng thật, staging/production, backup/restore và concurrency HTTP vẫn NOT RUN.

## 7. Bàn giao BH-07B — Chờ review (lịch sử 20/10/2026)

- Nhánh `feat/bh07b-data`, base `fd38838d85fed31603eae99ed363cf202650aeee`, tested code `89e1d8f5d2b8658a36b32ef80f3c77b82d798f80`. **Chờ review BH-07B**, không tự ghi Đạt.
- Thêm model/repository/provider cho `get_session_summary` và `list_my_session_history`: giữ tiền NULL khi management-only, không đổi NULL thành 0, không suy outstanding từ `due - paid`; lịch sử có pagination/filter/refresh, clear khi logout/đổi actor/CLB và bỏ response trễ; tổng kết clear khi logout/đổi actor/buổi, refresh sau mutation tiền đang mở.
- Giữ nguyên migration/RPC A và `completeSession`/version/`request_id` hiện có. Test stale/version xác nhận không báo thành công, retry giữ UUID.
- Kết quả mới: analyze sạch, **211/211 Flutter**, **23/23 BH-07**, **335/335 DB hồi quy**, **7/7 tích hợp**, **3/3 nâng cấp**. [Bàn giao, lệnh/exit/bằng chứng/NOT RUN](reviews/bh07/bh07b_handoff.md), [summary JSON](reviews/bh07/bh07b_evidence/summary.json).
- Không chuyển C/D, không merge main, không deploy. HTTP/PostgREST/JWT/Auth thật, UI C, thiết bị/ngân hàng thật, staging/production, backup/restore và concurrency HTTP vẫn NOT RUN.

## 8. Kết luận reviewer B — 1298490 (20/10/2026)

**Chưa đạt B**, theo [review độc lập](reviews/bh07/review_1298490.md): B1/B2 P2 còn mở (cache summary sau FORBIDDEN; history trùng ID khi các trang OFFSET chồng lấn). Reviewer tự chạy analyze sạch, 211 Flutter +335 DB +23 BH-07, 7 tích hợp +3 nâng cấp BH-06 PASS; probe provider 4 PASS/2 FAIL. Chỉ sửa B theo review, test đỏ trước sửa rồi xanh; tối đa hai vòng theo AGENTS. Không sửa RPC/migration A, làm UI C/D hoặc merge/deploy.

## 9. (Lịch sử) Bàn giao BH-07B sửa review vòng 1/2 — Chờ review (20/10/2026)

- Nhánh `feat/bh07b-data`, review công bố `135ff23`, base A `fd38838`, tested code vòng 0 `89e1d8f`, **tested code vòng 1 `a682007f6cd85931b410ec2930fd40cdd3fc73f4`**. **Chờ review BH-07B vòng 1**, không tự ghi Đạt.
- B1: `FORBIDDEN` xoá summary/quyền finance cache, giữ lỗi rõ ràng và scope để retry; transport error tạm thời vẫn giữ cache kèm lỗi; tiền không bị đổi thành 0.
- B2: dedupe lịch sử theo session ID; offset kế tiếp theo số dòng thô server đã tiêu thụ, không theo số ID duy nhất; filter/actor/serial/loading giữ nguyên; test ba trang `[0,2,4]` với dữ liệu chồng lấn.
- Test-first `prefix.log`: exit 1, đúng 2 FAIL; sau sửa targeted **58/58 PASS**, probe reviewer **6/6 PASS**. Final: analyze sạch, **212/212 Flutter**, **23/23 BH-07**, **335/335 DB hồi quy**, **7/7 tích hợp**, **3/3 nâng cấp**. [Bàn giao sửa](reviews/bh07/bh07b_fix_handoff.md), [summary JSON](reviews/bh07/bh07b_fix_evidence/summary.json).
- Không sửa migration/RPC A, không UI C/D, không merge main/deploy. HTTP/PostgREST/JWT/Auth thật, UI/thiết bị/ngân hàng thật, staging/production, backup/restore và concurrency HTTP vẫn NOT RUN.

## 10. (Lịch sử) Kết luận reviewer B vòng 1/2 — d7bac04 (20/10/2026)

BH-07B **Đạt phần B local tại `d7bac04`**, tested code `a682007`, vòng sửa 1/2; reviewer đóng B1/B2 P2 theo [review độc lập](reviews/bh07/review_d7bac04.md). Tự chạy analyze sạch, **212 Flutter +335 DB hồi quy +23 BH-07**, **7 tích hợp +3 nâng cấp BH-06**, **6/6 probe gốc PASS**. A giữ Đạt; C/D, toàn BH-07 và pilot chưa nghiệm thu. Không tự chuyển phần, merge main hoặc deploy.

Các bàn giao/kết luận vòng 0–1 của B phía trên giữ làm snapshot lịch sử. NOT RUN giữ theo review; C đã bàn giao chờ review tại mục 11, D chưa giao.

## 11. (Lịch sử) Bàn giao BH-07C — Chờ review (20/10/2026)

- Nhánh `feat/bh07c-ui`, base `cf95d76855acf1f394b1976ebab54087b4d7bba9`, tested code `15ae1af0d9d39678f4b9d99fabc9e9e22cb860ba`. **Chờ review BH-07C**, người triển khai không tự ghi Đạt.
- Chỉ UI C: lịch sử có filter CLB/khoảng ngày, loading/empty/error/retry/pagination/refresh; tổng kết theo quyền và copy không lộ contact/bank, giữ tiền NULL là `—`; nút kết thúc buổi trong màn tài chính chỉ bật khi management + in_progress + billing current/canCollect + có version server; thành công tải lại chi tiết/lịch sử.
- Không sửa migration/RPC A, model/repository/provider B hoặc contract. Start giữ hành vi hiện có. Không thêm provider mới.
- Kết quả mới: analyze sạch, **225/225 Flutter**, **23/23 BH-07 DB**; 335 DB hồi quy giữ baseline B, không chạy lại vì C không đổi DB/backend. [Bàn giao, lệnh/exit/bằng chứng/NOT RUN](reviews/bh07/bh07c_handoff.md).
- Không chuyển D, không merge main, không deploy. HTTP/PostgREST/JWT/Auth thật, thiết bị/browser/offline, ngân hàng/VietQR/webhook thật, staging/production, backup/restore, concurrency HTTP và pilot vẫn NOT RUN.

## 12. Review C — Chưa đạt tại 15ae1af (21/10/2026)

BH-07C **Chưa đạt tại `15ae1af`** trên `feat/bh07c-ui` theo [review độc lập](reviews/bh07/review_15ae1af.md): C1/C2/C3 P2 (complete thiếu DTO version, lỗi refresh cache rỗng bị che, lọc ngày phụ thuộc múi giờ). Reviewer tự chạy analyze sạch, **225 Flutter +52 targeted C +23 BH-07 DB PASS**; probe UI **2 PASS/3 FAIL**, control ngày UTC+7 **1 PASS**. A giữ Đạt `4512c3a`; B giữ Đạt `d7bac04` (code `a682007`). Chỉ sửa C vòng 1/2, test đỏ trước sửa; không đổi A/B, chuyển D, merge main hoặc deploy. Các cổng môi trường thật và pilot vẫn NOT RUN.

## 13. Bàn giao BH-07C sửa review vòng 1/2 — Chờ review (21/10/2026)

- Nhánh `feat/bh07c-ui`, base `9b978467316d66c458846ac68c5de8021401fa0c`, **tested code `02a9b857724e9ba031323ad732c90355d7932a39`**. **Chờ review BH-07C vòng 1/2**, người triển khai không tự ghi Đạt.
- C1: complete chỉ dùng `sessionVersion` từ DTO tài chính; thiếu DTO thì khoá nút và hướng dẫn tải lại, không fallback route. Fallback route vẫn giữ cho chốt phí BH-06.
- C2: lỗi refresh với cache rỗng vẫn hiện inline error, giữ empty card và có nút `Tải lại`; không biến lỗi mạng thành empty thành công.
- C3: ngày lọc là ngày lịch Việt Nam, đổi sang UTC+7 bằng helper; mốc cuối bao gồm hết ngày, độc lập múi giờ thiết bị.
- Bằng chứng: test đỏ trước sửa exit 1 với 3 FAIL đúng C1/C2/C3; sau sửa analyze sạch, **230/230 Flutter**, **57/57 targeted C** dưới cả `TZ=UTC` và `TZ=Asia/Ho_Chi_Minh`, **23/23 BH-07 DB**. Chi tiết tại [evidence](reviews/bh07/bh07c_fix_evidence/commands.md) và [bàn giao](reviews/bh07/bh07c_handoff.md).
- Không sửa A/B, migration hoặc backend. Không chuyển D, merge main hoặc deploy. HTTP/PostgREST/JWT/Auth thật, thiết bị/browser/offline, ngân hàng/VietQR/webhook, staging/production, backup/restore, concurrency HTTP và pilot vẫn NOT RUN.

## 14. Kết luận reviewer C vòng 1/2 — 02a9b85 (21/10/2026)

BH-07C **Đạt local vòng 1/2 tại `02a9b85`** theo [review độc lập](reviews/bh07/review_02a9b85.md), đóng C1/C2/C3 P2; không có P0/P1/P2 mới trong phạm vi sửa. Reviewer tự chạy analyze sạch, **230 Flutter**, **57 targeted C mỗi múi giờ UTC/Asia_Ho_Chi_Minh**, **23 BH-07 DB**, **5 probe UI mỗi múi giờ** PASS. A giữ `4512c3a`; B giữ `d7bac04` (code `a682007`). D, toàn BH-07/pilot và các cổng môi trường thật chưa nghiệm thu; không tự chuyển D, merge main hoặc deploy. Bảy log gốc đã bổ sung tại `3d5583b`, reviewer kiểm hash/count khớp; xem phụ lục review_02a9b85_logs_3d5583b.md.

Bàn giao/kết luận các vòng phía trên giữ làm lịch sử theo SHA; không tự coi phần C Đạt local là pilot/deploy.

## 15. Bàn giao BH-07D — Chờ review tích hợp BH-07 (21/10/2026)

- Nhánh `feat/bh07-integration`, base D `b0478a72021a726530c4051b52239a0a22d7fb96`, **tested code `3d590a8418157cf91b00b9a5503d09be4df069f3`**. **Chờ review tích hợp BH-07**; người triển khai không tự ghi Đạt. A giữ `4512c3a`; B giữ `d7bac04` (code `a682007`); C giữ `02a9b85`.
- Chỉ thêm 10 test tích hợp D và sửa tối thiểu `session_finance_screen.dart`: ẩn `Thêm chi phí` sau `completed/cancelled` vì RPC `post_session_expense` từ chối; giữ chốt lại phí, thu tiền mặt, xác nhận/từ chối thanh toán và hoàn tác.
- Test đỏ trước sửa exit 1 đúng 1 FAIL (`bh06c-add-expense` vẫn hiện sau complete). Sau sửa: analyze sạch, **240/240 Flutter**, **10/10 D mỗi múi giờ UTC/Asia_Ho_Chi_Minh**, **50/50 targeted C mỗi múi giờ**, **23/23 BH-07 DB** (`worktree_dirty=false`). [Bàn giao](reviews/bh07/bh07_integration_handoff.md), [lệnh/bằng chứng](reviews/bh07/integration_evidence/commands.md).
- Không sửa migration/RPC/model/repository/provider/contract, không sửa A/B/C, không merge main hoặc deploy. HTTP/PostgREST/JWT/Auth thật, browser/mobile/offline/deep link, concurrency HTTP, banking/webhook, staging/production, backup/restore, rehearsal/pilot và nghiệm thu toàn BH-07: NOT RUN.

## Kết luận reviewer BH-07D — 3d590a8 (21/10/2026)

BH-07D **Đạt tích hợp local tại `3d590a8`** theo [review độc lập](reviews/bh07/review_3d590a8.md), không có P0/P1/P2 mở trong phạm vi được giao. Reviewer tự chạy analyze sạch, **240 Flutter**, **10 D +50 C mỗi múi giờ UTC/Asia_Ho_Chi_Minh**, **23 BH-07 DB**, **6 probe reviewer** PASS. A giữ `4512c3a`; B giữ `d7bac04` (code `a682007`); C giữ `02a9b85`. HTTP/JWT/Auth thật, thiết bị/browser/offline, ngân hàng, staging/production/backup, concurrency HTTP và rehearsal/pilot vẫn NOT RUN; toàn BH-07 chưa nghiệm thu. Không tự merge main, apply DB thật hoặc deploy.

Chỉ nghiệm thu tích hợp local trong phạm vi giao, không đóng cổng pilot/D môi trường thật bằng mock. Giữ các bàn giao/kết luận phía trên làm lịch sử theo SHA.

## 16. Bàn giao kiểm chứng HTTP/Auth BH-07 — Chờ review vòng 1/2 (21/10/2026)

- Nhánh `feat/bh07-http-verification`, base `593bea86ffb807675387dba6b0276b555fdc87a1`, **tested source `f9159dd483baf2dd219b2854fd8ab08d1e5f0330`**. **Chờ review HTTP/Auth BH-07 vòng 1/2**; người triển khai không tự ghi Đạt.
- Chỉ thêm/sửa script, seed và test kiểm chứng; không sửa migration, RPC, model, repository, provider, UI hay contract. Không merge main, apply DB thật hoặc deploy.
- H1: seed charge0 cho đúng free player/revision; precondition kiểm player exempt/present, revision, một charge 0; sau complete/retry kiểm finance và DB vẫn giữ charge/revision.
- H2: whitelist chính xác mọi row history, summary finance/cohost; cohost có đủ finance key null; negative control top-level/nested/later-row cho bank/account/receiver; seed contact/bank/receiver giả để kiểm nguồn riêng tư thật.
- Kết quả local: HTTP/Auth **70/70 PASS**, `flutter analyze` sạch, **240 Flutter +1 skip**, **23/23 BH-07 DB**, `worktree_dirty_before_run=false` tại tested source; red run trước sửa **67/70**. [Bàn giao và phạm vi](reviews/bh07/http_auth_handoff.md); [evidence](reviews/bh07/http_auth_evidence/).
- Còn NOT RUN: thiết bị/browser/offline, ngân hàng/webhook, staging/production/backup, concurrency HTTP và rehearsal/pilot. Toàn BH-07 chưa nghiệm thu.

## Lịch sử review HTTP/Auth — Chưa đạt tại 3ad25a4 (21/10/2026)

Kiểm chứng **HTTP/Auth BH-07 Chưa đạt tại `3ad25a4`**, docs/evidence `c54b004`, theo [review độc lập](reviews/bh07/review_3ad25a4.md): H1/H2 P2 về fixture free-current thiếu charge0 và assertion privacy chưa bao phủ raw payload. Reviewer tự chạy **65/65 HTTP check** qua GoTrue/PostgREST/Kong/PostgreSQL17.11 thật trên stack Linux riêng; analyze sạch, **240 Flutter +1 skip**, **23 BH-07 DB PASS**. Lệnh Windows/full Supabase CLI recipe chưa tái lập trên reviewer; khác biệt môi trường ghi rõ trong review. A/B/C/D local giữ kết luận trước; toàn BH-07/pilot chưa nghiệm thu. Chỉ sửa gói kiểm chứng vòng1/2; không đổi contract/backend/UI, merge main, apply DB thật hoặc deploy.

## Kết luận reviewer HTTP/Auth vòng1/2 — f9159dd (21/10/2026)

Gói kiểm chứng **HTTP/Auth BH-07 Đạt local vòng1/2 tại `f9159dd`**, docs/evidence `0758b72`, theo [review độc lập](reviews/bh07/review_f9159dd.md): đóng H1/H2 P2, không có P0/P1/P2 mới trong phạm vi sửa. Reviewer tự chạy **70/70 HTTP check** trên stack Linux GoTrue/PostgREST/Kong/PostgreSQL17.11 thật; analyze sạch, **240 Flutter +1 skip**, **23 BH-07 DB**, **4 probe validator** PASS. Manifest tác giả21/21 khớp LF. A/B/C/D local giữ kết luận trước; **toàn BH-07/pilot chưa nghiệm thu**, không chuyển ticket sang hoàn thành. Các cổng thiết bị/browser/offline, ngân hàng, staging/production/backup, concurrency HTTP và rehearsal/pilot vẫn NOT RUN; không tự merge/apply DB thật/deploy.

Bàn giao và review cũ giữ làm lịch sử theo SHA. Đây là nghiệm thu riêng kiểm chứng HTTP/Auth local, không đóng cổng còn NOT RUN của toàn BH-07.

## 17. (Lịch sử) Bàn giao kiểm chứng Concurrency HTTP/Auth BH-07 — Chờ review (21/10/2026)

- Nhánh `feat/bh07-http-concurrency`, base `4da6339a1a92bcf27675f50ca4b785fbb45f1e78`. **Chờ review Concurrency HTTP/Auth BH-07**; người triển khai không tự ghi Đạt.
- Bổ sung 6 check concurrency:
  1. Idempotent replay cho complete session đồng thời cùng `request_id`: version tăng đúng 1 lần (v3→v4), `audit_events` và `operation_requests` chỉ tạo 1 bản ghi.
  2. Idempotent replay cho cash payment đồng thời cùng `request_id`: cùng `payment_id`, 1 payment, 1 ledger, 1 operation request.
  3. Idempotent replay cho confirm payment đồng thời cùng `request_id`: 1 ledger, 1 operation request, tất toán công nợ về 0.
  4. Competing complete conflict: 2 request complete đồng thời khác `request_id`, 1 winner commit v4, 1 loser bị từ chối với conflict / invalid state.
  5. Competing cash payments no-overcollect: 2 request thanh toán đồng thời khác `request_id` cạnh tranh trên số nợ còn lại, server từ chối bên vượt nợ (`PAYMENT_EXCEEDS_OUTSTANDING`), nợ được bảo toàn chính xác.
  6. Transport drop response sau commit: client proxy `DropResponseAfterCommitClient` nhận response 200 từ server rồi ngắt kết nối mạng mô phỏng lỗi transport; retry lại qua client thường với cùng `request_id` nhận kết quả thành công mà không duplicate payment/ledger.
- Kết quả kiểm chứng local: **76/76 PASS** HTTP checks, `flutter analyze` sạch (0 issues), **240 Flutter +1 skip**, **23/23 BH-07 DB PASS**. Red run trước khi nạp fixture đạt **70/76** (đúng 6 FAIL concurrency). Manifest 21/21 khớp LF, quét sạch secret.
- [Bàn giao và phạm vi](reviews/bh07/http_concurrency_handoff.md); [bằng chứng](reviews/bh07/http_concurrency_evidence/).
- Còn NOT RUN: thiết bị/browser/offline, ngân hàng/webhook, staging/production/backup và rehearsal/pilot. Toàn BH-07 chưa nghiệm thu.

## 18. Review Concurrency HTTP/Auth tại 2f0aa59 (22/10/2026)

**Chưa đạt**, H1/H2 P2; xem [báo cáo độc lập](reviews/bh07/review_2f0aa59.md). Chỉ sửa gói test kiểm chứng vòng1/2: chứng minh commit trước retry và kiểm đúng lỗi domain competitor, giữ 70 check cũ. Không sửa backend/app, không chuyển pilot/merge/deploy.

## 19. Review sửa Concurrency HTTP/Auth vòng1/2 (22/10/2026)

Gói kiểm chứng **Concurrency HTTP/Auth BH-07 Chưa đạt vòng1/2 tại `cbcc46c`**, docs/evidence `b23df5e`, theo [review độc lập](reviews/bh07/review_cbcc46c.md). **Đóng H1/H2 P2** sau kiểm chứng độc lập; còn **H3/H4 P2 về log UTF-16/CRLF trái công bố LF và full base SHA sai**. Reviewer tự chạy **76/76 HTTP**, analyze sạch, **240 Flutter +1 skip**, **23/23 DB**, **4/4 probe** PASS. Manifest19/19 khớp raw bytes, chưa đạt chuẩn LF; scan đã decode không thấy secret theo mẫu kiểm. Chỉ sửa tài liệu/bằng chứng vòng2/2, không đổi logic test/app/backend. Giữ HTTP/Auth `f9159dd` và A/B/C/D local; **toàn BH-07/pilot chưa nghiệm thu**. Thiết bị/browser/offline, ngân hàng/webhook, staging/production/backup và rehearsal/pilot vẫn NOT RUN; không merge/apply DB thật/deploy.

## 20. Bàn giao sửa Concurrency HTTP/Auth vòng 2/2 — Chờ review (22/10/2026)

- Trạng thái: **Chờ review vòng 2/2 tại tested source `cbcc46c2e125b156b53f4297ef864cf658855d37`** trên nhánh `feat/bh07-http-concurrency`, base thực tế `a0f831af47f98c7649e0c80dce4d5f13004a0db2` (đính chính từ tham số ban đầu `a0f831ae3f47e305608bfa0dff19ae035b31f798`).
- Xử lý triệt để H3 & H4 P2 theo [review cbcc46c](reviews/bh07/review_cbcc46c.md); bảo toàn kết luận H1 & H2 đã ĐÓNG.
- Không sửa bất kỳ file test hay code ứng dụng nào (chỉ cập nhật tài liệu và bộ bằng chứng).
- Toàn bộ 19 file evidence được chuẩn hóa UTF-8 thuần không BOM, CRLF=0 ở cấp text; quét secret sạch sau decode; manifest 19/19 forward-slash khớp tuyệt đối.
- [Bàn giao](reviews/bh07/http_concurrency_handoff.md); [bằng chứng](reviews/bh07/http_concurrency_evidence/).
- Toàn BH-07/pilot vẫn chưa nghiệm thu; các cổng môi trường thật tiếp tục ghi nhận NOT RUN.


## 20. Review Concurrency HTTP/Auth vòng2/2 (22/10/2026)

Gói kiểm chứng **Concurrency HTTP/Auth BH-07 Đạt local vòng2/2**, tested source `cbcc46c`, docs/evidence thực tế `bb940280333aec96457dd3014aabba9f66adf4ae`, theo [review độc lập](reviews/bh07/review_cbcc46c_r2.md). **Đóng H3/H4**, giữ H1/H2 đã đóng; không còn P0/P1/P2 mở trong gói. Reviewer tự audit **19/19 hash**, UTF-8 không BOM, CR/CRLF=0, nội dung log và metadata lịch sử bảo toàn, scan không thấy secret theo mẫu kiểm; source không đổi. Vòng2/2 không chạy lại suite; kế thừa kết quả reviewer vòng1/2: **76 HTTP, 240 Flutter +1 skip, 23 DB, 4 probe PASS**, analyze sạch. Giữ A/B/C/D và HTTP/Auth nền Đạt local; **toàn BH-07/pilot chưa nghiệm thu**. Thiết bị/browser/offline, ngân hàng/webhook, staging/production/backup, rehearsal/pilot vẫn NOT RUN; không merge/apply DB thật/deploy.

## 21. Review Browser / Offline / Reopen (22/10/2026)

Gói kiểm chứng **Browser / Offline / Reopen BH-07 Chưa đạt tại `c8a8e7f`** theo [review độc lập](reviews/bh07/review_c8a8e7f.md). Mở **BR1/BR2 P1, BR3–BR5 P2**: runner bỏ qua UI, không kiểm mutation offline/request_id, copy/privacy/ACL và auth/cache chưa đủ, thiếu log/provenance. Reviewer tự chạy analyze sạch, **240 Flutter +1 skip**, **23 DB**, build Web thành công. Runner trên Chromium thật tự báo11/11 nhưng UI trắng; 17 ảnh tác giả giống nhau và chỉ là guest screen, nên **không nghiệm thu browser UI**. Manifest chỉ22/23, thiếu browser_runner.log. Chỉ sửa gói kiểm chứng vòng1/2; giữ app/backend và các kết luận A/B/C/D, HTTP/Auth/concurrency đã Đạt local. **Toàn BH-07/pilot chưa nghiệm thu**; thiết bị/browser UI đúng luồng, banking/webhook, staging/production/backup, rehearsal/pilot vẫn NOT RUN/chưa đạt. Không merge/apply DB thật/deploy.

## 22. Review Browser / Offline / Reopen vòng1/2 (22/10/2026)

Gói **Browser / Offline / Reopen BH-07 Chưa đạt vòng1/2 tại `b00b580`**, docs/evidence thực tế `d01e3692b6b07f145f603565a91ea6f629016ba1`, theo [review độc lập](reviews/bh07/review_b00b580.md). UI thật đã chạy,12 ảnh khác nhau; **BR1 còn P2, BR2 P1, BR3/BR4/BR5 P2** về postcondition, gate retry/privacy/history/cache và bằng chứng. Reviewer tự chạy **11/11 browser UI tự báo PASS**, analyze sạch, **240 Flutter +1 skip**, **23 DB**, Web build PASS; trace POST/DB chứng minh app giữ cùng intent và1 audit/operation. Nhưng8 control sai vẫn bị test nhận PASS, manifest chỉ17/21 (thiếu4 log). Chỉ sửa gói kiểm chứng vòng2/2, không sửa app/backend. Giữ A/B/C/D và HTTP/Auth/concurrency Đạt local; **toàn BH-07/pilot chưa nghiệm thu**. Các cổng mobile, banking/webhook, staging/production/backup, rehearsal/pilot và cache cùng instance vẫn NOT RUN/chưa đạt; không merge/apply DB thật/deploy.

## 23. Review Browser / Offline / Reopen vòng2/2 — dừng gói (23/10/2026)

Gói **Browser / Offline / Reopen BH-07 Chưa đạt vòng2/2** tại source `51cb3b1`, docs/evidence `eadb5c7`, theo [review độc lập](reviews/bh07/review_eadb5c7.md). Đóng BR1 và ca SPA BR4; lỗi P1 retry đã sửa nhưng **BR2 còn P2**, **BR3/BR5 P2 còn mở** về gate UI error, aggregate/ACL và verifier/negative controls/provenance. Reviewer tự chạy analyze sạch, **240 Flutter +1 skip**, **23 DB**, **11/11 browser**, Web build PASS; **21/21 hash**, readonly missing/hash/sb_secret controls PASS. Tuy nhiên4 control BR3, silent-error, JWT/UTF8 và mutant negative-runner vẫn được nhận xanh sai. **Dừng gói sau2 vòng theo AGENTS, chờ quyết định chủ dự án; không tự mở vòng3 hoặc giao sửa tiếp.** App/backend không đổi; giữ A/B/C/D và HTTP/Auth/concurrency Đạt local. Toàn BH-07/pilot chưa nghiệm thu; mobile/banking/webhook/staging/production/backup/rehearsal/pilot và response trễ sau đổi actor vẫn NOT RUN. Không merge/apply DB thật/deploy.
