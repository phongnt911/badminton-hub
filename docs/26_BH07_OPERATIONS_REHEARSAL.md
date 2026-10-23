# BH-07 — Vận hành và backup/restore rehearsal local

Trạng thái: **Chờ review độc lập bản sửa R1 cleanup của backup/restore local**. Người triển khai tự kiểm, không phải review độc lập. Browser đã đóng Đạt local tại `74305bb`; không mở lại trong gói này. Tài liệu không cấp phép vận hành production hoặc pilot.

## Phạm vi hiện hành

Source `6d00e9cea29c29a2b57d3291fb92be7600110f98`, base review `ec0784f359ed877177330c59dbf40e0ce384ecbf`. Chỉ sửa script rehearsal/probe và tài liệu; app, unit test, migration/RPC, contract và backend không đổi. Môi trường chạy thật là Windows 11/Docker29.8.2, PostgreSQL17, GoTrue2.197.0, PostgREST16.4, Kong2.8.1; Flutter3.47.6. Đây là môi trường khác evidence Linux cũ.

Script tạo stack nguồn riêng từ migration hiện hành, Auth users thật và fixture cũ. Owner đăng nhập mật khẩu thật, ghi tiền mặt 10.000đ qua RPC; kiểm Owner/Cohost/outsider/anonymous qua HTTP. Dừng Auth nguồn trước snapshot; không có writer ứng dụng khác. Không phải backup online với writer đồng thời.

## R1 cleanup gate

Phần `finally` của `scripts/bh07_backup/run_local_rehearsal.py` kiểm tra từng container/network do lượt chạy sở hữu trước khi xóa và `docker inspect` lại sau khi xóa. Lỗi xóa, resource còn tồn tại hoặc private dump/key còn lại đều ghi `cleanup_errors`, đặt `cleanup_failed=true`, chuyển summary sang `FAIL` và trả exit `1`. Cleanup vẫn tiếp tục các resource còn lại sau một lỗi; lỗi chạy chính được giữ nguyên, không bị `CleanupError` ghi đè. Log cleanup chỉ dùng alias/return code, không chứa command/secret.

Probe `scripts/bh07_backup/cleanup_probe.py` trích nguyên cleanup `finally` và `return` hiện hành bằng AST, không copy logic. Control gồm positive, private cleanup failure, Docker cleanup failure, cleanup tiếp tục sau lỗi và giữ lỗi chạy chính. Trước sửa probe exit1 và tái hiện hai negative vẫn exit0; sau sửa exit0 với5/5 control đúng.

## Cách chạy an toàn trong local

Yêu cầu Docker và Python3; image local/cache tương ứng. Repo phải sạch để provenance có ý nghĩa. Script không nhận database URL hay credential từ production.

```bash
python scripts/bh07_backup/cleanup_probe.py
python -u scripts/bh07_backup/run_local_rehearsal.py --out /tmp/bh07-recovery-fresh
```

Đường dẫn output phải chưa tồn tại. Tên source container `bh07-http-review-*` và network `bh07-http-review-network` phải chưa tồn tại; nếu có, script từ chối, không tự xóa tài nguyên có sẵn. API nguồn dùng cổng loopback tự do để không đụng Supabase local; đích dùng port loopback ngẫu nhiên. Trong lúc chạy không dùng chung stack này cho việc khác. Giữ stdout/exit thật; PASS cần13 check, exit0, `cleanup_failed=false`, dump/key đã xóa và không còn container/network của lượt chạy.

Không đưa archive, roles SQL, mật khẩu/JWT hay nội dung Auth users vào Git. Chỉ công bố counts/digests, metadata và log đã kiểm secret. Script xóa private dump/key khi kết thúc; đây là rehearsal khả năng phục hồi, không phải kho backup lưu dài hạn. Nếu bị kill cưỡng bức, người vận hành kiểm đúng tên tài nguyên/thư mục tạm của lần chạy trước khi xóa; không xóa container có sẵn của người khác.

## Kết quả đo local và giới hạn

Lượt sạch cuối tại `6d00e9c`: 13/13 check PASS, backup `0,219giây`, từ tạo cluster đích đến Auth/ACL/replay smoke `9,219giây`, `private_dumps_keys_removed=true`, `cleanup_errors=[]`, `cleanup_failed=false`, source_port `55874`; sau chạy không còn `bh07-http-review-*`. Một lượt tại `2c6225f` exit1 vì target PostgreSQL chưa sẵn sàng; log/summary thất bại được giữ, đã thêm chờ60giây/stage tại `6d00e9c`. Các số này không phải RTO/RPO hay SLA production.

Bằng chứng mới ở `reviews/bh07/backup_restore_cleanup_evidence/`; evidence cũ `backup_restore_evidence/` và `review_b626a78_evidence/` giữ nguyên. Manifest18/18, UTF-8 LF,0 secret/JWT ngoài allowlist, verify readonly exit0.

NOT RUN: backup toàn bộ managed Supabase project/Storage objects/Edge Functions/Realtime/cấu hình secret bên ngoài DB; PITR, offsite/encryption/retention rotation tự động; backup với writer đồng thời; staging/production và restore thực tế; ngân hàng/webhook; browser/device/offline/deep link trong gói rehearsal này; rehearsal tải thật, pilot và nghiệm thu toàn BH-07. PostgreSQL/Auth fixture local không thay thế các cổng này.
