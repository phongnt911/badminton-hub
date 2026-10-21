# Bàn giao BH-07C — Chờ review vòng 1/2 (21/10/2026)

> **Kết luận reviewer hiện hành 21/10/2026: Đạt C local tại `02a9b85`, vòng sửa 1/2**, đóng C1/C2/C3 P2. [Review/bằng chứng/giới hạn log gốc](review_02a9b85.md). Nội dung bàn giao phía dưới giữ làm lịch sử; không tự chuyển D, merge main hoặc deploy.


> **Implementer 21/10/2026: Chờ review vòng 1/2 tại tested code `02a9b85`**, base `9b97846`. Đã sửa C1/C2/C3 P2 theo [review 15ae1af](review_15ae1af.md); test đỏ trước sửa 3 FAIL, sau sửa analyze sạch, **230 Flutter +57 targeted C (UTC và Asia/Ho_Chi_Minh) +23 BH-07 DB PASS**. [Lệnh/bằng chứng](bh07c_fix_evidence/commands.md). Không đổi A/B, chưa chuyển D/merge/deploy; người triển khai không tự ghi Đạt.
>
> **Reviewer 21/10/2026 (lịch sử): Chưa đạt C tại `15ae1af`**, C1/C2/C3 P2 còn mở. Bàn giao/kết quả tác giả dưới đây giữ làm lịch sử.


- Nhánh `feat/bh07c-ui`, base `cf95d76855acf1f394b1976ebab54087b4d7bba9`, tested code `15ae1af0d9d39678f4b9d99fabc9e9e22cb860ba`.
- Chỉ làm phần C (UI). Không sửa migration/RPC A, model/repository/provider B, contract complete/history/summary, `main`, staging hay production.
- A và B giữ Đạt local theo `4512c3a` và `d7bac04`. **C đang Chờ review**, người triển khai không tự ghi Đạt.

## 1. Phạm vi đã làm

### Lịch sử buổi

- Thêm `SessionHistoryScreen`, dùng `SessionProvider` + `ClubProvider`; không thêm provider mới.
- Lọc theo CLB và khoảng ngày, gọi đúng `SessionHistoryFilter` của B.
- Có loading, empty, error/retry, refresh, tải thêm theo offset do provider giữ; mở chi tiết và tải lại lịch sử khi quay về.
- Lối vào “Lịch sử buổi” trên `HomeScreen` chỉ hiện khi đã đăng nhập; guest vẫn giữ nội dung/test cũ.

### Tổng kết và sao chép

- Thêm `SessionSummaryScreen`, chỉ đọc `FinanceProvider.sessionSummary` từ `get_session_summary`.
- Summary hiển thị số có mặt/vắng/đã xác nhận; phần tiền chỉ hiện khi `canViewFinance`.
- Trường tiền `null` hiển thị `—`, không đổi thành `0`; không suy `outstanding` từ `due - paid`.
- Nút sao chép dùng `buildSessionSummaryText`: management-only không có phần tiền; finance có aggregate server; nội dung không chứa danh sách người chơi, số điện thoại hay tài khoản ngân hàng.
- Lối vào tổng kết trong chi tiết buổi chỉ hiện với `canManage || canViewFinance` và buổi `completed`/`cancelled`.

### Kết thúc buổi

- Start giữ nguyên hành vi hiện có trong `SessionDetailScreen` và test cũ.
- Thêm nút “Kết thúc buổi chơi” trong `SessionFinanceScreen` khi:
  - người dùng `canManage`;
  - buổi `in_progress`;
  - phí `canCollect` (current + có revision);
  - có `sessionVersion` từ DTO tài chính.
- Có hộp xác nhận; gọi `FinanceProvider.completeSession` với version server; lỗi hiển thị thông điệp domain, không báo thành công.
- Thành công trả `true` về chi tiết, chi tiết tải lại session và gọi `refreshHistoryIfLoaded`; công nợ còn lại vẫn do server giữ.

### File chính

- `lib/core/session_summary_text.dart`
- `lib/screens/session_history_screen.dart`
- `lib/screens/session_summary_screen.dart`
- `lib/screens/home_screen.dart`
- `lib/screens/session_detail_screen.dart`
- `lib/screens/session_finance_screen.dart`
- Test: `test/core/session_summary_text_test.dart`, `test/screens/session_history_screen_test.dart`, `test/screens/session_summary_screen_test.dart`, bổ sung test chi tiết/tài chính/home.

## 2. Bằng chứng đã chạy

| Lệnh | Kết quả | Log |
|---|---|---|
| `flutter analyze` | exit 0, không issue | `bh07c_evidence/flutter_analyze.log` |
| `flutter test` | exit 0, **225/225 PASS** | `bh07c_evidence/flutter_test.log` |
| `python docs/reviews/bh07/run_bh07_tests.py` | exit 0, **23/23 PASS** (21 clean + 2 upgrade) | `bh07c_evidence/bh07_db_runner.log`, `bh07c_evidence/bh07_test_results.json` |
| Targeted 6 file C | **52/52 PASS** trước khi chạy toàn bộ | nằm trong log Flutter |

Môi trường: Flutter 3.47.6 / Dart 3.13.5, Python 3.12.7, PostgreSQL cô lập trong container `bh02-test-postgres`. Runner tự tạo DB `bh07_clean_*` và `bh07_upgrade_*`.

Không đổi DB/migration nên không chạy lại 335 DB hồi quy BH-02..06; baseline B trước đó là 335/335 và C chỉ tác động Flutter. BH-07 runner được chạy lại để xác nhận complete/history/summary và nâng cấp vẫn xanh.

## 3. NOT RUN

- HTTP/PostgREST/JWT/Supabase Auth thật.
- Thiết bị/browser/deep link/offline/reopen thực tế.
- Ngân hàng/VietQR/webhook thật.
- Staging/production, backup/restore.
- Concurrency HTTP thật.
- Pilot D và rehearsal vận hành.

Các kết quả trên chỉ là local/widget/PostgreSQL cô lập, không cho phép deploy hoặc kết luận pilot Đạt.

## 4. Điểm cần reviewer kiểm

1. Nút complete chỉ bật đúng gate; lỗi/version conflict không pop route và không báo thành công.
2. Summary/copy không lộ tiền khi management-only, giữ `null` là `—`, không có contact/bank.
3. History lọc/pagination/refresh đúng contract B, không tự lọc lại phía client.
4. Sau complete, chi tiết tải lại và lịch sử (nếu đang mở) refresh; start không bị đổi hành vi.

## 5. Sửa review vòng 1/2 — Chờ review (21/10/2026)

- Nhánh `feat/bh07c-ui`, base `9b978467316d66c458846ac68c5de8021401fa0c`, **tested code `02a9b857724e9ba031323ad732c90355d7932a39`**. **Chờ review vòng 1/2**, không tự ghi Đạt.
- C1: complete chỉ dùng `finance.sessionVersion`; thiếu DTO thì khoá nút kèm `Chưa xác định được phiên bản buổi để kết thúc. Hãy tải lại dữ liệu tài chính.` Fallback route chỉ còn cho chốt phí BH-06.
- C2: cache rỗng không che lỗi refresh; hiện inline error + empty card + `Tải lại`, retry tải được dữ liệu mới.
- C3: `_from/_to` là ngày lịch Việt Nam; `_filter` đổi sang UTC+7 bằng helper, mốc cuối `23:59:59.999999` giờ Việt Nam.
- Test: red exit 1 với 3 FAIL (C1/C2/C3); green analyze sạch, **230/230 Flutter**, **57/57 targeted C** dưới `TZ=UTC` và `TZ=Asia/Ho_Chi_Minh`, **23/23 BH-07 DB**. Log/JSON/exit tại [bh07c_fix_evidence](bh07c_fix_evidence/commands.md).
- Không sửa migration/RPC A, model/repository/provider B, contract, `main`, staging hoặc production. Không chuyển D, merge hoặc deploy. Các cổng môi trường thật và pilot vẫn NOT RUN.
