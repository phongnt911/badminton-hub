# BH-06 — giao việc triển khai phí, VietQR, thu tiền và quỹ

Ngày 16/10/2026 (Việt Nam). Chủ dự án đã giao: merge bộ docs sau BH-05 vào main, để **phiên mới của AI triển khai** kéo main và làm BH-06 từng phần; Codex phiên này **giao việc và review độc lập**, không viết code triển khai. Trạng thái 20/10/2026: BH-06A **Đạt** tại `706bd73` ([review_706bd73](reviews/bh06/review_706bd73.md)); BH-06B (model/repository/provider) **Đạt phần B** tại `5e62007` ([review vòng 2](reviews/bh06/review_5e62007.md)), code sửa `58d03ca` ([ghi chú sửa vòng 1 B1/B2](reviews/bh06/bh06b_review_round1.md), [ghi chú sửa vòng 2 B2-R1](reviews/bh06/bh06b_review_round2.md), [bàn giao](reviews/bh06/bh06b_handoff.md); review vòng 1 [review_3894cb7](reviews/bh06/review_3894cb7.md)) trên `feat/bh06b-data` tách từ bản A đã Đạt `48d45d2`; BH-06C (UI phí/thu tiền/quỹ) **Đạt phần C tại `b31f988`** ([review độc lập](reviews/bh06/review_b31f988.md): đóng C4; C1/C2/C3 giữ đóng; analyze sạch, 187 Flutter +84 DB PASS, 8 widget probe PASS, RPC C2/C4 PASS; code sửa `bd17a95`, test `bfbd8f6`, [ghi chú C4](reviews/bh06/bh06c_c4_fix.md)) trên `feat/bh06c-ui` tách từ bản B đã Đạt `f28fd0f` ([bàn giao C](reviews/bh06/bh06c_handoff.md); commit `777f9df`, `39aef81`, `b123db9`); vòng 1 sửa C1/C2 P1 theo [review_af31e7b](reviews/bh06/review_af31e7b.md) tại code `8e3cd83` ([ghi chú sửa vòng 1](reviews/bh06/bh06c_review_round1.md)); vòng 2 sửa C3 P2 theo chỉ định của chủ dự án tại code `5174e9d` ([ghi chú sửa vòng 2](reviews/bh06/bh06c_review_round2.md)); tích hợp **Chưa đạt tại `afeff39`** theo [review độc lập](reviews/bh06/review_afeff39.md): I1 P1, I2 P2 còn mở; đã sửa cả hai ở vòng 1 tại `31a553c`, đang **chờ review lại** (xem đoạn dưới). BH-06B/C chỉ bắt đầu sau cổng review phần trước. Không coi việc publish đầu bài là hoàn thành BH-06 hoặc cho phép deploy.

> **(Lịch sử bàn giao) Tích hợp (20/10/2026): Chờ review tích hợp** trên `feat/bh06-integration` (base `a9c7edb`; code `8af7be5`, bằng chứng `6ecefb2`). Đã rà hợp đồng ba lớp và phát hiện lỗi tích hợp: `receiver_snapshot` chưa từng được chốt nên `has_receiver = false`, UI không dựng được QR/nút gửi chuyển khoản. Migration forward `20261020100000_bh06_integration_receiver.sql` chốt snapshot khi publish/start/complete (CLB trước, host fallback), điền cho buổi đang mở khi cấu hình ngân hàng sau, không ghi đè snapshot cũ. Bằng chứng: analyze sạch, 189/189 Flutter, 335/335 DB, 6/6 case tích hợp DB; chi tiết/NOT RUN tại [bàn giao tích hợp](reviews/bh06/integration_handoff.md). Chưa merge/deploy/apply; người triển khai không tự ghi Đạt.

> **Hiện hành tích hợp 20/10/2026: Chờ review vòng 1 sau sửa I1/I2** trên `feat/bh06-integration`, code/test `31a553c`. Theo [review afeff39](reviews/bh06/review_afeff39.md): I1 P1 thiếu backfill receiver cho buổi cũ; I2 P2 refresh không cập nhật session version. Đã thêm migration backfill `20261020160000_bh06_integration_receiver_backfill.sql` (chỉ buổi đủ điều kiện còn NULL, không ghi đè snapshot cũ) và `20261020170000_bh06_finance_session_version.sql` (DTO trả `session_version`, UI dùng cho chốt phí). Test tái hiện FAIL trước sửa; sau sửa analyze sạch, **190/190 Flutter, 335/335 DB, 7/7 tích hợp DB, 3/3 case nâng cấp DB**. Chi tiết/NOT RUN tại [bàn giao tích hợp](reviews/bh06/integration_handoff.md). Không tự merge/BH-07/deploy; người triển khai không tự ghi Đạt.

## 1. Baseline và nguồn yêu cầu

Bộ docs sau audit: `a7fed96`, các mục A/B/C đã áp dụng theo [xác nhận](23_DOC_AUDIT_FOLLOWUP.md). Bằng chứng code BH-05: [Đạt tích hợp d769531](reviews/bh05/review_d769531.md), [hồi quy main 3a34883](reviews/bh05/review_main_3a34883.md): analyze sạch, 137 Flutter + 251 DB. Chưa chạy lại các suite trong lượt giao việc chỉ tài liệu này; giữ regression, bổ sung test BH-06, không giữ nguyên tổng test bằng cách bỏ test cũ.

Đọc AGENTS, [docs/00](00_START_HERE.md), [quy tắc](04_LLM_RULES.md), [PRD](01_PRD_SPEC.md), [kiến trúc](02_ARCHITECTURE.md), [schema](03_DATABASE.md), [contracts §4–7 và §12](08_DOMAIN_CONTRACTS.md), [backlog BH-06/R4/R6](09_IMPLEMENTATION_PLAN.md), [screen flows](10_SCREEN_FLOWS.md), [ADR-02/04/08](11_ARCHITECTURE_DECISIONS.md), [AG-06](12_ANTIGRAVITY_PROMPTS.md), [PD-04](14_PRODUCT_LEARNINGS_VMITO_VUT.md#pd-04-qr-rõ-người-nhận-và-số-phải-thu-không-tự-suy-đã-thanh-toán), [handoff BH-05](22_BH05_HANDOFF.md).

Kiểm tra code/migration thật trước khi chọn signature. Schema tài chính đã có các bảng session_expenses/charge_revisions/session_charges/payments/club_transactions; không tạo lại. Đã có `get_session_payment_instructions(p_session_id)` từ nền BH-02, khác tên/input đề xuất `get_payment_instructions(player_id)` trong contract: kiểm caller/ACL/DTO, xác định cách chuyển đổi tương thích và ghi rõ trong contract, không bỏ đường đọc cũ để lọt gate stale. `start_session` đã có ở BH-05, không viết lại. Giữ Flutter + Provider + Supabase, không thêm dependency nếu chưa được giao.

## 2. Phiên triển khai mới: bắt đầu từ main sạch

Nếu checkout có thay đổi local, giữ nguyên và báo trước khi switch/pull; không reset/clean để làm mất công việc khác. Với checkout sạch:

```bash
git fetch origin
git switch main
git pull --ff-only origin main
git rev-parse HEAD
git switch -c feat/bh06a-db
```

Ghi HEAD main thực tế vào báo cáo, kiểm đã có tài liệu này và bộ docs sau audit. Nếu tên nhánh đã tồn tại thì kiểm tiến độ/HEAD của nó trước khi tiếp tục, không tạo lại hoặc ghi đè. Không chạy lại AG-00/BH-01..05; chỉ chạy baseline/regression cần thiết cho phần đang làm. Lệnh trên do AI triển khai ở **phiên mới** thực hiện, không phải nhánh đã được tạo bởi lượt giao việc.

## 3. Chia phần và cổng review

| Phần | Nhánh | Phạm vi | Cổng để đi tiếp |
|---|---|---|---|
| A | feat/bh06a-db | Migration forward, RPC/RLS/projection, runner DB và hợp đồng chính xác | Codex review đúng SHA, kết luận Đạt A trước khi bắt đầu B |
| B | feat/bh06b-data | Model/repository/provider typed, session/auth isolation, retry/idempotency, test dữ liệu/state | Tách từ bản A đã Đạt (hoặc main đã chứa A), ghi SHA phụ thuộc; Đạt B trước C |
| C | feat/bh06c-ui | UI phí/thu tiền/quỹ, QR thật/fallback, quyền/loading/error/empty/submitting, widget tests | Tách từ bản B đã Đạt (hoặc main đã chứa B); Đạt C chưa thay review tích hợp |
| Tích hợp | feat/bh06-integration | Ghép các bản A/B/C đã Đạt, test xuyên suốt client↔RPC và regression | Review độc lập chính cây tích hợp, không suy Đạt tích hợp từ Đạt từng phần |

Mỗi phần có commit riêng; A có thể tách các commit expenses/finalize, payments/ledger, reads/gates/tests để dễ review nhưng phải giữ trọn các invariant trước khi gửi A. Không tự merge main/deploy ở các phần triển khai. Nếu phạm vi cần thay đổi hợp đồng sản phẩm hoặc dependency, báo điểm cụ thể cho reviewer/chủ dự án, không tự mở rộng tính năng.

### A — việc được giao ngay

1. Kiểm schema/helpers hiện có, đọc grants/RLS/callers; ghi file dự kiến sửa và bảng signature input/output/error/ACL của RPC mới hoặc thay thế. Giữ helper nội bộ không callable từ client, actor từ auth.uid(), chỉ cấp quyền cần thiết. Dùng migration forward mới, không sửa lịch sử đã chia sẻ hoặc chạy SQL legacy.
2. Post/reverse expense: đúng quyền tài chính, amount nguyên VNĐ dương, expense và ledger CLB cùng transaction; buổi độc lập không tạo ledger CLB. Reverse có reason, giữ nguồn và entry đảo duy nhất, không xóa lịch sử. Mọi thay đổi input phí tăng billing_input_version trong transaction.
3. Finalize/refinalize: khoá và kiểm expected version/billing_input_version; tính server-side từ present/miễn phí/agreed fee/posted expenses. Chia dư nguyên VNĐ có thứ tự ID ổn định và ghi contract; tổng đúng allocation_total. Có chi phí nhưng không người chịu phí trả NO_BILLABLE_PLAYERS. Buổi miễn phí vẫn revision current/charges 0. Supersede revision cũ nguyên tử, mỗi new due phải đối chiếu confirmed payment, kể cả người bị loại khỏi tập billable; không làm mất tiền đã thu hoặc tạo ledger thu lặp.
4. Submit/confirm/reject/reverse payment và record_cash_payment: submitted chưa là đã trả; xác nhận thủ công đúng finance, tổng confirmed không vượt active due, cash tạo+confirm nguyên tử. Retry/replay không ghi thu kép, reverse cần reason và unique entry đảo, không đồng nghĩa hoàn tiền ngân hàng. Quỹ manual chỉ owner/treasurer; không cho client giả source_payment/source_expense hoặc ghi balance.
5. Reads/QR và gate current: xác định đủ các đường đọc bank/outstanding/revision, chỉ đúng player confirmed hoặc finance; không lộ contacts/bank qua projection public. Không revision trả BILLING_NOT_FINALIZED, stale trả BILLING_STALE với QR/submit/confirm mới/cash/complete; history/reject/reversal và replay đã committed còn hoạt động theo quyền. Bảo vệ contract complete ngay trong A, không để BH-07 có đường complete bypass; ghi rõ RPC/gate nào đã có và phần UI/history BH-07 chưa làm. Không triển khai rộng toàn bộ BH-07.
6. Kiểm mọi nguồn thay input: expenses, confirmed roster, attendance/exemption và cấu hình ảnh hưởng phí; giữ gate finance BH-05 sau active revision và idempotency canonical theo actor/operation/request. Cùng key khác payload phải conflict; lock order thống nhất và audit cùng transaction.
7. Thêm runner DB local/staging dùng fixture giả, role app thật dưới SET ROLE (Auth stub phải ghi rõ giới hạn), clean + legacy theo toàn chuỗi migration. Giữ regression BH-02..05, kiểm concurrency đa kết nối có kiểm soát, rollback và ACL; không chỉ test chuỗi SQL hoặc SELECT bằng postgres rồi kết luận đúng quyền.

### B — giao sau khi A Đạt

Dùng signature/DTO đã được review ở A; không gọi function chưa có. Repository typed cho fee/revision/expense/payment/ledger; provider loading/error/empty/submitting, giữ request ID qua lỗi/timeout, xoay key sau commit thành công trước refresh, không báo mutation thất bại chỉ vì refresh lỗi. Dọn state private khi logout/đổi actor/đổi session/club; loại phản hồi trễ. Phân trang reads đúng contract, không lấy empty do lỗi quyền làm số dư 0. Test thực hành vi retry/replay/double-submit/stale/auth isolation, không chỉ kiểm tên method.

### C — giao sau khi B Đạt

Nối phí/chi phí/miễn phí/chốt lại, gửi chuyển khoản chờ xác nhận, finance confirm/reject/cash/reverse, sổ quỹ theo role. Hiện bản chốt current/stale/not_finalized và outstanding có nguồn/version; giữ lịch sử, chặn thao tác thu mới khi stale. Dùng VietQRHelper hiện có; QR theo receiver snapshot + outstanding > 0 + reference đúng người/buổi, hiện bank/name/number/amount/reference có copy/fallback nếu ảnh không tải. QR không xác nhận đã thu, không webhook/ngân hàng, không tự chuyển tiền. Loading/error/retry/empty/submitting và permission-denied phải có widget test, kiểm player không thấy thao tác finance.

## 4. Ca bắt buộc trước kết luận Đạt A và tích hợp

| Nhóm | Bằng chứng cần có |
|---|---|
| Phân quyền/privacy | anon/outsider/player không ghi tiền, không tự confirm/giả actor/source; cohost không finance bị chặn; quyền finance buổi và owner/treasurer CLB đúng scope |
| Chia tiền | split 450.000/7 tổng chính xác, chia dư ổn định, fixed khác tổng expense được phép; exemption, không billable, total 0 |
| Revision/stale | expense/attendance/roster/exemption đổi sau finalize làm stale; chặn tất cả đường QR/thu mới/complete; refinalize current; version cũ conflict |
| Tiền đã thu | refinalize không giảm due dưới paid hoặc bỏ qua người đã thu nhưng nay no_show/exempt/cancel; không mất lịch sử payment/ledger |
| Đồng thời/idempotency | 2 confirm/cash tranh outstanding không thu dư; retry cùng key đúng response, khác payload conflict; reverse hai lần không đảo kép; lỗi giữa transaction rollback toàn bộ |
| Ledger | expense/payment CLB sinh đúng một entry; buổi độc lập không lẫn quỹ; manual và reverse có quyền/source/audit đúng |
| Replay/history | replay committed sau stale trả kết quả cũ có quyền; history/reject/reverse vẫn phục vụ đối soát; không biến sửa docs thành phép nới gate |
| Hồi quy | analyze sạch, Flutter baseline 137 được giữ cùng test mới, DB baseline 251 được giữ cùng test mới; không tự sửa expected để che lỗi |

Báo số PASS/FAIL/NOT RUN thực tế, commit/hash migration, công cụ/phiên bản, DB clean/legacy và Auth stub/full Supabase. Chưa có môi trường thì chuẩn bị được phần độc lập và ghi rõ test chưa chạy; không lấy production thay môi trường test. Không kết luận Đạt khi cổng kiểm chứng bắt buộc chưa có bằng chứng.

## 5. Bàn giao cho reviewer

Người triển khai ghi **Chờ review**, push đúng nhánh phần đang làm và gửi tên nhánh + full SHA + base/dependency SHA, diff phạm vi, danh sách migration/RPC, lệnh/exit/result, đường dẫn JSON/log, NOT RUN và config ngoài code. Bằng chứng đặt trong `docs/reviews/bh06/`, không ghi đè BH-05. Cập nhật docs/09 và handoff theo trạng thái thực tế, không tự ghi Done/Đạt.

Codex đọc diff ở đúng SHA, kiểm client↔RPC và tiền/quyền/cạnh tranh, tự chạy kiểm thử phù hợp khi môi trường cho phép; ghi `docs/reviews/bh06/review_<sha>.md`, mỗi phát hiện file:dòng/P0/P1/P2/cách sửa, kết luận Đạt/Chưa đạt cùng giới hạn. Không viết lại code triển khai thay AI được giao. Theo AGENTS, sửa các P0/P1 được giao bằng test tái hiện trước, tối đa hai vòng; P2 chỉ sửa khi được giao rõ. Sau hai vòng còn lỗi thì báo chủ dự án. Mỗi phần Đạt mới giao phần tiếp, tích hợp cần review riêng trước khi đề xuất merge main.

## 6. Prompt dùng cho phiên triển khai mới

> Vai trò: người triển khai BH-06A; Codex ở phiên giao việc là reviewer độc lập. Đọc AGENTS.md và docs/00_START_HERE.md, kéo main mới nhất trên checkout sạch rồi đọc docs/24_BH06_IMPLEMENTATION_HANDOFF.md và nguồn chuẩn được liên kết. Chỉ làm phần A trên feat/bh06a-db từ main, ghi base SHA, kiểm schema/helpers/callers hiện hữu, nêu file và RPC trước sửa. Triển khai forward migration + DB tests/contract cho fees/expenses/revisions/payments/ledger và gate current, giữ regression BH-02..05. Không làm B/C hoặc toàn bộ BH-07, không sửa migration cũ, không test/apply production. Chạy analyze/Flutter/DB runner phù hợp, ghi PASS/FAIL/NOT RUN và bằng chứng; cập nhật docs trạng thái Chờ review, commit/push nhánh rồi gửi full SHA cho Codex review. Không tự ghi Done/Đạt, merge main hoặc deploy.
