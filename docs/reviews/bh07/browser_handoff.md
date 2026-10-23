> **Hiện hành23/10/2026: Đạt local, đã đóng công việc Browser verification** theo [review và tự sửa](review_c4ce99b.md), không độc lập. Không còn trạng thái Chờ review hiện hành của gói này. Phần dưới bảo lưu bàn giao lịch sử; toàn BH-07/production/pilot chưa nghiệm thu.

> **Hiện hành23/10/2026:** Bổ sung gói response Owner trả trễ,2/2 ca UI local tự kiểm PASS, **Chờ review**, source `c4ce99b`. Xem [bàn giao mới](late_response_handoff.md). Giữ kết luận Browser trước ở phạm vi tự review; các phần dưới là lịch sử.

> **Hiện hành23/10/2026: Đạt theo tự review local, KHÔNG độc lập**, theo yêu cầu trực tiếp của chủ dự án. Xem [kết luận](self_review_a6d58af.md). Phần bàn giao bên dưới giữ trạng thái tại thời điểm công bố trước tự review; không nghiệm thu toàn BH-07/production/pilot.

> **Hiện hành23/10/2026:** Codex đã tự sửa/tự kiểm BR3, **Chờ review độc lập**, tested source `a6d58aff3f1726484146a6c89aa7d559bb684d6d`. Xem [bàn giao mới](browser_codex_fix_handoff.md) và [bằng chứng riêng](browser_codex_fix_evidence/). Đây **không phải review độc lập**; không tự ghi Đạt. Phần dưới giữ bàn giao tác giả trước Codex để truy vết.

# Bàn giao kiểm chứng Browser / Offline / Reopen BH-07 — sửa cuối theo ủy quyền bổ sung

- **Trạng thái:** **Chờ review lần sửa cuối theo ủy quyền bổ sung**. Người triển khai không tự ghi Đạt.
- **Nhánh:** `feat/bh07-browser-verification`
- **Base commit:** `b5517df1055ded3de86bdce49927188eab8e53d8`
- **Tested source commit:** `a62f509986f65592da3fb5bccebe7b7c246ff7b7`
- **Docs/evidence:** thư mục `docs/reviews/bh07/browser_evidence/`; commit bàn giao hiện hành được gửi kèm trong prompt review và xác định bằng `git log` (không thể tự ghi SHA của chính commit đang chứa file này).
- **Phạm vi thay đổi:** chỉ script kiểm chứng, fixture, tài liệu và bằng chứng. Không đổi `lib/`, unit test, migration/RPC, model/repository/provider/UI hay contract nghiệp vụ.
- **Môi trường:** Windows 11 IoT Enterprise LTSC 10.0.26100; Flutter 3.47.6 / Dart 3.13.5; Chrome 155.0.8059.85; Node v24.21.0; Python 3.12.7; Supabase local; PostgreSQL 17.11 trong `bh02-test-postgres`.

---

## 1. Phát hiện còn mở từ `review_eadb5c7.md` và phần đã bổ sung

| Mã | Nội dung reviewer yêu cầu | Phần đã bổ sung trong gói này | Trạng thái |
|:---|:---|:---|:---|
| **BR2** (P2) | Phải chứng minh UI thật hiện lỗi offline, không được im lặng không lỗi/không thành công; đúng 2 POST, cùng `request_id`, cùng toàn bộ payload; online hoàn tất; đúng 1 operation và 1 audit `SESSION_COMPLETED`. | `assertions.js` có `validateOfflineUiState` kiểm đúng câu lỗi `Đã xảy ra lỗi. Vui lòng thử lại sau.`, cấm success giả và yêu cầu route tài chính còn giữ. `validateCompleteRequests` lọc POST, bắt buộc đúng 2 request, so sánh `request_id`, session, version và toàn bộ payload. Runner polling lỗi thật trước khi retry, sau đó kiểm DB `completed|3`, 1 operation và 1 audit. | Chờ reviewer xác nhận |
| **BR3** (P2) | Aggregate phải đúng trường/số, không được nhận field lạ hoặc `—`; Cohost chỉ được thấy count, không lộ tài chính/contact/bank; History phải kiểm ID/empty/denied row và payload filter thật. | `validateManagerClipboard` kiểm chính xác `Tổng chi phí=200,000 VNĐ`, `Tổng phải thu=200,000 VNĐ`, `Đã thu=0 VNĐ`, `Còn phải thu=200,000 VNĐ`; từ chối field lạ và `—`. `validateCohostClipboard`/`validateCohostSummarySurface` chỉ cho phép header/place/time/count, cấm mọi nhãn tiền, số tiền, phone/bank/account/receiver/secret. History chụp request/response RPC thật, kiểm `p_club_id`, đúng tập ID `[10000000-0000-4000-8000-000000000099]`, row marker, empty state và dữ liệu Club B/treasury. Member kiểm `p_club_id=null`, response `[]`, `Chưa có buổi nào`, không row. | Chờ reviewer xác nhận |
| **BR5** (P2) | `--verify` phải read-only tuyệt đối; thiếu/thừa/hash sai/UTF-8 sai/BOM/CRLF/secret phải exit khác 0 và không sửa file; chỉ allowlist public anon JWT; reject JWT `service_role` đã decode; negative runner phải chạy predicate hiện tại, await đủ case, đủ số lượng, có positive control và fail khi gate manager thành `if (true)`. | `clean_and_manifest.py` tách `--verify` chỉ đọc; kiểm missing/extra/hash/UTF-8/BOM/CRLF; decode JWT và từ chối `service_role` ngoài allowlist; không tìm literal role trong base64. `run_negative_controls.js` có 27 case await tuần tự, marker check, đúng số case, positive control, JSON đầy đủ. `run_verifier_controls.py` có 9 control read-only. `run_mutant_controls.py` chạy bản sao không sửa (exit 0) và bản `if (true)` (exit 1), không sửa script thật. | Chờ reviewer xác nhận |

BR1 và ca SPA Owner→Cohost của BR4 vẫn giữ nguyên; 11/11 browser check vẫn PASS.

---

## 2. Kết quả bằng chứng local

| Lệnh / cổng | Kết quả | Exit | Bằng chứng |
|:---|:---|:---:|:---|
| `flutter build web` | Build thành công | 0 | `web_build.log` |
| `run_browser_verification.js` | **11/11 browser check PASS**, 12 ảnh khác hash; `is_dirty=false`; tested `a62f509` | 0 | `summary.json`, `browser_runner.log`, `browser_runner.console.log`, `screenshots/` |
| `flutter analyze` | Không issue | 0 | `analyze.log` |
| `flutter test` | **240 test + 1 skip** | 0 | `flutter_test.log` |
| `run_bh07_tests.py` | **23/23 DB PASS** | 0 | `bh07_db_runner.log`, `bh07_db_results.json` |
| `run_negative_controls.js` | **27/27 case** đúng kỳ vọng; 7 PASS + 20 FAIL; 0 HARNESS_ERROR | 0 | `negative_controls.json`, `negative_controls.log` |
| `run_verifier_controls.py` | **9/9 control**; baseline pass; mọi fault exit 1; `readonly=True` | 0 | `verifier_controls.log`, `verifier_controls.stdout.log`, `verifier_controls.json` |
| `run_mutant_controls.py` | Bản không sửa exit 0; bản `if (true)` exit 1; mutant PASS | 0 | `mutant_negative_control.log`, `mutant_negative_control.stdout.log`, `mutant_negative_control.json` |
| `clean_and_manifest.py --generate` | 33 entry; 0 secret; UTF-8 LF | 0 | `hashes.sha256` |
| `clean_and_manifest.py --verify` | **33/33 file**, 0 secret/JWT ngoài allowlist, read-only | 0 | `manifest_verify.log` |
| `supabase db reset` toàn bộ | Không chạy | **NOT RUN** | `exits.json` |

Contract chính đã quan sát trên UI/clipboard thật:

- Manager clipboard: `200,000 VNĐ`, `200,000 VNĐ`, `0 VNĐ`, `200,000 VNĐ`; không field lạ, không `—`.
- Cohost clipboard/UI: chỉ có header/place/time và dòng `👥 Có mặt: 1 · Vắng: 0 · Đã xác nhận: 2`; không tài chính, tiền, contact, bank, account, receiver.
- History Cohost: request `p_club_id=aaaaaaaa-1111-4111-8111-111111111111`; response đúng một ID `10000000-0000-4000-8000-000000000099`; một row.
- History Member: request `p_club_id=null`; response `[]`; `Chưa có buổi nào`; không row/Club B/treasury.
- Offline complete: lỗi UI thật hiện; retry đúng 2 POST cùng payload/`request_id`; DB `completed|3`; 1 operation, 1 audit `SESSION_COMPLETED`.

---

## 3. File kiểm chứng chính

- `scripts/bh07_browser/assertions.js`: predicate dùng chung cho browser thật và negative controls.
- `scripts/bh07_browser/run_browser_verification.js`: matrix UI thật, RPC capture, offline/history/clipboard gate.
- `scripts/bh07_browser/run_negative_controls.js`: 27 control dùng đúng predicate hiện tại.
- `scripts/bh07_browser/clean_and_manifest.py`: `--generate` và `--verify` read-only.
- `scripts/bh07_browser/run_verifier_controls.py`: 9 fault/read-only control.
- `scripts/bh07_browser/run_mutant_controls.py`: kiểm mutation gate manager thành `if (true)`.
- `scripts/bh07_browser/seed_setup.js`: fixture deterministic (không đổi app/DB contract).

---

## 4. Lịch sử review được giữ nguyên

Các kết luận trước không bị xóa hoặc đổi thành Đạt:

- [review_eadb5c7.md](review_eadb5c7.md): gói Chưa đạt vòng2/2 tại `51cb3b1`; BR1 và ca SPA BR4 đóng; BR2/BR3/BR5 P2 còn mở. Đây là các phát hiện gói sửa cuối này nhắm tới.
- [review_b00b580.md](review_b00b580.md): Chưa đạt vòng1/2.
- [review_c8a8e7f.md](review_c8a8e7f.md): Chưa đạt; runner/UI và bằng chứng chưa đủ.
- [review_cbcc46c_r2.md](review_cbcc46c_r2.md): Concurrency HTTP/Auth Đạt local vòng2/2; không bị thay đổi bởi gói này.

Toàn bộ lịch sử trạng thái chi tiết nằm ở `docs/STATUS_HISTORY.md`.

---

## 5. Rủi ro, giới hạn và NOT RUN

- Đây là kiểm chứng local trên Flutter Web/Chrome headless + Supabase local; không đại diện mobile, trình duyệt khác, staging hay production.
- Không chứng minh tích hợp ngân hàng/VietQR/webhook thật, backup/restore, rehearsal hoặc pilot.
- Không chạy `supabase db reset` toàn bộ; chỉ truncate/seed fixture qua `seed_setup.js`.
- Response trễ sau khi đổi actor vẫn **NOT RUN**.
- Không merge main, apply DB thật, deploy hoặc chạy pilot.
- Các kết luận P2 chỉ được đóng khi reviewer độc lập chạy lại và chấp nhận; người triển khai không tự kết luận Đạt.

## 6. Trọng tâm đề nghị reviewer kiểm

1. Chạy lại `run_negative_controls.js` và xác nhận 27/27 case, không chỉ đọc JSON.
2. Chạy `run_verifier_controls.py` và kiểm `readonly=True` cho mọi fault, đặc biệt fake `sb_secret`, JWT `service_role` đã decode, invalid UTF-8/BOM/CRLF.
3. Chạy `run_mutant_controls.py`; xác nhận bản `if (true)` thực sự exit 1 vì manager positive control fail.
4. Chạy browser matrix trên checkout sạch và đối chiếu `summary.json` (`is_dirty=false`, tested SHA), clipboard, history ID và offline POST/DB/audit.
5. Chạy `clean_and_manifest.py --verify`; xác nhận exit 0 và không sửa file.
