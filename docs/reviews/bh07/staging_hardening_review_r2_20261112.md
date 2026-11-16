# Staging hardening candidate — review vòng 2, 12/11/2026

**Chưa đóng gói bàn giao; còn hai P2 trong test/handoff.** SQL candidate giữ nguyên; không phát hiện P1 mới trong phạm vi sửa. Reviewer chỉ đọc source/artifact và tự chạy static tests, không chạy Docker/hosted SQL hoặc sửa source.

## P2 còn mở

1. **Static allowlist chưa exact.** `test_ten_helpers_signatures_and_grants` và `test_two_legacy_triggers_alterations` dùng `re.search` không neo cuối statement. Thay một GRANT bằng `GRANT EXECUTE ON FUNCTION public.is_app_admin(UUID) TO authenticated, anon;` vẫn thỏa regex, giữ22statement và không vi phạm negative checks; anon exposure được mở lại nhưng suite vẫn có thể xanh. Tương tự suffix search_path bổ sung schema không bị chặn. Dùng full statement match hoặc đối chiếu toàn bộ tập22statement chuẩn hóa; thêm mutant controls cho extra grantee/search_path/statement suffix.
2. **Proposed semantic SQL chưa thực thi đúng schema/phạm vi nó mô tả.** Handoff dòng167–169 tạo profiles mà không tạo auth.users FK, dòng250–251 giả định cột/giá trị session_players không khớp canonical; UPDATE sessions hiện đại không chứng minh legacy-shaped sync function được kích hoạt/đúng dữ liệu. Guest block chỉ kiểm count view, không gọi public/unlisted detail hoặc private/draft denial; caller block chỉ hỏi helper với UUID của chính caller, không chứng minh row isolation. Dù được ghi NOT RUN, recipe này không đáp ứng claim executable controls. Thay bằng liên kết probe/receipt Codex đã thực thi và mô tả chính xác phạm vi, thay vì duy trì SQL chưa chạy có giả định sai.

## Finding đã đóng và kiểm mới

- Hai test baseline literal/policy-presence đã bỏ; module/handoff nay phân biệt static syntax với runtime semantics, không còn khẳng định đảm bảo RLS/loại bỏ hồi quy.
- Các link nguồn/bằng chứng trong handoff dùng đường dẫn tương đối đúng từ `docs/reviews/bh07`; finding link máy riêng đóng.
- Reviewer tự chạy `python tests/test_bh07_staging_hardening.py -v`: **6 PASS**, exit0. Không chạy mutant hoặc semantic runtime trong lượt này; fail-open allowlist ở trên được xác định từ logic regex và statement-count checks.

## Artifact runtime Codex được đọc

[Local runtime report](staging_hardening_local_runtime_20261112.md), [probe](staging_hardening_local_probe_20261112.py) và [PASS receipt](staging_hardening_local_pass_20261112.json) nhất quán về42focused checks và21existing clean DB cases PASS, cleanup_verified=true, candidate LF-normalized SHA256 `f9c821130802f2ea5cd508d8388cad3989da2e5b8fb8b5d6a3c3d2c512ef6081`. Source probe thực hiện10anon deny/authenticated execution controls, guest public/unlisted/private/draft, public listing/summary, caller row identity và legacy-shaped temp-table trigger DML; receipt ghi các check tương ứng. Reviewer đọc artifact, không nhận đây là runtime do reviewer tự chạy.

Report giữ đúng hai attempt FAIL trước đó và lý do verifier/readiness; không retag chúng PASS. Runtime dùng PostgreSQL17 cô lập, auth.uid stub, không GoTrue/JWT/managed Supabase. Fixtures được dọn bằng hủy container sở hữu sau kiểm label và xóa exact ID, không phải mọi thao tác đều SQL ROLLBACK. Candidate vẫn noncanonical; hosted helper exposure chưa sửa, views/advisor và authenticated arbitrary-UUID probing chưa được đóng. V3/V5/V7/BH-07/V8 vẫn chưa nghiệm thu.
