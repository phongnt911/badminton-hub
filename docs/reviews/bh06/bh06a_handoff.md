# BH-06A — bàn giao cho review độc lập

Trạng thái: **Chờ review** (người triển khai không tự ghi Đạt). Ngày 16/10/2026.

- Nhánh: `feat/bh06a-db`, tách từ `main` = `c35dd27` (không làm việc trên `main`).
- Commit mã: `c929b67` (helper + chi phí + chốt phí + complete gate), `d7deaae` (thanh toán + quỹ CLB), `fe8cf99` (đường đọc/QR), `9336bb0` + `947f8ae` (runner DB, bổ sung ca ACL ghi trực tiếp/helper và gỡ bằng chứng cũ).
- Phạm vi: chỉ phần A theo [24_BH06_IMPLEMENTATION_HANDOFF.md](../../24_BH06_IMPLEMENTATION_HANDOFF.md). Không làm B (model/repository/provider) hay C (UI VietQR/sổ quỹ); không merge `main`; không deploy.

## Migration

| File | Nội dung |
|---|---|
| `supabase/migrations/20261016110000_bh06_expenses_finalize.sql` | helper trạng thái chốt phí, `post_session_expense`, `reverse_session_expense`, `finalize_session_charges`, `complete_session` |
| `supabase/migrations/20261016120000_bh06_payments_ledger.sql` | `submit_payment`, `confirm_payment`, `reject_payment`, `reverse_payment`, `record_cash_payment`, `post_manual_club_transaction`, `reverse_club_transaction` |
| `supabase/migrations/20261016130000_bh06_reads.sql` | `get_payment_instructions`, `get_session_finance`, `get_club_ledger` |

Forward-only; không sửa migration đã chia sẻ. Hợp đồng chữ ký/ACL/mã lỗi đầy đủ ở [docs/08 §13](../../08_DOMAIN_CONTRACTS.md).

## Sửa theo review vòng 1 (16/10/2026)

[Review `e3c73c1`](review_e3c73c1.md) kết luận **Chưa đạt** với 2 phát hiện P1. Đã sửa cả hai trong nhánh này (chi tiết: [bh06a_review_round1.md](bh06a_review_round1.md)):

- Commit `59baa25`: thêm 2 ca tái hiện vào `run_bh06_tests.py` (FAIL trước khi sửa) — R1 outsider/cohost đọc công nợ khách offline `user_id=NULL`; R2 RPC bank cũ (BH-02) chưa gate not_finalized/stale.
- Commit `83586ed`: migration forward [`20261016140000_bh06a_review_round1.sql`](../../../supabase/migrations/20261016140000_bh06a_review_round1.sql) — (R1) `get_payment_instructions` kiểm quyền null-safe; (R2) `get_session_payment_instructions` gate `assert_billing_current`. Không sửa ba migration BH-06A đã chia sẻ.
- Bằng chứng trên cây sạch `83586ed`: analyze 0 issue; `flutter test` 137/137; runner BH-06 **84/84 PASS** (42 × CLEAN/LEGACY, `worktree_dirty=false`) → [`bh06_test_results_20261016151610.json`](bh06_test_results_20261016151610.json). Hồi quy BH-02..05 xanh lại (33+14, 48+22, 44, 90).
- Trạng thái: **Chờ review vòng 1**.

## Bằng chứng (cây `947f8ae`)

- `flutter analyze`: 0 issue.
- `flutter test`: 137/137 PASS (A không chạm Dart nên không đổi).
- `python docs/reviews/bh06/run_bh06_tests.py`: **80/80 PASS** (40 kịch bản × CLEAN/LEGACY), `tested_commit=947f8aeb211f002c3f4525a87aebfcd2ca5e6a55`, `worktree_dirty=false`. JSON: [`bh06_test_results_20261016042103.json`](bh06_test_results_20261016042103.json).

## Quyết định cần reviewer xác nhận

1. **Chữ ký đọc QR**: §5 đề xuất `get_payment_instructions(player_id)`; hiện thực dùng `get_payment_instructions(p_session_id, p_player_id?)` (NULL = chính actor) để khớp quyền/phiên. RPC cũ `get_session_payment_instructions(p_session_id)` (BH-02) **giữ nguyên** làm đường đọc bank snapshot — nó không trả số tiền/mã tham chiếu nên không thể dùng để thu sai khi stale. Đề nghị chấp nhận hoặc yêu cầu thay/gỡ.
2. **`complete_session` trong A**: chỉ gate + đổi lifecycle (`in_progress` → `completed`, cần revision `current`, không yêu cầu thu đủ tiền) để "bảo vệ hợp đồng complete" theo item 5 của đầu bài; UI/lịch sử/pilot BH-07 **chưa** làm.
3. **Không bump `billing_input_version` trong `update_session`**: `update_session` chỉ chạy ở `draft/published` (trước khi có revision), nên không làm revision đã chốt trở nên stale; mọi nguồn đổi input sau khi chốt (chi phí, roster confirmed, điểm danh) đều bump.
4. **Thứ tự ưu tiên lỗi khi chốt lại**: `NO_BILLABLE_PLAYERS` được kiểm trước đối chiếu tiền đã thu. Với tình huống vừa "không còn người chịu phí" vừa "đã thu tiền của người bị loại", hệ thống trả `NO_BILLABLE_PLAYERS`; cả hai đều chặn và không mất tiền (đã thu giữ nguyên). Ca `INVALID_STATE` (due mới < paid) dùng kịch bản còn billable player.
5. **`p_method` của `submit_payment`**: chỉ nhận `bank_transfer`; tiền mặt đi qua `record_cash_payment` theo §4.

## NOT RUN / giới hạn

- PostgREST HTTP/JWT thật (chỉ PostgreSQL cô lập + Auth stub), apply staging/production, thiết bị/browser e2e, backup/restore, concurrency qua HTTP.
- UI VietQR/sổ quỹ và model/repository/provider (phần B/C), lịch sử/công nợ sau complete (BH-07).
- Chưa chạy lại runner BH-02..05 trên nhánh này (chưa giao cổng review; chuỗi migration chỉ thêm 3 file forward-only).
