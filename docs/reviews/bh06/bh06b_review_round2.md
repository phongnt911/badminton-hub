# BH-06B — ghi chú sửa theo review vòng 2 (B2-R1)

Ngày 18/10/2026 (Việt Nam). Người triển khai sửa theo [review_3894cb7.md](review_3894cb7.md) (kết luận **Chưa đạt phần B**, chỉ còn **B2-R1 mức P2**) và mục "Sửa theo review" trong `docs/ai/IMPLEMENTER.md`. Đây là **vòng sửa thứ 2** (tối đa hai vòng theo quy trình). Nhánh `feat/bh06b-data`, rebase trên commit review `584ebf1`; dependency A `48d45d2` (Đạt tại `706bd73`), base main `c35dd27`.

## Phát hiện và cách sửa

### B2-R1 — load-more bị bỏ qua vì đã hết trang vẫn huỷ refresh đang bay

- Vị trí: `lib/providers/finance_provider.dart` trong `fetchClubLedger`.
- Trước sửa: `_ledgerSerial` được tăng **trước** guard `if (appending && !_ledgerHasMore) return;`. Một `fetchClubLedger(..., loadMore: true)` bị bỏ qua (đã hết trang) vì vậy vẫn làm serial của request đang bay (refresh cùng CLB) trở nên cũ. Khi refresh trả về, cả nhánh cập nhật dữ liệu lẫn `finally` đều bị bỏ qua do serial mismatch ⇒ dữ liệu mới không được ghi và `_isLoadingLedger` kẹt `true`.
- Sửa (tối thiểu): tính `previous/switching/appending` và **thực hiện guard trước** `++_ledgerSerial`, không thay state, không phát RPC khi bị bỏ qua. Yêu cầu bị bỏ qua không còn huỷ phản hồi hợp lệ của request đang chạy. Không viết lại phần B, không sửa migration/RPC của A.

## Test và bằng chứng

- Commit tách test-first: `83b6d494eaa8954960400bd16eb6655ad02185cc` — thêm test `B2-R1: loadMore bị bỏ qua không được huỷ refresh đang bay`, **FAIL** trước sửa (xác nhận bằng chạy thật: `Expected: false / Actual: <true>`); `58d03ca660c0edc4968a92ea4c79ad2307c41c3f` — fix.
- Trên cây `58d03ca` (sạch): `flutter analyze` **0 issue**; `flutter test` **167/167 PASS** (= 166 vòng 1 + 1 test tái hiện B2-R1).
- Phát lại **nguyên văn probe vòng 1 của reviewer** (B1 + 2 ca B2 + control logout + race B2-R1): **5/5 PASS** (trước đó 4 PASS / 1 FAIL). Probe chạy tạm dưới `test/` rồi xoá, không để lại trong repo.
- Không đổi DB/migration/RPC của A ⇒ runner DB BH-06 **không chạy lại**; baseline DB 84/84 (và 335/335 của A) giữ nguyên. Không sửa/bỏ test BH-02..05, không chỉnh kỳ vọng probe của reviewer.

## Trạng thái và giới hạn

- Trạng thái: **Chờ review vòng 2**; người triển khai không tự ghi Đạt. Nếu vẫn còn P0/P1 sau vòng này, theo quy trình sẽ dừng và báo chủ dự án.
- NOT RUN: HTTP/PostgREST/JWT/Supabase Auth thật, repository↔RPC thật, UI phần C/thiết bị/browser e2e, apply staging/production, backup/restore, concurrency qua HTTP, bank/VietQR thực tế. Probe chỉ chứng minh hành vi state/phân trang provider với repository fixture.
