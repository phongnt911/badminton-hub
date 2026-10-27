# Bàn giao V2b §4.4 — Retained paths + finance coverage trên web profile (Chờ review)

**Trạng thái: Chờ review độc lập.** Người triển khai **không** tự ghi Đạt.

- Nhánh: `feat/bh07-retained-path-verification`
- Base review: `56e86accf2943ab2c7a79ebb0d6373b0dbcf0ef1` ([chốt điều phối QA bank sentinel](review_2d16369.md))
- Tested source (lần đo công bố): `66bda0e7e3e1c2e983110e26a6300f6685c3a450` — `git_dirty: false` tại thời điểm bắt đầu đo
- Evidence: [`retained_path_evidence/`](retained_path_evidence/) — `summary.json`, `report.md`, `run.log`, `hashes.sha256`
- Tiêu chí: [`bh07_readiness.md` §4.4](bh07_readiness.md)
- Kết quả máy: `status=RUN`, `verdict=PASS`, 2/2 chu kỳ PASS, `verify_evidence.py` PASS, cleanup (dump, profile Chrome, fixture dùng một lần) đã xác minh
- Bundle bank-sentinel đã chốt [`app_profile_heap_evidence/`](app_profile_heap_evidence/) **giữ nguyên byte**, không sửa, không tái dùng làm bằng chứng cho cổng mới

## 1. Phạm vi

Chỉ **công cụ kiểm chứng + test + tài liệu/bằng chứng**. Không sửa `lib/`, app/backend/contract/migration, không merge `main`/`staging`/`production`, không deploy/pilot/BH-08. Fixture thêm cho lần đo là **một dòng `session_expenses` chỉ tồn tại trong lúc chạy** (xem §5).

| Thành phần | Đường dẫn | Control |
| --- | --- | --- |
| Oracle sentinel + retained paths (nguồn luật duy nhất) | `scripts/bh07_appheap/heap_oracle.py` | self-test **32/32**, `tests/test_bh07_app_heap_oracle.py` 48 |
| Test retained path / class / strict verdict | `tests/test_bh07_app_heap_paths.py` | **50** |
| Auditor bundle | `scripts/bh07_appheap/verify_evidence.py` | `tests/test_bh07_app_heap_evidence.py` **96** |
| Runner thật (build + Chrome CDP) | `scripts/bh07_appheap/run_app_profile_heap.js` | guard 4, phát lại probe 3, link 3 |

Tổng **258 test Python** (`python -X utf8 -m unittest discover -s tests`).

## 2. Cổng mới (đóng phần "retained paths toàn model/cache" một phần, có giới hạn)

1. **Đường giữ (retained path)**: oracle BFS từ synthetic root trên **cạnh mạnh** (bỏ `weak`), rồi in path của node string mang sentinel: `root_kind`, khung `edge:label -> type`, `path_len`, `path_sha256_12`. Count string-table một mình **không** còn đủ để nói "đã xoá".
2. **Phân lớp sentinel theo giá trị** (`SENTINEL_CLASSES`, ghi vào mọi scan): `rendered`, `distinctive`, `scope ∈ {finance, identity, control, bank}`.
3. **Chỉ `scope: finance` + không rendered + distinctive mới gate.** `MIN_GATED_SENTINELS = 2`, cả hai là finance; thiếu ⇒ FAIL.
4. **Rendered text còn sau logout/đổi actor** ⇒ bảng `## Residual risks`, **không** gate (retainer là LRU segmentation của Flutter **web engine**, không phải state app).
5. **Identity (roster id của CLB dùng chung)** ⇒ `## Notes`, không gate: Cohost **được phép** fetch lại danh sách đó (xem §4).
6. **Không công bố giá trị sentinel**: nhãn cạnh mà **chứa** sentinel bị in thành `<redacted>` ngay trong oracle; runner còn quét lại toàn bộ byte công bố và FAIL nếu còn khớp.

## 3. Kết quả lần đo công bố (source sạch `66bda0e`)

Chrome 155.0.8059.85, Flutter 3.47.6, Node v24.21.0, build profile **39 artifact**, `served_match: true`; 2 chu kỳ `Owner → logout → Cohost` và `Owner → logout → Member`, mỗi chu kỳ 4 mốc trong **cùng document** (`performance.timeOrigin` không đổi).

| Mốc | `bank` (digits) | `expense_id`, `expense_id_2` (finance, không render) | `expense`, `expense2` (title render) | `player_a/b` (identity) | `probe` |
| --- | --- | --- | --- | --- | --- |
| baseline (khách) | không | không | không | không | có |
| owner_active | **có** (17 cạnh) | **có** (20–21 cạnh) | có | có (18 cạnh) | có |
| post_logout | không | **không** | **còn** → residual risk | không | có |
| post_actor Cohost | không | **không** | **còn** → residual risk | **có** → note (fetch lại hợp lệ) | có |
| post_actor Member | không | **không** | **còn** → residual risk | không | có |

- Finance id của Owner **không còn reachable từ GC root** sau logout và sau khi actor khác đăng nhập, lặp lại 2 chu kỳ; đây là phần gate của cổng này.
- Title chi phí vẫn reachable qua `internal:properties → _1 → _itemMap → _strings → property:<redacted> → hashMapCellKey`, tức `segmentationCache` của web engine (path hash `5ae7d1eb096c`, 12 cạnh) — công bố là **residual risk**, không phải state app.
- STK ngân hàng dạng **10 chữ số** không distinctive: hit duy nhất khớp phần đuôi fixture UUID `10000000-0000-4000-8000-000000000007` (`exact: false`), nên chỉ ghi note. Kết luận bank-sentinel trước đây **đúng nhưng là may mắn về mặt bằng chứng** — nay không còn là cổng duy nhất.
- Tên chủ tài khoản (`receiver`) **không** được nạp trên bề mặt Owner (chỉ nhánh player của `session_finance_screen.dart` gọi `fetchPaymentInstructions`) ⇒ báo "không nạp", không tính là coverage.

## 4. Hai lỗi thật do lần chạy đầu tự bắt (đã sửa, có control)

| Hiện tượng | Nguyên nhân | Sửa |
| --- | --- | --- |
| Runner FAIL: `raw sentinel value reached the publication step (bank, expense)` | (a) nhãn cạnh của engine **chính là** text được cache (`property:<title>`) nên path frame công bố nguyên giá trị; (b) câu Limitations hard-code 10 chữ số STK | Oracle đổi nhãn chứa sentinel thành `<redacted>` (control: `test_property_label_carrying_a_sentinel_is_redacted`, self-test `labelled` case); bỏ literal trong report |
| FAIL: `player_a/player_b expected absent, got True` ở mốc Cohost | Cohost mở session detail nên **fetch lại roster** (`_PlayersList`, `provider.currentPlayers`) — dữ liệu actor mới **được phép** xem | Roster id chuyển sang `scope: identity`: vẫn công bố presence + path, chỉ **note**, không gate. Gate yêu cầu finance, và thêm một expense dùng một lần để có **2** finance id |

Đây là phát hiện của chính công cụ trên dữ liệu thật, không phải kết luận app leak.

## 5. Fixture dùng một lần + cleanup

Runner chèn `session_expenses` id `50000000-0000-4000-8000-000000000098` (title riêng, `created_by` mượn của expense seed) để có finance id thứ hai, rồi **xoá và đọc lại xác minh vắng mặt**; `summary.cleanup.extra_expense_removed: true`. Kiểm độc lập sau lượt đo: `select count(*) … = 0`. Dump heap + profile Chrome ghi ngoài repo, xoá và xác minh (`raw_snapshots_remaining: 0`).

## 6. Lệnh đã chạy (máy triển khai, cây sạch tại `66bda0e`)

| Lệnh | Exit | Ghi chú |
| --- | --- | --- |
| `node scripts/bh07_appheap/run_app_profile_heap.js` (env `BH07_APPHEAP_EVIDENCE`) | 0 | `status=RUN verdict=PASS cycles=2` |
| `python -X utf8 scripts/bh07_appheap/verify_evidence.py --dir <abs path>` | 0 | PASS (bắt buộc **đường dẫn tuyệt đối**, xem `review_2d16369.md`) |
| `python -X utf8 -m unittest discover -s tests` | 0 | **258/258 OK** |
| `python -X utf8 scripts/bh07_appheap/heap_oracle.py self-test` | 0 | **32/32** |
| `flutter analyze` | 0 | no issues |
| `flutter test` | 0 | 247 pass + 1 skip |

## 7. Giới hạn / NOT RUN

- **V8/dart2js của web profile**, không phải Dart VM: **desktop/mobile VM heap NOT RUN** (máy không có Visual Studio/Android SDK).
- **Runtime reviewer NOT RUN** — đây là lần chạy của người triển khai, không thay lần chạy độc lập.
- Sentinel chứng minh **một số** giá trị riêng của Owner không còn reachable; **không** liệt kê đủ mọi retained object/model/cache/listener. Cổng này **thu hẹp** khoảng trống §4.4, **không** đóng toàn bộ.
- Rendered text vẫn nằm trong LRU của web engine sau khi app bỏ — công bố là residual risk, **chưa** có biện pháp loại bỏ; không kết luận đây là rò rỉ app.
- Fixture chỉ có 1 session/2 player/2 expense; chưa có charge/payment, chưa tải thật/nhiều actor song song, chưa browser khác, chưa staging/production.

## 8. Trọng tâm cho reviewer

1. Tự chạy lại runner trên máy đủ đĩa (port 8088 trống, Supabase local up) và tự chạy `verify_evidence.py` với **đường dẫn tuyệt đối**; đối chiếu 2 bundle: bundle mới PASS, bundle `app_profile_heap_evidence/` cũ **phải bị auditor mới từ chối** (thiếu path/class).
2. Thử mutant: đổi `scope` một finance sentinel thành `identity` (gate phải đỏ vì thiếu finance); để finance id còn reachable sau logout (FAIL); nhãn cạnh chứa sentinel (phải ra `<redacted>`, không lộ giá trị); bỏ `paths` (strict phải FAIL).
3. Kiểm tính trung thực: `git_dirty: false` + `tested_source_sha` khớp commit đã công bố; manifest `hashes.sha256` khớp raw bytes; `run.log` không có secret/JWT/password; `cleanup.extra_expense_removed` đúng và DB local không còn dòng fixture.
4. Kiểm lại kết luận: chỉ trong V8/web profile; bank digits **không** phải bằng chứng mạnh; residual risk engine **không** bị tính là app sạch.
5. Không đổi verdict/evidence cũ; nếu cần mở gate khác (mobile VM heap, browser khác) thì ghi NOT RUN, không suy từ lần đo này.
