# Bàn giao V2b — App-profile heap / in-memory retention sau đổi actor (Chờ review, sửa AH7/AH8 theo ủy quyền ngoại lệ)

**Trạng thái: Chờ review độc lập sau sửa AH7/AH8 (ủy quyền ngoại lệ của chủ dự án sau khi review 76334e2 DỪNG vòng 2/2).** Người triển khai **không** tự ghi Đạt.

- Nhánh: `feat/bh07-app-profile-heap-verification`
- Base review: `268735ccd071936bada7cbcdf81fad6c87187e00` ([review 76334e2](review_76334e2.md))
- Tested source (runtime lần đo mới): `c3ca02e` — `git_dirty: false` tại thời điểm bắt đầu đo
- Evidence: [`app_profile_heap_evidence/`](app_profile_heap_evidence/) — `summary.json`, `report.md`, `run.log`, `hashes.sha256`
- Bundle các vòng trước vẫn tra được ở lịch sử Git: `268735c` (vòng 2 / AH1–AH6), `8c02605` (vòng 1); evidence của reviewer (`review_*_evidence/`) giữ nguyên, không sửa.
- Tiêu chí: [`bh07_readiness.md` §4.4](bh07_readiness.md)
- Kết quả máy: `status=RUN`, `verdict=PASS`, 2/2 chu kỳ PASS, cleanup dump + profile Chrome đã xác minh

## 1. Phạm vi

Chỉ sửa **công cụ kiểm chứng + test + tài liệu/bằng chứng**. Không sửa `lib/`, app/backend/contract, không đổi DB/migration, không merge `main`/`staging`/`production`, không deploy/pilot/BH-08.

| Thành phần | Đường dẫn | Control |
| --- | --- | --- |
| Oracle sentinel | `scripts/bh07_appheap/heap_oracle.py` | 36 (self-test 14) |
| Auditor bundle | `scripts/bh07_appheap/verify_evidence.py` | 77 |
| Runner đo | `scripts/bh07_appheap/run_app_profile_heap.js` | phát `available` cho sentinel |
| Guard build/serve | `scripts/bh07_appheap/build_guard.js` | 8 self-test |
| Test oracle | `tests/test_bh07_app_heap_oracle.py` | 36 |
| Test auditor | `tests/test_bh07_app_heap_evidence.py` | 77 |
| Test guard + sanitizer | `tests/test_bh07_app_heap_build_guard.py` | 4 |
| Phát lại probe reviewer | `tests/test_bh07_app_heap_review_controls.py` | 3 |
| Audit link trạng thái | `tests/test_bh07_app_heap_links.py` | 3 |

Tổng: **123 test Python** (36 + 77 + 4 + 3 + 3).

## 2. Sửa theo review 76334e2

| Phát hiện | Cách sửa | Control tái hiện (đỏ trước sửa) |
| --- | --- | --- |
| **AH7 P2** — hai JSON cùng giá trị cho presence trái nhau (literal `true`, `\uXXXX` `false`) | Nguyên nhân: `scan()` đếm **raw bytes** sau khi đã parse đúng. Nay `parse_snapshot()` trả **document đã parse** và `scan()` đếm sentinel trên **bảng `strings` đã decode** (`count_sentinels`), nên cùng một giá trị string table luôn cho cùng presence/occurrences, bất kể cách JSON escape; dump hỏng vẫn `ok:false` + presence `null`. Matching policy ghi rõ: substring, exact/case-sensitive, cộng theo từng string value. Parse chỉ chạy **một lần** (không parse lại). | `RepresentationControls` (6): escaped = literal về document/presence/occurrences; chu kỳ có bank escaped còn retained ⇒ **FAIL** đúng mốc `post_actor`; bank literal còn retained ⇒ FAIL; mixed literal/escaped ⇒ FAIL; escaped vắng ⇒ PASS |
| **AH8 P2** — thiếu `length`/`sha256_12` làm tắt detector raw sentinel mà bundle vẫn PASS | `_check_sentinels` **không `continue` im lặng** nữa: mọi sentinel bắt buộc (`bank`, `probe`) và **mọi sentinel mà scan nhắc tới** phải có metadata nhận diện; `length` phải là `int` dương thật (loại bool/0/âm/None) và `sha256_12` phải đúng 12 hex, thiếu/sai ⇒ finding. Sentinel optional không đo được phải khai `available: false` **và** không được xuất hiện trong scan hay công bố length/hash; runner nay phát cờ `available` tường minh. | `SentinelMetadataControls` (13): mất `length`, mất hash, `null`/0/âm/bool length, hash sai định dạng, mất entry `bank`, scan nhắc sentinel không có metadata, `available:false` bị scan claim, `available:false` mà vẫn công bố hash, raw trong log + mất `length`; positive `available:false` hợp lệ ⇒ PASS; positive hash-only ⇒ PASS |

Giữ nguyên AH1–AH6 và AH4/AH5; chạy lại toàn bộ để chứng minh không hồi quy (probe cũ giữ nguyên kỳ vọng).

### Bằng chứng đỏ trước khi sửa

Chạy test mới trên công cụ vừa bàn giao vòng 2 (`76334e2`): **`Ran 113, FAILED (failures=12)`** — đúng AH7 (2: escaped presence + chu kỳ retained escaped) và AH8 (10: missing/null/zero/negative/bool length, missing hash, mất entry `bank`, scan không metadata, `available:false` công bố hash, raw + mất length). Sau sửa: **123/123 OK**.

## 3. Phương pháp đo và kết quả lần đo mới (source sạch `c3ca02e`)

Build `flutter build web --profile` thật (dart-defines `APP_ENV=test` + Supabase local), serve tĩnh `127.0.0.1:8088`, Chrome headless thật qua CDP `HeapProfiler.takeHeapSnapshot`; mỗi chu kỳ một document (`performance.timeOrigin` trước/sau), 2 chu kỳ `Owner → logout → Cohost/Member`, mỗi chu kỳ 4 mốc. Chrome 155.0.8059.85, Flutter 3.47.6, Node v24.21.0, Windows 10.0.26100.

Build profile **46,7 s**, **39 artifact** đã hash, `served_match: true`, `git_dirty: false`.

| Chu kỳ | Mốc | Snapshot bytes | sha256[:12] | present | `bank` | `probe` |
| --- | --- | --- | --- | --- | --- | --- |
| 1 Cohost | baseline | 58.363.385 | `1cae110873fe` | probe | không | có |
| 1 Cohost | owner_active | 83.871.151 | `2f0d8d9780e1` | bank, probe | **có** | có |
| 1 Cohost | post_logout | 69.242.212 | `1acb09bd3241` | probe | không | có |
| 1 Cohost | post_actor | 82.147.760 | `50fb576cacd7` | probe | không | có |
| 2 Member | baseline | 58.400.095 | `e1b7fbbc9e08` | probe | không | có |
| 2 Member | owner_active | 83.608.303 | `5b318ee6dcf1` | bank, probe | **có** | có |
| 2 Member | post_logout | 69.482.713 | `599b05cbb56c` | probe | không | có |
| 2 Member | post_actor | 73.669.489 | `8ff4ebdcab6d` | probe | không | có |

Sentinels công bố (chỉ metadata): `bank` (10, `65dce15efcc4`), `expense` (16, `41a394dd2dcd`), `probe` (25, `94a462a8be32`), cả ba `available: true`. Occurrences đếm trên string table đã decode: `bank` 1 ở `owner_active`/0 ở các mốc còn lại, `probe` 1 ở mọi mốc, `expense` 0 (màn hình Owner không nạp).

Đọc kết luận: STK ngân hàng riêng của Owner **có thật** trong heap khi Owner đang xem và **không còn** sau logout lẫn sau khi Cohost/Member đăng nhập, lặp lại ở cả 2 chu kỳ — **trong phạm vi V8/web profile**.

## 4. Lệnh đã chạy (máy triển khai, cây sạch tại `c3ca02e`)

| Lệnh | Exit | Ghi chú |
| --- | --- | --- |
| `python -X utf8 -m unittest tests.test_bh07_app_heap_oracle tests.test_bh07_app_heap_evidence tests.test_bh07_app_heap_build_guard tests.test_bh07_app_heap_review_controls tests.test_bh07_app_heap_links` | 0 | **123/123 OK** |
| `python -X utf8 scripts/bh07_appheap/heap_oracle.py self-test` | 0 | 14/14 control |
| `node scripts/bh07_appheap/build_guard.js --self-test` | 0 | 8/8 control |
| `node scripts/bh07_appheap/run_app_profile_heap.js --cycles 2` | 0 | `status=RUN verdict=PASS cycles=2`, build 46,7 s |
| `python -X utf8 scripts/bh07_appheap/verify_evidence.py` | 0 | PASS trên bundle mới |
| `python -X utf8 docs/reviews/bh07/review_76334e2_evidence/closure_controls.py` | 0 | escaped=literal (`present:true`, 1 occurrence); chu kỳ retained escaped ⇒ **FAIL**; thiếu `length`/`sha256_12` ⇒ có finding |
| `python -X utf8 docs/reviews/bh07/review_57ec02c_evidence/extra_controls.py` | 0 | positive PASS; grammar/summary/Markdown/symlink/raw-sentinel vẫn bị chặn; CLI `{}` exit 1 |
| `python -X utf8 docs/reviews/bh07/review_8914b2f_evidence/probes.py` | 0 | 8/8 ca có finding chặn |
| `node docs/reviews/bh07/review_8914b2f_evidence/build_probe.js` | 1 | từ chối `--reuse-build` |
| `python -X utf8 docs/reviews/bh07/review_57ec02c_evidence/link_audit.py` | 0 | `[]` |
| `flutter analyze --no-pub` | 0 | no issues |
| `flutter test --no-pub` | 0 | 247 pass + 1 skip |

## 5. Dọn dẹp, sanitize, readonly

- Heap dump + profile Chrome ghi **ngoài repo**, quét một lần rồi xoá; `summary.json`: `dumps_dir_removed: true`, `raw_snapshots_remaining: 0`, `chrome_profile_dir_removed: true`, `ok: true`.
- Bundle chỉ 4 file (3 entry manifest): chỉ `length` + `sha256[:12]`, không giá trị thô, không `.heapsnapshot`.
- Auditor read-only: hash **mọi entry** (file/dir/link) trước và sau; test readonly của suite vẫn qua.

## 6. Giới hạn / NOT RUN

- **Dart VM heap desktop/mobile: NOT RUN** — thiếu Visual Studio/Android SDK; kết luận chỉ trong phạm vi **V8/dart2js của web profile**.
- **Runtime reviewer: NOT RUN** — lần đo này là của người triển khai, không thay lần chạy reviewer.
- **AH7 chỉ chứng minh oracle nhất quán trên JSON hợp lệ** (literal vs escaped); **không** chứng minh Chrome 155 thực sự ghi dạng escaped trong 8 dump của lần đo (dump đã xoá) và **không** kết luận app leak.
- Nhánh `available: false` của sentinel optional chỉ được kiểm bằng **unit test**: fixture hiện tại luôn có `expense` title nên runtime ghi `available: true`; runtime cho trường hợp không có expense **NOT RUN**.
- Sentinel chứng minh **một số giá trị riêng của Owner** không còn reachable; **không** liệt kê đủ retained object/model/cache/listener, không đo retention path chi tiết.
- Windows junction và link control tự `skip` trên host thiếu quyền tạo link (máy này tạo được nên đã chạy thật).
- Chưa đo tải thật/nhiều actor song song, chưa mobile/browser khác, chưa staging/production.

## 7. Trọng tâm cho reviewer

1. Chạy lại `closure_controls.py` **nguyên bản**: escaped/literal phải cùng presence, chu kỳ retained escaped phải FAIL, thiếu `length`/`sha256_12` phải có finding.
2. Thử mutant: sentinel có `length`/hash đúng nhưng **occurrences** ghi tay; sentinel `available:false` xuất hiện trong scan; raw sentinel ở file thứ 5 đã thêm manifest.
3. Kiểm AH1/AH2/AH3 không hồi quy: `probes.py`, `extra_controls.py`, `build_probe.js`, `link_audit.py` giữ nguyên kỳ vọng.
4. Kiểm auditor không phụ thuộc secret: chỉ `length` + `sha256_12`.
5. Kiểm giới hạn: kết luận chỉ trong V8/web profile; desktop/mobile VM heap và runtime reviewer vẫn NOT RUN.
