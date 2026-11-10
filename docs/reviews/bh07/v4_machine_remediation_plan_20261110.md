# Giao Anti CLI — phương án MC1–MC6 ngày 10/11/2026

**Ủy quyền mới 10/11/2026:** chủ dự án yêu cầu “codex tự sửa”. Codex trực tiếp triển khai MC1–MC6 và test tái hiện; đây là ngoại lệ cụ thể sau mốc dừng Anti, không giao Anti vòng sửa thứ tư. Không tự coi phần tự sửa/tự kiểm là review độc lập. Phạm vi chỉ tooling V4/test và tài liệu trạng thái; không đổi app/schema hoặc chạy production.

Thứ tự thực hiện: RED cho collector/snapshot/overlap/replay/trạng thái và dữ liệu seed → sửa helper/luồng main tối thiểu → regression Python/probe → kiểm source/provenance và môi trường → báo cáo Chờ review độc lập, runtime nào chưa chạy giữ NOT RUN.

Base `423f354`, nhánh `feat/bh07-completion-local`. Chủ dự án giao chuyển nhánh, review và giao Anti CLI việc tiếp theo. Codex review tại [báo cáo](review_423f354_machine_continuation.md).

## Phiên Anti và trạng thái thực

- Anti IMPLEMENTER, model `gemini-3.8-flash-high`, effort high, chế độ `plan`.
- Conversation `7740d64d-dde6-4613-8ffd-3793b80684fe`.
- Nhiệm vụ: phân tích MC1–MC6, thiết kế sửa tối thiểu và RED reproductions đi qua collector/main; không sửa source/test/config, không shell/SQL/Docker, không agent con, không commit/push.
- CLI trả **exit 1 / DEADLINE_EXCEEDED / print_timeout sau 6 phút**, có nội dung phương án trả về một phần. Không nhận là bàn giao hoàn chỉnh hoặc implementation đã xong. Phần dưới là Codex tóm lược có attribution từ phản hồi Anti, không phải nguyên văn hay verdict review độc lập.
- Không có sửa implementation trong Git từ lượt giao này. Anti báo đã tạo artifact nội bộ của CLI; artifact đó không phải bằng chứng runtime hay file bàn giao được Git theo dõi.

## Phương án Anti đề xuất

1. **MC1:** sửa collector dùng `payments.session_player_id`, `club_transactions.amount_vnd`; liên kết request qua operation_requests/audit. Đồng bộ validator/fixture theo contract mới; không thay schema app.
2. **MC2:** psql quiet + tuples-only, đọc snapshot ID có định dạng hợp lệ; timeout/EOF/exit và giữ transaction sống tới khi dump xong.
3. **MC3:** loại observer khỏi pg_stat_activity; ghi mốc kết thúc dump trong worker, kiểm giao hai writer trong khoảng dump thật; bỏ receipt PID/query tổng hợp.
4. **MC4:** đọc fingerprint DB sau replay và so với trước replay, kiểm dữ liệu cả payment/ledger/audit/request, không chỉ row count.
5. **MC5:** phân biệt hoàn tất collector với verdict auditor; không để receipt thành công thiếu status hoặc gán PASS đè lỗi.
6. **MC6:** không dựng row khi SQL thiếu; lấy audit bằng request/actor đúng scope thay vì thứ tự hoàn thành; cardinality theo workload hoặc baseline seed.

File dự kiến (CHƯA được sửa): runner, probe, test V4 hiện có và một file test runtime-collection mới; handoff cập nhật theo candidate. Không sửa lib/supabase/migration. RED cần đi qua collector, giao thức snapshot, lịch executor và nhánh main; test chỉ dựng receipt không đủ đóng MC1–MC6.

## Codex đối chiếu phương án trước khi triển khai

**Chưa chấp thuận để triển khai từ phản hồi một phần.** Cần chỉnh rõ các điểm sau trong thiết kế trước khi thực thi:

- Anti đề xuất vòng `while timeout` quanh `stdout.readline()`: bản thân readline có thể block vô hạn. Cần cơ chế timeout thật cho đọc pipe và đảm bảo đóng transaction/process cả khi lỗi; không nhận vòng while đó là đủ.
- Query observer chỉ loại psql/chứa COPY chưa đủ chứng minh dump đúng run. Cần identity backend/connection cụ thể và quan sát trong khoảng giao writer; kết thúc subprocess không tự chứng minh backend tồn tại xuyên suốt khoảng đó.
- MC1 SQL lỗi với ON_ERROR_STOP sẽ raise, không bị fallback che exception. Fallback chỉ che trường hợp query chạy thành công nhưng trả không có row; giữ hai loại failure tách biệt.
- Liên kết request phải gồm actor + operation + request ID theo khóa schema; không chỉ request_id. Khi thay receipt phải bảo toàn kiểm idempotency và cập nhật toàn bộ fixture liên quan.
- Fingerprint replay phải lấy dữ liệu mới từ DB sau RPC, kiểm cả schema và dữ liệu các bảng liên quan. Không cho phép copy digest trước replay vào trường sau replay.
- Inventory/port cố định do Anti đề xuất chưa chứng minh cổng runtime cấp phát động hay Docker daemon máy mới. Python bundled đã có, Docker/Flutter chưa có trên PATH; không tự cài hoặc coi environment máy POTA là bằng chứng máy PHONGNT.

## Cổng tiếp theo

AGENTS.md:150 yêu cầu dừng sau ba vòng; V4 đã hết ba vòng. **Đã được thay bằng quyết định owner “codex tự sửa” ngày 10/11/2026:** Codex sửa trực tiếp MC1–MC6, không giao Anti vòng 4; không còn chờ owner cho phạm vi tự sửa này. Bản hỏi ngoại lệ trước đó là lịch sử.

Codex đã sửa tại `704a326`; [review độc lập](review_704a326_mc_fixes.md) Đạt phần source/test MC1–MC6. Kết luận tự kiểm được tách biệt với reviewer và runtime chưa chạy. Rehearsal chỉ sau source đạt và tiền kiểm môi trường/resources/provenance được xác nhận. Không merge/deploy/pilot.

**Cập nhật sau tự sửa:** code/test tại `704a326`, 76 targeted PASS; full Python 509 PASS +4 SKIP; probe 49/49 PASS. **NOT RUN:** Flutter mới, Docker/HTTP/DB/dump/restore/cleanup V4. Toàn BH-07/V8 chưa nghiệm thu.
