# BH-07 V8 — audit hồ sơ ngày 09/11/2026

Base/HEAD kiểm tra: `b72c563d9e519986dbd88ec98bcc3f015a41a442`, nhánh `feat/bh07-completion-local`. Chỉ đọc hồ sơ và Git; không sửa app/backend, không chạy browser/DB hoặc bộ test. Anti đang phụ trách V4 ở phạm vi riêng; audit này không đánh giá code/test/runtime V4 đang làm và không đổi verdict lịch sử.

## Phát hiện

**V8-D1 — P2, dự thảo quyết định rủi ro chưa cập nhật ledger.** [bh07_v8_risk_decision_draft.md](bh07_v8_risk_decision_draft.md), dòng 14, vẫn ghi “ledger đang triển khai test, chưa có verdict mới”, trong khi [review chốt b25aaef](review_b25aaef_ledger_final.md) và [ma trận hiện hành](bh07_completion_status_20261108.md) đã ghi ledger sentinel Web local RUN/PASS. Nếu dùng dự thảo này để xin quyết định, chủ dự án nhận sai phạm vi đã đo. Cần cập nhật kết quả ledger, giới hạn sentinel và tính độc lập chính xác trước khi trình bản quyết định cuối; giữ nguyên trạng thái chưa phê duyệt và các rủi ro rendered/instructions/listener/native. Không sửa bundle lịch sử hoặc diễn giải thành toàn V2b sạch. Đây là lỗi hồ sơ hiện hành, không mở lại LGR9–LGR12 đã đóng.

Không thấy P0/P1 hoặc cổng core bị mất kết luận Đạt trong phạm vi tài liệu đã đối chiếu.

## Kết luận core kế thừa đã đối chiếu

| Cổng | Báo cáo chốt | Mốc source/docs đã resolve | Kết luận thực trong báo cáo |
|---|---|---|---|
| A | [review_4512c3a](review_4512c3a.md) | `4512c3a`, code `c339a47` | Đạt phần A DB/RPC local |
| B | [review_d7bac04](review_d7bac04.md) | `d7bac04`, code `a682007` | Đạt phần B; B1/B2 đóng |
| C | [review_02a9b85](review_02a9b85.md), [phụ lục log](review_02a9b85_logs_3d5583b.md) | `02a9b85`, docs `f63e5a4`, bổ sung `3d5583b` | Đạt C; C1–C3 đóng; thiếu bảy log đã được đóng bằng phụ lục |
| D | [review_3d590a8](review_3d590a8.md) | `3d590a8`, docs `ce4522d` | Đạt tích hợp local |
| HTTP/Auth | [review_f9159dd](review_f9159dd.md) | `f9159dd`, docs `0758b72` | Đạt HTTP/Auth local; H1/H2 đóng |
| Concurrency HTTP/Auth | [review_cbcc46c_r2](review_cbcc46c_r2.md) | `cbcc46c`, docs `bb940280333aec96457dd3014aabba9f66adf4ae` | Đạt; H3/H4 đóng, H1/H2 giữ đóng |
| R0 | [review_31fced4](review_31fced4.md) | `31fced4` | Đạt readiness docs-only; R1–R4 đóng |
| V1 | [chốt 448c50f](v1_acceptance_448c50f.md), [review/QA](review_6283dbb.md) | checkout `6283dbb`, report/evidence `448c50f` | Đạt V1 local; reviewer/QA xác nhận không tham gia viết/sửa Browser |

Đã đọc kết luận và giới hạn thực tế, không chỉ đọc tên file hay bảng trạng thái. V1 độc lập dựa trên reviewer/QA ở `review_6283dbb.md`, không dựa vào lượt điều phối của Codex từng sửa Browser. R0 và vòng 2 concurrency là audit docs/evidence kế thừa các lần runtime trước, không gọi là runtime mới. Full SHA sai trong tin nhắn concurrency cũ đã được báo cáo đính chính; không coi đó là ref nghiệm thu hiện hành hoặc mở lại H3/H4.

## Kiểm chứng thực hiện trong lượt này

- `git rev-parse HEAD`, `git branch --show-current`, `git status --short`: đúng HEAD/nhánh nêu trên; có các file mới do root/Anti đang làm, không khai working tree sạch trong toàn lượt audit.
- `git show --no-patch --format="%H %s" 4512c3a c339a47 a682007 d7bac04 02a9b85 f63e5a4 3d5583b 3d590a8 ce4522d f9159dd 0758b72 cbcc46c bb940280333aec96457dd3014aabba9f66adf4ae 31fced4 6283dbb 448c50f b25aaef a095a457f2f12e8d65fe69ba5a3ca3ddb79ea110 511ce61 b036e9e`: 20 refs resolve, exit 0.
- `Test-Path` trên chín đường dẫn evidence đại diện của A/B/C/D/HTTP/concurrency/R0/V1/ledger: 9/9 `True`; các báo cáo trong bảng được đọc trực tiếp thành công. Phạm vi này không phải audit toàn bộ link/anchor/manifest trong repository.
- Kiểm bổ sung toàn bộ Markdown link local của đúng ba file `bh07_completion_status_20261108.md`, `bh07_v8_risk_decision_draft.md`, `review_b25aaef_ledger_final.md`: trích qua `ctx_read`, chuẩn hóa đường dẫn, `Test-Path` cho **28/28 đường dẫn riêng biệt đều True**. Hai link có fragment cùng trỏ heading `4.11. V8 — Nghiệm thu toàn BH-07`, heading đã đọc tại readiness dòng 256. Không có link local hỏng trong phạm vi ba file này.
- 19 chuỗi commit tham chiếu trong ba file trên đều resolve bằng `git show --no-patch --format="%H %s"` sau khi phân loại hai chuỗi 16 ký tự `846b2bb04ddf15c1`, `7df4026c62399be2` là **archive handles**, không phải Git SHA. Lần dò thô ban đầu gộp archive handle vào Git báo exit1 đúng expected unknown revision; không coi archive handle là lỗi provenance. Các kiểm tra 20 ref core và 19 ref ba file có phần giao nhau, không cộng thành 39 ref duy nhất.
- Thử kiểm tra tự động bằng `python -c` bị lean-ctx chặn trước thực thi; không nhận là kết quả kiểm chứng và không chạy lại qua công cụ khác để né chặn. Các kiểm tra Git/path nêu trên được thực hiện riêng bằng lệnh read-only được phép.

## Checklist còn lại để xét V8

1. Đóng V8-D1 trước khi trình quyết định. Cập nhật ma trận theo kết quả local mới, giữ timeline và attribution chính xác.
2. V4: thực thi/review rehearsal backup với hai HTTP writers, ranh giới snapshot/commit, invariants finance/ledger/audit/idempotency và cleanup. Thiết kế/test code chưa phải runtime PASS.
3. V2: matrix mobile/browser/OS/deep link ngoài Chromium đã đo vẫn NOT RUN. Chưa có thiết bị Android/iOS và môi trường phù hợp được xác nhận trong hồ sơ hiện hành.
4. V2b: ledger/bank/expense/payment ID sentinel đã có kết luận phạm vi Web local; rendered retention vẫn unattributed, PaymentInstructions/listener/native chưa đo, whole-model/app-wide UNKNOWN. Cần bằng chứng bổ sung hoặc quyết định rủi ro riêng cho phần chưa kiểm chứng; không gọi sentinel sạch là toàn app sạch.
5. V3/V5/V7: thiếu managed staging/restore và policy evidence; target/window/release/rollback; workload/SLO/pilot/support và quyết định tương ứng. Hoàn tất kiểm chứng được giao hoặc chủ dự án ban hành quyết định chấp nhận rủi ro theo từng cổng, nêu lý do, giới hạn, giảm thiểu và thời điểm. Không ký thay từ chỉ thị “tiếp tục/hoàn thành BH-07”.
6. V5b giữ Đạt local theo [review_b036e9e](review_b036e9e.md); V6 giữ NOT RUN ngoài phạm vi. Không cần waiver thay cho V5b đã chốt, không tự mở banking/webhook.
7. Sau khi có kết quả và quyết định cuối: kiểm toàn bộ link/SHA/manifest trong hồ sơ acceptance, không còn P0/P1/P2 mở hoặc FAIL chưa xử lý; reviewer mới chốt V8 theo [readiness §4.11](bh07_readiness.md#411-v8--nghiệm-thu-toàn-bh-07).

## NOT RUN và kết luận

Không chạy lại test/analyze/DB/HTTP/browser/heap/restore/load/mobile; không kiểm manifest/hash toàn bộ bundle, source drift toàn nhánh hoặc mọi Markdown link/anchor trong lượt audit này. Không biến kết quả kế thừa thành số đo mới. Không merge/push/deploy/pilot/BH-08 hoặc thay quyết định chủ dự án.

**Chưa đạt điều kiện chốt V8/toàn BH-07:** còn V8-D1 và các bằng chứng/quyết định nêu trên. Các kết luận core local đã chốt được giữ nguyên trong phạm vi của chúng.

## Bổ sung 09/11/2026 — đóng V8-D1 sau sửa hồ sơ

Codex root sửa duy nhất hàng V2b của `bh07_v8_risk_decision_draft.md`; reviewer này đọc lại exact `git diff`, toàn dự thảo hiện hành và `review_b25aaef_ledger_final.md` dòng 3–23. `git diff --numstat -- docs/reviews/bh07/bh07_v8_risk_decision_draft.md` xác nhận 1 dòng thêm/1 dòng bỏ; `git diff --check` trên file này exit 0; `Test-Path` tới review ledger mới được dẫn trả `True`.

Hàng mới khớp bằng chứng đã chốt: source sạch `b25aaef`, hai chu kỳ/tám epochs, ledger ID present/reachable ở Owner và absent/unreachable sau logout/actor. Phân biệt đúng runtime do Codex implementer chạy với review source/artifact và auditor độc lập; không nhận đây là runtime QA độc lập. Dòng mới giữ rendered retention chưa quy kết, không suy sentinel thành toàn model/cache/listener sạch, và giữ PaymentInstructions/listener/native chưa đo. Header dự thảo, cả sáu ô **CHƯA PHÊ DUYỆT**, biện pháp hạn chế dữ liệu thật/profile dùng chung và điều kiện quyết định chủ dự án đều giữ nguyên; không phát sinh chấp nhận rủi ro hoặc quyền tích hợp/triển khai.

**Đóng V8-D1 P2 trong phạm vi sửa hồ sơ này.** Không còn P0/P1/P2 mở được phát hiện trong audit tài liệu đã nêu; các đoạn trước giữ lịch sử trước sửa. Không chạy broad tests/runtime vì chỉ thay tài liệu. V4 vẫn đang triển khai/review riêng; các bằng chứng/quyết định còn thiếu trong checklist vẫn còn. **Toàn BH-07/V8 chưa nghiệm thu**, không merge/push/deploy/pilot/BH-08.
