# BH-06 tích hợp — bàn giao "Chờ review tích hợp"

Ngày 20/10/2026. Người triển khai: DeepSeek. Người review độc lập: Codex.

> **Hiện hành reviewer 20/10/2026: Chưa đạt tích hợp tại `afeff39`** theo [review độc lập](review_afeff39.md): I1 P1 thiếu backfill receiver, I2 P2 refresh không cập nhật session version. Reviewer tự chạy analyze sạch, 189 Flutter +335 DB +6 tích hợp PASS; 2 probe FAIL. Các kết quả/trạng thái bàn giao bên dưới là lịch sử phía tác giả.

> **Trạng thái bàn giao ban đầu: Chờ review tích hợp.** Người triển khai không tự ghi "Đạt"/"Done".
> Chưa merge `main`, chưa deploy, chưa apply staging/production.

## 1. Nhánh và SHA

| Mục | Giá trị |
|---|---|
| Nhánh tích hợp | `feat/bh06-integration` |
| Base | `a9c7edb` (tip C; chứa A `706bd73`, B `5e62007`, C `b31f988`) |
| Dependency A | `48d45d2` (A tách từ đây) |
| Dependency B | `f28fd0f` (B tách từ đây) |
| Commit code + test tích hợp | `8af7be5` |
| Commit bằng chứng trên cây sạch | `6ecefb2` |
| Commit tài liệu (báo cáo này) | commit ngay sau `6ecefb2` trên cùng nhánh |

Đã kiểm tra `git merge-base --is-ancestor` cho `706bd73`, `5e62007`, `b31f988`,
`48d45d2`, `f28fd0f` trên `a9c7edb`; không cherry-pick commit nào.

## 2. Phạm vi đã kiểm chứng

- Đọc lại ba review A/B/C và các ghi chú sửa C1–C4; không mở lại phạm vi BH-07.
- Đối chiếu hợp đồng DB → model/repository/provider → UI:
  - `get_session_finance`, `get_payment_instructions`, `get_club_ledger` với
    `SessionFinance`/`PaymentInstructions`/`ClubLedger` và các màn BH-06C.
  - Tên/đối số RPC của repository, wiring `FinanceProvider` trong `main.dart`,
    phân quyền owner/treasurer/host/member/anon, phân trang sổ quỹ.
  - Chuỗi chi phí → điểm danh/miễn phí → chốt phí → hướng dẫn/QR → gửi
    chuyển khoản → confirm/reject/cash/reverse → sổ quỹ; stale khi input đổi;
    chốt lại và trả thêm; chống thu dư; idempotency; lịch sử tài chính.
- Chạy lại toàn bộ runner DB BH-02..BH-06 và test Flutter trên nhánh tích hợp.
- Thêm bằng chứng xuyên lớp mới:
  - `run_integration_tests.py`: 6 case DB end-to-end (gồm receiver snapshot,
    stale/refinalize/trả thêm/hoàn tác/reject/idempotency/quyền/sổ quỹ/DTO).
  - `test/integration/bh06_finance_flow_test.dart`: 2 widget test đi qua
    `SessionFinanceScreen` → `FinanceProvider` thật → `FinanceRepository`
    (mock tại ranh giới RPC), kiểm tra tham số thật sự gửi xuống và refresh.

## 3. Lỗi tích hợp phát hiện và cách sửa

### 3.1. Hiện tượng

`receiver_snapshot` của buổi chơi **không được ghi ở bất kỳ đâu** trong chuỗi
migration/RPC hiện có. Sau khi chốt phí:

- `get_payment_instructions` trả `has_receiver = false`, `receiver_snapshot = null`.
- UI BH-06C rơi vào nhánh "Chưa có tài khoản nhận tiền", không tạo QR và không
  hiện nút "Tôi đã chuyển khoản". Toàn bộ luồng chuyển khoản → confirm không
  thể dùng từ ứng dụng, dù DB/RPC phía sau đã có.

Bằng chứng trước khi sửa (base `a9c7edb`):
`integration_results_20261020031956.json` — 1/6 PASS; case luồng đầy đủ dừng ở
`has_receiver: false` / `receiver_snapshot: None`.

### 3.2. Căn cứ sửa

- `docs/03_DATABASE.md` dòng 66: receiver phải thuộc đúng CLB/host; snapshot
  được chốt khi publish/chốt phí.
- `docs/08_DOMAIN_CONTRACTS.md`: publish kiểm tra cấu hình tài khoản nhận tiền;
  QR dựng từ receiver snapshot.
- Schema đã có `receiver_club_bank_account_id`, `receiver_host_bank_account_id`,
  `receiver_snapshot`; BH-03 đã có RPC cấu hình tài khoản CLB/host.

### 3.3. Thay đổi

Migration forward mới:
`supabase/migrations/20261020100000_bh06_integration_receiver.sql`
(SHA-256 `601f96fe3959263ad220632741b842dd5583f054962e1100656844a7a9a2eead`).

- `resolve_session_receiver(club_id, host_user_id)`: chọn tài khoản `active`
  của CLB nếu buổi gắn CLB; nếu CLB chưa có thì fallback tài khoản `active`
  của host. Trả kind/id/snapshot JSON.
- Trigger `BEFORE INSERT/UPDATE` trên `sessions`: khi buổi ở
  `published`/`in_progress`/`completed` và `receiver_snapshot` còn NULL thì
  chốt snapshot + FK tương ứng. **Không ghi đè snapshot đã chốt** (giữ lịch sử
  đối soát); draft không bị chốt.
- Trigger `AFTER INSERT/UPDATE` trên `club_bank_accounts`/`host_bank_accounts`:
  điền snapshot cho các buổi đang mở chưa có snapshot, để host cấu hình ngân
  hàng sau publish/start vẫn mở được hướng dẫn/QR.
- Các helper `SECURITY DEFINER`, `REVOKE` khỏi `PUBLIC, anon, authenticated`;
  không đổi RLS, không ghi số dư, không thêm dependency, không đổi công thức chia phí.

Đây là thay đổi DB thuộc phạm vi BH-06 (QR/hướng dẫn thanh toán), không phải
tính năng BH-07. Quy tắc chọn tài khoản (CLB trước, host fallback) là diễn giải
tối thiểu từ schema/docs; reviewer cần xác nhận hướng này hoặc yêu cầu bổ sung
API chọn receiver nếu chủ dự án muốn host tự chọn.

### 3.4. Sau khi sửa

- `integration_results_final.json`: 6/6 PASS trên cây sạch `8af7be5`
  (host bank chốt khi publish; buổi CLB ưu tiên tài khoản CLB; cấu hình bank
  sau publish vẫn mở được hướng dẫn; draft không chốt; luồng đầy đủ; DTO).
- Không có thay đổi code ứng dụng nào khác: UI vốn đã đúng khi có snapshot.

## 4. Bằng chứng chạy trên cây sạch `8af7be5` (commit bằng chứng `6ecefb2`)

Môi trường: Windows, Flutter 3.47.6 stable, Python 3.12.7, Docker PostgreSQL
17.11 (container `bh02-test-postgres`, Auth stub `request.jwt.claim.sub`).

| Lệnh | Exit | Kết quả | Bằng chứng |
|---|---|---|---|
| `flutter analyze` | 0 | No issues found | `integration_evidence/flutter_analyze_postfix.log` |
| `flutter test` | 0 | 189/189 PASS | `integration_evidence/flutter_test_postfix.log` |
| `python docs/reviews/bh06/integration_evidence/run_integration_tests.py` | 0 | 6/6 PASS | `integration_results_final.json`, `integration_results_20261020033850.json`, `integration_probe_clean.log` |
| `python docs/reviews/bh02/run_rls_tests.py` | 0 | 33/33 | `bh02_postfix.log`, `bh02_postfix_results.json` |
| `python docs/reviews/bh02/extended_tests_15ef59b.py` | 0 | 14/14 | `bh02_extended_postfix.log`, `bh02_extended_postfix_results.json` |
| `python docs/reviews/bh03/run_bh03_tests.py` | 0 | 48/48 | `bh03_postfix.log`, `bh03_postfix_results.json` |
| `python docs/reviews/bh03/run_bh03_retry_tests.py` | 0 | 22/22 | `bh03_retry_postfix.log`, `bh03_retry_postfix_results.json` |
| `python docs/reviews/bh04/run_bh04_tests.py` | 0 | 44/44 | `bh04_postfix.log`, `bh04_postfix_results.json` |
| `python docs/reviews/bh05/run_bh05_tests.py` | 0 | 90/90 | `bh05_postfix.log`, `bh05_postfix_results.json` |
| `python docs/reviews/bh06/run_bh06_tests.py` | 0 | 84/84 | `bh06_postfix.log`, `bh06_postfix_results.json` |

Tổng DB: 33 + 14 + 48 + 22 + 44 + 90 + 84 = **335/335 PASS**.
Flutter: **189/189 PASS** (187 cũ + 2 widget test tích hợp mới).

Log trước khi sửa (cùng bộ runner, base `a9c7edb`) được giữ ở các file
`*_prefix.log`; bộ này cũng 335/335 và xác nhận lỗi receiver không làm hỏng
các case DB sẵn có (vì chưa case nào khẳng định `has_receiver = true`).

## 5. Chưa chạy / NOT RUN

- HTTP/PostgREST/JWT/Auth thật: không có Supabase CLI, không có stack
  PostgREST + JWT local. Runner dùng `SET ROLE` + Auth stub, không phải JWT thật.
- Apply staging/production, merge `main`, deploy: **không chạy**.
- QR VietQR qua mạng thật, ngân hàng thật, webhook: không có; widget test chỉ
  kiểm tra URL/key/copy và errorBuilder của `Image.network`.
- Thiết bị thật (Android/iOS/web), deep link, callback: không chạy.
- Diễn tập backup/restore, migration trên dữ liệu production: không chạy.
- Đa kết nối PostgreSQL thật cho mọi case mới: chỉ runner hiện có dùng
  kết nối Docker; case tích hợp chạy tuần tự.

## 6. Quan sát chưa sửa (không chặn tích hợp, đề nghị reviewer phân loại)

1. **P2 UX — gửi trùng pending**: người chơi có thể bấm "Tôi đã chuyển khoản"
   nhiều lần trước khi manager xác nhận; server vẫn chặn thu dư khi confirm
   nhưng UI không hiển thị khoản đang chờ cho người chơi.
2. **P2 UX — version snapshot**: `SessionFinanceScreen` dùng
   `widget.session.version` tại thời điểm mở; nếu buổi bị sửa ở nơi khác, chốt
   phí trả `VERSION_CONFLICT` và màn hình không tự lấy version mới (phải rời
   màn hình mở lại). Không có bằng chứng hỏng dữ liệu.
3. **Ngoài phạm vi C**: chưa có nút "Kết thúc buổi" trên UI; `complete_session`
   chỉ có repository/provider (BH-07 theo docs/24 §3.C). Không sửa.

## 7. Cách tái lập nhanh

```powershell
# Container PostgreSQL test (đã có role anon/authenticated/service_role)
$env:BH02_TEST_CONTAINER='bh02-test-postgres'
python docs\reviews\bh06\integration_evidence\run_integration_tests.py

# Toàn bộ runner DB
python docs\reviews\bh02\run_rls_tests.py
python docs\reviews\bh02\extended_tests_15ef59b.py
python docs\reviews\bh03\run_bh03_tests.py
python docs\reviews\bh03\run_bh03_retry_tests.py
python docs\reviews\bh04\run_bh04_tests.py
python docs\reviews\bh05\run_bh05_tests.py
python docs\reviews\bh06\run_bh06_tests.py

flutter analyze
flutter test
```

Lưu ý môi trường: runner tạo DB mới `bhXX_*` mỗi lần; cần container PostgreSQL
có sẵn các role `anon`, `authenticated`, `service_role` (không có trong
migration). Các file JSON do runner sinh trong `docs/reviews/bhXX/` đã được
chép sang `integration_evidence/` và không commit ở thư mục gốc.

## 8. Đề nghị review

- Kiểm tra migration trigger: không ghi đè snapshot đã chốt, không rò bank qua
  projection public, không ảnh hưởng RLS/lịch sử.
- Xác nhận quy tắc receiver (CLB trước, host fallback) hoặc yêu cầu API chọn
  receiver nếu cần quyết định sản phẩm khác.
- Đánh giá chất lượng 2 widget test tích hợp (mock tại ranh giới RPC, không
  tuyên bố HTTP thật) và 6 case DB xuyên lớp.
- Phân loại 3 quan sát ở §6 và quyết định có cần sửa trước merge hay không.
