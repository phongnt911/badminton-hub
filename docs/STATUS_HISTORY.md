# Lịch sử cập nhật trạng thái

Tám mục từ “Cập nhật sau review v1.1” đến “Mới nhất — sau BH-05” được chuyển nguyên văn từ cuối `docs/00_START_HERE.md` (đợt rà soát sau BH-05); các mục sau đó được bổ sung ngày 16/10/2026. Đây là nhật ký theo thời gian: nhiều chỉ dẫn trong đó đã hết hiệu lực. Trạng thái hiện hành nằm ở mục "Trạng thái hiện tại" của [00_START_HERE.md](00_START_HERE.md) và [22_BH05_HANDOFF.md](22_BH05_HANDOFF.md).

## Browser / Offline / Reopen BH-07 — Chờ review (22/10/2026)

Gói kiểm chứng **Browser / Offline / Reopen BH-07 đang ở trạng thái Chờ review** trên nhánh `feat/bh07-browser-verification` từ base `8f9259e8dabf9b79088f9bb1eb9c9049d660eff5`. Đã kiểm chứng Flutter Web trên Google Chrome 155 thật qua CDP với Supabase local/Auth thật: luồng Start → điểm danh → chốt phí → complete → history/summary; phân quyền 4 actor (Owner, Finance, Cohost null finance, Member cô lập); mất mạng bắt lỗi transport chân thực không báo thành công giả, online phục hồi retry cùng intent giữ `request_id`, F5/reopen bảo toàn session từ `localStorage`, logout làm sạch cache không rò rỉ chéo. Kết quả: **11/11 browser matrix PASS (0 FAIL)**, **17 ảnh screenshot PNG**, analyze sạch, 240 Flutter +1 skip, 23 DB PASS. Giữ nguyên source đã nghiệm thu; **toàn BH-07/pilot chưa nghiệm thu**. Thiết bị di động thật, ngân hàng/webhook thật, staging/production và rehearsal/pilot vẫn NOT RUN; không merge main/apply DB thật/deploy. [Bàn giao](reviews/bh07/browser_handoff.md), [bằng chứng](reviews/bh07/browser_evidence/).

## Concurrency HTTP/Auth BH-07 — Đạt vòng2/2 (22/10/2026)

Gói kiểm chứng **Concurrency HTTP/Auth BH-07 Đạt local vòng2/2**, tested source `cbcc46c`, docs/evidence thực tế `bb940280333aec96457dd3014aabba9f66adf4ae`, theo [review độc lập](reviews/bh07/review_cbcc46c_r2.md). **Đóng H3/H4**, giữ H1/H2 đã đóng; không còn P0/P1/P2 mở trong gói. Reviewer tự audit **19/19 hash**, UTF-8 không BOM, CR/CRLF=0, nội dung log và metadata lịch sử bảo toàn, scan không thấy secret theo mẫu kiểm; source không đổi. Vòng2/2 không chạy lại suite; kế thừa kết quả reviewer vòng1/2: **76 HTTP, 240 Flutter +1 skip, 23 DB, 4 probe PASS**, analyze sạch. Giữ A/B/C/D và HTTP/Auth nền Đạt local; **toàn BH-07/pilot chưa nghiệm thu**. Thiết bị/browser/offline, ngân hàng/webhook, staging/production/backup, rehearsal/pilot vẫn NOT RUN; không merge/apply DB thật/deploy.

## Concurrency HTTP/Auth BH-07 sửa vòng 2/2 — Chờ review (22/10/2026)

Gói Concurrency HTTP/Auth **Chờ review vòng 2/2 tại tested source `cbcc46c`** trên nhánh `feat/bh07-http-concurrency`, base thực tế `a0f831af47f98c7649e0c80dce4d5f13004a0db2` (commit cha của `cbcc46c`, đính chính từ tham số ban đầu `a0f831ae3f47e305608bfa0dff19ae035b31f798`). Đã khắc phục triệt để H3 & H4 P2 theo [review cbcc46c](reviews/bh07/review_cbcc46c.md): H3 decode 6 file log theo đúng encoding nguồn, chuyển đổi 100% sang UTF-8 không BOM và LF (CRLF = 0 ở cả cấp raw bytes và decoded text), quét secret sau decode sạch (0 secret), manifest 19/19 forward-slash khớp tuyệt đối; H4 đính chính base SHA thực tế và lưu vết tham số ban đầu trong metadata và commands. Bảo toàn tested source `cbcc46c` và kết luận H1/H2 đã ĐÓNG; không sửa test/app/migration/RPC/contract. Giữ kết quả độc lập 76/76 HTTP checks PASS, analyze sạch, 240 Flutter +1 skip, 23/23 BH-07 DB PASS. [Bàn giao](reviews/bh07/http_concurrency_handoff.md), [bằng chứng](reviews/bh07/http_concurrency_evidence/). Không tự ghi Đạt, merge hoặc deploy; các cổng môi trường thật và pilot vẫn NOT RUN.

## Concurrency HTTP/Auth BH-07 — review cbcc46c (22/10/2026)

Gói kiểm chứng **Concurrency HTTP/Auth BH-07 Chưa đạt vòng1/2 tại `cbcc46c`**, docs/evidence `b23df5e`, theo [review độc lập](reviews/bh07/review_cbcc46c.md). **Đóng H1/H2 P2** sau kiểm chứng độc lập; còn **H3/H4 P2 về log UTF-16/CRLF trái công bố LF và full base SHA sai**. Reviewer tự chạy **76/76 HTTP**, analyze sạch, **240 Flutter +1 skip**, **23/23 DB**, **4/4 probe** PASS. Manifest19/19 khớp raw bytes, chưa đạt chuẩn LF; scan đã decode không thấy secret theo mẫu kiểm. Chỉ sửa tài liệu/bằng chứng vòng2/2, không đổi logic test/app/backend. Giữ HTTP/Auth `f9159dd` và A/B/C/D local; **toàn BH-07/pilot chưa nghiệm thu**. Thiết bị/browser/offline, ngân hàng/webhook, staging/production/backup và rehearsal/pilot vẫn NOT RUN; không merge/apply DB thật/deploy.

## Concurrency HTTP/Auth BH-07 sửa vòng 1/2 — Chờ review (22/10/2026)

Gói Concurrency HTTP/Auth **Chờ review vòng 1/2 tại tested source `cbcc46c`** trên nhánh `feat/bh07-http-concurrency`, base `a0f831a`. Đã sửa H1/H2 P2 theo [review_2f0aa59.md](reviews/bh07/review_2f0aa59.md): H1 chỉ drop sau HTTP 200, kiểm chứng DB server đã commit trước retry, bổ sung negative control HTTP 400; H2 kiểm domain error có cấu trúc (VERSION_CONFLICT/INVALID_STATE 22023/409, PAYMENT_EXCEEDS_OUTSTANDING 22023), bổ sung negative controls loại bỏ FORBIDDEN/NOT_FOUND/INVALID_INPUT/transport. Red probe 3 FAIL trước sửa, green probe 5/5 PASS sau sửa. Ma trận HTTP local đạt **76/76 PASS**, analyze sạch (0 issues), **240 Flutter +1 skip**, **23/23 BH-07 DB PASS**. Manifest 19/19 khớp LF, quét sạch secret. [Bàn giao](reviews/bh07/http_concurrency_handoff.md), [bằng chứng](reviews/bh07/http_concurrency_evidence/). Không tự ghi Đạt, merge hoặc deploy; các cổng môi trường thật và pilot vẫn NOT RUN.

## Concurrency HTTP/Auth BH-07 — Chưa đạt (22/10/2026)

Gói kiểm chứng **Concurrency HTTP/Auth BH-07 Chưa đạt tại `2f0aa59`** theo [review độc lập](reviews/bh07/review_2f0aa59.md): H1/H2 P2 về tiền đề drop sau commit và validator lỗi cạnh tranh quá rộng. Reviewer tự chạy **76/76 HTTP**, analyze sạch, **240 Flutter +1 skip**, **23/23 DB**; hai probe tái hiện xanh giả. Manifest tác giả21/21 khớp LF, không thấy secret theo scan. Chỉ sửa gói kiểm chứng vòng1/2, giữ HTTP/Auth `f9159dd` và A/B/C/D đã Đạt local. **Toàn BH-07/pilot chưa nghiệm thu**; thiết bị/browser/offline, ngân hàng, staging/production/backup và rehearsal/pilot vẫn NOT RUN. Không merge main/apply DB thật/deploy.

## Concurrency HTTP/Auth BH-07 — Chờ review (21/10/2026)

Gói Concurrency HTTP/Auth **Chờ review tại tested source** trên nhánh `feat/bh07-http-concurrency`, base `4da6339a1a92bcf27675f50ca4b785fbb45f1e78`. Bổ sung 6 check concurrency (idempotent replay, competing complete conflict, competing cash payment no-overcollect, transport drop response sau commit rồi retry). Ma trận HTTP local đạt **76/76 PASS**, analyze sạch (0 issues), **240 Flutter +1 skip**, **23/23 BH-07 DB PASS**. Red run ghi nhận **70/76** (đúng 6 FAIL concurrency). Manifest 21/21 khớp LF, quét sạch secret. [Bàn giao](reviews/bh07/http_concurrency_handoff.md), [bằng chứng](reviews/bh07/http_concurrency_evidence/). Không tự ghi Đạt, merge hoặc deploy; các cổng môi trường thật và pilot vẫn NOT RUN.

## HTTP/Auth BH-07 sửa review vòng 1/2 — Chờ review (21/10/2026)

Gói HTTP/Auth **Chờ review vòng 1/2 tại tested source `f9159dd`** trên `feat/bh07-http-verification`, base `593bea8`, sau khi sửa H1/H2 P2 theo [review](reviews/bh07/review_3ad25a4.md). Đã thêm charge0 cho free player/revision, kiểm charge được giữ sau complete/retry; raw projection whitelist mọi row history, summary finance/cohost và negative control bank/account/receiver/nested/later-row; seed contact/bank/receiver giả. Red run **67/70** trước seed fix; sau sửa HTTP **70/70**, analyze sạch, **240 Flutter +1 skip**, **23/23 BH-07 DB**. [Bàn giao](reviews/bh07/http_auth_handoff.md), [bằng chứng](reviews/bh07/http_auth_evidence/). Không tự ghi Đạt, merge hoặc deploy; các cổng môi trường thật và pilot vẫn NOT RUN.

## BH-07C sửa review vòng 1/2 — Chờ review (21/10/2026)

BH-07C **Chờ review vòng 1/2 tại tested code `02a9b85`** trên `feat/bh07c-ui`, base `9b97846`, sau khi sửa C1/C2/C3 P2 theo [review](reviews/bh07/review_15ae1af.md). Test đỏ trước sửa 3 FAIL; sau sửa analyze sạch, **230 Flutter +57 targeted C (UTC và Asia/Ho_Chi_Minh) +23 BH-07 DB PASS**. A/B giữ Đạt theo SHA trước. [Bàn giao](reviews/bh07/bh07c_handoff.md), [bằng chứng](reviews/bh07/bh07c_fix_evidence/commands.md). Chưa chuyển D, merge hoặc deploy; các cổng môi trường thật và pilot vẫn NOT RUN.

## Cập nhật sau review v1.1

Ngày 14/10/2026 đã đọc metadata DB thật qua connector: public chỉ thấy venues/sessions/session_players; SELECT/INSERT policy hai bảng nghiệp vụ mở cho PUBLIC, không có UPDATE policy; code CLB/quỹ gọi bảng chưa có. Chi tiết và hành động ở [backlog xử lý review](09_IMPLEMENTATION_PLAN.md#xử-lý-phát-hiện-review-p1p2). Đây là snapshot đọc, không phải xác nhận app hoạt động hoặc quyền đã được sửa.

Bắt đầu bằng prompt AG-00 để ghi nhận baseline local/staging và kế hoạch. Sau đó triển khai từng ticket, không mở UPDATE policy cho tất cả như cách chữa bộ đếm. v1.1 bổ sung bảo vệ bản chốt phí lỗi thời, lời mời waitlist và ADR. Việc cập nhật tài liệu không đồng nghĩa R1–R7 đã được sửa trong code/DB.

## Ưu tiên sau review BH-02 ngày 15/10/2026

Đọc [13_BH02_REVIEW_HANDOFF.md](13_BH02_REVIEW_HANDOFF.md) và thực hiện prompt sửa F1–F7 trước khi sang BH-03. Đây là cập nhật mới hơn nhật ký soạn migration: 33 ca RLS cô lập có 18 PASS / 15 FAIL; chưa đạt nghiệm thu. Không chạy lại AG-00/BH-01 từ đầu nếu đã có bằng chứng triển khai.

## Ưu tiên mới sau commit 15ef59b

Review độc lập ngày 15/10/2026 xác nhận 33 ca cũ PASS nhưng 6 ca bổ sung FAIL. Tiếp tục **H1–H3** ở cuối [13_BH02_REVIEW_HANDOFF.md](13_BH02_REVIEW_HANDOFF.md), chưa chuyển BH-03. Hướng dẫn này mới hơn mục nghiệm thu 33/33 trong lịch sử; không chạy lại AG-00/BH-01.

## Tiếp tục BH-03

Chủ dự án yêu cầu chuyển sang BH-03 sau remediation 11aaec7. Dùng [15_BH03_IMPLEMENTATION_HANDOFF.md](15_BH03_IMPLEMENTATION_HANDOFF.md) làm đầu bài cụ thể cho CLB/member/bank, giữ regression BH-02; không chạy lại AG-00/BH-01. Những mục chờ H1–H3 phía trên là lịch sử trước remediation; việc chấp nhận bước tiếp theo không thay cho báo cáo môi trường/giới hạn test thực tế.

## Cập nhật BH-03 sau review C1–C5

Đọc [17_BH03_REMEDIATION.md](17_BH03_REMEDIATION.md): đã có forward migration và regression cho consent, concurrent idempotency, request keys và logout/session isolation. Giữ lịch sử review 88dd247 như baseline; không lặp lại các lỗi đã sửa. Production chưa apply, full Supabase integration vẫn cần kiểm chứng theo giới hạn trong báo cáo.

## Điểm tiếp tục mới nhất trước BH-04

Đọc [19_PRE_BH04_HANDOFF.md](19_PRE_BH04_HANDOFF.md). Đợt sửa cấu hình/auth/phân trang/UI/ACL đã triển khai; các mục chờ sửa cũ là lịch sử. Chuyển đổi màn buổi chơi demo trong BH-04, giữ cổng pilot và giới hạn local/staging.

## Mới nhất — sau sửa review BH-04

Đọc [21_BH04_REMEDIATION.md](21_BH04_REMEDIATION.md), giữ 104 Flutter +161 DB regression rồi tiếp tục BH-05. Các lỗi R1–R4 ở review dd5c1e6 là baseline trước sửa.

## Mới nhất — sau BH-05

Đọc [22_BH05_HANDOFF.md](22_BH05_HANDOFF.md): đã triển khai đăng ký/duyệt/huỷ/điểm danh/lời mời danh sách chờ (migration `20261015170500_bh05_registrations.sql`) với **116 Flutter + 227 DB PASS**, analyze sạch. Giới hạn còn lại: chưa kiểm PostgREST HTTP/JWT thật, thiết bị thật và chưa apply production. Giữ regression trước khi sang BH-06.

## Mới nhất — sau review tích hợp và hồi quy main BH-05 (16/10/2026)

Review tích hợp [review_d769531.md](reviews/bh05/review_d769531.md) kết luận **Đạt tích hợp BH-05 A+B+C** tại `d769531`, thay cho kết luận "Chưa đạt" trước đó ([review_c7ed6d5.md](reviews/bh05/review_c7ed6d5.md), lỗi I1/I2 đã sửa ở `a41b48a`). Hồi quy trên `main` tại `3a34883` ([review_main_3a34883.md](reviews/bh05/review_main_3a34883.md)): 137/137 Flutter, 251/251 DB, analyze sạch. Mục "Mới nhất — sau BH-05" ngay phía trên (116 Flutter + 227 DB) là snapshot trước tích hợp. Giới hạn còn lại: chưa kiểm PostgREST HTTP/JWT thật, thiết bị thật, chưa apply production. Ticket kế tiếp: BH-06.

## (Lịch sử) — chủ dự án xác nhận cập nhật sau audit (16/10/2026)

Chủ dự án duyệt toàn bộ B1–B9 và các đề xuất C1-01..04, C2-01. Đã cập nhật hợp đồng RPC/lời mời/start/finance gate, hash blob LF và lịch sử CRLF; các tài liệu chuẩn và bàn giao có chỉ dẫn trạng thái hiện hành. [Bảng theo dõi và điểm tiếp tục](23_DOC_AUDIT_FOLLOWUP.md) ghi việc đã áp dụng và phần chưa kiểm chứng. Báo cáo audit/review cũ giữ nguyên làm bằng chứng tại thời điểm rà soát; không còn dùng trạng thái “chờ chủ dự án quyết” trong audit cũ làm trạng thái hiện hành.

Tiếp tục BH-06, giữ regression 137 Flutter + 251 DB tại `3a34883`. Lượt này chỉ tài liệu, chưa chạy lại app/DB; HTTP/JWT thật, thiết bị/browser e2e, apply staging/production, backup/restore và concurrency qua HTTP vẫn NOT RUN.

## Giao việc tiếp tục BH-06 (16/10/2026)

Chủ dự án cho merge/push bộ tài liệu vào main và giao AI triển khai ở phiên mới làm BH-06 từng phần; Codex giao việc/review. [Đầu bài BH-06](24_BH06_IMPLEMENTATION_HANDOFF.md) ghi prompt A, cổng A/B/C/tích hợp và yêu cầu bằng chứng. Trạng thái đã giao A, chưa triển khai/chưa review; chưa chạy lại app/DB hoặc deploy trong lượt docs này.

## (Lịch sử bàn giao) BH-06 tích hợp chờ review (20/10/2026)

A `706bd73`, B `5e62007`, C `b31f988` đã Đạt theo từng phần; nhánh `feat/bh06-integration` tách từ tip C `a9c7edb` giữ nguyên các commit đã Đạt. Rà hợp đồng ba lớp phát hiện `receiver_snapshot` chưa từng được chốt, nên `has_receiver = false` và UI không dựng QR/nút gửi chuyển khoản; migration forward `20261020100000_bh06_integration_receiver.sql` vá lỗi này (chốt khi publish/start/complete, CLB trước/host fallback, không ghi đè snapshot cũ, điền cho buổi đang mở khi cấu hình ngân hàng sau). Test tái hiện FAIL tại `a9c7edb`; sau sửa tại code `8af7be5`/bằng chứng `6ecefb2`: analyze sạch, 189/189 Flutter, 335/335 DB, 6/6 case tích hợp DB. [Bàn giao và NOT RUN](reviews/bh06/integration_handoff.md). **Chờ review tích hợp**; chưa merge/deploy/apply, chưa cho phép deploy production.

## (Lịch sử) — review tích hợp BH-06 Chưa đạt (20/10/2026)

Reviewer kiểm độc lập `afeff39` trên `feat/bh06-integration`: analyze sạch, 189 Flutter +335 DB +6 case tích hợp PASS; probe nâng cấp receiver và widget version FAIL. [Báo cáo/bằng chứng](reviews/bh06/review_afeff39.md) mở I1 P1 (không backfill receiver cho buổi có sẵn) và I2 P2 (refresh không cập nhật version chốt phí). A/B/C giữ kết luận theo tested SHA trước; tiếp tục sửa theo review tích hợp, không merge/BH-07/deploy. HTTP/JWT thật, thiết bị/browser, ngân hàng/VietQR thật, staging/production, backup/restore và concurrency HTTP vẫn NOT RUN.

## (Lịch sử) — sửa review tích hợp BH-06 vòng 1 (20/10/2026)

Người triển khai sửa **cả I1 P1 và I2 P2** của [review afeff39](reviews/bh06/review_afeff39.md) trên `feat/bh06-integration`, code/test/migration `31a553c`. I1: forward migration `20261020160000_bh06_integration_receiver_backfill.sql` backfill receiver cho buổi `published/in_progress/completed` còn NULL, dùng cùng resolver CLB→host, không ghi đè snapshot/FK đã chốt, buổi không bank giữ NULL. I2: `20261020170000_bh06_finance_session_version.sql` trả `session_version` trong `get_session_finance`; UI dùng version này cho `expectedVersion`, refresh sau `VERSION_CONFLICT` lấy được version mới.

Test tái hiện FAIL trước sửa: nâng cấp DB vẫn `has_receiver=false`; widget conflict refresh vẫn gửi version 3 (`Expected [3,4]`, `Actual [3,3]`). Sau sửa trên `31a553c`: analyze sạch, **190/190 Flutter**, **335/335 DB**, **7/7 case tích hợp**, **3/3 case nâng cấp** (backfill, không bank, snapshot cũ bất biến). [Bàn giao, bảng lệnh và NOT RUN](reviews/bh06/integration_handoff.md). Trạng thái **Chờ review vòng 1**; chưa merge/deploy/apply, không tự ghi Đạt.

## (Lịch sử) — Đạt review tích hợp BH-06 vòng sửa 1 (20/10/2026)

Reviewer kết luận **Đạt tích hợp local tại `318bc52`**, code/test/migration `31a553c`, theo [review/bằng chứng](reviews/bh06/review_318bc52.md). Đóng I1/I2. Reviewer tự chạy analyze sạch, 190 Flutter +335 DB, 7 case tích hợp, 3 case nâng cấp và 2 probe độc lập PASS. Giữ review trước và kết luận từng phần A/B/C làm lịch sử. HTTP/JWT/Auth thật, thiết bị/ngân hàng thật, staging/production, backup/restore và concurrency HTTP vẫn NOT RUN; không tự merge main, chuyển BH-07 hoặc deploy.

## (Lịch sử) — BH-06 merge main, chuẩn bị BH-07A (20/10/2026)

Theo yêu cầu chủ dự án, main đã nhận docs/ai tại eaeb209 và BH-06 tại **e7f7627** (parents eaeb209 và b3bcfbb). Lib/test/migration trùng bản Đạt 318bc52; [xác minh merge](reviews/bh06/main_merge_e7f7627.md) phân biệt kiểm tra mới với DB bằng chứng cũ. Đã đồng bộ README, AGENTS, trạng thái docs và [đầu bài BH-07A](25_BH07_IMPLEMENTATION_HANDOFF.md). Chưa triển khai/nghiệm thu BH-07 hoặc apply staging/production; merge code không phải deploy.

## (Lịch sử) — BH-07A Đạt phần A local (20/10/2026)

Reviewer kiểm độc lập 4512c3a trên feat/bh07a-db và kết luận **Đạt A** theo [review/bằng chứng](reviews/bh07/review_4512c3a.md). Analyze sạch, 190 Flutter +335 DB hồi quy +23 BH-07, 7 tích hợp +3 nâng cấp BH-06 và 9 kiểm tra RPC độc lập PASS. Không sửa lib/test/migration; B/C/D và pilot chưa nghiệm thu. Chưa merge main/deploy/apply staging/production; HTTP/JWT/Auth thật, thiết bị/ngân hàng thật và backup/restore vẫn chưa nghiệm thu.

## (Lịch sử bàn giao) — BH-07B Chờ review (20/10/2026)

Người triển khai bàn giao B trên `feat/bh07b-data`, base `fd38838`, tested code `89e1d8f`, theo [bàn giao](reviews/bh07/bh07b_handoff.md). Tự chạy analyze sạch, **211/211 Flutter**, **23/23 BH-07**, **335/335 DB hồi quy**, **7/7 tích hợp**, **3/3 nâng cấp**; reviewer chưa chạy lại B. Chỉ model/repository/provider, không sửa migration/RPC A, không UI C/pilot D. **Chờ review BH-07B**; chưa Đạt, chưa chuyển C/D, chưa merge main/deploy/apply staging/production.

## (Lịch sử) — BH-07B Chưa đạt tại 1298490 (20/10/2026)

Reviewer kiểm độc lập đúng tip 1298490, source trùng 89e1d8f và mở B1/B2 P2 theo [review/bằng chứng](reviews/bh07/review_1298490.md). Analyze sạch, 211 Flutter +335 DB +23 BH-07, 7 tích hợp +3 nâng cấp BH-06 PASS; probe provider 4 PASS/2 FAIL. B1: summary/permission cache còn sau FORBIDDEN; B2: history trùng ID khi OFFSET dịch do buổi mới chen đầu. A giữ Đạt; chỉ sửa B theo quy trình, không tự chuyển C/D, merge main hoặc deploy. Các cổng HTTP/JWT/Auth, UI/thiết bị/ngân hàng thật và pilot chưa nghiệm thu.

## (Lịch sử) — BH-07B sửa review vòng 1/2, Chờ review (20/10/2026)

Người triển khai đã sửa B1/B2 P2 trên `feat/bh07b-data`, tested code **`a682007f6cd85931b410ec2930fd40cdd3fc73f4`**, theo [bàn giao sửa](reviews/bh07/bh07b_fix_handoff.md). Test-first `prefix.log` exit 1 với đúng 2 FAIL; sau sửa targeted 58/58, probe reviewer phát lại 6/6. Final: analyze sạch, **212/212 Flutter**, **23/23 BH-07**, **335/335 DB hồi quy**, **7/7 tích hợp**, **3/3 nâng cấp**; reviewer chưa chạy lại vòng 1. **Chờ review BH-07B vòng 1**; chưa Đạt, chưa chuyển C/D, chưa merge main/deploy/apply staging/production.

## (Lịch sử) — BH-07B Đạt local vòng 1/2 (20/10/2026)

BH-07B **Đạt phần B local tại `d7bac04`**, tested code `a682007`, vòng sửa 1/2; reviewer đóng B1/B2 P2 theo [review độc lập](reviews/bh07/review_d7bac04.md). Tự chạy analyze sạch, **212 Flutter +335 DB hồi quy +23 BH-07**, **7 tích hợp +3 nâng cấp BH-06**, **6/6 probe gốc PASS**. A giữ Đạt; C/D, toàn BH-07 và pilot chưa nghiệm thu. Không tự chuyển phần, merge main hoặc deploy.

Checkout ban đầu sạch, nguồn trùng a682007 và không đổi sau kiểm thử; mọi runner exit 0. Chỉ commit/push báo cáo, bằng chứng, trạng thái trên feat/bh07b-data. Giữ NOT RUN theo review.

## (Lịch sử bàn giao) — BH-07C Chờ review (21/10/2026)

BH-07C **Chờ review** tại tested code `15ae1af0d9d39678f4b9d99fabc9e9e22cb860ba` trên `feat/bh07c-ui`, base `cf95d76`, theo [bàn giao](reviews/bh07/bh07c_handoff.md). Phạm vi chỉ UI: lịch sử có filter/pagination/refresh, tổng kết theo quyền, copy không lộ contact/bank và giữ tiền NULL là `—`, nút kết thúc buổi đúng gate management + in_progress + billing current + version server. Không sửa migration/RPC A, model/repository/provider B hoặc contract; start giữ hành vi cũ.

Kết quả người triển khai tự chạy: analyze sạch, **225/225 Flutter**, **23/23 BH-07 DB**; 335 DB hồi quy giữ baseline B, không chạy lại vì C không đổi DB/backend. A/B giữ Đạt; C chưa được reviewer kết luận, D và toàn BH-07/pilot chưa nghiệm thu. Không tự ghi Đạt, không chuyển D, không merge main/deploy. HTTP/PostgREST/JWT/Auth thật, thiết bị/browser/offline, ngân hàng/VietQR/webhook thật, staging/production, backup/restore và concurrency HTTP vẫn NOT RUN.

## (Lịch sử) — BH-07C Chưa đạt tại 15ae1af (21/10/2026)

BH-07C **Chưa đạt tại `15ae1af`** trên `feat/bh07c-ui` theo [review độc lập](reviews/bh07/review_15ae1af.md): C1/C2/C3 P2 (complete thiếu DTO version, lỗi refresh cache rỗng bị che, lọc ngày phụ thuộc múi giờ). Reviewer tự chạy analyze sạch, **225 Flutter +52 targeted C +23 BH-07 DB PASS**; probe UI **2 PASS/3 FAIL**, control ngày UTC+7 **1 PASS**. A giữ Đạt `4512c3a`; B giữ Đạt `d7bac04` (code `a682007`). Chỉ sửa C vòng 1/2, test đỏ trước sửa; không đổi A/B, chuyển D, merge main hoặc deploy. Các cổng môi trường thật và pilot vẫn NOT RUN. Đã được thay bằng mục sửa vòng 1/2 ở đầu tài liệu.

## (Lịch sử) — BH-07C Đạt local vòng 1/2 tại 02a9b85 (21/10/2026)

BH-07C **Đạt local vòng 1/2 tại `02a9b85`** theo [review độc lập](reviews/bh07/review_02a9b85.md), đóng C1/C2/C3 P2; không có P0/P1/P2 mới trong phạm vi sửa. Reviewer tự chạy analyze sạch, **230 Flutter**, **57 targeted C mỗi múi giờ UTC/Asia_Ho_Chi_Minh**, **23 BH-07 DB**, **5 probe UI mỗi múi giờ** PASS. A giữ `4512c3a`; B giữ `d7bac04` (code `a682007`). D, toàn BH-07/pilot và các cổng môi trường thật chưa nghiệm thu; không tự chuyển D, merge main hoặc deploy. Bảy log gốc đã bổ sung tại `3d5583b`, reviewer kiểm hash/count khớp; xem phụ lục review_02a9b85_logs_3d5583b.md.

## Bổ sung log gốc BH-07C — 3d5583b (21/10/2026)

Reviewer xác nhận đủ bảy log, hash nguyên bytes khớp manifest f63e5a4, count/exit khớp tự báo. [Phụ lục](reviews/bh07/review_02a9b85_logs_3d5583b.md). Đóng ghi chú thiếu log; C giữ Đạt local02a9b85. Không chạy test mới, không đổi code hoặc các cổng NOT RUN.

## (Lịch sử) — BH-07D Đạt tích hợp local tại 3d590a8 (21/10/2026)

BH-07D **Đạt tích hợp local tại `3d590a8`** theo [review độc lập](reviews/bh07/review_3d590a8.md), không có P0/P1/P2 mở trong phạm vi được giao. Reviewer tự chạy analyze sạch, **240 Flutter**, **10 D +50 C mỗi múi giờ UTC/Asia_Ho_Chi_Minh**, **23 BH-07 DB**, **6 probe reviewer** PASS. A giữ `4512c3a`; B giữ `d7bac04` (code `a682007`); C giữ `02a9b85`. HTTP/JWT/Auth thật, thiết bị/browser/offline, ngân hàng, staging/production/backup, concurrency HTTP và rehearsal/pilot vẫn NOT RUN; toàn BH-07 chưa nghiệm thu. Không tự merge main, apply DB thật hoặc deploy.

Chỉ publish báo cáo/bằng chứng/trạng thái trên feat/bh07-integration; không đổi nguồn triển khai.

## (Lịch sử) — HTTP/Auth BH-07 Chưa đạt3ad25a4 (21/10/2026)

Kiểm chứng **HTTP/Auth BH-07 Chưa đạt tại `3ad25a4`**, docs/evidence `c54b004`, theo [review độc lập](reviews/bh07/review_3ad25a4.md): H1/H2 P2 về fixture free-current thiếu charge0 và assertion privacy chưa bao phủ raw payload. Reviewer tự chạy **65/65 HTTP check** qua GoTrue/PostgREST/Kong/PostgreSQL17.11 thật trên stack Linux riêng; analyze sạch, **240 Flutter +1 skip**, **23 BH-07 DB PASS**. Lệnh Windows/full Supabase CLI recipe chưa tái lập trên reviewer; khác biệt môi trường ghi rõ trong review. A/B/C/D local giữ kết luận trước; toàn BH-07/pilot chưa nghiệm thu. Chỉ sửa gói kiểm chứng vòng1/2; không đổi contract/backend/UI, merge main, apply DB thật hoặc deploy.

## Hiện hành — HTTP/Auth BH-07 Đạt local vòng1/2 f9159dd (21/10/2026)

Gói kiểm chứng **HTTP/Auth BH-07 Đạt local vòng1/2 tại `f9159dd`**, docs/evidence `0758b72`, theo [review độc lập](reviews/bh07/review_f9159dd.md): đóng H1/H2 P2, không có P0/P1/P2 mới trong phạm vi sửa. Reviewer tự chạy **70/70 HTTP check** trên stack Linux GoTrue/PostgREST/Kong/PostgreSQL17.11 thật; analyze sạch, **240 Flutter +1 skip**, **23 BH-07 DB**, **4 probe validator** PASS. Manifest tác giả21/21 khớp LF. A/B/C/D local giữ kết luận trước; **toàn BH-07/pilot chưa nghiệm thu**, không chuyển ticket sang hoàn thành. Các cổng thiết bị/browser/offline, ngân hàng, staging/production/backup, concurrency HTTP và rehearsal/pilot vẫn NOT RUN; không tự merge/apply DB thật/deploy.
