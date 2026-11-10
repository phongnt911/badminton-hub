# BH-07 V4 — review chức năng candidate vòng đầu, 09/11/2026

**Chưa đạt.** Candidate working tree trên base `b72c563d9e519986dbd88ec98bcc3f015a41a442`, chưa có tested commit mới. Anti triển khai; Codex chạy kiểm chứng riêng. Không nhận lời bàn giao là PASS. Đây là review có giới hạn: gateway vẫn giữ runner với `secret.redacted/redaction.incomplete` kể cả sau khi Anti báo bỏ literal và Codex đọc `fresh=true`; chưa review được toàn source hoặc chạy Docker/DB. Không kết luận candidate chứa secret thật từ thông báo gateway.

## Phát hiện thực tế

1. **V4-R1 — P1: validator chấp nhận evidence thiếu hoặc mâu thuẫn dữ liệu.** `scripts/bh07_backup/run_v4_concurrent_rehearsal.py`, hàm `validate_v4_rehearsal` (không xác định được số dòng source vì gateway giữ nội dung). [Probe reviewer](v4_review_r1_evidence/probes.py) gọi hàm thật: positive PASS; cả các mutant `missing_both_fingerprints`, `missing_source_fingerprint`, `source_count_999`, `malformed_restored_hashes`, `wrong_numeric_amount`, `duplicate_source_payment_id`, `duplicate_source_request_id`, `substituted_restored_payment_id` đều `ok=true, verdict=PASS, findings=[]`. Các ID/số tiền sai không được bảo vệ bởi cờ presence và số dòng bằng nhau. Cần bắt buộc evidence nguồn/restore, kiểm hash hợp lệ và đối chiếu dữ liệu quan hệ thực (payment amount/ID ↔ ledger source_payment/amount ↔ audit entity/request/actor ↔ operation result), snapshot membership và replay content; không chỉ kiểm boolean/count. Thêm test RED cho từng lỗi trước sửa.
2. **V4-R2 — P2: trạng thái/provenance FAIL vẫn có verdict PASS.** Cùng hàm thật trả PASS cho `failed_status`, `dirty_source`, `invalid_source_sha` ở probe reviewer. Cần từ chối report FAIL, provenance thiếu/sai và source dirty theo contract clean-source runtime; runtime phải lấy SHA thực tế, không dùng SHA giả trong fixture làm metadata thật.
3. **V4-R3 — P2: control publication secret đang FAIL.** `tests/test_bh07_v4_backup_concurrency.py:424`, `test_reject_exposed_secrets`: `assertFalse(result.get('ok'))` nhận True. Codex chạy trực tiếp hai lần đều 27 tests/1 FAIL. Probe tác giả hiện chỉ chạy 21 controls, không còn control exposed-token ban đầu; probe xanh không thay test đang đỏ. Cần điều tra nguyên nhân và giữ control synthetic không tiết lộ credential thật; không bỏ/nới assertion để xanh.

## Khoảng trống cần xử lý cùng đợt sửa

[Review test độc lập](v4_test_design_review_20261109.md) chỉ ra receipt cleanup chưa ràng buộc đủ owned resource/network, overlap chưa có control DB observation liên kết đúng PID/query/request và các relational mutants còn thiếu. Đây chưa phải bằng chứng implementation runtime đã sai ở các nhánh đó, nhưng phải bổ sung kiểm chứng trước khi nhận acceptance; việc đọc/kiểm source còn thiếu là blocker review.

## Kiểm chứng và giới hạn

- Baseline trước V4: 437 Python PASS, exit0, 261.777s, archive `f7f178da1f5aa7a8`; không phải suite sau patch.
- RED giai đoạn đầu: 13 FAIL do missing implementation; sau candidate: `python tests/test_bh07_v4_backup_concurrency.py -v` 27 tests/1 FAIL, exit1.
- `python scripts/bh07_backup/v4_concurrent_probe.py`: 21 controls PASS, chỉ chứng minh các control có trong probe.
- `python docs/reviews/bh07/v4_review_r1_evidence/probes.py`: diagnostic, exit0 của script không phải verdict acceptance; 1 positive và 11 mutant đều PASS như trên, tái hiện fail-open.
- `python -m py_compile` trên ba file Python mới: exit0, không phải runtime.
- NOT RUN: full source review, Docker backup/restore/HTTP/DB runtime V4, cleanup runtime, full suite sau patch, Flutter mới, staging/mobile/managed/PITR/load/pilot. Các kết luận core/ledger trước đó giữ nguyên phạm vi.

Giao Anti sửa vòng 1/3 trên bốn file mới được giao, giữ probe reviewer nguyên bản. Chưa merge/push/deploy/pilot/BH-08; toàn BH-07/V8 chưa nghiệm thu.

## Đính chính phạm vi control sau audit độc lập

`wrong_numeric_amount` chỉ đổi một số nguyên hợp lệ trong `source_operations`, chưa có expected requested amount hoặc row restore độc lập để mâu thuẫn với 99.999. `source_count_999` cũng cần xác định rõ fingerprint tính trên fixture sở hữu hay toàn bảng có baseline. Hai control này chứng minh chưa có ràng buộc tới dữ liệu kỳ vọng độc lập trong contract đã dùng, **không chứng minh số tiền runtime bị sửa hoặc DB mất dữ liệu**. Các mâu thuẫn ID/request trùng, restored P0 ID bị thay, thiếu evidence, digest không hợp lệ và status/provenance vẫn giữ kết quả quan sát nêu trên.

Probe gốc import `build_canonical_summary` từ file tác giả có thể thay đổi. Giữ bytes probe không đồng nghĩa giữ bytes input. Vì chưa lưu frozen input/hash candidate ở lần đầu, không gọi lần chạy sau là replay byte-identical; phép kiểm sau sửa cần fixture/evidence cố định và source hash riêng, cùng positive mới hợp lệ theo schema tăng cường. Giữ probe/report gốc để truy vết, không dùng việc tất cả input cũ bị từ chối làm bằng chứng validator mới đúng.

Đã tạo **capture synthetic mới**, không gán ngược thành input R1 nguyên bản: [diagnostic_capture_20261109.json](v4_review_r1_evidence/diagnostic_capture_20261109.json), bằng [capture_current.py](v4_review_r1_evidence/capture_current.py). Lưu canonical/fingerprint synthetic, 12 kết quả và SHA256 của runner/probe/reviewer script; hash source trước/sau bằng nhau. Capture SHA256 `72944b37a5921d873163aaab818a23faecf17bc6a21b4b639e80777ace3d5225`. Đây không phải fingerprint DB hoặc runtime; digest synthetic không được diễn giải thành hash row thật. Không ghi đè capture này khi kiểm bản sửa.
