# Bàn Giao Sửa Cổng V2b (Vòng 2/2) — Private Dart Heap / In-Memory Retention & Cache BH-07

- **Ngày bàn giao:** 26/10/2026
- **Nhánh:** `feat/bh07-private-heap-verification`
- **Base review thực tế:** `b74860c756b1d56c4f24e5bc0221678c67b57bd6` (review [33ad6e6](review_33ad6e6.md))
- **Base gốc của gói sửa vòng1:** `2dac374fd98389b3ec9c54ec11f5781b01d32c77` (review [ccad24c](review_ccad24c.md))
- **Tested source SHA:** `f7922ed63f7594ace19daa8b999712fd849f0dbe`
- **Người thực thi:** AI triển khai (DeepSeek)
- **Người review dự kiến:** Codex (Reviewer độc lập)
- **Trạng thái:** **Chờ review độc lập vòng 2/2** (Người triển khai KHÔNG tự ghi Đạt)

Phạm vi vòng này **chỉ tooling/docs**: `scripts/bh07_heap/*`, `tests/test_bh07_heap_controls.py`, tài liệu/bundle.
Không sửa `lib/`, backend, migration, contract. App profile heap của V2b giữ **NOT RUN**.

---

## 1. Khắc Phục HP2/HP3/HP6/HP7 (Review `33ad6e6`)

### HP2 (P2) — Comment/string không còn được tính là lời gọi dispose

- File: `scripts/bh07_heap/audit_ast_memory.py:22` (`strip_comments_and_strings`), `:79` (`extract_dispose_body`), `:223` (audit listener/subscription), `:108` (static/global).
- Cách sửa: thêm bộ lọc lexical một lượt, thay comment (`//`, `/* */` lồng nhau) và string literal (`'`, `"`, `'''`, `"""`, raw `r'...'`, escape) bằng khoảng trắng nhưng **giữ nguyên offset và newline**. Mọi regex và phép cân bằng ngoặc nhọn `dispose()` chỉ chạy trên code đã lọc.
- Hệ quả: `// _sub?.cancel();`, `print('_sub?.cancel()')`, `/* auth.removeListener(_onAuthChanged); */` bị coi là **chưa** dispose (`leak_risk: HIGH`); `}` trong string không còn cắt sớm thân hàm; dòng `static final leak = <Object>[]; // static const` không còn bị comment che (bắt được 1 issue), còn `static const List<Object>` thật vẫn bỏ qua.
- Controls: `--test-controls` mở rộng **5 → 12** (giữ nguyên 5 controls cũ, thêm `real_cancel_positive`, `comment_cancel_is_not_a_call`, `string_cancel_is_not_a_call`, `block_comment_remove_is_not_a_call`, `brace_in_string_keeps_dispose_body`, `static_mutable_with_const_comment`, `static_const_only`). Kết quả **12/12 PASS**.
- Không sửa Provider/app để làm xanh checker. Audit vẫn là heuristic lexical (không phải Dart AST/retention-path proof) — giới hạn giữ nguyên và ghi rõ trong report.

### HP3 (P2) — Verdict lấy từ test identity, không từ một marker chung

- File: `scripts/bh07_heap/run_heap_verification.py:142` (`EXPECTED_TESTS`: 7 test identity → 10 controls), `:172` (`_parse_json_events`), `:213` (`_verdict_from_results`), `:264` (`parse_test_results`), `:369` (`gate_ok`).
- Cách sửa: runner chạy `flutter test --reporter json` và đọc event `testStart`/`testDone`; mỗi control chỉ `PASS` khi test identity sở hữu nó `success`. Thiếu test → `NOT_RUN` + `tests_missing`; skip → `NOT_RUN`; fail/error → `FAIL`; không có test nào → `suite_verdict: NOT_RUN`. Không còn fallback `7` và không còn gán toàn `PASS` từ `All tests passed!`.
- Tên test do Flutter prefix bằng tên group nên khớp theo hậu tố (có test regression riêng).
- Markdown, `summary.json` và exit code dùng **cùng một verdict/count/coverage**: chỉ khi `suite_verdict == PASS`, AST `CLEAN` và không có lỗi provenance thì report mới ghi `7/7 Provider test PASS`; ngược lại ghi `FAIL / INCOMPLETE` kèm số thực tế.
- Output text (không có tên test) chỉ còn là fallback `identity_coverage: COUNT_ONLY`, `PASS` chỉ khi đếm đủ 7 và không skip.
- Bỏ claim `Finalizer` khỏi `methodology`/report (suite không đăng ký Finalizer), thêm giới hạn "WeakReference target null ≠ mọi bản sao đã rời RAM".
- Mục AST trong report lấy số file + từng provider từ `ast_memory_audit.json`, không hardcode `38`/`Leak risk NONE`.

### HP6 (P2) — Lỗi `git status`/`rev-parse` là UNKNOWN, chặn công bố thành công

- File: `scripts/bh07_heap/run_heap_verification.py:32` (`get_git_info`), `:67` (`provenance_errors`), `:369`, `main`.
- Cách sửa: `git status` lỗi → `git_dirty = 'UNKNOWN'` + path `ERROR: git status --porcelain failed: ...`; `rev-parse` lỗi → `UNKNOWN_SHA` + error; source hash `MISSING`/không phải 64-hex → error. `provenance_errors()` gom lỗi; `main` in lỗi ra stderr, ghi `summary.provenance.{git_cleanliness,errors}` và **trả exit 1**, report ghi `FAIL / INCOMPLETE ... Provenance: UNKNOWN`. Không còn `git_dirty=false` giả khi chưa đọc được status.
- Positive/negative controls: clean → `CLEAN` + không lỗi; dirty → `DIRTY` + danh sách path; status lỗi → `UNKNOWN`; rev-parse lỗi → `UNKNOWN_SHA`; hash thiếu → lỗi.

### HP7 (P2) — Đính chính base SHA và link commit

- File: `docs/reviews/bh07/private_heap_handoff.md:5` (base review), link commit ở mục HP4.
- Base review đúng theo Git: **`2dac374fd98389b3ec9c54ec11f5781b01d32c77`** (`git rev-parse 33ad6e6^`). SHA dài `2dac3743…` trong handoff/yêu cầu cũ **không tồn tại** (cùng 7 ký tự đầu nhưng khác commit); trace input sai được giữ nguyên trong [review 33ad6e6](review_33ad6e6.md) và lịch sử AGENTS, không xoá.
- Link commit chuyển sang URL tuyệt đối `https://github.com/phongnt911/badminton-hub/commit/...` (link tương đối `../../../commit/...` không phải file trong repo).
- Regression test kiểm **mọi SHA 40-hex trong handoff resolve được** bằng `git cat-file -e <sha>^{commit}` và không còn link commit tương đối.

### Regression tests mới

`tests/test_bh07_heap_controls.py` — **24 test** (`python -m unittest tests.test_bh07_heap_controls -v`, exit 0), tái hiện đúng các ca reviewer nêu trong `review_33ad6e6_evidence/extra_controls.py`:

- dispose: real cancel positive, line-comment, string literal, block comment, brace trong string, `addListener` bị comment, static mutable kèm comment `static const`, static const thật.
- summary: đủ 7 identity, subset, tên test lạ, không có test, skip, fail, output text legacy, prefix group, verdict PASS phải khớp `identity_coverage`/`tests_missing`, metadata không claim Finalizer.
- provenance: status lỗi, rev-parse lỗi, source hash thiếu, clean/dirty hợp lệ, UNKNOWN chặn kết luận thành công.
- handoff: mọi SHA resolve, link commit tuyệt đối.

---

## 2. Giữ Nguyên Phạm Vi Và Controls Đã Qua

- **HP1**: vẫn tách bạch Provider/VM harness (bằng chứng bổ trợ) với App Profile Heap **NOT RUN**; không suy diễn thành toàn app sạch.
- **HP4/HP5**: bundle vẫn 4 file, `heap_test_run.log` được track, manifest strict UTF-8 LF đọc theo raw bytes, từ chối BOM/CRLF/mismatch/missing/extra, verify read-only.
- 5 controls AST cũ và 5 controls verifier cũ giữ nguyên kỳ vọng, chỉ **thêm** control mới.
- Không sửa `test/integration/bh07_heap_verification_test.dart`, `lib/`, backend, migration, contract.

## 3. Lệnh Đã Chạy Và Kết Quả Thực Tế

Log thô: [`private_heap_r2_evidence/`](private_heap_r2_evidence/) (UTF-8 LF), bundle: [`private_heap_evidence/`](private_heap_evidence/).

| Lệnh | Kết quả |
|---|---|
| `python scripts/bh07_heap/run_heap_verification.py` (full runner) | exit **0**; AST CLEAN; suite **PASS 7/7**, `identity_coverage: VERIFIED`, `tests_missing: []`; manifest 4/4 PASS |
| `python -m unittest tests.test_bh07_heap_controls -v` | exit **0**, **24/24 OK** |
| `python scripts/bh07_heap/audit_ast_memory.py --test-controls` | exit **0**, **12/12 PASS** |
| `python scripts/bh07_heap/clean_and_manifest.py --test-controls` | exit **0**, **5/5 PASS** |
| `python scripts/bh07_heap/clean_and_manifest.py --verify` | exit **0**, `Verified 4 files ... zero secret leaks` |
| `python docs/reviews/bh07/review_ccad24c_evidence/probes.py` | exit **0**; `report_matches_author: true`; 5 case audit cũ giữ kỳ vọng |
| `python docs/reviews/bh07/review_33ad6e6_evidence/extra_controls.py` | exit **0**; xem bảng dưới — không còn false-green |
| `flutter analyze --no-pub` | exit **0**, `No issues found!` |
| `flutter test --no-pub` | exit **0**, **247 PASS + 1 skip** |

Kết quả probe reviewer sau khi sửa (`reviewer_extra_controls.log`):

| Ca của reviewer | Trước (33ad6e6) | Sau (f7922ed) |
|---|---|---|
| `comment_cancel` / `string_cancel` / `comment_remove` | `NONE` (false green) | **`HIGH`**, `un_cancelled_subscriptions: ["_sub"]`, `removes_auth_listener_on_dispose: false` |
| `real_cancel_positive` | `NONE` | **`NONE`** (giữ nguyên) |
| `mutable_static_with_comment` | 0 issue | **1 issue** |
| `summary_controls.subset_only` | 10/10 control PASS + Markdown 7/7 | **FAIL**, controls `NOT_RUN`, Markdown **không** claim 7/7 |
| `summary_controls.no_tests` | Markdown 7/7 | **`NOT_RUN`**, Markdown không claim 7/7 |
| `summary_controls.full_positive` | PASS | **PASS** (giữ nguyên, `COUNT_ONLY`) |
| `summary_controls.failed_test` | FAIL | **FAIL** (giữ nguyên) |
| `git_status_failure` | `git_dirty: false`, `dirty_paths: []` | **`git_dirty: "UNKNOWN"`** + `ERROR: git status --porcelain failed: ... exit status 128` |
| `base_provenance.actual_base` | `2dac374fd983...` | **`2dac374fd983...`** (docs nay trích đúng SHA này) |

Ghi chú môi trường (không phải kết quả reviewer):

- Windows console mặc định cp1252 nên hai probe lịch sử đọc file UTF-8 bằng `read_text()` cần `PYTHONUTF8=1`; trên Linux của reviewer không cần.
- Trong `probes.py` (file của reviewer, **không sửa**), `verify_controls.positive` trả exit 1 khi chạy trên Windows vì probe ghi `summary.json`/`hashes.sha256` bằng text mode nên sinh CRLF, và strict verifier **từ chối CRLF** đúng như thiết kế; trên Linux probe này trả exit 0. Bằng chứng positive hợp lệ với bundle LF: `clean_and_manifest.py --test-controls` **positive PASS** + `--verify` bundle thật **exit 0**.
- `flutter test` log giữ nguyên bytes console Windows nên tên test tiếng Việt hiển thị thay ký tự; số đếm `+247 ~1`, `All tests passed!` và exit code không đổi.

## 4. Bundle Bằng Chứng

`docs/reviews/bh07/private_heap_evidence/` (4 file + manifest), regenerate từ tested source `f7922ed`:

```
5959fea0da97557d1e3cdedf1cb1817fce4537c967c961a04c3498b3969d1a13  ast_memory_audit.json
5246cf9a342581aa8ac331d08266a3e6ef02692231abe2e9d09f4fdc54f0c774  heap_test_run.log
2ffd312b60585e5c42f8f03522c54e4a47fcd29824f3ae96c0458b3f236ab20e  heap_verification_report.md
5dffbc931bbe34a89ad6c9e24423d1fbbe084be93bb10eb5d72464e41c33c56e  summary.json
```

- `summary.json`: `tested_source_sha: f7922ed...`, `git_dirty: false`, `git_dirty_paths: []`, `provenance: {git_cleanliness: CLEAN, errors: []}`, `heap_test_suite.verdict: PASS`, `tests_passed: 7`, `identity_coverage: VERIFIED`, `app_profile_heap_snapshot.status: NOT RUN`.
- `heap_test_run.log` nay là **raw output của `flutter test --reporter json`** (event gốc dùng để tính verdict), không phải log compact.
- Lần chạy này ghi nhận working tree sạch tại thời điểm capture (bundle cũ đã commit được khôi phục trước khi chạy), sau đó bundle được tái tạo và commit ở bước docs — đúng thứ tự đã công bố, không chỉnh metadata.

## 5. Giới Hạn & Trạng Thái

1. **App profile heap snapshot / Chrome DevTools Protocol / retained paths trên app thật: NOT RUN.** Provider harness chỉ là bằng chứng bổ trợ cấp Provider.
2. Audit AST vẫn là phân tích lexical (comment/string đã loại, cân bằng ngoặc nhọn, không phải Dart parser đầy đủ); chưa chứng minh retention path.
3. `WeakReference.target == null` chỉ nói harness không còn tham chiếu, không chứng minh mọi bản sao đã rời RAM.
4. Không chạy DB/HTTP/backup/deploy trong lượt này (không đổi backend).
5. V1/V5b giữ Đạt local; các cổng khác giữ NOT RUN; **toàn BH-07 chưa nghiệm thu**. Không merge `main`/`staging`/`production`, không deploy, không pilot, không chuyển BH-08.

Nếu review vòng 2/2 còn phát hiện mở, gói dừng theo AGENTS để chủ dự án quyết định, không tự mở vòng 3.
