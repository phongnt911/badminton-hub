async page => {
  // Configuration constants (Codex substitutes values in an ignored driver copy)
  const SESSION_ID = '__BH07_SESSION_ID__';
  const TITLE = 'BH07 V2 isolated lifecycle';
  const PHASE = 'prepare_offline';
  const FIRST_COMPLETE_PAYLOAD = null;

  const BASE_URL = 'http://127.0.0.1:8088';
  const API_URL = 'http://127.0.0.1:54321/rest/v1/rpc/complete_session';
  const OWNER_EMAIL = 'ownera@example.test';
  const OWNER_PASSWORD = 'bh07-http-pass-123456';
  const FINALIZE_REASON = 'Chốt phí kiểm thử BH-07 V2';
  const OFFLINE_ERROR_MESSAGE = 'Đã xảy ra lỗi. Vui lòng thử lại sau.';
  const OFFLINE_SUCCESS_MESSAGE = 'Đã kết thúc buổi chơi.';
  const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

  // Validate configuration constants before any page interaction
  if (typeof SESSION_ID !== 'string' || SESSION_ID === '__BH07_SESSION_ID__' || !UUID_RE.test(SESSION_ID)) {
    throw new Error('Guard failed: SESSION_ID must be replaced with a valid UUID');
  }
  if (typeof TITLE !== 'string' || !TITLE.trim()) {
    throw new Error('Guard failed: TITLE must be a non-empty string');
  }
  if (PHASE !== 'prepare_offline' && PHASE !== 'retry_online') {
    throw new Error('Guard failed: PHASE must be prepare_offline or retry_online');
  }

  const expectedBase = new URL(BASE_URL);
  if (expectedBase.origin !== 'http://127.0.0.1:8088') {
    throw new Error('Guard failed: BASE_URL origin must be exactly http://127.0.0.1:8088');
  }
  const expectedApi = new URL(API_URL);
  if (expectedApi.origin !== 'http://127.0.0.1:54321' || expectedApi.pathname !== '/rest/v1/rpc/complete_session') {
    throw new Error('Guard failed: API_URL must be exactly http://127.0.0.1:54321/rest/v1/rpc/complete_session');
  }
  const SESSION_URL = `${expectedBase.origin}/#/sessions/${SESSION_ID}`;

  function isPlainObject(value) {
    return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
  }

  function canonicalJson(value) {
    if (Array.isArray(value)) {
      return `[${value.map(canonicalJson).join(',')}]`;
    }
    if (isPlainObject(value)) {
      const keys = Object.keys(value).sort();
      return `{${keys.map(k => `${JSON.stringify(k)}:${canonicalJson(value[k])}`).join(',')}}`;
    }
    return JSON.stringify(value);
  }

  function validateCompletePayloadObject(payload, label) {
    if (!isPlainObject(payload)) {
      throw new Error(`${label}: complete_session payload must be a plain JSON object`);
    }
    const keys = Object.keys(payload).sort();
    const expectedKeys = ['p_expected_version', 'p_request_id', 'p_session_id'];
    if (keys.length !== expectedKeys.length || keys.some((k, idx) => k !== expectedKeys[idx])) {
      throw new Error(`${label}: complete_session payload keys mismatch`);
    }
    if (payload.p_session_id !== SESSION_ID) {
      throw new Error(`${label}: complete_session p_session_id mismatch`);
    }
    if (typeof payload.p_expected_version !== 'number' || !Number.isInteger(payload.p_expected_version) || payload.p_expected_version !== 2) {
      throw new Error(`${label}: complete_session p_expected_version must equal 2`);
    }
    if (typeof payload.p_request_id !== 'string' || !UUID_RE.test(payload.p_request_id)) {
      throw new Error(`${label}: complete_session p_request_id must be a valid UUID`);
    }
    return {
      p_session_id: payload.p_session_id,
      p_expected_version: payload.p_expected_version,
      p_request_id: payload.p_request_id,
    };
  }

  if (PHASE === 'retry_online') {
    validateCompletePayloadObject(FIRST_COMPLETE_PAYLOAD, 'Guard failed (retry_online)');
  }

  // Guard initial page origin before attaching listeners or interacting
  const initialUrl = page.url();
  if (initialUrl === 'about:blank') {
    if (PHASE !== 'prepare_offline') {
      throw new Error('Guard failed: retry_online requires existing session document, not about:blank');
    }
  } else {
    let initialOrigin = '';
    try {
      initialOrigin = new URL(initialUrl).origin;
    } catch (_) {
      throw new Error('Guard failed: invalid initial page URL');
    }
    if (initialOrigin !== expectedBase.origin) {
      throw new Error('Guard failed: initial page origin does not match http://127.0.0.1:8088');
    }
  }

  // Numeric console/pageerror counters only (never store raw messages, URLs, or secrets)
  const consoleSummary = {
    error_count: 0,
    warning_count: 0,
    pageerror_count: 0,
    offline_resource_errors: 0,
    qr_cors_errors: 0,
  };
  const onConsole = msg => {
    const type = msg.type();
    if (type === 'error') {
      consoleSummary.error_count++;
      const text = msg.text() || '';
      if (text.includes('ERR_INTERNET_DISCONNECTED')) {
        consoleSummary.offline_resource_errors++;
      } else if (text.includes('vietqr') || text.includes('CORS')) {
        consoleSummary.qr_cors_errors++;
      }
    } else if (type === 'warning') {
      consoleSummary.warning_count++;
    }
  };
  const onPageError = () => {
    consoleSummary.pageerror_count++;
  };
  page.on('console', onConsole);
  page.on('pageerror', onPageError);

  // Track strict POST requests to exact complete_session endpoint for this session
  let captureCompleteRequests = false;
  const capturedCompleteRequests = [];
  const completeCaptureErrors = [];

  function parseStrictJsonBody(raw) {
    if (typeof raw !== 'string' || raw.length === 0) {
      return { ok: false };
    }
    try {
      const parsed = JSON.parse(raw);
      if (!isPlainObject(parsed)) {
        return { ok: false };
      }
      return { ok: true, body: parsed };
    } catch (_) {
      return { ok: false };
    }
  }

  const onRequest = req => {
    if (!captureCompleteRequests) return;
    if (req.method() !== 'POST') return;
    let parsedUrl;
    try {
      parsedUrl = new URL(req.url());
    } catch (_) {
      return;
    }
    if (parsedUrl.origin !== expectedApi.origin || parsedUrl.pathname !== expectedApi.pathname) {
      return;
    }
    const parsed = parseStrictJsonBody(req.postData());
    if (!parsed.ok) {
      completeCaptureErrors.push('Malformed JSON body in complete_session POST');
      return;
    }
    if (parsed.body.p_session_id !== SESSION_ID) {
      return;
    }
    capturedCompleteRequests.push({ req, body: parsed.body });
  };
  page.on('request', onRequest);

  async function enableAccessibility() {
    const selector = 'flt-semantics-placeholder, [aria-label*="Enable accessibility"], button:has-text("Enable accessibility")';
    const placeholder = page.locator(selector).first();
    try {
      await placeholder.waitFor({ state: 'attached', timeout: 3000 });
      await placeholder.evaluate(el => el.click());
    } catch (_) {
      // Placeholder may already be activated
    }
    await page.waitForTimeout(400);
  }

  async function waitForSnapshot(predicate, errorMsg, timeoutMs = 15000, pollIntervalMs = 400) {
    const start = Date.now();
    while (Date.now() - start < timeoutMs) {
      const snap = await page.locator('body').ariaSnapshot();
      if (await predicate(snap)) {
        return snap;
      }
      await page.waitForTimeout(pollIntervalMs);
    }
    throw new Error(errorMsg);
  }

  async function settleInput() {
    const committed = await page.evaluate(() => Promise.race([
      new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(() => resolve(true)))),
      new Promise(resolve => setTimeout(() => resolve(false), 5000)),
    ]));
    if (!committed) throw new Error('Input frame commit timed out');
  }

  async function enterInput(field, value, label) {
    await field.waitFor({ state: 'visible', timeout: 10000 });
    for (let attempt = 0; attempt < 2; attempt++) {
      await field.click();
      await settleInput();
      await field.press('ControlOrMeta+a');
      await field.press('Backspace');
      await field.pressSequentially(value, { delay: 15 });
      await settleInput();
      if (await field.inputValue() === value) return;
    }
    throw new Error(`Input ${label} did not retain the typed value`);
  }

  async function navigateBackToMain() {
    const accountTab = page.getByRole('tab', { name: 'Tài Khoản' });
    for (let step = 0; step < 6; step++) {
      if (await accountTab.isVisible().catch(() => false)) {
        return;
      }
      const backBtn = page.getByRole('button', { name: 'Back' }).first();
      const hasBack = await backBtn.isVisible().catch(() => false);
      if (!hasBack) {
        await page.waitForTimeout(300);
        if (await accountTab.isVisible().catch(() => false)) {
          return;
        }
        throw new Error('Navigation failed: neither "Tài Khoản" tab nor "Back" button is visible');
      }

      const beforeHeadings = await page.getByRole('heading', { level: 2 }).allTextContents();
      try {
        await backBtn.click({ timeout: 5000 });
      } catch (_) {
        if (await accountTab.isVisible().catch(() => false)) return;
        throw new Error('Navigation Back click failed before reaching the main screen');
      }

      let changed = false;
      for (let i = 0; i < 20; i++) {
        if (await accountTab.isVisible().catch(() => false)) {
          return;
        }
        const currentHeadings = await page.getByRole('heading', { level: 2 }).allTextContents();
        if (currentHeadings.length === 1 && JSON.stringify(currentHeadings) !== JSON.stringify(beforeHeadings)) {
          await page.waitForTimeout(200);
          const settledHeadings = await page.getByRole('heading', { level: 2 }).allTextContents();
          if (JSON.stringify(settledHeadings) === JSON.stringify(currentHeadings)) {
            changed = true;
            break;
          }
        }
        await page.waitForTimeout(200);
      }
      if (!changed) {
        throw new Error(`Navigation Back step ${step + 1} did not produce a state change`);
      }
    }

    if (!await accountTab.isVisible().catch(() => false)) {
      throw new Error('Root navigation failed: "Tài Khoản" tab not reached within 6 steps');
    }
  }

  async function performOwnerLogin() {
    await navigateBackToMain();
    const accountTab = page.getByRole('tab', { name: 'Tài Khoản' });
    await accountTab.waitFor({ state: 'visible', timeout: 10000 });
    await accountTab.click();

    await waitForSnapshot(
      snap => snap.includes('Bạn đang xem dưới dạng khách') && snap.includes('Đăng Nhập / Đăng Ký'),
      'Expected fresh guest state on Account tab before Owner login'
    );

    const loginCta = page.getByRole('button', { name: 'Đăng Nhập / Đăng Ký' });
    await loginCta.waitFor({ state: 'visible', timeout: 10000 });
    await loginCta.click();

    const emailField = page.getByRole('textbox', { name: 'Email' });
    const passField = page.getByRole('textbox', { name: 'Mật khẩu' });
    await enterInput(emailField, OWNER_EMAIL, 'email');
    await enterInput(passField, OWNER_PASSWORD, 'password');
    await passField.press('Tab');
    await settleInput();
    if (await emailField.inputValue() !== OWNER_EMAIL || await passField.inputValue() !== OWNER_PASSWORD) {
      throw new Error('Login form did not retain both inputs before submission');
    }

    const submitBtn = page.getByRole('button', { name: 'Đăng Nhập', exact: true });
    await submitBtn.waitFor({ state: 'visible', timeout: 10000 });
    await submitBtn.click();

    await waitForSnapshot(
      snap => snap.includes(OWNER_EMAIL) && snap.includes('Đã xác thực'),
      'Owner login failed: authenticated state not found'
    );
  }

  const PLAYER_ROW_DEFS = {
    'Member A': {
      baseNameRe: /^M Member A Đã xác nhận · /,
      prefix: 'M Member A Đã xác nhận · ',
    },
    'Guest A': {
      baseNameRe: /^G Guest A Đã xác nhận · /,
      prefix: 'G Guest A Đã xác nhận · ',
    },
  };

  async function waitForCondition(checkFn, errorMsg, timeoutMs = 15000, pollIntervalMs = 400) {
    const start = Date.now();
    let lastErr = null;
    while (Date.now() - start < timeoutMs) {
      try {
        await checkFn();
        return;
      } catch (err) {
        lastErr = err;
      }
      await page.waitForTimeout(pollIntervalMs);
    }
    const detail = lastErr && lastErr.message ? `: ${lastErr.message.split('\n')[0]}` : '';
    throw new Error(`${errorMsg}${detail}`);
  }

  async function assertDetailContext() {
    const financeHeading = page.getByText('Tài chính buổi', { exact: true });
    if (await financeHeading.count() > 0) {
      throw new Error('Player row helpers restricted to session detail context (finance screen active)');
    }
    const detailHeading = page.getByText('Chi tiết buổi chơi', { exact: true });
    if (await detailHeading.count() !== 1 || !await detailHeading.isVisible().catch(() => false)) {
      throw new Error('Session detail screen "Chi tiết buổi chơi" not uniquely visible');
    }
    const registrationGroup = page.getByRole('group', { name: 'Danh sách đăng ký', exact: true });
    if (await registrationGroup.count() !== 1) {
      throw new Error('Players section group "Danh sách đăng ký" not uniquely resolved');
    }
  }

  async function resolveAndAssertPlayerRow(playerName, expectedAttendanceSuffix, expectPresentBtn) {
    const def = PLAYER_ROW_DEFS[playerName];
    if (!def) {
      throw new Error(`Unsupported player row target: ${playerName}`);
    }
    await assertDetailContext();

    const baseRows = page.getByRole('group', { name: def.baseNameRe });
    const baseCount = await baseRows.count();
    if (baseCount !== 1) {
      throw new Error(`Player row group not uniquely resolved for ${playerName} (found ${baseCount})`);
    }

    const expectedGroupName = `${def.prefix}${expectedAttendanceSuffix}`;
    const exactRows = page.getByRole('group', { name: expectedGroupName, exact: true });
    const exactCount = await exactRows.count();
    if (exactCount !== 1) {
      throw new Error(`Player ${playerName} attendance state mismatch (expected "${expectedGroupName}", found ${exactCount})`);
    }
    await exactRows.scrollIntoViewIfNeeded({ timeout: 2000 });
    if (!await exactRows.isVisible()) {
      throw new Error(`Player ${playerName} row group "${expectedGroupName}" is not visible`);
    }

    const presentBtn = exactRows.getByRole('button', { name: 'Có mặt', exact: true });
    const presentCount = await presentBtn.count();
    if (expectPresentBtn) {
      if (presentCount !== 1) {
        throw new Error(`Player ${playerName} expected 1 "Có mặt" button, found ${presentCount}`);
      }
      await presentBtn.scrollIntoViewIfNeeded({ timeout: 2000 });
      if (!await presentBtn.isVisible() || !await presentBtn.isEnabled()) {
        throw new Error(`Player ${playerName} "Có mặt" button is not visible/enabled`);
      }
    } else if (presentCount !== 0) {
      throw new Error(`Player ${playerName} unexpectedly has ${presentCount} "Có mặt" button(s)`);
    }

    return exactRows;
  }

  async function clickRowScopedPresent(playerName) {
    const row = await resolveAndAssertPlayerRow(playerName, 'Chưa điểm danh', true);
    const btn = row.getByRole('button', { name: 'Có mặt', exact: true });
    await btn.scrollIntoViewIfNeeded({ timeout: 2000 });
    if (!await btn.isEnabled()) {
      throw new Error(`Row-scoped "Có mặt" button is disabled for ${playerName}`);
    }
    await btn.click();
  }

  const context = page.context();
  let sessionStarted = false;
  let attendanceCheckedIn = false;
  let chargesFinalized = false;
  let offlineErrorVerified = false;
  let documentTimeOrigin = 0;
  let sanitizedFirstPayload = null;
  let rpcResponseStatus = 0;

  try {
    if (PHASE === 'prepare_offline') {
      // 1. Fresh guest session -> root Account UI login Owner -> goto fixed session URL
      await page.goto(`${expectedBase.origin}/#/`);
      if (new URL(page.url()).origin !== expectedBase.origin) {
        throw new Error('Loopback origin guard failed after navigating to home');
      }
      const rootAccountTab = page.getByRole('tab', { name: 'Tài Khoản' });
      await waitForCondition(
        async () => {
          if (await rootAccountTab.isVisible().catch(() => false)) {
            return;
          }
          await enableAccessibility();
          if (!await rootAccountTab.isVisible().catch(() => false)) {
            throw new Error('Root "Tài Khoản" tab not visible');
          }
        },
        'Guest home bootstrap timed out waiting for visible "Tài Khoản" tab',
        20000
      );
      await performOwnerLogin();

      await page.goto(SESSION_URL);
      if (new URL(page.url()).origin !== expectedBase.origin) {
        throw new Error('Loopback origin guard failed after navigating to session URL');
      }
      await enableAccessibility();

      documentTimeOrigin = await page.evaluate(() => performance.timeOrigin);

      await waitForSnapshot(
        s => s.includes('Chi tiết buổi chơi') &&
          s.includes(TITLE) &&
          s.includes('Đã công bố') &&
          s.includes('Danh sách đăng ký'),
        'Published session detail screen missing'
      );

      // Verify both players are initially confirmed / not_checked_in without Có mặt button
      await waitForCondition(
        async () => {
          await resolveAndAssertPlayerRow('Member A', 'Chưa điểm danh', false);
          await resolveAndAssertPlayerRow('Guest A', 'Chưa điểm danh', false);
        },
        'Initial published player rows verification failed'
      );

      // 2. Start session -> assert Đang diễn ra
      const startBtn = page.getByRole('button', { name: 'Bắt đầu buổi chơi', exact: true });
      await startBtn.waitFor({ state: 'visible', timeout: 10000 });
      await startBtn.click();

      await waitForSnapshot(
        s => s.includes('Chi tiết buổi chơi') &&
          s.includes(TITLE) &&
          s.includes('Đang diễn ra') &&
          s.includes('Danh sách đăng ký'),
        'Session did not transition to "Đang diễn ra"'
      );
      await waitForCondition(
        async () => {
          await resolveAndAssertPlayerRow('Member A', 'Chưa điểm danh', true);
          await resolveAndAssertPlayerRow('Guest A', 'Chưa điểm danh', true);
        },
        'In-progress player rows or "Có mặt" actions missing before check-in'
      );
      sessionStarted = true;

      // 3. Mark BOTH Member A and Guest A present via row-scoped Có mặt buttons
      await clickRowScopedPresent('Member A');
      await waitForCondition(
        async () => {
          await resolveAndAssertPlayerRow('Member A', 'Có mặt', false);
          await resolveAndAssertPlayerRow('Guest A', 'Chưa điểm danh', true);
        },
        'Member A attendance postcondition or Guest A readiness check failed'
      );

      await clickRowScopedPresent('Guest A');
      await waitForCondition(
        async () => {
          await resolveAndAssertPlayerRow('Member A', 'Có mặt', false);
          await resolveAndAssertPlayerRow('Guest A', 'Có mặt', false);
        },
        'Both Member A and Guest A attendance postconditions failed'
      );
      attendanceCheckedIn = true;

      // 4. Open Tài chính & thu tiền -> verify posted expense 200000 -> Chốt phí
      const financeTile = page.getByRole('button', { name: /Tài chính & thu tiền/ });
      await financeTile.waitFor({ state: 'visible', timeout: 10000 });
      await financeTile.scrollIntoViewIfNeeded();
      await financeTile.click();

      const preFinalizeSnap = await waitForSnapshot(
        s => s.includes('Tài chính buổi') &&
          s.includes('Trạng thái phí') &&
          s.includes('Chưa chốt phí') &&
          s.includes('Chi phí (200,000 VNĐ)'),
        'Finance screen did not load with not_finalized state and posted 200,000 expense'
      );
      if (!/Tổng chi phí:?\s*(?<!\d)200,000(?!\d)\s*VNĐ/.test(preFinalizeSnap)) {
        throw new Error('Finance screen total expense mismatch before finalize (expected 200,000 VNĐ)');
      }
      if (preFinalizeSnap.includes('Đã hoàn tác') || !preFinalizeSnap.includes('Chưa có thanh toán.')) {
        throw new Error('Unexpected reversed expense or existing payments before finalize');
      }

      const finalizeBtn = page.getByRole('button', { name: 'Chốt phí', exact: true });
      await finalizeBtn.waitFor({ state: 'visible', timeout: 10000 });
      await finalizeBtn.click();

      const reasonField = page.getByRole('textbox', { name: 'Lý do *' });
      await enterInput(reasonField, FINALIZE_REASON, 'finalize_reason');
      await reasonField.press('Tab');
      await settleInput();
      if (await reasonField.inputValue() !== FINALIZE_REASON) {
        throw new Error('Finalize reason textbox did not retain value after blur');
      }

      const confirmFinalizeBtn = page.getByRole('button', { name: 'Xác nhận', exact: true });
      await confirmFinalizeBtn.waitFor({ state: 'visible', timeout: 10000 });
      await confirmFinalizeBtn.click();

      // Scroll charges into view to ensure both player charges are materialized in semantics
      const chargesHeader = page.getByRole('group', { name: 'Khoản phải thu theo người', exact: true });
      await chargesHeader.waitFor({ state: 'visible', timeout: 15000 });
      await chargesHeader.scrollIntoViewIfNeeded();

      const finalizedSnap = await waitForSnapshot(
        s => s.includes('Tài chính buổi') &&
          s.includes('Đang hiệu lực') &&
          s.includes('Chốt lại phí') &&
          s.includes('Khoản phải thu theo người') &&
          s.includes('Member A') &&
          s.includes('Guest A'),
        'Finalized billing state "Đang hiệu lực" or player charges missing'
      );

      if (!/Tổng còn phải thu:?\s*(?<!\d)200,000(?!\d)\s*VNĐ/.test(finalizedSnap)) {
        throw new Error('Finalized total outstanding mismatch (expected 200,000 VNĐ)');
      }
      if (!finalizedSnap.includes('Chưa có thanh toán.')) {
        throw new Error('Unexpected payments present after finalize');
      }
      const chargesStart = finalizedSnap.indexOf('Khoản phải thu theo người');
      const paymentsStart = finalizedSnap.indexOf('Thanh toán', chargesStart);
      const chargesSlice = paymentsStart > chargesStart
        ? finalizedSnap.slice(chargesStart, paymentsStart)
        : finalizedSnap.slice(chargesStart);
      const charge100kMatches = chargesSlice.match(/(?<!\d)100,000(?!\d)\s*VNĐ/g) || [];
      if (charge100kMatches.length !== 2) {
        throw new Error(`Expected two 100,000 VNĐ player charges after finalize, found ${charge100kMatches.length}`);
      }

      const completeBtn = page.getByRole('button', { name: 'Kết thúc buổi chơi', exact: true });
      await completeBtn.waitFor({ state: 'visible', timeout: 10000 });
      await completeBtn.scrollIntoViewIfNeeded();
      if (!await completeBtn.isEnabled()) {
        throw new Error('Complete session button is not enabled after finalizing charges');
      }
      chargesFinalized = true;

      // 5. Offline mutation attempt: capture ONLY exact POST complete_session
      captureCompleteRequests = true;
      await context.setOffline(true);

      await completeBtn.click();
      const confirmCompleteBtn = page.getByRole('button', { name: 'Đồng ý', exact: true });
      await confirmCompleteBtn.waitFor({ state: 'visible', timeout: 10000 });
      await confirmCompleteBtn.click();

      const offlineSnap = await waitForSnapshot(
        s => s.includes(OFFLINE_ERROR_MESSAGE),
        'Expected offline error message did not appear on finance screen',
        20000
      );
      if (offlineSnap.includes(OFFLINE_SUCCESS_MESSAGE)) {
        throw new Error('Unexpected completion success message rendered while offline');
      }
      if (!offlineSnap.includes('Tài chính buổi') || !offlineSnap.includes('Đang hiệu lực')) {
        throw new Error('Finance screen state not preserved after offline complete failure');
      }
      await completeBtn.waitFor({ state: 'visible', timeout: 5000 });
      if (!await completeBtn.isEnabled()) {
        throw new Error('Complete session button did not remain enabled after offline failure');
      }
      offlineErrorVerified = true;

      if (completeCaptureErrors.length > 0) {
        throw new Error('Malformed complete_session POST captured during offline attempt');
      }
      if (capturedCompleteRequests.length !== 1) {
        throw new Error(`Expected exactly 1 complete_session POST during offline attempt, got ${capturedCompleteRequests.length}`);
      }
      sanitizedFirstPayload = validateCompletePayloadObject(
        capturedCompleteRequests[0].body,
        'Offline attempt'
      );

      const postOfflineTimeOrigin = await page.evaluate(() => performance.timeOrigin);
      if (postOfflineTimeOrigin !== documentTimeOrigin) {
        throw new Error('Document timeOrigin changed unexpectedly during prepare_offline');
      }
    } else {
      // PHASE === 'retry_online': NO login, NO reload, NO goto; preserve provider intent & document
      documentTimeOrigin = await page.evaluate(() => performance.timeOrigin);
      await enableAccessibility();

      const preRetrySnap = await waitForSnapshot(
        s => s.includes('Tài chính buổi') &&
          s.includes('Đang hiệu lực') &&
          s.includes('Chốt lại phí') &&
          s.includes('Kết thúc buổi chơi'),
        'Finance screen with current billing and complete button not ready for retry_online'
      );
      if (!preRetrySnap.includes('Chưa có thanh toán.')) {
        throw new Error('Unexpected payments present before retry_online');
      }

      const completeBtn = page.getByRole('button', { name: 'Kết thúc buổi chơi', exact: true });
      await completeBtn.waitFor({ state: 'visible', timeout: 10000 });
      await completeBtn.scrollIntoViewIfNeeded();
      if (!await completeBtn.isEnabled()) {
        throw new Error('Complete session button is not enabled at start of retry_online');
      }

      // Capture strict POST complete_session and arm response listener before confirming
      captureCompleteRequests = true;
      await completeBtn.click();

      const confirmCompleteBtn = page.getByRole('button', { name: 'Đồng ý', exact: true });
      await confirmCompleteBtn.waitFor({ state: 'visible', timeout: 10000 });
      if (capturedCompleteRequests.length !== 0) {
        throw new Error('complete_session POST fired before confirming dialog');
      }

      const responsePromise = page.waitForResponse(response => {
        const req = response.request();
        if (req.method() !== 'POST') return false;
        let parsedUrl;
        try {
          parsedUrl = new URL(response.url());
        } catch (_) {
          return false;
        }
        if (parsedUrl.origin !== expectedApi.origin || parsedUrl.pathname !== expectedApi.pathname) {
          return false;
        }
        if (response.status() !== 200) return false;
        const parsed = parseStrictJsonBody(req.postData());
        if (!parsed.ok) return false;
        return parsed.body.p_session_id === SESSION_ID &&
          capturedCompleteRequests.some(item => item.req === req);
      }, { timeout: 20000 });

      const [rpcResponse] = await Promise.all([
        responsePromise,
        confirmCompleteBtn.click(),
      ]);
      rpcResponseStatus = rpcResponse.status();
      if (rpcResponseStatus !== 200) {
        throw new Error(`Expected complete_session HTTP 200 on retry, got ${rpcResponseStatus}`);
      }

      await waitForSnapshot(
        s => s.includes('Chi tiết buổi chơi') &&
          s.includes(TITLE) &&
          s.includes('Đã kết thúc') &&
          s.includes('Tổng kết buổi'),
        'Completed session detail UI or "Tổng kết buổi" entry missing after retry_online'
      );

      if (completeCaptureErrors.length > 0) {
        throw new Error('Malformed complete_session POST captured during retry_online');
      }
      if (capturedCompleteRequests.length !== 1) {
        throw new Error(`Expected exactly 1 complete_session POST during retry_online, got ${capturedCompleteRequests.length}`);
      }

      const sanitizedRetryPayload = validateCompletePayloadObject(
        capturedCompleteRequests[0].body,
        'Retry attempt'
      );
      if (sanitizedRetryPayload.p_request_id !== FIRST_COMPLETE_PAYLOAD.p_request_id) {
        throw new Error('Retry complete_session p_request_id differs from prepare_offline');
      }
      if (canonicalJson(sanitizedRetryPayload) !== canonicalJson(FIRST_COMPLETE_PAYLOAD)) {
        throw new Error('Retry complete_session canonical JSON payload differs from prepare_offline');
      }

      // Open Summary screen and verify server aggregates and attendance counts
      const summaryBtn = page.getByRole('button', { name: /^Tổng kết buổi/ });
      await summaryBtn.waitFor({ state: 'visible', timeout: 10000 });
      await summaryBtn.click();

      const summarySnap = await waitForSnapshot(
        s => s.includes('Tổng kết buổi') &&
          s.includes(TITLE) &&
          s.includes('Đã kết thúc') &&
          s.includes('Tài chính tổng hợp'),
        'Completed summary screen or "Tài chính tổng hợp" missing'
      );

      const hasPresent = /(?:Có mặt|Có mặt:)\s+2(?!\d)/.test(summarySnap);
      const hasAbsent = /(?:Vắng|Vắng:)\s+0(?!\d)/.test(summarySnap);
      const hasConfirmed = /(?:Đã xác nhận|Đã xác nhận:)\s+2(?!\d)/.test(summarySnap);
      if (!hasPresent || !hasAbsent || !hasConfirmed) {
        throw new Error('Completed summary attendance counts mismatch (expected 2/0/2)');
      }

      const hasExpense = /Tổng chi phí:?\s*(?<!\d)200,000(?!\d)\s*VNĐ(?!\d)/.test(summarySnap);
      const hasDue = /Tổng phải thu:?\s*(?<!\d)200,000(?!\d)\s*VNĐ(?!\d)/.test(summarySnap);
      const hasPaid = /Đã thu:?\s*(?<!\d)0(?!\d)\s*VNĐ(?!\d)/.test(summarySnap);
      const hasOutstanding = /Còn phải thu:?\s*(?<!\d)200,000(?!\d)\s*VNĐ(?!\d)/.test(summarySnap);
      if (!hasExpense || !hasDue || !hasPaid || !hasOutstanding) {
        throw new Error('Completed summary finance aggregates mismatch (expected 200000/200000/0/200000)');
      }

      const postRetryTimeOrigin = await page.evaluate(() => performance.timeOrigin);
      if (postRetryTimeOrigin !== documentTimeOrigin) {
        throw new Error('Document continuity violated during retry_online');
      }
    }
  } finally {
    let cleanupErr = null;
    try {
      await context.setOffline(false);
    } catch (_) {
      cleanupErr = new Error('Cleanup failed: unable to restore network online state');
    } finally {
      captureCompleteRequests = false;
      page.off('request', onRequest);
      page.off('console', onConsole);
      page.off('pageerror', onPageError);
    }
    if (cleanupErr) {
      throw cleanupErr;
    }
  }

  if (PHASE === 'prepare_offline') {
    return {
      ok: true,
      phase: PHASE,
      session_id: SESSION_ID,
      session_started: sessionStarted,
      attendance_checked_in: attendanceCheckedIn,
      charges_finalized: chargesFinalized,
      offline_error: offlineErrorVerified,
      complete_attempt_count: capturedCompleteRequests.length,
      FIRST_COMPLETE_PAYLOAD: sanitizedFirstPayload,
      document_time_origin: documentTimeOrigin,
      recorded_console_summary: consoleSummary,
    };
  }

  return {
    ok: true,
    phase: PHASE,
    session_id: SESSION_ID,
    request_id_same: true,
    full_payload_same: true,
    retry_attempt_count: capturedCompleteRequests.length,
    rpc_status: rpcResponseStatus,
    complete_ui_verified: true,
    summary_verified: true,
    document_time_origin: documentTimeOrigin,
    recorded_console_summary: consoleSummary,
  };
}
