# Bank/receiver heap — chưa đạt sau sửa vòng 1, giao vòng 2

**Ủy quyền cập nhật 29/10/2026:** Chủ dự án cho phép tối đa 3 vòng sửa tổng cộng riêng task bank/receiver này. Đang ở vòng2/3, không reset bộ đếm. Các câu giới hạn2/2 bên dưới ghi lại quy định tại thời điểm lập review; giới hạn hiện hành là3, các ràng buộc model/phạm vi/không merge trước phê duyệt giữ nguyên.

- Ngày29/10/2026; base `94fd997674285f4bfe9e56a5ad8e70c06eb8d84b`, nhánh feat/bh07-bank-receiver-heap.
- Sáu file source/test của vòng sửa1 được snapshot local tại build/bank_review_round1_source/, kèm source_hashes.json/tracked.diff. Antigravity chỉ dùng Gemini 3.8 Flash (High). Codex không sửa logic triển khai.
- Đóng BKR1 (scope main), BKR3 (UI flag/finally/receipt/redaction), BKR4 (schema/Owner anchor), BKR7 (atomic fresh output/refusal). Missing-ID/profile omission của BKR5 đã bị chặn; legacy positive vẫn qua.
- **Chưa đạt: còn BKR2 P1, BKR5 P2, BKR6 P2. Chưa chạy live DB/runtime. Đây là toàn bộ gói sửa vòng2/2 cuối.**

## BKR2 — P1: HTTP adapter thật mất status, helper nhận sở hữu sau 403

`scripts/bh07_appheap/run_app_profile_heap.js:186–197` chỉ ném Error chuỗi, không giữ res.status. `disposable_bank_fixture.js:88/119/149` dựa vào err.status, trong khi fake test tự gắn thuộc tính mà adapter thật không có.

Probe xuyên chính restGet/restWrite và helper production, fake HTTP403 cùng matching readback: error_status_forwarded=null, claimed_club_after_definite_rejection=true, deleted_club_after_rejection=true. Không gọi DB thật. Phải truyền status, không nhận ownership khi server từ chối chắc chắn; giữ reconciliation exact payload cho lost ACK thực sự. Thêm control xuyên adapter+helper. Hoàn tất preflight memberId cùng clubId/bankId trước POST; không nhận/xóa ID có sẵn.

## BKR5 — P2: bank/receiver Owner-load và baseline graph mâu thuẫn vẫn exit0

`verify_evidence.py:717–741`, `heap_oracle.py:828`: chỉ ID có required Owner reachability; rendered load controls không được đối chiếu graph. Các clone dùng real renderer/manifest/auditor có đủ contract và receipts:

- bank_positive: oracle PASS, auditor0 (đúng).
- rendered_owner_values_unreachable: bank/receiver presenttrue,count1 nhưng reachablefalse ở Owner: oracle PASS,auditor0 (sai).
- rendered_baseline_path_retained: bank/receiver presentfalse,count0 nhưng graph reachabletrue ở baseline: oracle PASS,auditor0 (sai).

Đòi Owner reachable và baseline không reachable cho cả required load group, không chỉ count. Không biến rendered values sau logout thành absence gates; vẫn residual risk unattributed. Thêm full CLI positive/two mutants; giữ missing-ID và legacy controls.

## BKR6 — P2: test sai phase và tự sửa source

- `test_disposable_fixture_scenarios.js:244`: delete_failure trả row từ preflight nên test FAIL vì collision, không đến DELETE. `:185`: lost_foreign_row cũng trả foreign row trước POST, pass mà không kiểm reconciliation. Phân tách phase; assert đúng POST/DELETE đã được gọi ở nhánh cần test.
- `tests/test_bh07_bank_heap_coverage.py:521`: test obsolete-file tự unlink source rồi assert vắng. Xóa thao tác sửa source khỏi test; file rỗng cũ đã được xác nhận vắng, không tạo lại.
- `:473`: guard test trỏ nested path vào bundle lịch sử thật. Dùng clone/canary temp thay thế; không để negative/mutant test có thể ghi evidence cũ hoặc gọi local DB khi guard hỏng. Dùng entrypoint fake dependencies/transport để đếm zero mutations, hoặc production guard thuần FS trên clone.

## Bằng chứng và giới hạn

Probe tại bank_receiver_heap_review_r2_evidence/; còn có các probe .tmp/bank_httpstatus_probe.cjs và .tmp/bank_owner_graph_probe.py. Targeted fixture suite sau Chunk A:14/15, delete_failure còn FAIL. Snapshot readonly:1.606 evidence tracked +87 app/backend files không đổi byte. Publication fault probe nay không còn raw bank number/name; RAW đăng ký trước mutation.

Chỉ sửa tooling/tests/docs. Codex tự kiểm sau bàn giao. Còn P1/P2 sau vòng2/2 thì dừng báo chủ dự án, không mở vòng3 hay đề nghị merge như thể task đã đạt. Runtime browser/heap/DB và full V2b/BH-07 vẫn NOT RUN/chưa nghiệm thu; không push/merge/deploy/pilot/BH-08.
