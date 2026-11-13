# Auth listener — Guest layout calibration, 13/11/2026

**Calibration measured; full auth_listeners gate NOT RUN.** Không đăng nhập, không tạo fixture/payment, không sửa app/schema/remote. Codex chạy probe riêng từ tracked base1691154; driver/scanner là prototype trong `.build` khi đo, không nhận git_dirty=false là chứng minh chúng đã tracked trong source SHA. Bản code thực thi được giữ nguyên trong bundle để review.

[Bundle calibration cuối](auth_listener_guest_20261113_evidence/manifest.json) có layout/provenance và bản driver/scanner nguyên văn. Hai script chạy từ tên `.build/listener_baseline_probe.js` / `.build/listener_baseline_scan.py`; đường dẫn tương đối trong bản sao evidence giữ đúng ngữ cảnh đó. Muốn lặp lại cần copy về các tên `.build` này và chọn output directory mới, không overwrite kết quả cũ. Đây là prototype calibration, chưa phải harness nghiệm thu production.

## Phát hiện thực nghiệm

Fresh Edge157 headless, Guest UI xác nhận,39artifact profile khớp served. Có một AuthProvider và một SessionProvider reachable qua cạnh mạnh từ GC root; ClubProvider/FinanceProvider chưa được tạo trên màn Guest.

AuthProvider.ChangeNotifier__listeners có hai slot được enum: slot0 là UI tearoff `markNeedsNotifyDependents$0`, `_receiver` trỏ InheritedProviderScopeElement; slot1 là `_session_provider$_onAuthChanged$0`, `_receiver` trỏ SessionProvider. `$_name` nằm trên generated tearoff prototype. Đây không phải bằng chứng listeners phải biến mất khi logout.

V8 snapshot không có numeric_value trong node_fields. Đọc riêng ba counter bằng HeapProfiler.getObjectByHeapObjectId→Runtime.getProperties(ownProperties=true, generatePreview=false) trên đúng AuthProvider heap ID cho count2/depth0/removed0; object group đã release. Snapshot và scalar là hai quan sát gần nhau, chưa là hợp đồng nguyên tử/quiescent epoch cho kiểm thử chấp nhận. Null/false được nhận từ fixed primitive structural literals; class_name:null chỉ là metadata chưa nhận diện/đã lọc.

## Phạm vi và cleanup

Một vài probe Guest được dùng để hiệu chỉnh `_this`→`_receiver` và thêm primitive/counter inspection; bundle giữ lần cuối có method/receiver và scalar observation. Các dump/profile/browser của từng probe đã dọn. Không có raw heap hoặc credential trong bundle.

Chưa đo Owner-load, post_logout hoặc ba provider đầy đủ; chưa kiểm dispose, listener count sau logout, model retention hay privacy. Không đổi auth_listeners NOT RUN, toàn V2b/BH-07/V8 chưa nghiệm thu.

Tiếp theo phải chốt hybrid graph/scalar contract, bảo đảm provider-load precondition, chỉ kiểm finite fields đã được nạp và tách public refetch hợp lệ khỏi dữ liệu Owner cũ. Có thể bắt đầu nhánh FinanceProvider (_instructions/_finance) để tận dụng UI/fixture đã review; Club/Session/full-listener coverage vẫn riêng.

Reviewer riêng xác nhận ba P2 trong bản feasibility đã sửa (logout field invariants, public refetch và vị trí tearoff $_name); kiểm4/4hashes và đối chiếu prototype/receipt, không có P0/P1/P2 mới trong scope calibration. Không chạy prototype/browser/DB độc lập; không gọi calibration là listener acceptance.
