# Review BH-07C — 15ae1af — vòng 0

Ngày 21/10/2026 (Việt Nam). Nhánh `feat/bh07c-ui`, base `cf95d76855acf1f394b1976ebab54087b4d7bba9`, tested code `15ae1af0d9d39678f4b9d99fabc9e9e22cb860ba`, docs/evidence `65ce0f45fe9782184717ac52ba09a992e960d920`, fetched HEAD `1a88679` (full SHA trong summary). Checkout ban đầu sạch, không có thay đổi local cần cất. Đã đọc AGENTS, docs/04/ai/REVIEWER/08/09/25/10, handoff và evidence C. Xem diff main...HEAD, tách C bằng diff base...HEAD; lib/test/migration của HEAD trùng tested code. A giữ Đạt tại 4512c3a; B giữ Đạt tại d7bac04, code a682007. Không sửa triển khai.

## Phát hiện

### C1 — P2: complete vẫn bật khi DTO tài chính thiếu sessionVersion

`lib/screens/session_finance_screen.dart:582` dùng biến `version` ở dòng 534 (`finance.sessionVersion ?? widget.session.version`). Fallback có sẵn phục vụ chốt phí nay được dùng cho complete mới, trái gate yêu cầu complete phải có version từ DTO tài chính. Khi DTO version=NULL nhưng route version=3, current/revision hợp lệ và actor management, nút vẫn bật và complete dùng version route. Version này có thể cũ, dẫn tới conflict tránh được; không phải bằng chứng bypass gate optimistic concurrency ở server.

Probe C1 dùng provider/screen thật, fixture finance current/in_progress có revision nhưng sessionVersion=NULL và route version=3: kỳ vọng nút disabled FAIL vì callback còn tồn tại. Test complete thành công của tác giả cũng đang dùng fixture thiếu DTO version và chấp nhận route version=3 nên suite xanh chưa bảo vệ gate này.

Sửa: complete chỉ kiểm và truyền `finance.sessionVersion`; thiếu version thì disable kèm hướng dẫn tải lại. Không cần đổi contract B hoặc thay fallback chốt phí BH-06. Viết test đỏ thiếu DTO version dù route có version, rồi ca DTO version khác route phải truyền đúng DTO version; giữ canManage/current/revision/lifecycle/submitting, confirm và error controls.

### C2 — P2: refresh thất bại sau danh sách rỗng bị hiển thị thành empty không có lỗi

`lib/screens/session_history_screen.dart:181`: error đầu trang chỉ hiện khi `!hasLoadedHistory`, còn inline error nằm sau nhánh `isHistoryEmpty` (dòng 193). Tải thành công trang rỗng rồi refresh lỗi mạng: B giữ cache rỗng và đặt historyErrorMessage, UI tiếp tục chỉ nói “Chưa có buổi nào”, không hiển thị lỗi, nhãn dữ liệu cũ hoặc retry nội dung. Toolbar vẫn có thể refresh nhưng người dùng không biết lần vừa tải đã thất bại. Trái quy tắc docs/10: lỗi mạng không phải empty thành công.

Probe C2 tải empty thành công, đổi repository sang network disconnected, bấm “Tải lại lịch sử”: provider có lỗi nhưng Text lỗi và nút retry được kỳ vọng đều không xuất hiện; FAIL ở kỳ vọng Text lỗi.

Sửa: xử lý error độc lập với độ dài cache, kể cả cache đã tải rỗng. Giữ rõ kết quả cũ/lần làm mới thất bại và hành động retry. Thêm test empty→refresh error→retry success; giữ initial error, loading, empty thật và load-more error.

### C3 — P2: khoảng ngày Việt Nam phụ thuộc múi giờ thiết bị

`lib/screens/session_history_screen.dart:76` và dòng 77–84 dựng DateTime local; repository B đổi `.toUtc()` theo múi giờ máy. Trong khi các card hiển thị giờ Việt Nam, cùng ngày chọn sẽ gửi phạm vi khác nhau khi thiết bị/browser ở UTC hoặc múi giờ khác. Chọn 20/10/2026 trên máy UTC gửi from=20/10 00:00Z thay vì 19/10 17:00Z; bỏ buổi 00:00–06:59 giờ Việt Nam ngày đã chọn và lấy thêm buổi sáng ngày kế tiếp. Server lọc starts_at theo bounds nhận được, không sửa hộ lỗi UI này.

Probe C3 thao tác date picker thật, chọn ngày 20/10 rồi kiểm filter vào repository: TZ=UTC FAIL với actual 20/10 00:00Z, expected 19/10 17:00Z. Chính probe này chạy TZ=Asia/Ho_Chi_Minh PASS, xác nhận phụ thuộc múi giờ; không thay kỳ vọng giữa hai lần chạy.

Sửa: coi ngày picker là ngày lịch Việt Nam, chuyển mốc đầu/cuối ngày sang UTC+7 rõ ràng, không dựa local timezone. Phù hợp p_to inclusive của A, bao phủ toàn ngày cuối (kể cả phần giây lẻ), không sửa RPC B/A. Test dưới ít nhất UTC và Asia/Ho_Chi_Minh, gồm buổi sát nửa đêm và giữ nguyên filter CLB/pagination.

## Kiểm chứng độc lập

[Summary/hash](review_15ae1af_evidence/summary.json), [source hashes](review_15ae1af_evidence/source-hashes.json), [analyze](review_15ae1af_evidence/analyze.log), [Flutter](review_15ae1af_evidence/flutter.log), [targeted](review_15ae1af_evidence/targeted.log), [BH-07 runner](review_15ae1af_evidence/bh07.log), [DB JSON](review_15ae1af_evidence/bh07_test_results_20261021014104.json).

| Lệnh/nhóm reviewer tự chạy | Kết quả |
|---|---|
| `flutter analyze --no-pub` | 0 issue, exit 0 |
| `flutter test --no-pub` trước probe tạm | 225/225 PASS, exit 0 |
| Targeted sáu file C theo handoff | 52/52 PASS, exit 0 |
| `BH02_TEST_CONTAINER=bh02-review-bh06 python3 docs/reviews/bh07/run_bh07_tests.py` sau DB ready | 23/23 PASS (21 clean +2 upgrade), exit 0 |
| Năm probe UI reviewer, TZ=UTC | 2 PASS /3 FAIL, exit 1; C1/C2/C3 |
| C3 control TZ=Asia/Ho_Chi_Minh, cùng source/kỳ vọng | 1/1 PASS, exit 0 |

Flutter 3.47.7/Dart 3.13.5; PostgreSQL17 Docker cô lập network none, Auth stub + SET ROLE. Lần DB đầu exit 1 do container vừa khởi động chưa ready; [log khởi động](review_15ae1af_evidence/bh07-startup-failed.log) giữ riêng, chỉ lần sau pg_isready accepting connections được tính PASS. Không apply DB thật.

Probe [finance](review_15ae1af_evidence/review_bh07c_finance_probe_test.dart.txt), [history](review_15ae1af_evidence/review_bh07c_history_probe_test.dart.txt), [summary](review_15ae1af_evidence/review_bh07c_summary_probe_test.dart.txt), [log](review_15ae1af_evidence/probes.log), [control timezone](review_15ae1af_evidence/date-vietnam-control.log). Các file sao chép scaffold test tác giả và thêm ca reviewer trong main; để phát lại, chép thành đúng tên .dart dưới test/, chạy `TZ=UTC flutter test --no-pub test/review_bh07c_*_probe_test.dart --plain-name 'review '`. Không cộng lại ca tác giả vì đã lọc tên. Đã bỏ probe tạm khỏi test/ sau chạy, không thay code/test triển khai. Lần thử harness đầu dùng nhãn Save thay vì OK của picker input nên chưa tới assertion ngày; log giữ riêng, selector được sửa trước kết quả C3 bên trên, không đổi kỳ vọng ngày.

Hai control PASS: complete phải xác nhận trước RPC, dùng DTO version 7 khác route 3, disable trong pending, VERSION_CONFLICT không pop/báo thành công và cho retry; summary transport giữ cache có cảnh báo, FORBIDDEN sau cache xóa dữ liệu và nút copy, có retry. Kiểm thử chuẩn bao gồm quyền, null, copy, complete success/stale, history pagination/error; các ca C1/C2/C3 thiếu ở suite tác giả nên 225 PASS không đóng được chúng.

Đối chiếu evidence tác giả: tested_sha.txt và summary ghi đúng 15ae1af; DB JSON có base_sha=15ae1af, 23 PASS và hash migration khớp. Các raw log được handoff tham chiếu không có trong commit evidence; không xác nhận lại exit/count từ log tác giả vắng mặt, dùng lần tự chạy để kiểm 225/23/52. Không đổi migration/RPC A, model/repository/provider B hoặc nội dung contract; docs/10 chỉ đổi header trạng thái trong C. Các commit sau 15ae1af đến 1a88679 chỉ đổi docs/quy trình. Hash lib/test/migration trước/sau kiểm chứng giữ nguyên. Metadata DB worktree_dirty=true do file kết quả sinh trong lúc chạy, không phải thay triển khai. 335 hồi quy DB và BH-06 integration/upgrade không chạy lại: backend không đổi, giữ baseline B, không cộng vào số mới.

## Kết luận

**Chưa đạt** — phần C BH-07 tại 15ae1af: C1/C2/C3 P2 còn mở; không có phát hiện P0/P1. Người triển khai sửa cả ba trong UI, viết test tái hiện trước sửa, giữ control và chạy lại analyze/toàn bộ Flutter/targeted/BH-07; đây là đầu vào vòng sửa 1/2 theo AGENTS, tối đa hai vòng. Không đổi A/B, không chuyển D, merge main hoặc deploy.

**NOT RUN:** chạy lại 335 DB hồi quy BH-02..06 và BH-06 integration/upgrade; HTTP/PostgREST/JWT/Supabase Auth thật và token RLS; thiết bị/browser/deep link/offline/reopen thực tế; ngân hàng/VietQR/tải ảnh/webhook/chuyển tiền thật; staging/production/apply DB thật, backup/restore, concurrency HTTP, pilot D và rehearsal vận hành. Widget/provider/repository mock và PostgreSQL/Auth stub không thay cổng nghiệm thu toàn BH-07/deploy.
