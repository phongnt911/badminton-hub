# Review V2b finance heap coverage — 6f59f5e

- Ngày28/10/2026 Asia/Saigon; reviewer Codex, không sửa source triển khai/app/backend/DB.
- Base: `56ffbf9a4f1b524cd8fbc7f1e9118a94b06b9cbc`.
- Checkout docs/evidence: `6f59f5e9fb9a8280a46c70aa9ca237b81fb8a023`, sạch trước kiểm chứng.
- **Runtime source thực:** `cd25e1e3557e2013e8991b2031a240818ee84c96`, cùng source tree với docs tip. SHA dài cd25e1ea… trong yêu cầu/handoff không tồn tại, chi tiết FH3.
- Phạm vi: mở rộng charges/payments Web profile local. Giữ các kết luận tooling/QA local trước đó;Codex từng sửa AT1 attribution lịch sử nhưng không viết/sửa code mở rộng cd25e1e. Lượt này tự chạy controls/suites/auditors,không có runtime browser/heap mới.

## Kết luận

**Chưa đạt: FH1 P1 và FH2–FH4 P2 còn mở; không có P0.** Giao sửa vòng1/2 chỉ script/test/fixture/docs/evidence. Không sửa app/backend/contract,không nới gate cũ. Không tự merge main/staging/production,deploy/pilot/BH-08;toàn V2b/BH-07 chưa nghiệm thu.

Giữ Đạt tooling AT1–AT6/RP3-C,Provider,V1,V5b vàQA runtime hai expense-ID b13e468. Gói mới chưa được chốt Đạt không phủ nhận quan sát payment trong bundle hiện tại:8snapshot/2chu kỳ có payment_id khi Owner active và0occurrences/unreachable sau logout/đổi actor;payment_ref còn path12,official risk unattributed. Những quan sát của tác giả này không phải phép đo mới do reviewer thực hiện hoặc proof toàn FinanceCharge/FinancePayment object graph sạch.

## Phát hiện

### FH1 — P1: Payment không được nạp vẫn được nhận PASS coverage

- File:dòng: `scripts/bh07_appheap/run_app_profile_heap.js:615–619`; `scripts/bh07_appheap/verify_evidence.py:180–186`,`:275`; liên quan generic `heap_oracle.py:232–259` và `tests/test_bh07_finance_heap_coverage.py:189–199`.
- Tái hiện: `python docs/reviews/bh07/review_6f59f5e_evidence/probes.py`, case `payment_never_loaded`.
- Input clone: payment_id/payment_ref đều absent/count0/unreachable ở mọi mốc;giữ2expense IDs,probe,DTO metadata và cleanup. Derive lại verdict bằng oracle thật,render lại report vàhash clone để mô phỏng đúng runner thiếu payment coverage,không chỉ làm hỏng manifest.
- Thực tế: oracle không đưa payment_id vào owner gate,2expense IDs vẫn thỏa minimum2;summary PASS vàauditor **exit0**. Test “payment_id never loaded…fails precondition” hiện chỉ assertNotIn(payment_id,expectations),không assertFAIL/NOT_RUN/exit. Negative control đó không chặn xanh giả.
- Kỳ vọng: profile mở rộng payment chỉ được PASS khi payment_id thực được nạp ở Owner vàphân biệt với baseline;thiếu precondition phải FAIL/NOT RUN cho coverage payment,không PASS dựa vào expense IDs. Positive hiện có phải vẫn qua;legacy profile không khai payment tiếp tục được audit đúng phạm vi cũ.
- Cách sửa: xác định coverage contract/capability bắt buộc cho profile mới vàkiểm ở runner lẫn auditor;không chỉ suy tập gate từ những gì tình cờ loaded. Thêm test realCLI cho missing owner/baseline không phân biệt vàpositive;assertverdict/coverage/exit nhất quán. Không áp payment requirement vô điều kiện làm hỏng audit legacy hoặc nới minimum cũ.

### FH2 — P2: Có thể bỏ qua cleanup payment hoặc chứng nhận nhầm ID

- File:dòng: `scripts/bh07_appheap/verify_evidence.py:570–582`.
- Tái hiện cùng probes.py:
  - `payment_receipt_removed`: xóa tất cả payment cleanup fields,giữ payment sentinel/coverage→auditor exit0.
  - `payment_created_flag_missing`: xóa riêng run_only_payment_created,đặtremoved=false/verified_absent=false vàerror→auditor exit0,do toàn khối kiểm bị skip.
  - `payment_receipt_hash_wrong`: sha12receipt không khớp payment_id metadata→auditor exit0,chỉ kiểm regex12hex.
  - Negative control `payment_cleanup_false_control` giữ created flag vàremoved=false→exit1;positive→exit0. Không phải mọi input đều bị nhận hoặc bị bác.
- Kỳ vọng: bundle khai coverage/payment fixture phải có đủ receipt,không error,created/removed/absence true vàID receipt khớp sentinel được gate. Không được tự exempt bằng việc xóa cờ chứng minh ownership.
- Cách sửa: yêu cầu receipt theo measurement profile/sentinel khai báo thay vì sự tồn tại của chính cờ run_only_payment_created;match sha12 với payment_id. Giữ legacy không có payment vẫn qua. Test đủ omission/false/error/hash mismatch trên verifier hoàn chỉnh,cảJSON vàMarkdown nhất quán.
- Không khẳng định fixture thật còn trong DB;receipt gốc hiện tại khớp metadata. Lỗi là verifier vẫn chứng nhận một receipt thiếu/sai hoặc báo cleanup error.

### FH3 — P2: SHA tested-source bàn giao không resolve

- File:dòng: `docs/reviews/bh07/finance_heap_handoff.md:5`, `AGENTS.md:1`.
- Tái hiện: `git cat-file -e cd25e1ea1f93e9a7eecdb8da951a37c56bf0a624^{commit}` thất bại. `git rev-parse cd25e1e` trả **cd25e1e3557e2013e8991b2031a240818ee84c96**;SHA này là parent thực vànằm trong finance_heap_evidence/summary.json,report.md.
- Kỳ vọng: commit source có thể checkout,khớp runtime provenance;phân biệt source/code với docs tip6f59f5e.
- Cách sửa: đính chính metadata bàn giao/trạng thái/prompt thành SHA thực,ghi rõ lỗi SHA đã phát hiện. Không sửa/gán lại evidence cũ hoặc giả mạo provenance;nếu có chạy mới phải công bố source mới/dirty thực.

### FH4 — P2: Suy từ payment-ID absent sang cả model đã giải phóng

- File:dòng: `docs/reviews/bh07/finance_heap_handoff.md:17`.
- Tái hiện: đối chiếu claim “Model FinancePayment được giải phóng sạch sẽ khỏi bộ nhớ Dart” với summary chỉ đo các string sentinel/path V8. Path owner payment_id thực dài21 ởcycle1 và20 ởcycle2,không phải20 ởcảhai như câu tóm tắt.
- Kỳ vọng: chỉ kết luận absence của payment-ID fixture trong snapshot V8 đã đo;model/object graph,app-wide/native retention chưa được chứng minh phải giữ UNKNOWN/NOT RUN. Một path/ID không loại được retained copy/string/object khác. Không suy từ roster playerId thành charge leak hoặc charge model sạch.
- Cách sửa: thu hẹp claim đúng sentinel/phép đo,ghi chính xác21/20 hoặc không hardcode độ dài trong tóm tắt;giữ payment_ref unattributed,không gọi V8 measurement là native Dart VM proof. Không cần sửa app/backend để đính chính claim.

## Reviewer tự chạy

Evidence riêng: [review_6f59f5e_evidence/](review_6f59f5e_evidence/),lệnh/exits ở [commands.md](review_6f59f5e_evidence/commands.md) vàexits.json.

| Lệnh | Kết quả mới của reviewer |
| --- | --- |
| verify_evidence.py --dir docs/reviews/bh07/finance_heap_evidence | exit0 trên bundle gốc |
| node scripts/bh07_appheap/fixture_controls.js | exit0,8/8 controls |
| Python unittest discover | exit0,325/325 |
| flutter analyze | exit0,no issues |
| flutter test | exit0,247pass+1skip |
| verify_evidence.py --dir docs/reviews/bh07/review_runtime_b13e468_evidence | exit0 |
| Reviewer semantic probes | positive0,cleanup-false1 đúng;missing payment/receipt/flag/wrong receipt ID đều0 sai kỳ vọng |

DTO FinanceCharge chỉ playerId/displayName/amountDueVnd;identity roster không phải finance sentinel. Phép đo này chưa chứng minh charge object graph hoặc quyền Cohost bằng heap. Metadata payment nguyên bản có mặt ởOwner,0sau logout;payment_ref retainedunattributed12risk tổng gồm expense/ref. Receipt gốc payment sha852eec161334 khớp metadata. Đây là đối chiếu bundle tác giả,không freshSQL.

Manifest5bundle(currentfinance +4legacy),mỗi3payload khớp Git/manifest,strict UTF-8 LF,secret scan0,readonly hash trước/sau không đổi. Không có rawheap file tracked;oldbundle bytes giữ nguyên. Source cd25e1e..docs tip không đổi code,base..HEAD không đổi lib/test/supabase. Reviewer không sửa source hoặc bundle gốc;clone control tự xóa khi xong. Giữ các gate đã chốt,không lấy generic auditor PASS thay full payment-profile coverage.

## NOT RUN

- Runtime Chromium/heap dump mới hoặc query DB xác nhận fixture vắng của reviewer: NOT RUN. Cleanup thật chỉ được đối chiếu từ receipt/log tác giả,không suy thành lần DB check mới.
- Full FinanceCharge/FinancePayment model retention/app-wide,exhaustive paths vàlistener Web object graph: NOT RUN;ranh giới DTO/roster không phải proof charge sạch.
- Bank/receiver/ledger/payment instructions,summary aggregate object graph vàcác finance fields ngoài sentinel đã đo: NOT RUN.
- Dart VM desktop/mobile,browser khác,mobile web/đa tab/concurrent actor/tải thật: NOT RUN.
- Managed Supabase backup/PITR/offsite/encryption/retention,concurrent writers,staging/production/restore thật,banking/webhook,rehearsal/pilot/nghiệm thu toàn BH-07: NOT RUN.

**Chưa đạt gói mở rộng local trong phạm vi source thực cd25e1e3557e2013e8991b2031a240818ee84c96 vàdocs6f59f5e.** Không kết luận appleak thật;đề nghị người triển khai sửa đầy đủ FH1–FH4 vòng1/2 với test tái hiện,giữ positive vàlegacy controls.
