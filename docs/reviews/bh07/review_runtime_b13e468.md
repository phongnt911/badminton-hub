# Báo cáo QA độc lập — Runtime review V2b retained-path + finance coverage (b13e468)

- Ngày: 27/10/2026, Asia/Saigon.
- QA độc lập: Thực hiện độc lập trên máy đủ môi trường (ổ C trống ~80,3 GB, Docker + Supabase local cô lập), không tham gia viết hoặc sửa gói retained-path/oracle/auditor/publisher này.
- Base commit kiểm chứng: `b13e468d33e0d96437b58bb2da6088bff689b9eb` (code `29f44a8e8f86ff68e3ebe54f981cbb73ea5ceb2b`) trên nhánh `feat/bh07-retained-path-runtime-review`.
- Tested source runtime QA: `b13e468d33e0d96437b58bb2da6088bff689b9eb` (`git_dirty: false` tại thời điểm khởi động đo).
- Evidence QA riêng: [review_runtime_b13e468_evidence/](review_runtime_b13e468_evidence/). Không ghi đè bất kỳ bundle lịch sử nào; không xuất bản raw heap dump hoặc giá trị sentinel thô.
- Tài liệu tham chiếu: [AGENTS.md](../../../AGENTS.md), [docs/ai/REVIEWER.md](../../ai/REVIEWER.md), [review_c509aee.md](review_c509aee.md), [retained_path_handoff.md](retained_path_handoff.md), [bh07_readiness.md §4.4](bh07_readiness.md). Bàn giao Codex điều phối chốt theo quy trình.

## 1. Kết luận

**Đạt trong phạm vi phép đo runtime retained-path + finance sentinels độc lập 2 chu kỳ trên Web profile (V8/dart2js) + Chrome thật qua CDP trên commit `b13e468d33e0d96437b58bb2da6088bff689b9eb`.**

1. Đã tự dựng và xác minh stack Supabase local cô lập (`http://127.0.0.1:54321`, DB `supabase_db_badminton-hub`), build mới gói Flutter Web profile (`build_ms: 57043`, 39 artifacts, `reused: false`, `served_match: true`) và chạy thực tế 2 chu kỳ `Owner → logout → Cohost` và `Owner → logout → Member` trong cùng SPA document (`same_document: true`, `performance.timeOrigin` giữ nguyên trong từng chu kỳ).
2. Hai sentinel tài chính không render, phân biệt (`expense_id` sha12=`7b5ed5cb05a0` và `expense_id_2` sha12=`72412d54c227`, thuộc `scope: finance, rendered: false, distinctive: true`) **có mặt và reachable từ `gc_roots`** (path length 20 qua `_InheritedProviderScopeElement → _provider$_value → _finance → expenses → expenseId`) khi Owner đang xem màn hình tài chính (`owner_active`), và **biến mất hoàn toàn (`present: false, occurrences: 0, reachable: false, string_nodes: 0`)** ở cả `post_logout` lẫn `post_actor` (`post_cohost` và `post_member`) trong cả 2 chu kỳ.
3. Hai tiêu đề chi phí hiển thị dạng widget text (`expense` sha12=`41a394dd2dcd` và `expense2` sha12=`09ac31ed38b0`, `scope: finance, rendered: true, distinctive: true`) còn reachable qua `segmentationCache` sau khi thoát phiên Owner (path length 12, nhãn cạnh nhạy cảm đã được `<redacted>` trước khi cắt) và được công bố trung thực trong `residual_risks` với **`attribution: "unattributed"`** (không quy kết cho web engine hay ứng dụng).
4. Các roster ID (`player_a` sha12=`e3382947f391`, `player_b` sha12=`c5383f9762b9`, `scope: identity`) biến mất ở `post_logout` (cả 2 chu kỳ) và `post_member` (chu kỳ 2); ở `post_cohost` (chu kỳ 1) còn reachable (path length 18) và được ghi nhận trong `notes` với nhận định **`whether the new actor is entitled to fetch it is not established by this measurement`** (không tự khẳng định quyền truy cập). Sentinel `bank` (10 chữ số, `distinctive: false`, `exact: false` do khớp chuỗi con trong UUID của session) chỉ được báo cáo trong `notes`, không dùng làm coverage ngân hàng thật.
5. Fixture dùng một lần (`run_only_fixture_id_sha256_12: "72412d54c227"`) được tạo mới riêng cho lần chạy này (`run_only_fixture_created: true`), xóa sạch theo đúng ID sở hữu (`extra_expense_removed: true`, `extra_expense_verified_absent: true`), và đã được QA truy vấn độc lập bằng SQL trực tiếp trên `supabase_db_badminton-hub` (`extra_fixture_rows = 0`, chỉ còn đúng 1 dòng seed gốc `50000000-0000-4000-8000-000000000099`).
6. Toàn bộ 4 bundle lịch sử (`retained_path_r1_evidence/`, `retained_path_evidence/`, `app_profile_heap_evidence/`, `review_runtime_97d0e7e_evidence/`) giữ nguyên 100% byte/SHA-256 trước và sau khi chạy. Bundle QA mới (`review_runtime_b13e468_evidence/`) vượt qua cả `verify_evidence.py` (`exit=0`) và `clean_and_manifest.py --verify` (`exit=0`, 3/3 file hash khớp, 0 secret/JWT ngoài allowlist, strict UTF-8 LF).
7. Toàn bộ 312/312 test Python (`unittest discover`), 34/34 self-test oracle, 6/6 fixture controls, 8/8 build guard, các probe của reviewer (`json_structure_probe.js`, `redaction_probe.js`, `publication_probe.js`, `fixture_probe.js`, `probes.py`), `flutter analyze` (0 issues) và `flutter test` (247 PASS + 1 SKIP) đều PASS.
8. **Giữ nguyên giới hạn phạm vi:** Phép đo này chỉ gate trên **hai expense ID** không render trong V8/dart2js heap của bản build Web profile, kèm residual risk `unattributed` cho chuỗi đã render; **không** chứng minh toàn bộ object graph/model/cache/listener trong ứng dụng đã sạch và **không** đo Dart VM heap trên desktop/mobile (`NOT RUN`). Cổng V2b §4.4 đầy đủ và toàn BH-07 **chưa nghiệm thu**; không merge `main`/`staging`/`production`, không deploy/pilot/BH-08.

## 2. Phát hiện (P0 / P1 / P2)

| Mức | file:dòng | Kết quả | Hướng xử lý |
| --- | --- | --- | --- |
| P0 | — | Không có phát hiện mở trong phạm vi kiểm chứng runtime này | — |
| P1 | — | Không có phát hiện mở trong phạm vi kiểm chứng runtime này | — |
| P2 | — | Không có phát hiện mở trong phạm vi kiểm chứng runtime này | — |

Không sửa bất kỳ script, source app, backend hay hợp đồng DB nào để làm xanh kết quả.

## 3. Bằng chứng QA độc lập tự chạy

### 3.1. Replay test suites, self-tests, auditors và reviewer probes

| Lệnh / Kiểm tra | Exit code | Kết quả độc lập |
| --- | --- | --- |
| `node scripts/bh07_appheap/run_app_profile_heap.js --cycles 2` (`BH07_APPHEAP_EVIDENCE` trỏ `review_runtime_b13e468_evidence`) | 0 | `{"status":"RUN","verdict":"PASS","cycles":2}`; `run-only fixture 72412d54c227: created=true removed=true verified_absent=true` |
| `python -X utf8 scripts/bh07_appheap/verify_evidence.py --dir "$PWD\docs\reviews\bh07\review_runtime_b13e468_evidence"` | 0 | **PASS**: hoàn chỉnh, hash-consistent, khớp oracle, không có raw heap dump hay credentials |
| `python -X utf8 scripts/bh07_browser/clean_and_manifest.py --verify --evidence-dir "$PWD\docs\reviews\bh07\review_runtime_b13e468_evidence"` | 0 | **ALL CHECKS PASSED**: 3/3 files verified, 0 secret/JWT outside allowlist, strict UTF-8 LF |
| `python -X utf8 scripts/bh07_appheap/verify_evidence.py --dir "$PWD\docs\reviews\bh07\retained_path_r1_evidence"` | 0 | **PASS** trên bundle tác giả R1 (readonly) |
| `python -X utf8 scripts/bh07_appheap/verify_evidence.py --dir "$PWD\docs\reviews\bh07\retained_path_evidence"` | 1 | Từ chối đúng kỳ vọng (bundle cũ thiếu `attribution: unattributed`, note identity cũ và thiếu receipt cleanup) |
| `python -X utf8 scripts/bh07_appheap/verify_evidence.py --dir "$PWD\docs\reviews\bh07\app_profile_heap_evidence"` | 1 | Từ chối đúng kỳ vọng (bundle thế hệ cũ trước retained-path) |
| `python -X utf8 -m unittest discover -s tests` | 0 | **312/312 OK** (53,9 s) |
| `python -X utf8 scripts/bh07_appheap/heap_oracle.py self-test` | 0 | **34/34** controls passed |
| `node scripts/bh07_appheap/fixture_controls.js --self-test` | 0 | **6/6** controls passed (`collision_refused`, `create_then_clean`, `post_rejected_row_committed`, `post_rejected_row_absent`, `delete_rejected`, `remote_endpoint_refused`) |
| `node scripts/bh07_appheap/build_guard.js --self-test` | 0 | **8/8** controls passed |
| `node --check scripts/bh07_appheap/run_app_profile_heap.js` | 0 | Cú pháp hợp lệ |
| `node docs/reviews/bh07/review_04d1ea9_evidence/json_structure_probe.js` | 0 | Cả 3 ca (`ordinary_control`, `short_true_value`, `short_false_value`) đều `summary_json_valid: true`, `raw_placeholder_in_boolean: false` |
| `node docs/reviews/bh07/review_4184faf_evidence/redaction_probe.js` | 0 | `full_value_positive`, `prefix20_positive`, `prefix60`, `prefix40` đều `redacted_completely: true`, không sót mảnh |
| `node docs/reviews/bh07/review_4184faf_evidence/publication_probe.js` | 0 | `published_private_middle20: false`, `actual_private_fragment_absent: true` |
| `node docs/reviews/bh07/review_9fadecc_evidence/fixture_probe.js` | 0 | `post_calls: 0, delete_calls: 0, remaining: true, created: false, removed: false` |
| `python -X utf8 docs/reviews/bh07/review_9fadecc_evidence/probes.py` | 0 | `ninth_retained_node` (`reachable: true, string_nodes: 9`), `long_label` (`frame_has_redacted_marker: true`), `positive_real_record: PASS`, `finance_downgrade: FAIL`, `readonly: true` |
| `flutter analyze` | 0 | **No issues found!** (27,0 s) |
| `flutter test` | 0 | **247 passed + 1 skipped** |

### 3.2. Kết quả đo runtime 2 chu kỳ (`Owner → logout → Cohost` và `Owner → logout → Member`)

- Môi trường: Windows `win32 10.0.26100`, Node `v24.21.0`, Flutter `3.47.6 • channel stable`, Chrome `155.0.8059.85`, Supabase CLI `v2.121.0` (`http://127.0.0.1:54321`).
- Bản build: `mode=profile`, `reused=false`, `build_ms=57043`, `artifacts=39`, `served_match=true` (`main.dart.js` sha256=`c33fe27c7a4256174e9485a017f4bf84b082319b5f69eab117df255859e4762b`).
- Thời gian đo: bắt đầu `2026-10-27T16:43:48.504Z`, kết thúc `2026-10-27T16:48:00.726Z`.
- Cùng tài liệu SPA (`same_document: true`): Chu kỳ 1 giữ `time_origin = 1793119492141.4`; Chu kỳ 2 giữ `time_origin = 1793119591009.2`.

#### Bảng tổng hợp 8 heap snapshots (2 chu kỳ × 4 mốc)

| Chu kỳ | Actor path | Mốc | Snapshot bytes | sha256[:12] | Nodes / Edges / Strings | `expense_id` (gated finance) | `expense_id_2` (gated finance) | `expense` / `expense2` (rendered) | `player_a` / `player_b` (identity) | `bank` (non-distinctive) | `receiver` | `probe` (control) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Owner → logout → cohost | `baseline` | 58.322.442 | `3f29b7bf5338` | 528.511 / 2.252.884 / 164.075 | false (0) | false (0) | false (0) / false (0) | false (0) / false (0) | false (0) | false (0) | **true (1)** |
| 1 | Owner → logout → cohost | `owner_active` | 84.687.337 | `6ef00fd37e54` | 766.442 / 3.650.971 / 174.343 | **true (1, len=20, `a8be318199de`)** | **true (1, len=20, `a8be318199de`)** | true (1) / true (1) | true (1) / true (1) | true (1, `exact:false`) | false (0) | **true (1)** |
| 1 | Owner → logout → cohost | `post_logout` | 69.364.257 | `8dc258e2181a` | 640.687 / 2.862.284 / 170.322 | **false (0, unreachable)** | **false (0, unreachable)** | true (1, residual) / true (1, residual) | false (0) / false (0) | false (0) | false (0) | **true (1)** |
| 1 | Owner → logout → cohost | `post_actor` (`cohost`) | 81.102.465 | `de2de4ce9d95` | 735.859 / 3.493.603 / 173.263 | **false (0, unreachable)** | **false (0, unreachable)** | true (1, residual) / true (1, residual) | true (1, note) / true (1, note) | false (0) | false (0) | **true (1)** |
| 2 | Owner → logout → member | `baseline` | 58.492.664 | `77d832f8cf80` | 528.636 / 2.253.024 / 164.137 | false (0) | false (0) | false (0) / false (0) | false (0) / false (0) | false (0) | false (0) | **true (1)** |
| 2 | Owner → logout → member | `owner_active` | 84.725.049 | `8e5bf205c987` | 771.586 / 3.666.813 / 174.460 | **true (1, len=20, `66ec3dae6c33`)** | **true (1, len=20, `66ec3dae6c33`)** | true (1) / true (1) | true (1) / true (1) | true (1, `exact:false`) | false (0) | **true (1)** |
| 2 | Owner → logout → member | `post_logout` | 68.979.841 | `d3bc5347a6e5` | 631.165 / 2.839.946 / 170.378 | **false (0, unreachable)** | **false (0, unreachable)** | true (1, residual) / true (1, residual) | false (0) / false (0) | false (0) | false (0) | **true (1)** |
| 2 | Owner → logout → member | `post_actor` (`member`) | 73.186.935 | `cfb97f8315cc` | 667.983 / 3.067.583 / 171.146 | **false (0, unreachable)** | **false (0, unreachable)** | true (1, residual) / true (1, residual) | false (0) / false (0) | false (0) | false (0) | **true (1)** |

#### Kiểm tra chi tiết Retained Paths, Redaction & Residual Risks

- **Đường giữ của `expense_id` và `expense_id_2` ở `owner_active`:**
  - Chu kỳ 1 (`a8be318199de`) và Chu kỳ 2 (`66ec3dae6c33`): `root` → `GestureBinding__instance` → `WidgetsBinding__observers` → `_framework$_element` → `_inheritedElements` → `_persistent_hash_map$_root` → `keyValuePairs` → `___InheritedProviderScopeElement__delega` → `_provider$_value` → `_finance` → `expenses` → `property:expenseId -> string` (`path_len: 20`, `exact: true`, `string_nodes: 1`).
  - Ở `post_logout` và `post_actor` của cả 2 chu kỳ: `reachable: false`, `string_nodes: 0`, `occurrences: 0`.
- **Đường giữ của `expense` và `expense2` (rendered widget text) & Redaction:**
  - Chu kỳ 1 (`91dc804e80e6`) và Chu kỳ 2 (`5ae7d1eb096c`): `root` → `segmentationCache` → `_1` → `_itemMap` → `_strings` → `property:<redacted> -> object` → `property:hashMapCellKey -> string` (`path_len: 12`, `exact: true`).
  - Nhãn cạnh chứa nội dung chuỗi trong `_strings` đã được làm sạch thành `property:<redacted> -> object` trước khi cắt độ dài, không rò rỉ tiền tố hay mảnh chuỗi riêng tư.
  - Cả 8 bản ghi trong `residual_risks` (2 chu kỳ × 2 mốc sau logout × 2 sentinel `expense`/`expense2`) đều giữ đúng `"class": "rendered"` và `"attribution": "unattributed"`.

### 3.3. Kiểm tra Fixture Ownership, DB Cleanup và Disk Cleanup

1. **Receipt trong `summary.json` và `report.md`:**
   - `dump_dir_outside_repo: true`
   - `raw_snapshots_remaining: 0`
   - `dumps_dir_removed: true`
   - `chrome_profile_dir_removed: true`
   - `run_only_fixture_created: true`
   - `run_only_fixture_id_sha256_12: "72412d54c227"`
   - `extra_expense_removed: true`
   - `extra_expense_verified_absent: true`
   - `ok: true` (kiểu boolean nguyên vẹn).
2. **Truy vấn SQL độc lập trực tiếp vào `supabase_db_badminton-hub` sau khi runner kết thúc:**
   - `SELECT count(*) AS extra_fixture_rows FROM public.session_expenses WHERE title LIKE 'Tiền điện BH-07%';` → **`0`**.
   - `SELECT id, title, amount_vnd, status FROM public.session_expenses WHERE session_id = '10000000-0000-4000-8000-000000000099';` → chỉ còn duy nhất 1 dòng seed gốc (`50000000-0000-4000-8000-000000000099 | Tiền thuê sân 2h | 200000 | posted`).
3. **Kiểm tra đĩa sau khi chạy:**
   - Quét toàn bộ workspace và thư mục tạm (`%TEMP%`): `0` file `.heapsnapshot`, `.heapprofile`, `.heaptimeline` và `0` thư mục `bh07_appheap_*` còn sót.

### 3.4. Đối chiếu bảo toàn tính toàn vẹn các bundle lịch sử (Before / After SHA-256)

| Bundle / File | SHA-256 trước khi chạy | SHA-256 sau khi chạy | Trạng thái |
| --- | --- | --- | --- |
| `retained_path_r1_evidence/hashes.sha256` | `a952889e842351dd47b981955ab3c1cd8f6d7177b7311f5993c8a5b5aecbf7bf` | `a952889e842351dd47b981955ab3c1cd8f6d7177b7311f5993c8a5b5aecbf7bf` | Nguyên vẹn 100% |
| `retained_path_r1_evidence/report.md` | `34a37933af3437bdfed3889c9b0d11c9af34b297a43e1f0f17e9864fe3fa6032` | `34a37933af3437bdfed3889c9b0d11c9af34b297a43e1f0f17e9864fe3fa6032` | Nguyên vẹn 100% |
| `retained_path_r1_evidence/run.log` | `fc1f6ab3e1925ecd29f0293d9f7f0bfec018b65094f4d3d894e7dc22928d0c9a` | `fc1f6ab3e1925ecd29f0293d9f7f0bfec018b65094f4d3d894e7dc22928d0c9a` | Nguyên vẹn 100% |
| `retained_path_r1_evidence/summary.json` | `c5f10963ff833ab65b1e5ca52af41b87d3abddfaa518ffd1db918c594ce7948e` | `c5f10963ff833ab65b1e5ca52af41b87d3abddfaa518ffd1db918c594ce7948e` | Nguyên vẹn 100% |
| `retained_path_evidence/hashes.sha256` | `1e4ba6f88acd4245a0798d298d78a7eeff035cde9ac0c5927dd3bf331a8fe363` | `1e4ba6f88acd4245a0798d298d78a7eeff035cde9ac0c5927dd3bf331a8fe363` | Nguyên vẹn 100% |
| `retained_path_evidence/report.md` | `adff5afb95a2676725e1fbfcab6e2275ff1442146e61ea2cf9d880e91a382132` | `adff5afb95a2676725e1fbfcab6e2275ff1442146e61ea2cf9d880e91a382132` | Nguyên vẹn 100% |
| `retained_path_evidence/run.log` | `9c98f89adf74d593c3e2d233eabc2ee105d7eb03fedb82e36ebd15167cedf93f` | `9c98f89adf74d593c3e2d233eabc2ee105d7eb03fedb82e36ebd15167cedf93f` | Nguyên vẹn 100% |
| `retained_path_evidence/summary.json` | `e172240ac34b43b44c9b83cb1067fd0555acbd37ebd5847f148fa7da3a74f312` | `e172240ac34b43b44c9b83cb1067fd0555acbd37ebd5847f148fa7da3a74f312` | Nguyên vẹn 100% |
| `app_profile_heap_evidence/hashes.sha256` | `e1e1b8acbebdccd74fadcde0d248417a7da8c0afd1e302ef5988d460bf9077ad` | `e1e1b8acbebdccd74fadcde0d248417a7da8c0afd1e302ef5988d460bf9077ad` | Nguyên vẹn 100% |
| `app_profile_heap_evidence/report.md` | `d23b6ce1a16cd20fa88cf9c460154053256242d852d6102fdc80d3c3c38b2cb6` | `d23b6ce1a16cd20fa88cf9c460154053256242d852d6102fdc80d3c3c38b2cb6` | Nguyên vẹn 100% |
| `app_profile_heap_evidence/run.log` | `abd654eb894efb9064366e4d10427d220bd5f8f319e07e04a97536f338cf1ed6` | `abd654eb894efb9064366e4d10427d220bd5f8f319e07e04a97536f338cf1ed6` | Nguyên vẹn 100% |
| `app_profile_heap_evidence/summary.json` | `2a8ee7ae15b6dc24fcb5ae7ed2c65c52fb6c2990cfb7cd9e6a434bf3be6cbe3f` | `2a8ee7ae15b6dc24fcb5ae7ed2c65c52fb6c2990cfb7cd9e6a434bf3be6cbe3f` | Nguyên vẹn 100% |
| `review_runtime_97d0e7e_evidence/hashes.sha256` | `6c2325ba21625e411e6c29fc519f22d0b6d3ecaf81f57c5f56a4829046f70d1a` | `6c2325ba21625e411e6c29fc519f22d0b6d3ecaf81f57c5f56a4829046f70d1a` | Nguyên vẹn 100% |
| `review_runtime_97d0e7e_evidence/report.md` | `99340cc547a3481bfa60d95e70a8bfee33c2656149d94a0e608524b99382053a` | `99340cc547a3481bfa60d95e70a8bfee33c2656149d94a0e608524b99382053a` | Nguyên vẹn 100% |
| `review_runtime_97d0e7e_evidence/run.log` | `cc91a6fa59fb3dc141d23d984848cec81e00524c327da3137836c6aeca665a19` | `cc91a6fa59fb3dc141d23d984848cec81e00524c327da3137836c6aeca665a19` | Nguyên vẹn 100% |
| `review_runtime_97d0e7e_evidence/summary.json` | `6b8c916df4b247225bb1532205b0cf67848547f505db844137eeb16074871f90` | `6b8c916df4b247225bb1532205b0cf67848547f505db844137eeb16074871f90` | Nguyên vẹn 100% |
| `review_runtime_b13e468_evidence/hashes.sha256` | (tạo mới) | `458f51ec0d613f53112b83833aa43546369244a7901b4ac17bc4c857ae917764` | Khớp manifest |
| `review_runtime_b13e468_evidence/report.md` | (tạo mới) | `40c6a2418e0ffdb80f6d37c6d40ed14962a2c379c3627f133e4356a79dc0e4d9` | Khớp manifest |
| `review_runtime_b13e468_evidence/run.log` | (tạo mới) | `4576ede97ba9bdb81e3ef182fe4ccea6220b905e2aa8fa84d91e8551ddb37c06` | Khớp manifest |
| `review_runtime_b13e468_evidence/summary.json` | (tạo mới) | `1231dd93987aceec3d23324769533254cd1810d398fc6d832a875309d451ef4e` | Khớp manifest |

## 4. NOT RUN và giới hạn kỹ thuật trung thực

| Hạng mục | Trạng thái kỹ thuật | Điều kiện / Ranh giới |
| --- | --- | --- |
| Độ phủ sentinel tài chính và toàn bộ object graph V2b §4.4 | **GIỚI HẠN TRONG 2 EXPENSE ID** | Chỉ 2 giá trị tài chính không render, phân biệt (`expense_id` và `expense_id_2`) gate kết luận. Tiêu đề chi phí đã render (`expense`, `expense2`) còn trong heap sau logout và được báo cáo là residual risk `unattributed`. `bank` (10 chữ số) không distinctive (`exact: false` do khớp đuôi UUID); `receiver` không được luồng Owner tải; `player_a`/`player_b` không xác lập quyền truy cập bằng phép đo heap; mỗi giá trị chỉ xuất bản 1 đường ngắn nhất từ GC root. Không suy từ 2 expense ID thành toàn bộ model/cache/listener trong ứng dụng đã sạch. **Toàn cổng V2b §4.4 chưa đóng.** |
| Đo heap Dart VM trên desktop/mobile (VM-service) | **NOT RUN** | Gói này chỉ đo V8/dart2js heap của bản build Flutter Web profile trên Chrome 155; máy không cài Visual Studio / Android SDK nên Dart VM desktop/mobile giữ `NOT RUN`. |
| Trình duyệt khác (Safari/WebKit, Firefox), mobile web, nhiều tab/actor đồng thời, tải thật | **NOT RUN** | Chưa chạy trong phạm vi kiểm chứng local này. |
| V3/V4 Managed Supabase backup, PITR, retention, concurrent writers | **NOT RUN** | Cổng vận hành chưa chạy. |
| V5 Staging/production deploy và restore thật | **NOT RUN** | Cần môi trường và phê duyệt riêng. |
| V6 Banking / VietQR / webhook thật | **NOT RUN** | Ngoài phạm vi BH-07 hiện hành. |
| V7 Rehearsal tải thật/pilot và V8 Nghiệm thu toàn BH-07 | **NOT RUN** | Toàn BH-07 chưa nghiệm thu; không merge `main`/`staging`/`production`, không deploy/pilot/BH-08. |

## 5. Bàn giao

Báo cáo `docs/reviews/bh07/review_runtime_b13e468.md` và bộ bằng chứng `docs/reviews/bh07/review_runtime_b13e468_evidence/` được commit và push lên nhánh `feat/bh07-retained-path-runtime-review` (từ base `b13e468d33e0d96437b58bb2da6088bff689b9eb`), bàn giao Codex điều phối chốt theo quy trình.
