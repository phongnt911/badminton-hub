# Chốt điều phối V2b retained-path runtime — 3b393d3

- Ngày: 28/10/2026, Asia/Saigon. Vai trò: Codex điều phối/audit hồ sơ QA; không phải lần đo runtime độc lập mới của điều phối.
- Bàn giao QA: `3b393d33dd3dd773a92c1e4f2f4cbfd27af259e6`, nhánh `feat/bh07-retained-path-runtime-review`.
- Runtime QA tested source: `b13e468d33e0d96437b58bb2da6088bff689b9eb`, `git_dirty=false`, dirty paths rỗng; source publisher `29f44a8e8f86ff68e3ebe54f981cbb73ea5ceb2b`.
- [Báo cáo QA](review_runtime_b13e468.md), [bundle QA](review_runtime_b13e468_evidence/), [audit điều phối](review_3b393d3_evidence/).

## Kết luận

**Đạt trong phạm vi runtime local Web profile retained-path với hai expense-ID sentinel, theo QA độc lập và audit điều phối. Đóng công việc QA runtime này.** Không có P0/P1/P2 mở trong phạm vi bàn giao. Giữ kết luận tooling RP3-C đã đóng; Provider/tooling,V1,V5b giữ Đạt local trước đó.

**Chưa đóng toàn V2b §4.4, chưa nghiệm thu BH-07.** Hai title đã render còn reachable sau logout/đổi actor:8 residual risk, attribution `unattributed`. Identity/roster ở Cohost không được phép suy thành authorized chỉ từ heap; bank pattern không distinctive và receiver không được tải không chứng minh field bank/receiver thật đã sạch. Đây là giới hạn thực của phạm vi, không phải toàn bộ private models/caches/listeners được xác minh.

QA tự khai không tham gia viết/sửa gói. Điều phối từng review gói lịch sử, chỉ audit dữ liệu QA ở lượt này, không nhận là người tự dựng/chạy UI/runtime mới. Không merge main/staging/production, deploy/pilot/BH-08.

## Phát hiện

| Mức | file:dòng | Kết luận |
| --- | --- | --- |
| P0 | — | Không có phát hiện mở trong phạm vi |
| P1 | — | Không có phát hiện mở trong phạm vi |
| P2 | — | Không có yêu cầu sửa thêm trong gói bàn giao |

## Điều phối tự kiểm

- Diff b13e468..3b393d3 đúng5 file docs/evidence; không đổi lib/test/supabase/scripts/tests. Worktree sạch trước audit; git diff --check sạch.
- Tự chạy semantic auditor trên bundle QA:exit0, và R1:exit0. Hai bundle cũ retained_path_evidence/app_profile_heap_evidence:exit1 đúng kỳ vọng. Không đổi kỳ vọng để nhận bundle cũ.
- Tự verify read-only5 bundle (QA mới,R1,retained cũ,app-profile cũ,bank QA cũ): mỗi bundle3/3 payload hash khớp manifest và Git blob, strict UTF-8 LF,0 secret/JWT theo scanner. So hash mọi file trước/sau không đổi. Bốn bundle lịch sử không đổi từ base.
- Đối chiếu8 snapshot,16 finance-ID record:2 chu kỳ Owner→logout→Cohost/Member, cùng document mỗi chu kỳ; finance ID có/reachable ở owner_active, occurrences0/reachablefalse ở baseline/post_logout/post_actor. Probe kiểm soát tồn tại, metadata/path/verdict được auditor tính lại.
- Fresh build profile QA57043ms,39 artifact hash,served_match=true; không reuse theo báo cáo QA và source runner giữ nguyên. Mỗi giá trị chỉ xuất bản một path, không phải tất cả retainer paths.
- Cleanup receipt boolean hợp lệ:dump/profile đã xóa,raw_snapshots_remaining0;fixture72412d54c227 created/removed/verified_absent đều true. report.md và run.log nhất quán. SQL độc lập fixture0 được QA báo trong report; không có raw SQL stdout riêng và điều phối không query DB, nên không gọi là SQL mới điều phối đã chạy.
- QA khai312Python/34oracle/6fixture/8guard/analyze0/247Flutter+1skip. Bundle4 file không kèm log stdout từng suite; điều phối không xác nhận lại các count này bằng lần chạy mới. Hồi quy source tooling đã được kiểm ở [review_c509aee](review_c509aee.md), không cộng dồn số test.

Audit chi tiết,hashes,command vàexit:[audit.json](review_3b393d3_evidence/audit.json). Manifest riêng của điều phối cũng verify readonly, lưu trong evidence; không regenerate manifest QA/tác giả.

## NOT RUN / phần còn mở

| Cổng/phần | Trạng thái / điều kiện đóng |
| --- | --- |
| Runtime hoặc SQL mới do điều phối trực tiếp chạy | NOT RUN; lượt này audit QA đã chạy, không thay thế bằng phép đo khác |
| Toàn V2b:models/caches/listeners,charge/payment/bank thật/receiver và các path ngoài hai expense-ID | NOT RUN; cần lập coverage map từ code tới luồng thật, sentinel thích hợp và runtime riêng, không suy từ bank-pattern UUID |
| Nguyên nhân/title rendered retained | Chưa phân định engine/app, giữ8 residual risk unattributed; cần điều tra attribution trên build/SDK khớp QA, không tự waive |
| Identity được Cohost fetch lại có đúng quyền | Heap không xác lập quyền; không suy authorized từ việc còn reachable |
| Dart VM desktop/mobile,browser khác,mobile web,đa tab/actor đồng thời,tải thật | NOT RUN |
| Managed Supabase/PITR/offsite/encryption/retention,concurrent writers,staging/production/restore thật | NOT RUN |
| Banking/webhook,tải/rehearsal/pilot,V8 nghiệm thu toàn BH-07 | NOT RUN |

Bước tiếp đề xuất: giao AI thực thi điều tra residual rendered-title retention và lập coverage còn thiếu, chỉ script/fixture/docs local; không sửa app/backend khi chưa có kết luận và ủy quyền sửa cụ thể. Mỗi claim phải giữ provenance/giới hạn, không thay verdict cũ thành nghiệm thu toàn V2b.
