# Phiếu việc: cập nhật tài liệu sau BH-05 (chỉ tài liệu)

Vai trò: **người cập nhật tài liệu**. Chỉ sửa file Markdown. Không sửa `lib/`, `test/`, `supabase/`, `scripts/`, runner Python, JSON/log bằng chứng và các review hiện có trong `docs/reviews/`. Không merge `main`, không apply DB, không tự ghi "Done" hay "production-ready".

## 0. Chuẩn bị (dừng và báo nếu bước nào lệch)

1. `git fetch origin && git switch main && git pull --ff-only origin main`. Working tree phải sạch, nếu không thì dừng.
2. Ghi lại HEAD. Kiểm tra drift: bản nháp trong `doc-update-pack/drafts/` được soạn dựa trên các blob sau, nên `git rev-parse origin/main:<file>` phải khớp:

| File | Blob SHA |
|---|---|
| `README.md` | `614498e09edbfb879fe0e0b697bfc972cb603874` |
| `docs/00_START_HERE.md` | `4108bd702891fda8cdcc570941d54903fd891f6f` |
| `docs/22_BH05_HANDOFF.md` | `ff3276edda1c745c0be30fadc8fc5577b7f85a5a` |
| `docs/09_IMPLEMENTATION_PLAN.md` | `d795508d0ae9c338d61f5cb596489aeb4ed89794` |

   Nếu file nào lệch: dừng việc với file đó, so diff với bản nháp, báo lại, không đè.
3. Tạo nhánh `docs/audit-after-bh05` từ `main`.
4. Thư mục `doc-update-pack/` chỉ để tham chiếu: thêm vào `.git/info/exclude`, **không commit**.
5. Giữ nguyên kiểu xuống dòng của từng file (`git ls-files --eol`). Không để diff đổi toàn bộ dòng vì CRLF/LF.

## 1. Sự thật được phép ghi (kiểm lại với file bằng chứng trước khi ghi)

- `docs/reviews/bh05/review_d769531.md`: **Đạt tích hợp BH-05 A+B+C** tại `d769531`, không có phát hiện P0/P1/P2 trong phạm vi kiểm chứng.
- `docs/reviews/bh05/review_main_3a34883.md` và `main_3a34883/summary.json`: hồi quy trên `main` tại `3a34883`: analyze sạch, **137/137 Flutter**, **251/251 DB** (33 + 14 + 48 + 22 + 44 + 90).
- NOT RUN (giữ nguyên, không xoá): PostgREST HTTP/JWT thật, thiết bị/browser e2e, apply staging/production, backup/restore, concurrency qua HTTP.
- Quy tắc: mọi con số phải khớp file bằng chứng. Không suy diễn. Không xoá nhật ký cũ; chỗ nào lỗi thời thì **thêm** dòng "hiện hành" kèm ngày, giữ nguyên bản cũ làm lịch sử.

## Phần A: ĐÃ ĐƯỢC CHỦ DỰ ÁN DUYỆT, thực hiện

| # | Việc | Nguồn |
|---|---|---|
| A1 | Cập nhật `README.md` | `doc-update-pack/drafts/README.md` |
| A2 | Cập nhật `docs/00_START_HERE.md` | `doc-update-pack/drafts/docs/00_START_HERE.md` |
| A3 | Tạo mới `docs/STATUS_HISTORY.md` | `doc-update-pack/drafts/docs/STATUS_HISTORY.md` |

Cách làm: so bản nháp với file hiện có bằng `git diff --no-index`, chỉ áp dụng phần khác biệt đã mô tả dưới đây, đối chiếu từng con số với mục 1.

- A1: thêm bảng "Trạng thái hiện tại" BH-01 đến BH-05, sửa các câu lỗi thời ("Code hiện tại là demo", "tiếp theo là BH-03"), thay các bullet kết quả cũ trong mục QA bằng con trỏ tới bảng, thêm dòng BH-05 cuối file.
- A2: thay dòng trạng thái đầu file và khối "Trạng thái hiện tại", cập nhật bảng "Hiện trạng và đích", thay "Prompt bắt đầu gợi ý", chuyển 8 mục "Cập nhật / Ưu tiên / Mới nhất" sang A3 (giữ lại ở `00` mục "Tham khảo sản phẩm: Vmito và Vụt").
- A3: 8 mục chuyển từ `docs/00` phải **giống hệt nguyên văn** (kiểm bằng diff so với `git show origin/main:docs/00_START_HERE.md`); chỉ mục cuối là mới.
- Nếu bản nháp xung đột với sự thật trong repo thì **sự thật thắng**; ghi chú lại trong báo cáo cuối.
- Kiểm tra mọi link tương đối trong 3 file đều trỏ tới file có thật (viết script nhỏ, không commit).

## Phần B: ĐỀ XUẤT, CHỈ làm mục được chủ dự án tick `[x]`

Mục để `[ ]` thì **không làm**. Không tự tick.

- [x] **B1** `docs/22`: ngay dưới H1, thêm dòng in đậm: "Trạng thái hiện hành (16/10/2026): Đạt tích hợp A+B+C tại `d769531` ([review_d769531.md](reviews/bh05/review_d769531.md)); hồi quy main tại `3a34883` đạt 137 Flutter + 251 DB ([review_main_3a34883.md](reviews/bh05/review_main_3a34883.md)). Chưa cho phép deploy production. Đoạn trạng thái ngay dưới đây là snapshot trước review, giữ làm lịch sử." Không sửa đoạn cũ.
- [x] **B2** `docs/22` §2, câu mở đầu: đổi "mỗi phần một nhánh và **chờ review**" thành "mỗi phần một nhánh, qua review độc lập (A/B/C đều Đạt, xem bảng dưới)".
- [x] **B3** `docs/22` §8: thay bullet "Chưa nghiệm thu **chính bản tích hợp** bởi reviewer…" bằng "Nghiệm thu bản tích hợp: **Đạt** tại `d769531` ([review_d769531.md](reviews/bh05/review_d769531.md)); snapshot Chưa đạt/chờ review lại trước đó là lịch sử (review_c7ed6d5)."
- [x] **B4** `docs/22` §9, mục 1: đổi thành "1. (Đã xong 16/10/2026) Reviewer độc lập kết luận lại nhánh tích hợp: **Đạt** tại `d769531`."
- [x] **B5** `docs/22`: đổi tiêu đề "Kết luận review tích hợp mới nhất — c7ed6d5" thành "Kết luận review tích hợp — c7ed6d5 (đã được thay thế bởi d769531)".
- [x] **B6** `docs/09`, dòng "Trạng thái khởi đầu…": giữ nguyên, thêm sau đó: "(Snapshot 14/10/2026, giữ làm lịch sử.) **Hiện hành:** BH-01 đến BH-05 đã triển khai ở mức local/staging; BH-05 đạt review tích hợp (`d769531`) và hồi quy main (`3a34883`); BH-06 trở đi chưa làm; chưa apply production."
- [x] **B7** `docs/09`, bảng R1–R7, cột Trạng thái: **nối thêm** "Hiện hành 16/10:" sau chữ cũ (không thay chữ cũ).
  - R2: "đã triển khai local/staging ở BH-05 (RPC nguyên tử), chưa đóng ở production".
  - R3: "đã triển khai local/staging ở BH-02/03, chưa đóng ở production".
  - R7: "đã triển khai local/staging ở BH-05 (issue/revoke/accept), chưa đóng ở production".
  - R5 và R6: chỉ sửa nếu `docs/20_BH04_HANDOFF.md` và test BH-04/05 xác nhận; nếu không, ghi "chưa xác minh". R6 ghi rõ QR thật thuộc BH-06, chưa làm.
  - R1 và R4: không đổi.
- [x] **B8** `docs/09`: (a) bảng BH-04 thiếu dòng tiêu đề (`| Ngày | Ticket | Trạng thái | Bằng chứng |` + dòng ngăn cách), thêm vào; (b) thiếu dòng trống trước heading thứ hai "BH-05 — … 15–16/10/2026", thêm dòng trống. Chỉ sửa định dạng.
- [x] **B9** `docs/09`: ngay sau mục "Thứ tự và phụ thuộc", thêm mục "## Trạng thái hiện hành" gồm bảng BH-01 đến BH-05 giống `drafts/README.md`, kèm một dòng "BH-06 đến BH-09: chưa triển khai". Không sửa nhật ký phía dưới.

## Phần C: BÁO CÁO, KHÔNG SỬA tài liệu nào

Viết **một file mới** `docs/reviews/bh05/doc_audit_after_bh05.md` (không sửa review nào có sẵn), gồm:

1. **C1**: đối chiếu `docs/08_DOMAIN_CONTRACTS.md` §12 với 4 migration BH-05 (`20261015170500`, `20261016090000`, `20261016091000`, `20261016100000`): bảng 10 RPC gồm tên hàm, tham số, kiểu trả về, `GRANT`/`REVOKE`, mã lỗi. Mỗi chỗ lệch ghi: tài liệu nói gì, migration thực tế là gì, đề xuất sửa phía nào.
2. **C2**: kiểm tra các tuyên bố trong `docs/22` §3 và §7: SHA256 từng migration (lưu ý ghi chú CRLF), tên file tồn tại, số test khớp `summary.json`.
3. **C3**: quét link tương đối hỏng trong toàn bộ `docs/*.md` và `README.md`.

Với mỗi phát hiện: file, vị trí, bằng chứng, **ảnh hưởng tới code/test nếu có**. Chỉ báo cáo, chờ chủ dự án quyết.

## Commit và báo cáo

- Mỗi phần một commit riêng (A, các mục B đã tick, C). Thông điệp bằng tiếng Việt, có tiền tố `docs:`.
- Trước khi push: `git diff --stat origin/main...HEAD` chỉ được thấy file `.md`. Nếu thấy file khác thì dừng.
- Push nhánh `docs/audit-after-bh05`. **Không merge, không push `main`.**
- Báo cáo cuối (tiếng Việt, ngắn): mục nào đã làm, mục nào bỏ qua vì chưa tick, chỗ nào bản nháp xung đột với sự thật và cách xử lý, kết quả kiểm tra link, danh sách NOT RUN, xác nhận không đụng code/test/migration/bằng chứng.
