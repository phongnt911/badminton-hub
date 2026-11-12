# Bàn giao ứng viên gia cố Staging (Staging Hardening Candidate) — Vòng sửa 2, 12/11/2026

Tài liệu này cập nhật sau [review vòng 2](staging_hardening_review_r2_20261112.md) và tích hợp kết quả thực thi kiểm thử cục bộ của Codex tại [staging_hardening_local_runtime_20261112.md](staging_hardening_local_runtime_20261112.md).

---

## 1. Khắc phục phát hiện vòng 2

1. **Khắc phục Static Allowlist trong test tĩnh**:
   * **Nguyên nhân**: `re.search` trước đây không neo (`^...$`), dẫn đến việc chèn thêm grantee (ví dụ `TO authenticated, anon;`), thêm schema vào `search_path` hoặc thêm mệnh đề vẫn vượt qua regex.
   * **Khắc phục**: Thay thế bằng kiểm tra toàn bộ câu lệnh (whole-statement matching qua `re.fullmatch`), neo chặt chẽ từ đầu đến cuối câu lệnh, chuẩn hóa khoảng trắng và bổ sung bộ kiểm thử mutant trực tiếp (`test_mutant_controls_reject_permissive_modifications`) trong [test_bh07_staging_hardening.py](../../../tests/test_bh07_staging_hardening.py). Bất kỳ đột biến nào (thêm grantee, thêm schema, thêm mệnh đề, sai lệch số lượng 22 câu lệnh) đều bị từ chối fail-closed.
   * Loại bỏ test kiểm tra đường dẫn candidate tautological để tập trung và tinh gọn bộ test.

2. **Thay thế khối SQL đề xuất chưa chạy bằng Artifacts thực tế của Codex**:
   * Loại bỏ toàn bộ đoạn mã SQL giả định chưa chạy ở vòng 1 (đoạn mã có lỗi giả định về schema như `profiles` thiếu `auth.users` FK và câu lệnh `sessions` hiện đại không kích hoạt trigger legacy).
   * Thay thế bằng liên kết dẫn xuất tới [staging_hardening_local_probe_20261112.py](staging_hardening_local_probe_20261112.py) có thể thực thi đầy đủ và [biên nhận đạt PASS](staging_hardening_local_pass_20261112.json).

---

## 2. Kết quả thực thi kiểm thử cục bộ của Codex

Theo [báo cáo runtime cục bộ](staging_hardening_local_runtime_20261112.md) và [biên nhận đạt](staging_hardening_local_pass_20261112.json):
* **Phạm vi thực thi**: Codex đã trực tiếp chạy probe cục bộ trên container Docker PostgreSQL 17 chuyên dụng (`--network none`, không mở port ra host, đặt tên theo UUID).
* **Kết quả đo kiểm**:
  * **42/42 focused checks PASS**: bao gồm kiểm tra 10 hàm helper từ chối `anon` và cho phép `authenticated`; kiểm tra hiển thị khách (public published hiện, unlisted detail qua RPC, private/draft bị từ chối); kiểm tra cách ly người gọi (caller isolation); kiểm tra `proconfig` và kích hoạt DML trên các bảng tạm mang cấu trúc legacy.
  * **21/21 clean DB-suite cases PASS**.
  * **Dọn dẹp tài nguyên**: Xác nhận xóa sạch container theo đúng ID sở hữu và kiểm tra danh mục Docker rỗng (`cleanup_verified: true`).
* **Các giới hạn quan trọng**:
  * Đây là kiểm thử do **Codex thực thi cục bộ với stub `auth.uid`**, **KHÔNG PHẢI** là runtime QA độc lập của reviewer.
  * **KHÔNG PHẢI** là Supabase Auth / GoTrue / Session validation thật.
  * **KHÔNG PHẢI** là đã áp dụng (apply) lên môi trường hosted staging `mxqpukhfiugdwsjsbihj`.
  * **KHÔNG PHẢI** mọi thao tác đều dùng SQL ROLLBACK; dữ liệu fixture tồn tại trong container cô lập và việc dọn dẹp được thực hiện bằng cách hủy toàn bộ container sở hữu.

### Lưu vết các lần thử nghiệm trước đó:
* [Lần thử 1 (FAIL)](staging_hardening_local_attempt1_20261112.json): 40 focused + 21 DB cases pass, nhưng probe truy vấn cột `play_date` legacy trên bảng `sessions` hiện đại (nơi cột này không tồn tại). Đây là lỗi giả định của probe, không phải lỗi từ candidate SQL; đã được khắc phục ở probe cuối bằng bảng tạm cấu trúc legacy.
* [Lần thử 2 (FAIL)](staging_hardening_local_attempt2_20261112.json): `pg_isready` qua Unix-socket bắt nhầm tiến trình khởi tạo tạm trước khi server restart; đã được khắc phục bằng TCP readiness cục bộ.

---

## 3. Danh mục tài nguyên thuộc quyền sở hữu (Owned Files)

1. [role_helper_hardening.sql](../../../scripts/bh07_staging/role_helper_hardening.sql): File SQL ứng viên gồm chính xác 22 câu lệnh (10 `REVOKE ALL`, 10 `GRANT EXECUTE`, 2 `ALTER FUNCTION SET search_path`). **Giữ nguyên 100% không chỉnh sửa** (SHA256 LF-normalized: `f9c821130802f2ea5cd508d8388cad3989da2e5b8fb8b5d6a3c3d2c512ef6081`).
2. [test_bh07_staging_hardening.py](../../../tests/test_bh07_staging_hardening.py): Bộ kiểm thử tĩnh exact whole-statement, neo chặt chẽ và kiểm soát mutant fail-closed.
3. [staging_hardening_anti_handoff_20261112.md](staging_hardening_anti_handoff_20261112.md): Báo cáo bàn giao vòng sửa 2 này.

---

## 4. Chi tiết 10 Hàm Helper & 2 Legacy Triggers

### 10 Hàm Helper RLS (REVOKE ALL FROM PUBLIC, anon; GRANT EXECUTE TO authenticated):
1. `public.is_app_admin(UUID)`
2. `public.is_club_owner(UUID, UUID)`
3. `public.is_club_member_active(UUID, UUID)`
4. `public.has_club_role(UUID, UUID, TEXT[])`
5. `public.is_session_host(UUID, UUID)`
6. `public.has_session_staff_role(UUID, UUID, TEXT[])`
7. `public.has_session_management_access(UUID, UUID)`
8. `public.has_session_finance_access(UUID, UUID)`
9. `public.is_session_participant(UUID, UUID)`
10. `public.has_session_player_finance_access(UUID, UUID)`

Chữ ký được đối chiếu khớp hoàn toàn với migration chuẩn [20261015051808_init_schema_v1_1.sql](../../../supabase/migrations/20261015051808_init_schema_v1_1.sql).

### 2 Hàm Trigger Legacy (ALTER FUNCTION SET search_path = public, pg_temp):
1. `public.sync_legacy_session_columns()`
2. `public.sync_legacy_session_player_columns()`

---

## 5. Ranh giới an toàn & Trạng thái nghiệm thu

* **Trạng thái P2**: Không tự tuyên bố đóng các phát hiện P2; việc đánh giá closure phụ thuộc vào kết quả review độc lập của reviewer.
* **Ranh giới migration chính thức**: File SQL tiếp tục lưu tại `scripts/bh07_staging/role_helper_hardening.sql`, chưa chuyển vào `supabase/migrations/` do lệnh CLI `migration-new` bị chặn bởi danh sách trắng `npx.cmd`; không tìm cách vượt qua ranh giới này.
* **Bảo lưu trạng thái hosted**: Lỗ hổng RPC helper trên hosted staging vẫn tồn tại cho đến khi ứng viên được phê duyệt thành migration chính thức và áp dụng/kiểm tra độc lập trên hosted. Vấn đề probe arbitrary-UUID của authenticated và các thông báo security advisor khác chưa được xử lý trong phạm vi candidate này.
* **Không chạy lệnh ngoài quyền hạn**: Không chạy lệnh shell/SQL/CLI, không đổi cài đặt môi trường, không commit git.
* **Trạng thái chấp nhận rủi ro**: Toàn bộ V3/V5/V7 và BH-07/V8 vẫn **CHƯA NGHIỆM THU**; không merge/deploy/pilot/BH-08.
