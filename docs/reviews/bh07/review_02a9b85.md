# Review BH-07C — 02a9b85 — vòng 1/2

Ngày 21/10/2026 (Việt Nam). Nhánh `feat/bh07c-ui`, base review `9b978467316d66c458846ac68c5de8021401fa0c`, tested code `02a9b857724e9ba031323ad732c90355d7932a39`, docs/evidence và fetched HEAD `f63e5a4e58303a698017e8a46f91fcd3d79227f4`. Checkout ban đầu sạch; fetch trực tiếp ref nhánh, fast-forward, không có thay đổi local cần cất. Theo AGENTS, docs/ai/REVIEWER.md, docs/04/09/25, [review cũ](review_15ae1af.md), handoff và bằng chứng sửa. Chỉ review C1/C2/C3 và test/evidence liên quan; không review lại A/B. A giữ 4512c3a; B giữ d7bac04, code a682007.

Đã chạy hai diff được yêu cầu: base..tested code có đúng sáu file (ba production, ba test); tested code..docs chỉ có docs/evidence. Cây lib/test/migration của f63e5a4 trùng 02a9b85, không đổi migration/RPC, model/repository/provider B hoặc contract. Không sửa triển khai, không apply DB thật.

## Kết quả đối chiếu phát hiện cũ

### C1 — P2: complete thiếu version DTO — đã đóng

- File:dòng: `lib/screens/session_finance_screen.dart:537`, gate/callback tại dòng 591–592; hướng dẫn tải lại dòng 581–584.
- Cách tái hiện: DTO version=NULL, route version=3, finance current/in_progress có revision; đối chiếu ca DTO version=7 khác route=3.
- Kỳ vọng: thiếu DTO version thì disabled/hướng dẫn tải lại, không gọi complete; có DTO thì gửi đúng version=7. Chốt phí BH-06 vẫn được dùng fallback route.
- Thực tế: targeted test và probe reviewer PASS. Complete chỉ dùng completeVersion=finance.sessionVersion; đường fallback chốt phí ở dòng 534 vẫn giữ, test chốt phí route version=3 PASS. Callback complete không tồn tại khi disabled. Control xác nhận trước RPC, pending disable và VERSION_CONFLICT không pop/báo thành công vẫn PASS.
- Ảnh hưởng: không còn dùng version route thay DTO cho complete trong phạm vi kiểm chứng.
- Cách sửa: không cần sửa thêm C1.
- Trạng thái: **PASS**.

### C2 — P2: cache rỗng che lỗi refresh — đã đóng

- File:dòng: `lib/screens/session_history_screen.dart:178`, nhánh empty tại dòng 191.
- Cách tái hiện: tải empty thành công rồi refresh lỗi; đối chiếu cache có một buổi rồi refresh lỗi và retry.
- Kỳ vọng: cả cache rỗng và không rỗng đều hiện inline error, nhãn lần tải trước và nút “Tải lại”; giữ cache hợp lệ trong lúc lỗi, retry thành công cập nhật danh sách/xóa lỗi.
- Thực tế: error được render trước nhánh empty, có thông điệp riêng cho cache rỗng. Test tác giả kiểm empty→error→retry thành công; probe cũ và control reviewer mới cho cache không rỗng đều PASS dưới UTC và Asia/Ho_Chi_Minh.
- Ảnh hưởng: lỗi refresh không còn bị biểu diễn chỉ bằng empty thành công.
- Cách sửa: không cần sửa thêm C2.
- Trạng thái: **PASS**.

### C3 — P2: ngày lọc phụ thuộc múi giờ máy — đã đóng

- File:dòng: `lib/core/time_utils.dart:16` và dòng 21; `lib/screens/session_history_screen.dart:29`, nhãn ngày tại dòng 241.
- Cách tái hiện: picker chọn 20/10/2026, chạy cùng targeted/probe trên TZ=UTC và TZ=Asia/Ho_Chi_Minh.
- Kỳ vọng: from=`2026-10-19T17:00:00Z`, to=`2026-10-20T16:59:59.999999Z`, UI giữ nhãn `20/10/2026 - 20/10/2026`; gồm nửa đêm và giây lẻ cuối ngày, loại nửa đêm ngày kế tiếp.
- Thực tế: helper dựng DateTime.utc từ trường lịch rồi trừ UTC+7, cuối ngày trừ 1 microsecond. Unit/widget targeted kiểm exact bounds, isUtc, mốc đầu/cuối/ngày kế tiếp và nhãn UI; cả hai múi giờ PASS. Probe reviewer cũ giữ nguyên kỳ vọng ngày nay PASS trong cả hai múi giờ.
- Ảnh hưởng: lọc ngày Việt Nam không còn lệch theo timezone máy trong môi trường Dart VM đã chạy; chưa xác minh browser/thiết bị thật.
- Cách sửa: không cần sửa thêm C3.
- Trạng thái: **PASS**.

Không có phát hiện P0/P1/P2 còn mở trong phạm vi bản sửa được giao.

## Kiểm chứng độc lập và giới hạn bằng chứng

[Summary](review_02a9b85_evidence/summary.json), [hash nguồn](review_02a9b85_evidence/source-hashes.json), [lệnh/exit Flutter](review_02a9b85_evidence/flutter-exits.json), [script chạy](review_02a9b85_evidence/run_flutter.py). Không dùng log tác giả làm kết quả reviewer.

| Lệnh reviewer tự chạy | Kết quả |
|---|---|
| `flutter analyze --no-pub` | 0 issue, exit 0 ([log](review_02a9b85_evidence/analyze.log)) |
| `flutter test --no-pub` trước probe tạm | 230/230 PASS, exit 0 ([log](review_02a9b85_evidence/flutter.log)) |
| Bảy file targeted theo yêu cầu, TZ=UTC | 57/57 PASS, exit 0 ([log](review_02a9b85_evidence/targeted_utc.log)) |
| Cùng targeted, TZ=Asia/Ho_Chi_Minh | 57/57 PASS, exit 0 ([log](review_02a9b85_evidence/targeted_vietnam.log)) |
| `BH02_TEST_CONTAINER=bh02-review-bh06 python3 docs/reviews/bh07/run_bh07_tests.py` | 23/23 PASS (21 clean +2 upgrade), exit 0 ([log](review_02a9b85_evidence/bh07.log), [JSON](review_02a9b85_evidence/bh07_test_results_20261021022604.json)) |
| Năm probe UI reviewer, TZ=UTC | 5/5 PASS, exit 0 ([log](review_02a9b85_evidence/probes_utc.log)) |
| Cùng năm probe, TZ=Asia/Ho_Chi_Minh | 5/5 PASS, exit 0 ([log](review_02a9b85_evidence/probes_vietnam.log)) |

Flutter 3.47.7 / Dart 3.13.5; PostgreSQL17 Docker `bh02-review-bh06`, network none, Auth stub + SET ROLE. Runner chỉ tạo DB fixture cô lập; không apply remote/staging/production. Số targeted/probe là các lượt chạy riêng, không cộng vào 230 test đầy đủ.

Probe [finance](review_02a9b85_evidence/review_bh07c_finance_probe_test.dart.txt) giữ nguyên source/kỳ vọng của review cũ (C1 + control DTO7/version conflict); probe [history](review_02a9b85_evidence/review_bh07c_history_probe_test.dart.txt) giữ hai ca C2/C3 cũ, chỉ thêm control cache không rỗng/error/retry. Có thể chép thành đúng tên .dart dưới test/ rồi chạy `TZ=UTC flutter test --no-pub test/review_bh07c_finance_probe_test.dart test/review_bh07c_history_probe_test.dart --plain-name 'review '` và đổi TZ cho lần thứ hai. Không cộng các test tác giả sao chép trong scaffold vì đã lọc tên. Đã chuyển probe tạm ra khỏi test/ và kiểm lại hash: nguồn lib/test/migration không đổi, trùng tested code. Worktree ban đầu sạch; JSON/probe sinh trong lúc chạy có thể làm metadata worktree_dirty=true.

Đối chiếu [manifest hash tác giả](review_02a9b85_evidence/author-hash-check.json): **bảy raw log được liệt kê nhưng không có trên nhánh**, gồm red_targeted.log, flutter_analyze.log, flutter_test.log, targeted_utc.log, targeted_vietnam.log, bh07_db_runner.log và diff_check.log. Không xác nhận lại lịch sử red log tác giả “exit1/3 FAIL” từ file vắng; chỉ giữ đó là tự báo. Các file hiện có khớp hash trực tiếp hoặc khi tái dựng CRLF Windows từ checkout LF, không có hash lệch chưa giải thích. DB JSON tác giả ghi base_sha=`9b97846`, worktree_dirty=true, không phải metadata SHA02a9b85; không dùng nó để khẳng định đã test đúng cây code C. DB/backend không đổi giữa hai mốc. Kết luận bản sửa dựa trên các lần tự chạy trên HEADf63e5a4 với nguồn trùng 02a9b85, và probe đỏ reviewer vòng0 đã giữ nguyên trong review_15ae1af_evidence nay phát lại xanh. Giới hạn truy vết log gốc tác giả được giữ rõ, không chuyển thành bằng chứng đã kiểm.

## Kết luận

**Đạt** — BH-07C vòng sửa 1/2 tại tested code `02a9b85`, trong phạm vi sửa C1/C2/C3 và kiểm chứng local nêu trên. C1/C2/C3 P2 đã đóng; không mở P0/P1/P2 mới. Giữ các báo cáo/bằng chứng cũ theo SHA, không diễn giải thành nghiệm thu toàn BH-07 hoặc pilot. Không chuyển D, sửa A/B, merge main hoặc deploy.

**NOT RUN:** HTTP/PostgREST/JWT/Supabase Auth thật; thiết bị/browser/offline/reopen/deep link; ngân hàng/VietQR/tải ảnh/webhook/chuyển tiền thật; staging/production/apply DB thật/backup/restore; concurrency HTTP; pilot D/rehearsal vận hành; hồi quy DB BH-02..06 335 ca và BH-06 integration/upgrade không chạy lại vì DB/backend không đổi. Log gốc/red-run chronology tác giả chưa kiểm chứng do file thiếu. Local/widget/PostgreSQL/Auth stub không thay các cổng môi trường thật.
