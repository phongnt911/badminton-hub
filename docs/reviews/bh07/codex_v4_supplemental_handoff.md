# V4 — Codex sửa bổ sung theo ủy quyền ngày 09/11/2026

**Đạt bản sửa guard/probe trong phạm vi review độc lập; toàn V4/BH-07/V8 chưa nghiệm thu.** Chủ dự án giao rõ “codex tự sửa” sau [điểm dừng Anti 3/3](review_v4_concurrent_backup_final_20261109.md). Đây là ủy quyền sửa cụ thể, không tự mở vòng Anti thứ tư, không chấp nhận rủi ro vận hành hay phê duyệt tích hợp/deploy. [Reviewer riêng](codex_v4_supplemental_review.md) không triển khai bản sửa và chốt phạm vi delta/test, giữ full source/runtime NOT RUN.

## Thay đổi

- Thêm guard tại đầu `validate_v4_rehearsal`: cả ba operation của workload phải có `request.operation=record_cash_payment`, JSON `result` là object, `result.status=confirmed`. Các kiểm tra payment/amount/hash và gate cũ giữ nguyên phía sau.
- Probe đổi một dòng: `canonical_restored_fp = fp(1, sha_hex='e' * 64)`, khớp replay fingerprint fixture; giữ nguyên assertion và mutant.
- Thêm sáu regression tests trong `tests/test_bh07_v4_codex_supplemental.py`. Digest được tính lại độc lập; restored row evidence giữ cùng row sai, nên test kiểm invariant chứ không dựa vào checksum bị hỏng.

## RED → GREEN

Codex chạy sáu test mới trước sửa: **27 failures ở subtest/entrypoint**, positive hợp lệ vẫn PASS. Sau sửa: **6/6 PASS**. Suite V4 cũ **56/56 PASS**; standalone probe **49 controls PASS**. Đây là kiểm chứng implementer Codex; kết quả reviewer riêng được ghi tách bên dưới.

Kết quả cuối: Codex **499/499 Python PASS**, exit0, 274.930s, archive `dc76b368a2c8d7b9`. Reviewer tự chạy độc lập **499 PASS**, exit0, 269.599s, archive `40d0c86602f22803`, cùng 62 targeted/49 probe controls và 1 positive +48 semantic mutant. Không cộng hai suite thành số test duy nhất mới. Reviewer xác nhận delta byte ngoài guard giữ nguyên, không phát hiện P0/P1/P2 trong **bản sửa có giới hạn**.

Codex `flutter analyze` **0 issue**, 30.4s; `flutter test` **247 PASS +1 SKIP**, exit0, archive `30bc4a6831c03eb4`. App/schema/Dart tests/web/pubspec không đổi. [Replay immutable](codex_v4_supplemental_evidence/guard_replay_20261109.json): **11/11 kết quả đúng kỳ vọng**, gồm positive PASS và cả 10 mutant bị chặn; input gốc trước sửa giữ nguyên bytes.

## Giới hạn đọc source và bằng chứng delta

Gateway vẫn giữ toàn runner (`secret.redacted/redaction.incomplete`); không dùng reader khác để xuất nội dung bị giữ, không đổi quyền/gateway hoặc tạo bản source cho reader khác. Bản sửa là phép chỉnh AST có giới hạn trên preimage SHA256 đã ghim, thực hiện nội bộ khi edit, chỉ xuất metadata hash/offset và literal guard do Codex viết; **không nhận là đã đọc/review toàn bộ runner**.

[Editor và literal guard](codex_v4_supplemental_evidence/apply_request_guard.py), [receipt](codex_v4_supplemental_evidence/guard_edit_receipt.json): source trước `bd51710852ec075591e2e263f79c069d0c7988bbdefe4a6db6fc93916ebd95f8`, sau `53dc32fd1e647e2f0d7252fc513f85872c7250cea9b2c7d7b463289c17f7949d`; chèn 1.179 byte tại offset 7.969/dòng 209. Bỏ đúng đoạn guard khỏi postimage phải khôi phục hash preimage; mọi byte ngoài guard giữ nguyên. Editor từ chối preimage lạ, tên local trùng, receipt có sẵn hoặc kết quả parse không hợp lệ; không chạy lại editor trên source đã sửa.

[Replay helper](codex_v4_supplemental_evidence/replay_final_controls.py) dùng input immutable từ capture cuối trước sửa, hash source trước import và sau chạy, xuất file mới; không ghi lại bundle cũ. Đây là kiểm chứng synthetic, không phải DB/HTTP runtime.

## Phạm vi và NOT RUN

Chỉ sửa guard, fixture probe, test và tài liệu/evidence mới; không sửa app/schema/migration/dependency hoặc historical captures. HEAD/base vẫn `b72c563d9e519986dbd88ec98bcc3f015a41a442`, working tree chưa commit. Full source/runtime V4 (Docker/Auth/HTTP/export snapshot/dump/restore/cleanup), native/mobile/staging/managed/load/pilot NOT RUN. Không dùng test xanh hoặc delta review để đóng những khoảng này hay ký thay owner risk acceptance.
