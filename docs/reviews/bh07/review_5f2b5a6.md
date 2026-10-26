# Review V2b app-profile heap — chốt sửa AH9

- Ngày: 26/10/2026, Asia/Saigon. Reviewer: Codex, không sửa source triển khai.
- Base review: `a1263548cf06732475fe75577d141b0eedd75210`.
- Tested source runtime tác giả: `c04ce551a4cb7fa8cbddcd5f06dbc790a39889f6`.
- Docs/checkout reviewer: `5f2b5a6883295554353ce5301eeb58539e6b88d1`, sạch trước kiểm chứng.
- Phạm vi: sửa AH9 ở oracle/auditor, test kiểm chứng, bundle mới và trạng thái. Codex từng làm gói Provider/browser lịch sử; không dùng lịch sử đó thay phép đo app-profile.

## Kết luận

**Đạt trong phạm vi bản sửa AH9 và gói công cụ kiểm chứng V8/web-profile local. Đóng AH9; không còn P0/P1/P2 mở trong phạm vi review này.** AH1–AH8 giữ kết luận đã đóng của các báo cáo trước, các probe tương ứng được chạy lại nguyên bản.

Đóng phần sửa công cụ trên nhánh; giữ nhánh chưa merge. **Không kết luận Đạt toàn bộ cổng V2b §4.4 hoặc toàn BH-07**: runtime Chrome của reviewer và đo retained paths/toàn bộ model/cache/listener còn NOT RUN như bảng cuối. Metadata runtime tác giả được audit, không coi là lần chạy reviewer. Provider/tooling, V1 và V5b giữ Đạt local; không merge main,deploy,pilot hoặc chuyển BH-08.

## Phát hiện

| Mức | file:dòng | Kết quả | Hướng xử lý |
| --- | --- | --- | --- |
| P0 | — | Không có phát hiện mở trong phạm vi | — |
| P1 | — | Không có phát hiện mở trong phạm vi | — |
| P2 | — | Không có phát hiện mở trong phạm vi | — |

AH9 tại `scripts/bh07_appheap/heap_oracle.py:227` và `scripts/bh07_appheap/verify_evidence.py:266`: **Đóng**. Validator `scan_problems` được dùng ở ranh giới quyết định oracle và audit từng mốc. Probe cũ giữ nguyên input/kỳ vọng: positive trả `[]`; hai hướng mâu thuẫn, count âm/không nguyên đều có finding. CLI thật trên clone trong repo trả **exit1**, stdout có **`contradicts`**, stderr rỗng; không dựa vào crash ngoài repo để chứng minh từ chối. Lỗi control CLI ban đầu được handoff công bố; reviewer xác minh test hiện hành đòi cả nonzero và `contradicts` trong stdout.

## Bằng chứng reviewer tự chạy

Evidence riêng: [review_5f2b5a6_evidence/](review_5f2b5a6_evidence/). Không sửa source/probe cũ, không generate hoặc ghi đè author bundle. Reviewer chỉ tạo fixture tạm và thu log/báo cáo riêng.

| Lệnh/kiểm tra | Kết quả độc lập |
| --- | --- |
| 5 suite Python theo handoff | exit0,146/146,không skip |
| `python -X utf8 scripts/bh07_appheap/heap_oracle.py self-test` | exit0,15/15; fixture self-test nằm trong tempdir riêng của reviewer và được xóa |
| `node scripts/bh07_appheap/build_guard.js --self-test` | exit0,8/8 |
| `count_controls.py` nguyên bản | exit0 của probe quan sát; positive `[]`,4 mutant có finding; CLI mutant exit1 kèm `contradicts`,readonly |
| `closure_controls.py` nguyên bản | exit0; literal/escaped cùng presence/count,retained cycle FAIL,missing length/hash bị chặn |
| `extra_controls.py`, `probes.py` nguyên bản | exit0; negative cũ bị chặn,positive hợp lệ PASS |
| `build_probe.js` nguyên bản | exit1 đúng kỳ vọng từ chối reuse |
| `link_audit.py` nguyên bản | exit0,`[]` |
| Control bổ sung reviewer | 5/5 kỳ vọng: float `1.0`,presence int0/int1,scan hỏng khai presence đều FAIL; count1000/presence đúng PASS. `reviewer_relation_controls.py` dùng validator/oracle thật,không mock app |
| `python -X utf8 scripts/bh07_appheap/verify_evidence.py` | exit0 trên bundle tác giả |
| `flutter analyze --no-pub` | exit0,no issues |
| `flutter test --no-pub` | exit0,247 PASS+1 SKIP; HTTP/Auth suite mặc định skip,không có HTTP runtime mới |
| `node --check scripts/bh07_appheap/run_app_profile_heap.js` | exit0 |
| Source scope/whitespace | `lib/`,`test/`,`supabase/` không đổi từ base; source tree docs commit bằng tested source; diff-check exit0; reviewer evidence cũ giữ nguyên |
| Manifest/readonly | Author bundle3/3 entries,4 file gồm manifest; strict UTF-8 LF;hash sau mọi lệnh bằng Git blob docs commit; không thấy secret theo mẫu và raw-sentinel scan auditor; không sửa byte tác giả |

`provenance.json` ghi source/docs/dirty/exit/count,hashes author bundle; cả24 record runtime đều count/presence nhất quán. Audit metadata runtime tác giả: source sạch c04ce55,2cycle/8snapshot,bank count1 khi Owner active/count0 sau logout/đổi actor,probe sống,build profile32,7s,39 artifact hash,served_match,cleanup. Guard đối chiếu byte server của hai entry index/main; không gọi là kiểm response đủ39 artifact. Các số này là runtime **tác giả**,không gộp vào số reviewer tự chạy.

Reviewer Linux/Node24.19.0/Flutter3.47.7; tác giả Windows/Node24.21.0/Flutter3.47.6/Chrome155. Logs reviewer chuẩn hóa progress CR sang LF và bỏ terminal padding khi đóng gói; bytes tác giả không đổi. Các nhóm test/controls được liệt kê theo từng lệnh,không cộng dồn thành số ca runtime độc lập.

## NOT RUN / giới hạn kết luận

| Hạng mục | Trạng thái / điều kiện đóng |
| --- | --- |
| Reviewer chạy Chrome/profile `run_app_profile_heap.js --cycles 2` | **NOT RUN**: local API54321 không chạy;đĩa trống663.220.224byte (~632MiB),chưa đủ stack/profile build/snapshots cô lập. Cần QA/runtime độc lập trên máy đủ môi trường,source sạch và evidence riêng;không thay bằng log tác giả. |
| Parse/replay lại tám dump tác giả | NOT RUN: dump đã xóa,reviewer chỉ audit metadata/log/source và fixtures. |
| Retained paths,tất cả model/cache/listeners,ghi chú/số dư/doanh thu ngoài bank sentinel | **NOT RUN**; một sentinel bank không chứng minh mọi tiêu chí §4.4. Cổng V2b đầy đủ chưa đóng. |
| Dart VM desktop/mobile;browser/device khác | NOT RUN;gói này chỉ V8/dart2js web profile. |
| Chrome155 thực sự dùng bank escaped;expense unavailable runtime | NOT RUN;representation/unavailable chỉ có fixture controls. Expense fixture có nhưng chưa được màn hình nạp. |
| Windows junction độc lập;offline/deep link mới,HTTP/Auth/DB runtime mới | NOT RUN trong lượt reviewer này;giữ verdict local các gói cũ. |
| Managed backup/PITR/offsite/encryption/retention,concurrent writers,banking/webhook,staging/production,tải/rehearsal/pilot,BH-08,nghiệm thu toàn BH-07 | NOT RUN;không merge/deploy/pilot. |

**Kết luận: Đạt bản sửa AH9 và gói công cụ V8/web-profile local; giữ nguyên các giới hạn/NOT RUN trên.**
