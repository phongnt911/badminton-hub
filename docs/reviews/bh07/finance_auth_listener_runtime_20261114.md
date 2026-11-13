# Finance Auth listener finite subgraph — 14/11/2026

**PASS local trong phạm vi AuthProvider → FinanceProvider và hai field `_instructions` / `_finance`. Full auth_listeners/V2b/BH-07/V8 chưa nghiệm thu.**

Runtime Codex trên Edge headless/Web profile, source `70a71ba0ceb1602d0be24cc56952e24ee11d4dfb`, git_dirty=false. App/backend/migrations không đổi từ aa755b5; 39 build/served artifacts khớp, main.dart.js SHA256 `a20b3d22a011fb511a76ee4daa11167410a6a61a2aba3f796f8ae0e1e65fe83e`. [Bundle và manifest](finance_auth_listener_20261114_evidence/manifest.json).

Hai chu kỳ Owner→logout→Cohost/Member, tám epochs cùng document. Baseline đầu Finance0 do lazy được ghi NOT_RUN_LAZY; baseline thứ hai Finance1 với hai field null. Cả hai Owner có Auth1/Finance1 rooted, đúng một active `_onAuthChanged$0` tearoff với `_receiver` trỏ cùng FinanceProvider; `_instructions` là PaymentInstructions và `_finance` là SessionFinance. Cả hai post_logout giữ listener/provider nhưng currentUser và hai field null. Hai post_actor quan sát hai field null; contract cho phép legit refetch, không suy ra toàn bộ model sạch.

Numeric counters đọc qua CDP own-properties trước/sau selected-field metadata, không gọi getter; counters ổn định/quiescent, cùng timeOrigin và mọi observer objectgroup release. Snapshot/CDP là hybrid nearby observations, **không atomic**. Strict companion auditor với build/web exit0, base attribution PASS_DTO_ATTRIBUTED. Scope không bao gồm mọi field, ClubProvider/SessionProvider contracts, toàn Auth graph, listener disposal, native/Dart VM, Firefox/Safari hoặc remote.

Anti triển khai và sửa tối đa3 vòng. Codex/reviewer phát hiện result-parameter overwrite false binding và hai lỗi tương thích runtime; Codex trực tiếp sửa với RED→GREEN controls. 14 Python tests và Node controls PASS. Reviewer kiểm source/control/artifact:21/21parent hashes, strict auditor actualbuild exit0; thiếu builddir reject1. Không có P0/P1/P2 trong package được review; không nhận runtime Codex là QA browser/DB độc lập.

R1 tại c83764d FAIL Owner method vì scanner dừng trước own `$_name` trên generated prototype tên BoundClosure. Guest calibration riêng xác nhận hình dạng và cleanup. R2 tại de00926 FAIL baseline vì Session method bị structural allowlist redact. [Hai bundle FAIL](finance_auth_listener_20261114_evidence/) giữ nguyên verdict/bytes; không retag thành PASS. Hai method Session/Club chỉ được giữ như metadata cấu trúc, không đóng gate hai provider đó.

Fixture disposable riêng, không gửi payment: payments/club_transactions/audit_events/operation_requests đều0. Helper R3 public21tables/94rows/schema/roles/other sequences khớp, Auth84→88. Root đối chiếu riêng toàn bộ R1/R2/R3: public/schema/roles/other sequences khớp, Auth83→88; Auth rows loại riêng theo hợp đồng. Fixture xác minh absent; raw heaps0, dumpdir/profile/state dọn; private config/provenance directory ngoài repo đã xóa. [Receipt root](finance_auth_listener_20261114_evidence/root-db-receipt.json).

Bước tiếp theo: kiểm riêng contract SessionProvider/ClubProvider và coverage field còn thiếu theo kế hoạch hiện hành. Không merge/deploy/pilot/BH-08 hoặc tự ký risk acceptance.
