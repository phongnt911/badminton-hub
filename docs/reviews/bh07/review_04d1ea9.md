# Review retained-path V2b — chốt sửa RP3-B vòng 2/2

- Ngày: 27/10/2026, Asia/Saigon. Reviewer: Codex, không sửa source triển khai/app/backend/DB.
- Base review: `bc09d0c9406f4934b40a00f940667c008bb7a3a8`.
- Source kiểm chứng bản sửa: `6b530c52e8020f778a1caa86890ea3ba87fb084f`.
- Docs/checkout reviewer: `04d1ea988574d120f52ba773b88dea3326bc89b6`, sạch trước kiểm chứng.
- Runtime evidence được kế thừa: `retained_path_r1_evidence/`, **source `86181de1df03e11b3ad537f1024405724db83bfb`**, không có runtime mới được công bố cho6b530c5. Không retag/rewrite bundle.

## Kết luận

**Chưa đạt gói retained-path vòng 2/2. Đóng lỗi fragment RP3-B; còn 1 P2 mới RP3-C về cú pháp artifact JSON. Không có P0/P1 mở trong phạm vi review.** RP1,RP2,RP4,RP5,RP6 và oracle-label redaction giữ kết luận đóng từ [review_4184faf](review_4184faf.md), có hồi quy lần này.

**Dừng sau vòng2/2,báo chủ dự án quyết định;không tự mở vòng3 hoặc sửa source.** Theo [AGENTS.md](../../../AGENTS.md): “Sửa theo review: viết test tái hiện lỗi trước, sửa toàn bộ phát hiện P0/P1/P2 được nêu (kể cả P2), tối đa 2 vòng. Còn lỗi sau 2 vòng thì dừng và báo chủ dự án.” Giữ nhánh chưa merge. **Không chốt Đạt runtime độc lập cho source6b530c5,không đóng toàn bộ cổng V2b §4.4 hoặc toàn BH-07.** Runtime reviewer,DB query và coverage ngoài hai expense id còn NOT RUN ở bảng cuối. Các quan sát runtime R1 chỉ gắn source86181de;source oracle/auditor không đổi trong lượt sửa publisher này,nhưng không gọi đó là runtime mới. Không merge main/staging/production,deploy/pilot/BH-08. Provider/tooling,V1,V5b giữ kết luận local trước đó;Codex từng tham gia/review gói lịch sử,không dùng chúng thay runtime hiện tại.

## Phát hiện

| Mức | file:dòng | Trạng thái |
| --- | --- | --- |
| P0 | — | Không có phát hiện mở trong phạm vi |
| P1 | — | Không có phát hiện mở trong phạm vi |
| P2 | run_app_profile_heap.js:830 | RP3-C còn mở,chi tiết bên dưới |

RP3-B tại `scripts/bh07_appheap/run_app_profile_heap.js:647`–`:691` và publication `:813`: **Đóng**. Redaction tìm khoảng matching trên text gốc,merge overlap giữa các value trước thay thế;không thay prefix20 rồi bỏ mất prefix40/60. Structured string fields được làm sạch trước serialize. Hai probe reviewer nguyên bản nay xác nhận:

- Full value,prefix20,prefix40,prefix60 đều `<redacted>` trọn;không còn private_middle20/private_middle40.
- Actual writer trên draft giả có leak vẫn ghi status/verdict FAIL,nhưng artifact không còn fragment (`published_private_middle20=false,actual_private_fragment_absent=true`).
- 310 suite tests bao gồm các độ dài trung gian,embedded/interior,multiple/overlapping,self-overlapping và kiểm artifact JSON/Markdown. Không sửa probe/kỳ vọng hoặc chỉ đổi vị trí hai prefix cố định.

### RP3-C — P2: Redact trên JSON đã serialize phá boolean của protocol

- File:dòng: `scripts/bh07_appheap/run_app_profile_heap.js:830`;liên quan `:795` và `:814`.
- Tái hiện:

  ```bash
  node docs/reviews/bh07/review_04d1ea9_evidence/json_structure_probe.js
  ```

- Input: actual writer trong VM,temp output riêng,summary có các boolean chuẩn (`cleanup.ok`, `build.served_match`, `git_dirty`) và một string canary. Positive dùng canary dài thông thường;hai negative dùng **string** `"true"` hoặc `"false"`,là kiểu đầu vào sanitizer hỗ trợ (full value nếu ngắn hơn20). Không có HTTP/DB/app mutation.
- Kỳ vọng: failed artifact vẫn là JSON hợp lệ;redact dữ liệu chuỗi riêng tư không thay đổi cú pháp của boolean/number/null hoặc protocol metadata.
- Thực tế: positive parse được;hai case short-string đều `summary_json_valid=false`, `SyntaxError`,có placeholder không được quote ở vị trí boolean. Ví dụ `"ok": true` biến thành `"ok": <redacted>`. Test dùng ordinary true/false làm canary giả,không phải secret thật và không chứng minh bundle R1 hiện tại bị hỏng.
- Nguyên nhân: `redactValue` làm sạch string fields đúng kiểu,nhưng sau `JSON.stringify` writer lại gọi `redactSentinels` trên **toàn bộ serialized text**. Điều này cũng thay token JSON không phải string;detector và raw-text replacement không phân biệt private string với public protocol boolean cùng cách viết.
- Ảnh hưởng: artifact lỗi không đọc/audit được,trái yêu cầu giữ cú pháp JSON;đây không phải false PASS hoặc bằng chứng leak app. Dataset hiện tại và310 tests không có case này.
- Cách sửa: sanitize dữ liệu có cấu trúc/string fields trước serialize,rồi chỉ serialize một lần;không áp dụng replacement không biết grammar lên JSON/cleanup receipt đã serialize. Tách log free-text và report data khỏi protocol/static metadata;giữ cú pháp và kiểu public boolean. Nếu sentinel mơ hồ không hỗ trợ,phải từ chối sớm bằng artifact lỗi **vẫn hợp lệ**,không ghi JSON hỏng. Test actual writer với private-string trùng `true`/`false`/`null`/chuỗi số và quoted string,parse summary/cleanup receipt;giữ prefix/overlap controls cũ. Không cần sửa app/backend.

## Reviewer tự chạy

Evidence riêng: [review_04d1ea9_evidence/](review_04d1ea9_evidence/). Tất cả probe cũ chạy nguyên bản;exit0 của probe quan sát được đọc cùng output,không dùng một mình làm chứng minh negative input bị chặn.

| Lệnh/kiểm tra | Kết quả |
| --- | --- |
| `redaction_probe.js` nguyên bản review4184faf | exit0;full/prefix20/40/60 trọn,không fragment |
| `publication_probe.js` nguyên bản review4184faf | exit0;actual artifact FAIL nhưng sạch canary,output temp được xóa |
| `probes.py`, `fixture_probe.js` nguyên bản review9fadecc | exit0;target9 reachable,oracle label redacted,risk unattributed,class/cleanup sai bị chặn;collision không POST/DELETE,row còn |
| `python -X utf8 -m unittest discover -s tests` | exit0,310/310,no skip |
| `node scripts/bh07_appheap/fixture_controls.js --self-test` | exit0,6/6 |
| `python -X utf8 scripts/bh07_appheap/heap_oracle.py self-test` | exit0,34/34;temp fixture riêng đã xóa |
| Auditor abs path retained_path_r1_evidence | exit0 trên dữ liệu runtime86181de kế thừa |
| Auditor abs path retained_path_evidence và app_profile_heap_evidence | mỗi bundle exit1 đúng kỳ vọng contract cũ không đủ |
| `flutter analyze` | exit0,no issues;có pub resolution |
| `flutter test` | exit0,247 PASS+1 SKIP;HTTP/Auth disabled không phải runtime HTTP mới |
| JSON structure probe mới | exit0 thu quan sát;positive hợp lệ,hai negative true/false làm JSON hỏng;không coi exit0 là negative-control PASS |
| Source/whitespace | chỉ publisher và test kiểm chứng đổi ngoài docs;oracle/auditor,lib/test/supabase không đổi;diff-check sạch |
| Byte integrity/readonly | cả3 bundle runtime hiện có không đổi từ base review;R1/new và hai bundle cũ khớp Git sau các lệnh;không generate/chạy runner vào bundle tác giả |

Provenance tại `provenance.json`: checkout/docs04d1ea9,code6b530c5,git status sạch trước report;runtime trong JSON vẫn86181de/dirtyfalse. Không đánh tráo hai SHA. R1 bundle3/3 entry (4 file kể manifest),UTF-8 LF;source/docs mới không thay bytes. Reviewer Linux/Flutter3.47.7,tác giả Windows/Flutter3.47.6/Chrome155. Logs reviewer chuẩn hóa terminal CR/padding khi xuất bản;bytes tác giả giữ nguyên. Không cộng các nhóm self-test/probe vào số runtime mới.

## NOT RUN / giới hạn

| Hạng mục | Trạng thái |
| --- | --- |
| Runtime Chrome source6b530c5 của reviewer | **NOT RUN**: local API54321 không chạy,disk653.414.400byte (~623MiB) theo runtime_preflight.json;không đủ stack/profile build/dumps cô lập. Cần QA độc lập/evidence riêng cho source mới nếu chốt runtime. |
| Runtime source6b530c5 của tác giả | Không có bundle runtime mới;handoff công bố rõ kế thừa lần86181de,không gán thành lần chạy6b530c5. |
| Live DB row fixture đã vắng | NOT RUN độc lập;chỉ code/stub/audit receipt,không query DB khác. |
| Raw dump/path của lần R1 | Dump đã xóa;chỉ audit source/metadata và graph fixtures,không replay dump thật. |
| Charge/payment,bank/receiver thật chưa nạp,số dư/doanh thu/ghi chú,toàn model/cache/listener và mọi alternative retained paths | NOT RUN;chỉ hai expense id gate,rendered/identity ngoài gate vẫn residual/unattributed. Không suy hẹp thành toàn§4.4 sạch. |
| Dart VM desktop/mobile,browser khác,tải/concurrent actors,staging/production | NOT RUN theo phạm vi;giới hạn V8/web profile giữ nguyên. |
| Managed backup/PITR,banking/webhook,restore thật,pilot,BH-08,nghiệm thu toàn BH-07 | NOT RUN;không merge/deploy/pilot. |

**Kết luận: Chưa đạt vòng2/2,còn RP3-C P2. Dừng,báo chủ dự án;không tự mở vòng3/sửa source.**
