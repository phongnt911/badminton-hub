# Tự review BH-07 Browser / Offline / Reopen — a6d58af

Ngày23/10/2026. **Codex tự review mã do Codex sửa theo yêu cầu trực tiếp của chủ dự án; KHÔNG phải review độc lập.**

- Base: `1fc7e2eb171acd6c7afbc16e9f1053f9b3cb21c3`.
- Tested source: `a6d58aff3f1726484146a6c89aa7d559bb684d6d`.
- Docs/evidence đối chiếu: `994ebfeb98c7c76815c2b8e0e6519fbe735ab1af`.
- **Kết luận: Đạt trong phạm vi gói kiểm chứng Browser / Offline / Reopen local và ba lỗi BR3 được giao.** Không nghiệm thu toàn BH-07/production/pilot.

## Phát hiện P0/P1/P2

Không có phát hiện còn mở trong phạm vi diff và các ca tái hiện được giao. Đóng BR3-1/BR3-2/BR3-3 **theo tự review**, giữ giới hạn không độc lập.

| Mục | Đối chiếu mã và ca tái hiện |
|---|---|
| BR3-1 | `assertions.js` whitelist metadata + bốn dòng tài chính, kiểm số lần/số dòng; field `Hoàn tiền:999 VNĐ` bị loại; positive Manager aggregate200k/200k/0/200k còn PASS. |
| BR3-2 | Guard tiền dùng ranh giới Unicode; VNĐ/đ/VND bị loại ở UI/clipboard Cohost; ngày/giờ/count hợp lệ còn PASS. |
| BR3-3 | CDP thu status, parser chỉ nhận200 + JSON hợp lệ, validator bắt buộc array/row ID. Body FORBIDDEN/null/JSON lỗi/403[] không thành empty. History surface dùng guard privacy và tiền; STK bị loại, positive[] còn PASS. |

Đã rà cả caller lịch sử Cohost/Member và đường status từ CDP tới parser, không chỉ đọc predicate. BR1/BR2/BR4/BR5 và mutation/submitting/retry gate không đổi; source chỉ sửa3 script kiểm chứng, diff `lib/ test/ supabase/` rỗng.

## Bằng chứng

Lượt **tự review này chạy lại** trên docs checkout994ebfe (code/hash giống tested source):

- Probe reviewer cũ:9/9 đúng kỳ vọng,4 positive PASS +5 negative FAIL; không đổi kỳ vọng/input, chỉ đổi output path.
- Negative controls:41/41,0 HARNESS_ERROR.
- Verifier controls trên copy gói bằng chứng mới:9/9; mọi fault readonly.
- Mutant: bản gốc exit0; gate `if(true)` exit1.
- Manifest gói tự kiểm:52/52 PASS;53 file gồm manifest không đổi qua --verify.
- Source hash khớp; app/backend không đổi.

[Bằng chứng phát lại](self_review_a6d58af_evidence/).

**Kế thừa lần tự kiểm ngay trước trên cùng source a6d58af, không chạy lại trong lượt chốt này:** analyze0 issue;240 Flutter PASS+1 skip;23 DB PASS;Web build PASS;11/11 Chromium local;12 ảnh khác hash. Trace2 POST cùng request_id/full payload, DBcompleted v3/1 operation/1 audit/attendance present/expense200000. Những kết quả này do chính Codex chạy trong lượt triển khai và đã công bố tại [bàn giao](browser_codex_fix_handoff.md), [bằng chứng](browser_codex_fix_evidence/); không đổi tên thành kết quả review độc lập.

Không sửa code trong lượt tự review; báo cáo và trạng thái mới bổ sung vào lịch sử, không đổi manifest/log/summary của các lượt trước.

## NOT RUN

- Review độc lập bởi người/AI không tham gia sửa mã.
- Mobile/thiết bị thật/browser khác, Windows Chrome155; lần tự kiểm dùng Linux Chromium154/Flutter3.47.7.
- Response owner trả trễ sau đổi actor; same-SPA happy path không chứng minh ca này.
- Ngân hàng/VietQR/webhook thật; staging/production; backup/restore.
- Rehearsal/pilot và nghiệm thu toàn BH-07; full Supabase db reset.
- 335 ca DB hồi quy BH-02..06 không chạy lại vì không đổi DB/backend.

**Đạt — tự review local, không độc lập.** Giữ A/B/C/D và HTTP/Auth/concurrency local trước; không merge main/apply DB thật/deploy/chuyển pilot.
