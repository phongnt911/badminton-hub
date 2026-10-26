# Review V2b app-profile heap — sửa ngoại lệ AH7/AH8

- Ngày: 26/10/2026, Asia/Saigon. Reviewer: Codex, không sửa source triển khai.
- Base review: `268735ccd071936bada7cbcdf81fad6c87187e00`.
- Tested source runtime tác giả: `c3ca02e4f4a17cea7ac48526c398b212ab1445a9`.
- Docs/checkout reviewer: `0f11bb4239f2aedd1fe17a789b34474026e06577`, sạch trước kiểm chứng.
- Phạm vi: script/test kiểm chứng + docs/evidence. Codex từng làm gói Provider/browser lịch sử; không dùng chúng thay phép đo app-profile mới.

## Kết luận

**Chưa đạt gói V2b app-profile heap. Đóng AH7 và AH8; còn 1 P2 mới AH9**, không có P0/P1. Các gate cũ giữ kết luận trong phạm vi đã kiểm. Phát hiện mới là mutant được handoff mục7.2 yêu cầu thử, không phải kết luận app leak hoặc bundle runtime tác giả đã bị sửa.

Phần sửa AH7/AH8 đáp ứng các ca đã báo: literal/escaped có cùng presence/count, cycle retained escaped FAIL; missing length/hash có finding, metadata sentinel và trạng thái unavailable có controls. Tuy nhiên, auditor vẫn chứng nhận bundle có count mâu thuẫn presence ở AH9 bên dưới, nên chưa chốt gói kiểm chứng.

**Dừng và báo chủ dự án quyết định phần còn lại; không tự mở đợt sửa tiếp hoặc sửa source.** Handoff xác định đây là ủy quyền ngoại lệ sau dừng vòng2/2; không coi ngoại lệ sửa AH7/AH8 là quyền tự sửa lỗi mới. Quy định [AGENTS.md](../../../AGENTS.md): “Sửa theo review: viết test tái hiện lỗi trước, sửa toàn bộ phát hiện P0/P1/P2 được nêu (kể cả P2), tối đa 2 vòng. Còn lỗi sau 2 vòng thì dừng và báo chủ dự án.” Provider/tooling, V1, V5b giữ Đạt local; V2b chưa đóng, toàn BH-07 chưa nghiệm thu.

## Phát hiện còn mở

### AH9 — P2: Count và presence mâu thuẫn vẫn được chứng nhận nhất quán

- File:dòng: `scripts/bh07_appheap/heap_oracle.py:256`; điểm gọi audit `scripts/bh07_appheap/verify_evidence.py:263`.
- Cách tái hiện:

  ```bash
  PYTHONPATH=. python docs/reviews/bh07/review_0f11bb4_evidence/count_controls.py
  ```

- Input: positive synthetic bundle đủ hai chu kỳ, metadata bank/probe đầy đủ, report tương ứng, hash LF hợp lệ. Chỉ thay `occurrences` ở `post_actor` chu kỳ1 rồi rehash. Không sửa app/backend/bundle tác giả.
- Kỳ vọng: với scan `ok=true`, count phải là int không âm thực, presence bool thực và `present == (occurrences > 0)`. Dữ liệu scan không nhất quán phải có finding và FAIL/exit1 trước khi quyết định gate.
- Thực tế:
  - Bank `present=false, occurrences=1` ⇒ `problems=[]`.
  - Probe `present=true, occurrences=0` ⇒ `problems=[]`.
  - Count `-1` hoặc `0.5` ⇒ `problems=[]`.
  - CLI auditor chạy thật trên clone có bank false/count1 in PASS và exit0 (`contradictory_count_cli`). Positive không mutation cũng trả `[]`; hash trước/sau các clone không đổi.
- Nguyên nhân: `decide()` chỉ đọc cờ `present`; auditor tái gọi cùng hàm nhưng không validate count/presence. Report không chứa count nên đổi count không tác động kiểm Markdown; metadata length/hash chỉ bảo vệ raw-value scan, không bảo vệ tính nhất quán của scan record.
- Ảnh hưởng: bundle sai dữ liệu có thể vẫn được gọi “internally consistent”, không bảo đảm claim không còn bank/probe sống theo chính kết quả đếm được công bố. **24 sentinel records trong bundle runtime hiện tại đều nhất quán** qua audit reviewer; mutant không chứng minh chúng thực sự lỗi hay app giữ bank.
- Cách sửa khuyến nghị: schema/validator scan dùng chung ở ranh giới oracle/auditor; với scan thành công bắt buộc `type(occurrences) is int`, count>=0, `type(present) is bool`, và quan hệ trên. Thiếu/sai kiểu/mâu thuẫn ⇒ FAIL có finding; scan hỏng giữ null/FAIL như hiện tại. Bổ sung test count sai, missing/null/bool count, mâu thuẫn hai hướng, và CLI rejection; giữ positive decoded literal/escaped, các guard metadata/probe/cleanup. Fixture test phải cấp count đúng, không nới kỳ vọng để chấp nhận mâu thuẫn.

## Kiểm chứng reviewer tự chạy

Evidence riêng: [review_0f11bb4_evidence/](review_0f11bb4_evidence/). Probe cũ không bị sửa. `count_controls.py` in quan sát; exit0 của script không có nghĩa negative input đã bị chặn.

| Lệnh/kiểm tra | Kết quả |
| --- | --- |
| 5 suite Python theo handoff | exit0,123/123, không skip |
| `node scripts/bh07_appheap/build_guard.js --self-test` | exit0,8/8 |
| `closure_controls.py` nguyên bản | exit0; literal/escaped đều present=true,count1; retained cycle FAIL; missing length/hash bị chặn |
| `extra_controls.py`, `probes.py` nguyên bản | exit0; negative cũ bị chặn, positive hợp lệ PASS |
| `build_probe.js` nguyên bản | exit1 đúng kỳ vọng từ chối reuse |
| `link_audit.py` nguyên bản | exit0, `[]` |
| `python -X utf8 scripts/bh07_appheap/verify_evidence.py` | exit0 trên bundle tác giả |
| `flutter analyze --no-pub` | exit0, no issues |
| `flutter test --no-pub` | exit0,247 PASS+1 SKIP; HTTP/Auth suite mặc định skip, không có HTTP mới |
| `node --check scripts/bh07_appheap/run_app_profile_heap.js` | exit0 |
| Count consistency mutant mới | exit0, các false-green AH9 ghi trong `count_controls.json`; CLI mutant exit0 sai kỳ vọng |
| Scope/whitespace | `lib/`,`test/`,`supabase/` không đổi từ base; source tree docs commit bằng tested source; diff-check exit0; evidence reviewer cũ không đổi |
| Manifest/readonly | bundle tác giả3/3 entries,4 file gồm manifest; hash sau mọi lệnh bằng Git blob docs commit, UTF-8 LF thực tế hợp lệ; không generate/chạy runner vào author bundle |

`provenance.json` ghi SHA/dirty/exit/count,hashes tác giả và kiểm count/presence 24/24. Runtime metadata tác giả ghi source sạch c3ca02e,2cycle/8snapshot,build profile46,7s,39 artifact hash,served_match vàcleanup; chỉ hai file entry index/main được kiểm served bytes theo guard. Không gán log runtime tác giả thành lần chạy reviewer. Reviewer Linux/Node24.19.0/Flutter3.47.7; tác giả Windows/Node24.21.0/Flutter3.47.6/Chrome155. Logs reviewer chuẩn hóa progress CR sang LF và bỏ terminal padding khi đóng gói; bytes tác giả không đổi.

## NOT RUN

| Hạng mục | Giới hạn |
| --- | --- |
| Runtime Chrome/profile reviewer `--cycles 2` | NOT RUN: không có API local54321; dung lượng thực ghi tại runtime_preflight.json chỉ khoảng636MiB, chưa đủ stack/profile build/dump cô lập. Không tự dựng/reset/đổi DB. |
| Parse lại tám dump tác giả | NOT RUN: dump đã xóa. Audit metadata/source/log không thay phép đo độc lập. |
| Chrome155 thực sự dùng bank escaped trong tám dump; optional expense unavailable ở runtime | NOT RUN; representation/unavailable được kiểm bằng fixtures; expense runtime có fixture nhưng chưa được màn hình nạp. |
| Mọi retained object/path/cache/listener, số dư/doanh thu/ghi chú và Dart VM desktop/mobile | NOT RUN; bank sentinel không chứng minh toàn bộ §4.4. Giới hạn V8/web profile giữ nguyên. |
| Windows junction riêng; browser/device khác, offline/deep link mới, HTTP/Auth/DB runtime mới | NOT RUN trong lượt reviewer này, không đổi verdict local các gói cũ. |
| Managed backup/PITR/offsite/encryption/retention, concurrent writers, ngân hàng/webhook, staging/production, tải/rehearsal/pilot, BH-08 và nghiệm thu toàn BH-07 | NOT RUN; không merge main,deploy/chuyển pilot. |

**Kết luận: Chưa đạt gói kiểm chứng; AH7/AH8 đã đóng, AH9 P2 chờ quyết định chủ dự án.**
