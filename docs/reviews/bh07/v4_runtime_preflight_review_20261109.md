# Review tiền kiểm V4 — 09/11/2026

**Cập nhật chốt sau sửa:** Đạt trong phạm vi báo cáo tiền kiểm; PF1–PF4 đóng theo đối chiếu nội dung dưới đây. Các nhận xét ban đầu được giữ nguyên để truy vết. Không phải nghiệm thu runner, runtime V4 hoặc toàn BH-07.

Codex review báo cáo Anti `v4_runtime_preflight_20261109.md` với metadata tiền kiểm và review guard/probe. Đây là review tài liệu, không phải review full runner hoặc runtime. Anti job `shell_804065641d794633` đã bàn giao; archive `42d670370209e2eb`.

**Chưa chốt báo cáo tiền kiểm; cần sửa các điểm dưới đây.** Không mở lại guard/probe hoặc vòng sửa implementation thứ tư.

- **PF1 P2 — Cleanup thiếu xác minh ownership và absence.** Mục 6 mới yêu cầu namespace và receipt `cleanup.ok`; tên riêng hoặc cờ true không chứng minh quyền xóa. Cần preflight collision fail-closed, lưu ID/label/token sở hữu, chỉ xóa đúng tài nguyên đã tạo, inspect lỗi/không rõ phải FAIL, xác minh vắng mặt sau cleanup; tài nguyên có trước không được nhận làm của mình.
- **PF2 P2 — Bằng chứng concurrency/snapshot chưa đủ chính xác.** Mục 7 nói writer confirmed trong lúc snapshot diễn ra, chưa chứng minh hai writer overlap thực sự trong khoảng dump. Cần bằng chứng activity/barrier thực, không chỉ timestamp; snapshot export từ transaction còn mở và truyền vào dump; xác định visibility từ snapshot thay vì suy từ thời điểm HTTP confirmed. Restore đối chiếu đúng tập snapshot và replay nghiệp vụ, không yêu cầu mọi commit trong khoảng dump xuất hiện trong restore.
- **PF3 P2 — Các cổng cụ thể chưa được đo.** Mục 6 khẳng định 54321/54322/9999 đang bind nhưng metadata không có bindings. Cần ghi UNKNOWN, yêu cầu đo trước khi chọn loopback ports. 80,743,747,584 bytes tương đương khoảng 75.2 GiB (80.7 GB). Scanner chỉ được kết luận không có trên PATH.
- **PF4 — Attribution/provenance.** Runner hash là quan sát Codex kiểm lại, không phải Anti chứng minh byte được bảo toàn. Cần link tương đối đến hồ sơ nguồn và phân biệt điều kiện candidate có manifest/hash bất biến với quyền commit; báo cáo không tự cấp quyền commit, merge hay chạy runtime.

Codex kiểm mới: SHA256 runner vẫn `53dc32fd1e647e2f0d7252fc513f85872c7250cea9b2c7d7b463289c17f7949d`; `git diff --name-only -- lib test supabase web pubspec.yaml pubspec.lock` rỗng. Không chạy lại suite cho thay đổi chỉ tài liệu. 499 Python và Flutter là kết quả đã có trong review bổ sung, không phải lần chạy mới.

Full source tiếp tục chưa được review theo hồ sơ admission hiện có; lần `ctx_compose` tổng hợp trong lượt này cũng bị giữ do authority không xác minh được. Không suy nguyên nhân secret/false-positive, không dùng reader khác để vượt gateway. **V4 runtime NOT RUN; toàn BH-07/V8 chưa nghiệm thu; không merge/push/deploy/pilot/BH-08.**

## Chốt bản sửa tiền kiểm

Anti bàn giao từ cùng conversation `71eb2541-a4eb-4c37-bead-20c09fb2402a`, job `shell_82370cdc2a089dbd` exit0, archive `3c514bf206af322b`. Codex đọc lại toàn báo cáo, không lấy lời bàn giao thay nội dung:

- PF1 đóng: quy định collision fail-closed, ID/label/token sở hữu, chỉ xóa tài nguyên phiên tạo, inspect lỗi là FAIL, kiểm absence trước `cleanup.ok`. Đây là yêu cầu cần kiểm trên source/runtime, chưa chứng minh runner đã thực hiện.
- PF2 đóng: yêu cầu activity/barrier của hai writer overlap trong dump, transaction export snapshot giữ mở, truyền snapshot vào dump, restore theo visibility và replay nghiệp vụ. Khi review implementation phải đối chiếu actual snapshot membership; thời điểm commit riêng lẻ không đủ cho mọi transaction đã in-progress khi snapshot được tạo. Không bắt writer overlap toàn bộ thời lượng dump, nhưng phải chứng minh khoảng overlap thực nằm trong dump.
- PF3 đóng: báo cáo bỏ khẳng định cổng chưa đo, sửa GiB/GB và giới hạn scanner không có trên PATH.
- PF4 đóng: hash được gán nguồn Codex, link tương đối, candidate có provenance bất biến và không tự cấp quyền commit/runtime. Một manifest hash bất biến được review có thể phục vụ provenance; dirty tree hiện tại chưa được xem là candidate đã review full source.

Kiểm tra mới của Codex sau bản sửa: runner SHA vẫn `53dc32fd1e647e2f0d7252fc513f85872c7250cea9b2c7d7b463289c17f7949d`; diff app/schema rỗng. `docker ps --format '{{.Names}} | {{.Ports}}'` cho host publish 54321 (Kong), 54322 (Postgres), 54323 (Studio), 54324 (Inbucket), 54327 (Analytics), trên IPv4/IPv6 wildcard. Auth có `9999/tcp` nội bộ, không thấy host publish trong output. Đây chỉ inventory Docker tại thời điểm kiểm, không chứng minh mọi host listener hoặc cổng ứng viên trống; phải kiểm lại trước run. Không thay Docker/DB, không chạy lại Python/Flutter cho báo cáo.

## Handoff nút chặn source admission

Bước tiếp theo cần môi trường/gateway chính thống cung cấp khả năng đọc và review toàn runner có SHA trên. Chuyển cho người quản trị gateway: đường dẫn `scripts/bh07_backup/run_v4_concurrent_rehearsal.py`, SHA, các cờ `secret.redacted`/`redaction.incomplete`, và lỗi compose authority không xác minh được. Cần kết quả chẩn đoán policy/admission hoặc bản source sửa nguyên nhân được admission; không cần cung cấp secret, không yêu cầu tắt kiểm soát hoặc xuất source bằng reader khác. Nguyên nhân hiện UNKNOWN. Nếu source đổi, mọi review/hash/probe phải gắn candidate mới và chạy kiểm chứng tương ứng trước runtime.

Sau admission: review full source, chốt provenance candidate, đối chiếu dependency và quyền sở hữu tài nguyên, rồi mới chạy rehearsal cô lập và review bằng chứng runtime. **Tiền kiểm đã hoàn tất; full source/runtime vẫn NOT RUN, toàn BH-07/V8 chưa nghiệm thu.** Không tự giao thêm vòng tài liệu khi chưa có thay đổi điều kiện admission.

## Kiểm tra khả năng chẩn đoán gateway tiếp theo

Theo yêu cầu tiếp tục, Codex tìm công cụ chính thống bằng `ctx_discover_tools`: không có kết quả cho admission/authority/policy/doctor; nhóm debug chỉ liệt kê call/feedback/load-tools. Không xuất proof diện rộng hoặc đọc source bằng đường thay thế.

Thử lệnh chỉ chẩn đoán `C:/Users/POTA/AppData/Roaming/npm/node_modules/lean-ctx-bin/bin/lean-ctx.exe doctor` qua `ctx_shell` trả **BLOCKED — DO NOT RETRY**, vì `lean-ctx.exe` không thuộc shell allowlist. Config được tool chỉ ra: `C:/Users/POTA/.config/lean-ctx/config.toml`. Đây là chặn chẩn đoán CLI, tách biệt với source-admission; không chứng minh nguyên nhân của source withheld. Không retry, không đổi allowlist/security, không reroute qua shell khác.

**Hành động ngoại vi cần thiết:** quản trị môi trường chạy chẩn đoán gateway trong phiên quản trị được phép, xử lý authority/admission cho đúng path/hash ở trên, rồi cung cấp kết quả không chứa secret hoặc khôi phục admission để Codex review bằng `ctx_read`. Không yêu cầu tắt gateway. Không có code/runtime/DB/Docker thay đổi trong lượt này; trạng thái nghiệm thu giữ nguyên.
