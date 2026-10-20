# Review BH-07B — d7bac04 — vòng 1/2

Ngày 20/10/2026. Nhánh `feat/bh07b-data`, commit review `d7bac04df0712ab37ab5568900ee2da60b95b612`, tested code `a682007f6cd85931b410ec2930fd40cdd3fc73f4`, base A đã Đạt `fd38838d85fed31603eae99ed363cf202650aeee`. Fetch trực tiếp ref nhánh, fast-forward từ review công bố `135ff2316c8ee9b83bd9797b3257136256aea7ce`; checkout ban đầu sạch, không có thay đổi local cần cất. Đọc AGENTS, docs/04/08/ai/REVIEWER, BH-07 trong docs/09, docs/25 §7–9, review vòng 0 và evidence, handoff/summary sửa. Xem diff main...HEAD, tách B bằng diff base A...HEAD và sửa vòng này bằng diff 135ff23...HEAD.

## Phát hiện

Không có phát hiện P0/P1/P2 còn mở trong phạm vi B được kiểm chứng. Đóng hai phát hiện vòng 0:

- **B1 P2 — Đã đóng**, `lib/providers/finance_provider.dart:296`: FORBIDDEN vô hiệu summary/quyền finance cache, `hasSummary=false`; giữ lỗi, scope và đường retry. Probe gốc với DTO/42501 từ fixture RPC vòng 0 nay PASS. Control transport giữ cache kèm lỗi; kiểm thử retry, tiền NULL, đổi actor/logout và response trễ PASS. Không diễn giải đây là kiểm chứng token HTTP hoặc thu hồi quyền trên thiết bị thật.
- **B2 P2 — Đã đóng**, `lib/providers/session_provider.dart:332`: ghép theo session ID duy nhất; cursor thô tại dòng 338 tăng theo số dòng server trả, hasMore lấy từ trang thô (model tại `lib/models/session.dart:510`). Probe gốc phát lại ba trang OFFSET `[0,2,4]` khi có buổi mới chen đầu, giữ kỳ vọng `[D,C,B,A]`, nay PASS. Test filter/actor/serial/loading/refresh cùng suite PASS. Không yêu cầu load-more tự lấy buổi vừa chen đầu; refresh mở lại cửa sổ.

## Kiểm chứng độc lập

[Summary](review_d7bac04_evidence/summary.json), [analyze](review_d7bac04_evidence/analyze.log), [Flutter](review_d7bac04_evidence/flutter.log), [exit từng runner](review_d7bac04_evidence/regression-exits.json), [orchestrator](review_d7bac04_evidence/run_regression.py). Các JSON/log mới nằm cùng thư mục; không dùng log tự báo của người triển khai thay lần chạy này.

| Lệnh/nhóm | Kết quả tự chạy |
|---|---|
| Flutter 3.47.7 / Dart 3.13.5 `flutter analyze --no-pub` | 0 issue, exit 0 |
| `flutter test --no-pub`, trước khi thêm probe tạm | 212/212 PASS, exit 0 |
| BH-02 + extended | 33 +14 PASS |
| BH-03 + retry/concurrency | 48 +22 PASS |
| BH-04 / BH-05 / BH-06 | 44 /90 /84 PASS |
| Tổng hồi quy DB BH-02..06 | 335/335 PASS, mọi runner exit 0 |
| `python3 docs/reviews/bh07/run_bh07_tests.py` | 23/23 PASS (21 CLEAN +2 upgrade), exit 0 |
| BH-06 integration / upgrade | 7/7 +3/3 PASS, exit 0 |
| Probe reviewer vòng 0 phát lại | 6/6 PASS, exit 0 |

[Probe replay](review_d7bac04_evidence/provider_probe_replay.dart.txt), [diff duy nhất đường dẫn fixture](review_d7bac04_evidence/probe-path.diff), [hash replay/fixture](review_d7bac04_evidence/probe-replay-check.json), [log](review_d7bac04_evidence/probes.log). Không đổi kỳ vọng nào. Dùng nguyên [fixture RPC vòng 0](review_1298490_evidence/rpc-fixture.json), không dựng lại fixture trong lượt này. Hai probe B1/B2 chuyển từ FAIL vòng 0 sang PASS; bốn control transport, response trễ khác scope, complete VERSION_CONFLICT và BILLING_STALE giữ PASS, retry cùng intent giữ request ID. Probe là provider thật/repository mock phát lại response, không phải Dart→HTTP→DB.

PostgreSQL17 trong Docker `bh02-review-bh06`, network none, dữ liệu giả, Auth stub + SET ROLE; runner tự dựng DB test riêng. Extended/retry chạy sau runner nền tương ứng. Không apply DB remote. Model/repository đối chiếu DTO/signature A; tiền nullable giữ NULL, outstanding đọc từ server. Migration/RPC A và lib/screens không đổi so với base A. Hash [lib/test/migration](review_d7bac04_evidence/source-hashes.json) trước/sau trùng, cây mã trùng `a682007`; chỉ báo cáo/bằng chứng/trạng thái được publish.

Một số JSON ghi worktree_dirty=true do JSON và probe tạm sinh trong lúc chạy; không dùng metadata đó để tuyên bố toàn worktree sạch trong suốt kiểm thử. Checkout trước chạy sạch; đã bỏ probe tạm khỏi test/ và kiểm lại hash nguồn sau chạy. Raw log đỏ/xanh mà handoff tác giả tham chiếu không được commit trong bh07b_fix_evidence; không xác nhận độc lập số test-first 2 FAIL/targeted 58 từ các log vắng đó. Bằng chứng đỏ reviewer vòng 0 được giữ nguyên và cả sáu kỳ vọng nay tự chạy xanh. Không chạy lại probe lịch sử A/BH-06 hoặc các cổng môi trường thật rồi cộng vào số mới.

## Kết luận

**Đạt** — chỉ phần B BH-07 local tại `d7bac04`, tested code `a682007`, vòng sửa 1/2; B1/B2 P2 đã đóng, không có P0/P1/P2 mới. A giữ kết luận theo tested SHA trước. Không tự chuyển C/D, sửa triển khai, merge main hoặc deploy; kết luận không phải nghiệm thu toàn BH-07/pilot.

**NOT RUN:** HTTP/PostgREST/JWT/Supabase Auth thật và repository/RLS qua token thật; UI C; thiết bị/browser/deep link/offline/reopen; ngân hàng/VietQR/tải ảnh/webhook/chuyển tiền thật; staging/production, apply DB thật, backup/restore rehearsal, concurrency HTTP và pilot D. Local/PostgreSQL/Auth stub không thay các cổng deploy/nghiệm thu này.
