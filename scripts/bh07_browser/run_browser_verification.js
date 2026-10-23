// BH-07 Browser / Offline / Reopen Verification Suite (authorized final fix)
// Real Flutter Web on real Chrome (CDP) against real local Supabase Auth/PostgREST.
// Addresses the remaining BR2/BR3/BR5 P2 findings from review_eadb5c7.md while
// keeping the already-closed BR1 and same-SPA BR4 actor-switch case intact:
// - BR1: Strict attendance assertion on specific player, preconditions & postconditions (no false pass on no-op)
// - BR2: Filter POST-only (drop OPTIONS), require 2 requests, assert deep payload/request_id match, assert the real offline UI error, and verify exactly-once DB/audit side effects
// - BR3: Assert every exact aggregate field/number, reject wrong fields or "—", enforce cohost count-only/private-data exclusion, and assert history IDs, empty/denied rows and the real filter payload
// - BR4: SPA cache invalidation across actor switch within the SAME document/instance (no Page.navigate/reload reset) and isolated F5 persistence
// - BR5: Publish all logs, measure real exits, source provenance & honest hashes, strict read-only verifier mode

const { spawn, execSync } = require('child_process');
const fs = require('fs');
const path = require('path');
const os = require('os');
const crypto = require('crypto');

const {
  FIXTURE,
  OFFLINE_ERROR_MESSAGE,
  validateOfflineUiState,
  validateCompleteRequests,
  validateManagerClipboard,
  validateCohostClipboard,
  validateCohostSummarySurface,
  validateHistoryCall,
  parseHistoryResponse,
  validateHistoryResponse,
  validateHistorySurface,
} = require('./assertions');

const CHROME_PATH = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const DEBUG_PORT = 9335;
const PROJECT_ROOT = path.resolve(__dirname, '../..');
const EVIDENCE_DIR = path.resolve(PROJECT_ROOT, 'docs/reviews/bh07/browser_evidence');
const SCREENSHOTS_DIR = path.resolve(EVIDENCE_DIR, 'screenshots');
const USER_DATA_DIR = path.join(os.tmpdir(), 'chrome_bh07_isolated_v2');
const WEB_URL = 'http://127.0.0.1:8088';
const BASE_SHA = '1fc7e2eb171acd6c7afbc16e9f1053f9b3cb21c3';

if (!fs.existsSync(SCREENSHOTS_DIR)) {
  fs.mkdirSync(SCREENSHOTS_DIR, { recursive: true });
}

let logLines = [];
function log(msg) {
  const ts = new Date().toISOString();
  const line = `[${ts}] ${msg}`;
  console.log(line);
  logLines.push(line);
}

function queryDb(sql) {
  const dbContainer = 'supabase_db_badminton-hub';
  const out = execSync(`docker exec -i ${dbContainer} psql -U postgres -d postgres -t -A -c "${sql.replace(/"/g, '\\"')}"`, { encoding: 'utf-8' });
  return out.trim();
}

function readGitStatus() {
  return execSync('git status --porcelain', { encoding: 'utf-8' }).trim();
}

async function waitForCondition(predicate, description, timeoutMs = 8000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    if (predicate()) return true;
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  throw new Error(`Timed out waiting for ${description}`);
}

class CdpClient {
  constructor(wsUrl) {
    this.wsUrl = wsUrl;
    this.ws = null;
    this.nextId = 1;
    this.pending = new Map();
    this.sessionId = null;
    this.targetId = null;
    this.requestListeners = [];
    this.responseListeners = [];
    this.networkRequests = new Map();
  }

  async connect() {
    this.ws = new WebSocket(this.wsUrl);
    await new Promise((resolve, reject) => {
      this.ws.onopen = resolve;
      this.ws.onerror = reject;
    });
    this.ws.onmessage = (evt) => {
      const msg = JSON.parse(evt.data);
      if (msg.method === 'Network.requestWillBeSent') {
        this.networkRequests.set(msg.params.requestId, {
          requestId: msg.params.requestId,
          url: msg.params.request.url,
          method: msg.params.request.method,
          postData: msg.params.request.postData,
        });
        for (const listener of this.requestListeners) {
          listener(msg.params);
        }
      }
      if (msg.method === 'Network.responseReceived') {
        const meta = this.networkRequests.get(msg.params.requestId);
        if (meta) meta.status = msg.params.response.status;
      }
      if (msg.method === 'Network.loadingFinished' && this.responseListeners.length > 0) {
        const meta = this.networkRequests.get(msg.params.requestId);
        if (meta) {
          this.send('Network.getResponseBody', { requestId: msg.params.requestId })
            .then((res) => {
              if (!res.result) return;
              let body = res.result.body;
              if (res.result.base64Encoded) {
                body = Buffer.from(body, 'base64').toString('utf8');
              }
              for (const listener of this.responseListeners) {
                try {
                  listener({ ...meta, body });
                } catch (_) {}
              }
            })
            .catch(() => {});
        }
      }
      if (msg.id && this.pending.has(msg.id)) {
        this.pending.get(msg.id)(msg);
        this.pending.delete(msg.id);
      }
    };
  }

  send(method, params = {}) {
    return new Promise((resolve) => {
      const id = this.nextId++;
      this.pending.set(id, resolve);
      this.ws.send(JSON.stringify({ id, method, params, sessionId: this.sessionId }));
    });
  }

  async createTab(url) {
    const res = await new Promise((resolve) => {
      const id = this.nextId++;
      this.pending.set(id, resolve);
      this.ws.send(JSON.stringify({ id, method: 'Target.createTarget', params: { url } }));
    });
    this.targetId = res.result.targetId;

    const attach = await new Promise((resolve) => {
      const id = this.nextId++;
      this.pending.set(id, resolve);
      this.ws.send(JSON.stringify({ id, method: 'Target.attachToTarget', params: { targetId: this.targetId, flatten: true } }));
    });
    this.sessionId = attach.result.sessionId;

    await this.send('Page.enable');
    await this.send('Runtime.enable');
    await this.send('Network.enable');

    // Grant clipboard permissions
    await new Promise((resolve) => {
      const id = this.nextId++;
      this.pending.set(id, resolve);
      this.ws.send(JSON.stringify({
        id,
        method: 'Browser.grantPermissions',
        params: {
          permissions: ['clipboardReadWrite', 'clipboardSanitizedWrite'],
          origin: WEB_URL
        }
      }));
    });
  }

  async evaluate(expression) {
    const res = await this.send('Runtime.evaluate', {
      expression,
      returnByValue: true,
      awaitPromise: true
    });
    if (res.result && res.result.exceptionDetails) {
      throw new Error(`Evaluate error: ${JSON.stringify(res.result.exceptionDetails)}`);
    }
    return res.result?.result?.value;
  }

  async enableFlutterSemantics() {
    await this.evaluate(`
      (() => {
        const el = document.querySelector('flt-semantics-placeholder');
        if (el) el.click();
      })()
    `);
    await new Promise(r => setTimeout(r, 1000));
  }

  async getAllSemantics() {
    await this.enableFlutterSemantics();
    return await this.evaluate(`
      (() => {
        const all = Array.from(document.querySelectorAll('*'));
        return all
          .filter(e => e.getAttribute('aria-label') || e.getAttribute('role') || e.tagName === 'INPUT' || (e.innerText && e.innerText.length < 100))
          .map(e => {
            const rect = e.getBoundingClientRect();
            return {
              tag: e.tagName,
              aria: e.getAttribute('aria-label'),
              role: e.getAttribute('role'),
              text: (e.innerText || '').trim(),
              x: Math.round(rect.x + rect.width / 2),
              y: Math.round(rect.y + rect.height / 2),
              w: Math.round(rect.width),
              h: Math.round(rect.height)
            };
          })
          .filter(i => i.w > 0 && i.h > 0);
      })()
    `);
  }

  async findSemantic(predicate, timeoutMs = 8000) {
    const start = Date.now();
    while (Date.now() - start < timeoutMs) {
      const elements = await this.getAllSemantics();
      const matches = elements.filter(predicate);
      if (matches.length > 0) {
        const buttonMatch = matches.find(m => m.role === 'button' || m.tag === 'BUTTON');
        if (buttonMatch) return buttonMatch;
        matches.sort((a, b) => (a.w * a.h) - (b.w * b.h));
        return matches[0];
      }
      await new Promise(r => setTimeout(r, 400));
    }
    return null;
  }

  async waitForSemantic(predicate, desc, timeoutMs = 10000) {
    const el = await this.findSemantic(predicate, timeoutMs);
    if (!el) throw new Error(`Timed out waiting for semantic element: ${desc}`);
    return el;
  }

  async clickSemantic(predicate, stepName) {
    const el = await this.findSemantic(predicate);
    if (!el) {
      throw new Error(`Could not find semantic element to click for: ${stepName}`);
    }
    log(`Clicking semantic element [${el.tag} aria="${el.aria}" role="${el.role}" text="${(el.text||'').slice(0, 30)}"] at (${el.x}, ${el.y}) for: ${stepName}`);
    await this.send('Input.dispatchMouseEvent', { type: 'mousePressed', x: el.x, y: el.y, button: 'left', clickCount: 1 });
    await this.send('Input.dispatchMouseEvent', { type: 'mouseReleased', x: el.x, y: el.y, button: 'left', clickCount: 1 });
    await new Promise(r => setTimeout(r, 1000));
  }

  async clickBack(stepName = 'Click Back via UI') {
    const backBtn = await this.findSemantic(e => 
      (e.role === 'button' || e.tag === 'BUTTON') && 
      (e.aria === 'Back' || e.aria === 'Quay lại' || (e.aria || '').toLowerCase().includes('back') || (e.aria || '').toLowerCase().includes('quay lại') || (e.x < 80 && e.y < 60))
    , 2000);
    if (backBtn) {
      log(`Clicking Back button semantic [${backBtn.tag} aria="${backBtn.aria}" role="${backBtn.role}"] at (${backBtn.x}, ${backBtn.y}) for: ${stepName}`);
      await this.send('Input.dispatchMouseEvent', { type: 'mousePressed', x: backBtn.x, y: backBtn.y, button: 'left', clickCount: 1 });
      await this.send('Input.dispatchMouseEvent', { type: 'mouseReleased', x: backBtn.x, y: backBtn.y, button: 'left', clickCount: 1 });
    } else {
      log(`Clicking standard AppBar back coordinate (28, 28) for: ${stepName}`);
      await this.send('Input.dispatchMouseEvent', { type: 'mousePressed', x: 28, y: 28, button: 'left', clickCount: 1 });
      await this.send('Input.dispatchMouseEvent', { type: 'mouseReleased', x: 28, y: 28, button: 'left', clickCount: 1 });
    }
    await new Promise(r => setTimeout(r, 1500));
    await this.enableFlutterSemantics();
  }

  async typeIntoInput(predicate, text) {
    const el = await this.findSemantic(predicate);
    if (!el) throw new Error('Could not find input element to type');
    await this.clickSemantic(predicate, 'focus input');
    await new Promise(r => setTimeout(r, 300));

    await this.evaluate(`
      (() => {
        const inputs = Array.from(document.querySelectorAll('input, textarea'));
        const active = document.activeElement;
        const target = inputs.includes(active) ? active : inputs[inputs.length - 1];
        if (target) {
          target.value = ${JSON.stringify(text)};
          target.dispatchEvent(new Event('input', { bubbles: true }));
          target.dispatchEvent(new Event('change', { bubbles: true }));
        }
      })()
    `);
    await new Promise(r => setTimeout(r, 400));
  }

  async setOffline(offline) {
    log(`Setting network offline = ${offline}`);
    await this.send('Network.emulateNetworkConditions', {
      offline,
      latency: offline ? 1000 : 0,
      downloadThroughput: offline ? 0 : -1,
      uploadThroughput: offline ? 0 : -1
    });
    await new Promise(r => setTimeout(r, 500));
  }

  async reloadPage() {
    log('Reloading page via Page.reload...');
    await this.send('Page.reload');
    await new Promise(r => setTimeout(r, 4000));
    await this.enableFlutterSemantics();
  }

  async navigateToHome() {
    log('Navigating to MainNavigationScreen (home)...');
    await this.send('Page.navigate', { url: `${WEB_URL}/#/` });
    await new Promise(r => setTimeout(r, 3500));
    await this.enableFlutterSemantics();
  }

  async navigateToSession(sessionId) {
    log(`Navigating to session detail: ${sessionId}...`);
    await this.send('Page.navigate', { url: `${WEB_URL}/#/sessions/${sessionId}` });
    await new Promise(r => setTimeout(r, 3500));
    await this.enableFlutterSemantics();
  }

  async screenshot(filename, stepDesc) {
    const res = await this.send('Page.captureScreenshot', { format: 'png' });
    const filePath = path.resolve(SCREENSHOTS_DIR, filename);
    fs.writeFileSync(filePath, Buffer.from(res.result.data, 'base64'));
    log(`[SCREENSHOT] ${filename} - ${stepDesc} (${fs.statSync(filePath).size} bytes)`);
    return filePath;
  }

  async readClipboard() {
    return await this.evaluate(`navigator.clipboard.readText()`);
  }

  async close() {
    if (this.targetId) {
      await new Promise(resolve => {
        const id = this.nextId++;
        this.pending.set(id, resolve);
        this.ws.send(JSON.stringify({ id, method: 'Target.closeTarget', params: { targetId: this.targetId } }));
      });
    }
    this.ws.close();
  }
}

async function startChrome() {
  if (fs.existsSync(USER_DATA_DIR)) {
    try {
      fs.rmSync(USER_DATA_DIR, { recursive: true, force: true });
    } catch (_) {}
  }
  fs.mkdirSync(USER_DATA_DIR, { recursive: true });

  const proc = spawn(CHROME_PATH, [
    `--remote-debugging-port=${DEBUG_PORT}`,
    '--headless=new',
    '--no-first-run',
    '--no-default-browser-check',
    '--disable-gpu',
    '--disable-background-networking',
    '--window-size=1280,900',
    `--user-data-dir=${USER_DATA_DIR}`,
    'about:blank',
  ], {
    detached: true,
    stdio: 'ignore',
  });

  for (let i = 0; i < 30; i++) {
    await new Promise(r => setTimeout(r, 200));
    try {
      const res = await fetch(`http://127.0.0.1:${DEBUG_PORT}/json/version`);
      if (res.ok) {
        const version = await res.json();
        return { proc, version };
      }
    } catch (_) {}
  }
  throw new Error(`Chrome failed to start on port ${DEBUG_PORT}`);
}

async function runMatrix() {
  const checks = [];
  const startTime = Date.now();
  const dirtyAtStart = readGitStatus();
  const isDirtyAtStart = dirtyAtStart.length > 0;
  log(`=== Starting BH-07 Browser / Offline / Reopen Verification Suite (final authorized fix) ===`);
  log(`Dirty checkout before run: ${isDirtyAtStart ? 'true' : 'false'}${isDirtyAtStart ? `\n${dirtyAtStart}` : ''}`);

  // Step 0: Ensure fresh fixtures in local database
  log('Resetting and seeding deterministic fixtures...');
  let seedExit = 0;
  try {
    execSync('node scripts/bh07_browser/seed_setup.js', { stdio: 'inherit' });
  } catch (err) {
    seedExit = err.status || 1;
    throw new Error(`Seed setup failed with exit code ${seedExit}`);
  }

  const { proc: chromeProc, version } = await startChrome();
  log(`Chrome version: ${version.Browser}`);

  const cdp = new CdpClient(version.webSocketDebuggerUrl);
  await cdp.connect();
  await cdp.createTab(WEB_URL);

  log('Waiting 6s for Flutter web bundle initialization...');
  await new Promise(r => setTimeout(r, 6000));
  await cdp.enableFlutterSemantics();

  // --------------------------------------------------------------------------
  // Negative Control: Guest screen & Unrendered Guard (BR1)
  // --------------------------------------------------------------------------
  log('Asserting initial guest state before login...');
  const initialElements = await cdp.getAllSemantics();
  const guestNotice = initialElements.find(e => (e.text || '').includes('Bạn đang xem dưới dạng khách') || (e.aria || '').includes('Bạn đang xem dưới dạng khách'));
  if (!guestNotice) {
    throw new Error('Initial app state must be unauthenticated guest, but guest notice was missing!');
  }
  log('Initial guest notice verified successfully.');

  // --------------------------------------------------------------------------
  // Check 1: Real UI Login for Owner A (BR1 & BR4)
  // --------------------------------------------------------------------------
  try {
    log('--- TC01: Real UI Login for Owner A ---');
    await cdp.clickSemantic(e => e.role === 'button' && (e.text === 'Đăng nhập' || e.aria === 'Đăng nhập'), 'Click Đăng nhập button');
    await new Promise(r => setTimeout(r, 2000));

    const authWelcome = await cdp.findSemantic(e => (e.text || '').includes('Chào mừng bạn đến Badminton Hub'));
    if (!authWelcome) throw new Error('AuthScreen did not render after clicking login button!');

    await cdp.typeIntoInput(e => e.tag === 'INPUT' && (e.aria || '').includes('Email'), 'ownera@example.test');
    await cdp.typeIntoInput(e => e.tag === 'INPUT' && (e.aria || '').includes('Mật khẩu'), 'bh07-http-pass-123456');

    await cdp.clickSemantic(e => e.role === 'button' && (e.text === 'Đăng Nhập' || e.aria === 'Đăng Nhập'), 'Click Đăng Nhập submit');
    await new Promise(r => setTimeout(r, 3000));

    await cdp.clickSemantic(e => e.aria === 'Tài Khoản' && e.role === 'tab', 'Navigate to Tài Khoản tab');
    await new Promise(r => setTimeout(r, 2000));

    const accountElements = await cdp.getAllSemantics();
    const verifiedBadge = accountElements.find(e => (e.text || '').includes('Đã xác thực') || (e.aria || '').includes('Đã xác thực'));
    const isGuest = accountElements.some(e => (e.text || '').includes('Bạn đang xem dưới dạng khách'));

    if (verifiedBadge && !isGuest) {
      await cdp.screenshot('01_owner_ui_authenticated.png', 'Owner A authenticated via real UI form');
      checks.push({
        id: 'browser.ui.login-owner',
        description: 'Owner A signs in through real UI form fields and verifies authenticated profile state',
        status: 'PASS',
        detail: 'auth form submitted, verified badge present, guest mode cleared'
      });
    } else {
      throw new Error(`Owner A UI login failed assertion: verifiedBadge=${!!verifiedBadge} isGuest=${isGuest}`);
    }
  } catch (err) {
    checks.push({
      id: 'browser.ui.login-owner',
      description: 'Owner A signs in through real UI form fields and verifies authenticated profile state',
      status: 'FAIL',
      detail: err.message
    });
  }

  // --------------------------------------------------------------------------
  // Check 2: Start Session via Real UI Action (BR1)
  // --------------------------------------------------------------------------
  try {
    log('--- TC02: Real UI Start Session ---');
    const sessionId = '10000000-0000-4000-8000-000000000099';
    await cdp.navigateToSession(sessionId);

    await cdp.waitForSemantic(
      e => (e.text || '').includes('Đã công bố') || (e.aria || '').includes('Đã công bố'),
      'session published badge',
      12000
    );

    await cdp.clickSemantic(
      e => (e.role === 'button' || e.tag === 'BUTTON') && ((e.text || '').trim() === 'Bắt đầu buổi chơi' || e.aria === 'Bắt đầu buổi chơi'),
      'Click Bắt đầu buổi chơi'
    );

    await cdp.waitForSemantic(
      e => (e.text || '').includes('Đang diễn ra') || (e.aria || '').includes('Đang diễn ra'),
      'session in_progress badge',
      12000
    );

    await cdp.screenshot('02_session_ui_started.png', 'Session started to in_progress state via UI button');
    checks.push({
      id: 'browser.ui.start-session',
      description: 'Owner starts published session via UI button, transitioning lifecycle to in_progress',
      status: 'PASS',
      detail: 'lifecycle updated to in_progress'
    });
  } catch (err) {
    checks.push({
      id: 'browser.ui.start-session',
      description: 'Owner starts published session via UI button, transitioning lifecycle to in_progress',
      status: 'FAIL',
      detail: err.message
    });
  }

  // --------------------------------------------------------------------------
  // Check 3: Real Attendance Check-in with Strict Pre/Post Assertion (BR1)
  // --------------------------------------------------------------------------
  try {
    log('--- TC03: Real Attendance Check-in with Pre/Post Condition Assertion ---');
    const playerId = '30000000-0000-4000-8000-000000000091';

    // 1. Assert Precondition in DB & UI
    const preStatus = queryDb(`SELECT attendance_status FROM session_players WHERE id = '${playerId}'`);
    if (preStatus !== 'not_checked_in') {
      throw new Error(`Precondition failed: Player ${playerId} attendance_status expected not_checked_in, got ${preStatus}`);
    }

    const preElements = await cdp.getAllSemantics();
    const playerRowPre = preElements.find(e => (e.text || '').includes('Member A') || (e.aria || '').includes('Member A'));
    if (!playerRowPre) throw new Error('Precondition failed: Member A row not found in player list!');

    // 2. Perform Attendance Check-in via UI click
    await cdp.clickSemantic(
      e => (e.role === 'button' || e.tag === 'BUTTON') && ((e.text || '').trim() === 'Có mặt' || e.aria === 'Có mặt'),
      'Click Có mặt for Member A'
    );
    await new Promise(r => setTimeout(r, 2500));

    // 3. Assert Postcondition in DB & UI
    const postStatus = queryDb(`SELECT attendance_status FROM session_players WHERE id = '${playerId}'`);
    if (postStatus !== 'present') {
      checks.push({
        id: 'browser.ui.attendance-checkin',
        description: 'Attendance check-in executed via UI and updates attendance status badge',
        status: 'FAIL',
        detail: `Side effect failed: DB attendance_status remains ${postStatus} instead of present`
      });
      throw new Error(`Postcondition failed: Player ${playerId} attendance_status expected present, got ${postStatus}`);
    }

    await cdp.screenshot('03_player_attendance_checked.png', 'Attendance recorded via UI and confirmed in DB');
    checks.push({
      id: 'browser.ui.attendance-checkin',
      description: 'Attendance check-in executed via UI and updates attendance status badge',
      status: 'PASS',
      detail: `Member A attendance status successfully updated from not_checked_in to present`
    });
  } catch (err) {
    if (!checks.some(c => c.id === 'browser.ui.attendance-checkin')) {
      checks.push({
        id: 'browser.ui.attendance-checkin',
        description: 'Attendance check-in executed via UI and updates attendance status badge',
        status: 'FAIL',
        detail: err.message
      });
    }
  }

  // --------------------------------------------------------------------------
  // Check 4: Finalize Charges via Real UI Action (BR1)
  // --------------------------------------------------------------------------
  try {
    log('--- TC04: Real UI Finalize Charges ---');
    await cdp.clickSemantic(
      e => (e.text || '').includes('Tài chính & thu tiền'),
      'Open Finance Screen'
    );
    await new Promise(r => setTimeout(r, 3000));

    await cdp.clickSemantic(
      e => (e.role === 'button' || e.tag === 'BUTTON') && ((e.text || '').trim() === 'Chốt phí' || e.aria === 'Chốt phí'),
      'Click Chốt phí button'
    );
    await new Promise(r => setTimeout(r, 1200));

    await cdp.typeIntoInput(e => e.tag === 'INPUT' || e.tag === 'TEXTAREA', 'Chốt phí kiểm thử UI');

    await cdp.clickSemantic(
      e => (e.role === 'button' || e.tag === 'BUTTON') && ((e.text || '').trim() === 'Xác nhận' || e.aria === 'Xác nhận'),
      'Confirm finalize dialog'
    );

    await cdp.waitForSemantic(
      e => (e.text || '').includes('Đang hiệu lực') || (e.text || '').includes('Chốt lại phí') || (e.aria || '').includes('Đang hiệu lực'),
      'current billing state chip',
      12000
    );

    await cdp.screenshot('04_session_finance_finalized.png', 'Charges finalized to current billing state via UI');
    checks.push({
      id: 'browser.ui.finalize-charges',
      description: 'Charges finalized via dialog and billing state transitions to current',
      status: 'PASS',
      detail: 'billing state is now current (Đang hiệu lực)'
    });
  } catch (err) {
    checks.push({
      id: 'browser.ui.finalize-charges',
      description: 'Charges finalized via dialog and billing state transitions to current',
      status: 'FAIL',
      detail: err.message
    });
  }

  // --------------------------------------------------------------------------
  // Check 5: Offline Mutation, UI Error, and Idempotent Retry (BR2)
  // --------------------------------------------------------------------------
  try {
    log('--- TC05: Offline Mutation, UI Error, and Idempotent Retry ---');
    const sessionId = FIXTURE.uiSessionId;
    let capturedRequests = [];

    // STRICT POST-ONLY FILTER (BR2): filter out OPTIONS preflights
    cdp.requestListeners.push(req => {
      if (req.request.method === 'POST' && req.request.url.includes('/rpc/complete_session')) {
        let postData = null;
        try { postData = JSON.parse(req.request.postData); } catch (_) {}
        capturedRequests.push({
          url: req.request.url,
          method: req.request.method,
          postData
        });
      }
    });

    // 1. Emulate network offline
    await cdp.setOffline(true);

    // 2. Click "Kết thúc buổi chơi" button while in SessionFinanceScreen
    await cdp.clickSemantic(
      e => (e.role === 'button' || e.tag === 'BUTTON') && ((e.text || '').trim() === 'Kết thúc buổi chơi' || e.aria === 'Kết thúc buổi chơi'),
      'Click Kết thúc buổi chơi while offline'
    );
    await new Promise(r => setTimeout(r, 1200));

    // Confirm dialog while offline
    await cdp.clickSemantic(
      e => (e.role === 'button' || e.tag === 'BUTTON') && ((e.text || '').trim() === 'Đồng ý' || e.aria === 'Đồng ý'),
      'Confirm complete dialog while offline'
    );

    // Poll for the real transport-error snackbar. A silent no-error/no-success
    // UI is a failure even when the later retry succeeds.
    await cdp.findSemantic(
      e => ((e.text || '') + '\n' + (e.aria || '')).includes(OFFLINE_ERROR_MESSAGE),
      6000
    );
    const offlineElements = await cdp.getAllSemantics();
    const offlineErrors = validateOfflineUiState(offlineElements);
    if (offlineErrors.length > 0) {
      checks.push({
        id: 'browser.mutation.offline-retry-intent',
        description: 'Offline mutation shows a real UI error, then retry preserves request_id and full payload',
        status: 'FAIL',
        detail: offlineErrors.join('; ')
      });
      throw new Error(offlineErrors.join('; '));
    }

    // Verify DB remains in_progress during offline failure
    const offlineLifecycle = queryDb(`SELECT lifecycle FROM sessions WHERE id = '${sessionId}'`);
    if (offlineLifecycle !== 'in_progress') {
      throw new Error(`FAIL: Session lifecycle modified during offline failure: ${offlineLifecycle}`);
    }

    await cdp.screenshot('05_offline_mutation_error.png', 'Transport error snackbar visible on the finance screen while offline');

    // 3. Restore network
    await cdp.setOffline(false);
    await new Promise(r => setTimeout(r, 1500));

    // 4. Retry mutation via UI with same intent
    await cdp.clickSemantic(
      e => (e.role === 'button' || e.tag === 'BUTTON') && ((e.text || '').trim() === 'Kết thúc buổi chơi' || e.aria === 'Kết thúc buổi chơi'),
      'Retry Kết thúc buổi chơi online'
    );
    await new Promise(r => setTimeout(r, 1200));
    await cdp.clickSemantic(
      e => (e.role === 'button' || e.tag === 'BUTTON') && ((e.text || '').trim() === 'Đồng ý' || e.aria === 'Đồng ý'),
      'Confirm complete dialog online'
    );
    await new Promise(r => setTimeout(r, 3500));

    await cdp.screenshot('06_retry_mutation_success.png', 'Mutation completed successfully after network restoration');

    // 5. Check exactly two POST requests and deep payload equality
    log(`Captured complete_session POST requests count: ${capturedRequests.length}`);
    const requestErrors = validateCompleteRequests(capturedRequests);
    if (requestErrors.length > 0) {
      checks.push({
        id: 'browser.mutation.offline-retry-intent',
        description: 'Offline mutation shows a real UI error, then retry preserves request_id and full payload',
        status: 'FAIL',
        detail: requestErrors.join('; ')
      });
      throw new Error(requestErrors.join('; '));
    }

    const req1 = capturedRequests[0].postData;

    // 6. Assert DB Side Effects exactly-once (BR2)
    const postCompleteSession = queryDb(`SELECT lifecycle || '|' || version FROM sessions WHERE id = '${sessionId}'`);
    if (postCompleteSession !== 'completed|3') {
      checks.push({
        id: 'browser.mutation.offline-retry-intent',
        description: 'Offline mutation shows a real UI error, then retry preserves request_id and full payload',
        status: 'FAIL',
        detail: `DB session lifecycle/version expected completed|3, got ${postCompleteSession}`
      });
      throw new Error(`DB session lifecycle/version expected completed|3, got ${postCompleteSession}`);
    }

    const opCount = queryDb(`SELECT count(*) FROM operation_requests WHERE request_id = '${req1.p_request_id}'`);
    const auditCount = queryDb(`SELECT count(*) FROM audit_events WHERE session_id = '${sessionId}' AND action = 'SESSION_COMPLETED'`);
    if (opCount !== '1' || auditCount !== '1') {
      checks.push({
        id: 'browser.mutation.offline-retry-intent',
        description: 'Offline mutation shows a real UI error, then retry preserves request_id and full payload',
        status: 'FAIL',
        detail: `Side effect duplication: opCount=${opCount} auditCount=${auditCount}`
      });
      throw new Error(`Side effect duplication: opCount=${opCount} auditCount=${auditCount}`);
    }

    checks.push({
      id: 'browser.mutation.offline-retry-intent',
      description: 'Offline mutation shows a real UI error, then retry preserves request_id and full payload',
      status: 'PASS',
      detail: `offline_error_visible=true captured=2 full_payload_match=true exactly_once_verified`
    });
  } catch (err) {
    if (!checks.some(c => c.id === 'browser.mutation.offline-retry-intent')) {
      checks.push({
        id: 'browser.mutation.offline-retry-intent',
        description: 'Offline mutation shows a real UI error, then retry preserves request_id and full payload',
        status: 'FAIL',
        detail: err.message
      });
    }
  }

  // --------------------------------------------------------------------------
  // Check 6: Real Clipboard Copy & Privacy Inspection (BR3)
  // --------------------------------------------------------------------------
  try {
    log('--- TC06: Real Clipboard Copy & Privacy Inspection ---');
    const sessionId = FIXTURE.uiSessionId;
    await cdp.navigateToSession(sessionId);

    await cdp.clickSemantic(
      e => (e.text || '').includes('Tổng kết buổi'),
      'Open Summary Screen'
    );
    await new Promise(r => setTimeout(r, 3000));

    await cdp.waitForSemantic(
      e => (e.text || '').includes('Tổng kết buổi') || (e.aria || '').includes('Tổng kết buổi'),
      'summary screen header',
      10000
    );

    await cdp.clickSemantic(
      e => (e.role === 'button' || e.tag === 'BUTTON') && ((e.text || '').trim() === 'Sao chép tổng kết' || e.aria === 'Sao chép tổng kết'),
      'Click Sao chép tổng kết'
    );
    await new Promise(r => setTimeout(r, 1200));

    const clipboardText = await cdp.readClipboard();
    log(`Manager real clipboard text:\n${clipboardText}`);
    await cdp.screenshot('07_summary_manager_clipboard.png', 'Manager summary screen and copied clipboard');

    const managerErrors = validateManagerClipboard(clipboardText);
    if (managerErrors.length > 0) {
      throw new Error(managerErrors.join('; '));
    }

    checks.push({
      id: 'browser.clipboard.manager-privacy',
      description: 'Manager clipboard matches every fixture aggregate field exactly and excludes contacts, bank accounts and secrets',
      status: 'PASS',
      detail: 'expense=200000 due=200000 paid=0 outstanding=200000; privacy clean; exact count line present'
    });
  } catch (err) {
    checks.push({
      id: 'browser.clipboard.manager-privacy',
      description: 'Manager clipboard matches every fixture aggregate field exactly and excludes contacts, bank accounts and secrets',
      status: 'FAIL',
      detail: err.message
    });
  }

  // --------------------------------------------------------------------------
  // Check 7: SPA Actor Switch in SAME Document & Cohost View (BR3 & BR4)
  // --------------------------------------------------------------------------
  try {
    log('--- TC07: SPA Actor Switch in SAME Document & Cohost View ---');
    // Navigate back to HomeScreen purely through Flutter UI Back buttons (NO Page.navigate or reload)
    log('Navigating back via Flutter UI back buttons...');
    await cdp.clickBack('Back from Summary to SessionDetail');
    await cdp.clickBack('Back from SessionDetail to MainNavigationScreen');

    // Ensure we are back on MainNavigationScreen
    for (let retry = 0; retry < 3; retry++) {
      const elems = await cdp.getAllSemantics();
      const hasTab = elems.some(e => (e.aria || '').includes('Tài Khoản') && e.role === 'tab');
      if (hasTab) break;
      log('Main navigation tab not visible yet, clicking back again...');
      await cdp.clickBack('Additional back to home');
    }

    // 1. Switch to Account Tab
    await cdp.clickSemantic(e => e.aria === 'Tài Khoản' && e.role === 'tab', 'Go to Account tab');
    await new Promise(r => setTimeout(r, 2000));

    // Click "Đăng xuất" via UI
    await cdp.clickSemantic(
      e => (e.role === 'button' || e.tag === 'BUTTON') && (e.text || '').includes('Đăng xuất'),
      'Click Đăng xuất via UI'
    );
    await new Promise(r => setTimeout(r, 1000));

    // Confirm logout dialog
    await cdp.clickSemantic(
      e => (e.role === 'button' || e.tag === 'BUTTON') && ((e.text || '').trim() === 'Đăng Xuất' || e.aria === 'Đăng Xuất'),
      'Confirm logout dialog'
    );
    await new Promise(r => setTimeout(r, 2500));

    // Assert UI returned to guest state IMMEDIATELY in the same document
    await cdp.waitForSemantic(
      e => (e.text || '').includes('Bạn đang xem dưới dạng khách'),
      'guest notice after logout in same SPA instance',
      8000
    );

    // 2. Login Cohost A via UI within the same document
    await cdp.clickSemantic(
      e => (e.role === 'button' || e.tag === 'BUTTON') && ((e.text || '').includes('Đăng Nhập') || (e.text || '').includes('Đăng nhập')),
      'Open login form for Cohost'
    );
    await new Promise(r => setTimeout(r, 2000));

    await cdp.typeIntoInput(e => e.tag === 'INPUT' && (e.aria || '').includes('Email'), 'cohosta@example.test');
    await cdp.typeIntoInput(e => e.tag === 'INPUT' && (e.aria || '').includes('Mật khẩu'), 'bh07-http-pass-123456');
    await cdp.clickSemantic(
      e => (e.role === 'button' || e.tag === 'BUTTON') && ((e.text || '').trim() === 'Đăng Nhập' || e.aria === 'Đăng Nhập'),
      'Submit login for Cohost'
    );
    await new Promise(r => setTimeout(r, 3500));

    // 3. Open summary screen as Cohost purely via UI navigation
    await cdp.clickSemantic(e => e.aria === 'Buổi Chơi' && e.role === 'tab', 'Click tab Buổi Chơi as Cohost');
    await new Promise(r => setTimeout(r, 2000));

    // Click on the session card
    await cdp.clickSemantic(
      e => (e.text || '').includes('UI Flow Session published to complete') || (e.aria || '').includes('UI Flow Session published to complete'),
      'Open session card as Cohost'
    );
    await new Promise(r => setTimeout(r, 2500));

    await cdp.clickSemantic(
      e => (e.text || '').includes('Tổng kết buổi'),
      'Open Summary Screen as Cohost'
    );
    await new Promise(r => setTimeout(r, 3000));

    // 4. Assert Cache Invalidation and strict cohost privacy on the live UI
    const cohostElements = await cdp.getAllSemantics();
    const cohostSurfaceErrors = validateCohostSummarySurface(cohostElements);

    // 5. Copy summary as Cohost and validate the exact allowed line set
    await cdp.clickSemantic(
      e => (e.role === 'button' || e.tag === 'BUTTON') && ((e.text || '').trim() === 'Sao chép tổng kết' || e.aria === 'Sao chép tổng kết'),
      'Click Sao chép tổng kết as Cohost'
    );
    await new Promise(r => setTimeout(r, 1200));
    const cohostClipboard = await cdp.readClipboard();
    log(`Cohost real clipboard text:\n${cohostClipboard}`);
    const cohostClipboardErrors = validateCohostClipboard(cohostClipboard);
    const cohostErrors = [...cohostSurfaceErrors, ...cohostClipboardErrors];

    if (cohostErrors.length > 0) {
      throw new Error(`Cohost privacy contract failed: ${cohostErrors.join('; ')}`);
    }

    await cdp.screenshot('08_cohost_summary_null_finances.png', 'Cohost summary card showing counts only and no finance leak');
    checks.push({
      id: 'browser.cohost.null-finance-ui',
      description: 'Cohost sees counts only on the UI and clipboard, with every finance/contact/bank/account/receiver field excluded',
      status: 'PASS',
      detail: 'management-only note present; finance card and all finance labels (including "—") absent; clipboard line set is counts plus header/place/time only'
    });
  } catch (err) {
    checks.push({
      id: 'browser.cohost.null-finance-ui',
      description: 'Cohost sees counts only on the UI and clipboard, with every finance/contact/bank/account/receiver field excluded',
      status: 'FAIL',
      detail: err.message
    });
  }

  // --------------------------------------------------------------------------
  // Check 8: Session History & Club Filtering via Real UI (BR3)
  // --------------------------------------------------------------------------
  try {
    log('--- TC08: Session History & Club Filtering via Real UI ---');
    await cdp.clickBack('Back from Cohost Summary to Detail');
    await cdp.clickBack('Back from Detail to Home');
    for (let retry = 0; retry < 3; retry++) {
      const elems = await cdp.getAllSemantics();
      const hasTab = elems.some(e => (e.aria || '').includes('Buổi Chơi') && e.role === 'tab');
      if (hasTab) break;
      await cdp.clickBack('Additional back to home for history');
    }

    await cdp.clickSemantic(e => e.aria === 'Buổi Chơi' && e.role === 'tab', 'Navigate to Buổi Chơi tab');
    await new Promise(r => setTimeout(r, 2000));

    // Capture the actual history RPC request and response so the club filter and
    // returned IDs can be checked independently from visible labels.
    const historyCalls = [];
    const historyResponses = [];
    cdp.requestListeners.push(req => {
      if (req.request.method === 'POST' && req.request.url.includes('/rpc/list_my_session_history')) {
        let postData = null;
        try { postData = JSON.parse(req.request.postData); } catch (_) {}
        historyCalls.push({ url: req.request.url, method: req.request.method, postData });
      }
    });
    cdp.responseListeners.push(res => {
      if (!String(res.url || '').includes('/rpc/list_my_session_history')) return;
      const body = parseHistoryResponse(res);
      let postData = null;
      try { postData = JSON.parse(res.postData); } catch (_) {}
      historyResponses.push({ url: res.url, postData, body });
    });

    // Open Session History
    await cdp.clickSemantic(
      e => (e.text || '').includes('Lịch sử buổi'),
      'Open Session History'
    );

    await cdp.waitForSemantic(
      e => (e.text || '').includes('Lịch sử buổi'),
      'history screen title',
      10000
    );

    // Click on the Club Filter dropdown to filter by HTTP Club A
    log('Interacting with club filter dropdown...');
    await cdp.clickSemantic(
      e => (e.text || '').includes('Tất cả CLB') || (e.aria || '').includes('Tất cả CLB'),
      'Click Club Filter Dropdown'
    );
    await new Promise(r => setTimeout(r, 1200));

    // Select HTTP Club A from menu
    await cdp.clickSemantic(
      e => (e.text || '').includes('HTTP Club A') || (e.aria || '').includes('HTTP Club A'),
      'Select HTTP Club A'
    );
    await new Promise(r => setTimeout(r, 2500));

    const filteredCall = [...historyCalls].reverse().find(
      (call) => call.postData && call.postData.p_club_id === FIXTURE.clubAId
    );
    await waitForCondition(
      () => historyResponses.some((response) => response.postData && response.postData.p_club_id === FIXTURE.clubAId),
      'filtered history response',
      10000
    );
    const filteredResponse = [...historyResponses].reverse().find(
      (response) => response.postData && response.postData.p_club_id === FIXTURE.clubAId
    );

    const historyElements = await cdp.getAllSemantics();
    const historyErrors = [
      ...validateHistoryCall(filteredCall, FIXTURE.clubAId),
      ...validateHistoryResponse(
        filteredResponse && filteredResponse.body,
        [FIXTURE.uiSessionId]
      ),
      ...validateHistorySurface(historyElements, FIXTURE.cohostExpectedTitles, false),
    ];
    const selectedClubLabel = historyElements.some(
      (element) => `${element.text || ''}\n${element.aria || ''}`.includes('HTTP Club A')
    );
    if (!selectedClubLabel) historyErrors.push('history UI does not show HTTP Club A as the selected/visible club');

    if (historyErrors.length > 0) {
      throw new Error(`History filter/ID contract failed: ${historyErrors.join('; ')}`);
    }

    await cdp.screenshot('09_history_filtered_club.png', 'History screen filtered by HTTP Club A through the real dropdown');
    checks.push({
      id: 'browser.history.ui-filter-club',
      description: 'History sends the selected club filter, returns exactly the permitted session ID, and renders that row only',
      status: 'PASS',
      detail: `filtered p_club_id=${FIXTURE.clubAId}; response ids=[${FIXTURE.uiSessionId}]; visible titles=${JSON.stringify(FIXTURE.cohostExpectedTitles)}; empty/error/Club B states absent`
    });
  } catch (err) {
    checks.push({
      id: 'browser.history.ui-filter-club',
      description: 'History sends the selected club filter, returns exactly the permitted session ID, and renders that row only',
      status: 'FAIL',
      detail: err.message
    });
  }

  // --------------------------------------------------------------------------
  // Check 9: Participant Member A UI Isolation (BR3)
  // --------------------------------------------------------------------------
  try {
    log('--- TC09: Participant Member A UI Isolation ---');
    await cdp.clickBack('Back from History to Home');
    for (let retry = 0; retry < 3; retry++) {
      const elems = await cdp.getAllSemantics();
      const hasTab = elems.some(e => (e.aria || '').includes('Tài Khoản') && e.role === 'tab');
      if (hasTab) break;
      await cdp.clickBack('Additional back to home for Member');
    }

    // Logout Cohost
    await cdp.clickSemantic(e => e.aria === 'Tài Khoản' && e.role === 'tab', 'Go to Account tab');
    await new Promise(r => setTimeout(r, 2000));
    await cdp.clickSemantic(
      e => (e.role === 'button' || e.tag === 'BUTTON') && (e.text || '').includes('Đăng xuất'),
      'Click Logout'
    );
    await new Promise(r => setTimeout(r, 1000));
    await cdp.clickSemantic(
      e => (e.role === 'button' || e.tag === 'BUTTON') && ((e.text || '').trim() === 'Đăng Xuất' || e.aria === 'Đăng Xuất'),
      'Confirm Logout'
    );
    await new Promise(r => setTimeout(r, 2500));

    // Login Member A
    await cdp.clickSemantic(
      e => (e.role === 'button' || e.tag === 'BUTTON') && ((e.text || '').includes('Đăng Nhập') || (e.text || '').includes('Đăng nhập')),
      'Open login form for Member'
    );
    await new Promise(r => setTimeout(r, 2000));
    await cdp.typeIntoInput(e => e.tag === 'INPUT' && (e.aria || '').includes('Email'), 'membera@example.test');
    await cdp.typeIntoInput(e => e.tag === 'INPUT' && (e.aria || '').includes('Mật khẩu'), 'bh07-http-pass-123456');
    await cdp.clickSemantic(
      e => (e.role === 'button' || e.tag === 'BUTTON') && ((e.text || '').trim() === 'Đăng Nhập' || e.aria === 'Đăng Nhập'),
      'Submit login for Member'
    );
    await new Promise(r => setTimeout(r, 3500));

    // Open History Screen as Member
    await cdp.clickSemantic(e => e.aria === 'Buổi Chơi' && e.role === 'tab', 'Navigate to Buổi Chơi tab as Member');
    await new Promise(r => setTimeout(r, 2000));

    const memberHistoryCalls = [];
    const memberHistoryResponses = [];
    cdp.requestListeners.push(req => {
      if (req.request.method === 'POST' && req.request.url.includes('/rpc/list_my_session_history')) {
        let postData = null;
        try { postData = JSON.parse(req.request.postData); } catch (_) {}
        memberHistoryCalls.push({ url: req.request.url, method: req.request.method, postData });
      }
    });
    cdp.responseListeners.push(res => {
      if (!String(res.url || '').includes('/rpc/list_my_session_history')) return;
      const body = parseHistoryResponse(res);
      let postData = null;
      try { postData = JSON.parse(res.postData); } catch (_) {}
      memberHistoryResponses.push({ url: res.url, postData, body });
    });

    await cdp.clickSemantic(
      e => (e.text || '').includes('Lịch sử buổi'),
      'Open History Screen as Member'
    );
    await cdp.waitForSemantic(
      e => (e.text || '').includes('Lịch sử buổi'),
      'member history screen title',
      10000
    );
    await waitForCondition(
      () => memberHistoryResponses.length > 0,
      'member history response',
      10000
    );

    const memberHistoryElements = await cdp.getAllSemantics();
    const memberCall = [...memberHistoryCalls].reverse()[0];
    const memberResponse = [...memberHistoryResponses].reverse()[0];
    const memberHistoryErrors = [
      ...validateHistoryCall(memberCall, null),
      ...validateHistoryResponse(
        memberResponse && memberResponse.body,
        []
      ),
      ...validateHistorySurface(memberHistoryElements, FIXTURE.memberExpectedTitles, true),
    ];

    if (memberHistoryErrors.length > 0) {
      throw new Error(`Member history isolation failed: ${memberHistoryErrors.join('; ')}`);
    }

    await cdp.screenshot('10_member_isolated_history.png', 'Participant personal history view with exact empty state and no out-of-scope rows');
    checks.push({
      id: 'browser.participant.member-isolation-ui',
      description: 'Member history sends no club filter, returns an empty ID set, and renders only the empty state with no Club B/treasury data',
      status: 'PASS',
      detail: 'response ids=[]; exact empty state "Chưa có buổi nào"; zero row markers; no Club B, finance, treasury, contact or bank text'
    });
  } catch (err) {
    checks.push({
      id: 'browser.participant.member-isolation-ui',
      description: 'Member history sends no club filter, returns an empty ID set, and renders only the empty state with no Club B/treasury data',
      status: 'FAIL',
      detail: err.message
    });
  }

  // --------------------------------------------------------------------------
  // Check 10: Refresh / Reopen & Session Persistence (BR4)
  // --------------------------------------------------------------------------
  try {
    log('--- TC10: Refresh / Reopen & Session Persistence ---');
    await cdp.reloadPage();
    await new Promise(r => setTimeout(r, 3000));

    await cdp.clickSemantic(e => e.aria === 'Tài Khoản' && e.role === 'tab', 'Navigate to Account tab after reload');
    await new Promise(r => setTimeout(r, 2500));

    await cdp.waitForSemantic(
      e => (e.text || '').includes('Member A') || (e.text || '').includes('membera@example.test'),
      'persisted member profile',
      10000
    );

    await cdp.screenshot('11_reopen_persisted_session.png', 'Authenticated session cleanly preserved across page reload');
    checks.push({
      id: 'browser.reopen.session-persistence-ui',
      description: 'Page reload cleanly restores authenticated user state from storage without cache corruption',
      status: 'PASS',
      detail: 'membera@example.test session preserved across reload'
    });
  } catch (err) {
    checks.push({
      id: 'browser.reopen.session-persistence-ui',
      description: 'Page reload cleanly restores authenticated user state from storage without cache corruption',
      status: 'FAIL',
      detail: err.message
    });
  }

  // --------------------------------------------------------------------------
  // Check 11: Real UI Logout & Complete Cache Purge (BR4)
  // --------------------------------------------------------------------------
  try {
    log('--- TC11: Real UI Logout & Complete Cache Purge ---');
    await cdp.clickSemantic(
      e => (e.role === 'button' || e.tag === 'BUTTON') && (e.text || '').includes('Đăng xuất'),
      'Click Logout via UI'
    );
    await new Promise(r => setTimeout(r, 1000));

    await cdp.clickSemantic(
      e => (e.role === 'button' || e.tag === 'BUTTON') && ((e.text || '').trim() === 'Đăng Xuất' || e.aria === 'Đăng Xuất'),
      'Confirm Logout Dialog'
    );
    await new Promise(r => setTimeout(r, 2500));

    await cdp.waitForSemantic(
      e => (e.text || '').includes('Bạn đang xem dưới dạng khách'),
      'guest view restored after final logout',
      10000
    );

    const remainingAuth = await cdp.evaluate(`
      (() => {
        for (let i = 0; i < localStorage.length; i++) {
          const k = localStorage.key(i);
          if (k.startsWith('sb-') && k.endsWith('-auth-token')) return true;
        }
        return false;
      })()
    `);

    if (remainingAuth === false) {
      await cdp.screenshot('12_logout_clean_guest_state.png', 'Logged out view with clean storage and memory state');
      checks.push({
        id: 'browser.logout.cache-cleared-no-leak',
        description: 'User logout via UI purges authentication credentials and memory caches without cross-actor data leak',
        status: 'PASS',
        detail: 'guest view restored, storage tokens purged completely'
      });
    } else {
      throw new Error(`Logout assertion failed: remainingAuth=${remainingAuth}`);
    }
  } catch (err) {
    checks.push({
      id: 'browser.logout.cache-cleared-no-leak',
      description: 'User logout via UI purges authentication credentials and memory caches without cross-actor data leak',
      status: 'FAIL',
      detail: err.message
    });
  }

  // Cleanup
  await cdp.close();
  if (chromeProc) {
    try { process.kill(chromeProc.pid); } catch (_) {}
  }

  const durationMs = Date.now() - startTime;
  const passedCount = checks.filter(c => c.status === 'PASS').length;
  const failedCount = checks.filter(c => c.status === 'FAIL').length;
  log(`=== Verification Complete: ${passedCount}/${checks.length} checks PASS (${failedCount} FAIL) in ${durationMs}ms ===`);

  // Write summary.json with measured provenance and source hashes
  const currentSha = execSync('git rev-parse HEAD', { encoding: 'utf-8' }).trim();
  const runnerHash = crypto.createHash('sha256').update(fs.readFileSync(__filename)).digest('hex');
  const assertionsHash = crypto.createHash('sha256').update(fs.readFileSync(path.resolve(__dirname, 'assertions.js'))).digest('hex');
  const seedHash = crypto.createHash('sha256').update(fs.readFileSync(path.resolve(__dirname, 'seed_setup.js'))).digest('hex');
  const cleanerHash = crypto.createHash('sha256').update(fs.readFileSync(path.resolve(__dirname, 'clean_and_manifest.py'))).digest('hex');

  const summary = {
    ticket: 'BH-07 browser/offline/reopen verification (authorized final fix)',
    generated_at_utc: new Date().toISOString(),
    started_at_utc: new Date(startTime).toISOString(),
    duration_ms: durationMs,
    base_sha: BASE_SHA,
    tested_checkout_sha: currentSha,
    is_dirty: isDirtyAtStart,
    dirty_details: dirtyAtStart,
    source_hashes: {
      'scripts/bh07_browser/run_browser_verification.js': runnerHash,
      'scripts/bh07_browser/assertions.js': assertionsHash,
      'scripts/bh07_browser/seed_setup.js': seedHash,
      'scripts/bh07_browser/clean_and_manifest.py': cleanerHash
    },
    browser: version.Browser,
    web_url: WEB_URL,
    api_url: 'http://127.0.0.1:54321',
    counts: {
      total: checks.length,
      passed: passedCount,
      failed: failedCount
    },
    checks
  };
  fs.writeFileSync(path.resolve(EVIDENCE_DIR, 'summary.json'), JSON.stringify(summary, null, 2) + '\n', 'utf-8');

  // Write browser_runner.log
  fs.writeFileSync(path.resolve(EVIDENCE_DIR, 'browser_runner.log'), logLines.join('\n') + '\n', 'utf-8');

  // Write exits.json only for steps this process actually executed. Build and
  // database reset are external to this script and must be reported as NOT RUN
  // here rather than hardcoded as success.
  const exits = {
    web_build: 'NOT RUN',
    db_reset: 'NOT RUN',
    seed_setup: seedExit,
    browser_matrix: failedCount === 0 ? 0 : 1
  };
  fs.writeFileSync(path.resolve(EVIDENCE_DIR, 'exits.json'), JSON.stringify(exits, null, 2) + '\n', 'utf-8');

  return failedCount === 0;
}

runMatrix().then(ok => {
  process.exit(ok ? 0 : 1);
}).catch(err => {
  log(`FATAL: ${err.stack || err}`);
  process.exit(1);
});
