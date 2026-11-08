# Ledger — review vòng sửa 3/3: Chưa đạt

2026-11-08. Owner mở vòng sửa bổ sung và đổi giới hạn chung từ 2 thành 3 vòng, lưu tại `53f65e4`. Base triển khai `53f65e4`; candidate source/test `c427e27f7a2b0082907ac6d6942fc5a5fed6724a`. Anti CLI Gemini 3.8 Flash High triển khai (conversation `9c3e9245-68d5-4249-95d3-a1527fa4f667`, archive `4e54aab467d96f11`); Codex kiểm chứng, Code Reviewer riêng review source và probe. Không nghiệm thu candidate này.

## Kết luận và phát hiện

- **LGR9 P2 — đóng phần diagnostic wiring.** `takeSnapshot` bắt scan nonzero, trích `{exit_status,error_type,detail}`, xóa snapshot trong finally, và `main` giữ `summary.scan_failure`. Chỉ lấy error field/exception diagnostic thay vì công bố bảng sentinel/heap; known sentinel redaction chạy trước truncate. Không suy việc có diagnostic thành runtime PASS.
- **LGR10 P2 — chưa đóng đầy đủ.** Đường abort bình thường đã có `dump_dir_outside_repo` và `raw_snapshots_remaining`, nhưng implementation mới tạo LGR11 bên dưới.
- **LGR11 P2 — enumeration có thể ngắt cleanup DB**, `scripts/bh07_appheap/run_app_profile_heap.js:979`. Sau khi `rmSync` thất bại, `readdirSync(DUMPS)` không được catch; lỗi EACCES/EPERM hoặc race làm finally thoát trước cleanup expense/payment/ledger/club/bank và công bố evidence. [Probe](ledger_round3_review_evidence/cleanup_enumeration_probe.cjs) chạy chính block metadata mới với injected EACCES, xác nhận `subsequent_db_cleanup_reached=false`. Cách sửa ở vòng được owner cho phép tiếp: catch lỗi enumeration, giữ cleanup unverified/fail-closed và luôn tiếp tục cleanup fixtures. Không sửa source sau review này.
- **LGR12 P1 — oracle không tương thích Chrome đang cài**, `scripts/bh07_appheap/heap_oracle.py:38`. [Probe Chrome thật](ledger_round3_review_evidence/chrome_schema_probe.cjs) dùng Chrome `156.0.8078.80`, V8 `15.6.75.27`, trang trắng với profile riêng. Snapshot hợp lệ có `scopes`, `scope_context_vars`, `scope_uses`; oracle hiện tại exit 2 với `snapshot_unexpected_top_level_key: scopes`. Lỗi tooling này chặn live heap verification trên môi trường hiện tại, **không phải bằng chứng app leak**. Vòng sửa tiếp cần xác định contract/validation cho scope tables theo V8 và thêm controls dương/âm; không xóa kiểm unknown-key hoặc bỏ qua cấu trúc tùy ý.

Snapshot lỗi lịch sử của `a2efc1e` đã xóa và không giữ diagnostic, nên không thể khẳng định nó có cùng nguyên nhân. LGR12 là kết quả mới có bằng chứng trên cùng phiên bản Chrome; không retag probe trang trắng thành app runtime.

## Kiểm chứng Codex thực chạy

| Lệnh/phạm vi | Kết quả | Archive/bằng chứng |
|---|---|---|
| `python -X utf8 -m unittest tests.test_bh07_ledger_scan_diagnostic_and_abort_cleanup -v` | 14 PASS, exit 0 | `eb7f8e49983692d3` |
| `python -X utf8 -m unittest discover -s tests` | **434 PASS**, 224.474s, exit 0 | `1032d19e67fb361f` |
| `node --check scripts/bh07_appheap/run_app_profile_heap.js` | exit 0 | phiên review |
| `node .../cleanup_enumeration_probe.cjs` | xác nhận EACCES chặn bước DB tiếp theo; probe exit 0 | [result](ledger_round3_review_evidence/cleanup_enumeration_result.json) |
| `node .../chrome_schema_probe.cjs` | real oracle exit 2, diagnostic đúng; probe exit 0 | `d4be8ebce263c864`, [result](ledger_round3_review_evidence/chrome_schema_result.json) |
| `git diff --check` và staged check | exit 0 | phiên review |

14 test mới chạy qua `require` vào các helper thực, không phải Node VM như handoff Anti mô tả. Các cleanup tests gọi helper `evaluateCleanupState` **chưa được main sử dụng**, nên không thay thế integration coverage của finally; probe reviewer bổ sung đã tìm ra LGR11. Anti ghi 12 test/432 dự kiến; count thực tế là 14/434. Không có lần chạy RED trước implementation được Codex ghi nhận, không nhận đây là TDD red-to-green đã chứng minh.

Full Python bắt đầu trên working tree rồi source/test được commit nguyên bytes thành `c427e27` trong khi suite còn chạy; không gọi là clean-checkout replay. App/backend/schema/Dart tests/web/pubspec không đổi. Kết quả Flutter analyze 0 và 247 PASS +1 SKIP trước đó trên cùng app được giữ theo [review tooling](review_205dcd5.md), không tuyên bố chạy lại trong vòng này. Oracle không được sửa đoán nguyên nhân.

## An toàn bằng chứng và giới hạn

Probe Chrome chỉ mở `about:blank`, không lấy credentials, không truy cập app/DB. Snapshot 2.202.231 bytes, SHA-256 `3ce2bbf98b846ee22e9e0d1a8e1d03cbe73845486f74050ec99f569e90eb17b3`; raw dump không công bố. Browser exited=true, profile_removed=true, raw_dump_directory_removed=true. Probe EACCES dùng fs stub, không xóa file hoặc gọi DB. Không có live ledger/app runtime mới; không chạy candidate trên fixture DB sau khi xác nhận LGR11.

Các bundle lịch sử giữ nguyên. Candidate và probe chạy trên working tree có tài liệu mới; không gán `git_dirty:false` hoặc provenance clean-source app runtime cho vòng này. Reviewer riêng xác nhận hai probe và mức P1/P2, không viết code/chạy lại browser/DB.

**Dừng sau vòng sửa 3/3 theo [AGENTS.md](../../../AGENTS.md).** LGR11/LGR12 còn mở, LGR10 chưa đóng; không tự mở vòng 4. V2b/BH-07/V8 chưa nghiệm thu; operational risk draft chưa được owner ký và không thể waive các lỗi này. Không merge/push/deploy/pilot/BH-08.
