# BH-07 — Vận hành và backup/restore rehearsal local

Trạng thái: **Chờ review độc lập backup/restore local**. Browser đã đóng Đạt local tại `74305bb`; Codex tự sửa/tự kiểm browser, không phải review độc lập. Tài liệu này không cấp phép vận hành production hoặc pilot.

## Phạm vi đã thực hiện

Source `b626a7852401e91db436ecc70134150f4c87c06f`, base `74305bb343fbaf548cb5eea38a77475cc3a21b39`. Chỉ thêm script fixture local và tài liệu; app, unit test, migration/RPC và contract không đổi. PostgreSQL17.11, GoTrue2.197.0, PostgREST16.4, Kong2.8.1 trên Docker/Linux.

Script tạo stack nguồn riêng từ migration hiện hành, Auth users thật và fixture cũ. Owner đăng nhập mật khẩu thật, ghi tiền mặt 10.000đ qua RPC; kiểm Owner/Cohost/outsider/anonymous qua HTTP. Dừng Auth nguồn trước snapshot để không có writer Auth; không có writer ứng dụng khác trong fixture. Không phải thử nghiệm backup online với writer đồng thời.

Backup `pg_dump --format=custom --create` và `pg_dumpall --globals-only` nằm trong thư mục tạm quyền0700 cùng key/password runtime. Restore vào cluster mới, chỉ bỏ đúng câu CREATE ROLE postgres đã tồn tại; giữ ALTER/password/role memberships. Restore giữ owner, ACL, RLS policies, function, sequence theo schema dump. So sánh SHA256 và số hàng của toàn bộ bảng public/Auth, schema dump (bỏ nonce psql restrict ngẫu nhiên), thuộc tính roles và sequence trước khi khởi động Auth đích.

Sau restore: GoTrue mật khẩu thật, PostgREST JWT/ACL thật; Owner xem tiền, Cohost có đủ8 trường tiền null, outsider FORBIDDEN, anonymous bị từ chối ở quyền function, sai mật khẩu bị từ chối. Retry cùng request_id trả cùng payment_id, chỉ1 payment/ledger/operation; aggregate/outstanding server không đổi. Negative controls dùng chính comparator/oracle hiện tại: archive hỏng, thiếu audit row, mất EXECUTE RPC đều bị phát hiện. Chỉ phá dữ liệu ở đích fixture rồi xóa container.

## Cách chạy an toàn trong local

Yêu cầu Docker và Python3; các image local/cache tương ứng ở trên. Repo phải sạch để provenance có ý nghĩa. Không cần Flutter cho rehearsal riêng. Script không nhận database URL hay credential từ production.

```bash
python -u scripts/bh07_backup/run_local_rehearsal.py --out /tmp/bh07-recovery-fresh
```

Đường dẫn output phải chưa tồn tại. Tên source container `bh07-http-review-*` và network `bh07-http-review-network` phải chưa tồn tại; nếu có, script từ chối, không tự xóa tài nguyên có sẵn. API nguồn chỉ loopback54321; đích dùng port loopback ngẫu nhiên. Trong lúc chạy không dùng chung stack này cho việc khác. Giữ stdout và exit thực tế; PASS cần13 check, exit0, dump/key đã xóa. Cuối chạy cleanup tài nguyên do chính script tạo. Nếu bị kill cưỡng bức, người vận hành kiểm tên tài nguyên và thư mục tạm của đúng lần chạy trước khi xóa; không xóa container có sẵn của người khác.

Không đưa archive, roles SQL, mật khẩu/JWT hay nội dung Auth users vào Git. Chỉ công bố counts/digests, metadata và log đã kiểm secret. Script xóa private dump/key khi kết thúc; đây là rehearsal khả năng phục hồi, không phải kho backup lưu dài hạn. JWT signing secret cấu hình lại trong smoke đích là key runtime riêng được giữ tạm ngoài dump.

## Kết quả đo local và giới hạn

13/13 check PASS; backup0,369giây; từ tạo cluster đích đến Auth/ACL/replay smoke11,386giây. Không mất dữ liệu so với snapshot fixture đã quiesce. Các số này không phải RTO/RPO hay SLA production. Bằng chứng ở `reviews/bh07/backup_restore_evidence/`; phải review độc lập trước khi chốt gói mới.

NOT RUN: backup toàn bộ managed Supabase project/Storage objects/Edge Functions/Realtime/cấu hình secret bên ngoài DB; PITR, offsite/encryption/retention rotation tự động; backup với writer đồng thời; staging/production và restore thực tế; ngân hàng/webhook; browser/device/offline/deep link trong gói rehearsal này; rehearsal tải thật, pilot và nghiệm thu toàn BH-07. PostgreSQL/Auth fixture local không thay thế các cổng này.
