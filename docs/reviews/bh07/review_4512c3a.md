# Review BH-07A — 4512c3a

Ngày 20/10/2026 (Việt Nam). Tested HEAD `4512c3a19e7c22f2adc4a9f3269cbabe8acd9d09`, nhánh `feat/bh07a-db`, code/runner/migration `c339a47fdcb08e50811079bd89df7a1f9f53908a`, base main `62d2c67`. Lib/test/migration của HEAD trùng code SHA; thay đổi sau code chỉ tài liệu/bằng chứng. Theo AGENTS, `docs/ai/REVIEWER.md` trên main, docs/04/08/09 và đầu bài docs/25; đọc diff main...HEAD. Không sửa code tác giả, migration hoặc test triển khai.

## Phát hiện P0/P1/P2

Không có phát hiện cần mở trong phạm vi kiểm chứng phần A tại tested HEAD.

## Kiểm chứng độc lập

[Summary/hash](review_4512c3a_evidence/summary.json), [analyze](review_4512c3a_evidence/analyze.log), [Flutter](review_4512c3a_evidence/flutter.log), [exit các runner](review_4512c3a_evidence/regression-exits.json), [orchestrator](review_4512c3a_evidence/run_regression.py), [BH-07 JSON](review_4512c3a_evidence/bh07_test_results_20261020110908.json), [BH-07 log](review_4512c3a_evidence/run_bh07_tests.log). Các JSON/log hồi quy mới nằm cùng thư mục, không dùng bằng chứng tác giả làm kết quả reviewer.

| Nhóm | Reviewer tự chạy |
|---|---|
| Flutter 3.47.7 / Dart 3.13.5 analyze --no-pub | 0 issue, exit 0 |
| flutter test --no-pub | 190/190 PASS, exit 0 |
| BH-02 + extended | 33 +14 PASS |
| BH-03 + retry/concurrency | 48 +22 PASS |
| BH-04 | 44 PASS |
| BH-05 | 90 PASS |
| BH-06 | 84 PASS |
| Tổng hồi quy DB BH-02..06 | 335/335 PASS; mọi runner exit 0 |
| Runner BH-07 mới | 23/23 PASS: 21 CLEAN +2 nâng cấp, exit 0 |
| Tích hợp BH-06 | 7/7 PASS, exit 0 |
| Nâng cấp BH-06 | 3/3 PASS, exit 0 |
| RPC probe reviewer độc lập | 9/9 kiểm tra PASS, exit 0 |

[Source probe](review_4512c3a_evidence/reviewer_probe.py), [log](review_4512c3a_evidence/reviewer-probe.log), [kết quả có cấu trúc](review_4512c3a_evidence/reviewer-probe-results.json). Probe tạo DB riêng theo full migration và dùng dữ liệu giả. Sau complete, tạo 60 intent thu tiền mặt bằng RPC dưới role authenticated: trang finance 50 dòng chỉ cộng 50.000, summary phải tổng hợp 60.000 đã thu và 40.000 còn nợ trên due 100.000. Kiểm whitelist không có contact/bank/raw player/payment; cohost chỉ thấy count và NULL tiền; finance staff thấy đúng scope, khi inactive phải mất cả summary/history; participant, owner CLB khác và outsider đều bị chặn. Reverse một payment sau complete phải đưa paid/outstanding về 59.000/41.000, giữ lifecycle completed. Không lấy kết quả SUM từ trang làm oracle cho tổng toàn buổi.

Runner BH-07 kiểm complete gate/role/version/replay/audit, công nợ còn sau complete, lịch sử/phân trang/filter/detail, summary/privacy/stale, các đường tài chính sau complete, hai complete đồng thời và dữ liệu completed trước nâng cấp. Quy tắc lọc history theo starts_at và whitelist theo quyền được đọc cùng [audit/contract A](bh07a_audit.md); không suy các endpoint đề xuất trong đặc tả đích thành API đã có.

Tất cả DB chạy PostgreSQL17 Docker cô lập --network none, Auth stub và SET ROLE app. Các nhóm dùng DB riêng; extended/retry chạy sau runner nền tương ứng. Probe tái sử dụng helper dựng fixture nhưng có assertion riêng, không chạy main của runner tác giả; các phép thu tiền/tổng kết đọc bằng RPC app role, không dùng SELECT bằng postgres để kết luận quyền đúng. Postgres chỉ dựng migration và cấp/thu hồi role fixture. Không apply staging/production.

Không đổi lib/test/migration trong lượt review. Metadata worktree_dirty có thể là true do JSON runner khác sinh tạm; hash nguồn và tested HEAD lưu trong summary. 335 hồi quy, 23 BH-07, 7 tích hợp, 3 nâng cấp và 9 kiểm tra probe là các nhóm riêng. Không chạy lại hai probe I1/I2 BH-06 lịch sử trong lượt A này; chúng giữ bằng chứng tại review BH-06, không gọi là kết quả mới.

## Kết luận

**Đạt phần A BH-07 tại `4512c3a`** trong phạm vi DB/RPC/projection và bằng chứng local nêu trên. Không phải nghiệm thu B/C/D, toàn BH-07 hoặc pilot. Không tự chuyển phần tiếp theo, merge main hoặc deploy; giữ trạng thái Chờ review phía tác giả làm lịch sử và cập nhật trạng thái hiện hành theo kết luận này.

**NOT RUN:** BH-07 model/repository/provider/UI mới, HTTP/PostgREST/JWT/Supabase Auth thật, repository nối DB qua HTTP; mobile/web/deep link e2e, mất mạng/mở lại app; ngân hàng/tải ảnh VietQR/chuyển tiền thật; staging/production, backup/restore rehearsal và concurrency HTTP. Concurrency PostgreSQL/Auth stub trong runner không thay kiểm HTTP/pilot.
