# Review bổ sung Codex V4 — 09/11/2026

Phạm vi: bản sửa được owner ủy quyền “codex tự sửa” sau mốc dừng vòng 3; base `b72c563d9e519986dbd88ec98bcc3f015a41a442`, workspace chưa commit. Reviewer này không triển khai guard hoặc sửa probe. Không sửa kết luận lịch sử và không coi đây là mở lại toàn BH-07.

## Kết luận có giới hạn

**Đạt phần sửa guard operation/stored-result và positive control của probe trong phạm vi kiểm chứng dưới đây.** Không phát hiện P0/P1/P2 trong phần sửa được xem xét. Không phải kết luận nghiệm thu V4 hoặc toàn runner.

Guard mới xét đủ ba operation `p0_precommit`, `p1a_concurrent`, `p1b_concurrent`: request phải có `operation == record_cash_payment`, `result` là object và `result.status == confirmed`; giá trị khác trả FAIL trước các kiểm tra cũ. Những nhánh thiếu cấu trúc được chuyển tiếp tới validator cũ, không được guard mới tự cấp PASS. Positive fixture giữ PASS. Probe sửa fingerprint restored thành `e * 64`, thống nhất với bằng chứng replay đã có; không nới validator để hợp thức hóa fixture sai.

## Bằng chứng reviewer tự chạy

- Tại `tests/`: `python -m unittest test_bh07_v4_codex_supplemental test_bh07_v4_backup_concurrency` — **62 test PASS** (56 hiện có + 6 bổ sung).
- `python scripts/bh07_backup/v4_concurrent_probe.py` — **49 controls PASS**, gồm canonical positive và các mutant cũ.
- `python docs/reviews/bh07/codex_v4_supplemental_evidence/reviewer_verify.py` — **1 positive PASS; 48 semantic mutants đều FAIL như kỳ vọng** trên cả ba operation. Bao gồm thiếu operation/result/status, sai kiểu object, status sai/case/whitespace; digest được tính lại hợp lệ và restored evidence P0 đồng bộ để không dựa vào mismatch phụ.
- Cùng script kiểm tra literal guard, SHA postimage `53dc32fd1e647e2f0d7252fc513f85872c7250cea9b2c7d7b463289c17f7949d`, SHA guard theo receipt; bỏ đúng đoạn guard cho SHA preimage `bd51710852ec075591e2e263f79c069d0c7988bbdefe4a6db6fc93916ebd95f8`. Do đó byte ngoài guard giữ nguyên theo preimage pin; không xuất nội dung runner.

Lệnh discover với `-p` bị lean-ctx chặn do nhận là inline interpreter flag; không thử lại lệnh bị chặn. Bộ 62 test ở trên chạy thành công bằng module name. Reviewer cũng tự chạy `python -m unittest discover -s tests`: **499 test PASS trong 269.599s, exit 0**; job `shell_27702bfc8df6af07`, archive `40d0c86602f22803` (không truncate). Đây là kết quả reviewer tự poll, không lấy số tác giả thay thế.

## Giới hạn còn giữ

Gateway giữ full runner (`secret.redacted`/`redaction.incomplete`); reviewer chỉ đọc literal guard trong editor được admission, receipt, probe và test, rồi kiểm tra byte bằng hash. **Review full source NOT RUN**; không suy hash thành review nội dung source cũ. Những kiểm tra cũ được bảo toàn byte và hồi quy cục bộ, chưa phải audit đầy đủ mọi invariant.

**DB/HTTP/dump/restore/runtime V4 NOT RUN. Toàn BH-07/V8 chưa nghiệm thu**; tám core và V8-D1 giữ nguyên phạm vi kết luận lịch sử. Không merge/push/deploy/pilot/BH-08. Bước tiếp theo cần bằng chứng runtime và khả năng review source đầy đủ theo gateway, không lấy control tổng hợp thay runtime.
