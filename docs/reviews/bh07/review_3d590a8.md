# Review BH-07D — 3d590a8

Ngày 21/10/2026 (Việt Nam). Nhánh `feat/bh07-integration`, base D `b0478a72021a726530c4051b52239a0a22d7fb96`, tested code `3d590a8418157cf91b00b9a5503d09be4df069f3`, docs/evidence và checkout tự chạy `ce4522da5dc6785a0487acd1ae19d3ff80014a0c`. Fetch trực tiếp ref nhánh, checkout ban đầu sạch; lib/test/migration của ce4522d trùng 3d590a8. Theo AGENTS, docs/ai/REVIEWER, docs/04/08/09/25 và handoff/summary/commands/evidence D. Xem diff main...HEAD, tách D bằng base..tested code: chỉ một file UI và một file test tích hợp mới. A giữ 4512c3a; B giữ d7bac04 (code a682007); C giữ 02a9b85.

## Phát hiện

Không có phát hiện P0/P1/P2 cần mở trong phạm vi D local được giao. Không sửa code, migration/RPC/model/repository/provider hoặc contract. Sửa UI chỉ thêm điều kiện lifecycle quanh nút chi phí; không đổi callback/gate các thao tác tài chính khác.

[Red log tác giả](integration_evidence/d_red_post_complete_add_expense.log) ghi đúng một FAIL khi expected không có bh06c-add-expense nhưng actual có một widget ở completed, exit1; source base có nút không điều kiện lifecycle. Source mới tại `lib/screens/session_finance_screen.dart:555` loại đúng completed/cancelled. Đối chiếu red bằng log/hash và diff, không gọi đó là lần reviewer tự chạy đỏ. Probe reviewer kiểm năm lifecycle và số outstanding server độc lập, kết quả bên dưới.

## Kiểm chứng độc lập

[Summary/hash](review_3d590a8_evidence/summary.json), [source hashes](review_3d590a8_evidence/source-hashes.json), [lệnh/exit Flutter](review_3d590a8_evidence/flutter-exits.json), [script](review_3d590a8_evidence/run_flutter.py), [scope](review_3d590a8_evidence/scope-code.txt), [diff check](review_3d590a8_evidence/diff-check.txt).

| Lệnh reviewer tự chạy trên cây mã ce4522d | Kết quả |
|---|---|
| `flutter analyze` | 0 issue, exit0 ([log](review_3d590a8_evidence/analyze.log)) |
| `flutter test` trước probe tạm | 240/240 PASS, exit0 ([log](review_3d590a8_evidence/flutter.log)) |
| `TZ=UTC flutter test test/integration/bh07_full_flow_test.dart` | 10/10 PASS, exit0 ([log](review_3d590a8_evidence/d_utc.log)) |
| Cùng D với `TZ=Asia/Ho_Chi_Minh` | 10/10 PASS, exit0 ([log](review_3d590a8_evidence/d_vietnam.log)) |
| Bốn file C theo yêu cầu, TZ=UTC | 50/50 PASS, exit0 ([log](review_3d590a8_evidence/c_utc.log)) |
| Cùng C với TZ=Asia/Ho_Chi_Minh | 50/50 PASS, exit0 ([log](review_3d590a8_evidence/c_vietnam.log)) |
| `BH02_TEST_CONTAINER=bh02-review-bh06 python3 docs/reviews/bh07/run_bh07_tests.py` | 23/23 PASS (21 clean +2 upgrade), exit0 ([log](review_3d590a8_evidence/bh07.log), [JSON](review_3d590a8_evidence/bh07_test_results_20261021050629.json)) |
| Sáu widget probe bổ sung reviewer | 6/6 PASS, exit0 ([source](review_3d590a8_evidence/review_bh07d_probe_test.dart.txt), [log](review_3d590a8_evidence/probes.log)) |
| `git diff --check b0478a7..3d590a8` | Không output lỗi, exit0 |

Flutter 3.47.7/Dart 3.13.5; PostgreSQL17 Docker network none, Auth stub + SET ROLE, DB giả cô lập do runner tự dựng. Không apply DB thật. Không cộng targeted/probe vào 240 test đầy đủ. Không chạy lại baseline 230 hoặc 335 hồi quy DB/BH-06 integration/upgrade; backend không đổi.

Rà cả mười test D và đường UI/provider liên quan: start→attendance→finalize→complete→detail/history refresh được thao tác trên màn/provider thật; free-current và còn outstanding được complete; stale/not-finalized không gọi complete; VERSION_CONFLICT không pop thành công, refresh lấy version mới; timeout giữ [version7,version7] và cùng request ID, pending disable và call count không tăng ngoài hai attempt; version conflict [7,8] có payload mới nên request ID mới, không phải replay cùng intent. Không có mô phỏng timeout sau server đã commit, không suy idempotency server từ UUID mock.

History D kiểm offset [0,2], dedupe overlap, reset offset khi đổi CLB, exact bounds UTC+7, detail-back giữ filter/refresh; tổng kết/copy kiểm management-only, finance, NULL “—”, aggregate outstanding và không contact/bank; participant/guest không có lối quản lý; logout/đổi actor dọn history. D không thay B/C, không tự tính outstanding từ due-paid. Ca sau complete thực sự bấm chốt lại, confirm/reject/reverse payment và reverse expense; cash trong ca đó **chỉ kiểm nút hiện**, chưa thực thi cash qua widget D. Không diễn giải coverage rộng hơn assertion.

Sáu probe reviewer bổ sung: draft/published/in_progress vẫn có nút thêm chi phí, completed/cancelled không có; mọi state giữ nút chốt phí và hiển thị outstanding server=60.000 dù charge=100.000/payment confirmed=50.000. Probe còn lại inject FORBIDDEN cho session thuộc CLB khác, kiểm client hiện lỗi và không có action quản lý. Probe này kiểm phản ứng với từ chối quyền, **không chứng minh server đã thực thi ACL chéo CLB**. Mười test D không phải bộ test ACL server. Các RPC/ACL local trong runner là PostgreSQL/Auth stub; HTTP/JWT/token ACL thật vẫn NOT RUN.

Test D dùng repository mock ở ranh giới client/RPC, không gọi FinanceRepository/SessionRepository thật qua HTTP. UI/provider thật không biến chúng thành test HTTP end-to-end. Test tạm của reviewer được chuyển sang .dart.txt sau chạy; source lib/test/migration trước/sau trùng hash và tested code. Không sửa triển khai.

## Bằng chứng và trạng thái worktree

[Kiểm hash tác giả](review_3d590a8_evidence/author-hash-check.json): đủ mọi path trong manifest; raw log/exit khớp nguyên bytes, DB JSON khớp sau tái dựng CRLF Windows. Exit files green đều0, red1; raw log đúng 240/10/10/50/50/23, analyze sạch. DB JSON tác giả ghi base_sha=3d590a8 và worktree_dirty=false, migration hashes khớp checkout. Điều này nhất quán với mốc code được bàn giao; không phải chứng thực độc lập trạng thái máy tác giả tại thời điểm lịch sử.

Reviewer tự chạy từ checkout sạch ce4522d, DB JSON mới ghi đúng full SHA ce4522d, worktree_dirty=false, 23 PASS/0 FAIL; UI/test/migration trùng 3d590a8. JSON và probe sinh sau có thể làm worktree bẩn trong giai đoạn gom bằng chứng, không thay kết quả checkout đầu lượt. Giữ nguyên evidence tác giả, kết luận dựa trên log reviewer mới. Diff ce4522d so với tested code chỉ docs/evidence; không có dependency/backend/contract đổi ngoài phạm vi.

## Kết luận

**Đạt** — BH-07D **tích hợp local** tại 3d590a8 trong phạm vi mười test D và sửa UI tối thiểu đã giao. Không có P0/P1/P2 mở. Đây không phải nghiệm thu toàn BH-07, rehearsal/pilot hoặc cho phép deploy. A/B/C giữ kết luận theo SHA trước; không merge main hoặc chuyển triển khai môi trường thật.

**NOT RUN:** HTTP/PostgREST/JWT/Supabase Auth thật, repository HTTP và ACL qua token thật; browser/mobile/thiết bị thực, offline/reopen/deep link; concurrency HTTP và timeout sau server commit; ngân hàng/VietQR/tải ảnh/webhook/chuyển tiền thật; staging/production/apply DB thật, backup/restore; rehearsal/pilot D/nghiệm thu toàn BH-07. Không chạy lại 335 hồi quy DB BH-02..06, BH-06 integration/upgrade hoặc baseline/red lịch sử. Không dùng mock/PostgreSQL/Auth stub để suy các cổng này PASS.
