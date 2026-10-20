# Rà soát Badminton Hub và đề xuất MVP cho host

> **Hiện hành 20/10/2026:** Nội dung dưới là snapshot lịch sử; không dùng lỗi hoặc prompt cũ để triển khai lại ticket đã nghiệm thu. BH-06 Đạt tích hợp local tại `318bc52` ([review](reviews/bh06/review_318bc52.md)), đã merge vào main tại `e7f7627`; docs/ai đã có trên main (`eaeb209`). Baseline review: analyze sạch, 190 Flutter +335 DB, 7 tích hợp +3 nâng cấp +2 probe PASS. Điểm tiếp tục: [BH-07A](25_BH07_IMPLEMENTATION_HANDOFF.md), đầu bài đã chuẩn bị, chưa triển khai. Chưa nghiệm thu HTTP/JWT/Auth thật, thiết bị/ngân hàng thật, staging/production, backup/restore hoặc concurrency HTTP; merge code không phải deploy.

Ngày: 14/10/2026. Repo: phongnt911/badminton-hub, commit được đọc: 33edcbd.

## 1. Kết luận sản phẩm

Nên định vị bước 1 là **công cụ giúp host vận hành CLB và buổi chơi**, bắt đầu tại Nha Trang như PRD hiện tại. Lợi ích cụ thể: bớt tổng hợp tin nhắn đăng ký, biết ai sẽ đến, ai đã đóng tiền và buổi nào còn thiếu người. Người chơi đến qua đường link host chia sẻ; luồng tìm kèo công khai phát triển sau khi đã có các host đăng lịch đều đặn.

Flutter + Supabase + Provider phù hợp để tiếp tục. Chưa có lý do từ lần rà soát này để viết lại app hay thêm backend riêng. Code hiện là bản mẫu nhiều tính năng; chưa đủ bằng chứng để ghi MVP đã hoàn thành 100% hoặc sẵn sàng vận hành thật.

Phạm vi kiểm tra: đọc đặc tả, SQL, code ứng dụng và test; tham khảo trang công khai Vmito. Chưa chạy ứng dụng/test, chưa kiểm tra schema, grants và RLS đang triển khai trên Supabase thật. Những nhận xét về policy dưới đây dựa trên SQL trong repo, không khẳng định tình trạng production.

## 2. Phát hiện có bằng chứng

| Ưu tiên | Hiện trạng | Hệ quả / đề xuất |
|---|---|---|
| P0 | `docs/05_DB_V2_UPDATE.sql:55–58` dùng `FOR ALL USING (true) WITH CHECK (true)` cho CLB, quỹ, thống kê, đối tác; app chưa có luồng auth | Nếu được triển khai với grants cho client, policy không giới hạn người đọc/ghi/xóa. Thêm định danh và quyền theo CLB, thu hẹp policy trước pilot; kiểm thử trực tiếp API bằng người ngoài CLB. |
| P0 | `lib/data/supabase_service.dart:56–71`: insert người chơi rồi cập nhật bộ đếm từ giá trị client | Hai người cùng tranh slot cuối có thể cùng được thêm, ghi đè bộ đếm; một thao tác lỗi gây dữ liệu lệch. Đăng ký qua một giao dịch DB, khóa session, kiểm tra sức chứa và chống gửi trùng. |
| P0 | `lib/data/supabase_service.dart:110–127`: ghi thu/chi rồi cập nhật balance từ client | Ghi đè số dư khi thao tác đồng thời, hoặc có giao dịch nhưng số dư chưa cập nhật. Sổ giao dịch là nguồn dữ liệu; tính tổng ở DB hoặc duy trì số dư trong cùng giao dịch. |
| P1 | `lib/screens/home_screen.dart:89` truyền giờ cố định thay vì `timeCtrl.text`; provider luôn lấy ngày hôm nay | Người dùng sửa khung giờ nhưng dữ liệu vẫn 17:30–19:30; không tạo được lịch tương lai. Chọn ngày/giờ bằng form, kiểm tra kết thúc sau bắt đầu. |
| P1 | `createSession` đặt `joined_count=1` nhưng không thêm người chơi tương ứng | Danh sách và số slot không thống nhất. Host chỉ chiếm slot khi có bản ghi tham gia thật. |
| P1 | `lib/screens/session_detail_screen.dart:77` hiển thị icon QR | Chưa phải QR thanh toán. Gắn tài khoản nhận tiền thật, số tiền phải thu và mã tham chiếu của người tham gia; helper QR hiện có có thể tái sử dụng. |
| P1 | Các provider chỉ `debugPrint` khi lỗi; chi tiết session/leaderboard thiếu xử lý lỗi mạng | Host có thể thấy dữ liệu cũ hoặc loading không kết thúc. Cần loading/error/empty, nút thử lại và trạng thái đang gửi cho thao tác ghi. |
| P1 | CLB chưa có bảng thành viên; session chưa liên kết CLB/host/venue bằng khóa ngoại | Chưa biểu diễn được nghiệp vụ quản lý CLB. Bổ sung quan hệ và vai trò trước khi mở rộng tính năng. |
| P1 | Xoay tua và sổ kèo nằm trong state màn hình; `main.dart` chỉ gắn màn hình tab đang chọn | Dữ liệu có thể mất khi đổi tab hoặc khởi động lại. Lưu theo buổi chơi, phục hồi khi mở lại. |
| P2 | `FairMatchmaker` tăng số trận ngay khi bấm tạo gợi ý; chưa có trạng thái đang chơi/nhiều sân | Bấm lại làm sai thống kê. Tách gợi ý, xác nhận bắt đầu và kết thúc; không đưa người đang chơi vào trận khác. |
| P2 | Undo điểm sau khi kết thúc không hoàn tác mục sổ nợ đã tạo | Có thể ghi nợ trùng khi chấm lại điểm thắng. Kết quả và khoản giao lưu cần gắn ID trận, cập nhật/hoàn tác nhất quán. |
| P2 | Leaderboard chỉ đọc `player_stats`; luồng ghi kết quả đang không cập nhật bảng này | Chưa có thống kê tự động từ trận đấu. Để sau khi dữ liệu trận và người chơi ổn định. |
| P2 | `test/widget_test.dart` chỉ dựng một `Text`, không dựng app thật | Test hiện không chứng minh luồng ứng dụng hoạt động. Ưu tiên test slot cuối, quyền truy cập, thu/chi và tính phí. |

Khóa public/anon trong client không tự nó là lỗi bảo mật; quyền DB mới là hàng rào chính. Không đặt service-role hoặc secret trong app. Lần rà soát này không xác minh loại khóa hay quyền thực tế của dự án remote.

Tài liệu còn lệch code: `level_requirement`, các cột `created_at` được dùng nhưng không được mô tả đủ trong database doc; bộ SQL trong repo chưa thể hiện một migration tạo toàn bộ schema từ đầu. PRD có nội dung hướng dẫn dán file và block Markdown bị lẫn với đặc tả; cần biên tập lại.

## 3. Tham khảo Vmito

Nguồn đọc ngày 14/10/2026:

- Trang chủ: https://vmito.com/vi — có các mục tìm kèo, sân, nhóm, giải, lớp học và xếp hạng.
- Hướng dẫn: https://vmito.com/vi/guide — mô tả host duyệt yêu cầu tham gia, quản lý người chơi, cấu hình/xếp sân, phí cố định/chia đều, QR và xác nhận bằng chứng thanh toán, thành viên và vai trò nhóm.
- Một trang kèo: https://vmito.com/vi/sessions/keo-san-the-b-hoa-binh-334ru — hiển thị địa điểm, giờ chơi, trình độ, mức phí, loại cầu và nguồn Facebook.

Đây là quan sát trang công khai và nội dung hướng dẫn; chưa thử các chức năng sau đăng nhập. Không suy luận stack, chất lượng thuật toán, số người dùng hay hiệu quả kinh doanh của Vmito.

Nên học cách trình bày thông tin kèo, cơ chế host duyệt, chia sẻ link/mã, trạng thái tham gia và xác nhận thanh toán. Khác biệt đề xuất cho Badminton Hub là vận hành CLB định kỳ: nhân bản lịch, danh sách thành viên cố định, điểm danh, chốt phí và công nợ theo từng người. Đây là hướng ưu tiên của app mình, không phải khẳng định Vmito thiếu những khả năng này.

## 4. Đặc tả MVP đề xuất

### Người dùng và quyền

- Người xem: xem sân và thông tin buổi chơi được công khai; không đọc số điện thoại người tham gia, sổ quỹ hoặc thông tin tài khoản không được chủ sở hữu cho công khai.
- Chủ CLB: cấu hình CLB, phân quyền, quản lý thành viên và tài chính.
- Đồng host: quản lý các buổi được phân công; quyền sửa tài chính cấp riêng.
- Thành viên/người vãng lai: xem và sửa đăng ký của mình theo thời hạn, xem khoản phải đóng của mình.
- Quản trị ứng dụng: quản lý danh bạ và xử lý báo cáo với quyền được quy định riêng.

Vai trò thuộc từng CLB/buổi: một người có thể là host tại CLB A và thành viên tại CLB B. Số điện thoại liên hệ không phải bằng chứng sở hữu tài khoản.

### Luồng chính

1. Host đăng nhập, tạo CLB, nhập ngân hàng và thêm thành viên cố định, kể cả người chưa có tài khoản.
2. Tạo buổi từ mẫu: ngày/giờ, sân, số sân, sức chứa, trình độ, phí, thời hạn đăng ký/hủy. Nhân bản buổi cho tuần sau; tự sinh lịch hàng loạt để sau.
3. Mời thành viên đăng ký từng buổi. Thành viên cố định không mặc định là đã xác nhận đến. Host có thể thêm người đã đăng ký qua Zalo.
4. Mở số chỗ còn lại cho vãng lai, chia sẻ link qua Zalo/Facebook. Có chế độ host duyệt hoặc tự xác nhận khi còn chỗ.
5. Điểm danh, ghi nhận người vắng và khách đến trực tiếp. Giai đoạn sau hỗ trợ gợi ý xoay tua từ danh sách đã có mặt.
6. Nhập chi phí thực tế, chốt phí từng người, hiển thị QR và ghi nhận thanh toán tiền mặt/chuyển khoản. Người chơi gửi biên lai là đang chờ xác nhận; không tự coi là đã thu tiền.
7. Kết thúc buổi, xem còn phải thu ai và tổng thu/chi. Xuất hoặc sao chép bản tóm tắt để gửi nhóm.

### Trạng thái và quy tắc

- Buổi: `draft → published → in_progress → completed`; có `cancelled`. Còn/hết chỗ là trạng thái tính từ đăng ký, không trộn với vòng đời buổi.
- Đăng ký: `pending`, `confirmed`, `waitlisted`, `cancelled`, `rejected`. Chỉ `confirmed` chiếm sức chứa. Điểm danh dùng trường riêng: `not_checked_in`, `present`, `no_show`.
- Khi hủy: giải phóng slot trong cùng giao dịch, xử lý danh sách chờ theo chế độ host duyệt/tự động đã chọn. Không tự chuyển người chờ sang confirmed nếu họ chưa đồng ý cơ chế này.
- Phí: hỗ trợ `fixed` hoặc `split_actual`. Chia thực tế theo người có mặt; phí khách/thành viên khác nhau, miễn phí host hay phí hủy phải được cấu hình rõ trước buổi.
- Chốt phí tạo khoản phải thu riêng mỗi người; tiền dự kiến không thay thế tiền đã chốt. Phần dư do làm tròn phải được xử lý sao cho tổng khoản phải thu đúng tổng được phân bổ.
- Số người chia bằng 0: báo chưa thể chia, không tự chia cho 1. Không cho tiền âm/sức chứa âm; phí 0 chỉ khi host chọn buổi miễn phí.
- Thanh toán: hỗ trợ trả thiếu/trả nhiều lần. Số còn nợ = phải thu trừ khoản thu được xác nhận. QR chỉ hỗ trợ chuyển khoản; không xác minh tiền đã vào ngân hàng.
- Chốt lại hoặc sửa khoản thu phải có lý do/lịch sử. Không ghi trùng tiền thu buổi vào quỹ CLB; mỗi khoản thu liên kết một giao dịch quỹ nếu thuộc quỹ.

### Kèo giao lưu / kèo độ

Phân biệt buổi sinh hoạt (`session`), trận trong buổi (`match`) và thỏa thuận giao lưu (`challenge`). Bước 1 có thể giữ giao lưu nước/cầu tự nguyện, ghi người/cặp tham gia, vật phẩm, số lượng, kết quả và trạng thái hoàn tất; không gộp với tiền sân hoặc quỹ CLB. Chưa ưu tiên ví, giữ tiền hay tự động thu tiền theo thắng thua. Cần hỏi host thực tế họ muốn hẹn trận, theo dõi kết quả hay sổ giao lưu để chọn phạm vi đúng.

### Chưa ưu tiên

Giải đấu, Elo toàn hệ thống, lớp học, mạng xã hội, đặt sân/thanh toán cho chủ sân, quảng cáo/affiliate mở rộng. Có thể giữ danh bạ sân hiện tại và các tiện ích demo, nhưng không dùng chúng làm tiêu chí hoàn thành MVP cho host.

## 5. Mô hình dữ liệu đề xuất

| Thực thể | Trường/quan hệ chính | Ý nghĩa |
|---|---|---|
| `profiles` | `id → auth.users`, tên, trình độ | Tài khoản đã định danh; thông tin liên hệ bảo vệ riêng. |
| `clubs` | `owner_user_id`, tên, visibility | Không lấy owner_phone làm quyền sở hữu. |
| `club_members` | club_id, user_id nullable, tên, liên hệ riêng, role, status | Cho phép host quản lý người chưa có tài khoản; một bản ghi ổn định cho mỗi thành viên. |
| `venues` | dữ liệu danh bạ hiện tại | `sessions.venue_id` làm khóa ngoại; có thể lưu tên/địa chỉ snapshot cho lịch sử. |
| `sessions` | club_id nullable, host_user_id, venue_id, starts_at, ends_at, capacity, court_count, fee_mode, lifecycle, visibility | Cho phép host tạo buổi độc lập hoặc thuộc CLB. Thời gian dùng timestamptz, hiển thị Asia/Ho_Chi_Minh. |
| `session_players` | session_id, user_id nullable, club_member_id nullable, guest_name, registration_status, attendance_status | Giữ tên bảng hiện tại để giảm đổi code; liên kết người chơi ổn định. Thêm checked_in_at/by. |
| `session_expenses` | session_id, loại chi phí, amount_vnd, created_by | Tiền sân, cầu và chi phí được thống nhất. |
| `session_charges` | session_player_id, amount_due_vnd, version, finalized_at/by | Khoản phải thu đã chốt; một phiên bản hiện hành cho mỗi người. |
| `payments` | charge_id, amount_vnd, method, status, confirmed_by/at, reference | Nhiều khoản thanh toán cho một khoản phải thu; biên lai trong storage riêng nếu triển khai. |
| `club_transactions` | club_id, direction, amount_vnd, source_payment_id/source_expense_id, created_by, reversal_of | Sổ quỹ có truy vết; source unique chống ghi hai lần. Điều chỉnh qua giao dịch đảo thay vì xóa lịch sử. |

Bổ sung `session_templates`, `matches`, `match_players`, `challenges`, `challenge_participants`, `audit_events` theo tính năng thực sự cần. Bảng điểm và thống kê về sau phải lấy kết quả từ matches, không ghi số thắng theo tên tự do.

Ràng buộc bắt buộc: khóa ngoại, số tiền nguyên VNĐ, CHECK cho trạng thái/tiền/sức chứa/thời gian, chống đăng ký trùng theo định danh đã có và index theo CLB/ngày/session. Khách chưa có tài khoản phải đăng ký qua endpoint có kiểm soát hoặc do host thêm; không mở toàn bộ bảng cho anonymous insert/update. Nếu dùng mã quản lý đăng ký khách, mã phải bí mật, có hạn và chỉ cho phép sửa đúng đăng ký đó. Không coi nhập cùng số điện thoại là xác minh danh tính.

Không tự động gộp dữ liệu cũ theo tên/SĐT hoặc suy ra chủ CLB từ số điện thoại. Migration cần host xác nhận quyền sở hữu và xử lý bản ghi trùng. Các trường joined_count/balance nếu giữ làm cache phải do DB duy trì; client không được đặt giá trị tổng.

## 6. Cấu trúc ứng dụng

Giữ các thư mục core/data/providers/screens trong bước đầu. Đề xuất thêm `models/` khi cập nhật tài liệu kiến trúc, với các kiểu Club, ClubMember, Session, SessionPlayer, Payment thay vì truyền Map khắp UI. Đây là đề xuất cho lần triển khai sau, chưa thay đổi cấu trúc trong lần rà soát này.

- `screens/`: hiển thị/form, không gọi Supabase trực tiếp.
- `providers/`: state loading/error/empty/success, điều phối thao tác; tách state chi tiết theo session để tránh dữ liệu buổi trước xuất hiện ở buổi sau.
- `data/`: tách service/repository theo auth, club, session, finance khi file chung lớn; một nơi gọi RPC/DB và ánh xạ model.
- `core/`: cấu hình, định dạng thời gian/tiền, VietQR; thuật toán chia phí/xoay tua thành hàm độc lập để kiểm thử.
- DB/RPC: bảo vệ quyền, slot, chống thao tác trùng, chốt phí và ghi quỹ nguyên tử. Mọi RPC vẫn phải kiểm tra người gọi; không dùng quyền cao để bỏ qua authorization.

Điều hướng host đề xuất: **Tổng quan · Buổi chơi · CLB · Tài khoản**. Thu/chi và quỹ nằm trong CLB hoặc chi tiết buổi; danh bạ sân là công cụ khi tạo buổi; bảng điểm/xoay tua/kèo giao lưu nằm trong buổi đang diễn ra. Người chơi mở link nhận giao diện đăng ký đơn giản. Cần route theo ID để mở link vào đúng buổi trên web/mobile; xác minh trải nghiệm web Flutter trên điện thoại trước khi chọn là kênh mời chính.

Không thêm Riverpod/BLoC/microservices hoặc thư viện mới chỉ để đổi kiến trúc. Provider đủ cho giai đoạn này. Flutter có thể tiếp tục cho mobile và thử web nhận link; chưa cần làm song song một web stack khác.

## 7. Kế hoạch triển khai và tiêu chí nghiệm thu

1. **Sửa đặc tả:** bỏ tuyên bố hoàn thành 100%, tách demo/đã kiểm thử/đã pilot; xác định quyền, phí, hủy và bộ dữ liệu pilot. Cập nhật PRD/database/architecture/LLM rules cùng lúc để AI không bị tài liệu cũ ràng buộc sai.
2. **Nền tảng dữ liệu:** có migration tạo schema từ đầu, auth/RLS, mô hình thành viên và liên kết CLB–buổi; RPC đăng ký/thu chi; xác nhận owner cho dữ liệu cũ.
3. **Một buổi hoàn chỉnh:** tạo/nhân bản → chia sẻ → đăng ký/duyệt/hủy → điểm danh → chốt phí → QR/thu tiền → kết thúc và công nợ.
4. **Pilot có hỗ trợ:** đề xuất 3–5 host tại Nha Trang trong khoảng 4 tuần; hướng dẫn nhập CLB và theo dõi ít nhất một buổi thực tế mỗi host. Quy mô/thời gian này là đề xuất, không phải cam kết.
5. **Mở rộng theo phản hồi:** xoay tua nhiều sân, mẫu lịch định kỳ, kèo giao lưu; tìm kèo công khai khi lịch host đã đủ đều.

Các kiểm tra bắt buộc trước pilot:

- Hai đăng ký đồng thời vào slot cuối: tối đa một confirmed, người còn lại chờ/báo hết chỗ; bộ đếm khớp dữ liệu. Gửi lại cùng request không thêm trùng.
- Host A không sửa buổi/quỹ CLB B bằng UI hoặc API. Người ngoài không đọc danh sách SĐT/quỹ; người chơi không tự xác nhận đã thu tiền.
- Hai giao dịch quỹ đồng thời và lỗi giữa thao tác: tổng đúng, không có bản ghi dở dang; ghi lại payment không cộng quỹ hai lần.
- QR đúng tài khoản nhận và khoản phải thu; khoản trả thiếu còn hiện nợ; buổi không có người có mặt không chia phí.
- Tạo lịch tương lai/giờ tùy chọn, hủy/duyệt/hết chỗ/điểm danh hoạt động; mất mạng có lỗi và thử lại, không báo thành công giả.
- Mở lại app không mất dữ liệu buổi; dữ liệu demo tách khỏi dữ liệu thật.

Chỉ số pilot đề xuất: host tổ chức được buổi đầu; số host quay lại tạo buổi tuần sau; thời gian tổng hợp danh sách/chốt tiền; số lần phải sửa tay số người hoặc số tiền; tỷ lệ đăng ký qua link và số phản ánh. Ngưỡng thử nghiệm gợi ý: ít nhất 3/5 host dùng liên tiếp 3 tuần và báo giảm việc tổng hợp; không có sai số slot/quỹ hay lỗi lộ quyền trong các ca kiểm tra. Đo baseline trước khi kết luận tiết kiệm thời gian.

## 8. Mô hình vận hành và nguồn thu

PRD hiện cam kết miễn phí 100%. Giữ miễn phí trong pilot; chưa tự thay đổi cam kết hay thêm quảng cáo vào luồng thu tiền. Sau khi có dữ liệu sử dụng, có thể thảo luận miễn phí tính năng cơ bản và gói host nâng cao (nhiều CLB, xuất báo cáo, lịch tự động), hoặc tiếp tục tài trợ địa phương/affiliate như định hướng hiện tại. Không nên coi nguồn thu quảng cáo đã được chứng minh khi chưa có lượng sử dụng.

Khi phỏng vấn host, cần xác nhận: thành viên đóng theo buổi hay tháng; số sân/người mỗi buổi; thường đăng ký qua đâu; host có tự chơi không; phí khách và thành viên có khác nhau không; xử lý hủy sát giờ/no-show; có đồng host/thủ quỹ không; cách hiện tại họ chốt tiền; mục đích thực tế của kèo độ. Câu trả lời quyết định phạm vi, thay vì thêm tính năng vì app tham khảo có.
