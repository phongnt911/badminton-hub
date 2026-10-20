# Quyết định kiến trúc (ADR)

> **Hiện hành 20/10/2026:** Accepted là quyết định thiết kế, không phải mọi ADR đã được thực thi hoặc kiểm production. BH-06 Đạt tích hợp local tại `318bc52` ([review](reviews/bh06/review_318bc52.md)), đã merge vào main tại `e7f7627`; docs/ai đã có trên main (`eaeb209`). Baseline review: analyze sạch, 190 Flutter +335 DB, 7 tích hợp +3 nâng cấp +2 probe PASS. BH-07A **Đạt phần A local tại `4512c3a`** theo [review độc lập](reviews/bh07/review_4512c3a.md); B/C/D và pilot chưa nghiệm thu, không tự chuyển phần tiếp theo. Chưa nghiệm thu HTTP/JWT/Auth thật, thiết bị/ngân hàng thật, staging/production, backup/restore hoặc concurrency HTTP; merge code không phải deploy.

v1.1 · 14/10/2026. Status Accepted for MVP nghĩa là quyết định thiết kế được chọn để triển khai; không có nghĩa code, migration hay môi trường đã hoàn thành. ADR-01..06 giữ ID của bản kiến trúc trước; 07..09 bổ sung sau review.

## ADR-01: Giữ Flutter + Provider + Supabase

Status: Accepted for MVP.

Context: chủ dự án mới học, repo có stack này và cần thử với vài host; chưa có số liệu yêu cầu scaling/backend riêng.

Options: A giữ stack và module/repository/RPC; B thêm backend riêng với lớp domain/use-case/adapter đầy đủ.

Decision: chọn A, chỉ tách model/repository theo trách nhiệm thật; công thức thuần Dart để preview/test, DB tính tiền chính thức.

Consequences: ít hạ tầng và tận dụng code; chấp nhận phụ thuộc Supabase/Postgres và cần test DB. Không tạo abstraction cho CRUD chỉ để theo pattern. Xem lại khi tích hợp/tác vụ server hoặc giới hạn tải có bằng chứng.

## ADR-02: Transaction DB bảo vệ slot/payment/ledger

Status: Accepted for MVP.

Context: ghi hai request từ client gây thành công một phần, đua slot và ghi đè số dư.

Options: A RPC đồng bộ, khóa session/input và ghi nguồn+ledger trong một transaction; B client phối hợp nhiều writes hoặc xử lý số liệu nguồn bằng event async.

Decision: A. Actor từ auth.uid(), request_id chống retry; thứ tự khóa theo 08_DOMAIN_CONTRACTS. Realtime không phải hàng rào đúng dữ liệu.

Consequences: rollback và quyền có thể kiểm thử; phải quản lý lock/SQL/RPC cẩn thận. Thông báo có thể async sau, nhưng không quyết định số người/tiền nguồn. Xem lại theo contention được đo, không tách service trước.

## ADR-03: Quyền theo CLB và buổi

Status: Accepted for MVP.

Context: một người là host CLB A nhưng player CLB B; bật RLS vẫn không an toàn khi policy true.

Options: A ownership/membership/session_staff và projection private/public; B global is_host hoặc public CRUD rồi ẩn nút.

Decision: A. Grants, policy và EXECUTE RPC cùng bảo vệ; owner/cohost/finance được phân biệt. Contacts riêng. Admin query không là bằng chứng role app an toàn.

Consequences: cần nhiều ca quyền và kiểm tra view/function; bớt dữ liệu trả xuống app. Không thêm quyền quản trị implicit khi user tự sửa metadata. Xem lại role matrix bằng yêu cầu host thực.

## ADR-04: Ledger và charges/payments là nguồn tài chính

Status: Accepted for MVP.

Context: client ghi balance và transaction riêng dễ lệch; has_paid boolean không đối chiếu được trả thiếu/nhiều lần.

Options: A SUM ledger và active charges trừ confirmed payments; B balance/has_paid do client cập nhật.

Decision: A. Số dư quỹ gồm bút toán đảo, nguồn payment/expense unique, không xóa lịch sử. Công nợ giữ sau completed.

Consequences: truy vết được, truy vấn tổng tốn hơn cache. Chỉ thêm cache khi có dữ liệu tải và DB duy trì nguyên tử; không cho UI ghi balance. Test quỹ+payment+đảo trước pilot.

## ADR-05: Online và xác nhận ngân hàng thủ công cho MVP

Status: Accepted for MVP.

Context: chưa có nhu cầu offline sync/bank webhook được xác minh, đội nhỏ cần vận hành đơn giản.

Options: A online mutations, lỗi/retry rõ, host xác nhận cash/transfer; B offline queue + reconciliation + webhook ngân hàng.

Decision: A. Timeout retry cùng request_id, QR không xác nhận thu; mất mạng không báo ghi thành công.

Consequences: host cần mạng và xác nhận tay; tránh thêm hạ tầng tích hợp chưa cần. Xem lại khi pilot cho thấy mất mạng/khối lượng xác nhận là nút thắt.

## ADR-06: Migration theo môi trường, tách thiết kế khỏi triển khai

Status: Accepted for MVP.

Context: schema live chỉ có ba bảng, tài liệu mô tả đích rộng hơn; SQL legacy policy mở chưa đủ an toàn.

Options: A migration versioned, local/staging rehearsal rồi release có đối chiếu; B chạy SQL demo trực tiếp để lấp bảng thiếu.

Decision: A. Không suy ra owner từ phone, không ghi payment thật từ has_paid cũ thiếu bằng chứng. Triển khai code/schema/thu hồi policy theo kế hoạch release.

Consequences: cần chuẩn bị môi trường và đối chiếu dữ liệu; không thể ghi done bằng việc soạn file. Không áp dụng production trong task viết tài liệu hoặc test.

## ADR-07: Login cho tự đăng ký, host thêm khách chưa account

Status: Accepted for MVP.

Context: host nhận đăng ký qua Zalo, nhưng quyền player cần danh tính thật.

Options: A self registration có login và host-added guest theo ID; B self-service guest token/OTP ngay MVP.

Decision: A. Guest không có account giả; account linking/invitation tự phục vụ hoãn, không gộp theo tên/SĐT.

Consequences: thêm bước login cho player; host có thể ghi hộ để pilot không bị chặn. Xem lại theo tỷ lệ bỏ đăng ký trong pilot, triển khai token/OTP chỉ khi có yêu cầu và test quyền.

## ADR-08: Bản chốt phải khớp phiên bản dữ liệu tính phí

Status: Accepted for MVP.

Context: expenses/attendance/roster đổi sau chốt làm active charges lỗi thời.

Options: A billing_input_version + revision.source_version và server gate; B chỉ banner chốt lại hoặc tự ghi đè charges.

Decision: A. Input đổi làm stale; finalize transaction lưu đúng version. QR/thu mới/complete yêu cầu current; buổi miễn phí cũng chốt. Giữ tiền đã thu và lịch sử, chặn giảm due dưới paid.

Consequences: host cần thao tác chốt lại, không thu tiếp trên bản cũ. Retry đã committed không ghi lại; lịch sử/đảo vẫn có quyền khi stale. QR lưu ngoài app không thu hồi được, phải đối chiếu chuyển khoản trễ. Xem lại luồng hoàn tiền khi thật sự cần, không tự đảo sổ để giả hoàn tiền.

## ADR-09: Lời mời waitlist lưu tại DB, không giữ slot

Status: Accepted for MVP.

Context: contract mời/chấp nhận không thể phục hồi nếu chỉ là state UI.

Options: A invitation có issuer/expiry/status và accept transaction; B tự promote mọi waitlisted khi có chỗ.

Decision: A. Host mời, đúng player accept, kiểm tra capacity lại. Guest chưa account được host ghi consent và accept thay có audit.

Consequences: nhiều bước hơn nhưng có đồng ý rõ; lời mời không cam kết giữ chỗ và có thể full lúc accept. Opt-in auto promotion hoặc reservation có hạn chỉ thêm khi được yêu cầu, không âm thầm đổi hành vi.
