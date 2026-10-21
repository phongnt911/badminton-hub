# Bàn giao BH-07D — Chờ review tích hợp BH-07 (21/10/2026)

> **Reviewer 21/10/2026: Đạt BH-07D tích hợp local tại `3d590a8`** theo [review/bằng chứng](review_3d590a8.md). Không có P0/P1/P2 mở trong phạm vi giao; toàn BH-07, môi trường thật và rehearsal/pilot chưa nghiệm thu. Bàn giao tự báo phía dưới giữ làm lịch sử; không merge/deploy/apply DB thật.


> **Implementer 21/10/2026: Chờ review tích hợp BH-07** tại tested code
> `3d590a8418157cf91b00b9a5503d09be4df069f3`, base D
> `b0478a72021a726530c4051b52239a0a22d7fb96`, nhánh `feat/bh07-integration`.
> Người triển khai **không tự ghi Đạt/Done**. A giữ `4512c3a`; B giữ `d7bac04`
> (code `a682007`); C giữ `02a9b85`. Không merge `main`, không deploy.

## 1. Phạm vi

Chỉ làm phần D — kiểm chứng tích hợp end-to-end ở ranh giới UI/provider/repository,
không thay màn hình hoặc nghiệp vụ bằng bản giả:

- `test/integration/bh07_full_flow_test.dart` (mới): 10 ca tích hợp.
- `lib/screens/session_finance_screen.dart`: sửa tối thiểu lỗi tích hợp sau complete.

Không đổi migration, RPC, model/repository/provider, contract, dependency, `main`,
staging hoặc production.

## 2. Lỗi tích hợp, test đỏ và cách sửa

**Lỗi:** sau khi buổi ở `completed`, màn tài chính vẫn hiện nút `Thêm chi phí`
(`bh06c-add-expense`) dù RPC `post_session_expense` từ chối `completed/cancelled`.
Người dùng có thể bấm rồi nhận lỗi server.

**Test đỏ trước sửa:** giữ nguyên test D, tạm đưa riêng file UI về base:

```powershell
git checkout HEAD^ -- lib/screens/session_finance_screen.dart
flutter test test/integration/bh07_full_flow_test.dart --plain-name "sau complete"
# exit 1
# Expected: no matching candidates
# Actual: Found 1 widget with key <'bh06c-add-expense'>
# bh07_full_flow_test.dart:1162
```

**Sửa tối thiểu:** chỉ ẩn `Thêm chi phí` khi lifecycle `completed`/`cancelled`.
Giữ nguyên chốt lại phí, thu tiền, xác nhận/từ chối thanh toán, thu tiền mặt và
hoàn tác — các thao tác server vẫn cho phép sau complete. Không nới gate, không
suy công nợ từ `due - paid`; UI hiển thị `outstanding` do server trả.

## 3. Phạm vi test D (10 ca)

1. Host: start → điểm danh → chốt phí → complete → history refresh, giữ công nợ.
2. Complete buổi miễn phí current 0 vẫn gửi đúng `version`/`request_id`.
3. Complete bị khoá khi phí `stale` hoặc chưa chốt; không gọi RPC.
4. `VERSION_CONFLICT`: không báo thành công, tải lại lấy version mới rồi complete.
5. Đang submit: nút bị khoá, không gọi lặp; retry cùng intent giữ nguyên
   `request_id`, không báo thành công giả.
6. History: offset/dedupe, lọc CLB và ngày UTC+7, mở chi tiết rồi quay lại refresh.
7. Summary/copy: management-only không lộ tiền/contact/bank; finance giữ tiền NULL
   là `—`, copy không biến NULL thành 0.
8. Participant/guest không thấy lối tổng kết quản lý hay tài chính quản lý.
9. Sau complete: ẩn thêm chi phí; vẫn cho chốt lại, thu tiền mặt, xác nhận/từ chối
   thanh toán và hoàn tác thanh toán/chi phí.
10. Logout/đổi actor: xoá lịch sử cũ, không lộ dữ liệu actor trước.

## 4. Bằng chứng đã chạy tại tested code

| Hạng mục | Kết quả | Log / ghi chú |
|---|---|---|
| Baseline base `b0478a7` | analyze sạch, **230 Flutter**, **23/23 BH-07 DB** | `baseline_*.log` |
| `flutter analyze` | exit 0, no issues | `analyze.log`, `analyze_exit.txt` |
| Full Flutter | exit 0, **240/240 PASS** | `flutter_test_full.log` |
| D targeted `TZ=UTC` | exit 0, **10/10 PASS** | `d_targeted_tz_utc.log` |
| D targeted `TZ=Asia/Ho_Chi_Minh` | exit 0, **10/10 PASS** | `d_targeted_tz_asia_hcm.log` |
| C regression `TZ=UTC` | exit 0, **50/50 PASS** (4 file) | `c_regression_targeted_tz_utc.log` |
| C regression `TZ=Asia/Ho_Chi_Minh` | exit 0, **50/50 PASS** (4 file) | `c_regression_targeted_tz_asia_hcm.log` |
| BH-07 DB runner | exit 0, **23/23 PASS**, `worktree_dirty=false` | `bh07_db_results_3d590a8.json` |
| Test đỏ trước sửa | exit 1, đúng 1 FAIL `bh06c-add-expense` | `d_red_post_complete_add_expense.log` |

DB runner chạy trên PostgreSQL local + Auth stub, không phải Supabase thật. Kết quả
DB ghi `base_sha=3d590a8...`, `worktree_dirty=false`.

## 5. Cổng kiểm chứng

| Cổng | Trạng thái | Ghi chú |
|---|---|---|
| Local: analyze + Flutter + PostgreSQL runner | **PASS local** | Chỉ trong phạm vi local nêu trên |
| HTTP/PostgREST/JWT/Supabase Auth thật | **NOT RUN** | Không có môi trường/Auth thật được phép |
| Browser/desktop thật | **NOT RUN** | Widget test không thay browser thật |
| Mobile iOS/Android thật | **NOT RUN** | Không có thiết bị/emulator được nghiệm thu |
| Offline/reopen/deep link | **NOT RUN** | Không có môi trường kiểm chứng |
| Concurrency qua HTTP thật | **NOT RUN** | Chỉ có version/DB local; chưa có nhiều client HTTP |
| Ngân hàng/VietQR/webhook thật | **NOT RUN** | Không dùng tài khoản/tiền thật |
| Staging/production, backup/restore | **NOT RUN** | Không apply/ deploy |
| Rehearsal/pilot, nghiệm thu toàn BH-07 | **NOT RUN** | Chỉ là bàn giao D để review |

## 6. Giới hạn

- Test D dùng UI/provider thật nhưng mock repository tại ranh giới client/RPC; không
  chứng minh HTTP/PostgREST/JWT/Auth thật, RLS hay mạng thật.
- DB runner là PostgreSQL local + Auth stub, không phải Supabase production.
- Hai lần chạy D dưới `TZ=UTC` và `TZ=Asia/Ho_Chi_Minh` đều PASS; log D có nội dung
  giống nhau vì test không in giờ, khác với C có log khác nhau theo múi giờ.
- Kết quả local **không** phải nghiệm thu D, không phải nghiệm thu toàn BH-07 và
  không cho phép deploy. Reviewer phải tự chạy lại và quyết định Đạt/Chưa đạt.

## 7. Lệnh reviewer cần tự chạy

```powershell
git checkout 3d590a8418157cf91b00b9a5503d09be4df069f3
flutter analyze
flutter test
$env:TZ='UTC'; flutter test test/integration/bh07_full_flow_test.dart
$env:TZ='Asia/Ho_Chi_Minh'; flutter test test/integration/bh07_full_flow_test.dart
$env:TZ='UTC'; flutter test test/screens/session_finance_screen_test.dart test/screens/session_history_screen_test.dart test/screens/session_summary_screen_test.dart test/screens/session_detail_screen_test.dart
$env:TZ='Asia/Ho_Chi_Minh'; flutter test test/screens/session_finance_screen_test.dart test/screens/session_history_screen_test.dart test/screens/session_summary_screen_test.dart test/screens/session_detail_screen_test.dart
python docs/reviews/bh07/run_bh07_tests.py
```

Kỳ vọng: analyze 0; 240 Flutter; 10 D mỗi múi giờ; 50 C mỗi múi giờ; 23/23 BH-07 DB.
Sau đó kiểm tra `sha256.txt`, `summary.json`, diff và ghi phát hiện P0/P1/P2/NOT RUN
vào `docs/reviews/bh07/`.

## 8. Bằng chứng

- [commands.md](integration_evidence/commands.md)
- [summary.json](integration_evidence/summary.json)
- [environment.txt](integration_evidence/environment.txt)
- [sha256.txt](integration_evidence/sha256.txt)
- Log/JSON thô trong `docs/reviews/bh07/integration_evidence/`.

Người triển khai dừng ở **Chờ review tích hợp BH-07**; không merge `main`, không
deploy, không bắt đầu pilot.
