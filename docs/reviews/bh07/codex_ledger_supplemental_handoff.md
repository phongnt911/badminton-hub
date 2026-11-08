# Codex supplemental ledger repair — chờ runtime

2026-11-08. Owner giao rõ “codex tự sửa” sau review `c427e27`, cho phép sửa trực tiếp ngoài điểm dừng vòng 3. Quy tắc chung vẫn tối đa 3 vòng; đây là ủy quyền bổ sung cụ thể, không tự đổi thành unlimited rounds. Codex là implementer và người chạy self-check; Code Reviewer riêng review source độc lập, không viết code.

Base `2167363`. Sửa LGR11: finally dùng lại `evaluateCleanupState`, catch enumeration errors thành count null/unverified để tiếp tục cleanup DB; containment dùng `path.relative`. Sửa LGR12: chấp nhận đúng ba bảng source metadata `scopes`, `scope_context_vars`, `scope_uses` theo [serializer V8 15.6.75.27](https://raw.githubusercontent.com/v8/v8/15.6.75.27/src/profiler/heap-snapshot-generator.cc), kiểm layout/kiểu int/width/count/node-string indexes và nonnegative depth/count. Giữ signed scope IDs, legacy snapshots, unknown-key rejection, graph/retention gates. Không sửa app/backend/schema.

Codex chạy 3 test regression trước sửa: 2 FAIL đúng scope-key và EACCES finally; sau sửa 17 targeted PASS (3 mới +14 cũ). 11 malformed scope controls trong subtests đều bị từ chối. Fresh about:blank Chrome156/V8 15.6 probe real oracle exit0, browser/profile/raw dump directory đã dọn (archive `2cc0dfdf518f98a9`); stdout probe cũ vẫn có diagnostic placeholder ngay cả khi exit0, không diễn giải placeholder đó là lỗi scan mới. Đây không phải app runtime. Fixture controls8/8; node syntax pass. Full suite đang kiểm chứng, không khai count xanh trước khi hoàn tất.

**Kết quả sau khi full suite kết thúc:** 437 Python PASS, 173.785s, exit0, archive `846b2bb04ddf15c1`. Chạy trên working tree trước commit; không gọi là clean-checkout replay. App không đổi nên giữ kết quả analyze0/247Flutter+1skip đã ghi ở review trước, không khai lần chạy Flutter mới.

Reviewer độc lập không thấy P0/P1/P2 trong supplemental source repair, xác nhận pinned layouts/counts và cleanup fail-closed/continuation. Chưa có live ledger runtime mới. Toàn V2b/BH-07/V8 chưa nghiệm thu; risk draft chưa có acceptance của owner. Không merge/push/deploy/pilot/BH-08.

Runtime kế tiếp dùng reviewer wrapper đã review, output mới `ledger_heap_20261108_codex_evidence`; không ghi đè bundle cũ. Tested SHA phải là HEAD sạch thực tế khi chạy, không gán source SHA trước đó cho lần runtime mới.
