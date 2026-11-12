# Staging hardening candidate — review vòng 1, 12/11/2026

**SQL candidate đúng phạm vi tối thiểu được đọc; chưa đủ bàn giao để áp dụng hosted.** Không phát hiện P1 trong SQL candidate. Reviewer không sửa code/SQL, không tạo migration canonical hoặc chạy hosted SQL. File vẫn là candidate ngoài `supabase/migrations`; CLI migration-new còn bị chặn, không có quyền bypass.

## P2 cần sửa trong bàn giao/kiểm chứng

1. **Chưa có đề xuất SQL semantic test có rollback như đầu bài yêu cầu.** Handoff chỉ có mô tả và static tests; chưa có recipe cụ thể kiểm quyền đủ mười helper dưới anon/authenticated, RLS có populated fixtures/caller isolation, guest compatibility và trigger behavior trong transaction kết thúc ROLLBACK. Handoff dòng6 khẳng định bảo đảm RLS vẫn bình thường vượt bằng chứng hiện có. Bổ sung proposal NOT RUN với expected results và giới hạn; không cần chạy hosted trong vòng sửa này.
2. **Hai static tests không kiểm điều chúng mô tả.** `test_rls_policies_use_authenticated_helpers` chỉ kiểm tên policy và helper xuất hiện độc lập trong migration, không kiểm helper thuộc policy đó hoặc role authenticated; `test_empty_staging_baseline_alignment` tạo dict literal rồi so với chính constants. Chúng vẫn PASS nếu binding sai hoặc receipt baseline thay đổi. Kiểm block policy/role thực và đọc sanitized baseline receipt, hoặc bỏ assertion giả cùng claim xác minh baseline. Static tests không chứng minh DB semantics.
3. **Handoff có link gắn máy riêng.** Các link `file:///C:/Users/POTA/...` tại dòng11–12,19–21,42 không portable cho checkout khác. Dùng repo-relative Markdown links để người review truy được source/evidence.

## Đối chiếu source và kiểm mới

- Candidate chứa đúng mười signature khớp init migration dòng543–701; thu hồi PUBLIC/anon và giữ authenticated EXECUTE. Đúng hai ALTER FUNCTION pin `public, pg_temp`; không đổi body/view/table/data.
- Canonical init policy `venues_select_active` dòng1150–1151 là anon predicate không dùng helper. Các policy helper đã đọc nhắm authenticated, ví dụ dòng1153–1154 và1202–1223.
- Guest RPC `get_session_public_detail` trong migration BH04 dòng9–102 là SECURITY DEFINER, anon được grant; helper calls gắn actor và public/unlisted guest path được giữ. `list_public_sessions` dòng626–686 là SECURITY DEFINER, đọc public projection, vẫn được grant anon. Candidate không revoke hai guest RPC này. Không thấy dependency guest trực tiếp bị phá trong các đường đã đọc; đây là source reasoning, chưa phải DB guest regression PASS.
- Reviewer tự chạy `python tests/test_bh07_staging_hardening.py -v`: **8 PASS**, exit0. Không gọi kết quả static này là grant/RLS/guest runtime PASS. Không có RED behavioral evidence được reviewer xác nhận.

Không kết luận authenticated arbitrary-user probing đã được sửa: candidate giữ authenticated EXECUTE và không thay caller-binding/body, đúng phạm vi được giao. Views/advisor còn phải triage và populated isolation phải được đo riêng. Không có security finding được đóng chỉ nhờ review candidate; V3/V5/V7 và toàn BH-07/V8 vẫn chưa nghiệm thu, không deploy/pilot/BH-08.
