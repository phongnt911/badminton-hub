# Review recovery diagnostics + V5b — R1, 10/11/2026

**Chưa đạt phần diagnostics; V5b token fix PASS targeted.** Base `15f981b`, Anti conversation `ae525d38-c7e1-4e4c-910a-5d740ba08648`, bàn giao thành công không timeout (853.317s). Codex chỉ review sau result. Runner SHA-256 trước/sau reviewer control `e10321b3d3adb0f4900e031bb8712183efe31811ce5c722a23d7b1578a13be23`.

## Phát hiện phải sửa

- **RD1 P2 — tests/test_bh07_v4_runtime_collection.py:1180–1352:** test orchestration mới nằm trong `PersistentDumpObserverTests` không có `_run_orchestration_scenario`, nên7test ERROR AttributeError trước khi kiểm hành vi. Chuyển test về class/harness đúng, không kế thừa toàn bộ suite chỉ để chữa lỗi. Auth failure hook còn áp dụng cả source login trước stage; giới hạn hook ở target login để thực sự tái hiện boundary, thêm import urllib nếu dùng, bỏ wall sleep không cần thiết bằng patch chỉ trong test.
- **RD2 P1 — runner:289–299,1687:** regex sanitizer vẫn công bố arbitrary private exception message. Reviewer đi qua main với replay ValueError chứa marker và target-command RuntimeError chứa marker: cả hai marker còn trong artifact. Dùng message/label tiền định ở boundary mới, không dựa vào regex đoán toàn bộ secret. Không dump argv/env/HTTP body/stdout/stderr hoặc free-text exceptions vào public metadata. Đây là synthetic fail-open publication control, không kết luận đã có leak app/credential thật trong runtime.
- **RD3 P2 — runner:1688–1718:** lấy `err.operation` và `err.exit_code` rồi serialize thẳng, không xác minh whitelist/type ở sink. Control gán operation ngoài whitelist và exit_code string: cả hai xuất hiện trong summary, findings không chặn. Chỉ metadata đã validate được xuất; exit_code phải int thật. Không suy danh tính/exit bằng tìm chữ “exited” trong arbitrary message; production `cmd` đã có structured fields. Loại message tùy ý khỏi command-error factory nếu không có consumer hợp lệ.

## Kiểm chứng

Codex `python tests/test_bh07_v4_runtime_collection.py -v`:50test/7ERROR, exit1; `python tests/test_v5b_runner_flaws.py -v`:22/22PASS, exit0, có16path/inventory subtests. Không chạy Docker hoặc full suite khi targeted còn lỗi.

Control local `.build/recovery-diagnostics-r1-controls.py` gọi main harness bằng class đúng (không sửa source/test candidate), có source hash-before/after: raw-command-message, arbitrary-operation, non-int-exit và raw-replay-message đều được công bố (`true`). Log `.build/recovery-diagnostics-r0-tests.log`, `.build/recovery-diagnostics-r0-v5b.log`.

Handoff hướng dẫn replay probe V5b cũ cần ghi rõ tương thích: probe lịch sử tự ép `prefix`, còn test mới đã truyền prefix, nên không được sửa evidence cũ để lấy xanh;16controls mới và probe thích ứng mới phải chứng minh cùng ý nghĩa. Giữ production V5b không đổi.

Giao sửa correction **vòng1/3** RD1–RD3 trong đúng ownership, không sửa app/schema/gate/timing/workload. Đợi bàn giao không timeout. Toàn BH-07/V8 chưa nghiệm thu.
