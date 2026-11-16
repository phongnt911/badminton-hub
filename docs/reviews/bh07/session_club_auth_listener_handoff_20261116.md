# BH-07 — Bàn giao mã nguồn AuthProvider -> SessionProvider / ClubProvider Listener Graph (16/11/2026)

- **Vai trò triển khai (implementer):** AGY (`gemini-4-hydrogen-xhigh`)
- **Vai trò review & chạy kiểm chứng/runtime:** Codex
- **Base commit lúc giao việc:** `b87dba6` (tài liệu kế hoạch [2026-11-16-bh07-session-club-listeners.md](../../superpowers/plans/2026-11-16-bh07-session-club-listeners.md) ghi tham chiếu `51013c7`; lệnh giao việc xác nhận base sạch `b87dba6`)
- **Trạng thái thay đổi:** Đã hoàn tất **vòng sửa 2/3 (R2)** xử lý phần **SC4 P1** còn lại và các lỗi control **SC5 P2**, **SC6 P2** theo [session_club_auth_listener_review_r2_20261116.md](docs/reviews/bh07/session_club_auth_listener_review_r2_20261116.md) (sau vòng R1 theo [session_club_auth_listener_review_r1_20261116.md](docs/reviews/bh07/session_club_auth_listener_review_r1_20261116.md)); **SC3** đã được reviewer xác nhận độc lập từ R1 và được giữ nguyên; mã nguồn **để uncommitted** chờ Codex review/runtime.
- **Tình trạng chạy kiểm thử tại AGY:**
  - `python -X utf8 -m unittest scripts/bh07_appheap/test_session_club_auth_listener_graph.py -v`: **`PASS`** (chạy sau chỉnh sửa mã cuối cùng: **17/17 tests in 21.250s — `OK`**, gồm `test_real_build_web_main_dart_js_binding_if_present`, `test_wrong_receiver_rejected`, `test_callback_only_rooting_of_providers_passes`, `test_sc1`–`test_sc4`).
  - `node scripts/bh07_appheap/session_club_auth_listener_controls.js`: **`PASS`** (chạy sau chỉnh sửa mã cuối cùng: **exit 0 — `ALL_SESSION_CLUB_AUTH_LISTENER_CONTROLS_PASS`**).
  - Các bộ Finance & Instructions regressions, lệnh `bind` đơn lẻ, và **toàn bộ runtime trình duyệt / Supabase DB** là **`NOT RUN` tại AGY** (quy tắc cho phép theo phiên chỉ cấp cho 2 lệnh test Session/Club ở trên; không xin mở rộng quyền, không sinh subagent, không commit).

---

## 0. Bản vá vòng sửa 2/3 (SC4 P1, SC5 P2, SC6 P2) & vết R1 (SC1–SC3)

### Vòng 2/3 (R2)
1. **SC4 P1 (Ngữ pháp biểu thức bảo toàn giá trị tối thiểu cho dart2js, bịt lỗ hổng comma/ternary & alias giả):**
   - Trong [session_club_auth_listener_graph.py](../../../scripts/bh07_appheap/session_club_auth_listener_graph.py#L443-L759), loại bỏ hoàn toàn nhận diện theo substring (`rhs_uses_res` / `re.search` trên `args_inner` / `rhs_is_tainted_expr` / `rhs_is_ctor_from_taint`) và thay bằng ngữ pháp đóng tối thiểu khớp đúng mã compiler dart2js thực ([build/web/main.dart.js](build/web/main.dart.js)):
     - `_strip_outer_parens_no_comma` ([L517-L530](../../../scripts/bh07_appheap/session_club_auth_listener_graph.py#L517-L530)): chỉ bóc ngoặc nhóm đơn, từ chối mọi biểu thức có toán tử dấu phẩy `,` ở depth 0 (`($async$result, {})`, `(m, null)`, v.v.).
     - `_verified_type_aliases_with_defs` & `_is_valid_type_cast_receiver` ([L443-L552](../../../scripts/bh07_appheap/session_club_auth_listener_graph.py#L443-L552)): nhận diện local `type_alias` không bị ghi đè gán `= type$.<Type>` trước vị trí dùng (như `$async$temp3 = type$.Map_dynamic_dynamic` trong `build/web/main.dart.js`), cấm ghi đè `type$` hoặc thuộc tính `aname.<prop>`.
     - `_is_value_preserving_rpc_expr` ([L555-L625](../../../scripts/bh07_appheap/session_club_auth_listener_graph.py#L555-L625)) & `_rhs_produces_model_from_vars` ([L689-L758](../../../scripts/bh07_appheap/session_club_auth_listener_graph.py#L689-L758)): chỉ chấp nhận định danh trong `source_vars`, `<type_ref>._as(arg0)` (`len==1`), `<a_alias>.LinkedHashMap_LinkedHashMap$from(arg0, ...)` (`1..3` arg), và bắt buộc kiểm **`args[0]`** (arity `1` cho `$fromJson`, `1..3` cho `$fromResponse`) — từ chối mọi comma/ternary/binary/logic/literal (`($async$result, {})`, `false ? $async$result : {}`, `var bogus = ($async$result, {}); ...fromJson(bogus)`, truyền sai vị trí `arg0` ở `$fromResponse`, v.v.). Giữ chữ ký tương thích ngược cho caller trực tiếp của `_rhs_produces_model_from_vars`.
     - Trong `_derive_async_repo_candidates_ext` ([L1162-L1308](../../../scripts/bh07_appheap/session_club_auth_listener_graph.py#L1162-L1308)) và `_derive_id_field_candidates` ([L1339-L1383](../../../scripts/bh07_appheap/session_club_auth_listener_graph.py#L1339-L1383)): tách `_is_provider_model_expr` và `_is_history_list_expr` (`<var>.<field>`, `type._as`, `List_List$_of`, `<self>._uniqueSessions$1` chỉ cho `fetchSessionHistory`, kiểm đúng `args[0]` của `new SessionHistoryPage`), thêm `_has_trivially_falsy_if_guard` ([L245-L267](../../../scripts/bh07_appheap/session_club_auth_listener_graph.py#L245-L267)), và dùng helper `_invalidate_untracked_writes_in_decl` ([L490-L514](../../../scripts/bh07_appheap/session_club_auth_listener_graph.py#L490-L514)) để loại biến/field bị ghi đè trong ngoặc (`($async$returnValue = null)`, `($async$self._currentSession = null)`); kiểm chặt `rhs_clean == id_param` ở `_derive_id_field_candidates`.
   - Thêm các mutant RED→GREEN chính xác trong [test_session_club_auth_listener_graph.py](../../../scripts/bh07_appheap/test_session_club_auth_listener_graph.py#L926-L1104) (gồm gọi trực tiếp `_rhs_produces_model_from_vars` và binding đầy đủ cho comma/false-ternary/alias/model-alias/arg0/id-ternary/parenthesized-overwrite) và [session_club_auth_listener_controls.js](../../../scripts/bh07_appheap/session_club_auth_listener_controls.js#L620-L639).

2. **SC5 P2 (`test_wrong_receiver_rejected` & positive callback-only rooting):**
   - Giữ nguyên logic BFS rooting trong [finance_auth_listener_graph.py](../../../scripts/bh07_appheap/finance_auth_listener_graph.py) (vì cạnh mạnh `Auth -> ChangeNotifier__listeners -> tear_off -> _receiver -> Provider` thực sự giữ root cho Provider trong V8).
   - Trong [test_session_club_auth_listener_graph.py](../../../scripts/bh07_appheap/test_session_club_auth_listener_graph.py#L441-L453) và [L1119-L1164](../../../scripts/bh07_appheap/test_session_club_auth_listener_graph.py#L1119-L1164), hỗ trợ `weak_receiver` ở `build_sc_snapshot`, thay subtest bất khả thi `session_bound_to_unrooted` bằng các negative trung thực (`session_missing_receiver`, `session_weak_receiver_and_unrooted`, `club_bound_to_weak_receiver`, `session_bound_to_user_object` bên cạnh `session_bound_to_club` & `club_bound_to_object`), đồng thời bổ sung test positive `test_callback_only_rooting_of_providers_passes` cho cả `SessionProvider` và `ClubProvider`.

3. **SC6 P2 (`buildSyntheticSnapshotFile` string interner `__proto__`):**
   - Trong [session_club_auth_listener_controls.js](../../../scripts/bh07_appheap/session_club_auth_listener_controls.js#L376-L385) và [L462](../../../scripts/bh07_appheap/session_club_auth_listener_controls.js#L462), đổi từ object `{ '': 0 }` (vướng setter `Object.prototype.__proto__`) sang `new Map([['', 0]])` và kiểm tra `flatEdges.every((v) => Number.isInteger(v))`; giữ nguyên validator integer-edge ở phía Python.

### Vết vòng 1/3 đã giữ/đóng (SC1–SC3)
1. **SC1:** Tái sử dụng `base_graph._read_bounded_bytes(main_js)`, kiểm `pi_verifier._is_link` và `HEX64` ([L1478-L1501](../../../scripts/bh07_appheap/session_club_auth_listener_graph.py#L1478-L1501)).
2. **SC2:** `_verified_a_aliases_with_defs` và biên `(?<![.\w$])` trước alias `$async$temp1` ([L418-L440](../../../scripts/bh07_appheap/session_club_auth_listener_graph.py#L418-L440)).
3. **SC3 (đã xác nhận độc lập ở review R2):** `_is_valid_heap_object_id` ([L1847-L1869](../../../scripts/bh07_appheap/session_club_auth_listener_graph.py#L1847-L1869)), `_validate_snapshot_cdp_field_pair` ([L2261-L2319](../../../scripts/bh07_appheap/session_club_auth_listener_graph.py#L2261-L2319)), `_check_post_actor_field_contract` ([L2322-L2354](../../../scripts/bh07_appheap/session_club_auth_listener_graph.py#L2322-L2354)), `extract_owner_field_object_ids` & `verify()` ([L3169-L3208](../../../scripts/bh07_appheap/session_club_auth_listener_graph.py#L3169-L3208), [L3461-L3475](../../../scripts/bh07_appheap/session_club_auth_listener_graph.py#L3461-L3475)), và [run_session_club_auth_listener.js](../../../scripts/bh07_appheap/run_session_club_auth_listener.js#L456-L487) ([L762-L765](../../../scripts/bh07_appheap/run_session_club_auth_listener.js#L762-L765)).

---

## 1. Phạm vi sở hữu & tái sử dụng

### File thêm mới
- [session_club_auth_listener_graph.py](../../../scripts/bh07_appheap/session_club_auth_listener_graph.py): Companion artifact-bound source binder (`bind`), V8 snapshot scanner (`scan`), CDP own-properties merger (`apply-cdp`), và strict read-only auditor (`verify`) cho cặp `AuthProvider -> SessionProvider` và `AuthProvider -> ClubProvider`.
- [run_session_club_auth_listener.js](../../../scripts/bh07_appheap/run_session_club_auth_listener.js): Companion runner 2 chu kỳ / 8 epoch cùng document (`1: cohost`, `2: member`), điều hướng UI thực không ghi DB, quan sát CDP own-properties read-only, ép giải phóng `Runtime.releaseObjectGroup`, xuất evidence bundle có kiểm rò rỉ FL4.
- [test_session_club_auth_listener_graph.py](../../../scripts/bh07_appheap/test_session_club_auth_listener_graph.py): Bộ unit + RED→GREEN control + anti-forgery auditor bằng Python `unittest` (có test tùy chọn đọc trực tiếp `build/web/main.dart.js` nếu tồn tại trên đĩa).
- [session_club_auth_listener_controls.js](../../../scripts/bh07_appheap/session_club_auth_listener_controls.js): Bộ control Node cho CDP wire shape, getter/descriptor rejection, `Runtime.releaseObjectGroup`, source binding, mocked 2-cycle/8-epoch (cả mode đủ bank `PASS`, mode thiếu bank fixture `PARTIAL_CLUB_BANK_NOT_RUN`, RED wrong receiver/stale secret/cleanup failure) và gọi chéo `session_club_auth_listener_graph.py verify`.

### Chỉnh sửa tương thích ngược tối thiểu ở tooling Finance/Instructions hiện có
- [finance_auth_listener_graph.py](../../../scripts/bh07_appheap/finance_auth_listener_graph.py):
  - Tham số hóa `provider_class='FinanceProvider', repo_class='FinanceRepository'` trên `_verify_factory_listener_wiring(...)` để tái sử dụng cho `SessionProvider` và `ClubProvider` mà không nhân bản hàm.
  - Tách helper `_inspect_tearoff_core(...)` ngay trên `_inspect_tearoff(...)` (và `_inspect_tearoff(...)` gọi lại helper này với nguyên vẹn hành vi cũ) để tránh nhân bản logic duyệt chuỗi `__proto__` / `BoundClosure` / `$_name`.
- [run_finance_auth_listener.js](../../../scripts/bh07_appheap/run_finance_auth_listener.js): Chỉ bổ sung export các hàm/hằng thuần túy sẵn có (`COUNTER_FIELDS`, `STRUCTURAL_CLASS_ALLOWLIST`, `isValidTimeOrigin`, `buildAllowedClasses`, `cdpSend`, `readTimeOrigin`, `extractSafeDescriptorMeta`, `findUniqueOwnProperty`, `readAuthOwnSnapshot`, `unlinkIfExists`, `runCmd`) trong `module.exports`; **không sửa logic Finance**.
- [run_payment_instructions_heap.js](../../../scripts/bh07_appheap/run_payment_instructions_heap.js): Chỉ bổ sung export các helper/hằng sẵn có (`ROOT`, `PY`, `FIXTURE_CLI`, `BUILD_DIR`, `DEFAULT_WEB_URL`, `UI_SESSION_TITLE`, `MAX_PARSE_BYTES`, `REQUIRED_EPOCHS`, `CdpClient`, `runCmd`, `runVerdict`, `sanitizeDiagnostic`, `collectStrings`, `assertNoSymlinkChain`, `startBrowserLogged`, `shutdownOwnedBrowser`, `loginActor`, `logoutActor`, `returnHomeTabs`, `openCohostSummary`, `openMemberHistory`, `safeEvaluate`, `checked`, `textOf`, `button`, `wait`, `sha12`) trong `module.exports`; **không sửa logic Instructions**.

Không chạm `lib/`, `migrations/`, `supabase/`, các fixture DB hiện có, hoặc các evidence bundle lịch sử.

---

## 2. Đối chiếu Dart wiring và Compiled Executable Bindings (`build/web/main.dart.js`)

Đã đọc trực tiếp nguồn Dart (`lib/main.dart`, `lib/providers/auth_provider.dart`, `lib/providers/session_provider.dart`, `lib/providers/club_provider.dart`, `lib/screens/clubs_screen.dart`, `lib/screens/session_history_screen.dart`) và đối chiếu từng dòng trong profile JS `build/web/main.dart.js` trên đĩa:

1. **`AuthProvider -> SessionProvider`**
   - Constructor `A.SessionProvider` (`build/web/main.dart.js` L17635-17670): `_session_provider$_repository = t0`, `auth = t1`.
   - `MultiProvider` factory `A.main_closure3.prototype.call$1` (`L93028-93047`): tạo `new A.SessionRepository(...)`, `new A.SessionProvider(t5, t1, ...)`, gọi `t1.addListener$1(t4.get$_session_provider$_onAuthChanged())`, trả về `t4`.
   - Đăng ký tearoff (`L222211`): `_instance_0_u(_ = A.SessionProvider.prototype, "get$_session_provider$_onAuthChanged", "_session_provider$_onAuthChanged$0", 0)`.
   - Hàm listener `_session_provider$_onAuthChanged$0()` (`L95509-95535`): dart2js **inline trực tiếp `clearAll()`** vào `_onAuthChanged$0` (không còn method `clearAll$0` riêng); gán `_this._currentSession = _this._currentSessionId = null;` và gọi `_this._resetHistory$0()` (`L95694-95702`, gán `_this._session_provider$_history = null`).
   - Eager baseline thực tế: `HomeScreen.build` (`lib/screens/home_screen.dart`) gọi `context.watch<SessionProvider>()`, nên Cycle 1 `baseline` Guest thường có `SessionProvider = 1` (trạng thái `PASS`); scanner cũng hỗ trợ `0` ở Cycle 1 `baseline` thành `NOT_RUN_LAZY`, và bắt buộc `= 1` từ `owner_active` trở đi.

2. **`AuthProvider -> ClubProvider`**
   - Constructor `A.ClubProvider` (`L17448-17476`): `_club_provider$_repository = t0`, `auth = t1`.
   - `MultiProvider` factory `A.main_closure2.prototype.call$1` (`L93008-93027`): tạo `new A.ClubRepository(...)`, `new A.ClubProvider(t5, t1, ...)`, gọi `t1.addListener$1(t3.get$_club_provider$_onAuthChanged())`, trả về `t3`.
   - Đăng ký tearoff (`L222209`): `_instance_0_u(_ = A.ClubProvider.prototype, "get$_club_provider$_onAuthChanged", "_club_provider$_onAuthChanged$0", 0)`.
   - Hàm listener `_club_provider$_onAuthChanged$0()` (`L93710-93738`): dart2js **inline trực tiếp `clearAll()`** (gồm cả `clearCurrentClub`) vào `_onAuthChanged$0`; gán `_this._currentClub = _this._currentClubId = null;` và `_this._currentBankAccount = null;`.
   - Lazy baseline thực tế: Guest `HomeScreen` chưa tạo `ClubProvider`, nên Cycle 1 `baseline` có `ClubProvider = 0` (`NOT_RUN_LAZY`); từ `owner_active`, `post_logout`, Cycle 1 `post_actor` (`SessionHistoryScreen` gọi `fetchClubs()`), và suốt Cycle 2 bắt buộc `ClubProvider = 1`.

### Bảng Selected Fields & Hợp đồng theo Epoch

| Provider | Dart Field | Compiled JS Property (Profile) | Kiểu/Class JS khi populated | Nơi set / clear trong JS | Cycle 1 `baseline` | `owner_active` (C1 & C2) | `post_logout` (C1 & C2) | `post_actor` C1 (`cohost`) | `post_actor` C2 (`member`) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `AuthProvider` | `_currentUser` | `_currentUser` | `User` (`object`) | Auth listener (`L93704` / `L93651`) | `null` | `User` (`is_null=false`) | `null` | `User` (`is_null=false`) | `User` (`is_null=false`) |
| `SessionProvider` | `_currentSessionId` | `_currentSessionId` | `string` (không xuất raw text) | Set `L95926` (`fetchSessionDetail`); clear `L95523` | `null` (hoặc `NOT_RUN_LAZY` nếu SP=0) | `string` (`is_null=false`) | `null` | **Legit refetch:** `string` (`is_null=false`) | `null` (Member chỉ mở History) |
| `SessionProvider` | `_currentSession` | `_currentSession` | `Session0` (`object`, bind qua `Session_Session$fromJson` L17171) | Set `L95948` (`get_session_public_detail` L92241); clear `L95523` | `null` (hoặc `NOT_RUN_LAZY` nếu SP=0) | `Session0` (`is_null=false`) | `null` | **Legit refetch:** `Session0`, `target_heap_object_id != owner_active` | `null` |
| `SessionProvider` | `_history` | `_session_provider$_history` | `SessionHistoryPage` (`object`, L17413) | Set `L95793` (`list_my_session_history` L92308); clear `L95697` (`_resetHistory$0`) | `null` (hoặc `NOT_RUN_LAZY` nếu SP=0) | `SessionHistoryPage` (`is_null=false`) | `null` | **Legit refetch:** `SessionHistoryPage`, `target_heap_object_id != owner_active` | **Legit refetch:** `SessionHistoryPage`, `target_heap_object_id != owner_active` |
| `ClubProvider` | `_currentClubId` | `_currentClubId` | `string` (không xuất raw text) | Set `L93855` (`fetchClubDetails`); clear `L93730` | `NOT_RUN_LAZY` (CP=0) hoặc `null` | `string` (`is_null=false`) | `null` | `null` | `null` |
| `ClubProvider` | `_currentClub` | `_currentClub` | `Club` (`object`, `L16820` qua `Club_Club$fromJson` `L16730`) | Set `L93874` (`get_club_detail` L91235); clear `L93730` | `NOT_RUN_LAZY` (CP=0) hoặc `null` | `Club` (`is_null=false`) | `null` | `null` | `null` |
| `ClubProvider` | `_currentBankAccount` | `_currentBankAccount` | `BankAccount` (`object`, `L16845` qua `BankAccount_BankAccount$fromJson` `L16794`) | Set `L94110` (`get_club_bank_account` L91413); clear `L93732` | `NOT_RUN_LAZY` (CP=0) hoặc `null` | `BankAccount` **hoặc `NOT_RUN` trung thực nếu fixture không có bank row** | `null` | `null` | `null` |

> **Giới hạn suy diễn:** Các field đã chọn chỉ kiểm chứng chính bản thân chúng và sự tồn tại/nhận diện listener đăng ký trên `AuthProvider`. Không suy ra toàn bộ state khác của `SessionProvider` (`_mySessions`, `_publicSessions`, `_currentPlayers`, `_myInvitation`, `_session_provider$_pendingRequests`, `_historyFilter`) hay `ClubProvider` (`_clubs`, `_currentMembers`, `_rosterClubId`, `_rosterMembers`, `_club_provider$_pendingRequests`).

---

## 3. Khả thi của Precondition `ClubProvider._currentBankAccount` & Đề xuất mở rộng Fixture tối thiểu

- Fixture hiện hành `disposable_instructions_fixture.py` tạo một CLB riêng tư dùng 1 lần (`clubs`, `club_members` owner) và một buổi chơi (`sessions`, `session_players`, `charge_revisions`, `session_charges`), **nhưng không chèn dòng nào vào `public.club_bank_accounts`**.
- Do đó, khi `run_session_club_auth_listener.js` cho Owner điều hướng thật vào `ClubsScreen` → card `fixtureMeta.club_name` → tab `Tài khoản quỹ`:
  - `ClubProvider._currentClubId` và `ClubProvider._currentClub` (`Club`) **đều nạp thành công**.
  - `get_club_bank_account` trả `null`, màn hình hiển thị `'Chưa cấu hình tài khoản ngân hàng nhận quỹ'`, và `ClubProvider._currentBankAccount` giữ `null`.
- Để **không giả `PASS`**, companion scanner/verifier tách riêng hai gate:
  - Chế độ mặc định (không `--require-bank-account`): nếu `_currentBankAccount` là `null` ở `owner_active` (và vẫn `null` ở `baseline`/`post_logout`/`post_actor`, không getter/rò rỉ), `club_bank_account_gate` trả **`NOT_RUN`** và `session_club_listener_gate` trả **`PARTIAL_CLUB_BANK_NOT_RUN`** (summary `verdict: "PARTIAL_NOT_RUN"`). Nếu bundle nào giả mạo `club_bank_account_gate: "PASS"` hoặc `verdict: "PASS"` khi `_currentBankAccount` chưa nạp ở `owner_active`, `verify()` **FAIL (exit 1)**.
  - Chế độ nghiêm ngặt (`--require-bank-account`): bắt buộc `BankAccount` phải được nạp ở cả 2 `owner_active` và xóa sạch ở `post_logout`, nếu không trả **`FAIL` (exit 1)**.

### Đề xuất mở rộng fixture cục bộ tối thiểu (cho Codex khi muốn đo cả `BankAccount`)
Nếu Codex muốn đóng `club_bank_account_gate == PASS` trên fixture dùng 1 lần qua `psql` (không cần `service_role_key` như `disposable_bank_fixture.js`):
1. Trong `disposable_instructions_fixture.py` (hoặc một subclass local của Codex dưới cờ opt-in `--include-club-bank`), cấp thêm `bank_id = uuid4()`, `bank_code = 'VCB'`, `bank_account_number = '99990000' + 8 chữ số ngẫu nhiên` (tránh trùng substring UUID) và `bank_account_name = 'BH07 TEST RECEIVER'`.
2. Preflight kiểm tra `club_bank_accounts` chưa có `bank_id`; trong `create()` chèn thêm 1 dòng `INSERT INTO public.club_bank_accounts (id, club_id, bank_code, account_number, account_name, status) VALUES (..., self.club_id, ..., 'active');` trước `COMMIT;`.
3. Trong `cleanup()`, xóa `DELETE FROM public.club_bank_accounts WHERE id = ... AND club_id = ...;` **trước** `DELETE FROM public.clubs`, đồng thời cộng `club_bank_accounts` vào truy vấn `remaining_counts` xác nhận bằng 0 trước khi kiểm tra `baseline_fingerprint_equal`.

---

## 4. Danh sách RED→GREEN Controls & trạng thái kiểm tra tại AGY

### Python (`scripts/bh07_appheap/test_session_club_auth_listener_graph.py` — `17/17 OK`, `21.250s`)
1. `test_executable_binding_succeeds_and_rejects_comment_or_literal_masking` + `test_real_build_web_main_dart_js_binding_if_present`: chứng minh parser chỉ nhận mã thực thi, suy ra đúng `Session0`/`Club`/`BankAccount`/`SessionHistoryPage`, từ chối comment/string literal, thiếu `_instance_0_u`, thiếu `addListener$1` factory wiring, thiếu reset bất kỳ field nào trong `_onAuthChanged$0`, và pass trên `build/web/main.dart.js` thực.
2. `test_wrong_receiver_rejected` + `test_callback_only_rooting_of_providers_passes`: **SC5** kiểm chứng bác bỏ receiver sai loại/thiếu `_receiver`/cạnh `_receiver` yếu/object khác (`session_bound_to_club`, `session_missing_receiver`, `session_weak_receiver_and_unrooted`, `club_bound_to_weak_receiver`, `session_bound_to_user_object`, `club_bound_to_object`) và xác nhận **callback-only rooting** (cạnh mạnh `Auth -> listeners -> tear_off -> _receiver`) giữ root hợp lệ cho `SessionProvider` và `ClubProvider` (`PASS`).
3. `test_wrong_method_and_prototype_spoof_rejected`: sai tên method, spoof `$_name` trên instance slot, hoặc `__proto__` trỏ ngược về provider → `FAIL`.
4. `test_duplicate_provider_and_duplicate_listener_rejected`: 2 rooted `SessionProvider`, 2 rooted `ClubProvider`, hoặc 2 exact tearoff cho 1 target → `FAIL`.
5. `test_zero_provider_after_required_load_vs_lazy_baseline`: Cycle 1 `baseline` `ClubProvider=0` → `NOT_RUN_LAZY` (trong khi `SessionProvider=1` vẫn đạt `PASS`); `0` provider ở `owner_active` / `post_logout` / Cycle 2 `baseline` / `post_actor` → `FAIL`.
6. `test_stale_selected_fields_at_logout_rejected`: bất kỳ field nào trong 6 field của Session/Club chưa về `null` ở `post_logout` → `FAIL`.
7. `test_mismatched_snapshot_cdp_counters_timeorigin_and_getters_rejected`: lệch `heap_object_id`, lệch null giữa snapshot và CDP, counter drift, `depth > 0`, lệch `timeOrigin`, `object_group_released=False`, `has_getter=True`, CDP getter error, forged `atomic_claim=True` → `FAIL`.
8. `test_post_actor_legitimate_refetch_vs_reused_owner_object_vs_member_stale_leak`: Cohost refetch mới `Session0`/`SessionHistoryPage` với `target_heap_object_id != owner_active` → `PASS`; thiếu `previous_owner_field_ids` → `FAIL`; dùng lại đúng `target_heap_object_id` của Owner → `FAIL`; Member `post_actor` còn `_currentSession` non-null → `FAIL`.
9. `test_valid_full_bank_and_partial_bank_not_run_honesty`, `test_red_fake_pass_on_unpopulated_bank_rejected`, `test_red_mutants_forged_slots_binding_cleanup_and_fl4_secrets`, `test_sc3_missing_or_invalid_target_heap_object_id_and_claimed_map_rejected`: kiểm chứng tách biệt `PASS` vs `PARTIAL_CLUB_BANK_NOT_RUN`, từ chối mọi bundle giả `PASS`, anti-forgery **SC3**/slot/SHA/cleanup/secret/claim, và **FL4**.
10. Regression R1/R2 cho **SC1–SC4**: `test_sc1_oversized_main_dart_js_fails_closed_via_base_bounded_reader`, `test_sc2_async_a_alias_positive_and_negative_controls`, `test_sc4_rpc_to_provider_value_flow_rejects_discarded_overwritten_null` (gồm các mutant R2: `_rhs_produces_model_from_vars` trực tiếp & binding cho `($async$result, {})`, `false ? $async$result : {}`, alias `var bogus = ($async$result, {})` / `false ? ...`, model-alias spoof, sai vị trí `arg0` ở `$fromResponse`, `sessionId ? "" : ""`, ghi đè trong ngoặc `($async$returnValue = null)` / `($async$self._currentSession = null)`).

### Node (`scripts/bh07_appheap/session_club_auth_listener_controls.js` — `exit 0`, `ALL_SESSION_CLUB_AUTH_LISTENER_CONTROLS_PASS`)
1. `testObserveAuthAndTargetProviders`: kiểm wire shape CDP `result.result` vs legacy `result.object`, `ownProperties: true, generatePreview: false`, cấm gọi `Runtime.callFunctionOn`, ép `Runtime.releaseObjectGroup` khi đọc lỗi, phát hiện getter, unsafe integer, lệch `timeOrigin`, và FL4 không lộ giá trị chuỗi thô.
2. `testExtractSessionClubBinding`: kiểm CLI `bind` qua Python từ Node (hợp lệ, sai SHA, thiếu đăng ký, thiếu reset bank, **SC2** `$async$temp1 = A` vs overwritten/comment-masked alias, **SC4** R1/R2 discarded/`return null`/overwritten/comma-discard/false-ternary/alias-spoof).
3. `testMockedTwoCycleRuns` (với **SC6** `Map`-based snapshot interner giữ toàn bộ edge là số nguyên): chạy end-to-end 2 chu kỳ / 8 epoch (chế độ đủ bank `PASS` + `verify --require-bank-account` exit 0; chế độ thiếu bank `PARTIAL_NOT_RUN` + `verify` exit 0 và `--require-bank-account` exit 1; RED wrong receiver + stale secret ở Cycle 2 `post_logout` xác nhận FL4 sạch ở bundle FAIL; RED lỗi DB cleanup giữ nguyên `statePath` và vẫn xóa `dumpsDir`; **SC3** RED reused Owner `currentSessionObjId` & RED stripped `target_heap_object_id` ở cả `owner_active` lẫn `post_actor`).

---

## 5. Lệnh kiểm chứng dành cho Codex

### A. Kiểm tra unit & control suite (bắt buộc chạy trước runtime)
```powershell
python -X utf8 -m unittest scripts/bh07_appheap/test_session_club_auth_listener_graph.py -v
node scripts/bh07_appheap/session_club_auth_listener_controls.js
```

### B. Regression toàn bộ suite Finance & Instructions hiện có (kiểm tương thích ngược)
```powershell
python -X utf8 -m unittest scripts/bh07_appheap/test_finance_auth_listener_graph.py -v
node scripts/bh07_appheap/finance_auth_listener_controls.js
python -X utf8 -m unittest scripts/bh07_appheap/test_payment_instructions_heap.py -v
```

### C. Kiểm tra nhanh source binding trên `build/web` (nếu đang có artifact profile)
```powershell
python -X utf8 scripts/bh07_appheap/session_club_auth_listener_graph.py bind --build-dir build/web
```

### D. Lệnh chạy runtime sạch local (khi Codex chạy thực tế với Supabase/DB sạch và private config)
Lưu ý: dùng đúng `BH07_INSTRUCTIONS_CONFIG` (container `bh07-android-db`, loopback `:54321`, không sửa DB sản phẩm):
```powershell
node scripts/bh07_appheap/run_session_club_auth_listener.js --config <path-to-private-config.json> --out docs/reviews/bh07/session_club_auth_listener_evidence/run
python -X utf8 scripts/bh07_appheap/session_club_auth_listener_graph.py verify docs/reviews/bh07/session_club_auth_listener_evidence/run --build-dir build/web
```
*(Nếu chạy bằng `disposable_instructions_fixture.py` chưa mở rộng `club_bank_accounts`, kỳ vọng `session_listener_gate: PASS`, `club_core_listener_gate: PASS`, `club_bank_account_gate: NOT_RUN`, `session_club_listener_gate: PARTIAL_CLUB_BANK_NOT_RUN`. Nếu đã bổ sung dòng bank fixture dùng 1 lần, thêm `--require-bank-account` vào cả runner và `verify`.)*

---

## 6. Giới hạn kết luận (Claim Limits)

- Runtime trình duyệt và Supabase DB hiện là **`NOT RUN`** cho tới khi Codex thực thi thực tế trên source sạch với receipt DB before/after/cleanup.
- Khi có runtime PASS, kết luận vẫn chỉ giới hạn ở đồ thị hữu hạn `AuthProvider -> SessionProvider` (3 field đã chọn) và `AuthProvider -> ClubProvider` (3 field đã chọn, với `currentBankAccount` tách gate `NOT_RUN` nếu thiếu bank row) trên Flutter Web profile V8/CDP non-atomic.
- Toàn bộ `auth_listeners`, các provider/model còn lại, V2/V2b toàn cục, native mobile/desktop, Firefox/Safari và toàn bộ BH-07/V8 vẫn **chưa nghiệm thu**. Không merge/push/deploy/pilot/BH-08.
