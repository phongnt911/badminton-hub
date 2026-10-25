# Báo Cáo Kiểm Chứng Cổng V2b — Private Dart Heap / In-Memory Retention BH-07

- **Ngày thực thi:** 2026-10-25T15:09:34.225472+00:00
- **Tested Source SHA:** `ccad24cf67eabb5c17de285792fe96bca21714aa`
- **Git Dirty:** `True`
- **Gate:** `V2b — Đo private Dart heap/cache sau đổi actor`
- **Kết luận:** **Chờ review độc lập** (Tất cả 7/7 kiểm thử bộ nhớ đạt PASS; phương pháp đo trực tiếp trên Dart VM).

---

## 1. Mục Tiêu & Phương Pháp Đo

Mục tiêu cổng V2b theo `docs/reviews/bh07/bh07_readiness.md` mục 4.4:
Đo lường trực tiếp bộ nhớ RAM / Dart Heap của ứng dụng, chứng minh rằng sau khi **Owner đăng xuất** và chuyển sang **Cohost/Member** trong **CÙNG MỘT INSTANCE ỨNG DỤNG**:
1. Không còn bất kỳ **retained object** (tham chiếu sống) nào trong Dart heap giữ dữ liệu tài chính nhạy cảm của Owner (`PaymentInstructions`, `SessionFinance`, `SessionSummary`, `ClubLedger`).
2. Không rò rỉ bộ nhớ qua `static mutable`, global listeners hoặc stream subscriptions.
3. Không nuốt các phản hồi trả về trễ (late-arriving responses) sau khi đổi phiên làm việc.
4. Có baseline đối chứng, positive controls, negative controls và mutant controls chứng minh Oracle nhạy bén.

### Phương pháp kỹ thuật:
- Sử dụng cơ chế cốt lõi của Dart SDK (`WeakReference<T>` và `Finalizer<T>`) theo dõi vòng đời đối tượng mà không giữ strong reference.
- Khởi tạo cây Provider (`AuthProvider`, `FinanceProvider`, `SessionProvider`, `ClubProvider`) trong cùng một instance ứng dụng.
- Kích hoạt Garbage Collector (GC) của Dart VM thông qua áp lực bộ nhớ tạm (allocation pressure) để thu hồi toàn bộ các đối tượng mồ côi (không còn strong reference).
- Kiểm tra `weakRef.target == null` làm Oracle xác nhận đối tượng đã hoàn toàn biến mất khỏi bộ nhớ RAM.

---

## 2. Kết Quả Kiểm Chứng Từng Mốc (Epochs & Controls)

| Mốc / Control | Loại Control | Kỳ vọng | Kết quả | Trạng thái |
|---|---|---|---|---|
| **Baseline Epoch** | Baseline | Trạng thái ban đầu rỗng, không có instance tài chính nào | 0 retained objects | **PASS** |
| **Owner Active (Epoch 1)** | Positive Control P1 | 4 đối tượng tài chính sống trong heap, Provider tham chiếu mạnh | `weakRef.target != null` | **PASS** |
| **Post-Logout Purge (Epoch 2)** | Negative Control N1 | Gọi `logout()`, `clearAll()` kích hoạt; GC thu hồi 100% 4 đối tượng nhạy cảm | `weakRef.target == null` (cả 4) | **PASS** |
| **Cohost Switch (Epoch 3)** | Negative Control N2 | Đổi sang Cohost trong cùng instance; dữ liệu Owner không hồi sinh; Cohost state độc lập | `weakRef.target == null`, không có tiền | **PASS** |
| **Member Switch (Epoch 4)** | Negative Control N3 | Đổi sang Member; đối tượng của Owner vẫn chết; Member nhận object mới | `weakRef.target == null`, new ref riêng | **PASS** |
| **Late Response Logout** | Negative Control N4 | Response tài chính trả về trễ sau logout bị drop hoàn toàn, GC thu hồi payload | `weakRef.target == null` | **PASS** |
| **Late Response Actor Switch** | Negative Control N5 | Response tài chính trả về trễ sau khi đổi sang Member bị drop, không rò rỉ | `weakRef.target == null` | **PASS** |
| **Static Cache Leak** | Mutant Control M1 | Cố tình giữ strong reference trong static list; Oracle phải phát hiện đối tượng còn sống | Oracle phát hiện FAIL leak | **PASS** |
| **Skipped ClearAll** | Mutant Control M2 | Cố tình không dọn field khi đổi user; Oracle phải phát hiện đối tượng còn sống | Oracle phát hiện FAIL leak | **PASS** |
| **Session & Club Purge** | Negative Control | Chi tiết buổi và CLB nội bộ của Owner bị thu hồi sạch khỏi heap sau logout | `weakRef.target == null` | **PASS** |

---

## 3. Kết Quả AST Static Memory Audit

- **Tổng số file Dart quét:** 38 files trong `lib/`.
- **Static mutable collections:** 0 (Không phát hiện `static List`, `static Map`, `static Set` nào lưu trữ dữ liệu người dùng).
- **Provider Lifecycle & Stream Disposal:**
  - `finance_provider.dart`: `auth.addListener(_onAuthChanged)` được gỡ bỏ bằng `removeListener` trong `dispose()`. Leak risk: **NONE**.
  - `session_provider.dart`: `auth.addListener(_onAuthChanged)` được gỡ bỏ bằng `removeListener` trong `dispose()`. Leak risk: **NONE**.
  - `club_provider.dart`: `auth.addListener(_onAuthChanged)` được gỡ bỏ bằng `removeListener` trong `dispose()`. Leak risk: **NONE**.
  - `auth_provider.dart`: StreamSubscription `_authSubscription` được `cancel()` trong `dispose()`. Leak risk: **NONE**.

---

## 4. Bảo Mật & Sanitization

- Toàn bộ bằng chứng trong bundle này đã được **sanitized 100%**:
  - Không chứa số tài khoản ngân hàng thật, mã bí mật, mật khẩu hay JWT token nhạy cảm.
  - Các giá trị đối soát chỉ sử dụng fixture giả lập, boolean flags, và mã băm SHA-256.

---

## 5. Giới Hạn Kỹ Thuật & Khuyến Nghị

1. **Phạm vi đã kiểm chứng:** Đo lường trực tiếp cơ chế quản lý bộ nhớ, chuỗi tham chiếu sống (retention path) và thu hồi GC của Dart VM Runtime thông qua test harness độc lập.
2. **Giới hạn môi trường:** Chưa trích xuất file `.heapsnapshot` nhị phân từ Chrome DevTools Memory Profiler trên bản build Web profile (do môi trường Windows headless không chạy browser profile server tương tác).
3. **Quy định bàn giao:** Cổng V2b thuộc Nhóm 3 (Cổng môi trường chuyên sâu). Người triển khai ghi nhận kết quả và giới hạn trung thực, ghi nhận trạng thái **Chờ review**, KHÔNG tự ý ghi "Đạt" hay tự ý nghiệm thu toàn bộ BH-07.
