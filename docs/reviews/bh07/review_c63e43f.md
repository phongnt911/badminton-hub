# Review chốt HP3-C — c63e43f

## Kết luận

**Đạt trong phạm vi gói Provider/tooling và bản sửa HP3-C. Đóng P2 exact-full-name duplicate; không còn P0/P1/P2 mở được xác định trong phạm vi review này.** Giữ HP3-A/B vàHP1/HP2/HP4/HP5/HP6/HP7 theo phạm vi đã đóng. **Không phải Đạt toàn cổng app-profile heap V2b**: phần đó vẫn **NOT RUN**, toàn BH-07 chưa nghiệm thu.

- Ngày:26/10/2026 (Asia/Saigon).
- Base review:`01bfd160820eb7cda7198da4e0c1bb5d6810b795` ([review b7eb881](review_b7eb881.md)).
- Tested source:`996c4266e6a38324dfc7e3a4b19ee50be101087b`.
- Docs/evidence:`c63e43f113e95d8cf56ff79504802e249f38d4a7` (đúng origin khi fetch).
- Reviewer không viết/sửa bản source này. Checkout docs sạch trước kiểm; full runner chạy ở worktree reviewer riêng source996c426 sạch trước capture. Source/app/backend/Provider heap suite và bundle bàn giao không bị chỉnh sửa trong lượt review.

## Xác nhận HP3-C

| Điều kiện | Kết quả reviewer mới |
|---|---|
| Exact full name,2 testIDs khác nhau | **FAIL/UNVERIFIED**, tests_duplicate ghi rõ `[testID 999]`; canonical tests_passed7≤7; Markdown không claim7/7; main-boundary control exit1. |
| Không gộp trước validator | Trace `_parse_json_events` giữ **8 record/8 distinct IDs**, gồm2 records cùng full name. `_verdict_from_results` thấy record thứ hai rồi báo duplicate; không có dict khóa theo name trước bước kiểm này. |
| Positive7 expected | **PASS7/7,VERIFIED**, không duplicate; full runner thật exit0. |
| Duplicate khác group | **FAIL/UNVERIFIED**, báo testID; Markdown negative, main-boundary exit1. |
| Unknown extra | **FAIL**, canonical passed7,UNVERIFIED; tên lạ được ghi ở tests_unexpected. |
| Skipped thật | success+skipped=true → owned control NOT_RUN,6 passed+1skipped,FAIL/INCOMPLETE; không claim7/7. |
| Diagnostics trước JSON / thiếu event expected | Full runner checkout mới và replay stream cũ đều PASS7/7; bỏ expected testDone vẫn FAIL6+1missing. |

Phạm vi “không dedupe che multiplicity” được kiểm ở ranh giới parser→validator cho **hai testID khác nhau**, đúng lỗi được giao. Count canonical chỉ giảm về7 expected sau khi duplicate đã được đánh dấu và gate chặn. Không suy thành một full Dart parser hoặc chứng minh mọi dạng protocol hỏng ngoài phạm vi đã kiểm.

## Phát hiện P0/P1/P2

Không có phát hiện mới/còn mở trong phạm vi HP3-C sau bản sửa996c426. Các báo cáo Chưa đạt trước vẫn là lịch sử đúng, không bị sửa/xóa. Provider harness chỉ là bằng chứng bổ trợ, không kết luận app đã sạch mọi retained object/RAM.

## Reviewer tự chạy

Evidence riêng:[review_c63e43f_evidence/](review_c63e43f_evidence/).

| Lệnh/kiểm tra | Kết quả mới |
|---|---|
| python scripts/bh07_heap/run_heap_verification.py | **Exit0**, source996c426 sạch trước capture, AST CLEAN,suite **PASS7/7 VERIFIED**,provenance CLEAN,generated manifest4/4 PASS; không wrapper/không đổi thành --no-pub. |
| python -m unittest tests.test_bh07_heap_controls -v | **Exit0,33/33 OK** |
| audit_ast_memory.py --test-controls | **Exit0,12/12** |
| clean_and_manifest.py --test-controls | **Exit0,5/5** |
| clean_and_manifest.py --verify | **Exit0,4/4** bundle tác giả,strict UTF-8 LF,0 secret/JWT ngoài allowlist theo scanner; fingerprint trước/sau bằng nhau. |
| review_b7eb881_evidence/duplicate_probe.py | **Exit0**, nguyên file; exact-name/different-group duplicate đều FAIL/UNVERIFIED,report false,main-boundary1; positive PASS7,missing expected event FAIL. |
| review_cb5bf41_evidence/protocol_probe.py | **Exit0**, nguyên file; prefix/JSON positive PASS,skipped/unknown negative đúng kỳ vọng. |
| review_ccad24c_evidence/probes.py | **Exit0**, nguyên file vàpositive controls giữ nguyên. |
| review_33ad6e6_evidence/extra_controls.py | **Exit0**, nguyên file; dispose lexical controls,subset/no-tests,Git error UNKNOWN giữ đúng kỳ vọng. |
| flutter analyze --no-pub | **Exit0,0 issue** |
| flutter test --no-pub | **Exit0,247 PASS+1 skip** |
| multiplicity_trace.py reviewer | **Exit0**,8 records trước validator,2 equal-name records còn đủ,duplicate999 làmFAIL. |
| Source/SHA | source996c426..docs c63e43f không đổi runtime tree; từ base chỉ runner +Python regression test đổi,lib/backend/Provider suite nguyên; source hashes4/4 khớp Git blob vàbytes hiện hành;2 handoff SHA resolve. |

Reviewer Linux Flutter3.47.7, tác giả Windows3.47.6. Full runner gọi Flutter thật trên PATH, package resolution bình thường ở worktree mới. Hồi quy/analyze --no-pub dùng dependencies đã có, local loopback harness; skip1 là HTTP integration chưa bật, không gọi là real HTTP/Auth trong lượt này.

Raw full runner reviewer và bundle mới được lưu trong runner_output (khác bundle tác giả); original manifest bytes được giữ dưới tên original_manifest.txt để tránh recursive verifier bỏ qua nested hashes.sha256. Old probes không đổi source/kỳ vọng. Main-boundary controls là external-command stubs để kiểm exit âm/dương, **không phải** các lần chạy full runner thật bổ sung; full runner thật7/7 được ghi riêng. Log reviewer chuẩn hóa UTF-8 LF; không regenerate bundle tác giả.

## NOT RUN và giới hạn giữ nguyên

- **V2b app-profile heap snapshot/retained paths trên app thật** (widget/Auth/SupabaseClient graph,Chrome CDP/VM-service):NOT RUN. WeakReference root DTO trong Provider/mock harness không chứng minh mọi bản sao đã rời RAM.
- Audit memory tĩnh là lexical heuristic, không phải Dart AST đầy đủ/retention-path proof.
- Real HTTP/JWT/Auth/DB/migration/backup/managed Supabase/PITR/offsite/encryption/retention/concurrent writers trong lượt tooling này.
- Device/browser khác/offline/deep link,banking/webhook,staging/production restore/deploy,load rehearsal/pilot và nghiệm thu toàn BH-07.

## Trạng thái và bước tiếp

**Đóng phần sửa gói Provider/tooling hỗ trợ V2b trên nhánh, giữ Git ref chưa merge.** Không còn yêu cầu sửa HP3-C. V1/V5b giữ Đạt local; app-profile heap V2b và các cổng chưa kiểm giữ NOT RUN. Có thể giao phép đo app-profile heap thật theo mục4.4 readiness ở nhiệm vụ riêng; chưa triển khai/chuyển cổng trong lượt này.

Không merge main/staging/production/deploy/pilot/BH-08.

**Kết luận cuối: Đạt gói Provider/tooling trong phạm vi review HP3-C; V2b app-profile vẫn NOT RUN.**
