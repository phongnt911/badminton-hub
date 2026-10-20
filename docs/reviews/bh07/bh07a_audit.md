# BH-07A — audit DB/RPC/projection (20/10/2026)

> **Reviewer 20/10/2026: Đạt phần A local tại `4512c3a`**, theo [review/bằng chứng](review_4512c3a.md). Chỉ DB/RPC/projection; B/C/D và pilot chưa nghiệm thu. Các trạng thái Chờ review và kết quả phía tác giả dưới đây giữ làm lịch sử. Không tự chuyển phần, merge main hoặc deploy.

Trạng thái: **Chờ review BH-07A**. Người triển khai không tự ghi Đạt/Done.

- Nhánh: `feat/bh07a-db`
- Base: `62d2c67dc66d512cf7f6f19932e2131ae060e2e9` (main sau merge BH-06 `e7f7627` và docs/ai `eaeb209`)
- Tested code SHA: `c339a47fdcb08e50811079bd89df7a1f9f53908a`
- Migration mới: `supabase/migrations/20261020180000_bh07_reads.sql`
- Runner: `docs/reviews/bh07/run_bh07_tests.py`
- Bằng chứng: `docs/reviews/bh07/evidence/`

## 1. Phạm vi đã rà

Chỉ phần A: complete, lịch sử/chi tiết, tổng kết, công nợ và các thao tác tài chính sau complete.
Không sửa UI, model/repository/provider, partition B/C/D, BH-08/BH-09, không merge main,
không apply staging/production.

## 2. Đã có / còn thiếu

| Năng lực | Hiện có trước BH-07A | Kết luận | Thay đổi BH-07A |
|---|---|---|---|
| `complete_session` | BH-06: auth, quản lý buổi, chỉ `in_progress`, `expected_version`, gate `billing_state=current`, idempotency, audit; trả public detail | Đủ contract, không cần sửa | Không đổi; thêm test replay/version/ACL/concurrency |
| Buổi miễn phí | Revision current với charges 0 vẫn complete được | Đủ | Không đổi; test riêng |
| Công nợ sau complete | `get_session_finance` trả charges/payments/outstanding; complete không thu tiền | Đủ dữ liệu, nhưng DTO tài chính không có present count/tổng đã thu gọn cho tổng kết | Giữ nguyên finance; thêm projection summary |
| Lịch sử sau complete | `list_my_sessions` trả cả completed/cancelled, có phân trang, ACL host/management/finance | Đọc được nhưng trộn buổi sắp tới/lịch sử và không lọc lifecycle/ngày/CLB; client phải đọc rộng | Thêm `list_my_session_history` |
| Chi tiết sau complete | `get_session_public_detail` giữ lifecycle, count; private check quyền; không lộ bank/contact | Đủ | Không đổi; test sau complete/private/anon |
| Tổng kết | Chưa có RPC tổng hợp; UI sẽ phải ghép finance + danh sách người, dễ lộ contact hoặc tính thiếu do phân trang | Thiếu projection an toàn | Thêm `get_session_summary` |
| Sao chép tổng kết | Chưa có; C sẽ làm UI | A cần dữ liệu server đúng scope | Summary chỉ trả aggregate, không contact/bank/per-player |
| Submit/confirm/cash sau complete | BH-06 cho phép khi billing current; giữ payment/ledger | Đủ, không nới gate | Không đổi; test sau complete + retry + ledger |
| Reject/reverse sau complete | BH-06 cho phép theo trạng thái payment; reverse một lần, giữ nguồn | Đủ | Không đổi; test sau complete |
| Refinalize sau complete | BH-06 cho phép `in_progress/completed`, cần lý do; không giảm due dưới paid | Đủ | Không đổi; test sau complete và trường hợp bị chặn |
| Chi phí sau complete | `post_session_expense` bị chặn; `reverse_session_expense` được phép và làm stale | Đúng contract | Không đổi; test |
| Idempotency/audit/version | `operation_requests`, audit, session lock, expected version | Đủ | Không đổi; test replay/conflict/concurrency DB |
| Quyền đọc | Host/cohost/CLB owner; treasurer/staff finance; participant/outsider bị chặn | Đủ cho list/detail; summary/history mới cần ACL riêng | Thêm test chéo CLB, participant, outsider, anon |

## 3. Contract thực tế của phần bổ sung

### `get_session_summary(p_session_id UUID) -> JSONB`

- Actor bắt buộc đăng nhập; phải là management (host/cohost/CLB owner) hoặc finance
  (host/CLB owner/treasurer/staff finance). Participant, outsider, cross-club và anon bị chặn.
- Trả: `session_id`, `title`, `club_id`, `club_name`, `venue_name`, `starts_at`, `ends_at`,
  `lifecycle`, `fee_mode`, `session_version`, `can_manage`, `can_view_finance`,
  `present_count`, `no_show_count`, `confirmed_count`.
- Chỉ khi `can_view_finance=true` mới trả: `billing_state`, `active_revision_id`, `revision_no`,
  `source_version`, `expenses_total_vnd`, `amount_due_total_vnd`, `total_paid_vnd`,
  `outstanding_total_vnd`. Management-only nhận các khóa này là `null`.
- `total_paid_vnd` là tổng payment `confirmed` của mọi player trong buổi; `outstanding_total_vnd`
  tính trên active revision như `get_session_finance`; `expenses_total_vnd` chỉ expense `posted`.
- Không suy `outstanding = due - paid` ở UI khi có overpayment hoặc payment của người không còn
  trong revision; ba số `amount_due_total_vnd`, `total_paid_vnd`, `outstanding_total_vnd` là độc lập.
- Không trả contact, số tài khoản/ngân hàng, receiver snapshot, danh sách player,
  charges/payments thô. `billing_state` stale/not_finalized được trả đúng nhãn, không giả current.

### `list_my_session_history(p_limit, p_offset, p_club_id, p_from, p_to) -> JSONB`

- Chỉ `completed`/`cancelled`; actor phải là host/management/finance của từng buổi.
- Sắp xếp `starts_at DESC, id DESC`; `p_limit` mặc định 20, clamp 1..100; `p_offset >= 0`.
- `confirmed_count` tính sau khi phân trang; filter CLB/khoảng ngày trước khi trả.
- Cùng whitelist field với `list_my_sessions` (không contact/bank).
- `list_my_sessions` giữ nguyên cho tab tổng hợp sắp tới/đang mở; không thay signature cũ.

## 4. Quyết định thiết kế

1. Không sửa `complete_session` hoặc gate tài chính vì code hiện có đã đúng contract và test
   BH-06 bao phủ. Chỉ thêm test hồi quy cho complete/debt/retry/concurrency.
2. Không mở rộng `get_session_finance` thành màn tổng kết vì DTO này chứa charges/payments thô
   và có phân trang; thêm `get_session_summary` aggregate-only giảm nguy cơ C tự tính từ trang bị cắt
   hoặc lấy contact từ roster.
3. Management-only thấy count nhưng không thấy tiền; finance thấy tiền nhưng không cần quyền
   quản lý roster. Điều này khớp ma trận quyền hiện hành, không tạo quyền mới.
4. Lịch sử có RPC riêng thay vì lọc client trên `list_my_sessions`, vì lọc client sẽ đọc cả
   buổi sắp tới và có thể bỏ sót khi phân trang. Không đổi `list_my_sessions` để tránh ảnh hưởng
   màn hiện tại.
5. Không thêm cột/bảng/backfill. Migration chỉ `CREATE OR REPLACE`/tạo RPC đọc mới, giữ
   forward-only và không ghi dữ liệu.

## 5. Test-first và kết quả

- Trước migration: runner mới có **22 ca, 9 PASS / 13 FAIL**. Các FAIL chính do thiếu
  `get_session_summary`/`list_my_session_history` và một truy vấn test lấy `id` mơ hồ; log
  `evidence/bh07_prefix.log`, JSON `evidence/bh07_prefix_results_20261020100620.json`.
- Sau migration + sửa truy vấn test: **23/23 PASS** (21 ca CLEAN + 2 ca upgrade), log
  `evidence/bh07_final_run.log`, JSON `bh07_test_results_20261020101646.json`.
- Các ca bao phủ: complete gate/ACL/free/debt/replay/version/concurrency; history/detail/list
  sau complete; summary aggregate/privacy/role/stale; submit/confirm/cash/reject/reverse/refinalize
  sau complete; upgrade dữ liệu completed cũ.

## 6. NOT RUN / giới hạn

- HTTP/PostgREST/JWT/Supabase Auth thật; repository/provider/UI thật.
- Thiết bị/browser/deep link, mất mạng/mở lại app.
- Ngân hàng/VietQR thật, webhook/chuyển tiền.
- Apply staging/production, backup/restore rehearsal, concurrency qua HTTP.
- Probe độc lập của reviewer (không chạy lại 2 probe lịch sử BH-06).

Các kết quả trên chỉ là PostgreSQL local + Auth stub, không thay cổng HTTP/pilot.
