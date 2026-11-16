# Đồng bộ máy và audit điều kiện V8 — 12/11/2026

**Toàn BH-07/V8 chưa đủ điều kiện nghiệm thu.** Đây là audit source/provenance/artifact, không chạy Docker/HTTP/DB/heap/backup/restore mới và không ký risk acceptance thay owner.

## Tuyến source hiện hành

Checkout local trước lượt này vẫn ở `423f354`, trong khi fetch cho thấy remote feature đi trước18commit tại `aa755b5`. Đợt producer local ngày12/11 đã dựa trên checkout cũ; không nhập nó vào runner remote đã có runtime. Đã lưu16file local vào commit `fdf1fd8`, nhánh `archive/bh07-producer-local-20261112`, rồi fast-forward `feat/bh07-completion-local` tới `aa755b5`. Không merge main, không cherry-pick runner cũ, không force-push. Archive chỉ lưu local; chưa push nhánh archive. File `.codex/anti-v4-read-session.local.json` vẫn untracked/inert, không thuộc source candidate và không kích hoạt quyền global.

V4 hiện hành kế thừa [runtime sạch7589179](recovery_site_url_runtime_final_20261110.md), **PASS local/staging-like**. Mốc source/runtime và review của máy trước được giữ nguyên attribution. Kết quả546Python của tuyến archive chỉ thuộc candidate `cdda0b…67917f`, không gán cho aa755b5 hoặc nâng thành runtime mới.

## Kiểm mới trên aa755b5

| Kiểm tra | Kết quả |
| --- | --- |
| `python tests/test_bh07_v4_runtime_collection.py` | 53 PASS, exit0 |
| `python scripts/bh07_backup/v4_concurrent_probe.py` | 49 controls PASS, exit0 |
| Diff runner/probe/runtime-collection từ7589179 tới HEAD | Rỗng; không có source V4 mới cần retag runtime |
| Validator hiện hành trên summary/source/restored fingerprints7589179 | ok=true, verdict=PASS, findings rỗng; audit script chỉ đọc artifact, exit0 |
| SHA256 summary7589179 | `c3eda1aa1e7cf0d22cb33ef6dace1460439a857f99ed0d5d0dbed37e0f40819a`, khớp báo cáo |
| Web matrix manifest | 3/3 hash khớp cho Edge, Firefox headless và provenance |
| Provenance finance provider | Git blob `7693b5d628aeca4391bdee66de98e2a59e2f728f` khớp; raw hash LF/CRLF trên Windows không tự chứng minh source drift |
| Connected Supabase listing | Chỉ thấy1project badminton-hub INACTIVE trong connection này; không tạo/activate/query project, không suy sang account khác |
| Docker inventory chỉ đọc | 11container Supabase hiện có, vector restarting; không có stack V4; không can thiệp tài nguyên hiện có |

Không chạy lại full Python/Flutter vì lượt này chỉ đồng bộ source đã có review và sửa tài liệu. Những count full suite/runtime/Web trước đây giữ attribution lịch sử. Script audit tạm ở `.build/bh07-sync-audit-20261112.py` kiểm hash, sourceSHA, gọi `validate_v4_rehearsal` với ba artifact đã công bố và đối chiếu manifest Web; không thực thi main runner hay tạo tài nguyên.

## Audit V8 độc lập

Reviewer riêng đọc core A/B/C/D/HTTP/Auth/concurrency/V1/R0 và điều kiện §4.11: các báo cáo chính có closure trong phạm vi, principal SHA resolve; V1 gắn đúng runtime reviewer6283dbb. Reviewer cũng tự đối chiếu3/3hash Web và blob provenance. Không gọi audit hồ sơ này là reviewer đã chạy lại runtime hoặc kiểm mọi link trong toàn bộ lịch sử.

Finding tài liệu: readiness còn chỉ dẫn giao lại FH1–FH4 và mô tả V4/V2 cũ. Đã cập nhật phần vận hành §3.2/§4.4/§5 và hàngV2 trong ma trận; giữ review lịch sử theo nhãn lịch sử, không mở lại lỗi đã đóng hoặc thay byte evidence.

## Điều kiện còn thiếu

| Cổng | Bằng chứng còn thiếu | Trạng thái quyết định |
| --- | --- | --- |
| V2 | Full device/OS/deep-link/lifecycle matrix; Android đã dừng theo owner; Firefox có cửa sổ UNKNOWN, clipboard Edge/Firefox NOT RUN | CHƯA PHÊ DUYỆT |
| V2b | Whole-model UNKNOWN; instructions/listener/native thiếu coverage; rendered retention unattributed | CHƯA PHÊ DUYỆT |
| V3 | Managed staging/PITR/offsite/retention/encryption/restore evidence; connection hiện không có staging khả dụng | CHƯA PHÊ DUYỆT |
| V5 | Target/release/window/backup/rollback/smoke/RTO/RPO được phê duyệt và đo | CHƯA PHÊ DUYỆT |
| V7 | Workload/SLO/target/support/pilot và load/rollback evidence được phê duyệt và đo | CHƯA PHÊ DUYỆT |

[Bảng quyết định cụ thể](bh07_v8_risk_decision_packet_20261110.md) vẫn là dự thảo. Owner phải quyết định từng cổng: yêu cầu đo tiếp/cấp môi trường, từ chối, hoặc chấp nhận đúng rủi ro/giới hạn/giảm thiểu của hàng đó cho **Web local với dữ liệu thử**. Không coi “tiếp tục”, quyền run hay ủy quyền code là chấp nhận rủi ro. Không đổi NOT RUN/UNKNOWN thành PASS, không phát hành native, merge/deploy/pilot/BH-08. Reviewer chỉ chốt V8 sau khi mọi điều kiện §4.11 đồng thời thỏa mãn.
