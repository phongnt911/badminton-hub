# Codex sửa trực tiếp Retention Attribution — vòng3 theo ủy quyền

- Trạng thái: **Đạt trong phạm vi AT1 retention attribution tooling**, đã đóng bởi reviewer độc lập tại [review_41c1ea1.md](review_41c1ea1.md) ([evidence](review_41c1ea1_evidence/)). (Lịch sử khi bàn giao: Chờ reviewer độc lập chốt; Codex tự sửa/tự kiểm, KHÔNG phải review độc lập.)
- Chủ dự án đã ủy quyền bổ sung: **“mở vòng 3 sửa”**, sau khi dừng2vòng theo AGENTS.
- Base review: `a35c219d7c8f61742ad0753359681e72c9bf5a32` ([review5226a3d](review_5226a3d.md)).
- Tested auditor source: `f11d20f6c5025f7f774c266298bc0309fcd0de0c`; sạch trước full self-check, source hashes trong [provenance](retention_attribution_codex_r3_evidence/provenance.json).
- Runtime QA tham chiếu vẫn `b13e468d33e0d96437b58bb2da6088bff689b9eb`, không có lần đo mới.
- Evidence riêng: [retention_attribution_codex_r3_evidence/](retention_attribution_codex_r3_evidence/). Giữ nguyên byte các bundle cũ.

## Phạm vi sửa

AT1: kiểm source cycle payload có đúng1 và2,actor Cohost/Member tương ứng;không dùng chỉ length2/risk matrix để suy đủ chu kỳ. Dùng scan_problems của oracle hiện hành để kiểm schema;đối chiếu present/count với reachable/string_nodes;kiểm path_len vàhash từ frames. Đối chiếu mỗi risk với source path đúng cycle/epoch/sentinel vềhash/root/length,class rendered vàattribution unattributed;giữ nguyên kiểm đủ8tổ hợp đã có. Bốn finance sentinel phải giữ đúng class/scope đã đo.

AT2–AT6 giữ kết luận trước:app-wide UNKNOWN,official risk unattributed,listeners/full coverage NOT RUN,portable links/sanitize/logs. Không sửa lib/,Flutter unit test,DB/migration/RPC/model/repository/provider/UI/contract.

## Tự kiểm

- TDD red trước sửa:2method,8assertion fail,exit1;green targeted7/7,exit0.
- Full self-check319Python,Flutter analyze0,Flutter247+1skip;numeric exits/log trong evidence. Đây là tự kiểm,không phải verdict reviewer.
- Immutable original/extra/closure probes:3positive CLI0,10negative CLI1,không đổi file/kỳ vọng. Thêm control actor/root/class/ok/frame-hash/scope trong unittest.
- Auditor generated output mới từ QA sanitized sourceb13e468:exit0;không chạy default --out-dir vào evidence lịch sử.
-5bundle lịch sử verify readonly,hash không đổi;QA/R1 semantic0,2bundle obsolete semantic1 như trước. Own manifest verify readonly vàGit blob audit trước commit.

## Reviewer tiếp theo phải kiểm

Đọc AGENTS,review5226a3d và file này. Review source f11d20f6 + docs tip của bàn giao,không dùng log tự kiểm thay lần chạy mới. Phát lại3probe nguyên bản,Python discover,analyze,Flutter test;run auditor với --out-dir temp riêng,không ghi lên bundle cũ. Kiểm scan/path/risk/actor mutations vàAT2 machine fields,manifest readonly/secret scan,provenance source vs runtime. Ghi report riêng vàchốt Đạt/Chưa đạt trong phạm vi AT1 tooling;không nhận self-check này là độc lập.

## NOT RUN

Runtime browser/heap/SQL/DB mới;full V2b ngoài2expense ID,charge/payment/bank thật/receiver/ledger/listener/object graph/exhaustive paths;Dart VM desktop/mobile,browser khác,đa tab/actor,tải thật. Managed Supabase backup/PITR/offsite/encryption/retention,concurrent writers,staging/production/restore thật,banking/webhook,rehearsal/pilot/nghiệm thu toàn BH-07 giữ NOT RUN.

QA runtime hai expense-ID b13e468,RP3-C,V1,V5b giữ kết luận local đã chốt;toàn V2b/BH-07 chưa nghiệm thu,không merge/deploy/pilot/BH-08.
