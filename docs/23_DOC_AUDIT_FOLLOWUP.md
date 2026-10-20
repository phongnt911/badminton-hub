# Xác nhận và trạng thái tài liệu sau audit BH-05

Ngày 16/10/2026 (Việt Nam). Chủ dự án xác nhận: “làm theo đề xuất, tích toàn bộ mục B”, cập nhật tài liệu/trạng thái toàn bộ docs và push để tiếp tục. Phạm vi **chỉ Markdown**, không mở ticket code hoặc cấp quyền deploy. Bản ghi này thay trạng thái chờ quyết định của [audit ban đầu](reviews/bh05/doc_audit_after_bh05.md); audit/review cũ giữ nguyên theo thời điểm và vị trí dòng lúc rà soát.

## Hiện hành 20/10/2026

BH-06 đã Đạt tích hợp local tại 318bc52 và merge main e7f7627; [review](reviews/bh06/review_318bc52.md), [xác minh merge](reviews/bh06/main_merge_e7f7627.md). Chủ dự án giao merge/cập nhật tiến độ/chuẩn bị prompt BH-07; [BH-07A](25_BH07_IMPLEMENTATION_HANDOFF.md) **Đạt A local tại 4512c3a** theo [review](reviews/bh07/review_4512c3a.md), B/C/D chưa nghiệm thu. Nội dung audit 16/10 phía dưới giữ nguyên theo thời điểm, không dùng chỉ dẫn BH-06 chưa làm bên dưới làm hiện trạng mới. Chưa deploy/apply DB thật hoặc nghiệm thu HTTP/JWT/thiết bị/ngân hàng thật.

## Snapshot xác nhận 16/10/2026 và điểm tiếp tục khi đó

BH-01..05 đã triển khai ở mức kiểm thử local/PostgreSQL cô lập + Auth stub. **BH-05 Đạt tích hợp A+B+C** tại `d769531` theo [review độc lập](reviews/bh05/review_d769531.md). Hồi quy main `3a34883`: analyze sạch, **137/137 Flutter + 251/251 DB** theo [review và bằng chứng](reviews/bh05/review_main_3a34883.md). Không có lần chạy app/DB mới trong lượt cập nhật tài liệu này.

**Ticket tiếp theo BH-06/AG-06**: chốt phí, VietQR, thu tiền/quỹ theo [backlog](09_IMPLEMENTATION_PLAN.md), [contract](08_DOMAIN_CONTRACTS.md), [ADR](11_ARCHITECTURE_DECISIONS.md), [prompt](12_ANTIGRAVITY_PROMPTS.md). Giữ regression đã có, không triển khai lại AG-00..05 hoặc tạo lại start_session đã có. Việc thực thi BH-06 là lượt công việc tiếp theo, chưa được thực hiện bởi thay đổi docs này. BH-06..09 chưa triển khai; BH-10 là đề xuất sau pilot.

NOT RUN vẫn giữ: PostgREST HTTP/JWT thật; thiết bị/browser e2e và OS deep link; apply staging/production; backup/restore; concurrency qua HTTP, kể cả revoke khi client refresh. Cụm local/staging ở tài liệu cũ là nhãn mức triển khai, không chứng minh apply staging thật. Không cho phép deploy production từ việc duyệt docs.

## Theo dõi xác nhận và áp dụng

Tất cả B1–B9 trong WORK_ORDER đã được tick `[x]` từ gói đầu vào, nay được chủ dự án xác nhận lại toàn bộ. Không có mục B bỏ qua hoặc còn chờ duyệt. Các cập nhật A/B trước đó nằm trong `a09a513`, `0266f2b`; báo cáo C trong `df8a7d0`.

- [x] A1–A3: README, docs/00 và STATUS_HISTORY đã cập nhật, giữ nguyên tám mục lịch sử.
- [x] B1: trạng thái hiện hành ngay đầu docs/22, giữ snapshot cũ.
- [x] B2: ghi nhận review A/B/C độc lập.
- [x] B3: nghiệm thu tích hợp d769531 thay chỉ dẫn chờ review lại.
- [x] B4: mục reviewer kết luận lại đã được đánh dấu đã xong trong docs/22.
- [x] B5: c7ed6d5 được gắn nhãn đã bị thay thế.
- [x] B6: nhãn hiện hành sau trạng thái khởi đầu trong docs/09.
- [x] B7: nối trạng thái R2/R3/R5/R6/R7; giữ R1/R4. R5 không được coi đã kiểm form e2e, R6 còn QR thật ở BH-06.
- [x] B8: tiêu đề bảng BH-04 và dòng trống heading BH-05 đã sửa.
- [x] B9: bảng BH-01..05 và BH-06..09 chưa triển khai trong docs/09.
- [x] C1-01: docs/08 §12 tách response đăng ký, invite, revoke, accept; khớp model client đang dùng.
- [x] C1-02: docs/08 §12 bổ sung start_session, projection trả về, quyền/state/request ID/replay/audit và bốn migration forward.
- [x] C1-03: docs/08 §12 ghi revoke lời mời đã revoked trả thành công không side effect; giữ lỗi accepted/expired, không đổi code.
- [x] C1-04: docs/08 §12 ghi gate finance sau active revision cho add/decide/cancel/accept, dẫn ADR-08; không nới quyền.
- [x] C2-01: docs/22 §3 dùng SHA256 blob Git LF; giữ ba hash CRLF cũ trong bảng lịch sử. Không sửa migration hoặc bằng chứng hash trong JSON.
- [x] C3: quét lại liên kết sau thay đổi; kết quả kiểm tra được ghi ở cuối tài liệu này.

“Đã áp dụng” ở đây là trạng thái thay đổi **tài liệu**, không phải nghiệm thu mới code/DB. Đề xuất thay code để từ chối revoked không được chọn: áp dụng hướng sửa docs cho khớp hành vi hiện hữu.

## Đồng bộ toàn bộ tài liệu

README, AGENTS và doc-update-pack đã liên kết bản ghi xác nhận hiện hành; WORK_ORDER ghi rõ ba bản nháp nằm ngay trong gói và gói được chủ dự án cho giữ trong Git. Quy tắc docs/04 và AGENTS yêu cầu ghi quyết định/trạng thái sau xác nhận trong cùng lượt, không tiếp tục coi mục đã duyệt là chờ quyết định.

Tất cả file Markdown trực tiếp trong docs/ được rà soát và có trạng thái/điểm tiếp tục phù hợp. Bảng dưới cho biết cách đọc, không thay các con số kiểm thử lịch sử bằng số mới.

| Tài liệu | Vai trò và xử lý trạng thái |
|---|---|
| [00_START_HERE.md](00_START_HERE.md) | Entrypoint/trạng thái hiện hành; nối xác nhận A/B/C và BH-06. |
| [01_PRD_SPEC.md](01_PRD_SPEC.md) | Đặc tả/quy tắc hiện hành; phân biệt yêu cầu đích với triển khai đã kiểm, nối trạng thái BH-05/BH-06. |
| [02_ARCHITECTURE.md](02_ARCHITECTURE.md) | Đặc tả/quy tắc hiện hành; phân biệt yêu cầu đích với triển khai đã kiểm, nối trạng thái BH-05/BH-06. |
| [03_DATABASE.md](03_DATABASE.md) | Đặc tả/quy tắc hiện hành; phân biệt yêu cầu đích với triển khai đã kiểm, nối trạng thái BH-05/BH-06. |
| [04_LLM_RULES.md](04_LLM_RULES.md) | Đặc tả/quy tắc hiện hành; phân biệt yêu cầu đích với triển khai đã kiểm, nối trạng thái BH-05/BH-06. |
| [07_HOST_FIRST_REVIEW.md](07_HOST_FIRST_REVIEW.md) | Giữ snapshot/baseline, thêm nhãn hiện hành và chỉ dẫn BH-06; không dùng prompt/lỗi cũ để giao lại ticket. |
| [08_DOMAIN_CONTRACTS.md](08_DOMAIN_CONTRACTS.md) | Đặc tả/quy tắc hiện hành; phân biệt yêu cầu đích với triển khai đã kiểm, nối trạng thái BH-05/BH-06. |
| [09_IMPLEMENTATION_PLAN.md](09_IMPLEMENTATION_PLAN.md) | Entrypoint/trạng thái hiện hành; nối xác nhận A/B/C và BH-06. |
| [10_SCREEN_FLOWS.md](10_SCREEN_FLOWS.md) | Đặc tả/quy tắc hiện hành; phân biệt yêu cầu đích với triển khai đã kiểm, nối trạng thái BH-05/BH-06. |
| [11_ARCHITECTURE_DECISIONS.md](11_ARCHITECTURE_DECISIONS.md) | Đặc tả/quy tắc hiện hành; phân biệt yêu cầu đích với triển khai đã kiểm, nối trạng thái BH-05/BH-06. |
| [12_ANTIGRAVITY_PROMPTS.md](12_ANTIGRAVITY_PROMPTS.md) | Đặc tả/quy tắc hiện hành; phân biệt yêu cầu đích với triển khai đã kiểm, nối trạng thái BH-05/BH-06. |
| [13_BH02_REVIEW_HANDOFF.md](13_BH02_REVIEW_HANDOFF.md) | Giữ snapshot/baseline, thêm nhãn hiện hành và chỉ dẫn BH-06; không dùng prompt/lỗi cũ để giao lại ticket. |
| [14_PRODUCT_LEARNINGS_VMITO_VUT.md](14_PRODUCT_LEARNINGS_VMITO_VUT.md) | Giữ snapshot/baseline, thêm nhãn hiện hành và chỉ dẫn BH-06; không dùng prompt/lỗi cũ để giao lại ticket. |
| [15_BH03_IMPLEMENTATION_HANDOFF.md](15_BH03_IMPLEMENTATION_HANDOFF.md) | Giữ snapshot/baseline, thêm nhãn hiện hành và chỉ dẫn BH-06; không dùng prompt/lỗi cũ để giao lại ticket. |
| [16_BH03_IMPLEMENTATION_SUMMARY.md](16_BH03_IMPLEMENTATION_SUMMARY.md) | Giữ snapshot/baseline, thêm nhãn hiện hành và chỉ dẫn BH-06; không dùng prompt/lỗi cũ để giao lại ticket. |
| [17_BH03_REMEDIATION.md](17_BH03_REMEDIATION.md) | Giữ snapshot/baseline, thêm nhãn hiện hành và chỉ dẫn BH-06; không dùng prompt/lỗi cũ để giao lại ticket. |
| [18_REVIEW_CONSOLIDATED_BH01_BH03.md](18_REVIEW_CONSOLIDATED_BH01_BH03.md) | Giữ snapshot/baseline, thêm nhãn hiện hành và chỉ dẫn BH-06; không dùng prompt/lỗi cũ để giao lại ticket. |
| [19_PRE_BH04_HANDOFF.md](19_PRE_BH04_HANDOFF.md) | Giữ snapshot/baseline, thêm nhãn hiện hành và chỉ dẫn BH-06; không dùng prompt/lỗi cũ để giao lại ticket. |
| [20_BH04_HANDOFF.md](20_BH04_HANDOFF.md) | Giữ snapshot/baseline, thêm nhãn hiện hành và chỉ dẫn BH-06; không dùng prompt/lỗi cũ để giao lại ticket. |
| [21_BH04_REMEDIATION.md](21_BH04_REMEDIATION.md) | Giữ snapshot/baseline, thêm nhãn hiện hành và chỉ dẫn BH-06; không dùng prompt/lỗi cũ để giao lại ticket. |
| [22_BH05_HANDOFF.md](22_BH05_HANDOFF.md) | Entrypoint/trạng thái hiện hành; nối xác nhận A/B/C và BH-06. |
| [STATUS_HISTORY.md](STATUS_HISTORY.md) | Giữ tám mục nguyên văn; thêm nhật ký xác nhận hiện hành. |
| [23_DOC_AUDIT_FOLLOWUP.md](23_DOC_AUDIT_FOLLOWUP.md) | Bản ghi xác nhận và trạng thái áp dụng hiện hành của lượt này. |

Các Markdown trong `docs/reviews/` và báo cáo nguồn `docs/research/competitors/` giữ nguyên: tested commit, phát hiện và số kiểm thử thuộc thời điểm của mỗi báo cáo. [Audit C](reviews/bh05/doc_audit_after_bh05.md) là snapshot trước sửa; bốn điểm hợp đồng và một điểm hash đã được xử lý ở docs/08, docs/22 theo checklist phía trên. Không sửa đè review hoặc nghiên cứu để biến baseline thành kết luận mới. SQL legacy docs/05, docs/06 không thay và không chạy.

## Kiểm tra tài liệu trong lượt này

Đối chiếu tĩnh tên RPC/response/ACL với migration, hash byte LF và biểu diễn CRLF; đối chiếu số PASS với JSON/log đã lưu. Kiểm lại link tương đối, fragment Markdown, kiểu LF và `git diff --check`; kiểm diff chỉ có `.md`, review/code/test/migration/JSON/log không thay đổi. Kết quả quét:

- README + 23 file docs/*.md: **197 link tương đối, 0 link hỏng**, bao gồm fragment Markdown.
- Mở rộng README + AGENTS + toàn bộ docs/**/*.md: **281 link tương đối**. Có 8 đích evidence gốc không được cung cấp trong repo, tất cả nằm trong `docs/research/competitors/vut-report.md`: `apk-identities.json` (:17), `hermes-endpoints.json` và `hermes-strings.json` (:58), `ClipboardFileProvider.java` và `decoded/resources/res/xml/clipboard_provider_paths.xml` (:70), `rea-artifact.json`, `rea-arm64.json`, `rea-analyze.json` (:92). `docs/research/competitors/README.md` đã ghi rõ chỉ tiếp nhận hai báo cáo Markdown, các link này là provenance gốc. Giữ nguyên nguồn, không tạo evidence giả hoặc xoá link để che phần thiếu. Không ảnh hưởng code/test Badminton Hub.
- Hai link `#L64`/`#L50` trong review BH-02 cũ là fragment dòng GitHub, không phải slug heading; file đích và số dòng vẫn tồn tại, nhưng nội dung được đọc theo baseline review. Giữ review bất biến.
- Không có link hỏng mới trong các tài liệu được cập nhật. Bốn hash migration và tám mục lịch sử được kiểm lại với byte/blob nguồn. Không chạy Flutter/analyze/runner DB vì chỉ sửa tài liệu.
