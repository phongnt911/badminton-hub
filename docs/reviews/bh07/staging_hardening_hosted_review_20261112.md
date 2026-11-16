# Hosted hardening — independent post-apply review, 12/11/2026

**Đạt trong phạm vi hardening mười anonymous helper và hai trigger search paths trên đúng test staging `mxqpukhfiugdwsjsbihj`; không có P1/P2 mới trong delta được review.** Không phải whole-app security clearance hoặc nghiệm thu BH-07/V8.

Reviewer đọc [runtime report](staging_hardening_hosted_runtime_20261112.md), [sanitized receipts](staging_hardening_hosted_receipts_20261112.json) và toàn bộ [HTTP probe](staging_hardening_hosted_probe_20261112.js). Canonical migration đã được review riêng; receipt ghi đúng source-file hash `bcc8ef85cccc9dbd480cb9ee8c1fd831eef7d6e042b187e074fe93887a133819`, hosted execution version `20261112151606` và19history entries. Version mapping vẫn chưa đồng nghĩa CLI history đã được reconcile.

## Kiểm mới do reviewer thực hiện

- Chạy `node docs/reviews/bh07/staging_hardening_hosted_probe_20261112.js`: exit0, **15/15 PASS**. Mười helper đều401/42501; public summary/venues/list-public RPC đều200 và0row; private outstanding/bank getter đều401/42501. Probe fixed đúng target, chỉ gọi read RPC/SELECT; đọc ignored publishable-key file mà không in/lưu key hoặc row data. Receipt mới ở `.build/bh07-staging-hosted-http-20261112.json`.
- Gọi read-only catalog SQL qua connected Supabase trên chính ref trên, đối chiếu12signatures: **10helpers anon EXECUTE=false/authenticated=true**; cả hai legacy trigger functions có `search_path=public, pg_temp`. Trigger-function EXECUTE grants còn nguyên; không nhầm chúng với10helper được revoke.

Reviewer không chạy DDL, tạo user/fixture hoặc thay đổi project. Lần SQL mới chỉ xác minh grants/config; không nhận counts/hash/advisor kế thừa là reviewer tự đo lại.

## Đối chiếu artifact và giới hạn

Before/after receipt giữ12body hashes và3view hashes không đổi;21public tables/21RLS, auth_users/sessions/payments bằng0. Advisor artifact không còn mutable-path notice; anon-callable definer19→9, hai definer views và62authenticated-callable functions vẫn còn. Report không diễn giải health0notice thành security PASS toàn bộ.

Đóng anonymous direct-helper execution và mutable-path hardening đúng target/phạm vi đã đo. Các HTTP public controls chứng minh response200/array trên project rỗng; chưa chứng minh populated-row isolation, authenticated GoTrue/JWT/session behavior hoặc mọi guest flow. Authenticated arbitrary-UUID helper probing, chín anon-callable functions còn lại, view/advisor triage và các cổng vận hành vẫn cần đánh giá riêng.

Không tự ký risk acceptance, không tác động project cũ/paid features, không deploy/restore/load/pilot/BH-08. V3/V5/V7 và toàn BH-07/V8 vẫn chưa nghiệm thu. Reviewer chỉ ghi báo cáo này và receipt HTTP ignored do probe tạo.
