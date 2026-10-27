// BH-07 V2b app-profile heap verification (readiness §4.4).
//
// Real Flutter Web *profile* build served locally, real Chrome over CDP, real local
// Supabase Auth/PostgREST fixtures. Same document for the whole actor cycle: no reload,
// no Page.navigate between epochs, so "same instance" is genuine.
//
// Oracle: synthetic/fixture sentinel strings that only exist inside the Owner's private
// financial payloads. Presence is decided by scanning live V8 heap snapshots, so the
// verdict does not depend on dart2js class names (web profile minifies them).
//
// Raw heap dumps are written to a temp dir outside the repo, scanned once, then deleted
// and the deletion is verified. Only counts and short hashes are published.
const { execFileSync, spawn } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const crypto = require('node:crypto');

const ROOT = path.resolve(__dirname, '../..');
const OUT = path.resolve(process.env.BH07_APPHEAP_EVIDENCE || path.join(ROOT, 'docs/reviews/bh07/app_profile_heap_evidence'));
const DUMPS = path.join(os.tmpdir(), `bh07_appheap_dumps_${process.pid}`);
const ORACLE = path.join(__dirname, 'heap_oracle.py');
const DRIVER = path.join(ROOT, 'scripts/bh07_browser/run_browser_verification.js');
const WEB_URL = 'http://127.0.0.1:8088';
const WEB_PORT = 8088;
const API_URL = 'http://127.0.0.1:54321';
const CLUB_A = 'aaaaaaaa-1111-4111-8111-111111111111';
const UI_SESSION_TITLE = 'UI Flow Session published to complete';
const UI_SESSION_ID = '10000000-0000-4000-8000-000000000099';
const PASSWORDS = { ownera: 'bh07-http-pass-123456', cohosta: 'bh07-http-pass-123456', membera: 'bh07-http-pass-123456' };
const PY = process.platform === 'win32' ? 'python' : 'python3';

const { CdpClient } = require(DRIVER);
const { hashArtifacts, snapshotArtifacts, assertArtifactsFresh, assertPortFree, assertServedMatches } = require('./build_guard');
const CHROME_PATH = process.env.CHROME_PATH || 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const DEBUG_PORT = 9337;
const BUILD_DIR = path.join(ROOT, 'build/web');
// Two actor paths, one document each: the renderer reliably survives four heap
// snapshots, so Owner -> logout -> Cohost and Owner -> logout -> Member each get
// their own same-document run instead of one six-snapshot chain.
const ACTORS = ['cohost', 'member'];

const logLines = [];
function log(msg) {
  const line = `[${new Date().toISOString()}] ${msg}`;
  console.log(line);
  logLines.push(line);
}
const wait = (ms) => new Promise((r) => setTimeout(r, ms));
const text = (e) => `${e.text || ''}\n${e.aria || ''}`;
const button = (label) => (e) => (e.role === 'button' || e.tag === 'BUTTON') && ((e.text || '').trim() === label || e.aria === label);
const sha12 = (value) => crypto.createHash('sha256').update(String(value)).digest('hex').slice(0, 12);

function run(cmd, args, opts = {}) {
  return execFileSync(cmd, args, { cwd: ROOT, encoding: 'utf8', maxBuffer: 64 * 1024 * 1024, ...opts });
}

// The oracle signals a FAIL verdict with exit 1 and still prints it: a measured failure is
// evidence that must be published, not an aborted run. Any other exit stays fatal.
function runVerdict(cmd, args) {
  try {
    return run(cmd, args);
  } catch (error) {
    if (error.status === 1 && error.stdout) return error.stdout;
    throw error;
  }
}

async function checked(cdp, method, params = {}, timeoutMs = 60000) {
  // A dead renderer otherwise leaves the run hanging with no evidence.
  const result = await Promise.race([
    cdp.send(method, params),
    new Promise((_, reject) => setTimeout(() => reject(new Error(`${method}: CDP timeout after ${timeoutMs}ms`)), timeoutMs)),
  ]);
  if (result.error) throw new Error(`${method}: ${result.error.message}`);
  return result.result;
}

// Chrome is launched here (not through the V1 driver helper) so its stderr lands in a
// file: a browser that dies mid-run must leave a reason behind, not a silent hang.
async function startChromeLogged(logFile) {
  const userDataDir = path.join(os.tmpdir(), `bh07_appheap_chrome_${process.pid}`);
  fs.rmSync(userDataDir, { recursive: true, force: true });
  fs.mkdirSync(userDataDir, { recursive: true });
  const stderr = fs.openSync(logFile, 'a');
  const proc = spawn(CHROME_PATH, [
    `--remote-debugging-port=${DEBUG_PORT}`,
    '--headless=new',
    '--no-first-run',
    '--no-default-browser-check',
    '--disable-gpu',
    '--disable-background-networking',
    '--window-size=1280,900',
    `--user-data-dir=${userDataDir}`,
    'about:blank',
  ], { detached: true, stdio: ['ignore', 'ignore', stderr] });
  fs.closeSync(stderr);
  for (let i = 0; i < 50; i++) {
    await wait(200);
    try {
      const res = await fetch(`http://127.0.0.1:${DEBUG_PORT}/json/version`);
      if (res.ok) return { proc, version: await res.json(), userDataDir };
    } catch (_) { /* not listening yet */ }
  }
  throw new Error(`Chrome failed to start on port ${DEBUG_PORT}`);
}

// Every CDP call must be able to fail: a dead browser used to leave the run hanging.
function hardenCdp(cdp, timeoutMs = 60000) {
  const originalSend = cdp.send.bind(cdp);
  cdp.send = (method, params = {}) => Promise.race([
    originalSend(method, params),
    new Promise((_, reject) => setTimeout(
      () => reject(new Error(`${method}: CDP timeout after ${timeoutMs}ms`)), timeoutMs)),
  ]);
}

function supabaseEnv() {
  const raw = execFileSync('npx', ['--yes', 'supabase@2.121.0', 'status', '-o', 'env'],
    { cwd: ROOT, encoding: 'utf8', shell: true, maxBuffer: 8 * 1024 * 1024 });
  const env = {};
  for (const line of raw.split(/\r?\n/)) {
    const m = line.trim().match(/^([A-Z_]+)="(.*)"$/);
    if (m) env[m[1]] = m[2];
  }
  for (const key of ['ANON_KEY', 'SERVICE_ROLE_KEY']) {
    if (!env[key]) throw new Error(`local Supabase status is missing ${key}`);
  }
  return env;
}

async function restGet(env, query) {
  const res = await fetch(`${env.API_URL}/rest/v1/${query}`, {
    headers: { apikey: env.SERVICE_ROLE_KEY, Authorization: `Bearer ${env.SERVICE_ROLE_KEY}` },
  });
  if (!res.ok) throw new Error(`PostgREST ${query}: ${res.status}`);
  return res.json();
}

// Sentinels are real fixture values that only the Owner's private payloads carry. Each one
// declares the class the gate depends on (see SENTINEL_CLASSES below).
async function resolveSentinels(env, runId) {
  const banks = await restGet(env, `club_bank_accounts?club_id=eq.${CLUB_A}&select=account_number,account_name&status=eq.active`);
  if (!banks.length) throw new Error('no active club bank account fixture for club A');
  const expenses = await restGet(env, `session_expenses?session_id=eq.${UI_SESSION_ID}&select=id,title&status=eq.posted`);
  if (!expenses.length) throw new Error('no posted expense fixture for the UI session');
  const players = await restGet(env, `session_players?session_id=eq.${UI_SESSION_ID}&select=id&order=id.asc`);
  return {
    bank: banks[0].account_number,
    receiver: banks[0].account_name,
    expense: expenses[0].title,
    expense_id: expenses[0].id,
    players: players.map((row) => row.id),
    probe: `BH07APPHEAPPROBE-${runId}`,
  };
}

// Class of each sentinel, declared once so runner, oracle and auditor agree:
// - `rendered` text is laid out by the engine, which keeps it in its own segmentation LRU
//   after the app drops it (flutter/engine web_ui text_fragmenter.dart), so retention there
//   is published as a residual risk and never as app state;
// - `distinctive: false` short digit runs can match inside an unrelated UUID (measured:
//   `0000000007` matched only `10000000-0000-4000-8000-000000000007`), so a hit proves
//   nothing and is reported as a note instead of gating;
// - `scope: finance` keeps at least one financial value in the gated set.
const SENTINEL_CLASSES = {
  bank: { rendered: false, distinctive: false, scope: 'bank' },
  receiver: { rendered: false, distinctive: true, scope: 'bank' },
  expense: { rendered: true, distinctive: true, scope: 'finance' },
  expense_id: { rendered: false, distinctive: true, scope: 'finance' },
  player_a: { rendered: false, distinctive: true, scope: 'identity' },
  player_b: { rendered: false, distinctive: true, scope: 'identity' },
  probe: { rendered: false, distinctive: true, scope: 'control' },
};
const SENTINEL_KINDS = {
  bank: 'club bank account number (Owner-private, digits only)',
  receiver: 'bank account holder name (loaded by payment instructions, not the Owner surface)',
  expense: 'posted session expense title rendered as widget text',
  expense_id: 'posted session expense id returned by get_session_finance (never rendered)',
  player_a: 'session player id of the seeded roster (never rendered)',
  player_b: 'second session player id of the seeded roster (never rendered)',
  probe: 'detector sanity marker set on window',
};

async function buildProfile(env) {
  const args = ['build', 'web', '--profile',
    '--dart-define=APP_ENV=test',
    `--dart-define=SUPABASE_URL=${env.API_URL}`,
    `--dart-define=SUPABASE_ANON_KEY=${env.ANON_KEY}`];
  const before = snapshotArtifacts(BUILD_DIR);
  const startedAt = Date.now();
  log('building Flutter web profile bundle (dart-defines not printed)');
  run(process.platform === 'win32' ? 'flutter.bat' : 'flutter', args, { shell: process.platform === 'win32' });
  if (!fs.existsSync(path.join(BUILD_DIR, 'index.html'))) throw new Error('flutter build web produced no build/web/index.html');
  // Provenance: these hashes are the artifacts the server must answer with (review AH5).
  assertArtifactsFresh(BUILD_DIR, startedAt, before);
  return {
    mode: 'profile',
    build_ms: Date.now() - startedAt,
    started_at: new Date(startedAt).toISOString(),
    artifacts_root: 'build/web',
    artifacts: hashArtifacts(BUILD_DIR),
  };
}

function startServer() {
  const proc = spawn(PY, ['-m', 'http.server', String(WEB_PORT), '--bind', '127.0.0.1',
    '--directory', BUILD_DIR], { cwd: ROOT, stdio: 'ignore' });
  return proc;
}

async function waitForServer(timeoutMs = 20000) {
  const end = Date.now() + timeoutMs;
  while (Date.now() < end) {
    try {
      const res = await fetch(`${WEB_URL}/index.html`);
      if (res.ok) return;
    } catch (_) { /* server not up yet */ }
    await wait(250);
  }
  throw new Error(`static server did not answer on ${WEB_URL}`);
}

async function login(cdp, actor) {
  await cdp.clickSemantic((e) => (e.role === 'button' || e.tag === 'BUTTON') && /Đăng [Nn]hập/.test(text(e)), 'Open login form');
  for (const [label, value] of [['Email', `${actor}@example.test`], ['Mật khẩu', PASSWORDS[actor]]]) {
    await cdp.clickSemantic((e) => e.tag === 'INPUT' && (e.aria || '').includes(label), 'Focus login input');
    await checked(cdp, 'Input.insertText', { text: value });
  }
  await cdp.clickSemantic(button('Đăng Nhập'), 'Submit real Auth login');
  await wait(1500);
  await cdp.clickSemantic((e) => e.role === 'tab' && e.aria === 'Tài Khoản', 'Verify account identity');
  await cdp.waitForSemantic((e) => text(e).includes(`${actor}@example.test`), `UI account email ${actor}`);
}

async function home(cdp) {
  for (let i = 0; i < 5; i++) {
    if ((await cdp.getAllSemantics()).some((e) => e.role === 'tab' && e.aria === 'Tài Khoản')) return;
    await cdp.clickBack('Return through AppBar to main tabs');
  }
  throw new Error('Main tabs not reachable through UI');
}

async function logout(cdp) {
  await home(cdp);
  await cdp.clickSemantic((e) => e.role === 'tab' && e.aria === 'Tài Khoản', 'Account tab');
  await cdp.clickSemantic(button('Đăng xuất'), 'Logout');
  await cdp.clickSemantic(button('Đăng Xuất'), 'Confirm logout');
  await cdp.waitForSemantic((e) => text(e).includes('Bạn đang xem dưới dạng khách'), 'Guest UI');
  const tokenCleared = await cdp.evaluate(`!Object.keys(localStorage).some(k => k.startsWith('sb-') && k.endsWith('-auth-token'))`);
  if (!tokenCleared) throw new Error('Auth token remains after logout');
}

async function openOwnerFinance(cdp) {
  await cdp.clickSemantic((e) => e.role === 'tab' && e.aria === 'Buổi Chơi', 'Sessions tab');
  await cdp.clickSemantic((e) => text(e).includes('Lịch sử buổi'), 'History');
  await cdp.clickSemantic((e) => text(e).includes(UI_SESSION_TITLE), 'Fixture history row');
  // Owner-private payloads beyond the bank sentinel only load here: expenses, charges
  // and payments of the session (retained-path coverage for §4.4).
  await cdp.clickSemantic((e) => text(e).includes('Tài chính & thu tiền'), 'Open session finance');
  await cdp.waitForSemantic((e) => text(e).includes('Chi phí ('), 'Owner finance screen loaded');
  await cdp.clickBack('Return to session detail');
  await cdp.clickSemantic((e) => text(e).includes('Tổng kết buổi'), 'Summary entry');
  await cdp.waitForSemantic((e) => text(e).includes('Tài chính tổng hợp'), 'Owner finance card loaded');
}

async function openCohostSummary(cdp) {
  await cdp.clickSemantic((e) => e.role === 'tab' && e.aria === 'Buổi Chơi', 'Sessions tab');
  await cdp.clickSemantic((e) => text(e).includes('Lịch sử buổi'), 'History');
  await cdp.clickSemantic((e) => text(e).includes(UI_SESSION_TITLE), 'Fixture history row');
  await cdp.clickSemantic((e) => text(e).includes('Tổng kết buổi'), 'Summary entry');
  await cdp.waitForSemantic((e) => text(e).includes('Chỉ xem số lượng'), 'Cohost count-only summary');
}

async function openMemberHistory(cdp) {
  await cdp.clickSemantic((e) => e.role === 'tab' && e.aria === 'Buổi Chơi', 'Sessions tab');
  await cdp.clickSemantic((e) => text(e).includes('Lịch sử buổi'), 'History');
  await wait(1500);
}

// One live V8 heap snapshot, scanned once, then deleted. The chunk events are the only
// way CDP delivers a snapshot, so the driver's message handler is wrapped temporarily.
async function takeSnapshot(cdp, label, sentinelsPath, classesPath) {
  const file = path.join(DUMPS, `${label}.heapsnapshot`);
  const chunks = [];
  const original = cdp.ws.onmessage;
  let finish;
  const progressed = new Promise((resolve) => { finish = resolve; });
  cdp.ws.onmessage = (event) => {
    original(event);
    const msg = JSON.parse(event.data);
    if (msg.method === 'HeapProfiler.addHeapSnapshotChunk') chunks.push(msg.params.chunk);
    if (msg.method === 'HeapProfiler.reportHeapSnapshotProgress' && msg.params.finished) finish();
  };
  try {
    await checked(cdp, 'HeapProfiler.enable');
    await checked(cdp, 'HeapProfiler.collectGarbage');
    const taken = checked(cdp, 'HeapProfiler.takeHeapSnapshot', { reportProgress: true });
    await Promise.all([taken, progressed]);
  } finally {
    cdp.ws.onmessage = original;
  }
  fs.writeFileSync(file, chunks.join(''));
  const scanned = JSON.parse(run(PY, ['-X', 'utf8', ORACLE, 'scan', '--snapshot', file, '--sentinels', sentinelsPath,
    '--classes', classesPath, '--paths'], { shell: false }));
  fs.unlinkSync(file);
  await checked(cdp, 'Runtime.evaluate', { expression: '1' }, 15000);
  log(`${label}: snapshot ${scanned.size_bytes} bytes sha=${scanned.sha256_12} ok=${scanned.ok} `
    + `present=${JSON.stringify(Object.fromEntries(Object.entries(scanned.sentinels).map(([k, v]) => [k, v.present])))}`);
  return scanned;
}

async function runCycle(cycle, actor, sentinelsPath, classesPath, cdp) {
  const epochs = {};
  await cdp.evaluate(`window.__bh07heapProbe = ${JSON.stringify(PROBE_VALUE)}`);
  await wait(500);
  epochs.baseline = await takeSnapshot(cdp, `c${cycle}_baseline`, sentinelsPath, classesPath);

  await login(cdp, 'ownera');
  await openOwnerFinance(cdp);
  await cdp.evaluate(`window.__bh07heapProbe = ${JSON.stringify(PROBE_VALUE)}`);
  epochs.owner_active = await takeSnapshot(cdp, `c${cycle}_owner_active`, sentinelsPath, classesPath);

  await logout(cdp);
  epochs.post_logout = await takeSnapshot(cdp, `c${cycle}_post_logout`, sentinelsPath, classesPath);

  await login(cdp, `${actor}a`);
  if (actor === 'cohost') await openCohostSummary(cdp);
  else await openMemberHistory(cdp);
  epochs.post_actor = await takeSnapshot(cdp, `c${cycle}_post_${actor}`, sentinelsPath, classesPath);

  return epochs;
}

let PROBE_VALUE = '';
// Live sentinel values, kept only in memory so publication can be checked and redacted.
const RAW_SENTINEL_VALUES = {};

async function main() {
  fs.mkdirSync(OUT, { recursive: true });
  fs.mkdirSync(DUMPS, { recursive: true });
  const runId = crypto.randomBytes(4).toString('hex');
  const argv = process.argv.slice(2);
  const cycles = Number(argv[argv.indexOf('--cycles') + 1]) || 2;
  const reuseBuild = argv.includes('--reuse-build');
  const summary = {
    gate: 'V2b — app-profile Dart heap / in-memory retention after actor switch',
    reference: 'docs/reviews/bh07/bh07_readiness.md §4.4',
    status: 'NOT RUN',
    measurement_surface: 'Flutter Web profile build + Chrome DevTools Protocol HeapProfiler (V8 heap snapshot)',
    oracle: 'fixture sentinel strings counted in live V8 heap snapshots; no class-name dependency',
    tested_source_sha: run('git', ['rev-parse', 'HEAD']).trim(),
    git_dirty: run('git', ['status', '--porcelain']).trim() !== '',
    git_dirty_paths: run('git', ['status', '--porcelain']).trim().split(/\r?\n/).filter(Boolean),
    started_at: new Date().toISOString(),
    environment: { os: `${process.platform} ${os.release()}`, node: process.version },
    sentinels: {},
    cycles: [],
    notes: [],
    residual_risks: [],
    cleanup: {},
  };
  let chrome, server, cdp;
  try {
    const env = supabaseEnv();
    const sentinels = await resolveSentinels(env, runId);
    PROBE_VALUE = sentinels.probe;
    const values = {
      bank: sentinels.bank,
      receiver: sentinels.receiver,
      expense: sentinels.expense,
      expense_id: sentinels.expense_id,
      player_a: sentinels.players[0],
      player_b: sentinels.players[1],
      probe: sentinels.probe,
    };
    if (!values.player_b) throw new Error('the fixture session needs two players for the gated set');
    Object.assign(RAW_SENTINEL_VALUES, values);
    // `available` is explicit so the auditor never has to guess why a length/hash is
    // missing (review 76334e2 AH8). A value the Owner surface never loaded is reported as
    // not loaded instead of being invented as coverage.
    summary.sentinels = Object.fromEntries(Object.entries(values).filter(([, v]) => v)
      .map(([name, value]) => [name, {
        available: true,
        sha256_12: sha12(value),
        length: value.length,
        kind: SENTINEL_KINDS[name],
        ...SENTINEL_CLASSES[name],
      }]));
    const sentinelsPath = path.join(DUMPS, 'sentinels.json');
    const classesPath = path.join(DUMPS, 'classes.json');
    fs.writeFileSync(sentinelsPath, JSON.stringify(values));
    fs.writeFileSync(classesPath, JSON.stringify(SENTINEL_CLASSES));

    if (reuseBuild) {
      // A build this run did not produce cannot prove profile provenance (review AH5).
      throw new Error('--reuse-build is not accepted: the run must build the profile artifact it measures');
    } else {
      await assertPortFree(WEB_PORT);
      summary.environment.build = await buildProfile(env);
    }
    summary.environment.flutter = run(process.platform === 'win32' ? 'flutter.bat' : 'flutter', ['--version'], { shell: process.platform === 'win32' })
      .split(/\r?\n/)[0].trim();

    server = startServer();
    await waitForServer();
    // The served bytes must be the artifact we hashed, not a leftover server's build.
    summary.environment.build.served_match = await assertServedMatches(WEB_URL, BUILD_DIR);

    for (let cycle = 1; cycle <= cycles; cycle++) {
      const actor = ACTORS[(cycle - 1) % ACTORS.length];
      log(`cycle ${cycle}: actor path Owner -> logout -> ${actor}`);
      chrome = await startChromeLogged(path.join(DUMPS, 'chrome.log'));
      const launched = chrome;
      launched.proc.on('exit', (code, signal) => {
        if (launched.expectedExit) return;
        log(`cycle ${cycle}: chrome exited unexpectedly code=${code} signal=${signal}`);
      });
      cdp = new CdpClient(chrome.version.webSocketDebuggerUrl);
      hardenCdp(cdp);
      await cdp.connect();
      await cdp.createTab(WEB_URL);
      summary.environment.chrome = chrome.version['Browser'] || chrome.version.Browser;
      await cdp.waitForSemantic((e) => text(e).includes('Bạn đang xem dưới dạng khách'), 'guest baseline UI', 30000);
      const origin = await cdp.evaluate('performance.timeOrigin');
      const epochs = await runCycle(cycle, actor, sentinelsPath, classesPath, cdp);
      const originAfter = await cdp.evaluate('performance.timeOrigin');
      if (origin !== originAfter) throw new Error(`cycle ${cycle}: document reloaded between epochs (${origin} != ${originAfter})`);
      const scans = {};
      for (const [epoch, result] of Object.entries(epochs)) scans[epoch] = result;
      const scansPath = path.join(DUMPS, `c${cycle}_scans.json`);
      fs.writeFileSync(scansPath, JSON.stringify(scans));
      // Expectations come from the oracle, not from a second copy of the rule in this
      // file, so runner and auditor cannot disagree about what is gated.
      const expectationsPath = path.join(DUMPS, 'expectations.json');
      run(PY, ['-X', 'utf8', ORACLE, 'expectations', '--scans', scansPath, '--out', expectationsPath]);
      const verdict = JSON.parse(runVerdict(PY, ['-X', 'utf8', ORACLE, 'decide', '--scans', scansPath,
        '--expectations', expectationsPath, '--cleanup-ok', 'true', '--mode', summary.environment.build.mode,
        '--require-paths']));
      summary.cycles.push({ cycle, actor, same_document: true, time_origin: origin, epochs, verdict });
      await cdp.close();
      launched.expectedExit = true;
      try { process.kill(chrome.proc.pid); } catch (_) { /* already gone */ }
      try { fs.rmSync(chrome.userDataDir, { recursive: true, force: true }); } catch (_) { /* best effort */ }
      chrome = null; cdp = null;
    }

    const remaining = fs.existsSync(DUMPS) ? fs.readdirSync(DUMPS).filter((f) => f.endsWith('.heapsnapshot')) : [];
    summary.cleanup = {
      dump_dir_outside_repo: !DUMPS.startsWith(ROOT),
      raw_snapshots_remaining: remaining.length,
    };
    const verdicts = summary.cycles.map((c) => c.verdict.verdict);
    summary.verdict = verdicts.length === cycles && verdicts.every((v) => v === 'PASS') ? 'PASS' : 'FAIL';
    summary.findings = summary.cycles.flatMap((c) => c.verdict.findings.map((f) => `cycle ${c.cycle}: ${f}`));
    // Published but never gated: a coincidence in the gated set, and rendered text kept by
    // the web engine's segmentation cache after the app dropped it.
    summary.notes = summary.cycles.flatMap((c) => (c.verdict.notes || []).map((n) => `cycle ${c.cycle}: ${n}`));
    summary.residual_risks = summary.cycles.flatMap((c) => (c.verdict.residual_risks || [])
      .map((risk) => ({ cycle: c.cycle, ...risk })));
    summary.status = summary.verdict === 'PASS' ? 'RUN' : 'FAIL';
  } catch (error) {
    summary.status = 'NOT RUN';
    summary.error = error.message;
    log(`aborted: ${error.message}`);
  } finally {
    if (cdp) await cdp.close().catch(() => {});
    if (chrome) { try { process.kill(chrome.proc.pid); } catch (_) { /* already gone */ } }
    if (server) { try { process.kill(server.pid); } catch (_) { /* already gone */ } }
    summary.finished_at = new Date().toISOString();
    // Browser stderr is diagnostic only; keep the interesting lines, redact endpoints.
    if (fs.existsSync(path.join(DUMPS, 'chrome.log'))) {
      const digest = fs.readFileSync(path.join(DUMPS, 'chrome.log'), 'utf8').split(/\r?\n/)
        .filter((line) => /FATAL|crash|out of memory|listening on/i.test(line))
        .slice(-10)
        .map((line) => line.replace(/ws:\/\/\S+/g, 'ws://<redacted>').slice(0, 200));
      for (const line of digest) log(`chrome stderr: ${line}`);
    }
    // Raw heap dumps and the throw-away Chrome profile must not survive the run.
    const chromeDir = path.join(os.tmpdir(), `bh07_appheap_chrome_${process.pid}`);
    for (const dir of [DUMPS, chromeDir]) {
      try { fs.rmSync(dir, { recursive: true, force: true }); } catch (_) { /* best effort */ }
    }
    summary.cleanup = {
      ...summary.cleanup,
      dumps_dir_removed: !fs.existsSync(DUMPS),
      chrome_profile_dir_removed: !fs.existsSync(chromeDir),
    };
    summary.cleanup.ok = summary.cleanup.dump_dir_outside_repo === true
      && summary.cleanup.raw_snapshots_remaining === 0
      && summary.cleanup.dumps_dir_removed === true
      && summary.cleanup.chrome_profile_dir_removed === true;
    if (!summary.cleanup.ok) {
      summary.findings = [...(summary.findings || []), 'heap dump or browser profile cleanup not verified'];
      if (summary.status === 'RUN') summary.status = 'FAIL';
    }
    writeEvidence(summary);
  }
  console.log(JSON.stringify({ status: summary.status, verdict: summary.verdict || null, cycles: summary.cycles.length }));
  process.exitCode = summary.status === 'RUN' ? 0 : 1;
}

function sentinelClassLabel(meta) {
  const scope = meta && meta.scope ? meta.scope : 'identity';
  const rendered = meta && meta.rendered === true ? 'rendered' : 'not rendered';
  const distinctive = meta && meta.distinctive === true ? 'distinctive' : 'not distinctive';
  return `${scope}, ${rendered}, ${distinctive}`;
}

function findSentinelLeaks(texts, values = RAW_SENTINEL_VALUES) {
  // Review 57ec02c AH3-B: the published bytes must never carry a raw sentinel value.
  // Matching the live value is exact, so this cannot fire on a hash or a length.
  const leaks = [];
  for (const [name, value] of Object.entries(values)) {
    if (!value) continue;
    if (texts.some((text) => String(text).includes(value))) leaks.push(name);
  }
  return leaks;
}

function redactSentinels(text, values = RAW_SENTINEL_VALUES) {
  let out = String(text);
  for (const value of Object.values(values)) {
    if (!value) continue;
    out = out.split(value).join('<redacted>');
  }
  return out;
}

function renderReport(summary) {
  const build = (summary.environment || {}).build || {};
  const lines = [
    '# V2b — app-profile heap / in-memory retention after actor switch',
    '',
    `- Gate: ${summary.gate}`,
    `- Reference: ${summary.reference}`,
    `- Status: **${summary.status}**${summary.verdict ? ` (verdict ${summary.verdict})` : ''}`,
    `- Tested source: \`${summary.tested_source_sha}\` (git dirty: ${summary.git_dirty})`,
    `- Measurement surface: ${summary.measurement_surface}`,
    `- Oracle: ${summary.oracle}`,
    `- Build: mode=${build.mode || 'n/a'} reused=${build.reused || false} `
      + `artifacts=${Object.keys(build.artifacts || {}).length} served_match=${build.served_match || false}`,
    `- Chrome: ${(summary.environment || {}).chrome || 'n/a'}; Flutter: ${(summary.environment || {}).flutter || 'n/a'}`,
    '',
    '## Sentinels (values never published)',
    '',
    '| sentinel | kind | class | length | sha256[:12] |',
    '| --- | --- | --- | --- | --- |',
    ...Object.entries(summary.sentinels || {}).map(([name, s]) =>
      `| ${name} | ${s.kind} | ${sentinelClassLabel(s)} | ${s.length ?? 'n/a'} | ${s.sha256_12 || 'n/a'} |`),
    '',
    '## Cycles',
    '',
    '| cycle | actor path | same document | epoch | snapshot bytes | snapshot sha256[:12] | present sentinels |',
    '| --- | --- | --- | --- | --- | --- | --- |',
  ];
  for (const cycle of summary.cycles || []) {
    for (const [epoch, scan] of Object.entries(cycle.epochs || {})) {
      const present = Object.entries(scan.sentinels || {})
        .filter(([, v]) => v.present).map(([k]) => k).join(', ') || 'none';
      lines.push(`| ${cycle.cycle} | Owner -> logout -> ${cycle.actor} | ${cycle.same_document} | ${epoch} `
        + `| ${scan.size_bytes ?? 'n/a'} | ${scan.sha256_12 || 'n/a'} | ${present} |`);
    }
  }
  lines.push('', '## Retained paths', '',
    '| cycle | epoch | sentinel | reachable | root kind | path length | path sha256[:12] |',
    '| --- | --- | --- | --- | --- | --- | --- |');
  for (const cycle of summary.cycles || []) {
    for (const [epoch, scan] of Object.entries(cycle.epochs || {})) {
      for (const name of Object.keys(scan.paths || {}).sort()) {
        const record = scan.paths[name] || {};
        const reachable = record.reachable === true;
        lines.push(`| ${cycle.cycle} | ${epoch} | ${name} | ${reachable} `
          + `| ${reachable ? record.root_kind : 'n/a'} | ${reachable ? record.path_len : 'n/a'} `
          + `| ${reachable ? record.path_sha256_12 : 'n/a'} |`);
      }
    }
  }
  lines.push('', '## Residual risks', '',
    'Rendered text the Owner saw can stay in the web engine’s segmentation LRU after the app',
    'dropped it. That retainer is engine-internal (flutter/engine web_ui text_fragmenter.dart),',
    'so it is published here and never counted as app state by the gate.',
    '',
    '| cycle | epoch | sentinel | root kind | path length | path sha256[:12] |',
    '| --- | --- | --- | --- | --- | --- |');
  const risks = summary.residual_risks || [];
  if (!risks.length) {
    lines.push('| none | n/a | n/a | n/a | n/a | n/a |');
  } else {
    for (const risk of risks) {
      lines.push(`| ${risk.cycle} | ${risk.epoch} | ${risk.sentinel} | ${risk.root_kind || 'n/a'} `
        + `| ${risk.path_len || 'n/a'} | ${risk.path_sha256_12 || 'n/a'} |`);
    }
  }
  lines.push('', '## Notes', '');
  const notes = summary.notes || [];
  lines.push(...(notes.length ? notes.map((n) => `- ${n}`) : ['- none']));
  lines.push('', '## Findings', '');
  const findings = summary.findings || [];
  lines.push(...(findings.length ? findings.map((f) => `- ${f}`) : ['- none']));
  if (summary.error) lines.push(`- run aborted: ${summary.error}`);
  lines.push('', '## Cleanup', '', `- ${JSON.stringify(summary.cleanup || {})}`, '');
  lines.push('## Limitations', '',
    '- Web *profile* build measures the dart2js/V8 heap, not the Dart VM heap of a desktop/mobile build;',
    '  no Visual Studio or Android SDK is installed on this machine, so the VM-service path is NOT RUN.',
    '- Only *unrendered, distinctive* values gate the verdict. Rendered text is retained by the web',
    '  engine’s segmentation LRU after the app drops it, so gating on it would measure the engine, and',
    '  a short digit run can match inside an unrelated fixture UUID (measured for `0000000007`).',
    '- The bank account holder name is only fetched by the player payment-instructions surface, so the',
    '  Owner path never loads it; it is measured and reported as not loaded, not as coverage.',
    '- Sentinels prove that specific Owner-private values are no longer reachable; they do not enumerate',
    '  every retained object of the financial models.',
    '- Raw heap snapshots are written outside the repository, scanned once and deleted; only counts and',
    '  short hashes are published.', '');
  return lines.join('\n');
}

function writeEvidence(summary) {
  const hashFile = (file) => crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
  const drafts = () => ({
    'summary.json': JSON.stringify(summary, null, 2) + '\n',
    'run.log': logLines.join('\n') + '\n',
    'report.md': renderReport(summary),
  });
  // Sanitize before publication: a raw sentinel in any published byte fails the run.
  const leaks = findSentinelLeaks(Object.values(drafts()));
  if (leaks.length) {
    summary.findings = [...(summary.findings || []),
      `raw sentinel value reached the publication step (${leaks.join(', ')}); redacted, run failed`];
    summary.verdict = 'FAIL';
    summary.status = 'FAIL';
  }
  for (const [name, text] of Object.entries(drafts())) {
    fs.writeFileSync(path.join(OUT, name), redactSentinels(text));
  }
  const manifest = ['summary.json', 'run.log', 'report.md']
    .map((name) => `${hashFile(path.join(OUT, name))}  ${name}`).join('\n');
  fs.writeFileSync(path.join(OUT, 'hashes.sha256'), manifest + '\n');
}

module.exports = { findSentinelLeaks, redactSentinels, renderReport, RAW_SENTINEL_VALUES };

if (require.main === module) main().catch((e) => { console.error(e.stack || e.message); process.exitCode = 1; });
