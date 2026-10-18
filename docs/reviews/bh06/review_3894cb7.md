# Review BH-06B vòng sửa 1 — 3894cb7

Ngày 18/10/2026 (Việt Nam). Tested commit **`3894cb782e6855e78f63df5dd29d49621c94cff2`** (checkout detached để kiểm đúng SHA được giao); base phần B `48d45d2`, base main `c35dd27`. Nhánh remote lúc nhận việc có commit docs mới hơn `4b0ecbb`, không đổi lib/test/supabase so với tested commit. Theo `docs/ai/REVIEWER.md` trên chore/ai-roles=`163bc45`, đọc diff main...3894cb7 và phần sửa sau `77d9df2`. Không sửa code triển khai/test tác giả.

## Phát hiện

### B2-R1 — P2: guard hết trang làm mất phản hồi refresh và giữ loading vô hạn

**Vị trí:** `lib/providers/finance_provider.dart:277–283`; tác động tại :304–305 và :326–332.

`fetchClubLedger` tăng `_ledgerSerial` trước khi kiểm nhánh `appending && !_ledgerHasMore` để return. Một yêu cầu load-more bị bỏ qua vì đã hết trang vì vậy vẫn vô hiệu serial của refresh đang bay, dù không phát RPC hoặc thực hiện finally riêng. Khi refresh trả về, cả cập nhật dữ liệu lẫn finally đều bị bỏ qua vì serial cũ, khiến `_isLoadingLedger=true` và dữ liệu cũ không được thay.

**Tái hiện độc lập:** tải trang 1/limit 2 nên hết dữ liệu; bắt đầu refresh cùng CLB nhưng trì hoãn response bằng Completer; gọi API public `fetchClubLedger('c1', limit:2, loadMore:true)`; trả response refresh mới. RPC chỉ được gọi hai lần như mong đợi, nhưng sau khi await cả hai future, `isLoadingLedger` vẫn true (kỳ vọng false) và refresh không cập nhật state. [Log probe](review_3894cb7_evidence/round1_probes.log), [mã probe](review_3894cb7_evidence/round1_probe.dart.txt).

Lỗi thuộc API public `fetchClubLedger(..., loadMore:true)`; wrapper `loadMoreLedger()` có guard loading riêng và không kích hoạt chuỗi này. Không suy diễn đã có UI lỗi vì C chưa triển khai. API public có tham số loadMore vẫn phải giữ đúng state khi bị gọi đồng thời với refresh.

**Cách sửa:** test tái hiện trước sửa; thực hiện guard không làm gì **trước** khi tăng serial hoặc thay state, hoặc đồng bộ guard loading cho đường loadMore trực tiếp. Yêu cầu bị bỏ qua không được huỷ phản hồi hợp lệ của yêu cầu đang chạy. Kiểm refresh nhận số dư/entries mới và tắt loading; giữ các ca hết trang/ngắn/rỗng/retry lỗi/đổi CLB. Không viết lại phần B hoặc sửa migration để chữa lỗi provider.

## Kiểm chứng độc lập

[Summary/hash và bằng chứng](review_3894cb7_evidence/summary.json). Flutter3.47.7/Dart3.13.5. Provider probes dùng FinanceProvider thật, repository fixture; không phải kiểm cấu trúc hoặc Text giả. Probe được đặt tạm dưới test/ rồi chuyển ra scratch; bản lưu .dart.txt tránh ảnh hưởng analyze. Bản probe cũ giữ nguyên từng byte/kỳ vọng từ review d00a121.

| Lệnh/nhóm | Kết quả |
|---|---|
| flutter analyze --no-pub | No issues found, exit 0 |
| flutter test --no-pub (test tác giả) | 166/166 PASS, exit 0 |
| Probe cũ B1/B2/control logout | 4/4 PASS, exit 0 |
| Probe mở rộng (giữ 4 ca cũ + race B2-R1) | 4 PASS / **1 FAIL**, exit 1 |
| Runner DB BH-06 | 84/84 PASS (CLEAN/LEGACY), exit 0 |

B1 và các tình huống phân trang ban đầu không còn tái hiện theo probe cũ; không lặp các lỗi đã được sửa. Phát hiện còn mở là tương tác serial với guard mới, không phải thay kỳ vọng của probe cũ. Không có P0/P1 mới trong phạm vi lượt này.

Migration và runner A không đổi; không chạy lại riêng BH-02..05 trong lượt này. 335 DB PASS ở review A là bằng chứng trước, không phải kết quả chạy mới của lượt B. Runner dùng PostgreSQL17 container local tắt mạng/Auth stub, fixture giả, không apply remote DB. Container test đang dừng khi bắt đầu; đã khởi động lại và đợi pg_isready trước lượt chạy cuối. JSON/probe tạm có thể làm metadata dirty nhưng nguồn triển khai không đổi ở tested SHA.

## Kết luận

**Chưa đạt phần B tại `3894cb7`** sau vòng sửa 1: còn B2-R1 P2. Cần sửa trong phạm vi trên và gửi SHA mới để review vòng 2; theo quy trình tối đa hai vòng, chưa phải lý do dừng trước khi dùng vòng còn lại. Không tự chuyển C/tích hợp, merge main hoặc deploy. A vẫn giữ kết luận Đạt của review A.

**NOT RUN:** repository/client↔PostgREST HTTP/JWT/Supabase Auth thật, UI C/thiết bị/browser e2e, apply staging/production, backup/restore, concurrency qua HTTP và bank/VietQR thực tế. Probe chỉ chứng minh lỗi state provider, không chứng minh UI hoặc giao dịch thực tế. Giữ review và bằng chứng cũ làm lịch sử.
