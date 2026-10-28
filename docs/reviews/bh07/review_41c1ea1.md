# Báo cáo Review Độc lập — Chốt AT1 vòng 3 (Retention Attribution & Coverage Map Tooling)

- Ngày: 28/10/2026, Asia/Saigon.
- Vai trò: **Reviewer độc lập**, chưa tham gia sửa trực tiếp AT1 vòng 3; tự chạy lại toàn bộ probe, control, auditor, test suite và kiểm tra manifest readonly trên worktree sạch, không dùng log tự kiểm của người triển khai thay cho lượt chạy độc lập.
- Nhánh: `feat/bh07-retention-attribution`.
- Base review: `a35c219d7c8f61742ad0753359681e72c9bf5a32` ([review_5226a3d.md](review_5226a3d.md)).
- Tested auditor source: `f11d20f6c5025f7f774c266298bc0309fcd0de0c` (`git_dirty: false`).
- Docs/handoff được kiểm: `41c1ea184835b0678504c6bc012c711871351d38` ([codex_retention_attribution_r3_handoff.md](codex_retention_attribution_r3_handoff.md)).
- Runtime QA tham chiếu: `b13e468d33e0d96437b58bb2da6088bff689b9eb` ([review_runtime_b13e468.md](review_runtime_b13e468.md), [review_3b393d3.md](review_3b393d3.md)) — không thực hiện phép đo browser/heap/SQL mới và không gán thành runtime mới.
- Evidence riêng của reviewer: [review_41c1ea1_evidence/](review_41c1ea1_evidence/). Giữ nguyên byte toàn bộ 10 bundle lịch sử.

---

## 1. Kết luận

**Đạt trong phạm vi gói công cụ điều tra phân định giữ dữ liệu & bản đồ độ phủ V2b (đóng AT1 P1 sau vòng 3 theo ủy quyền của chủ dự án; giữ nguyên kết luận đã đóng của AT2–AT6; không còn P0/P1/P2 mở trong phạm vi tooling).**

1. **Đóng AT1 P1:** Hàm `source_record_problems(data)` (`scripts/bh07_appheap/audit_retention_attribution.py:183–232`) kết hợp cùng `audit_summary_json` và `analyze_attribution` đã kiểm tra chặt chẽ toàn bộ bản ghi nguồn thay vì chỉ dựa trên ma trận 8 tổ hợp `residual_risks`:
   - Bắt buộc `cycles` có đúng 2 chu kỳ số nguyên thực sự (`type(n) is int`, loại trừ `bool`) là `1` và `2` với đúng `actor` theo hợp đồng (`{1: 'cohost', 2: 'member'}`).
   - Bắt buộc cả 4 mốc (`baseline`, `owner_active`, `post_logout`, `post_actor`) trong từng chu kỳ có `ok is True` và vượt qua validator cấu trúc `heap_oracle.scan_problems(scan, require_paths=True)`.
   - Đối chiếu chéo giữa `sentinels[name]` và `paths[name]` trên mọi mốc: nếu `path['reachable']` là `True` thì bắt buộc `record['present'] is True` và `string_nodes >= 1`; nếu `not record['present']` thì bắt buộc `not path['reachable']` và `string_nodes == 0`; đồng thời tính lại `sha256('\n'.join(frames))[:12]` để xác minh `path_len == len(frames) - 1` và `path_sha256_12 == digest`.
   - Bắt buộc 4 sentinel tài chính (`expense`, `expense2`, `expense_id`, `expense_id_2`) giữ đúng `scope == 'finance'`, `rendered == (name in ('expense', 'expense2'))` và `distinctive is True`.
   - Đối chiếu từng bản ghi trong `residual_risks` với đúng chu kỳ nguồn duy nhất và đúng `paths[sentinel]` của mốc tương ứng về `path_len`, `root_kind`, `path_sha256_12`, đồng thời bắt buộc `class == 'rendered'` và `attribution == 'unattributed'`.
2. **Giữ AT2–AT6 đã đóng:** Các trường máy (`app_model_retention: "SCOPED_TWO_IDS_CLEAN_APP_WIDE_UNKNOWN"`, `observed_peer_ids_absent: true`, `app_wide_retention_proven: false`, `secondary_app_paths_possible: true`, `residual_risk_official_classification: "unattributed"`), bảng đối chiếu DTO thực tế (11 thực thể, `auth_listeners` giữ `NOT_RUN_WEB_HEAP_OBJECT_GRAPH`), `run.log` được track, 88/88 link Markdown tương đối hợp lệ và không rò rỉ đường dẫn máy cá nhân hay sentinel thô đều giữ nguyên tính đúng đắn.
3. **Giữ nguyên ranh giới nghiệm thu:** Kết luận Đạt này chỉ đóng gói công cụ điều tra attribution và bản đồ độ phủ V2b. QA runtime local hai expense-ID `b13e468`, tooling RP3-C, Provider, V1, V5b giữ Đạt local; 8 rendered-title residual risks vẫn mang phân loại chính thức là **`unattributed`**; độ phủ ngoài 2 expense ID, Dart VM desktop/mobile và các cổng vận hành khác giữ **`NOT RUN`**; **toàn cổng V2b §4.4 và toàn BH-07 chưa nghiệm thu**; không merge `main`/`staging`/`production`, không deploy/pilot/BH-08.

---

## 2. Rà soát AT1–AT6 và Phát hiện (P0 / P1 / P2)

| Hạng mục | Trạng thái | Đối chiếu độc lập của Reviewer |
| --- | --- | --- |
| **AT1 (P1)** | **Đóng** | Đã chặn toàn bộ 10 mutant từ 3 bộ probe lịch sử (`probes.py`, `extra_controls.py`, `closure_controls.py`) và 12 mutant kiểm tra sâu của reviewer (`reviewer_at1_controls.json`), tất cả đều `exit=1`, `valid=false`, `status="FAIL"`, `primary_retainer_component="UNATTRIBUTED"`. Cả 3 ca positive đều `exit=0`, `valid=true`. |
| **AT2 (P2)** | **Giữ đóng** | Machine fields và báo cáo tách bạch rõ quan sát trong phạm vi 2 expense ID (`observed_peer_ids_absent: true`) với trạng thái toàn ứng dụng (`app_wide_retention_proven: false`, `app_wide_model_retention: "UNKNOWN"`), giữ `residual_risk_official_classification: "unattributed"`. |
| **AT3 (P2)** | **Giữ đóng** | Bản đồ độ phủ 11 thực thể khớp chính xác với trường thực tế trong `lib/models/finance.dart` và `lib/models/club.dart`; `auth_listeners` giữ `NOT_RUN_WEB_HEAP_OBJECT_GRAPH`. |
| **AT4 (P2)** | **Giữ đóng** | `retention_attribution_evidence/` giữ nguyên 5/5 payload + `hashes.sha256`, verify readonly `exit=0`. |
| **AT5 (P2)** | **Giữ đóng** | 88/88 link tương đối trong 4 tài liệu điều tra/bàn giao tồn tại trên đĩa; không có đường dẫn tuyệt đối máy cá nhân. |
| **AT6 (P2)** | **Giữ đóng** | Không có chuỗi sentinel thô hay tiền tố riêng tư trong báo cáo/bằng chứng; secret scan `0` phát hiện ngoài allowlist. |

### Bảng phát hiện mới (P0 / P1 / P2)

| Mức | file:dòng | Kết quả | Hướng xử lý |
| --- | --- | --- | --- |
| P0 | — | Không có phát hiện mở trong phạm vi review này | — |
| P1 | — | Không có phát hiện mở trong phạm vi review này | — |
| P2 | — | Không có phát hiện mở trong phạm vi review này | — |

---

## 3. Bằng chứng Reviewer Độc lập Tự Chạy

Toàn bộ kết quả và log dưới đây được chạy mới độc lập trên worktree sạch tại commit `41c1ea184835b0678504c6bc012c711871351d38` (source `f11d20f6c5025f7f774c266298bc0309fcd0de0c`), lưu tại [review_41c1ea1_evidence/](review_41c1ea1_evidence/).

### 3.1. Phát lại nguyên bản 3 bộ probe lịch sử (3 positive + 10 mutant)

| Bộ probe | Ca kiểm tra | Exit code CLI | `valid` | `status` | `primary_retainer_component` |
| --- | --- | --- | --- | --- | --- |
| `review_37b4954_evidence/probes.py` | `positive` | **0** | `true` | `SUPPORTED_HYPOTHESIS_WITH_LIMITS` | `Flutter Web Engine (dart._engine.segmentationCache)` |
| `review_37b4954_evidence/probes.py` | `peer_retained` | **1** | `false` | `FAIL` | `UNATTRIBUTED` |
| `review_37b4954_evidence/probes.py` | `wrong_environment` | **1** | `false` | `FAIL` | `UNATTRIBUTED` |
| `review_37b4954_evidence/probes.py` | `missing_rendered_paths` | **1** | `false` | `FAIL` | `UNATTRIBUTED` |
| `review_eda1ead_evidence/extra_controls.py` | `positive` | **0** | `true` | `SUPPORTED_HYPOTHESIS_WITH_LIMITS` | `Flutter Web Engine (dart._engine.segmentationCache)` |
| `review_eda1ead_evidence/extra_controls.py` | `expense2_path_missing` | **1** | `false` | `FAIL` | `UNATTRIBUTED` |
| `review_eda1ead_evidence/extra_controls.py` | `post_actor_paths_missing` | **1** | `false` | `FAIL` | `UNATTRIBUTED` |
| `review_eda1ead_evidence/extra_controls.py` | `duplicate_risk_record` | **1** | `false` | `FAIL` | `UNATTRIBUTED` |
| `review_eda1ead_evidence/extra_controls.py` | `missing_post_logout_occurrences` | **1** | `false` | `FAIL` | `UNATTRIBUTED` |
| `review_5226a3d_evidence/closure_controls.py` | `positive` | **0** | `true` | `SUPPORTED_HYPOTHESIS_WITH_LIMITS` | `Flutter Web Engine (dart._engine.segmentationCache)` |
| `review_5226a3d_evidence/closure_controls.py` | `duplicate_cycle_payload` | **1** | `false` | `FAIL` | `UNATTRIBUTED` |
| `review_5226a3d_evidence/closure_controls.py` | `rendered_presence_contradiction` | **1** | `false` | `FAIL` | `UNATTRIBUTED` |
| `review_5226a3d_evidence/closure_controls.py` | `risk_path_hash_mismatch` | **1** | `false` | `FAIL` | `UNATTRIBUTED` |

### 3.2. Bộ 12 control đột biến bổ sung của Reviewer (`reviewer_at1_controls.json`)

| Ca đột biến | Biến đổi đầu vào | Exit code CLI | Lý do từ chối (`failure_reasons`) |
| --- | --- | --- | --- |
| `swapped_actors` | Đổi chỗ `actor` chu kỳ 1 (`member`) và chu kỳ 2 (`cohost`) | **1** | `Cycle actor does not match the Owner-to-Cohost/Member contract` |
| `boolean_cycle_id` | Đặt `cycles[0].cycle = true` (kiểu `bool` thay vì `int`) | **1** | `Cycle payloads must contain unique integer cycles 1 and 2` |
| `unrendered_peer_present_unreachable` | `expense_id` ở `post_logout` có `present=true, occurrences=1` nhưng `reachable=false, string_nodes=0` | **1** | `Peer non-rendered sentinels were not cleanly released post-logout` |
| `absent_sentinel_nonzero_string_nodes` | `expense_id` ở `post_logout` có `present=false, occurrences=0, reachable=false` nhưng `string_nodes=2` | **1** | `post_logout: absent sentinel contradicts path node count` |
| `reachable_zero_string_nodes` | `expense` ở `post_logout` có `present=true, reachable=true` nhưng `string_nodes=0` | **1** | `post_logout: reachable path contradicts sentinel presence` |
| `path_len_frames_mismatch` | Sửa cả `path.path_len` và `risk.path_len` thành `11` trong khi `len(frames)-1 == 12` | **1** | `post_logout: path length/hash does not match frames` |
| `forged_both_path_and_risk_hash` | Sửa đồng thời cả `path.path_sha256_12` và `risk.path_sha256_12` thành `deadbeefcafe` mà không đổi `frames` | **1** | `post_logout: path length/hash does not match frames` |
| `risk_attribution_attributed` | Đặt `residual_risks[0].attribution = "engine"` | **1** | `Risk class/root/length/hash does not match its source path` |
| `risk_root_kind_mismatch` | Đặt `residual_risks[0].root_kind = "global_handles"` | **1** | `Risk class/root/length/hash does not match its source path` |
| `risk_class_mismatch` | Đặt `residual_risks[0].class = "identity"` | **1** | `Risk class/root/length/hash does not match its source path` |
| `finance_sentinel_rendered_flip` | Đặt `sentinels.expense_id.rendered = true` | **1** | `post_logout: finance sentinel class missing or inconsistent` |
| `scan_ok_false` | Đặt `cycles[1].epochs.post_actor.ok = false` | **1** | `post_actor: usable scan missing` |

### 3.3. Chạy Auditor với thư mục tạm riêng, Test Suites và Kiểm tra Toàn vẹn Bundle

| Lệnh / Kiểm tra | Exit code | Kết quả độc lập |
| --- | --- | --- |
| `python -X utf8 scripts/bh07_appheap/audit_retention_attribution.py --out-dir <temp_out_dir>` | **0** | `Attribution status: SUPPORTED_HYPOTHESIS_WITH_LIMITS (valid=True)`; `Coverage entities analyzed: 11` (1 clean web profile, 6 not measured in app heap, 1 not run web heap object graph); không ghi đè `retention_attribution_evidence/` |
| `python -X utf8 -m unittest discover -s tests` | **0** | **319/319 tests OK** (94,5 s) — lưu tại [unit.log](review_41c1ea1_evidence/unit.log) |
| `flutter analyze` | **0** | **No issues found!** (42,2 s) — lưu tại [analyze.log](review_41c1ea1_evidence/analyze.log) |
| `flutter test` | **0** | **247 passed + 1 skipped** — lưu tại [flutter_test.log](review_41c1ea1_evidence/flutter_test.log) |
| `clean_and_manifest.py --verify` trên 10 bundle lịch sử (`retention_attribution_codex_r3_evidence`, `review_5226a3d_evidence`, `retention_attribution_evidence`, `review_eda1ead_evidence`, `review_37b4954_evidence`, `review_runtime_b13e468_evidence`, `retained_path_r1_evidence`, `retained_path_evidence`, `app_profile_heap_evidence`, `review_runtime_97d0e7e_evidence`) | **0** (cả 10) | Tất cả 10 bundle đều `ALL CHECKS PASSED`, 0 secret/JWT ngoài allowlist, strict UTF-8 LF; SHA-256 trước/sau khớp 100% ([integrity.json](review_41c1ea1_evidence/integrity.json)) |
| `verify_evidence.py` trên `review_runtime_b13e468_evidence` và `retained_path_r1_evidence` | **0** | Cả 2 bundle hợp lệ PASS, readonly |
| `verify_evidence.py` trên 2 bundle thế hệ cũ (`retained_path_evidence`, `app_profile_heap_evidence`) | **1** | Bị từ chối đúng kỳ vọng, readonly |
| `clean_and_manifest.py --verify` trên bundle reviewer mới (`review_41c1ea1_evidence`) | **0** | **ALL CHECKS PASSED**: 14/14 files verified, 0 secret/JWT outside allowlist, strict UTF-8 LF |
| Kiểm tra provenance & diff `lib/`, `test/`, `supabase/` từ `b13e468..HEAD` | **0** | Rỗng (`""`); không có thay đổi nào ở ứng dụng, backend, migration hay test Dart ([provenance.json](review_41c1ea1_evidence/provenance.json)) |

---

## 4. NOT RUN & Giới hạn Kỹ thuật Bảo lưu

| Hạng mục | Trạng thái kỹ thuật | Ranh giới & Ràng buộc |
| --- | --- | --- |
| **Runtime browser / heap dump / SQL mới trong lượt review này** | **NOT RUN** | Gói này chỉ kiểm chứng công cụ phân định và bản đồ độ phủ trên dữ liệu đã làm sạch từ QA runtime tham chiếu `b13e468d33e0d96437b58bb2da6088bff689b9eb`. Không gán thành lần đo heap mới. |
| **Phân loại chính thức của 8 rendered-title residual risks (`expense`, `expense2`)** | **UNATTRIBUTED RESIDUAL RISK** | Đường BFS ngắn nhất đi qua `dart._engine.segmentationCache` và 2 peer ID (`expense_id`, `expense_id_2`) về 0 sau logout ủng hộ giả thuyết có giới hạn (`SUPPORTED_HYPOTHESIS_WITH_LIMITS`), nhưng một đường BFS đơn lẻ trên V8 không chứng minh tính vét cạn mọi đường tham chiếu phụ trong app; phân loại chính thức theo `bh07_readiness.md §4.4` vẫn là `unattributed`. |
| **Độ phủ V2b §4.4 ngoài 2 expense ID** | **NOT RUN** | 6 thực thể tài chính/ngân hàng (`session_charges`, `session_payments`, `club_bank_account`, `bank_receiver`, `payment_instructions`, `club_ledger`) chưa có sentinel đo thực tế trên app-profile heap (`NOT_MEASURED_IN_APP_HEAP`); `session_summary_totals` không distinctive; `roster_identities` chỉ ghi nhận note (`not established`); `auth_listeners` chưa đo đồ thị đối tượng trên Web heap (`NOT_RUN_WEB_HEAP_OBJECT_GRAPH`). |
| **Đo heap Dart VM trên desktop/mobile (VM-service)** | **NOT RUN** | Chưa chạy trên Dart VM desktop/mobile. |
| **Trình duyệt khác, mobile web, đa tab/actor đồng thời, tải thật** | **NOT RUN** | Chưa chạy trong phạm vi kiểm chứng local. |
| **V3/V4 Managed Supabase backup, PITR, offsite, encryption, retention, concurrent writers** | **NOT RUN** | Cổng vận hành chưa chạy. |
| **V5 Staging/production deploy và restore thật; V6 Banking/VietQR/webhook; V7 Pilot/rehearsal; V8 Nghiệm thu toàn BH-07** | **NOT RUN** | Toàn V2b §4.4 và toàn BH-07 **chưa nghiệm thu**; không merge `main`/`staging`/`production`, không deploy/pilot/BH-08. |
