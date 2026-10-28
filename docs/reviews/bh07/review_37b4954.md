# Review V2b retention attribution — 37b4954

- Ngày28/10/2026 Asia/Saigon. Reviewer Codex; không sửa triển khai/app/backend/DB.
- Base90e9d99b848f30fa3e3b2a3e643dbf784baaea9e; checkout **37b49540ea174acd2c93de4500dec7a5b95b5b75** (full SHA trong integrity.json), sạch trước review.
- Phạm vi: script/test/docs điều tra attribution và coverage. Runtime được đối chiếu vẫn sourceb13e468, không phải runtime mới của gói này.

## Kết luận

**Chưa đạt: 1 P1 và5 P2 còn mở.** Giữ Đạt runtime local hai expense-ID theo [review_3b393d3](review_3b393d3.md) và tooling RP3-C; không mở lại các gate trước. Không đóng toàn V2b/BH-07; residual rendered-title risk vẫn **unattributed**. Không merge/deploy/pilot/BH-08. Giao sửa vòng1/2 chỉ gói kiểm chứng/docs, không sửa app/backend.

## Phát hiện

### AT1 — P1: CLI vẫn kết luận app không giữ model khi control đã thất bại

- File:dòng: `scripts/bh07_appheap/audit_retention_attribution.py:343–366`, `:446`; tests `test_bh07_retention_attribution.py:44`.
- Tái hiện: `python docs/reviews/bh07/review_37b4954_evidence/probes.py`.
- Positive gốc exit0. Ba mutant đều **exit0** và `app_model_retention=false`, `primary_retainer_component=Flutter Web Engine`: (a) peer expense-ID còn present/reachable sau logout (`peer_sentinel_proof_valid=false`); (b) SDK sai/build debug (`environment.consistent=false`); (c) bỏ paths rendered (`path_leads_to_segmentationCache=false`).
- Kỳ vọng: đầu vào thiếu/sai precondition phải FAIL/UNKNOWN và exit khác0, không khẳng định app sạch hoặc engine là nguyên nhân; positive đầy đủ vẫn chạy.
- Cách sửa: derive kết luận vàexit từ validated evidence; chặn thiếu mốc/path/metadata/environment/peer, không gán cố định false/true. Test phải assert cả artifact verdict vàCLI exit, không chỉ assert peer flag đã false. Giữ positive/ba mutant nguyên kỳ vọng.

### AT2 — P2: Phân định dứt khoát và suy rộng app/native vượt bằng chứng

- File:dòng: `docs/reviews/bh07/retention_attribution_report.md:130–145`; `retention_attribution_handoff.md:20–21`; script `:354–365`.
- Tái hiện: đối chiếu các claim này với QA summary chỉ xuất bản một path cho mỗi sentinel,hai expense-ID,không raw object graph; bundle mới không có exact SDK source extract/hash/callsite audit.
- Thực tế: tuyên bố app giải phóng toàn bộ model/widget,không leak controller,nguyên nhân chỉ engine và hiện tượng không tồn tại native. ID mất không loại được app giữ riêng string/copy/khác object, cũng không chứng minh không có path app khác tới cùng title. Tên segmentationCache phù hợp giả thuyết, không đủ chứng minh source mapping/exhaustiveness hoặc heap native sạch.
- Cách sửa: tách observed/supported hypothesis/unknown; giữ unattributed cho phần chưa chứng minh, không nhận acceptance là PASS. Nếu muốn attribution mạnh hơn phải cung cấp source/hash đúng engine/build và control/path evidence phù hợp; không bắt buộc thêm runtime để chỉ đính chính claim. Dart VM tiếp tục NOT RUN; cập nhật đồng bộ JSON/report/handoff/map.

### AT3 — P2: Coverage map dùng field không tồn tại và nhận listener heap đã sạch

- File:dòng: `docs/reviews/bh07/v2b_coverage_map.md:27–36`, `:43`, `:50`; `scripts/bh07_appheap/audit_retention_attribution.py:155–166`.
- Tái hiện: đọc `lib/models/finance.dart:34`,`:258`,`:279`,`:98` và so map.
- Thực tế: FinanceCharge chỉ có playerId/displayName/amountDueVnd, không notes/status/chargeVnd/chargeId; FinancePayment dùng reference, không referenceCode/displayName; PaymentInstructions dùng receiverSnapshot/accountName/reference, không accountHolder/bankAccount/transferContent/vietqrUrl như map. Những sentinel đề xuất vì thế không thể đi qua DTO hiện hành. Dòng listener “đã xác minh sạch/hoàn thành” suy từ AST/generation, không đo object/listener heap; summary aggregate cũng nêu field sai.
- Cách sửa: map đúng field/DTO/provider/UI hiện hành, ghi chứng cứ từng mức (source/Provider/Web heap); listener/object graph chưa đo phải NOT RUN, không coi AST zero-static là full retention proof. Giữ fixture theo contract, không đổi app/backend để khớp map. Test coverage kiểm tên field thực thay vì chỉ count danh sách hardcode.

### AT4 — P2: Bundle thiếu log đã khai manifest

- File:dòng: `docs/reviews/bh07/retention_attribution_evidence/hashes.sha256:4`; handoff `:30`.
- Tái hiện: `python scripts/bh07_browser/clean_and_manifest.py --verify --evidence-dir docs/reviews/bh07/retention_attribution_evidence`.
- Thực tế exit1 `MISSING FILE: run.log`; chỉ4/5 payload có trên Git. Claim5/5 trong bàn giao không tái lập được từ checkout sạch.
- Cách sửa: force-add log gốc đúng hash nếu còn; nếu mất, công bố mất và chạy lại ghi log thật, không chế tạo log hay retag runtime cũ. Verify manifest/staged Git blobs trên checkout sạch và lưu exit trung thực. Không sửa manifest lịch sử.

### AT5 — P2: Link source trỏ máy riêng, không dùng được với reviewer khác

- File:dòng: `docs/reviews/bh07/retention_attribution_handoff.md:26–27`; `v2b_coverage_map.md:19` và nhiều dòng; report `:108`.
- Tái hiện: tìm `file:///c:/Users/POTA` trong ba tài liệu mới; đường dẫn không nằm trong repo reviewer Linux, không định vị commit.
- Cách sửa: dùng link Markdown tương đối tới repo hoặc permalink GitHub đúng source SHA; kiểm tất cả link/file/line từ checkout sạch, không dựa vào thư mục cá nhân.

### AT6 — P2: Xuất bản lại sentinel thô trái phạm vi sanitize

- File:dòng: `docs/reviews/bh07/retention_attribution_report.md:57–58`.
- Tái hiện: đọc danh sách giá trị expense/expense2 ngay dưới bảng8 residual risk; report in nguyên seed expense-title và tiền tố title fixture.
- Kỳ vọng: giữ name/hash/length/class/path đã sanitize, không xuất bản giá trị sentinel thô hoặc prefix trong hồ sơ mới.
- Cách sửa: thay giá trị bằng identifier/sha12/length, quét cả Markdown ngoài evidence. Đây là vi phạm phạm vi sanitize, **không** khẳng định có credential/JWT thật bị lộ; seed title đã có trong fixture không phải bí mật production.

## Reviewer tự chạy

Evidence: [review_37b4954_evidence/](review_37b4954_evidence/); probes giữ nguyên source triển khai và QA bundle. Python discover316/316, analyze0 issue, Flutter247+1skip; numeric exit/log được lưu trực tiếp. Suite xanh không phủ các false-conclusion controls AT1. CLI attribution phát lại4 ca bằng output temp riêng, không ghi đè bundle tác giả. Manifest tác giả exit1 có chủ ý ghi nhận AT4,không gọi là PASS. Bốn bundle lịch sử không đổi byte; payload có mặt khớp hash. Diff chỉ scripts/tests/docs được giao, app/backend không đổi; whitespace sạch. Không dùng log tác giả thay kết quả reviewer.

## NOT RUN

- Runtime browser/heap/SQL mới và exact-engine build attribution thực nghiệm mới của reviewer: NOT RUN. Lượt này audit sanitized QA,không raw heap parse.
- Full coverage V2b,charge/payment/bank thật/receiver/ledger/listener/object graph và tất cả retainer paths: NOT RUN; chỉ hai expense-ID runtime local đã đạt.
- Native Dart VM desktop/mobile,browser khác,mobile web/đa tab/concurrent actor/tải thật: NOT RUN.
- Managed backup/PITR/offsite/encryption/retention/concurrent writers,staging/production/restore thật,banking/webhook,rehearsal/pilot/full BH-07: NOT RUN.

V1,V5b,Provider/tooling và QA runtime trước giữ kết luận local. Người triển khai sửa đầy đủ AT1–AT6 bằng control tái hiện trước; không tự ghi Đạt,không chuyển gate/merge/deploy.
