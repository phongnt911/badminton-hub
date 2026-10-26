# Review V2b app-profile heap — 8914b2f

- Reviewer: Codex; review độc lập gói app-profile mới, không sửa source. Codex từng làm gói Provider/browser lịch sử; không dùng lịch sử đó thay phép đo app-profile.
- Ngày: 26/10/2026 (Asia/Saigon).
- Base: `3b30e4941058c0cfebec06b377abfc53f19576a4`.
- Tested source: `bb2d2130276ad31824acc650a02ecee4b6ba95a6`.
- Docs/evidence và checkout reviewer: `8914b2ffb7f24d37c007e46a5973fbd4a8923a51`, sạch trước kiểm tra.
- Phạm vi: script/oracle/auditor app-profile, hai suite Python, bundle và trạng thái. Source app/backend không đổi. Không đổi DB, merge hoặc deploy.

## Kết luận

**Chưa đạt gói V2b app-profile heap.** Còn **1 P1 và 4 P2** bên dưới; không có P0. Đây là lỗi công cụ kiểm chứng có thể nhận bằng chứng thiếu/hỏng thành sạch, **không phải kết luận đã phát hiện leak trong app**. V2b chưa được đóng. Gói Provider/tooling, V1 và V5b giữ kết luận Đạt local trước đó; toàn BH-07 chưa nghiệm thu.

## Phát hiện

### AH1 — P1: Snapshot không hợp lệ vẫn được coi là sạch

- File:dòng: `scripts/bh07_appheap/heap_oracle.py:58`.
- Tái hiện: `python docs/reviews/bh07/review_8914b2f_evidence/probes.py`, xem `invalid_snapshot` và `full_cycle_with_invalid_snapshot`.
- Kỳ vọng: snapshot JSON hỏng hoặc thiếu cấu trúc V8 thực phải FAIL; không diễn giải sentinel vắng mặt thành đã thu hồi.
- Thực tế: fixture 5.062 byte có `"snapshot":BROKEN`, ba marker và dấu `}` cuối. `json.loads` từ chối nhưng `scan.ok=true`, `bank=false`, `probe=true`; `decide` trả PASS. Đưa scan này vào bộ đủ bốn mốc với positive Owner cũng PASS. Kiểm đầu/đuôi/substring không chứng minh dump hoàn chỉnh; mất chunk giữa stream có thể vượt gate này.
- Ảnh hưởng: dữ liệu đo không sử dụng được có thể chứng nhận cache sạch.
- Cách sửa: parse/validate snapshot hoàn chỉnh, metadata và tính nhất quán node/edge/string tables/counts trước khi scan có hiệu lực; fail-closed khi lỗi. Thêm control mất đoạn giữa nhưng còn đầu/đuôi/marker, JSON hợp lệ nhưng schema/count sai; giữ positive từ snapshot V8 thực đã sanitize hoặc tạo fixture cấu trúc hợp lệ.

### AH2 — P2: Auditor không kiểm lại số chu kỳ, đủ mốc và verdict oracle

- File:dòng: `scripts/bh07_appheap/verify_evidence.py:103`.
- Tái hiện: cùng probe, xem `zero_cycles`, `missing_epoch`, `leaked_failed_scan`.
- Kỳ vọng: RUN/PASS chỉ hợp lệ khi đủ hai actor paths, bốn mốc mỗi chu kỳ, scan dùng được, probe sống, positive Owner và negative hậu đổi actor; verdict phải khớp dữ liệu.
- Thực tế: clone bundle rồi cập nhật hash hợp lệ: xóa toàn bộ `cycles`, xóa `post_actor`, hoặc đặt `post_actor.ok=false` cùng `bank.present=true` đều trả danh sách lỗi `[]`. Auditor chỉ lặp qua những mốc còn lại và kiểm hai khóa metadata; không tái tính verdict.
- Ảnh hưởng: ngay cả khi runner fail-closed, bundle thiếu mốc/leak được gắn PASS vẫn qua công cụ audit.
- Cách sửa: schema chặt về cycle/actor/epoch, đối chiếu same-document evidence và mode, tái sử dụng oracle với expectation cố định; kiểm verdict tổng/cycle và Markdown nhất quán. Test mutant phải rehash sau sửa để đo gate semantic thay vì chỉ gate hash.

### AH3 — P2: Manifest không bao phủ file thừa; secret scan bỏ qua chúng

- File:dòng: `scripts/bh07_appheap/verify_evidence.py:56`, `scripts/bh07_appheap/verify_evidence.py:110`.
- Tái hiện: cùng probe, `unmanifested_secret_extra`: thêm `extra.txt` chứa canary khớp chính regex password của auditor, giữ nguyên manifest.
- Kỳ vọng: file ngoài manifest hoặc có secret trong bất kỳ văn bản xuất bản nào đều bị từ chối.
- Thực tế: `verify()` trả `[]`; chỉ yêu cầu ít nhất ba dòng manifest, không so tập file thực, chỉ scan bốn tên cố định. Bundle có thể chứa file không hash và không scan.
- Ảnh hưởng: không đủ cơ sở cho claim bundle đầy đủ và không có bí mật. Probe dùng canary giả, không dùng mật khẩu thật.
- Cách sửa: manifest unique/canonical paths, cấm traversal/absolute/symlink escape; so đúng tập file đệ quy trừ chính manifest, kiểm mọi byte/file được xuất bản và deny raw heap; kiểm hash trước/sau ở chế độ readonly. Thêm extra/duplicate/path/secret controls.

### AH4 — P2: CRLF và UTF-8 lỗi vẫn qua auditor strict LF

- File:dòng: `scripts/bh07_appheap/verify_evidence.py:114`.
- Tái hiện: cùng probe, `crlf`, `invalid_utf8`; đổi log thành CRLF hoặc thêm byte `0xff`, cập nhật manifest đúng raw bytes.
- Kỳ vọng: strict UTF-8 không BOM, không byte CR; vi phạm phải FAIL.
- Thực tế: cả hai trả `[]`. `read_text` universal-newline xóa dấu CR trước kiểm; `errors='replace'` che decode failure. Manifest cũng được đọc bằng text newline translation.
- Cách sửa: đọc binary, kiểm BOM/CR, decode UTF-8 strict và báo lỗi; làm cho cả manifest và toàn bộ file được bao phủ. Test CRLF, CR đơn, UTF-8 lỗi, BOM và xác nhận không sửa file/manifest.

### AH5 — P2: `--reuse-build` tự gán profile mà không có bằng chứng artifact

- File:dòng: `scripts/bh07_appheap/run_app_profile_heap.js:316`; liên quan `:152`–`:163`.
- Tái hiện: `node docs/reviews/bh07/review_8914b2f_evidence/build_probe.js` thực thi nguyên nhánh reuse-build hiện hành, không cung cấp artifact; vẫn tạo `{mode:'profile', reused:true}`. Đây là branch probe, **không phải lần chạy Chrome**. Đường thực tế: build debug/release trước rồi gọi runner `--reuse-build --cycles 2` sẽ bỏ build và dùng nhãn profile này.
- Kỳ vọng: build không profile/không chứng minh được profile phải FAIL. Server được đo phải phục vụ đúng artifact đã xác minh.
- Thực tế: mode chỉ là literal do runner tự điền. Chưa kiểm hash/mode của build cũ. Static server cũng chỉ chờ HTTP 200; nếu cổng 8088 đã có server, child mới bind lỗi vẫn có thể dùng server cũ.
- Ảnh hưởng: oracle kiểm `mode == 'profile'` không bảo đảm phép đo dùng profile artifact/source được giao. Không khẳng định lượt tác giả đã dùng debug: bundle hiện ghi build mới 44.925 ms, không có `reused`.
- Cách sửa: bỏ reuse trong lượt chứng nhận hoặc buộc provenance build profile gắn source và artifact hashes; preflight port ownership và kiểm artifact thực được serve. Negative controls debug/release/missing/stale build và occupied port phải FAIL.

## Bằng chứng reviewer tự chạy

Evidence riêng: [review_8914b2f_evidence/](review_8914b2f_evidence/). Probe là input đối nghịch để quan sát lỗi hiện tại, không sửa oracle hay nới kỳ vọng. `verify()` được gọi trực tiếp trên clone tạm; `[]` là auditor chấp nhận, không gán thành lần chạy CLI/profile mới.

| Lệnh/kiểm tra | Kết quả reviewer |
| --- | --- |
| `python -X utf8 scripts/bh07_appheap/verify_evidence.py` | exit 0 trên bundle tác giả |
| `python -m unittest tests.test_bh07_app_heap_oracle tests.test_bh07_app_heap_evidence -v` | exit 0, 18/18 |
| `node --check scripts/bh07_appheap/run_app_profile_heap.js` | exit 0 |
| `flutter analyze --no-pub` | exit 0, 0 issue |
| `flutter test --no-pub` | exit 0, 247 PASS + 1 SKIP |
| Reviewer probes Python/Node | exit 0, ghi nhận các gate nhận sai như trên |
| Author bundle audit binary/hash và readonly | 3/3 manifest entries, 4 file gồm manifest; strict UTF-8 LF thực tế hợp lệ; không thấy secret theo mẫu kiểm; toàn bộ hash trước/sau không đổi |
| Diff source → docs; base → app/backend | runtime tree không đổi ở docs commit; `lib/`, `test/`, `supabase/` không đổi từ base |
| `git diff --check 3b30e49..8914b2f` | exit 0 |

Môi trường reviewer Linux, Flutter 3.47.7; tác giả Windows/Flutter 3.47.6/Chrome 155. Logs Flutter reviewer chuẩn hóa progress CR thành LF khi đóng gói; không sửa bytes bundle tác giả. Checkout reviewer sạch trước lệnh, SHA/dirty/exit/count tại `provenance.json`; trạng thái dirty sau viết báo cáo chỉ là docs/evidence reviewer.

## NOT RUN và giới hạn

| Hạng mục | Trạng thái / điều kiện đóng |
| --- | --- |
| `node scripts/bh07_appheap/run_app_profile_heap.js --cycles 2` tại reviewer | **NOT RUN**: API local 54321 không chạy; chỉ còn 672.018.432 byte (~641 MiB) đĩa, chưa đủ dựng stack và build/snapshot cô lập. `runtime_preflight.json` ghi điều kiện thực. Không reset/đổi DB để tạo môi trường. Cần QA runtime mới source sạch sau sửa. |
| Runtime tác giả | Audit metadata tám snapshot, hai chu kỳ và timeOrigin; raw dump đã xóa nên không thể parse/replay lại tám dump. Không dùng claim tác giả thay lần chạy reviewer. |
| Toàn bộ retained objects/paths, số dư/doanh thu/ghi chú, cache/listener ngoài bank sentinel | **NOT RUN** trong phép đo này; một sentinel bank biến mất không chứng minh toàn bộ tiêu chí §4.4. Expense chưa nạp không tạo kết luận. |
| Dart VM desktop/mobile, browser/device khác; HTTP/Auth/DB mới | **NOT RUN** trong lượt này; Flutter HTTP suite bị skip không chứng minh HTTP thật. |
| Managed backup/PITR/offsite/encryption/retention, concurrent writers, staging/production, ngân hàng/webhook, tải/rehearsal/pilot, nghiệm thu toàn BH-07/BH-08 | **NOT RUN**, giữ trạng thái cổng kế hoạch; không merge/deploy/pilot. |

Giao sửa gói kiểm chứng vòng 1/2 theo AGENTS: test tái hiện trước, sửa đầy đủ AH1–AH5 và phát lại positive/negative controls; chỉ script/test kiểm chứng/docs/evidence. Giữ nguyên bằng chứng cũ và các gate đã đóng. **Kết luận: Chưa đạt.**
