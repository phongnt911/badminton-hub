# Hợp đồng thao tác nghiệp vụ

> **Hiện hành 16/10/2026:** Các đề xuất C1-01..04 đã được chủ dự án duyệt và cập nhật ở §12; phần finance BH-06 vẫn là hợp đồng đích. BH-05 đạt review tích hợp tại `d769531`; hồi quy main `3a34883`: analyze sạch, 137 Flutter + 251 DB. Tiếp theo BH-06. Chỉ kiểm thử local/PostgreSQL cô lập; chưa apply staging/production, chưa HTTP/JWT thật, thiết bị/browser e2e, backup/restore hoặc concurrency qua HTTP. [Trạng thái và xác nhận sau audit](23_DOC_AUDIT_FOLLOWUP.md).

Phiên bản 1.1 · yêu cầu đích và hợp đồng RPC đã triển khai. BH-03/04/05 đã có migration và kiểm thử PostgreSQL cô lập; §10–12 ghi chi tiết hiện thực. Các thao tác ngoài phạm vi này, nhất là finance BH-06, vẫn là yêu cầu để triển khai; không suy ra mọi tên ở §1–9 đã tồn tại trên DB live.

## 1. Quy ước chung

Mutation nhận `request_id UUID` do client tạo và giữ cho cùng một ý định khi retry; actor lấy từ auth.uid(), không nhận từ payload. Client không gửi currentJoined/currentBalance. Validation ở DB; kiểm tra quyền cả lần gọi mới và replay. `operation_requests` ghi trong cùng transaction với kết quả. Khóa (actor,operation,request_id), payload hash: key trùng/input giống trả cùng kết quả, input khác trả IDEMPOTENCY_CONFLICT. Các actor khác nhau không dùng cùng key để nhìn dữ liệu của nhau.

Kết quả logic: `{data, request_id}`. Lỗi domain có code ổn định và thông điệp UI tiếng Việt: UNAUTHENTICATED, FORBIDDEN, NOT_FOUND, INVALID_INPUT, INVALID_STATE, VERSION_CONFLICT, CAPACITY_FULL, DUPLICATE_PARTICIPANT, DEADLINE_PASSED, PAYMENT_EXCEEDS_OUTSTANDING, NO_BILLABLE_PLAYERS, IDEMPOTENCY_CONFLICT, BILLING_NOT_FINALIZED, BILLING_STALE, INVITATION_REQUIRED, INVITATION_EXPIRED, INVITATION_REVOKED. Có thể hiện thực bằng SQLSTATE + detail; repository ánh xạ, không parse câu lỗi tùy ý hoặc hiển thị raw SQL cho người dùng. Tài nguyên không được đọc trả NOT_FOUND/FORBIDDEN theo chính sách nhất quán, không lộ trường riêng.

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

Duplicate nhận source_session_id và ngày/giờ mới; chỉ copy cấu hình, không người chơi/staff/payment/expense/charge/audit của buổi nguồn. Tạo draft mới, actor làm host. publish_session kiểm tra đủ cấu hình tài khoản nhận tiền và public projection; start_session chỉ published; complete_session chỉ in_progress và có active charge revision current theo billing_input_version; buổi miễn phí cũng cần revision current với charges 0. complete không yêu cầu thu đủ tiền.

### request_join_session

Input: session_id, contact chủ động cung cấp, request_id. Yêu cầu login; đọc người dùng/membership từ DB. Lock session; kiểm tra visibility/private access, published, hạn đăng ký, không trùng. Host approval → pending. Auto confirm → confirmed nếu còn slot, nếu full → waitlisted. Fixed lưu agreed_fee_vnd khi confirmed; pending chưa chốt mức phí. Trả player_id, status, slot summary. Không tạo host phantom slot.

### add_session_player

Input: session_id, member_id nullable hoặc guest_name/contact, fee_exempt (nếu có quyền finance), request_id. Host/cohost của buổi; chọn ID member không tự match tên. Kiểm tra slot và vòng đời; published hoặc in_progress với khách tại sân. Không vượt capacity; hết chỗ trả CAPACITY_FULL hoặc host chủ động thêm vào waitlist. Fixed chốt agreed_fee khi confirmed. Guest không account không được tạo account giả.

### decide_registration / cancel_registration / accept_waitlist_invitation

Decide: host/cohost quyết định confirmed/rejected/waitlisted; lock session và player, confirmed kiểm tra lại capacity và deadline. Cancel: player riêng trước hạn hoặc host có lý do; không hủy người present/đã có payment như đăng ký thông thường. Giải phóng slot nguyên tử. Không duyệt thẳng waitlisted → confirmed; dùng invitation issue/accept và kiểm tra lại slot theo phần 7. Nếu muốn auto promotion tương lai cần opt-in rõ.

### record_attendance

Input: session_id, player_id, present/no_show/not_checked_in, request_id. Host/cohost; confirmed; chỉ lifecycle=in_progress; nếu đã finalize thì thay attendance yêu cầu finance và refinalize, không âm thầm đổi khoản phải thu. Audit checked_in_by/time. Tự mở app của người chơi không đánh dấu đã có mặt.

## 4. Tài chính

### post_session_expense / reverse_session_expense

Quyền owner/host chính/session finance/club treasurer. Input category/title/amount. Lock session, validate, expense posted → ledger expense cùng transaction nếu club_id có giá trị. Reverse cần reason, tạo ledger đảo unique, không xóa expense. Tăng billing_input_version cùng transaction; nếu đã finalize thì billing_state trở thành stale; complete khóa sửa chi phí thường, chỉ điều chỉnh qua hành động tài chính có audit.

### finalize_session_charges

Input: session_id, expected_version, expected_billing_input_version, reason khi revision > 1, request_id. Lock session và players; quyền finance; chỉ in_progress hoặc điều chỉnh tài chính completed. Tính từ attendance/expenses server-side, không tin số tiền chia do client gửi.

Fixed: tổng agreed fee của present, exemption 0. Split_actual: tổng posted expenses chia cho present không exempt. Nếu total > 0 và không billable player → NO_BILLABLE_PLAYERS. Total = 0 tạo charges 0 cho người present, cho phép hoàn thành buổi miễn phí. Với fixed, ghi nhận chênh thu−chi như kết quả buổi, không ép tổng phí bằng tổng expenses.

Kiểm tra expected_billing_input_version; tạo revision.source_version bằng billing_input_version + tất cả charges, supersede revision cũ và audit cùng transaction. Sum charges đúng allocation_total. Kiểm tra mỗi new due >= confirmed payments của player; nếu không thì báo cần xử lý đảo/hoàn tiền trước. Re-finalize không làm payment/ledger lặp. Khi revision active thay đổi, người chơi nhìn thấy thông báo in-app/version mới.

### submit_payment / confirm_payment / reject_payment / reverse_payment

Submit: yêu cầu billing_state=current; player riêng gửi amount và method bank_transfer cho active charge; amount > 0 và <= outstanding. submitted chưa cộng ledger. MVP có thể không upload biên lai, chỉ reference/note được giới hạn; receipt bổ sung sau. Không coi submitted là đã trả.

Confirm: quyền finance, lock session/player/payment; yêu cầu billing_state=current cho xác nhận mới; không đã confirmed/reversed; tổng confirmed + amount không vượt active due. Nếu đã confirmed cùng payment trả kết quả hiện tại, không ghi thêm. Ghi confirmed_by/time và ledger income nếu CLB, audit cùng transaction. Hai submitted có thể cùng tổng vượt due; từng confirm phải kiểm tra lại, khoản vượt bị từ chối/điều chỉnh.

Cash: yêu cầu billing_state=current; finance tạo và confirm một payment trong cùng RPC `record_cash_payment`, không yêu cầu player gửi. Reject submitted cần reason, không ghi ledger. Reverse confirmed cần reason, giữ payment nhưng status reversed, tạo ledger đảo unique. Không dùng xóa bản ghi để hoàn tác. V1 chưa xử lý hoàn tiền qua ngân hàng; đảo sổ không tự chuyển tiền.

### post_manual_club_transaction / reverse_club_transaction

Chỉ owner/treasurer CLB; type direction và amount>0/title/request_id; không nhận source_payment_id/source_expense_id từ UI manual. Reverse cần reason và chỉ entry manual; entry tự sinh đảo qua thao tác nguồn để status expense/payment khớp ledger. Balance trả từ SUM DB, client không update balance.

## 5. Reads và QR

- list_public_sessions(filters,cursor,limit): public published/in_progress, thời gian phù hợp; whitelist fields.
- get_session_public_detail(id): public/unlisted tối thiểu; private phải check quyền. Không trả contacts/bank/sổ quỹ.
- get_session_management(id): đúng host/cohost, contacts; finance projection riêng nếu có quyền tiền.
- get_my_registration(id): account hiện tại, charge active/payments và tài khoản nhận tiền khi confirmed; không danh sách contacts người khác.
- get_session_finance(id), get_club_ledger(club_id): quyền theo ma trận; phân trang.
- get_payment_instructions(player_id): đúng player/finance, chỉ khi billing_state=current, trả bank snapshot, outstanding, source_version và mã tham chiếu duy nhất. UI dùng VietQRHelper và chỉ tạo QR khi outstanding > 0; không có ngân hàng thì báo cấu hình thiếu.

Danh sách mặc định limit 20, tối đa 100; cursor theo thời gian+ID ổn định. Tìm buổi host lọc club/date/lifecycle, không đọc tất cả lịch sử.

## 6. Các tình huống phải kiểm thử

Slot cuối có 2 request khác nhau; cùng request retry sau timeout; pending không chiếm chỗ; hủy/duyệt đồng thời; capacity update khi đầy; đăng ký lại cancelled không thêm ID; cohost không tự miễn tiền; actor giả không được chấp nhận; player không tự confirm; 2 payment cùng confirm không thu dư; post expense/ledger rollback toàn bộ khi lỗi; reverse hai lần không đảo hai lần; refinalize không mất tiền đã thu; payload/view không rò contact/bank qua public API.

## 7. Hợp đồng bổ sung v1.1

### Chống bản chốt lỗi thời

Các thao tác ảnh hưởng tiền theo 03_DATABASE tăng billing_input_version trong transaction, không chỉ hiện banner. finalize kiểm tra phiên bản dưới lock rồi trả revision_id/source_version. get_payment_instructions, submit_payment, xác nhận payment mới, record_cash_payment và complete_session phải kiểm tra current ở server. Không revision → BILLING_NOT_FINALIZED; lệch phiên bản → BILLING_STALE. QR từng tạo có thể đã được lưu ngoài app, không thể thu hồi ảnh; UI không tiếp tục phát hành QR cũ và host phải đối chiếu số tiền thật khi xử lý chuyển khoản trễ.

Retry cùng request_id của thao tác đã committed trả kết quả cũ sau kiểm tra quyền; không thu thêm hoặc kiểm tra stale để biến thành công trước đó thành ghi mới. Confirm payment đã confirmed cũng trả kết quả hiện tại, không ghi ledger lần hai. Đảo/reject thanh toán và đọc lịch sử vẫn được phép khi stale theo quyền; chúng phục vụ reconciliation, không sửa khoản phải thu. UI đọc stale không hiện khoản cũ như số phải thanh toán cuối cùng.

record_attendance sau finalize và add/cancel confirmed roster có ảnh hưởng tiền cần finance; giữ dữ liệu đã thu và làm revision stale. Muốn thay đổi attendance khiến người đã đóng trở thành no_show, vẫn kiểm tra phần đã thu lúc finalize, không bỏ người đó khỏi đối chiếu.

### invite_waitlisted_player / revoke_waitlist_invitation

Input: session_id, player_id, expires_at tùy chọn, request_id. Host/cohost; player waitlisted, session published, trước deadline; expires_at mặc định min(now()+30 phút, registration_deadline, starts_at), phải > now(). Lock session/player, hết hạn lời mời cũ trước khi tạo mới; trả invitation_id/expiry. Lời mời không giữ slot. Revoke cần đúng quyền và pending invitation; accepted phải dùng cancel registration.

### accept_waitlist_invitation

Input: session_id, invitation_id, request_id; khách không account thêm consent_note khi host thực hiện. Self: auth.uid() khớp user_id player; host_recorded: host/cohost đúng session và guest chưa liên kết account, có consent_note không rỗng. Lock session → player → invitation; kiểm tra người chơi waitlisted, invitation pending và chưa hết hạn/thu hồi, session published và hạn đăng ký, còn capacity. Thành công: player confirmed, agreed_fee chốt, invitation accepted + accepted_by/time/mode, audit cùng transaction. Đã accepted và player vẫn confirmed: retry hợp lệ trả kết quả, không thêm slot. Hết chỗ trả CAPACITY_FULL, không chuyển confirmed; lời mời còn pending tới expiry để có thể thử lại. Lời mời không có/hết hạn/thu hồi trả code tương ứng. Hủy player/buổi thu hồi mọi invitation pending của đối tượng trong cùng transaction.

### Dữ liệu tải và mutation

Repository không xem UPDATE 0 hàng là thành công; mọi RPC mutation trả ID/state/version để UI đối chiếu. Khi bảng/RPC chưa có, hiển thị schema_unavailable có thông điệp tiếng Việt, không biến thành empty và không fallback mở quyền. Luồng legacy chưa được chuyển đổi phải được đánh dấu demo/không khả dụng, không cho ghi không kiểm soát lên DB thật.

## 8. Read/filter và link sau nghiên cứu đối thủ

list_public_sessions chỉ trả whitelist của public published/in_progress; nhận area, khoảng starts_at/ends_at, available_only, fee_mode và cursor/limit. Lọc khoảng thời gian là overlap: session.starts_at < filter_end AND session.ends_at > filter_start; ngày chọn ở UI đổi từ giờ Việt Nam sang UTC. Không có filter thì dùng cửa sổ ngày hợp lý trên UI, không tải hết lịch sử. Exact SQL/index được kiểm theo query thật khi triển khai BH-04.

available_only dựa capacity minus tổng confirmed DB, không count theo player RLS. Phí split_actual là dự kiến, không giả thành giá cố định để lọc. Unlisted chỉ detail theo ID, private check quyền; URI/callback không thay auth. Chính sách receiver/contacts giữ như review và đặc tả, không mở raw data để phục vụ filter. Không thêm API chat/push/bank theo endpoint trích trong report.

## 9. Làm rõ BH-03

[15_BH03_IMPLEMENTATION_HANDOFF.md](15_BH03_IMPLEMENTATION_HANDOFF.md) định nghĩa create/update club, member/contact/role và bank theo scope. create_club không yêu cầu bank/phone; ClubOwner lấy từ actor. Guest member mới user_id NULL; user_id online chỉ qua acceptance đã xác minh, chưa có thì từ chối thay vì tự gán. set_club_member_role chỉ host/treasurer/member, không thay owner. update contact không nhận role/user_id. Bank mutations khóa scope, giữ account inactive/history và session snapshot. Helper nội bộ không được client gọi thẳng. Read DTO trả contact/bank/quỹ theo ma trận, không lấy RLS-filtered zero làm số dư hợp lệ cho người không có quyền.

## 10. BH-03 sau sửa C1–C5

Forward migration bắt buộc request_id cho mọi BH-03 mutation; idempotency check khóa theo actor/operation/request trước side effect và hash canonical toàn bộ payload có scope. Same key khác payload phải conflict, không dùng hash nối chuỗi thiếu field. UI provider giữ key qua retry cùng ý định, không chỉ disable nút; caller bên ngoài phải gửi key. add_club_member chưa có acceptance API thì từ chối user_id không NULL. Auth identity thay đổi xóa private club state và loại response phiên cũ. Chi tiết triển khai/giới hạn ở [17_BH03_REMEDIATION.md](17_BH03_REMEDIATION.md).

## 11. BH-04 buổi chơi (đã triển khai — migration `20261015163000_bh04_sessions.sql`)

RPC mutation (đều `SECURITY DEFINER`, `search_path = public, pg_temp`, bắt buộc `p_request_id`, idempotency theo actor/operation/request + hash canonical, có audit, `REVOKE PUBLIC/anon` + `GRANT authenticated`):

- `create_session(p_venue_id, p_title, p_starts_at, p_ends_at, p_capacity, p_court_count, p_club_id?, p_description?, p_level_requirement?, p_visibility, p_approval_mode, p_fee_mode, p_member_fee_vnd?, p_guest_fee_vnd?, p_registration_deadline?, p_cancellation_deadline?, p_request_id)` → JSONB chi tiết. Tạo `lifecycle='draft'`, `version=1`, `host_user_id=actor`. Gắn CLB thì actor phải là owner/host của CLB active; không gắn thì buổi vãng lai. `starts_at` phải ở tương lai; `ends_at > starts_at` (cho phép qua nửa đêm); `fee_mode='fixed'` đòi đủ hai mức phí.
- `update_session(p_session_id, p_version, ...)` → JSONB. Chỉ management; `FOR UPDATE` + `p_version <> version` ⇒ `VERSION_CONFLICT`; chặn khi `lifecycle ∉ {draft, published}` (`INVALID_STATE`); tăng `version`.
- `set_session_lifecycle(p_session_id, p_action, p_request_id)` với `p_action ∈ {publish, cancel}`. Publish chỉ từ `draft` và `starts_at > now()`; cancel từ `{draft, published, in_progress}`.
- `duplicate_session(p_session_id, p_starts_at, p_ends_at, p_request_id)` → JSONB draft mới; chỉ copy cấu hình, **không** copy `session_players`/`session_player_contacts`/charge; actor thành host.

RPC đọc (projection whitelist, không lộ contact/bank/snapshot):

- `get_session_public_detail(p_session_id)` — `anon, authenticated`. Public/unlisted đọc theo link; `visibility='private'` **hoặc** `lifecycle='draft'` yêu cầu đăng nhập + quyền (host/management/finance/member CLB/participant). Trả cờ `can_manage`, `can_view_finance`, `is_host`, `version`, `my_registration`, `confirmed_count`.
- `list_my_sessions(p_limit, p_offset)` — `authenticated`; buổi host/management/finance; phân trang trước aggregate, `offset>0` trả phần còn lại (không NULL).
- `list_public_sessions(p_area?, p_from?, p_to?, p_fee_mode?, p_only_available?, p_limit, p_offset)` — `anon, authenticated`; đọc `public_session_summary` (chỉ public + published/in_progress), lọc khu vực/khoảng ngày/còn chỗ/fee_mode (PD-02).
- `list_session_players(p_session_id, p_limit, p_offset)` — chỉ management (finance **không** đọc, F7); phân trang; trả SĐT cho management.

Helper `validate_session_config(...)` dùng chung và bị `REVOKE` khỏi mọi role client. Thời gian lưu UTC (`timestamptz`); UI đổi sang `Asia/Ho_Chi_Minh` (+07) qua `lib/core/time_utils.dart`. Link tài nguyên nội bộ `/sessions/:id` kiểm hợp lệ bằng `lib/core/app_routes.dart` (allowlist scheme/host/path/query, UUID bắt buộc); chi tiết và giới hạn ở [20_BH04_HANDOFF.md](20_BH04_HANDOFF.md).

### BH-04 sau review R1–R4

Lifecycle idempotency hash chỉ từ session_id/action đầu vào; retry cùng key trả kết quả cũ dù DB version đã tăng. Client giữ key khi chưa rõ kết quả, xóa key khi có response thành công và tạo key mới cho ý định tiếp theo. Roster có loading/error/retry riêng. Web route `/sessions/:id` nối vào MaterialApp; URL chia sẻ phải có origin (APP_BASE_URL hoặc web origin), hosting cần fallback index.html. Chi tiết giới hạn trong 21_BH04_REMEDIATION.

## 12. BH-05 đăng ký / duyệt / huỷ / lời mời (đã triển khai — migration `20261015170500_bh05_registrations.sql`)

Migration nối tiếp chuỗi v1.1 (không sửa lịch sử migration cũ). Mọi RPC mutation: `SECURITY DEFINER`, `search_path = public, pg_temp`, bắt buộc `p_request_id`, idempotency theo actor/operation/request + hash canonical chỉ từ input ổn định, có audit, `REVOKE PUBLIC/anon` + `GRANT authenticated`. Ghi bộ đếm/số dư/tác nhân audit chỉ ở phía DB. Chỉ `confirmed` giữ chỗ; `pending`/`waitlisted` không giữ slot và không đọc thông tin ngân hàng/QR.

Cập nhật hiện hành 16/10/2026 theo các đề xuất C1-01..04 đã được chủ dự án duyệt. Bốn migration áp dụng theo thứ tự:

1. [`20261015170500_bh05_registrations.sql`](../supabase/migrations/20261015170500_bh05_registrations.sql): đăng ký, điểm danh, lời mời và helper/projection.
2. [`20261016090000_bh05_review_fixes.sql`](../supabase/migrations/20261016090000_bh05_review_fixes.sql): thay định nghĩa add/decide/cancel/accept để gate finance; bảo vệ capacity trong update_session.
3. [`20261016091000_bh05_a3_cancel_revokes_invitations.sql`](../supabase/migrations/20261016091000_bh05_a3_cancel_revokes_invitations.sql): huỷ buổi thu hồi lời mời pending trong cùng transaction.
4. [`20261016100000_bh05_start_session.sql`](../supabase/migrations/20261016100000_bh05_start_session.sql): bổ sung start_session. Không sửa các migration trước.

Có 10 RPC BH-05: 9 mutation và 1 đọc, ngoài RPC `list_session_players` được mở rộng. Kết quả trả trực tiếp JSONB, không phải mọi RPC dùng cùng một object:

| RPC | Kết quả thành công |
|---|---|
| request_join_session, add_session_player, decide_registration, cancel_registration, record_attendance | `{player_id, session_id, registration_status, attendance_status, participant_type, fee_exempt, agreed_fee_vnd, confirmed_count, capacity, seats_left, session_version}` (kết quả đăng ký R) |
| invite_waitlisted_player | `{invitation_id, session_id, player_id, status, invited_at, expires_at}`, status=pending; không có các trường R hoặc invitation_status |
| revoke_waitlist_invitation | `{invitation_id, session_id, player_id, status, expires_at}`, status=revoked; không có invited_at, các trường R hoặc invitation_status |
| accept_waitlist_invitation | R cộng `{invitation_id, invitation_status}`, invitation_status=accepted |
| get_my_waitlist_invitation | Object lời mời như invite hoặc SQL NULL nếu không có lời mời pending chưa hết hạn của chính actor |
| start_session | Projection `get_session_public_detail(p_session_id)` (§11), gồm id/lifecycle/version/can_manage/my_registration; không phải R |

Các mutation bên dưới bắt buộc `p_request_id UUID` khác NULL dù mặc định SQL là NULL; thiếu trả `INVALID_INPUT` (22023). Các tham số có `?` là nullable/default NULL; add có mặc định `p_fee_exempt=FALSE`, `p_allow_waitlist=FALSE`. Tên/thứ tự/kiểu SQL, ACL và mã lỗi của cả 10 RPC đã được đối chiếu trong [báo cáo C1](reviews/bh05/doc_audit_after_bh05.md); báo cáo là snapshot trước cập nhật, kết quả áp dụng nằm ở [23_DOC_AUDIT_FOLLOWUP.md](23_DOC_AUDIT_FOLLOWUP.md).

RPC mutation:

- `request_join_session(p_session_id, p_contact?, p_request_id)` — người chơi tự đăng ký buổi đã công bố. `approval_mode='host_approval'` ⇒ `pending`; `approval_mode='auto_confirm'` ⇒ `confirmed` nếu còn chỗ, ngược lại `waitlisted`. Một đăng ký mỗi người/buổi. Khoá session (`FOR UPDATE`) rồi kiểm lại lifecycle/deadline/state trong một transaction.
- `add_session_player(p_session_id, p_member_id?, p_guest_name?, p_contact?, p_fee_exempt, p_allow_waitlist, p_request_id)` — host/cohost thêm thành viên CLB (chọn đúng `member_id`, **không** tự khớp tên/SĐT) hoặc khách chưa có tài khoản (`participant_type='guest'`, `user_id NULL`). Khách luôn `host_recorded`; hết chỗ mà không `p_allow_waitlist` ⇒ `CAPACITY_FULL`, có ⇒ `waitlisted`. `p_fee_exempt` cần quyền tài chính.
- `decide_registration(p_session_id, p_player_id, p_decision, p_reason?, p_request_id)` — `p_decision ∈ {confirmed, waitlisted, rejected}`; chỉ management. `waitlisted→confirmed` **bị từ chối** trực tiếp (phải qua lời mời); `FOR UPDATE` session + player, kiểm lại state và sức chứa.
- `cancel_registration(p_session_id, p_player_id, p_reason?, p_request_id)` — người chơi tự huỷ theo `cancellation_deadline`; host/quản lý huỷ theo quyền; `confirmed`/`pending`/`waitlisted` → `cancelled`, giải phóng slot khi trước đây là `confirmed`.
- `record_attendance(p_session_id, p_player_id, p_attendance, p_request_id)` — chỉ `confirmed` và `lifecycle='in_progress'`; `p_attendance ∈ {present, no_show}`.
- `invite_waitlisted_player(p_session_id, p_player_id, p_expires_at?, p_request_id)` — host/cohost; người chơi đang `waitlisted`, buổi `published`, trước deadline. `expires_at` mặc định `min(now()+30 phút, registration_deadline, starts_at)` và phải ở tương lai; hết hạn lời mời cũ trước khi tạo mới. Lời mời **không** giữ slot, gắn cặp (session, player).
- `revoke_waitlist_invitation(p_session_id, p_invitation_id, p_reason?, p_request_id)` — đúng quyền; lời mời `pending` được đổi thành `revoked` và ghi audit. Lời mời đã `revoked` trả thành công không đổi trạng thái/ghi audit lần nữa, kể cả với request ID mới. Lời mời `accepted` hoặc `expired` trả `INVALID_STATE`; đã accepted muốn huỷ chỗ phải đi qua `cancel_registration`.
- `accept_waitlist_invitation(p_session_id, p_invitation_id, p_consent_note?, p_request_id)` — self: `auth.uid()` khớp `user_id` của player; `host_recorded`: host/cohost đúng buổi + khách chưa liên kết account + `p_consent_note` không rỗng. Trong một transaction khoá session → player → invitation, kiểm lại người nhận/state/hết hạn/deadline/slot; đơn dùng một lần, retry trả kết quả trước đó và **không** thêm slot.
- `start_session(p_session_id UUID, p_request_id UUID DEFAULT NULL)` — chỉ management, chỉ chuyển `published → in_progress`. Khoá session FOR UPDATE, xác thực actor/quyền và request ID; cùng key/payload trả projection đã lưu trước kiểm lifecycle, không tăng version hoặc audit lại. Thành công tăng version, ghi audit START_SESSION rồi trả `get_session_public_detail`. Không mở direct UPDATE sessions, không nới guard điểm danh. Lỗi trực tiếp: `UNAUTHENTICATED`/`FORBIDDEN` (42501), `INVALID_INPUT`/`INVALID_STATE` (22023), `NOT_FOUND` (P0002); helper idempotency có thể trả `IDEMPOTENCY_CONFLICT` (23505).

### Gate tài chính sau khi chốt phí

Khi có `charge_revisions.status='active'`, actor còn phải có `has_session_finance_access` để add người thành `confirmed`, decide thành `confirmed`, cancel người đang `confirmed`, hoặc accept lời mời để nhận chỗ. Thiếu quyền trả `FORBIDDEN` (42501). Đây là gate bổ sung cho quyền management/self, không thay quyền gốc; `p_fee_exempt` vẫn cần finance. Giữ các kiểm tra điểm danh/đã thu tiền của cancel và regression A1. Xem [ADR-08](11_ARCHITECTURE_DECISIONS.md#adr-08-bản-chốt-phải-khớp-phiên-bản-dữ-liệu-tính-phí); mô tả gate hiện có không đồng nghĩa toàn bộ finance BH-06 đã triển khai.

RPC đọc:

- `get_my_waitlist_invitation(p_session_id)` — `authenticated`; trả lời mời `pending` của chính người dùng (không lộ token/SĐT).
- `list_session_players(...)` được `CREATE OR REPLACE` thêm `pending_invitation_id`, `pending_invitation_expires_at`; giữ nguyên grant cũ (chỉ management).

Helper nội bộ `registration_result(...)` và `bump_billing_input_version(...)` bị `REVOKE` khỏi mọi role client. `accept_waitlist_invitation` cho khách cần đồng ý không rỗng; mọi chuyển trạng thái đều kiểm lại lifecycle/deadline/quyền/state ở DB. Bằng chứng/giới hạn: [22_BH05_HANDOFF.md](22_BH05_HANDOFF.md).
