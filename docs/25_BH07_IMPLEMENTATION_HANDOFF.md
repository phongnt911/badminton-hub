# BH-07 — buổi hoàn chỉnh, lịch sử, tổng kết và pilot

> **Hiện hành 21/10/2026:** BH-07C **Chưa đạt tại `15ae1af`** trên `feat/bh07c-ui` theo [review độc lập](reviews/bh07/review_15ae1af.md): C1/C2/C3 P2 (complete thiếu DTO version, lỗi refresh cache rỗng bị che, lọc ngày phụ thuộc múi giờ). Reviewer tự chạy analyze sạch, **225 Flutter +52 targeted C +23 BH-07 DB PASS**; probe UI **2 PASS/3 FAIL**, control ngày UTC+7 **1 PASS**. A giữ Đạt `4512c3a`; B giữ Đạt `d7bac04` (code `a682007`). Chỉ sửa C vòng 1/2, test đỏ trước sửa; không đổi A/B, chuyển D, merge main hoặc deploy. Các cổng môi trường thật và pilot vẫn NOT RUN.

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

**Phần A trên `feat/bh07a-db` đã Đạt local tại 4512c3a.** Không triển khai lại A chỉ vì đọc đầu bài; các yêu cầu A dưới đây giữ làm contract/tiêu chí đã kiểm. **B đã Đạt local tại `d7bac04`, tested code `a682007`, đóng B1/B2 vòng 1/2**; **C đang Chờ review tại `15ae1af`** theo mục 11. Chỉ bắt đầu D khi C được reviewer Đạt. Không tự làm hết A/B/C/D. Nếu A không cần đổi DB, chứng minh bằng test và contract audit; không tạo migration hoặc lớp trừu tượng chỉ để đủ tên phần.

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

BH-06 mới Đạt trong phạm vi local/PostgreSQL cô lập. HTTP/PostgREST/JWT/Supabase Auth thật, thiết bị/browser/deep link, tải ảnh VietQR/ngân hàng thật, staging/production, backup/restore và concurrency HTTP vẫn chưa có nghiệm thu. BH-07D phải báo bằng chứng thực tế cho các cổng pilot được yêu cầu, không kết luận pilot Đạt từ 190 unit/widget test hoặc 335 DB fixture.

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
