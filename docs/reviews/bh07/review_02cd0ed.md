# Review BH-07 — 02cd0ed (lần sửa cuối theo ủy quyền bổ sung)

Ngày 23/10/2026. Nhánh `feat/bh07-browser-verification`.

- Base: `b5517df1055ded3de86bdce49927188eab8e53d8`.
- Tested source: `a62f509986f65592da3fb5bccebe7b7c246ff7b7`.
- Docs/evidence: `02cd0edbb9b1f77213c6788474984686895e125c`.
- Kết luận: [ ] Đạt  [x] Chưa đạt.
- Reviewer chỉ review và ghi tài liệu; không sửa script triển khai/app/backend. Ủy quyền bổ sung cho một lượt sửa cuối đã được ghi trong bàn giao; không áp dụng lại quy tắc dừng hai vòng để từ chối lượt này. Phần Codex triển khai tiếp theo, nếu được thực hiện theo ủy quyền chủ dự án, phải ghi rõ **tự sửa/tự kiểm, không phải review độc lập**.

## Phát hiện

### P0

Không có.

### P1

Không có.

### P2

#### BR3-1 — Manager vẫn nhận field tiền ngoài contract

- **File:dòng:** `scripts/bh07_browser/assertions.js:197` (gate trả PASS tại `:210`); caller `scripts/bh07_browser/run_browser_verification.js:773`.
- **Cách tái hiện:** giữ nguyên clipboard fixture hợp lệ (chi phí/phải thu/đã thu/còn phải thu = 200,000/200,000/0/200,000 VNĐ), thêm dòng `📉 Hoàn tiền: 999 VNĐ`. Gọi predicate thật `validateManagerClipboard` → `[]`, tức PASS; positive baseline vẫn PASS.
- **Kỳ vọng:** FAIL vì gói được giao phải từ chối field lạ, không chỉ kiểm bốn field đã biết.
- **Thực tế/ảnh hưởng:** vòng lặp chỉ chặn một blacklist hữu hạn `FINANCE_LABELS`, không whitelist toàn bộ field/line; bộ kiểm chứng tiếp tục báo xanh nếu copy thừa trường tài chính khác. Không khẳng định clipboard app thật đã có dòng này.
- **Cách sửa:** kiểm tập dòng/field được phép và đúng số lần, giữ bốn aggregate chính xác; thêm negative control field ngoài danh sách hiện hành và positive clipboard thật.
- **Trạng thái:** FAIL — P2 còn mở của BR3.

#### BR3-2 — Regex tiền bỏ lọt VNĐ/đ trên UI và clipboard Cohost

- **File:dòng:** `scripts/bh07_browser/assertions.js:60`, `:245`, `:263`.
- **Cách tái hiện:** thêm ` · 999 VNĐ` vào dòng địa điểm của clipboard Cohost hợp lệ; hoặc đưa semantics `Chỉ xem số lượng, các count hợp lệ và 999 VNĐ` vào `validateCohostSummarySurface`. Cả hai predicate thật trả `[]` (PASS), positive count-only baseline vẫn PASS.
- **Kỳ vọng:** FAIL khi có số tiền, dù không đi kèm nhãn tài chính trong blacklist.
- **Thực tế/ảnh hưởng:** `\b` của JavaScript không coi `Đ/đ` là ký tự word; sau ký tự này là whitespace/end cũng non-word nên nhánh VNĐ/đ không khớp. Dòng metadata cho phép nội dung tự do, vì vậy whitelist dòng không bù được guard tiền hỏng. Không phát hiện rò tiền trong lần browser thật; đây là lỗ hổng gate kiểm chứng.
- **Cách sửa:** dùng ranh giới Unicode hoặc delimiter phù hợp sau đơn vị tiền; kiểm cả UI lẫn clipboard, có control cho VNĐ/đ/VND và positive chứa ngày/giờ/count hợp lệ.
- **Trạng thái:** FAIL — P2 còn mở của BR3.

#### BR3-3 — Member history có thể coi response lỗi là rỗng và bỏ lọt tài khoản trên UI

- **File:dòng:** `scripts/bh07_browser/run_browser_verification.js:1098`; `scripts/bh07_browser/assertions.js:293`, `:314`.
- **Cách tái hiện:** reviewer trích nguyên block gate Member hiện hành (không đổi kỳ vọng) vào VM; request `p_club_id=null`, UI empty hợp lệ nhưng body HTTP là `{code:'42501', message:'FORBIDDEN'}` → gate không ném lỗi, PASS. Body `[]` + cùng UI là positive baseline, PASS. Độc lập, semantics `Lịch sử buổi\nChưa có buổi nào\nSTK: 123456789012` cũng được `validateHistorySurface(..., [], true)` trả `[]`.
- **Kỳ vọng:** chỉ body array rỗng thực sự của request thành công mới chứng minh empty history; UI lịch sử không được có contact/bank/account. FORBIDDEN/error không được giả thành empty.
- **Thực tế/ảnh hưởng:** ternary đổi mọi body không phải array thành `[]`; history surface chỉ kiểm một danh sách nhãn/tên buổi và row marker, không áp dụng `privacyErrors`. Do đó kiểm chứng “response [] và không STK/contact” có thể xanh giả. Không khẳng định API/app thật trả dữ liệu lỗi hoặc lộ STK trong happy path.
- **Cách sửa:** bắt buộc response HTTP thành công, body là array trước khi lấy IDs; lỗi parse/domain phải FAIL. Dùng guard privacy cho surface lịch sử và control lỗi response/contact/account, giữ exact filter/ID/empty/denied-row đã bổ sung.
- **Trạng thái:** FAIL — P2 còn mở của BR3.

[Probe reviewer](review_02cd0ed_evidence/extra_controls.js), [9 kết quả](review_02cd0ed_evidence/extra-controls.json): **4 positive baseline PASS; 5 negative input bị nhận PASS sai**; exit 1 đúng để báo lỗi gate.

### NOT RUN

- Thiết bị mobile thật; browser khác/Chrome155 trên Windows; ma trận offline/deep link đa thiết bị. Reviewer chạy Chromium154/Linux như mô tả dưới.
- Response owner trả trễ sau khi đổi actor; không suy ra từ ca same-SPA happy path.
- Ngân hàng/VietQR/webhook thật.
- Staging/production, backup/restore, rehearsal/pilot; nghiệm thu toàn BH-07.
- `supabase db reset` toàn bộ stack; reviewer dựng DB mới biệt lập và cài migration hiện hành + fixture. Hồi quy DB BH-02..06 335 ca không chạy lại vì không đổi DB/backend.

## Bằng chứng reviewer tự chạy

| Cổng | Kết quả tự chạy | Bằng chứng |
|---|---|---|
| Analyze | 0 issue; exit0 | `analyze.log` |
| Flutter | 240 PASS +1 SKIP; exit0 | `flutter.log` |
| DB BH-07 | 23/23 PASS; exit0; clean checkout | `bh07.log`, `bh07_test_results_20261023044706.json` |
| Web build | PASS; exit0 | `build-web.log` |
| Browser thật | 11/11 PASS; exit0; checkout `02cd0ed`, dirty=false; code/hash tương ứng tested source không đổi | `browser-summary.json`, `browser-stdout.log`, 12 ảnh `screenshots/` |
| POST/DB độc lập | 2 POST giống payload kể cả expectedVersion2; lần đầu ERR_INTERNET_DISCONNECTED, retry200; completed v3,1 operation,1 audit,attendance present,expense200000 | `post-retry-audit.json`, `network-observer.json`, `side-effects.json` |
| Negative tác giả | 27/27 đúng kỳ vọng (7 positive,20 negative),0 HARNESS_ERROR; exit0 | `negative.log`, `negative_controls.json` |
| Verifier controls | 9/9; baseline0,8 fault1; mọi tree/manifest readonly | `verifier-controls.log`, `verifier_controls.json` |
| Mutant | Bản gốc exit0; gate manager đổi `if(true)` exit1; harness exit0 | `mutant.log`, `mutant_negative_control.log` |
| Manifest/encoding/secret tác giả | 33/33 khớp; UTF-8 không BOM, CR=0; không thấy secret/JWT ngoài public anon allowlist theo scanner hiện hành; 12 ảnh khác hash; source hashes khớp | `manifest.log`, `artifact-audit.json` |
| Probe bổ sung reviewer | 4 baseline đúng;5 ca sai vẫn bị chấp nhận; exit1 | `extra-controls.json`, `extra-controls.log` |

Bằng chứng ở [review_02cd0ed_evidence/](review_02cd0ed_evidence/). Chạy `--verify` trực tiếp trên checkout và đối chiếu **34/34 file gồm manifest với git blob** không đổi. Để tránh overwrite bằng chứng tác giả, các runner sinh JSON/log chạy ở bản sao ngoài repo. Riêng `run_verifier_controls.py` trên bản sao đổi đúng một dòng: copy manifest đã xuất bản vào pristine thay vì gọi `--generate`; mọi fault và expectation giữ nguyên. **Reviewer không chạy --generate.** [Patch duy nhất cho verifier control](review_02cd0ed_evidence/verifier-controls-infra.patch).

Ca SPA dùng Back/tab và logout/login thật, không reload giữa Owner→Cohost; F5 riêng ở TC10. Observer thu hai timeOrigin, phù hợp F5 riêng; không thu được owner finance-card=true trong các sample, nên không dùng riêng observer để kết luận đã quan sát mọi trạng thái cache. Đối chiếu thêm log UI và ảnh Manager/Cohost. Delayed response vẫn NOT RUN.

`git diff --check` có whitespace trong hai log gốc tác giả (trailing space dòng build và blank EOF verifier); không sửa log hoặc coi đây là P2 độc lập vì không ảnh hưởng nội dung/hash/encoding.

## Phạm vi và tính độc lập

Diff base→source chỉ sáu file script kiểm chứng; source→docs chỉ docs/evidence/trạng thái. `git diff b5517df..02cd0ed -- lib test supabase` rỗng; không đổi migration/RPC/model/repository/provider/UI/contract. Đã xem diff `main...HEAD` và tách phần gói kiểm chứng theo base được giao, không review lại A/B/C/D. [Source diff](review_02cd0ed_evidence/scope-source.txt), [docs diff](review_02cd0ed_evidence/scope-docs.txt), [app/backend diff rỗng](review_02cd0ed_evidence/scope-app.txt).

Lần đầu khởi chạy browser bị dừng vì JSON mới của reviewer DB runner làm checkout dirty; đã chuyển JSON sang scratch, seed lại cùng SQL và phát lại từ checkout sạch. Lần build khởi động trước khi recipe stack tạo xong runtime key dừng ở wrapper (chưa chạy Flutter); sau stack-ready đã build thành công. Đây là điều chỉnh orchestration reviewer, không phải lỗi app.

Môi trường reviewer: Linux/bash; Flutter3.47.7, Chromium154; GoTrue2.197.0/PostgREST16.4/PostgreSQL17.11/Kong2.8.1 local riêng. Khác tác giả Windows/Flutter3.47.6/Chrome155. Dùng cùng migration và fixture SQL, Auth đăng nhập mật khẩu thật, không mock repository. Bản runner ngoài repo chỉ đổi đường dẫn Chromium/output/DB container, cờ sandbox renderer của môi trường, nạp đúng assertions.js gốc và bỏ gọi seed Windows vì recipe đã seed cùng SQL; không đổi assertion/selectors. Build dùng `--no-web-resources-cdn` và public anon runtime của stack riêng; không dùng token khác cho mutation client. [Patch hạ tầng](review_02cd0ed_evidence/runner-infra.patch).

Giữ BR1 và ca SPA BR4 đã đóng. BR2 và BR5 được đóng trong phạm vi lần kiểm chứng này; BR3 còn ba P2 như trên. Không cần sửa app/backend theo các phát hiện này.

**Chưa đạt** gói Browser / Offline / Reopen lần sửa cuối tại source `a62f509`, docs `02cd0ed`. Bàn giao phần còn lại cho Codex theo ủy quyền bổ sung; nếu Codex thực hiện thì kết quả là tự sửa/tự kiểm và cần phân biệt với nghiệm thu độc lập. Không merge main/apply DB thật/deploy/chuyển pilot.
