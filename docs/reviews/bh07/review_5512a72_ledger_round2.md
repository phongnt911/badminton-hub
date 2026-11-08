# Ledger coverage — review sau sửa vòng 1/2

2026-11-08. Cùng base `5512a72bc7c5c4377916f7afb663e1fe014c7376`, working tree chưa commit trên `feat/bh07-completion-local`. Handoff Anti `e3e0f092-ab76-44a5-9535-054e6ef14728`, archive `7f46b820314b4221`. Codex chạy kiểm chứng; Code Reviewer riêng đối chiếu code và probe. Không nhận source đang dirty thành clean tested SHA.

## Kết luận LGR1–LGR5

Đóng LGR1–LGR5 trong phần code đã sửa: runner parse được, sentinel hai chế độ đã ghép trước return, oracle strict bắt buộc ledger, runner kiểm parent cleanup trong ledger-only, helper bắt buộc endpoint và exact successful-POST readback. Probe LGR3 giữ positive PASS và cả hai mutant FAIL. Những kết luận này không đồng nghĩa toàn bộ tooling/runtime được nghiệm thu; còn các phát hiện bên dưới.

## Phát hiện phải sửa vòng 2/2

1. **LGR6 P2 — Nút hủy aria-only không được nhận diện.** `scripts/bh07_appheap/run_app_profile_heap.js:667`: predicate chỉ kiểm `e.text`, bỏ `e.aria`. Probe thật của exported `openOwnerLedger`, không browser/DB: trường hợp text `Huỷ` PASS; cùng nút chỉ có aria-label `Huỷ` FAIL tại `Cancel manual transaction dialog`. Dùng helper semantic button hiện có để so exact label theo cả text và aria; giữ điều kiện role/button, không dùng substring hoặc click `Ghi sổ`. Bổ sung positive text/aria và negative role/label controls.
2. **LGR7 P2 — Auditor vẫn nhận xanh khi parent chưa cleanup.** `scripts/bh07_appheap/verify_evidence.py:657`: kiểm parent chỉ khi `disposable_club_created is True`; ledger-only còn bỏ bank receipt dù runner luôn tạo bank/club parent. Repro bằng clone có report/manifest khớp qua **real CLI**: positive exit 0; bỏ toàn bộ parent receipts **exit 0**; set các parent created/removed/verified_absent false **exit 0**; bank created true nhưng removed/verified_absent false và có error **exit 0**. Archive `60d459f76f7311e7`. Với contract ledger hiện hành, bắt buộc strict true receipts created/removed/verified_absent cho cả club và bank, SHA12 hợp lệ, không error; không được bỏ qua khi flags thiếu/false/string. Khi có bank ID sentinel phải đối chiếu receipt hash như contract bank cũ. Cập nhật positive synthetic ledger fixture cho đúng contract đầy đủ; không áp các yêu cầu ledger mới lên legacy bundles.
3. **LGR8 P2 — Hai regression bank output-guard bị phá.** `run_app_profile_heap.js:51,56`: đổi thông báo lỗi làm hai test đã chốt thất bại. Full suite **410 tests, 2 failures**, archive `17230924e366608c`: `test_refusal_on_nested_under_evidence_bundle` cần chuỗi `refusing to nest bank evidence under existing evidence bundle`; `test_refusal_on_preexisting_directory_preserves_bytes_and_no_mutation` cần `refusing to overwrite existing output directory for --bank-coverage`. Giữ contract bank hai-argument cũ và thông báo tương ứng; thêm ledger-mode wording nếu cần. Không sửa/giảm assertion của test bank cũ để nhận xanh.

## Kiểm chứng đã chạy

- Targeted ledger trong lúc hoàn tất sửa: 34 PASS, archive `7caea6757bc1fac9`; test parent club bổ sung được chạy riêng sau bàn giao: 1 PASS. Không cộng thành một lần chạy 35 chưa thực hiện.
- `flutter analyze`: 0 issues, archive `e617a3b9faed17f2`.
- `flutter test --reporter compact`: 247 PASS + 1 SKIP, archive `161897fa62b27bbb`.
- Full Python 410 có hai failure LGR8, không gọi là green suite.
- `build/ledger_ui_semantics_probe.cjs` exit 1 đúng LGR6; `build/ledger_parent_receipt_review_probe.py` exit 1 do cả ba mutant nhận exit 0. Đây là probe trên fake semantics/cloned bundles, không runtime mới.
- Mọi fixture/heap/browser runtime mới **NOT RUN**; app/backend/schema và historical evidence không đổi. Các cổng V8/risk decisions vẫn chưa được chốt.

## Fingerprint candidate R1 (SHA-256)

[Metadata review](ledger_round2_review_evidence/results.json); [probe UI đã đóng gói](ledger_round2_review_evidence/ui_semantics_probe.cjs), [probe parent receipts](ledger_round2_review_evidence/parent_receipt_probe.py). Hai probe được đóng gói từ bản chạy trong `build/`, chỉ chỉnh lookup về project root theo vị trí evidence. Chúng đánh giá source hiện tại; JSON giữ nguyên kết quả R1, không đổi thành kết quả sau sửa.

| File | SHA-256 |
|---|---|
| `run_app_profile_heap.js` | `de3248bc9c9bf449cbd0ebcc582d1a263645d04dfc2196623b3c447958be06d0` |
| `verify_evidence.py` | `f881687969345675465ad454e6ed5b7427a1b8bc97b12638ad174b44169e545d` |
| `disposable_ledger_fixture.js` | `d6248c8926e9d421eda904daa14f0508bce952c539ff10ed5254c24a34f81c2c` |
| `heap_oracle.py` | `4729d224c648b9541eaad117806090d970c7fa2a38fd32006e793273d4ad69dc` |
| `test_bh07_ledger_fixture.py` | `7c3cca92ddfc9285f197e7e81b84b8fcf16332d1ebf9ec604fd60b21c2dfacef` |
| `test_bh07_ledger_heap_coverage.py` | `b75b1aefd4debc6d7ce304bb55bc5fe5a60f959157b0e5a10aa9982b6ad789cb` |

**Chưa đạt.** Giao sửa toàn bộ LGR6–LGR8 vòng 2/2. Còn lỗi sau vòng này thì dừng và báo chủ dự án theo AGENTS, không tự mở vòng 3. Không merge/push/deploy/pilot hoặc đổi trạng thái NOT RUN thành PASS.
