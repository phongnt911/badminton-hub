# BH-06B — ghi chú sửa theo review vòng 1 (B1/B2)

Ngày 16/10/2026 (Việt Nam). Người triển khai sửa theo [review_d00a121.md](review_d00a121.md) (kết luận **Chưa đạt** với B1/B2 mức P2) và mục "Sửa theo review" trong `docs/ai/IMPLEMENTER.md`. Chủ dự án giao rõ sửa cả hai. Nhánh `feat/bh06b-data`, dependency A `48d45d2` (Đạt tại `706bd73`), base main `c35dd27`.

## Phát hiện và cách sửa

### B1 — cache hướng dẫn thanh toán vẫn "current/canPay" sau khi server báo stale

- Trước sửa: `fetchPaymentInstructions` khi lỗi chỉ ghi `instructionsErrorMessage`, vẫn giữ object cũ với `billingState=current`, `canPay=true`, bank/reference/outstanding cũ → vẫn quảng bá một chỉ dẫn có thể thanh toán dù revision không còn hợp lệ.
- Sửa (`lib/providers/finance_provider.dart`, nhánh catch): khi làm mới lỗi trong cùng phạm vi (session/player), **vô hiệu cache** `_instructions = null` và giữ thông điệp lỗi. Áp dụng cho `BILLING_STALE`/`BILLING_NOT_FINALIZED`/mất quyền và cả lỗi khác — an toàn vì không bao giờ giữ chỉ dẫn có thể trả sau một lần làm mới lỗi. Không hạ số phải thu về 0 và không biến lỗi thành "đã trả".

### B2 — phân trang ledger không kết thúc và load-more bỏ qua hết dữ liệu

- Trước sửa: `hasMoreLedger` so **tổng** entries đã nối với `limit` (trang 1 đầy + trang 2 ngắn vẫn `true`); `loadMoreLedger` không kiểm hết trang nên vẫn phát RPC.
- Sửa (`lib/providers/finance_provider.dart`): thêm `_ledgerHasMore` suy từ **trang vừa nhận** (`page.entries.length >= page.limit` ⇒ còn trang, ngắn hơn ⇒ hết); getter `hasMoreLedger = _ledger != null && _ledgerHasMore`; nhánh nối của `fetchClubLedger` và `loadMoreLedger()` **không phát RPC khi đã hết**; lỗi mạng **không** đánh dấu hết trang (giữ nguyên trạng thái cũ); reset khi đổi CLB/`clearAll`. Giữ đúng `offset = entries.length`, không mất entries/số dư khi lỗi.

## Test và bằng chứng

- Commit tách test-first: `3338566` (`3338566ec788aaa290a2fcd9fd93233ed5aefd88`) — thêm 3 test tái hiện, **FAIL** trước sửa (xác nhận bằng chạy thật); `3894cb7` (`3894cb782e6855e78f63df5dd29d49621c94cff2`) — fix + chỉnh test `loadMoreLedger` cũ (test cũ mã hoá hành vi sai: trang đầu ngắn vẫn nối).
- Trên cây `3894cb7` (sạch): `flutter analyze` **0 issue**; `flutter test` **166/166 PASS** (= 163 trước + 3 test tái hiện).
- Phát lại **probe độc lập của reviewer** (B1 + 2 tình huống B2 + control logout) trên bản sửa: **4/4 PASS** (trước đó 3 FAIL / 1 control PASS). Probe chạy tạm ở `test/tmp_bh06b_probe_test.dart` rồi xoá, không để lại trong repo.
- Không đổi DB/migration/RPC của A ⇒ runner DB BH-06 **không chạy lại**; baseline DB 335/335 của A giữ nguyên. Không sửa/bỏ test BH-02..05.

## Trạng thái và giới hạn

- Trạng thái: **Chờ review vòng 1**; người triển khai không tự ghi Đạt.
- NOT RUN: HTTP/PostgREST/JWT/Supabase Auth thật, repository↔RPC thật, UI phần C/thiết bị/browser e2e, apply staging/production, backup/restore, concurrency qua HTTP, bank/VietQR thực tế. Probe chỉ chứng minh hành vi state/phân trang provider.
