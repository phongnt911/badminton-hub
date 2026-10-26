# Chốt điều phối — QA runtime V2b app-profile local

- Ngày: 26/10/2026, Asia/Saigon. Người chốt: Codex điều phối, audit gói QA bàn giao, không sửa source.
- Nhánh: `feat/bh07-app-profile-runtime-review`.
- Base/tested runtime QA: `97d0e7e3be59fa8504d7ec0d6b55a0e67495ebff`.
- Source công cụ được chốt trước: `c04ce551a4cb7fa8cbddcd5f06dbc790a39889f6`.
- Docs/evidence QA: `2d16369bee16bd2a98a356dab962ec1d3ad20762`, checkout điều phối sạch trước audit.
- Báo cáo được đối chiếu: [review_runtime_97d0e7e.md](review_runtime_97d0e7e.md), [bundle QA](review_runtime_97d0e7e_evidence/).

## Kết luận

**Đạt trong phạm vi QA runtime độc lập local của phép đo bank sentinel trên Flutter Web profile/V8**, hai chu kỳ Owner→logout→Cohost/Member, theo hồ sơ QA đã đối chiếu. Đóng phần QA runtime này; không còn phát hiện P0/P1/P2 mở đối với tính toàn vẹn/phạm vi bundle QA được bàn giao.

Đây là chốt điều phối dựa trên **QA đã tự chạy runtime** và audit readonly độc lập của Codex; **Codex không chạy lại Chrome trong lượt này**. QA được chủ dự án bàn giao là người không viết/sửa gói; báo cáo QA xác nhận vai trò này. Codex từng làm gói Provider/browser lịch sử nên không dùng lịch sử đó thay vai trò QA mới.

Gói công cụ V8 local/AH1–AH9 giữ Đạt theo [review_5f2b5a6](review_5f2b5a6.md). **Không đóng toàn bộ V2b §4.4**: retained paths/toàn bộ model/cache/listener và Dart VM desktop/mobile vẫn NOT RUN. Provider/tooling, V1 và V5b giữ Đạt local; toàn BH-07 chưa nghiệm thu. Không merge main/staging/production, deploy/pilot/BH-08 hoặc xóa nhánh.

## Đối chiếu và bằng chứng điều phối

Evidence riêng: [review_2d16369_evidence/](review_2d16369_evidence/). Script `audit_runtime_bundle.py` chỉ đọc; có thể phát lại từ repo root. Các asserts đối chiếu dữ liệu đã có, **không phải runtime mới hoặc bằng chứng replay raw heap**.

| Kiểm tra do điều phối tự chạy | Kết quả |
| --- | --- |
| Auditor appheap trên bundle QA, dùng đường dẫn tuyệt đối | exit0,verdict/actor/epoch/report/cleanup/metadata hợp lệ theo auditor hiện hành |
| Auditor appheap trên bundle tác giả | exit0 |
| Strict readonly verifier trên QA và tác giả | mỗi bundle3/3 entries,4 file gồm manifest;exit0,UTF-8 LF,không secret/JWT ngoài allowlist |
| Audit Git/manifest trước-sau | mọi byte hai bundle trùng Git blob checkout QA;manifest đúng tập file,không extra/missing/mismatch |
| Audit tám snapshot metadata với run.log | số byte/hash12/presence khớp từng nhãn;8 hash khác nhau;timestamp tăng và nằm giữa started/finished |
| Scan consistency | 24/24 record int/count>=0,bool/presence tương ứng;bank1 ở Owner-active và0 ở các mốc khác;probe1 mọi mốc |
| Build/source provenance | runtime tested97d0e7e,dirtyfalse,39 artifact hash;index/main hash trùng gói tác giả;source/scripts/tests giữa c04ce55→97d0e7e→QA không đổi |
| Report QA | hash author bundle trong báo cáo khớp file thực;UTF-8 LF,credential/raw-sentinel scan không thấy rò rỉ theo mẫu/metadata |
| Scope/whitespace | diff97d0e7e→QA chỉ5 file docs/evidence,diff-check exit0;không đổi app/backend/test/công cụ |

QA run.log ghi build profile37,8s và tám mốc mới;metadata source97d0e7e/dirtyfalse,actor cohost/member,same_document true,timeOrigin mỗi chu kỳ,cleanup dump/profile đều verified,raw_snapshots_remaining0. Script source đã chốt kiểm timeOrigin trước/sau và luồng UI thật; bundle lưu kết quả kiểm cùng giá trị origin. Không dựng thêm giá trị origin-after hoặc transcript không có trong bundle. Guard hiện hành kiểm served bytes hai entry index/main,không kiểm response đủ39 artifact;`served_match` giữ đúng nghĩa này.

### Phân biệt số QA báo cáo và số điều phối xác minh

Báo cáo QA ghi146 Python,15self/8guard/5relation,247Flutter+1skip,analyze0 và replay các probe. Bundle QA bốn file chứa **log runtime**,không có stdout riêng của từng suite; lượt chốt này **không chứng nhận mới các lần suite đó**. Source không đổi nên kế thừa kết quả Codex đã tự chạy tại review_5f2b5a6 với log riêng. Không chạy lại Flutter/DB/Python suites chỉ vì delta docs/evidence; không gộp chúng vào số runtime QA. QA chạy Windows/Node24.21.0/Flutter3.47.6/Chrome155; điều phối audit Linux.

### Ghi chú về lệnh auditor

Lần gọi `verify_evidence.py --dir docs/reviews/bh07/review_runtime_97d0e7e_evidence` trả exit1 vì formatter `Path(args.dir).relative_to(ROOT)` dùng đường dẫn tương đối. Hàm kiểm đã không có finding nhưng không lấy lần lỗi này làm PASS. Chạy lại với đường dẫn **tuyệt đối** trả exit0; lưu cả log lỗi và log thành công,không sửa CLI trong lượt điều phối. Cách gọi đã kiểm chứng:

```bash
python -X utf8 scripts/bh07_appheap/verify_evidence.py --dir /workspace/badminton-hub/docs/reviews/bh07/review_runtime_97d0e7e_evidence
```

Đây là giới hạn của cách gọi/định dạng output hiện hành; không làm thay đổi kết quả hash/semantic của bundle được chốt. Lượt này không review lại hoặc sửa usability của CLI.

## NOT RUN và ranh giới đóng

| Cổng/hạng mục | Trạng thái hiện hành |
| --- | --- |
| QA độc lập chạy2cycle bank sentinel Web profile | **Đạt local theo hồ sơ QA,đã điều phối đối chiếu**;không còn là phần thiếu runtime độc lập này |
| Codex điều phối tự chạy Chrome lại/đo lại raw dumps | NOT RUN trong lượt chốt;raw dump QA đã xóa,không được suy audit metadata thành replay dumps |
| Retained graph/paths toàn bộ model/cache/listener,ghi chú/số dư/doanh thu ngoài bank sentinel | **NOT RUN**;V2b §4.4 đầy đủ chưa đóng;expense chưa nạp không sinh kết luận |
| Dart VM desktop/mobile và browser/device khác | NOT RUN;gói QA chỉ V8/dart2js web profile/Chrome cụ thể |
| Bank escaped thực tế trong Chrome155;expense unavailable runtime | NOT RUN;chỉ có controls bằng fixture ở gói công cụ |
| Kiểm inventory độc lập của stack QA/recipe dựng lại | Không có inventory/recipe dựng stack riêng trong bundle bốn file;local API/CLI do QA báo cáo. Không chứng nhận một gate vận hành/cleanup Docker mới. Cleanup được chốt ở đây là dump/profile theo runner,bundle không lưu xác minh host trực tiếp của điều phối. |
| Managed backup/PITR/offsite/encryption/retention,concurrent writers,banking/webhook,staging/production,tải/rehearsal/pilot,BH-08,nghiệm thu toàn BH-07 | NOT RUN,giữ giới hạn cổng kế hoạch;không merge/deploy/pilot |

**Kết luận: Đạt QA runtime độc lập local trong phạm vi bank sentinel Web profile;V2b đầy đủ và toàn BH-07 chưa nghiệm thu.**
