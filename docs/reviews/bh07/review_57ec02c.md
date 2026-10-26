# Review V2b app-profile heap — vòng sửa 1/2

- Reviewer: Codex, không sửa source triển khai. Codex từng làm gói Provider/browser lịch sử; review này không coi các phép đo đó là phép đo app-profile mới.
- Base review: `a972ecd73ab2339306f80b081823057c5935819c`.
- Tested source runtime tác giả: `249f12ed5b8ba042de1d48e9d5e06ffe7c125ada`.
- Docs/checkout reviewer: `57ec02c856f7e14f36aaa5a7add0356f1496c1f1`, sạch trước kiểm tra.
- Ngày: 26/10/2026, Asia/Saigon. Phạm vi chỉ công cụ/test kiểm chứng, evidence và trạng thái.

## Kết luận

**Chưa đạt V2b app-profile heap vòng 1/2.** Còn **1 P1 và 5 P2**: AH1, AH2-A/B, AH3-A/B và AH6. Không có P0. AH4/AH5 đóng trong phạm vi source/control đã kiểm; runtime Chrome/profile của reviewer vẫn NOT RUN. Đây là lỗi gói kiểm chứng, **không phải bằng chứng app đã leak**. Không nghiệm thu toàn V2b/BH-07; Provider/tooling, V1 và V5b giữ Đạt local.

| Gate cũ | Trạng thái review |
| --- | --- |
| AH1 — snapshot hỏng | Còn mở P1; probe cũ bị chặn nhưng còn ba dạng JSON hỏng được PASS |
| AH2 — auditor tái tính verdict/mốc | Còn mở P2: summary rỗng bỏ qua toàn bộ kiểm semantic, Markdown verdict chưa đối chiếu |
| AH3 — manifest/secret/raw heap coverage | Còn mở P2: symlink thư mục và raw sentinel trong log còn qua |
| AH4 — strict bytes UTF-8/BOM/CR | Đóng; phát lại byte controls và suite LF-safe, readonly |
| AH5 — reuse/build/serve provenance | Đóng trong phạm vi review: reuse bị từ chối, guard 8/8; source bắt buộc build profile, hash 39 artifact trong bundle; đối chiếu served bytes áp dụng hai file entry index/main theo handoff, không gọi là kiểm byte toàn bộ 39 file |

## Phát hiện

Lệnh chung tái hiện AH1–AH3:

```bash
PYTHONPATH=. python docs/reviews/bh07/review_57ec02c_evidence/extra_controls.py
```

Probe dùng fixture giả trong thư mục tạm và rehash LF-safe sau mỗi mutation; không sửa app/backend/bundle tác giả. Các fixture syntax xuất phát từ helper test được bàn giao; `json.loads` kiểm độc lập tính hợp lệ JSON. Output `problems: []` là hàm auditor chấp nhận, không phải suite đối nghịch đã đạt kỳ vọng. Riêng `empty_summary_cli` còn chạy CLI thật để xác nhận exit 0 sai.

### AH1 — P1: Parser vẫn coi JSON hỏng là snapshot hợp lệ

- File:dòng: `scripts/bh07_appheap/heap_oracle.py:127`, liên quan `:116`, `:167`.
- Tái hiện: `missing_string_comma`, `garbage_before_nodes`, `leading_zero_integer` trong probe. Positive `positive_valid` vẫn PASS.
- Kỳ vọng: JSON hỏng phải `ok:false`, mọi presence `null`, quyết định FAIL.
- Thực tế: bỏ dấu phẩy giữa hai string, thêm `BROKEN` trước `nodes`, hoặc thay số `0` thành `00`: `json.loads` đều FAIL nhưng `scan.ok=true`, presence bank=false/probe=true và `decide=PASS`. `_string_elements` chỉ loại literal rồi strip dấu phẩy/space, không kiểm grammar separator/escape; tìm bảng bằng regex bỏ qua nội dung trước bảng; regex số chấp nhận số JSON không hợp lệ.
- Ảnh hưởng: vẫn có thể chứng nhận sạch từ dump hỏng dù metadata/count tổng khớp. Probe chỉ dùng mốc post_logout để cô lập lỗi scan; không giả làm một lần đo Chrome.
- Cách sửa: validate JSON đầy đủ bằng parser đúng grammar trước kiểm cấu trúc/counts; nếu cần streaming, phải kiểm toàn bộ token/separator/escape/UTF-8 và không bỏ qua khoảng giữa bảng. Giữ kiểm strings-last/counts, trả presence null khi không hợp lệ. Test cả ba input này, escaped literals và positive snapshot V8 hợp lệ.

### AH2-A — P2: Summary rỗng/null bỏ qua toàn bộ gate semantic

- File:dòng: `scripts/bh07_appheap/verify_evidence.py:271`.
- Tái hiện: `empty_summary`, `null_summary`, `empty_list_summary`; `empty_summary_cli` chạy `verify_evidence.py --dir <clone-tạm>` thật.
- Kỳ vọng: summary phải là object đúng schema, đủ trường, cycles/mốc và verdict; không có measurement phải FAIL/exit 1.
- Thực tế: `{}`, `null`, `[]` đều trả `[]` sau rehash. CLI với `{}` in PASS/exit 0. `if summary:` bỏ qua required fields, build, cycles, cleanup, report khi JSON falsy.
- Cách sửa: kiểm top-level type không phụ thuộc truthiness, required fields vô điều kiện sau parse; type-check dữ liệu lồng nhau và fail-closed có finding thay vì crash/skip. Thêm CLI controls cho `{}`, null, list, scalar và missing required fields; giữ positive bundle.

### AH2-B — P2: Markdown có thể ghi verdict trái JSON mà auditor vẫn PASS

- File:dòng: `scripts/bh07_appheap/verify_evidence.py:218`.
- Tái hiện: `contradictory_markdown_verdict`, thay `(verdict PASS)` thành `(verdict FAIL)` trong report, rehash.
- Kỳ vọng: Markdown/JSON/verdict tái tính nhất quán.
- Thực tế: `problems=[]`; chỉ kiểm substring `- Status: **RUN**`, không kiểm verdict đi kèm. Việc tìm size/hash toàn văn cũng chưa xác minh chúng thuộc đúng hàng cycle/epoch.
- Cách sửa: dùng renderer/parser report chung có cấu trúc hoặc so canonical output từ summary đã validate; kiểm status, verdict và từng hàng cycle/epoch thay vì substring rời. Test verdict trái nhau, đổi hàng/nhãn mốc và positive report.

### AH3-A — P2: Symlink thư mục nằm ngoài inventory nên không bị chặn

- File:dòng: `scripts/bh07_appheap/verify_evidence.py:60`, liên quan `:117`.
- Tái hiện: `directory_symlink_to_raw_heap`: thêm symlink `linked` tới thư mục tạm ngoài bundle chứa raw-heap fixture; không có manifest entry mới.
- Kỳ vọng: mọi symlink, kể cả symlink thư mục/broken link, phải bị từ chối trước khi đọc hoặc hash target; không coi inventory bỏ qua link là bundle sạch.
- Thực tế Linux: `symlink_present=true`, `problems=[]`. `_bundle_files` lọc `is_file()` trước; `rglob` không đi vào symlink directory nên kiểm `is_symlink()` phía sau không bao giờ thấy nó. Hash trước/sau cũng không bao phủ link này.
- Cách sửa: kiểm entry bằng lstat/is_symlink trước phân loại file/directory, fail-closed với symlink/junction/escape; inventory và readonly snapshot phải bao phủ entry bị cấm. Thêm file-link, directory-link, broken-link controls; Windows thiếu quyền tạo link phải ghi NOT RUN rõ ràng.

### AH3-B — P2: Raw sentinel ở log đã hash vẫn được nhận là sanitized

- File:dòng: `scripts/bh07_appheap/verify_evidence.py:288`, liên quan `:301`.
- Tái hiện: `raw_bank_sentinel_in_log`: dùng canary giả 10 ký tự, cập nhật length/hash sentinel trong summary đúng canary, ghi nguyên canary vào run.log và rehash.
- Kỳ vọng: raw sentinel không xuất hiện ở bất kỳ văn bản bundle nào, không chỉ bị cấm dưới khóa `sentinels.bank.value`.
- Thực tế: canary khớp length/hash công bố nhưng `problems=[]`. Kiểm chỉ cấm khóa `value` và vài regex credential cố định; không đối chiếu raw sentinel trong nội dung khác.
- Cách sửa: thêm sanitizer trước publication và gate độc lập phát hiện sentinel dựa trên deny-values riêng tư trong lần chạy hoặc candidate length/hash; không xuất bản deny-values/raw dump. Controls phải cấy raw sentinel trong log/report/extra file và nested metadata, giữ positive chỉ có hash/length. Canary probe không phải STK hay mật khẩu thật.

### AH6 — P2: Link mới trong tài liệu trạng thái bị thêm thừa `docs/`

- File:dòng: `docs/09_IMPLEMENTATION_PLAN.md:1`; tương tự `docs/00_START_HERE.md:1`, `docs/25_BH07_IMPLEMENTATION_HANDOFF.md:1`, `docs/26_BH07_OPERATIONS_REHEARSAL.md:1`, `docs/STATUS_HISTORY.md:1` tại docs commit được review.
- Tái hiện: audit Markdown trong `link_audit.py`; có 10 target không tồn tại.
- Kỳ vọng: link tương đối mở được handoff/evidence trong repo.
- Thực tế: `docs/reviews/bh07/...` từ tài liệu đã nằm trong `docs/` resolve thành `docs/docs/reviews/bh07/...` không tồn tại.
- Cách sửa: dùng `reviews/bh07/...` cho năm tài liệu này; giữ `docs/reviews/...` ở file root. Audit link toàn bộ các dòng trạng thái/handoff, kể cả đoạn lịch sử vừa lưu; không thay nội dung bằng chứng cũ.

## Bằng chứng reviewer tự chạy

Evidence riêng: [review_57ec02c_evidence/](review_57ec02c_evidence/). Không sửa probe cũ. Giữ cả log thất bại môi trường ban đầu và log chạy lại.

| Lệnh | Exit / kết quả |
| --- | --- |
| `node scripts/bh07_appheap/build_guard.js --self-test` | 0, 8/8 |
| `node docs/reviews/bh07/review_8914b2f_evidence/build_probe.js` | 1, đúng kỳ vọng từ chối reuse |
| `python -X utf8 docs/reviews/bh07/review_8914b2f_evidence/probes.py` | 0; các ca cũ nay có finding semantic/strict bytes đúng, trên Linux không có CRLF Windows che lỗi semantic |
| `python -X utf8 scripts/bh07_appheap/verify_evidence.py` | 0 trên bundle tác giả |
| Bốn suite Python theo handoff | Lượt sandbox exit1 do Node listen EPERM; chạy lại cùng lệnh với quyền loopback: exit0, 66/66. Không tính EPERM là lỗi triển khai |
| `flutter analyze --no-pub` | 0, no issues |
| `flutter test --no-pub` | 0, 247 PASS +1 SKIP; HTTP/Auth suite mặc định skip, không có HTTP runtime mới |
| `node --check scripts/bh07_appheap/run_app_profile_heap.js` | 0 |
| Probes bổ sung | 0, positive valid PASS và các false-green được ghi tại extra_controls.json |
| Diff từ base, source→docs và whitespace | Chỉ script/test kiểm chứng + docs/evidence; `lib/`, `test/`, `supabase/` không đổi; source tree docs tip giống tested source; diff-check exit0 |
| Bundle tác giả | 3/3 manifest entries (4 file kể manifest), hash trùng Git blob docs commit sau mọi lệnh; không generate/ghi đè bundle; strict UTF-8 LF thực tế hợp lệ; chưa thấy secret theo mẫu kiểm |

Provenance tại `provenance.json`: checkout SHA, git status sạch trước report, exit/count, 39 artifact hash, 2 cycle/8 snapshot ghi bởi tác giả. Reviewer Linux/Node 24.19.0/Flutter 3.47.7; tác giả Windows/Node 24.21.0/Flutter 3.47.6/Chrome 155. Runtime tác giả source sạch được audit, không gán thành runtime reviewer. Log Flutter reviewer chỉ chuẩn hóa progress CR sang LF khi đóng gói; bytes tác giả giữ nguyên. Reviewer sửa một lỗi truyền đối số trong fixture canary tự viết trước khi chốt output; không sửa source hoặc kỳ vọng target.

## NOT RUN

| Hạng mục | Giới hạn / điều kiện đóng |
| --- | --- |
| `node scripts/bh07_appheap/run_app_profile_heap.js --cycles 2` của reviewer | NOT RUN: Supabase local 54321 không chạy; đĩa trống 669.831.168 byte (~639 MiB), chưa đủ stack/profile build/dump cô lập. Cần máy đủ môi trường để chạy runtime mới sau sửa; không tự đổi/reset DB. |
| Parse lại tám dump runtime tác giả | NOT RUN: dump đã xóa; chỉ audit summary/log/build hashes và code. Không dùng log tác giả thay phép đo reviewer. |
| Retained paths/tất cả model, số dư/doanh thu/ghi chú, cache/listeners ngoài bank sentinel; Dart VM desktop/mobile | NOT RUN; một bank sentinel và expense chưa được nạp không chứng minh toàn tiêu chí §4.4. Giới hạn V8/web profile giữ nguyên. |
| Link controls trên Windows junction/symlink | NOT RUN tại reviewer Linux; directory symlink Linux đã tái hiện. |
| Browser/device khác, offline/deep link mới, HTTP/Auth/DB runtime mới, managed backup/PITR/offsite/encryption/retention, concurrent writers, ngân hàng/webhook, staging/production, tải/rehearsal/pilot, BH-08 | NOT RUN trong lượt này; giữ kết luận local các cổng cũ, không nghiệm thu toàn BH-07. |

Giao sửa vòng **2/2** theo AGENTS: viết test tái hiện trước; sửa đầy đủ AH1,AH2-A/B,AH3-A/B,AH6; giữ AH4/AH5 và các gate cũ. Không sửa app/backend/contract, không merge/deploy/pilot. Nếu còn lỗi sau vòng 2/2 thì dừng và báo chủ dự án. **Kết luận: Chưa đạt.**
