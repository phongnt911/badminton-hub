# Badminton Hub

Ứng dụng Flutter + Supabase giúp host quản lý CLB, lịch sinh hoạt, đăng ký vãng lai, điểm danh, chốt phí và thu/chi. Thị trường pilot: Nha Trang.

## Trạng thái hiện tại — 20/10/2026

**BH-06 đã Đạt tích hợp local tại `318bc52` và merge vào main tại `e7f7627`.** [Review/bằng chứng](docs/reviews/bh06/review_318bc52.md), [xác minh merge main](docs/reviews/bh06/main_merge_e7f7627.md). Quy trình [người triển khai](docs/ai/IMPLEMENTER.md) và [reviewer](docs/ai/REVIEWER.md) cũng đã có trên main.

| Ticket | Kiểm chứng DB local | Trạng thái |
|---|---|---|
| BH-01 | Flutter/Auth fixture | Đã triển khai; chưa kiểm Auth HTTP thật đầy đủ |
| BH-02 | 33 +14 PASS | Đã triển khai |
| BH-03 | 48 +22 PASS | Đã triển khai |
| BH-04 | 44 PASS | Đã triển khai |
| BH-05 | 90 PASS | Đạt tích hợp; giữ lịch sử review/hồi quy main |
| BH-06 | 84 PASS; tích hợp 7, nâng cấp 3 | Đạt tích hợp local; đã merge main |
| BH-07 | 23 PASS (A); B/C/D chưa chạy | **Đạt phần A local tại 4512c3a**, chưa nghiệm thu toàn BH-07 |

Baseline reviewer BH-06: analyze sạch, **190 Flutter +335 DB hồi quy +7 tích hợp +3 nâng cấp +2 probe PASS**. Các nhóm là bằng chứng local riêng biệt, không phải HTTP/e2e. Merge main giữ nguyên code/test/migration đã review; phân biệt kiểm tra mới với bằng chứng DB trước merge trong báo cáo merge.

[BH-07A đã Đạt local](docs/reviews/bh07/review_4512c3a.md); B/C/D và pilot chưa nghiệm thu. Giữ [cổng hai AI](docs/25_BH07_IMPLEMENTATION_HANDOFF.md), không tự chuyển phần. Chưa nghiệm thu HTTP/PostgREST/JWT/Auth thật, mobile/web/deep link e2e, ngân hàng/VietQR thật, staging/production, backup/restore hoặc concurrency HTTP. **Chưa deploy; merge code không phải apply DB.** Nhật ký nằm ở [STATUS_HISTORY](docs/STATUS_HISTORY.md).

## Tài liệu để triển khai

Bắt đầu tại **[docs/00_START_HERE.md](docs/00_START_HERE.md)**. Bộ đặc tả v1.1 ngày 14/10/2026 gồm:

- [Yêu cầu sản phẩm](docs/01_PRD_SPEC.md).
- [Kiến trúc tổng thể](docs/02_ARCHITECTURE.md).
- [Cơ sở dữ liệu, ERD và phân quyền](docs/03_DATABASE.md).
- [Quy tắc cho Antigravity/AI](docs/04_LLM_RULES.md).
- [Hợp đồng thao tác nghiệp vụ](docs/08_DOMAIN_CONTRACTS.md).
- [Backlog và nghiệm thu](docs/09_IMPLEMENTATION_PLAN.md).
- [Đầu bài BH-07A và cổng A/B/C/D](docs/25_BH07_IMPLEMENTATION_HANDOFF.md).
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
