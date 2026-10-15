# Review độc lập BH-05A — 7fcbdee

Ngày 16/10/2026, giờ Việt Nam. Nhánh `feat/bh05a-db`, HEAD `7fcbdeed7bf0d53e35f470e927ac6f0d84b97820`; main remote `da1285dba9b952f0b3ef5d2b04423f17fa1d0648`; merge-base `d8dfe74`. Phạm vi `git diff origin/main...HEAD` (tương đương main...HEAD; local không có nhánh main), phần A gồm SQL/runner/bằng chứng. Đọc quy trình hai AI từ AGENTS.md trên main vì nhánh A tách trước commit quy trình, cùng 04/08/BH05/R2/R7 tại 09. Không review phần B/C trên main như thay đổi của nhánh A.

## A1 — P1: thiếu kiểm quyền finance khi đổi confirmed roster sau chốt phí

**File:dòng:** `supabase/migrations/20261015170500_bh05_registrations.sql:370-377` (add_session_player); cùng khoảng trống tại `:566-573` (decide_registration), `:692-699` (cancel_registration).

**Mô tả:** add_session_player chỉ yêu cầu finance nếu fee_exempt=true, không kiểm active charge revision khi thêm confirmed. Hợp đồng 08 §7 yêu cầu add/cancel confirmed roster ảnh hưởng tiền sau finalize phải có finance. Đã tái hiện clean và legacy: buổi in_progress có active revision; actor có session_staff=cohost, has_session_finance_access=false, gọi add_session_player với fee_exempt=false vẫn thành công và trả confirmed. bump_billing_input_version không thay thế authorization. cancel chỉ kiểm present/payment, nên cũng thiếu gate theo revision khi người bị hủy chưa present/chưa có payment.

**Cách sửa:** trong transaction đang giữ khóa session, kiểm active revision và quyền finance trước thay đổi tập confirmed; áp dụng cho mọi đường thêm/duyệt/accept/hủy liên quan theo lifecycle hợp lệ. Giữ replay đã committed sau kiểm quyền phù hợp. Bổ sung hành vi cohost bị từ chối, finance được phép, phiên bản tính phí tăng đúng; không chỉ test fee_exempt. Tái hiện runtime trong lượt này tập trung add_session_player, các đường khác được đối chiếu code.

## A2 — P1: chưa bảo vệ invariant capacity khi sửa buổi đã có người confirmed

**File:dòng trong diff:** `docs/reviews/bh05/run_bh05_tests.py:575-601` (test slot chỉ chạy join/join và approve/approve, thiếu capacity-update). Đường gây lỗi kế thừa: `supabase/migrations/20261015163000_bh04_sessions.sql:362-368`.

**Mô tả:** sau hai đăng ký confirmed vào buổi capacity=2, host gọi update_session với version hiện tại và capacity=1 vẫn thành công; DB trả capacity=1, confirmed_count=2 trên clean và legacy. Hợp đồng 08 §3/§6 ghi rõ không hạ capacity dưới confirmed và bắt buộc kiểm ca này. Đây là lỗi tích hợp kế thừa BH04, không phải dòng update mới trong migration BH05; phần A mở đường đăng ký nhưng chưa bảo vệ/kiểm invariant xuyên các RPC. Không coi 66/66 là đủ bằng chứng toàn bộ capacity invariant.

**Cách sửa:** forward migration bổ sung kiểm confirmed_count dưới cùng khóa session trong update_session (hoặc guard DB tương đương); từ chối capacity mới nhỏ hơn confirmed. Thêm ca tuần tự và hai kết nối update-capacity đấu với join/approve/accept, bảo đảm count không bao giờ vượt capacity sau commit. Không sửa migration cũ đã chia sẻ, không xóa người để ép vừa capacity.

## A3 — P2: hủy buổi không thu hồi các lời mời pending

**File:dòng trong diff:** `docs/reviews/bh05/run_bh05_tests.py:603-605` (kết thúc suite thiếu ca hủy buổi với invitation). RPC kế thừa cần tích hợp: `supabase/migrations/20261015163001_bh04_review_fixes.sql:62-76`; migration BH05 không override/trigger để thu hồi theo lifecycle.

**Mô tả:** hợp đồng 08 §7 yêu cầu hủy player/buổi thu hồi pending invitation cùng transaction. Tái hiện clean/legacy: tạo buổi, người waitlisted có invitation, host cancel buổi; invitation vẫn pending. get_my_waitlist_invitation chỉ lọc pending/expiry nên người chơi vẫn nhận lời mời của buổi đã hủy. Accept mới bị lifecycle chặn, do đó chưa chứng minh vượt slot; lỗi là hợp đồng trạng thái/lời mời hiển thị sai.

**Cách sửa:** khi lifecycle chuyển cancelled, thu hồi toàn bộ invitation pending của players thuộc buổi trong cùng transaction, actor/time/audit theo contract; giữ thứ tự khóa nhất quán với accept. Thêm test cancel-session, cancel-vs-accept hai kết nối, replay cancel không tạo thêm tác dụng phụ; get_my_waitlist_invitation không trả lời mời hủy.

## Kết quả kiểm thử độc lập

- `/workspace/toolchains/flutter-3.47.7/bin/flutter analyze --no-pub`: No issues found, exit 0.
- `/workspace/toolchains/flutter-3.47.7/bin/flutter test --no-pub`: **104/104 PASS**, exit 0; bộ này là baseline Flutter trước B/C.
- `BH02_TEST_CONTAINER=bh02-review-postgres python docs/reviews/bh05/run_bh05_tests.py`: **66/66 PASS**, exit 0, PostgreSQL17.11/Auth stub trên DB test clean và legacy. Có hai tiến trình psql/kết nối độc lập trong hai ca race hiện có. [Kết quả tự chạy](bh05_test_results_20261015171008.json).
- Sáu probe bổ sung (3 tình huống × clean/legacy) đều vi phạm kỳ vọng; [dữ liệu tái hiện](review_7fcbdee_edges.json). Chỉ seed giả và gọi RPC trên DB test do runner tạo, không đổi source/migration. Script probe tại `/workspace/scratch/bh05a-review/check_edges.py` trong workspace review.
- Migration SHA256 bytes LF: `356f5831649eb4d09efa624402679cce67211056ce44e09cf6088715970ac588`. SHA trong báo cáo tác giả `2c63e2...` khớp chính file khi đổi sang CRLF; không xem khác newline là thay đổi logic hoặc bằng chứng gian lệch.

## NOT RUN

- Supabase HTTP/PostgREST/JWT thật; staging/production apply; không sửa DB remote.
- Test phần B/C, thiết bị thật, browser e2e (ngoài phạm vi nhánh A).
- Không chạy lại runner BH02/BH03/BH04 trong lượt này; runner BH05 áp toàn chuỗi migration trên DB test, không thay cho chạy lại mọi suite cũ.
- Chưa chạy concurrency update-capacity-vs-join/approve/accept, cancel-session-vs-accept, cancel-player-vs-approve và cùng request_id đồng thời; chỉ có các ca race do runner hiện tại cung cấp. Các lỗ hổng coverage được nêu trong phát hiện tương ứng.

## Kết luận

**Chưa đạt** — còn A1/A2 mức P1 và A3 mức P2. Không sửa code, không apply remote DB, không merge hoặc push trong lượt review. Phát hiện A2/A3 phân biệt rõ code kế thừa với phần coverage/tích hợp còn thiếu của phần A; không yêu cầu viết lại phần B/C.
