# Lệnh tái lập gói Browser / Offline / Reopen BH-07 (sửa cuối theo ủy quyền)

Tài liệu này ghi lại các lệnh đã chạy để tạo bằng chứng trong thư mục này. Đây là
gói kiểm chứng browser/offline/reopen; **không phải** nghiệm thu toàn BH-07 hoặc pilot.

## Nguồn và môi trường

- Base: `b5517df1055ded3de86bdce49927188eab8e53d8`
- Source đã kiểm thử: `a62f509986f65592da3fb5bccebe7b7c246ff7b7`
- Branch: `feat/bh07-browser-verification`
- Trạng thái checkout khi bắt đầu browser matrix: `is_dirty=false`, `dirty_details=""`
- Windows 11 IoT Enterprise LTSC 10.0.26100; Flutter 3.47.6 / Dart 3.13.5;
  Node v24.21.0; Python 3.12.7; Chrome 155.0.8059.85; Supabase CLI 2.121.0;
  PostgreSQL 17.11 trong container `bh02-test-postgres`.
- Local Supabase API: `http://127.0.0.1:54321`; web bundle: `http://127.0.0.1:8088`.

Các log được ghi bằng redirect raw của `cmd.exe` (không dùng `Tee-Object` của
PowerShell 5.1), sau đó chuẩn hóa UTF-8 không BOM + LF bằng
`clean_and_manifest.py --generate`. Vì vậy log giữ đúng tiếng Việt và không có
UTF-16/CRLF.

## 1. Build Flutter Web

```bat
flutter build web --dart-define=APP_ENV=test ^
  --dart-define=SUPABASE_URL=http://127.0.0.1:54321 ^
  --dart-define=SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0
```

Ghi log: `web_build.log` (UTF-8 LF, có `EXIT_CODE=0`).

## 2. Web server tĩnh

```bat
python -m http.server 8088 --directory build/web
```

Access log được lưu ở `web_server.access.log`; server chỉ phục vụ `build/web`
trên loopback và đã dừng sau browser matrix.

## 3. Browser matrix thật (Chrome headless + CDP)

```bat
node scripts\bh07_browser\run_browser_verification.js
```

Script tự gọi `seed_setup.js` để truncate/seed fixture, chạy 11 kịch bản UI thật
và ghi `summary.json`, `browser_runner.log`, 12 ảnh PNG trong `screenshots/`.
Console đầy đủ nằm ở `browser_runner.console.log`.

Kết quả: **11/11 PASS, exit 0**; `tested_checkout_sha=a62f509...`,
`is_dirty=false`, 12/12 ảnh có hash khác nhau.

Các contract chính đã được kiểm:

- Manager clipboard: đúng `200,000 VNĐ` cho tổng chi phí, tổng phải thu và còn
  phải thu; `0 VNĐ` cho đã thu; không có field lạ hoặc dấu `—`.
- Cohost clipboard/UI: chỉ có header/địa điểm/thời gian/dòng đếm
  `👥 Có mặt: 1 · Vắng: 0 · Đã xác nhận: 2`; không có card tài chính, số tiền,
  contact, ngân hàng, tài khoản hoặc receiver.
- History: request thật có `p_club_id` của HTTP Club A; response đúng một ID
  `10000000-0000-4000-8000-000000000099`; màn hình chỉ có đúng một row marker.
  Member A gửi `p_club_id=null`, response `[]`, màn hình chỉ có
  `Chưa có buổi nào` và không có row/Club B/treasury.
- Offline complete: UI hiện đúng lỗi `Đã xảy ra lỗi. Vui lòng thử lại sau.`,
  không hiện success; sau khi online lại có đúng 2 POST `complete_session` cùng
  `p_request_id` và cùng toàn bộ payload; DB/audit chỉ có 1 operation và 1
  `SESSION_COMPLETED`.

## 4. Flutter analyze và test

```bat
flutter analyze
flutter test
```

Kết quả: analyze exit 0, không issue; test exit 0, **240 test + 1 skip**.
Log: `analyze.log`, `flutter_test.log`.

## 5. DB runner BH-07

```powershell
$env:BH02_TEST_CONTAINER='bh02-test-postgres'
python -u docs\reviews\bh07\run_bh07_tests.py
```

Kết quả: **23/23 PASS**, exit 0. Log: `bh07_db_runner.log`; JSON đã copy sang
`bh07_db_results.json`. Runner tạo DB test riêng và không đụng DB khác.

## 6. Negative controls dùng predicate hiện tại

```bat
node scripts\bh07_browser\run_negative_controls.js
```

Kết quả: **27/27 case**, 7 PASS + 20 FAIL đúng kỳ vọng, 0 HARNESS_ERROR, exit 0.
`negative_controls.json` ghi source SHA, hash của `assertions.js` và runner,
marker errors, case count và toàn bộ kết quả. Log đầy đủ:
`negative_controls.log`.

## 7. Verifier controls (read-only)

```bat
python scripts\bh07_browser\run_verifier_controls.py
```

Kết quả: **9/9 control đúng**, exit 0. Baseline pass; missing/extra/hash mismatch/
fake secret/fake service_role JWT/invalid UTF-8/BOM/CRLF đều exit 1 và
`readonly=True` (snapshot trước/sau giống nhau). Log chi tiết:
`verifier_controls.log`; stdout: `verifier_controls.stdout.log`; JSON:
`verifier_controls.json`.

## 8. Mutant control cho manager gate

```bat
python scripts\bh07_browser\run_mutant_controls.py
```

Kết quả: bản copy không sửa exit 0; bản đổi gate thành `if (true)` exit 1;
mutant control PASS, exit 0. Log chi tiết: `mutant_negative_control.log`;
stdout: `mutant_negative_control.stdout.log`; JSON:
`mutant_negative_control.json`.

## 9. Manifest và kiểm tra read-only

```bat
python scripts\bh07_browser\clean_and_manifest.py --generate
python scripts\bh07_browser\clean_and_manifest.py --verify
```

`--generate` chuẩn hóa text UTF-8 LF, quét secret/JWT và ghi `hashes.sha256`.
`--verify` chỉ đọc; fail nếu thiếu file, thừa file, hash lệch, UTF-8 sai, có BOM,
có CR/CRLF, hoặc có secret/JWT ngoài public anon allowlist. Chỉ public anon JWT
trong lệnh build ở trên được allowlist; JWT `service_role` bị decode và từ chối.

## Bảng exit thực tế

| Bước | Exit |
|---|---:|
| `flutter build web` | 0 |
| `seed_setup.js` (trong browser runner) | 0 |
| `run_browser_verification.js` | 0 |
| `flutter analyze` | 0 |
| `flutter test` | 0 |
| `run_bh07_tests.py` | 0 |
| `run_negative_controls.js` | 0 |
| `run_verifier_controls.py` | 0 |
| `run_mutant_controls.py` | 0 |
| `clean_and_manifest.py --generate` | 0 |
| `clean_and_manifest.py --verify` | 0 |
| `supabase db reset` toàn bộ | NOT RUN |

`exits.json` là bản ghi máy đọc của bảng này, gồm cả danh sách NOT RUN.

## NOT RUN / ngoài phạm vi

- Thiết bị/mobile và browser khác.
- Response trễ sau khi đổi actor.
- Banking/VietQR/webhook.
- Staging, production, backup/restore.
- Rehearsal và pilot.
- `supabase db reset`/reset toàn bộ DB; chỉ seed fixture qua `seed_setup.js`.

Không có merge main, apply DB thật, deploy hoặc chạy pilot trong gói này. Trạng
thái bàn giao là **Chờ review lần sửa cuối theo ủy quyền bổ sung**; người triển
khai không tự ghi Đạt.
