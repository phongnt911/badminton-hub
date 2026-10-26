# Bàn giao V2b — App-profile heap / in-memory retention sau đổi actor (Chờ review)

**Trạng thái: Chờ review độc lập.** Người triển khai **không** tự ghi Đạt.

- Nhánh: `feat/bh07-app-profile-heap-verification`
- Base: `3b30e4941058c0cfebec06b377abfc53f19576a4` (chốt review `c63e43f`, đóng HP3-C)
- Tested source: `bb2d2130276ad31824acc650a02ecee4b6ba95a6` (`git_dirty: false` tại thời điểm đo)
- Evidence: [`app_profile_heap_evidence/`](app_profile_heap_evidence/) — `summary.json`, `report.md`, `run.log`, `hashes.sha256`
- Tiêu chí: [`bh07_readiness.md` §4.4](bh07_readiness.md)
- Kết quả máy: `status=RUN`, `verdict=PASS`, 2/2 chu kỳ PASS, cleanup heap dump + profile Chrome đã xác minh

## 1. Phạm vi đã làm

Chỉ bổ sung công cụ đo local + test + tài liệu. **Không** sửa app/backend/contract, không đổi DB local, không migration, không merge `main`/`staging`/`production`, không deploy/pilot/BH-08.

| Thành phần | Đường dẫn |
| --- | --- |
| Runner đo | `scripts/bh07_appheap/run_app_profile_heap.js` |
| Oracle sentinel | `scripts/bh07_appheap/heap_oracle.py` |
| Auditor bundle | `scripts/bh07_appheap/verify_evidence.py` |
| Test oracle (14) | `tests/test_bh07_app_heap_oracle.py` |
| Test auditor (4) | `tests/test_bh07_app_heap_evidence.py` |

## 2. Phương pháp đo

- **Build profile thật:** `flutter build web --profile` (dart-defines `APP_ENV=test`, `SUPABASE_URL`, `SUPABASE_ANON_KEY` của Supabase local), serve tĩnh tại `http://127.0.0.1:8088`, Chrome headless thật điều khiển qua **Chrome DevTools Protocol** (`HeapProfiler.takeHeapSnapshot`).
- **Cùng một instance:** mỗi chu kỳ chỉ tạo **một** document; không reload, không `Page.navigate` giữa các mốc. Runner chụp `performance.timeOrigin` trước và sau chu kỳ và **fail** nếu khác nhau (`same_document: true` trong evidence).
- **Chu kỳ:** 2 chu kỳ, mỗi chu kỳ 4 mốc, `Owner → logout → Cohost/Member`:

  | Chu kỳ | Actor sau logout | Các mốc |
  | --- | --- | --- |
  | 1 | Cohost (`cohosta@example.test`) | `baseline` → `owner_active` → `post_logout` → `post_actor` |
  | 2 | Member (`membera@example.test`) | `baseline` → `owner_active` → `post_logout` → `post_actor` |

  Lý do tách 2 chu kỳ: renderer Chrome sống ổn định tới **4** heap snapshot trong một document; chuỗi 6 snapshot (Cohost rồi Member liên tiếp) làm trình duyệt chết giữa chuỗi (xem §6). Hai chu kỳ riêng vẫn giữ đúng "một instance cho mỗi lần đổi actor".
- **Thao tác UI thật, không mock:** login qua form thật (GoTrue local), mở `Buổi Chơi → Lịch sử buổi → UI Flow Session published to complete → Tổng kết buổi`, Owner thấy card `Tài chính tổng hợp`, Cohost thấy `Chỉ xem số lượng`, logout qua dialog `Đăng xuất/Đăng Xuất`, xác nhận guest `Bạn đang xem dưới dạng khách`, kiểm `localStorage` không còn `sb-*-auth-token`.

## 3. Oracle (quyết định PASS/FAIL)

Vì `dart2js` ở web profile **rút gọn tên class**, oracle không dựa vào tên class mà dựa trên **chuỗi sentinel thật của fixture** chỉ tồn tại trong payload tài chính riêng của Owner:

| Sentinel | Nguồn | Vai trò |
| --- | --- | --- |
| `bank` | `club_bank_accounts.account_number` của Club A (10 ký tự, sha256[:12] `65dce15efcc4`) | **sentinel chốt** — phải có khi Owner đang xem, phải mất sau logout/đổi actor |
| `expense` | `session_expenses.title` (sha256[:12] `41a394dd2dcd`) | chỉ chốt nếu màn hình Owner thực sự nạp; lần đo này **không** xuất hiện (`expense:false`) nên chỉ báo "not loaded", **không** dùng để kết luận |
| `probe` | marker `BH07APPHEAPPROBE-<runId>` gán lên `window` mỗi mốc | kiểm tra detector còn sống; thiếu ⇒ FAIL, tránh "sạch giả" |

Quy tắc cứng của oracle:

- Snapshot thiếu cấu trúc/thiếu đuôi/bị cắt ⇒ `ok=false` và verdict **FAIL**; **không bao giờ** đọc "không thấy sentinel" thành "sạch".
- Thiếu mốc, thiếu tín hiệu dương (`owner_active` phải có `bank`), `probe` chết, build không phải `profile`, cleanup chưa xác minh ⇒ FAIL.
- Kết luận dùng **chung một verdict** cho JSON, `report.md` và exit code.

## 4. Kết quả

Tested source `bb2d213`, `git_dirty: false`, Flutter 3.47.6 (stable), Chrome 155.0.8059.85, Node v24.21.0, Windows 10.0.26100; build profile 44.9 s.

| Chu kỳ | Mốc | Snapshot bytes | sha256[:12] | `bank` | `probe` |
| --- | --- | --- | --- | --- | --- |
| 1 Cohost | baseline | 58.337.657 | `b7af1df93088` | không | có |
| 1 Cohost | owner_active | 83.644.962 | `58ea5804d674` | **có** | có |
| 1 Cohost | post_logout | 69.240.102 | `1a4010b7fe12` | không | có |
| 1 Cohost | post_actor | 81.355.237 | `d10fbe9d3980` | không | có |
| 2 Member | baseline | 58.329.272 | `fe25f6852289` | không | có |
| 2 Member | owner_active | 84.345.277 | `1a179ca49760` | **có** | có |
| 2 Member | post_logout | 69.743.938 | `1f7fb2a4ff68` | không | có |
| 2 Member | post_actor | 73.929.215 | `97cd99659c71` | không | có |

Đọc kết quả: STK ngân hàng riêng của Owner **có thật** trong heap khi Owner đang xem (chứng minh detector hoạt động), và **không còn** sau logout lẫn sau khi Cohost/Member đăng nhập trong cùng instance. Hai chu kỳ lặp lại cùng kết luận.

## 5. Dọn dẹp và sanitize

- Heap snapshot ghi ra `%TEMP%\bh07_appheap_dumps_<pid>` (**ngoài repo**), quét **một lần** rồi xoá; `summary.json` ghi `dumps_dir_removed: true`, `raw_snapshots_remaining: 0`.
- Profile Chrome tạm `%TEMP%\bh07_appheap_chrome_<pid>` (~90 MB) cũng bị xoá và kiểm lại: `chrome_profile_dir_removed: true`.
- Bundle **không** chứa `.heapsnapshot/.heapprofile/.heaptimeline`, **không** chứa mật khẩu/JWT/DB URL/sentinel thô; chỉ công bố độ dài + sha256[:12].
- `verify_evidence.py` là auditor **read-only**: kiểm manifest `hashes.sha256`, cấm raw heap trong repo và trong bundle, cấm secret, cấm CRLF/BOM, và bắt `status=RUN` phải có verdict PASS + cleanup đã xác minh.

## 6. Giới hạn (phải đọc trước khi kết luận)

- **Đo V8/dart2js heap của bản web profile**, không phải Dart VM heap của bản desktop/mobile. Máy này **không có Visual Studio và không có Android SDK** (`flutter doctor`), nên đường **Dart VM service / DevTools Memory Profiler cho app desktop/mobile: NOT RUN**.
- Sentinel chứng minh **một số giá trị riêng của Owner** không còn reachable; **không** liệt kê đủ mọi retained object của model tài chính, không đo được "retention path" chi tiết theo từng tham chiếu như DevTools hiển thị.
- `expense` sentinel không được nạp ở màn hình đã mở ⇒ không sinh kết luận nào từ nó.
- Trong quá trình phát triển, chuỗi 6 snapshot/1 document làm tiến trình Chrome chết giữa chuỗi (không có log crash lý do; lần chạy chính thức chỉ dùng 4 snapshot/chu kỳ). Runner nay có timeout CDP 60 s + log `chrome exited unexpectedly` để lỗi như vậy **không** còn treo im lặng và không thể bị đọc thành PASS.
- Chưa đo tải thật/nhiều actor song song, chưa mobile/browser khác, chưa staging/production.

## 7. Lệnh đã chạy (máy triển khai)

| Lệnh | Exit | Ghi chú |
| --- | --- | --- |
| `node scripts/bh07_appheap/run_app_profile_heap.js --cycles 2` | 0 | build profile thật + 2 chu kỳ, `status=RUN verdict=PASS` |
| `python -X utf8 scripts/bh07_appheap/verify_evidence.py` | 0 | PASS: bundle đủ, hash khớp, không raw heap/secret, LF |
| `python -m unittest tests.test_bh07_app_heap_oracle tests.test_bh07_app_heap_evidence` | 0 | 18/18 OK |
| `python -m py_compile scripts/bh07_appheap/heap_oracle.py scripts/bh07_appheap/verify_evidence.py` | 0 | |
| `node --check scripts/bh07_appheap/run_app_profile_heap.js` | 0 | |
| `flutter analyze --no-pub` | 0 | 0 issue |
| `flutter test --no-pub` | 0 | 247 pass + 1 skip |

**Không** chạy trong lượt này: Dart VM service desktop/mobile (thiếu toolchain), V1/V5b và các cổng khác (giữ nguyên trạng thái đã có).

## 8. Gợi ý trọng tâm cho reviewer

1. Chạy lại `verify_evidence.py` và đọc `summary.json`/`report.md` độc lập với lời bàn giao này.
2. Kiểm phương pháp: có thật sự cùng document (`time_origin`, `same_document`), có reload/navigate ngầm không, có mock Auth/repository không.
3. Kiểm oracle có thể "sạch giả": snapshot hỏng/cắt, mốc thiếu, `probe` chết, build không profile, cleanup chưa xác minh — tất cả phải FAIL (đã có test).
4. Kiểm rò rỉ dữ liệu: bundle không chứa giá trị sentinel thô, mật khẩu, JWT; raw heap không nằm trong repo.
5. Kiểm giới hạn: kết luận chỉ trong phạm vi V8/web profile; desktop/mobile VM heap vẫn NOT RUN.
