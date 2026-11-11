async page => {
  // Guard initial configuration and loopback origin
  const BASE_URL = 'http://127.0.0.1:8088';
  const SESSION_ID = '10000000-0000-4000-8000-000000000099';
  const SESSION_HASH = `/#/sessions/${SESSION_ID}`;
  const SESSION_URL = `${BASE_URL}${SESSION_HASH}`;

  const OWNER_EMAIL = 'ownera@example.test';
  const COHOST_EMAIL = 'cohosta@example.test';
  const MEMBER_EMAIL = 'membera@example.test';
  const PASSWORD = 'bh07-http-pass-123456';

  // Explicit aggregate expectations; root Codex mutates EXPECTED.due to 200001 for fail-closed negative control
  const EXPECTED = {
    expense: 200000,
    due: 200000,
    paid: 100000,
    outstanding: 100000,
    present: 2,
    absent: 0,
    confirmed: 2,
  };

  // Verify loopback URL format
  const loopbackUrl = new URL(BASE_URL);
  if (loopbackUrl.hostname !== '127.0.0.1' && loopbackUrl.hostname !== 'localhost') {
    throw new Error(`Guard failed: non-loopback base URL hostname (${loopbackUrl.hostname})`);
  }
  if (loopbackUrl.port !== '8088') {
    throw new Error(`Guard failed: expected port 8088, got (${loopbackUrl.port})`);
  }

  // Validate initial page.url() origin before listeners or navigation
  const initialUrl = page.url();
  try {
    const initialOrigin = new URL(initialUrl).origin;
    if (initialOrigin !== loopbackUrl.origin && initialUrl !== 'about:blank') {
      throw new Error(`Guard failed: initial page origin ${initialOrigin} does not match BASE_URL ${loopbackUrl.origin}`);
    }
  } catch (urlErr) {
    if (initialUrl !== 'about:blank') throw urlErr;
  }

  // Format currency helper matching Flutter NumberFormat / formatVnd ('200,000 VNĐ')
  function formatVnd(num) {
    return `${num.toLocaleString('en-US')} VNĐ`;
  }

  // Record console categories and counts without persisting raw URLs, text or query parameters
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

  // Activate Flutter accessibility semantics placeholder outside viewport
  async function enableAccessibility() {
    const selector = 'flt-semantics-placeholder, [aria-label*="Enable accessibility"], button:has-text("Enable accessibility")';
    const placeholder = page.locator(selector).first();
    try {
      await placeholder.waitFor({ state: 'attached', timeout: 3000 });
      await placeholder.evaluate(el => el.click());
    } catch (_) {
      // Placeholder may have already been activated or semantics already attached
    }
    await page.waitForTimeout(400);
  }

  // Bounded polling for state assertion on page ariaSnapshot (safe fixed error label, no raw excerpts)
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

  // Navigate back to main UI safely by popping visible Back buttons with real state change waits
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
        // A completed route transition can detach Back while Playwright is
        // resolving it. Only accept the actual destination, not the error.
        if (await accountTab.isVisible().catch(() => false)) return;
        throw new Error('Navigation Back click failed before reaching the main screen');
      }

      let changed = false;
      for (let i = 0; i < 20; i++) {
        if (await accountTab.isVisible().catch(() => false)) {
          changed = true;
          return;
        }
        const currentHeadings = await page.getByRole('heading', { level: 2 }).allTextContents();
        if (currentHeadings.length === 1 && JSON.stringify(currentHeadings) !== JSON.stringify(beforeHeadings)) {
          // Tooltip/focus changes are not route changes. Wait for the new
          // heading to remain stable before resolving another Back button.
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

  // Logout via Account UI and assert auth storage key count is zero without reading values
  async function performLogout() {
    await navigateBackToMain();
    const accountTab = page.getByRole('tab', { name: 'Tài Khoản' });
    await accountTab.waitFor({ state: 'visible', timeout: 10000 });
    await accountTab.click();
    await page.waitForTimeout(300);

    const logoutBtn = page.getByRole('button', { name: 'Đăng xuất' });
    await logoutBtn.waitFor({ state: 'visible', timeout: 10000 });
    await logoutBtn.click();

    const confirmBtn = page.getByRole('button', { name: 'Đăng Xuất', exact: true });
    await confirmBtn.waitFor({ state: 'visible', timeout: 10000 });
    await confirmBtn.click();

    // Await guest state
    await waitForSnapshot(
      snap => snap.includes('Bạn đang xem dưới dạng khách') && snap.includes('Đăng Nhập / Đăng Ký'),
      'Logout failed: guest state not reached'
    );

    // Verify auth storage key count is zero (inspect keys only, never read private values)
    const authKeyCount = await page.evaluate(() => {
      let count = 0;
      for (let i = 0; i < localStorage.length; i++) {
        const k = localStorage.key(i) || '';
        if (k.startsWith('sb-') || k.includes('auth-token') || k.includes('supabase.auth')) {
          count++;
        }
      }
      for (let i = 0; i < sessionStorage.length; i++) {
        const k = sessionStorage.key(i) || '';
        if (k.startsWith('sb-') || k.includes('auth-token') || k.includes('supabase.auth')) {
          count++;
        }
      }
      return count;
    });

    if (authKeyCount !== 0) {
      throw new Error(`Logout assertion failed: auth storage key count is ${authKeyCount}, expected 0`);
    }
  }

  // Login via Account UI, fill fields and press Tab to commit Flutter text controllers
  async function performLogin(email, password, expectedIdentity) {
    async function settleInput() {
      const committed = await page.evaluate(() => Promise.race([
        new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(() => resolve(true)))),
        new Promise(resolve => setTimeout(() => resolve(false), 5000)),
      ]));
      if (!committed) throw new Error('Login input frame commit timed out');
    }
    await navigateBackToMain();
    const accountTab = page.getByRole('tab', { name: 'Tài Khoản' });
    await accountTab.waitFor({ state: 'visible', timeout: 10000 });
    await accountTab.click();
    await page.waitForTimeout(300);

    const loginCta = page.getByRole('button', { name: 'Đăng Nhập / Đăng Ký' });
    await loginCta.waitFor({ state: 'visible', timeout: 10000 });
    await loginCta.click();

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
      throw new Error(`Login ${label} input did not retain the typed value`);
    }

    const emailField = page.getByRole('textbox', { name: 'Email' });
    const passField = page.getByRole('textbox', { name: 'Mật khẩu' });
    await enterInput(emailField, email, 'email');
    await enterInput(passField, password, 'password');
    await passField.press('Tab');
    await settleInput();
    if (await emailField.inputValue() !== email || await passField.inputValue() !== password) {
      throw new Error('Login form did not retain both inputs before submission');
    }

    // Submit login
    const submitBtn = page.getByRole('button', { name: 'Đăng Nhập', exact: true });
    await submitBtn.waitFor({ state: 'visible', timeout: 10000 });
    await submitBtn.click();

    // Await identity from semantic snapshot
    await waitForSnapshot(
      snap => snap.includes(expectedIdentity) && snap.includes('Đã xác thực'),
      `Login failed: expected identity '${expectedIdentity}' with "Đã xác thực" not found in semantic snapshot`
    );
  }

  // Open Summary entry from session detail
  async function openSummaryFromSessionDetail() {
    const summaryBtn = page.getByRole('button', { name: /^Tổng kết buổi/ });
    await summaryBtn.waitFor({ state: 'visible', timeout: 10000 });
    await summaryBtn.click();
  }

  // Verify Owner summary contents against EXPECTED
  async function verifyOwnerSummary(expected, contextLabel) {
    const snap = await waitForSnapshot(
      s => s.includes('Tổng kết buổi') && s.includes('Tài chính tổng hợp') && s.includes('UI Flow Session published to complete'),
      `[${contextLabel}] Summary screen not displayed or missing "Tài chính tổng hợp"`
    );

    // Exact count matching with boundary
    const hasPresent = new RegExp(`(?:Có mặt|Có mặt:)\\s+${expected.present}(?!\\d)`).test(snap);
    const hasAbsent = new RegExp(`(?:Vắng|Vắng:)\\s+${expected.absent}(?!\\d)`).test(snap);
    const hasConfirmed = new RegExp(`(?:Đã xác nhận|Đã xác nhận:)\\s+${expected.confirmed}(?!\\d)`).test(snap);
    if (!hasPresent || !hasAbsent || !hasConfirmed) {
      throw new Error(`[${contextLabel}] Attendance counts mismatch: expected present=${expected.present}, absent=${expected.absent}, confirmed=${expected.confirmed}`);
    }

    // Check financial amounts using EXPECTED values with boundary
    const expStr = formatVnd(expected.expense);
    const dueStr = formatVnd(expected.due);
    const paidStr = formatVnd(expected.paid);
    const outStr = formatVnd(expected.outstanding);

    if (!new RegExp(`Tổng chi phí:?\\s+${expStr}(?!\\d)`).test(snap)) {
      throw new Error(`[${contextLabel}] Total expense mismatch: expected "Tổng chi phí ${expStr}"`);
    }
    if (!new RegExp(`Tổng phải thu:?\\s+${dueStr}(?!\\d)`).test(snap)) {
      throw new Error(`[${contextLabel}] Total due mismatch: expected "Tổng phải thu ${dueStr}"`);
    }
    if (!new RegExp(`Đã thu:?\\s+${paidStr}(?!\\d)`).test(snap)) {
      throw new Error(`[${contextLabel}] Total paid mismatch: expected "Đã thu ${paidStr}"`);
    }
    if (!new RegExp(`Còn phải thu:?\\s+${outStr}(?!\\d)`).test(snap)) {
      throw new Error(`[${contextLabel}] Total outstanding mismatch: expected "Còn phải thu ${outStr}"`);
    }

    return snap;
  }

  // Verify Cohost count-only summary contents
  async function verifyCohostSummary() {
    const snap = await waitForSnapshot(
      s => s.includes('Tổng kết buổi') && s.includes('Chỉ xem số lượng') && s.includes('UI Flow Session published to complete'),
      'Cohost summary screen missing "Tổng kết buổi" or "Chỉ xem số lượng"'
    );

    // Exact count matching with boundary
    const hasPresent = new RegExp(`(?:Có mặt|Có mặt:)\\s+${EXPECTED.present}(?!\\d)`).test(snap);
    const hasAbsent = new RegExp(`(?:Vắng|Vắng:)\\s+${EXPECTED.absent}(?!\\d)`).test(snap);
    const hasConfirmed = new RegExp(`(?:Đã xác nhận|Đã xác nhận:)\\s+${EXPECTED.confirmed}(?!\\d)`).test(snap);
    if (!hasPresent || !hasAbsent || !hasConfirmed) {
      throw new Error(`Cohost attendance counts mismatch: expected present=${EXPECTED.present}, absent=${EXPECTED.absent}, confirmed=${EXPECTED.confirmed}`);
    }

    // Negative assertions: NO finance aggregate group, NO currency, NO financial amounts
    if (snap.includes('Tài chính tổng hợp')) {
      throw new Error('Forbidden "Tài chính tổng hợp" present in Cohost summary');
    }
    if (snap.includes('Tổng chi phí') || snap.includes('Tổng phải thu') || snap.includes('Đã thu') || snap.includes('Còn phải thu')) {
      throw new Error('Forbidden financial labels present in Cohost summary');
    }
    if (snap.includes('200,000') || snap.includes('100,000') || snap.includes('VNĐ') || snap.includes('VND')) {
      throw new Error('Forbidden financial amounts/currency present in Cohost summary');
    }

    return snap;
  }

  let postReloadTimeOrigin = 0;
  let cohostTimeOrigin = 0;
  let memberTimeOrigin = 0;

  let guestSessionSnap = '';
  let ownerSummarySnap = '';
  let ownerSummaryAfterF5Snap = '';
  let cohostSummarySnap = '';
  let cohostOfflineSnap = '';
  let cohostRecoveredSnap = '';
  let recoveryRpcStatus = 0;
  let memberFeeResult = null;
  let clipboardResult = { status: 'NOT_RUN', reason: 'Optional clipboard step omitted in matrix run; covered by Chrome baseline' };

  try {
    // =========================================================================
    // 1. Fresh guest context: direct session link
    // =========================================================================
    await page.goto(SESSION_URL);
    await enableAccessibility();

    // Guard page URL origin matches loopback exactly
    const currentOrigin = new URL(page.url()).origin;
    if (currentOrigin !== loopbackUrl.origin) {
      throw new Error(`Loopback guard failed: expected origin ${loopbackUrl.origin}, got ${currentOrigin}`);
    }

    guestSessionSnap = await waitForSnapshot(
      s => s.includes('UI Flow Session published to complete') && s.includes('Đăng nhập để đăng ký'),
      'Guest session detail screen not loaded or missing public login CTA'
    );

    // Assert absence of management, summary, and private money in guest view
    if (guestSessionSnap.includes('Tổng kết buổi')) {
      throw new Error('Forbidden "Tổng kết buổi" visible in guest session view');
    }
    if (guestSessionSnap.includes('Tài chính & thu tiền')) {
      throw new Error('Forbidden "Tài chính & thu tiền" visible in guest session view');
    }
    if (guestSessionSnap.includes('Phần phí của tôi')) {
      throw new Error('Forbidden "Phần phí của tôi" visible in guest session view');
    }
    if (guestSessionSnap.includes('Tài chính tổng hợp') || guestSessionSnap.includes('200,000') || guestSessionSnap.includes('100,000')) {
      throw new Error('Forbidden private finance details visible in guest session view');
    }

    // =========================================================================
    // 2. Login Owner via normal home Account UI
    // =========================================================================
    await page.goto(`${BASE_URL}/#/`);
    await enableAccessibility();

    await performLogin(OWNER_EMAIL, PASSWORD, 'ownera@example.test');

    // Navigate to authenticated session hash link
    await page.goto(SESSION_URL);
    await enableAccessibility();

    await openSummaryFromSessionDetail();
    ownerSummarySnap = await verifyOwnerSummary(EXPECTED, 'Stage 2 Initial Owner');

    // =========================================================================
    // 3. F5 Reload: verify auth restored and reopen summary
    // =========================================================================
    await page.reload();
    await enableAccessibility();

    // After F5 reload, navigate back to main navigation if hash session detail was preserved
    await navigateBackToMain();

    const accountTab = page.getByRole('tab', { name: 'Tài Khoản' });
    await accountTab.waitFor({ state: 'visible', timeout: 10000 });
    await accountTab.click();
    await waitForSnapshot(
      snap => snap.includes('ownera@example.test') && snap.includes('Đã xác thực'),
      'Auth not restored after F5 reload'
    );

    // Reopen hash session and verify same exact amounts
    await page.goto(SESSION_URL);
    await enableAccessibility();
    await openSummaryFromSessionDetail();
    ownerSummaryAfterF5Snap = await verifyOwnerSummary(EXPECTED, 'Stage 3 Post-F5 Owner');

    // =========================================================================
    // 4. Capture timeOrigin AFTER reload, logout Owner, login Cohost (same doc)
    // =========================================================================
    postReloadTimeOrigin = await page.evaluate(() => performance.timeOrigin);

    await performLogout();

    // Login Cohost via UI (NO reload, NO goto for actor switch)
    await performLogin(COHOST_EMAIL, PASSWORD, 'cohosta@example.test');

    cohostTimeOrigin = await page.evaluate(() => performance.timeOrigin);
    if (cohostTimeOrigin !== postReloadTimeOrigin) {
      throw new Error(`Document continuity violated: timeOrigin changed from ${postReloadTimeOrigin} to ${cohostTimeOrigin}`);
    }

    // Navigate to summary via in-app UI
    const sessionTab = page.getByRole('tab', { name: 'Buổi Chơi' });
    await sessionTab.waitFor({ state: 'visible', timeout: 10000 });
    await sessionTab.click();
    const historyTile = page.getByRole('button', { name: /^Lịch sử buổi/ });
    await historyTile.waitFor({ state: 'visible', timeout: 10000 });
    await historyTile.click();
    // Match the named history row, not an ancestor group containing every row.
    const sessionRow = page.getByRole('group', { name: /^UI Flow Session published to complete/ });
    await sessionRow.waitFor({ state: 'visible', timeout: 10000 });
    await sessionRow.click();
    await waitForSnapshot(
      s => s.includes(`/sessions/${SESSION_ID}`) && s.includes('Chi tiết buổi chơi'),
      'Selected history row did not open the expected fixture session'
    );

    await openSummaryFromSessionDetail();
    cohostSummarySnap = await verifyCohostSummary();

    // =========================================================================
    // 5. Offline read refresh and online recovery
    // =========================================================================
    try {
      await page.context().setOffline(true);
      const refreshBtn = page.getByRole('button', { name: 'Tải lại tổng kết' });
      await refreshBtn.waitFor({ state: 'visible', timeout: 5000 });
      await refreshBtn.click();

      cohostOfflineSnap = await waitForSnapshot(
        s => s.includes('Chưa làm mới được tổng kết') && s.includes('Dữ liệu đang hiển thị là lần tải trước'),
        'Offline refresh error banner did not appear',
        25000 // Includes the app's 15-second deadline for a stalled read.
      );

      // Reconnect and retry
      await page.context().setOffline(false);
      const retryBtn = page.getByRole('button', { name: 'Thử lại' });
      await retryBtn.waitFor({ state: 'visible', timeout: 5000 });

      // Start waitForResponse before clicking retry, await together with bounded timeout
      // A timed-out HTTP call may still finish after reconnect. Only accept
      // the new UI retry request, not that older response for the same session.
      let retryRequest = null;
      const observeRetryRequest = request => {
        if (retryRequest) return;
        try {
          const url = new URL(request.url());
          if (request.method() === 'POST' &&
              (url.origin === 'http://127.0.0.1:54321' || url.origin === 'http://localhost:54321') &&
              url.pathname === '/rest/v1/rpc/get_session_summary' &&
              request.postDataJSON()?.p_session_id === SESSION_ID) retryRequest = request;
        } catch (_) {}
      };
      page.on('request', observeRetryRequest);
      let rpcResponse;
      try {
        [rpcResponse] = await Promise.all([
        page.waitForResponse(response => {
          const req = response.request();
          if (req !== retryRequest) return false;
          if (req.method() !== 'POST') return false;
          try {
            const url = new URL(response.url());
            if (url.origin !== 'http://127.0.0.1:54321' && url.origin !== 'http://localhost:54321') return false;
            if (url.pathname !== '/rest/v1/rpc/get_session_summary') return false;
          } catch (_) {
            return false;
          }
          if (response.status() !== 200) return false;
          try {
            return req.postDataJSON()?.p_session_id === SESSION_ID;
          } catch (_) {
            return false;
          }
        }, { timeout: 15000 }),
        retryBtn.click(),
        ]);
      } finally {
        page.off('request', observeRetryRequest);
      }

      recoveryRpcStatus = rpcResponse.status();

      // Retry clears the old banner at start. Wait for loading to finish too.
      await waitForSnapshot(
        async s => !s.includes('Chưa làm mới được tổng kết') &&
          !s.includes('Dữ liệu đang hiển thị là lần tải trước') &&
          await refreshBtn.isEnabled({ timeout: 1000 }),
        'Online retry did not finish with the error banner cleared'
      );

      // Verify Cohost count-only summary and absence of finance AFTER response
      cohostRecoveredSnap = await verifyCohostSummary();
      if (cohostRecoveredSnap.includes('Chưa làm mới được tổng kết') || cohostRecoveredSnap.includes('Dữ liệu đang hiển thị là lần tải trước')) {
        throw new Error('Offline refresh error banner still present in recovered summary');
      }
    } finally {
      // Ensure browser context always returns online with fail-closed error
      try {
        await page.context().setOffline(false);
      } catch (_) {
        throw new Error('Cleanup failed: unable to restore network online state');
      }
    }

    // =========================================================================
    // 6. Optional clipboard check (omitted with explicit NOT_RUN; measured on Chrome)
    // =========================================================================
    clipboardResult = {
      status: 'NOT_RUN',
      reason: 'Optional clipboard step omitted in matrix run; covered by Chrome baseline',
    };

    // =========================================================================
    // 7. Logout Cohost -> Login Member (same document) -> Member fee boundary
    // =========================================================================
    await performLogout();

    await performLogin(MEMBER_EMAIL, PASSWORD, 'membera@example.test');

    memberTimeOrigin = await page.evaluate(() => performance.timeOrigin);
    if (memberTimeOrigin !== postReloadTimeOrigin) {
      throw new Error(`Document continuity violated in stage 7: timeOrigin changed from ${postReloadTimeOrigin} to ${memberTimeOrigin}`);
    }

    // Navigate to session detail via direct hash link (Member history management may be empty)
    await page.goto(SESSION_URL);
    await enableAccessibility();

    const memberDetailSnap = await waitForSnapshot(
      s => s.includes('Phần phí của tôi'),
      'Member session detail missing "Phần phí của tôi" entry'
    );

    // Assert boundaries: no management / finance actions for Member
    if (memberDetailSnap.includes('Tài chính & thu tiền')) {
      throw new Error('Forbidden "Tài chính & thu tiền" present in Member session detail');
    }
    if (memberDetailSnap.includes('Tổng kết buổi')) {
      throw new Error('Forbidden "Tổng kết buổi" present in Member session detail');
    }

    // Open own fees
    const ownFeeBtn = page.getByRole('button', { name: /^Phần phí của tôi/ });
    await ownFeeBtn.waitFor({ state: 'visible', timeout: 10000 });
    await ownFeeBtn.click();

    // Verify own fee assertions: due 100,000, paid 100,000, outstanding 0
    const feeSnap = await waitForSnapshot(
      s => s.includes('Phần phí của bạn'),
      'Member fee screen missing "Phần phí của bạn"'
    );

    const hasDue = feeSnap ? /Phải trả:?\s*100,000\s*VNĐ(?!\d)/.test(feeSnap) : false;
    const hasPaid = feeSnap ? /Đã trả:?\s*100,000\s*VNĐ(?!\d)/.test(feeSnap) : false;
    const hasOutstanding = feeSnap ? /Còn lại:?\s*0\s*VNĐ(?!\d)/.test(feeSnap) : false;

    if (!hasDue || !hasPaid || !hasOutstanding) {
      throw new Error('Member own-fee mismatch: expected due=100000, paid=100000, outstanding=0');
    }

    memberFeeResult = {
      due: 100000,
      paid: 100000,
      outstanding: 0,
      verified: true,
    };
  } finally {
    // End online, do not close browser or touch backend
    let cleanupErr = null;
    try {
      await page.context().setOffline(false);
    } catch (_) {
      cleanupErr = new Error('Cleanup failed: unable to restore network online state');
    } finally {
      page.off('console', onConsole);
      page.off('pageerror', onPageError);
    }
    if (cleanupErr) {
      throw cleanupErr;
    }
  }

  // Return sanitized structured result
  return {
    ok: true,
    url_origin: loopbackUrl.origin,
    session_id: SESSION_ID,
    expected_aggregate: EXPECTED,
    time_origins: {
      post_reload: postReloadTimeOrigin,
      cohost_session: cohostTimeOrigin,
      member_session: memberTimeOrigin,
      continuity_verified: (postReloadTimeOrigin === cohostTimeOrigin && cohostTimeOrigin === memberTimeOrigin),
    },
    step_results: {
      stage_1_guest: {
        verified: true,
        has_login_cta: true,
        management_absent: true,
        summary_absent: true,
        private_money_absent: true,
        snapshot: guestSessionSnap,
      },
      stage_2_owner_initial: {
        verified: true,
        identity: OWNER_EMAIL,
        snapshot: ownerSummarySnap,
      },
      stage_3_owner_post_f5: {
        verified: true,
        auth_restored: true,
        snapshot: ownerSummaryAfterF5Snap,
      },
      stage_4_cohost_actor_switch: {
        verified: true,
        identity: COHOST_EMAIL,
        logout_auth_storage_key_count: 0,
        count_only_verified: true,
        finance_aggregate_absent: true,
        amounts_and_currency_absent: true,
        snapshot: cohostSummarySnap,
      },
      stage_5_offline_refresh_recovery: {
        verified: true,
        offline_error_detected: true,
        online_recovery_detected: true,
        rpc_status: recoveryRpcStatus,
        offline_snapshot: cohostOfflineSnap,
        recovered_snapshot: cohostRecoveredSnap,
      },
      stage_6_clipboard: clipboardResult,
      stage_7_member_actor_switch: {
        verified: true,
        identity: MEMBER_EMAIL,
        navigation_method: 'direct_hash_link',
        management_and_summary_absent: true,
        own_fees: memberFeeResult,
      },
    },
    recorded_console_summary: consoleSummary,
  };
}
