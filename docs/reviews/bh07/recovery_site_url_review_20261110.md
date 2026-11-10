**Cập nhật sau review source:** candidate `7589179` đã full553test/549PASS+4SKIP và runtime V4 PASS; xem [review cuối](recovery_site_url_runtime_final_20261110.md). Phần bên dưới giữ mốc source review trước runtime.

# Review source/test recovery SITE_URL — 10/11/2026

**Đạt delta source/test Task3 ban đầu, không có P0/P1/P2 được phát hiện trong phạm vi này.** Anti triển khai, Codex và reviewer riêng review sau bàn giao. Base `791bcf7`, candidate là commit chứa source và báo cáo này. Chưa có runtime candidate mới; V4/BH-07/V8 chưa nghiệm thu.

Diff runner chỉ thêm `GOTRUE_SITE_URL=http://127.0.0.1:3000` vào target Auth envfile, nhất quán nguồn local. Không đổi image/API_EXTERNAL_URL/port/network/HTTP workload/padding/gate/cleanup. [Diagnosis](recovery_site_url_diagnosis_20261110.md) có actual failure metadata thiếu SITE_URL từ diagnostic wrapper; source GoTrue pinned xác nhận required.

Test mới đọc envfile thật tại target_auth_start trong main harness, chỉ trích site URL an toàn. Codex baseline replay compile Git blob791bcf7 rồi chạy test mới:1FAIL đúng thiếu SITE_URL; candidate53runtime-collection PASS. Đây là replay hồi cứu sau Anti bàn giao, không phải test Anti đã thực thi. Reviewer riêng tự chạy53/53PASS và không nêu P0/P1/P2; scoped GO cho clean-source Docker. Codex chỉnh hai điểm attribution/command baseline của handoff theo review, không sửa thêm implementation.

Log `.build/recovery-site-url-baseline-red.log`, `.build/recovery-site-url-green.log`; helper `.build/replay_site_url_baseline.py`. Full552test/548PASS+4SKIP thuộc diagnostics source791bcf7 trước một dòng env/test mới; full và runtime candidate mới sẽ được ghi riêng khi kết thúc. Flutter mới NOT RUN, app/schema không đổi.

Task tiếp: source sạch, runner thường không wrapper, phải hoàn tất target Auth/login/replay/final oracle/verified cleanup. Không nhận site URL unit test hoặc metadata cũ là runtime PASS. Không merge/deploy/pilot/BH-08 hoặc ký risk acceptance thay owner.
