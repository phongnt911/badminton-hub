# Review BH-06B — d00a121

Ngày 16/10/2026 (Việt Nam). Tested HEAD `d00a121f655fc11f560ac11a2843542ca98f0fd1`, code/test `a794a91`, dependency A `48d45d2` đã Đạt tại `706bd73`, base main `c35dd27`. Theo `docs/ai/REVIEWER.md` tại `chore/ai-roles=163bc45`. Đọc diff origin/main...HEAD, tách phần B bằng diff 48d45d2..HEAD; không review lại kết luận A từ số test B, không sửa code triển khai/test tác giả.

## Phát hiện

### B1 — P2: lỗi BILLING_STALE vẫn để cache QR ở trạng thái current/canPay

**Vị trí:** `lib/providers/finance_provider.dart:155–160`; cache chỉ được xoá khi đổi session/player ở dòng 134–139.

Sau một lần tải hướng dẫn hợp lệ, cùng session/player được tải lại khi server đã báo BILLING_STALE. Catch chỉ ghi instructionsErrorMessage; paymentInstructions vẫn trả object cũ với billingState=current, canPay=true, bank/reference/outstanding cũ, và isLoadingInstructions đã false. State dành cho C vì vậy vẫn quảng bá một chỉ dẫn có thể thanh toán dù server vừa xác nhận revision không còn hợp lệ. Điều này khác giữ công nợ cũ có nhãn lịch sử: object hiện tại không có nhãn stale hoặc bị vô hiệu. Không kết luận đã render QR hoặc chuyển tiền thật; C chưa triển khai.

**Tái hiện:** probe B1 tải current/canPay=true, lần hai repository ném PostgrestException BILLING_STALE; lỗi được map nhưng cache không bị vô hiệu, assertion không còn paymentInstructions sử dụng được FAIL. [Log probe](review_d00a121_evidence/probes.log), [mã probe](review_d00a121_evidence/provider_probe.dart.txt).

**Cách sửa:** thêm test trước sửa; khi nhận stale/not_finalized hoặc mất quyền, vô hiệu chỉ dẫn thanh toán hiện hành (đơn giản nhất xoá cache, giữ lỗi), hoặc cung cấp state không thể dùng cho QR và gắn nhãn rõ nếu cần giữ snapshot lịch sử. Kiểm loading→error→retry current và đổi actor/session; không hạ số phải thu về 0 hoặc biến lỗi thành “đã trả”. Không dựa vào UI phần C để đoán rằng object current thực ra đã stale.

### B2 — P2: trạng thái hết trang ledger tính theo tổng tích luỹ và load-more bỏ qua hết dữ liệu

**Vị trí:** `lib/providers/finance_provider.dart:252`, :297–305, :325–328.

hasMoreLedger so tổng entries đã nối với limit thay vì số entry của trang vừa nhận. Khi trang 1 có 2/2 entry, trang 2 chỉ còn 1/2, tổng 3>=2 nên hasMoreLedger vẫn true; những trang rỗng tiếp theo cũng không kết thúc phân trang. Ngoài ra loadMoreLedger không kiểm hasMoreLedger: ngay khi trang đầu chỉ 1/2 (getter false) vẫn phát RPC mới nếu được gọi. UI tải thêm/infinite scroll sẽ tiếp tục gọi các trang đã hết dữ liệu.

**Tái hiện:** probe trang 2+1 kỳ vọng hasMore=false FAIL; probe trang đầu ngắn rồi gọi loadMore kỳ vọng chỉ một RPC nhưng thực tế hai RPC, FAIL. [Log](review_d00a121_evidence/probes.log).

**Cách sửa:** thêm test trang đầy→ngắn, đầy→rỗng, retry lỗi và đổi CLB/refresh; lưu tình trạng còn trang từ response trang cuối, reset khi đổi scope/tải lại; chặn loadMore khi đã hết dữ liệu. Giữ offset đúng, không đánh mất entries/số dư khi lỗi mạng và không đánh dấu hết trang chỉ do lỗi.

## Kiểm chứng độc lập

[Summary/hash/bằng chứng](review_d00a121_evidence/summary.json): Flutter3.47.7/Dart3.13.5, PostgreSQL17 local tắt mạng/Auth stub cho runner DB. Provider probe gọi FinanceProvider thật với repository stub, không phải widget Text giả hoặc kiểm chuỗi tên method.

| Lệnh/nhóm | Kết quả reviewer tự chạy |
|---|---|
| flutter analyze --no-pub | No issues found, exit 0 |
| flutter test --no-pub (test tác giả) | 163/163 PASS, exit 0 |
| python docs/reviews/bh06/run_bh06_tests.py | 84/84 PASS, clean + legacy, exit 0 |
| Probe độc lập provider | **3 FAIL** (B1 + 2 tình huống B2), 1 control logout PASS, exit 1 |

Không thay migration/runner A so với dependency 48d45d2; 335 DB PASS của [review A](review_706bd73.md) là bằng chứng lượt trước, không gọi đó là số DB tự chạy trong lượt B. Chưa chạy lại riêng các runner BH-02..05 vì B không đổi DB. Probe đặt tạm ở test/review_bh06b_d00a121_probe_test.dart rồi chuyển ra scratch; bản lưu .dart.txt tránh bị analyzer coi là source ứng dụng. Để tái chạy, chép bản probe về đúng đường dẫn test trên rồi dùng flutter test --no-pub cho file đó và chuyển ra sau chạy. JSON runner sinh tạm trong repo; metadata dirty có thể phản ánh probe/bằng chứng tạm, nguồn/migration tác giả không đổi suốt kiểm chứng.

## Kết luận

**Chưa đạt phần B** tại `d00a121`: còn B1/B2 mức P2 cần sửa và gửi lại SHA để review. Giữ Chờ review của báo cáo người triển khai làm snapshot trước kết luận. A vẫn Đạt trong phạm vi review A; không chuyển C, không nghiệm thu toàn BH-06, không merge main hoặc deploy.

**NOT RUN:** client/repository↔PostgREST HTTP/JWT/Supabase Auth thật; UI phần C, thiết bị/browser e2e, apply staging/production, backup/restore, concurrency qua HTTP và bank/VietQR thực tế. Probe chỉ chứng minh lỗi state/phân trang provider, không chứng minh giao dịch ngân hàng hoặc UI e2e. Không sửa code triển khai trong lượt review.
