# Review retained paths V2b — sửa RP1–RP6 vòng 1/2

- Ngày: 27/10/2026, Asia/Saigon. Reviewer: Codex, không sửa source/app/backend/DB.
- Base review: `47b1e92dae7657ddb52e0d4e78d2063447129a47`.
- Tested source: `86181de1df03e11b3ad537f1024405724db83bfb`.
- Docs/evidence: `4184fafac7c19ff764e9f41a94a219f4a54c35ed`.
- Checkout/status AGENTS: `12e0aa0313c876aea0c0bf0f71544778b8c713a9`, sạch trước kiểm chứng; commit này chỉ cập nhật AGENTS sau docs/evidence.

## Kết luận

**Chưa đạt vòng 1/2; còn 1 P2 RP3-B. Không có P0/P1 mở trong phạm vi review.** Đóng RP1,RP2,RP4,RP5,RP6 trong phạm vi source/control đã kiểm; phần redaction label của oracle ở RP3 đã sửa, nhưng sanitizer lúc ghi artifact còn lỗi bên dưới.

Không phát hiện secret trong bundle PASS được bàn giao theo các kiểm tra hiện hành. RP3-B được tái hiện bằng canary giả và artifact lỗi trong thư mục tạm, **không phải bằng chứng leak app hoặc leak dữ liệu thật trong bundle tác giả**. Runtime reviewer và query DB xác nhận fixture vắng vẫn NOT RUN. V2b đầy đủ/BH-07 chưa nghiệm thu; không merge/deploy/pilot/BH-08. Codex từng làm/review gói Provider/browser lịch sử; không dùng các lần đó thay runtime source mới.

## Phát hiện còn mở

### RP3-B — P2: Redact prefix ngắn trước prefix dài để sót dữ liệu riêng tư

- File:dòng: `scripts/bh07_appheap/run_app_profile_heap.js:642`, `:667`; đường ghi file tại `:781`–`:782`.
- Tái hiện từ repo root:

  ```bash
  node docs/reviews/bh07/review_4184faf_evidence/redaction_probe.js
  node docs/reviews/bh07/review_4184faf_evidence/publication_probe.js
  ```

- Input: canary giả dài hơn60 ký tự, draft chỉ chứa40 ký tự đầu của nó. Không gọi app/HTTP/DB; publication probe thực thi **writeEvidence hiện hành** trong VM,output temp riêng và xóa sau kiểm tra.
- Kỳ vọng: thay toàn bộ private prefix đang có trong input,không xuất bản fragment còn lại; full value,prefix20,prefix40 và các độ dài trung gian/lớn hơn phải có kết quả đã sanitize đầy đủ.
- Thực tế: thứ tự needle là `[fullValue,prefix20,prefix40]`. Full value không có; thay prefix20 trước biến input thành `<redacted>` + **20 ký tự riêng tư thứ21–40**. Prefix40 sau đó không còn khớp. Output dài30,`private_middle20_survives=true`,`findSentinelLeaks(output)=[]`. Prefix60 cũng còn nguyên40 ký tự riêng tư sau bước thay prefix20. Positive full value và prefix20 vẫn được xóa trọn.
- Kiểm đường publication: `writeEvidence` nhận diện leak trước khi ghi và hạ `status/verdict=FAIL`, nhưng **run.log được ghi vẫn chứa20 ký tự canary còn sót** (`published_private_middle20=true`). Tempdir đã được xóa. Không khẳng định đây là false PASS của runtime; lỗi là failed bundle vẫn phát tán dữ liệu riêng tư sau bước được gọi là redaction.
- Cách sửa: redact theo **khớp prefix dài nhất thực sự có trong input** hoặc mask trọn trường chứa match,trước khi biến đổi phần ngắn; xử lý chồng lấn giữa các value. Không chỉ đảo20/40: prefix60 vẫn có thể sót nếu chỉ thay40. Bảo toàn cú pháp JSON/Markdown khi ghi. Thêm test đỏ cho40/60/độ dài trung gian,embedded/multiple/overlapping values và **artifact thực của writeEvidence**,đòi không còn fragment riêng tư chứ không chỉ “không còn full needle/prefix đầu”. Giữ positive full/prefix20 và oracle-label controls.

## Đối chiếu RP1–RP6

| Phát hiện | Kết luận và chứng cứ |
| --- | --- |
| RP1 — ownership fixture | Đóng trong phạm vi control. Probe cũ nguyên bản: POST0/DELETE0,row có sẵn còn nguyên;fixture_controls6/6 bao phủ collision,create-clean,POST không trả lời nhưng đã commit,POST không commit,DELETE lỗi,remote endpoint. Dynamic UUID/title độc lập,gated id không bị nhúng trong rendered title. Không có live DB reviewer. |
| RP2 — target cap/budget | Đóng. Probe cũ trả reachable=true/string_nodes9. Unit69 path controls bao gồm walk vượt budget/error và không biến thiếu phân tích thành unreachable;source tính reachable toàn bộ matches,chỉ giới hạn đường xuất bản. |
| RP3 — label/privacy | Oracle full-label trước truncate và prefix-label control đóng;sanitizer nhận diện prefix≥20 nhưng **redaction publication còn RP3-B**. |
| RP4 — class agreement | Đóng: metadata/scan từng epoch và declaration table report được so;302 suite bao gồm isolated controls với receipt mới,không chỉ dựa vào bundle cũ vốn bị reject do cleanup contract. |
| RP5 — causal/actor claims | Đóng trong phạm vi diễn giải đã báo. Probe cũ: risk attribution=unattributed;identity sau logout nói quyền “not established”,không note authorized. Giữ narrow finance-id gate,không dùng class flag kết luận app/engine/actor entitlement. |
| RP6 — cleanup contract | Đóng trong phạm vi audit/control. Created/removed/verified_absent true,sha12 đúng dạng,không error;report receipt phải bằng JSON. New bundle receipt hash trùng expense_id_2 metadata. Live DB row absence chưa được reviewer xác nhận. |

## Reviewer tự chạy

Evidence riêng: [review_4184faf_evidence/](review_4184faf_evidence/). Các probe reviewer cũ chạy nguyên bản,không sửa kỳ vọng. New probes là quan sát; exit0 của probe không có nghĩa negative case đã được chặn.

| Lệnh/kiểm tra | Kết quả |
| --- | --- |
| `python -X utf8 docs/reviews/bh07/review_9fadecc_evidence/probes.py` | exit0,quan sát cập nhật đúng RP2/label/class/risk;giữ file cũ |
| `node docs/reviews/bh07/review_9fadecc_evidence/fixture_probe.js` | exit0,collision không POST/DELETE,row còn;sanitizer phát hiện prefix theo kỳ vọng |
| `node scripts/bh07_appheap/fixture_controls.js --self-test` | exit0,6/6 |
| `python -X utf8 -m unittest discover -s tests` | exit0,302/302,no skip |
| `python -X utf8 scripts/bh07_appheap/heap_oracle.py self-test` | exit0,34/34;fixture temp riêng đã xóa |
| Auditor abs path retained_path_r1_evidence | exit0 |
| Auditor abs path retained_path_evidence và app_profile_heap_evidence | mỗi bundle exit1 đúng kỳ vọng contract mới;không sửa bytes/verdict lịch sử |
| `flutter analyze` | exit0,no issues;có pub resolution,không thay bằng --no-pub |
| `flutter test` | exit0,247 PASS+1 SKIP;HTTP/Auth disabled không phải HTTP runtime mới |
| Redaction/publication probes mới | exit0 thu quan sát RP3-B;positive full/prefix20 qua,prefix40/60 còn fragment;actual writer FAIL nhưng artifact vẫn có fragment |
| Source/Git/whitespace | runtime source tree docs4184faf/status12e0aa0 bằng86181de;lib/test/supabase không đổi từ base;diff-check sạch;old bundles byte-identical |

`provenance.json` ghi source/docs/status/dirty/exit/count,hash mọi file mới/cũ;new bundle3/3 entries (4 file gồm manifest),strict UTF-8 LF,hash khớp Git sau mọi lệnh. Không generate/chạy runtime vào bundle tác giả. Reviewer Linux/Flutter3.47.7;runtime tác giả Windows/Flutter3.47.6/Chrome155. Logs reviewer chuẩn hóa terminal CR/padding khi xuất bản;bytes tác giả giữ nguyên. Các nhóm controls ghi theo từng lệnh,không cộng thành số runtime độc lập.

## NOT RUN

| Hạng mục | Giới hạn |
| --- | --- |
| Runner thật source86181de | NOT RUN: local API54321 không có listener;disk trống ghi tại runtime_preflight.json chưa đủ stack/profile build/dumps cô lập. Không ghi fixture vào DB khác để cố chạy. |
| DB local không còn fixture sau lượt tác giả | NOT RUN độc lập;chỉ audit receipt/log/source và HTTP stub. Claim query0 trong handoff là kết quả tác giả,không thay query reviewer. |
| Parse lại tám dump thật/path từng object | Dump đã xóa;không replay raw dumps. Chỉ audit source,metadata và graph fixtures. |
| Coverage ngoài hai expense id | Charge/payment,bank field thật/receiver chưa nạp,số dư/doanh thu/ghi chú,toàn model/cache/listener và mọi alternative path chưa được chứng minh. Bank-pattern cũ không chứng minh field STK thật. |
| Dart VM desktop/mobile,browser khác,tải thật/concurrent actors,staging/production | NOT RUN theo yêu cầu;giới hạn V8/web profile giữ nguyên. |
| Managed backup/PITR,banking/webhook,restore thật,pilot,BH-08,nghiệm thu toàn BH-07 | NOT RUN;không merge/deploy/pilot. |

Giao sửa **vòng2/2** chỉ RP3-B và kiểm hồi quy toàn bộ gate đã đóng. Không sửa app/backend/DB. Nếu còn lỗi sau vòng2/2,dừng và báo chủ dự án theo AGENTS. **Kết luận: Chưa đạt.**
