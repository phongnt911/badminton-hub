# Bàn giao V2b — App-profile heap / in-memory retention sau đổi actor (Chờ review, sửa AH9 theo ủy quyền bổ sung)

**Trạng thái: Chờ review độc lập sau sửa AH9 (ủy quyền bổ sung sau review 0f11bb4).** Người triển khai **không** tự ghi Đạt.

- Nhánh: `feat/bh07-app-profile-heap-verification`
- Base review: `a1263548cf06732475fe75577d141b0eedd75210` ([review 0f11bb4](review_0f11bb4.md))
- Tested source (runtime lần đo mới): `c04ce55` — `git_dirty: false` tại thời điểm bắt đầu đo
- Evidence: [`app_profile_heap_evidence/`](app_profile_heap_evidence/) — `summary.json`, `report.md`, `run.log`, `hashes.sha256`
- Bundle các lượt trước vẫn tra được ở Git: `a126354` (AH7/AH8), `268735c` (vòng 2), `8c02605` (vòng 1); evidence reviewer (`review_*_evidence/`) giữ nguyên, không sửa.
- Tiêu chí: [`bh07_readiness.md` §4.4](bh07_readiness.md)
- Kết quả máy: `status=RUN`, `verdict=PASS`, 2/2 chu kỳ PASS, cleanup dump + profile Chrome đã xác minh

## 1. Phạm vi

Chỉ sửa **công cụ kiểm chứng + test + tài liệu/bằng chứng**. Không sửa `lib/`, app/backend/contract, không đổi DB/migration, không merge `main`/`staging`/`production`, không deploy/pilot/BH-08.

| Thành phần | Đường dẫn | Control |
| --- | --- | --- |
| Oracle sentinel (validator dùng chung) | `scripts/bh07_appheap/heap_oracle.py` | 48 (self-test 15) |
| Auditor bundle | `scripts/bh07_appheap/verify_evidence.py` | 88 |
| Test oracle | `tests/test_bh07_app_heap_oracle.py` | 48 |
| Test auditor | `tests/test_bh07_app_heap_evidence.py` | 88 |
| Test guard + sanitizer | `tests/test_bh07_app_heap_build_guard.py` | 4 |
| Phát lại probe reviewer | `tests/test_bh07_app_heap_review_controls.py` | 3 |
| Audit link trạng thái | `tests/test_bh07_app_heap_links.py` | 3 |

Tổng: **146 test Python** (48 + 88 + 4 + 3 + 3).

## 2. Sửa theo review 0f11bb4 (AH9)

| Phát hiện | Cách sửa | Control tái hiện (đỏ trước sửa) |
| --- | --- | --- |
| **AH9 P2** — count/presence mâu thuẫn hoặc count sai kiểu vẫn được auditor chứng nhận "internally consistent" | Thêm **validator dùng chung** `heap_oracle.scan_problems(scan)` ở ranh giới oracle/auditor: scan `ok=true` bắt buộc mỗi sentinel có `type(occurrences) is int`, `occurrences >= 0`, `type(present) is bool` và **`present == (occurrences > 0)`**; scan `ok=false` không được khai presence (phải `null`). `decide()` gọi validator này **trước** khi so kỳ vọng (verdict FAIL + finding), auditor gọi lại cho **từng mốc** (finding có `cycle/epoch`), nên JSON/Markdown/exit dùng chung một quyết định. Không nới kỳ vọng: fixture test được cấp count đúng. | `ScanConsistencyControls` (12) + `CountConsistencyControls` (11): bank `present:false`/count `1`, probe `present:true`/count `0`, count `-1`, `0.5`, `"0"`, `true`, `null`, thiếu khóa, presence `"false"`/`1`/`null`, scan hỏng vẫn khai presence; CLI trên bundle mâu thuẫn phải exit 1 và in `contradicts` |

### Bằng chứng đỏ trước khi sửa

Chạy test mới trên công cụ vừa bàn giao AH7/AH8 (`0f11bb4`): **`Ran 136, FAILED (failures=17, errors=1)`** — 18 control đỏ (12 oracle, 6 auditor/CLI; riêng control "scan hỏng khai presence" đã đỏ từ trước nên vẫn xanh). Sau sửa: **146/146 OK**, `self-test` 15/15.

Ghi chú trung thực: control CLI ban đầu **xanh giả** vì bundle đặt ngoài repo làm CLI ném `ValueError` (exit 1 do crash, không do từ chối). Đã sửa control để tạo bundle trong repo và đòi cả exit ≠ 0 **và** chuỗi `contradicts` trong stdout.

## 3. Kết quả lần đo mới (source sạch `c04ce55`)

Chrome 155.0.8059.85, Flutter 3.47.6, Node v24.21.0, Windows 10.0.26100; build profile **32,7 s**, **39 artifact**, `served_match: true`, `git_dirty: false`; 2 chu kỳ `Owner → logout → Cohost/Member`, mỗi chu kỳ 4 mốc trong cùng document.

| Chu kỳ | Mốc | Snapshot bytes | sha256[:12] | present | `bank` | `probe` |
| --- | --- | --- | --- | --- | --- | --- |
| 1 Cohost | baseline | 58.398.477 | `dd2a0b263b6e` | probe | không | có |
| 1 Cohost | owner_active | 83.673.723 | `390c8fd38e7f` | bank, probe | **có** | có |
| 1 Cohost | post_logout | 69.671.279 | `ea2a588ece91` | probe | không | có |
| 1 Cohost | post_actor | 81.371.875 | `4373f0e19f8e` | probe | không | có |
| 2 Member | baseline | 58.441.227 | `24b658992e6b` | probe | không | có |
| 2 Member | owner_active | 83.667.461 | `da113521608d` | bank, probe | **có** | có |
| 2 Member | post_logout | 69.616.735 | `181616d5a46b` | probe | không | có |
| 2 Member | post_actor | 73.843.299 | `0cb9fa39eba2` | probe | không | có |

Occurrences đếm trên string table đã decode và **nhất quán** với presence ở cả 24 record: `bank` 1 ở `owner_active`/0 ở các mốc còn lại; `probe` 1 ở mọi mốc; `expense` 0. Sentinel công bố chỉ metadata, cả ba `available: true`.

Đọc kết luận: STK ngân hàng riêng của Owner **có thật** trong heap khi Owner đang xem và **không còn** sau logout lẫn sau khi Cohost/Member đăng nhập, lặp lại ở 2 chu kỳ — trong phạm vi **V8/web profile**.

## 4. Lệnh đã chạy (máy triển khai, cây sạch tại `c04ce55`)

| Lệnh | Exit | Ghi chú |
| --- | --- | --- |
| `python -X utf8 -m unittest tests.test_bh07_app_heap_oracle tests.test_bh07_app_heap_evidence tests.test_bh07_app_heap_build_guard tests.test_bh07_app_heap_review_controls tests.test_bh07_app_heap_links` | 0 | **146/146 OK** |
| `python -X utf8 scripts/bh07_appheap/heap_oracle.py self-test` | 0 | 15/15 control |
| `node scripts/bh07_appheap/build_guard.js --self-test` | 0 | 8/8 control |
| `node scripts/bh07_appheap/run_app_profile_heap.js --cycles 2` | 0 | `status=RUN verdict=PASS cycles=2`, build 32,7 s |
| `python -X utf8 scripts/bh07_appheap/verify_evidence.py` | 0 | PASS trên bundle mới |
| `python -X utf8 docs/reviews/bh07/review_0f11bb4_evidence/count_controls.py` | 0 | positive `[]`; 4 mutant count (contradiction hai hướng, âm, không nguyên) đều có finding + readonly; CLI `contradictory_count_cli` **exit 1** |
| `python -X utf8 docs/reviews/bh07/review_76334e2_evidence/closure_controls.py` | 0 | literal/escaped cùng presence; retained escaped ⇒ FAIL; thiếu length/hash có finding |
| `python -X utf8 docs/reviews/bh07/review_57ec02c_evidence/extra_controls.py` | 0 | positive PASS; grammar/summary/Markdown/symlink/raw-sentinel bị chặn; CLI `{}` exit 1 |
| `python -X utf8 docs/reviews/bh07/review_8914b2f_evidence/probes.py` | 0 | 8/8 ca có finding chặn |
| `node docs/reviews/bh07/review_8914b2f_evidence/build_probe.js` | 1 | từ chối `--reuse-build` |
| `python -X utf8 docs/reviews/bh07/review_57ec02c_evidence/link_audit.py` | 0 | `[]` |
| `flutter analyze --no-pub` | 0 | no issues |
| `flutter test --no-pub` | 0 | 247 pass + 1 skip |

## 5. Giới hạn / NOT RUN

- **Dart VM heap desktop/mobile: NOT RUN** — thiếu Visual Studio/Android SDK; kết luận chỉ trong phạm vi **V8/dart2js của web profile**.
- **Runtime reviewer: NOT RUN** — lần đo này là của người triển khai, không thay lần chạy reviewer.
- AH9 chỉ là **lỗi fail-open của validator trên dữ liệu scan**; bundle runtime hiện tại có 24 record nhất quán nên phát hiện này **không** chứng minh app leak và **không** phủ định các quan sát raw bytes đã công bố.
- Nhánh `available: false` của sentinel optional chỉ kiểm bằng **unit test**; fixture runtime luôn có `expense` title nên runtime ghi `available: true`.
- Sentinel chứng minh **một số giá trị riêng của Owner** không còn reachable; **không** liệt kê đủ retained object/model/cache/listener.
- Windows junction và link control tự `skip` trên host thiếu quyền tạo link.
- Chưa đo tải thật/nhiều actor song song, chưa mobile/browser khác, chưa staging/production.

## 6. Trọng tâm cho reviewer

1. Chạy lại `count_controls.py` nguyên bản: positive `[]`, 4 mutant count có finding, CLI **exit 1** kèm `contradicts`.
2. Thử mutant mới: `occurrences` là `1.0` (float) ở probe; `present` là `0`/`1`; scan `ok=false` nhưng vẫn khai `present:false`; count lớn nhưng presence đúng — gate phải là **quan hệ**, không chỉ kiểu.
3. Kiểm các gate đã đóng không hồi quy: `closure_controls.py`, `extra_controls.py`, `probes.py`, `build_probe.js`, `link_audit.py`.
4. Kiểm auditor không phụ thuộc secret và vẫn read-only (hash trước/sau).
5. Kiểm giới hạn: kết luận chỉ trong V8/web profile; desktop/mobile VM heap và runtime reviewer vẫn NOT RUN.
