# Bàn Giao Sửa Cổng V2b (Vòng 1/2) — Private Dart Heap / In-Memory Retention & Cache BH-07

- **Ngày bàn giao:** 25/10/2026
- **Nhánh:** `feat/bh07-private-heap-verification`
- **Base review thực tế:** `2dac37434df6b9409b53e36e65f3bc85bf755b40` (review [ccad24c](review_ccad24c.md))
- **Tested source SHA:** `33ad6e6fd7e33b8495ec9dda0732df1b6df2096b`
- **Docs/Evidence origin trước đó:** `eb4362bcec70e0922204b6a1040b02cbdb0f0924`
- **Người thực thi:** AI triển khai (Antigravity)
- **Người review dự kiến:** Codex (Reviewer độc lập)
- **Trạng thái:** **Chờ review độc lập vòng 1/2** (Người triển khai KHÔNG tự ghi Đạt).

---

## 1. Khắc Phục Toàn Diện Phát Hiện HP1–HP5 (Review `ccad24c`)

### HP1 (P1) — Định vị chuẩn xác phạm vi Provider harness & ghi nhận NOT RUN cho App Profile Heap
- **Khắc phục:**
  - Sửa đổi toàn bộ tiêu đề, docstring, setUp và comment trong [`test/integration/bh07_heap_verification_test.dart`](../../../test/integration/bh07_heap_verification_test.dart) để làm rõ đây là **Provider/Dart VM Harness — In-Memory State Purge & WeakReference Retention Test (Bằng chứng bổ trợ cấp Provider)**.
  - Làm rõ setup sử dụng `FakeAuth` và Mock Repositories để kiểm tra việc dọn state (`clearAll()`) và giải phóng tham chiếu mạnh tới các root DTO nhạy cảm khi nhận sự kiện `auth.changeUser(null)`.
  - Không tuyên bố là đã đo toàn bộ application instance, không tuyên bố "toàn bộ RAM đã bị xóa".
  - **Ghi nhận NOT RUN trung thực:** Phần đo **App Profile Heap Snapshot / Chrome DevTools Protocol / Retained Paths** của toàn bộ ứng dụng Flutter Web/Desktop profile thật được ghi nhận là **NOT RUN** do môi trường local headless chưa có công cụ dump heapsnapshot profile.
  - Tuyệt đối không suy diễn từ kết quả Provider WeakReference DTO hoặc UI sạch thành toàn bộ ứng dụng sạch.

### HP2 (P2) — Nâng cấp AST Memory Audit phân tích sâu cú pháp và scope dispose
- **Khắc phục:** Trong [`scripts/bh07_heap/audit_ast_memory.py`](../../../scripts/bh07_heap/audit_ast_memory.py):
  - Mở rộng nhận diện typed static (`static List<Object>`), inferred static constructors (`static final leak = List<Object>.empty(...)`), và global/top-level mutable collections (`final leak = <Object>[];`).
  - Hỗ trợ đầy đủ nullable subscriptions `StreamSubscription<int>? _sub` (bao gồm `_authSubscription` trong `AuthProvider`).
  - Phân tích cú pháp khối hàm `void dispose() { ... }` bằng thuật toán cân bằng ngoặc nhọn `{ ... }`.
  - Xác thực nghiêm ngặt: `removeListener` và `.cancel()` phải nằm **bên trong thân hàm `dispose()`**. Nếu nằm ngoài `dispose()` (ví dụ trong hàm `unused()`), tính là chưa giải phóng (`leak_risk: HIGH`).
  - Tích hợp cờ `--test-controls` chạy tự kiểm tra 5 controls (typed static, inferred constructor, global list, nullable uncancelled, remove outside dispose) đạt 5/5 PASS.

### HP3 (P2) — Bỏ hardcode PASS trong summary và report; parse kết quả động
- **Khắc phục:** Trong [`scripts/bh07_heap/run_heap_verification.py`](../../../scripts/bh07_heap/run_heap_verification.py):
  - Viết hàm `parse_test_results` phân tích trực tiếp output thực tế từ `test_output`. Nếu test thất bại (`test_ok == False`), cả 10 controls được gán chính xác là `FAIL`, số test passed/failed được phản ánh đúng thực tế, `suite_verdict: FAIL`.
  - Đọc kết quả trực tiếp từ `ast_memory_audit.json` thay vì hardcode.
  - Báo cáo Markdown kiểm tra điều kiện `test_ok` và `ast_ok`; không in mẫu template thành công hay tuyên bố `7/7 PASS` khi test thất bại.
  - Ghi nhận `git_dirty_paths` cụ thể từ `git status --porcelain` và mã băm `source_hashes` của 4 file kiểm chứng nhằm ràng buộc provenance chặt chẽ.

### HP4 (P2) — Bổ sung đầy đủ raw log gốc và tái tạo bundle mới sạch sẽ
- **Khắc phục:**
  - File `heap_test_run.log` ban đầu bị bỏ qua do `.gitignore` chứa rule `*.log`.
  - Đã thực hiện commit tested source sạch [`33ad6e6`](../../../commit/33ad6e6fd7e33b8495ec9dda0732df1b6df2096b), sau đó chạy full runner tái tạo toàn bộ bundle bằng chứng mới.
  - Sử dụng lệnh `git add -f docs/reviews/bh07/private_heap_evidence/heap_test_run.log` để force-add file nhật ký test gốc vào Git.
  - Bundle evidence có đủ 4/4 files, manifest SHA-256 khớp 100%.

### HP5 (P2) — Strict Verifier kiểm tra binary bytes của manifest, từ chối CRLF/BOM
- **Khắc phục:** Trong [`scripts/bh07_heap/clean_and_manifest.py`](../../../scripts/bh07_heap/clean_and_manifest.py):
  - Đọc file manifest `hashes.sha256` dưới dạng raw binary (`read_bytes()`).
  - Kiểm tra và báo lỗi ngay lập tức nếu phát hiện BOM (`\xef\xbb\xbf`) hoặc byte `\r` (CRLF).
  - Kiểm tra tính hợp lệ của định dạng từng dòng (`<64 hex><2 spaces><relative_path>`), từ chối dòng rác, dòng trống ở giữa hoặc duplicate paths.
  - Bảo đảm nguyên tắc **strict read-only** (so sánh mã băm trước và sau, không sửa file khi verify).
  - Tích hợp cờ `--test-controls` kiểm tra 5 cases (positive, manifest_crlf, hash_mismatch, missing, extra) đều đạt PASS và đảm bảo tính read-only.

---

## 2. Kết Quả Kiểm Thử Thực Tế

| Lệnh / Công cụ | Số lượng / Kết quả | Chi tiết |
|---|---|---|
| `flutter test test/integration/bh07_heap_verification_test.dart` | 7/7 **PASS** | Baseline, Full cycle (P1, N1, N2, N3), Late response drop (N4, N5), Mutant controls (M1, M2), Session/Club purge. |
| `flutter analyze` | 0 warning / 0 error | `No issues found! (ran in 1.1s)` |
| `flutter test` | 247 pass / 1 skip | Toàn bộ suite hồi quy Flutter xanh 100%. |
| `python scripts/bh07_heap/audit_ast_memory.py --test-controls` | 5/5 **PASS** | Tự kiểm tra 5 controls của AST memory audit thành công. |
| `python scripts/bh07_heap/audit_ast_memory.py` | 38 files **CLEAN** | 0 static mutable collections, 100% provider subscriptions/listeners được dispose. |
| `python scripts/bh07_heap/clean_and_manifest.py --test-controls` | 5/5 **PASS** | Tự kiểm tra 5 controls của verifier (từ chối CRLF, mismatch, missing, extra; readonly). |
| `python scripts/bh07_heap/clean_and_manifest.py --verify` | 4/4 files **PASS** | Toàn bộ bundle evidence tuân thủ strict UTF-8 LF, hash khớp, 0 secret leak. |

---

## 3. Thư Mục Bằng Chứng & Manifest

Thư mục bằng chứng: [`docs/reviews/bh07/private_heap_evidence/`](private_heap_evidence/)
Bao gồm đủ 4 file:
1. `ast_memory_audit.json`: Kết quả phân tích tĩnh AST 38 files Dart trong `lib/`.
2. `heap_test_run.log`: Nhật ký chạy thực tế của suite test Provider heap.
3. `summary.json`: Tóm tắt các controls, môi trường và provenance.
4. `heap_verification_report.md`: Báo cáo chi tiết phương pháp và kết quả.
5. `hashes.sha256`: Bảng mã băm SHA-256 các file trên:
```
5959fea0da97557d1e3cdedf1cb1817fce4537c967c961a04c3498b3969d1a13  ast_memory_audit.json
c96decb97d11422759401fdd382dc559f13281155922d40de5b510bfd9090915  heap_test_run.log
5b9764855398b0dd8bdd2f7a8cd45ed0778fcf626ab650837b64cd6296968f66  heap_verification_report.md
df4fb9b14801c1c06377c204b4b8ae839f04e5461713e1c72a9b108495b34721  summary.json
```

---

## 4. Công Bố Giới Hạn & Trạng Thái

1. **Phạm vi hoàn thành:** Provider / VM test harness (bằng chứng bổ trợ cấp Provider). Xác nhận 100% các đối tượng tài chính nhạy cảm của Owner được giải phóng khỏi Provider và thu hồi sạch khỏi heap sau logout.
2. **Giới hạn môi trường (NOT RUN):** App profile heap snapshot trên toàn bộ cây widget và SupabaseClient thật trên Flutter Web/Desktop profile mode là NOT RUN.
3. **Quy định bàn giao:** Cổng V2b đang ở trạng thái **Chờ review độc lập vòng 1/2**. Người triển khai KHÔNG tự ghi "Đạt".
4. Giữ nguyên **V1** và **V5b** Đạt local; toàn dự án BH-07 chưa nghiệm thu; không merge vào `main`, `staging`, `production`, không deploy, không pilot và không chuyển sang BH-08.
