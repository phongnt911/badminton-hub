# Ledger coverage — review bản triển khai đầu tiên

2026-11-08. Base `5512a72bc7c5c4377916f7afb663e1fe014c7376`, nhánh `feat/bh07-completion-local`. Anti CLI Gemini 3.8 Flash High bàn giao conversation `e3e0f092-ab76-44a5-9535-054e6ef14728` (archive `663d947bc7540651`). Code được review là **working tree chưa commit**, không gán base SHA thành tested source sạch. Codex kiểm chứng và một Code Reviewer riêng kiểm tra độc lập; không sửa code triển khai.

## Phát hiện phải sửa trong vòng 1/2

1. **LGR1 P1 — Runner không parse được.** `scripts/bh07_appheap/run_app_profile_heap.js:871`: hai assignment bị lặp và dấu `}` thừa tại 873 đóng sai `try`. `node --check` exit 1 với `Missing catch or finally after try`. Sửa cấu trúc block, giữ default/bank behavior; kiểm tra parse trước khi chạy suite.
2. **LGR2 P1 — Hai cờ cùng bật làm mất ledger sentinel.** `run_app_profile_heap.js:487`: nhánh bank trả về trước nhánh ledger. Với `--bank-coverage --ledger-coverage`, child fixture được tạo nhưng `ledger_transaction_id` không có trong values/metadata. Ghép các sentinel tùy chọn trước khi return, hoặc dùng một chế độ ledger bao gồm bank với contract/UI/cleanup nhất quán. Thêm control qua nhánh resolve thực tế, không chỉ substring source.
3. **LGR3 P1 — Oracle/runner có thể PASS khi chưa đo ledger.** `run_app_profile_heap.js:925` và `heap_oracle.py:255`: expectations tự suy ra bỏ sentinel chưa load hoặc đã có từ baseline; hai expense ID vẫn đủ minimum gate. Probe Codex `build/ledger_oracle_review_probe.py`: positive PASS, mutant thiếu Owner ledger **PASS**, mutant baseline collision **PASS**; probe exit 1. Bắt buộc ledger khi profile khai báo, như bank/payment strict gates hiện có, mà không đổi generic legacy semantics. Không chữa test bằng cách chỉ chèn expectations thủ công ở test (`tests/test_bh07_ledger_heap_coverage.py:158`) rồi để runner thật không áp dụng. Bảo đảm CLI trả FAIL/exit 1 khi precondition sai và bảo vệ trường hợp sentinel bị bỏ khỏi resolved values.
4. **LGR4 P2 — Ledger-only bỏ qua lỗi cleanup parent.** `run_app_profile_heap.js:1091`: `bankCleanupOk` chỉ được tính trong `if (isBankCoverage)`, dù ledger-only tạo parent bank/club. Tính validity của parent khi bất kỳ chế độ nào cần parent; delete/absence/error parent thất bại phải làm cleanup tổng FAIL. Child phải được cleanup trước parent. Thêm behavior test cho ledger-only và lỗi parent.
5. **LGR5 P2 — Helper chưa fail-closed tại endpoint/ownership.** `scripts/bh07_appheap/disposable_ledger_fixture.js:54,80,109`: thiếu apiUrl bỏ qua guard; cleanup không kiểm endpoint; POST 2xx lập tức nhận ownership, không đọc lại exact row. Bắt buộc loopback cho ensure/cleanup có thể ghi, kiểm exact full-row readback trước khi nhận creation. Thêm controls cho thiếu/remote cleanup endpoint, POST báo thành công nhưng không có row hoặc row không khớp, DELETE no-op còn row; không adopt/delete foreign row. Giữ definite 403 kể cả matching row xuất hiện và ambiguous POST reconciliation.

## Kiểm chứng và giới hạn

- Fresh fixture tests của bản bàn giao: **8/8 PASS**, archive `4503d65c96c96610`. Lỗi escape path Windows của bản trung gian đã được sửa bằng `.as_posix()`; không mang lỗi đã sửa sang finding mới.
- Parse runner và probe LGR3 được Codex tự chạy, đều exit 1 theo triệu chứng trên.
- Lượt targeted trung gian 28 tests có 8 failures/13 errors, archive `a9744cd558bea283`; không coi count này là suite cuối sau bàn giao vì file còn đang được Anti sửa khi chạy.
- Chưa chạy full Python/analyze/Flutter của bản ledger vì parse đang chặn. Kết quả 375/analyze 0/247+1skip trước đó thuộc baseline đã chốt, không áp cho patch ledger này.
- Chưa chạy DB fixture, browser hay heap mới. Preflight chỉ đọc sáu bảng local, không phải runtime coverage.
- Một số cửa sổ source auditor bị context gateway giữ lại; reviewer kiểm diff mới và hợp đồng qua test, chưa tuyên bố đọc lại toàn bộ auditor. Cần chạy positive/mutant CLI và regression sau sửa.

## Fingerprint working tree đã review (SHA-256)

[Metadata lần review](ledger_round1_review_evidence/results.json); [probe LGR3 đã đóng gói](ledger_round1_review_evidence/oracle_gate_probe.py) dùng cùng logic như probe chạy ở `build/`, chỉ đổi project-root lookup cho vị trí lưu evidence. Probe luôn đánh giá source hiện tại; kết quả trước sửa được giữ trong JSON, không ghi đè bằng kết quả sau sửa.

| File | SHA-256 |
|---|---|
| `scripts/bh07_appheap/run_app_profile_heap.js` | `45e19242a0cc837e2d13951bee29f75c3e529871dd40cdb3f1c31641342e85ba` |
| `scripts/bh07_appheap/verify_evidence.py` | `6867b83796a593368cc4266f75efa12d9b87ea8e0f1ef9787883f0236035748e` |
| `scripts/bh07_appheap/disposable_ledger_fixture.js` | `a6edf8dcefcafc2428325ab06aa178c75a315711b2906c98ada8617b96cf077e` |
| `tests/test_bh07_ledger_fixture.py` | `b30b79ae832be2ce5bc1a82379fe5d70b37bcc32f1f86b0caeb246d51395464f` |
| `tests/test_bh07_ledger_heap_coverage.py` | `81a1a12c36524f59fdbca0f1fd80d6372dd348bfe64d395d8866c8d8a8dc606d` |

**Chưa đạt bản triển khai ledger.** Giao sửa toàn bộ LGR1–LGR5 vòng 1/2, test đỏ trước sửa và kiểm chứng lại. Không merge/push/deploy/pilot; toàn V2b/BH-07 chưa nghiệm thu. Owner risk draft vẫn chưa được phê duyệt; yêu cầu quyết định riêng V2/V3/V5/V7 đang chờ trả lời và không miễn V2b/V4 hay các lỗi ở đây.
