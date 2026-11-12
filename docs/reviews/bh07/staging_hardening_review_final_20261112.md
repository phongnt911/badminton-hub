# Staging hardening candidate — review chốt delta, 12/11/2026

**Đạt trong phạm vi SQL candidate/static tests/handoff được review; không còn P1/P2 mở trong phạm vi này.** Đóng các finding của [vòng1](staging_hardening_review_r1_20261112.md) và [vòng2](staging_hardening_review_r2_20261112.md); không mở thêm vòng sửa.

- Static validation nay dùng whole-statement matching cho đúng22statement, không nhận extra grantee/search_path schema/clause. Reviewer tự chạy `python tests/test_bh07_staging_hardening.py -v`: **6 PASS**, exit0, gồm controls từ chối extra anon GRANT, extra schema, WITH GRANT OPTION và extra statement. Không nhận static suite là DB authorization runtime.
- SQL không đổi: reviewer kiểm SHA256 thực `f9c821130802f2ea5cd508d8388cad3989da2e5b8fb8b5d6a3c3d2c512ef6081`, khớp candidate hash trong local PASS receipt. Giữ đúng10helper signatures và2trigger search_path pins, không đổi function bodies/views.
- Invalid unrun SQL proposal đã bỏ; handoff liên kết tương đối tới executable probe, runtime report, PASS receipt và hai FAIL attempts. Baseline/policy-presence tautologies và claim bảo đảm RLS đã được bỏ từ vòng trước.
- Handoff ghi đúng **Codex** đã chạy42focused checks +21existing clean DB cases với PostgreSQL17/auth.uid stub, không phải reviewer runtime QA độc lập, GoTrue/JWT/managed Auth hoặc hosted staging apply. Không retag hai attempt FAIL và không tuyên bố mọi thao tác đều SQL ROLLBACK.

Reviewer đã đọc [probe](staging_hardening_local_probe_20261112.py), [report](staging_hardening_local_runtime_20261112.md) và [PASS receipt](staging_hardening_local_pass_20261112.json) ở vòng trước; không chạy lại Docker/SQL ở vòng chốt. Cụm “danh mục Docker rỗng” trong handoff được hiểu theo source probe: **inventory lọc đúng owned container ID trả rỗng**, không phải toàn máy không có container. Đây là lưu ý diễn đạt không chặn closure.

Chưa có canonical migration vì CLI migration-new còn bị chặn; không bypass. Hosted anonymous-helper exposure vẫn mở cho đến khi áp dụng đúng target và kiểm chứng riêng. Authenticated arbitrary-UUID probing, các advisor khác và whole-app security không được đóng bởi candidate giữ nguyên body này. V3/V5/V7/BH-07/V8 vẫn chưa nghiệm thu; review không cấp quyền deploy/pilot/BH-08.

Reviewer chỉ tạo báo cáo này, không sửa SQL/test/handoff hoặc thay đổi tài nguyên môi trường.
