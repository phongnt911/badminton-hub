# BH-07 — buổi hoàn chỉnh, lịch sử, tổng kết và pilot

> **Hiện hành 22/10/2026:** Gói kiểm chứng **Concurrency HTTP/Auth BH-07 Đạt local vòng2/2**, tested source `cbcc46c`, docs/evidence thực tế `bb940280333aec96457dd3014aabba9f66adf4ae`, theo [review độc lập](reviews/bh07/review_cbcc46c_r2.md). **Đóng H3/H4**, giữ H1/H2 đã đóng; không còn P0/P1/P2 mở trong gói. Reviewer tự audit **19/19 hash**, UTF-8 không BOM, CR/CRLF=0, nội dung log và metadata lịch sử bảo toàn, scan không thấy secret theo mẫu kiểm; source không đổi. Vòng2/2 không chạy lại suite; kế thừa kết quả reviewer vòng1/2: **76 HTTP, 240 Flutter +1 skip, 23 DB, 4 probe PASS**, analyze sạch. Giữ A/B/C/D và HTTP/Auth nền Đạt local; **toàn BH-07/pilot chưa nghiệm thu**. Thiết bị/browser/offline, ngân hàng/webhook, staging/production/backup, rehearsal/pilot vẫn NOT RUN; không merge/apply DB thật/deploy.

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

**Phần A trên `feat/bh07a-db` đã Đạt local tại 4512c3a.** Không triển khai lại A chỉ vì đọc đầu bài; các yêu cầu A dưới đây giữ làm contract/tiêu chí đã kiểm. **B đã Đạt local tại `d7bac04`, tested code `a682007`, đóng B1/B2 vòng 1/2**; **C đã Đạt local tại `02a9b85`**; **D đã Đạt tích hợp local tại `3d590a8`**; **HTTP/Auth local đang Chờ review tại `3ad25a4`** theo mục 16. Không tự làm hết A/B/C/D. Nếu A không cần đổi DB, chứng minh bằng test và contract audit; không tạo migration hoặc lớp trừu tượng chỉ để đủ tên phần.

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

BH-06 mới Đạt trong phạm vi local/PostgreSQL cô lập. **Cập nhật 21/10/2026:** HTTP/PostgREST/JWT/Supabase Auth đã được kiểm local bằng ma trận **65/65 tại `3ad25a4`** ([bàn giao](reviews/bh07/http_auth_handoff.md)), đang **Chờ review kiểm chứng HTTP/Auth BH-07**. Thiết bị/browser/deep link, tải ảnh VietQR/ngân hàng thật, staging/production, backup/restore và concurrency HTTP vẫn chưa có nghiệm thu. BH-07D phải báo bằng chứng thực tế cho các cổng pilot được yêu cầu, không kết luận pilot Đạt từ 190 unit/widget test hoặc 335 DB fixture.

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
