async page => {
  // Configuration constants (Codex substitutes only these declarations in ignored driver copies)
  const SESSION_ID = '__BH07_SESSION_ID__';
  const GUEST_PLAYER_ID = '__BH07_PLAYER_ID__';
  const PAYMENT_ID = null;
  const PHASE = 'submit';
  const EXPECTED_AMOUNT = 100000;

  const TITLE = 'BH07 V2 isolated payment';
  const BASE_URL = 'http://127.0.0.1:8088';
  const API_ORIGIN = 'http://127.0.0.1:54321';
  const SUBMIT_PATH = '/rest/v1/rpc/submit_payment';
  const CONFIRM_PATH = '/rest/v1/rpc/confirm_payment';
  const MUTATION_PATHS = new Set([
    SUBMIT_PATH,
    CONFIRM_PATH,
    '/rest/v1/rpc/record_cash_payment',
    '/rest/v1/rpc/reject_payment',
    '/rest/v1/rpc/reverse_payment',
  ]);
  const GUEST_EMAIL = 'guesta@example.test';
  const OWNER_EMAIL = 'ownera@example.test';
  const PASSWORD = 'bh07-http-pass-123456';
  const VIETQR_ROUTE_PATTERN = 'https://img.vietqr.io/**';
  const QR_FALLBACK_TEXT = 'Không tải được ảnh QR. Dùng thông tin bên dưới để chuyển khoản.';
  const QR_MANUAL_NOTICE =
    'Mã QR chỉ là hướng dẫn chuyển khoản, KHÔNG tự xác nhận đã thu. Ban quản lý xác nhận thủ công sau khi nhận tiền.';
  const SUBMIT_SUCCESS_TEXT = 'Đã ghi nhận, chờ ban quản lý xác nhận.';
  const CONFIRM_SUCCESS_TEXT = 'Đã xác nhận thanh toán.';
  const TOTAL_EXPECTED_EXPENSE = 200000;
  const TOTAL_EXPECTED_DUE = 200000;
  const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

  // Validate configuration constants via regex/type checks before any browser interaction
  if (typeof SESSION_ID !== 'string' || !UUID_RE.test(SESSION_ID)) {
    throw new Error('Guard failed: SESSION_ID must be a valid UUID');
  }
  if (typeof GUEST_PLAYER_ID !== 'string' || !UUID_RE.test(GUEST_PLAYER_ID)) {
    throw new Error('Guard failed: GUEST_PLAYER_ID must be a valid UUID');
  }
  if (PHASE !== 'submit' && PHASE !== 'confirm' && PHASE !== 'verify_guest') {
    throw new Error('Guard failed: PHASE must be submit, confirm, or verify_guest');
  }
  if (PHASE === 'confirm') {
    if (typeof PAYMENT_ID !== 'string' || !UUID_RE.test(PAYMENT_ID)) {
      throw new Error('Guard failed: PAYMENT_ID must be a valid UUID in confirm phase');
    }
  } else if (PAYMENT_ID !== null && (typeof PAYMENT_ID !== 'string' || !UUID_RE.test(PAYMENT_ID))) {
    throw new Error('Guard failed: PAYMENT_ID must be null or a valid UUID');
  }
  if (typeof EXPECTED_AMOUNT !== 'number' || !Number.isSafeInteger(EXPECTED_AMOUNT) || EXPECTED_AMOUNT <= 0) {
    throw new Error('Guard failed: EXPECTED_AMOUNT must be a positive integer');
  }
  if (typeof TITLE !== 'string' || TITLE.trim().length === 0) {
    throw new Error('Guard failed: TITLE must be a non-empty string');
  }

  const expectedBase = new URL(BASE_URL);
  if (expectedBase.origin !== 'http://127.0.0.1:8088') {
    throw new Error('Guard failed: BASE_URL origin must be exactly http://127.0.0.1:8088');
  }
  const SESSION_URL = `${expectedBase.origin}/#/sessions/${SESSION_ID}`;

  // Guard initial page origin before attaching listeners or interacting
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

  let vietqrRouteInstalled = false;
  let routeAbortCount = 0;
  const vietqrRouteHandler = async route => {
    routeAbortCount++;
    await route.abort();
  };

  function isPlainObject(value) {
    return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
  }

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

  // Capture ALL requests to target payment endpoints without silently skipping mismatches
  const capturedSubmitRequests = [];
  const capturedConfirmRequests = [];
  const captureErrors = [];
  const unexpectedMutationPaths = [];

  const onRequest = req => {
    let parsedUrl;
    try {
      parsedUrl = new URL(req.url());
    } catch (_) {
      return;
    }
    if (parsedUrl.origin !== API_ORIGIN || !MUTATION_PATHS.has(parsedUrl.pathname)) {
      return;
    }
    const method = req.method();
    if (method === 'OPTIONS') {
      return;
    }
    if (method !== 'POST') {
      captureErrors.push(`Unexpected HTTP method on ${parsedUrl.pathname}`);
      return;
    }
    if (PHASE === 'submit' && parsedUrl.pathname === SUBMIT_PATH) {
      const parsed = parseStrictJsonBody(req.postData());
      if (!parsed.ok) {
        captureErrors.push('Malformed JSON body in submit_payment POST');
        return;
      }
      capturedSubmitRequests.push({ req, body: parsed.body });
      return;
    }
    if (PHASE === 'confirm' && parsedUrl.pathname === CONFIRM_PATH) {
      const parsed = parseStrictJsonBody(req.postData());
      if (!parsed.ok) {
        captureErrors.push('Malformed JSON body in confirm_payment POST');
        return;
      }
      capturedConfirmRequests.push({ req, body: parsed.body });
      return;
    }
    unexpectedMutationPaths.push(parsedUrl.pathname);
  };
  page.on('request', onRequest);

  function escapeRegex(value) {
    return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  }

  function formatVnd(amount) {
    return `${amount.toLocaleString('en-US')} VNĐ`;
  }

  function hasExactMoneyLabel(snap, label, amount) {
    const formatted = escapeRegex(amount.toLocaleString('en-US'));
    const re = new RegExp(`${escapeRegex(label)}(?::|\\s)\\s*(?<!\\d)${formatted}(?!\\d)\\s*VNĐ`);
    return re.test(snap);
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
      placeholder.waitFor({ state: 'attached', timeout: 5000 }).catch(() => {}),
      accountTab.waitFor({ state: 'visible', timeout: 5000 }).catch(() => {}),
      detailHeading.waitFor({ state: 'visible', timeout: 5000 }).catch(() => {}),
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
    await page.goto(`${expectedBase.origin}/#/`);
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

  function validateSubmitRequestBody(body) {
    const keys = Object.keys(body).sort();
    const expectedKeys = ['p_amount_vnd', 'p_method', 'p_player_id', 'p_reference', 'p_request_id'];
    if (keys.length !== expectedKeys.length || keys.some((k, idx) => k !== expectedKeys[idx])) {
      throw new Error('submit_payment request body keys mismatch');
    }
    if (body.p_player_id !== GUEST_PLAYER_ID) {
      throw new Error('submit_payment p_player_id mismatch');
    }
    if (body.p_amount_vnd !== EXPECTED_AMOUNT) {
      throw new Error('submit_payment p_amount_vnd mismatch');
    }
    if (body.p_method !== 'bank_transfer') {
      throw new Error('submit_payment p_method must equal bank_transfer');
    }
    if (body.p_reference !== null) {
      throw new Error('submit_payment p_reference must be null');
    }
    if (typeof body.p_request_id !== 'string' || !UUID_RE.test(body.p_request_id)) {
      throw new Error('submit_payment p_request_id must be a valid UUID');
    }
    return {
      p_player_id: body.p_player_id,
      p_amount_vnd: body.p_amount_vnd,
      p_method: body.p_method,
      p_reference: null,
      p_request_id: body.p_request_id,
    };
  }

  function validateConfirmRequestBody(body) {
    const keys = Object.keys(body).sort();
    const expectedKeys = ['p_payment_id', 'p_request_id'];
    if (keys.length !== expectedKeys.length || keys.some((k, idx) => k !== expectedKeys[idx])) {
      throw new Error('confirm_payment request body keys mismatch');
    }
    if (body.p_payment_id !== PAYMENT_ID) {
      throw new Error('confirm_payment p_payment_id mismatch');
    }
    if (typeof body.p_request_id !== 'string' || !UUID_RE.test(body.p_request_id)) {
      throw new Error('confirm_payment p_request_id must be a valid UUID');
    }
    return {
      p_payment_id: body.p_payment_id,
      p_request_id: body.p_request_id,
    };
  }

  try {
    if (PHASE === 'submit') {
      await bootstrapFreshGuestAndLogin(GUEST_EMAIL, GUEST_EMAIL);

      // Abort ONLY external VietQR image requests while preserving local API untouched
      await page.route(VIETQR_ROUTE_PATTERN, vietqrRouteHandler);
      vietqrRouteInstalled = true;

      await page.goto(SESSION_URL);
      assertLoopbackOrigin();
      await enableAccessibility();

      const detailSnap = await waitForSnapshot(
        s => s.includes('Chi tiết buổi chơi') && s.includes(TITLE) && s.includes('Phần phí của tôi'),
        'Guest session detail missing title or "Phần phí của tôi"'
      );
      if (
        detailSnap.includes('Tổng kết buổi') ||
        detailSnap.includes('Tài chính & thu tiền') ||
        detailSnap.includes('Tài chính tổng hợp') ||
        detailSnap.includes('Danh sách đăng ký')
      ) {
        throw new Error('Forbidden management or summary visible in Guest session detail');
      }

      const ownFeeBtn = page.getByRole('button', { name: /^Phần phí của tôi/ });
      await ownFeeBtn.waitFor({ state: 'visible', timeout: 10000 });
      await ownFeeBtn.click();

      const preSubmitSnap = await waitForSnapshot(
        async s => {
          if (s.includes('Phần phí của bạn') && !s.includes(QR_MANUAL_NOTICE)) {
            await page.mouse.move(400, 400);
            await page.mouse.wheel(0, 400);
          }
          return (
            s.includes('Tài chính buổi') &&
            s.includes('Phần phí của bạn') &&
            s.includes('Đang hiệu lực') &&
            s.includes('Chuyển khoản để thanh toán') &&
            s.includes(QR_FALLBACK_TEXT) &&
            s.includes(QR_MANUAL_NOTICE)
          );
        },
        'Guest own-fee screen missing fee summary, QR fallback, or manual notice'
      );
      if (
        preSubmitSnap.includes('Tài chính tổng hợp') ||
        preSubmitSnap.includes('Tổng kết buổi') ||
        preSubmitSnap.includes('Khoản phải thu theo người')
      ) {
        throw new Error('Forbidden management or summary visible in Guest own-fee screen');
      }
      if (
        !hasExactMoneyLabel(preSubmitSnap, 'Phải trả', EXPECTED_AMOUNT) ||
        !hasExactMoneyLabel(preSubmitSnap, 'Đã trả', 0) ||
        !hasExactMoneyLabel(preSubmitSnap, 'Còn lại', EXPECTED_AMOUNT)
      ) {
        throw new Error('Guest own-fee mismatch before submit');
      }
      if (routeAbortCount < 1) {
        throw new Error('Expected at least one aborted https://img.vietqr.io/** request');
      }

      const submitPaymentBtn = page.getByRole('button', { name: 'Tôi đã chuyển khoản', exact: true });
      await submitPaymentBtn.waitFor({ state: 'visible', timeout: 10000 });
      await submitPaymentBtn.scrollIntoViewIfNeeded();
      await submitPaymentBtn.click();

      await waitForSnapshot(
        s => s.includes('Xác nhận đã chuyển khoản'),
        'Confirmation dialog "Xác nhận đã chuyển khoản" did not appear'
      );
      const confirmDialogBtn = page.getByRole('button', { name: 'Đồng ý', exact: true });
      await confirmDialogBtn.waitFor({ state: 'visible', timeout: 10000 });

      if (capturedSubmitRequests.length !== 0 || captureErrors.length > 0 || unexpectedMutationPaths.length > 0) {
        throw new Error('submit_payment or unexpected mutation fired before dialog confirmation');
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
        if (parsedUrl.origin !== API_ORIGIN || parsedUrl.pathname !== SUBMIT_PATH) {
          return false;
        }
        return capturedSubmitRequests.some(item => item.req === req);
      }, { timeout: 20000 });

      const [rpcResponse] = await Promise.all([
        responsePromise,
        confirmDialogBtn.click(),
      ]);

      const rpcStatus = rpcResponse.status();
      if (rpcStatus !== 200) {
        throw new Error(`Expected submit_payment HTTP 200, got ${rpcStatus}`);
      }
      if (captureErrors.length > 0 || unexpectedMutationPaths.length > 0) {
        throw new Error('Invalid or unexpected payment mutation captured during submit phase');
      }
      if (capturedSubmitRequests.length !== 1) {
        throw new Error(`Expected exactly 1 submit_payment POST, got ${capturedSubmitRequests.length}`);
      }

      const safeRequestPayload = validateSubmitRequestBody(capturedSubmitRequests[0].body);

      let resJson;
      try {
        resJson = await rpcResponse.json();
      } catch (_) {
        throw new Error('submit_payment response was not valid JSON');
      }
      if (!isPlainObject(resJson)) {
        throw new Error('submit_payment response must be a JSON object');
      }
      if (typeof resJson.payment_id !== 'string' || !UUID_RE.test(resJson.payment_id)) {
        throw new Error('submit_payment response missing valid payment_id UUID');
      }
      if (resJson.player_id !== GUEST_PLAYER_ID) {
        throw new Error('submit_payment response player_id mismatch');
      }
      if (resJson.session_id !== SESSION_ID) {
        throw new Error('submit_payment response session_id mismatch');
      }
      if (resJson.amount_vnd !== EXPECTED_AMOUNT) {
        throw new Error('submit_payment response amount_vnd mismatch');
      }
      if (resJson.status !== 'submitted') {
        throw new Error('submit_payment response status must be submitted');
      }

      const postSubmitSnap = await waitForSnapshot(
        s => s.includes(SUBMIT_SUCCESS_TEXT) && s.includes('Phần phí của bạn'),
        'Expected submit_payment success snackbar did not appear'
      );
      if (postSubmitSnap.includes('Bạn đã trả đủ.')) {
        throw new Error('Submitted payment must not mark player fee as paid in full');
      }
      if (
        !hasExactMoneyLabel(postSubmitSnap, 'Phải trả', EXPECTED_AMOUNT) ||
        !hasExactMoneyLabel(postSubmitSnap, 'Đã trả', 0) ||
        !hasExactMoneyLabel(postSubmitSnap, 'Còn lại', EXPECTED_AMOUNT)
      ) {
        throw new Error('Submitted payment erroneously altered paid/outstanding amounts');
      }

      return {
        ok: true,
        phase: PHASE,
        session_id: SESSION_ID,
        submission_ui_verified: true,
        submitted_not_counted_paid: true,
        attempts: capturedSubmitRequests.length,
        rpc_status: rpcStatus,
        payment_id: resJson.payment_id,
        responseId: resJson.payment_id,
        request_payload: safeRequestPayload,
        recorded_console_summary: consoleSummary,
      };
    }

    if (PHASE === 'confirm') {
      await bootstrapFreshGuestAndLogin(OWNER_EMAIL, OWNER_EMAIL);

      await page.goto(SESSION_URL);
      assertLoopbackOrigin();
      await enableAccessibility();

      await waitForSnapshot(
        s => s.includes('Chi tiết buổi chơi') && s.includes(TITLE) && s.includes('Tài chính & thu tiền'),
        'Owner session detail missing title or "Tài chính & thu tiền"'
      );

      const financeTile = page.getByRole('button', { name: /Tài chính & thu tiền/ });
      await financeTile.waitFor({ state: 'visible', timeout: 10000 });
      await financeTile.scrollIntoViewIfNeeded();
      await financeTile.click();

      const financeSnap = await waitForSnapshot(
        async s => {
          if (
            s.includes('Tài chính buổi') &&
            s.includes('Đang hiệu lực') &&
            !s.includes('Chờ xác nhận') &&
            !s.includes('Chưa có thanh toán.')
          ) {
            await page.mouse.move(400, 400);
            await page.mouse.wheel(0, 600);
          }
          return (
            s.includes('Tài chính buổi') &&
            s.includes('Trạng thái phí') &&
            s.includes('Đang hiệu lực') &&
            s.includes('Thanh toán') &&
            (s.includes('Chờ xác nhận') || s.includes('Chưa có thanh toán.'))
          );
        },
        'Owner finance screen missing current billing or payment section'
      );
      if (financeSnap.includes('Chưa có thanh toán.')) {
        throw new Error('Owner finance screen unexpectedly shows no payments before confirm');
      }

      const paymentsStart = financeSnap.indexOf('Thanh toán');
      const paymentsSlice = paymentsStart >= 0 ? financeSnap.slice(paymentsStart) : financeSnap;
      const paymentEntries = paymentsSlice.match(/VNĐ\s+—\s+/g) || [];
      if (paymentEntries.length !== 1) {
        throw new Error(`Expected exactly 1 payment entry in Thanh toán section, found ${paymentEntries.length}`);
      }

      const expectedAmountText = formatVnd(EXPECTED_AMOUNT);
      const pendingRowRe = new RegExp(
        `^${escapeRegex(expectedAmountText)}\\s+—\\s+bank_transfer\\s+Chờ xác nhận(?:\\s|•|$)`
      );
      const pendingRows = page.getByRole('group', { name: pendingRowRe });
      const pendingRowCount = await pendingRows.count();
      if (pendingRowCount !== 1) {
        throw new Error(`Expected exactly 1 pending payment row group, found ${pendingRowCount}`);
      }
      const allConfirmBtns = page.getByRole('button', { name: 'Xác nhận', exact: true });
      if (await allConfirmBtns.count() !== 1) {
        throw new Error('Expected exactly 1 "Xác nhận" button on finance screen');
      }

      const rowConfirmBtn = pendingRows.getByRole('button', { name: 'Xác nhận', exact: true });
      if (await rowConfirmBtn.count() !== 1) {
        throw new Error('Expected exactly 1 row-scoped "Xác nhận" button');
      }
      await rowConfirmBtn.scrollIntoViewIfNeeded();
      if (!await rowConfirmBtn.isVisible() || !await rowConfirmBtn.isEnabled()) {
        throw new Error('Row-scoped "Xác nhận" button is not visible/enabled');
      }
      await rowConfirmBtn.click();

      await waitForSnapshot(
        s => s.includes('Xác nhận thanh toán'),
        'Confirmation dialog "Xác nhận thanh toán" did not appear'
      );
      const confirmDialogBtn = page.getByRole('button', { name: 'Đồng ý', exact: true });
      await confirmDialogBtn.waitFor({ state: 'visible', timeout: 10000 });

      if (capturedConfirmRequests.length !== 0 || captureErrors.length > 0 || unexpectedMutationPaths.length > 0) {
        throw new Error('confirm_payment or unexpected mutation fired before dialog confirmation');
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
        if (parsedUrl.origin !== API_ORIGIN || parsedUrl.pathname !== CONFIRM_PATH) {
          return false;
        }
        return capturedConfirmRequests.some(item => item.req === req);
      }, { timeout: 20000 });

      const [rpcResponse] = await Promise.all([
        responsePromise,
        confirmDialogBtn.click(),
      ]);

      const rpcStatus = rpcResponse.status();
      if (rpcStatus !== 200) {
        throw new Error(`Expected confirm_payment HTTP 200, got ${rpcStatus}`);
      }
      if (captureErrors.length > 0 || unexpectedMutationPaths.length > 0) {
        throw new Error('Invalid or unexpected payment mutation captured during confirm phase');
      }
      if (capturedConfirmRequests.length !== 1) {
        throw new Error(`Expected exactly 1 confirm_payment POST, got ${capturedConfirmRequests.length}`);
      }

      const safeRequestPayload = validateConfirmRequestBody(capturedConfirmRequests[0].body);

      let resJson;
      try {
        resJson = await rpcResponse.json();
      } catch (_) {
        throw new Error('confirm_payment response was not valid JSON');
      }
      if (!isPlainObject(resJson)) {
        throw new Error('confirm_payment response must be a JSON object');
      }
      if (resJson.payment_id !== PAYMENT_ID) {
        throw new Error('confirm_payment response payment_id mismatch');
      }
      if (resJson.session_id !== SESSION_ID) {
        throw new Error('confirm_payment response session_id mismatch');
      }
      if (resJson.player_id !== GUEST_PLAYER_ID) {
        throw new Error('confirm_payment response player_id mismatch');
      }
      if (resJson.amount_vnd !== EXPECTED_AMOUNT) {
        throw new Error('confirm_payment response amount_vnd mismatch');
      }
      if (resJson.status !== 'confirmed') {
        throw new Error('confirm_payment response status must be confirmed');
      }
      if (typeof resJson.ledger_id !== 'string' || !UUID_RE.test(resJson.ledger_id)) {
        throw new Error('confirm_payment response missing valid ledger_id UUID');
      }

      const expectedRemainingTotal = TOTAL_EXPECTED_DUE - EXPECTED_AMOUNT;
      const postConfirmSnap = await waitForSnapshot(
        s =>
          s.includes(CONFIRM_SUCCESS_TEXT) &&
          s.includes('Tài chính buổi') &&
          !s.includes('Chờ xác nhận') &&
          s.includes('Đã xác nhận'),
        'Expected confirm_payment success snackbar or confirmed row status missing'
      );
      if (!hasExactMoneyLabel(postConfirmSnap, 'Tổng còn phải thu', expectedRemainingTotal)) {
        throw new Error('Finance screen total outstanding mismatch after payment confirmation');
      }
      const confirmedRowRe = new RegExp(
        `^${escapeRegex(expectedAmountText)}\\s+—\\s+bank_transfer\\s+Đã xác nhận(?:\\s|•|$)`
      );
      if (await page.getByRole('group', { name: confirmedRowRe }).count() !== 1) {
        throw new Error('Confirmed payment row group not uniquely found after confirmation');
      }
      if (await page.getByRole('button', { name: 'Xác nhận', exact: true }).count() !== 0) {
        throw new Error('Confirm button remained visible after payment confirmation');
      }

      // Navigate Back to session detail and open summary
      const backBtn = page.getByRole('button', { name: 'Back' }).first();
      await backBtn.waitFor({ state: 'visible', timeout: 10000 });
      await backBtn.click();

      await waitForSnapshot(
        s => s.includes('Chi tiết buổi chơi') && s.includes(TITLE) && s.includes('Tổng kết buổi'),
        'Session detail screen or "Tổng kết buổi" missing after Back navigation'
      );

      const summaryBtn = page.getByRole('button', { name: /^Tổng kết buổi/ });
      await summaryBtn.waitFor({ state: 'visible', timeout: 10000 });
      await summaryBtn.click();

      const summarySnap = await waitForSnapshot(
        s =>
          s.includes('Tổng kết buổi') &&
          s.includes(TITLE) &&
          s.includes('Đã kết thúc') &&
          s.includes('Tài chính tổng hợp'),
        'Owner summary screen or "Tài chính tổng hợp" missing'
      );

      const hasPresent = /(?:Có mặt|Có mặt:)\s+2(?!\d)/.test(summarySnap);
      const hasAbsent = /(?:Vắng|Vắng:)\s+0(?!\d)/.test(summarySnap);
      const hasConfirmed = /(?:Đã xác nhận|Đã xác nhận:)\s+2(?!\d)/.test(summarySnap);
      if (!hasPresent || !hasAbsent || !hasConfirmed) {
        throw new Error('Owner summary attendance counts mismatch (expected 2/0/2)');
      }

      if (
        !hasExactMoneyLabel(summarySnap, 'Tổng chi phí', TOTAL_EXPECTED_EXPENSE) ||
        !hasExactMoneyLabel(summarySnap, 'Tổng phải thu', TOTAL_EXPECTED_DUE) ||
        !hasExactMoneyLabel(summarySnap, 'Đã thu', EXPECTED_AMOUNT) ||
        !hasExactMoneyLabel(summarySnap, 'Còn phải thu', expectedRemainingTotal)
      ) {
        throw new Error('Owner summary finance aggregates mismatch after payment confirmation');
      }

      return {
        ok: true,
        phase: PHASE,
        session_id: SESSION_ID,
        confirmation_ui_verified: true,
        summary_verified: true,
        attempts: capturedConfirmRequests.length,
        rpc_status: rpcStatus,
        payment_id: resJson.payment_id,
        ledger_id: resJson.ledger_id,
        request_payload: safeRequestPayload,
        recorded_console_summary: consoleSummary,
      };
    }

    // PHASE === 'verify_guest'
    await bootstrapFreshGuestAndLogin(GUEST_EMAIL, GUEST_EMAIL);

    // Abort ONLY external VietQR image requests; expect 0 aborts when paid in full
    await page.route(VIETQR_ROUTE_PATTERN, vietqrRouteHandler);
    vietqrRouteInstalled = true;

    await page.goto(SESSION_URL);
    assertLoopbackOrigin();
    await enableAccessibility();

    const guestDetailSnap = await waitForSnapshot(
      s => s.includes('Chi tiết buổi chơi') && s.includes(TITLE) && s.includes('Phần phí của tôi'),
      'Guest session detail missing title or "Phần phí của tôi" in verify_guest'
    );
    if (
      guestDetailSnap.includes('Tổng kết buổi') ||
      guestDetailSnap.includes('Tài chính & thu tiền') ||
      guestDetailSnap.includes('Tài chính tổng hợp') ||
      guestDetailSnap.includes('Danh sách đăng ký')
    ) {
      throw new Error('Forbidden management or summary visible in Guest session detail');
    }

    const ownFeeBtn = page.getByRole('button', { name: /^Phần phí của tôi/ });
    await ownFeeBtn.waitFor({ state: 'visible', timeout: 10000 });
    await ownFeeBtn.click();

    const feeSnap = await waitForSnapshot(
      s => s.includes('Tài chính buổi') && s.includes('Phần phí của bạn') && s.includes('Bạn đã trả đủ.'),
      'Guest own-fee screen missing paid-in-full state "Bạn đã trả đủ."'
    );

    if (
      !hasExactMoneyLabel(feeSnap, 'Phải trả', EXPECTED_AMOUNT) ||
      !hasExactMoneyLabel(feeSnap, 'Đã trả', EXPECTED_AMOUNT) ||
      !hasExactMoneyLabel(feeSnap, 'Còn lại', 0)
    ) {
      throw new Error('Guest own-fee mismatch after confirmation: expected due=100000, paid=100000, outstanding=0');
    }

    if (
      feeSnap.includes('Tôi đã chuyển khoản') ||
      await page.getByRole('button', { name: 'Tôi đã chuyển khoản' }).count() !== 0
    ) {
      throw new Error('Unexpected "Tôi đã chuyển khoản" button visible after payment confirmation');
    }

    const forbiddenQrTokens = [
      'Chuyển khoản để thanh toán',
      'Ngân hàng',
      'Số tài khoản',
      'Chủ tài khoản',
      'Nội dung',
      'Mã QR chỉ là hướng dẫn',
    ];
    if (forbiddenQrTokens.some(token => feeSnap.includes(token))) {
      throw new Error('Unexpected QR transfer section visible when Guest fee is paid in full');
    }

    const forbiddenManagementTokens = [
      'Tài chính tổng hợp',
      'Tổng kết buổi',
      'Khoản phải thu theo người',
      'Chốt lại phí',
      'Xác nhận',
    ];
    if (forbiddenManagementTokens.some(token => feeSnap.includes(token))) {
      throw new Error('Forbidden management or summary visible in Guest verify_guest screen');
    }

    if (routeAbortCount !== 0) {
      throw new Error('Unexpected VietQR network request attempted when Guest outstanding is 0');
    }
    if (captureErrors.length > 0 || unexpectedMutationPaths.length > 0) {
      throw new Error('Unexpected payment mutation occurred during verify_guest phase');
    }

    return {
      ok: true,
      phase: PHASE,
      session_id: SESSION_ID,
      guest_verified: true,
      management_absent: true,
      submit_button_absent: true,
      qr_section_absent: true,
      no_mutation_performed: true,
      expected_fees: {
        due_vnd: EXPECTED_AMOUNT,
        paid_vnd: EXPECTED_AMOUNT,
        outstanding_vnd: 0,
      },
      recorded_console_summary: consoleSummary,
    };
  } finally {
    const cleanupFailures = [];
    try {
      await context.setOffline(false);
    } catch (_) {
      cleanupFailures.push('setOffline(false)');
    }
    if (vietqrRouteInstalled) {
      try {
        await page.unroute(VIETQR_ROUTE_PATTERN, vietqrRouteHandler);
      } catch (_) {
        cleanupFailures.push('unroute(vietqr)');
      }
    }
    try {
      page.off('request', onRequest);
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