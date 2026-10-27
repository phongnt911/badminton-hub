# Review V2b §4.4 — retained paths + finance coverage

- Ngày: 27/10/2026, Asia/Saigon. Reviewer: Codex, không sửa source triển khai/app/backend/DB.
- Base: `56e86accf2943ab2c7a79ebb0d6373b0dbcf0ef1`.
- Tested source tác giả: `66bda0e7e3e1c2e983110e26a6300f6685c3a450`.
- Docs/evidence/checkout reviewer: `9fadecc3fe27a305072e5027bf00ba41b34fe6ca`, sạch trước kiểm chứng.
- Phạm vi: script/test kiểm chứng và hồ sơ mới. Codex từng làm/review các gói Provider/browser/công cụ lịch sử; không gán các lần đó thành runtime độc lập của source mới.

## Kết luận

**Chưa đạt gói retained paths + finance coverage. Còn 1 P1 và 5 P2 RP1–RP6; không có P0.** Đây là phát hiện về công cụ/diễn giải bằng chứng, không phải xác nhận app có leak. Chưa đóng V2b §4.4 hoặc nghiệm thu toàn BH-07. Không sửa app/backend, không merge/deploy/pilot/BH-08.

Gói cũ và evidence cũ giữ nguyên byte. Auditor mới từ chối bundle cũ đúng kỳ vọng thiếu paths/class; việc từ chối là thay đổi contract của phép đo mới, không rewrite verdict lịch sử. Khi dùng quan sát bank cũ, phải giữ phân biệt **pattern xuất hiện trong UUID** với chứng minh field STK đã được Owner nạp/xóa; không suy `exact:false` thành đã đo bank account thật.

## Phát hiện

Các probe tái hiện, chạy từ repo root:

```bash
PYTHONPATH=. python docs/reviews/bh07/review_9fadecc_evidence/probes.py
node docs/reviews/bh07/review_9fadecc_evidence/fixture_probe.js
```

Python dùng graph giả và clone bundle có rehash LF-safe; Node chạy nguyên helper hiện hành trong VM với HTTP stub in-memory, **không gọi DB thật**. Không sửa source hoặc kỳ vọng để làm xanh. Exit0 của probe chỉ là thu được quan sát, không nghĩa negative cases đã bị chặn.

### RP1 — P1: Cleanup xóa cả expense đã tồn tại, không thuộc lượt chạy

- File:dòng: `scripts/bh07_appheap/run_app_profile_heap.js:167`, `:183`.
- Cách tái hiện: `fixture_probe.js`, xem `preexisting=true,post_calls=0,delete_calls=1,remaining=false,cleanup_result=true`.
- Kỳ vọng: chỉ xóa resource do chính lượt chạy tạo/sở hữu; collision phải fail trước khi đo, không lấy id có sẵn làm quyền cleanup.
- Thực tế: bất kỳ expense id cố định đuôi `...098` có status posted đều được gán `extraFixtureId`. Không kiểm session/title/ownership token; finally DELETE theo id dù không POST. Có thể là fixture của lượt khác/đang chạy hoặc dữ liệu khác trong local stack.
- Ảnh hưởng: mất dữ liệu local ngoài sở hữu, phép đo khác bị can thiệp. Probe chứng minh hành vi helper với stub, không tuyên bố đã xóa row thật.
- Cách sửa: dùng run-specific id/ownership marker và preflight collision; chỉ ghi nhận cleanup ownership cho row được lượt này tạo, có kiểm local endpoint trước mutation. Row có sẵn phải từ chối và giữ nguyên. Bao phủ create+cleanup, collision, lỗi POST/response không rõ commit và lỗi cleanup; không được báo đã dọn khi chưa xác minh row thuộc run vắng mặt.

### RP2 — P2: Cắt tập target trước khi kiểm reachable tạo kết quả graph sai

- File:dòng: `scripts/bh07_appheap/heap_oracle.py:458`, `:470`; liên quan `_chain` tại `:375`.
- Cách tái hiện: `probes.py`, `ninth_retained_node`: tám string node orphan đầu tiên mang cùng canary, node thứ chín được Object giữ mạnh. BFS ghi parent của node thứ chín là2, không có graph error, nhưng kết quả công bố `reachable=false,string_nodes=8`.
- Kỳ vọng: reachable đúng nếu **bất kỳ** target nào có đường mạnh từ root. Giới hạn chỉ được cắt output, không cắt kết luận; không phân tích đủ phải unknown/error, không false.
- Thực tế: `MAX_PATH_NODES_PER_SENTINEL=8` loại target thứ chín trước `_chain()`. `_chain` cũng trả None nếu chain vượt4096, đồng nhất budget limit với unreachable.
- Ảnh hưởng: claim retained-path thiếu/sai, có thể bỏ retainer thật. **Không khẳng định mutant này làm finance gate hiện tại PASS**: count vẫn true và điều kiện absent hiện hành vẫn có thể chặn; lỗi đã chứng minh là kết luận reachable=false không đúng đồ thị.
- Cách sửa: xác định reachability trên toàn bộ target từ BFS; chỉ cap số path/frame xuất bản. Với budget/overflow phải trả trạng thái không đủ phân tích và strict FAIL. Test >8 target, target reachable nằm cuối, nhiều retainer và chain dài; giữ weak-edge/orphan positive controls.

### RP3 — P2: Truncate nhãn trước redaction làm lộ tiền tố sentinel dài

- File:dòng: `scripts/bh07_appheap/heap_oracle.py:406`.
- Cách tái hiện: `long_label` trong Python probe: sentinel giả dài80 ký tự là property label; frame chứa nguyên40 ký tự đầu, không có `<redacted>`. Node probe `truncated_private_label_sanitizer_findings=[]`: sanitizer so full value không phát hiện tiền tố này.
- Kỳ vọng: path không công bố giá trị riêng tư hoặc một phần có ý nghĩa của giá trị; nhãn chứa sentinel phải được redacted trước mọi thao tác cắt.
- Thực tế: `strings[raw][:40]` làm mất phần cuối needle, nên phép kiểm `needle in label` không còn khớp. Short-label control vẫn redacted đúng nhưng chưa bao phủ case này.
- Ảnh hưởng: giá trị dài có thể lộ tiền tố trong frames mặc dù full-value scan PASS. Chưa thấy rò rỉ như vậy trong bundle runtime hiện tại; canary probe không phải secret thật.
- Cách sửa: kiểm/redact trên full label đã decode rồi mới giới hạn độ dài; kiểm mọi frame trước publication. Thêm control label dài, sentinel nằm sau vị trí40, embedded needle, nhiều needle và sanitizer end-to-end, giữ short-label positive.

### RP4 — P2: Metadata class và class từng scan không được ràng buộc nhau

- File:dòng: `scripts/bh07_appheap/verify_evidence.py:545`.
- Cách tái hiện: `metadata_scope_drift`: đổi `summary.sentinels.expense_id.scope` thành identity và sửa hàng class tương ứng trong report; giữ scan class finance, rehash. Auditor trả `problems=[]`.
- Kỳ vọng: declaration được xuất bản và mọi scan phải đồng nhất `scope/rendered/distinctive`; scope finance không được hạ ở một lớp mà auditor vẫn chứng nhận nội bộ nhất quán.
- Thực tế: comment nói phải agree nhưng code chỉ kiểm type/enum metadata. Gate tính theo owner scan, báo cáo khai scope khác vẫn qua. Đây khác mutant đổi scope ở tất cả scans: mutant đó đã FAIL đúng vì chỉ còn một finance gate.
- Ảnh hưởng: người đọc không biết dữ liệu được gate theo declaration nào; scope drift không được phát hiện.
- Cách sửa: đối chiếu metadata với từng scan, cả ba class fields và availability/name coverage; kiểm bảng declaration trong report. Thêm metadata-only, one-epoch, all-epoch drift và positive nhất quán; không chỉ dựa vào min-count gate.

### RP5 — P2: Ngoại lệ class bị diễn giải thành nguyên nhân/quyền truy cập chưa được chứng minh

- File:dòng: `scripts/bh07_appheap/heap_oracle.py:700`, `scripts/bh07_appheap/run_app_profile_heap.js:652`; diễn giải tại `retained_path_handoff.md` mục2–4 và readiness§4.4.
- Cách tái hiện: `rendered_app_cache`: đặt path title được khai rendered dưới `financeProviderCache`; verdict vẫn PASS và chỉ residual risk. `identity_after_logout`: đặt roster id còn reachable sau logout; verdict PASS và note khẳng định actor hiện tại được phép fetch.
- Kỳ vọng: có thể giới hạn gate vào hai finance id, nhưng không được suy **mọi rendered retainer là engine chứ không phải app**, hoặc **mọi epoch/actor được phép fetch identity**, chỉ từ class flag.
- Thực tế: gate/renderer gán lời giải thích LRU/engine cho rendered mà không đọc nguồn giữ cụ thể; chỉ xuất một shortest path nên cũng không loại trừ đồng thời có app retainer. Note identity nói authorized ngay cả `post_logout` (Guest) hoặc khi actor là Member.
- Đối chiếu code: `SessionDetailScreen.initState` gọi `fetchSessionDetail`; `SessionProvider` chỉ fetch roster management khi `session.canManage` (`lib/providers/session_provider.dart:447`). `_PlayersList` chỉ render `provider.currentPlayers` (`session_detail_screen.dart:644,889`), không tự chứng minh quyền cho Guest/Member. Nhánh Owner ở `session_finance_screen.dart:62` fetchSessionFinance, nhánh còn lại fetchPaymentInstructions: điều này hỗ trợ receiver **chưa nạp**, không hỗ trợ claim bank thật đã sạch. SDK reviewer3.47.7 có segmentationCache tại engine/text_fragmenter.dart:47, nhưng sự tồn tại cache không chứng minh mọi path minified của runtime3.47.6 chỉ thuộc engine.
- Ảnh hưởng: báo cáo có thể giải thích mất coverage/leak là benign mà không có bằng chứng. Không kết luận app leak từ mutant giả này.
- Cách sửa: giữ narrow PASS cho các finance id thực được đo nếu cần, nhưng các retainer ngoài gate phải được ghi đúng **unattributed/residual/NOT RUN** cho đến khi có mapping/path/actor evidence. Phân biệt Cohost fetch lại hợp lệ với post_logout/Member retention; không dùng class flag để tuyên bố toàn bộ app đã bỏ state. Nếu muốn phân loại engine-only, cần control app-cache/engine-cache/dual-retainer và attribution kiểm được. Đính chính cách đọc bank cũ thành pattern/UUID collision, không nói chứng minh bank account sạch “do may mắn”. Không sửa verdict/raw evidence lịch sử.

### RP6 — P2: Auditor không bắt buộc fixture cleanup đã xác minh

- File:dòng: `scripts/bh07_appheap/verify_evidence.py:489`.
- Cách tái hiện: `cleanup_false`, `cleanup_missing`: clone bundle, đặt `cleanup.extra_expense_removed=false` hoặc bỏ khóa, giữ aggregate ok=true, rehash. Với false còn sửa dòng cleanup report tương ứng. Cả hai trả `problems=[]`, hash trước/sau không đổi.
- Kỳ vọng: contract mới có mutation fixture nên thiếu/false xác minh xóa fixture phải FAIL, không tin aggregate ok đơn lẻ.
- Thực tế: `_check_cleanup` vẫn chỉ kiểm các trường dump/profile cũ, bỏ qua extra_expense_removed mà runner mới dùng để quyết định cleanup.ok.
- Ảnh hưởng: bundle có thể được chứng nhận PASS dù fixture chưa được xóa hoặc chưa có bằng chứng vắng mặt.
- Cách sửa: bắt buộc boolean true cho fixture cleanup/ownership verification của phép đo mới; so với report, có log/receipt đã sanitize cho cleanup khi chạy runtime. Test missing/false/null và cleanup error, giữ readonly. Reviewer hiện không có DB local để tự xác nhận row thực đã vắng.

## Bằng chứng reviewer tự chạy

| Lệnh/kiểm tra | Kết quả |
| --- | --- |
| `python -X utf8 -m unittest discover -s tests` | exit0,258/258,no skips |
| `python -X utf8 scripts/bh07_appheap/heap_oracle.py self-test` | exit0,32/32; fixture self-test riêng đã xóa |
| `flutter analyze` | exit0,no issues; có pub resolution, không thay bằng --no-pub |
| `flutter test` | exit0,247 PASS+1 SKIP; HTTP/Auth disabled không phải HTTP runtime mới |
| Auditor mới trên retained_path_evidence bằng abs path | exit0 |
| Auditor mới trên app_profile_heap_evidence cũ | exit1 đúng kỳ vọng thiếu retained-path/class contract |
| Requested mutants | scope finance→identity ở scans FAIL; finance retained FAIL; bỏ paths FAIL; nhãn ngắn mang sentinel redacted |
| Reviewer probes bổ sung | exit0 thu quan sát RP1–RP6; không là một passing negative-control suite |
| Git/provenance/bytes | tested66bda0e,author git_dirty=false;reviewer checkout9fadecc sạch trước report;source tree docs commit không đổi;lib/test/supabase không diff;bundle cũ không diff;strict UTF-8 LF và hash theo Git sau mọi lệnh |

`provenance.json` và log riêng tại [review_9fadecc_evidence/](review_9fadecc_evidence/). Bundle mới3/3 manifest entry (4 file gồm manifest) khớp; không regenerate hoặc sửa bundle mới/cũ. Reviewer Linux/Flutter3.47.7; tác giả Windows/Flutter3.47.6/Chrome155. Log reviewer chuẩn hóa terminal CR/padding để xuất bản;bytes tác giả giữ nguyên. Không cộng các nhóm self-test/controls vào số runtime độc lập.

## NOT RUN

| Hạng mục | Giới hạn |
| --- | --- |
| Runner thật `node scripts/bh07_appheap/run_app_profile_heap.js` | **NOT RUN**: precondition Supabase local up không đạt,API54321 không có listener;disk chỉ658.530.304byte (~628MiB),không đủ stack/profile build/dumps cô lập. Không gọi mutation fixture vào DB khác để cố chạy. |
| DB row fixture đuôi098 vắng mặt sau lượt tác giả | **NOT RUN độc lập**: không có local API/DB để query;summary true là báo cáo tác giả,không thay phép kiểm reviewer. RP1 chỉ dùng stub,RP6 chỉ clone bundle. |
| Đồ thị/path của tám dump thật | Dump đã xóa,không parse lại được;chỉ audit source/metadata và graph fixtures;không gán log tác giả thành runtime reviewer. |
| Coverage ngoài hai expense id | Charge/payment,bank field thật/receiver chưa nạp,số dư/doanh thu/ghi chú,toàn model/cache/listener và mọi alternative retained paths chưa được chứng minh. Không coi min2 id cùng collection là coverage mọi loại tài chính. |
| Dart VM desktop/mobile,browser khác,tải thật/concurrent actors | NOT RUN theo yêu cầu;giới hạn V8/web profile giữ nguyên. |
| Managed backup/PITR,banking/webhook,staging/production,backup/restore thật,pilot,BH-08,nghiệm thu toàn BH-07 | NOT RUN;không merge/deploy/pilot. |

Giao sửa theo AGENTS **vòng1/2** cho gói retained-path mới: test tái hiện trước,sửa đầy đủ RP1–RP6,giữ các control đã qua và evidence cũ. Không sửa app/backend. **Kết luận: Chưa đạt.**
