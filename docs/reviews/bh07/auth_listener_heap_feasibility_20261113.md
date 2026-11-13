# BH-07 V2b Feasibility Study: `auth_listeners` Object-Graph Check on Flutter Web Profile V8 Heaps

- **Date:** 2026-11-13
- **Baseline commit:** `1691154` (post synthetic `PaymentInstructions` R2 local check; `auth_listeners` remains `NOT RUN`)
- **Mode:** Read-only code, compiled-artifact, and tooling feasibility analysis
- **Scope / Claim boundary:** Design and feasibility assessment only. **No runtime tests executed**, **no runtime `PASS` claimed**, **no owner risk acceptance**, and **BH-07 / V2b / V8 overall acceptance remains open**.

---

## 1. Executive Conclusion

**Feasible without app or schema changes: YES (for rooted `AuthProvider` listener-slot and target-provider state verification), subject to layout/scalar calibration and a controlled Owner→logout measurement; Guest-only calibration is not acceptance.**

Why this differs fundamentally from all prior BH-07 V2b gates:
1. Prior gates (`expense_id`, `payment_id`, `bank_account_id`, `ledger_transaction_id`, `PaymentInstructions` synthetic map values) used [`heap_oracle.py`](../../../scripts/bh07_appheap/heap_oracle.py) to search V8 `STRING_NODE_TYPES` for injected canary substrings and reconstruct a single shortest strong-edge BFS parent chain from GC root node `0`.
2. Preexisting canary string absence does **not** prove `auth_listeners` clean:
   - String-absent snapshots tell us nothing about listener array structure, `ChangeNotifier__count` vs null holes, duplicate/reentrant registrations, or non-canary model objects retained in `ClubProvider`, `SessionProvider`, `FinanceProvider`, or closure captures.
   - Conversely, **expecting `AuthProvider` listener absence on logout would be a bug**. In [`lib/main.dart`](../../../lib/main.dart#L33-L49), `MultiProvider` mounts `AuthProvider`, `ClubProvider`, `SessionProvider`, and `FinanceProvider` at the app root for the lifetime of the SPA. All three dependent providers intentionally stay registered via `auth?.addListener(_onAuthChanged)` after `logout()` so a future login triggers `_onAuthChanged()` -> `clearAll()`. Do **not** confuse `dispose()` / `removeListener()` with `clearAll()`.

**Smallest recommended architecture:** Reuse the existing single-profile Chrome CDP snapshot streaming, `build/web/main.dart.js` SHA binding, and fail-closed cleanup lifecycle from [`run_payment_instructions_heap.js`](../../../scripts/bh07_appheap/run_payment_instructions_heap.js), paired with a **separate, dependency-free offline V8 graph scanner** (proposed: `scripts/bh07_appheap/auth_listener_graph_scanner.py`) invoked via one constrained optional hook on each streamed `.heapsnapshot` before temporary-file deletion. Do **not** rewrite `heap_oracle.py` or old runners, add third-party packages, or build a generic heap query framework.

---

## 2. Source & Compiled-Artifact Grounding

### 2.1 Provider Wiring and Lifecycle in Dart Source

- [`lib/main.dart`](../../../lib/main.dart#L33-L49): `MultiProvider` creates:
  - `ChangeNotifierProvider(create: (_) => AuthProvider())`
  - `ChangeNotifierProvider(create: (context) => ClubProvider(auth: context.read<AuthProvider>()))`
  - `ChangeNotifierProvider(create: (context) => SessionProvider(auth: context.read<AuthProvider>()))`
  - `ChangeNotifierProvider(create: (context) => FinanceProvider(auth: context.read<AuthProvider>()))`
- [`lib/main.dart`](../../../lib/main.dart#L94-L127): `MainNavigationScreen` renders `body: _screens[_currentIndex]` (not an `IndexedStack`). Combined with `ChangeNotifierProvider`'s default `lazy: true`, `ClubProvider` and `FinanceProvider` are **not instantiated at startup** until a screen reads them (e.g., Clubs / Club Fund / Session Finance).
- [`lib/providers/auth_provider.dart`](../../../lib/providers/auth_provider.dart#L9-L37): `AuthProvider extends ChangeNotifier` listens to `_repository.authStateChanges` via `_listenToAuthChanges()`.
  - [`logout()`](../../../lib/providers/auth_provider.dart#L147-L161) signs out and sets `_currentUser = null` inside `try`, then calls `notifyListeners()`.
  - [`dispose()`](../../../lib/providers/auth_provider.dart#L164-L167) cancels `_authSubscription` and calls `super.dispose()`. During normal app logout, `AuthProvider` is **not** disposed.
- Dependent providers all follow the same pattern:
  - [`ClubProvider`](../../../lib/providers/club_provider.dart#L20-L32): constructor records `_authUserId = auth?.currentUser?.id` and calls `auth?.addListener(_onAuthChanged)`. `dispose()` ([L61-L65](../../../lib/providers/club_provider.dart#L61-L65)) removes `_onAuthChanged` and sets `_disposed = true`. `_onAuthChanged()` calls `clearAll()` ([L603-L614](../../../lib/providers/club_provider.dart#L603-L614)) when `auth?.currentUser?.id != _authUserId`.
  - [`SessionProvider`](../../../lib/providers/session_provider.dart#L86-L158): constructor calls `auth?.addListener(_onAuthChanged)`; `dispose()` ([L127-L132](../../../lib/providers/session_provider.dart#L127-L132)) removes it; `_onAuthChanged()` calls `clearAll()` ([L135-L158](../../../lib/providers/session_provider.dart#L135-L158)).
  - [`FinanceProvider`](../../../lib/providers/finance_provider.dart#L30-L89): constructor calls `auth?.addListener(_onAuthChanged)`; `dispose()` ([L71-L76](../../../lib/providers/finance_provider.dart#L71-L76)) removes it; `_onAuthChanged()` calls `clearAll()` ([L79-L89](../../../lib/providers/finance_provider.dart#L79-L89)).

### 2.2 Compiled Profile Artifact Layout (`build/web/main.dart.js`)

Observed directly in `build/web/main.dart.js` (Flutter Web profile build):

1. **Lazy `MultiProvider` factories** (`main0` `L16666`, implementations `L92994-93062`):
   - `A.main_closure1` constructs `A.AuthProvider` (`L17435`).
   - `A.main_closure2` reads `type$.AuthProvider`, constructs `A.ClubProvider` (`L17451`), and calls `t1.addListener$1(t3.get$_club_provider$_onAuthChanged())`.
   - `A.main_closure3` reads `type$.AuthProvider`, constructs `A.SessionProvider` (`L17635`), and calls `t1.addListener$1(t4.get$_session_provider$_onAuthChanged())`.
   - `A.main_closure4` reads `type$.AuthProvider`, constructs `A.FinanceProvider` (`L17479`), and calls `t1.addListener$1(t2.get$_onAuthChanged())`.
   - `_CreateInheritedProviderState.get$value` (`L216561-216610`) calls `create.call$1` lazily on first lookup and calls `ListenableProvider__startListening` (`L223016`), registering `e.get$markNeedsNotifyDependents()` on `AuthProvider` (removed in `dispose$0` via `ListenableProvider__startListening_closure`, `L216402-216408`).
2. **Dart2js tearoff representation (`Closure_fromTearOff`, `L8334-8389`; `BoundClosure`, `L8996-8999`; `installTearOffs`, `L222206-222212`, `L223017`)**:
   - Calling `get$_club_provider$_onAuthChanged()`, `get$_session_provider$_onAuthChanged()`, `get$_onAuthChanged()`, or `get$markNeedsNotifyDependents()` returns `new cache(this, null)` (`instanceTearOffGetter`, `L147-158`).
   - In `Closure_fromTearOff`, each tearoff constructor is named `tear_off(a, b)` (`L8352`) and allocates an object whose prototype is `Object.create(new A.BoundClosure(null, null).constructor.prototype)` (`L8348`).
   - Each `tear_off` instance carries `_receiver` (bound `this`) and `_interceptor` (`null` for non-intercepted `_instance_0u` tearoffs).
   - The generated tearoff prototype (not the provider prototype) carries `$_name` and `$_target` (`L8357-8358`):
     - Provider getter on `A.ClubProvider.prototype` creates a tearoff whose generated prototype has `$_name = "_club_provider$_onAuthChanged$0"` (`L222207`)
     - Provider getter on `A.FinanceProvider.prototype` creates a tearoff whose generated prototype has `$_name = "_onAuthChanged$0"` (`L222209`)
     - Provider getter on `A.SessionProvider.prototype` creates a tearoff whose generated prototype has `$_name = "_session_provider$_onAuthChanged$0"` (`L222211`)
     - Getter on `A._InheritedProviderScopeElement.prototype` creates a tearoff whose generated prototype has `$_name = "markNeedsNotifyDependents$0"` (`L223017`)
3. **`ChangeNotifier` listener storage layout (`ChangeNotifier`, `L20865-20870`; `ChangeNotifier.prototype`, `L109080-109205`)**:
   - Fields on every `ChangeNotifier` subclass (`AuthProvider`, `ClubProvider`, `SessionProvider`, `FinanceProvider`):
     - `ChangeNotifier__count` (active upper bound index `0 .. _count - 1`)
     - `ChangeNotifier__listeners` (`JSArray` of length `0` (`ChangeNotifier__emptyListeners()`), or power-of-2 capacity `1, 2, 4, 8, ...` grown by doubling / shrunk when `_count * 2 <= length`)
     - `ChangeNotifier__notificationCallStackDepth` (nesting depth during `notifyListeners$0`)
     - `ChangeNotifier__reentrantlyRemovedListeners` (count of `null` holes left inside `[0 .. _count - 1]` when `removeListener$1` executes while `_notificationCallStackDepth > 0`; compacted only when depth returns to `0`)
   - `dispose$0()` resets `ChangeNotifier__listeners` to `ChangeNotifier__emptyListeners()` and `ChangeNotifier__count` to `0`.

### 2.3 Why [`heap_oracle.py`](../../../scripts/bh07_appheap/heap_oracle.py) Alone Cannot Run This Check

- [`heap_oracle.py`](../../../scripts/bh07_appheap/heap_oracle.py) (`MAX_PARSE_BYTES = 512 << 20`, `MAX_PATH_FRAMES = 24`, `MAX_PATH_EDGES = 4096`) exposes `_layout`, `_root_reach`, `scan`, and `decide`, **only** inspecting `STRING_NODE_TYPES = ('string', 'concatenated string', 'sliced string')` for exact/substring sentinel matches.
- `_root_reach(doc, layout)` builds a single-parent BFS tree (`parent`, `parent_edge`) from node `0` skipping `weak` edges. It does **not** index nodes by constructor/class name, enumerate all properties of an object node, follow `JSArray` element slots `[0 .. _count - 1]`, resolve `tear_off -> __proto__ -> $_name`, or enforce multi-instance provider state invariants.

---

## 3. Proposed Smallest Design

### 3.1 Architecture & Integration Boundary

1. **Snapshot capture & lifecycle (reused):** Keep the single-profile Chrome CDP streaming loop, origin/same-document guard, `build_guard.js` artifact check, `owned_browser_cleanup.js`, disposable fixture cleanup verification, and outside-repo temp dump streaming (`<= 512 MiB` cap) from [`run_payment_instructions_heap.js`](../../../scripts/bh07_appheap/run_payment_instructions_heap.js).
2. **Offline graph scanner (new, single-purpose):** Add `scripts/bh07_appheap/auth_listener_graph_scanner.py` (stdlib Python `json` + `collections` only). Given `--snapshot <path>`, `--binding <source_binding.json>`, `--epoch <baseline|owner_active|post_logout|post_actor>`, it performs a single bounded pass over V8 snapshot nodes/edges and emits deterministic JSON verdicts with redacted structural metadata only (node ordinals, class names, field names, counts, non-secret booleans/enum tags — never raw string values, user IDs, tokens, or emails).
3. **Constrained optional hook:** Instead of altering `heap_oracle.py` or rewriting the runner, add one optional CLI/hook parameter to a future `auth_listeners` runner (or optional `--graph-scanner` callback invoked right after `streamSnapshotToFile` while the temp `.heapsnapshot` exists).

### 3.2 Artifact-Bound Source/Class Verification (Fail-Closed)

Before scanning any snapshot, bind expectations directly to the served `build/web/main.dart.js` SHA256 using an AST/token-masked source-binding extractor modeled on `extractAndValidateSourceBinding` in [`run_payment_instructions_heap.js`](../../../scripts/bh07_appheap/run_payment_instructions_heap.js):
- Verify the constructor definitions and exact mangled JS property names exist in executable `build/web/main.dart.js` for:
  - `AuthProvider`, `ClubProvider`, `SessionProvider`, `FinanceProvider`, `ChangeNotifier`, `BoundClosure` (`_receiver`, `_interceptor`)
  - `main_closure2`, `main_closure3`, `main_closure4` tearoff registrations (`_club_provider$_onAuthChanged$0`, `_session_provider$_onAuthChanged$0`, `_onAuthChanged$0`)
  - `ListenableProvider__startListening_closure`, `_InheritedProviderScopeElement` (`markNeedsNotifyDependents$0`)
- Any mismatch between the served `main.dart.js` SHA/symbols and the expected layout -> `FAIL` / `UNKNOWN`, never `PASS`.

### 3.3 Bounded Rooted Graph Traversal & Enumeration Rules

1. **Strong-edge root reachability:** Compute reachable nodes from GC root `0` via BFS ignoring edges of type `weak` (and metadata `shortcut`/`internal` filtering gated by calibration), capped cleanly:
   - Proposed hard caps (tunable after calibration): `MAX_PARSE_BYTES = 512 << 20`, `MAX_CLOSURE_NODES = 10000`, `MAX_PROVIDER_DEPTH = 4`, `MAX_EDGES_PER_ARRAY = 4096`.
   - **Fail-closed:** Hitting *any* cap, encountering an ambiguous array/slot layout, finding `0` rooted `AuthProvider` instances, or finding an uninstantiated target provider -> verdict `UNKNOWN` / `NOT_RUN` (or `FAIL` when precondition requires instantiation), **never `PASS`**.
2. **Enumerate ALL rooted instances (no cherry-picking):**
   - Collect **every** rooted node whose V8 class/constructor name is `AuthProvider`. Expected count = `1` (any count != `1` is reported and fails strict structural checks rather than taking `[0]`).
   - Collect **every** rooted node of `ClubProvider`, `SessionProvider`, and `FinanceProvider` across the whole heap (not just via `_listeners`, so orphaned/duplicate instances retained by widget closures or `_InheritedProviderScopeElement` cannot hide).
3. **`ChangeNotifier` listener array inspection (`AuthProvider.ChangeNotifier__listeners`):**
   - Inspect `ChangeNotifier__count`, `ChangeNotifier__notificationCallStackDepth`, `ChangeNotifier__reentrantlyRemovedListeners`, and the `ChangeNotifier__listeners` backing store (`elements` / numeric index edges).
   - Iterate **every** active slot `0 .. ChangeNotifier__count - 1`:
     - If `slot[i]` is `null`: allowed **only** when `ChangeNotifier__notificationCallStackDepth > 0` and the total count of `null` holes in `0 .. count - 1` equals `ChangeNotifier__reentrantlyRemovedListeners`; otherwise **fail closed** (corrupt/ambiguous layout or unexpected null hole).
     - Trailing slots `[count .. backing_length - 1]` are expected `null` / unused capacity.
     - For each non-null slot `L`, identify closure/tearoff class:
       - If V8 class is `tear_off` (or inherits `BoundClosure` prototype): resolve `_receiver` and prototype `$_name`. Classify into sibling provider `_onAuthChanged` tearoffs (`ClubProvider`, `SessionProvider`, `FinanceProvider`), Provider scope tearoff (`_InheritedProviderScopeElement.markNeedsNotifyDependents$0`), or other live UI/framework listeners.
       - If generic closure (`*closure*`), inspect captured `$this` / captured object edges up to `MAX_PROVIDER_DEPTH` to detect any captured model/provider retention.
   - Do **not** infer clean state from `ChangeNotifier__count == 0` or absence of a provider tearoff! Missing one of the 3 sibling provider tearoffs means the provider was either never instantiated (lazy `MultiProvider`) or unexpectedly disposed; both invalidate a logout-clear check (`NOT_RUN` / `FAIL`).

### 3.4 Epoch Semantics, Preconditions, and Anti-Leak-Tagging Rules

| Epoch | Timing Constraint | Required Positive Preconditions | Target Evaluation |
| :--- | :--- | :--- | :--- |
| `baseline` (Guest) | Cold start before login (and for Root's calibration) | Exactly 1 rooted `AuthProvider`, `_currentUser == null`, `ChangeNotifier__notificationCallStackDepth == 0` | Calibrate V8 edge names; expect **lazy** `ClubProvider`/`FinanceProvider` may still be `0` unless Clubs/Finance tabs were opened |
| `owner_active` | After Owner opens Sessions, Clubs, Club Fund, & Session Finance | Exactly 1 rooted `AuthProvider` (`_currentUser != null`), plus **all 3** rooted providers (`ClubProvider`, `SessionProvider`, `FinanceProvider`) registered in `AuthProvider._listeners`, `_disposed == false`, and positive populated state (non-null Owner models/IDs loaded) | **Gate:** if any of the 3 providers is missing/unpopulated here, abort/mark `NOT_RUN` (`UNKNOWN`), **never** proceed to claim logout clean |
| `post_logout` | **Immediately** after `logout()` settles and before any second actor logs in or UI triggers new RPC refetches | Exactly 1 rooted `AuthProvider` (`_currentUser == null`, `_authSubscription != null`), all 3 sibling `_onAuthChanged` tearoffs **still active** (`_disposed == false`, exact count 1 per provider class, no unexpected extra provider instances) | Inspect exact cleared fields + zero retained Owner models/closures on all 3 providers (Section 4) |
| `post_actor` | After second actor logs in & loads their own scope | Actor has distinct `_authUserId` and reloads legitimately | **Do not** tag Actor's legitimately reloaded `Club`/`Session`/`Finance` objects as old Owner leaks; verify `_authUserId` matches Actor, no duplicate stale `AuthProvider`/provider instances from Owner cycle, and (when combined with cross-actor checks) distinct Owner IDs remain absent |

---

## 4. Exact Post-`clearAll()` Field Expectations (Source & `main.dart.js` Grounded)

Legend for `post_logout` inspection (Dart field -> `build/web/main.dart.js` mangled property):

### 4.1 `AuthProvider` (`L17435-17446`, [`auth_provider.dart`](../../../lib/providers/auth_provider.dart#L10-L167))

- **Successful settled logout:** `_currentUser == null`, `_isLoading == false`, `_errorMessage == null`. `_isSubmitting == false` is a controlled idle-workflow precondition, not a field reset performed by logout. `_successMessage` is not reset by logout and must not be required null as a generic invariant.
- **Expected non-null / live structural refs:** `_repository` (`AuthRepository`), `_authSubscription` (non-null `StreamSubscription<AuthState>` bound via `AuthProvider__listenToAuthChanges_closure` with `$this == AuthProvider` so subsequent login still works), `ChangeNotifier__listeners` (`JSArray` with active sibling `_onAuthChanged` tearoffs and mounted UI `InheritedProviderScopeElement` listeners), `ChangeNotifier__count > 0`, `ChangeNotifier__reentrantlyRemovedListeners == 0`, `ChangeNotifier__notificationCallStackDepth == 0`.

### 4.2 `ClubProvider` (`L17451-17476`, [`club_provider.dart`](../../../lib/providers/club_provider.dart#L11-L614))

- **Cleared by `clearAll()` (`L603-614`) -> MUST be null / empty / false:**
  - Models & IDs: `_currentClubId == null`, `_currentClub == null`, `_rosterClubId == null`, `_currentBankAccount == null`
  - Model lists (`length == 0`): `_clubs` (empty JSArray), `_currentMembers` (empty JSArray), `_rosterMembers` (empty JSArray)
  - Pending idempotency map: `_club_provider$_pendingRequests` (`JsLinkedHashMap` with `__js_helper$_length == 0`, `_first == null`, `_last == null`, `_strings == null`, `_nums == null`, `__js_helper$_rest == null`)
  - Flags & errors (all `false` / `null`): `_isLoadingClubs`, `_clubsErrorMessage`, `_isLoadingDetail`, `_detailErrorMessage`, `_isLoadingMembers`, `_membersErrorMessage`, `_isLoadingRoster`, `_rosterErrorMessage`, `_isLoadingBank`, `_bankErrorMessage`, `_club_provider$_isSubmitting`, `_submitErrorMessage`
  - Auth tracking: `_club_provider$_authUserId == null`, `_club_provider$_disposed == false`
- **Expected surviving structural refs / monotonic counters (NOT leaks):**
  - `auth` -> the single rooted `AuthProvider`
  - `_club_provider$_repository` -> `ClubRepository` (`_club_repository$_client` -> `SupabaseClient`)
  - Counters: `_club_provider$_generation > 0`, `_listSerial > 0`, `_rosterSerial > 0`
  - `ChangeNotifier__listeners` / `ChangeNotifier__count` (live UI `Consumer`/`Provider` scope tearoffs if mounted)

### 4.3 `FinanceProvider` (`L17479-17508`, [`finance_provider.dart`](../../../lib/providers/finance_provider.dart#L22-L342))

- **Cleared by `clearAll()` (`L79-89`) -> MUST be null / empty / false:**
  - Instructions: `_instructions == null`, `_instructionsPlayerId == null`, `_instructionsSessionId == null`, `_isLoadingInstructions == false`, `_instructionsErrorMessage == null`
  - Session finance: `_finance == null`, `_financeSessionId == null`, `_isLoadingFinance == false`, `_financeErrorMessage == null`
  - Session summary: `_sessionSummary == null`, `_summarySessionId == null`, `_isLoadingSummary == false`, `_summaryErrorMessage == null`
  - Club ledger: `_ledger == null`, `_ledgerClubId == null`, `_isLoadingLedger == false`, `_isLoadingMoreLedger == false`, `_ledgerHasMore == false`, `_ledgerErrorMessage == null`
  - Pending idempotency map & submit state: `_finance_provider$_pendingRequests` (empty `JsLinkedHashMap`, `__js_helper$_length == 0`), `_finance_provider$_isSubmitting == false`, `_finance_provider$_submitErrorMessage == null`
  - Auth tracking: `_finance_provider$_authUserId == null`, `_finance_provider$_disposed == false`
- **Expected surviving structural refs / monotonic counters (NOT leaks):**
  - `auth` -> the single rooted `AuthProvider`
  - `_finance_provider$_repository` -> `FinanceRepository` (`_finance_repository$_client` -> `SupabaseClient`)
  - Counters: `_finance_provider$_generation > 0`, `_instructionsSerial`, `_financeSerial`, `_summarySerial`, `_ledgerSerial`

### 4.4 `SessionProvider` (`L17635-17670`, [`session_provider.dart`](../../../lib/providers/session_provider.dart#L75-L415))

- **Cleared by `clearAll()` (`L135-158`) -> MUST be null / empty / false:**
  - Private & detail models/IDs: `_currentSessionId == null`, `_currentSession == null`, `_myInvitation == null`, `_session_provider$_history == null`
  - History filter reset: `_historyFilter` is reset to `const SessionHistoryFilter()` (`clubId == null`, `from == null`, `to == null`, via constant `B.SessionHistoryFilter_null_null_null` in `main_closure3`), `_historyHasMore == false`, `_historyRawOffset == 0`
  - Private/detail lists (`length == 0` at the controlled checkpoint): `_mySessions`, `_currentPlayers`. `_publicSessions` is synchronously cleared but may legitimately refill from Guest public RPCs; emptiness is only valid with an explicit no-refetch checkpoint, never a general privacy invariant
  - Pending idempotency map: `_session_provider$_pendingRequests` (empty `JsLinkedHashMap`, `__js_helper$_length == 0`)
  - Flags & errors (all `false` / `null`): `_isLoadingPublic`, `_publicErrorMessage`, `_isLoadingMine`, `_myErrorMessage`, `_isLoadingHistory`, `_isLoadingMoreHistory`, `_historyErrorMessage`, `_session_provider$_isLoadingDetail`, `_session_provider$_detailErrorMessage`, `_isLoadingInvitation`, `_invitationErrorMessage`, `_isLoadingPlayers`, `_playersErrorMessage`, `_session_provider$_isSubmitting`, `_session_provider$_submitErrorMessage`
  - Auth tracking: `_authUserId == null`, `_session_provider$_disposed == false`
- **Expected surviving structural refs / monotonic counters (NOT leaks):**
  - `auth` -> the single rooted `AuthProvider`
  - `_session_provider$_repository` -> `SessionRepository` (`_session_repository$_client` -> `SupabaseClient`)
  - `_session_provider$_filter` (`SessionFilter` — intentionally **not** reset by `clearAll()`; inspect only that public filter fields contain no leaked user/session models)
  - Counters: `_session_provider$_generation > 0`, `_historySerial`, `_publicSerial`, `_mineSerial`, `_detailSerial`, `_invitationSerial`

---

## 5. Finite Field Verification vs. Full Object Graph & Realistic Unknowns

| Proof Level | What It Actually Establishes | What Remains `UNKNOWN` / `NOT RUN` |
| :--- | :--- | :--- |
| **Preexisting sentinel/canary checks** | Absence of 2 injected strings anywhere in strong reachable `STRING_NODE_TYPES` | Does **not** prove `AuthProvider._listeners` count/targets, provider instantiation, or non-canary fields (`Club`, `Session0`, `SessionFinance`, `SessionSummary`, `ClubLedger`) |
| **Proposed `auth_listeners` scanner** | Rooted `AuthProvider` count == 1, live `_listeners` array integrity (all `_onAuthChanged` tearoffs + provider scopes bounded & resolved), zero stale/duplicate providers, and every finite provider field above null/empty immediately after `logout()` | Arbitrary deep retainers outside provider/listener closure subgraphs (e.g., `SupabaseClient` / `GoTrueClient` internal HTTP/storage caches, `WidgetsBinding` focus/overlay/route trees, browser/engine `segmentationCache`, or native Dart VM desktop/mobile heaps) |

**Realistic V8 Snapshot Unknowns requiring calibration before implementation:**
1. **V8 hidden-class / prototype chain edge encoding for `tear_off`:** Whether V8 `.heapsnapshot` exposes `$_name` cleanly via `tear_off -> __proto__ -> $_name` (own/internal property edge) or through a shared descriptor/`Function` constructor edge when multiple `tear_off` classes exist.
2. **Backing-store layout of `JSArray` for `ChangeNotifier__listeners`:** In V8 snapshots, small JS arrays may store slot indices `0..n-1` directly on the array object's own `element` edges or indirectly via a `FixedArray` (`elements` edge). The scanner must check both and return `UNKNOWN` if neither matches cleanly.
3. **In-flight async microtasks / `post_logout` listener retention:** `FinanceProvider` / `ClubProvider` / `SessionProvider` guard late async responses with `_generation` and serials (`Future.timeout` does not cancel HTTP). Immediately after `logout()`, a transient `_FutureListener` may exist until settled, which holds `$this` (the live provider) — valid only if the provider's own fields remain cleared when it resolves.
4. **`SessionProvider._filter` & widget `Consumer` rebuild timing:** In `post_logout`, `notifyListeners()` inside `clearAll()` triggers widget rebuilds on `_InheritedProviderScopeElement`. Capturing too early (mid-`notifyListeners$0`) could observe `_notificationCallStackDepth > 0`; capture must run after frame settle.

---

## 6. Bounded Calibration & Minimal Verification Plan

1. **Root's GUEST-ONLY Read-Only Baseline Calibration:**
   - Capture one Guest-only `.heapsnapshot` on `MainNavigationScreen` without logging in or mutating DB state.
   - Verify concrete V8 snapshot schema details offline against `build/web/main.dart.js`:
     - Node `name` for `AuthProvider`, `SessionProvider`, `tear_off`, `_InheritedProviderScopeElement`, `AuthProvider__listenToAuthChanges_closure`
     - Exact edge path from `tear_off` -> `_receiver` and `$_name`
     - Exact edge representation for `ChangeNotifier__listeners` -> `elements` / numeric slot indices
     - Confirm expected absence (or lazy creation) of `ClubProvider` / `FinanceProvider` on Guest initial tab (`HomeScreen`) so preconditions don't assume eager instantiation.
2. **Minimal Python Unit-Test & Fixture Interface (Proposed):**
   - Synthetic minimal V8 `.heapsnapshot` generator (small in-memory JSON nodes/edges helper inside a new unit test file, e.g., `scripts/bh07_appheap/tests/test_auth_listener_graph_scanner.py`) covering:
     1. Clean `post_logout` with all 3 active `_onAuthChanged` tearoffs + cleared fields -> `PASS`.
     2. Duplicate/second `AuthProvider` or duplicate `ClubProvider` tearoff retained -> `FAIL`.
     3. Reentrant removal hole inside `0 .. ChangeNotifier__count - 1`: valid only when `_notificationCallStackDepth > 0` and `_reentrantlyRemovedListeners` matches; invalid otherwise -> `FAIL`.
     4. Uninstantiated `FinanceProvider` (count = 2 instead of 3) in `owner_active` or `post_logout` -> fail-closed `UNKNOWN` / `FAIL`, never `PASS`.
     5. Non-null stale field (`_currentBankAccount`, `_ledger`, `_currentSession`, non-empty `_pendingRequests`) even when global canary strings are absent -> `FAIL`.
     6. Weak-only path vs strong-edge cap hit (`MAX_CLOSURE_NODES`) -> weak-only ignored cleanly; cap hit returns `UNKNOWN`.
     7. Mismatched `source_binding` SHA / missing constructor symbol -> `FAIL`.

## 7. Codex Guest calibration update (not full listener acceptance)

Read-only Guest probes on tracked base1691154 found AuthProvider1 and SessionProvider1 rooted; ClubProvider/FinanceProvider0 due lazy creation. Final calibration resolves Auth listener slot0→generated tearoff prototype `markNeedsNotifyDependents$0` with `_receiver` InheritedProviderScopeElement, slot1→`_session_provider$_onAuthChanged$0` with `_receiver` SessionProvider. Raw snapshots/profile/owned browser were removed. No login, fixture, payment or remote action.

Snapshot node fields are type/name/id/self_size/edge_count/detachedness: numeric values are not present. A separate read-only CDP scalar observation on the exact rooted AuthProvider heap object returned count2, notification depth0, removed-listeners0; object group release succeeded. These are nearby observations, not an atomic full-session proof. Future runtime must define epoch identity/quiescence, snapshot↔scalar correlation, handle release on every failure, and fail-closed behavior for mismatches. Snapshot null/false literals were decoded from fixed structural values; a redacted class_name:null in calibration is not a null field.

The proposed offline scanner alone cannot certify active-count/reentrancy scalars from this V8 format. Use a clearly labeled hybrid snapshot + read-only own-property CDP contract, or leave those invariants UNKNOWN. All three Owner provider-load preconditions and logout verification remain NOT RUN.
