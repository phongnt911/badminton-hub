# Review V2b — ccad24c

## Kết luận

**Chưa đạt cổng V2b**. Còn **1 P1 và 4 P2** bên dưới; chưa xác định lỗi app/retention thực tế. Các tests mới có giá trị trong phạm vi Provider/Dart VM harness nhưng không đủ chứng minh heap ứng dụng profile sạch. Phần đo heap ứng dụng thật vẫn **NOT RUN**.

- Ngày: 25/10/2026 (Asia/Saigon).
- Tested source: `ccad24cf67eabb5c17de285792fe96bca21714aa`; base `aca3f08a80d359ad1a69c444f428c6b8f5142cc8`.
- Docs/evidence origin thực tế: **`eb4362bcec70e0922204b6a1040b02cbdb0f0924`**. SHA dài `eb4362b083832ffc9fe6d3be9f67a21394a17ef0` trong yêu cầu không tồn tại; fetch trực tiếp nhánh và đối chiếu tested source/parent, không giả định SHA sai là SHA thật.
- Codex không viết/sửa gói heap này. Lượt này chỉ review, thêm report/evidence/trạng thái; không sửa code, app/backend/contract hay bundle tác giả. V1/V5b giữ Đạt local.

## Phát hiện

### HP1 — P1: Provider harness bị mô tả thành heap của toàn application instance

- File:dòng: `test/integration/bh07_heap_verification_test.dart:23`, `test/integration/bh07_heap_verification_test.dart:279`; `docs/reviews/bh07/private_heap_handoff.md:30`.
- Tái hiện: chạy heap suite; đối chiếu setup/import và mục4.4 readiness. Auth là `FakeAuth implements AuthProvider`; ba repository là mock; setup chỉ tạo Finance/Session/ClubProvider, không tạo AuthProvider thật, app/widget tree, SupabaseClient/repositories thật hay phiên ứng dụng profile.
- Kỳ vọng: V2b đo retained objects/paths trong cùng app profile qua baseline→Owner active→logout→Cohost/Member; có oracle phát hiện retained copy ngoài các DTO được theo dõi. Thiếu môi trường thì giữ NOT RUN.
- Thực tế: 7/7 PASS chỉ kiểm các WeakReference tới một số root DTO trong VM test harness. `target == null` chứng minh target đó đã bị GC clear, không chứng minh mọi bản sao field/string, widget state, repository cache, auth/client/listener graph đã sạch hoặc RAM đã bị xóa. Handoff nói toàn cây AuthProvider/app instance nhưng Auth là fake; không có Finalizer instance dù metadata nói dùng Finalizer. Allocation pressure không tự chứng minh đã thực hiện đầy đủ generational GC/retention-path enumeration.
- Cách sửa: giữ harness như bằng chứng unit/provider bổ trợ, sửa các claim RAM/app/Finalizer thành đúng phạm vi. Muốn đóng V2b cần app Web/Desktop/Mobile profile thật, phép đo snapshot/VM-service/retained paths tại các mốc và canary/copy-leak controls có oracle lặp lại được; sanitize, xóa raw dumps. Nếu chưa có công cụ, ghi phần đó NOT RUN, không biến provider test thành PASS toàn cổng. Không yêu cầu sửa app ngoài phạm vi.

### HP2 — P2: “AST audit” dùng regex, bỏ sót leak patterns và dispose scope

- File:dòng: `scripts/bh07_heap/audit_ast_memory.py:26`, `scripts/bh07_heap/audit_ast_memory.py:79`, `scripts/bh07_heap/audit_ast_memory.py:85`.
- Tái hiện: `python docs/reviews/bh07/review_ccad24c_evidence/probes.py`, phần static/subscription controls.
- Kỳ vọng: audit được quảng bá global/static/subscription phải phát hiện các trường hợp này hoặc báo không đủ phạm vi; không kết luận LeakRisk NONE chỉ từ keyword.
- Thực tế: positive `static List<Object> leak = <Object>[]` bị bắt, nhưng `static final leak = List<Object>.empty(growable:true)` và top-level `final leak = <Object>[]` trả0 issues. `StreamSubscription<int>? _sub` không cancel vẫn được báo tracked0/LeakRisk NONE; trong app thật `_authSubscription` cũng là nullable nên audit gốc báo tracked0 dù có subscription (app hiện có cancel, không kết luận app leak). Đặt removeListener trong hàm không gọi, ngoài dispose, vẫn được công nhận remove-on-dispose vì chỉ tìm text toàn file. Đây không phải phân tích AST/retention paths.
- Cách sửa: dùng parser/analysis phù hợp hoặc thu hẹp rõ thành heuristic; không tự suy “0 mutable/global/un-cancelled” từ các pattern không bao phủ. Có control cho inferred/constructor/global/nullable, multiline và remove/cancel ngoài dispose; missing provider/không phân tích được phải là UNKNOWN/FAIL, không tự xanh. Giữ positive control phân biệt typed field với static method.

### HP3 — P2: Summary/report hardcode PASS cả khi test và audit thất bại

- File:dòng: `scripts/bh07_heap/run_heap_verification.py:97`, `scripts/bh07_heap/run_heap_verification.py:104`, `scripts/bh07_heap/run_heap_verification.py:108`.
- Tái hiện: probes.py gọi nguyên `generate_summary(..., ast_ok=False, test_ok=False, test_output='synthetic failed test')` với output temp.
- Kỳ vọng: counts/control/verdict/report được lấy từ kết quả thực, failed hoặc chưa chạy không được ghi PASS.
- Thực tế: suite verdict là FAIL nhưng cả10 controls vẫn PASS; ast count luôn0, disposal luôntrue; Markdown vẫn claim7/7 PASS. `test_output` không được dùng để tính counts/controls. Exit1 cuối orchestrator không sửa mâu thuẫn trong artifact mà auditor đọc.
- Cách sửa: đọc structured test events/actual audit JSON; đối chiếu test identities/count/exit. Failed/not-run phải giữ FAIL/NOT RUN/UNKNOWN đúng control; không in success template vô điều kiện. Chỉ claim sanitized sau scan. Ghi dirty paths/source hashes hoặc clean source checkout để ràng buộc provenance; bundle tác giả hiện git_dirty=true nhưng không ghi paths, không tự đổi thành false.

### HP4 — P2: Bundle Git chỉ có3/4 entries, thiếu log gốc

- File:dòng: `docs/reviews/bh07/private_heap_evidence/hashes.sha256:2`; `docs/reviews/bh07/private_heap_handoff.md` mục4.
- Tái hiện: `python scripts/bh07_heap/clean_and_manifest.py --verify` từ checkout docs tip.
- Kỳ vọng: manifest4/4, raw heap_test_run.log được track và hash khớp.
- Thực tế: **exit1 — MISSING file: heap_test_run.log**; ba file hiện có khớp hash, không có log để audit lần chạy tác giả. Reviewer tự chạy mới7/7 nhưng log mới không phải log tác giả và không được dùng để điền manifest lịch sử.
- Cách sửa: force-add đúng raw log có hash đã công bố nếu tác giả còn giữ; nếu không, chạy source sạch tạo bundle mới, công bố provenance/count/exit/log mới. Không chế tạo log hoặc sửa hash cũ để che thiếu hụt. Verify từ checkout Git sạch sau commit.

### HP5 — P2: Strict verifier chấp nhận manifest CRLF

- File:dòng: `scripts/bh07_heap/clean_and_manifest.py:119`.
- Tái hiện: probes.py tạo synthetic complete bundle LF (positive exit0), chỉ đổi manifest sang CRLF rồi chạy nguyên verifier `--verify --dir <temp>`.
- Kỳ vọng: strict UTF-8 LF kiểm cả manifest, exit khác0 nếu CRLF/BOM/malformed entry; read-only không sửa file.
- Thực tế: **manifest CRLF vẫn exit0** vì open text universal-newline và `.strip()` xóa dấu vết CR; vòng kiểm text chỉ áp dụng .log/.json/.md/.txt, không kiểm bytes hashes.sha256. Hash mismatch/missing/extra controls trả exit1 đúng; tất cả case read-only. Không kết luận bundle tác giả đang có CRLF: đây là lỗ hổng verifier được negative control tái hiện độc lập với lỗi missing log HP4.
- Cách sửa: đọc manifest bytes, kiểm BOM/CR/UTF-8 trước parse; validate format hash/path/duplicates và không bỏ qua malformed lines. Positive LF PASS, CRLF/BOM/invalid UTF8/invalid entry FAIL, so hash trước/sau. Có thể tái dùng verifier chuẩn đã có thay vì duy trì hai bộ lệch nhau.

## Bằng chứng reviewer tự chạy

Evidence riêng: [review_ccad24c_evidence/](review_ccad24c_evidence/).

| Kiểm tra | Kết quả |
|---|---|
| Checkout | Detached origin docs thực tế sạch trước test; tree runtime sau tested source không đổi; lib/supabase diff rỗng từ base. |
| Heap suite | `flutter test --no-pub test/integration/bh07_heap_verification_test.dart`: **exit0,7/7 PASS** |
| Analyze | `flutter analyze --no-pub`: **exit0,0 issue** |
| Toàn Flutter | `flutter test --no-pub`: **exit0,247 PASS+1 skip**; skip là HTTP integration chưa bật |
| Audit script | Chạy nguyên CLI trên bản copy disposable của script và38 file lib để không ghi đè bundle; **exit0**, report byte-identical bản tác giả. Kết quả CLEAN có giới hạn HP2. |
| Independent probes | Exit0 của probe orchestration, output công bố false negatives HP2/HP3/HP5; không gọi false-green là gate PASS. |
| Bundle author verify | **Exit1**,3/4 hash hiện có khớp, thiếu heap_test_run.log; readonly toàn thư mục trước/sau bằng nhau. |
| Verifier controls synthetic | LF exit0; CRLF exit0 sai; mismatch/missing/extra exit1; mọi case readonly. |

Flutter reviewer Linux3.47.7, khác tác giả Windows3.47.6. Dùng --no-pub để chạy dependencies đã có; cho test harness quyền bind loopback local, không dựng backend thật. Reviewer logs chuẩn hóa UTF-8 LF. Các file tác giả hiện có được audit strict UTF-8 LF và không thấy secret theo scanner; không thể quét log không có. Không chạy --generate hay full orchestrator vào bundle tác giả; summary failure probe và audit CLI chỉ ghi temp rồi xóa.

## NOT RUN

- App Web/Desktop/Mobile profile thật; baseline/Owner/post-actor heap snapshots hoặc retained-path analysis/GC event evidence; đo cache/widget/Auth/client graph ngoài Provider harness. Không thay bằng UI/copy sạch hay weak root DTO trong mock test.
- Finalizer callbacks: không có implementation sử dụng Finalizer trong suite bàn giao.
- Nội dung log heap gốc bị thiếu; provenance dirty paths và byte-exact code trong lượt tác giả không thể khẳng định chỉ từ git_dirty=true.
- HTTP/JWT/Auth thật trong lượt heap này; unit fake Auth/repository không thay bằng chứng V1/HTTP đã nghiệm thu trước.
- Full orchestrator tạo lại bundle tác giả (tùy chọn) không chạy để bảo toàn evidence; đã replay các thành phần và failure probes riêng.
- DB hồi quy mới không chạy: không đổi migration/RPC/backend. V2 device/browser khác/offline/deep link; V3 managed backup/PITR/offsite/encryption/retention; V4 concurrent writers; V5 staging/production restore/deploy; V6 banking/webhook; V7 tải/pilot; V8 toàn BH-07 giữ NOT RUN.

## Bước tiếp

Giao AI thực thi sửa HP1–HP5 theo phạm vi kiểm chứng; giữ harness hữu ích, không sửa app/backend để làm xanh. Bổ sung red/green controls, machine-readable evidence và phương pháp đo app thật hoặc giữ app-heap NOT RUN trung thực. Tối đa hai vòng sửa theo AGENTS; không tự mở thêm nếu vượt hạn. Commit/push source và bundle mới, bàn giao Chờ review.

**Kết luận cuối: Chưa đạt V2b. V1 và V5b giữ Đạt local; toàn BH-07 chưa nghiệm thu. Không merge main/staging/production/deploy/pilot/BH-08.**
