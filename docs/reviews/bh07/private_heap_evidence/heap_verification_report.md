# Báo Cáo Kiểm Chứng Cổng V2b — Private Dart Heap / In-Memory Retention BH-07

- **Ngày thực thi:** 2026-10-26T04:05:55.439775+00:00
- **Tested Source SHA:** `16e5b5116738ab9d4417fe11b651aea794868401`
- **Git Dirty:** `False`
- **Git Cleanliness:** `CLEAN`
- **Provenance Errors:**
  - None
- **Dirty Paths:**
  - None (Clean checkout)
- **Suite Verdict:** `PASS` — **Identity Coverage:** `VERIFIED`
- **Tests:** 7/7 passed, 0 failed, 0 skipped, missing: 0
- **Unexpected visible identities:** None
- **Duplicate identities:** None
- **Gate:** `V2b — Đo private Dart heap/cache sau đổi actor`
- **Kết luận:** **Chờ review độc lập** (7/7 Provider test PASS, AST CLEAN; App profile heap: NOT RUN).

---

## 1. Mục Tiêu & Phạm Vi Kiểm Chứng

Mục tiêu cổng V2b theo `docs/reviews/bh07/bh07_readiness.md` mục 4.4:
Đo lường trực tiếp bộ nhớ RAM / Dart Heap của ứng dụng, kiểm tra xem sau khi **Owner đăng xuất** và chuyển sang **Cohost/Member** trong cùng instance:
1. Không còn đối tượng tài chính nhạy cảm của Owner (`PaymentInstructions`, `SessionFinance`, `SessionSummary`, `ClubLedger`) bị lưu giữ trong heap.
2. Không rò rỉ bộ nhớ qua `static mutable`, global listeners hoặc stream subscriptions.
3. Không nuốt các phản hồi trả về trễ (late-arriving responses) sau khi đổi phiên làm việc.
4. Có baseline đối chứng, positive controls, negative controls và mutant controls.

### Phân định phạm vi rõ ràng (Khắc phục HP1):
- **Phần Provider / VM Test Harness (Bằng chứng bổ trợ):** Đạt 7/7 kiểm thử `WeakReference` trên `FinanceProvider`, `SessionProvider`, `ClubProvider`. Kết quả chỉ nói về việc Provider/harness còn tham chiếu DTO hay không, không phải toàn bộ app profile.
- **Phần App Profile Heap Snapshot / Chrome DevTools Protocol:** **NOT RUN** do môi trường kiểm thử headless chưa có công cụ dump heapsnapshot của toàn bộ ứng dụng Flutter Web/Desktop thật.
- **Nguyên tắc:** Tuyệt đối không suy diễn từ kết quả Provider harness hoặc UI sạch thành toàn bộ ứng dụng profile đã sạch.


---

## 2. Kết Quả Kiểm Chứng Controls (Provider Harness)

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
- **Static mutable collections found:** 0
- **Provider Lifecycle & Stream Disposal (từ ast_memory_audit.json):**
  - `auth_provider.dart`: Leak risk **NONE**, removeListener trong dispose=False, uncancelled=[]
  - `club_provider.dart`: Leak risk **NONE**, removeListener trong dispose=True, uncancelled=[]
  - `finance_provider.dart`: Leak risk **NONE**, removeListener trong dispose=True, uncancelled=[]
  - `session_provider.dart`: Leak risk **NONE**, removeListener trong dispose=True, uncancelled=[]

---

## 4. Bảo Mật & Sanitization

- Toàn bộ bằng chứng trong bundle này đã được **sanitized 100%**:
  - Không chứa số tài khoản ngân hàng thật, mã bí mật, mật khẩu hay JWT token nhạy cảm.
  - Các giá trị đối soát chỉ sử dụng fixture giả lập, boolean flags, và mã băm SHA-256.

---

## 5. Giới Hạn Kỹ Thuật & Khuyến Nghị

1. **Phạm vi đã kiểm chứng:** Đo lường cơ chế quản lý bộ nhớ, chuỗi tham chiếu sống và thu hồi GC của Dart VM Runtime trên Provider harness độc lập.
2. **Giới hạn môi trường (NOT RUN):** Chưa trích xuất file `.heapsnapshot` nhị phân từ Chrome DevTools Memory Profiler trên bản build Web profile.
3. **Quy định bàn giao:** Cổng V2b thuộc Nhóm 3 (Cổng môi trường chuyên sâu). Người triển khai ghi nhận kết quả và giới hạn trung thực, ghi nhận trạng thái **Chờ review**, KHÔNG tự ý ghi "Đạt" hay tự ý nghiệm thu toàn bộ BH-07.
