# Badminton Hub — điểm bắt đầu cho Antigravity

> **Hiện hành23/10/2026:** Gói **kiểm chứng response tài chính Owner trả trễ sau đổi actor BH-07 Chờ review**, source `c4ce99bcd9a9b02c4b794c8eb5ab51e43c06155a`, base `1ed4f3e6b42b853f51add79279fe3daf8168e360`. Codex triển khai/tự kiểm, **không độc lập**. Hai ca UI thật cùng SPA **Owner→Cohost và Owner→Member PASS**: giữ POST summary200 khoảng44,7/40,5 giây, thả sau login actor mới, delivered body hash trùng, timeOrigin không đổi; Cohost vẫn count-only/copy an toàn,Member empty/không summary-copy. **21 control mới**,41 control cũ,11 browser baseline,analyze sạch,240 Flutter+1skip,44/44 manifest. Không thấy lỗi app ở bề mặt đã thử; chưa tự ghi Đạt cho gói mới. [Bàn giao](reviews/bh07/late_response_handoff.md). Private Dart heap không đo trực tiếp;giữ unit cache guard bổ sung và nêu giới hạn. Không đổi app/unit/backend/contract. Giữ Browser trước Đạt tự review local cùng A/B/C/D/HTTP/Auth/concurrency; toàn BH-07/production/pilot chưa nghiệm thu. Review độc lập,mobile/browser khác,banking/webhook,staging/production/backup,rehearsal/pilot vẫn NOT RUN. Không merge/apply DB thật/deploy/chuyển pilot.

> **(Lịch sử kết luận browser trước gói response trễ)** Gói **Browser / Offline / Reopen BH-07 Đạt theo Codex tự review local**, source `a6d58aff3f1726484146a6c89aa7d559bb684d6d`, evidence `994ebfeb98c7c76815c2b8e0e6519fbe735ab1af`, theo [kết luận tự review](reviews/bh07/self_review_a6d58af.md). Chủ dự án yêu cầu trực tiếp tự review và chốt; **KHÔNG phải review độc lập**. Đóng BR3-1/BR3-2/BR3-3 theo tự review; không có P0/P1/P2 còn mở trong phạm vi được giao. Phát lại9 probe,41 negative,9 verifier,mutant và52/52 manifest đều đúng; kế thừa tự kiểm cùng SHA: analyze sạch,240 Flutter+1skip,23 DB,11 browser,12 ảnh khác hash. Chỉ3 script kiểm chứng đổi; app/backend/contract và bằng chứng cũ giữ nguyên. **Toàn BH-07/production/pilot chưa nghiệm thu.** Review độc lập, mobile/browser khác, response trễ sau đổi actor, banking/webhook, staging/production/backup, rehearsal/pilot và full Supabase reset vẫn NOT RUN. Không merge/apply DB thật/deploy/chuyển pilot.

> **(Lịch sử bàn giao Codex trước tự review)** Gói **Browser / Offline / Reopen BH-07 Chờ review độc lập sau Codex tự sửa/tự kiểm**, tested source `a6d58aff3f1726484146a6c89aa7d559bb684d6d`, base `1fc7e2eb171acd6c7afbc16e9f1053f9b3cb21c3`. Chủ dự án giao trực tiếp Codex sửa **BR3-1/BR3-2/BR3-3** sau review `02cd0ed`; Codex bổ sung whitelist Manager, guard tiền Unicode và status/body/privacy lịch sử. **KHÔNG phải review độc lập; chưa tự ghi Đạt hay xác nhận đóng P2.** Tự chạy analyze sạch, **240 Flutter +1 skip**, **23 DB**, **11/11 browser**, **9/9 probe cũ giữ nguyên kỳ vọng**, **41/41 negative**, **9/9 verifier readonly**, mutant PASS, **52/52 manifest**; checkout browser sạch. [Bàn giao](reviews/bh07/browser_codex_fix_handoff.md). Chỉ3 script kiểm chứng thay đổi; giữ gate BR1/BR2/BR4/BR5, app/unit test/backend/contract và bằng chứng cũ. Giữ A/B/C/D và HTTP/Auth/concurrency Đạt local; toàn BH-07/pilot chưa nghiệm thu. Mobile/browser khác, response trễ sau đổi actor, banking/webhook, staging/production/backup, rehearsal/pilot và full Supabase reset vẫn NOT RUN. Không merge/apply DB thật/deploy/chuyển pilot.

> **(Lịch sử review lần sửa cuối)** Gói **Browser / Offline / Reopen BH-07 Chưa đạt lần sửa cuối theo ủy quyền bổ sung** tại source `a62f509986f65592da3fb5bccebe7b7c246ff7b7`, docs/evidence `02cd0edbb9b1f77213c6788474984686895e125c`, theo [review độc lập](reviews/bh07/review_02cd0ed.md). **Đóng BR2/BR5; BR3 còn ba P2**: field tiền lạ của Manager, regex VNĐ/đ của Cohost và gate response/privacy lịch sử Member. Reviewer tự chạy analyze sạch, **240 Flutter +1 skip**, **23 DB**, **11/11 browser**, **27/27 negative**, **9/9 verifier readonly**, mutant PASS, **33/33 manifest**; nhưng **5 negative input bổ sung bị nhận PASS sai**, cùng4 positive baseline đúng. Giữ BR1 và ca SPA BR4; app/backend không đổi. **Bàn giao phần sửa kiểm chứng còn lại cho Codex theo ủy quyền chủ dự án; kết quả Codex tự sửa/tự kiểm phải ghi không độc lập. Lượt review này không sửa triển khai.** Giữ A/B/C/D và HTTP/Auth/concurrency Đạt local; toàn BH-07/pilot chưa nghiệm thu. Mobile/browser khác, response trễ sau đổi actor, banking/webhook, staging/production/backup, rehearsal/pilot và full Supabase reset vẫn NOT RUN. Không merge/apply DB thật/deploy.

> **(Lịch sử bàn giao lần sửa cuối)** Gói **Browser / Offline / Reopen BH-07 đang ở trạng thái Chờ review lần sửa cuối theo ủy quyền bổ sung** tại source `a62f509986f65592da3fb5bccebe7b7c246ff7b7`, theo [bàn giao](reviews/bh07/browser_handoff.md). BR1 và ca SPA BR4 giữ nguyên; đã bổ sung gate cho BR2/BR3/BR5 P2: lỗi offline thật, đúng 2 POST cùng payload/`request_id`, aggregate/cohost privacy/history ID chính xác, verifier read-only, 27 negative control, 9 verifier control và mutant `if (true)`. Bằng chứng local: analyze sạch, **240 Flutter +1 skip**, **23 DB**, **11/11 browser**, **27/27 negative case đúng kỳ vọng**, **9/9 verifier control**, mutant PASS, **33/33 manifest**, `is_dirty=false`, Web build PASS. App/backend không đổi; giữ A/B/C/D và HTTP/Auth/concurrency Đạt local. Toàn BH-07/pilot chưa nghiệm thu; mobile, delayed response sau đổi actor, banking/webhook, staging/production/backup, rehearsal/pilot và `supabase db reset` vẫn NOT RUN. Không merge/apply DB thật/deploy; người triển khai không tự ghi Đạt.
>
> **(Lịch sử review) 23/10/2026:** Gói **Browser / Offline / Reopen BH-07 Chưa đạt vòng2/2** tại source `51cb3b1`, docs/evidence `eadb5c7`, theo [review độc lập](reviews/bh07/review_eadb5c7.md). Đóng BR1 và ca SPA BR4; lỗi P1 retry đã sửa nhưng **BR2 còn P2**, **BR3/BR5 P2 còn mở** về gate UI error, aggregate/ACL và verifier/negative controls/provenance. Reviewer tự chạy analyze sạch, **240 Flutter +1 skip**, **23 DB**, **11/11 browser**, Web build PASS; **21/21 hash**, readonly missing/hash/sb_secret controls PASS. Tuy nhiên4 control BR3, silent-error, JWT/UTF8 và mutant negative-runner vẫn được nhận xanh sai. **Dừng gói sau2 vòng theo AGENTS, chờ quyết định chủ dự án; không tự mở vòng3 hoặc giao sửa tiếp.** App/backend không đổi; giữ A/B/C/D và HTTP/Auth/concurrency Đạt local. Toàn BH-07/pilot chưa nghiệm thu; mobile/banking/webhook/staging/production/backup/rehearsal/pilot và response trễ sau đổi actor vẫn NOT RUN. Không merge/apply DB thật/deploy.

## Trạng thái hiện tại (cập nhật 23/10/2026)

Chủ dự án đã duyệt audit B1–B9/C1/C2 và giao merge BH-06, đồng bộ tiến độ, chuẩn bị BH-07. [Lịch sử xác nhận](23_DOC_AUDIT_FOLLOWUP.md); điểm tiếp tục hiện hành ở docs/25.

- BH-01 đến BH-05 đã triển khai ở mức local/staging theo [09_IMPLEMENTATION_PLAN.md](09_IMPLEMENTATION_PLAN.md) và [22_BH05_HANDOFF.md](22_BH05_HANDOFF.md). **BH-05 đạt review tích hợp A+B+C** tại `d769531` theo [review_d769531.md](reviews/bh05/review_d769531.md): không có phát hiện P0/P1/P2 trong phạm vi kiểm chứng.
- **Hồi quy trên `main` tại `3a34883` đạt**, do reviewer tự chạy trên checkout sạch ([review_main_3a34883.md](reviews/bh05/review_main_3a34883.md)): `flutter analyze` sạch, 137/137 Flutter test, 251/251 DB test (BH-02 33+14, BH-03 48+22, BH-04 44, BH-05 90) trên PostgreSQL cô lập + Auth stub.
- Gói kiểm chứng **Concurrency HTTP/Auth BH-07 Đạt local vòng2/2**, tested source `cbcc46c`, docs/evidence thực tế `bb940280333aec96457dd3014aabba9f66adf4ae`, theo [review độc lập](reviews/bh07/review_cbcc46c_r2.md).
- **BH-06 đã merge main tại `e7f7627`**, chứa review `b3bcfbb` (tested `318bc52`); [xác minh merge](reviews/bh06/main_merge_e7f7627.md). Baseline review: analyze sạch, 190 Flutter +335 DB +7 tích hợp +3 nâng cấp +2 probe PASS. docs/ai có trên main từ `eaeb209`.
- **Điểm tiếp tục:** Gói Browser/Offline/Reopen đang **Chờ review lần sửa cuối theo ủy quyền bổ sung** tại source `a62f509`, theo [bàn giao](reviews/bh07/browser_handoff.md); reviewer cần tự chạy lại các cổng. Không tự merge/deploy/pilot; nếu review không đạt, bàn giao phần còn lại cho Codex và ghi rõ phần Codex làm không độc lập.
- Lịch sử các đợt cập nhật trước nằm ở [STATUS_HISTORY.md](STATUS_HISTORY.md); đó là nhật ký, không phải chỉ dẫn hiện hành.

## Mục tiêu

Xây công cụ cho host quản lý CLB và buổi cầu lông tại Nha Trang. Người chơi tham gia qua link host chia sẻ. Hoàn thiện một buổi chơi từ đăng ký đến thu tiền trước khi mở rộng khám phá cộng đồng.

## Thứ tự đọc

1. [Quy tắc làm việc](04_LLM_RULES.md).
2. [Yêu cầu sản phẩm](01_PRD_SPEC.md).
3. [Kiến trúc](02_ARCHITECTURE.md).
4. [Cơ sở dữ liệu và phân quyền](03_DATABASE.md).
5. [Hợp đồng thao tác nghiệp vụ](08_DOMAIN_CONTRACTS.md).
6. [Backlog và nghiệm thu](09_IMPLEMENTATION_PLAN.md).
7. [Luồng màn hình](10_SCREEN_FLOWS.md).
8. [Quyết định ADR](11_ARCHITECTURE_DECISIONS.md).
9. [Prompt và cổng nghiệm thu cho Antigravity](12_ANTIGRAVITY_PROMPTS.md).
10. [Đầu bài và bàn giao BH-07](25_BH07_IMPLEMENTATION_HANDOFF.md); [bàn giao BH-06](24_BH06_IMPLEMENTATION_HANDOFF.md) và [lịch sử BH-05](22_BH05_HANDOFF.md).

[07_HOST_FIRST_REVIEW.md](07_HOST_FIRST_REVIEW.md) là bằng chứng rà soát và tham khảo Vmito, không thay thế các đặc tả trên. `05_DB_V2_UPDATE.sql` và `06_SEED_VENUES.sql` là tài liệu SQL cũ; không chạy làm schema mới. Các migration trong `supabase/migrations/` mới chỉ được kiểm thử trên PostgreSQL cô lập, chưa apply production.

## Hiện trạng và đích

Cột "Hiện trạng" dưới đây dựa trên báo cáo trong docs/09, docs/22, review_d769531, review_main_3a34883 và bàn giao tích hợp BH-06; dòng nào chưa đối chiếu với code thì ghi rõ.

| Hiện trạng | Đích triển khai |
|---|---|
| Flutter + Supabase + Provider; lớp demo `SupabaseService` đã bị thay bằng model/repository/provider typed từ BH-04 | Giữ stack, triển khai dần |
| Đã có đăng nhập (BH-01), schema v1.1 + RLS (BH-02) và phân quyền CLB (BH-03) ở mức local/staging; chưa kiểm HTTP/JWT thật | Auth và RLS kiểm chứng trên Supabase thật trước pilot |
| CLB, buổi, đăng ký đã liên kết qua schema v1.1 và RPC (BH-03 đến BH-05) ở mức local/staging | Schema tại 03_DATABASE |
| Mutation đăng ký/duyệt/huỷ/điểm danh đi qua RPC nguyên tử, client không ghi bộ đếm theo thiết kế BH-05. Chốt phí/chi phí/thanh toán/sổ quỹ đã có ở mức local/staging (BH-06); Đạt review tích hợp local tại `318bc52` sau vòng sửa 1; BH-07A có projection history/summary/debt sau complete và **Đạt A local tại 4512c3a**; chưa kiểm HTTP/JWT thật | DB xử lý nguyên tử, client chỉ gửi ý định |
| QR/hướng dẫn chuyển khoản dựng từ `receiver_snapshot` + outstanding + reference (BH-06C); đã vá lỗi snapshot không được chốt và backfill cho buổi có sẵn khi nâng cấp. UI/DB đã test; ảnh QR qua mạng thật, ngân hàng thật và webhook chưa kiểm | QR thật, dữ liệu gắn ID buổi/người |
| Đợt BH-07A: analyze sạch, **190 Flutter**, **335 DB hồi quy BH-02..06**, **23 DB BH-07**, **7 tích hợp**, **3 nâng cấp** PASS trên PostgreSQL cô lập; 9 kiểm tra RPC reviewer mới PASS; hai probe lịch sử BH-06 không chạy lại, chưa HTTP/JWT/thiết bị thật | Kiểm thử quyền, cạnh tranh slot, tiền và luồng thực |

Không được diễn giải tài liệu đích là chức năng đã tồn tại; đối chiếu bảng trên và nhật ký ở docs/09. Đợt cập nhật tài liệu không thay đổi code hoặc DB remote.

## Quyết định mặc định cho MVP

- Miễn phí trong pilot; Nha Trang là thị trường đầu tiên.
- Host đăng nhập bằng email/mật khẩu; xác nhận email và khôi phục mật khẩu. Google login/OTP điện thoại để sau.
- Người xem không cần đăng nhập; người chơi tự đăng ký cần tài khoản. Host có thể thêm khách chưa có tài khoản đã đăng ký qua Zalo. Đăng ký khách tự phục vụ bằng token là giai đoạn sau.
- CLB có owner/host/treasurer/member. Host buổi độc lập được phép tạo buổi không thuộc CLB.
- Vãng lai mặc định cần host duyệt; host có thể chọn tự xác nhận nếu còn slot. Danh sách chờ được mời lại, không tự ép xác nhận.
- Phí cố định hoặc chia chi phí thực tế; quỹ và thanh toán được xác nhận thủ công. Không có webhook ngân hàng ở MVP.
- Không tự đóng buổi chỉ vì hết giờ; host chốt kết thúc.
- Các mặc định này là lựa chọn thiết kế để bắt đầu, có thể được chủ dự án điều chỉnh trong yêu cầu chức năng sau.

## Prompt bắt đầu gợi ý

> Đọc AGENTS.md (gồm mục "Quy trình hai AI") và docs/00_START_HERE.md, rồi các tài liệu chuẩn theo thứ tự. Làm đúng vai trò và ticket được giao trong docs/09_IMPLEMENTATION_PLAN.md (BH-06 đã merge main; BH-07A Đạt local tại 4512c3a theo docs/25, không tự chuyển B/C/D). Kiểm tra code/schema hiện có, nêu file cần sửa, chỉ làm phạm vi được giao và chạy các kiểm thử trong tiêu chí nghiệm thu, giữ regression các ticket trước. Không chạy SQL cũ hoặc tự deploy Supabase production. Không tự ghi "Done": ghi "Chờ review" kèm bằng chứng. Báo rõ thay đổi, kết quả kiểm thử, phần NOT RUN và việc cần cấu hình ngoài code.

Khi đổi yêu cầu: cập nhật PRD → model/schema → hợp đồng DB → màn hình/backlog trong cùng thay đổi. Không tự suy ra chủ CLB hoặc gộp người từ tên/SĐT.

## Tham khảo sản phẩm: Vmito và Vụt

[14_PRODUCT_LEARNINGS_VMITO_VUT.md](14_PRODUCT_LEARNINGS_VMITO_VUT.md) là bản áp dụng hai báo cáo REA do chủ dự án cung cấp. Đọc phần PD tương ứng khi thực hiện BH-03..07; giữ các giới hạn static/runtime, không thêm dependency/schema theo danh sách thư viện đối thủ. Đây là tài liệu bổ sung yêu cầu, không thay lịch sử kiểm thử hoặc xác nhận sửa BH-02.

## Giao việc BH-06 — 16/10/2026

Chủ dự án giao AI triển khai, Codex review độc lập. [Đầu bài BH-06 và cổng A→B→C→tích hợp](24_BH06_IMPLEMENTATION_HANDOFF.md). Trạng thái 20/10/2026: A/B/C đã Đạt từng phần; **Đạt tích hợp local tại `318bc52`**, đóng I1/I2 theo [review độc lập](reviews/bh06/review_318bc52.md). Đã merge main `e7f7627`, chưa deploy.

## Giao việc BH-07A — 20/10/2026 (lịch sử bàn giao)

Kết luận mới nhất: **Đạt A local tại 4512c3a**, theo [review](reviews/bh07/review_4512c3a.md); đoạn bên dưới ghi trạng thái phía tác giả trước review.

Theo [đầu bài BH-07](25_BH07_IMPLEMENTATION_HANDOFF.md), lượt này chỉ làm phần A trên `feat/bh07a-db` từ main mới nhất. Đã thêm migration forward `20261020180000_bh07_reads.sql` với `get_session_summary` và `list_my_session_history`, runner `docs/reviews/bh07/run_bh07_tests.py`, audit/handoff trong `docs/reviews/bh07/`. **Trạng thái: Chờ review BH-07A** tại tested code `c339a47`; analyze sạch, 190 Flutter, 335 DB hồi quy, 23 DB BH-07, 7 tích hợp và 3 nâng cấp PASS. Chưa nghiệm thu BH-07, chưa làm B/C/D, chưa merge main hoặc apply staging/production. NOT RUN: HTTP/PostgREST/JWT/Auth thật, thiết bị/ngân hàng thật, backup/restore và concurrency HTTP.
