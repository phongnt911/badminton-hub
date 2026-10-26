# Bàn Giao Sửa HP3-C (Ủy quyền sửa ngoại lệ) — Private Dart Heap / In-Memory Retention & Cache BH-07

- **Ngày bàn giao:** 26/10/2026
- **Nhánh:** `feat/bh07-private-heap-verification`
- **Base review:** `01bfd160820eb7cda7198da4e0c1bb5d6810b795` (review [b7eb881](review_b7eb881.md))
- **Tested source SHA:** `996c4266e6a38324dfc7e3a4b19ee50be101087b`
- **Người thực thi:** AI triển khai (DeepSeek), theo ủy quyền sửa ngoại lệ trực tiếp của chủ dự án
- **Người review dự kiến:** Codex (Reviewer độc lập)
- **Trạng thái:** **Chờ review độc lập sau sửa HP3-C** (Người triển khai KHÔNG tự ghi Đạt)

Phạm vi vòng này **chỉ HP3-C**: `scripts/bh07_heap/run_heap_verification.py`, `tests/test_bh07_heap_controls.py`, tài liệu/bundle.
Không sửa `lib/`, backend, migration, contract, Provider heap suite. HP3-A/HP3-B và HP1/HP2/HP4/HP5/HP6/HP7 giữ nguyên.
App profile heap của V2b giữ **NOT RUN**.

---

## 1. Khắc Phục HP3-C (Review `b7eb881`)

**Phát hiện (P2):** `_parse_json_events()` ghi `results[name] = ...` nên hai `testID` khác nhau có **cùng full name** bị last-write-wins trước khi validator kiểm coverage. Stream đó là hợp lệ với Flutter thật (reviewer chứng minh hai `testStart` IDs 3/4 cùng full name, cả hai `success`, exit 0), nên duplicate vẫn cho `PASS 7/7 VERIFIED`, `tests_duplicate: []`, Markdown `7/7 Provider test PASS`, main-boundary exit 0.

**Cách sửa (đúng yêu cầu: giữ record theo testID trước khi kiểm duplicate):**

| Vị trí | Trước | Sau |
|---|---|---|
| `run_heap_verification.py:174` `_parse_json_events` | trả `{tên: result}`, mất multiplicity khi trùng tên | trả **list record** `{'id','name','result'}` cho từng `testID`; không có khóa nào theo tên |
| `run_heap_verification.py:230` `_verdict_from_results` | lặp trên dict theo tên | lặp trên **từng record**; expected identity đã `matched` lần hai ⇒ `tests_duplicate`, tên không khớp expected nào ⇒ `tests_unexpected` |
| Entry duplicate/unexpected | chỉ tên | `f'{name} [testID {id}]'` để exact-name duplicate nhìn thấy được ID gây trùng |
| `_suite_report` (không đổi) | counts trên `matched` | vẫn counts canonical trên 7 expected identity ⇒ `tests_passed` tối đa 7, không 8/7 |

Không dùng dedupe để che duplicate; không nới điều kiện gate; `duplicates` chặn `identity_coverage: VERIFIED` → `UNVERIFIED` + `FAIL`, và Markdown/`summary.json`/exit code dùng chung verdict đó.

## 2. Test Tái Hiện Trước Khi Sửa (RED → GREEN)

Thêm `test_exact_full_name_duplicate_ids_block_verified` (`tests/test_bh07_heap_controls.py:326`): 7 expected identity success + **một** `testStart/testDone` ID 998 với full name **giống chính xác** Baseline.

| Bước | Kết quả |
|---|---|
| Trước sửa | **FAIL** — `AssertionError: 'PASS' == 'PASS'` (`suite['verdict']` vẫn `PASS` dù có duplicate exact name) |
| Sau sửa | PASS — `FAIL`, coverage `UNVERIFIED`, `tests_duplicate` chứa `[testID 998]`, `tests_passed` vẫn 7, Markdown không claim 7/7, `summary.heap_test_suite.verdict != PASS` |

Toàn bộ suite: **33/33 OK** (`python -m unittest tests.test_bh07_heap_controls -v`).

Các control cũ giữ nguyên kỳ vọng: duplicate khác group vẫn `FAIL/UNVERIFIED`; unknown extra vẫn `FAIL`, passed 7; skipped thật vẫn `NOT_RUN`/`INCOMPLETE`; diagnostics trước JSON vẫn `PASS 7/7`; positive 7/7 vẫn `PASS`.

## 3. Lệnh Đã Chạy Và Kết Quả Thực Tế

Log thô: [`private_heap_r4_evidence/`](private_heap_r4_evidence/) (UTF-8 LF); bundle: [`private_heap_evidence/`](private_heap_evidence/).

| Lệnh | Kết quả |
|---|---|
| `python scripts/bh07_heap/run_heap_verification.py` | exit **0**; SHA `996c426`, `git_dirty: false`, `git_dirty_paths: []`, provenance `CLEAN`; AST CLEAN; suite **PASS 7/7**, `identity_coverage: VERIFIED`, `tests_missing/unexpected/duplicate: []`; manifest 4/4 PASS |
| `python -m unittest tests.test_bh07_heap_controls -v` | exit **0**, **33/33 OK** |
| `python scripts/bh07_heap/audit_ast_memory.py --test-controls` | exit **0**, **12/12 PASS** |
| `python scripts/bh07_heap/clean_and_manifest.py --test-controls` | exit **0**, **5/5 PASS** |
| `python scripts/bh07_heap/clean_and_manifest.py --verify` | exit **0**, 4/4 strict UTF-8 LF, zero secret |
| `python docs/reviews/bh07/review_b7eb881_evidence/duplicate_probe.py` (nguyên file reviewer) | exit **0**, 4 ca đúng kỳ vọng (bảng dưới) |
| `python docs/reviews/bh07/review_cb5bf41_evidence/protocol_probe.py` (nguyên file) | exit **0**, HP3-A/B giữ nguyên kỳ vọng |
| `python docs/reviews/bh07/review_ccad24c_evidence/probes.py` (nguyên file) | exit **0** |
| `python docs/reviews/bh07/review_33ad6e6_evidence/extra_controls.py` (nguyên file) | exit **0** |
| `flutter analyze --no-pub` | exit **0**, `No issues found!` |
| `flutter test --no-pub` | exit **0**, **247 PASS + 1 skip** |

Replay đúng probe reviewer (`duplicate_probe.py`, không sửa file):

| Ca | Trước sửa (`16e5b51`) | Sau sửa (`996c426`) |
|---|---|---|
| `positive_real_seven` | `PASS` 7/7 `VERIFIED` | **`PASS` 7/7 `VERIFIED`** (giữ nguyên) |
| `missing_expected_testDone` | `FAIL`, 6 passed, 1 missing, `INCOMPLETE` | **`FAIL`**, 6 passed, 1 missing, `INCOMPLETE` (giữ nguyên) |
| `different_group_duplicate` | `FAIL`, `UNVERIFIED`, markdown `false`, exit 1 | **`FAIL`**, `tests_duplicate` có `[testID 999]`, markdown `false`, exit 1 (giữ nguyên) |
| `exact_full_name_duplicate` | **`PASS` 7/7 `VERIFIED`**, `tests_duplicate: []`, markdown `true`, exit **0** | **`FAIL`**, `tests_passed 7`, `tests_duplicate: ["… Baseline Epoch: … [testID 999]"]`, `identity_coverage: UNVERIFIED`, markdown **`false`**, `main_boundary_control_exit` **1** |

Ghi chú trung thực về môi trường:

- Lần chạy full runner local có pub cache sẵn nên **không** in `Resolving dependencies...`; đường HP3-A vẫn được chứng minh bằng replay raw stream reviewer đã lưu (`protocol_probe.py`) và 8 control protocol, không phải bằng cách đổi command sang `--no-pub`.
- Reviewer Linux Flutter 3.47.7; tác giả Windows Flutter 3.47.6. Probe lịch sử của reviewer đọc file bằng `read_text()` mặc định cp1252 nên trên Windows cần `python -X utf8`; trên Linux không cần.
- `flutter test` log giữ nguyên bytes console Windows nên tên test tiếng Việt hiển thị thay ký tự; số đếm `+247 ~1`, `All tests passed!` và exit code không đổi.

## 4. Bundle Bằng Chứng

`docs/reviews/bh07/private_heap_evidence/` (4 file + manifest), regenerate từ tested source `996c426`:

```
5959fea0da97557d1e3cdedf1cb1817fce4537c967c961a04c3498b3969d1a13  ast_memory_audit.json
18d85315b88dd9b6dc1642d76b67c98709186e392fc6af81985893a579251930  heap_test_run.log
e2d3730b014c99438ac87d51bd1e81efc470ffeb8073f43d8e70c74f89b06797  heap_verification_report.md
d8e2c173c37bc55fde60a41c5ff7df96cf732377b52582fc2e7b2e5608f7af5f  summary.json
```

- `summary.json`: `tested_source_sha: 996c426…`, `git_dirty: false`, `git_dirty_paths: []`, `provenance: {git_cleanliness: CLEAN, errors: []}`, `heap_test_suite.verdict: PASS`, `tests_passed: 7`, `tests_skipped: 0`, `tests_unexpected: []`, `tests_duplicate: []`, `identity_coverage: VERIFIED`, `app_profile_heap_snapshot.status: NOT RUN`.
- `heap_test_run.log` là raw `flutter test --reporter json` events (nguồn verdict), không phải log compact.
- Lần chạy ghi nhận working tree sạch tại thời điểm capture (bundle đã commit được khôi phục trước khi chạy), sau đó bundle tái tạo và commit ở bước docs.

## 5. Giới Hạn & Trạng Thái

1. **App profile heap snapshot / Chrome DevTools Protocol / retained paths trên app thật: NOT RUN.** Provider harness chỉ là bằng chứng bổ trợ cấp Provider.
2. Audit AST vẫn là phân tích lexical (đã loại comment/string, cân bằng ngoặc), không phải Dart parser đầy đủ; chưa chứng minh retention path.
3. `WeakReference.target == null` chỉ nói harness không còn tham chiếu, không chứng minh mọi bản sao đã rời RAM.
4. Duplicate detection dựa trên khớp exact/hậu tố tên với 7 expected identity; nó chặn false-green, không thay thế việc Flutter phát tên test duy nhất.
5. Không chạy DB/HTTP/backup/deploy trong lượt này (không đổi backend).
6. V1/V5b giữ Đạt local; các cổng khác giữ NOT RUN; **toàn BH-07 chưa nghiệm thu**. Không merge `main`/`staging`/`production`, không deploy, không pilot, không chuyển BH-08.

Nếu review sau ủy quyền này còn phát hiện mở, gói dừng và báo chủ dự án; người triển khai không tự mở vòng tiếp theo.
