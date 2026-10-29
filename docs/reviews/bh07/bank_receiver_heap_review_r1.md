# Bank/receiver heap coverage — review đầu, giao sửa vòng 1/2

- Base: `94fd997674285f4bfe9e56a5ad8e70c06eb8d84b`; nhánh `feat/bh07-bank-receiver-heap`.
- Source được review là working diff chưa commit của Antigravity, model Gemini 3.8 Flash (High). Không có runtime bank/DB mới; các probe dùng fake transport hoặc clone evidence.
- Người triển khai thông báo cleanup/export còn chưa hoàn thiện khi lượt CLI hết thời gian. Codex không sửa implementation.
- Kết luận: **Chưa đạt**, còn BKR1–BKR7. Không chạy live fixture/runtime trước khi sửa các lỗi an toàn và kiểm chứng lại.

## Findings (toàn bộ gói sửa vòng 1/2)

### BKR1 — P1: làm hỏng cả runner mặc định

`scripts/bh07_appheap/run_app_profile_heap.js:738`: `main()` dùng `runOnly.title/id` ngoài scope của `resolveSentinels()`. Probe gọi main thật với môi trường/transport/FS giả trả `status=NOT RUN`, error `runOnly is not defined`. Dùng lại các trường `sentinels.expense2/expense_id_2`, thêm regression chạy main default với dependency fake. Không đổi luồng default đã được chốt.

### BKR2 — P1: nhận sở hữu và xóa nhầm sau POST lỗi

`run_app_profile_heap.js:363–371`,`:398–407`: catch POST nhận mọi hàng readback nonempty là hàng mình tạo, không đối chiếu ID/owner/nonce/payload. Probe production functions mô phỏng preflight trống, POST409 do hàng khác thắng collision, readback là dữ liệu khác; flags club/bank đều true rồi cleanup gửi DELETE cả bank/member/club. Phải phân biệt POST từ chối chắc chắn với mất phản hồi chưa rõ, xác minh đầy đủ dấu sở hữu do run tạo, giữ state theo từng thao tác, tuyệt đối không nhận hàng khác. Refusal phải dừng trước khi tiếp tục profile. Test phải chạy helper JS production với fake fetch.

### BKR3 — P1: profile không nối đủ vòng đời/UI/cleanup

`run_app_profile_heap.js:805` không truyền bank flag cho `runCycle`; `removeDisposableBank()` chỉ được định nghĩa, không được gọi trong finally; không xuất receipt bank vào cleanup hoặc tính vào `cleanup.ok`. Sau khi sửa BKR1, bank fixture có thể được tạo mà không nạp UI và không được dọn. Nối opt-in flag, actual Owner bank route, finally child-first cleanup, matched receipts, aggregate verdict và failure publication. Test cả lỗi giữa chừng, partial create và cleanup error qua orchestration thật.

### BKR4 — P1: fixture không khớp schema/Owner

`run_app_profile_heap.js:324–360`: lấy user_id của session player đầu tiên làm Owner; POST clubs dùng `created_by` thay `owner_user_id`, membership thiếu `display_name`, bank payload thêm `user_id` không thuộc club_bank_accounts. Schema kiểm chứng ở `supabase/migrations/20261015051808_init_schema_v1_1.sql:81–125`. Đọc Owner xác thực/Owner của CLUB_A làm anchor, dùng đúng schema hiện hành; không đoán từ roster, không sửa schema/app. Thêm transport controls xác minh đúng bảng, required columns, IDs và Owner.

### BKR5 — P1: bank contract vẫn fail-open khi bỏ bank ID/load

`heap_oracle.py:828`, `verify_evidence.py:607–648`: oracle chỉ bật contract khi bank_account_id còn trong owner scan; auditor kiểm danh sách tên contract/receipt nhưng không yêu cầu các key/load thực sự tồn tại. Clone evidence finance sạch, đặt coverage_profile=bank, contract1.0 đúng tên và receipt true/hash hợp lệ nhưng không có bank_account_id, bank/receiver không nạp ở Owner: real auditor CLI vẫn exit0. Phải bắt contract bắt buộc theo profile độc lập với chính key có thể bị bỏ, yêu cầu đủ metadata/scan/class/Owner-load/baseline/path của required set; thiếu bank metadata không được skip hash matching. Giữ legacy profile không-bank vẫn pass. Thêm full CLI mutants bỏ từng key/metadata/load/contract và mâu thuẫn receipt.

### BKR6 — P2: controls fixture kiểm bản sao Python, không kiểm code chạy thật

`tests/test_bh07_bank_heap_coverage.py:237–295` chỉ kiểm `DisposableClubBankFixture` trong module Python không được runner gọi; không chặn được BKR2/BKR4. 10 test mới và cả341 Python đều xanh dù main/fixture production hỏng. Dùng fake transport trên helper JS thực tế được runner import/export; không duy trì implementation fixture giả tách rời để test tự xanh. Bổ sung các controls đã cam kết trong spec: lost POST ack, POST reject/collision/race, parent/child partial creation, delete failure/absence, cleanup receipt và contract CLI.

### BKR7 — P2: profile mới có thể ghi đè evidence cũ

`run_app_profile_heap.js:22`,`:694`,`:1110–1116`: env override có thể trỏ OUT vào một bundle cũ; mkdir recursive/writeEvidence không có guard fresh output. Với --bank-coverage, phải từ chối output đã tồn tại/không thuộc run trước mọi fixture mutation và không ghi failure artifact vào chính thư mục bị từ chối. Test hash directory cũ trước/sau và assertion không có transport mutations. Không thay byte bundle cũ để xử lý guard.

## Kiểm chứng

- node --check: exit0 (syntax hợp lệ không chứng minh runtime đúng).
- Targeted bank tests:10/10; full Python341/341, vẫn có các lỗi semantic nêu trên.
- Probe main + race dùng production JS trong VM với fake FS/transport, không gọi API/DB: tái hiện BKR1/BKR2.
- Probe clone qua renderReport + hashes + verifier CLI: legacy positive0, mutant bank-without-required-ID/load vẫn0 sai kỳ vọng (BKR5).
- Bằng chứng/probe tại [bank_receiver_heap_review_r1_evidence/](bank_receiver_heap_review_r1_evidence/). Live bank runtime/DB giữ NOT RUN.

Giao Antigravity sửa đầy đủ BKR1–BKR7 vòng1/2, chỉ tooling/tests/docs. Không đổi model khỏi Gemini 3.8 Flash (High), không mở quyền, không sửa app/backend/schema, không push/merge/deploy/pilot/BH-08. Codex tự kiểm lại; còn lỗi sau hai vòng thì dừng báo chủ dự án.
