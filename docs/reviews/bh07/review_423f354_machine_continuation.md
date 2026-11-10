# Review tiếp tục trên máy PHONGNT — 10/11/2026

Tested HEAD `423f354`, nhánh `feat/bh07-completion-local`. Codex review toàn file runner V4 và helper setup, đối chiếu schema/seed hiện có. Không sửa implementation, không mở vòng sửa Anti thứ tư. Review này bổ sung phần source chưa đọc được trên máy cũ, không phủ định acceptance guard/probe giới hạn ngày 09/11.

## Chẩn đoán gateway lịch sử

Đạt trong phạm vi báo cáo quan sát trên máy POTA: hai path cấu hình bị jail, nguyên nhân source redaction vẫn UNKNOWN; không có bằng chứng admission được phục hồi. Đây là bằng chứng lịch sử, không phải trạng thái máy PHONGNT. Ở máy mới công cụ đọc source hiện hành đã trả toàn runner; không thay policy, không truy cập config POTA, không thử lại lệnh doctor bị chặn. Working tree hiện đã có candidate Git, không còn dùng trạng thái dirty của máy cũ cho candidate này.

## Phát hiện cần xử lý trước runtime

Các vị trí dưới đây thuộc `scripts/bh07_backup/run_v4_concurrent_rehearsal.py` tại tested HEAD.

- **MC1 P1 — dòng 776–778:** query dùng `payments.request_id`, `payments.player_id`, `club_transactions.amount`. Schema migration hiện dùng `payments.session_player_id`, `club_transactions.amount_vnd`; không có hai cột payment kể trên. SQL thu evidence sẽ lỗi trước snapshot. Sửa mapping từ schema thật; request liên kết qua operation_requests/audit, không thêm cột app để chiều runner.
- **MC2 P1 — dòng 811–823:** psql không bật quiet/tuples-only nhưng lấy dòng stdout đầu tiên làm snapshot ID. Command tag `BEGIN` có thể bị dùng làm `--snapshot=BEGIN`. Sửa giao thức đọc snapshot tường minh, timeout, kiểm transaction còn sống; test transcript psql thực tế và lỗi/EOF.
- **MC3 P1 — dòng 851–914, 958–976:** query quan sát không loại `pg_backend_pid()` nên chính SELECT chứa `COPY` có thể tự khớp. Mốc kết thúc dump chỉ lấy sau khi đợi cả hai writer; dump kết thúc trước writer vẫn có thể được báo overlap. Phải ghi completion trong worker dump và chứng minh backend thật còn sống trong khoảng giao hai writer; thiếu receipt phải FAIL, bỏ fallback PID/query dựng sẵn.
- **MC4 P1 — dòng 1067–1086:** after_replay_fingerprint dùng lại `restored_fp` trước replay, fingerprint_unchanged hardcode true. Mutation giá trị nhưng không tăng số dòng có thể không bị phát hiện. Đọc lại DB sau replay, so sánh fingerprint payment/ledger/audit/request và schema đúng scope; thêm control cùng count khác dữ liệu.
- **MC5 P2 — dòng 719–731, 1144:** summary không có status PASS trên đường thành công trước khi gọi validator, trong khi validator yêu cầu status == PASS tại dòng 248. Do đó đường thành công vẫn bị failed_status. Tách trạng thái thực thi ứng viên với verdict auditor; bảo toàn lỗi trước đó, không chỉ gán PASS vô điều kiện.
- **MC6 P1 — dòng 777–794, 919–920:** thiếu row SQL được thay bằng record tổng hợp; audit hai writer gán theo thứ tự created_at thay vì request ID nên có thể đổi chéo. Bằng chứng phải được đọc thật, thiếu row phải FAIL, audit/request gắn actor+operation+request ID; kiểm cardinality theo workload thay vì toàn bảng seed có sẵn.

## Kiểm chứng mới

Python runtime đi kèm Codex: `C:/Users/PHONGNT/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe`.

Trong `tests/`: `python -m unittest test_bh07_v4_codex_supplemental test_bh07_v4_backup_concurrency` — **62/62 PASS**, exit 0, 0.169s. Đây là unit/synthetic validator, không đi qua main/DB/dump; không đóng các lỗi source nêu trên. Schema đối chiếu tại `supabase/migrations/20261015051808_init_schema_v1_1.sql:446` và các migration hiện có. Không có sửa app/DB.

[Control reviewer mới](review_423f354_evidence/probes.py) chạy exit 0: canonical receipt được nhận, cùng receipt bỏ status bị `failed_status`; [JSON kết quả](review_423f354_evidence/results.json) ghi rõ synthetic/NOT RUN và SHA-256 worktree. Git blob runner `10cd30afd7940c0da92591469778f66d6a2fef52`; không lấy raw hash khác do checkout line ending để suy source ứng dụng đã thay đổi.

Anti CLI `agy models` qua quyền truy cập thông thường của CLI đã thành công. Python/Flutter/Docker không có trên PATH phiên hiện tại; Python bundled có sẵn. Không lấy inventory Docker của máy POTA làm kết quả máy này.

## Kết luận và giao tiếp

**Chưa đạt full runner V4; chưa cho chạy rehearsal.** Giữ acceptance guard/probe lịch sử đúng phạm vi. Anti đã hết ba vòng sửa V4; nhiệm vụ tiếp chỉ phân tích thiết kế khắc phục MC1–MC6, đề xuất test RED và tiền kiểm máy mới, không sửa source/test hoặc chạy Docker. Cần ủy quyền ngoại lệ riêng trước khi triển khai sửa tiếp; giao phân tích không tự mở vòng 4.

Đã giao Anti CLI, conversation `7740d64d-dde6-4613-8ffd-3793b80684fe`; CLI hết 6 phút và trả phương án một phần, không phải bàn giao hoàn chỉnh. [Phương án và các điểm Codex yêu cầu làm rõ](v4_machine_remediation_plan_20261110.md). Không nhận timeout là một vòng sửa code; chưa có source/test implementer thay đổi.

**NOT RUN:** full Python suite, Flutter analyze/test mới, Docker/HTTP/Auth/pg_dump/restore/cleanup runtime và rehearsal V4; staging/production, pilot, toàn BH-07/V8. Không merge/deploy hoặc chấp nhận rủi ro thay owner.
