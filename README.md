# Badminton Hub

Ứng dụng Flutter + Supabase giúp host quản lý CLB, lịch sinh hoạt, đăng ký vãng lai, điểm danh, chốt phí và thu/chi. Thị trường pilot: Nha Trang.

## Trạng thái hiện tại — 23/10/2026

Ngày23/10/2026: Gói **Browser / Offline / Reopen và response Owner trả trễ BH-07 Đạt local, đã đóng công việc trên nhánh `feat/bh07-browser-verification`** theo yêu cầu chủ dự án. Codex review/tự sửa, **không độc lập**; [kết luận](docs/reviews/bh07/review_c4ce99b.md). Source browser trễ `c4ce99b`, source control chốt `417ee30`; đã sửa2 P2 về negative control bị lỗi khác che,21 control và2 mutant riêng PASS;41 regression,9 probe,9 verifier,manager mutant vàmanifest52/44 PASS. Kế thừa analyze sạch,240 Flutter+1skip,11 baseline+2 late browser trên app/driver/helper không đổi; không giả thành lần chạy mới. Không còn P0/P1/P2 mở trong phạm vi local được giao; không mở vòng Chờ review tiếp. **Giữ Git ref chưa merge; không xóa/merge main/deploy.** App/backend/contract và evidence cũ giữ nguyên. Toàn BH-07/production/pilot chưa nghiệm thu; private Dart heap/mobile/browser khác/banking/webhook/staging/production/backup/rehearsal/pilot vẫn có giới hạn/NOT RUN. **Chủ dự án đã giao tiếp bước kế: tài liệu vận hành và backup/restore rehearsal local cô lập**, trên nhánh mới; không production/pilot.

**(Lịch sử bàn giao trước chốt browser)** Gói **kiểm chứng response tài chính Owner trả trễ sau đổi actor BH-07 Chờ review**, source `c4ce99bcd9a9b02c4b794c8eb5ab51e43c06155a`, base `1ed4f3e6b42b853f51add79279fe3daf8168e360`. Codex triển khai/tự kiểm, **không độc lập**. Hai ca UI thật cùng SPA **Owner→Cohost và Owner→Member PASS**: giữ POST summary200 khoảng44,7/40,5 giây, thả sau login actor mới, delivered body hash trùng, timeOrigin không đổi; Cohost vẫn count-only/copy an toàn,Member empty/không summary-copy. **21 control mới**,41 control cũ,11 browser baseline,analyze sạch,240 Flutter+1skip,44/44 manifest. Không thấy lỗi app ở bề mặt đã thử; chưa tự ghi Đạt cho gói mới. [Bàn giao](docs/reviews/bh07/late_response_handoff.md). Private Dart heap không đo trực tiếp;giữ unit cache guard bổ sung và nêu giới hạn. Không đổi app/unit/backend/contract. Giữ Browser trước Đạt tự review local cùng A/B/C/D/HTTP/Auth/concurrency; toàn BH-07/production/pilot chưa nghiệm thu. Review độc lập,mobile/browser khác,banking/webhook,staging/production/backup,rehearsal/pilot vẫn NOT RUN. Không merge/apply DB thật/deploy/chuyển pilot.

**(Lịch sử kết luận browser trước gói response trễ)** Gói **Browser / Offline / Reopen BH-07 Đạt theo Codex tự review local**, source `a6d58aff3f1726484146a6c89aa7d559bb684d6d`, evidence `994ebfeb98c7c76815c2b8e0e6519fbe735ab1af`, theo [kết luận tự review](docs/reviews/bh07/self_review_a6d58af.md). Chủ dự án yêu cầu trực tiếp tự review và chốt; **KHÔNG phải review độc lập**. Đóng BR3-1/BR3-2/BR3-3 theo tự review; không có P0/P1/P2 còn mở trong phạm vi được giao. Phát lại9 probe,41 negative,9 verifier,mutant và52/52 manifest đều đúng; kế thừa tự kiểm cùng SHA: analyze sạch,240 Flutter+1skip,23 DB,11 browser,12 ảnh khác hash. Chỉ3 script kiểm chứng đổi; app/backend/contract và bằng chứng cũ giữ nguyên. **Toàn BH-07/production/pilot chưa nghiệm thu.** Review độc lập, mobile/browser khác, response trễ sau đổi actor, banking/webhook, staging/production/backup, rehearsal/pilot và full Supabase reset vẫn NOT RUN. Không merge/apply DB thật/deploy/chuyển pilot.

**(Lịch sử bàn giao Codex trước tự review)** Gói **Browser / Offline / Reopen BH-07 Chờ review độc lập sau Codex tự sửa/tự kiểm**, tested source `a6d58aff3f1726484146a6c89aa7d559bb684d6d`, base `1fc7e2eb171acd6c7afbc16e9f1053f9b3cb21c3`. Chủ dự án giao trực tiếp Codex sửa **BR3-1/BR3-2/BR3-3** sau review `02cd0ed`; Codex bổ sung whitelist Manager, guard tiền Unicode và status/body/privacy lịch sử. **KHÔNG phải review độc lập; chưa tự ghi Đạt hay xác nhận đóng P2.** Tự chạy analyze sạch, **240 Flutter +1 skip**, **23 DB**, **11/11 browser**, **9/9 probe cũ giữ nguyên kỳ vọng**, **41/41 negative**, **9/9 verifier readonly**, mutant PASS, **52/52 manifest**; checkout browser sạch. [Bàn giao](docs/reviews/bh07/browser_codex_fix_handoff.md). Chỉ3 script kiểm chứng thay đổi; giữ gate BR1/BR2/BR4/BR5, app/unit test/backend/contract và bằng chứng cũ. Giữ A/B/C/D và HTTP/Auth/concurrency Đạt local; toàn BH-07/pilot chưa nghiệm thu. Mobile/browser khác, response trễ sau đổi actor, banking/webhook, staging/production/backup, rehearsal/pilot và full Supabase reset vẫn NOT RUN. Không merge/apply DB thật/deploy/chuyển pilot.

**(Lịch sử review lần sửa cuối)** Gói **Browser / Offline / Reopen BH-07 Chưa đạt lần sửa cuối theo ủy quyền bổ sung** tại source `a62f509986f65592da3fb5bccebe7b7c246ff7b7`, docs/evidence `02cd0edbb9b1f77213c6788474984686895e125c`, theo [review độc lập](docs/reviews/bh07/review_02cd0ed.md). **Đóng BR2/BR5; BR3 còn ba P2**: field tiền lạ của Manager, regex VNĐ/đ của Cohost và gate response/privacy lịch sử Member. Reviewer tự chạy analyze sạch, **240 Flutter +1 skip**, **23 DB**, **11/11 browser**, **27/27 negative**, **9/9 verifier readonly**, mutant PASS, **33/33 manifest**; nhưng **5 negative input bổ sung bị nhận PASS sai**, cùng4 positive baseline đúng. Giữ BR1 và ca SPA BR4; app/backend không đổi. **Bàn giao phần sửa kiểm chứng còn lại cho Codex theo ủy quyền chủ dự án; kết quả Codex tự sửa/tự kiểm phải ghi không độc lập. Lượt review này không sửa triển khai.** Giữ A/B/C/D và HTTP/Auth/concurrency Đạt local; toàn BH-07/pilot chưa nghiệm thu. Mobile/browser khác, response trễ sau đổi actor, banking/webhook, staging/production/backup, rehearsal/pilot và full Supabase reset vẫn NOT RUN. Không merge/apply DB thật/deploy.

**(Lịch sử bàn giao lần sửa cuối)** Gói **Browser / Offline / Reopen BH-07 đang ở trạng thái Chờ review lần sửa cuối theo ủy quyền bổ sung** tại source `a62f509986f65592da3fb5bccebe7b7c246ff7b7`, theo [bàn giao](docs/reviews/bh07/browser_handoff.md). BR1 và ca SPA BR4 giữ nguyên; đã bổ sung gate cho BR2/BR3/BR5 P2: lỗi offline thật, đúng 2 POST cùng payload/`request_id`, aggregate/cohost privacy/history ID chính xác, verifier read-only, 27 negative control, 9 verifier control và mutant `if (true)`. Bằng chứng local: analyze sạch, **240 Flutter +1 skip**, **23 DB**, **11/11 browser**, **27/27 negative case đúng kỳ vọng**, **9/9 verifier control**, mutant PASS, **33/33 manifest**, `is_dirty=false`, Web build PASS. App/backend không đổi; giữ A/B/C/D và HTTP/Auth/concurrency Đạt local. Toàn BH-07/pilot chưa nghiệm thu; mobile, delayed response sau đổi actor, banking/webhook, staging/production/backup, rehearsal/pilot và `supabase db reset` vẫn NOT RUN. Không merge/apply DB thật/deploy; người triển khai không tự ghi Đạt.

(Lịch sử review) Ngày 23/10/2026: Gói **Browser / Offline / Reopen BH-07 Chưa đạt vòng2/2** tại source `51cb3b1`, docs/evidence `eadb5c7`, theo [review độc lập](docs/reviews/bh07/review_eadb5c7.md). Đóng BR1 và ca SPA BR4; lỗi P1 retry đã sửa nhưng **BR2 còn P2**, **BR3/BR5 P2 còn mở** về gate UI error, aggregate/ACL và verifier/negative controls/provenance. Reviewer tự chạy analyze sạch, **240 Flutter +1 skip**, **23 DB**, **11/11 browser**, Web build PASS; **21/21 hash**, readonly missing/hash/sb_secret controls PASS. Tuy nhiên4 control BR3, silent-error, JWT/UTF8 và mutant negative-runner vẫn được nhận xanh sai. **Dừng gói sau2 vòng theo AGENTS, chờ quyết định chủ dự án; không tự mở vòng3 hoặc giao sửa tiếp.** App/backend không đổi; giữ A/B/C/D và HTTP/Auth/concurrency Đạt local. Toàn BH-07/pilot chưa nghiệm thu; mobile/banking/webhook/staging/production/backup/rehearsal/pilot và response trễ sau đổi actor vẫn NOT RUN. Không merge/apply DB thật/deploy.

(Lịch sử review) Gói kiểm chứng **Browser / Offline / Reopen BH-07 Chưa đạt tại `c8a8e7f`** theo [review độc lập](docs/reviews/bh07/review_c8a8e7f.md). Mở **BR1/BR2 P1, BR3–BR5 P2**: runner bỏ qua UI, không kiểm mutation offline/request_id, copy/privacy/ACL và auth/cache chưa đủ, thiếu log/provenance. Đã chuyển sang sửa gói kiểm chứng vòng 1/2.

(Lịch sử review) Gói kiểm chứng **Concurrency HTTP/Auth BH-07 Đạt local vòng2/2**, tested source `cbcc46c`, docs/evidence thực tế `bb940280333aec96457dd3014aabba9f66adf4ae`, theo [review độc lập](docs/reviews/bh07/review_cbcc46c_r2.md).

**BH-06 đã Đạt tích hợp local tại `318bc52` và merge vào main tại `e7f7627`.** [Review/bằng chứng](docs/reviews/bh06/review_318bc52.md), [xác minh merge main](docs/reviews/bh06/main_merge_e7f7627.md). Quy trình [người triển khai](docs/ai/IMPLEMENTER.md) và [reviewer](docs/ai/REVIEWER.md) cũng đã có trên main.

| Ticket | Kiểm chứng DB local | Trạng thái |
|---|---|---|
| BH-01 | Flutter/Auth fixture | Đã triển khai; chưa kiểm Auth HTTP thật đầy đủ |
| BH-02 | 33 +14 PASS | Đã triển khai |
| BH-03 | 48 +22 PASS | Đã triển khai |
| BH-04 | 44 PASS | Đã triển khai |
| BH-05 | 90 PASS | Đạt tích hợp; giữ lịch sử review/hồi quy main |
| BH-06 | 84 PASS; tích hợp 7, nâng cấp 3 | Đạt tích hợp local; đã merge main |
| BH-07 | Browser+response trễ đã đóng Đạt local | **Codex review/tự sửa không độc lập; tiếp backup/restore local; toàn BH-07/pilot chưa nghiệm thu** |

Baseline reviewer BH-06: analyze sạch, **190 Flutter +335 DB hồi quy +7 tích hợp +3 nâng cấp +2 probe PASS**. Các nhóm là bằng chứng local riêng biệt, không phải HTTP/e2e. Merge main giữ nguyên code/test/migration đã review; phân biệt kiểm tra mới với bằng chứng DB trước merge trong báo cáo merge.


## Tài liệu để triển khai

Bắt đầu tại **[docs/00_START_HERE.md](docs/00_START_HERE.md)**. Bộ đặc tả v1.1 ngày 14/10/2026 gồm:

- [Yêu cầu sản phẩm](docs/01_PRD_SPEC.md).
- [Kiến trúc tổng thể](docs/02_ARCHITECTURE.md).
- [Cơ sở dữ liệu, ERD và phân quyền](docs/03_DATABASE.md).
- [Quy tắc cho Antigravity/AI](docs/04_LLM_RULES.md).
- [Hợp đồng thao tác nghiệp vụ](docs/08_DOMAIN_CONTRACTS.md).
- [Backlog và nghiệm thu](docs/09_IMPLEMENTATION_PLAN.md).
- [Đầu bài BH-07 và cổng A/B/C/D](docs/25_BH07_IMPLEMENTATION_HANDOFF.md).
- [Luồng màn hình](docs/10_SCREEN_FLOWS.md).
- [Rà soát code và tham khảo Vmito](docs/07_HOST_FIRST_REVIEW.md).

SQL 05/06 là legacy; không chạy để tạo schema mới hoặc vào production. Các migration trong `supabase/migrations/` mới chỉ được kiểm thử trên PostgreSQL cô lập.

## Chạy dự án hiện có

Cài Git, Flutter SDK tương thích `pubspec.yaml`, VS Code/extensions nếu cần. Clone repo và mở thư mục:

```bash
git clone https://github.com/phongnt911/badminton-hub.git
cd badminton-hub
flutter pub get
flutter run -d chrome
# Windows: flutter run -d windows
# macOS: flutter run -d macos
# Mobile: flutter devices rồi chọn thiết bị
```

## Cấu hình môi trường & Supabase

Dự án sử dụng `AppConfig` (`lib/core/app_config.dart`) để quản lý cấu hình kết nối. Không có kết nối mặc định. Bắt buộc truyền APP_ENV (dev/staging/prod/test), URL và public anon key qua `--dart-define`; project production chỉ chấp nhận APP_ENV=prod. Test chỉ chấp nhận URL local:

```bash
flutter run --dart-define=APP_ENV=dev --dart-define=SUPABASE_URL=https://your-project.supabase.co --dart-define=SUPABASE_ANON_KEY=your-anon-key
```

### Công cụ dòng lệnh tương tác trực tiếp với Supabase
Để kiểm tra kết nối hoặc truy vấn dữ liệu từ terminal mà không cần khởi động toàn bộ app:

```bash
# Kiểm tra kết nối REST API và Auth API
dart run scripts/supabase_client.dart ping

# Truy vấn nhanh dữ liệu bảng (ví dụ: venues)
dart run scripts/supabase_client.dart query venues

# Xem thông tin cấu hình dự án
dart run scripts/supabase_client.dart info
```

## Kiểm tra chất lượng (Quality Assurance)

```bash
flutter analyze
flutter test
```

Test DB chạy bằng các runner Python trong `docs/reviews/bh0X/` (cần Docker); kết quả và giới hạn từng ticket xem bảng "Trạng thái hiện tại" và các file bàn giao. Kết quả "đạt" chỉ có giá trị khi kèm bằng chứng và phần NOT RUN được ghi rõ.

## Dùng với Antigravity

Mở đúng checkout repo, đọc `AGENTS.md` (gồm quy trình hai AI: người triển khai và người review độc lập) và `docs/00_START_HERE.md`, rồi yêu cầu từng ticket (tiếp theo là BH-06 theo docs/09_IMPLEMENTATION_PLAN.md). Nếu làm trên máy cá nhân khác, dùng GitHub Desktop Pull hoặc `git pull --ff-only` trên nhánh main trước khi yêu cầu code; file trong cloud workspace không tự xuất hiện ở checkout máy cá nhân.

## Đầu bài Antigravity v1.1

- [ADR và đánh đổi](docs/11_ARCHITECTURE_DECISIONS.md).
- [Prompt từng bước và tiêu chí báo cáo](docs/12_ANTIGRAVITY_PROMPTS.md).

Bắt đầu AG-00 để ghi baseline và môi trường test, sau đó AG-01 trở đi theo phụ thuộc. Phát hiện P1/P2 được chuyển thành yêu cầu và test; code/DB chưa tự thay đổi khi tài liệu được cập nhật.

## Nghiên cứu ứng dụng tương tự

Đã tiếp nhận báo cáo REA tĩnh của Vmito và Vụt: [bản áp dụng vào Badminton Hub](docs/14_PRODUCT_LEARNINGS_VMITO_VUT.md). Bổ sung yêu cầu link/filter/trạng thái/QR và release privacy cho BH-03..07; không đổi stack hoặc tự triển khai chat/push/GPS. Quan sát thư viện/endpoints không được coi là chức năng runtime đã kiểm chứng.

## Đầu bài BH-03

Hiện hành 16/10/2026: mục này và các bàn giao BH-03/BH-04 bên dưới là lịch sử. Tiếp tục BH-06 theo trạng thái đầu file, không triển khai lại từ các prompt cũ.

Tiếp tục CLB, thành viên và tài khoản nhận tiền theo [15_BH03_IMPLEMENTATION_HANDOFF.md](docs/15_BH03_IMPLEMENTATION_HANDOFF.md): RPC nguyên tử, role/privacy, models/repository/provider, UI và acceptance từng phần. Bắt đầu từ trạng thái thực tế của IDE, giữ regression BH-02; không làm lại migration hoặc tính năng đã có.

## BH-03 sau review

Đã sửa C1–C5 bằng [forward migration và app/session retry](docs/17_BH03_REMEDIATION.md). Xác minh Flutter 3.47.7/Dart 3.13.5: 61 tests PASS, analyze sạch; PostgreSQL cô lập 109 checks PASS. Chưa apply Supabase production hoặc kiểm full HTTP/JWT; giữ đúng giới hạn báo cáo trước rollout.

Bàn giao phiên tiếp theo: [19_PRE_BH04_HANDOFF.md](docs/19_PRE_BH04_HANDOFF.md). CLI đọc cần SUPABASE_URL/SUPABASE_ANON_KEY từ environment; script update_db chỉ seed local.

BH-04 review remediation: [21_BH04_REMEDIATION.md](docs/21_BH04_REMEDIATION.md). Chia sẻ link trên mobile cần `--dart-define=APP_BASE_URL=https://<domain-web-da-trien-khai>`; web mặc định dùng origin hiện tại. Hosting cần fallback index.html cho đường dẫn tài nguyên; OS App Links chưa cấu hình.

BH-05: xem [22_BH05_HANDOFF.md](docs/22_BH05_HANDOFF.md) (đăng ký/duyệt/huỷ/điểm danh/lời mời danh sách chờ/bắt đầu buổi; đạt review tích hợp tại `d769531` và hồi quy main tại `3a34883`, xem [review_d769531.md](docs/reviews/bh05/review_d769531.md)).

## Giao việc BH-06 — 16/10/2026 (lịch sử)

Chủ dự án giao AI triển khai ở phiên mới kéo main và làm từng phần; Codex giao việc/review độc lập. [Đầu bài BH-06A, cổng A→B→C và prompt phiên mới](docs/24_BH06_IMPLEMENTATION_HANDOFF.md). Trạng thái: đã giao phần A, chưa triển khai/chưa review.
