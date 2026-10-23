# Bàn giao kiểm chứng response Owner trả trễ sau đổi actor — BH-07 local

Ngày23/10/2026. **Codex triển khai/tự kiểm script; không phải review độc lập. Trạng thái: Chờ review gói kiểm chứng response trễ.**

- Branch `feat/bh07-browser-verification`.
- Base `1ed4f3e6b42b853f51add79279fe3daf8168e360`.
- Source: `c4ce99bcd9a9b02c4b794c8eb5ab51e43c06155a`.
- Docs/evidence: commit chứa bàn giao, full SHA gửi trong chat sau push.
- Bằng chứng mới: [late_response_evidence/](late_response_evidence/). Giữ nguyên các gói evidence/review cũ.

## Phạm vi

Bổ sung `run_late_response.js`, `late_response_assertions.js`, `run_late_response_controls.js`. Driver browser cũ chỉ thêm export và `require.main` guard để tái sử dụng CDP/UI; không đổi11 gate cũ. Không sửa app/lib, unit test, model/repository/provider, migration/RPC/contract. Không merge main/apply DB thật/deploy/pilot.

## Ca browser thật

1. Khởi động Chromium, xác nhận Guest thật trước login. Login Owner bằng form UI + Input.insertText; kiểm email trên Account UI.
2. Mở summary từ History→chi tiết bằng click UI. Positive control: Owner thật thấy finance card, clipboard đúng200k/200k/0/200k. Negative control trên chính dữ liệu Owner: guard Cohost phải loại cả UI và clipboard này.
3. Refresh qua nút AppBar, dùng CDP Fetch response-stage giữ **POST** `get_session_summary` đã nhận200 từ PostgREST; bỏ qua OPTIONS. Kiểm đúng session, `can_view_finance=true`,expenses200000; giữ body nguyên vẹn, ghi hash thay vì header/token.
4. Back/AppBar/tab để logout, xác nhận Guest và các key SDK dạng sb-...-auth-token không còn; đây không phải phép quét mọi loại storage; login actor mới qua UI trong cùng document. Không Page.navigate/reload/auth injection.
5. Cohost: mở summary mới và chờ count-only trước khi thả response Owner. Member: mở lịch sử cá nhân và chờ empty hợp lệ; không có summary/copy entry.
6. Continue response nguyên bản; phải có Network.loadingFinished cho đúng networkId và hash delivered body trùng hash held body. Timeline bắt buộc held<guest<login<release<=delivered.
7. Lấy4 sample UI sau delivery + kiểm surface/clipboard cuối. Cohost không có card/nhãn/số tiền/contact/bank, copy chỉ count. Member giữ empty, không có summary/copy entry hoặc private text. `performance.timeOrigin` phải giữ nguyên qua toàn bộ hai ca; chạy lại cùng SPA giữa các actor.

Không chỉ giả lập delay bằng mock hoặc dựa vào DOM reset/reload. Request được Auth/ACL/RPC thật xử lý trước khi bị giữ ở ranh giới transport của Chrome; không sửa payload/body/business response.

## Phân biệt kiểm cache và quan sát UI

Browser quan sát hành vi provider thông qua summary/copy của Cohost và lịch sử/capability của Member; không đọc trực tiếp private Dart heap. Không suy “đã đo nội bộ cache Member” từ empty UI. Full Flutter suite giữ ca provider có sẵn `summary: logout/đổi actor dọn state, phản hồi cũ không khôi phục` kiểm sessionSummary=null với repository stub, là bằng chứng bổ sung ở tầng unit, **không thay thế HTTP browser**. Kết luận về browser giới hạn ở việc late response thật không phục hồi dữ liệu đặc quyền qua các bề mặt UI/copy đã thử.

## Kết quả và provenance

| Cổng | Kết quả tự chạy | Exit |
|---|---|---|
| Late Owner→Cohost |PASS; giữ44.661ms, delivered hash trùng;4 sample an toàn; copy count-only |0 |
| Late Owner→Member |PASS; giữ40.528ms, delivered hash trùng;4 sample an toàn; empty history,không có summary/copy |0 |
| Cùng SPA |timeOrigin không đổi qua cả2 ca;guest/account email được assert trước release |0 |
| Positive/negative mới |21/21 đúng kỳ vọng:2 positive,19 negative; actualOwner UI/clipboard cũng bị guard Cohost loại đúng |0 |
| Browser baseline cũ |11/11 PASS;12 ảnh khác hash;checkout sạch |0 |
| Negative cũ |41/41,0 HARNESS_ERROR |0 |
| Analyze / Flutter |0 issues;240 PASS+1 SKIP |0 |
| Web build |PASS |0 |
| Manifest |44/44;UTF-8 không BOM/CR;scanner không thấy secret/JWT ngoài allowlist;final verify45 file gồm manifest readonly |0 |

`late_summary.json` và `late_run/summary.json` lưu timeline/body hash/actor/origin và4 sample từng ca; không lưu header/token. Mã source/dirty/SHA/run được ghi trong environment/summary/exits. Không phát hiện lỗi app qua các bề mặt đã kiểm; chưa tự kết luận Đạt ở vai triển khai.

Phân biệt mốc chạy: analyze/full Flutter/build/baseline/41 control chạy ở `0a2b95f21b2289c9252e026dbcf14ece10fa3d15`; lần late cuối và21 control chạy ở `c4ce99bcd9a9b02c4b794c8eb5ab51e43c06155a`. Commit sau chỉ sửa1 selector trong script late, app/lib/test/supabase và driver baseline giống hệt; tree hashes đối chiếu trong environment. Không gắn lại SHA cũ thành SHA mới. Cả baseline và late đều bắt đầu với checkout sạch.

Lượt late đầu ở0a2b95f exit1 vì selector refresh chỉ tìm aria, chưa giữ response nên không phải lỗi app. Log/summary lượt lỗi được giữ nguyên. Sửa selector đọc cả text/aria, commitc4ce99b trước lần phát lại; hai ca cuối PASS.

Các script/fixture/evidence cũ giữ nguyên, ngoại trừ export/entry guard tối thiểu ở driver. Bằng chứng cũ52/52 vẫn verify; không ghi đè logs/manifest lịch sử. Stack/browser/server/runtime key local đã dọn sau kiểm chứng.

## Tái lập

- Dùng Flutter3.47.7 + Chromium154/Linux; stack riêng PostgreSQL17.11/GoTrue2.197.0/PostgREST16.4/Kong2.8.1.
- Dựng stack/seed cùng fixture qua recipe `run_local_stack.py` trong evidence. Chỉ local API127.0.0.1:54321.
- `flutter analyze`, `flutter test`; Web build dùng runtime public anon riêng và `--no-web-resources-cdn`, không publish runtime key.
- Serve `build/web` trên127.0.0.1:8088.
- Chạy nguyên browser baseline11 ca trước để tạo completed fixture200k. Bản driver Linux ngoài repo chỉ đổi paths/browser flags/DB container và bỏ lặp seed Windows vì SQL đã seed giống hệt; patch hạ tầng được công bố. Baseline raw summary giữ base_sha của gate cũ1fc7e2e; task base mới1ed4f3e được ghi riêng, không đính chính giả lịch sử baseline.
- `BH07_BROWSER_DRIVER=<driver-linux-copy> BH07_LATE_EVIDENCE=<scratch-output> node scripts/bh07_browser/run_late_response.js`. Windows có thể dùng driver mặc định nếu Chrome/Supabase theo đường dẫn cũ. Luôn chạy sạch và ghi output scratch để không overwrite gói bàn giao.
- `node scripts/bh07_browser/run_late_response_controls.js`;21 control, gồm2 positive và19 negative.
- Chạy41 negative control cũ trên copy ngoài repo. Reviewer chỉ `clean_and_manifest.py --verify --evidence-dir docs/reviews/bh07/late_response_evidence`; không --generate trên gói bàn giao.

## NOT RUN

- Review độc lập và kiểm private Dart heap bằng browser; chỉ quan sát UI/copy, có unit cache guard bổ sung.
- Mobile/thiết bị thật/browser khác; Windows Chrome155 không chạy lại.
- Ngân hàng/VietQR/webhook; staging/production/backup/restore; rehearsal/pilot; nghiệm thu toàn BH-07.
- Full Supabase db reset và chạy lại23 DB/335 DB hồi quy trong lượt này: không đổi DB/backend.23 DB gần nhất ở source a6d58af giữ lịch sử, không gắn thành kết quả mới của source hiện hành.
- Không biến hai ca actor cụ thể thành bảo đảm cho mọi RPC, mọi cache và mọi lịch trình race.
