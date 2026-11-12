# BH-07/V8 — bảng quyết định rủi ro còn lại, 10/11/2026

**DỰ THẢO, CHƯA ĐƯỢC OWNER PHÊ DUYỆT.** Codex chuẩn bị từ [ma trận hiện tại](bh07_completion_status_20261110.md). Không điền người ký/ngày quyết định hoặc đổi technical NOT RUN/UNKNOWN thành PASS thay owner. Lệnh tiếp tục làm code và tự duyệt lệnh run không phải quyết định này.

Audit12/11 đã đối chiếu tuyến source mới và các phạm vi Web bổ sung; [review độc lập](sync_v8_review_20261112.md) vẫn xác nhận cần quyết định riêng cho năm hàng dưới. Chưa có quyết định owner mới tại lúc cập nhật; không có runtime/DB mới trong audit.

Sau audit, owner đã chọn phongnt911's Org và duyệt tạo/chuẩn bị staging0USD/tháng, Singapore, dữ liệu thử. [Project mxqpukhfiugdwsjsbihj](staging_setup_20261112.md) đã có18migration/21bảng RLS; đây là phê duyệt môi trường, không phải ký chấp nhận rủi ro năm cổng bên dưới. Chưa bật PITR/add-on trả phí hoặc chạy restore/deploy/load/pilot.

## Phạm vi cụ thể để xem xét

Nếu owner chọn chấp nhận từng cổng bên dưới, phạm vi chỉ là nghiệm thu phần phát triển/kiểm chứng **Web local với dữ liệu thử**, sau khi tất cả core và các lỗi đã chạy FAIL được xử lý, reviewer chốt độc lập. Không phát hành native, deploy/restore staging/production, phục vụ dữ liệu vận hành thật, mở pilot hay chuyển BH-08. Các cổng chưa đo vẫn NOT RUN/UNKNOWN; trước khi mở rộng sử dụng phải hoàn thành và review bằng chứng tương ứng.

V4 đã [PASS local/staging-like](recovery_site_url_runtime_final_20261110.md), không cần waiver thay kết quả; managed V3 vẫn riêng. V5b inherited runtime PASS và harness delta đã review. V6 vẫn ngoài phạm vi.

| Cổng | Lý do thiếu bằng chứng hiện có | Rủi ro còn lại | Giới hạn/giảm thiểu và việc phải hoàn tất trước mở rộng | Quyết định owner |
|---|---|---|---|---|
| V2 | Android smoke đã có login/start/attendance/finalize do owner thao tác và SQL đối chiếu, sau đó owner dừng Android; [Chrome local](web_local_runtime_20261110.md) và [Edge/Firefox headless](web_matrix_runtime_20261111.md) đã có bằng chứng. Firefox có cửa sổ UNKNOWN, clipboard Edge/Firefox NOT RUN; iOS/OS deep-link và full device/browser matrix vẫn thiếu | Lỗi lifecycle, điều hướng, offline hoặc privacy riêng nền tảng | Chỉ ghi hỗ trợ phạm vi Web local đã đo; chưa phát hành native/khẳng định matrix khác. Chạy và review matrix nền tảng trước hỗ trợ | **CHƯA PHÊ DUYỆT** |
| V2b phần chưa đo | Web sentinel IDs đã được kiểm, nhưng whole-model UNKNOWN, instructions/listener/native thiếu coverage; rendered bank/receiver/title/reference còn unattributed | Dữ liệu tài chính có thể tồn lưu trong bộ nhớ trên máy/profile dùng chung | Chỉ dữ liệu thử, profile riêng, không dùng chung actor trên máy có dữ liệu thật; giữ/xóa heap riêng tư theo receipt. Đo thêm hoặc có quyết định mới trước mở rộng | **CHƯA PHÊ DUYỆT** |
| V3 | Đã có staging riêng được duyệt; chưa có PITR/offsite/retention/encryption policy evidence hoặc backup drill | Không phục hồi đầy đủ dịch vụ/dữ liệu/secrets khi mất môi trường managed | Chỉ dữ liệu thử tái tạo được, chưa có dữ liệu vận hành thật. Trước remote release phải có chính sách+target cô lập+managed restore/PITR drill+ACL/RPC review | **CHƯA PHÊ DUYỆT** |
| V5 | Target staging đã được duyệt tạo/chuẩn bị; release/window/backup/rollback/smoke chưa được phê duyệt và đo | Lỗi recovery/deploy ngoài local, RTO/RPO chưa xác lập | Chưa thực hiện staging/production deployment/restore. Trước release cần ủy quyền target/window riêng, backup/rollback, smoke và RTO/RPO đã review | **CHƯA PHÊ DUYỆT** |
| V7 | Chưa có môi trường production-like, SLO/workload, support/on-call và nhóm pilot được phê duyệt | Không chứng minh capacity, rollback dưới tải hoặc hỗ trợ người dùng thật | Không mở pilot/cam kết SLO. Trước pilot phải chốt workload/SLO/target/support và chạy load+rollback drill rồi review | **CHƯA PHÊ DUYỆT** |

## Cách ghi nhận quyết định

Owner chọn rõ từng cổng: chấp nhận với lý do/giới hạn/giảm thiểu ở hàng đó, từ chối, hoặc yêu cầu cung cấp môi trường để đo. Ghi đúng lời quyết định thực tế, thời điểm và phạm vi áp dụng trong bản ban hành liên kết ma trận đã cập nhật. Không dùng một chữ “đồng ý” không rõ đối tượng để điền tất cả cổng.

Quyết định chỉ được dùng ở bước chốt V8 sau khi core có independent PASS, mọi P0/P1/P2 đóng, không có gate đã chạy FAIL và mọi link/SHA/provenance nhất quán. Hiện chưa đủ điều kiện đó; bảng này là công việc chuẩn bị, không phải nghiệm thu hoặc risk acceptance đã ký.
