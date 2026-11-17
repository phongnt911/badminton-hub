const fs = require('fs');
const assert = require('assert/strict');

const PROBE_PATH = 'scripts/bh07_browser/firefox_headed_input_probe.js';

function loadProbeSource() {
  return fs.readFileSync(PROBE_PATH, 'utf8');
}

function compileProbe(overrides = {}) {
  let source = loadProbeSource();
  assert(!source.trimEnd().endsWith(';'), 'Probe expression must not end with a trailing semicolon');
  if (overrides.focusMode !== undefined) {
    const marker = "  const FOCUS_MODE = 'baseline';";
    assert.equal(source.split(marker).length, 2, 'Missing FOCUS_MODE constant');
    source = source.replace(marker, `  const FOCUS_MODE = ${JSON.stringify(overrides.focusMode)};`);
  }
  if (overrides.renderMode !== undefined) {
    const marker = "  const RENDER_MODE = 'default';";
    assert.equal(source.split(marker).length, 2, 'Missing RENDER_MODE constant');
    source = source.replace(marker, `  const RENDER_MODE = ${JSON.stringify(overrides.renderMode)};`);
  }
  return new Function('return (' + source + '\n)')();
}

function withFastMockClock(fn) {
  const realNow = Date.now;
  let fakeNow = realNow();
  Date.now = () => fakeNow;
  const advance = ms => {
    fakeNow += Math.max(1, Number(ms) || 1);
  };
  return Promise.resolve()
    .then(() => fn(advance))
    .finally(() => {
      Date.now = realNow;
    });
}

function createMockPage(opts = {}) {
  let currentUrl = opts.initialUrl !== undefined ? opts.initialUrl : 'about:blank';
  let screen = opts.initialScreen || 'blank';
  let semanticsReady = Boolean(opts.semanticsAlreadyReady);
  let bringToFrontCalls = 0;
  let gotoCalls = 0;
  let submitClicks = 0;
  let emailTypedValue = '';
  let passTypedValue = '';
  const screenshotCalls = [];
  const clickLog = [];
  const pageListeners = new Map();
  const domListeners = new Map();

  const makeEl = (tagName, role, value = '', customRect = null) => ({
    tagName,
    role,
    value,
    pointerEvents: opts.pointerEventsCss || 'auto',
    rect: customRect || { left: 100, top: 120, width: 140, height: 40 },
    contains(other) {
      return other === this;
    },
    getAttribute(name) {
      return name === 'role' ? this.role : null;
    },
    getBoundingClientRect() {
      return this.rect;
    },
  });

  const placeholderEl = makeEl('flt-semantics-placeholder', null);
  placeholderEl.click = () => {
    clickLog.push({ target: 'semantics_placeholder', via: 'dom_evaluate' });
    if (!opts.bootstrapFails) {
      semanticsReady = true;
    }
  };

  const accountTabEl = makeEl(opts.customTag || 'flt-semantics', opts.customRole || 'tab');
  const loginCtaEl = makeEl('flt-semantics', 'button');
  const emailFieldEl = makeEl('input', 'textbox');
  const passFieldEl = makeEl('input', 'textbox');
  const submitBtnEl = makeEl('flt-semantics', 'button');
  const bodyEl = makeEl('body', null);
  const occluderEl = makeEl('flt-glass-pane', 'presentation');

  let activeElement = bodyEl;
  let hasFocus = opts.initialHasFocus !== undefined ? opts.initialHasFocus : false;
  let visibilityState = opts.initialVisibilityState || 'visible';

  const storageData = new Map(Object.entries(opts.localStorageEntries || {}));
  const sessionStorageData = new Map(Object.entries(opts.sessionStorageEntries || {}));

  const storageFacade = map => ({
    get length() {
      return map.size;
    },
    key(i) {
      return Array.from(map.keys())[i] ?? null;
    },
    getItem(k) {
      return map.has(k) ? map.get(k) : null;
    },
  });

  function dispatchDomEvent(type, trusted = true, extra = {}) {
    const handlers = domListeners.get(type);
    if (!handlers) return;
    const evt = { type, isTrusted: trusted, ...extra };
    for (const h of Array.from(handlers)) {
      h(evt);
    }
  }

  function emitPageEvent(type, payload) {
    const handlers = pageListeners.get(type);
    if (!handlers) return;
    for (const h of Array.from(handlers)) {
      h(payload);
    }
  }

  function dispatchTrustedClick(el) {
    dispatchDomEvent('pointerdown', true);
    dispatchDomEvent('mousedown', true);
    dispatchDomEvent('pointerup', true);
    dispatchDomEvent('mouseup', true);
    dispatchDomEvent('click', true);
    if (el === emailFieldEl || el === passFieldEl) {
      if (activeElement !== el) {
        if (activeElement !== bodyEl) {
          dispatchDomEvent('blur', true);
        }
        activeElement = el;
        dispatchDomEvent('focusin', true);
      }
    }
  }

  function activeDomListenerCount() {
    let total = 0;
    for (const set of domListeners.values()) total += set.size;
    return total;
  }

  function activePageListenerCount() {
    let total = 0;
    for (const set of pageListeners.values()) total += set.size;
    return total;
  }

  let mockWindow = {
    innerWidth: 1280,
    innerHeight: 720,
    outerWidth: 1296,
    outerHeight: 796,
    devicePixelRatio: 1,
    addEventListener(type, handler) {
      if (!domListeners.has(type)) domListeners.set(type, new Set());
      domListeners.get(type).add(handler);
    },
    removeEventListener(type, handler) {
      if (opts.cleanupThrows && type === 'pointerdown') {
        throw new Error('simulated DOM cleanup failure');
      }
      const set = domListeners.get(type);
      if (set) set.delete(handler);
    },
  };

  function resetDocumentWindow() {
    domListeners.clear();
    for (const key of Object.keys(mockWindow)) {
      if (key.startsWith('__bh07')) delete mockWindow[key];
    }
  }

  let promiseRaceCallIndex = 0;
  const realPromiseRace = Promise.race.bind(Promise);

  const savedGlobals = new Map();
  let savedPromiseRaceDesc = null;
  function withBrowserGlobals(fn) {
    const mockDocument = {
      get visibilityState() {
        return visibilityState;
      },
      hasFocus() {
        return hasFocus;
      },
      get activeElement() {
        if (opts.shadowHostTarget && (activeElement === emailFieldEl || activeElement === passFieldEl)) {
          return opts.shadowHostTarget;
        }
        return activeElement;
      },
      elementFromPoint() {
        if (opts.occludeTarget) return occluderEl;
        if (opts.shadowHostTarget) return opts.shadowHostTarget;
        if (screen === 'home' && semanticsReady) return accountTabEl;
        if (screen === 'account_guest') return loginCtaEl;
        if (screen === 'login_dialog') return emailFieldEl;
        return bodyEl;
      },
    };
    const mockNavigator = {
      userAgent: opts.userAgent !== undefined
        ? opts.userAgent
        : 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:156.0) Gecko/20100101 Firefox/156.0',
    };
    const mockGetComputedStyle = el => ({ pointerEvents: (el && el.pointerEvents) || 'auto' });
    const mockRaf = cb => {
      if (opts.rafStalled) return 0;
      return Promise.resolve().then(() => cb(16));
    };
    const realSetTimeout = globalThis.setTimeout;
    const mockSetTimeout = (cb, ms) => {
      if (opts.rafStalled && ms >= 1000) {
        return realSetTimeout(cb, 5);
      }
      return realSetTimeout(cb, ms);
    };

    const patches = {
      window: mockWindow,
      document: mockDocument,
      navigator: mockNavigator,
      localStorage: storageFacade(storageData),
      sessionStorage: storageFacade(sessionStorageData),
      getComputedStyle: mockGetComputedStyle,
      requestAnimationFrame: mockRaf,
      setTimeout: mockSetTimeout,
    };

    for (const [k, v] of Object.entries(patches)) {
      if (!savedGlobals.has(k)) {
        savedGlobals.set(k, Object.getOwnPropertyDescriptor(globalThis, k) || null);
      }
      Object.defineProperty(globalThis, k, {
        configurable: true,
        writable: true,
        enumerable: true,
        value: v,
      });
    }

    if (opts.promiseRaceOverrides) {
      savedPromiseRaceDesc = Object.getOwnPropertyDescriptor(Promise, 'race') || null;
      Promise.race = iterable => {
        promiseRaceCallIndex++;
        if (Object.prototype.hasOwnProperty.call(opts.promiseRaceOverrides, promiseRaceCallIndex)) {
          const override = opts.promiseRaceOverrides[promiseRaceCallIndex];
          if (override === 'reject') return Promise.reject(new Error('simulated raf eval failure'));
          return Promise.resolve(override);
        }
        return realPromiseRace(iterable);
      };
    }

    return Promise.resolve()
      .then(fn)
      .finally(() => {
        if (opts.promiseRaceOverrides && savedPromiseRaceDesc) {
          Object.defineProperty(Promise, 'race', savedPromiseRaceDesc);
          savedPromiseRaceDesc = null;
        }
        for (const [k, prevDesc] of savedGlobals.entries()) {
          if (prevDesc === null) {
            delete globalThis[k];
          } else {
            Object.defineProperty(globalThis, k, prevDesc);
          }
        }
        savedGlobals.clear();
      });
  }

  function makeRoleLocator(role, name) {
    const isTarget = () => {
      if (role === 'tab' && name === 'Tài Khoản') {
        return {
          name: 'account_tab',
          el: accountTabEl,
          visible: () => screen === 'home' && semanticsReady && !opts.bootstrapFails,
          onClick: () => {
            if (opts.highEventVolume) {
              for (let i = 0; i < 15000; i++) dispatchDomEvent('pointerdown', true);
            }
            if (opts.accountClickTimeout) {
              throw new Error(opts.rawExceptionText || 'locator.click: Timeout 10000ms exceeded');
            }
            if (opts.emitRequestOnAccountClick) {
              emitPageEvent('request', {
                method: () => opts.emitRequestOnAccountClick.method,
                url: () => opts.emitRequestOnAccountClick.url,
              });
            }
            if (opts.emitReadOnlyMethodsOnAccountClick) {
              emitPageEvent('request', { method: () => 'GET', url: () => 'http://127.0.0.1:54321/rest/v1/sessions' });
              emitPageEvent('request', { method: () => 'HEAD', url: () => 'http://127.0.0.1:8088/' });
              emitPageEvent('request', { method: () => 'OPTIONS', url: () => 'http://127.0.0.1:54321/rest/v1/rpc/complete_session' });
            }
            dispatchTrustedClick(accountTabEl);
            if (!opts.accountClickNoNav) {
              screen = 'account_guest';
            }
          },
        };
      }
      if (role === 'button' && name === 'Đăng Nhập / Đăng Ký') {
        return {
          name: 'login_cta',
          el: loginCtaEl,
          visible: () => screen === 'account_guest',
          onClick: () => {
            if (opts.loginCtaTimeout) {
              throw new Error('locator.click: Timeout 10000ms exceeded');
            }
            dispatchTrustedClick(loginCtaEl);
            if (!opts.loginCtaNoDialog) {
              screen = 'login_dialog';
            }
          },
        };
      }
      if (role === 'button' && name === 'Đăng Nhập') {
        return {
          name: 'submit_btn',
          el: submitBtnEl,
          visible: () => screen === 'login_dialog',
          onClick: () => {
            submitClicks++;
          },
        };
      }
      if (role === 'textbox' && name === 'Email') {
        return {
          name: 'email_field',
          el: emailFieldEl,
          visible: () => screen === 'login_dialog',
          onClick: () => {
            if (opts.emailClickFails) throw new Error('email click failed');
            dispatchTrustedClick(emailFieldEl);
          },
          getValue: () => emailTypedValue,
          setValue: v => {
            if (!opts.emailValueNotRetained) emailTypedValue = v;
          },
        };
      }
      if (role === 'textbox' && name === 'Mật khẩu') {
        return {
          name: 'password_field',
          el: passFieldEl,
          visible: () => screen === 'login_dialog',
          onClick: () => {
            dispatchTrustedClick(passFieldEl);
          },
          getValue: () => passTypedValue,
          setValue: v => {
            if (!opts.passwordValueNotRetained) passTypedValue = v;
          },
        };
      }
      return { name: 'unknown', el: bodyEl, visible: () => false, onClick: () => {} };
    };

    const loc = {
      first() {
        return loc;
      },
      async count() {
        return isTarget().visible() ? 1 : 0;
      },
      async isVisible() {
        return isTarget().visible();
      },
      async isEnabled() {
        return isTarget().visible();
      },
      async waitFor(waitOpts = {}) {
        const state = waitOpts.state || 'visible';
        if (state === 'visible' && !isTarget().visible()) {
          throw new Error(`waitFor(${state}) timeout`);
        }
      },
      async evaluate(fn, arg) {
        const info = isTarget();
        return withBrowserGlobals(() => fn(info.el, arg));
      },
      async click(clickOpts = {}) {
        assert(!clickOpts.force, 'App action click must never pass force: true');
        const info = isTarget();
        clickLog.push({ target: info.name, via: 'locator.click' });
        await info.onClick();
      },
      async dispatchEvent() {
        throw new Error('App action must never call dispatchEvent');
      },
      async press(key) {
        const info = isTarget();
        dispatchDomEvent('keydown', true);
        if (key === 'Backspace' && info.setValue) {
          info.setValue('');
        }
        if (key === 'Tab') {
          if (activeElement !== bodyEl) dispatchDomEvent('blur', true);
          activeElement = bodyEl;
          dispatchDomEvent('focusin', true);
        }
      },
      async pressSequentially(text) {
        const info = isTarget();
        for (let i = 0; i < text.length; i++) {
          dispatchDomEvent('keydown', true);
        }
        if (info.setValue) info.setValue(text);
        if (opts.emitConsoleAndPageError) {
          emitPageEvent('console', { type: () => 'error', text: () => 'SECRET_CONSOLE_TEXT' });
          emitPageEvent('console', { type: () => 'warning', text: () => 'SECRET_WARNING_TEXT' });
          emitPageEvent('pageerror', new Error('SECRET_PAGEERROR_TEXT'));
        }
        if (opts.emitAuthPostAfterType) {
          emitPageEvent('request', {
            method: () => 'POST',
            url: () => 'http://127.0.0.1:54321/auth/v1/token?grant_type=password',
          });
        }
      },
      async inputValue() {
        const info = isTarget();
        return info.getValue ? info.getValue() : '';
      },
    };
    return loc;
  }

  const page = {
    url() {
      return currentUrl;
    },
    context() {
      return {
        browser() {
          if (opts.noBrowserObject) return null;
          return {
            browserType() {
              return { name: () => (opts.browserName !== undefined ? opts.browserName : 'firefox') };
            },
          };
        },
      };
    },
    on(type, handler) {
      if (!pageListeners.has(type)) pageListeners.set(type, new Set());
      pageListeners.get(type).add(handler);
    },
    off(type, handler) {
      const set = pageListeners.get(type);
      if (set) set.delete(handler);
    },
    async bringToFront() {
      bringToFrontCalls++;
      hasFocus = true;
      visibilityState = 'visible';
    },
    async goto(url) {
      gotoCalls++;
      currentUrl = opts.postGotoUrl !== undefined ? opts.postGotoUrl : url;
      screen = opts.postGotoScreen || 'home';
      resetDocumentWindow();
    },
    viewportSize() {
      return opts.viewportSize !== undefined ? opts.viewportSize : { width: 1280, height: 720 };
    },
    async waitForTimeout(ms) {
      if (opts.advanceClock) opts.advanceClock(ms);
    },
    isClosed() {
      return Boolean(opts.closed);
    },
    async screenshot(sOpts) {
      screenshotCalls.push(sOpts);
      if (opts.screenshotFails) throw new Error('screenshot failed');
    },
    async evaluate(fn, arg) {
      return withBrowserGlobals(() => fn(arg));
    },
    locator(selector) {
      if (selector === 'body') {
        return {
          async ariaSnapshot() {
            if (screen === 'account_guest') {
              return 'heading "Tài Khoản"\ntext "Bạn đang xem dưới dạng khách"\nbutton "Đăng Nhập / Đăng Ký"';
            }
            if (screen === 'login_dialog') {
              return 'dialog\ntextbox "Email"\ntextbox "Mật khẩu"\nbutton "Đăng Nhập"';
            }
            if (screen === 'home' && semanticsReady) {
              return 'tab "Tài Khoản"';
            }
            return '';
          },
        };
      }
      if (selector.includes('flt-semantics-placeholder')) {
        const ph = {
          first() {
            return ph;
          },
          async count() {
            return screen === 'home' ? 1 : 0;
          },
          async waitFor() {
            if (screen !== 'home') throw new Error('placeholder not attached');
          },
          async evaluate(fn) {
            return withBrowserGlobals(() => fn(placeholderEl));
          },
          async click() {
            throw new Error('Placeholder bootstrap should use evaluate(el => el.click()), not locator click');
          },
        };
        return ph;
      }
      throw new Error(`Unexpected selector in mock: ${selector}`);
    },
    getByRole(role, roleOpts = {}) {
      return makeRoleLocator(role, roleOpts.name);
    },
    _inspect: {
      getBringToFrontCalls: () => bringToFrontCalls,
      getGotoCalls: () => gotoCalls,
      getSubmitClicks: () => submitClicks,
      getScreenshots: () => screenshotCalls.slice(),
      getClickLog: () => clickLog.slice(),
      activePageListenerCount,
      activeDomListenerCount,
      cleanupGlobalPresent: () =>
        Object.prototype.hasOwnProperty.call(mockWindow, '__bh07FfInputProbeCleanup') ||
        Object.prototype.hasOwnProperty.call(mockWindow, '__bh07FfInputProbeState'),
    },
  };
  return page;
}

const results = [];
let failures = 0;

async function runControl(name, fn) {
  try {
    await fn();
    results.push({ name, status: 'PASS' });
    console.log(`${name} PASS`);
  } catch (err) {
    failures++;
    results.push({ name, status: 'FAIL', reason: err && err.message ? err.message : String(err) });
    console.log(`${name} FAIL: ${err && err.message ? err.message : String(err)}`);
  }
}

(async () => {
  await runControl('source_expression_and_static_safety', async () => {
    const src = loadProbeSource();
    const fn = compileProbe();
    assert.equal(typeof fn, 'function');

    // Never ship real credentials or DB mutations
    for (const forbidden of [
      'ownera@example.test',
      'cohosta@example.test',
      'membera@example.test',
      'guesta@example.test',
      'bh07-http-pass-123456',
      'require(',
      'import ',
      'process.',
      'setOffline(',
      'submit_payment',
      'confirm_payment',
      'complete_session',
      'dispatchEvent',
      'force: true',
      'force:true',
      'headless: true',
      'insertRule',
      'style.cssText',
      'HTMLElement.prototype',
      '/rest/v1/rpc/get_',
      '/rest/v1/rpc/list_',
      '/rest/v1/rpc/fetch_',
    ]) {
      assert(!src.includes(forbidden), `Forbidden token found in probe source: ${forbidden}`);
    }

    // Only semantics-placeholder bootstrap may call .click() inside DOM evaluate
    const domClickMatches = src.match(/=>\s*[a-zA-Z0-9_]+\.click\(\)/g) || [];
    assert.equal(domClickMatches.length, 1, 'Expected exactly one DOM el.click() for semantics bootstrap only');
    const idx = src.indexOf(domClickMatches[0]);
    const bootStart = src.indexOf('async function runSemanticsBootstrap()');
    const bootEnd = src.indexOf('async function countAuthStorageKeys()');
    assert(bootStart >= 0 && bootEnd > bootStart, 'Missing runSemanticsBootstrap boundaries');
    assert(idx > bootStart && idx < bootEnd, 'DOM el.click() must be inside runSemanticsBootstrap only');
    assert(src.slice(bootStart, bootEnd).includes('flt-semantics-placeholder'), 'runSemanticsBootstrap must target flt-semantics-placeholder');
  });

  await runControl('guard_invalid_focus_and_render_mode', async () => {
    const badFocusFn = compileProbe({ focusMode: 'bad_focus' });
    const p1 = createMockPage();
    await assert.rejects(badFocusFn(p1), /Guard failed: FOCUS_MODE/);
    assert.equal(p1._inspect.getGotoCalls(), 0);

    const badRenderFn = compileProbe({ renderMode: 'bad_render' });
    const p2 = createMockPage();
    await assert.rejects(badRenderFn(p2), /Guard failed: RENDER_MODE/);
    assert.equal(p2._inspect.getGotoCalls(), 0);
  });

  await runControl('guard_external_and_invalid_initial_origin', async () => {
    const fn = compileProbe();
    const extPage = createMockPage({ initialUrl: 'https://example.com/?secret=1' });
    await assert.rejects(fn(extPage), /Guard failed: initial page origin/);
    assert.equal(extPage._inspect.getGotoCalls(), 0);
    assert.equal(extPage._inspect.getBringToFrontCalls(), 0);
    assert.equal(extPage._inspect.activePageListenerCount(), 0);

    const badUrlPage = createMockPage({ initialUrl: 'not-a-valid-url' });
    await assert.rejects(fn(badUrlPage), /Guard failed: invalid initial page URL/);
    assert.equal(badUrlPage._inspect.getGotoCalls(), 0);
  });

  await runControl('guard_non_firefox_and_headless_ua', async () => {
    const fn = compileProbe();
    const chromePage = createMockPage({ browserName: 'chromium' });
    await assert.rejects(fn(chromePage), /Guard failed: Firefox browser required/);
    assert.equal(chromePage._inspect.getGotoCalls(), 0);

    const headlessUaPage = createMockPage({
      noBrowserObject: true,
      userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) HeadlessFirefox/156.0',
    });
    await assert.rejects(fn(headlessUaPage), /Guard failed: Firefox browser required/);
    assert.equal(headlessUaPage._inspect.getGotoCalls(), 0);
  });

  await runControl('guard_post_goto_origin_escape_with_cleanup', async () => {
    const fn = compileProbe();
    const escapePage = createMockPage({ postGotoUrl: 'https://evil.example/hijack' });
    await assert.rejects(fn(escapePage), /Guard failed: page origin/);
    assert.equal(escapePage._inspect.activePageListenerCount(), 0);
    assert.equal(escapePage._inspect.activeDomListenerCount(), 0);
    assert.equal(escapePage._inspect.cleanupGlobalPresent(), false);
  });

  await runControl('focus_selection_baseline_vs_bring_to_front', async () => {
    const baselineFn = compileProbe({ focusMode: 'baseline' });
    const basePage = createMockPage({ initialHasFocus: false });
    const baseRes = await baselineFn(basePage);
    assert.equal(baseRes.ok, true);
    assert.equal(baseRes.status, 'PASS');
    assert.equal(baseRes.config.focus_mode, 'baseline');
    assert.equal(baseRes.config.bring_to_front_calls, 0);
    assert.equal(basePage._inspect.getBringToFrontCalls(), 0);
    assert.equal(baseRes.after_bring_to_front_state, null);

    const focusedFn = compileProbe({ focusMode: 'bring_to_front' });
    const focusedPage = createMockPage({ initialHasFocus: false });
    const focusedRes = await focusedFn(focusedPage);
    assert.equal(focusedRes.ok, true);
    assert.equal(focusedRes.status, 'PASS');
    assert.equal(focusedRes.config.focus_mode, 'bring_to_front');
    assert(focusedRes.config.bring_to_front_calls >= 1);
    assert(focusedPage._inspect.getBringToFrontCalls() >= 1);
    assert.equal(focusedRes.after_bring_to_front_state.has_focus, true);
  });

  await runControl('physical_actions_and_semantics_bootstrap_isolation', async () => {
    const fn = compileProbe({ focusMode: 'baseline', renderMode: 'software' });
    const page = createMockPage({ initialHasFocus: true });
    const res = await fn(page);

    assert.equal(res.diagnosticOnly, true);
    assert.equal(res.ok, true);
    assert.equal(res.status, 'PASS');
    assert.equal(res.config.render_mode, 'software');
    assert.equal(res.config.no_submit, true);
    assert.equal(res.safety_checks.no_submit_verified, true);
    assert.equal(page._inspect.getSubmitClicks(), 0);

    // Semantics bootstrap isolated from app-action trusted counters
    assert.equal(res.semantics_bootstrap.status, 'PASS');
    assert.equal(res.semantics_bootstrap.placeholder_clicked, true);
    assert.equal(res.semantics_bootstrap.account_tab_visible, true);

    const clicks = page._inspect.getClickLog();
    assert.deepEqual(clicks, [
      { target: 'semantics_placeholder', via: 'dom_evaluate' },
      { target: 'account_tab', via: 'locator.click' },
      { target: 'login_cta', via: 'locator.click' },
      { target: 'email_field', via: 'locator.click' },
      { target: 'password_field', via: 'locator.click' },
    ]);

    assert(res.steps.account_tab_click.event_delta.click_trusted >= 1);
    assert(res.steps.account_tab_click.event_delta.pointerdown_trusted >= 1);
    assert.equal(res.steps.email_input.value_retained, true);
    assert.equal(res.steps.password_input.value_retained, true);
    assert.equal(res.steps.post_input_tab_blur.email_retained_after_blur, true);
    assert.equal(res.steps.post_input_tab_blur.password_retained_after_blur, true);
    assert.equal(res.steps.post_input_tab_blur.raf_commit, true);

    const shots = page._inspect.getScreenshots();
    assert.equal(shots.length, 2);
    for (const s of shots) {
      assert(s.path.startsWith('.build/bh07-firefox-headed-input/software-baseline-'));
      assert(s.path.endsWith('.png'));
      assert(!s.path.includes('..'));
    }
  });

  await runControl('failure_account_click_timeout_not_pass', async () => {
    const fn = compileProbe();
    const page = createMockPage({ accountClickTimeout: true, occludeTarget: true });
    const res = await fn(page);

    assert.equal(res.ok, false);
    assert.equal(res.status, 'FAIL');
    assert.equal(res.failure_stage, 'account_tab_click');
    assert.equal(res.steps.account_tab_click.status, 'FAIL');
    assert.equal(res.steps.account_tab_click.pre_state.target.element_from_point.status, 'other_element');
    assert.equal(res.steps.account_tab_click.pre_state.target.element_from_point.tag, 'flt-glass-pane');
    assert.equal(res.steps.account_guest_view.status, 'NOT_RUN');
    assert.equal(res.steps.email_input.status, 'NOT_RUN');
    assert.equal(page._inspect.activePageListenerCount(), 0);
    assert.equal(page._inspect.activeDomListenerCount(), 0);
  });

  await runControl('failure_account_click_no_navigation_not_pass', async () => {
    const fn = compileProbe();
    await withFastMockClock(async advanceClock => {
      const page = createMockPage({ accountClickNoNav: true, advanceClock });
      const res = await fn(page);
      assert.equal(res.ok, false);
      assert.equal(res.status, 'FAIL');
      assert.equal(res.failure_stage, 'account_guest_view');
      assert.equal(res.steps.account_tab_click.status, 'PASS');
      assert.equal(res.steps.account_guest_view.status, 'FAIL');
      assert.equal(res.steps.login_cta_click.status, 'NOT_RUN');
    });
  });

  await runControl('failure_login_cta_no_dialog_not_pass', async () => {
    const fn = compileProbe();
    await withFastMockClock(async advanceClock => {
      const page = createMockPage({ loginCtaNoDialog: true, advanceClock });
      const res = await fn(page);
      assert.equal(res.ok, false);
      assert.equal(res.status, 'FAIL');
      assert.equal(res.failure_stage, 'login_dialog_open');
      assert.equal(res.steps.login_cta_click.status, 'PASS');
      assert.equal(res.steps.login_dialog_open.status, 'FAIL');
      assert.equal(res.steps.email_input.status, 'NOT_RUN');
    });
  });

  await runControl('failure_synthetic_value_not_retained_not_pass', async () => {
    const fn = compileProbe();
    const page = createMockPage({ emailValueNotRetained: true });
    const res = await fn(page);

    assert.equal(res.ok, false);
    assert.equal(res.status, 'FAIL');
    assert.equal(res.failure_stage, 'email_input');
    assert.equal(res.error_code, 'EMAIL_VALUE_NOT_RETAINED');
    assert.equal(res.steps.email_input.status, 'FAIL');
    assert.equal(res.steps.email_input.value_retained, false);
    assert.equal(res.steps.email_input.attempts.length, 2);
    assert.equal(res.steps.password_input.status, 'NOT_RUN');
  });

  await runControl('failure_raf_commit_timeout_not_pass', async () => {
    const fn = compileProbe();

    // Global stalled rAF fails at the first post-click commit check (account_tab_click)
    const globalStallPage = createMockPage({ rafStalled: true });
    const globalRes = await fn(globalStallPage);
    assert.equal(globalRes.ok, false);
    assert.equal(globalRes.status, 'FAIL');
    assert.equal(globalRes.failure_stage, 'account_tab_click');
    assert.equal(globalRes.error_code, 'ACCOUNT_TAB_POST_CLICK_RAF_TIMEOUT');
    assert.equal(globalRes.steps.account_tab_click.post_state.raf_commit, false);

    // Input-stage stalled rAF (5th Promise.race inside evaluate = email pre-type settle) fails at email_input
    const inputStallPage = createMockPage({
      semanticsAlreadyReady: true,
      promiseRaceOverrides: { 5: false },
    });
    const inputRes = await fn(inputStallPage);
    assert.equal(inputRes.ok, false);
    assert.equal(inputRes.status, 'FAIL');
    assert.equal(inputRes.failure_stage, 'email_input');
    assert.equal(inputRes.error_code, 'EMAIL_PRE_TYPE_RAF_TIMEOUT');
    assert.equal(inputRes.steps.email_input.attempts[0].pre_type_raf_commit, false);
  });

  await runControl('failure_unexpected_mutation_and_auth_storage_not_pass', async () => {
    const fn = compileProbe();
    const reqPage = createMockPage({ emitAuthPostAfterType: true });
    const reqRes = await fn(reqPage);
    assert.equal(reqRes.ok, false);
    assert.equal(reqRes.status, 'FAIL');
    assert.equal(reqRes.safety_checks.auth_or_mutation_request_count, 1);

    const storePage = createMockPage({
      localStorageEntries: { 'sb-local-auth-token': 'SECRET_JWT_VALUE' },
    });
    const storeRes = await fn(storePage);
    assert.equal(storeRes.ok, false);
    assert.equal(storeRes.status, 'FAIL');
    assert.equal(storeRes.safety_checks.auth_storage_key_count, 1);
    assert(!JSON.stringify(storeRes).includes('SECRET_JWT_VALUE'));
  });

  await runControl('bounded_and_redacted_metadata', async () => {
    const fn = compileProbe();
    const failPage = createMockPage({
      initialUrl: 'http://127.0.0.1:8088/?token=SECRET_QUERY_TOKEN#/',
      postGotoUrl: 'http://127.0.0.1:8088/?token=SECRET_QUERY_TOKEN#/',
      customTag: 'x-very-long-unbounded-custom-tag-name-that-should-be-sanitized',
      customRole: 'secret-role-xyz',
      occludeTarget: false,
      highEventVolume: true,
      accountClickTimeout: true,
      rawExceptionText: 'RAW_PLAYWRIGHT_ERROR_WITH_SECRET_TEXT',
      localStorageEntries: { 'sb-proj-auth-token': 'SECRET_JWT_VALUE' },
    });
    const failRes = await fn(failPage);
    assert.equal(failRes.ok, false);
    assert.equal(failRes.status, 'FAIL');
    assert.equal(failRes.observer_summary.capped, true);
    assert.equal(failRes.observer_summary.totals.pointerdown_trusted, 10000);
    assert.equal(failRes.steps.account_tab_click.pre_state.target.element_from_point.tag, 'other');
    assert.equal(failRes.steps.account_tab_click.pre_state.target.element_from_point.role, 'other');

    const consolePage = createMockPage({ emitConsoleAndPageError: true });
    const consoleRes = await fn(consolePage);
    assert.equal(consoleRes.ok, true);
    assert.equal(consoleRes.recorded_console_summary.error_count, 2);
    assert.equal(consoleRes.recorded_console_summary.warning_count, 2);
    assert.equal(consoleRes.recorded_console_summary.pageerror_count, 2);

    const serialized = JSON.stringify({ failRes, consoleRes });
    for (const secret of [
      'SECRET_QUERY_TOKEN',
      'SECRET_JWT_VALUE',
      'RAW_PLAYWRIGHT_ERROR_WITH_SECRET_TEXT',
      'SECRET_CONSOLE_TEXT',
      'SECRET_WARNING_TEXT',
      'SECRET_PAGEERROR_TEXT',
      'probe-synthetic@example.invalid',
      'synthetic-probe-pass',
      'x-very-long-unbounded',
      'secret-role-xyz',
    ]) {
      assert(!serialized.includes(secret), `Telemetry leaked sensitive/unbounded string: ${secret}`);
    }
  });

  await runControl('viewport_null_and_shadow_dom_element_from_point', async () => {
    const fn = compileProbe();
    let shadowInnerEl = null;
    const shadowHost = {
      tagName: 'flutter-view',
      contains: () => false,
      getAttribute: () => null,
      shadowRoot: {
        get activeElement() {
          return shadowInnerEl;
        },
        elementFromPoint() {
          return shadowInnerEl;
        },
      },
    };
    const page = createMockPage({
      viewportSize: null,
      shadowHostTarget: shadowHost,
    });
    // In shadow-host test, expose inner element matching locator target
    const origGetByRole = page.getByRole.bind(page);
    page.getByRole = (role, rOpts) => {
      const loc = origGetByRole(role, rOpts);
      const origEval = loc.evaluate.bind(loc);
      loc.evaluate = async (evalFn, arg) => {
        return origEval((el, a) => {
          shadowInnerEl = el;
          return evalFn(el, a);
        }, arg);
      };
      return loc;
    };
    const res = await fn(page);
    assert.equal(res.ok, true);
    assert.equal(res.initial_page_state.playwright_viewport, null);
    assert.equal(res.initial_page_state.window_inner.width, 1280);
    assert.equal(res.steps.account_tab_click.pre_state.target.element_from_point.top_tag, 'flutter-view');
    assert.equal(res.steps.account_tab_click.pre_state.target.element_from_point.tag, 'flt-semantics');
    assert.equal(res.steps.account_tab_click.pre_state.target.element_from_point.shadow_depth, 1);
    assert.equal(res.steps.account_tab_click.pre_state.target.element_from_point.hit_matches_target, true);
  });

  await runControl('failure_semantics_bootstrap_timeout_not_pass', async () => {
    const fn = compileProbe();
    await withFastMockClock(async advanceClock => {
      const page = createMockPage({ bootstrapFails: true, advanceClock });
      const res = await fn(page);
      assert.equal(res.ok, false);
      assert.equal(res.status, 'FAIL');
      assert.equal(res.failure_stage, 'semantics_bootstrap');
      assert.equal(res.error_code, 'BOOTSTRAP_TIMEOUT');
      assert.equal(res.semantics_bootstrap.status, 'FAIL');
      assert.equal(res.observer_summary.installed, false);
      assert.equal(res.observer_summary.cleaned_up, true);
      assert.equal(res.steps.account_tab_click.status, 'NOT_RUN');
    });
  });

  await runControl('ff1_rejects_ungrounded_prefix_rpcs_and_external_nonread', async () => {
    const fn = compileProbe();
    const cases = [
      { method: 'POST', url: 'http://127.0.0.1:54321/rest/v1/rpc/get_unreviewed_mutation', secret: 'get_unreviewed_mutation' },
      { method: 'POST', url: 'http://127.0.0.1:54321/rest/v1/rpc/list_unreviewed_mutation', secret: 'list_unreviewed_mutation' },
      { method: 'POST', url: 'http://127.0.0.1:54321/rest/v1/rpc/fetch_unreviewed_mutation', secret: 'fetch_unreviewed_mutation' },
      { method: 'POST', url: 'https://external.invalid/receive', secret: 'external.invalid' },
      { method: 'PUT', url: 'http://127.0.0.1:8088/local-write?secret=1', secret: 'local-write' },
      { method: 'POST', url: 'not-a-valid-url-secret', secret: 'not-a-valid-url-secret' },
    ];
    for (const tc of cases) {
      const page = createMockPage({ emitRequestOnAccountClick: { method: tc.method, url: tc.url } });
      const res = await fn(page);
      assert.equal(res.ok, false, `Expected FAIL for ${tc.method} ${tc.url}`);
      assert.equal(res.status, 'FAIL', `Expected FAIL status for ${tc.method} ${tc.url}`);
      assert.equal(res.safety_checks.auth_or_mutation_request_count, 1);
      assert(!JSON.stringify(res).includes(tc.secret), `Leaked URL/path fragment ${tc.secret}`);
    }

    const readOnlyPage = createMockPage({ emitReadOnlyMethodsOnAccountClick: true });
    const readOnlyRes = await fn(readOnlyPage);
    assert.equal(readOnlyRes.ok, true);
    assert.equal(readOnlyRes.safety_checks.auth_or_mutation_request_count, 0);
  });

  await runControl('ff2_exact_first_promise_race_false_mutant_and_login_click_variant', async () => {
    const fn = compileProbe();

    // Exact reviewer mutant: semanticsAlreadyReady so 1st Promise.race is account_tab_click RAF check -> false
    const accountFalsePage = createMockPage({
      semanticsAlreadyReady: true,
      promiseRaceOverrides: { 1: false },
    });
    const accountFalseRes = await fn(accountFalsePage);
    assert.equal(accountFalseRes.ok, false);
    assert.equal(accountFalseRes.status, 'FAIL');
    assert.equal(accountFalseRes.failure_stage, 'account_tab_click');
    assert.equal(accountFalseRes.steps.account_tab_click.status, 'FAIL');
    assert.equal(accountFalseRes.steps.account_tab_click.post_state.raf_commit, false);
    assert.equal(accountFalseRes.steps.account_tab_click.post_state.raf_commit_state, 'timed_out');
    assert.equal(accountFalseRes.steps.account_guest_view.status, 'NOT_RUN');

    // Login-click variant: 3rd Promise.race (login_cta_click post-click RAF check) -> false
    const loginFalsePage = createMockPage({
      semanticsAlreadyReady: true,
      promiseRaceOverrides: { 3: false },
    });
    const loginFalseRes = await fn(loginFalsePage);
    assert.equal(loginFalseRes.ok, false);
    assert.equal(loginFalseRes.status, 'FAIL');
    assert.equal(loginFalseRes.failure_stage, 'login_cta_click');
    assert.equal(loginFalseRes.steps.account_tab_click.status, 'PASS');
    assert.equal(loginFalseRes.steps.account_guest_view.status, 'PASS');
    assert.equal(loginFalseRes.steps.login_cta_click.status, 'FAIL');
    assert.equal(loginFalseRes.steps.login_cta_click.post_state.raf_commit, false);
    assert.equal(loginFalseRes.steps.login_cta_click.post_state.raf_commit_state, 'timed_out');
    assert.equal(loginFalseRes.steps.login_dialog_open.status, 'NOT_RUN');

    // Unknown RAF check outcomes (undefined or rejected) must also fail measured click and overall probe
    for (const overrideVal of [undefined, 'reject']) {
      const accUnknownPage = createMockPage({
        semanticsAlreadyReady: true,
        promiseRaceOverrides: { 1: overrideVal },
      });
      const accUnknownRes = await fn(accUnknownPage);
      assert.equal(accUnknownRes.ok, false);
      assert.equal(accUnknownRes.status, 'FAIL');
      assert.equal(accUnknownRes.steps.account_tab_click.status, 'FAIL');
      assert.equal(accUnknownRes.steps.account_tab_click.post_state.raf_commit, false);
      assert.equal(accUnknownRes.steps.account_tab_click.post_state.raf_commit_state, 'unknown');

      const loginUnknownPage = createMockPage({
        semanticsAlreadyReady: true,
        promiseRaceOverrides: { 3: overrideVal },
      });
      const loginUnknownRes = await fn(loginUnknownPage);
      assert.equal(loginUnknownRes.ok, false);
      assert.equal(loginUnknownRes.status, 'FAIL');
      assert.equal(loginUnknownRes.steps.login_cta_click.status, 'FAIL');
      assert.equal(loginUnknownRes.steps.login_cta_click.post_state.raf_commit, false);
      assert.equal(loginUnknownRes.steps.login_cta_click.post_state.raf_commit_state, 'unknown');
    }

    // Snapshot / dialog post-state RAF=false must also fail cleanly
    const guestViewFalsePage = createMockPage({
      semanticsAlreadyReady: true,
      promiseRaceOverrides: { 2: false },
    });
    const guestViewFalseRes = await fn(guestViewFalsePage);
    assert.equal(guestViewFalseRes.ok, false);
    assert.equal(guestViewFalseRes.status, 'FAIL');
    assert.equal(guestViewFalseRes.failure_stage, 'account_guest_view');
    assert.equal(guestViewFalseRes.steps.account_guest_view.status, 'FAIL');

    const dlgFalsePage = createMockPage({
      semanticsAlreadyReady: true,
      promiseRaceOverrides: { 4: false },
    });
    const dlgFalseRes = await fn(dlgFalsePage);
    assert.equal(dlgFalseRes.ok, false);
    assert.equal(dlgFalseRes.status, 'FAIL');
    assert.equal(dlgFalseRes.failure_stage, 'login_dialog_open');
    assert.equal(dlgFalseRes.steps.login_dialog_open.status, 'FAIL');
  });

  await runControl('observer_cleanup_and_cleanup_error_propagation', async () => {
    const fn = compileProbe();

    const passPage = createMockPage();
    const passRes = await fn(passPage);
    assert.equal(passRes.observer_summary.cleaned_up, true);
    assert.equal(passPage._inspect.activePageListenerCount(), 0);
    assert.equal(passPage._inspect.activeDomListenerCount(), 0);
    assert.equal(passPage._inspect.cleanupGlobalPresent(), false);

    const errPage = createMockPage({ cleanupThrows: true });
    await assert.rejects(fn(errPage), /Cleanup failed:/);
    assert.equal(errPage._inspect.activePageListenerCount(), 0);
  });

  console.log(JSON.stringify({ total_controls: results.length, failed_controls: failures }));
  if (failures > 0) {
    process.exitCode = 1;
  }
})().catch(err => {
  console.error(err && err.message ? err.message : String(err));
  process.exitCode = 1;
});
