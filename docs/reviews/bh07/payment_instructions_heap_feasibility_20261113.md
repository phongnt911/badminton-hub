# Báo cáo Khả thi & Thiết kế Kỹ thuật: Mở rộng BH-07 V2b Heap Coverage cho `PaymentInstructions`

**Ngày:** 2026-11-13
**Base commit tham chiếu:** `feat/bh07-completion-local` (`7816f5c`)
**Loại tài liệu:** Thẩm định khả thi & thiết kế chỉ-đọc (**READ-ONLY feasibility/design**)
**Trạng thái:** **CHƯA TRIỂN KHAI / RUNTIME NOT RUN / KHÔNG TỰ GHI PASS**

> **Tuyên bố phạm vi (Scope & Authority):**
> - Tài liệu này chỉ phân tích tính khả thi và đề xuất kiến trúc tối thiểu cho cổng V2b đối với `PaymentInstructions` (hạng mục `2.3` đang `NOT RUN` trong [v2b_coverage_map.md](v2b_coverage_map.md)).
> - **Không** sửa code ứng dụng, schema/migration, script/test, không chạy runtime/browser/DB, **không** chấp nhận rủi ro, **không** nghiệm thu toàn V2b / BH-07 / V8, và **không** merge/deploy/pilot/BH-08.

---

## 1. Kết luận tóm tắt (Executive Verdict)

1. **Khả thi ở mức hẹp, không cần sửa app hoặc schema/migration.** Phương án đưa **hai trường JSON tổng hợp chứa giá trị UUID ngẫu nhiên phân biệt** vào cột `sessions.receiver_snapshot` (JSONB) của một **buổi chơi dùng một lần (disposable session)**, rồi để `Owner` nạp qua luồng UI thật (`Thu tiền mặt` -> `get_payment_instructions` -> bấm `Huỷ` ở dialog nhập số tiền), truyền được hai chuỗi không-render xuyên suốt qua `PaymentInstructions.fromJson` -> `_asMap(...)` -> `FinanceProvider._instructions` mà **không** tạo bản ghi thanh toán, sổ quỹ hay audit mutation.
2. **Không thể chạy trực tiếp bằng `run_app_profile_heap.js` hiện có.** Runner hiện tại gọi `npx --yes supabase@2.121.0 status -o env` (`scripts/bh07_appheap/run_app_profile_heap.js#L214`), không tương thích với cụm fixture 4 container hiện hành (`bh07-android-db/auth/rest/kong` trên `127.0.0.1:54321`), và buffering snapshot trong RAM (`chunks.push` / `chunks.join('')`, `#L693-L731`). Cần một **companion runner mỏng** (hoặc chế độ cô lập mới không sửa spec/bundle cũ) stream chunk CDP thẳng ra file tạm ngoài repo.
3. **Phạm vi chứng minh bị giới hạn nghiêm ngặt.** Kết quả âm tính sau logout/đổi actor chỉ chứng minh **hai chuỗi canary JSON tổng hợp trong `FinanceProvider._instructions.receiverSnapshot` không còn reachable trong V8 profile heap Web** ở 2 chu kỳ cùng document — **không** chứng minh retention của toàn bộ model `PaymentInstructions`, **không** quy kết các chuỗi có render (`bank_code`, `account_number`, `account_name`, `reference`), và **không** phủ listener `AuthProvider` hay Dart VM native/Safari/Firefox.

---

## 2. Truy vết kỹ thuật End-to-End (DB -> RPC -> DTO -> Provider -> UI)

### 2.1. Đường đi của sentinel từ DB vào `FinanceProvider._instructions`
| Tầng | Symbol / File (đã đọc trực tiếp) | Hành vi xác minh từ mã nguồn |
| --- | --- | --- |
| **DB & Trigger** | `sessions.receiver_snapshot` + `bh06_sessions_receiver_snapshot` ([20261020100000_bh06_integration_receiver.sql](../../../supabase/migrations/20261020100000_bh06_integration_receiver.sql)) | Trigger `BEFORE INSERT OR UPDATE` kiểm tra `IF NEW.receiver_snapshot IS NOT NULL THEN RETURN NEW; END IF;`. Vì vậy `INSERT INTO public.sessions` truyền sẵn JSONB chứa đủ `bank_code`, `account_number`, `account_name` **kèm 2 key tổng hợp mới** sẽ giữ nguyên 100% hai key đó trong DB mà không bị trigger ghi đè. |
| **RPC** | `get_payment_instructions` ([20261016140000_bh06a_review_round1.sql](../../../supabase/migrations/20261016140000_bh06a_review_round1.sql#L64-L65)) | Trả trực tiếp `receiver_snapshot` JSONB của session cho caller thoả ACL (`has_session_finance_access(p_session_id, v_actor)` hoặc player `confirmed` của chính `v_actor`). |
| **Repository** | `FinanceRepository.getPaymentInstructions` ([lib/data/finance_repository.dart](../../../lib/data/finance_repository.dart)) | Gọi `_client.rpc('get_payment_instructions', ...)` và trả `PaymentInstructions.fromJson(...)`. |
| **DTO** | `PaymentInstructions.fromJson` & `_asMap` ([lib/models/finance.dart](../../../lib/models/finance.dart#L18-L90)) | `_asMap(json['receiver_snapshot'])` (`L18-L19`) gọi `Map<String, dynamic>.from(value)`, **sao chép toàn bộ key-value** vào `PaymentInstructions.receiverSnapshot` (`L45`). |
| **Không render UI** | Getters `bankCode`, `accountNumber`, `accountName` ([lib/models/finance.dart](../../../lib/models/finance.dart#L69-L71)) & `SessionFinanceScreen` ([lib/screens/session_finance_screen.dart](../../../lib/screens/session_finance_screen.dart)) | Ba getter chỉ đọc `receiverSnapshot?['bank_code']`, `'account_number'`, `'account_name'`. Các widget `_qrCard` / `_copyRow` chỉ hiển thị 3 trường ngân hàng này + `reference` + `outstandingVnd`. Hai key tổng hợp và hai chuỗi UUID canary **không bao giờ được render**, copy clipboard hoặc đưa vào QR. |
| **Provider & Clear** | `FinanceProvider` ([lib/providers/finance_provider.dart](../../../lib/providers/finance_provider.dart#L57-L154)) | `fetchPaymentInstructions` (`L124-L154`) gán `_instructions = instructions` (`L154`). Khi logout/đổi user, `_onAuthChanged` (`L57-L63`) gọi `clearAll()` (`L79-L89`) -> `_resetInstructions()` (`L112-L119`) đặt `_instructions = null` và tăng `_instructionsSerial`. |

### 2.2. Nạp qua UI thật không tạo giao dịch thanh toán
1. `Owner` mở màn hình tài chính của session (`SessionFinanceScreen`). Trong chế độ quản lý (`widget.session.canViewFinance == true`), `_load()` ([lib/screens/session_finance_screen.dart](../../../lib/screens/session_finance_screen.dart#L60-L67)) **chỉ** gọi `fetchSessionFinance(widget.session.id)` — lúc này `FinanceProvider._instructions` vẫn là `null`.
2. Trên hàng của một người chơi `confirmed` còn nợ (`outstandingVnd > 0`), `Owner` bấm nút `Thu tiền mặt` (`Key('bh06c-cash-${c.playerId}')`, `L679-L688`).
3. `_recordCash(playerId)` (`L299-L325`) await `provider.fetchPaymentInstructions(widget.session.id, playerId: playerId)` (`L304-L307`), kiểm tra `instructions.outstandingVnd <= 0` (`L317`), rồi mở dialog `_askAmount('Thu tiền mặt', initial: instructions.outstandingVnd)` (`L321-L324`).
4. Ngay sau khi dialog xuất hiện, runner bấm nút `Huỷ` (`Navigator.pop(ctx)`, `L144-L147`). `_askAmount` trả `null`, hàm `_recordCash` return sớm tại `L325` **trước mọi lời gọi `recordPayment`**.
5. Kết quả: `FinanceProvider._instructions` **đang giữ** object `PaymentInstructions` chứa hai chuỗi canary từ `receiverSnapshot`, trong khi DB **không có bất kỳ mutation** nào ở `payments`, `club_transactions`, hay audit log.

### 2.3. Kiểm tra trùng lặp với DTO/API khác (`SessionFinance`, `Session`, Public RPCs)
Các trường định danh có sẵn trên `PaymentInstructions` (`sessionId`, `playerId`, `activeRevisionId`) **không dùng làm sentinel riêng cho `PaymentInstructions` được**, vì chúng trùng với `Session` / `SessionPlayer` / `FinanceRevision` trong `get_session_finance`; còn `reference` và `bank_code`/`account_number`/`account_name` bị **render trên UI**.

Đối chiếu các DTO/RPC khác cho thấy:

| DTO / RPC | Nguồn migration đã kiểm tra | Có trả `receiver_snapshot` không? | Ghi chú |
| --- | --- | --- | --- |
| `SessionFinance` (`get_session_finance`) | `20261020170000_bh06_finance_session_version.sql` | **Không** | Chỉ trả phí, chi, charges, payments, active revision. |
| `SessionSummary` (`get_session_summary`) | `20261020180000_bh07_reads.sql` | **Không** | Chỉ trả tổng hợp buổi chơi. |
| `Session` (`get_session_public_detail`, `list_my_sessions`, `list_public_sessions`, `list_my_session_history`) | `20261015163000_bh04_sessions.sql`, `20261020180000_bh07_reads.sql` | **Không** | Không chứa `receiver_snapshot`. |
| `get_session_payment_instructions(UUID)` (legacy RPC) | `20261016140000_bh06a_review_round1.sql` | **Có** | Không thấy gọi trong `FinanceRepository`, `SessionRepository`, `ClubRepository`; cần grep toàn `lib/` trước khi code để loại trừ call site ẩn. |
| Direct table REST (`GET /rest/v1/sessions`) | Chưa đọc hết RLS gốc bảng `sessions` (trước BH-04) | **Chưa xác minh RLS** | Các repository Flutter đã đọc chỉ gọi `.rpc(...)`, không gọi `.from('sessions').select(...)`; ngoài ra nếu disposable session nằm trong disposable private club chỉ có `ownera`, actor khác cũng bị chặn đọc. |

---

## 3. Giá trị chứng minh & Giới hạn (What Presence/Absence Proves)

- **Nếu 2 sentinel có mặt + reachable ở `owner_active` (cả 2 chu kỳ) VÀ vắng mặt ở `baseline` + toàn bộ snapshot sau logout / `cohost` / `member`:**
  - **Chứng minh được:** Hai giá trị UUID tổng hợp trong `sessions.receiver_snapshot` đã thực sự đi qua RPC `get_payment_instructions` -> JSON decode -> `PaymentInstructions.fromJson` (`_asMap`) -> `FinanceProvider._instructions` trong phiên `Owner`, và **không còn reachable qua cạnh mạnh từ GC root trong V8 heap** sau khi `Owner` logout (`clearAll()` -> `_resetInstructions()`) và chuyển sang `Cohost`/`Member` trong cùng document trên Chrome/Edge profile Web build.
- **KHÔNG chứng minh được (ràng buộc bắt buộc phải khai báo trong `scope` / báo cáo):**
  1. **Không phủ toàn bộ trường của `PaymentInstructions`:** Nếu một bug tương lai hoặc tree-shaking/refactor giữ lại riêng `reference`, `amountDueVnd`, hoặc callback giữ bản sao tách rời của các trường khác mà làm rơi `receiverSnapshot`, canary map vẫn sạch — kết luận phải ghi rõ đây chỉ là **synthetic JSON-map values carried in `PaymentInstructions.receiverSnapshot`**.
  2. **Không quy kết chuỗi render:** `bank_code`, `account_number`, `account_name`, `reference` vẫn là rendered residual risks nằm ngoài phạm vi kiểm soát của oracle không-render.
  3. **Không phủ listener/native/cross-browser:** Listener graph của `AuthProvider`/`FinanceProvider`, Dart VM desktop/mobile, Safari, và Firefox heap chưa được đo.
  4. **Cần kiểm chứng path thực tế khi chạy smoke đầu tiên:** Trong `dart2js` profile build, cần xác nhận khi `owner_active` chụp heap ngay lúc dialog `Thu tiền mặt` đang mở (hoặc vừa bấm `Huỷ`), hai chuỗi UUID value trong `LinkedMap` thực sự tồn tại tách biệt trong V8 heap (không bị tối ưu gộp hoặc GC nhầm nếu dialog giữ/nhả sớm) và retaining path đi qua `FinanceProvider` / `PaymentInstructions` chứ không phải buffer XHR chưa GC. Nếu V8 snapshot chỉ giữ được 1 chuỗi JSON gộp hoặc không giữ được chuỗi key-value ổn định qua `triggerGc()`, phép đo là **không hợp lệ** và phải fail-closed ở bước smoke.

---

## 4. Phương án đề xuất, phương án thay thế & Đánh đổi

### 4.1. Đề xuất khuyến nghị: Disposable Private Club + Disposable Finalized Session của riêng `ownera`
- **Tạo fixture cô lập hoàn toàn theo run UUID:**
  - Sinh các UUID mới ngẫu nhiên mỗi lần chạy: `run_id`, `club_id`, `club_member_owner_id`, `session_id`, `player_id`, `revision_id`, `charge_id`, và `sentinel_1`, `sentinel_2` (UUIDv4 phân biệt, không trùng bất kỳ chuỗi seed nào).
  - Tạo **disposable `private` club** chỉ có 1 thành viên duy nhất là `ownera` (role `owner`), tránh dùng chung `CLUB_A` để loại trừ hoàn toàn nguy cơ `cohosta` hoặc `membera` có quyền/vai trò vô tình đọc lại được disposable session.
  - Tạo **disposable `unlisted` session** thuộc club đó (`lifecycle = 'completed'` hoặc `'in_progress'`, `starts_at = now()` mới nhất để hiện trên đầu danh sách `Buổi tôi quản lý` / `Lịch sử buổi`), kèm `session.description = '[BH07-DISPOSABLE-INSTR:' + run_id + ']'` làm marker sở hữu dọn dẹp (**tuyệt đối không đặt sentinel vào `title`/`description`** để tránh render ra UI).
  - Trong `sessions.receiver_snapshot`, đặt các trường hợp lệ (`bank_code`, `account_number`, `account_name` là chuỗi giả lập hợp lệ không phải sentinel) **cộng thêm** 2 trường JSON tổng hợp: `"canary_instr_a": "<sentinel_1>"`, `"canary_instr_b": "<sentinel_2>"`.
  - Tạo 1 `session_players` đã `confirmed` (guest/offline `user_id = NULL`, không dùng `cohosta`/`membera`), 1 `charge_revisions` (`status = 'active'`, `fee_mode = 'fixed'`; `source_version` khớp `sessions.billing_input_version` để RPC tính `billing_state = 'current'`; không có cột `sessions.billing_state`), 1 `session_charges` cho player đó với `amount_due_vnd = 100000` (chưa có `payments`).
- **Luồng UI 2 chu kỳ (cùng document, không reload trang):**
  1. `baseline`: mở app ở trạng thái chưa đăng nhập -> chụp V8 snapshot (`baseline`, bắt buộc vắng cả 2 sentinel).
  2. Cycle 1 (`owner_active`): đăng nhập `ownera` -> vào session disposable qua UI thật (`Buổi tôi quản lý` trên [lib/screens/home_screen.dart](../../../lib/screens/home_screen.dart#L123-L270), hoặc `Key('bh07c-history-entry')` `Lịch sử buổi` `#L182-L196` nếu chọn `completed`) -> `Tài chính & thu tiền` -> bấm `Thu tiền mặt` (`Key('bh06c-cash-<player_id>')`) -> đợi dialog `Thu tiền mặt` mở -> bấm `Huỷ` (hoặc chụp trước/ngay sau khi bấm `Huỷ` — **khuyến nghị bấm `Huỷ` trước khi chụp `owner_active`** để dialog đóng, không giữ thêm text controller/widget phụ, chỉ còn `FinanceProvider._instructions` giữ model!) -> GC + chụp snapshot `owner_active`.
  3. Gate precondition ngay tại runner/oracle: cả `sentinel_1` và `sentinel_2` **bắt buộc `present == true` và `reachable == true` trong `owner_active`**; thiếu một trong hai -> **FAIL ngay**, không tiếp tục verdict PASS; vẫn bắt buộc chạy cleanup trong finally.
  4. Logout `ownera` -> chụp `post_logout` -> đăng nhập `cohosta` -> mở `UI_SESSION_ID` (`...0099`) `Tổng kết buổi` (chỉ session seed cũ, `cohosta` hoàn toàn không có quyền/link tới disposable session) -> chụp `cohost_active`.
  5. Logout `cohosta` -> Cycle 2 lặp lại: `owner_active_2` (verify lại precondition `present && reachable` lần 2) -> logout -> `membera` (mở `Lịch sử buổi` / `UI_SESSION_ID` bình thường, không thể re-fetch disposable session) -> chụp `member_active_2`.

### 4.2. Các phương án thay thế & Lý do không chọn
| Phương án thay thế | Đánh đổi / Lý do loại |
| --- | --- |
| **A. Dùng lại `CLUB_A` + tạo thêm session mới trong `CLUB_A`** | Rủi ro `cohosta` (nếu có quyền management/finance trên `CLUB_A` hoặc trong một revision seed tương lai) vô tình đọc hoặc thấy session trong lịch sử CLB. Dùng disposable private club chỉ có `ownera` sạch và an toàn hơn hẳn. |
| **B. Cho `Member`/`Guest` tự mở `SessionFinanceScreen` xem QR để nạp `PaymentInstructions`** | Đảo ngược chiều bảo mật cần kiểm tra (`Owner` thao tác thu tiền rồi chuyển sang `Cohost`/`Member` dùng chung máy) và buộc phải gắn user đăng nhập làm payer của session sentinel; đồng thời màn hình payer QR render luôn thông tin hướng dẫn thanh toán, khó tách bạch luồng `Owner` thu tiền mặt. |
| **C. Đọc `bank_code` / `reference` có sẵn làm sentinel thay cho JSON extra keys** | Sai hợp đồng V2b: các trường này được `_qrCard` / `_copyRow` render trực tiếp ra DOM/Canvas -> vi phạm điều kiện `rendered: False` của `heap_oracle.py`. |
| **D. Sửa `run_app_profile_heap.js` thành đa năng cho cả Supabase CLI và 4-container Docker** | Tăng nguy cơ làm lệch/vỡ spec các chế độ `finance`/`payment`/`bank`/`ledger` đã chốt; dễ chạm phạm vi test cũ. Viết **thin companion runner** giữ nguyên toàn vẹn `run_app_profile_heap.js` và 100% bundle lịch sử. |

---

## 5. Ranh giới file, Giao diện kỹ thuật & Tương thích công cụ hiện có

### 5.1. Ranh giới file đề xuất (chỉ thuộc tooling/test/docs mới, không đụng app/backend/bundle cũ)
- **KHÔNG sửa:** `lib/**`, `supabase/**`, `docs/reviews/bh07/*evidence*` (mọi bundle cũ giữ nguyên byte readonly), `scripts/bh07_appheap/run_app_profile_heap.js`.
- **Tạo mới (companion mỏng):**
  1. `scripts/bh07_appheap/disposable_instructions_fixture.py` (hoặc `.js` gọi `docker exec` giống helper private `.build/payment_fixture.py` (không phải artifact bàn giao)):
     - Giao diện: `preflight(docker_bin, db_container)`, `create_fixture(...) -> DisposableInstructionsFixture` (chỉ chứa ID + hash/metadata đã redact nếu cần ghi disk; raw `sentinel_1`, `sentinel_2` chỉ trả trong RAM cho runner), `cleanup_and_verify(...) -> CleanupReceipt`, `assert_clean_after_abort(...)`.
     - Chống rò rỉ sentinel: khi cleanup xóa theo thứ tự FK (`session_charges` -> `charge_revisions` -> `session_players` -> `sessions` -> `club_members` -> `clubs`), kiểm tra lại số row còn lại theo `run_id` / UUID = `0`, và đối chiếu fingerprint DB `after == before` (tương tự `payment_fingerprint.py` / `run_local_rehearsal.py`).
  2. `scripts/bh07_appheap/run_payment_instructions_heap.js`:
     - Tái sử dụng `build_guard.js`, `owned_browser_cleanup.js`, logic `findSentinelLeaks` / `redactValue` / `RAW_SENTINEL_VALUES`, và gọi `heap_oracle.py`.
     - Khắc phục 3 hạn chế của `run_app_profile_heap.js`: không gọi `npx supabase`, streaming CDP chunks thẳng ra file, và gắn `scope/precondition/coverage_profile` rõ ràng.
  3. Unit test mới (ví dụ `scripts/bh07_appheap/test_payment_instructions_heap.py`):
     - Test fixture lifecycle (mock/dry-run hoặc SQL schema check), fail-closed khi `owner_active` thiếu `sentinel_1` hoặc `sentinel_2` hoặc `reachable: false`, fail-closed khi cleanup sót row hoặc `after != before` fingerprint, test redaction từ chối mọi bundle/report còn chứa raw sentinel UUID, và positive + mutant tests cho verifier.

### 5.2. Tương thích với `heap_oracle.py`, `verify_evidence.py`, `audit_retention_attribution.py`
1. **`heap_oracle.py`:**
   - `SENTINEL_SCOPES = ('finance', 'identity', 'control', 'bank')`, `GATED_SCOPES = ('finance',)`, `MIN_GATED_SENTINELS = 2`, `MAX_PARSE_BYTES = 512 << 20`.
   - Khai báo `sentinel_1` và `sentinel_2` với `scope: 'finance'`, `rendered: false`, `distinctive: true` thoả trực tiếp `derive_expectations(scans)` và `MIN_GATED_SENTINELS = 2` mà **không cần sửa `heap_oracle.py`**.
   - **Lưu ý fail-closed cho precondition:** `heap_oracle.py` kiểm tra `present` ở `owner_active`, nhưng để ép cứng điều kiện `reachable == true` ở cả 2 chu kỳ (`owner_active` và `owner_active_2`) trước khi xác nhận `PASS`, runner và/hoặc verifier cần gate thêm `reachable is True` cho cả hai sentinel ở `owner_active` và `owner_active_2`.
2. **`verify_evidence.py` — Bẫy tương thích cần tránh:**
   - Trong `scripts/bh07_appheap/verify_evidence.py#L622` và `#L718`, điều kiện kích hoạt nhánh kiểm tra `bank` là:
     `coverage_profile in ('bank', 'bank_ledger')` **HOẶC** `('disposable_bank_created' in cleanup and coverage_profile not in ('ledger', 'finance', None))`.
   - Nếu runner mới đặt `coverage_profile: 'payment_instructions'` mà lại dùng key cleanup `'disposable_bank_created'`, bản `verify_evidence.py` hiện tại sẽ **nhầm sang `has_bank_coverage`** và báo lỗi thiếu `bank_coverage_contract`!
   - **Giải pháp sạch:**
     - **Không** dùng các key `disposable_bank_*` trong `cleanup`; thay bằng `disposable_instructions_club_created`, `disposable_instructions_session_created`, `disposable_instructions_cleanup_verified` (và không mượn `bank_coverage_contract`).
     - Thêm nhánh độc lập, **thuần cộng thêm (additive-only)** cho `coverage_profile == 'payment_instructions'` trong `verify_evidence.py` (kèm `instructions_coverage_contract` khai báo rõ `scope: 'synthetic_receiver_snapshot_map_values_only'`, `dto: 'PaymentInstructions'`, `provider_field: 'FinanceProvider._instructions'`, `actor_isolation: 'owner_only_disposable_club'`, `payment_mutation_forbidden: true`) **hoặc** tạo companion verifier riêng + giữ nguyên hoàn toàn `verify_evidence.py`. Nếu mở rộng `verify_evidence.py` theo hướng additive-only, mọi test cũ và 100% bundle lịch sử vẫn phải pass không đổi byte.
3. **`audit_retention_attribution.py`:**
   - Giữ nguyên byte và verdict các bundle lịch sử; không sao chép số lượng residual risk cũ thành quan sát mới. Companion bundle phải khai báo rõ `rendered_strings_unattributed: ['bank_code', 'account_number', 'account_name', 'reference']` để không đánh tráo sang "full `PaymentInstructions` model clean".

---

## 6. Đánh giá môi trường 4-Container, CDP Streaming, Dọn dẹp & Provenance

| Hạng mục | Thực tế hiện tại | Ràng buộc & Yêu cầu cho thiết kế mới |
| --- | --- | --- |
| **Stack Supabase local** | Cụm 4 container `bh07-android-db`, `bh07-android-auth`, `bh07-android-rest`, `bh07-android-kong` trên `bh07-android-network`, API `127.0.0.1:54321`, không dùng `npx supabase` CLI. | Runner đọc `SUPABASE_URL=http://127.0.0.1:54321` và `SUPABASE_ANON_KEY` từ env / cấu hình local riêng (không hardcode, không gọi `npx supabase status`); fixture SQL + fingerprint chạy qua `docker exec -i bh07-android-db psql` như `payment_fixture.py`. **Không** claim CLI `supabase db reset`. |
| **Build & Port `8088`** | `build_guard.js` kiểm tra `assertPortFree(8088)` và `assertServedMatches(WEB_URL, BUILD_DIR)`. Nếu port `8088` đang có server khác giữ hoặc build cũ lệch hash sẽ fail. | Bắt buộc build `flutter build web --profile` từ clean `HEAD` (`git_dirty: false`) hoặc fail-closed nếu port `8088` bị chiếm dụng bởi server lạ; tắt server tạm ở `finally`. |
| **CDP Heap Streaming & Disk** | `run_app_profile_heap.js#L693-L731` gom mọi `HeapProfiler.addHeapSnapshotChunk` vào mảng RAM `chunks.push` rồi `writeFileSync(chunks.join(''))`. | Companion runner phải mở `fs.createWriteStream(tempSnapshotPath, { mode: 0o600 })` tại thư mục riêng ngoài repo (`os.tmpdir()`), cộng dồn byte count khi nhận chunk và **abort + đóng stream + xoá file** nếu vượt trần `512 MiB` (`MAX_PARSE_BYTES`), chạy `heap_oracle.py` xong mới xoá ngay `.heapsnapshot` ở `finally`. |
| **Browser & Profile Cleanup** | `owned_browser_cleanup.js` dọn Chrome/Edge PID do runner tạo và `userDataDir`. Trong lịch sử `AGENTS.md`, `Stop-Process`/`Remove-Item` từng vướng chính sách nếu process không sạch. | Runner chỉ spawn Chromium/Edge headless với `--user-data-dir` riêng ngoài repo, chờ process thoát thực sự và xác minh thư mục tạm đã biến mất; nếu dọn thất bại phải ghi `cleanup` fail-closed. |
| **DB Before / After Fingerprint** | Baseline `21 public tables / 94 rows` đã được xác minh trên `bh07-android-db` trong [web_payment_runtime_20261113.md](web_payment_runtime_20261113.md). | Chụp fingerprint schema/bảng/row-counts/roles (và sequence nếu cần kiểm chứng zero-payment) trước preflight và sau cleanup cuối; mismatch -> **FAIL**. |
| **Redaction & Provenance** | Bắt buộc không để raw sentinel UUID xuất hiện trong bất kỳ file bundle (`summary.json`, `run.log`, `provenance.json`, `manifest.json`) hay báo cáo. | Quét `findSentinelLeaks` toàn bộ output directory trước khi đóng gói; chỉ lưu label + `sha256[:12]` của sentinel. Ghi đủ `git_sha`, `git_dirty: false`, `build_manifest_hash`, `served_manifest_hash`, `browser_version`. |
| **Phân vai chạy & review** | Root thực thi runtime local; reviewer độc lập kiểm tra source/test/bundle artifact. | Không dán nhãn runtime của root là "QA độc lập" trừ khi reviewer độc lập tự chạy lại một vòng runtime riêng biệt. |

---

## 7. Kế hoạch triển khai tối thiểu & Control Tests (khi được giao triển khai)

1. **Bước 1 (Kiểm tra tĩnh trước khi viết code):** Grep toàn `lib/` xác nhận không có call site nào gọi `get_session_payment_instructions` hoặc `.from('sessions').select(...)`, và đọc chính sách RLS bảng `sessions` trong migration gốc để xác nhận không mở rò `receiver_snapshot` qua PostgREST.
2. **Bước 2 (Fixture helper + Unit test DB contract):** Tạo `disposable_instructions_fixture.py` (preflight, tạo disposable private club + unlisted finalized session + 1 unpaid confirmed player + `receiver_snapshot` 2 canary UUID, cleanup FK order, before/after fingerprint).
3. **Bước 3 (Companion runner + CDP streaming):** Tạo `run_payment_instructions_heap.js` dùng `build_guard.js`, `owned_browser_cleanup.js`, stream CDP chunk ra file ngoài repo có giới hạn `512 MiB`, luồng UI 2 chu kỳ (`baseline` -> `owner_active` qua `Thu tiền mặt` + `Huỷ` -> `post_logout` -> `cohost_active` trên `...0099` -> `owner_active_2` -> `member_active_2`), tích hợp `heap_oracle.py` + `findSentinelLeaks`.
4. **Bước 4 (Verifier & Negative/Positive Controls):** Thêm kiểm tra cho `coverage_profile == 'payment_instructions'` và suite test unit/control giả lập:
   - *Positive control:* cả 2 canary `present && reachable` ở `owner_active` & `owner_active_2`, vắng ở `baseline`/`post_logout`/`cohost`/`member`, cleanup sạch, DB fingerprint khớp -> `PASS`.
   - *Mutant 1 (Precondition missing):* `owner_active` thiếu 1 sentinel hoặc `reachable == false` -> **FAIL** (`exit 1`).
   - *Mutant 2 (Post-logout leak):* 1 sentinel còn trong `cohost_active` hoặc `member_active_2` -> **FAIL**.
   - *Mutant 3 (Payment mutation / dirty DB):* số dòng `payments` / `club_transactions` thay đổi hoặc cleanup sót session -> **FAIL**.
   - *Mutant 4 (Raw sentinel leak):* 1 raw sentinel UUID lọt vào `summary.json` / `run.log` -> **FAIL**.
5. **Bước 5 (Smoke & Full Runtime tại Root):** Chạy 1 smoke xác nhận trong profile Web build hai giá trị UUID trong `PaymentInstructions.receiverSnapshot` thực sự xuất hiện tách biệt ở `owner_active` sau khi bấm `Huỷ`; nếu đạt, chạy đầy đủ 2 chu kỳ trên `HEAD` sạch, dọn dẹp và bàn giao reviewer độc lập kiểm tra source + bundle artifact.

---

## 8. Các điểm chưa rõ & Blocker còn lại (Blockers / Open Unknowns)

1. **[Cần xác minh bằng smoke] Cấu trúc giữ chuỗi của `Map<String, dynamic>` trong V8 Profile Heap (`dart2js`):** Chưa có bằng chứng thực nghiệm rằng sau khi đóng dialog `Thu tiền mặt`, V8 profile heap vẫn giữ cả 2 chuỗi UUID value trong `PaymentInstructions.receiverSnapshot` dưới dạng 2 string riêng biệt reachable sau `triggerGc()` (tránh trường hợp đã bị GC hoặc gộp cấu trúc khác). Nếu smoke chứng minh không đo được hoặc path không trỏ về `FinanceProvider._instructions`, phải dừng và giữ `NOT RUN` (hoặc cân nhắc giải pháp khác có ủy quyền sửa app).
2. **[Chưa đọc hết] RLS `SELECT` trực tiếp trên bảng `public.sessions`:** Cần đọc phần tạo bảng/RLS `sessions` ở migration trước BH-04 và grep toàn bộ `lib/` đối với `get_session_payment_instructions` trước bước triển khai.
3. **[Môi trường local khi chạy]** Cần xác nhận tại thời điểm chạy: cụm 4 container `bh07-android-*` đang `healthy`, `SUPABASE_ANON_KEY` hợp lệ của stack local sẵn sàng không qua `npx supabase`, port `8088` trống để `build_guard.js` serve bản `build/web` khớp `HEAD`, và trình duyệt Chromium/Edge headless dọn sạch PID/profile không bị chính sách môi trường chặn.
4. **[Phạm vi nghiệm thu]** Kể cả khi runtime `PaymentInstructions` hoàn tất và đạt sau này, các hạng mục rendered strings (`bank_code`, `account_number`, `account_name`, `reference`), `auth_listeners`, và Dart VM native vẫn chưa tự động đạt; toàn V2b / BH-07 / V8 vẫn chưa nghiệm thu nếu chưa đủ bằng chứng và quyết định đúng §4.11.

## 9. Đối chiếu tĩnh bổ sung của Codex

`rg` toàn `lib/` không thấy call site `get_session_payment_instructions` hoặc `.from('sessions')`; có một chỗ decode `receiver_snapshot` ở DTO finance. Policy `sessions_select_auth` trong migration gốc giới hạn raw SELECT cho host/management/finance. Đây là đối chiếu source, chưa chứng minh actor isolation runtime. Hai canary cần precondition/path được đo thực tế trước mọi kết luận attribution. Codex sửa tên bảng, contract billing, đường dẫn và cleanup trong bản khảo sát; runtime vẫn NOT RUN.
