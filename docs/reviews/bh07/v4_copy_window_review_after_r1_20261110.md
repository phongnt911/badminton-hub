# Review sau sửa COPY-window vòng1/3 — 10/11/2026

**Chưa đạt, còn CW2 P2 về độ dài digest.** Anti bàn giao xong trong conversation `34c06b11-57b4-4d1d-97d5-6133f87255c0`, không timeout. Codex chỉ review sau CLI result thành công. Base `5db7e93`, source/test hiện vẫn chưa commit.

CW1 đóng: parser bỏ fallback stats/expected substitution, mock main được sửa trả đúng JSON. CW3 đóng: padding target receipt đã được đưa vào cấu trúc cuối cùng. CW4 đóng: timing 2–3 giây được thay bằng giả thuyết chưa đo; native COPY/HTTP overlap vẫn là gate thật. CW2 đã băm ordered ID+md5(payload) và đối chiếu hai receipt đầy đủ, nhưng regex còn lỗi:

- **CW2 P2 — runner:93 và1062:** `[0-9a-f]{32,64}` nhận mọi độ dài từ32 đến64, trong khi contract nói chỉ32 hoặc64. Reviewer subagent đọc delta và direct probe: digest33 ký tự được cả parser và auditor source/target matching chấp nhận, `ok=True`, findings rỗng. Yêu cầu đúng32 hoặc64 và thêm negative controls cho33/40/63, positive32/64. SQL thật dùng md5 nên32; lỗi này không phải quan sát corruption DB thật, nhưng cổng malformed receipt chưa đóng.

Codex chạy **26 runtime-collection +56 concurrency +6 supplemental =88 test PASS**, probe **49/49 PASS**. Reviewer tự chạy26 runtime-collection PASS. Full Python đã kết thúc exit0; summary/count được ghi ở bản review chốt sau khi đối chiếu log `.build/v4-copy-window-full-python.log`, không nhận các dòng mutant FAIL kỳ vọng là suite failure. Không có Docker runtime candidate này.

Reviewer nêu giới hạn: host disk preflight không đo được free space bên trong Docker VM; COPY duration mới chưa đo; subprocess timeout cũ/full V4 nằm ngoài delta. Điều phối giữ các giới hạn công khai, không gọi host preflight là bảo đảm capacity Docker. Giao Anti sửa **vòng2/3** chỉ regex/test/handoff, không thay workload hoặc gate khác. Đợi bàn giao không timeout.
