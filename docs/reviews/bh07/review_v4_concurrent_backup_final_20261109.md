# BH-07 V4 — Chưa đạt, dừng sau sửa vòng 3/3

Ngày 09/11/2026. Anti CLI triển khai; Codex kiểm chứng hành vi độc lập. Nhánh `feat/bh07-completion-local`, HEAD/base vẫn `b72c563d9e519986dbd88ec98bcc3f015a41a442`; candidate mới nằm trong working tree, chưa có clean tested commit. Không ghi nhận full source review: gateway tiếp tục giữ runner với `secret.redacted/redaction.incomplete` khi Codex đọc fresh sau vòng 3. Thông báo đó không chứng minh có secret thật.

## Kết luận

**Chưa đạt phạm vi V4 tooling; V4 runtime NOT RUN; toàn BH-07/V8 chưa nghiệm thu.** Còn R1 P1 và một P2 probe. Dừng sửa theo [AGENTS.md](../../../AGENTS.md), dòng 148: “Còn lỗi sau 3 vòng thì dừng và báo chủ dự án.” Dòng 149 cũng giữ vai trò reviewer, không tự viết lại implementation nếu chưa được giao rõ. Không mở vòng 4 hoặc tự sửa thay Anti.

## Phát hiện cuối

### R1 — P1, stored result vẫn có thể thiếu hoặc mâu thuẫn mà PASS

`scripts/bh07_backup/run_v4_concurrent_rehearsal.py`, hàm `validate_v4_rehearsal` (số dòng implementation chưa đọc được do gateway). [Control độc lập cuối](v4_review_r1_evidence/final_controls.py) gọi hàm thật với positive mới của candidate vòng 3; SHA256 relational được tính lại độc lập và restored row evidence được cập nhật giống row sai:

- `stored_result_wrong_status`: nested `request.result.status='rejected'`, trong khi normalized `request.status='confirmed'` ⇒ **ok=true, PASS, findings=[]**.
- `missing_stored_result`: bỏ hẳn `request.result`, giữ các field normalized khác ⇒ **ok=true, PASS, findings=[]**.
- `wrong_request_operation`: `request.operation='confirm_payment'` trong workload `record_cash_payment` ⇒ **ok=true, PASS, findings=[]**.

Đây là mâu thuẫn/thiếu dữ liệu trong **receipt synthetic** mà validator chấp nhận; không có quan sát raw DB hoặc bằng chứng app/DB thật bị hỏng. Cần bắt buộc stored `result` đúng schema, kiểm trạng thái nghiệp vụ và operation/actor/intent thay vì chỉ tin field normalized. Các binding actor/payload hash và toàn bộ scoped replay content vẫn cần bằng chứng/source review đầy đủ; canonical hiện hành chưa đủ để tự chứng minh các ràng buộc đó.

Các control sai stored result payment/amount, sai ledger amount/audit request, replay hash không hợp lệ hoặc hợp lệ nhưng khác restored payment hash, và sai replay response payment đã bị chặn. Không gọi việc chặn các case đó là đóng toàn bộ R1 khi ba case trên còn PASS.

### V4-R6 — P2, probe tác giả không qua positive control

`scripts/bh07_backup/v4_concurrent_probe.py:168–174`: `canonical_restored_fp = fp(1)` cung cấp payments SHA256 bằng 64 ký tự `a`, trong khi canonical replay fingerprint là 64 ký tự `e`. Validator mới yêu cầu khớp nên `python scripts/bh07_backup/v4_concurrent_probe.py` **exit1 tại dòng 174**, finding `replay_fingerprint_mismatch`. Probe dừng trước các mutant. Cần sửa fixture positive nhất quán và giữ nguyên guard/finding; không bỏ assertion hoặc nới validator để xanh.

## Kiểm chứng thực hiện

| Lệnh/kiểm tra | Kết quả |
|---|---|
| `python tests/test_bh07_v4_backup_concurrency.py -v` | **56/56 PASS**, exit0 |
| `python scripts/bh07_backup/v4_concurrent_probe.py` | **FAIL**, exit1 tại positive control |
| `python docs/reviews/bh07/v4_review_r1_evidence/final_controls.py` | **FAIL**, exit1: 1 positive PASS, 7 mutant bị chặn, 3 mutant vẫn PASS |
| `python -m unittest discover -s tests` của candidate cuối | **493/493 PASS**, exit0, 300.616s, archive `dda516cc1529656f` |
| `flutter analyze` trong lượt này, app không đổi | **0 issue**, 38.9s |
| `flutter test` trong lượt này, app không đổi | **247 PASS +1 SKIP**, exit0, archive `c6bf57e63de74c51` |
| `git diff --check` và diff app/schema | Whitespace sạch; `lib/`, `test/`, `supabase/`, `web/`, pubspec không đổi |

[Capture cuối](v4_review_r1_evidence/final_capture_20261109.json) lưu input/output synthetic và hash source, lấy hash **trước cả import/fixture load** rồi kiểm lại sau; không ghi đè capture cũ. Đây là capture mới theo schema vòng 3, không phải replay byte-identical các canonical cũ. Source hashes:

- Runner: `bd51710852ec075591e2e263f79c069d0c7988bbdefe4a6db6fc93916ebd95f8`.
- V4 test: `9f4e51a5075e4dbe460e1ed4597ea1afbcc1c4c29552d0daf76c90e96f86ea82`.
- Probe tác giả kiểm riêng: `a703b79b858bb01fe11630f5f9191b2cf6ce75559e7056376ed2133579f8ab9a`.

Suite 437 là baseline trước V4; 477 là bản sửa vòng 1; không dùng hai count đó làm kết quả candidate cuối. Vòng 2 có 49 targeted/44 author controls PASS theo [review sau vòng 2](review_v4_concurrent_backup_after_r2.md); không retag thành vòng 3.

Full suite cuối kết thúc sau các control độc lập; hash runner/test kiểm lại vẫn khớp capture cuối. Đây là working-tree verification, không phải clean-checkout replay. Standalone probe và reviewer controls được chạy riêng như bảng trên, nên suite unittest xanh chưa đóng các phát hiện của chúng. Không còn process `agy` tại kiểm tra sau bàn giao.

## NOT RUN và điểm tiếp

Full source review; Docker/DB/HTTP writers/export snapshot/dump/restore/replay/cleanup runtime V4; DB fingerprints trước/sau runtime; staging/managed/PITR/native/mobile/load/pilot. Không có fixture/dump/browser profile V4 được tạo trong lượt này. Không dùng black-box unit hoặc canonical synthetic thay cho các bằng chứng đó.

Tám core local tiếp tục giữ kết luận theo [audit V8](v8_readiness_audit_20261109.md); V8-D1 docs đã đóng. V2/V2b/V3/V5/V7 vẫn thiếu các bằng chứng/quyết định riêng, V6 ngoài phạm vi, gói 59 file main tooling vẫn chưa được tích hợp. Chỉ có owner mới có thể giao thêm phạm vi sửa sau điểm dừng hoặc đổi vai trò; các cổng chưa chạy cần bằng chứng hoặc quyết định rủi ro đúng quy tắc V8, không dùng quyết định đó che lỗi còn mở.

Mọi thay đổi của lượt này còn local/uncommitted. Không merge/push/deploy/pilot/BH-08. [Bàn giao tiếp tục](bh07_completion_continuation_20261109.md) giữ lịch sử phiên Anti, lỗi permission/network và các vòng kiểm chứng.
