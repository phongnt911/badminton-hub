> **Hiện hành23/10/2026: Đạt theo tự review local, KHÔNG độc lập**, theo yêu cầu trực tiếp của chủ dự án. Xem [kết luận](self_review_a6d58af.md). Phần bàn giao bên dưới giữ trạng thái tại thời điểm công bố trước tự review; không nghiệm thu toàn BH-07/production/pilot.

# Bàn giao Codex sửa BR3 — Browser / Offline / Reopen BH-07

Ngày 23/10/2026. **Codex tự sửa/tự kiểm, KHÔNG phải review độc lập. Trạng thái: Chờ review độc lập sau Codex tự sửa.** Không ghi Đạt/hoàn thành toàn gói.

- Branch: `feat/bh07-browser-verification`.
- Base: `1fc7e2eb171acd6c7afbc16e9f1053f9b3cb21c3`.
- Tested source: `a6d58aff3f1726484146a6c89aa7d559bb684d6d`.
- Docs/evidence commit: commit chứa bản bàn giao này, full SHA gửi trong prompt reviewer; không tự ghi SHA của chính file đang commit.
- Review nguồn: [review_02cd0ed.md](review_02cd0ed.md). Không sửa kết luận review cũ.
- Bằng chứng mới: [browser_codex_fix_evidence/](browser_codex_fix_evidence/). Bằng chứng tác giả/reviewer cũ giữ nguyên.

## Phạm vi và phần sửa

Chỉ sửa ba script: `assertions.js`, `run_browser_verification.js`, `run_negative_controls.js` trong `scripts/bh07_browser/`. Diff base→tested source với `lib/ test/ supabase/` rỗng. Không đổi app, unit test, migration/RPC/model/repository/provider/UI/contract. Giữ gate BR1/BR2/BR4/BR5.

| Phát hiện | Sửa nguyên nhân | Kiểm chứng tự chạy |
|---|---|---|
| BR3-1 P2 | Manager dùng whitelist dòng metadata + bốn dòng finance của fixture; đúng số dòng/số lần. Field tiền ngoài whitelist bị loại; giữ exact aggregate200k/200k/0/200k, guard null/privacy và mutant marker. | Probe cũ thêm `Hoàn tiền:999 VNĐ` đỏ trước sửa, xanh sau sửa; control field lạ/metadata trùng và positive clipboard. |
| BR3-2 P2 | Đổi `\b` sau đơn vị tiền thành negative lookahead Unicode letter/number. Guard chung bắt VNĐ/đ/VND trên Cohost UI/clipboard và metadata Manager; không bắt nhầm count/date/time. | Probe cũ UI/clipboard VNĐ từ false-PASS thành FAIL đúng; thêm6 control ba đơn vị tiền trên UI/clipboard. |
| BR3-3 P2 | CDP thu HTTP status. Parser chỉ chấp nhận200 + JSON hợp lệ; response lỗi vẫn giữ dạng lỗi. Validator bắt buộc array/row ID trước exact IDs, bỏ fallback lỗi→[]. History surface áp dụng privacy và money guard. | Probe cũ body FORBIDDEN và STK UI bị loại, positive[] giữ PASS; control403-body[], invalidJSON, null và positive200[]. |

Các sửa chỉ là predicate/capture của bộ kiểm chứng, không thay hành vi ứng dụng. Chưa được reviewer độc lập xác nhận đóng P2.

## Red → Green và controls

- Phát lại `review_02cd0ed_evidence/extra_controls.js` **trước sửa** trên base1fc7e2e: exit1,4 positive PASS,5 ca sai bị nhận PASS.
- **Sau sửa**: exit0, cả9 ca đúng kỳ vọng;4 positive PASS,5 negative FAIL. Chỉ thay đường dẫn output của bản probe ngoài repo; không đổi expectation/input/logic VM.
- Giữ27 control trước, thêm14 thành **41 control**:8 positive PASS,33 negative FAIL,0 HARNESS_ERROR; overall exit0.
- Verifier controls:9/9; baseline0,8 fault1; mọi fault readonly.
- Mutant: bản không sửa exit0; gate `if(true)` exit1; harness exit0.

## Kết quả tự chạy và provenance

| Cổng | Kết quả | Exit |
|---|---|---|
| Flutter analyze | 0 issues | 0 |
| Flutter test | 240 PASS +1 SKIP | 0 |
| BH-07 DB | 23/23 PASS, tested source đúng, worktree sạch khi chạy | 0 |
| Web build | PASS | 0 |
| Browser thật | 11/11 PASS,12 ảnh khác hash, `is_dirty=false` | 0 |
| Probe reviewer cũ |9/9 đúng kỳ vọng;4 positive/5 negative; red trước sửa5 false accepts | Green0 / Red1 |
| Negative |41/41 đúng kỳ vọng,8 positive/33 negative/0 harness error | 0 |
| Verifier |9/9 trên copy bằng chứng mới; baseline0,8 fault1; readonly mọi ca | 0 |
| Mutant |Bản gốc0, `if(true)`1; giữ gate phát hiện mutation | 0 |
| Manifest mới |52/52 khớp; UTF-8 không BOM/CR, scanner không thấy secret/JWT ngoài allowlist; final verify không đổi53 file gồm manifest | 0 |

`environment.json` lưu tested SHA/hash mọi script gốc và khác biệt hạ tầng; `browser_summary.json` là raw output của runner. `summary.json` ghi rõ tự sửa/tự kiểm, trạng thái Chờ review độc lập. `exits.json` đo exit process, không điền0 cho NOT RUN. Các bundle cũ và review cũ không bị sửa.

Trace mới có đúng2 POST complete cùng payload/request_id/expectedVersion2; lỗi đầu là `ERR_INTERNET_DISCONNECTED`, retry200. DB read sau chạy: completed v3,1 operation,1 SESSION_COMPLETED audit, attendance present/checked_in,expenses200000. Không suy kết quả DB từ UI.

Recipe đóng gói dùng --generate để chuẩn hóa và tính manifest ở vai triển khai. Hai lượt --verify đo snapshot thật, đều readonly; sau khi ghi proof/log, generate lại một lần rồi final --verify xác nhận nội dung log/proof/manifest ổn định. Không làm mới bằng chứng cũ và không dùng --generate ở vai reviewer.

## Tái lập trong môi trường Linux của Codex

Các recipe/copy hạ tầng được lưu trong evidence; không đổi assertion/selectors khi thích ứng Windows→Linux.

1. Checkout tested source sạch. Flutter `/workspace/toolchains/flutter-review-3.47.7/bin/flutter analyze`, `flutter test` (240+1skip).
2. Dựng stack mới biệt lập bằng recipe `run_local_stack.py`: PostgreSQL17.11, GoTrue2.197.0, PostgREST16.4, Kong2.8.1. Seed cùng `scripts/bh07_http/seed.sql` và SQL UI trong `seed_setup.js`;7 user đăng nhập mật khẩu qua Auth thật. Không dùng repo/Auth mock. Recipe cần sửa đường dẫn scratch theo checkout, không in runtime key.
3. `BH02_TEST_CONTAINER=bh07-http-review-db python -u docs/reviews/bh07/run_bh07_tests.py`. Chuyển JSON mới sang scratch trước browser để checkout sạch;23/23.
4. Recipe build đọc public anon runtime của stack local riêng (không xuất bản token); `flutter build web --no-pub --no-web-resources-cdn --dart-define=APP_ENV=test --dart-define=SUPABASE_URL=http://127.0.0.1:54321 --dart-define=SUPABASE_ANON_KEY=<runtime-public-anon>`.
5. `python -m http.server 8088 --bind 127.0.0.1 --directory build/web`; `prepare_browser.py` tạo bản runner ngoài repo chỉ đổi Chromium/output/DB-container/path và cờ môi trường. Seed đã chạy cùng SQL nên không gọi lại CLI Windows. Chạy runner Node và observers; không ghi đè evidence cũ.
6. Chạy `run_negative_controls.js`, `run_verifier_controls.py`, `run_mutant_controls.py` trên bản sao script/evidence ngoài repo để thu JSON/log mới. Các predicate/expectation không đổi. Verifier control tự generate manifest **chỉ trong bản sao tạm** theo thiết kế gốc. Với bằng chứng công bố, reviewer chỉ dùng `clean_and_manifest.py --verify --evidence-dir docs/reviews/bh07/browser_codex_fix_evidence`.
7. Phát lại probe cũ; đối chiếu snapshot trước/sau `--verify` và manifest mới. Không chạy --generate khi review.

Raw browser summary ghi hash của bản runner đã thích ứng, assertion/seed/verifier đúng blob nguồn; environment công bố thêm hash của mọi script gốc và patch hạ tầng. Build/seed/browser exit được đo từ process; bước không chạy ghi NOT RUN. Các log text chỉ chuẩn hóa UTF-8 LF để công bố, giữ đầy đủ nội dung gốc.

## NOT RUN và giới hạn

- Mobile/thiết bị thật, browser khác; Windows/Chrome155 không chạy lại. Tự kiểm dùng Linux/Chromium154, Flutter3.47.7 (khác tác giả Flutter3.47.6).
- Response owner trả trễ sau đổi actor; same-SPA happy path không chứng minh ca này.
- Ngân hàng/VietQR/webhook thật; staging/production; backup/restore; rehearsal/pilot; nghiệm thu toàn BH-07.
- Full `supabase db reset`; dùng stack DB mới + migration/fixture local. Hồi quy335 ca BH-02..06 không chạy lại vì DB/backend không đổi.
- Chưa có review độc lập cho mã Codex tự sửa. Giữ A/B/C/D và HTTP/Auth/concurrency đã Đạt local, không suy rộng thành production/pilot.
- Không merge main/apply DB thật/deploy/chuyển pilot. Đã dọn stack/browser/server/runtime key tạm sau tự kiểm.
