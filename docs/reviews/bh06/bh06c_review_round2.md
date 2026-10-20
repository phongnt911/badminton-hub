# BH-06C — ghi chú sửa theo review vòng 2

Ngày 20/10/2026. Nhánh `feat/bh06c-ui`. Phạm vi: **C3 (P2)** và ca còn thiếu mà review ghi NOT RUN, theo chỉ định của chủ dự án (“sửa P2 và các phần khác được chỉ ra”). Không đổi migration/RPC của A, không viết lại B, không merge `main`, không thêm dependency. Đây là vòng sửa **2/2**.

## 1. Test tái hiện trước (test-first)

Commit `75aa95b` — `test/screens/session_finance_screen_test.dart`:

- `C2: trả thêm sau refinalize tạo intent mới với số tiền mới` (dòng 360): instructions gọi lần 1 outstanding 100.000; sau khi gửi, gọi lần 2 mô phỏng chốt lại phí (due 150.000, đã trả 100.000, còn 50.000). Kỳ vọng hai intent hai request ID khác nhau, số tiền 100.000 rồi 50.000, `reference: null`. Test này **PASS sẵn** trên code `8e3cd83` vì C2 đã sửa ở vòng 1; nó bổ sung bằng chứng cho ca NOT RUN, không phải test đỏ.
- `C3: không suy khoản nợ từ một trang payment thiếu lịch sử` (dòng 427): đúng fixture reviewer (50 payment = đầy trang, người `paid-player` đã trả đủ theo RPC). **FAIL** trước khi sửa: UI hiện `Còn phải thu: 100,000 VNĐ`.
- `C3: prefill thu tiền mặt lấy outstanding từ RPC` (dòng 486): trang chỉ có 40.000 của `p1`, nhưng server biết đã trả 70.000, còn 30.000. **FAIL** trước khi sửa: hộp thoại prefill 60.000 (phép trừ trên trang).

Lệnh: `flutter test test/screens/session_finance_screen_test.dart` → `+9 -2` (2 FAIL đúng C3), log đã ghi trong phiên.

## 2. Sửa

Commit `5174e9d` — `lib/screens/session_finance_screen.dart`:

- dòng 42: thêm `_loadingOutstanding` để khoá nút thu tiền mặt khi đang đọc outstanding, tránh mở hai luồng.
- dòng 268–304: `_recordCash(String playerId)` **luôn** gọi `FinanceProvider.fetchPaymentInstructions(sessionId, playerId)` trước khi mở hộp thoại; lỗi đọc giữ nguyên lỗi và không mở hộp thoại; `outstandingVnd <= 0` thì báo “Người chơi đã trả đủ.” và không prefill; prefill bằng `outstandingVnd` của RPC.
- dòng 590–625: chỉ suy “Còn phải thu” theo người khi `finance.limit > 0 && finance.payments.length < finance.limit` (biết chắc đã có đủ lịch sử). Trang bị cắt thì hiện `Phải trả theo phí: <amountDueVnd> VNĐ` (revision hiện hành từ server) và không khẳng định nợ.

Không đổi model/repository/provider của B; chỉ dùng API sẵn có. `get_payment_instructions` cho phép vai trò finance đọc instructions của người khác trong buổi (ACL đã có ở migration A).

## 3. Bằng chứng

Trên cây `5174e9d` (sạch):

- `flutter analyze` → **No issues found!** (0 issue).
- `flutter test` → **186/186 PASS** (183 trước + 3 test mới).
- Không đổi DB/migration → runner DB BH-06 **không chạy lại**.

## 4. Probe C3 của reviewer

Probe `review_af31e7b_evidence/widget_probe.dart.txt` dòng 355–356 có hai kỳ vọng mâu thuẫn trong cùng một trạng thái:

```dart
expect(find.text('Còn phải thu: 100,000 VNĐ'), findsOneWidget); // observed incorrect amount
expect(find.text('Còn phải thu: 0 VNĐ'), findsOneWidget);
```

Không trạng thái nào thoả cả hai, nên probe **nguyên văn không thể PASS** kể cả sau khi sửa đúng. Hướng sửa bám đúng hai lựa chọn reviewer nêu (“lấy outstanding từ nguồn tổng hợp đầy đủ phía server, **hoặc** chỉ hiển thị/prefill khi đã có dữ liệu đầy đủ”): khi trang bị cắt, UI không hiển thị con số nợ suy diễn; prefill thu tiền mặt lấy từ RPC. Test hồi quy của tác giả kiểm đúng các hành vi này; đề nghị reviewer dùng test đó (hoặc probe đã sửa kỳ vọng) thay cho probe mâu thuẫn.

## 5. Cập nhật quy trình

Chủ dự án yêu cầu người triển khai sửa **toàn bộ P** trong review:

- `AGENTS.md` (commit cùng lượt trên nhánh này): “sửa toàn bộ phát hiện P0/P1/P2 được nêu (kể cả P2)”.
- `docs/ai/IMPLEMENTER.md` + `AGENTS.md` trên nhánh `chore/ai-roles`, commit `07b31d4` (đã push).

## 6. NOT RUN

- Refinalize ở mức RPC/DB: chỉ kiểm ở UI/provider bằng instructions thay đổi; không chạy lại runner DB.
- HTTP/PostgREST/JWT/Auth thật; thiết bị/browser e2e; ảnh VietQR/bank thật; staging/production; backup/restore; concurrency HTTP.

## 7. Trạng thái

**Chờ review vòng 2**. Người triển khai không tự ghi Đạt; chỉ chuyển sang tích hợp sau khi reviewer kết luận Đạt C.
