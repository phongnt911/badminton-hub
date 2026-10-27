# Bàn giao V2b §4.4 — Retained paths + finance coverage, vòng sửa 2/2 sau sửa RP3-B (Chờ review)

**Trạng thái: Chờ review độc lập vòng 2/2 sau sửa RP3-B.** Người triển khai **không** tự ghi Đạt.

- Nhánh: `feat/bh07-retained-path-verification`
- Base review: `bc09d0c9406f4934b40a00f940667c008bb7a3a8` ([review 4184faf](review_4184faf.md) + `review_4184faf_evidence/`)
- Tested source: `6b530c52e8020f778a1caa86890ea3ba87fb084f` — `git_dirty: false`
- Evidence: [`retained_path_r1_evidence/`](retained_path_r1_evidence/) — `summary.json`, `report.md`, `run.log`, `hashes.sha256` (giữ nguyên byte; không rewrite verdict lịch sử)
- Bundle cũ [`retained_path_evidence/`](retained_path_evidence/) và [`app_profile_heap_evidence/`](app_profile_heap_evidence/) **giữ nguyên byte**; auditor mới **từ chối** cả hai (contract đổi, không rewrite verdict lịch sử)
- Tiêu chí: [`bh07_readiness.md` §4.4](bh07_readiness.md)
- Kết quả máy: `status=RUN`, `verdict=PASS`, 2/2 chu kỳ PASS, `verify_evidence.py` PASS, cleanup (dump, profile Chrome, fixture dùng một lần) xác minh đủ ownership/removal/absence

## 1. Phạm vi

Chỉ **công cụ kiểm chứng + test + tài liệu/bằng chứng**. Không sửa `lib/`, app/backend/contract/migration, không merge `main`/`staging`/`production`, không deploy/pilot/BH-08.

| Thành phần | Đường dẫn | Control |
| --- | --- | --- |
| Oracle sentinel + retained paths (nguồn luật duy nhất) | `scripts/bh07_appheap/heap_oracle.py` | self-test **34/34**, `tests/test_bh07_app_heap_oracle.py` 48 |
| Retained path / class / strict verdict | `tests/test_bh07_app_heap_paths.py` | **69** (gồm phát lại nguyên bản `review_9fadecc_evidence/probes.py`) |
| Auditor bundle | `scripts/bh07_appheap/verify_evidence.py` | `tests/test_bh07_app_heap_evidence.py` **116** |
| Fixture ownership | `scripts/bh07_appheap/fixture_controls.js` | **6** case, `tests/test_bh07_app_heap_fixture_ownership.py` 5 (gồm phát lại `fixture_probe.js`) |
| Runner thật + Guard + Publication Redaction | `scripts/bh07_appheap/run_app_profile_heap.js`, `build_guard.js` | **12** tests (gồm `RedactionCompletenessControls`, `PublicationProbeReplay`, build guard, publication sanitizer) |

Tổng **310 test Python** (`python -X utf8 -m unittest discover -s tests`).

## 2. Bảy phát hiện review và cách sửa

| # | Mức | Sửa | Control tái hiện trước khi sửa |
| --- | --- | --- | --- |
| RP1 | P1 | Fixture dùng một lần lấy **UUID mới mỗi lần chạy**, có guard endpoint local, preflight từ chối khi id đã tồn tại (không POST/DELETE), đọc lại để nhận sở hữu sau POST không trả lời, chỉ DELETE dòng do chính lần chạy tạo, xác minh vắng mặt **theo id**; helper trả object thay vì ném lỗi để receipt cleanup luôn tồn tại | `fixture_controls.js` 6 case + `fixture_probe.js` phát lại: `post_calls=0, delete_calls=0, remaining=true, removed=false` (trước: `delete_calls=1, remaining=false, cleanup=true`) |
| RP2 | P2 | Reachability tính trên **mọi** string node khớp; chỉ **đường công bố** bị giới hạn (`MAX_CHAIN_WALKS=8`). Walk vượt budget hoặc gặp chu trình ⇒ record `error` (`retained_path_too_deep`/`retained_path_cycle`) và `path_problems` **FAIL** — không bao giờ là "unreachable" | `ReachabilityCoverageControls` 5 ca; probe `ninth_retained_node` nay `reachable=true, string_nodes=9` |
| RP3 | P2 | Nhãn cạnh kiểm trên **toàn bộ** giá trị đã decode (`needle in value or needle.startswith(label)`) **trước** khi cắt `EDGE_LABEL_MAX`; frame còn bị quét lại lần cuối; sanitizer công bố coi **tiền tố ≥20 ký tự** của giá trị riêng là riêng tư (`MIN_PREFIX_LEAK`) | `LabelPrivacyControls` 5 ca; probe `long_label` nay `frame_contains_private_prefix=false`, `truncated_private_label_sanitizer_findings=['label']` |
| RP3-B | P2 | Quét toàn bộ **maximal private runs** (≥20 ký tự hoặc toàn bộ giá trị nếu ngắn hơn) trên chuỗi gốc trước khi thay thế, **hợp nhất (merge) các khoảng chồng lấn** giữa mọi sentinel values; xử lý triệt để multiple/overlapping values, khoảng dịch chuyển, giá trị ngắn trong dài, chuỗi tự lặp; đệ quy làm sạch các trường chuỗi có cấu trúc của `summary` bằng `redactValue` trước khi serialize nhằm **bảo toàn tuyệt đối cú pháp JSON và Markdown** | `RedactionCompletenessControls` 6 ca (mọi độ dài cắt xén, embedded/overlapping, mid-length, multiple/overlapping values, self-overlapping, writeEvidence artifact thực tế kiểm tra cú pháp JSON/Markdown); phát lại nguyên bản `redaction_probe.js` và `publication_probe.js` |
| RP4 | P2 | Auditor đối chiếu `rendered`/`distinctive`/`scope` giữa metadata đã công bố và **từng** scan (hai chiều), và **parse bảng declaration trong `report.md`** so với `summary.json` | `ClassAgreementControls` 8 ca (metadata-only, một epoch, mọi epoch, rendered, distinctive, scan-only, report table) |
| RP5 | P2 | `residual_risks` có `class` + `attribution: 'unattributed'`; note identity nói "not established" cho cả `post_logout` (Guest) và `post_actor`; report/limitations bỏ mọi suy "engine chứ không phải app" và "actor được phép fetch" | `test_rendered_residual_risk_is_unattributed`, `test_identity_retention_after_logout_is_not_called_authorized`, probe `rendered_app_cache`/`identity_after_logout` |
| RP6 | P2 | Contract cleanup: `run_only_fixture_created`, `run_only_fixture_id_sha256_12`, `extra_expense_removed`, `extra_expense_verified_absent`, optional `extra_expense_error`; auditor đòi created/removed/absent đều `true`, sha12 hợp lệ, không error, và **receipt JSON trong `report.md` phải bằng `summary.cleanup`** | `FixtureCleanupControls` 11 ca (thiếu/false/null/không sở hữu/error/thiếu hash/ok=false/receipt lệch/thiếu receipt) |

Probe của reviewer (`review_4184faf_evidence/redaction_probe.js`, `publication_probe.js`, `review_9fadecc_evidence/fixture_probe.js`, `probes.py`) được phát lại **nguyên bản**; các kiểm tra đều đạt kỳ vọng.

## 3. Cổng mới (thu hẹp §4.4, có giới hạn)

1. **Đường giữ**: BFS từ synthetic root trên **cạnh mạnh** (bỏ `weak`), công bố `root_kind`, khung `edge:label -> type`, `path_len`, `path_sha256_12`. Kết luận reachable bao trùm mọi node khớp; chỉ đường in ra bị giới hạn, và "không phân tích xong" là FAIL.
2. **Phân lớp theo giá trị** (`SENTINEL_CLASSES`, ghi vào mọi scan, auditor đối chiếu): `rendered`, `distinctive`, `scope ∈ {finance, identity, control, bank}`.
3. **Chỉ `scope: finance` + không rendered + distinctive mới gate.** `MIN_GATED_SENTINELS = 2`, cả hai finance; thiếu ⇒ FAIL.
4. **Rendered text còn sau logout/đổi actor** ⇒ `## Residual risks`, **unattributed**, không gate.
5. **Identity (roster id CLB dùng chung)** ⇒ `## Notes`, không gate; lần đo này **không** kết luận actor được phép fetch.
6. **Không công bố giá trị sentinel**: oracle redact nhãn chứa/tiền tố sentinel; runner còn quét lại toàn bộ byte công bố (full value + tiền tố 20/40) và FAIL nếu còn khớp.

## 4. Kết quả lần đo công bố (source sạch `86181de`)

Chrome 155.0.8059.85, Flutter 3.47.6, build profile **39 artifact** (27 s), `served_match: true`; 2 chu kỳ `Owner → logout → Cohost` và `Owner → logout → Member`, mỗi chu kỳ 4 mốc trong **cùng document** (`performance.timeOrigin` không đổi).

| Mốc | `bank` (digits) | `expense_id`, `expense_id_2` (finance, không render) | `expense`, `expense2` (title render) | `player_a/b` (identity) | `probe` |
| --- | --- | --- | --- | --- | --- |
| baseline (khách) | không | không | không | không | có |
| owner_active | **có** (17 cạnh) | **có** (20 cạnh) | có (12 cạnh) | có (18 cạnh) | có |
| post_logout | không | **không** | **còn** → residual risk (unattributed) | không | có |
| post_actor Cohost | không | **không** | **còn** → residual risk | **có** → note "not established" | có |
| post_actor Member | không | **không** | **còn** → residual risk | không | có |

- Hai finance id **không còn reachable từ GC root** sau logout và sau khi actor khác đăng nhập, lặp lại 2 chu kỳ; đây là phần gate.
- Title chi phí vẫn reachable (`path_sha256_12 5ae7d1eb096c`, 12 cạnh) — **residual risk unattributed**, không phải kết luận về app hay engine.
- STK 10 chữ số không distinctive: hit khớp đuôi fixture UUID `...-000000000007` (`exact:false`) ⇒ chỉ note.
- `receiver` không được nạp trên bề mặt Owner ⇒ báo "không nạp", không tính coverage.
- Cycle 1 `post_actor` (Cohost) vẫn fetch lại roster ⇒ 2 note identity; cycle 2 (Member) không.

## 5. Lỗi công cụ tự bắt trong vòng này (đã sửa, có control)

Lần chạy đầu của vòng này **FAIL** đúng như thiết kế mới: `expense_id_2` vẫn present ở `post_logout`. Nguyên nhân: title fixture dùng một lần **chứa** chính id của nó, nên id xuất hiện như **substring** trong string node của title mà engine còn giữ — false positive do fixture, không phải app. Sửa: title độc lập với id (`Tiền điện BH-07 <8 hex>`), thêm control `the run title must not embed the gated id`. Đây là lần chạy bị **huỷ**, không công bố; lần đo công bố là lần chạy lại trên source `86181de`.

## 6. Fixture dùng một lần + cleanup (contract mới)

Runner POST **một** dòng `session_expenses` với UUID mới (`crypto.randomUUID`), title riêng, `created_by` mượn của expense seed; preflight từ chối nếu id đã tồn tại; chỉ DELETE dòng do lần chạy tạo; đọc lại theo id để xác minh vắng mặt. Receipt công bố trong `summary.cleanup` **và** trong `## Cleanup` của `report.md`:

```
run_only_fixture_created: true, run_only_fixture_id_sha256_12: f4c5b2af20ea,
extra_expense_removed: true, extra_expense_verified_absent: true, ok: true
```

Kiểm độc lập sau lượt đo: `select count(*) from public.session_expenses where title like 'Tiền điện BH-07%'` **= 0**. Dump heap + profile Chrome ghi ngoài repo, xoá và xác minh (`raw_snapshots_remaining: 0`).

## 7. Lệnh đã chạy (máy triển khai, tested source `6b530c5`)

| Lệnh | Exit | Ghi chú |
| --- | --- | --- |
| `node docs/reviews/bh07/review_4184faf_evidence/redaction_probe.js` | 0 | **4/4** check RP3-B: full value, prefix20, prefix40, prefix60 đều `redacted_completely=true`, không còn fragment |
| `node docs/reviews/bh07/review_4184faf_evidence/publication_probe.js` | 0 | `status=FAIL, verdict=FAIL`, `published_private_middle20=false`, `actual_private_fragment_absent=true` |
| `node docs/reviews/bh07/review_9fadecc_evidence/fixture_probe.js` | 0 | `post_calls=0, delete_calls=0, remaining=true` |
| `python -X utf8 docs/reviews/bh07/review_9fadecc_evidence/probes.py` | 0 | quan sát probes đúng kỳ vọng |
| `node scripts/bh07_appheap/fixture_controls.js --self-test` | 0 | **6/6** case ownership |
| `python -X utf8 scripts/bh07_appheap/heap_oracle.py self-test` | 0 | **34/34** |
| `python -X utf8 -m unittest discover -s tests` | 0 | **310/310 OK** |
| `python -X utf8 scripts/bh07_appheap/verify_evidence.py --dir <abs path r1>` | 0 | PASS (bắt buộc **đường dẫn tuyệt đối**) |
| Auditor trên 2 bundle cũ (`retained_path_evidence`, `app_profile_heap_evidence`) | 1 | mỗi bundle exit 1 đúng kỳ vọng |
| `flutter analyze` | 0 | no issues found (26.9s) |
| `flutter test` | 0 | 247 pass + 1 skip |

## 8. Giới hạn / NOT RUN

- **V8/dart2js của web profile**, không phải Dart VM: **desktop/mobile VM heap NOT RUN** (máy không có Visual Studio/Android SDK).
- **Runtime reviewer NOT RUN** — đây là lần chạy của người triển khai, không thay lần chạy độc lập.
- Sentinel chứng minh **một số** giá trị riêng của Owner không còn reachable; **không** liệt kê đủ mọi retained object/model/cache/listener; chỉ **một** đường mỗi giá trị được in. Cổng này **thu hẹp** §4.4, **không** đóng toàn bộ.
- Residual risk **không quy được** cho engine hay app: run này không chứng minh retainer.
- Fixture chỉ 1 session/2 player/2 expense; chưa có charge/payment, chưa tải thật/nhiều actor song song, chưa browser khác, chưa staging/production.

## 9. Trọng tâm cho reviewer

1. Chạy lại `probes.py` và `fixture_probe.js` của review 9fadecc **nguyên bản**; kỳ vọng mới: `reachable=true/string_nodes=9`, không còn tiền tố private, `risks[].attribution=unattributed`, không note "authorized", `post_calls=0/delete_calls=0/remaining=true`, sanitizer bắt `label`.
2. Tự chạy runner trên máy đủ đĩa (port 8088 trống, Supabase local up) và `verify_evidence.py --dir <abs>`; bundle mới PASS, **cả hai bundle cũ bị từ chối**.
3. Mutant: scope finance → identity ở metadata hoặc một epoch (FAIL), rendered/distinctive lệch (FAIL), bảng declaration trong report lệch (FAIL), thiếu/false `extra_expense_removed`/`extra_expense_verified_absent`/`run_only_fixture_created`, receipt cleanup trong report lệch (FAIL), finance id còn reachable sau logout (FAIL), walk vượt budget (FAIL, không phải unreachable).
4. Trung thực: `git_dirty: false` + `tested_source_sha` khớp commit; manifest khớp raw bytes; `run.log` không secret/JWT/password; DB local không còn dòng fixture.
5. Không đổi verdict/evidence cũ; không suy lần đo này thành nghiệm thu toàn BH-07.
