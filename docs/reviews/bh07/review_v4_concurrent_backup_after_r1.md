# BH-07 V4 — kiểm bản sửa vòng 1/3, 09/11/2026

**Chưa đạt.** Working-tree candidate trên base `b72c563d9e519986dbd88ec98bcc3f015a41a442`, Anti conversation `05505acc-f3db-49b5-8d16-ac5d0b65e29c`. Không có clean tested commit/runtime mới. Runner vẫn bị gateway giữ khi đọc `fresh=true`: `secret.redacted/redaction.incomplete`; full source review NOT RUN, không suy ra có credential thật.

## Kiểm chứng thực tế

- Codex: `python tests/test_bh07_v4_backup_concurrency.py -v`: **40/40 PASS**, exit0.
- Codex: `python scripts/bh07_backup/v4_concurrent_probe.py`: **35 controls PASS**, exit0.
- Probe reviewer R1 nguyên file: positive PASS, 11 mutant được chặn. Canonical import của tác giả đã thay đổi; đây là kiểm lại hành vi với input hiện hành, không nhận là exact replay input cũ. R1 đã có capture synthetic riêng để giữ lịch sử.
- [Control mới](v4_review_r1_evidence/post_r1_controls.py): **exit1**, positive PASS; duplicate ledger/audit ID, bool/float counts bị chặn; hai mutant sau vẫn PASS. [Capture input/output/source hashes](v4_review_r1_evidence/post_r1_capture_20261109.json) là synthetic mới, không phải DB runtime; script kiểm hash nguồn trước/sau bằng nhau và không ghi đè capture.
- Full Python suite sau patch đang chạy; chưa ghi count/verdict khi chưa có output kết thúc.

## Phát hiện còn mở

1. **V4-R4 — P2: writers nối tiếp vẫn được gọi là overlap.** `scripts/bh07_backup/run_v4_concurrent_rehearsal.py`, `validate_v4_rehearsal` (source line chưa đọc được). Control `serial_writers_inside_dump`: A thực thi 100.10–100.20, B 100.30–100.40, dump 100.05–100.60; không có khoảng giao nhau giữa hai writer nhưng `overlap_verified=true` cùng các cờ cũ vẫn cho `ok=true, PASS, findings=[]`. Cần kiểm giao interval của hai writer và chứng cứ thực thi DB gắn đúng dump/writer PID/query/request, không chỉ tin cờ hoặc notify. Thêm RED tái hiện và control DB observation thiếu/sai danh tính.
2. **V4-R5 — P2: cleanup chấp nhận danh sách tài nguyên không thuộc rehearsal.** Cùng validator: `unrelated_cleanup_resources` thay toàn bộ danh sách bằng `unrelated-src-db`, `unrelated-target-db`, `unrelated-net`, các cờ true giữ nguyên ⇒ PASS. Contract/handoff yêu cầu tài nguyên `bh07-v4-*` sở hữu theo lượt, nhưng receipt không ràng buộc exact owned manifest/created identity với verified absent. Cần manifest resource tên/ID/ownership thực tế, exact coverage và fail-closed khi thiếu/thừa/trùng/sai ID hoặc inspect lỗi; không chỉ nhận chuỗi có hậu tố db/net.

## Trạng thái review trước

V4-R2/R3 đã hết triệu chứng quan sát ở các control hiện hành: status/provenance sai và token synthetic bị chặn; test publication đã GREEN. V4-R1 đã chặn các mutant được nêu, nhưng **chưa đóng toàn bộ yêu cầu relational evidence**: canonical còn chứa ID/count/cờ và digest synthetic, chưa có bằng chứng độc lập về amount/FK/audit actor/entity/request/result/replay content của row thực. Không nói digest đúng 64 hex là hash khớp dữ liệu. Full source/query review và runtime chưa chạy nên phần này vẫn chưa đủ bằng chứng; cần giữ yêu cầu đối chiếu row scoped thật, không chỉ tăng cờ hoặc hardcode số tiền.

Giao Anti sửa **vòng 2/3**, chỉ bốn file candidate đã giao; giữ nguyên mọi report/probe/capture reviewer. V4 runtime, whole BH-07/V8 vẫn chưa nghiệm thu. Không merge/push/deploy/pilot/BH-08.

## Bổ sung kết quả và giới hạn provenance

Full `python -m unittest discover -s tests` của candidate vòng 1 kết thúc **477/477 PASS**, exit0, 245.580s, archive `28be337a99df8f16`. Runner SHA256 `27705cd6515c414817cf41a76e558f8e5009a64e56873bdbdadc2c941a2ef5c0`, test SHA256 `a56695e137fed4e1927691ed8e82f88fe9d7b277e67d067357c8c1e3af492063` kiểm sau suite khớp capture vòng 1; Anti chưa ghi bản sửa vòng 2 tại kiểm tra này. Không gán kết quả này cho code vòng 2 sắp thay đổi hoặc clean checkout.

Audit độc lập lưu ý `post_r1_controls.py` import validator trước khi lấy hash-before. Guard chỉ chứng minh file trên đĩa ổn định trong khoảng capture sau đó; chưa tự chứng minh bytes module đã load đúng hash nếu có race trước hash đầu. Không có bằng chứng race đã xảy ra, nhưng không gọi guard này là proof tuyệt đối của loaded source. Giữ capture gốc; lần kiểm tiếp phải hash trước cả import/fixture load rồi kiểm lại sau, không sửa lịch sử để che giới hạn.
