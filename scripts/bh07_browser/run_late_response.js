// Real GoTrue/PostgREST responses held at Chrome's response boundary.
// No repository/Auth mock, response replacement, reload or programmatic login.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { execFileSync } = require('node:child_process');
const { CdpClient, startChrome } = require(process.env.BH07_BROWSER_DRIVER || './run_browser_verification');
const A = require('./assertions');
const { validateLateResponse } = require('./late_response_assertions');
const ROOT = path.resolve(__dirname, '../..');
const OUT = path.resolve(process.env.BH07_LATE_EVIDENCE || path.join(ROOT, 'docs/reviews/bh07/late_response_evidence'));
const wait = (ms) => new Promise((r) => setTimeout(r, ms));
const hash = (text) => crypto.createHash('sha256').update(text).digest('hex');
const text = (e) => `${e.text || ''}\n${e.aria || ''}`;
const button = (label) => (e) => (e.role === 'button' || e.tag === 'BUTTON') && ((e.text || '').trim() === label || e.aria === label);
async function until(predicate, desc, timeout = 15000) {
  const end = Date.now() + timeout;
  while (Date.now() < end) { if (await predicate()) return; await wait(100); }
  throw new Error(`Timed out: ${desc}`);
}
async function checked(cdp, method, params = {}) {
  const result = await cdp.send(method, params);
  if (result.error) throw new Error(`${method}: ${result.error.message}`);
  return result.result;
}
async function home(cdp) {
  for (let i = 0; i < 5; i++) {
    if ((await cdp.getAllSemantics()).some((e) => e.role === 'tab' && e.aria === 'Tài Khoản')) return;
    await cdp.clickBack('Return through AppBar to main tabs');
  }
  throw new Error('Main tabs not reachable through UI');
}
async function login(cdp, actor) {
  await cdp.clickSemantic((e) => (e.role === 'button' || e.tag === 'BUTTON') && /Đăng [Nn]hập/.test(text(e)), 'Open login form');
  for (const [label, value] of [['Email', `${actor}@example.test`], ['Mật khẩu', 'bh07-http-pass-123456']]) {
    await cdp.clickSemantic((e) => e.tag === 'INPUT' && (e.aria || '').includes(label), 'Focus login input');
    await checked(cdp, 'Input.insertText', { text: value });
  }
  await cdp.clickSemantic(button('Đăng Nhập'), 'Submit real Auth login');
  await wait(1500);
  await cdp.clickSemantic((e) => e.role === 'tab' && e.aria === 'Tài Khoản', 'Verify account identity');
  await cdp.waitForSemantic((e) => text(e).includes(`${actor}@example.test`), 'UI account email');
  return Date.now();
}
async function logout(cdp) {
  await home(cdp);
  await cdp.clickSemantic((e) => e.role === 'tab' && e.aria === 'Tài Khoản', 'Account tab');
  await cdp.clickSemantic(button('Đăng xuất'), 'Logout');
  await cdp.clickSemantic(button('Đăng Xuất'), 'Confirm logout');
  await cdp.waitForSemantic((e) => text(e).includes('Bạn đang xem dưới dạng khách'), 'Guest UI');
  const tokenCleared = await cdp.evaluate(`!Object.keys(localStorage).some(k => k.startsWith('sb-') && k.endsWith('-auth-token'))`);
  if (!tokenCleared) throw new Error('Auth token remains after logout');
  return Date.now();
}
async function history(cdp) {
  await cdp.clickSemantic((e) => e.role === 'tab' && e.aria === 'Buổi Chơi', 'Sessions tab');
  await cdp.clickSemantic((e) => text(e).includes('Lịch sử buổi'), 'History');
}
async function summary(cdp) {
  await history(cdp);
  await cdp.clickSemantic((e) => text(e).includes(A.FIXTURE.uiSessionTitle), 'Fixture history row');
  await cdp.clickSemantic((e) => text(e).includes('Tổng kết buổi'), 'Summary entry');
}
async function copy(cdp) {
  await cdp.clickSemantic(button('Sao chép tổng kết'), 'Copy current actor summary');
  return cdp.readClipboard();
}
async function screenshot(cdp, filename) {
  const result = await checked(cdp, 'Page.captureScreenshot', { format: 'png' });
  fs.writeFileSync(path.join(OUT, filename), Buffer.from(result.data, 'base64'));
}
async function main() {
  const provenance = { base_sha: '1ed4f3e6b42b853f51add79279fe3daf8168e360', tested_source_sha: execFileSync('git', ['rev-parse', 'HEAD'], { cwd: ROOT, encoding: 'utf8' }).trim(), dirty_before_run: execFileSync('git', ['status', '--porcelain'], { cwd: ROOT, encoding: 'utf8' }).trim(), verification_mode: 'Codex implementation/self-verification, not independent review' };
  fs.mkdirSync(OUT, { recursive: true });
  const results = []; let cdp, chrome;
  try {
    chrome = await startChrome(); cdp = new CdpClient(chrome.version.webSocketDebuggerUrl);
    await cdp.connect(); await cdp.createTab('http://127.0.0.1:8088');
    await cdp.waitForSemantic((e) => text(e).includes('Bạn đang xem dưới dạng khách'), 'Initial guest negative control', 20000);
    const origin = await cdp.evaluate('performance.timeOrigin');
    let armed = false, held = null, fatal = null;
    const originalOnMessage = cdp.ws.onmessage;
    cdp.ws.onmessage = (event) => {
      originalOnMessage(event);
      const m = JSON.parse(event.data);
      if (m.method === 'Fetch.requestPaused') {
        (async () => {
          const p = m.params;
          if (!armed || p.request.method !== 'POST') { await checked(cdp, 'Fetch.continueResponse', { requestId: p.requestId }); return; }
          armed = false;
          const raw = await checked(cdp, 'Fetch.getResponseBody', { requestId: p.requestId });
          const body = raw.base64Encoded ? Buffer.from(raw.body, 'base64').toString('utf8') : raw.body;
          const dto = JSON.parse(body);
          held = { method: p.request.method, requestId: p.requestId, networkId: p.networkId, status: p.responseStatusCode, sessionId: dto.session_id, ownerFinance: dto.can_view_finance, expenses: dto.expenses_total_vnd, bodyHash: hash(body), heldAt: Date.now(), deliveredHash: null, deliveredAt: null };
          console.log('Held actual Owner response:', JSON.stringify({ status: held.status, sessionId: held.sessionId, ownerFinance: held.ownerFinance, bodyHash: held.bodyHash }));
        })().catch((e) => { fatal = e; });
      }
      if (m.method === 'Network.loadingFinished' && held && m.params.requestId === held.networkId) {
        (async () => {
          const raw = await checked(cdp, 'Network.getResponseBody', { requestId: held.networkId });
          held.deliveredHash = hash(raw.base64Encoded ? Buffer.from(raw.body, 'base64').toString('utf8') : raw.body);
          held.deliveredAt = Date.now();
        })().catch((e) => { fatal = e; });
      }
    };
    await checked(cdp, 'Fetch.enable', { patterns: [{ urlPattern: 'http://127.0.0.1:54321/rest/v1/rpc/get_session_summary', requestStage: 'Response' }] });
    for (const actor of ['cohosta', 'membera']) {
      held = null; fatal = null;
      await login(cdp, 'ownera');
      await summary(cdp);
      await cdp.waitForSemantic((e) => text(e).includes('Tài chính tổng hợp'), 'Owner positive finance card');
      const ownerClipboard = await copy(cdp);
      const ownerSurface = await cdp.getAllSemantics();
      const positiveErrors = A.validateManagerClipboard(ownerClipboard);
      const ownerNegativePassed = A.validateCohostClipboard(ownerClipboard).length > 0 && A.validateCohostSummarySurface(ownerSurface).length > 0;
      if (!ownerNegativePassed) throw new Error('Target guards accepted actual Owner privileged UI/clipboard');
      if (positiveErrors.length) throw new Error(positiveErrors.join('; '));
      armed = true;
      await cdp.clickSemantic((e) => e.aria === 'Tải lại tổng kết', 'Refresh Owner summary to hold real response');
      await until(() => { if (fatal) throw fatal; return held !== null; }, 'Held Owner 200');
      const guestAt = await logout(cdp);
      if (held.deliveredAt) throw new Error('Response delivered before actor login');
      const loginAt = await login(cdp, actor);
      if (actor === 'cohosta') {
        await summary(cdp);
        await cdp.waitForSemantic((e) => text(e).includes('Chỉ xem số lượng'), 'Cohost fresh count-only summary');
      } else {
        await history(cdp);
        await cdp.waitForSemantic((e) => text(e).includes('Chưa có buổi nào'), 'Member isolated empty history');
      }
      await screenshot(cdp, `${actor}_before_release.png`);
      const releaseAt = Date.now();
      await checked(cdp, 'Fetch.continueResponse', { requestId: held.requestId });
      await until(() => { if (fatal) throw fatal; return !!held.deliveredAt; }, 'Actual late response delivered to browser');
      const samples = [];
      for (let i = 0; i < 4; i++) {
        const elements = await cdp.getAllSemantics(); const joined = A.semanticTexts(elements).join('\n');
        samples.push({ privacyErrors: actor === 'cohosta' ? A.validateCohostSummarySurface(elements) : A.validateHistorySurface(elements, [], true), financeCard: joined.includes('Tài chính tổng hợp'), ownerProfile: joined.includes('ownera@example.test'), summaryEntryForMember: actor === 'membera' && joined.includes('Tổng kết buổi') });
        await wait(300);
      }
      const surface = await cdp.getAllSemantics(); const joined = A.semanticTexts(surface).join('\n');
      const clipboard = actor === 'cohosta' ? await copy(cdp) : null;
      const witness = { ...held, requestId: undefined, networkId: undefined, actor, ownerPositive: true, ownerNegativePassed, ownerProfile: true, targetProfile: `${actor}@example.test`, guestVerified: true, tokenCleared: true, guestAt, loginAt, releaseAt, originBefore: origin, originAfter: await cdp.evaluate('performance.timeOrigin'), samples, surface, clipboard, copyAvailable: surface.some(button('Sao chép tổng kết')), summaryEntry: joined.includes('Tổng kết buổi'), memberHistoryEmpty: joined.includes('Chưa có buổi nào') };
      const errors = validateLateResponse(witness);
      await screenshot(cdp, `${actor}_after_release.png`);
      // Publish safe semantic projections only, never headers/tokens or full browser storage.
      delete witness.surface;
      results.push({ actor, status: errors.length ? 'FAIL' : 'PASS', errors, witness });
      if (errors.length) throw new Error(`${actor}: ${errors.join('; ')}`);
      await logout(cdp);
    }
  } catch (e) { results.push({ status: 'FAIL', error: e.message }); }
  finally {
    if (cdp) await cdp.close().catch(() => {});
    if (chrome) { try { process.kill(chrome.proc.pid); } catch (_) {} }
    fs.writeFileSync(path.join(OUT, 'summary.json'), JSON.stringify({ ...provenance, results, passed: results.filter((r) => r.status === 'PASS').length, failed: results.filter((r) => r.status === 'FAIL').length }, null, 2) + '\n');
  }
  if (results.length !== 2 || results.some((r) => r.status !== 'PASS')) process.exitCode = 1;
  console.log(JSON.stringify({ passed: results.filter((r) => r.status === 'PASS').length, failed: results.filter((r) => r.status === 'FAIL').length }));
}
if (require.main === module) main().catch((e) => { console.error(e.message); process.exitCode = 1; });
