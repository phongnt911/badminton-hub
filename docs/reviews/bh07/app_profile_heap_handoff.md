# Bàn giao V2b — App-profile heap / in-memory retention sau đổi actor (Chờ review vòng 2/2)

**Trạng thái: Chờ review độc lập vòng 2/2 sau sửa AH1, AH2-A/B, AH3-A/B và AH6.** Người triển khai **không** tự ghi Đạt.

- Nhánh: `feat/bh07-app-profile-heap-verification`
- Base review: `8c02605bad98edd9c55f44f57fdfea18c2ecac68` ([review 57ec02c](review_57ec02c.md))
- Tested source (runtime lần đo mới): `130af7d` — `git_dirty: false` tại thời điểm bắt đầu đo
- Evidence: [`app_profile_heap_evidence/`](app_profile_heap_evidence/) — `summary.json`, `report.md`, `run.log`, `hashes.sha256`
- Bundle vòng 1 vẫn tra được ở lịch sử Git tại `8c02605` (`docs/reviews/bh07/app_profile_heap_evidence/`); không ghi đè bằng chứng của reviewer (`review_57ec02c_evidence/`).
- Tiêu chí: [`bh07_readiness.md` §4.4](bh07_readiness.md)
- Kết quả máy: `status=RUN`, `verdict=PASS`, 2/2 chu kỳ PASS, cleanup dump + profile Chrome đã xác minh

## 1. Phạm vi

Chỉ sửa **công cụ kiểm chứng + test + tài liệu/bằng chứng**. Không sửa `lib/`/app/backend/contract, không đổi DB, không migration, không merge `main`/`staging`/`production`, không deploy/pilot/BH-08.

| Thành phần | Đường dẫn | Control |
| --- | --- | --- |
| Runner đo | `scripts/bh07_appheap/run_app_profile_heap.js` | sanitizer publish + export |
| Guard build/serve | `scripts/bh07_appheap/build_guard.js` | 8 self-test |
| Oracle sentinel | `scripts/bh07_appheap/heap_oracle.py` | 30 (self-test 14) |
| Auditor bundle | `scripts/bh07_appheap/verify_evidence.py` | 64 |
| Test oracle | `tests/test_bh07_app_heap_oracle.py` | 30 |
| Test auditor | `tests/test_bh07_app_heap_evidence.py` | 64 |
| Test guard + sanitizer | `tests/test_bh07_app_heap_build_guard.py` | 4 |
| Phát lại probe reviewer | `tests/test_bh07_app_heap_review_controls.py` | 3 |
| Audit link trạng thái (mới) | `tests/test_bh07_app_heap_links.py` | 3 |

Tổng: **104 test Python** (30 + 64 + 4 + 3 + 3).

## 2. Sửa theo review 57ec02c

| Phát hiện | Cách sửa | Control tái hiện (đỏ trước sửa) |
| --- | --- | --- |
| **AH1 P1** — JSON hỏng vẫn PASS (`missing_string_comma`, `garbage_before_nodes`, `leading_zero_integer`) | Oracle bỏ hẳn lối "quét marker + regex": `validate()` **decode UTF-8 strict rồi `json.loads` toàn bộ tài liệu** với `object_pairs_hook` **từ chối khóa trùng**, sau đó mới kiểm cấu trúc V8 (khóa `snapshot` đầu tiên, chỉ các bảng V8 hợp lệ, thứ tự `nodes`→`edges`→`strings`, `strings` cuối, `snapshot` có đủ `meta`/`node_count`/`edge_count`, số phần tử khớp `node_count × len(node_fields)`/`edge_count × len(edge_fields)`, mọi phần tử bảng số là **int** thật, bảng chuỗi toàn `str`). Vượt `MAX_PARSE_BYTES` (512 MiB) ⇒ từ chối (`snapshot_too_large_to_parse`) thay vì hạ cấp sang quét marker. | `ReviewerGrammarControls`: `missing_string_comma`, `garbage_before_nodes`, `leading_zero_integer`, `trailing_comma`, `duplicate_top_level_key`; positive `escaped_string_literals_still_pass` |
| **AH2-A P2** — summary `{}`/`null`/`[]` bỏ qua mọi gate semantic | `verify()` không còn `if summary:`; kiểm **top-level type vô điều kiện**, `_check_summary_shape` đòi đủ trường và type của `environment`/`sentinels`/`cleanup`; `_check_cycles`, `_check_cleanup`, `_check_build`, `_check_report`, `_check_sentinels` đều **fail-closed có finding** khi dữ liệu lồng nhau sai kiểu (không crash, không skip). CLI trả exit 1 cho `{}`. | `SummaryShapeControls`: `empty_object`, `null`, `empty_list`, `scalar`, `missing_required_field`, `cycles_wrong_type`, `cycle_entry_not_object`, `epochs_not_object`, `scan_entry_not_object`, `empty_summary_cli_exits_nonzero` |
| **AH2-B P2** — Markdown ghi verdict trái JSON vẫn PASS | `_check_report` **parse** report: đúng **một** dòng `- Status: **…** (verdict …)`, dòng `Tested source` + `git dirty`, dòng `Build` (mode/reused/artifacts/served_match), **toàn bộ hàng bảng cycle** (7 cột: cycle, actor path, same document, epoch, size, sha[:12], present sentinels) so **đúng thứ tự và đúng nội dung** với summary, và mục `## Findings` khớp `summary.findings`. | `ReportControls`: verdict contradiction, status contradiction, duplicate status line, swapped epoch rows, duplicate row, actor label mismatch, present-sentinel mismatch, missing Findings, build line mismatch |
| **AH3-A P2** — symlink thư mục ngoài inventory | `_bundle_entries` lấy **mọi entry** (không lọc `is_file()` trước); `_is_link()` bắt cả symlink và **junction** Windows; mọi link bị từ chối trước khi đọc/hash; `_digests` (readonly snapshot) ghi cả `link`/`dir` nên link thêm vào cũng bị phát hiện. | `LinkControls`: file symlink, **directory symlink**, **broken symlink**, `link_is_part_of_the_readonly_snapshot` (đều chạy thật trên Windows Developer Mode; host không tạo được link ⇒ `skipTest` nêu rõ) |
| **AH3-B P2** — raw sentinel trong log đã hash vẫn "sanitized" | Hai lớp: (1) runner **sanitizer trước publication** — `findSentinelLeaks`/`redactSentinels` quét bản nháp `summary.json`/`run.log`/`report.md` bằng **giá trị sentinel sống**, nếu lọt thì redact, thêm finding và hạ `status/verdict = FAIL`; (2) auditor `_check_sentinels` **không cần secret**: với mỗi sentinel đã công bố `length` + `sha256_12`, quét **mọi cửa sổ cùng độ dài** trong **mọi file** đã xuất bản, khớp hash ⇒ finding "publishes the raw value of sentinel X". | `RawSentinelControls`: raw bank trong `run.log`, raw probe trong `report.md`, raw trong metadata lồng nhau, raw trong file thừa; positive `hash_only_metadata_passes`; JS control `PublicationSanitizerControls` |
| **AH6 P2** — 10 link trạng thái thêm thừa `docs/` | Sửa 5 tài liệu dưới `docs/` sang `reviews/bh07/...` (10 target) và thêm `tests/test_bh07_app_heap_links.py` audit link tương đối trên 9 tài liệu trạng thái/handoff để không tái diễn. | `StatusLinkControls`: 3 test; phát lại `review_57ec02c_evidence/link_audit.py` nay trả `[]` |

Giữ nguyên AH4 (byte UTF-8/LF/BOM, readonly) và AH5 (từ chối `--reuse-build`, guard 8/8, hash 39 artifact, served bytes) — chỉ chạy lại để chứng minh không hồi quy.

### Bằng chứng đỏ trước khi sửa

Chạy đúng các test mới trên **công cụ vòng 1** (stash `heap_oracle.py` + `verify_evidence.py`): **94 test, 20 failure + 4 error** — đúng các nhóm AH1 (3), AH2-A (7, gồm 4 error do auditor cũ crash khi dữ liệu lồng nhau sai kiểu), AH2-B (9), AH3-A (3), AH3-B (5). Sau sửa: **104/104 OK**.

## 3. Phương pháp đo (không đổi)

Build `flutter build web --profile` thật (dart-defines `APP_ENV=test` + Supabase local), serve tĩnh `127.0.0.1:8088`, Chrome headless thật qua CDP `HeapProfiler.takeHeapSnapshot`; mỗi chu kỳ một document (`performance.timeOrigin` trước/sau), 2 chu kỳ `Owner → logout → Cohost/Member`, mỗi chu kỳ 4 mốc. Sentinel STK ngân hàng Club A chỉ có trong payload riêng của Owner; `probe` gán lên `window` mỗi mốc để chứng minh detector sống.

Khác biệt kỹ thuật của vòng này: oracle parse toàn bộ JSON (đo thực tế **2,25 s cho dump 61,7 MB**, tức ~3 s cho dump runtime ~85 MB; 8 dump của lần chạy này đều `ok=true`).

## 4. Kết quả lần đo mới (source sạch `130af7d`)

Flutter 3.47.6 (stable), Chrome 155.0.8059.85, Node v24.21.0, Windows 10.0.26100; build profile **61,3 s**, **39 artifact** đã hash, `served_match: true`, `git_dirty: false`.

| Chu kỳ | Mốc | Snapshot bytes | sha256[:12] | `bank` | `probe` |
| --- | --- | --- | --- | --- | --- |
| 1 Cohost | baseline | 58.357.152 | `23a453ada885` | không | có |
| 1 Cohost | owner_active | 84.919.680 | `5cd7c1851c11` | **có** | có |
| 1 Cohost | post_logout | 68.961.793 | `60cd377c1904` | không | có |
| 1 Cohost | post_actor | 81.734.053 | `210c30ad5aeb` | không | có |
| 2 Member | baseline | 58.512.742 | `5d1d6294517f` | không | có |
| 2 Member | owner_active | 84.204.480 | `da2833705279` | **có** | có |
| 2 Member | post_logout | 68.819.082 | `2d45678f9529` | không | có |
| 2 Member | post_actor | 73.199.374 | `2b570260287a` | không | có |

Đọc kết quả: cùng kết luận với lần đo trước — STK ngân hàng riêng của Owner **có thật** trong heap khi Owner đang xem (detector hoạt động) và **không còn** sau logout lẫn sau khi Cohost/Member đăng nhập trong cùng instance; 2 chu kỳ lặp lại. `expense` vẫn không được nạp ở màn hình đã mở nên **không** dùng để kết luận.

## 5. Dọn dẹp, sanitize, readonly

- Heap dump + profile Chrome ghi **ngoài repo** (`%TEMP%`), quét một lần rồi xoá; `summary.json`: `dumps_dir_removed: true`, `raw_snapshots_remaining: 0`, `chrome_profile_dir_removed: true`, `ok: true`.
- Bundle chỉ có 4 file (3 entry manifest, `hashes.sha256` không tự hash): chỉ độ dài + `sha256[:12]` của sentinel, không giá trị thô, không `.heapsnapshot`.
- Auditor read-only: hash **mọi entry** (file/dir/link) trước và sau, phải giống nhau.

## 6. Lệnh đã chạy (máy triển khai, cây sạch tại `130af7d`)

| Lệnh | Exit | Ghi chú |
| --- | --- | --- |
| `python -X utf8 -m unittest tests.test_bh07_app_heap_oracle tests.test_bh07_app_heap_evidence tests.test_bh07_app_heap_build_guard tests.test_bh07_app_heap_review_controls tests.test_bh07_app_heap_links` | 0 | **104/104 OK** |
| `python -X utf8 scripts/bh07_appheap/heap_oracle.py self-test` | 0 | 14/14 control |
| `node scripts/bh07_appheap/build_guard.js --self-test` | 0 | 8/8 control |
| `node scripts/bh07_appheap/run_app_profile_heap.js --cycles 2` | 0 | `status=RUN verdict=PASS cycles=2`, build profile 61,3 s |
| `python -X utf8 scripts/bh07_appheap/verify_evidence.py` | 0 | PASS trên bundle mới |
| `python -X utf8 docs/reviews/bh07/review_8914b2f_evidence/probes.py` | 0 | 8/8 ca có finding chặn (script chỉ in JSON) |
| `python -X utf8 docs/reviews/bh07/review_57ec02c_evidence/extra_controls.py` | 0 | positive PASS; 3 ca grammar `ok:false`+`present:null`+FAIL; summary rỗng/null/list bị chặn; Markdown trái verdict bị chặn; symlink thư mục bị chặn; raw sentinel trong log bị chặn; `empty_summary_cli` exit 1 |
| `node docs/reviews/bh07/review_8914b2f_evidence/build_probe.js` | 1 | từ chối `--reuse-build` |
| `python -X utf8 docs/reviews/bh07/review_57ec02c_evidence/link_audit.py` | 0 | `[]` — không còn link chết |
| `flutter analyze --no-pub` | 0 | no issues |
| `flutter test --no-pub` | 0 | 247 pass + 1 skip |

## 7. Giới hạn / NOT RUN

- **Dart VM heap desktop/mobile: NOT RUN** — máy không có Visual Studio/Android SDK; kết luận chỉ trong phạm vi **V8/dart2js của bản web profile**.
- Sentinel chứng minh **một số giá trị riêng của Owner** không còn reachable; **không** liệt kê đủ mọi retained object/model, không đo retention path chi tiết.
- Kiểm "artifact do lần chạy này sinh ra" dựa trên mtime/hash; bằng chứng trực tiếp là byte server trả trùng hash artifact (`served_match`).
- Link control chạy thật trên Windows có quyền tạo symlink (Developer Mode); trên host không tạo được link, control tự `skip` kèm lý do — khi đó phải ghi **NOT RUN** thay vì coi là PASS.
- Runtime **reviewer** vẫn phải tự chạy; lần đo này là của người triển khai, không thay lần chạy reviewer.
- Chưa đo tải thật/nhiều actor song song, chưa mobile/browser khác, chưa staging/production.

## 8. Trọng tâm cho reviewer

1. Chạy lại `verify_evidence.py` và `extra_controls.py` nguyên bản; positive phải PASS, mọi ca hỏng/rò rỉ/mâu thuẫn phải FAIL.
2. Thử mutant mới: snapshot hợp lệ nhưng `strings` không ở cuối; `summary.json` là object thiếu trường; report đúng verdict nhưng **đổi hàng** cycle/epoch; raw sentinel nằm trong file thứ 5 đã thêm manifest.
3. Kiểm AH1 là **grammar gate**, không phải marker gate: dump cắt giữa bảng, `00`, thiếu dấu phẩy, khóa trùng, nội dung lạ trước `nodes` ⇒ `ok:false`, `present:null`.
4. Kiểm AH3-B không phụ thuộc secret: auditor chỉ dùng `length` + `sha256_12`; canary giả trong probe reviewer phải bị bắt.
5. Kiểm giới hạn: kết luận chỉ trong V8/web profile; desktop/mobile VM heap vẫn NOT RUN.
