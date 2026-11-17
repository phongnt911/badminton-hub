# Bàn giao AGY: Tùy chọn `include_club_bank` cho BH-07 Club Bank Listener — Sửa vòng 1/3 CB1 P1 (17/11/2026)

## 1. Phạm vi và tệp thay đổi
- Tham chiếu review vòng 1: [club_bank_fixture_review_r1_20261117.md](club_bank_fixture_review_r1_20261117.md) và kế hoạch [2026-11-17-bh07-club-bank-listener.md](../../superpowers/plans/2026-11-17-bh07-club-bank-listener.md).
- Chỉ sửa đúng 2 tệp fixture/test và tài liệu bàn giao này (để uncommitted, không đụng `lib/`, `supabase/`, tài liệu Codex, hay bằng chứng lịch sử):
  - [disposable_instructions_fixture.py](../../../scripts/bh07_appheap/disposable_instructions_fixture.py)
  - [test_payment_instructions_heap.py](../../../scripts/bh07_appheap/test_payment_instructions_heap.py)
  - [club_bank_listener_handoff_20261117.md](club_bank_listener_handoff_20261117.md)

## 2. Bản sửa CB1 P1 và chuẩn hóa hợp đồng (vòng 1/3)
- **Khóa hàng SQL tối thiểu chỉ trong nhánh opt-in (`include_club_bank=True`):**
  - Ngay sau `BEGIN;` (trước mọi kiểm tra sở hữu `DO $$` và toàn bộ `DELETE`), giao dịch cleanup thực hiện tuần tự:
    1. `SELECT id FROM public.clubs WHERE id = <club_id> FOR UPDATE;` nhằm khóa hàng cha `clubs` trước để chặn `FOR KEY SHARE` từ `INSERT`/`UPDATE` FK `club_bank_accounts(club_id)` đồng thời đến khi xóa `clubs` và `COMMIT;`.
    2. `SELECT id FROM public.club_bank_accounts WHERE id = <bank_id> OR club_id = <club_id> ORDER BY id FOR UPDATE;` nhằm khóa các hàng bank liên quan trước khi đánh giá điều kiện sở hữu các cột có thể thay đổi.
  - Khối `DO $$` ngay sau hai câu lệnh khóa đánh giá lại toàn bộ điều kiện sở hữu/số lượng trong transaction, và các khóa được giữ liên tục tới `COMMIT;`.
  - Nhánh mặc định tắt (`include_club_bank=False`) giữ nguyên hoàn toàn SQL/state cũ (không thêm `FOR UPDATE`, không truy vấn `public.club_bank_accounts`).
- **Đồng nhất `status = 'active'` và giới hạn phát biểu kiểm tra mutation:**
  - Bổ sung `AND status = 'active'` nhất quán ở cả `_query_ownership`, khối `DO $$` trong `delete_sql`, và điều kiện `DELETE FROM public.club_bank_accounts` (cùng `club_id`, `bank_code`, `account_number`, `account_name`).
  - Phạm vi kiểm tra thực tế của `check_zero_mutations`: hàm chỉ kiểm tra 4 bộ đếm `payments`, `club_transactions`, `audit_events`, `operation_requests` cộng thêm đối chiếu danh tính/sở hữu hiện hành (`club_id`, `bank_code`, `account_number`, `account_name`, `status = 'active'`), **không** kiểm tra `created_at`/`updated_at` hay lịch sử cập nhật ngoài 4 bảng trên (biến động bảng `public` sau cùng được đối chiếu qua baseline fingerprint).
- **Trung thực về kiểm chứng đồng thời trên mock (`FakeDb`):**
  - `FakeDb` chỉ kiểm chứng thứ tự câu lệnh SQL `FOR UPDATE`, hành vi bảo toàn nhánh default-off, từ chối sửa `status='inactive'`, và tình huống TOCTOU giả lập (`on_before_delete_locks` chen ghi giữa `_query_ownership`/`check_zero_mutations` và `delete_sql`). `FakeDb` **không** chứng minh cơ chế khóa `FOR UPDATE` / `KEY SHARE` thực tế của PostgreSQL đa kết nối; probe hai kết nối trên DB cục bộ do Codex thực hiện riêng.

## 3. Kiểm thử đã chạy
- **RED (trước khi sửa `disposable_instructions_fixture.py`):**
  - `python -X utf8 -m unittest scripts.bh07_appheap.test_payment_instructions_heap -v` → thoát mã `1` (`Ran 28 tests in 24.129s`, `FAILED (failures=1, errors=4)`): 21 test cũ và các test collision/default-off pass; các test đụng `_query_ownership`/`delete_sql` opt-in và test `test_include_club_bank_row_lock_order_and_toctou_interleaving_control` fail đúng kỳ vọng do thiếu `status = 'active'` và `FOR UPDATE`.
- **GREEN (sau bản sửa cuối):**
  - `python -X utf8 -m unittest scripts.bh07_appheap.test_payment_instructions_heap -v` → thoát mã `0` (`Ran 28 tests in 26.359s`, `OK`: 21 test nền + 7 test `test_include_club_bank_*`, chạy trên `FakeDb` trong bộ nhớ).
  - `node scripts/bh07_appheap/session_club_auth_listener_controls.js` → thoát mã `0` (`ALL_SESSION_CLUB_AUTH_LISTENER_CONTROLS_PASS`).

## 4. Trạng thái runtime & nghiệm thu
- **Probe 2 kết nối DB cục bộ và runtime trình duyệt (`--require-bank-account`, `include_club_bank=true`): NOT RUN** (do Codex thực hiện riêng).
- **Chưa nghiệm thu:** Giữ nguyên các trạng thái evidence cũ; không suy ra PASS cho `BankAccount`, `auth_listeners`, BH-07, V2b hay V8; không commit/push/merge/deploy/pilot.
