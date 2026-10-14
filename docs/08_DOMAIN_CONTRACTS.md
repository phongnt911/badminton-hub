# Hợp đồng thao tác nghiệp vụ

Phiên bản 1.0 · thiết kế RPC/API để triển khai. Tên bên dưới là tên chuẩn đề xuất, chưa phải functions đã tồn tại. SQL implementation/test thuộc BH-02/BH-04/BH-05/BH-06.

## 1. Quy ước chung

Mutation nhận `request_id UUID` do client tạo và giữ cho cùng một ý định khi retry; actor lấy từ auth.uid(), không nhận từ payload. Client không gửi currentJoined/currentBalance. Validation ở DB; kiểm tra quyền cả lần gọi mới và replay. `operation_requests` ghi trong cùng transaction với kết quả. Khóa (actor,operation,request_id), payload hash: key trùng/input giống trả cùng kết quả, input khác trả IDEMPOTENCY_CONFLICT. Các actor khác nhau không dùng cùng key để nhìn dữ liệu của nhau.

Kết quả logic: `{data, request_id}`. Lỗi domain có code ổn định và thông điệp UI tiếng Việt: UNAUTHENTICATED, FORBIDDEN, NOT_FOUND, INVALID_INPUT, INVALID_STATE, VERSION_CONFLICT, CAPACITY_FULL, DUPLICATE_PARTICIPANT, DEADLINE_PASSED, PAYMENT_EXCEEDS_OUTSTANDING, NO_BILLABLE_PLAYERS, IDEMPOTENCY_CONFLICT. Có thể hiện thực bằng SQLSTATE + detail; repository ánh xạ, không parse câu lỗi tùy ý hoặc hiển thị raw SQL cho người dùng. Tài nguyên không được đọc trả NOT_FOUND/FORBIDDEN theo chính sách nhất quán, không lộ trường riêng.

Đối với thao tác đổi slot/attendance/cấu hình/chốt phí/payment, thứ tự khóa: session → player theo ID tăng dần → payment/expense → revision → ledger nguồn. Transaction quỹ manual khóa club khi cần; không lấy club lock rồi session lock trong đường khác. Thống nhất thứ tự trên toàn bộ functions để tránh deadlock. Retry lỗi serialization/deadlock có giới hạn, vẫn cùng request_id.

## 2. CLB và định danh

| Thao tác | Input chính | Quyền / hành vi |
|---|---|---|
| create_club | name, visibility, request_id | Tài khoản xác nhận email; tạo club + owner membership nguyên tử |
| update_club | club_id, expected_version nếu áp dụng, fields whitelist | Owner; không sửa owner qua hàm này |
| add_club_member | club_id, display_name, contact, user_id nullable | Owner/club host thêm member; tạo contact riêng. user_id phải theo invitation/acceptance đã xác thực |
| set_member_role | club_id, member_id, role | Owner; member đã liên kết account cho quyền có hiệu lực; audit |
| transfer_club_owner | club_id, target_member_id | Owner hiện tại; target active/account đã xác nhận, cập nhật owner và membership nguyên tử |
| link_member_account | member_id, invitation_token | Token có hạn/hash server; người được mời chấp nhận; kiểm tra không trùng, không match phone tự động |
| set_bank_account | scope, bank_code, number, name | Owner CLB hoặc host cá nhân; đặt một account active, dữ liệu private |

BH-03 tối thiểu cho owner/host thêm thành viên không account. Invitation/link tự phục vụ có thể thêm sau; không tự gán account chỉ vì người nhập SĐT giống nhau.

## 3. Buổi và đăng ký

### create_session / update_session / duplicate_session

Create nhận club_id nullable, venue_id, title, starts_at/ends_at, capacity, court_count, approval_mode, visibility, fee_mode, fee amounts, deadlines. Kiểm tra quyền create CLB; host_user_id là actor khi tạo, owner có thể giao host qua hành động riêng. Update nhận expected_version; không trùng thì VERSION_CONFLICT và yêu cầu tải lại. Không hạ capacity dưới confirmed, không sửa phí của người đã confirmed bằng thay đổi mức phí mặc định.

Duplicate nhận source_session_id và ngày/giờ mới; chỉ copy cấu hình, không người chơi/staff/payment/expense/charge/audit của buổi nguồn. Tạo draft mới, actor làm host. publish_session kiểm tra đủ cấu hình tài khoản nhận tiền và public projection; start_session chỉ published; complete_session chỉ in_progress và có active charge revision, hoặc xác nhận buổi miễn phí với khoản phải thu 0. complete không yêu cầu thu đủ tiền.

### request_join_session

Input: session_id, contact chủ động cung cấp, request_id. Yêu cầu login; đọc người dùng/membership từ DB. Lock session; kiểm tra visibility/private access, published, hạn đăng ký, không trùng. Host approval → pending. Auto confirm → confirmed nếu còn slot, nếu full → waitlisted. Fixed lưu agreed_fee_vnd khi confirmed; pending chưa chốt mức phí. Trả player_id, status, slot summary. Không tạo host phantom slot.

### add_session_player

Input: session_id, member_id nullable hoặc guest_name/contact, fee_exempt (nếu có quyền finance), request_id. Host/cohost của buổi; chọn ID member không tự match tên. Kiểm tra slot và vòng đời; published hoặc in_progress với khách tại sân. Không vượt capacity; hết chỗ trả CAPACITY_FULL hoặc host chủ động thêm vào waitlist. Fixed chốt agreed_fee khi confirmed. Guest không account không được tạo account giả.

### decide_registration / cancel_registration / accept_waitlist_invitation

Decide: host/cohost quyết định confirmed/rejected/waitlisted; lock session và player, confirmed kiểm tra lại capacity và deadline. Cancel: player riêng trước hạn hoặc host có lý do; không hủy người present/đã có payment như đăng ký thông thường. Giải phóng slot nguyên tử. Không tự đổi waitlisted → confirmed; host mời, người chấp nhận, kiểm tra lại slot. Nếu muốn auto promotion tương lai cần opt-in rõ.

### record_attendance

Input: session_id, player_id, present/no_show/not_checked_in, request_id. Host/cohost; confirmed; chỉ in_progress hoặc trước complete; nếu đã finalize thì thay attendance yêu cầu finance và refinalize, không âm thầm đổi khoản phải thu. Audit checked_in_by/time. Tự mở app của người chơi không đánh dấu đã có mặt.

## 4. Tài chính

### post_session_expense / reverse_session_expense

Quyền owner/host chính/session finance/club treasurer. Input category/title/amount. Lock session, validate, expense posted → ledger expense cùng transaction nếu club_id có giá trị. Reverse cần reason, tạo ledger đảo unique, không xóa expense. Khi đã finalize phải hiện needs_refinalization; complete khóa sửa chi phí thường, chỉ điều chỉnh qua hành động tài chính có audit.

### finalize_session_charges

Input: session_id, expected_version, reason khi revision > 1, request_id. Lock session và players; quyền finance; chỉ in_progress hoặc điều chỉnh tài chính completed. Tính từ attendance/expenses server-side, không tin số tiền chia do client gửi.

Fixed: tổng agreed fee của present, exemption 0. Split_actual: tổng posted expenses chia cho present không exempt. Nếu total > 0 và không billable player → NO_BILLABLE_PLAYERS. Total = 0 tạo charges 0 cho người present, cho phép hoàn thành buổi miễn phí. Với fixed, ghi nhận chênh thu−chi như kết quả buổi, không ép tổng phí bằng tổng expenses.

Tạo revision + tất cả charges, supersede revision cũ và audit cùng transaction. Sum charges đúng allocation_total. Kiểm tra mỗi new due >= confirmed payments của player; nếu không thì báo cần xử lý đảo/hoàn tiền trước. Re-finalize không làm payment/ledger lặp. Khi revision active thay đổi, người chơi nhìn thấy thông báo in-app/version mới.

### submit_payment / confirm_payment / reject_payment / reverse_payment

Submit: player riêng gửi amount và method bank_transfer cho active charge; amount > 0 và <= outstanding. submitted chưa cộng ledger. MVP có thể không upload biên lai, chỉ reference/note được giới hạn; receipt bổ sung sau. Không coi submitted là đã trả.

Confirm: quyền finance, lock session/player/payment; không đã confirmed/reversed; tổng confirmed + amount không vượt active due. Nếu đã confirmed cùng payment trả kết quả hiện tại, không ghi thêm. Ghi confirmed_by/time và ledger income nếu CLB, audit cùng transaction. Hai submitted có thể cùng tổng vượt due; từng confirm phải kiểm tra lại, khoản vượt bị từ chối/điều chỉnh.

Cash: finance tạo và confirm một payment trong cùng RPC `record_cash_payment`, không yêu cầu player gửi. Reject submitted cần reason, không ghi ledger. Reverse confirmed cần reason, giữ payment nhưng status reversed, tạo ledger đảo unique. Không dùng xóa bản ghi để hoàn tác. V1 chưa xử lý hoàn tiền qua ngân hàng; đảo sổ không tự chuyển tiền.

### post_manual_club_transaction / reverse_club_transaction

Chỉ owner/treasurer CLB; type direction và amount>0/title/request_id; không nhận source_payment_id/source_expense_id từ UI manual. Reverse cần reason và chỉ entry manual; entry tự sinh đảo qua thao tác nguồn để status expense/payment khớp ledger. Balance trả từ SUM DB, client không update balance.

## 5. Reads và QR

- list_public_sessions(filters,cursor,limit): public published/in_progress, thời gian phù hợp; whitelist fields.
- get_session_public_detail(id): public/unlisted tối thiểu; private phải check quyền. Không trả contacts/bank/sổ quỹ.
- get_session_management(id): đúng host/cohost, contacts; finance projection riêng nếu có quyền tiền.
- get_my_registration(id): account hiện tại, charge active/payments và tài khoản nhận tiền khi confirmed; không danh sách contacts người khác.
- get_session_finance(id), get_club_ledger(club_id): quyền theo ma trận; phân trang.
- get_payment_instructions(player_id): đúng player/finance, trả bank snapshot, outstanding, mã tham chiếu duy nhất. UI dùng VietQRHelper và chỉ tạo QR khi outstanding > 0; không có ngân hàng thì báo cấu hình thiếu.

Danh sách mặc định limit 20, tối đa 100; cursor theo thời gian+ID ổn định. Tìm buổi host lọc club/date/lifecycle, không đọc tất cả lịch sử.

## 6. Các tình huống phải kiểm thử

Slot cuối có 2 request khác nhau; cùng request retry sau timeout; pending không chiếm chỗ; hủy/duyệt đồng thời; capacity update khi đầy; đăng ký lại cancelled không thêm ID; cohost không tự miễn tiền; actor giả không được chấp nhận; player không tự confirm; 2 payment cùng confirm không thu dư; post expense/ledger rollback toàn bộ khi lỗi; reverse hai lần không đảo hai lần; refinalize không mất tiền đã thu; payload/view không rò contact/bank qua public API.
