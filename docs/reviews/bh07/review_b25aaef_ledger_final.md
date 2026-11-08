# Ledger supplemental repair — Đạt phạm vi sentinel Web local

2026-11-08. Owner giao rõ “codex tự sửa” sau điểm dừng vòng3. Codex sửa và tự chạy runtime; Code Reviewer riêng review source/artifacts và tự chạy auditor. **Không gọi runtime này là QA độc lập với implementer.** Tested source sạch `b25aaef1878b42e625c93d247b246237ba5cfd9b`, base `2167363`.

## Kết luận sửa lỗi

Đóng LGR9–LGR12 trong phạm vi tooling và phép đo này; không còn P0/P1/P2 chặn phạm vi sửa. LGR11: actual finally dùng helper đã test, lỗi enumeration giữ null/unverified và tiếp tục fixture cleanup; containment dùng `path.relative`. LGR12: thêm đúng ba scope tables theo [V8 tag15.6.75.27](https://raw.githubusercontent.com/v8/v8/15.6.75.27/src/profiler/heap-snapshot-generator.cc), kiểm layout/int/width/count/index và giữ unknown-key/graph gates. Legacy snapshots vẫn hợp lệ; scope IDs có dấu không bị cấm nhầm.

Codex chạy regression trước sửa: 2 test fail đúng lỗi EACCES và scope key; sau sửa 17 targeted PASS. Full **437 Python PASS**, exit0, 173.785s (`846b2bb04ddf15c1`); fixture8/8, node syntax và whitespace checks PASS. Full suite chạy trên working tree trước commit, không nhận clean-checkout replay. App/backend/schema/Dart tests/web/pubspec không đổi; giữ analyze0/247Flutter+1skip trước đó trên cùng app, không khai chạy Flutter mới. [Handoff](codex_ledger_supplemental_handoff.md) giữ timeline trước runtime.

## Runtime thực tế và audit

`node docs/reviews/bh07/ledger_tooling_review_evidence/runtime_review.cjs --name=ledger_heap_20261108_codex` **exit0**, child0/auditor0, archive `7df4026c62399be2`. [Bundle](ledger_heap_20261108_codex_evidence/report.md) RUN/PASS: build profile mới39artifact, served_match=true, Chrome156; hai chu kỳ Owner→logout→Cohost/Member, tám epochs, cùng document trong mỗi chu kỳ. `ledger_transaction_id` vắng/unreachable ở baseline, present/reachable trong Owner (path length18 cả hai chu kỳ), vắng/unreachable sau logout và actor switch. Bank-account, expense và payment ID gates cũng đạt. Không suy một UUID sentinel thành toàn bộ ClubLedger object đã giải phóng.

Wrapper độc lập với child kiểm sáu bảng `clubs`, `club_members`, `club_bank_accounts`, `session_expenses`, `payments`, `club_transactions`: count/full-row SHA256 trước/sau giống hệt, receipt ID hashes vắng sau cleanup. HEAD trước/sau trùng tested SHA; **1.974 protected tracked files không đổi**. Expense/payment/ledger/bank/club fixtures removed+verified_absent; raw snapshots0, dump/profile directories đã xóa. Detailed checker ở `build/ledger_heap_20261108_codex_independent_check.json`; [safe review results](codex_ledger_review_evidence/results.json) lưu metadata/hashes, không row data/credentials/raw dumps.

Reviewer riêng tự chạy real auditor exit0, xác nhận hashes/internal consistency và sentinel paths/cleanup/provenance. Đây là source/artifact review, không có lần browser/DB runtime thứ hai của reviewer. Bundle cũ giữ nguyên bytes; bundle mới có scoped `-text` attribute và script kiểm staged blobs theo manifest, không sửa payload sau runtime.

## Đính chính ngoài bundle và giới hạn

**Erratum cho report.md:207–208:** câu template kế thừa “Owner never loads” receiver không đúng với bank-coverage mode của lần này. Cả hai Owner record cho receiver present/reachable; baseline vắng, sau logout/actor còn retained và được báo unattributed residual risk. Bảng quan sát/path là bằng chứng thực; không dùng câu template để gọi receiver NOT LOADED hoặc sạch. Giữ nguyên bundle/hash, đính chính tại review này theo reviewer độc lập.

Rendered bank/receiver/expense titles/payment_ref vẫn là **unattributed residual risks**, không quy kết riêng engine hay app. Roster note không xác lập quyền actor. PaymentInstructions, listener graph/native chưa đo; whole-model/app-wide UNKNOWN. **Toàn V2b/BH-07/V8 chưa nghiệm thu**; chưa có owner risk acceptance và không có staging/mobile test. Không merge/push/deploy/pilot/BH-08. Quy tắc chung vẫn tối đa3 vòng; không suy ủy quyền bổ sung cụ thể thành quyền mở vòng vô hạn.
