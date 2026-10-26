# Bàn Giao Sửa Cổng V2b (Ủy quyền ngoại lệ sau 2 vòng) — Private Dart Heap / In-Memory Retention & Cache BH-07

- **Ngày bàn giao:** 26/10/2026
- **Nhánh:** `feat/bh07-private-heap-verification`
- **Base review:** `30feeb981b36473711d5ed4120ba7e14082f95c7` (review [cb5bf41](review_cb5bf41.md))
- **Tested source SHA:** `16e5b5116738ab9d4417fe11b651aea794868401`
- **Người thực thi:** AI triển khai (DeepSeek), theo ủy quyền ngoại lệ trực tiếp của chủ dự án sau khi gói dừng ở vòng 2/2
- **Người review dự kiến:** Codex (Reviewer độc lập)
- **Trạng thái:** **Chờ review độc lập sau sửa HP3** (Người triển khai KHÔNG tự ghi Đạt)

Phạm vi vòng này **chỉ HP3-A/B/C**: `scripts/bh07_heap/run_heap_verification.py`, `tests/test_bh07_heap_controls.py`, tài liệu/bundle.
Không sửa `lib/`, backend, migration, contract, Provider heap suite. HP1/HP2/HP4/HP5/HP6/HP7 giữ nguyên.
App profile heap của V2b giữ **NOT RUN**.

---

## 1. Khắc Phục HP3-A/B/C (Review `cb5bf41`)

### HP3-A (P2) — Diagnostics/pub output trước JSON không còn hạ verdict xuống text parser

- File: `scripts/bh07_heap/run_heap_verification.py:174` (`_parse_json_events`), `:296` (`parse_test_results`).
- Trước: `output.lstrip().startswith('{')` quyết định chế độ; Flutter in `Resolving dependencies...`/`Got dependencies!` trước event JSON ở checkout mới nên rơi về text parser → `FAIL 0/7, identity_coverage NONE`, runner exit 1 dù raw stream có đủ 7 test success.
- Sau: quét **từng dòng** trên toàn stream, chỉ nhận object JSON có `type` thuộc protocol (`start/suite/allSuites/group/testStart/testDone/print/error/done`). Diagnostics/pub output bị bỏ qua khi tính verdict nhưng vẫn giữ nguyên trong `heap_test_run.log`. Cờ `saw_protocol` quyết định chế độ JSON, nên stream **thiếu** `testDone` vẫn là `NOT_RUN`, không rơi về text `All tests passed!`.
- Không đổi command của runner (không thêm `--no-pub`, không wrapper) để tránh che parser bug.

### HP3-B (P2) — Tôn trọng cờ `skipped` thật của Flutter

- File: `scripts/bh07_heap/run_heap_verification.py:186` (`testDone`), `:205` (normalize), `:169` (`_RESULT_MAP`).
- Trước: parser chỉ lấy `result`/`hidden`; protocol thật của Flutter phát `result: "success", skipped: true` cho test bị skip, nên test không chạy vẫn `PASS 7/7`.
- Sau: đọc `skipped` boolean và chuẩn hoá thành `'skipped'` trước khi map → `NOT_RUN`; `tests_skipped` tăng, `identity_coverage: INCOMPLETE`, suite `FAIL`, Markdown không claim 7/7. `success` + `skipped=false` vẫn là positive control.

### HP3-C (P2) — Map strict 7 expected identity; tên lạ/trùng không được tính coverage

- File: `scripts/bh07_heap/run_heap_verification.py:229` (`_verdict_from_results`), `:212` (`_suite_report`), `:437`–`:440` (report), `:382` (summary).
- Trước: chỉ kiểm tên expected còn thiếu; thêm 1 visible identity lạ cho ra `PASS, tests_passed 8, tests_expected 7, VERIFIED`, Markdown vẫn `7/7`.
- Sau: mỗi visible result phải khớp **đúng một** expected identity (exact hoặc hậu tố group); tên lạ vào `tests_unexpected`, khớp trùng vào `tests_duplicate`. Cả hai chặn `VERIFIED` (`UNVERIFIED` + `FAIL`). Counts chỉ tính trên 7 expected (không thể vượt 7), `tests_passed + tests_failed + tests_skipped + len(tests_missing) == tests_expected`. Markdown, `summary.json` và exit code dùng chung một verdict; report in thêm `Suite Verdict`, `Identity Coverage`, `Tests`, `Unexpected visible identities`, `Duplicate identities`.

## 2. Test Tái Hiện Trước Khi Sửa (RED → GREEN)

Thêm 8 control vào `tests/test_bh07_heap_controls.py` (lớp `ProtocolStreamControls`), dựng stream JSON đúng protocol Flutter (loader `hidden`, tên test có prefix group):

| Control | Trước sửa | Sau sửa |
|---|---|---|
| `test_diagnostics_prefix_before_json_does_not_downgrade_to_text` | FAIL (`FAIL` thay vì `PASS`) | PASS 7/7 `VERIFIED` |
| `test_malformed_lines_between_events_are_ignored` | — | PASS |
| `test_incomplete_protocol_is_not_pass` | — | không PASS |
| `test_real_protocol_skip_is_not_run_and_blocks_pass` | FAIL (PASS 7/7) | `FAIL`, skipped 1, M1 `NOT_RUN` |
| `test_real_protocol_success_without_skip_is_positive` | PASS | PASS (positive giữ nguyên) |
| `test_extra_unknown_identity_blocks_verified_and_counts` | FAIL (PASS 8/7) | `FAIL`, passed 7, `UNVERIFIED` |
| `test_duplicate_identity_blocks_verified` | FAIL (PASS) | `FAIL`, `tests_duplicate` có tên |
| `test_counts_always_reconcile_with_expected_identities` | FAIL (8 ≠ 7) | PASS |

Toàn bộ suite: **32/32 OK** (`python -m unittest tests.test_bh07_heap_controls -v`).

## 3. Lệnh Đã Chạy Và Kết Quả Thực Tế

Log thô: [`private_heap_r3_evidence/`](private_heap_r3_evidence/) (UTF-8 LF); bundle: [`private_heap_evidence/`](private_heap_evidence/).

| Lệnh | Kết quả |
|---|---|
| `python scripts/bh07_heap/run_heap_verification.py` | exit **0**; SHA `16e5b51`, `git_dirty: false`, provenance `CLEAN`; AST CLEAN; suite **PASS 7/7**, `identity_coverage: VERIFIED`, `tests_missing/unexpected/duplicate: []`; manifest 4/4 PASS |
| `python -m unittest tests.test_bh07_heap_controls -v` | exit **0**, **32/32 OK** |
| `python scripts/bh07_heap/audit_ast_memory.py --test-controls` | exit **0**, **12/12 PASS** |
| `python scripts/bh07_heap/clean_and_manifest.py --test-controls` | exit **0**, **5/5 PASS** |
| `python scripts/bh07_heap/clean_and_manifest.py --verify` | exit **0**, 4/4 strict UTF-8 LF, zero secret |
| `python docs/reviews/bh07/review_cb5bf41_evidence/protocol_probe.py` (nguyên file reviewer) | exit **0**, cả 3 ca HP3 đúng kỳ vọng (bảng dưới) |
| `python docs/reviews/bh07/review_ccad24c_evidence/probes.py` (nguyên file) | exit **0** |
| `python docs/reviews/bh07/review_33ad6e6_evidence/extra_controls.py` (nguyên file) | exit **0** |
| `flutter analyze --no-pub` | exit **0**, `No issues found!` |
| `flutter test --no-pub` | exit **0**, **247 PASS + 1 skip** |

Replay đúng probe của reviewer (`protocol_probe.py`, không sửa file):

| Ca | Trước sửa (review cb5bf41) | Sau sửa (`16e5b51`) |
|---|---|---|
| `real_full_runner_raw` (stream thật có diagnostics) | `FAIL`, 0 passed, 7 missing, `NONE` | **`PASS` 7/7, `VERIFIED`** |
| `same_run_json_only_positive` | `PASS` | **`PASS`** (giữ nguyên) |
| `one_real_protocol_skip` | `PASS` 7/7, skipped 0 | **`FAIL`**, passed 6, skipped 1, M1 `NOT_RUN`, `INCOMPLETE` |
| `unknown_extra_identity` | `PASS`, passed 8/7, `VERIFIED` | **`FAIL`**, passed 7, `UNVERIFIED`, `tests_unexpected: ["unrecognized extra test"]` |
| `skip_markdown_claims_7_of_7` | `true` | **`false`** |
| `unknown_extra_markdown_claims_7_of_7` | `true` | **`false`** |

Ghi chú trung thực về môi trường:

- Lần chạy full runner local có pub cache sẵn nên **không** in `Resolving dependencies...`; đường HP3-A được chứng minh bằng (a) replay đúng raw stream reviewer đã lưu và (b) 8 regression control mới, không phải bằng cách đổi command sang `--no-pub`.
- Reviewer Linux Flutter 3.47.7; tác giả Windows Flutter 3.47.6. Hai probe lịch sử của reviewer đọc file bằng `read_text()` mặc định cp1252 nên trên Windows cần `python -X utf8`; trên Linux không cần.
- `flutter test` log giữ nguyên bytes console Windows nên tên test tiếng Việt hiển thị thay ký tự; số đếm `+247 ~1`, `All tests passed!` và exit code không đổi.

## 4. Bundle Bằng Chứng

`docs/reviews/bh07/private_heap_evidence/` (4 file + manifest), regenerate từ tested source `16e5b51`:

```
5959fea0da97557d1e3cdedf1cb1817fce4537c967c961a04c3498b3969d1a13  ast_memory_audit.json
66de337b3e593ee3ce6b1742d937fdd40fa5000aed3f02ba6570cc645b6ce1dd  heap_test_run.log
8f18e2ee3813319dc74d4a1fefec3d7579d5001d178a88b7d674746e16c5a283  heap_verification_report.md
9e013b0673b774b03859173e927e9a91e2aa66f163540f493aa16c437135ceb8  summary.json
```

- `summary.json`: `tested_source_sha: 16e5b51...`, `git_dirty: false`, `git_dirty_paths: []`, `provenance: {git_cleanliness: CLEAN, errors: []}`, `heap_test_suite.verdict: PASS`, `tests_passed: 7`, `tests_skipped: 0`, `tests_unexpected: []`, `tests_duplicate: []`, `identity_coverage: VERIFIED`, `app_profile_heap_snapshot.status: NOT RUN`.
- `heap_test_run.log` là raw `flutter test --reporter json` events (nguồn verdict), không phải log compact.
- Lần chạy ghi nhận working tree sạch tại thời điểm capture (bundle đã commit được khôi phục trước khi chạy), sau đó bundle tái tạo và commit ở bước docs.

## 5. Giới Hạn & Trạng Thái

1. **App profile heap snapshot / Chrome DevTools Protocol / retained paths trên app thật: NOT RUN.** Provider harness chỉ là bằng chứng bổ trợ cấp Provider.
2. Audit AST vẫn là phân tích lexical (đã loại comment/string, cân bằng ngoặc), không phải Dart parser đầy đủ; chưa chứng minh retention path.
3. `WeakReference.target == null` chỉ nói harness không còn tham chiếu, không chứng minh mọi bản sao đã rời RAM.
4. Không chạy DB/HTTP/backup/deploy trong lượt này (không đổi backend).
5. V1/V5b giữ Đạt local; các cổng khác giữ NOT RUN; **toàn BH-07 chưa nghiệm thu**. Không merge `main`/`staging`/`production`, không deploy, không pilot, không chuyển BH-08.

Nếu review sau ủy quyền này còn phát hiện mở, gói dừng và báo chủ dự án; người triển khai không tự mở vòng tiếp theo.
