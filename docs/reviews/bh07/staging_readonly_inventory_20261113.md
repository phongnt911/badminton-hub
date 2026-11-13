# Staging — kiểm kê chỉ đọc 13/11/2026

Toàn BH-07/V8 chưa nghiệm thu. Nguồn: Supabase connected `list_projects`, `get_project`, `get_advisors(type=security)` và hai truy vấn SELECT metadata view/grants/definition trong lượt này; không restore, deploy hoặc thay cấu hình remote.

| Project | Ref | Trạng thái | Region | PostgreSQL | Tạo lúc UTC |
|---|---|---|---|---|---|
| badminton-hub | vqelcjxljddxoyplgcvm | INACTIVE | ap-southeast-1 | 17.11.0.003 | 2026-10-06T11:51:02.425472Z |
| badminton-hub-staging | mxqpukhfiugdwsjsbihj | ACTIVE_HEALTHY | ap-southeast-1 | 17.11.0.018 | 2026-11-12T08:57:08.803544Z |

Listing mới thay giả định hiện hành “chỉ thấy một project INACTIVE”; không sửa lịch sử quan sát 10/11. ACTIVE_HEALTHY không chứng minh schema parity, backup/PITR, retention, offsite, restore hoặc release readiness. Các tool Supabase hiện có không cung cấp listing managed backup/PITR; chưa có backup ID, recovery window hay restore drill. V3/V5 vẫn NOT RUN.

## Security Advisor

[Kết quả chỉ đọc](staging_security_advisor_20261113.json): `security_definer_view` ERROR ×2 (`public_session_summary`, `player_outstanding`); `anon_security_definer_function_executable` WARN ×9; `authenticated_security_definer_function_executable` WARN ×62. Đây là advisory cần triage theo quyền thực tế và thiết kế RPC, chưa phải bằng chứng exploit hoặc severity P1/P2 của dự án. Chưa có kết luận đóng các cảnh báo.

SELECT metadata xác nhận cả hai view thuộc `postgres`, có `security_barrier=true`, không thấy option `security_invoker=true`. `player_outstanding`: anon SELECT=false, authenticated=true; `public_session_summary`: cả hai=true. [Định nghĩa remote và grants](staging_view_metadata_20261113.json) có predicate cùng cấu trúc migration `20261015051808_init_schema_v1_1.sql`: summary chỉ public và published/in_progress; outstanding giới hạn theo auth.uid hoặc management/finance access. Chưa kiểm chứng helper function/actor runtime, nên chưa đóng advisory và không kết luận dữ liệu đã bị lộ. Không truy vấn dòng dữ liệu nghiệp vụ.

Việc tiếp theo cho staging: review định nghĩa view/function và grants bằng truy vấn chỉ đọc có phạm vi; đối chiếu các role/actor và thiết kế local; lập danh sách chênh lệch cần sửa. Sau đó mới chuẩn bị target, backup ID/recovery window, rollback và phép thử restore để owner duyệt cụ thể. Không tự ký quyết định V3/V5 hoặc dùng generic “tiếp” làm quyền restore/deploy.
