async page => {
  // Configuration constants (Codex may substitute FOCUS_MODE / RENDER_MODE in ignored driver copies)
  const FOCUS_MODE = 'baseline';
  const RENDER_MODE = 'default';

  const BASE_URL = 'http://127.0.0.1:8088';
  const API_ORIGIN = 'http://127.0.0.1:54321';
  const SYNTHETIC_EMAIL = 'probe-synthetic@example.invalid';
  const SYNTHETIC_PASS = 'synthetic-probe-pass';
  const ACTION_TIMEOUT_MS = 10000;
  const BOOTSTRAP_TIMEOUT_MS = 20000;
  const RAF_TIMEOUT_MS = 5000;
  const MAX_EVENT_COUNT = 10000;

  const SCREENSHOT_PATHS = {
    default: {
      baseline: {
        home: '.build/bh07-firefox-headed-input/default-baseline-home.png',
        login: '.build/bh07-firefox-headed-input/default-baseline-login-synthetic.png',
        failure: '.build/bh07-firefox-headed-input/default-baseline-failure.png',
      },
      bring_to_front: {
        home: '.build/bh07-firefox-headed-input/default-bring_to_front-home.png',
        login: '.build/bh07-firefox-headed-input/default-bring_to_front-login-synthetic.png',
        failure: '.build/bh07-firefox-headed-input/default-bring_to_front-failure.png',
      },
    },
    software: {
      baseline: {
        home: '.build/bh07-firefox-headed-input/software-baseline-home.png',
        login: '.build/bh07-firefox-headed-input/software-baseline-login-synthetic.png',
        failure: '.build/bh07-firefox-headed-input/software-baseline-failure.png',
      },
      bring_to_front: {
        home: '.build/bh07-firefox-headed-input/software-bring_to_front-home.png',
        login: '.build/bh07-firefox-headed-input/software-bring_to_front-login-synthetic.png',
        failure: '.build/bh07-firefox-headed-input/software-bring_to_front-failure.png',
      },
    },
  };

  // Validate configuration constants before any browser interaction
  if (FOCUS_MODE !== 'baseline' && FOCUS_MODE !== 'bring_to_front') {
    throw new Error('Guard failed: FOCUS_MODE must be baseline or bring_to_front');
  }
  if (RENDER_MODE !== 'default' && RENDER_MODE !== 'software') {
    throw new Error('Guard failed: RENDER_MODE must be default or software');
  }
  const expectedBase = new URL(BASE_URL);
  if (expectedBase.origin !== 'http://127.0.0.1:8088') {
    throw new Error('Guard failed: BASE_URL origin must be http://127.0.0.1:8088');
  }
  const caseShots = SCREENSHOT_PATHS[RENDER_MODE][FOCUS_MODE];

  // Guard initial page origin before attaching listeners or navigating
  const initialUrl = page.url();
  if (initialUrl !== 'about:blank') {
    let initialOrigin = '';
    try {
      initialOrigin = new URL(initialUrl).origin;
    } catch (_) {
      throw new Error('Guard failed: invalid initial page URL');
    }
    if (initialOrigin !== expectedBase.origin) {
      throw new Error('Guard failed: initial page origin must be about:blank or http://127.0.0.1:8088');
    }
  }

  // Guard Firefox browser and reject explicit Headless UA strings (headed provenance requires explicit runner launch config)
  const context = typeof page.context === 'function' ? page.context() : null;
  const browser = context && typeof context.browser === 'function' ? context.browser() : null;
  const browserType = browser && typeof browser.browserType === 'function' ? browser.browserType() : null;
  const browserName = browserType && typeof browserType.name === 'function' ? String(browserType.name() || '') : '';
  if (browserName && browserName !== 'firefox') {
    throw new Error('Guard failed: Firefox browser required');
  }
  const userAgent = await page.evaluate(() =>
    typeof navigator === 'object' && navigator ? String(navigator.userAgent || '') : ''
  );
  if (!/Firefox\/\d+/i.test(userAgent) || /Headless|Chrome\/|Chromium\/|Edg\//i.test(userAgent)) {
    throw new Error('Guard failed: Firefox browser required');
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

  // Numeric console/pageerror and non-mutation network guards (never store raw text, URLs, or payloads)
  const consoleSummary = {
    error_count: 0,
    warning_count: 0,
    pageerror_count: 0,
  };
  const onConsole = msg => {
    const type = msg.type();
    if (type === 'error') {
      consoleSummary.error_count++;
    } else if (type === 'warning') {
      consoleSummary.warning_count++;
    }
  };
  const onPageError = () => {
    consoleSummary.pageerror_count++;
  };

  // Grounded in lib/main.dart, home_screen.dart, account_screen.dart, auth_screen.dart:
  // Guest home -> Account -> AuthScreen (before submit) triggers zero read RPCs.
  const ALLOWED_READ_RPC_PATHS = new Set();

  let authOrMutationRequestCount = 0;
  const onRequest = req => {
    const method = String(req.method() || '').toUpperCase();
    if (method === 'GET' || method === 'HEAD' || method === 'OPTIONS') {
      return;
    }
    let parsedUrl;
    try {
      parsedUrl = new URL(req.url());
    } catch (_) {
      authOrMutationRequestCount++;
      return;
    }
    const isAllowedReadRpc =
      method === 'POST' &&
      parsedUrl.origin === API_ORIGIN &&
      ALLOWED_READ_RPC_PATHS.has(parsedUrl.pathname);
    if (!isAllowedReadRpc) {
      authOrMutationRequestCount++;
    }
  };

  page.on('console', onConsole);
  page.on('pageerror', onPageError);
  page.on('request', onRequest);

  const probeStartMs = Date.now();
  const elapsedMs = () => Math.max(0, Date.now() - probeStartMs);

  const ZERO_COUNTERS = {
    pointerdown_trusted: 0,
    pointerdown_untrusted: 0,
    pointerup_trusted: 0,
    pointerup_untrusted: 0,
    mousedown_trusted: 0,
    mousedown_untrusted: 0,
    mouseup_trusted: 0,
    mouseup_untrusted: 0,
    click_trusted: 0,
    click_untrusted: 0,
    keydown_trusted: 0,
    keydown_untrusted: 0,
    focusin_count: 0,
    blur_count: 0,
  };

  let observerInstalled = false;
  let observerCleanedUp = false;
  let lastObserverSnapshot = { capped: false, totals: { ...ZERO_COUNTERS } };

  async function installDomObserver() {
    const installed = await page.evaluate(maxCount => {
      const root = typeof window !== 'undefined' ? window : globalThis;
      if (!root || typeof root.addEventListener !== 'function') {
        return false;
      }
      if (typeof root.__bh07FfInputProbeCleanup === 'function') {
        root.__bh07FfInputProbeCleanup();
      }
      const state = {
        capped: false,
        totals: {
          pointerdown_trusted: 0,
          pointerdown_untrusted: 0,
          pointerup_trusted: 0,
          pointerup_untrusted: 0,
          mousedown_trusted: 0,
          mousedown_untrusted: 0,
          mouseup_trusted: 0,
          mouseup_untrusted: 0,
          click_trusted: 0,
          click_untrusted: 0,
          keydown_trusted: 0,
          keydown_untrusted: 0,
          focusin_count: 0,
          blur_count: 0,
        },
        listeners: [],
      };
      function bump(key) {
        if (state.totals[key] >= maxCount) {
          state.capped = true;
          return;
        }
        state.totals[key]++;
      }
      function bind(type, handler) {
        root.addEventListener(type, handler, { capture: true, passive: true });
        state.listeners.push([type, handler]);
      }
      for (const type of ['pointerdown', 'pointerup', 'mousedown', 'mouseup', 'click', 'keydown']) {
        bind(type, evt => {
          const suffix = evt && evt.isTrusted ? '_trusted' : '_untrusted';
          bump(type + suffix);
        });
      }
      bind('focusin', () => bump('focusin_count'));
      bind('blur', () => bump('blur_count'));
      root.__bh07FfInputProbeState = state;
      root.__bh07FfInputProbeCleanup = () => {
        for (const [type, handler] of state.listeners) {
          root.removeEventListener(type, handler, { capture: true, passive: true });
        }
        state.listeners.length = 0;
        delete root.__bh07FfInputProbeCleanup;
        delete root.__bh07FfInputProbeState;
        return true;
      };
      return true;
    }, MAX_EVENT_COUNT);
    observerInstalled = Boolean(installed);
    if (!observerInstalled) {
      throw new Error('Observer setup failed: addEventListener unavailable');
    }
  }

  async function readObserverSnapshot() {
    if (!observerInstalled) {
      return { capped: false, totals: { ...ZERO_COUNTERS } };
    }
    const snap = await page.evaluate(() => {
      const root = typeof window !== 'undefined' ? window : globalThis;
      const st = root && root.__bh07FfInputProbeState;
      if (!st) return null;
      return {
        capped: Boolean(st.capped),
        totals: { ...st.totals },
      };
    }).catch(() => null);
    if (snap) {
      lastObserverSnapshot = snap;
    }
    return snap || lastObserverSnapshot;
  }

  function diffCounters(before, after) {
    const delta = {};
    for (const key of Object.keys(ZERO_COUNTERS)) {
      const b = before && typeof before[key] === 'number' ? before[key] : 0;
      const a = after && typeof after[key] === 'number' ? after[key] : 0;
      delta[key] = Math.max(0, a - b);
    }
    return delta;
  }

  const SANITIZE_ENUMS = {
    visibilities: ['visible', 'hidden', 'prerender'],
    tags: [
      'body', 'canvas', 'div', 'span', 'button', 'input', 'textarea', 'form', 'label', 'a',
      'flt-glass-pane', 'flt-semantics', 'flt-semantics-host', 'flt-semantics-placeholder',
      'flt-scene-host', 'flt-canvas-container', 'flt-text-editing-host', 'flutter-view', 'svg', 'path',
    ],
    roles: ['tab', 'button', 'textbox', 'dialog', 'group', 'presentation', 'generic'],
    pointerEvents: ['auto', 'none', 'all', 'visible'],
  };

  async function inspectPageState() {
    const vp = typeof page.viewportSize === 'function' ? page.viewportSize() : null;
    const domState = await page.evaluate(enums => {
      const ALLOWED_VIS = new Set(enums.visibilities);
      const ALLOWED_TAGS = new Set(enums.tags);
      const ALLOWED_ROLES = new Set(enums.roles);
      function sanitizeTag(node) {
        if (!node || !node.tagName) return 'none';
        const lower = String(node.tagName).toLowerCase();
        return ALLOWED_TAGS.has(lower) ? lower : 'other';
      }
      function sanitizeRole(node) {
        if (!node || typeof node.getAttribute !== 'function') return 'none';
        const role = node.getAttribute('role');
        if (!role) return 'none';
        const lower = String(role).toLowerCase().trim();
        return ALLOWED_ROLES.has(lower) ? lower : 'other';
      }
      const rawVis = typeof document !== 'undefined' ? String(document.visibilityState || '') : '';
      const visibility_state = ALLOWED_VIS.has(rawVis) ? rawVis : 'unknown';
      const has_focus = typeof document !== 'undefined' && typeof document.hasFocus === 'function'
        ? Boolean(document.hasFocus())
        : false;
      let topActive = typeof document !== 'undefined' ? document.activeElement : null;
      let deepActive = topActive;
      for (let d = 0; d < 4 && deepActive && deepActive.shadowRoot && deepActive.shadowRoot.activeElement; d++) {
        deepActive = deepActive.shadowRoot.activeElement;
      }
      const dpr = typeof window !== 'undefined' && Number.isFinite(window.devicePixelRatio)
        ? Math.round(window.devicePixelRatio * 1000) / 1000
        : null;
      return {
        visibility_state,
        has_focus,
        active_element_top_tag: sanitizeTag(topActive),
        active_element_tag: sanitizeTag(deepActive),
        active_element_role: sanitizeRole(deepActive),
        window_inner: typeof window !== 'undefined'
          ? {
              width: Number.isFinite(window.innerWidth) ? Math.round(window.innerWidth) : 0,
              height: Number.isFinite(window.innerHeight) ? Math.round(window.innerHeight) : 0,
            }
          : { width: 0, height: 0 },
        window_outer: typeof window !== 'undefined'
          ? {
              width: Number.isFinite(window.outerWidth) ? Math.round(window.outerWidth) : 0,
              height: Number.isFinite(window.outerHeight) ? Math.round(window.outerHeight) : 0,
            }
          : { width: 0, height: 0 },
        device_pixel_ratio: dpr,
      };
    }, SANITIZE_ENUMS).catch(() => ({
      visibility_state: 'unknown',
      has_focus: false,
      active_element_top_tag: 'none',
      active_element_tag: 'none',
      active_element_role: 'none',
      window_inner: { width: 0, height: 0 },
      window_outer: { width: 0, height: 0 },
      device_pixel_ratio: null,
    }));

    return {
      ...domState,
      playwright_viewport: vp
        ? { width: Math.round(vp.width), height: Math.round(vp.height) }
        : null,
    };
  }

  async function inspectTarget(locator) {
    const count = await locator.count().catch(() => 0);
    if (count === 0) {
      return {
        count: 0,
        visible: false,
        enabled: false,
        rect: null,
        target_pointer_events_css: 'other',
        active_element_matches_target: false,
        element_from_point: {
          status: 'not_checked',
          top_tag: 'none',
          tag: 'none',
          role: 'none',
          shadow_depth: 0,
          pointer_events_css: 'other',
          hit_matches_target: false,
        },
      };
    }
    const first = locator.first();
    const visible = await first.isVisible().catch(() => false);
    const enabled = await first.isEnabled().catch(() => false);
    const geom = await first.evaluate((el, enums) => {
      const ALLOWED_TAGS = new Set(enums.tags);
      const ALLOWED_ROLES = new Set(enums.roles);
      const ALLOWED_PE = new Set(enums.pointerEvents);
      function sanitizeTag(node) {
        if (!node || !node.tagName) return 'none';
        const lower = String(node.tagName).toLowerCase();
        return ALLOWED_TAGS.has(lower) ? lower : 'other';
      }
      function sanitizeRole(node) {
        if (!node || typeof node.getAttribute !== 'function') return 'none';
        const role = node.getAttribute('role');
        if (!role) return 'none';
        const lower = String(role).toLowerCase().trim();
        return ALLOWED_ROLES.has(lower) ? lower : 'other';
      }
      function sanitizePe(node) {
        try {
          const pe = String(getComputedStyle(node).pointerEvents || '').toLowerCase().trim();
          return ALLOWED_PE.has(pe) ? pe : 'other';
        } catch (_) {
          return 'other';
        }
      }
      function round2(n) {
        return Number.isFinite(n) ? Math.round(n * 100) / 100 : null;
      }

      const r = el.getBoundingClientRect();
      const cx = r.left + r.width / 2;
      const cy = r.top + r.height / 2;
      const vw = Number.isFinite(window.innerWidth) ? window.innerWidth : 0;
      const vh = Number.isFinite(window.innerHeight) ? window.innerHeight : 0;
      const inViewport = r.width > 0 && r.height > 0 && cx >= 0 && cx <= vw && cy >= 0 && cy <= vh;

      let deepActive = document.activeElement;
      for (let d = 0; d < 4 && deepActive && deepActive.shadowRoot && deepActive.shadowRoot.activeElement; d++) {
        deepActive = deepActive.shadowRoot.activeElement;
      }
      const activeMatches = Boolean(deepActive && (deepActive === el || el.contains(deepActive)));

      let hitStatus = 'not_checked';
      let topTag = 'none';
      let hitTag = 'none';
      let hitRole = 'none';
      let shadowDepth = 0;
      let hitPe = 'other';
      let hitMatches = false;

      if (r.width <= 0 || r.height <= 0) {
        hitStatus = 'zero_rect';
      } else if (!inViewport) {
        hitStatus = 'outside_viewport';
      } else {
        const topHit = document.elementFromPoint(cx, cy);
        if (!topHit) {
          hitStatus = 'null';
        } else {
          topTag = sanitizeTag(topHit);
          let deepHit = topHit;
          while (
            shadowDepth < 4 &&
            deepHit !== el &&
            deepHit.shadowRoot &&
            typeof deepHit.shadowRoot.elementFromPoint === 'function'
          ) {
            const innerHit = deepHit.shadowRoot.elementFromPoint(cx, cy);
            if (!innerHit || innerHit === deepHit) break;
            deepHit = innerHit;
            shadowDepth++;
          }
          hitTag = sanitizeTag(deepHit);
          hitRole = sanitizeRole(deepHit);
          hitPe = sanitizePe(deepHit);
          if (deepHit === el) {
            hitStatus = 'exact_target';
            hitMatches = true;
          } else if (el.contains(deepHit)) {
            hitStatus = 'target_descendant';
            hitMatches = true;
          } else if (deepHit.contains(el)) {
            hitStatus = 'target_ancestor';
            hitMatches = false;
          } else {
            hitStatus = 'other_element';
            hitMatches = false;
          }
        }
      }

      return {
        rect: {
          x: round2(r.left),
          y: round2(r.top),
          width: round2(r.width),
          height: round2(r.height),
          center_x: round2(cx),
          center_y: round2(cy),
          in_viewport: inViewport,
        },
        target_pointer_events_css: sanitizePe(el),
        active_element_matches_target: activeMatches,
        element_from_point: {
          status: hitStatus,
          top_tag: topTag,
          tag: hitTag,
          role: hitRole,
          shadow_depth: shadowDepth,
          pointer_events_css: hitPe,
          hit_matches_target: hitMatches,
        },
      };
    }, SANITIZE_ENUMS).catch(() => null);

    return {
      count,
      visible,
      enabled,
      rect: geom ? geom.rect : null,
      target_pointer_events_css: geom ? geom.target_pointer_events_css : 'other',
      active_element_matches_target: geom ? geom.active_element_matches_target : false,
      element_from_point: geom
        ? geom.element_from_point
        : {
            status: 'evaluate_failed',
            top_tag: 'none',
            tag: 'none',
            role: 'none',
            shadow_depth: 0,
            pointer_events_css: 'other',
            hit_matches_target: false,
          },
    };
  }

  async function probeRafCommit(timeoutMs = RAF_TIMEOUT_MS) {
    const start = Date.now();
    const res = await page.evaluate(
      ms =>
        Promise.race([
          new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(() => resolve(true)))),
          new Promise(resolve => setTimeout(() => resolve(false), ms)),
        ]),
      timeoutMs
    ).catch(() => null);
    const raf_commit_state = res === true ? 'committed' : res === false ? 'timed_out' : 'unknown';
    return {
      raf_commit: res === true,
      raf_commit_state,
      raf_elapsed_ms: Math.max(0, Date.now() - start),
    };
  }

  function rafFailCode(prefix, raf) {
    return raf.raf_commit_state === 'unknown' ? `${prefix}_RAF_UNKNOWN` : `${prefix}_RAF_TIMEOUT`;
  }

  async function waitForSnapshot(predicate, timeoutMs = ACTION_TIMEOUT_MS, pollMs = 400) {
    const start = Date.now();
    while (Date.now() - start < timeoutMs) {
      const snap = predicate.length > 0 ? await page.locator('body').ariaSnapshot().catch(() => '') : '';
      if (await predicate(snap)) {
        return true;
      }
      await page.waitForTimeout(pollMs);
    }
    return false;
  }

  // Permitted Flutter accessibility placeholder bootstrap (distinct from app-action physical clicks)
  async function runSemanticsBootstrap() {
    const start = Date.now();
    const selector = 'flt-semantics-placeholder, [aria-label*="Enable accessibility"], button:has-text("Enable accessibility")';
    const placeholder = page.locator(selector).first();
    const accountTab = page.getByRole('tab', { name: 'Tài Khoản' });
    let attempts = 0;
    let placeholderFound = false;
    let placeholderClicked = false;
    const deadline = Date.now() + BOOTSTRAP_TIMEOUT_MS;

    while (!(await accountTab.isVisible().catch(() => false))) {
      attempts++;
      await Promise.race([
        placeholder.waitFor({ state: 'attached', timeout: 3000 }).catch(() => {}),
        accountTab.waitFor({ state: 'visible', timeout: 3000 }).catch(() => {}),
      ]);
      if (await accountTab.isVisible().catch(() => false)) {
        break;
      }
      const phCount = await placeholder.count().catch(() => 0);
      if (phCount > 0) {
        placeholderFound = true;
        try {
          await placeholder.evaluate(el => el.click());
          placeholderClicked = true;
        } catch (_) {
          // Placeholder may detach during semantics tree swap
        }
      }
      await page.waitForTimeout(400);
      if (await accountTab.isVisible().catch(() => false)) {
        break;
      }
      if (Date.now() >= deadline) {
        return {
          attempted: true,
          placeholder_found: placeholderFound,
          placeholder_clicked: placeholderClicked,
          account_tab_visible: false,
          attempts,
          duration_ms: Math.max(0, Date.now() - start),
          status: 'FAIL',
          error_code: 'BOOTSTRAP_TIMEOUT',
        };
      }
    }

    return {
      attempted: true,
      placeholder_found: placeholderFound,
      placeholder_clicked: placeholderClicked,
      account_tab_visible: true,
      attempts,
      duration_ms: Math.max(0, Date.now() - start),
      status: 'PASS',
      error_code: null,
    };
  }

  async function countAuthStorageKeys() {
    return page.evaluate(() => {
      let count = 0;
      for (const store of [
        typeof localStorage !== 'undefined' ? localStorage : null,
        typeof sessionStorage !== 'undefined' ? sessionStorage : null,
      ]) {
        if (!store) continue;
        for (let i = 0; i < store.length; i++) {
          const k = store.key(i) || '';
          if (k.startsWith('sb-') || k.includes('auth-token') || k.includes('supabase.auth')) {
            count++;
          }
        }
      }
      return count;
    }).catch(() => -1);
  }

  const screenshots = [];
  async function captureSafeScreenshot(stageName, shotPath) {
    assertLoopbackOrigin();
    try {
      await page.screenshot({ path: shotPath, scale: 'css', timeout: ACTION_TIMEOUT_MS });
      screenshots.push({ stage: stageName, path: shotPath, taken: true, error_code: null });
    } catch (_) {
      screenshots.push({ stage: stageName, path: shotPath, taken: false, error_code: 'SCREENSHOT_FAILED' });
    }
  }

  function notRunStep() {
    return { status: 'NOT_RUN', error_code: null, duration_ms: 0 };
  }

  let bringToFrontCalls = 0;
  let initialPageState = null;
  let afterGotoState = null;
  let afterBringToFrontState = null;
  let semanticsBootstrap = {
    attempted: false,
    placeholder_found: false,
    placeholder_clicked: false,
    account_tab_visible: false,
    attempts: 0,
    duration_ms: 0,
    status: 'NOT_RUN',
    error_code: null,
  };
  const steps = {
    account_tab_click: notRunStep(),
    account_guest_view: notRunStep(),
    login_cta_click: notRunStep(),
    login_dialog_open: notRunStep(),
    email_input: notRunStep(),
    password_input: notRunStep(),
    post_input_tab_blur: notRunStep(),
  };

  let overallOk = false;
  let failureStage = null;
  let errorCode = null;
  let authStorageKeyCount = -1;

  function markFail(stage, code) {
    overallOk = false;
    failureStage = stage;
    errorCode = code;
  }

  function isTimeoutErr(err) {
    return Boolean(err && typeof err.message === 'string' && /timeout/i.test(err.message));
  }

  async function runPhysicalClickStep(stepKey, locator, prefix) {
    const start = Date.now();
    const beforeSnap = await readObserverSnapshot();
    const prePage = await inspectPageState();
    const preTarget = await inspectTarget(locator);

    try {
      await locator.waitFor({ state: 'visible', timeout: ACTION_TIMEOUT_MS });
    } catch (_) {
      const raf = await probeRafCommit();
      const afterSnap = await readObserverSnapshot();
      const notVisibleCode = `${prefix}_NOT_VISIBLE`;
      steps[stepKey] = {
        status: 'FAIL',
        error_code: notVisibleCode,
        duration_ms: Math.max(0, Date.now() - start),
        pre_state: { page: prePage, target: preTarget },
        post_state: { page: await inspectPageState(), ...raf },
        event_delta: diffCounters(beforeSnap.totals, afterSnap.totals),
      };
      markFail(stepKey, notVisibleCode);
      return false;
    }

    let clickCode = null;
    try {
      await locator.click({ timeout: ACTION_TIMEOUT_MS });
    } catch (err) {
      clickCode = isTimeoutErr(err) ? `${prefix}_CLICK_TIMEOUT` : `${prefix}_CLICK_FAILED`;
    }
    const raf = await probeRafCommit();
    const afterSnap = await readObserverSnapshot();
    const postPage = await inspectPageState();
    const stepCode = clickCode || (raf.raf_commit !== true ? rafFailCode(`${prefix}_POST_CLICK`, raf) : null);

    if (stepCode) {
      steps[stepKey] = {
        status: 'FAIL',
        error_code: stepCode,
        duration_ms: Math.max(0, Date.now() - start),
        pre_state: { page: prePage, target: preTarget },
        post_state: { page: postPage, ...raf },
        event_delta: diffCounters(beforeSnap.totals, afterSnap.totals),
      };
      markFail(stepKey, stepCode);
      return false;
    }

    steps[stepKey] = {
      status: 'PASS',
      error_code: null,
      duration_ms: Math.max(0, Date.now() - start),
      pre_state: { page: prePage, target: preTarget },
      post_state: { page: postPage, ...raf },
      event_delta: diffCounters(beforeSnap.totals, afterSnap.totals),
    };
    return true;
  }

  async function runSyntheticFieldStep(stepKey, field, value, prefix) {
    const start = Date.now();
    const attempts = [];
    let finalCode = `${prefix}_VALUE_NOT_RETAINED`;
    let retained = false;

    try {
      await field.waitFor({ state: 'visible', timeout: ACTION_TIMEOUT_MS });
    } catch (_) {
      steps[stepKey] = {
        status: 'FAIL',
        error_code: `${prefix}_FIELD_NOT_VISIBLE`,
        duration_ms: Math.max(0, Date.now() - start),
        value_retained: false,
        attempts,
      };
      markFail(stepKey, `${prefix}_FIELD_NOT_VISIBLE`);
      return false;
    }

    for (let attempt = 1; attempt <= 2; attempt++) {
      const beforeSnap = await readObserverSnapshot();
      const prePage = await inspectPageState();
      const preTarget = await inspectTarget(field);
      const clickStart = Date.now();
      let clickOk = true;
      let clickCode = null;

      try {
        await field.click({ timeout: ACTION_TIMEOUT_MS });
      } catch (err) {
        clickOk = false;
        clickCode = isTimeoutErr(err) ? `${prefix}_CLICK_TIMEOUT` : `${prefix}_CLICK_FAILED`;
      }
      const clickDuration = Math.max(0, Date.now() - clickStart);
      const afterClickTarget = await inspectTarget(field);
      const preRaf = await probeRafCommit();

      if (!clickOk) {
        const afterSnap = await readObserverSnapshot();
        attempts.push({
          attempt,
          pre_page: prePage,
          pre_target: preTarget,
          click_duration_ms: clickDuration,
          click_ok: false,
          active_element_matched_after_click: afterClickTarget.active_element_matches_target,
          pre_type_raf_commit: preRaf.raf_commit,
          pre_type_raf_elapsed_ms: preRaf.raf_elapsed_ms,
          type_ok: false,
          post_type_raf_commit: false,
          post_type_raf_elapsed_ms: 0,
          value_retained: false,
          event_delta: diffCounters(beforeSnap.totals, afterSnap.totals),
        });
        finalCode = clickCode;
        break;
      }

      if (preRaf.raf_commit !== true) {
        const afterSnap = await readObserverSnapshot();
        attempts.push({
          attempt,
          pre_page: prePage,
          pre_target: preTarget,
          click_duration_ms: clickDuration,
          click_ok: true,
          active_element_matched_after_click: afterClickTarget.active_element_matches_target,
          pre_type_raf_commit: false,
          pre_type_raf_commit_state: preRaf.raf_commit_state,
          pre_type_raf_elapsed_ms: preRaf.raf_elapsed_ms,
          type_ok: false,
          post_type_raf_commit: false,
          post_type_raf_elapsed_ms: 0,
          value_retained: false,
          event_delta: diffCounters(beforeSnap.totals, afterSnap.totals),
        });
        finalCode = rafFailCode(`${prefix}_PRE_TYPE`, preRaf);
        break;
      }

      let typeOk = true;
      try {
        await field.press('ControlOrMeta+a', { timeout: ACTION_TIMEOUT_MS });
        await field.press('Backspace', { timeout: ACTION_TIMEOUT_MS });
        await field.pressSequentially(value, { delay: 15, timeout: ACTION_TIMEOUT_MS });
      } catch (_) {
        typeOk = false;
      }
      const postRaf = await probeRafCommit();
      retained = typeOk && (await field.inputValue().catch(() => '')) === value;
      const afterSnap = await readObserverSnapshot();

      attempts.push({
        attempt,
        pre_page: prePage,
        pre_target: preTarget,
        click_duration_ms: clickDuration,
        click_ok: true,
        active_element_matched_after_click: afterClickTarget.active_element_matches_target,
        pre_type_raf_commit: true,
        pre_type_raf_commit_state: preRaf.raf_commit_state,
        pre_type_raf_elapsed_ms: preRaf.raf_elapsed_ms,
        type_ok: typeOk,
        post_type_raf_commit: postRaf.raf_commit,
        post_type_raf_commit_state: postRaf.raf_commit_state,
        post_type_raf_elapsed_ms: postRaf.raf_elapsed_ms,
        value_retained: retained,
        event_delta: diffCounters(beforeSnap.totals, afterSnap.totals),
      });

      if (!typeOk) {
        finalCode = `${prefix}_TYPE_FAILED`;
        break;
      }
      if (postRaf.raf_commit !== true) {
        finalCode = rafFailCode(`${prefix}_POST_TYPE`, postRaf);
        break;
      }
      if (retained) {
        finalCode = null;
        break;
      }
    }

    const ok = Boolean(retained && finalCode === null);
    steps[stepKey] = {
      status: ok ? 'PASS' : 'FAIL',
      error_code: ok ? null : finalCode,
      duration_ms: Math.max(0, Date.now() - start),
      value_retained: Boolean(retained),
      attempts,
    };
    if (!ok) {
      markFail(stepKey, finalCode || `${prefix}_VALUE_NOT_RETAINED`);
    }
    return ok;
  }

  try {
    initialPageState = await inspectPageState();

    if (FOCUS_MODE === 'bring_to_front') {
      await page.bringToFront();
      bringToFrontCalls++;
    }

    try {
      await page.goto(`${expectedBase.origin}/#/`, { timeout: BOOTSTRAP_TIMEOUT_MS });
    } catch (_) {
      markFail('navigate_home', 'NAVIGATION_FAILED');
    }

    if (!failureStage) {
      assertLoopbackOrigin();
      afterGotoState = await inspectPageState();

      if (FOCUS_MODE === 'bring_to_front') {
        await page.bringToFront();
        bringToFrontCalls++;
        afterBringToFrontState = await inspectPageState();
      }

      semanticsBootstrap = await runSemanticsBootstrap();
      if (semanticsBootstrap.status !== 'PASS') {
        markFail('semantics_bootstrap', semanticsBootstrap.error_code || 'BOOTSTRAP_TIMEOUT');
        await captureSafeScreenshot('failure', caseShots.failure);
      } else {
        await installDomObserver();
        await captureSafeScreenshot('home_guest', caseShots.home);

        const accountTab = page.getByRole('tab', { name: 'Tài Khoản' });
        const accountClickOk = await runPhysicalClickStep(
          'account_tab_click',
          accountTab,
          'ACCOUNT_TAB'
        );

        if (!accountClickOk) {
          await captureSafeScreenshot('failure', caseShots.failure);
        } else {
          const guestStart = Date.now();
          const guestReached = await waitForSnapshot(
            snap => snap.includes('Bạn đang xem dưới dạng khách') && snap.includes('Đăng Nhập / Đăng Ký'),
            ACTION_TIMEOUT_MS
          );
          const guestRaf = await probeRafCommit();
          const guestPage = await inspectPageState();
          let guestCode = null;
          if (!guestReached) {
            guestCode = 'ACCOUNT_GUEST_VIEW_NOT_REACHED';
          } else if (guestRaf.raf_commit !== true) {
            guestCode = rafFailCode('ACCOUNT_GUEST_VIEW', guestRaf);
          }
          steps.account_guest_view = {
            status: guestCode ? 'FAIL' : 'PASS',
            error_code: guestCode,
            duration_ms: Math.max(0, Date.now() - guestStart),
            post_state: { page: guestPage, ...guestRaf },
          };
          if (guestCode) {
            markFail('account_guest_view', guestCode);
            await captureSafeScreenshot('failure', caseShots.failure);
          } else {
            const loginCta = page.getByRole('button', { name: 'Đăng Nhập / Đăng Ký' });
            const ctaClickOk = await runPhysicalClickStep(
              'login_cta_click',
              loginCta,
              'LOGIN_CTA'
            );

            if (!ctaClickOk) {
              await captureSafeScreenshot('failure', caseShots.failure);
            } else {
              const dlgStart = Date.now();
              const emailField = page.getByRole('textbox', { name: 'Email' });
              const passField = page.getByRole('textbox', { name: 'Mật khẩu' });
              const submitBtn = page.getByRole('button', { name: 'Đăng Nhập', exact: true });
              const dlgReached = await waitForSnapshot(
                async () =>
                  (await emailField.isVisible().catch(() => false)) &&
                  (await passField.isVisible().catch(() => false)),
                ACTION_TIMEOUT_MS
              );
              const emailVisible = await emailField.isVisible().catch(() => false);
              const passwordVisible = await passField.isVisible().catch(() => false);
              const submitButtonVisible = await submitBtn.isVisible().catch(() => false);
              const dlgPage = await inspectPageState();
              const dlgRaf = await probeRafCommit();
              let dlgCode = null;
              if (!dlgReached || !emailVisible || !passwordVisible) {
                dlgCode = 'LOGIN_DIALOG_NOT_OPENED';
              } else if (dlgRaf.raf_commit !== true) {
                dlgCode = rafFailCode('LOGIN_DIALOG', dlgRaf);
              }
              steps.login_dialog_open = {
                status: dlgCode ? 'FAIL' : 'PASS',
                error_code: dlgCode,
                duration_ms: Math.max(0, Date.now() - dlgStart),
                email_visible: emailVisible,
                password_visible: passwordVisible,
                submit_button_visible: submitButtonVisible,
                post_state: { page: dlgPage, ...dlgRaf },
              };

              if (dlgCode) {
                markFail('login_dialog_open', dlgCode);
                await captureSafeScreenshot('failure', caseShots.failure);
              } else {
                const emailOk = await runSyntheticFieldStep('email_input', emailField, SYNTHETIC_EMAIL, 'EMAIL');
                if (!emailOk) {
                  await captureSafeScreenshot('failure', caseShots.failure);
                } else if (authOrMutationRequestCount > 0) {
                  markFail('unexpected_mutation_request', 'UNEXPECTED_AUTH_OR_MUTATION_ACTIVITY');
                  await captureSafeScreenshot('failure', caseShots.failure);
                } else {
                  const passOk = await runSyntheticFieldStep('password_input', passField, SYNTHETIC_PASS, 'PASSWORD');
                  if (!passOk) {
                    await captureSafeScreenshot('failure', caseShots.failure);
                  } else {
                    const tabStart = Date.now();
                    const beforeTabSnap = await readObserverSnapshot();
                    let tabPressOk = true;
                    try {
                      await passField.press('Tab', { timeout: ACTION_TIMEOUT_MS });
                    } catch (_) {
                      tabPressOk = false;
                    }
                    const tabRaf = await probeRafCommit();
                    const emailRetained = (await emailField.inputValue().catch(() => '')) === SYNTHETIC_EMAIL;
                    const passwordRetained = (await passField.inputValue().catch(() => '')) === SYNTHETIC_PASS;
                    const afterTabSnap = await readObserverSnapshot();
                    const postTabPage = await inspectPageState();

                    let tabCode = null;
                    if (!tabPressOk) {
                      tabCode = 'TAB_BLUR_FAILED';
                    } else if (tabRaf.raf_commit !== true) {
                      tabCode = rafFailCode('TAB_BLUR', tabRaf);
                    } else if (!emailRetained || !passwordRetained) {
                      tabCode = 'INPUTS_LOST_AFTER_TAB_BLUR';
                    }

                    steps.post_input_tab_blur = {
                      status: tabCode ? 'FAIL' : 'PASS',
                      error_code: tabCode,
                      duration_ms: Math.max(0, Date.now() - tabStart),
                      raf_commit: tabRaf.raf_commit,
                      raf_commit_state: tabRaf.raf_commit_state,
                      raf_elapsed_ms: tabRaf.raf_elapsed_ms,
                      email_retained_after_blur: emailRetained,
                      password_retained_after_blur: passwordRetained,
                      post_state: postTabPage,
                      event_delta: diffCounters(beforeTabSnap.totals, afterTabSnap.totals),
                    };

                    if (tabCode) {
                      markFail('post_input_tab_blur', tabCode);
                      await captureSafeScreenshot('failure', caseShots.failure);
                    } else {
                      overallOk = true;
                      await captureSafeScreenshot('login_synthetic', caseShots.login);
                    }
                  }
                }
              }
            }
          }
        }
      }

      authStorageKeyCount = await countAuthStorageKeys();
      if (authOrMutationRequestCount > 0 || authStorageKeyCount !== 0) {
        markFail('unexpected_mutation_request', 'UNEXPECTED_AUTH_OR_MUTATION_ACTIVITY');
      }
    }

    lastObserverSnapshot = await readObserverSnapshot();
  } catch (err) {
    if (err && typeof err.message === 'string' && err.message.startsWith('Guard failed:')) {
      throw err;
    }
    markFail(failureStage || 'unexpected_error', 'UNEXPECTED_PROBE_FAILURE');
  } finally {
    let cleanupErr = null;
    try {
      page.off('console', onConsole);
      page.off('pageerror', onPageError);
      page.off('request', onRequest);
      if (observerInstalled && (typeof page.isClosed !== 'function' || !page.isClosed())) {
        const removed = await page.evaluate(() => {
          const root = typeof window !== 'undefined' ? window : globalThis;
          const fn = root && root.__bh07FfInputProbeCleanup;
          if (typeof fn !== 'function') return false;
          return Boolean(fn());
        });
        if (!removed) {
          cleanupErr = new Error('Cleanup failed: DOM probe cleanup returned false');
        } else {
          observerCleanedUp = true;
        }
      } else if (!observerInstalled) {
        observerCleanedUp = true;
      }
    } catch (_) {
      cleanupErr = new Error('Cleanup failed: unable to remove DOM probe observer');
    }
    if (cleanupErr) {
      throw cleanupErr;
    }
  }

  return {
    diagnosticOnly: true,
    ok: overallOk,
    status: overallOk ? 'PASS' : 'FAIL',
    failure_stage: overallOk ? null : failureStage,
    error_code: overallOk ? null : errorCode,
    config: {
      render_mode: RENDER_MODE,
      focus_mode: FOCUS_MODE,
      browser_name: browserName || 'firefox',
      bring_to_front_calls: bringToFrontCalls,
      base_origin: expectedBase.origin,
      no_submit: true,
      no_headless_fallback: true,
      no_force_or_dom_click_for_app: true,
    },
    total_duration_ms: elapsedMs(),
    initial_page_state: initialPageState,
    after_goto_state: afterGotoState,
    after_bring_to_front_state: afterBringToFrontState,
    semantics_bootstrap: semanticsBootstrap,
    steps,
    observer_summary: {
      installed: observerInstalled,
      cleaned_up: observerCleanedUp,
      capped: Boolean(lastObserverSnapshot.capped),
      totals: lastObserverSnapshot.totals,
    },
    safety_checks: {
      auth_or_mutation_request_count: authOrMutationRequestCount,
      auth_storage_key_count: authStorageKeyCount,
      no_submit_verified: true,
    },
    recorded_console_summary: consoleSummary,
    screenshots,
  };
}