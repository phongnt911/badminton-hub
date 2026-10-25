# Bàn Giao Kiểm Chứng V2b — Private Dart Heap / In-Memory Retention & Cache BH-07

- **Ngày bàn giao:** 25/10/2026
- **Nhánh:** `feat/bh07-private-heap-verification`
- **Base commit:** `aca3f08a80d359ad1a69c444f428c6b8f5142cc8`
- **Người thực thi:** AI triển khai (Antigravity)
- **Người review dự kiến:** Codex (Reviewer độc lập)
- **Trạng thái:** **Chờ review độc lập** (Người triển khai KHÔNG tự ghi Đạt).

---

## 1. Bối Cảnh & Mục Tiêu

Theo `docs/reviews/bh07/bh07_readiness.md` mục 4.4 và `AGENTS.md`:
- Ở cổng V1 (Browser / Offline / Reopen), giao diện người dùng (UI), DOM, clipboard, và web storage đã được kiểm chứng không lộ dữ liệu tài chính sau khi logout.
- **Tuy nhiên**, UI/copy sạch KHÔNG đồng nghĩa với việc bộ nhớ trong (Dart Heap) đã sạch! Nếu các đối tượng tài chính (`PaymentInstructions`, `SessionFinance`, `SessionSummary`, `ClubLedger`) hoặc session/club vẫn còn retained references trong heap sau khi đổi actor (Owner → logout → Cohost/Member trong cùng một instance ứng dụng), rủi ro rò rỉ bộ nhớ và khai thác trái phép qua bộ nhớ RAM vẫn tồn tại.
- Cổng **V2b** yêu cầu:
  + Đo lường trực tiếp retained objects trong Dart Heap qua chu trình Owner → logout → Cohost/Member trong **cùng instance ứng dụng**.
  + Có baseline đối chứng, positive controls, negative controls, và mutant controls có oracle xác định, lặp lại được.
  + Không công bố raw heap chứa secrets; lưu bằng chứng sanitized.
  + Ghi nhận trung thực phương pháp và giới hạn; thiếu công cụ thì ghi NOT RUN.

---

## 2. Phương Pháp Đo Lường Kỹ Thuật

1. **Cơ chế đo retained objects qua Dart VM:**
   - Sử dụng `WeakReference<T>` và `Finalizer<T>` chuẩn của Dart SDK (`dart:core`) để theo dõi các đối tượng nhạy cảm mà không cản trở Garbage Collector thu hồi chúng.
   - Toàn bộ cây Provider (`AuthProvider`, `FinanceProvider`, `SessionProvider`, `ClubProvider`) được khởi tạo và duy trì trong **cùng một application instance**.
   - Kích hoạt Garbage Collector của Dart VM thông qua áp lực cấp phát bộ nhớ (allocation pressure) để ép buộc generational GC (Scavenge + Mark-Sweep) thu hồi các đối tượng mồ côi.
   - Oracle xác nhận: Nếu `weakRef.target == null`, đối tượng đã hoàn toàn bị thu hồi khỏi heap. Nếu `weakRef.target != null`, đối tượng vẫn còn bị giữ lại (retained leak).

2. **AST & Static Codebase Audit:**
   - Quét toàn bộ 38 files Dart trong `lib/` nhằm phát hiện `static mutable` collections (List, Map, Set), global singletons giữ state, hoặc các `StreamSubscription` / event listeners không được gỡ bỏ trong `dispose()`.

---

## 3. Kết Quả Kiểm Chứng Từng Mốc

### 3.1. AST Static Memory Audit
- **Kết quả:** `CLEAN` (0 static mutable collections, 0 un-cancelled subscriptions).
- Tất cả listeners `auth.addListener(_onAuthChanged)` trong `FinanceProvider`, `SessionProvider`, `ClubProvider` đều có `auth.removeListener(_onAuthChanged)` trong `dispose()`.
- File báo cáo: [`docs/reviews/bh07/private_heap_evidence/ast_memory_audit.json`](private_heap_evidence/ast_memory_audit.json).

### 3.2. Integration Test Đo Retained Objects (7/7 PASS)
Suite kiểm chứng: [`test/integration/bh07_heap_verification_test.dart`](../../../test/integration/bh07_heap_verification_test.dart).

1. **Baseline Epoch (PASS):** Trạng thái ban đầu rỗng, không có retained object nào của các class tài chính.
2. **Owner Active — Positive Control P1 (PASS):** Nạp đầy đủ 4 đối tượng tài chính: `PaymentInstructions` (STK, QR), `SessionFinance` (chi tiết thu chi), `SessionSummary` (doanh thu tổng), `ClubLedger` (quỹ CLB). Xác nhận cả 4 đối tượng đang sống trong heap (`weakRef.target != null`) và được Provider tham chiếu.
3. **Owner Logout — Negative Control N1 (PASS):** Gọi `auth.changeUser(null)`. `clearAll()` kích hoạt lập tức nullified toàn bộ fields. Sau khi GC chạy, **cả 4 đối tượng nhạy cảm của Owner đều bị GC thu hồi 100% (`weakRef.target == null`)**.
4. **Cohost Switch — Negative Control N2 (PASS):** Đăng nhập Cohost trong cùng instance. Cohost nhận view hạn chế (không có số tiền). Xác nhận 4 weak references của Owner vẫn là `null` (không hồi sinh, không rò rỉ chéo).
5. **Member Switch — Negative Control N3 (PASS):** Đăng nhập Member trong cùng instance. Member nhận hướng dẫn thanh toán riêng. Xác nhận 4 weak references của Owner vẫn là `null`, object của Member là instance mới độc lập.
6. **Late Response sau Logout — Negative Control N4 (PASS):** Request tài chính trả về trễ sau khi Owner đã logout bị `_generation` và `_authUserId` drop hoàn toàn. GC thu hồi sạch payload mồ côi (`weakRef.target == null`).
7. **Late Response sau Switch Actor — Negative Control N5 (PASS):** Request của Owner trả về trễ sau khi đã chuyển sang Member bị drop, không rò rỉ vào state của Member (`weakRef.target == null`).
8. **Mutant Control M1 (PASS):** Cố ý tạo leak vào static list; Oracle phát hiện `weakRef.target != null` và báo FAIL.
9. **Mutant Control M2 (PASS):** Cố ý không dọn field khi đổi user; Oracle phát hiện `weakRef.target != null` và báo FAIL.
10. **Session & Club Purge (PASS):** Chi tiết buổi và CLB nội bộ của Owner cũng được thu hồi sạch khỏi heap sau logout.

---

## 4. Bằng Chứng & Manifest

Thư mục bằng chứng: [`docs/reviews/bh07/private_heap_evidence/`](private_heap_evidence/)
Bao gồm:
- `ast_memory_audit.json`: Kết quả phân tích tĩnh AST toàn bộ 38 files mã nguồn `lib/`.
- `heap_test_run.log`: Nhật ký chạy thực thi chi tiết của suite test bộ nhớ Dart VM.
- `summary.json`: Báo cáo tóm tắt các controls và metadata môi trường (sanitized 100%).
- `heap_verification_report.md`: Báo cáo chi tiết phương pháp và kết quả kiểm chứng.
- `hashes.sha256`: Bảng mã băm SHA-256 các file, định dạng strict UTF-8 LF, không BOM.

Manifest verification:
```
python scripts/bh07_heap/clean_and_manifest.py --verify
PASS: Verified 4 files in manifest. All strict UTF-8 LF, clean hashes, zero secret leaks.
```

---

## 5. Giới Hạn Kỹ Thuật & Công Bố Trung Thực

1. **Phương pháp thực thi:** Kiểm chứng thực tế trên Dart VM Runtime Test Harness (môi trường Windows 64-bit, Flutter 3.47.6, Dart 3.13.5).
2. **Giới hạn môi trường:** Chưa trích xuất file `.heapsnapshot` đồ thị bộ nhớ nhị phân từ Chrome DevTools Memory Profiler trên bản build Web profile tương tác (do môi trường Windows headless không chạy browser profile server).
3. **Quy định bàn giao:** Cổng V2b thuộc Nhóm 3 (Cổng môi trường/vận hành chuyên sâu). Người triển khai công bố trung thực kết quả đo và các giới hạn; ghi nhận trạng thái **Chờ review**, KHÔNG tự ý ghi "Đạt" và KHÔNG nghiệm thu toàn bộ BH-07.
4. Giữ nguyên V1 và V5b Đạt local; không merge `main`/`staging`/`production`, không deploy, không pilot, không chuyển BH-08.
