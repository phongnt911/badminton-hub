# Review BH-06A vòng sửa 1 — 706bd73

Ngày 16/10/2026 (Việt Nam). Tested HEAD `706bd73428b3c59261ff73df5cbd90be64dbb571`; code sửa R1/R2 `83586ed`, test tái hiện `59baa25`, base main `c35dd27`. Vai trò reviewer theo `docs/ai/REVIEWER.md` tại `chore/ai-roles=163bc45`. Đọc diff `origin/main...HEAD`, tập trung phần sửa sau `1ff4d97`; giữ [review trước](review_e3c73c1.md) là baseline lịch sử. Không sửa code triển khai/migration/test tác giả.

## Phát hiện P0/P1/P2

Không có phát hiện cần mở trong phạm vi kiểm chứng lượt này. R1/R2 của review e3c73c1 được đóng tại tested HEAD dựa trên runner và probe độc lập, không suy kết luận từ báo cáo của người triển khai.

## Kiểm chứng độc lập

[Summary và hash migrations](review_706bd73_evidence/summary.json), [probe JSON](review_706bd73_evidence/probes.json), [probe log](review_706bd73_evidence/probes.log). Flutter3.47.7/Dart3.13.5; PostgreSQL17 container `bh02-review-bh06`, `--network none`, fixture giả, Auth stub và SET ROLE authenticated/anon. Toàn chuỗi migration trên CLEAN/LEGACY.

| Lệnh/nhóm | Kết quả reviewer tự chạy |
|---|---|
| flutter analyze --no-pub | No issues found, exit 0 |
| flutter test --no-pub | 137/137 PASS, exit 0 |
| BH-02 baseline + extended | 33 + 14 PASS, exit 0 |
| BH-03 + retry | 48 + 22 PASS, exit 0 |
| BH-04 | 44/44 PASS, exit 0 |
| BH-05 | 90/90 PASS, exit 0 |
| BH-06 | 84/84 PASS (42 ca × CLEAN/LEGACY), exit 0 |
| Probe reviewer giữ kỳ vọng từ review trước | 8/8 PASS, exit 0 |

Tổng runner DB **335/335 PASS**; 8 probe tính riêng. Script probe chỉ thay tên DB và thư mục output so với bản review trước, không đổi kỳ vọng. Các kiểm tra outsider đọc khách offline và đường bank cũ khi stale nay từ chối; các control giữ nguyên. Runner mới còn kiểm cohost không finance, finance hợp lệ và not_finalized cho cả hai endpoint. Không sửa expected hoặc bỏ ca cũ để làm xanh.

Cây sạch trước chạy. JSON runner sinh tạm trong repo để runner phụ baseline→extended, BH03→retry đọc; sau mỗi nhóm chuyển ra scratch trước khi thêm bằng chứng review. Metadata dirty ở một số runner có thể phản ánh JSON bằng chứng đang chờ chuyển, không phải đổi code. Chạy BH-06 và regression độc lập có thể sinh JSON cùng thời gian; toàn bộ tested source/migrations giữ ở HEAD trên. Không apply DB remote.

## Kết luận

**Đạt phần A BH-06 tại `706bd73`** trong phạm vi DB/RPC/RLS/projection và bằng chứng trên. Kết luận thay trạng thái Chưa đạt/Chờ review của các snapshot trước; giữ nguyên chúng để truy vết. Không phải nghiệm thu toàn BH-06 hoặc bản tích hợp A+B+C. Không tự chuyển B/C, merge main hoặc deploy.

**NOT RUN:** PostgREST HTTP/JWT/Supabase Auth thật; thiết bị/browser e2e; repository/provider/UI BH-06B/C; apply staging/production, backup/restore; concurrency qua HTTP; đối chiếu bank/VietQR thực tế và pilot/BH-07. PostgreSQL/Auth stub không thay các cổng này; không gọi kết quả là production-ready.
