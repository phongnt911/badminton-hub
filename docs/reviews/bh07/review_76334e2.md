# Review V2b app-profile heap — vòng sửa 2/2

- Reviewer: Codex, chỉ review, không sửa source. Codex từng làm các gói Provider/browser lịch sử; các gói đó không thay phép đo app-profile.
- Ngày: 26/10/2026, Asia/Saigon.
- Base review: `8c02605bad98edd9c55f44f57fdfea18c2ecac68`.
- Tested source runtime tác giả: `130af7d103cdea22c2f9ac9e4cb000f74ec02590`.
- Docs/checkout reviewer: `76334e21e41e6f9c018778d1f7b8d0a526012f3d`, sạch trước kiểm chứng.

## Kết luận

**Chưa đạt gói V2b app-profile heap vòng 2/2.** Các ca AH1, AH2-A/B, AH3-A/B, AH6 của vòng trước đã được khắc phục; AH4/AH5 giữ nguyên. Còn **2 P2 mới AH7/AH8**, không có P0/P1. Không xác nhận leak app từ các probe này. Runtime reviewer vẫn NOT RUN; runtime tác giả không được gán thành lần chạy độc lập.

**Dừng sau vòng 2/2, báo chủ dự án; không tự mở vòng 3 hoặc sửa source.** Theo [AGENTS.md](../../../AGENTS.md), “Sửa theo review: viết test tái hiện lỗi trước, sửa toàn bộ phát hiện P0/P1/P2 được nêu (kể cả P2), tối đa 2 vòng. Còn lỗi sau 2 vòng thì dừng và báo chủ dự án.” Chủ dự án cần quyết định phần còn lại hoặc ủy quyền ngoại lệ riêng. Provider/tooling, V1, V5b giữ Đạt local; V2b chưa đóng, toàn BH-07 chưa nghiệm thu.

## Rà soát gate cũ

| Gate | Kết luận trong phạm vi ca đã báo |
| --- | --- |
| AH1 — grammar/cấu trúc dump | Đóng các ca invalid literal, thiếu comma, garbage, leading zero, duplicate key, cắt/missing chunk/count/string-table order; presence null khi dump hỏng. AH7 bên dưới là lỗi **đếm giá trị trên JSON hợp lệ**, không phải lặp lại grammar control. |
| AH2-A — empty/null/list summary | Đóng; probe cũ có findings; CLI empty summary exit1. |
| AH2-B — report verdict/rows | Đóng; verdict trái JSON bị chặn; suite kiểm order/actor/rows/findings/build. |
| AH3-A — directory/file/broken links | Đóng trên Linux; probe directory symlink bị chặn, suite link controls không skip. Windows junction độc lập NOT RUN. |
| AH3-B — raw sentinel với metadata đầy đủ | Đóng ca đã báo, canary log bị chặn; sanitizer JS control qua. AH8 là bypass khi metadata nhận diện bị thiếu. |
| AH4 — UTF-8/BOM/CR và readonly | Giữ đóng; byte controls và hash bundle tác giả trùng Git sau các lần chạy. |
| AH5 — build/serve/reuse | Giữ đóng; guard8/8, reuse probe exit1, source bắt buộc build profile. Bundle ghi39 artifact; served-match kiểm hai entry index/main, không gọi đó là kiểm response đủ39 file. |
| AH6 — status links | Đóng; probe link cũ trả `[]`, suite link audit3/3 qua. |

## Phát hiện còn mở

Tái hiện cả hai bằng:

```bash
PYTHONPATH=. python docs/reviews/bh07/review_76334e2_evidence/closure_controls.py
```

Control chỉ ghi fixture giả trong tempdir và clone bundle synthetic; không sửa app/backend/bundle tác giả. Script in quan sát, exit0 không có nghĩa negative input đã bị từ chối. Positive literal vẫn present=true, positive đủ metadata được kiểm bởi104 test và probe cũ. Output riêng tại [closure_controls.json](review_76334e2_evidence/closure_controls.json).

### AH7 — P2: Hai JSON cùng giá trị có kết quả sentinel trái nhau

- File:dòng: `scripts/bh07_appheap/heap_oracle.py:180`.
- Cách tái hiện: `escaped_retained_bank` tạo hai snapshot cùng cấu trúc/count, khác duy nhất representation của bank canary: literal và `\uXXXX`. `json.loads(body) == json.loads(escaped)` là true; bank có trong `doc['strings']` đã decode ở cả hai.
- Kỳ vọng: cùng giá trị string table phải cho cùng presence; nếu bank vẫn retained ở post_actor thì cycle FAIL.
- Thực tế: cả hai `ok=true`; bản literal bank=true nhưng bản escaped bank=false. Bộ đủ bốn mốc (Owner literal, post_actor escaped giữ nguyên bank) vẫn `PASS`, findings rỗng. Full JSON parser đã đúng grammar nhưng kết quả decoded bị bỏ đi, `scan()` đếm raw bytes nên không thấy chuỗi đã escape.
- Ảnh hưởng: oracle có false-negative trên snapshot JSON hợp lệ, không đủ bảo đảm “sentinel vắng = đã thu hồi”. Chưa chứng minh Chrome155 dùng representation này trong tám dump tác giả đã xóa; probe này **không** chứng minh leak app hay phủ định quan sát raw bytes cụ thể của lượt tác giả.
- Cách sửa khuyến nghị: xác định presence từ string values đã decode của snapshot được validate, giữ matching policy rõ ràng (exact/substr tùy sentinel); tái sử dụng parse result thay vì parse lại. Thêm literal/escaped/mixed representation controls với cùng verdict và cycle retained FAIL, giữ grammar/null/probe controls. Không thay UI/backend.

### AH8 — P2: Thiếu length/hash làm tắt kiểm raw sentinel mà vẫn PASS

- File:dòng: `scripts/bh07_appheap/verify_evidence.py:408`, đặc biệt `:412`–`:413`.
- Cách tái hiện: `raw_bank_missing_length` và `raw_bank_missing_sha256_12`: tạo canary bank giả, ghi raw vào log; chỉ bỏ một trường length hoặc hash khỏi metadata, render report tương ứng và rehash LF-safe.
- Kỳ vọng: metadata cần để chứng minh sanitized bị thiếu phải có finding và FAIL; không công bố bundle sạch khi không thể chạy detector.
- Thực tế: cả hai trả `problems=[]`. `digest=None` không bị báo lỗi; thiếu/không hợp lệ length dẫn tới `continue`, bỏ toàn bộ tìm raw sentinel. Các fields còn lại/cycle/report/hash hợp lệ nên bundle được nhận. Với đầy đủ metadata cùng canary, probe cũ vẫn bắt đúng raw bank.
- Ảnh hưởng: bundle thiếu thông tin nhận diện sentinel có thể chứa raw private value nhưng qua auditor; đây là lỗi fail-open metadata, không khẳng định bundle runtime hiện tại đã lộ STK.
- Cách sửa khuyến nghị: bắt buộc bank/probe có length int dương thực và hash12 hợp lệ; mọi sentinel có mặt trong scans phải có metadata nhận diện tương ứng. Sentinel optional không khả dụng phải có trạng thái explicit và không được dùng cho claim/expectation. Thiếu metadata ⇒ finding, không skip. Test missing/null/0/bool/malformed length/hash + raw ở log/report/nested/extra file, giữ positive hash-only và expense-unavailable hợp lệ.

## Reviewer tự chạy

| Lệnh/kiểm tra | Kết quả |
| --- | --- |
| 5 suite Python theo handoff | exit0, **104/104**, không skip |
| `node scripts/bh07_appheap/build_guard.js --self-test` | exit0,8/8 |
| `node docs/reviews/bh07/review_8914b2f_evidence/build_probe.js` | exit1 đúng kỳ vọng từ chối reuse |
| Probe reviewer cũ `probes.py`, `extra_controls.py`, `link_audit.py` | nguyên bản, exit0; negative cũ bị chặn đúng, link `[]` |
| `python -X utf8 scripts/bh07_appheap/verify_evidence.py` | exit0 trên bundle tác giả |
| `flutter analyze --no-pub` | exit0,no issues |
| `flutter test --no-pub` | exit0,247 PASS+1 SKIP; HTTP/Auth suite disabled không phải phép đo HTTP mới |
| `node --check scripts/bh07_appheap/run_app_profile_heap.js` | exit0 |
| New closure controls | exit0, ghi false-green AH7/AH8; không dùng mock app/repository |
| Scope/source/whitespace | `lib/`,`test/`,`supabase/` không đổi từ base review; source tree docs commit bằng tested source; diff-check exit0 |
| Author manifest và readonly | 3/3 entry,4 file gồm manifest; hash sau mọi lệnh bằng Git blob docs commit, strict UTF-8 LF thực tế hợp lệ. Không generate/chạy runner vào bundle tác giả. |

Evidence riêng [review_76334e2_evidence/](review_76334e2_evidence/); `provenance.json` ghi source/docs/dirty/exit/count và hashes tác giả. Reviewer Linux/Node24.19.0/Flutter3.47.7; tác giả Windows/Node24.21.0/Flutter3.47.6/Chrome155. Log reviewer chuẩn hóa progress CR sang LF và bỏ padding cuối dòng analyze khi đóng gói; bytes tác giả không đổi. Audit metadata runtime tác giả ghi source sạch130af7d,2cycle/8snapshot,bank present/absent theo mốc,profile build61,3s và cleanup; không diễn giải audit này là chạy lại Chrome độc lập.

## NOT RUN

| Hạng mục | Lý do/giới hạn |
| --- | --- |
| Reviewer runtime `run_app_profile_heap.js --cycles 2` | API local54321 không có listener, đĩa trống667.648.000byte (~637MiB); không đủ stack/profile build/snapshots cô lập. Cần môi trường đủ để chạy mới sau quyết định chủ dự án; không tự reset/đổi DB. |
| Parse lại tám dump tác giả | Dump đã xóa; chỉ audit metadata/log/source. Không lấy log tác giả thay phép đo reviewer. |
| Actual Chrome155 tạo bank escaped trong runtime | Chưa tái hiện trên Chrome app thật; AH7 chỉ chứng minh oracle sai trên hai representation JSON hợp lệ tương đương. |
| Toàn bộ retained paths/model/cache/listeners, số dư/doanh thu/ghi chú, expense chưa nạp, Dart VM desktop/mobile | NOT RUN; bank sentinel riêng lẻ không chứng minh hết §4.4 hoặc nghiệm thu toàn V2b. |
| Windows junction, browser/device khác, offline/deep link mới, HTTP/Auth/DB runtime mới | NOT RUN trong lượt này; không đổi verdict local các gói cũ. |
| Managed backup/PITR/offsite/encryption/retention, concurrent writers, ngân hàng/webhook, staging/production, tải/rehearsal/pilot, BH-08, nghiệm thu toàn BH-07 | NOT RUN; không merge main, deploy hoặc chuyển pilot. |

**Kết luận: Chưa đạt. Dừng vòng2/2 và báo chủ dự án, không tự giao vòng3/sửa source.**
