# Ledger heap tooling — chốt review sau sửa 2/2

2026-11-08. Base `5512a72bc7c5c4377916f7afb663e1fe014c7376`; code được chốt `205dcd53cd42514cc26cbbd1cb72f76afe38f364`, nhánh `feat/bh07-completion-local`. Antigravity CLI Gemini 3.8 Flash High triển khai; Codex chạy kiểm chứng và Code Reviewer riêng kiểm tra source/probes, không sửa triển khai.

## P0/P1/P2

Không còn P0/P1/P2 trong phạm vi tooling ledger đã review. Đóng LGR1–LGR8 của [review đầu](review_5512a72_ledger_round1.md) và [review sau sửa 1/2](review_5512a72_ledger_round2.md). Chưa chốt runtime ledger hoặc toàn V2b/BH-07.

## Thay đổi và kiểm chứng

Runner có chế độ ledger dùng parent club/bank riêng và child transaction UUID, bảo vệ output mới, nạp ledger bằng UI sau finance/bank và trước Owner snapshot, rồi cleanup child trước parent. Oracle bắt buộc ledger được tải/reachable ở Owner, vắng ở baseline và sau logout/actor. Auditor kiểm contract version, classes, receipt boolean/hash/error cho ledger và cả hai parent; không nhận việc thiếu/false parent flags làm lý do bỏ kiểm. Helper kiểm local endpoint, full-row ownership readback và cleanup verified absence. Bank output-guard contract cũ được giữ.

| Kiểm chứng Codex chạy | Kết quả thật | Archive |
|---|---|---|
| `python -m unittest discover -s tests` sau bản cố định | **420 PASS**, exit 0 | `879edf9bd05c22eb` |
| Hai test chẩn đoán parent error sau chỉnh expectation | 2 PASS, giữ error injection + exit 1 + diagnostic cụ thể | `d5c21403134c21be` |
| Probe oracle độc lập | positive PASS; thiếu Owner ledger/baseline collision đều FAIL | logic tại [probe](ledger_round1_review_evidence/oracle_gate_probe.py) |
| Probe UI exported runner | text cancel và aria-only cancel đều PASS | [probe](ledger_round2_review_evidence/ui_semantics_probe.cjs) |
| Probe real auditor CLI | positive exit 0; omitted/false parent và bank cleanup failure đều exit 1 | `de981b8e5f882fea` |
| `node scripts/bh07_appheap/fixture_controls.js` | 8/8 controls, exit 0 | output tool trong phiên |
| `python scripts/bh07_appheap/heap_oracle.py self-test` | 34/34, exit 0 | `395159d59c8164c5` |
| `flutter analyze` | 0 issues, exit 0 | `e617a3b9faed17f2` |
| `flutter test --reporter compact` | 247 PASS + 1 SKIP, exit 0 | `161897fa62b27bbb` |
| Parse runner và staged whitespace | exit 0 | `node --check`, `git diff --cached --check` |

Full Python chạy trên working tree sau đó được commit nguyên source/test thành `205dcd5`; không gọi đây là clean-checkout replay. Flutter được chạy trong vòng review trên app không đổi; R2 chỉ đổi tooling Python/JS và test Python, không chạy lại Flutter để tăng count. `git diff` từ base cho `lib/`, `supabase/`, Dart `test/`, `web/`, pubspec và lock không có thay đổi.

Handoff R2 archive `1f0cdb9e2f04bb06` đã đóng source findings. Lượt kiểm chứng đầu 49 targeted còn hai assertion **mới** so nhầm literal field-name với diagnostic đang có; auditor đã trả exit 1 đúng. Anti chỉ sửa hai expected strings (conversation `73017a83-6ba3-4087-a527-3e3ba2b5b986`, archive `8f86290c9f6210cb`), không đổi production logic, error injection, exit assertions hoặc test bank cũ. Reviewer xác nhận không làm yếu test; đây là hoàn tất xác minh R2, không mở vòng sửa production thứ ba.

Một số source windows của auditor bị context gateway giữ lại; reviewer kiểm toàn bộ changed diff và hành vi real CLI, không tuyên bố đọc lại toàn bộ source dependency. Các bundle và draft lịch sử giữ nguyên byte; full suite giữ kiểm legacy generic/finance/bank.

## Runtime kế tiếp và giới hạn

**Heap/browser/DB fixture runtime mới NOT RUN tại thời điểm chốt tooling này.** Preflight chỉ đọc sáu bảng local, count và fingerprint đầy đủ (archive `ed7688e2d8860a38`); không dùng preflight thay runtime.

[Reviewer wrapper](ledger_tooling_review_evidence/runtime_review.cjs) đã qua review riêng: local env keys chỉ trong memory, row fingerprints/receipt absence trên sáu bảng gồm `club_transactions`, bảo vệ tracked app/tool/test/evidence hashes, đối chiếu HEAD sau chạy, auditor độc lập, clean-source/fresh-output và dump/profile absence. Chạy từ project root; file trong `build/` và bản đóng gói này cùng nội dung. Bundle mới sẽ được ghi ở `ledger_heap_20261108_r1_evidence`, với scoped `-text` Git attribute để giữ nguyên bytes; chưa có bundle tại bước này. Không dùng wrapper PASS nếu child/auditor/provenance/cleanup không đồng thời đạt.

PaymentInstructions chưa có ID độc quyền, listener/native/whole-model chưa đo. Rendered text tiếp tục là unattributed residual risk; không suy sentinel sạch thành toàn app sạch. Owner chưa ban hành risk acceptance cho V8; các yêu cầu quyết định đang chờ không được diễn giải là đã đồng ý.

**Đạt trong phạm vi tooling ledger tại `205dcd5`. Runtime ledger và toàn BH-07/V8 chưa nghiệm thu.** Không merge main, push, deploy hoặc pilot.
