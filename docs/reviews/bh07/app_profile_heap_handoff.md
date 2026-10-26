# Bàn giao V2b — App-profile heap / in-memory retention sau đổi actor (Chờ review vòng 1/2)

**Trạng thái: Chờ review độc lập vòng 1/2 sau sửa AH1–AH5.** Người triển khai **không** tự ghi Đạt.

- Nhánh: `feat/bh07-app-profile-heap-verification`
- Base review: `a972ecd73ab2339306f80b081823057c5935819c` ([review 8914b2f](review_8914b2f.md))
- Tested source (lần đo mới): `249f12ed5b8ba042de1d48e9d5e06ffe7c125ada` (`git_dirty: false` tại thời điểm đo)
- Evidence: [`app_profile_heap_evidence/`](app_profile_heap_evidence/) — `summary.json`, `report.md`, `run.log`, `hashes.sha256`
- Bundle tác giả **cũ** (trước sửa) bị thay thế; vẫn tra được ở lịch sử Git tại `8914b2f` (`docs/reviews/bh07/app_profile_heap_evidence/`).
- Tiêu chí: [`bh07_readiness.md` §4.4](bh07_readiness.md)
- Kết quả máy: `status=RUN`, `verdict=PASS`, 2/2 chu kỳ PASS, cleanup heap dump + profile Chrome đã xác minh

## 1. Phạm vi đã làm

Chỉ sửa **công cụ kiểm chứng + test + tài liệu/bằng chứng**. **Không** sửa app/backend/contract, không đổi DB local, không migration, không merge `main`/`staging`/`production`, không deploy/pilot/BH-08.

| Thành phần | Đường dẫn | Control |
| --- | --- | --- |
| Runner đo | `scripts/bh07_appheap/run_app_profile_heap.js` | — |
| Guard build/serve (mới) | `scripts/bh07_appheap/build_guard.js` | 8 self-test |
| Oracle sentinel | `scripts/bh07_appheap/heap_oracle.py` | 24 |
| Auditor bundle | `scripts/bh07_appheap/verify_evidence.py` | 36 |
| Test oracle | `tests/test_bh07_app_heap_oracle.py` | 24 |
| Test auditor | `tests/test_bh07_app_heap_evidence.py` | 36 |
| Test guard build/serve | `tests/test_bh07_app_heap_build_guard.py` | 3 |
| Phát lại probe reviewer | `tests/test_bh07_app_heap_review_controls.py` | 3 |

## 2. Sửa theo review 8914b2f

| Phát hiện | Cách sửa | Control tái hiện (đã đỏ trước khi sửa) |
| --- | --- | --- |
| **AH1 P1** — snapshot hỏng vẫn PASS | `heap_oracle.validate()` đọc **nhị phân** và chứng minh dump là snapshot V8 hoàn chỉnh **trước khi** câu trả lời sentinel có hiệu lực: object `"snapshot"` parse riêng (không `json.load` cả 80 MB), thứ tự `nodes`→`edges`→`strings`, số phần tử `nodes` khớp `node_count × len(node_fields)`, `edges` khớp `edge_count × len(edge_fields)`, bảng số chỉ chứa số nguyên, bảng `strings` chỉ chứa chuỗi JSON và **nằm cuối** (chỉ `}` sau nó). Dump không dùng được ⇒ `ok:false`, mọi `sentinels.*.present = null` (không bao giờ suy "vắng = sạch"). | `invalid_literal`, `truncated`, `trailing_garbage`, `node_count_mismatch`, `edge_count_mismatch`, `missing_chunk_mid_stream`, `unterminated_string`, `metadata_without_v8_fields`, `metadata_with_inconsistent_types`, `strings_not_last`, `empty_snapshot` |
| **AH2 P2** — auditor không kiểm số chu kỳ/mốc/verdict | Auditor **tự tính lại** verdict từng chu kỳ và verdict tổng bằng chính `heap_oracle.decide`, với expectation **suy từ scan** (không tin file của runner): bắt buộc đúng 2 actor path (`cohost`, `member`), đúng 4 mốc, `same_document`, `time_origin`, `ok` từng scan, `probe` sống, positive Owner, negative sau đổi actor; verdict tổng và `findings` phải khớp dữ liệu; `report.md` phải khớp status/source/số liệu từng mốc. | `zero_cycles`, `single_cycle`, `same_actor_twice`, `missing_epoch`, `extra_epoch`, `failed_scan_with_leak`, `retained_after_logout`, `dead_detector`, `cycle_verdict_mismatch`, `overall_verdict_mismatch`, `report_status_mismatch`, `report_missing_epoch_row` |
| **AH3 P2** — manifest không bao phủ file thừa; secret scan bị bỏ qua | Manifest phải phủ **đúng** tập file xuất bản (cấm file thừa, entry trùng, `..`/absolute/backslash, symlink, tự hash chính nó); mọi file được quét secret, cấm raw heap; hash toàn bộ bundle **trước và sau** để chứng minh auditor read-only. | `unmanifested_extra`, `unmanifested_secret`, `secret_in_manifested_file`, `manifest_traversal`, `manifest_absolute`, `manifest_duplicate`, `manifest_missing_entry`, `manifest_self_entry`, `published_raw_heap`, `sentinel_value_published`, `audit_is_readonly` |
| **AH4 P2** — CRLF/UTF-8 lỗi vẫn qua auditor strict LF | Đọc **bytes** trước: cấm BOM, cấm mọi byte CR, decode UTF-8 `strict` (không `errors='replace'`, không universal-newline) cho cả manifest lẫn mọi file xuất bản. | `crlf`, `lone_cr`, `crlf_manifest`, `invalid_utf8`, `bom` |
| **AH5 P2** — `--reuse-build` tự gắn profile vô căn cứ | `--reuse-build` **bị từ chối** (throw); preflight cổng 8088 bằng **connect** (không chỉ bind); runner hash **39 artifact** `build/web` sau build, kiểm artifact do chính lần chạy này sinh ra, và chứng minh byte server trả (`index.html`, `main.dart.js`) **trùng hash artifact**; auditor đòi `mode=profile`, `artifacts`, `started_at`, `served_match=true`, không `reused`. | `missing_artifact`, `stale_artifact`, `rebuilt_identical_artifact`, `fresh_artifact`, `served_match`, `served_mismatch`, `occupied_port`, `free_port`; probe reviewer `build_probe.js` nay exit 1 |

Phát lại probe reviewer **không sửa file** (`docs/reviews/bh07/review_8914b2f_evidence/probes.py`, `build_probe.js`): mọi ca `invalid_snapshot`, `full_cycle_with_invalid_snapshot`, `crlf`, `invalid_utf8`, `unmanifested_secret_extra`, `zero_cycles`, `missing_epoch`, `leaked_failed_scan` nay đều bị chặn, `build_probe.js` exit 1 (trước exit 0 và in `mode:'profile'`).

Lưu ý trung thực khi phát lại trên Windows: `probes.py` ghi lại manifest bằng `write_text` (`rehash()`), nên trên Windows `hashes.sha256` thành CRLF và **chính nó** sinh thêm finding strict-LF; vì vậy một số ca bị chặn **đồng thời** bởi strict LF và bởi ngữ nghĩa. Các control ngữ nghĩa tương ứng trong `tests/test_bh07_app_heap_evidence.py` ghi hash bằng `write_bytes` (LF-safe) nên chứng minh **đúng lý do ngữ nghĩa** bị chặn (`zero_cycles`, `missing_epoch`, `failed_scan_with_leak`, `retained_after_logout`, `dead_detector`, ...). Kết quả phát lại: 8/8 ca đều có finding chặn, `build_probe.js` exit 1.

## 3. Phương pháp đo

- **Build profile thật:** `flutter build web --profile` (dart-defines `APP_ENV=test`, `SUPABASE_URL`, `SUPABASE_ANON_KEY` của Supabase local), serve tĩnh tại `http://127.0.0.1:8088`, Chrome headless thật điều khiển qua **Chrome DevTools Protocol** (`HeapProfiler.takeHeapSnapshot`).
- **Cùng một instance:** mỗi chu kỳ chỉ tạo **một** document; không reload, không `Page.navigate` giữa các mốc. Runner chụp `performance.timeOrigin` trước và sau chu kỳ và **fail** nếu khác nhau (`same_document: true` trong evidence).
- **Chu kỳ:** 2 chu kỳ, mỗi chu kỳ 4 mốc, `Owner → logout → Cohost/Member`:

  | Chu kỳ | Actor sau logout | Các mốc |
  | --- | --- | --- |
  | 1 | Cohost (`cohosta@example.test`) | `baseline` → `owner_active` → `post_logout` → `post_actor` |
  | 2 | Member (`membera@example.test`) | `baseline` → `owner_active` → `post_logout` → `post_actor` |

  Lý do tách 2 chu kỳ: renderer Chrome sống ổn định tới **4** heap snapshot trong một document; chuỗi 6 snapshot (Cohost rồi Member liên tiếp) làm trình duyệt chết giữa chuỗi (xem §6).
- **Thao tác UI thật, không mock:** login qua form thật (GoTrue local), mở `Buổi Chơi → Lịch sử buổi → UI Flow Session published to complete → Tổng kết buổi`, Owner thấy card `Tài chính tổng hợp`, Cohost thấy `Chỉ xem số lượng`, logout qua dialog `Đăng xuất/Đăng Xuất`, xác nhận guest `Bạn đang xem dưới dạng khách`, kiểm `localStorage` không còn `sb-*-auth-token`.

## 4. Oracle (quyết định PASS/FAIL)

Vì `dart2js` ở web profile **rút gọn tên class**, oracle không dựa vào tên class mà dựa trên **chuỗi sentinel thật của fixture** chỉ tồn tại trong payload tài chính riêng của Owner:

| Sentinel | Nguồn | Vai trò |
| --- | --- | --- |
| `bank` | `club_bank_accounts.account_number` của Club A (10 ký tự, sha256[:12] `65dce15efcc4`) | **sentinel chốt** — phải có khi Owner đang xem, phải mất sau logout/đổi actor |
| `expense` | `session_expenses.title` (sha256[:12] `41a394dd2dcd`) | chỉ chốt nếu màn hình Owner thực sự nạp; lần đo này **không** xuất hiện (`expense:false`) nên chỉ báo "not loaded", **không** dùng để kết luận |
| `probe` | marker `BH07APPHEAPPROBE-<runId>` gán lên `window` mỗi mốc | kiểm tra detector còn sống; thiếu ⇒ FAIL, tránh "sạch giả" |

Quy tắc cứng của oracle:

- Snapshot phải **chứng minh cấu trúc** (metadata + thứ tự bảng + counts + bảng strings ở cuối); thiếu/hỏng/bị cắt ⇒ `ok=false`, presence `null`, verdict **FAIL**; **không bao giờ** đọc "không thấy sentinel" thành "sạch".
- Thiếu mốc, mốc thừa, thiếu tín hiệu dương (`owner_active` phải có `bank`), `probe` chết, build không phải `profile`, cleanup chưa xác minh ⇒ FAIL.
- Kết luận dùng **chung một verdict** cho JSON, `report.md` và exit code; auditor tính lại độc lập từ scan.

## 5. Kết quả (lần đo mới, source sạch `249f12e`)

Tested source `249f12e`, `git_dirty: false`, Flutter 3.47.6 (stable), Chrome 155.0.8059.85, Node v24.21.0, Windows 10.0.26100; build profile 50,7 s, **39 artifact** đã hash và `served_match: true`.

| Chu kỳ | Mốc | Snapshot bytes | sha256[:12] | `bank` | `probe` |
| --- | --- | --- | --- | --- | --- |
| 1 Cohost | baseline | 58.414.388 | `35fd5a35e3ca` | không | có |
| 1 Cohost | owner_active | 84.037.436 | `f49ae02f751f` | **có** | có |
| 1 Cohost | post_logout | 69.258.978 | `99ba1a5b2d49` | không | có |
| 1 Cohost | post_actor | 82.317.587 | `3852b92e2732` | không | có |
| 2 Member | baseline | 58.326.149 | `4062854ebdfe` | không | có |
| 2 Member | owner_active | 83.941.045 | `3b75780647e9` | **có** | có |
| 2 Member | post_logout | 69.379.107 | `67446555bb72` | không | có |
| 2 Member | post_actor | 73.596.863 | `7a4d6d280731` | không | có |

Đọc kết quả: STK ngân hàng riêng của Owner **có thật** trong heap khi Owner đang xem (chứng minh detector hoạt động), và **không còn** sau logout lẫn sau khi Cohost/Member đăng nhập trong cùng instance. Hai chu kỳ lặp lại cùng kết luận; `time_origin` mỗi chu kỳ ổn định trước/sau 4 mốc.

## 6. Dọn dẹp và sanitize

- Heap snapshot ghi ra `%TEMP%\bh07_appheap_dumps_<pid>` (**ngoài repo**), quét **một lần** rồi xoá; `summary.json` ghi `dumps_dir_removed: true`, `raw_snapshots_remaining: 0`.
- Profile Chrome tạm `%TEMP%\bh07_appheap_chrome_<pid>` (~90 MB) cũng bị xoá và kiểm lại: `chrome_profile_dir_removed: true`.
- Bundle **không** chứa `.heapsnapshot/.heapprofile/.heaptimeline`, **không** chứa mật khẩu/JWT/DB URL/sentinel thô; chỉ công bố độ dài + sha256[:12].
- `verify_evidence.py` là auditor **read-only**: đọc bytes, cấm BOM/CR/UTF-8 lỗi, phủ đúng tập file bằng manifest, cấm raw heap + secret trên **mọi** file, tự tính lại verdict, và hash bundle trước/sau để chứng minh không sửa gì.

## 7. Giới hạn (phải đọc trước khi kết luận)

- **Đo V8/dart2js heap của bản web profile**, không phải Dart VM heap của bản desktop/mobile. Máy này **không có Visual Studio và không có Android SDK** (`flutter doctor`), nên đường **Dart VM service / DevTools Memory Profiler cho app desktop/mobile: NOT RUN**.
- Sentinel chứng minh **một số giá trị riêng của Owner** không còn reachable; **không** liệt kê đủ mọi retained object của model tài chính, không đo được "retention path" chi tiết theo từng tham chiếu như DevTools hiển thị.
- `expense` sentinel không được nạp ở màn hình đã mở ⇒ không sinh kết luận nào từ nó.
- Kiểm "artifact do lần chạy này sinh ra" dựa trên **mtime** của `index.html`/`main.dart.js` (hoặc hash trùng với trước build). Đây là bằng chứng gián tiếp; bằng chứng trực tiếp là byte server trả trùng hash artifact vừa build.
- Chuỗi 6 snapshot/1 document từng làm Chrome chết giữa chuỗi; runner có timeout CDP 60 s + log `chrome exited unexpectedly` để lỗi như vậy **không** còn treo im lặng và không thể bị đọc thành PASS.
- Chưa đo tải thật/nhiều actor song song, chưa mobile/browser khác, chưa staging/production.

## 8. Lệnh đã chạy (máy triển khai)

| Lệnh | Exit | Ghi chú |
| --- | --- | --- |
| `node scripts/bh07_appheap/build_guard.js --self-test` | 0 | 8/8 control |
| `node docs/reviews/bh07/review_8914b2f_evidence/build_probe.js` | 1 | từ chối `--reuse-build` (trước exit 0) |
| `python -X utf8 docs/reviews/bh07/review_8914b2f_evidence/probes.py` | 0 | script chỉ in JSON; 8/8 ca đều có finding chặn (không ca nào PASS) |
| `node scripts/bh07_appheap/run_app_profile_heap.js --cycles 2` | 0 | build profile thật + 2 chu kỳ, `status=RUN verdict=PASS` |
| `python -X utf8 scripts/bh07_appheap/verify_evidence.py` | 0 | PASS: bundle đủ, hash khớp, verdict tính lại khớp, không raw heap/secret, LF |
| `python -m unittest tests.test_bh07_app_heap_oracle tests.test_bh07_app_heap_evidence tests.test_bh07_app_heap_build_guard tests.test_bh07_app_heap_review_controls` | 0 | 66/66 OK |
| `node --check scripts/bh07_appheap/run_app_profile_heap.js scripts/bh07_appheap/build_guard.js` | 0 | |
| `flutter analyze --no-pub` | 0 | 0 issue |
| `flutter test --no-pub` | 0 | 247 pass + 1 skip |

**Không** chạy trong lượt này: Dart VM service desktop/mobile (thiếu toolchain), V1/V5b và các cổng khác (giữ nguyên trạng thái đã có).

## 9. Gợi ý trọng tâm cho reviewer

1. Chạy lại `verify_evidence.py` và đọc `summary.json`/`report.md` độc lập với lời bàn giao này.
2. Phát lại `review_8914b2f_evidence/probes.py` và `build_probe.js` **nguyên bản**: mọi ca phải bị chặn; thử thêm mutant mới (snapshot hợp lệ nhưng count sai, manifest có file thừa, verdict ghi tay) — gate phải là semantic, không chỉ hash.
3. Kiểm oracle có thể "sạch giả": dump cắt/chunk mất/metadata sai/strings không ở cuối ⇒ `ok:false` + `present:null`.
4. Kiểm AH5: build debug/release rồi chạy lại phải FAIL; cổng 8088 đã có server phải bị từ chối; server trả byte khác phải FAIL.
5. Kiểm giới hạn: kết luận chỉ trong phạm vi V8/web profile; desktop/mobile VM heap vẫn NOT RUN.
