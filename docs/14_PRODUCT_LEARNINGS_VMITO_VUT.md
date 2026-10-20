# Áp dụng nghiên cứu Vmito và Vụt vào Badminton Hub

> **Hiện hành 20/10/2026:** Nội dung dưới là snapshot lịch sử; không dùng lỗi hoặc prompt cũ để triển khai lại ticket đã nghiệm thu. BH-06 Đạt tích hợp local tại `318bc52` ([review](reviews/bh06/review_318bc52.md)), đã merge vào main tại `e7f7627`; docs/ai đã có trên main (`eaeb209`). Baseline review: analyze sạch, 190 Flutter +335 DB, 7 tích hợp +3 nâng cấp +2 probe PASS. Điểm tiếp tục: [BH-07A](25_BH07_IMPLEMENTATION_HANDOFF.md), đầu bài đã chuẩn bị, chưa triển khai. Chưa nghiệm thu HTTP/JWT/Auth thật, thiết bị/ngân hàng thật, staging/production, backup/restore hoặc concurrency HTTP; merge code không phải deploy.

Ngày 15/10/2026. Đây là bổ sung yêu cầu sản phẩm, UX và chất lượng phát hành, không phải code đã triển khai hoặc migration mới. Đọc cùng PRD, architecture, database và backlog. Baseline repo khi tích hợp: 11aaec7; commit này mới báo sửa H1–H3, lượt nghiên cứu này chưa review/test lại để xác nhận đóng BH-02.

## 1. Nguồn và mức tin cậy

Nguồn do chủ dự án cung cấp: [Vmito](research/competitors/vmito-report.md), [Vụt](research/competitors/vut-report.md), [giới hạn evidence](research/competitors/README.md). Không cài/chạy hai app, không gọi endpoint, không xem APK/XAPK gốc trong lượt này.

| Quan sát trong report | Có thể dùng để làm gì | Không được suy ra |
|---|---|---|
| Vmito Flutter AOT, Vụt React Native/Expo/Hermes | Cả hai cách làm mobile tồn tại trong mẫu phân tích; giữ stack mình theo khả năng đội ngũ | Framework nào tốt hơn, số người dùng hay hiệu năng thực |
| Vmito có App Link paths sessions/venues/clubs và các module khác | Xác định link theo tài nguyên là yêu cầu cần thiết cho host chia sẻ | Các màn hình/routes đều hoạt động hoặc có UX tốt |
| Vụt có chuỗi sessions/filters/joinRequests/updateStatus/matchHistories | Gợi ý các luồng nên kiểm chứng với host: lọc, yêu cầu tham gia, trạng thái, lịch sử | Backend dùng HTTP method/quyền hay mô hình service nào chắc chắn |
| VietQR/bank list, Google Maps, messaging, camera/barcode libraries | Lập lựa chọn tích hợp theo nhu cầu, chia giai đoạn và quyền thiết bị | Có đối soát ngân hàng tự động, chat/push đúng hoặc mọi thư viện đều được gọi |
| Provider/deep link/backup/permissions đáng chú ý | Bổ sung ca kiểm thử own app và minimization | Kết luận đối thủ có lỗ hổng hoặc hành vi thu thập dữ liệu |
| Version metadata khác nhau, APK nhiều ABI/split | Thêm release traceability và đo artifact đúng cấu hình | Gian lận version hoặc so sánh raw size giữa universal APK và split XAPK |

Không sao chép endpoint/service naming của Vụt thành kiến trúc microservices của mình. Không đổi Flutter thành React Native hoặc thêm Stream Chat/Firebase/Maps SDK chỉ vì xuất hiện trong gói đối thủ.

## 2. Các quyết định áp dụng

Giữ định vị **host vận hành CLB và buổi định kỳ**; người chơi vào từ link host. Luồng chính: lịch → đăng ký/duyệt/chờ → điểm danh → chốt phí → thu tiền/công nợ. Khám phá công khai là cửa vào hỗ trợ khi đã có host đăng lịch đều; không mở thêm một feed xã hội/giải đấu để sao đủ menu của app khác.

### PD-01: Link có tài nguyên, nhưng không mang quyền truy cập

Áp dụng BH-04 và BH-07. `/sessions/:id`, `/clubs/:id` là canonical internal routes; path venues có thể bổ sung khi cần link danh bạ. URL chia sẻ không chứa JWT, số điện thoại, bank snapshot hoặc auth token. Anonymous đọc public/unlisted qua projection, private vẫn cần quyền. Guest mở link login xong trở lại đúng buổi, không rơi về màn hình mặc định.

Chỉ nhận scheme/host/path/query đã định nghĩa; return URL chỉ route nội bộ hợp lệ. Auth callback giữ riêng allowlist, kiểm cơ chế state/PKCE theo SDK/cấu hình đang dùng, không tự viết lại flow OAuth. Link tài nguyên không được xử lý như callback đăng nhập. Khi có tên miền sở hữu và cấu hình platform association thì làm verified HTTPS App Links/Universal Links; chưa có domain thì giữ scheme hiện tại có host/path hẹp, không bịa domain hoặc coi scheme custom là verified.

Nghiệm thu: link public/private, ID không tồn tại, chưa login/đã login, app đóng/đang mở, web refresh, URL scheme/host/path sai và return URL bên ngoài bị từ chối. Backend vẫn chặn ID người khác dù link hợp lệ. Không bắt buộc thêm router dependency trước khi đọc routing code đang có.

### PD-02: Tìm kèo vừa đủ để host tuyển vãng lai

Áp dụng BH-04, không tạo marketplace mới. Bộ lọc MVP: khu vực sân (venues.area), khoảng ngày/giờ, còn chỗ và fee_mode; phí cố định có thể lọc member/guest fee đúng nhãn, không gán split_actual thành giá cuối. Trình độ dùng nhãn requirement hiện có để hiển thị; chỉ thêm bộ lọc trình độ có thứ bậc sau khi host thống nhất taxonomy, không tự quy đổi Elo.

Kết quả card hiển thị: sân/khu vực, ngày giờ Việt Nam, host/CLB display name, yêu cầu trình độ, số chỗ tổng từ DB, phí dự kiến/quy tắc chia và status của chính người xem nếu có. Không có danh sách SĐT/bank ở public card. Lọc public chỉ published/in_progress trong thời gian phù hợp, không scan unlisted/draft; phân trang ổn định. Khách chưa chọn vị trí vẫn tìm được bằng khu vực, không xin GPS chỉ để mở app.

Nghiệm thu: host/player/anon thấy cùng số slot; ngày mai/qua nửa đêm; hết chỗ/empty/error; thay filter reset cursor; split cost chưa chốt không hiển thị như fixed price. Không truy vấn tên sân tự do như khóa quan hệ; venue_id là nguồn chuẩn.

### PD-03: Đăng ký là một yêu cầu có vòng đời rõ

Áp dụng BH-05. Phân biệt pending, confirmed, waitlisted, rejected, cancelled; chỉ confirmed giữ slot. Người chơi tự xem trạng thái và thời hạn hủy; host duyệt từ cùng danh sách canonical. Pending không được ghi “đã giữ chỗ”. Host thêm guest từ Zalo vẫn dùng RPC kiểm capacity/idempotency. Mời waitlist có consent/expiry, không giữ slot mặc định.

Nghiệm thu: pending không chiếm chỗ hoặc đọc ngân hàng, hai người tranh slot cuối, retry không tạo trùng, player không sửa status/paid trực tiếp, thu hồi/hết hạn lời mời, financial role thấy tiền nhưng không contact. Các quy tắc này là thiết kế của mình, không khẳng định đối thủ thực thi như vậy.

### PD-04: QR rõ người nhận và số phải thu, không tự suy đã thanh toán

Áp dụng BH-03/BH-06. Giữ VietQRHelper, bank code/account/name của own host/CLB. Không gọi endpoint bank-list tìm thấy trong report để thay nghiệp vụ không cần thiết. Nếu tích hợp danh mục ngân hàng ở bước sau, dùng nguồn API được phép của nhà cung cấp và xử lý cache/lỗi riêng.

Chỉ phát instructions/QR khi đúng player/finance, đăng ký và billing revision đủ điều kiện; stale thì chốt lại trước. Hiện người nhận, số tiền còn phải đóng và reference, có fallback copy thông tin nếu ảnh QR lỗi. Bấm “đã chuyển” là submitted; host/finance kiểm tra tiền thực rồi confirmed. Biên lai, quét QR camera, tự đối soát/webhook để sau; không xin camera cho việc hiển thị QR.

### PD-05: Cập nhật trạng thái trước, push/chat sau

MVP BH-04/05/07: refresh khi vào lại route, sau mutation và nút thử lại; hiển thị trạng thái đăng ký, lời mời và thông báo lịch/phí đã đổi trong chi tiết buổi từ projection hợp quyền. Không dùng audit_events private làm feed public hoặc tự tạo notification inbox từ report. Nếu trạng thái thiếu dữ liệu để phát hiện thay đổi, bổ sung read contract/version rõ khi triển khai, không giả “đã thông báo”.

Sau pilot BH-10 (đề xuất, chưa được giao code): opt-in push cho kết quả duyệt, lời mời, đổi/hủy buổi và khoản phải đóng cần chú ý. Xin quyền khi user chọn nhận nhắc, không ở lần mở đầu. Token thiết bị phải private theo user, có revoke/logout và sở hữu; chỉ backend được gửi, payload không chứa contact/bank/private amounts trên lock screen; mở thông báo phải kiểm quyền lại. Không cần chat SDK cho MVP vì host đã có Zalo; realtime không thay transaction.

### PD-06: Lịch sử theo định danh, không theo chuỗi tên

Giữ session/participant IDs, charges/payment history và audit theo quyền trong BH-07. matchHistories trong report Vụt chỉ gợi ý hướng tương lai; matches/xoay tua/giao lưu vẫn BH-08/09 sau pilot. Không tính rank từ tên và không tự cập nhật thắng thua từ nút gợi ý trận. Không gộp sổ giao lưu với thu tiền sân/quỹ.

## 3. Quyền thiết bị và dữ liệu riêng

Đây là yêu cầu áp dụng cho app mình, không phải kết luận lỗi đối thủ:

- MVP không cần microphone, overlay/SYSTEM_ALERT_WINDOW, broad storage hoặc boot receiver tự thêm. Chỉ khai báo quyền thực sự dùng bởi dependency/feature; kiểm merged release manifest, không chỉ manifest source.
- GPS: chọn khu vực thủ công và mở link map đủ MVP; near-me sau pilot mới xem quyền vị trí foreground/approximate nếu đủ. Từ chối quyền vẫn dùng app được.
- Camera/media: chỉ xin tại hành động quét/upload thực tế khi feature được giao; ưu tiên picker hệ thống; không log/private-cache contact hoặc biên lai vào shared public path.
- File/content provider mặc định non-exported nếu không có lý do; nếu phải chia sẻ, dùng URI grant hẹp, read-only/thời hạn và cache cleanup. Không đánh giá provider chỉ theo exported=true; cần kiểm đường dẫn và kiểm truy cập thực tế.
- Không lưu session/refresh token vào source, URL, logs hoặc clipboard. Kiểm cơ chế persistence thật của Supabase SDK trên từng platform trước chọn giải pháp storage; không thêm SecureStore plugin theo suy đoán. Kiểm backup rules đối với dữ liệu app đã ghi, không chỉ cờ allowBackup.
- Public/publishable key là cấu hình client; service role/secret/password không vào client. Maps key nếu triển khai phải có hạn chế package/signing certificate/API theo provider. Không đưa bất kỳ key/certificate/package identity của đối thủ vào build của mình.

## 4. Kiến trúc và database: giữ nền, chỉ thêm khi có use case

- Không đổi schema v1.1 hoặc chạy migration trong lượt nghiên cứu. venues.area, sessions date/time/lifecycle/visibility/fee fields, existing registration statuses và projections đủ cho lọc MVP đề xuất; join theo venue_id, financial/public reads theo review H1/H2.
- Nếu triển khai lọc còn chỗ, count phải lấy từ DB đúng quyền; không COUNT trên roster bị RLS lọc theo player. Không mở contacts để aggregate.
- Deep link/permission/release là cấu hình app và test boundaries, không phải lý do thêm backend riêng.
- Module notification sau pilot cần thiết kế riêng device registrations/preferences/delivery và RLS khi BH-10 được duyệt; hiện chưa tạo bảng, token hoặc push provider. Không thêm GPS coordinates chỉ vì report có Maps.
- Các helper private, freshness và ledger invariant trong ADR-02/03/04/08 vẫn giữ. Chưa thêm ADR chọn nhà cung cấp chat/maps/push vì chưa có nhu cầu pilot/đánh giá chi phí.

## 5. Kiểm tra phát hành và đo lường

BH-07 thêm release checklist: build versionName/versionCode/source commit thống nhất theo quy trình đã chọn; ghi rõ nếu app version và schema version khác nhau có chủ đích. Pin dependency/lockfile; kiểm merged manifest, exported components, callbacks, backup và không log secrets. Đo download/install size trên cùng ABI/build mode/artifact loại, không so universal Vmito APK 3 ABI với split Vụt ARM64 để kết luận app nào nhẹ hơn. Chưa đặt ngưỡng size không có baseline.

Test link callback trên thiết bị thật và web, permission denied, ảnh QR lỗi, token/session hết hạn, role khác và stale fee. Không “pass” từ thấy tên thư viện hoặc endpoint trong binary. Lưu kết quả PASS/FAIL/NOT RUN và giới hạn platform.

Pilot: đo thời gian host tạo/nhân bản buổi và chốt tiền, tỷ lệ link → yêu cầu đăng ký, số pending bị bỏ sót, tỷ lệ confirmed thực sự đến, mức dùng lại của host tuần sau. Không thêm analytics SDK chỉ để đo sớm; quan sát có consent hoặc số liệu tổng hợp không PII đủ trước. Phỏng vấn 3–5 host xem họ ưu tiên tìm vãng lai, nhắc lịch, quỹ tháng hay xoay tua; feature mới chỉ lên ưu tiên theo bằng chứng.

## 6. Thứ tự thực hiện

1. Review/test lại commit H1–H3 mới, đóng BH-02 bằng bằng chứng thích hợp; tài liệu nghiên cứu không ghi đè trạng thái implementation.
2. BH-03: cấu hình CLB/member/ngân hàng và quyền đúng.
3. BH-04: link/fallback khu vực/card/lọc tối thiểu, lịch đúng; giữ phạm vi vừa sức.
4. BH-05/06: lifecycle đăng ký + QR/payment/read finance đúng.
5. BH-07: end-to-end và release/privacy checklist.
6. BH-08/09 và đề xuất BH-10 sau pilot; chưa triển khai feed/chat/giải đấu/lớp học chỉ vì đối thủ có dấu hiệu tích hợp.
