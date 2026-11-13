async page => {
  // Guard loopback origin and fixed session configuration
  const BASE_URL = 'http://127.0.0.1:8088';
  const SESSION_ID = '10000000-0000-4000-8000-000000000099';
  const SESSION_URL = `${BASE_URL}/#/sessions/${SESSION_ID}`;
  const MEMBER_EMAIL = 'membera@example.test';
  const EXPECTED_FEE = {
    due: 100000,
    paid: 100000,
    outstanding: 0,
  };

  const expectedOrigin = new URL(BASE_URL).origin;
  if (expectedOrigin !== 'http://127.0.0.1:8088') {
    throw new Error(`Guard failed: invalid BASE_URL origin (${expectedOrigin})`);
  }

  const initialOrigin = new URL(page.url()).origin;
  if (initialOrigin !== expectedOrigin) {
    throw new Error(`Guard failed: initial page origin ${initialOrigin} does not match ${expectedOrigin}`);
  }

  // Record console/pageerror counts without storing raw URLs, text, or query parameters
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
  async function enableAccessibility(targetPage) {
    const selector = 'flt-semantics-placeholder, [aria-label*="Enable accessibility"], button:has-text("Enable accessibility")';
    const placeholder = targetPage.locator(selector).first();
    try {
      await placeholder.waitFor({ state: 'attached', timeout: 3000 });
      await placeholder.evaluate(el => el.click());
    } catch (_) {
      // Placeholder may have already been activated or semantics already attached
    }
    await targetPage.waitForTimeout(400);
  }

  // Bounded polling on page ariaSnapshot (fixed error label, no raw excerpts)
  async function waitForSnapshot(targetPage, predicate, errorMsg, timeoutMs = 15000, pollIntervalMs = 400) {
    const start = Date.now();
    while (Date.now() - start < timeoutMs) {
      const snap = await targetPage.locator('body').ariaSnapshot();
      if (await predicate(snap)) {
        return snap;
      }
      await targetPage.waitForTimeout(pollIntervalMs);
    }
    throw new Error(errorMsg);
  }

  // Navigate back to main UI safely by popping visible Back buttons with real state change waits
  async function navigateBackToMain(targetPage) {
    const accountTab = targetPage.getByRole('tab', { name: 'Tài Khoản' });
    for (let step = 0; step < 6; step++) {
      if (await accountTab.isVisible().catch(() => false)) {
        return;
      }
      const backBtn = targetPage.getByRole('button', { name: 'Back' }).first();
      const hasBack = await backBtn.isVisible().catch(() => false);
      if (!hasBack) {
        await targetPage.waitForTimeout(300);
        if (await accountTab.isVisible().catch(() => false)) {
          return;
        }
        throw new Error('Navigation failed: neither "Tài Khoản" tab nor "Back" button is visible');
      }

      const beforeHeadings = await targetPage.getByRole('heading', { level: 2 }).allTextContents();
      try {
        await backBtn.click({ timeout: 5000 });
      } catch (_) {
        if (await accountTab.isVisible().catch(() => false)) return;
        throw new Error('Navigation Back click failed before reaching the main screen');
      }

      let changed = false;
      for (let i = 0; i < 20; i++) {
        if (await accountTab.isVisible().catch(() => false)) {
          changed = true;
          return;
        }
        const currentHeadings = await targetPage.getByRole('heading', { level: 2 }).allTextContents();
        if (currentHeadings.length === 1 && JSON.stringify(currentHeadings) !== JSON.stringify(beforeHeadings)) {
          await targetPage.waitForTimeout(200);
          const settledHeadings = await targetPage.getByRole('heading', { level: 2 }).allTextContents();
          if (JSON.stringify(settledHeadings) === JSON.stringify(currentHeadings)) {
            changed = true;
            break;
          }
        }
        await targetPage.waitForTimeout(200);
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
  async function performLogout(targetPage) {
    await navigateBackToMain(targetPage);
    const accountTab = targetPage.getByRole('tab', { name: 'Tài Khoản' });
    await accountTab.waitFor({ state: 'visible', timeout: 10000 });
    await accountTab.click();
    await targetPage.waitForTimeout(300);

    const logoutBtn = targetPage.getByRole('button', { name: 'Đăng xuất' });
    await logoutBtn.waitFor({ state: 'visible', timeout: 10000 });
    await logoutBtn.click();

    const confirmBtn = targetPage.getByRole('button', { name: 'Đăng Xuất', exact: true });
    await confirmBtn.waitFor({ state: 'visible', timeout: 10000 });
    await confirmBtn.click();

    await waitForSnapshot(
      targetPage,
      snap => snap.includes('Bạn đang xem dưới dạng khách') && snap.includes('Đăng Nhập / Đăng Ký'),
      'Logout failed: guest state not reached'
    );

    const authKeyCount = await targetPage.evaluate(() => {
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
    return authKeyCount;
  }

  const context = page.context();
  let newPage = null;
  let pagesBeforeClose = 0;
  let pagesAfterClose = 0;
  let destinationLoadedAfterOriginalClosed = false;
  let logoutAuthKeyCount = -1;
  let destinationAssertionsPassed = false;

  // Build dynamic fee regex from EXPECTED_FEE using en-US locale grouping and digit boundaries
  function buildFeeRegex(label, amount) {
    const formatted = amount.toLocaleString('en-US').replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    return new RegExp(`${label}:?\\s*(?<!\\d)${formatted}(?!\\d)\\s*VNĐ(?!\\d)`);
  }

  try {
    // =========================================================================
    // 1. Assert initial Member identity on original tab via root Account tab
    // =========================================================================
    await enableAccessibility(page);
    await navigateBackToMain(page);

    const initialAccountTab = page.getByRole('tab', { name: 'Tài Khoản' });
    await initialAccountTab.waitFor({ state: 'visible', timeout: 10000 });
    await initialAccountTab.click();
    await waitForSnapshot(
      page,
      snap => snap.includes(MEMBER_EMAIL) && snap.includes('Đã xác thực'),
      'Initial Member identity not verified on original tab Account screen'
    );

    // =========================================================================
    // 2. Open blank safety-anchor tab, verify >=2 pages, then close original tab
    // =========================================================================
    newPage = await context.newPage();
    newPage.on('console', onConsole);
    newPage.on('pageerror', onPageError);

    pagesBeforeClose = context.pages().length;
    if (pagesBeforeClose < 2) {
      throw new Error(`Guard failed: refusing to close original tab with only ${pagesBeforeClose} page(s) open`);
    }
    if (newPage.isClosed()) {
      throw new Error('Guard failed: blank anchor tab closed unexpectedly before original tab close');
    }
    await page.close();
    if (!page.isClosed()) {
      throw new Error('Original tab failed to close');
    }
    pagesAfterClose = context.pages().length;
    if (pagesAfterClose < 1 || pagesAfterClose >= pagesBeforeClose || newPage.isClosed()) {
      throw new Error(
        `Guard failed: unexpected page count after closing original tab (before=${pagesBeforeClose}, after=${pagesAfterClose})`
      );
    }

    // =========================================================================
    // 3. Reopen app on blank new tab ONLY after original.isClosed() check
    // =========================================================================
    if (!page.isClosed()) {
      throw new Error('Guard failed: original tab must be closed before navigating new tab to session URL');
    }
    await newPage.goto(SESSION_URL);
    destinationLoadedAfterOriginalClosed = true;

    const newTabOrigin = new URL(newPage.url()).origin;
    if (newTabOrigin !== expectedOrigin) {
      throw new Error(`Guard failed: new tab origin ${newTabOrigin} does not match ${expectedOrigin}`);
    }
    await enableAccessibility(newPage);

    const memberDetailSnap = await waitForSnapshot(
      newPage,
      s => s.includes('UI Flow Session published to complete') && s.includes('Phần phí của tôi'),
      'New tab Member session detail missing session title or "Phần phí của tôi"'
    );

    if (
      memberDetailSnap.includes('Tài chính & thu tiền') ||
      memberDetailSnap.includes('Tổng kết buổi') ||
      memberDetailSnap.includes('Tài chính tổng hợp')
    ) {
      throw new Error('Forbidden management, summary, or financial aggregate visible in Member session detail');
    }

    const ownFeeBtn = newPage.getByRole('button', { name: /^Phần phí của tôi/ });
    await ownFeeBtn.waitFor({ state: 'visible', timeout: 10000 });
    await ownFeeBtn.click();

    const feeSnap = await waitForSnapshot(
      newPage,
      s => s.includes('Phần phí của bạn'),
      'New tab Member fee screen missing "Phần phí của bạn"'
    );

    const hasDue = buildFeeRegex('Phải trả', EXPECTED_FEE.due).test(feeSnap);
    const hasPaid = buildFeeRegex('Đã trả', EXPECTED_FEE.paid).test(feeSnap);
    const hasOutstanding = buildFeeRegex('Còn lại', EXPECTED_FEE.outstanding).test(feeSnap);
    if (!hasDue || !hasPaid || !hasOutstanding) {
      throw new Error(
        `New tab Member own-fee mismatch: expected due=${EXPECTED_FEE.due}, paid=${EXPECTED_FEE.paid}, outstanding=${EXPECTED_FEE.outstanding}`
      );
    }

    // =========================================================================
    // 4. Operate new tab: navigate root Account and assert Member restored
    // =========================================================================
    await navigateBackToMain(newPage);
    const restoredAccountTab = newPage.getByRole('tab', { name: 'Tài Khoản' });
    await restoredAccountTab.waitFor({ state: 'visible', timeout: 10000 });
    await restoredAccountTab.click();
    await waitForSnapshot(
      newPage,
      snap => snap.includes(MEMBER_EMAIL) && snap.includes('Đã xác thực'),
      'Restored Member identity check failed on new tab Account screen'
    );

    // =========================================================================
    // 5. Logout via real UI and verify guest direct session URL boundary
    // =========================================================================
    logoutAuthKeyCount = await performLogout(newPage);

    await newPage.goto(SESSION_URL);
    const guestOrigin = new URL(newPage.url()).origin;
    if (guestOrigin !== expectedOrigin) {
      throw new Error(`Guard failed: guest session origin ${guestOrigin} does not match ${expectedOrigin}`);
    }
    await enableAccessibility(newPage);

    const guestSessionSnap = await waitForSnapshot(
      newPage,
      s => s.includes('UI Flow Session published to complete') && s.includes('Đăng nhập để đăng ký'),
      'Guest session detail screen not loaded or missing public login CTA'
    );

    if (
      guestSessionSnap.includes('Tổng kết buổi') ||
      guestSessionSnap.includes('Tài chính & thu tiền') ||
      guestSessionSnap.includes('Phần phí của tôi') ||
      guestSessionSnap.includes('Phần phí của bạn') ||
      guestSessionSnap.includes('Tài chính tổng hợp') ||
      guestSessionSnap.includes('200,000') ||
      guestSessionSnap.includes('100,000')
    ) {
      throw new Error('Forbidden private fee, summary, or finance details visible in guest session view');
    }

    destinationAssertionsPassed = true;
  } finally {
    // Always restore online state and detach listeners; never suppress cleanup errors.
    // On failure, leave original tab if not yet closed and never close the last remaining page.
    let cleanupErr = null;
    try {
      await context.setOffline(false);
    } catch (_) {
      cleanupErr = new Error('Cleanup failed: unable to restore network online state');
    } finally {
      page.off('console', onConsole);
      page.off('pageerror', onPageError);
      if (newPage) {
        newPage.off('console', onConsole);
        newPage.off('pageerror', onPageError);
      }
    }
    if (cleanupErr) {
      throw cleanupErr;
    }
  }

  const originalClosed = page.isClosed();
  const newTabOpen = Boolean(newPage && !newPage.isClosed());
  if (!originalClosed || !newTabOpen || !destinationLoadedAfterOriginalClosed || !destinationAssertionsPassed) {
    throw new Error('Tab reopen assertions incomplete after execution');
  }

  return {
    ok: true,
    url_origin: expectedOrigin,
    session_id: SESSION_ID,
    tab_reopen: {
      status: 'PASS',
      original_tab_closed: originalClosed,
      destination_loaded_after_original_closed: destinationLoadedAfterOriginalClosed,
      new_tab_open: newTabOpen,
      pages_before_close: pagesBeforeClose,
      pages_after_close: pagesAfterClose,
    },
    browser_cold_restart: {
      status: 'NOT_RUN',
      reason: 'Same-profile tab close/reopen only; full browser process cold restart not executed',
    },
    clipboard: {
      status: 'NOT_RUN',
      reason: 'No clipboard or QR verification claimed by this scenario',
    },
    qr: {
      status: 'NOT_RUN',
      reason: 'No clipboard or QR verification claimed by this scenario',
    },
    checks: {
      initial_member_identity_verified: true,
      new_tab_member_session_verified: true,
      new_tab_management_summary_finance_absent: true,
      new_tab_own_fee_verified: true,
      expected_own_fee: EXPECTED_FEE,
      restored_member_identity_verified: true,
      logout_guest_state_verified: true,
      logout_auth_storage_key_count: logoutAuthKeyCount,
      guest_direct_session_public_cta_verified: true,
      guest_private_fee_summary_finance_absent: true,
    },
    recorded_console_summary: consoleSummary,
  };
}