# Code review BH-03

Ngày 15/10/2026. Head `88dd247`, base `19578f5`; gồm hai commit BH-03A và BH-03B/C/D. Đã đọc migration, repository/provider/model/UI và tests liên quan. 24 ca DB hiện có chạy lại đều PASS; ba ca DB bổ sung đều FAIL. Còn lỗi định danh, idempotency và vòng đời dữ liệu private nên chưa đủ kết luận BH-03 đã đạt đầy đủ nghiệm thu.

## Phạm vi và kiểm thử

Review theo skill code-review được chỉ định; nhận xét chỉ gắn dòng thêm/sửa trong diff. Tests PostgreSQL 17 cô lập, Auth stub/role/claim và dữ liệu giả; không gọi/apply Supabase live. Chạy `BH02_TEST_CONTAINER=bh02-review-postgres python docs/reviews/bh03/run_bh03_tests.py` được 24/24 PASS. Bộ runner tạo clean/legacy và apply migration cả hai nhưng các ca hành vi dùng TARGET_DB=CLEAN, vì vậy không diễn giải 24/24 thành toàn bộ tests đã chạy trên cả hai schema.

Ba ca bổ sung: gán account không consent; đổi payload contact_note cùng request key; hai create_club đồng thời cùng request key. Cả ba không đạt. Ca concurrency dùng trigger test-only sleep tại INSERT để tạo lịch đua hợp lệ, removed sau khi chạy. Tất cả thao tác chỉ trên DB test. Kết quả: `baseline_results.json` (artifact review), [baseline_extra_results.json](baseline_extra_results.json), `extra_tests.py` (artifact review).

Không chạy lại Flutter/analyze trong lượt này. Hai vấn đề Flutter dưới đây dựa trên đọc toàn luồng và tìm callers, không gọi là widget tests đã tái hiện. Số 56/56 và 47/47 regression trong báo cáo tác giả chưa được xác nhận lại ở lượt này.

## Tóm tắt file

- Đã thêm [migration BH-03](../../../supabase/migrations/20261015133247_bh03_clubs_and_members.sql): 12 read/mutation RPC và profile backfill.
- Đã thêm [club model](../../../lib/models/club.dart), [repository](../../../lib/data/club_repository.dart); đã thay [provider](../../../lib/providers/club_provider.dart) và [màn hình CLB](../../../lib/screens/clubs_screen.dart).
- Đã thêm [DB runner](../../../docs/reviews/bh03/run_bh03_tests.py), [model tests](../../../test/models/club_model_test.dart), [provider tests](../../../test/providers/club_provider_test.dart), [widget tests](../../../test/screens/clubs_screen_test.dart) và các JSON kết quả BH-02/BH-03.
- Đã cập nhật [backlog](../../../docs/09_IMPLEMENTATION_PLAN.md) và thêm [implementation summary](../../../docs/16_BH03_IMPLEMENTATION_SUMMARY.md).

## Phát hiện

### C1 — P1/high: Gán account thành viên khi chưa được người đó đồng ý

File: [migration](../../../supabase/migrations/20261015133247_bh03_clubs_and_members.sql#L261). Line: 261–272.

add_club_member chỉ kiểm profile tồn tại và chưa vào CLB, rồi gắn p_user_id thành active member ngay. Không có invitation/acceptance; owner/host biết UUID của bất kỳ user nào có thể gắn người đó vào CLB, rồi cấp role theo account đã gắn. Vi phạm hợp đồng BH-03: user_id mới phải NULL nếu chưa có cơ chế xác nhận, không cho nhập UUID tùy ý. Không kết luận đây là đọc trộm profile của người bị gắn; tác động trực tiếp là liên kết danh tính/quyền/membership không có consent.

Test: owner thêm user 9 với p_user_id tồn tại nhưng không có lời mời, RPC thành công và trả đúng UUID user 9. Expected là từ chối.

Đề xuất: trong MVP từ chối p_user_id không NULL nếu không có acceptance đã xác minh; guest tạo NULL. Khi triển khai linking phải bind invitation với actor nhận và CLB/member đúng, chống replay/trùng. Không coi owner chọn UUID là consent.

### C2 — P1/high: Hai request cùng idempotency key vẫn tạo hai CLB

File: [migration](../../../supabase/migrations/20261015133247_bh03_clubs_and_members.sql#L59). Line: 59–66.

check_idempotency chỉ SELECT trước khi ghi, không có lock/reservation cho (actor,operation,request_id). Hai transaction có thể cùng thấy chưa có key, cùng insert CLB + owner, cuối cùng record_idempotency ON CONFLICT DO NOTHING chỉ giữ một result nhưng cả hai CLB đã được commit. Test sequential replay hiện có không bắt lịch này.

Test: hai create_club cùng actor/key/payload chạy đồng thời, cả hai trả hai UUID khác nhau, COUNT club tên test=2, expected=1.

Đề xuất: serialize hoặc reserve request identity trước bất kỳ side effect; check payload/replay sau lock trong cùng transaction. Chỉ khóa club sau khi tạo chưa đủ vì request create chưa có club id. Kiểm thử cả concurrent same-payload (cùng result) và different-payload (một conflict, không thêm side effect). Áp dụng cho các mutation khác có cùng read-then-write helper pattern.

### C3 — P1/high: Dữ liệu private CLB không được gắn vòng đời đăng nhập

File: [ClubProvider](../../../lib/providers/club_provider.dart#L375). Line: 375–381; fetchClubs line 63–68.

clearAll được thêm nhưng không có caller trong code ứng dụng. AuthProvider và ClubProvider được tạo độc lập ở root, logout trong AccountScreen chỉ gọi AuthProvider.logout. Vì vậy list/detail/member contacts/bank có thể còn trong provider sau logout, và tài khoản khác có thể nhìn thấy dữ liệu cũ trước khi fetch mới hoàn tất hoặc khi fetch lỗi. fetchClubs cũng gán kết quả bất chấp user/session đã đổi; ngay cả gọi clearAll một lần vẫn có thể bị response đang bay điền dữ liệu lại.

Đề xuất: nối reset/recreate ClubProvider theo auth user/session thay đổi và gắn generation token cho request để bỏ kết quả phiên cũ. Clear list/detail/bank/contacts khi logout/đổi user trước khi UI được render dưới phiên mới; không giữ private data cũ khi read mới lỗi. Không chỉ xóa lúc rời một route.

Kiểm thử cần thêm: user A tải private member/bank → logout → user B; response A tới sau clear hoặc B gặp lỗi mạng vẫn không thấy data A. Test clearAll gọi trực tiếp hiện có không chứng minh integration logout hoạt động.

### C4 — P2/medium: UI không truyền request_id nên retry vẫn tạo mới

File: [ClubRepository](../../../lib/data/club_repository.dart#L39). Line: 32–39; create dialog call tại [ClubsScreen](../../../lib/screens/clubs_screen.dart#L106).

requestId optional xuyên suốt UI/provider/repository; mọi callback mutation của UI không tạo hoặc truyền key. Repository bỏ p_request_id khi NULL và server cho phép NULL, nên các thao tác thật đi đường không idempotent. Nếu server đã commit nhưng response timeout, user bấm lại tạo CLB/thêm guest hoặc cập nhật bank thành thao tác mới; isSubmitting chỉ chống bấm khi Future đang chạy, không bảo vệ retry sau timeout.

Đề xuất: tạo UUID một lần theo ý định form, giữ qua retry và truyền bắt buộc qua provider/repository/RPC; đổi input phải tạo key mới hoặc báo conflict đúng. Không sinh key mới cho mỗi lần bấm thử lại. Server nên reject key thiếu cho mutation theo contract; tests UI verify timeout+retry giữ cùng key. Đây là vấn đề khác C2: client phải gửi key và server phải bảo vệ key trước cạnh tranh.

### C5 — P2/medium: Payload hash bỏ sót trường làm thay đổi nghiệp vụ

File: [migration](../../../supabase/migrations/20261015133247_bh03_clubs_and_members.sql#L252). Line: 252–255.

Hash add_club_member không có p_contact_note; set_club_bank_account/set_host_bank_account cũng bỏ p_account_name. Cùng request key nhưng đổi các trường này không trả IDEMPOTENCY_CONFLICT, mà trả kết quả payload trước, làm người dùng tưởng thông tin mới được lưu. Ghép chuỗi bằng dấu ':' cũng không biểu diễn ranh giới field an toàn nếu input có dấu này.

Test: add member với Note A rồi Note B cùng key đều thành công. Expected lần hai conflict.

Đề xuất: hash biểu diễn canonical có đủ mọi trường được normalize, phân biệt NULL/empty theo semantics API; dùng JSON/structure thay nối delimiter tùy ý. Test đổi từng field, bao gồm contact note và account name; giữ exact replay trả cùng result.

## Đánh giá và khuyến nghị

Kiến trúc Flutter/Provider/Supabase vẫn phù hợp, chưa cần thêm backend hoặc framework. Code đã đi đúng hướng repository/typed model/RPC, nhưng acceptance phải chứng minh các đường đang dùng từ UI, concurrency và session lifecycle, không chỉ helper/unit tests độc lập.

Ưu tiên C1/C2/C3 trước, rồi C4/C5 cùng regression. Giữ 24 ca hiện có, thêm ba ca DB vừa FAIL và widget/provider tests logout+delayed response+retry key. Kiểm clean và legacy thực sự cho các ca liên quan; không kết luận cả hai chỉ vì migration chạy cả hai.

Lượt này chỉ review/kiểm thử và bổ sung báo cáo, chưa sửa SQL/Dart, chưa push GitHub hoặc thay DB thật.

## Khắc phục tiếp theo

C1–C5 được xử lý bằng forward migration và thay đổi app; xem [17_BH03_REMEDIATION.md](../../17_BH03_REMEDIATION.md). Các nhận xét phía trên mô tả baseline 88dd247, không phải trạng thái sau sửa.
