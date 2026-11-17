# BH-07 Phase 1 Handoff: Firefox Headed Input Diagnostic Probe (Correction 1/3) — 17/11/2026

**Trạng thái: `NOT RUN` (chờ Codex review vòng sửa 1/3 và chạy runtime trình duyệt; chưa nghiệm thu).** Tài liệu này cập nhật gói chẩn đoán Phase 1 sau [review R1](firefox_headed_input_review_r1_20261117.md) theo [kế hoạch 17/11/2026](../../superpowers/plans/2026-11-17-bh07-firefox-headed-input.md). Không chỉnh sửa `web_lifecycle_scenario.js`, mã nguồn ứng dụng, backend, schema hay bằng chứng cũ. Các trạng thái lịch sử (`Firefox` software-headed write attempt `FAIL` tại click tab `Tài Khoản` / `Login input frame commit timed out` trong [13/11 lifecycle/copy](web_lifecycle_copy_runtime_20261113.md) và [13/11 web extension](web_v2_extension_runtime_20261113.md); `Firefox` default-headed `UNKNOWN`) giữ nguyên không thay đổi. Toàn bộ V2, V2b, BH-07 và V8 vẫn chưa nghiệm thu; không merge, deploy, pilot hay ký chấp nhận rủi ro.

## 1. Thành phần bàn giao Phase 1 (cập nhật sửa R1: FF1 & FF2)

- [firefox_headed_input_probe.js](../../../scripts/bh07_browser/firefox_headed_input_probe.js): biểu thức `async page => { ... }` đơn mục đích cho `playwright-cli run-code --filename=...` (không dấu `;` cuối, không `import`/`require`/`process`, không framework chung).
  - **Guard trước tương tác:** kiểm tra `FOCUS_MODE` (`'baseline' | 'bring_to_front'`), `RENDER_MODE` (`'default' | 'software'`), `BASE_URL` origin chính xác `http://127.0.0.1:8088`, `page.url()` khởi đầu là `about:blank` hoặc origin `http://127.0.0.1:8088`, trình duyệt `firefox` (qua `browserType().name()` và `navigator.userAgent`, từ chối Chromium/Edge/chuỗi `Headless` tường minh — lưu ý `navigator.userAgent` không tự chứng minh được chế độ headed; provenance headed đến từ cấu hình mở trình duyệt `headless: false` của runner gốc), và giữ origin loopback sau `goto`.
  - **FF1 — Allowlist read-RPC chính xác theo origin/path (không suy đoán prefix):** đối chiếu trực tiếp mã nguồn hiện hành ([main.dart](../../../lib/main.dart), [home_screen.dart](../../../lib/screens/home_screen.dart), [account_screen.dart](../../../lib/screens/account_screen.dart), [auth_screen.dart](../../../lib/screens/auth_screen.dart), [auth_provider.dart](../../../lib/providers/auth_provider.dart), [session_repository.dart](../../../lib/data/session_repository.dart)): ở trạng thái Guest trên `/#/` → tab `Tài Khoản` → nút `Đăng Nhập / Đăng Ký` → màn hình `AuthScreen` trước khi bấm submit (không mở Discovery hay deep-link `/sessions/:id`), ứng dụng phát sinh **0** read RPC (`ALLOWED_READ_RPC_PATHS = new Set()`, mọi phần tử trong tương lai bắt buộc khớp đồng thời `parsedUrl.origin === 'http://127.0.0.1:54321'` và đúng path allowlist). Bỏ hoàn toàn lọc prefix `get_`/`list_`/`fetch_`; mọi request khác `GET`/`HEAD`/`OPTIONS` (gồm `POST`/`PUT`/`PATCH`/`DELETE`, URL lỗi parse, origin ngoài như `https://external.invalid/...`, hay `/rest/v1/rpc/get_*`/`list_*`/`fetch_*`) đều tăng `auth_or_mutation_request_count` và ép `ok: false`, `status: 'FAIL'` mà không ghi raw URL hay payload.
  - **Bootstrap semantics tách biệt:** tái sử dụng vòng lặp `enableAccessibility()` trên `flt-semantics-placeholder` (`BOOTSTRAP_TIMEOUT_MS = 20000`) trong mục `semantics_bootstrap` tách riêng trước khi gắn DOM observer ứng dụng.
  - **Thao tác vật lý thật, không submit / không mutation:** so sánh `baseline` (không gọi `bringToFront`) với `bring_to_front` (gọi `await page.bringToFront()`). Dùng `locator.click({ timeout: 10000 })` thật (cấm `{ force: true }`, `dispatchEvent`, DOM `.click()`, monkeypatch CSS/focus hay fallback headless) lên tab `Tài Khoản`, nút `Đăng Nhập / Đăng Ký`, và hai ô `Email` / `Mật khẩu` với chuỗi tổng hợp vô hại (`probe-synthetic@example.invalid` / `synthetic-probe-pass`) theo đúng hành vi `enterInput` + double-`requestAnimationFrame` `settleInput` + `Tab` blur của lifecycle. **Tuyệt đối không bấm `Đăng Nhập`, không chứa tài khoản thật, không đọc giá trị storage/input vào telemetry.**
  - **FF2 — Bảo toàn `FAIL` trên mọi kết quả RAF `false`/`unknown` & metadata giới hạn:** `probeRafCommit()` trả `raf_commit` boolean (`res === true`) và `raf_commit_state` (`'committed' | 'timed_out' | 'unknown'`). Mọi kết quả click thất bại, không chuyển màn hình khách/hộp thoại, kiểm tra `raf_commit !== true` (`false` hoặc `'unknown'`) sau click `Tài Khoản` / `Đăng Nhập / Đăng Ký` / màn khách / mở hộp thoại / trước-sau gõ / `Tab` blur, không giữ giá trị gõ, request không phải read-only hoặc có auth storage key đều đánh dấu bước tương ứng và tổng thể là `ok: false`, `status: 'FAIL'` (không nhận `PASS`). Ghi nhận enum/tag/role đã làm sạch, `visibility_state`, `has_focus`, `playwright_viewport`, `window_inner`/`window_outer`, `device_pixel_ratio`, `rect`, `elementFromPoint` (hỗ trợ xuyên tối đa 4 lớp `shadowRoot`), bộ đếm trusted pointer/mouse/click/keydown/focusin/blur có trần `10000`, `raf_commit`/`raf_commit_state`/`raf_elapsed_ms`, thời gian từng bước và ảnh chụp Guest/dữ liệu tổng hợp tại đường dẫn cố định bị ignore dưới `.build/bh07-firefox-headed-input/*.png`.
  - **Dọn dẹp `finally`:** luôn gỡ listener Playwright (`console`, `pageerror`, `request`) và gỡ listener DOM capture + biến trạng thái trên `window` qua `__bh07FfInputProbeCleanup`, ném lỗi `Cleanup failed:` nếu dọn dẹp thất bại khi trang chưa đóng.
- [firefox_headed_input_controls.js](../../../scripts/bh07_browser/firefox_headed_input_controls.js): bộ kiểm soát offline chỉ dùng Node stdlib (`fs`, `assert/strict`).
  - **RED trước khi sửa FF1/FF2:** chạy `node scripts/bh07_browser/firefox_headed_input_controls.js` -> exit `1` (`19` controls, `3` FAIL: kiểm tra tĩnh phát hiện prefix `/rest/v1/rpc/get_`, control `ff1_rejects_ungrounded_prefix_rpcs_and_external_nonread` FAIL trên `get_unreviewed_mutation`, và control `ff2_exact_first_promise_race_false_mutant_and_login_click_variant` FAIL trên mutant `Promise.race` đầu tiên trả `false`).
  - **GREEN sau sửa FF1/FF2:** chạy `node scripts/bh07_browser/firefox_headed_input_controls.js` -> exit `0`, **`19/19 PASS`** (`failed_controls: 0`), gồm đủ static safety, guard rejections, `baseline` vs `bring_to_front`, physical clicks tách bootstrap, failure preservation, bounded/redacted metadata, `viewport: null` + shadow DOM, FF1 (prefix-bypass `get_*`/`list_*`/`fetch_*`, external POST `https://external.invalid/receive`, `PUT`, malformed URL, đọc `GET`/`HEAD`/`OPTIONS`), FF2 (mutant exact `Promise.race` #1 = `false` của reviewer trên `Tài Khoản`, biến thể login-click `Promise.race` #3 = `false`, nhánh `unknown` = `undefined`/`reject`, `account_guest_view`/`login_dialog_open` RAF `false`, và rAF stall toàn cục vs rAF stall tại `email_input`), và dọn observer trong `finally`.

## 2. Điều kiện môi trường & công thức chạy chẩn đoán 4 ca cho Codex (`NOT RUN`)

Lưu ý môi trường thực tế từ [review R1](firefox_headed_input_review_r1_20261117.md):
- **Giữ nguyên local anon key đã hết hạn:** lệnh gộp làm mới anon key local trước đó đã bị chặn bởi policy và không được thử lại qua đường khác; không áp dụng gia hạn key mới. Vì probe này chỉ thực hiện chẩn đoán UI focus/input **không submit**, có thể chạy tách riêng mà **không tuyên bố Guest authorization hoặc read-success acceptance**.
- **Tái sử dụng đúng 39 artifact Web profile hiện có:** dùng lại bộ 39 artifact khớp bản `7614c6a` và byte HTTP đang phục vụ tại `http://127.0.0.1:8088` (không chạy fresh build, không retag thành build mới).
- **Provenance chế độ headed:** `navigator.userAgent` tự nó không đủ khẳng định Firefox đang chạy có cửa sổ; provenance headed dựa trên các cấu hình/cờ `headless: false` tường minh ở cấp runner của Codex (`--headed` và [firefox-software-config.json](web_v2_20261113_evidence/firefox-software-config.json)).

Sau khi Codex review mã nguồn và commit probe/controls sạch (không reset DB hay đổi cấu hình remote):

1. Tạo 4 bản driver tạm trong thư mục gitignored `.build/bh07-firefox-headed-input/` (không sửa file nguồn đã commit):

```powershell
$ErrorActionPreference = 'Stop'
$outDir = '.build/bh07-firefox-headed-input'
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
$src = Get-Content -Raw 'scripts/bh07_browser/firefox_headed_input_probe.js'

$cases = @(
  @{ Name = 'default-baseline';        Focus = 'baseline';       Render = 'default';  UseSoftCfg = $false },
  @{ Name = 'default-bring_to_front';  Focus = 'bring_to_front'; Render = 'default';  UseSoftCfg = $false },
  @{ Name = 'software-baseline';       Focus = 'baseline';       Render = 'software'; UseSoftCfg = $true  },
  @{ Name = 'software-bring_to_front'; Focus = 'bring_to_front'; Render = 'software'; UseSoftCfg = $true  }
)

foreach ($c in $cases) {
  $driver = $src.Replace("const FOCUS_MODE = 'baseline';", "const FOCUS_MODE = '$($c.Focus)';").Replace("const RENDER_MODE = 'default';", "const RENDER_MODE = '$($c.Render)';")
  $driverPath = Join-Path $outDir ("driver-$($c.Name).js")
  Set-Content -Encoding UTF8 -NoNewline -Path $driverPath -Value $driver
}
```

2. Đối chiếu DB fingerprint / `auth.refresh_tokens_id_seq` trước khi chạy nếu DB/stack được mở, rồi thực thi tuần tự từng ca trong named session sạch (`open` với cấu hình `headless: false` tường minh -> `run-code` -> `close`), giữ các ảnh chụp cố định tại `.build/bh07-firefox-headed-input/<render>-<focus>-*.png`:

```powershell
$softCfg = 'docs/reviews/bh07/web_v2_20261113_evidence/firefox-software-config.json'

foreach ($c in $cases) {
  $sessionArg = "-s=bh07-ff-diag-$($c.Name)"
  $driverPath = ".build/bh07-firefox-headed-input/driver-$($c.Name).js"
  $logPath = ".build/bh07-firefox-headed-input/$($c.Name).log"

  playwright-cli.cmd $sessionArg close *> $null
  try {
    if ($c.UseSoftCfg) {
      playwright-cli.cmd $sessionArg open about:blank --browser=firefox --headed --config=$softCfg *> $null
    } else {
      playwright-cli.cmd $sessionArg open about:blank --browser=firefox --headed *> $null
    }
    if ($LASTEXITCODE -ne 0) { throw "Open failed for $($c.Name)" }

    playwright-cli.cmd $sessionArg run-code --filename=$driverPath *> $logPath
    if ($LASTEXITCODE -ne 0) { throw "Probe invocation failed for $($c.Name)" }
  } finally {
    playwright-cli.cmd $sessionArg close *> $null
  }
}
```

3. Kiểm tra hậu điều kiện sau 4 ca:
   - Đối chiếu kết quả JSON trong từng log: `safety_checks.auth_or_mutation_request_count === 0`, `safety_checks.auth_storage_key_count === 0`, `observer_summary.cleaned_up === true`, cùng các trường `focus_mode`, `render_mode`, `visibility_state`, `has_focus`, `element_from_point`, `event_delta`, `raf_commit`, `raf_commit_state`, `steps.*.status` và ảnh chụp `.build/bh07-firefox-headed-input/*.png` (chỉ chứa màn hình Guest / dữ liệu tổng hợp).
   - Xác nhận không phát sinh đăng nhập hay thay đổi DB; giữ nguyên phạm vi **chẩn đoán UI không submit** (không suy sang Guest authorization/read acceptance khi anon key còn hết hạn).
   - Kiểm tra đối chứng âm guard (ví dụ chạy probe trên `--browser=msedge` hoặc URL ngoài loopback phải từ chối ngay với `Guard failed:` trước tương tác).
   - Chỉ khi bằng chứng 4 ca xác lập được nguyên nhân gốc mới giao Phase 2 sửa tối thiểu cho tooling lifecycle.
