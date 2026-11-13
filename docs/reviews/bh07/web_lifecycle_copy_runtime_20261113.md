# V2 Web lifecycle, copy và QR fallback — 13/11/2026

**Đạt local trong phạm vi đã đo dưới đây; toàn V2/BH-07/V8 chưa nghiệm thu.** Base `835ed72` trên `feat/bh07-completion-local`, working tree có tooling/tài liệu mới. Anti CLI `gemini-4-hydrogen-high`, `--print-timeout 0` triển khai test; Codex review và chạy browser/DB. Không sửa app/backend/migration. Source/control/artifact review không được nhận là runtime QA độc lập.

## Kết quả mới

| Phạm vi | Edge 157 headless | Playwright Firefox 156 headless |
|---|---|---|
| Owner start → điểm danh hai người → chốt phí | PASS | PASS |
| Complete offline phải hiện lỗi thật, chưa ghi completion vào DB | PASS | PASS |
| Retry online cùng request ID và toàn bộ payload, cùng document | PASS, POST 200 | PASS, POST 200 |
| Tổng kết sau complete | PASS: số lượt 2/0/2; chi phí/phải thu/đã thu/còn thu 200000/200000/0/200000 | PASS cùng kỳ vọng |
| Cohost UI count-only | PASS | PASS |
| Cohost sao chép tổng kết và đọc clipboard thật | PASS: đúng 2/0/2, không tài chính/bank/contact/tên người chơi | NOT RUN: Playwright không hỗ trợ grant clipboard-read/write trên browser này |
| Guest A còn nợ: ép lỗi ảnh QR, thông tin chuyển khoản thủ công khớp DB | PASS | PASS |
| Copy số tài khoản và nội dung chuyển khoản, đối chiếu giá trị kỳ vọng DB | PASS | NOT RUN vì quyền clipboard không hỗ trợ |

Luồng ghi dùng **fixture UUID riêng từng lượt**, không reset/ghi đè session `0099` kế thừa. Trước retry, DB bắt buộc `in_progress/version2`, hai người present, một revision active/current, hai charge **100000/100000**, payments0, **operation/audit của đúng request đã bắt = 0**. Sau retry, DB bắt buộc `completed/version3`, đúng request đó có **1 operation và 1 SESSION_COMPLETED audit**, không đổi charge/payment; timeOrigin của hai pha trùng. Cả hai browser chạy đúng source lifecycle cuối r3, với request/payload khác nhau giữa các fixture.

Đây là retry sau lỗi transport khi offline, với DB chứng minh chưa commit trước retry; không tự nhận đã đo mất response sau commit hoặc replay sau commit. Những bằng chứng V1 kế thừa giữ nguyên phạm vi.

Copy/QR dùng session `0099` đã completed, Cohost và **Guest A** (`guesta`, còn nợ100000), không dùng Member A đã trả đủ. Giá trị receiver/reference kỳ vọng lấy bằng transaction DB chỉ đọc, lưu vào driver ignored. Test chỉ abort ảnh ngoài `https://img.vietqr.io/**`, không thay local API. Giao diện phải hiện fallback thật, thông tin thủ công khớp DB và thông báo QR không tự xác nhận đã thu. Không bấm “Tôi đã chuyển khoản”, không gửi/xác nhận payment, không xác minh ngân hàng/VietQR live.

## Review, đối chứng và các lần FAIL giữ nguyên

- Lifecycle qua ba vòng sửa Anti: selector row chuyển sang group đúng Flutter; tiêu đề khoản thu dùng group; chờ Guest home semantics trước login. Edge bản r2 đã PASS riêng rồi được chạy lại trên source cuối r3 bằng fixture mới. Firefox software headed r2 FAIL bootstrap; r3 FAIL tại physical click tab Account dù phần tử visible/enabled/stable. Không có workflow write trong hai lần headed thất bại; nguyên nhân click chưa xác lập. **Không đổi các lần này thành PASS headed**. Firefox headless chạy cùng bản r3 đã PASS.
- Copy/QR qua hai vòng sửa: chỉ skip đúng lỗi unsupported clipboard, mọi grant lỗi khác phải FAIL; cleanup cả grant chưa hoàn tất; oracle số lượt chặn confirmed20/23/200; thêm chờ semantics từ phiên mới sau một lần Edge Guest QR r1 cold bootstrap FAIL. Bốn ca cuối chạy lại tuần tự trong profile thử mới trên source copy r2, tránh clipboard dùng chung bị thao tác song song.
- Reviewer riêng trước runtime xác nhận không còn P0/P1/P2 trong các sửa đã review. Tự chạy riêng 6 DB-gate test PASS và 11 copy controls + 6 receiver-escaping controls PASS. DB-gate controls từng RED6 và copy controls từng RED8 trước sửa; các log đỏ giữ trong bundle. Lifecycle source controls kiểm 8 payload reject, 4 JSON reject, bộ lọc request, canonical JSON và origin guard. Không chạy lại Flutter suite/analyze/build vì không đổi product source; số kiểm thử cũ không được nhận là lần chạy mới.
- Review source/artifact cuối không còn P0/P1/P2 trong delta: reviewer tự xác minh **29/29 manifest hash**, hai source hash, provider/build hash, **4/4 lifecycle driver hash**, template QR chỉ thay mode/expected, bốn cleanup receipt và phép so baseline DB. Reviewer không chạy lại browser/DB/HTTP served hash; independent runtime giữ NOT RUN.
- Hai log DB-gate đỏ/xanh giữ nguyên các dấu cách do PowerShell ghi ra; `.gitattributes` chỉ bỏ kiểm trailing-space cho đúng hai log này để bảo toàn byte/hash đã review, không áp dụng cho source/test/JSON khác.
- Firefox clipboard được đánh dấu NOT RUN khi gặp đúng lỗi “Unknown permission” đã nhận diện. Không coi clipboard chưa đo là sạch hoặc đã hoạt động. Console có lỗi dự kiến từ offline/ảnh QR bị abort; pageerror của các ca cuối bằng0, không tuyên bố console tuyệt đối sạch.

## Dữ liệu, provenance và cleanup

- Bốn fixture đã tạo (gồm các lần thất bại) đều có preflight không trùng ID, marker sở hữu đọc lại, cleanup riêng và xác minh absent. Sau mọi ca lifecycle/copy/QR, fingerprint **21 bảng public/94 dòng, schema, roles và mọi sequence khác đều khớp baseline**. Riêng `auth.refresh_tokens_id_seq.last_value` tăng **56 → 68** do login; Auth rows không nằm trong phép đo. Không phát sinh payment/ledger trong lượt này. [Đối chiếu DB](web_lifecycle_copy_20261113_evidence/database-comparison.json).
- Hash build `main.dart.js` và HTTP phục vụ trùng; ứng dụng dùng lại profile build trước, không retag thành build mới. Source/driver hash và giới hạn có trong [provenance](web_lifecycle_copy_20261113_evidence/provenance.json). Driver QR có expected receiver chỉ ở ignored; publisher xác minh nó khớp template source rồi loại toàn bộ giá trị riêng tư khỏi bundle.
- Các named browser thử đã đóng, inventory không còn browser; không dùng profile cá nhân. Backend fixture và server loopback giữ chạy để tiếp tục local. Sau review đã xóa 5 file tạm sở hữu chứa expected receiver, driver QR và raw QR logs cùng 3 console log liên quan có giá trị riêng tư, kiểm tra vắng mặt; không công bố raw bank/clipboard/snapshot/secret.

[Manifest bằng chứng](web_lifecycle_copy_20261113_evidence/manifest.json) gồm kết quả đã làm sạch, oracle DB, cleanup, controls đỏ/xanh, source provenance và recipe runtime. [Bàn giao lifecycle](web_lifecycle_handoff_20261113.md) và [copy/QR](web_copy_qr_handoff_20261113.md) giữ trạng thái tại thời điểm giao; báo cáo này ghi kết quả mới hơn. Recipe dùng đường dẫn/tool Windows của máy đo, không tuyên bố portable runner cho mọi máy.

## Phần chưa đóng

Firefox headed mặc định vẫn UNKNOWN về hiển thị theo [lượt trước](web_v2_extension_runtime_20261113.md), và headed write attempt mới giữ FAIL input; Firefox clipboard chưa đo. Safari/macOS, iOS/Android, luồng gửi/xác nhận thanh toán trên Edge/Firefox và coverage V2 khác ngoài các ca trên chưa đủ. V2b/V3/V5/V7/V8 theo [ma trận hiện hành](bh07_completion_status_20261110.md); không ký risk acceptance thay owner, không merge/deploy/pilot/BH-08.
