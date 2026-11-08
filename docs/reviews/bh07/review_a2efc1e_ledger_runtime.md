# Ledger runtime — chưa đạt, dừng sau hai vòng sửa

2026-11-08. Tested source `a2efc1e5d553d32cf4bb039123681c8b7a9665df`, Git sạch; implementation code `205dcd53cd42514cc26cbbd1cb72f76afe38f364`. Codex tự chạy reviewer wrapper từ project root, không dùng runtime tác giả thay kết quả độc lập.

## Kết quả thực tế

`node build/ledger_runtime_review.cjs` exit 1, archive `fa3783d040e4a7a7`. Child exit 1, auditor exit 1. [Bundle nguyên bản](ledger_heap_20261108_r1_evidence/report.md) ghi **NOT RUN**, không có verdict và **0 chu kỳ**. Profile build mới có 39 artifact, served_match=true; baseline snapshot được tạo nhưng lệnh Python `heap_oracle.py scan --paths` trả nonzero trước Owner login. Không có quan sát ledger release hoặc leak từ lần chạy này.

Bundle không giữ stdout/stderr của scan con; reviewer wrapper chỉ giữ byte count/hash của output child. Vì vậy **nguyên nhân scan chưa xác định**, không kết luận MemoryError, lỗi Chrome hay lỗi oracle từ thông báo `Command failed` chung. Không sửa source hoặc chạy lại để thay thế bằng chứng lỗi.

Reviewer chạy thêm auditor trực tiếp: exit 1, phát hiện thiếu verdict, status NOT RUN, thiếu hai chu kỳ và cleanup contract không đầy đủ. Đây là fail-closed đúng; không coi 420 test xanh là runtime PASS.

## Xác minh độc lập sau chạy

Wrapper đã đối chiếu count và SHA-256 toàn bộ rows của `clubs`, `club_members`, `club_bank_accounts`, `session_expenses`, `payments`, `club_transactions`: **sáu bảng giống hệt trước/sau**, ID hash của club/bank/ledger fixture không còn trong bảng. Không công bố dữ liệu row hoặc credentials.

HEAD trước/sau giống tested SHA; **1.961 tracked protected files không đổi**. Temp dump và Chrome profile theo PID child đều không còn. Cleanup receipts ghi expense/payment/ledger/bank/club created + removed + verified_absent=true. Tuy nhiên `cleanup.ok=false`: abort xảy ra trước khi runner điền `dump_dir_outside_repo` và `raw_snapshots_remaining`; xác minh vật lý độc lập không được dùng để sửa bundle gốc thành PASS.

Safe wrapper output: child bytes 2110, SHA-256 `23a7505a3b95ce5f184f390bc9e47f534ba0124b279b71a69ea107f863ddad47`; auditor bytes 371, SHA-256 `063c04805673a25d8a2f07a909ed194cbd41b4b3dc8f3908226ae5d0a0620456`. Local detailed checker: `build/ledger_heap_20261108_r1_independent_check.json` (ignored, contains hashes/counts only).

## Phát hiện review độc lập

- **LGR9 P2 — diagnostic gap**, `scripts/bh07_appheap/run_app_profile_heap.js:714`: scan nonzero chỉ còn thông báo command chung trong bundle; stdout/stderr đã mất. Vòng được owner cho phép sau này cần giữ chẩn đoán đã redact và control lỗi CLI, không công bố sentinel/raw snapshot.
- **LGR10 P2 — cleanup reporting**, `scripts/bh07_appheap/run_app_profile_heap.js:1077`: đường abort không điền đủ metadata cleanup vật lý, tạo `cleanup.ok=false` dù dump/profile được dọn. Cần kiểm tra cleanup từ finally và test đường abort, giữ fail-closed nếu không xác minh được.

Code Reviewer riêng đọc bundle và checker, xác nhận hai P2 trên và nguyên nhân scan UNKNOWN; không sửa code/chạy lại. LGR1–LGR8 giữ kết luận tooling trước đó; còn hai phát hiện mới này nên runtime/package hiện hành chưa được nghiệm thu.

## Quyết định

Tooling acceptance tại `205dcd5` là kết luận trước runtime; lần kiểm chứng thực tế này **chưa đạt**. Ledger coverage vẫn NOT RUN; V2b/BH-07/V8 chưa nghiệm thu. Các kết quả runtime lịch sử không đổi và không được retag sang source mới.

Theo [AGENTS.md](../../../AGENTS.md), “Còn lỗi sau 2 vòng thì dừng và báo chủ dự án.” Hai vòng sửa source đã dùng hết. Dừng sửa production/tooling, chờ owner cho phép vòng chẩn đoán/sửa bổ sung có phạm vi cụ thể; không merge/push/deploy/pilot/BH-08. Quyết định rủi ro vận hành đang chờ không thể thay thế lỗi runtime này.
