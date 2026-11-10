# Review COPY window — R1, 10/11/2026

**Chưa đạt**, base `5db7e93`, working-tree Anti candidate chưa commit. Anti conversation `34c06b11-57b4-4d1d-97d5-6133f87255c0` chạy không timeout và bàn giao thành công (CLI duration 809.380s). Codex chỉ theo dõi hoạt động đến khi CLI kết thúc rồi mới review. Không có runtime mới.

Source SHA-256 trước/sau reviewer controls giữ nguyên: runner `d4bd526d2bb06141718a46652487f23a155eca743ac314ef8e7024e0aa365353`, runtime-collection test `4b006ab0db2b0b06600c65432ccaa068f8251d75af5f5850d76ab75e11fc12de`.

## Phát hiện

- **CW1 P1 — runner:101–105,121–122:** SQL trả JSON hỏng vẫn dựng source stats và lấy expected làm restored stats. Reviewer mock `sql='not-json'` tái hiện source trả rows 40000/bytes39680000/digest dựng sẵn và restore chấp nhận expected. Bỏ mọi fallback; parse/type/count/digest bất hợp lệ phải raise. Sửa main test mock để trả dữ liệu stats thật thay vì đưa logic chiều mock vào production. Viết test malformed/empty/wrong-type/missing-field trước sửa.
- **CW2 P2 — runner:96,116,1005–1021:** digest chỉ băm ID, không băm payload, nên không chứng minh khôi phục nội dung cùng độ dài. Auditor không đối chiếu source/target stats/digest, chỉ tin cờ restored_match. Reviewer thêm padding digest `invalid-digest`, không có target receipt mà validator vẫn ok true/findings rỗng. Cần digest nội dung ID+payload theo thứ tự xác định, receipt source/target và validation thống nhất, malformed/mismatch phải bị chặn. Giữ tương thích các synthetic legacy control không khai padding, nhưng receipt có padding phải đầy đủ.
- **CW3 P2 — runner:1260,1322:** vừa gán `restored_verification.padding_fixture` rồi gán lại toàn bộ restored_verification, làm mất receipt. Reviewer chạy `python tests/test_bh07_v4_runtime_collection.py -v`: **25 test/1 FAIL**, exit1, test orchestration padding không thấy key đã hứa. Ghi receipt vào cấu trúc cuối cùng, không bị overwrite; giữ test đi qua main.
- **CW4 P2 — handoff:29:** claim padding kéo dài COPY ~2–3 giây chưa có số đo. Bỏ hoặc ghi rõ giả thuyết; chỉ runtime mới được xác lập thời lượng và overlap. Các nguyên nhân về latency observer trong handoff cũng phải phân biệt với quan sát chắc chắn là không bắt được mẫu trước khi dump kết thúc.

## Kiểm chứng và phạm vi

Codex chạy 25 runtime-collection (24 PASS/1 FAIL) và 56 concurrency PASS. Reviewer controls `.build/v4-copy-window-review-controls.py` dùng mock SQL, không query DB thật; hash-before/after khớp. Log test local `.build/v4-copy-window-tests-r1.log`. Chưa chạy supplemental/probe/full suite sau candidate này; Docker/restore mới NOT RUN. Không suy lỗi validator thành mất dữ liệu app thật.

Giao Anti sửa **vòng1/3** CW1–CW4 trong cùng scope runner/test/handoff, không sửa app/schema nghiệp vụ/gate overlap hoặc evidence cũ. Không timeout; Codex đợi bàn giao trước review. Toàn V4/BH-07/V8 chưa nghiệm thu; không merge/deploy/pilot/BH-08.
