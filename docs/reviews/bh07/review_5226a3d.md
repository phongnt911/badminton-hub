# Review retention attribution — vòng2/2

- Ngày28/10/2026 Asia/Saigon. Codex reviewer; không sửa source triển khai/app/backend/DB.
- Tested checkout/source/docs: `5226a3df77256c650b0032da9a101d419b7cc7ff`; worktree sạch trước kiểm chứng.
- Base review: `dcdb7ce51095d03afbbb7f28e4bbb5117f8a3e48` ([review_eda1ead](review_eda1ead.md)). Runtime QA tham chiếu vẫn b13e468; không retag thành runtime mới.

## Kết luận

**Chưa đạt vòng2/2: còn AT1 P1. Đóng AT2 P2; giữ AT3–AT6 đã đóng. Không có P0 hoặc P2 mới mở trong phạm vi.**

**Dừng và báo chủ dự án; không tự mở vòng3/sửa triển khai.** [AGENTS.md](../../../AGENTS.md) quy định: “Sửa theo review: viết test tái hiện lỗi trước, sửa toàn bộ phát hiện P0/P1/P2 được nêu (kể cả P2), tối đa 2 vòng. Còn lỗi sau 2 vòng thì dừng và báo chủ dự án.” Đây là lỗi validator của gói attribution, không phải bằng chứng app/runtime thực đã leak.

Giữ Đạt QA runtime local hai expense-ID b13e468 và tooling RP3-C,V1,V5b,Provider. Official residual risk rendered-title vẫn unattributed; toàn V2b/BH-07 chưa nghiệm thu. Không merge main/staging/production,deploy/pilot/BH-08.

## Rà soát

| Mục | Kết luận |
| --- | --- |
| AT1 P1 | Còn mở: đã chặn7mutant cũ nhưng vẫn false-valid khi payload chu kỳ lặp hoặc record/path/sentinel mâu thuẫn |
| AT2 P2 | Đóng: machine fields giữ app-wide UNKNOWN,hai ID là scoped observation;limits nói secondary paths possible,native NOT RUN;docs không còn kết luận app sạch toàn diện |
| AT3–AT6 | Giữ đóng:map/listener NOT RUN,log tracked5/5,84link tương đối tồn tại,sanitize các vị trí đã yêu cầu |

## AT1 — P1 còn mở: Risk matrix đúng8 tổ hợp chưa đảm bảo8 record nguồn được validate nhất quán

- File:dòng: `scripts/bh07_appheap/audit_retention_attribution.py:234–240` (chỉ đếm hai cycle payload,không check unique cycle/actor),`:292–322` (path riêng,không đối chiếu rendered scan;rr match chỉ path_len).
- Tái hiện:

  ```bash
  python docs/reviews/bh07/review_5226a3d_evidence/closure_controls.py
  ```

- Positive gốc exit0,valid=true. Ba mutant dưới đây cũng exit0,valid=true,status SUPPORTED_HYPOTHESIS_WITH_LIMITS:

  | Control | Input thay đổi | Lỗi kiểm chứng |
  | --- | --- | --- |
  | duplicate_cycle_payload | cycles[1] là bản sao cycle1(cohost);giữ risk matrix có cycle1/2 | Đã bỏ payload Member/cycle2 nhưng validator đọc cycle1 hai lần và nhận đủ2chu kỳ |
  | rendered_presence_contradiction | Tại cả8 rendered record,set sentinel.present=false,occurrences=0;path vẫn reachable=true | Artifact không nhất quán mà vẫn xác nhận rendered_title_retained=true vàpaths hợp lệ |
  | risk_path_hash_mismatch | Đặt mọi residual risk path_sha256_12 thành giá trị khác;giữ snapshot path hash | Không khớp provenance record→path mà vẫn valid vì chỉ so path_len12 |

- Kỳ vọng: valid chỉ khi payload cycles đúng unique1/2 vàactorpath theo contract,đủ8rendered snapshot/risk record cùng identity;present/count/reachable nhất quán;path hash/class/root/record identity khớp nguồn. Mutant phải FAIL/UNKNOWN vàCLI khác0,không phát artifact xác nhận đủ bằng chứng.
- Ảnh hưởng: gói điều tra có thể xác nhận bằng chứng mất một chu kỳ/actor hoặc mâu thuẫn scan/path. Không kết luận QA bundle thật bị sửa hoặc runtime app leak; chỉ chứng minh validator còn fail-open trong phạm vi AT1 đã giao.
- Cách sửa nếu được chủ dự án ủy quyền bổ sung: validate unique cycle payload vàđủ actor,đối chiếu scan↔path↔risk cho từng tổ hợp,không chỉ rr set/độ dài. Tái sử dụng semantic validator hiện hành nếu phù hợp để tránh gate yếu hơn. Test actualCLI ba control này với positive và7mutant cũ,JSON/exit cùng verdict. Không tự thay expectation để nhận data lỗi. Reviewer không sửa source hoặc tự giao vòng3.

## Reviewer tự chạy

- Python discover317/317;Flutter analyze0 issues;Flutter247passed+1skip. Exit0/log được lưu trực tiếp;không lấy log tác giả thay lượt chạy.
- Immutable probes:2positive0,7mutant cũ1. Closure controls:positive0,3mutant sai0. Xem [evidence](review_5226a3d_evidence/) và [commands](review_5226a3d_evidence/commands.md).
- Current attribution bundle5/5;4bundle lịch sử3/3 mỗi bundle,khớp manifest/Git,strict UTF-8 LF,secret scan0,hash trước/sau không đổi. QA semantic auditor0;không coi pass của auditor QA là validator attribution đã đủ.
-84link trong3doc tác giả tồn tại;diff app/backend rỗng,whitespace sạch. Reviewer chỉ thêm docs/evidence/status;own manifest verify readonly,không regenerate author bundle.

## NOT RUN

- Runtime browser/SQL/heap dump mới hoặc exhaustive engine source/path attribution: NOT RUN;runtime QA tham chiếu b13e468 giữ nguyên.
- Full V2b ngoài2expense ID,private models/cache/listener/charge/payment/bank thật/receiver/ledger,tất cảretainer paths: NOT RUN.
- Dart VM desktop/mobile,browser khác,mobile web/đa tab/concurrent actor/tải thật: NOT RUN.
- Managed Supabase/PITR/offsite/encryption/retention,concurrent writers,staging/production/restore thật,banking/webhook,rehearsal/pilot/full BH-07: NOT RUN.

Bước tiếp là quyết định chủ dự án về xử lý AT1 sau giới hạn2vòng. Không tự động chuyển cổng,không tự nhận residual-risk acceptance thành PASS kỹ thuật.
