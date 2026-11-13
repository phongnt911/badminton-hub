async page => {
  // Configuration constants (Codex substitutes in an ignored driver copy only)
  const MODE = 'cohost_copy';
  const EXPECTED_RECEIVER = null;

  const BASE_URL = 'http://127.0.0.1:8088';
  const SESSION_ID = '10000000-0000-4000-8000-000000000099';
  const SESSION_TITLE = 'UI Flow Session published to complete';
  const SESSION_URL = `${BASE_URL}/#/sessions/${SESSION_ID}`;
  const COHOST_EMAIL = 'cohosta@example.test';
  const GUEST_EMAIL = 'guesta@example.test';
  const PASSWORD = 'bh07-http-pass-123456';
  const VIETQR_ROUTE_PATTERN = 'https://img.vietqr.io/**';
  const QR_FALLBACK_TEXT = 'Không tải được ảnh QR. Dùng thông tin bên dưới để chuyển khoản.';
  const QR_MANUAL_NOTICE =
    'Mã QR chỉ là hướng dẫn chuyển khoản, KHÔNG tự xác nhận đã thu. Ban quản lý xác nhận thủ công sau khi nhận tiền.';
  const CLIPBOARD_UNSUPPORTED_REASON =
    'Browser context does not support clipboard-read/clipboard-write permission grants';

  // Validate mode and receiver configuration before any browser interaction
  if (MODE !== 'cohost_copy' && MODE !== 'guest_qr') {
    throw new Error('Guard failed: MODE must be cohost_copy or guest_qr');
  }
  if (MODE === 'guest_qr') {
    if (!EXPECTED_RECEIVER || typeof EXPECTED_RECEIVER !== 'object' || Array.isArray(EXPECTED_RECEIVER)) {
      throw new Error('Guard failed: EXPECTED_RECEIVER must be a non-null plain object in guest_qr mode');
    }
    for (const key of ['bank_code', 'account_number', 'account_name', 'reference']) {
      const value = EXPECTED_RECEIVER[key];
      if (typeof value !== 'string' || value.trim().length === 0) {
        throw new Error(`Guard failed: EXPECTED_RECEIVER.${key} must be a non-empty string`);
      }
    }
  }

  // Guard loopback origin and initial page URL before attaching listeners or navigating
  const expectedBase = new URL(BASE_URL);
  if (expectedBase.origin !== 'http://127.0.0.1:8088') {
    throw new Error('Guard failed: BASE_URL origin must be exactly http://127.0.0.1:8088');
  }
  const initialUrl = page.url();
  if (initialUrl !== 'about:blank') {
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

  const context = page.context();

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

  let permissionsAttempted = false;
  let clipboardGranted = false;
  let vietqrRouteInstalled = false;
  let routeAbortCount = 0;
  const vietqrRouteHandler = async route => {
    routeAbortCount++;
    await route.abort();
  };

  function escapeRegex(value) {
    return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  }

  function hasExactCohostCounts(text) {
    return (
      typeof text === 'string' &&
      /(?:^|\r?\n)(?:👥 )?Có mặt: 2 · Vắng: 0 · Đã xác nhận: 2[ \t]*(?=\r?\n|$)/.test(text)
    );
  }

  function assertLoopbackOrigin() {
    let currentOrigin = '';
    try {
      currentOrigin = new URL(page.url()).origin;
    } catch (_) {
      throw new Error('Guard failed: invalid page URL after navigation');
    }
    if (currentOrigin !== expectedBase.origin) {
      throw new Error('Guard failed: page origin left http://127.0.0.1:8088');
    }
  }

  async function enableAccessibility() {
    const placeholder = page
      .locator('flt-semantics-placeholder, [aria-label*="Enable accessibility"], button:has-text("Enable accessibility")')
      .first();
    const accountTab = page.getByRole('tab', { name: 'Tài Khoản' });
    const detailHeading = page.getByText('Chi tiết buổi chơi', { exact: true });
    await Promise.race([
      placeholder.waitFor({ state: 'attached', timeout: 15000 }).catch(() => {}),
      accountTab.waitFor({ state: 'visible', timeout: 15000 }).catch(() => {}),
      detailHeading.waitFor({ state: 'visible', timeout: 15000 }).catch(() => {}),
    ]);
    try {
      if (await placeholder.count() > 0) {
        await placeholder.evaluate(el => el.click());
      }
    } catch (_) {
      // Placeholder may already be activated or detached
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

  async function bootstrapFreshGuestAndLogin(email, expectedIdentity) {
    await page.goto(`${BASE_URL}/#/`);
    assertLoopbackOrigin();

    // Repeatedly activate semantics until root Account tab is visible (bounded 20s deadline)
    const accountTab = page.getByRole('tab', { name: 'Tài Khoản' });
    const bootstrapDeadline = Date.now() + 20000;
    while (!(await accountTab.isVisible().catch(() => false))) {
      await enableAccessibility();
      if (await accountTab.isVisible().catch(() => false)) {
        break;
      }
      if (Date.now() >= bootstrapDeadline) {
        throw new Error('Guest home bootstrap timed out waiting for visible "Tài Khoản" tab');
      }
      await page.waitForTimeout(400);
    }
    await accountTab.waitFor({ state: 'visible', timeout: 10000 });
    await accountTab.click();

    await waitForSnapshot(
      snap => snap.includes('Bạn đang xem dưới dạng khách') && snap.includes('Đăng Nhập / Đăng Ký'),
      'Expected fresh guest state on Account tab before login'
    );

    const loginCta = page.getByRole('button', { name: 'Đăng Nhập / Đăng Ký' });
    await loginCta.waitFor({ state: 'visible', timeout: 10000 });
    await loginCta.click();

    const emailField = page.getByRole('textbox', { name: 'Email' });
    const passField = page.getByRole('textbox', { name: 'Mật khẩu' });
    await enterInput(emailField, email, 'email');
    await enterInput(passField, PASSWORD, 'password');
    await passField.press('Tab');
    await settleInput();
    if (await emailField.inputValue() !== email || await passField.inputValue() !== PASSWORD) {
      throw new Error('Login form did not retain both inputs before submission');
    }

    const submitBtn = page.getByRole('button', { name: 'Đăng Nhập', exact: true });
    await submitBtn.waitFor({ state: 'visible', timeout: 10000 });
    await submitBtn.click();

    await waitForSnapshot(
      snap => snap.includes(expectedIdentity) && snap.includes('Đã xác thực'),
      'Login failed: expected authenticated actor state not found in semantic snapshot'
    );
  }

  async function readClipboardOrThrow() {
    const text = await page.evaluate(() => navigator.clipboard.readText());
    if (typeof text !== 'string' || text.length === 0) {
      throw new Error('Clipboard read returned empty or non-string content');
    }
    return text;
  }

  let clipboardResult = null;
  let qrResult = null;
  let feeResult = null;

  try {
    // Grant clipboard permissions when supported; skip ONLY recognized unsupported clipboard permission errors
    permissionsAttempted = true;
    try {
      await context.grantPermissions(['clipboard-read', 'clipboard-write'], { origin: expectedBase.origin });
      clipboardGranted = true;
    } catch (err) {
      clipboardGranted = false;
      const message = err && typeof err.message === 'string' ? err.message : '';
      const isUnsupportedClipboard =
        /Unknown permission:\s*(['"]?)clipboard-(?:read|write)\1(?=$|[\s.,;:])/.test(message);
      if (!isUnsupportedClipboard) {
        throw new Error('Clipboard permission grant failed unexpectedly');
      }
    }

    if (MODE === 'cohost_copy') {
      await bootstrapFreshGuestAndLogin(COHOST_EMAIL, COHOST_EMAIL);

      await page.goto(SESSION_URL);
      assertLoopbackOrigin();
      await enableAccessibility();

      await waitForSnapshot(
        snap => snap.includes(SESSION_TITLE) && snap.includes('Tổng kết buổi'),
        'Cohost session detail missing session title or "Tổng kết buổi"'
      );

      const summaryBtn = page.getByRole('button', { name: /^Tổng kết buổi/ });
      await summaryBtn.waitFor({ state: 'visible', timeout: 10000 });
      await summaryBtn.click();

      const summarySnap = await waitForSnapshot(
        snap =>
          snap.includes('Tổng kết buổi') &&
          snap.includes(SESSION_TITLE) &&
          snap.includes('Chỉ xem số lượng'),
        'Cohost summary screen missing title or "Chỉ xem số lượng"'
      );

      const hasPresent = /(?:Có mặt|Có mặt:)\s+2(?!\d)/.test(summarySnap);
      const hasAbsent = /(?:Vắng|Vắng:)\s+0(?!\d)/.test(summarySnap);
      const hasConfirmed = /(?:Đã xác nhận|Đã xác nhận:)\s+2(?!\d)/.test(summarySnap);
      if (!hasPresent || !hasAbsent || !hasConfirmed) {
        throw new Error('Cohost summary attendance counts mismatch: expected 2/0/2');
      }

      const forbiddenUiTokens = [
        'Tài chính tổng hợp',
        'Tổng chi phí',
        'Tổng phải thu',
        'Đã thu',
        'Còn phải thu',
        '200,000',
        '100,000',
        '200000',
        '100000',
        'VNĐ',
        'VND',
      ];
      if (forbiddenUiTokens.some(token => summarySnap.includes(token))) {
        throw new Error('Forbidden finance group, labels, currency, or amounts visible in Cohost summary');
      }

      if (clipboardGranted) {
        const copySummaryBtn = page.getByRole('button', { name: 'Sao chép tổng kết', exact: true });
        await copySummaryBtn.waitFor({ state: 'visible', timeout: 10000 });
        await copySummaryBtn.click();

        await waitForSnapshot(
          snap => snap.includes('Đã sao chép tổng kết buổi.'),
          'Cohost copy confirmation snackbar "Đã sao chép tổng kết buổi." not found'
        );

        const copiedText = await readClipboardOrThrow();
        if (!copiedText.includes(SESSION_TITLE)) {
          throw new Error('Cohost clipboard mismatch: exact session title missing');
        }
        if (!hasExactCohostCounts(copiedText)) {
          throw new Error('Cohost clipboard mismatch: expected attendance counts string missing');
        }

        const forbiddenClipboardPatterns = [
          /vn[dđ]/i,
          /200,?000/,
          /100,?000/,
          /Tài chính tổng hợp/i,
          /Tổng chi phí/i,
          /Tổng phải thu/i,
          /Đã thu/i,
          /Còn phải thu/i,
          /Phải trả/i,
          /Còn lại/i,
          /Số tiền/i,
          /Ngân hàng/i,
          /Số tài khoản/i,
          /Chủ tài khoản/i,
          /Nội dung/i,
          /Chuyển khoản/i,
          /vietqr/i,
          /Số điện thoại/i,
          /SĐT/i,
          /@/,
          /\b0\d{8,10}\b/,
          /\+\d{8,15}\b/,
          /Member A/i,
          /Guest A/i,
          /membera|guesta|cohosta|ownera/i,
        ];
        if (forbiddenClipboardPatterns.some(pattern => pattern.test(copiedText))) {
          throw new Error('Cohost clipboard failed privacy check: forbidden finance, bank, contact, or player data found');
        }

        clipboardResult = {
          status: 'PASS',
          reason: null,
          counts_verified: true,
          private_finance_absent: true,
        };
      } else {
        clipboardResult = {
          status: 'NOT_RUN',
          reason: CLIPBOARD_UNSUPPORTED_REASON,
          counts_verified: false,
          private_finance_absent: false,
        };
      }

      return {
        ok: true,
        mode: MODE,
        url_origin: expectedBase.origin,
        session_id: SESSION_ID,
        ui_count_only: true,
        clipboard: clipboardResult,
        recorded_console_summary: consoleSummary,
      };
    }

    // MODE === 'guest_qr'
    await bootstrapFreshGuestAndLogin(GUEST_EMAIL, GUEST_EMAIL);

    // Abort ONLY external VietQR image requests while preserving local API untouched
    await page.route(VIETQR_ROUTE_PATTERN, vietqrRouteHandler);
    vietqrRouteInstalled = true;

    await page.goto(SESSION_URL);
    assertLoopbackOrigin();
    await enableAccessibility();

    const guestDetailSnap = await waitForSnapshot(
      snap => snap.includes(SESSION_TITLE) && snap.includes('Phần phí của tôi'),
      'Guest A session detail missing session title or "Phần phí của tôi"'
    );

    if (
      guestDetailSnap.includes('Tổng kết buổi') ||
      guestDetailSnap.includes('Tài chính & thu tiền') ||
      guestDetailSnap.includes('Tài chính tổng hợp')
    ) {
      throw new Error('Forbidden management or summary visible in Guest A session detail');
    }

    const ownFeeBtn = page.getByRole('button', { name: /^Phần phí của tôi/ });
    await ownFeeBtn.waitFor({ state: 'visible', timeout: 10000 });
    await ownFeeBtn.click();

    const feeQrSnap = await waitForSnapshot(
      snap =>
        snap.includes('Phần phí của bạn') &&
        snap.includes('Chuyển khoản để thanh toán') &&
        snap.includes(QR_FALLBACK_TEXT) &&
        snap.includes(QR_MANUAL_NOTICE),
      'Guest A finance screen missing fee summary, QR fallback message, or manual notice'
    );

    if (feeQrSnap.includes('Tài chính tổng hợp') || feeQrSnap.includes('Tổng kết buổi')) {
      throw new Error('Forbidden summary or aggregate finance visible in Guest A fee screen');
    }

    const hasDue = /Phải trả:?\s*100,000\s*VNĐ(?!\d)/.test(feeQrSnap);
    const hasPaid = /Đã trả:?\s*0\s*VNĐ(?!\d)/.test(feeQrSnap);
    const hasOutstanding = /Còn lại:?\s*100,000\s*VNĐ(?!\d)/.test(feeQrSnap);
    if (!hasDue || !hasPaid || !hasOutstanding) {
      throw new Error('Guest A own-fee mismatch: expected due=100000, paid=0, outstanding=100000');
    }

    if (routeAbortCount < 1) {
      throw new Error('Expected at least one aborted https://img.vietqr.io/** request');
    }

    const bankRe = new RegExp(`Ngân hàng\\s+${escapeRegex(EXPECTED_RECEIVER.bank_code)}\\s+Số tài khoản`);
    const acctRe = new RegExp(`Số tài khoản\\s+${escapeRegex(EXPECTED_RECEIVER.account_number)}\\s+Chủ tài khoản`);
    const nameRe = new RegExp(`Chủ tài khoản\\s+${escapeRegex(EXPECTED_RECEIVER.account_name)}\\s+Số tiền`);
    const amountRe = /Số tiền\s+100,000\s+VNĐ\s+Nội dung/;
    const refRe = new RegExp(`Nội dung\\s+${escapeRegex(EXPECTED_RECEIVER.reference)}\\s+Mã QR chỉ là hướng dẫn`);
    if (
      !bankRe.test(feeQrSnap) ||
      !acctRe.test(feeQrSnap) ||
      !nameRe.test(feeQrSnap) ||
      !amountRe.test(feeQrSnap) ||
      !refRe.test(feeQrSnap)
    ) {
      throw new Error('Guest A manual transfer fields did not match expected receiver details');
    }

    // Verify submit CTA exists without clicking it (read-only test)
    const submitPaymentBtn = page.getByRole('button', { name: 'Tôi đã chuyển khoản', exact: true });
    await submitPaymentBtn.waitFor({ state: 'visible', timeout: 5000 });

    if (clipboardGranted) {
      const copyAcctBtn = page.getByRole('button', { name: 'Sao chép Số tài khoản', exact: true });
      await copyAcctBtn.waitFor({ state: 'visible', timeout: 10000 });
      await copyAcctBtn.click();

      await waitForSnapshot(
        snap => snap.includes('Đã sao chép Số tài khoản'),
        'Snackbar "Đã sao chép Số tài khoản" not found after click'
      );
      const copiedAccount = await readClipboardOrThrow();
      if (copiedAccount !== EXPECTED_RECEIVER.account_number) {
        throw new Error('Clipboard mismatch: copied account number does not equal expected value');
      }

      const copyRefBtn = page.getByRole('button', { name: 'Sao chép Nội dung', exact: true });
      await copyRefBtn.waitFor({ state: 'visible', timeout: 10000 });
      await copyRefBtn.click();

      await waitForSnapshot(
        snap => snap.includes('Đã sao chép Nội dung'),
        'Snackbar "Đã sao chép Nội dung" not found after click'
      );
      const copiedReference = await readClipboardOrThrow();
      if (copiedReference !== EXPECTED_RECEIVER.reference) {
        throw new Error('Clipboard mismatch: copied payment reference does not equal expected value');
      }

      clipboardResult = {
        status: 'PASS',
        reason: null,
        account_number_verified: true,
        reference_verified: true,
      };
    } else {
      clipboardResult = {
        status: 'NOT_RUN',
        reason: CLIPBOARD_UNSUPPORTED_REASON,
        account_number_verified: false,
        reference_verified: false,
      };
    }

    qrResult = {
      fallback_verified: true,
      expected_info_matched: true,
      manual_notice_verified: true,
      payment_not_submitted: true,
      abort_count: routeAbortCount,
    };
    feeResult = {
      verified: true,
      due: 100000,
      paid: 0,
      outstanding: 100000,
      management_summary_absent: true,
    };

    return {
      ok: true,
      mode: MODE,
      url_origin: expectedBase.origin,
      session_id: SESSION_ID,
      qr: qrResult,
      fee: feeResult,
      clipboard: clipboardResult,
      recorded_console_summary: consoleSummary,
    };
  } finally {
    const cleanupFailures = [];
    try {
      await context.setOffline(false);
    } catch (_) {
      cleanupFailures.push('setOffline(false)');
    }
    if (permissionsAttempted) {
      try {
        await context.clearPermissions();
      } catch (_) {
        cleanupFailures.push('clearPermissions()');
      }
    }
    if (vietqrRouteInstalled) {
      try {
        await page.unroute(VIETQR_ROUTE_PATTERN, vietqrRouteHandler);
      } catch (_) {
        cleanupFailures.push('unroute(vietqr)');
      }
    }
    try {
      page.off('console', onConsole);
      page.off('pageerror', onPageError);
    } catch (_) {
      cleanupFailures.push('removeListeners');
    }
    if (cleanupFailures.length > 0) {
      throw new Error(`Cleanup failed: ${cleanupFailures.join(', ')}`);
    }
  }
}