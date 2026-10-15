# BH-03 — CLB, thành viên và tài khoản nhận tiền

Ngày 15/10/2026. Đây là đầu bài triển khai, chưa phải chức năng đã có. Baseline chuẩn bị: f61f840 (schema remediation 11aaec7). IDE tiếp tục từ HEAD và thay đổi local thực tế, không reset hoặc làm lại BH-01/BH-02. Tài liệu này làm rõ BH-03; nếu hợp đồng khác chưa thống nhất thì báo đúng điểm xung đột trước khi sửa phần liên quan.

## 1. Mục tiêu và phạm vi

Một host đã đăng nhập tạo CLB, thêm thành viên từ Zalo chưa có account, xem danh sách theo quyền, cập nhật thông tin CLB và cấu hình ngân hàng nhận tiền. Dữ liệu bền vững, RPC nguyên tử, có audit/idempotency. Số dư quỹ chỉ đọc đúng quyền, chưa ghi thu/chi trong BH-03.

Áp dụng nghiên cứu [Vmito/Vụt](14_PRODUCT_LEARNINGS_VMITO_VUT.md): vận hành CLB ít bước, phân biệt thao tác quản lý với view thành viên; tài khoản ngân hàng private. Không thêm chat, OTP, push, GPS, camera hoặc SDK chỉ vì report có tích hợp.

Không triển khai tạo buổi/đăng ký/thu tiền/quỹ mutation, invoice, phí tháng hoặc xoay tua ở ticket này. Chuyển các nút demo ghi quỹ sang trạng thái chưa khả dụng với nhãn rõ thay vì gọi API sai. Không xóa code tiện ích khác ngoài phần tích hợp bị ảnh hưởng.

## 2. Điều kiện bắt đầu

1. git status/HEAD, kiểm tra nhánh và changes chưa commit của IDE; pull --ff-only khi sạch. Nếu local có sửa, giữ và tích hợp có kiểm soát, không reset/discard.
2. Đọc 00/01/02/03/04/08/09/11/14 và code club/auth hiện có; kiểm tra file migration BH-03 đã được tạo chưa để tránh bản trùng.
3. Kiểm tra BH-02 prerequisites trên local/staging: migration sạch + legacy, read finance/private receiver và helper ACL. Kết quả tác giả báo 47/47 trên 11aaec7 là evidence baseline, lượt tài liệu này chưa chạy lại độc lập; không tuyên bố mới đã kiểm chứng toàn bộ Supabase.
4. Nếu phát hiện regression nền, ghi blocker và sửa phụ thuộc hẹp có test; vẫn làm các phần độc lập. Không quay về viết lại schema/app hoặc chờ vô hạn.
5. Task này không bao gồm apply production; tạo migration mới bằng CLI migration new (đọc --help) nếu chưa có. Không chỉnh migration đã apply/shared. Dựng DB test với toàn chuỗi migrations đúng thứ tự.

## 3. Quyền và dữ liệu

| Chủ thể | CLB/thành viên | Liên hệ | Ngân hàng/quỹ |
|---|---|---|---|
| Owner CLB | Tạo/sửa CLB, thêm member, đổi role hợp lệ | Quản lý contact của CLB | Cấu hình account CLB; xem quỹ |
| Club host active | Xem/thêm member, cập nhật contact; không cấp role | Đọc contact vận hành | Không tự cấu hình bank/quỹ CLB |
| Treasurer active | Xem danh sách tên/role/status cần dùng | Không đọc phone/note của người khác | Xem account CLB và quỹ; không đổi account |
| Member active | Xem CLB, tên/role/status thành viên CLB mình | Chỉ contact bản ghi mình liên kết | Không đọc account CLB/quỹ mặc định |
| Người ngoài/anon | Public summary nếu có, không danh sách nội bộ | Không | Không |
| Host cá nhân | Không nhờ quyền này để vào CLB khác | Chỉ dữ liệu thuộc quyền | Cấu hình host_bank_accounts của chính mình |

Owner lấy từ clubs.owner_user_id và membership đồng bộ, không từ owner_phone. Người chưa liên kết account chỉ là member record, không tạo tài khoản Auth giả và không cấp quyền thực tế bằng tên/SĐT. app_roles không được dùng làm quyền toàn năng đọc tài chính/contact CLB mặc định.

Trong scope MVP BH-03, thêm thành viên mới theo tên/contact với user_id=NULL. Thêm theo user_id chỉ được khi có cơ chế lời mời/chấp nhận đã được xác minh trong repo; nếu chưa có thì API từ chối và UI không cho nhập UUID tùy ý. Chưa bắt buộc xây self-service invitation/account linking cho ticket này. Fixture DB có linked accounts dùng để test role, không thay thế acceptance thực tế. Báo rõ giới hạn này khi kết thúc.

## 4. RPC chuẩn và invariant

Mutation dùng actor=auth.uid(), yêu cầu tài khoản thật/email xác nhận theo Auth policy; không tin actor/owner/confirmed từ client. request_id bắt buộc, cùng key/payload retry cùng kết quả, khác payload lỗi. Audit ghi trong transaction và không chứa SĐT/account thô. Helpers audit/idempotency chỉ nội bộ, REVOKE PUBLIC/app roles; nếu SECURITY DEFINER cần thiết thì search_path cố định, schema-qualified, explicit EXECUTE và check quyền bên trong. Không dùng SECURITY DEFINER cho mọi hàm một cách máy móc.

| RPC | Input chính | Invariant / output |
|---|---|---|
| create_club | name, description nullable, visibility private/public, request_id | owner_user_id=actor; club + active owner member atomic; retry không tạo CLB kép; trả club DTO/id và role |
| update_club | club_id, name/description/visibility whitelist, request_id | Chỉ owner; không nhận owner_user_id/balance/role; khóa club; trả DTO đã lưu |
| add_club_member | club_id, display_name, phone/contact_note optional, request_id | Owner/host active; tạo member role=member + contact riêng atomic; kiểm club active; không gộp tên/phone; user_id chỉ qua acceptance hợp lệ |
| update_club_member_contact | club_id, member_id, display_name, phone/note, request_id | Owner/club host; member đúng CLB; không nhận role/user_id; không xóa lịch sử |
| set_club_member_role | club_id, member_id, role host/treasurer/member, request_id | Chỉ owner; target linked account active; không sửa owner qua endpoint này; role không account không có hiệu lực và endpoint từ chối cấp role có quyền |
| set_club_bank_account | club_id, bank_code, account_number, account_name, request_id | Chỉ owner; lock club, một active account; account cũ inactive giữ lịch sử; không sửa receiver_snapshot của session đã chốt |
| set_host_bank_account | bank_code, account_number, account_name, request_id | Chỉ actor; lock profile/nguồn quyền tương ứng để serialize; một active account; không nhận user_id khác |
| get_club_detail | club_id | Chỉ quyền phù hợp; DTO không join vô điều kiện phone/bank/balance |
| list_club_members | club_id, cursor, limit | Member active/owner/host theo quyền; contact chỉ owner/host hoặc bản ghi mình; phân trang ổn định |
| get_club_bank_account / get_host_bank_account | club_id hoặc scope self | Role bank theo bảng trên; tài khoản có dữ liệu thật không trả vào public summary |

Nếu repo có API tên khác tương đương, giữ tương thích hoặc thêm mapping repository rõ ràng; không tạo hai bộ mutation trùng. Mỗi RPC trả state/ID/DTO được lưu, không báo thành công từ UPDATE 0 hàng. Invalid/missing/inactive/foreign target phải lỗi rõ, không silently success.

Owner role chỉ thay qua transfer_club_owner transaction chuyên biệt nếu triển khai; set role không được demote owner, tạo owner thứ hai hoặc bỏ CLB không owner. UI BH-03 có thể hoãn chuyển owner nhưng phải chặn các đường vòng; không hiện nút giả hoạt động. Profile của người đăng nhập có trước migration phải tồn tại/backfill có kiểm soát để FK create_club không lỗi; không dựa chỉ trigger cho user mới.

Cập nhật bank song song không được tạo hai active hoặc lỗi unique không có xử lý. Do chưa có webhook xác minh account, gọi đây là cấu hình host cung cấp, không gắn badge ngân hàng đã xác minh. Phân biệt active account đang cấu hình với snapshot buổi đã tồn tại.

## 5. Flutter và UX

- Model typed Club, ClubMember, BankAccount, role/status; không truyền Map/dynamic khắp UI. Chỉ thêm file cần dùng theo architecture hiện có.
- ClubRepository inject SupabaseClient; calls RPC/projection theo hợp đồng; không dùng owner_phone, clubs.bank_account, clubs.balance hoặc type thu/chi cũ làm schema đích. Không direct write bank/role/club/member từ widget/provider.
- ClubProvider inject repository, state list/detail riêng, loading/data/empty/error và submitting; route detail gắn clubId hoặc chống response cũ ghi vào CLB mới. Logout clear private data; dispose/subscriptions đúng vòng đời.
- ClubsScreen: khách xem summary hợp lệ nếu đã có và nút login để quản lý; user thấy CLB của mình, tạo CLB chỉ cần tên/mô tả/privacy. Không bắt nhập phone/bank ngay lúc tạo.
- ClubDetail: tabs Tổng quan/Thành viên/Tài khoản nhận tiền, phần quỹ chỉ owner/treasurer. Ẩn nút theo role nhưng DB vẫn check. Tạo/đổi role chỉ khi linked identity hợp lệ; người chưa account có nhãn rõ.
- Form thêm member: tên bắt buộc, contact tùy chọn, trim/validation, không phone mặc định giả và không gộp trùng tên tự động. Không gọi người chưa account là thiết bị offline sync.
- Account form: bank code/account/name rõ, số tài khoản dùng text giữ leading zeros. Lỗi network, schema/API chưa có, permission denied hiển thị error+retry tiếng Việt; không biến thành empty. Pending request chống bấm lặp và retry dùng cùng request_id.
- Quỹ đọc tổng ledger qua view/RPC đã bảo vệ. Không coi số 0 do RLS lọc hết là balance thật của người không có quyền; không hiện thẻ quỹ khi không được phép.
- Settings tài khoản cá nhân có thể đặt host bank; hiển thị QR/payment của buổi thuộc BH-06, không mở rộng trong BH-03.

## 6. Kế hoạch từng phần

- BH-03A: migration mới, RPC/grants/RLS/read DTO + DB tests. Chưa code API mà chỉ tạo stub không tính hoàn thành.
- BH-03B: models/repository/provider với test double và test state/error/retry/logout/club switch.
- BH-03C: UI tạo/xem CLB, member và bank; widget tests theo role, không có nút gọi chức năng demo chưa triển khai.
- BH-03D: kiểm thử tích hợp local/staging, chạy lại BH-02 regression, cập nhật nhật ký và commit/push từng nhóm. Không làm BH-04/push/GPS/chat trong lượt này.

## 7. Acceptance bắt buộc

| Nhóm | Ca tối thiểu |
|---|---|
| Atomic/idempotent | Create club có đúng một owner active; lỗi giữa member/contact rollback; retry không tạo bản ghi kép, key khác payload bị chặn |
| Auth/role | anon/actor hết phiên bị chặn mutation; member/host/treasurer không self-escalate; owner A không sửa CLB B; không đổi owner qua set role; membership inactive không có quyền |
| Privacy | Member/treasurer không đọc contact người khác qua table/view/RPC, kể cả phone legacy; owner/host đọc đúng; public không bank/quỹ/member list |
| Account identity | Guest tạo user_id NULL, không account giả; nhập user_id không có consent bị từ chối; không gộp theo phone; user đã tồn tại Auth trước migration tạo được CLB |
| Bank | Owner tự cấu hình, host/member/treasurer không đổi bank CLB; treasurer đọc hợp lệ; host bank chỉ self; concurrent update một active; giữ history và không đổi snapshot buổi |
| UI/state | Loading/empty/error/submitting, no fake success, retry giữ request key, switch CLB không lộ data cũ, logout clear, không nhập bank lúc tạo CLB |
| Regression | BH-02 baseline+extended chạy lại với chuỗi migrations, đồng thời finance vẫn thấy tiền và private contact/receiver vẫn chặn |
| Release evidence | flutter analyze/tests liên quan; DB role tests thực; ghi SHA/hash/worktree, môi trường và PASS/FAIL/NOT RUN; không gọi đầy đủ nghiệm thu khi thiếu staging/HTTP/JWT đã xác định là gate |

DB fixtures có email_confirmed_at/claims tương thích cách kiểm email xác nhận thật của implementation, không bỏ check production chỉ để Auth stub pass. Tests bằng role app, không dùng postgres để chứng minh quyền. Các ca thiếu môi trường phải NOT RUN có lý do, không bịa số lượng pass.

## 8. Prompt tiếp tục cho IDE

> Tiếp tục BH-03 theo docs/15_BH03_IMPLEMENTATION_HANDOFF.md. Đọc AGENTS.md, 00/03/08/09/11/14/15 và code club/auth/migrations hiện có. Trước hết kiểm git status, HEAD, migration BH-03 và thay đổi đang dở; giữ công việc đã làm, không reset hoặc sinh migration/API trùng. Đồng bộ origin/main khi an toàn, tích hợp theo diff nếu có sửa local. Nêu phạm vi/file/acceptance rồi triển khai lần lượt BH-03A→D, không dừng ở kế hoạch hoặc scaffold. Giữ Flutter/Provider/Supabase; chỉ SECURITY DEFINER khi cần và bảo vệ ACL/actor/role. Club+owner và member+contact nguyên tử, request_id chống lặp; owner role không sửa qua endpoint role thường. Guest không account/user_id tùy tiện; linking chỉ qua acceptance đã xác minh, nếu chưa có thì hoãn UI link và ghi giới hạn. Account ngân hàng private, một active theo scope, số tài khoản giữ leading zeros, không sửa snapshot buổi cũ. Sửa model/repository/provider/UI để bỏ cột demo và direct writes; error/retry/submitting/clear private state đúng. Quỹ chỉ read theo quyền, mutation BH-06 chưa mở. Không thêm push/chat/GPS hoặc thay schema không liên quan. Tạo migration mới đúng CLI nếu chưa có, kiểm toàn chuỗi trên local/staging, chạy BH-02 regression + ca BH-03 và Flutter tests/analyze. Ghi tested SHA/migration hash/worktree và PASS/FAIL/NOT RUN, không áp production hoặc báo done thiếu bằng chứng. Commit/push các nhóm thay đổi liên quan theo yêu cầu này và báo SHA cùng phần còn thiếu.
