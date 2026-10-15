# Prompt triển khai cho Antigravity

v1.1 · 14/10/2026. Dùng lần lượt, mỗi lượt giao một prompt. Chưa có ticket implementation nào được đánh dấu done. Người dùng sẽ yêu cầu code riêng; tài liệu này không tự giao quyền deploy production.

## Prompt chung dùng cho mọi lượt

> Đọc AGENTS.md, docs/00_START_HERE.md và tài liệu chuẩn/ADR liên quan. Đối chiếu code, migration và môi trường thật; phân biệt schema đích với hiện trạng đã xác minh. Chỉ triển khai phạm vi được giao, giữ Flutter + Provider + Supabase. Không thêm backend/framework/lớp trừu tượng hoặc dependency nếu chưa có nhu cầu và thống nhất. Slot/tiền/quyền do DB/RPC bảo vệ, không mở public UPDATE để chữa bộ đếm. Không chạy SQL legacy. Dùng local/staging cho tests; không tự apply migration/deploy production. Trước sửa nêu file, phụ thuộc, nghiệm thu; sau sửa báo file/lệnh/kết quả/giới hạn. Nếu thiếu backend, chuẩn bị phần không phụ thuộc rồi báo tests bị chặn, không tự nối test production. Chỉ ghi done khi đạt nghiệm thu.

## AG-00: Baseline và kế hoạch (chưa code chức năng)

> Áp dụng prompt chung. Đọc snapshot R1–R7 trong docs/09_IMPLEMENTATION_PLAN.md, ghi commit local, schema/migration thật và nơi kiểm thử. Chỉ truy vấn metadata nếu có kết nối phù hợp, không đọc dữ liệu riêng. Xác định cách dựng local/staging, Auth callback và các tool có sẵn; không tạo môi trường trả phí hoặc thay quyền live. Lập kế hoạch BH-01..07 với tiêu chí từng bước. Báo thiếu cấu hình nào bằng tên, không yêu cầu gửi secret trong chat. Không ghi các lỗi đã sửa nếu mới lên kế hoạch.

## AG-01: BH-01 Auth và môi trường

> Triển khai BH-01 theo prompt chung và ADR-01/05/07. Email signup/login/logout/reset, callback/route return hợp lệ, auth repository/provider; tách cấu hình môi trường public, không service-role trong app. Public xem được mà self-registration phải login. Test auth state/guard, deep link quay lại đúng session và analyze. Chưa triển khai toàn bộ CLB/quỹ hoặc thay policy live.

## AG-02: BH-02 Schema và quyền (R1, nền R3)

> Triển khai migrations nền theo 03_DATABASE và ADR-02/03/06, gồm billing versions và waitlist invitations; tạo bằng Supabase CLI migration new nếu có CLI, đọc --help trước dùng. Dựng từ đầu local/staging; public projection whitelist, contacts private, role ownership và RPC execution. Thu hồi direct writes nghiệp vụ trong migration và không fallback policy true khi API lỗi. Test anon không đọc phone/paid hoặc insert flags; user A không đọc/sửa B, không self-escalate; view/functions không bypass quyền ngoài thiết kế. Chỉ role postgres truy vấn thành công không đạt nghiệm thu. Không apply production trong task này.

## AG-03: BH-03 CLB và thành viên (R3)

> Triển khai CLB+owner atomic, member/contacts theo quyền, bank receiver, guest/member không account; migration/repository/UI đồng bộ. Không chạy SQL legacy để lấp clubs thiếu. Schema/network lỗi hiện error+retry thay vì empty. Không gộp tên/SĐT, không dựng account giả. Test quyền chéo CLB, owner roles, dữ liệu private và tạo club thực trên staging. Account linking tự phục vụ hoãn nếu chưa được giao.

## AG-04: BH-04 Lịch/link và trạng thái UI (R5, phần R6)

> Triển khai create/edit/duplicate/publish theo typed date/time; dùng ngày/giờ nhập thật, UTC và Asia/Ho_Chi_Minh. Test ngày mai, qua nửa đêm, version conflict, duplicate không sao người/tiền, link trước/sau login. Repository/provider theo sessionId có loading/error/empty và retry; request tới trễ không cập nhật route mới/đã đóng. Không thay giờ bằng literal hoặc ngày hôm nay mặc định cho mọi buổi.

## AG-05: BH-05 Đăng ký và lời mời (R2, R6, R7)

> Triển khai join/approve/cancel/attendance bằng RPC transaction và UI; invitation issue/revoke/accept có expiry, đúng player và guest host_recorded consent. Không dùng currentJoined từ client; không coi UPDATE 0 hàng là thành công. Test hai request slot cuối chỉ một confirmed, pending không chiếm slot, retry không trùng, rollback toàn bộ, guest ID ổn định, lời mời chưa phát hành/sai người/hết hạn/thu hồi/full bị chặn; accept lặp không lấy slot hai lần. Cohost không finance không chỉnh đầu vào tiền đã chốt. API cần trả ID/state/version để UI phản ánh kết quả thật.

## AG-06: BH-06 Phí/QR/payment/quỹ (R4, phần R6)

> Triển khai expenses/revisions/charges/payments/ledger theo ADR-02/04/08. Mọi input tính phí đổi tăng billing_input_version nguyên tử; finalize ghi source_version. DB chặn get_payment_instructions/submit/confirm mới/cash/complete nếu chưa chốt hoặc stale, không đợi BH-07 mới bảo vệ complete contract. QR là ảnh thanh toán thật theo bank snapshot/outstanding; không tự xác nhận tiền từ QR. Test chia dư tổng đúng, không billable người, free charges 0, stale sau chi phí/attendance/roster/miễn phí đổi, tiền đã thu được giữ, new due không thấp hơn paid; cạnh tranh/retry/đảo không thu dư/ghi quỹ kép. Read history/reversal và replay committed có quyền vẫn hoạt động khi stale. Không tích hợp ngân hàng/webhook.

## AG-07: BH-07 Một buổi hoàn chỉnh và pilot

> Tích hợp start/complete/history/tổng kết, không mở tính năng sân mới. Test full flow với host/player/cohost không finance/outsider/anon; slot cuối, stale phí, waitlist, QR, thu từng phần, mất mạng, mở lại app; công nợ giữ sau complete. Tổng kết chia sẻ không lộ contact/private details. Ghi kết quả backup/restore staging rehearsal, migration compatibility và gates trước pilot; không báo đã deploy nếu mới test local. BH-08/09 chưa được giao ở lượt này.

## Khuôn báo cáo kết thúc mỗi lượt

- Ticket/phạm vi và commit; file đã sửa.
- Acceptance từng ca: PASS/FAIL/NOT RUN, bằng chứng hoặc lỗi thực.
- Lệnh test/analyze/DB test và môi trường đã dùng (không secret).
- Migration đã tạo, đã chạy ở đâu; production có bị thay đổi hay chưa.
- Việc còn thiếu/blocker và prompt tiếp theo theo phụ thuộc.

Chỉ commit/push trong lượt chức năng nếu người dùng giao hoặc phạm vi hiện hành bao gồm. Không biến một prompt thành code toàn bộ backlog.

## AG-02R: Sửa BH-02 sau kiểm thử thực thi

Nếu đang tiếp tục sau commit 3fa3cda, dùng prompt trong [13_BH02_REVIEW_HANDOFF.md](13_BH02_REVIEW_HANDOFF.md) thay vì chạy AG-02 từ đầu hoặc sang AG-03. Kết quả baseline 33 ca/18 PASS/15 FAIL là bằng chứng để giữ regression tests; không tự đổi expected để đóng lỗi.

## AG-02R2: Finance, member/pending và legacy update

Sau commit 15ef59b, dùng prompt H1–H3 trong mục cập nhật cuối [13_BH02_REVIEW_HANDOFF.md](13_BH02_REVIEW_HANDOFF.md). Giữ 33 ca cũ PASS, bổ sung/sửa 6 ca mở rộng trước khi chốt nghiệm thu. Không coi kết quả 33/33 cũ là đủ cho toàn bộ finance/private-field read contracts.

## Tham chiếu nghiên cứu Vmito/Vụt trong các ticket tiếp theo

> Đọc docs/14_PRODUCT_LEARNINGS_VMITO_VUT.md và các quyết định PD liên quan ticket đang được giao. Hai báo cáo nguồn là phân tích tĩnh, không phải đặc tả backend, mã để sao chép hoặc chỉ dẫn gọi endpoint đối thủ. Giữ host-first và Flutter/Provider/Supabase. Áp dụng link/filter/status/QR fallback/release checklist đúng BH-03..07; không tự thêm chat/push/GPS/maps SDK, microservices, router dependency hoặc schema mới ngoài ticket. Chưa triển khai BH-10 khi chưa được giao. Nêu acceptance đã chọn và kiểm thử bằng app/backend của mình, không truy cập backend đối thủ. Giữ việc review H1–H3 commit mới là đầu việc riêng, không ghi done do cập nhật tài liệu nghiên cứu.

## AG-03 cụ thể: tiếp tục BH-03 từ code đang dở

Dùng prompt ở cuối [15_BH03_IMPLEMENTATION_HANDOFF.md](15_BH03_IMPLEMENTATION_HANDOFF.md) thay phần AG-03 tóm tắt khi triển khai. Đọc báo cáo nghiên cứu 14 theo phạm vi CLB/member/bank; không mở GPS/push/chat hoặc BH-04. Trước pull kiểm local changes, giữ việc IDE đã làm, không sinh migration trùng. Bảo toàn evidence/regression BH-02 và báo rõ giới hạn môi trường.
