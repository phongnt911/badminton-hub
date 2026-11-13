// Companion runner for BH-07 V2b PaymentInstructions synthetic receiverSnapshot heap measurement.
// Preserves existing run_app_profile_heap.js, heap_oracle.py, verify_evidence.py, and all historical bundles.
//
// Key guarantees:
// - Reads private local config JSON; never invokes `npx supabase status` and never logs credentials/canaries.
// - Targets bh07-android-db and strictly loopback :54321 Supabase URL only.
// - Never injects canaries via page.evaluate / Runtime.evaluate / JS globals; canaries load only via RPC.
// - Streams CDP HeapProfiler chunks directly to temp files outside the repository with a hard 512 MiB cap.
// - Verifies reused served builds across ALL build/web artifacts against explicit provenance input.
// - Runs 2 cycles x 4 epochs (8 epochs) in one same-document browser session and cleans up in finally.

const { execFileSync, spawn } = require('node:child_process');
const crypto = require('node:crypto');
const fs = require('node:fs');
const net = require('node:net');
const os = require('node:os');
const path = require('node:path');

const ROOT = path.resolve(__dirname, '../..');
const ORACLE = path.join(__dirname, 'heap_oracle.py');
const FIXTURE_CLI = path.join(__dirname, 'disposable_instructions_fixture.py');
const DRIVER = path.join(ROOT, 'scripts/bh07_browser/run_browser_verification.js');
const BUILD_DIR = path.join(ROOT, 'build/web');
const DEFAULT_WEB_URL = 'http://127.0.0.1:8088';
const UI_SESSION_TITLE = 'UI Flow Session published to complete';
const MAX_PARSE_BYTES = 512 * 1024 * 1024;
const PY = process.platform === 'win32' ? 'python' : 'python3';
const REQUIRED_CANARIES = ['canary_instr_a', 'canary_instr_b'];
const REQUIRED_EPOCHS = ['baseline', 'owner_active', 'post_logout', 'post_actor'];
const MIN_PREFIX_LEAK = 20;
const DUMPS_TOKEN_FILENAME = '.bh07_owned_dumps_dir.json';
const DUMPS_OWNER_MARKER = 'bh07_instructions_heap';
const FRAME_RE = /^([a-z_]+)(?::(.*))? -> (.+)$/;
const STRING_CHILD_TYPES = new Set(['string', 'concatenated string', 'sliced string']);
const CONTAINER_CHILD_TYPES = new Set(['object', 'array']);
const FORBIDDEN_DTO_LABEL_WORDS = ['xmlhttprequest', 'responsetext', 'script', 'xhr'];
const PROVIDER_HOLDER_EDGE = '_provider$_value';
const VALID_MAP_ROOT_PROPS = new Set(['_strings', '_nums', '_rest', '_first', '_last']);
const VALID_MAP_LINK_PROPS = new Set(['_next', '_previous']);
const MAX_CONSTRUCTOR_SNIPPET_BYTES = 32768;
const MAX_SOURCE_BINDING_BYTES = 65536;
const HEX64_RE = /^[0-9a-f]{64}$/;
const SOURCE_SECRET_PATTERNS = [
  /eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}/,
  /bh07-http-pass/,
  /SERVICE_ROLE_KEY|SUPABASE_ANON_KEY\s*=/,
  /postgresql:\/\/[^\s"]+:[^\s"]+@/,
];

const { CdpClient } = require(DRIVER);
const { hashArtifacts, snapshotArtifacts, assertArtifactsFresh, assertPortFree } = require('./build_guard');
const { shutdownOwnedBrowser } = require('./owned_browser_cleanup');

const wait = (ms) => new Promise((r) => setTimeout(r, ms));
const sha12 = (val) => crypto.createHash('sha256').update(String(val)).digest('hex').slice(0, 12);
const textOf = (e) => `${e.text || ''}\n${e.aria || ''}`;
const button = (label) => (e) =>
  (e.role === 'button' || e.tag === 'BUTTON') &&
  ((e.text || '').trim() === label || (e.aria || '').trim() === label);

function isInsideDir(targetPath, parentDir) {
  const rel = path.relative(path.resolve(parentDir), path.resolve(targetPath));
  return rel === '' || (!rel.startsWith('..') && !path.isAbsolute(rel));
}

function lstatSafe(p) {
  try {
    return fs.lstatSync(p);
  } catch (_) {
    return null;
  }
}

function canonicalizePathWithMissingTail(targetPath) {
  const abs = path.resolve(targetPath);
  const missing = [];
  let cur = abs;
  while (true) {
    if (fs.existsSync(cur) || lstatSafe(cur)) {
      const realBase = fs.realpathSync(cur);
      return missing.length ? path.join(realBase, ...missing.reverse()) : realBase;
    }
    const parent = path.dirname(cur);
    if (parent === cur) return abs;
    missing.push(path.basename(cur));
    cur = parent;
  }
}

function assertNoSymlinkChain(targetPath) {
  const tmpReal = fs.realpathSync(os.tmpdir());
  let cur = path.resolve(targetPath);
  while (true) {
    const st = lstatSafe(cur);
    if (st && st.isSymbolicLink()) {
      const curReal = (() => { try { return fs.realpathSync(cur); } catch (_) { return ''; } })();
      if (curReal !== tmpReal) {
        throw new Error(`path must not use or traverse symlink/junction: ${cur}`);
      }
    }
    const parent = path.dirname(cur);
    if (parent === cur) break;
    if (fs.existsSync(cur)) {
      try {
        if (fs.realpathSync(cur) === tmpReal) break;
      } catch (_) {}
    }
    cur = parent;
  }
}

function assertOutsideRepo(targetPath, label = 'path', rootDir = ROOT) {
  const resolved = path.resolve(targetPath);
  assertNoSymlinkChain(resolved);
  const canonicalTarget = canonicalizePathWithMissingTail(resolved);
  const canonicalRoot = fs.realpathSync(rootDir);

  if (resolved === path.parse(resolved).root || canonicalTarget === path.parse(canonicalTarget).root) {
    throw new Error(`${label} cannot be filesystem root: ${targetPath}`);
  }
  if (isInsideDir(canonicalTarget, canonicalRoot) || isInsideDir(resolved, path.resolve(rootDir))) {
    throw new Error(`${label} must be strictly outside repository root: ${targetPath}`);
  }
  if (isInsideDir(canonicalRoot, canonicalTarget) || isInsideDir(path.resolve(rootDir), resolved)) {
    throw new Error(`${label} cannot be an ancestor of repository root: ${targetPath}`);
  }
  return canonicalTarget;
}

function claimDumpsDirectory(dumpsDir, rootDir = ROOT) {
  const resolved = path.resolve(dumpsDir);
  assertOutsideRepo(resolved, 'dumps_dir', rootDir);
  if (fs.existsSync(resolved) || lstatSafe(resolved)) {
    throw new Error(`refusing preexisting dumps_dir target: ${resolved}`);
  }
  const parent = path.dirname(resolved);
  if (!fs.existsSync(parent)) {
    fs.mkdirSync(parent, { recursive: true, mode: 0o700 });
  }
  assertNoSymlinkChain(parent);
  fs.mkdirSync(resolved, { recursive: false, mode: 0o700 });
  const canonicalPath = fs.realpathSync(resolved);
  const token = crypto.randomUUID();
  const tokenFile = path.join(canonicalPath, DUMPS_TOKEN_FILENAME);
  const flags = fs.constants.O_CREAT | fs.constants.O_EXCL | fs.constants.O_WRONLY | (fs.constants.O_NOFOLLOW || 0);
  const fd = fs.openSync(tokenFile, flags, 0o600);
  try {
    fs.writeSync(fd, JSON.stringify({
      owner: DUMPS_OWNER_MARKER,
      token,
      canonical_path: canonicalPath,
      pid: process.pid,
    }, null, 2) + '\n', null, 'utf8');
  } finally {
    fs.closeSync(fd);
  }
  return { dir: canonicalPath, canonical_path: canonicalPath, token, tokenFile };
}

function deleteOwnedDumpsDirectory(claim, rootDir = ROOT) {
  if (!claim || typeof claim !== 'object' || !claim.dir || !claim.token || !claim.tokenFile || !claim.canonical_path) {
    throw new Error('cannot delete dumps_dir without verified ownership claim');
  }
  const st = lstatSafe(claim.dir);
  if (!st) {
    return { removed: true, alreadyAbsent: true };
  }
  if (st.isSymbolicLink() || !st.isDirectory()) {
    throw new Error(`refusing to delete symlink/non-directory dumps_dir: ${claim.dir}`);
  }
  const canonical = fs.realpathSync(claim.dir);
  assertOutsideRepo(canonical, 'dumps_dir', rootDir);
  if (canonical !== claim.canonical_path) {
    throw new Error(`dumps_dir canonical path mismatch: ${canonical} != ${claim.canonical_path}`);
  }
  const tokenSt = lstatSafe(claim.tokenFile);
  if (!tokenSt || tokenSt.isSymbolicLink() || !tokenSt.isFile()) {
    throw new Error(`dumps_dir ownership token missing or invalid: ${claim.tokenFile}`);
  }
  const tokenData = JSON.parse(fs.readFileSync(claim.tokenFile, 'utf8'));
  if (tokenData.owner !== DUMPS_OWNER_MARKER
      || tokenData.token !== claim.token
      || tokenData.canonical_path !== claim.canonical_path) {
    throw new Error('dumps_dir ownership token mismatch');
  }
  fs.rmSync(canonical, { recursive: true, force: true });
  return { removed: !fs.existsSync(canonical), canonical_path: canonical };
}

function finalizeRunResources({ dumpsClaim, statePath, fixtureCleanupVerified, rootDir = ROOT, fsMod = fs }) {
  let dumpsRemoved = false;
  let dumpsError = null;
  if (dumpsClaim) {
    try {
      const res = deleteOwnedDumpsDirectory(dumpsClaim, rootDir);
      dumpsRemoved = Boolean(res.removed);
    } catch (err) {
      dumpsError = err.message;
    }
  } else {
    dumpsRemoved = true;
  }

  let recoveryStateRetained = false;
  let recoveryStateError = null;
  if (statePath && fsMod.existsSync(statePath)) {
    if (fixtureCleanupVerified === true) {
      try {
        fsMod.unlinkSync(statePath);
      } catch (err) {
        recoveryStateError = err && err.message ? err.message : String(err);
      }
      recoveryStateRetained = Boolean(fsMod.existsSync(statePath));
      if (recoveryStateRetained && !recoveryStateError) {
        recoveryStateError = 'recovery state file remained on disk after unlink';
      }
    } else {
      recoveryStateRetained = true;
    }
  }

  return { dumpsRemoved, dumpsError, recoveryStateRetained, recoveryStateError };
}

function sanitizeDiagnostic(message, secretValues = {}) {
  const redacted = redactSentinels(String(message || ''), secretValues);
  return redacted.replace(/\r?\n+/g, ' ').slice(0, 400);
}

function buildCleanupSummary({
  existingCleanup = {},
  fixtureReceipt = {},
  resourceResult,
  browserCleanupOk = true,
  browserUserDataDir = null,
  secretValues = {},
  fsMod = fs,
}) {
  const chromeProfileDirRemoved = browserCleanupOk && (!browserUserDataDir || !fsMod.existsSync(browserUserDataDir));
  const cleanup = {
    ...existingCleanup,
    ...fixtureReceipt,
    dump_dir_outside_repo: true,
    raw_snapshots_remaining: resourceResult.dumpsRemoved ? 0 : null,
    dumps_dir_removed: resourceResult.dumpsRemoved === true,
    recovery_state_retained: resourceResult.recoveryStateRetained === true,
    chrome_profile_dir_removed: chromeProfileDirRemoved,
  };
  if (resourceResult.dumpsError) {
    cleanup.dumps_cleanup_error = sanitizeDiagnostic(resourceResult.dumpsError, secretValues);
  }
  if (resourceResult.recoveryStateError) {
    cleanup.recovery_state_error = sanitizeDiagnostic(resourceResult.recoveryStateError, secretValues);
  }
  cleanup.ok = (
    cleanup.dump_dir_outside_repo === true
    && cleanup.raw_snapshots_remaining === 0
    && cleanup.dumps_dir_removed === true
    && cleanup.chrome_profile_dir_removed === true
    && cleanup.disposable_instructions_cleanup_verified === true
    && cleanup.zero_mutation_verified === true
    && cleanup.baseline_fingerprint_equal === true
    && cleanup.recovery_state_retained === false
    && !cleanup.recovery_state_error
  );
  return cleanup;
}

function isNestedUnderEvidence(targetPath, rootDir = ROOT) {
  let curr = path.resolve(targetPath);
  let parent = path.dirname(curr);
  const resolvedRoot = path.resolve(rootDir);
  while (parent && parent !== curr && parent !== resolvedRoot) {
    if (fs.existsSync(path.join(parent, 'hashes.sha256')) || fs.existsSync(path.join(parent, 'summary.json'))) {
      return true;
    }
    curr = parent;
    parent = path.dirname(curr);
  }
  return false;
}

function claimOutputDirectory(outDir, rootDir = ROOT) {
  const resolved = path.resolve(outDir);
  if (isNestedUnderEvidence(resolved, rootDir)) {
    throw new Error(`refusing to nest output under existing evidence bundle: ${resolved}`);
  }
  if (fs.existsSync(resolved)) {
    throw new Error(`refusing to overwrite existing output directory: ${resolved}`);
  }
  const parent = path.dirname(resolved);
  if (!fs.existsSync(parent)) {
    fs.mkdirSync(parent, { recursive: true });
  }
  fs.mkdirSync(resolved);
  return resolved;
}

function validateConfig(cfg) {
  if (!cfg || typeof cfg !== 'object' || Array.isArray(cfg)) {
    throw new Error('config must be a JSON object');
  }
  const dbContainer = cfg.db_container || 'bh07-android-db';
  if (dbContainer !== 'bh07-android-db') {
    throw new Error(`db_container must be strictly "bh07-android-db", got ${JSON.stringify(dbContainer)}`);
  }

  const supabaseUrlRaw = String(cfg.supabase_url || '').trim();
  let parsedSupa;
  try {
    parsedSupa = new URL(supabaseUrlRaw);
  } catch (_) {
    throw new Error(`invalid supabase_url: ${supabaseUrlRaw}`);
  }
  const host = parsedSupa.hostname.replace(/^\[|\]$/g, '').toLowerCase();
  if (!['http:', 'https:'].includes(parsedSupa.protocol) || !['127.0.0.1', 'localhost', '::1'].includes(host)) {
    throw new Error(`supabase_url must be strictly loopback, got ${supabaseUrlRaw}`);
  }
  if (parsedSupa.port !== '54321') {
    throw new Error(`supabase_url port must be strictly 54321, got ${parsedSupa.port || 'default'}`);
  }

  const webUrlRaw = String(cfg.web_url || DEFAULT_WEB_URL).trim();
  const parsedWeb = new URL(webUrlRaw);
  const webHost = parsedWeb.hostname.replace(/^\[|\]$/g, '').toLowerCase();
  if (!['http:', 'https:'].includes(parsedWeb.protocol) || !['127.0.0.1', 'localhost', '::1'].includes(webHost)) {
    throw new Error(`web_url must be loopback, got ${webUrlRaw}`);
  }

  let maxBytes = MAX_PARSE_BYTES;
  if (cfg.max_snapshot_bytes !== undefined) {
    if (!Number.isSafeInteger(cfg.max_snapshot_bytes) || cfg.max_snapshot_bytes <= 0 || cfg.max_snapshot_bytes > MAX_PARSE_BYTES) {
      throw new Error(`max_snapshot_bytes must be a positive safe integer <= ${MAX_PARSE_BYTES}`);
    }
    maxBytes = cfg.max_snapshot_bytes;
  }

  const dumpsDir = cfg.dumps_dir
    ? path.resolve(cfg.dumps_dir)
    : path.join(os.tmpdir(), `bh07_instr_heap_dumps_${process.pid}_${crypto.randomBytes(6).toString('hex')}`);
  assertOutsideRepo(dumpsDir, 'dumps_dir');
  if (cfg.dumps_dir && (fs.existsSync(dumpsDir) || lstatSafe(dumpsDir))) {
    throw new Error(`dumps_dir target must not already exist: ${dumpsDir}`);
  }

  const statePath = cfg.state_path
    ? path.resolve(cfg.state_path)
    : path.join(os.tmpdir(), `bh07_instr_state_${process.pid}_${crypto.randomBytes(6).toString('hex')}.json`);
  assertOutsideRepo(statePath, 'state_path');
  if (isInsideDir(statePath, dumpsDir)) {
    throw new Error(`state_path must be strictly outside dumps_dir: ${statePath}`);
  }

  if (cfg.reuse_existing_server === true) {
    if (!cfg.provenance && !cfg.provenance_path) {
      throw new Error('reuse_existing_server requires explicit provenance or provenance_path');
    }
  }

  return {
    ...cfg,
    db_container: dbContainer,
    supabase_url: parsedSupa.origin,
    web_url: parsedWeb.origin,
    dumps_dir: dumpsDir,
    state_path: statePath,
    max_snapshot_bytes: maxBytes,
  };
}

function privateRuns(text, value) {
  const haystack = String(text);
  const v = String(value || '');
  const min = Math.min(v.length, MIN_PREFIX_LEAK);
  if (!v || min === 0) return [];
  const runs = [];
  for (let j = 0; j + min <= v.length; j += 1) {
    const needle = v.slice(j, j + min);
    for (let at = haystack.indexOf(needle); at >= 0; at = haystack.indexOf(needle, at + 1)) {
      if (at > 0 && j > 0 && haystack[at - 1] === v[j - 1]) continue;
      let end = at + min;
      let right = j + min;
      while (end < haystack.length && right < v.length && haystack[end] === v[right]) {
        end += 1;
        right += 1;
      }
      runs.push({ start: at, end });
    }
  }
  return runs;
}

function findSentinelLeaks(texts, values) {
  const leaks = [];
  for (const [name, value] of Object.entries(values || {})) {
    if (!value) continue;
    if (texts.some((t) => privateRuns(t, value).length > 0)) leaks.push(name);
  }
  return leaks;
}

function redactSentinels(text, values) {
  const haystack = String(text);
  const runs = Object.values(values || {}).flatMap((v) => privateRuns(haystack, v))
    .sort((a, b) => a.start - b.start || b.end - a.end);
  if (!runs.length) return haystack;
  const merged = [{ ...runs[0] }];
  for (const run of runs.slice(1)) {
    const last = merged[merged.length - 1];
    if (run.start <= last.end) last.end = Math.max(last.end, run.end);
    else merged.push({ ...run });
  }
  let out = '';
  let cursor = 0;
  for (const run of merged) {
    out += haystack.slice(cursor, run.start) + '<redacted>';
    cursor = run.end;
  }
  return out + haystack.slice(cursor);
}

function redactValue(node, values) {
  if (typeof node === 'string') return redactSentinels(node, values);
  if (Array.isArray(node)) return node.map((item) => redactValue(item, values));
  if (node && typeof node === 'object') {
    return Object.fromEntries(Object.entries(node).map(([k, v]) => [k, redactValue(v, values)]));
  }
  return node;
}

function collectStrings(node, out = []) {
  if (typeof node === 'string') out.push(node);
  else if (Array.isArray(node)) for (const item of node) collectStrings(item, out);
  else if (node && typeof node === 'object') for (const v of Object.values(node)) collectStrings(v, out);
  return out;
}

function assertNoCanaryInEvaluate(expressionOrInput, canaries = {}) {
  const text = String(expressionOrInput || '');
  const leaks = findSentinelLeaks([text], canaries);
  if (leaks.length > 0) {
    throw new Error(`refusing to inject canary (${leaks.join(', ')}) via evaluate or input`);
  }
}

async function verifyServedBuild({ webUrl, buildDir = BUILD_DIR, provenance, fetchImpl = fetch }) {
  if (!provenance || typeof provenance !== 'object') {
    throw new Error('explicit build provenance object is required');
  }
  if (provenance.mode !== 'profile') {
    throw new Error(`provenance mode must be "profile", got ${JSON.stringify(provenance.mode)}`);
  }
  if (!provenance.artifacts || typeof provenance.artifacts !== 'object') {
    throw new Error('provenance.artifacts map is required');
  }

  const localArtifacts = hashArtifacts(buildDir);
  const localKeys = Object.keys(localArtifacts).sort();
  const provKeys = Object.keys(provenance.artifacts).sort();
  if (JSON.stringify(localKeys) !== JSON.stringify(provKeys)) {
    throw new Error('local build/web artifact list does not match provenance.artifacts');
  }
  for (const name of localKeys) {
    if (localArtifacts[name] !== provenance.artifacts[name]) {
      throw new Error(`local artifact hash mismatch for ${name}`);
    }
  }

  for (const name of localKeys) {
    const res = await fetchImpl(`${webUrl.replace(/\/$/, '')}/${name}`);
    if (!res.ok) {
      throw new Error(`served artifact ${name} returned HTTP ${res.status}`);
    }
    const buf = Buffer.from(await res.arrayBuffer());
    const servedHash = crypto.createHash('sha256').update(buf).digest('hex');
    if (servedHash !== localArtifacts[name]) {
      throw new Error(`served artifact hash mismatch for ${name}`);
    }
  }

  return {
    mode: 'profile',
    reused: true,
    explicit_provenance_verified: true,
    started_at: provenance.started_at || new Date().toISOString(),
    tested_source_sha: provenance.tested_source_sha || null,
    artifacts_root: 'build/web',
    artifacts: localArtifacts,
    served_match: true,
  };
}

async function checked(cdp, method, params = {}, timeoutMs = 60000) {
  let timer = null;
  try {
    const result = await Promise.race([
      cdp.send(method, params),
      new Promise((_, reject) => {
        timer = setTimeout(() => reject(new Error(`${method}: CDP timeout after ${timeoutMs}ms`)), timeoutMs);
      }),
    ]);
    if (result && result.error) throw new Error(`${method}: ${result.error.message}`);
    return result ? result.result : undefined;
  } finally {
    if (timer) clearTimeout(timer);
  }
}

async function streamSnapshotToFile({
  cdp,
  outFile,
  maxBytes = MAX_PARSE_BYTES,
  rootDir = ROOT,
  fsMod = fs,
  timeoutMs = 120000,
}) {
  if (!Number.isSafeInteger(maxBytes) || maxBytes <= 0 || maxBytes > MAX_PARSE_BYTES) {
    throw new Error(`max_snapshot_bytes must be a positive safe integer <= ${MAX_PARSE_BYTES}`);
  }
  assertOutsideRepo(outFile, 'snapshot output path', rootDir);
  if (fsMod.existsSync(outFile) || lstatSafe(outFile)) {
    throw new Error(`refusing existing or symlinked snapshot path: ${outFile}`);
  }
  const dir = path.dirname(outFile);
  if (!fsMod.existsSync(dir)) {
    fsMod.mkdirSync(dir, { recursive: true, mode: 0o700 });
  }
  assertNoSymlinkChain(dir);

  const flags = fs.constants.O_CREAT | fs.constants.O_EXCL | fs.constants.O_WRONLY | (fs.constants.O_NOFOLLOW || 0);
  let fd = fsMod.openSync(outFile, flags, 0o600);
  const originalOnMessage = cdp.ws.onmessage;
  let bytesWritten = 0;
  let abortedError = null;
  let commandCompleted = false;
  let progressFinished = false;
  let rejectAbort = null;

  const abortPromise = new Promise((_, reject) => {
    rejectAbort = reject;
  });

  const closeAndUnlink = () => {
    if (fd !== null) {
      try { fsMod.closeSync(fd); } catch (_) {}
      fd = null;
    }
    try {
      if (fsMod.existsSync(outFile)) fsMod.unlinkSync(outFile);
    } catch (_) {}
  };

  const abortWithCleanup = (err) => {
    if (abortedError) return;
    abortedError = err;
    closeAndUnlink();
    if (rejectAbort) rejectAbort(err);
  };

  cdp.ws.onmessage = (event) => {
    if (typeof originalOnMessage === 'function') originalOnMessage(event);
    if (abortedError || commandCompleted || fd === null) return;
    let msg;
    try {
      msg = JSON.parse(event.data);
    } catch (_) {
      return;
    }
    if (msg.method === 'HeapProfiler.addHeapSnapshotChunk') {
      const chunk = String((msg.params && msg.params.chunk) || '');
      const chunkBytes = Buffer.byteLength(chunk, 'utf8');
      bytesWritten += chunkBytes;
      if (bytesWritten > maxBytes) {
        abortWithCleanup(new Error(`snapshot_cap_exceeded: ${bytesWritten} > ${maxBytes} bytes`));
        return;
      }
      try {
        fsMod.writeSync(fd, chunk, null, 'utf8');
      } catch (writeErr) {
        abortWithCleanup(new Error(`snapshot_write_error: ${writeErr.message}`));
      }
    } else if (msg.method === 'HeapProfiler.reportHeapSnapshotProgress' && msg.params && msg.params.finished) {
      // IH2: finished notification can arrive before trailing chunks; keep reading until command completes.
      progressFinished = true;
    }
  };

  try {
    await checked(cdp, 'HeapProfiler.enable', {}, timeoutMs);
    await checked(cdp, 'HeapProfiler.collectGarbage', {}, timeoutMs);
    const cmdPromise = checked(cdp, 'HeapProfiler.takeHeapSnapshot', { reportProgress: true }, timeoutMs);
    cmdPromise.catch(() => {});
    await Promise.race([cmdPromise, abortPromise]);
    if (abortedError) throw abortedError;
    commandCompleted = true;
    if (fd !== null) {
      fsMod.closeSync(fd);
      fd = null;
    }
    return { file: outFile, bytes: bytesWritten, progressFinished };
  } catch (err) {
    closeAndUnlink();
    throw err;
  } finally {
    cdp.ws.onmessage = originalOnMessage;
  }
}

function checkOwnerPrecondition(scanResult, requiredSentinels = REQUIRED_CANARIES) {
  const missing = [];
  const unreachable = [];
  if (!scanResult || scanResult.ok !== true) {
    return { ok: false, missing: [...requiredSentinels], unreachable: [...requiredSentinels] };
  }
  const sent = scanResult.sentinels || {};
  const paths = scanResult.paths || {};
  for (const name of requiredSentinels) {
    if (!sent[name] || sent[name].present !== true) missing.push(name);
    if (!paths[name] || paths[name].reachable !== true) unreachable.push(name);
  }
  return { ok: missing.length === 0 && unreachable.length === 0, missing, unreachable };
}

function escapeRegExp(str) {
  return String(str).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function sha256Hex(val) {
  return crypto.createHash('sha256').update(val).digest('hex');
}

function canonicalJson(obj) {
  if (Array.isArray(obj)) {
    return `[${obj.map((v) => canonicalJson(v)).join(',')}]`;
  }
  if (obj && typeof obj === 'object') {
    const keys = Object.keys(obj).sort();
    return `{${keys.map((k) => `${JSON.stringify(k)}:${canonicalJson(obj[k])}`).join(',')}}`;
  }
  return JSON.stringify(obj);
}

function findClosingBrace(text, openIdx, maxLen = MAX_CONSTRUCTOR_SNIPPET_BYTES) {
  let depth = 0;
  const limit = Math.min(text.length, openIdx + maxLen + 1);
  let i = openIdx;
  while (i < limit) {
    const ch = text[i];
    if (ch === '{') {
      depth += 1;
    } else if (ch === '}') {
      depth -= 1;
      if (depth === 0) return i;
    } else if (ch === "'" || ch === '"' || ch === '`') {
      const quote = ch;
      i += 1;
      while (i < limit) {
        if (text[i] === '\\') {
          i += 2;
          continue;
        }
        if (text[i] === quote) break;
        i += 1;
      }
    } else if (ch === '/' && i + 1 < limit) {
      if (text[i + 1] === '/') {
        i += 2;
        while (i < limit && text[i] !== '\n') i += 1;
      } else if (text[i + 1] === '*') {
        i += 2;
        while (i + 1 < limit && !(text[i] === '*' && text[i + 1] === '/')) i += 1;
        i += 1;
      }
    }
    i += 1;
  }
  return -1;
}

function executableSource(jsText) {
  // Conservative lexical masking, preserving offsets for the original snippets.
  // Templates/regex tokens are opaque; uncertain slash syntax can only remove proof.
  const tokens = /\/\/[^\r\n]*|\/\*[\s\S]*?(?:\*\/|$)|"(?:\\[\s\S]|[^"\\])*(?:"|$)|'(?:\\[\s\S]|[^'\\])*(?:'|$)|`(?:\\[\s\S]|[^`\\])*(?:`|$)|\/(?:\\[^\r\n]|\[(?:\\[^\r\n]|[^\]\\\r\n])*\]|[^/\\[\r\n])+\/[a-z]*/g;
  const strings = new Set();
  const code = jsText.replace(tokens, (token) => {
    if ((token[0] === '"' || token[0] === "'") && token.at(-1) === token[0]) {
      strings.add(token.slice(1, -1));
    }
    return token.replace(/[^\r\n]/g, ' ');
  });
  return { code, strings };
}

function extractJsConstructor(jsText, className, code = executableSource(jsText).code) {
  const esc = escapeRegExp(className);
  const re = new RegExp(`(?:^|[,{\\n\\r]\\s*)(${esc}\\s*:\\s*function(?:\\s+${esc})?\\s*\\(([^)]*)\\)\\s*\\{)`, 'g');
  const matches = [];
  let m;
  while ((m = re.exec(code)) !== null) {
    const fullHeader = m[1];
    const headerStart = m.index + m[0].indexOf(fullHeader);
    const openBraceIdx = headerStart + fullHeader.length - 1;
    const closeBraceIdx = findClosingBrace(code, openBraceIdx);
    if (closeBraceIdx < 0) continue;
    const snippet = jsText.slice(headerStart, closeBraceIdx + 1);
    const body = code.slice(openBraceIdx + 1, closeBraceIdx);
    const params = String(m[2] || '')
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean);
    matches.push({
      name: className,
      params,
      body,
      snippet,
      start: headerStart,
      end: closeBraceIdx + 1,
      sha256: sha256Hex(Buffer.from(snippet, 'utf8')),
    });
    if (matches.length > 1) {
      return { ok: false, error: `ambiguous ${className} constructor definition` };
    }
  }
  if (matches.length !== 1) {
    return { ok: false, error: `missing ${className} constructor definition` };
  }
  return { ok: true, ...matches[0] };
}

function parseConstructorAssignments(body) {
  const receivers = new Set(['this']);
  const aliasRe = /\b(?:var|let|const)\s+([A-Za-z_$][A-Za-z0-9_$]*)\s*=\s*this\b/g;
  let am;
  while ((am = aliasRe.exec(body)) !== null) {
    receivers.add(am[1]);
  }
  const recvPat = [...receivers].map(escapeRegExp).join('|');
  const chainRe = new RegExp(`((?:(?:${recvPat})\\.[A-Za-z_$][A-Za-z0-9_$]*\\s*=\\s*)+)([^;\\n}]+)`, 'g');
  const propRe = new RegExp(`(?:${recvPat})\\.([A-Za-z_$][A-Za-z0-9_$]*)`, 'g');
  const assignments = [];
  let cm;
  while ((cm = chainRe.exec(body)) !== null) {
    const rhs = cm[2].trim();
    const lhsGroup = cm[1];
    let pm;
    propRe.lastIndex = 0;
    while ((pm = propRe.exec(lhsGroup)) !== null) {
      assignments.push({ prop: pm[1], rhs });
    }
  }
  return { receivers: [...receivers], assignments };
}

function hasSecretInSnippets(snippets, secretValues = {}) {
  if (findSentinelLeaks(snippets, secretValues).length > 0) return true;
  return snippets.some((s) => SOURCE_SECRET_PATTERNS.some((pat) => pat.test(s)));
}

function extractCompactMatches(text, regex, maxItems = 3) {
  const out = [];
  const flags = regex.flags.includes('g') ? regex.flags : `${regex.flags}g`;
  const r = new RegExp(regex.source, flags);
  let m;
  while ((m = r.exec(text)) !== null) {
    const start = Math.max(0, text.lastIndexOf('\n', m.index) + 1);
    let end = text.indexOf('\n', m.index + m[0].length);
    if (end < 0) end = text.length;
    const line = text.slice(start, end).trim();
    if (line.length <= 400 && !out.includes(line)) {
      out.push(line);
      if (out.length >= maxItems) break;
    }
  }
  return out;
}

function extractAndValidateSourceBinding({ buildDir, expectedMainJsSha, secretValues = {} }) {
  if (!buildDir) {
    return { ok: false, main_dart_js_sha256: expectedMainJsSha || null, error: 'missing_build_dir' };
  }
  const mainJsPath = path.join(buildDir, 'main.dart.js');
  const st = lstatSafe(mainJsPath);
  if (!st || st.isSymbolicLink() || !st.isFile()) {
    return { ok: false, main_dart_js_sha256: expectedMainJsSha || null, error: 'main_dart_js_missing_or_symlink' };
  }
  const rawBuf = fs.readFileSync(mainJsPath);
  const actualSha = sha256Hex(rawBuf);
  if (!HEX64_RE.test(String(expectedMainJsSha || '')) || actualSha !== expectedMainJsSha) {
    return {
      ok: false,
      main_dart_js_sha256: actualSha,
      expected_main_dart_js_sha256: expectedMainJsSha || null,
      error: 'main_dart_js_sha256_mismatch',
    };
  }
  const jsText = rawBuf.toString('utf8');
  const { code, strings } = executableSource(jsText);

  const fpCtor = extractJsConstructor(jsText, 'FinanceProvider', code);
  if (!fpCtor.ok) {
    return { ok: false, main_dart_js_sha256: actualSha, error: fpCtor.error };
  }
  const piCtor = extractJsConstructor(jsText, 'PaymentInstructions', code);
  if (!piCtor.ok) {
    return { ok: false, main_dart_js_sha256: actualSha, error: piCtor.error };
  }

  const fpParsed = parseConstructorAssignments(fpCtor.body);
  const repoFields = [...new Set(fpParsed.assignments
    .map((a) => a.prop)
    .filter((p) => /^(?:_[A-Za-z0-9_]+\$)?_repository$/.test(p)))];
  const hasAuth = fpParsed.assignments.some((a) => a.prop === 'auth');
  const hasPlayerIdNull = fpParsed.assignments.some(
    (a) => /^(?:_[A-Za-z0-9_]+\$)?_instructionsPlayerId$/.test(a.prop) && a.rhs === 'null',
  );
  const hasSessionIdNull = fpParsed.assignments.some(
    (a) => /^(?:_[A-Za-z0-9_]+\$)?_instructionsSessionId$/.test(a.prop) && a.rhs === 'null',
  );
  const instrCandidates = [...new Set(fpParsed.assignments
    .filter((a) => /^(?:_[A-Za-z0-9_]+\$)?_instructions$/.test(a.prop) && a.rhs === 'null')
    .map((a) => a.prop))];
  if (repoFields.length !== 1 || !hasAuth || !hasPlayerIdNull || !hasSessionIdNull || instrCandidates.length !== 1) {
    return { ok: false, main_dart_js_sha256: actualSha, error: 'finance_provider_constructor_contract_failed' };
  }
  const instructionsField = instrCandidates[0];
  const repositoryField = repoFields[0];

  const jsWithoutFp = code.slice(0, fpCtor.start) + code.slice(fpCtor.end);
  const escInstr = escapeRegExp(instructionsField);
  const fpNonNullAssignRe = new RegExp(`[A-Za-z_$][A-Za-z0-9_$]*\\.${escInstr}\\s*=\\s*(?!null\\b|undefined\\b)[^;\\n}]+`);
  const fpNullResetRe = new RegExp(`[A-Za-z_$][A-Za-z0-9_$]*\\.${escInstr}\\s*=\\s*null\\b`);
  const fpReadRe = new RegExp(`[A-Za-z_$][A-Za-z0-9_$]*\\.${escInstr}(?![A-Za-z0-9_$])\\s*(?:===|!==|[^=])`);
  if (
    !fpNonNullAssignRe.test(jsWithoutFp)
    || !fpNullResetRe.test(jsWithoutFp)
    || !fpReadRe.test(jsWithoutFp)
    || !code.includes('fetchPaymentInstructions')
    || !strings.has('get_payment_instructions')
  ) {
    return { ok: false, main_dart_js_sha256: actualSha, error: 'finance_provider_field_use_unverified' };
  }

  const piParsed = parseConstructorAssignments(piCtor.body);
  const piParamSet = new Set(piCtor.params);
  const rsCandidates = [...new Set(piParsed.assignments
    .filter((a) => /^(?:_[A-Za-z0-9_]+\$)?receiverSnapshot$/.test(a.prop) && piParamSet.has(a.rhs))
    .map((a) => a.prop))];
  if (rsCandidates.length !== 1) {
    return { ok: false, main_dart_js_sha256: actualSha, error: 'payment_instructions_constructor_contract_failed' };
  }
  const receiverSnapshotField = rsCandidates[0];

  const jsWithoutPi = code.slice(0, piCtor.start) + code.slice(piCtor.end);
  const escRs = escapeRegExp(receiverSnapshotField);
  const piReadRe = new RegExp(`[A-Za-z_$][A-Za-z0-9_$]*\\.${escRs}(?![A-Za-z0-9_$])\\s*(?:===|!==|[^=])`);
  if (!piReadRe.test(jsWithoutPi) || !strings.has('receiver_snapshot')) {
    return { ok: false, main_dart_js_sha256: actualSha, error: 'payment_instructions_field_use_unverified' };
  }

  const provAssignRe = /[A-Za-z_$][A-Za-z0-9_$]*\._provider\$_value\s*=\s*[^;,\n}]+/;
  const provReadRe = /[A-Za-z_$][A-Za-z0-9_$]*\._provider\$_value(?![A-Za-z0-9_$])\s*(?:===|!==|[^=])/;
  if (!provAssignRe.test(code) || !provReadRe.test(code)) {
    return { ok: false, main_dart_js_sha256: actualSha, error: 'provider_holder_field_use_unverified' };
  }

  const fpFieldUseSnippets = [
    ...extractCompactMatches(jsWithoutFp, fpNonNullAssignRe, 1),
    ...extractCompactMatches(jsWithoutFp, fpNullResetRe, 1),
    ...extractCompactMatches(jsWithoutFp, fpReadRe, 1),
  ];
  const piFieldUseSnippets = extractCompactMatches(jsWithoutPi, piReadRe, 2);
  const provHolderSnippets = [
    ...extractCompactMatches(code, provAssignRe, 1),
    ...extractCompactMatches(code, provReadRe, 1),
  ];

  const allSnippets = [
    fpCtor.snippet,
    piCtor.snippet,
    ...fpFieldUseSnippets,
    ...piFieldUseSnippets,
    ...provHolderSnippets,
  ];
  if (hasSecretInSnippets(allSnippets, secretValues)) {
    return { ok: false, main_dart_js_sha256: actualSha, error: 'sensitive_pattern_in_source_binding_snippets' };
  }

  const core = {
    finance_provider: {
      constructor_name: 'FinanceProvider',
      constructor_sha256: fpCtor.sha256,
      field_use_verified: true,
      instructions_field: instructionsField,
      repository_field: repositoryField,
    },
    main_dart_js_sha256: actualSha,
    payment_instructions: {
      constructor_name: 'PaymentInstructions',
      constructor_sha256: piCtor.sha256,
      field_use_verified: true,
      receiver_snapshot_field: receiverSnapshotField,
    },
    provider_holder_edge: PROVIDER_HOLDER_EDGE,
  };
  const bindingSha = sha256Hex(Buffer.from(canonicalJson(core), 'utf8'));
  const sanitized = { ok: true, ...core, binding_sha256: bindingSha };
  const companion = {
    ok: true,
    version: '1.0',
    main_dart_js_sha256: actualSha,
    provider_holder_edge: PROVIDER_HOLDER_EDGE,
    provider_holder_snippets: provHolderSnippets,
    finance_provider: {
      ...core.finance_provider,
      constructor_snippet: fpCtor.snippet,
      field_use_snippets: fpFieldUseSnippets,
    },
    payment_instructions: {
      ...core.payment_instructions,
      constructor_snippet: piCtor.snippet,
      field_use_snippets: piFieldUseSnippets,
    },
    binding_sha256: bindingSha,
  };
  if (Buffer.byteLength(JSON.stringify(companion, null, 2) + '\n', 'utf8') > MAX_SOURCE_BINDING_BYTES) {
    return { ok: false, main_dart_js_sha256: actualSha, error: 'source_binding_artifact_exceeds_size_cap' };
  }
  return { ok: true, sanitized, companion };
}

function parseFrame(frame) {
  if (typeof frame !== 'string' || frame === '...') return null;
  const m = FRAME_RE.exec(frame);
  if (!m) return null;
  return { kind: m[1], label: m[2] || '', child: m[3] };
}

function hasOrderedDtoRetainerChain(frames, options = {}) {
  const { sourceBinding = null, canaryName = null, pathRecord = null } = options || {};
  if (!sourceBinding || sourceBinding.ok !== true) return false;
  const fp = sourceBinding.finance_provider;
  const pi = sourceBinding.payment_instructions;
  if (
    sourceBinding.provider_holder_edge !== PROVIDER_HOLDER_EDGE
    || !fp || fp.field_use_verified !== true || !fp.instructions_field
    || !pi || pi.field_use_verified !== true || !pi.receiver_snapshot_field
  ) {
    return false;
  }
  if (!Array.isArray(frames) || frames.length < 6 || frames[0] !== 'root' || frames.includes('...')) {
    return false;
  }
  if (pathRecord) {
    if (pathRecord.reachable !== true || pathRecord.exact !== true) return false;
    if (pathRecord.path_len !== frames.length - 1) return false;
    if (pathRecord.path_sha256_12 !== sha12(frames.join('\n'))) return false;
  }

  const parsed = frames.slice(1).map(parseFrame);
  if (parsed.some((p) => p === null)) return false;
  if (parsed.some((f) => FORBIDDEN_DTO_LABEL_WORDS.some((w) => f.label.toLowerCase().includes(w)))) {
    return false;
  }

  const expectedInstrField = fp.instructions_field;
  const expectedRsField = pi.receiver_snapshot_field;
  const allowedCanaryKeys = canaryName ? new Set([canaryName]) : new Set(REQUIRED_CANARIES);

  for (let i = 0; i <= parsed.length - 5; i += 1) {
    const holder = parsed[i];
    const step1 = parsed[i + 1];
    const step2 = parsed[i + 2];
    if (
      holder.kind === 'property'
      && holder.label === PROVIDER_HOLDER_EDGE
      && holder.child === 'object'
      && step1.kind === 'property'
      && step1.label === expectedInstrField
      && step1.child === 'object'
      && step2.kind === 'property'
      && step2.label === expectedRsField
      && step2.child === 'object'
    ) {
      const suffix = parsed.slice(i + 3);
      if (suffix.length < 2) continue;
      const mapRoot = suffix[0];
      const intermediates = suffix.slice(1, -1);
      const leaf = suffix[suffix.length - 1];
      if (mapRoot.kind !== 'property' || mapRoot.child !== 'object' || !VALID_MAP_ROOT_PROPS.has(mapRoot.label)) {
        continue;
      }
      if (leaf.kind !== 'property' || leaf.label !== 'hashMapCellValue' || !STRING_CHILD_TYPES.has(leaf.child)) {
        continue;
      }
      if (mapRoot.label === '_strings') {
        if (intermediates.length !== 1) continue;
        const keyEdge = intermediates[0];
        if (keyEdge.kind !== 'property' || keyEdge.child !== 'object' || !allowedCanaryKeys.has(keyEdge.label)) {
          continue;
        }
        return true;
      }
      if (mapRoot.label === '_first' || mapRoot.label === '_last') {
        if (intermediates.some((f) => f.kind !== 'property' || f.child !== 'object' || !VALID_MAP_LINK_PROPS.has(f.label))) {
          continue;
        }
        return true;
      }
      // _nums or _rest bucket traversal
      if (intermediates.some((f) => !['property', 'element'].includes(f.kind) || !CONTAINER_CHILD_TYPES.has(f.child))) {
        continue;
      }
      return true;
    }
  }
  return false;
}

function isValidTimeOrigin(val) {
  return typeof val === 'number' && Number.isFinite(val) && val > 0;
}

function isCycleCompleteAndPassing(cycle, expectedOrigin = null) {
  if (!cycle || !cycle.epochs || !cycle.verdict) return false;
  if (cycle.same_document !== true || !isValidTimeOrigin(cycle.time_origin)) return false;
  if (isValidTimeOrigin(expectedOrigin) && cycle.time_origin !== expectedOrigin) return false;
  for (const epName of REQUIRED_EPOCHS) {
    const ep = cycle.epochs[epName];
    if (!ep || ep.ok !== true || ep.time_origin !== cycle.time_origin) return false;
  }
  return cycle.verdict.verdict === 'PASS';
}

function computeSameDocumentAcrossCycles(cycles, expectedOrigin = null) {
  if (!Array.isArray(cycles) || cycles.length !== 2) return false;
  const refOrigin = isValidTimeOrigin(expectedOrigin) ? expectedOrigin : (cycles[0] && cycles[0].time_origin);
  if (!isValidTimeOrigin(refOrigin)) return false;
  return cycles.every((c) => {
    if (!c || c.same_document !== true || !isValidTimeOrigin(c.time_origin) || c.time_origin !== refOrigin) {
      return false;
    }
    return REQUIRED_EPOCHS.every((epName) => {
      const ep = c.epochs && c.epochs[epName];
      return Boolean(ep && ep.ok === true && ep.time_origin === refOrigin);
    });
  });
}

function assessPathAttribution(cycles, options = {}) {
  const { sourceBinding = null, expectedMainJsSha = null } = options || {};
  const ownerRecords = [];
  let allMeasured = Array.isArray(cycles) && cycles.length === 2;

  for (const cycle of cycles || []) {
    const ownerEp = cycle && cycle.epochs && cycle.epochs.owner_active;
    const paths = ownerEp && ownerEp.paths ? ownerEp.paths : {};
    for (const name of REQUIRED_CANARIES) {
      const rec = paths[name];
      if (!rec || rec.reachable !== true || !Array.isArray(rec.frames) || rec.frames.length < 2 || !rec.path_sha256_12) {
        allMeasured = false;
      } else {
        ownerRecords.push({ name, rec });
      }
    }
  }

  const bindingValid = Boolean(
    sourceBinding
    && sourceBinding.ok === true
    && typeof sourceBinding.main_dart_js_sha256 === 'string'
    && HEX64_RE.test(sourceBinding.main_dart_js_sha256)
    && (!expectedMainJsSha || sourceBinding.main_dart_js_sha256 === expectedMainJsSha)
  );
  const dtoProven = allMeasured
    && bindingValid
    && ownerRecords.length === 4
    && ownerRecords.every(({ name, rec }) => hasOrderedDtoRetainerChain(rec.frames, {
      sourceBinding,
      canaryName: name,
      pathRecord: rec,
    }));

  const normalizedBinding = bindingValid
    ? sourceBinding
    : {
      ok: false,
      main_dart_js_sha256: expectedMainJsSha || (sourceBinding && sourceBinding.main_dart_js_sha256) || null,
      error: (sourceBinding && sourceBinding.error) || 'source binding unavailable or mismatched',
    };

  return {
    root_reachability_measured: allMeasured,
    dto_attribution_proven: dtoProven,
    attribution_status: dtoProven ? 'proven_artifact_bound' : (bindingValid ? 'unproven_ordered_chain_mismatch' : 'unproven_missing_or_invalid_source_binding'),
    claim_scope: dtoProven ? 'payment_instructions_receiver_snapshot_only' : 'narrow_rpc_payload_retention_only',
    scoped_verdict: dtoProven ? 'PASS_DTO_ATTRIBUTED' : (allMeasured ? 'PASS_NARROW_RPC_PAYLOAD_ONLY' : 'FAIL'),
    payment_instructions_coverage_gate: dtoProven ? 'PASS' : 'UNKNOWN/NOT_RUN',
    source_binding: normalizedBinding,
    proven_frames: dtoProven ? ownerRecords[0].rec.frames : [],
  };
}

function renderReport(summary) {
  const attr = summary.attribution_assessment || {};
  const binding = attr.source_binding || {};
  const bindingLabel = binding.ok
    ? `verified (main.dart.js ${binding.main_dart_js_sha256.slice(0, 12)}, FinanceProvider.${binding.finance_provider && binding.finance_provider.instructions_field}, PaymentInstructions.${binding.payment_instructions && binding.payment_instructions.receiver_snapshot_field})`
    : `unverified (${binding.error || 'missing'})`;
  const lines = [
    '# V2b — PaymentInstructions synthetic receiverSnapshot heap retention',
    '',
    `- Gate: ${summary.gate}`,
    `- Status: **${summary.status}** (verdict ${summary.verdict || 'null'})`,
    `- Scoped verdict: **${attr.scoped_verdict || 'FAIL'}**`,
    `- PaymentInstructions coverage gate: ${attr.payment_instructions_coverage_gate || 'UNKNOWN/NOT_RUN'}`,
    `- Attribution: root_reachability_measured=${Boolean(attr.root_reachability_measured)}; dto_attribution_proven=${Boolean(attr.dto_attribution_proven)} (${attr.attribution_status || 'unknown'})`,
    `- Source binding: ${bindingLabel}`,
    `- Claim scope: ${attr.claim_scope || 'narrow_rpc_payload_retention_only'} (synthetic receiverSnapshot keys only; no whole-model claim)`,
    `- Tested source: \`${summary.tested_source_sha}\` (git dirty: ${summary.git_dirty})`,
    `- Same document across cycles: ${Boolean(summary.same_document_across_cycles)}`,
    '',
    '## Sentinels (values never published)',
    '',
    '| sentinel | scope | rendered | distinctive | length | sha256[:12] |',
    '| --- | --- | --- | --- | --- | --- |',
    ...Object.entries(summary.sentinels || {}).map(([name, s]) =>
      `| ${name} | ${s.scope} | ${s.rendered} | ${s.distinctive} | ${s.length} | ${s.sha256_12} |`),
    '',
    '## Cycles (8 epochs total across 2 cycles)',
    '',
    '| cycle | actor | same document | timeOrigin | epoch | bytes | sha256[:12] | present |',
    '| --- | --- | --- | --- | --- | --- | --- | --- |',
  ];

  for (const cycle of summary.cycles || []) {
    for (const [epName, scan] of Object.entries(cycle.epochs || {})) {
      const present = Object.entries(scan.sentinels || {})
        .filter(([, v]) => v.present).map(([k]) => k).join(', ') || 'none';
      lines.push(`| ${cycle.cycle} | ${cycle.actor} | ${cycle.same_document} | ${cycle.time_origin} | ${epName} | ${scan.size_bytes ?? 'n/a'} | ${scan.sha256_12 || 'n/a'} | ${present} |`);
    }
  }

  lines.push('', '## Findings', '');
  const findings = summary.findings || [];
  lines.push(...(findings.length ? findings.map((f) => `- ${f}`) : ['- none']));
  lines.push('', '## Cleanup', '', `- ${JSON.stringify(summary.cleanup || {})}`, '');
  lines.push('## Limitations', '',
    '- Covers ONLY synthetic non-rendered JSON keys (`canary_instr_a`, `canary_instr_b`) carried via `get_payment_instructions` into `receiverSnapshot` (no whole-model clean claim).',
    '- Rendered strings (`bank_code`, `account_number`, `account_name`, `reference`) remain unattributed.',
    '- Under dart2js compilation, V8 strong-root reachability proves Dart-level DTO attribution ONLY when served-artifact source binding (`main.dart.js` SHA + constructor/field validation) verifies an exact ordered retainer chain (`_provider$_value` -> bound instructions field -> bound `receiverSnapshot` field -> map edges).',
    '- Does not cover `AuthProvider` listener graphs, Dart VM desktop/mobile, Firefox, or Safari.', '');
  return lines.join('\n');
}

function writeEvidenceBundle(outDir, summary, logLines, secretValues, companionBindingArtifact = null) {
  const companionStrings = companionBindingArtifact ? collectStrings(companionBindingArtifact) : [];
  const leaks = findSentinelLeaks([...collectStrings(summary), ...logLines, ...companionStrings], secretValues);
  if (leaks.length > 0) {
    summary.findings = [...(summary.findings || []),
      `raw sensitive value reached publication (${leaks.join(', ')}); redacted, run failed`];
    summary.verdict = 'FAIL';
    summary.status = 'FAIL';
  }
  const cleanSummary = redactValue(summary, secretValues);
  const cleanJson = JSON.stringify(cleanSummary, null, 2) + '\n';
  const cleanLogs = logLines.map((line) => redactSentinels(line, secretValues)).join('\n') + '\n';
  const cleanReport = renderReport(cleanSummary);

  fs.writeFileSync(path.join(outDir, 'summary.json'), cleanJson, 'utf8');
  fs.writeFileSync(path.join(outDir, 'run.log'), cleanLogs, 'utf8');
  fs.writeFileSync(path.join(outDir, 'report.md'), cleanReport, 'utf8');

  const filesToHash = ['summary.json', 'run.log', 'report.md'];
  if (companionBindingArtifact && companionBindingArtifact.ok === true) {
    const cleanBinding = redactValue(companionBindingArtifact, secretValues);
    const bindingJson = JSON.stringify(cleanBinding, null, 2) + '\n';
    if (Buffer.byteLength(bindingJson, 'utf8') > MAX_SOURCE_BINDING_BYTES) {
      throw new Error('companion source_binding.json exceeded bounded artifact limit');
    }
    fs.writeFileSync(path.join(outDir, 'source_binding.json'), bindingJson, 'utf8');
    filesToHash.push('source_binding.json');
  }

  const hashFile = (file) => crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
  const manifest = filesToHash
    .map((name) => `${hashFile(path.join(outDir, name))}  ${name}`).join('\n') + '\n';
  fs.writeFileSync(path.join(outDir, 'hashes.sha256'), manifest, 'utf8');
  return cleanSummary;
}

function runCmd(cmd, args, opts = {}) {
  return execFileSync(cmd, args, { cwd: ROOT, encoding: 'utf8', maxBuffer: 64 * 1024 * 1024, ...opts });
}

function runVerdict(cmd, args) {
  try {
    return runCmd(cmd, args);
  } catch (err) {
    if (err.status === 1 && err.stdout) return err.stdout;
    throw err;
  }
}

async function startBrowserLogged(logFile, cfg) {
  const port = Number(cfg.debug_port) || 9338;
  const browserExe = cfg.browser_exe || process.env.CHROME_PATH || 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
  await assertPortFree(port);
  const userDataDir = path.join(os.tmpdir(), `bh07_instr_browser_${process.pid}`);
  assertOutsideRepo(userDataDir, 'userDataDir');
  if (fs.existsSync(userDataDir)) {
    throw new Error(`preexisting browser profile directory ${userDataDir} detected`);
  }
  fs.mkdirSync(userDataDir, { recursive: true });
  const stderrFd = fs.openSync(logFile, 'a');
  let proc = null;
  let spawnErr = null;
  try {
    proc = spawn(browserExe, [
      `--remote-debugging-port=${port}`,
      '--headless=new',
      '--no-first-run',
      '--no-default-browser-check',
      '--disable-gpu',
      '--disable-background-networking',
      '--window-size=1280,900',
      `--user-data-dir=${userDataDir}`,
      'about:blank',
    ], { detached: true, stdio: ['ignore', 'ignore', stderrFd] });
    proc.on('error', (err) => { spawnErr = err; });
  } catch (err) {
    fs.closeSync(stderrFd);
    await shutdownOwnedBrowser({ proc: null, userDataDir });
    throw err;
  }
  fs.closeSync(stderrFd);

  for (let i = 0; i < 50; i++) {
    if (spawnErr) break;
    await wait(200);
    try {
      const res = await fetch(`http://127.0.0.1:${port}/json/version`);
      if (res.ok) {
        const version = await res.json();
        const closeBrowser = async () => {
          if (!version.webSocketDebuggerUrl) return;
          const bCdp = new CdpClient(version.webSocketDebuggerUrl);
          bCdp.sessionId = undefined;
          try {
            await bCdp.connect();
            await bCdp.send('Browser.close');
          } catch (_) {
            /* best effort */
          } finally {
            try { if (bCdp.ws) bCdp.ws.close(); } catch (_) {}
          }
        };
        return { proc, version, userDataDir, closeBrowser };
      }
    } catch (_) { /* waiting for browser */ }
  }
  await shutdownOwnedBrowser({ proc, userDataDir });
  if (spawnErr) throw spawnErr;
  throw new Error(`Browser failed to start on port ${port}`);
}

async function safeEvaluate(cdp, expression, canaries) {
  assertNoCanaryInEvaluate(expression, canaries);
  return cdp.evaluate(expression);
}

async function waitForFlutterSemanticsReady(cdp, canaries, { placeholderTimeoutMs = 30000, pollMs = 250 } = {}) {
  const deadline = Date.now() + placeholderTimeoutMs;
  while (Date.now() < deadline) {
    try {
      const ready = await safeEvaluate(
        cdp,
        "Boolean(document.querySelector('flt-semantics-placeholder') || document.querySelector('flt-semantics-host'))",
        canaries,
      );
      if (ready) {
        if (typeof cdp.enableFlutterSemantics === 'function') {
          await cdp.enableFlutterSemantics();
        }
        return true;
      }
    } catch (_) {
      /* page still initializing */
    }
    await wait(pollMs);
  }
  throw new Error(`Timed out waiting for Flutter semantics placeholder after ${placeholderTimeoutMs}ms`);
}

async function waitForStartupAndGuestBaseline(cdp, canaries, {
  placeholderTimeoutMs = 30000,
  pollMs = 250,
  guestTimeoutMs = 30000,
} = {}) {
  await waitForFlutterSemanticsReady(cdp, canaries, { placeholderTimeoutMs, pollMs });
  await cdp.waitForSemantic((e) => textOf(e).includes('Bạn đang xem dưới dạng khách'), 'Guest baseline UI', guestTimeoutMs);
}

async function loginActor(cdp, email, password, canaries) {
  assertNoCanaryInEvaluate(password, canaries);
  await cdp.clickSemantic((e) => (e.role === 'button' || e.tag === 'BUTTON') && /Đăng [Nn]hập/.test(textOf(e)), 'Open login');
  for (const [label, value] of [['Email', email], ['Mật khẩu', password]]) {
    await cdp.clickSemantic((e) => e.tag === 'INPUT' && (e.aria || '').includes(label), `Focus ${label}`);
    assertNoCanaryInEvaluate(value, canaries);
    await checked(cdp, 'Input.insertText', { text: value });
  }
  await cdp.clickSemantic(button('Đăng Nhập'), 'Submit login');
  await wait(1500);
  await cdp.clickSemantic((e) => e.role === 'tab' && e.aria === 'Tài Khoản', 'Verify account tab');
  await cdp.waitForSemantic((e) => textOf(e).includes(email), `Account email ${email}`);
}

async function returnHomeTabs(cdp) {
  for (let i = 0; i < 6; i++) {
    if ((await cdp.getAllSemantics()).some((e) => e.role === 'tab' && e.aria === 'Tài Khoản')) return;
    await cdp.clickBack('Return to main tabs');
  }
  throw new Error('Main tabs not reachable through UI');
}

async function logoutActor(cdp, canaries) {
  await returnHomeTabs(cdp);
  await cdp.clickSemantic((e) => e.role === 'tab' && e.aria === 'Tài Khoản', 'Account tab');
  await cdp.clickSemantic(button('Đăng xuất'), 'Logout');
  await cdp.clickSemantic(button('Đăng Xuất'), 'Confirm logout');
  await cdp.waitForSemantic((e) => textOf(e).includes('Bạn đang xem dưới dạng khách'), 'Guest UI');
  const cleared = await safeEvaluate(
    cdp,
    "!Object.keys(localStorage).some(k => k.startsWith('sb-') && k.endsWith('-auth-token'))",
    canaries,
  );
  if (!cleared) throw new Error('Supabase auth token remained in localStorage after logout');
}

async function openOwnerInstructionsAndCancel(cdp, sessionTitle) {
  await cdp.clickSemantic((e) => e.role === 'tab' && e.aria === 'Buổi Chơi', 'Sessions tab');
  await cdp.clickSemantic((e) => textOf(e).includes('Lịch sử buổi'), 'History entry');
  await cdp.clickSemantic((e) => textOf(e).includes(sessionTitle), 'Disposable session row');
  await cdp.clickSemantic((e) => textOf(e).includes('Tài chính & thu tiền'), 'Open session finance');
  await cdp.waitForSemantic((e) => textOf(e).includes('Khoản phải thu theo người'), 'Charges section loaded');
  await cdp.clickSemantic((e) => (e.role === 'button' || e.tag === 'BUTTON') && textOf(e).includes('Thu tiền mặt'), 'Click Thu tiền mặt');
  await cdp.waitForSemantic((e) => textOf(e).includes('Số tiền (VNĐ)'), 'Cash dialog opened after get_payment_instructions');
  await cdp.clickSemantic(button('Huỷ'), 'Cancel cash dialog without payment mutation');
  await wait(500);
}

async function openCohostSummary(cdp) {
  await cdp.clickSemantic((e) => e.role === 'tab' && e.aria === 'Buổi Chơi', 'Sessions tab');
  await cdp.clickSemantic((e) => textOf(e).includes('Lịch sử buổi'), 'History entry');
  await cdp.clickSemantic((e) => textOf(e).includes(UI_SESSION_TITLE), 'Seeded UI session row');
  await cdp.clickSemantic((e) => textOf(e).includes('Tổng kết buổi'), 'Summary entry');
  await cdp.waitForSemantic((e) => textOf(e).includes('Chỉ xem số lượng'), 'Cohost count-only summary');
}

async function openMemberHistory(cdp) {
  await cdp.clickSemantic((e) => e.role === 'tab' && e.aria === 'Buổi Chơi', 'Sessions tab');
  await cdp.clickSemantic((e) => textOf(e).includes('Lịch sử buổi'), 'History entry');
  await wait(1200);
}

async function captureAndScan({ cdp, dumpsDir, label, sentinelsPath, classesPath, maxBytes }) {
  const snapFile = path.join(dumpsDir, `${label}.heapsnapshot`);
  try {
    await streamSnapshotToFile({ cdp, outFile: snapFile, maxBytes });
    const raw = runCmd(PY, [
      '-X', 'utf8', ORACLE, 'scan',
      '--snapshot', snapFile, '--sentinels', sentinelsPath, '--classes', classesPath, '--paths',
    ], { shell: false });
    return JSON.parse(raw);
  } finally {
    try { if (fs.existsSync(snapFile)) fs.unlinkSync(snapFile); } catch (_) {}
  }
}

async function runMeasurement({ cfg, cfgPath, outDir, hooks = {} }) {
  const resolvedOutDir = claimOutputDirectory(outDir);
  const dumpsClaim = claimDumpsDirectory(cfg.dumps_dir, ROOT);
  const dumpsDir = dumpsClaim.dir;
  const statePath = cfg.state_path;
  const fsMod = hooks.fsMod || fs;

  const logLines = [];
  let secretValues = {};
  const log = (msg) => {
    const line = `[${new Date().toISOString()}] ${redactSentinels(msg, secretValues)}`;
    console.log(line);
    logLines.push(line);
  };

  const gitProv = hooks.getGitProvenance
    ? hooks.getGitProvenance()
    : {
      tested_source_sha: runCmd('git', ['rev-parse', 'HEAD']).trim(),
      git_dirty: runCmd('git', ['status', '--porcelain']).trim() !== '',
    };

  const summary = {
    gate: 'V2b — PaymentInstructions synthetic receiverSnapshot heap retention',
    coverage_profile: 'payment_instructions',
    status: 'NOT RUN',
    verdict: null,
    measurement_surface: 'Flutter Web profile build + Chrome DevTools Protocol HeapProfiler (V8 heap snapshot)',
    oracle: 'synthetic receiverSnapshot UUIDs scanned in live V8 heap snapshots via heap_oracle.py',
    tested_source_sha: gitProv.tested_source_sha,
    git_dirty: gitProv.git_dirty,
    same_document_across_cycles: false,
    instructions_coverage_contract: {
      version: '1.0',
      required_owner_load: ['canary_instr_a', 'canary_instr_b'],
      scope: 'synthetic_receiver_snapshot_map_values_only',
      dto: 'PaymentInstructions',
      provider_field: 'FinanceProvider._instructions',
      actor_isolation: 'owner_only_disposable_club',
      payment_mutation_forbidden: true,
      rendered_strings_unattributed: ['bank_code', 'account_number', 'account_name', 'reference'],
    },
    environment: { os: `${process.platform} ${os.release()}`, node: process.version },
    sentinels: {},
    cycles: [],
    notes: [],
    residual_risks: [],
    findings: [],
    cleanup: {},
  };

  let browser = null;
  let cdp = null;
  let ownServer = null;
  let browserCleanupOk = true;
  let fixtureCreated = false;
  let origin0 = null;
  let currentStage = 'startup';
  let currentEpoch = null;
  let activeCycle = null;
  let sourceBindingResult = null;
  const effectiveBuildDir = cfg.build_dir || hooks.buildDir || BUILD_DIR;

  try {
    if (cfg.owner_password) secretValues.owner_password = cfg.owner_password;
    if (cfg.cohost_password) secretValues.cohost_password = cfg.cohost_password;
    if (cfg.member_password) secretValues.member_password = cfg.member_password;
    if (cfg.supabase_anon_key) secretValues.supabase_anon_key = cfg.supabase_anon_key;

    currentStage = 'build_provenance';
    if (hooks.prepareBuild) {
      summary.environment.build = await hooks.prepareBuild();
    } else if (cfg.reuse_existing_server === true) {
      const prov = cfg.provenance || JSON.parse(fs.readFileSync(cfg.provenance_path, 'utf8'));
      summary.environment.build = await verifyServedBuild({ webUrl: cfg.web_url, buildDir: effectiveBuildDir, provenance: prov });
    } else {
      const webPort = Number(new URL(cfg.web_url).port) || 8088;
      await assertPortFree(webPort);
      const before = snapshotArtifacts(effectiveBuildDir);
      const startedAt = Date.now();
      runCmd(process.platform === 'win32' ? 'flutter.bat' : 'flutter', [
        'build', 'web', '--profile',
        '--dart-define=APP_ENV=test',
        `--dart-define=SUPABASE_URL=${cfg.supabase_url}`,
        `--dart-define=SUPABASE_ANON_KEY=${cfg.supabase_anon_key}`,
      ], { shell: process.platform === 'win32' });
      assertArtifactsFresh(effectiveBuildDir, startedAt, before);
      ownServer = spawn(PY, ['-m', 'http.server', String(webPort), '--bind', '127.0.0.1', '--directory', effectiveBuildDir],
        { cwd: ROOT, stdio: 'ignore' });
      await wait(1000);
      summary.environment.build = await verifyServedBuild({
        webUrl: cfg.web_url,
        buildDir: effectiveBuildDir,
        provenance: { mode: 'profile', started_at: new Date(startedAt).toISOString(), artifacts: hashArtifacts(effectiveBuildDir) },
      });
      summary.environment.build.reused = false;
    }

    const expectedMainJsSha = summary.environment.build
      && summary.environment.build.artifacts
      ? summary.environment.build.artifacts['main.dart.js']
      : null;
    if (hooks.extractSourceBinding) {
      sourceBindingResult = await hooks.extractSourceBinding({
        buildDir: effectiveBuildDir,
        expectedMainJsSha,
        build: summary.environment.build,
      });
    } else {
      sourceBindingResult = extractAndValidateSourceBinding({
        buildDir: effectiveBuildDir,
        expectedMainJsSha,
        fsMod,
      });
    }

    currentStage = 'fixture_create';
    const fixtureMeta = hooks.createFixture
      ? hooks.createFixture({ cfgPath, statePath })
      : JSON.parse(runCmd(PY, ['-X', 'utf8', FIXTURE_CLI, 'create', '--config', cfgPath, '--state', statePath], { shell: false }));
    fixtureCreated = true;
    const privState = JSON.parse(fs.readFileSync(statePath, 'utf8'));
    const canaries = {
      canary_instr_a: privState.sentinel_1,
      canary_instr_b: privState.sentinel_2,
    };
    const probeValue = `BH07INSTRPROBE-${crypto.randomBytes(4).toString('hex')}`;
    const allSentinels = { ...canaries, probe: probeValue };
    secretValues = { ...secretValues, ...allSentinels };

    const classes = {
      canary_instr_a: { rendered: false, distinctive: true, scope: 'finance' },
      canary_instr_b: { rendered: false, distinctive: true, scope: 'finance' },
      probe: { rendered: false, distinctive: true, scope: 'control' },
    };
    summary.sentinels = Object.fromEntries(Object.entries(allSentinels).map(([k, v]) => [k, {
      available: true,
      sha256_12: sha12(v),
      length: v.length,
      kind: k === 'probe' ? 'detector sanity marker' : 'synthetic receiverSnapshot UUID (never rendered)',
      ...classes[k],
    }]));

    const sentinelsPath = path.join(dumpsDir, 'sentinels.json');
    const classesPath = path.join(dumpsDir, 'classes.json');
    fs.writeFileSync(sentinelsPath, JSON.stringify(allSentinels), { mode: 0o600 });
    fs.writeFileSync(classesPath, JSON.stringify(classes), { mode: 0o600 });

    currentStage = 'browser_start';
    if (hooks.startSession) {
      const session = await hooks.startSession({ dumpsDir, cfg });
      browser = session.browser;
      cdp = session.cdp;
    } else {
      browser = await startBrowserLogged(path.join(dumpsDir, 'browser.log'), cfg);
      cdp = new CdpClient(browser.version.webSocketDebuggerUrl);
      await cdp.connect();
      await cdp.createTab(cfg.web_url);
      summary.environment.chrome = browser.version.Browser;
    }

    currentStage = 'startup_semantics_placeholder';
    if (hooks.waitForStartupReady) {
      await hooks.waitForStartupReady(cdp, canaries);
    } else {
      await waitForStartupAndGuestBaseline(cdp, canaries);
    }

    currentStage = 'initial_time_origin';
    const measuredOrigin = hooks.measureTimeOrigin
      ? await hooks.measureTimeOrigin(cdp, canaries)
      : await safeEvaluate(cdp, 'performance.timeOrigin', canaries);
    if (!isValidTimeOrigin(measuredOrigin)) {
      throw new Error(`invalid initial performance.timeOrigin: ${measuredOrigin}`);
    }
    origin0 = measuredOrigin;

    const actors = [
      { cycle: 1, actor: 'cohost', email: cfg.cohost_email || 'cohosta@example.test', password: cfg.cohost_password },
      { cycle: 2, actor: 'member', email: cfg.member_email || 'membera@example.test', password: cfg.member_password },
    ];

    for (const step of actors) {
      log(`starting cycle ${step.cycle} (Owner -> logout -> ${step.actor})`);
      const cycleRecord = {
        cycle: step.cycle,
        actor: step.actor,
        same_document: false,
        time_origin: origin0,
        epochs: {},
        verdict: { verdict: 'FAIL', findings: ['cycle did not complete'], incomplete: true },
        last_stage: 'init',
      };
      summary.cycles.push(cycleRecord);
      activeCycle = cycleRecord;

      const recordEpoch = async (epName, label) => {
        currentEpoch = epName;
        currentStage = `${epName}_scan`;
        cycleRecord.last_stage = currentStage;
        const epOrigin = hooks.measureTimeOrigin
          ? await hooks.measureTimeOrigin(cdp, canaries)
          : await safeEvaluate(cdp, 'performance.timeOrigin', canaries);
        if (!isValidTimeOrigin(epOrigin) || epOrigin !== origin0) {
          cycleRecord.same_document = false;
          throw new Error(`cycle ${step.cycle} ${epName} document reloaded (${origin0} != ${epOrigin})`);
        }
        const scan = hooks.scanEpoch
          ? await hooks.scanEpoch({ cdp, dumpsDir, label, sentinelsPath, classesPath, maxBytes: cfg.max_snapshot_bytes, step, epName })
          : await captureAndScan({ cdp, dumpsDir, label, sentinelsPath, classesPath, maxBytes: cfg.max_snapshot_bytes });
        scan.time_origin = epOrigin;
        cycleRecord.epochs[epName] = scan;
        cycleRecord.same_document = Object.values(cycleRecord.epochs).every((ep) => ep && ep.time_origin === origin0);
      };

      const runEpochAction = async (epName, fn) => {
        if (hooks.performEpochAction) {
          await hooks.performEpochAction({ cdp, step, epName, fixtureMeta, canaries, probeValue });
        } else {
          await fn();
        }
      };

      currentStage = 'baseline_probe';
      currentEpoch = 'baseline';
      cycleRecord.last_stage = currentStage;
      await runEpochAction('baseline', async () => {
        await safeEvaluate(cdp, `window.__bh07heapProbe = ${JSON.stringify(probeValue)}`, canaries);
      });
      await recordEpoch('baseline', `c${step.cycle}_baseline`);

      currentStage = 'owner_instructions';
      currentEpoch = 'owner_active';
      cycleRecord.last_stage = currentStage;
      await runEpochAction('owner_active', async () => {
        await loginActor(cdp, cfg.owner_email || 'ownera@example.test', cfg.owner_password, canaries);
        await openOwnerInstructionsAndCancel(cdp, fixtureMeta.session_title);
        await safeEvaluate(cdp, `window.__bh07heapProbe = ${JSON.stringify(probeValue)}`, canaries);
      });
      await recordEpoch('owner_active', `c${step.cycle}_owner_active`);

      currentStage = 'owner_precondition';
      currentEpoch = 'owner_active';
      cycleRecord.last_stage = currentStage;
      const precond = checkOwnerPrecondition(cycleRecord.epochs.owner_active);
      if (!precond.ok) {
        throw new Error(`cycle ${step.cycle} owner_active precondition failed: missing=${precond.missing.join(',')} unreachable=${precond.unreachable.join(',')}`);
      }

      currentStage = 'zero_mutation_check';
      currentEpoch = 'owner_active';
      cycleRecord.last_stage = currentStage;
      const mutRes = hooks.checkFixtureZeroMutations
        ? hooks.checkFixtureZeroMutations({ cfgPath, statePath })
        : JSON.parse(runCmd(PY, ['-X', 'utf8', FIXTURE_CLI, 'check', '--config', cfgPath, '--state', statePath], { shell: false }));
      if (!mutRes.ok) {
        throw new Error(`cycle ${step.cycle} zero-mutation gate failed: ${JSON.stringify(mutRes.counts)}`);
      }

      currentStage = 'owner_logout';
      currentEpoch = 'post_logout';
      cycleRecord.last_stage = currentStage;
      await runEpochAction('post_logout', async () => {
        await logoutActor(cdp, canaries);
      });
      await recordEpoch('post_logout', `c${step.cycle}_post_logout`);

      currentStage = 'actor_navigation';
      currentEpoch = 'post_actor';
      cycleRecord.last_stage = currentStage;
      await runEpochAction('post_actor', async () => {
        await loginActor(cdp, step.email, step.password, canaries);
        if (step.actor === 'cohost') await openCohostSummary(cdp);
        else await openMemberHistory(cdp);
      });
      await recordEpoch('post_actor', `c${step.cycle}_post_${step.actor}`);

      if (step.cycle === 1) {
        currentStage = 'cycle1_logout';
        currentEpoch = null;
        cycleRecord.last_stage = currentStage;
        await runEpochAction('cycle1_logout', async () => {
          await logoutActor(cdp, canaries);
        });
      }

      currentStage = 'oracle_verdict';
      currentEpoch = null;
      cycleRecord.last_stage = currentStage;
      let verdict;
      if (hooks.decideCycleVerdict) {
        verdict = await hooks.decideCycleVerdict({ step, epochs: cycleRecord.epochs });
      } else {
        const scansPath = path.join(dumpsDir, `c${step.cycle}_scans.json`);
        const expPath = path.join(dumpsDir, `c${step.cycle}_expectations.json`);
        fs.writeFileSync(scansPath, JSON.stringify(cycleRecord.epochs), { mode: 0o600 });
        runCmd(PY, ['-X', 'utf8', ORACLE, 'expectations', '--scans', scansPath, '--out', expPath], { shell: false });
        verdict = JSON.parse(runVerdict(PY, [
          '-X', 'utf8', ORACLE, 'decide', '--scans', scansPath, '--expectations', expPath,
          '--cleanup-ok', 'true', '--mode', 'profile', '--require-paths',
        ]));
      }

      cycleRecord.verdict = verdict;
      cycleRecord.same_document = REQUIRED_EPOCHS.every(
        (ep) => cycleRecord.epochs[ep] && cycleRecord.epochs[ep].time_origin === origin0,
      );
      cycleRecord.last_stage = 'completed';
      activeCycle = null;
    }

    currentStage = 'post_cycles_attribution';
    currentEpoch = null;
    if (hooks.beforeAttribution) {
      await hooks.beforeAttribution(summary);
    }

    summary.same_document_across_cycles = computeSameDocumentAcrossCycles(summary.cycles, origin0);
    const bindingForAttr = sourceBindingResult && sourceBindingResult.ok
      ? sourceBindingResult.sanitized
      : (sourceBindingResult || null);
    summary.attribution_assessment = assessPathAttribution(summary.cycles, {
      sourceBinding: bindingForAttr,
      expectedMainJsSha,
    });
    const allCyclesPass = summary.cycles.length === 2
      && summary.cycles.every((c) => isCycleCompleteAndPassing(c, origin0));
    summary.verdict = allCyclesPass && summary.same_document_across_cycles ? 'PASS' : 'FAIL';
    summary.status = summary.verdict === 'PASS' ? 'RUN' : 'FAIL';
    summary.findings = summary.cycles.flatMap((c) => (c.verdict.findings || []).map((f) => `cycle ${c.cycle}: ${f}`));
  } catch (err) {
    summary.status = 'FAIL';
    summary.verdict = 'FAIL';
    const safeErr = sanitizeDiagnostic(err && err.message ? err.message : String(err), secretValues);
    summary.error = safeErr;
    summary.failure = {
      stage: currentStage,
      epoch: currentEpoch,
      cycle: activeCycle ? activeCycle.cycle : null,
      actor: activeCycle ? activeCycle.actor : null,
      message: safeErr,
    };
    if (activeCycle) {
      activeCycle.failed_stage = currentStage;
      if (currentEpoch) activeCycle.failed_epoch = currentEpoch;
      activeCycle.verdict = {
        verdict: 'FAIL',
        incomplete: true,
        failed_stage: currentStage,
        failed_epoch: currentEpoch || null,
        findings: [safeErr],
      };
    }
    summary.findings.push(safeErr);
    log(`aborted at stage=${currentStage}${currentEpoch ? ` epoch=${currentEpoch}` : ''}: ${safeErr}`);
  } finally {
    if (cdp) await cdp.close().catch(() => {});
    if (browser) {
      const shut = hooks.shutdownBrowser
        ? await hooks.shutdownBrowser(browser)
        : await shutdownOwnedBrowser(browser);
      if (!shut.exited || !shut.profileRemoved) {
        browserCleanupOk = false;
        summary.cleanup.browser_shutdown_error = shut.error;
      }
    }
    if (ownServer) {
      try { process.kill(ownServer.pid); } catch (_) {}
    }
    let fixtureReceipt = {};
    if (hooks.cleanupFixture) {
      try {
        fixtureReceipt = hooks.cleanupFixture({ cfgPath, statePath, fixtureCreated });
      } catch (cleanErr) {
        fixtureReceipt = {
          disposable_instructions_cleanup_verified: false,
          error: sanitizeDiagnostic(cleanErr.message, secretValues),
        };
      }
    } else if ((fixtureCreated && fs.existsSync(statePath)) || fs.existsSync(statePath)) {
      try {
        fixtureReceipt = JSON.parse(runVerdict(PY, ['-X', 'utf8', FIXTURE_CLI, 'cleanup', '--config', cfgPath, '--state', statePath], { shell: false }));
      } catch (cleanErr) {
        fixtureReceipt = {
          disposable_instructions_cleanup_verified: false,
          error: sanitizeDiagnostic(cleanErr.message, secretValues),
        };
      }
    } else {
      fixtureReceipt = {
        disposable_instructions_club_created: false,
        disposable_instructions_session_created: false,
        disposable_instructions_removed: false,
        disposable_instructions_verified_absent: false,
        disposable_instructions_cleanup_verified: false,
        zero_mutation_verified: false,
        baseline_fingerprint_equal: false,
      };
    }

    const res = finalizeRunResources({
      dumpsClaim,
      statePath,
      fixtureCleanupVerified: fixtureReceipt.disposable_instructions_cleanup_verified === true,
      rootDir: ROOT,
      fsMod,
    });
    summary.cleanup = buildCleanupSummary({
      existingCleanup: summary.cleanup,
      fixtureReceipt,
      resourceResult: res,
      browserCleanupOk,
      browserUserDataDir: browser && browser.userDataDir,
      secretValues,
      fsMod,
    });
    if (!summary.cleanup.ok) {
      summary.verdict = 'FAIL';
      summary.status = 'FAIL';
      if (summary.cleanup.recovery_state_retained && summary.cleanup.recovery_state_error) {
        summary.findings.push('private fixture recovery state unlink failed; state retained safely');
      }
      summary.findings.push('cleanup or zero-mutation/baseline verification failed');
    }

    summary.same_document_across_cycles = computeSameDocumentAcrossCycles(summary.cycles, origin0);
    if (!summary.attribution_assessment) {
      const fallbackExpectedSha = summary.environment.build && summary.environment.build.artifacts
        ? summary.environment.build.artifacts['main.dart.js']
        : null;
      const fallbackBinding = sourceBindingResult && sourceBindingResult.ok
        ? sourceBindingResult.sanitized
        : (sourceBindingResult || null);
      summary.attribution_assessment = assessPathAttribution(summary.cycles, {
        sourceBinding: fallbackBinding,
        expectedMainJsSha: fallbackExpectedSha,
      });
    }
    const completeAndPassing = (
      summary.cycles.length === 2
      && summary.cycles.every((c) => isCycleCompleteAndPassing(c, origin0))
      && summary.same_document_across_cycles
    );
    if (!completeAndPassing) {
      summary.verdict = 'FAIL';
      summary.status = 'FAIL';
      for (const c of summary.cycles) {
        if (!isCycleCompleteAndPassing(c, origin0) && (!c.verdict || c.verdict.verdict === 'PASS')) {
          c.verdict = { verdict: 'FAIL', incomplete: true, findings: ['cycle failed completion or same-document gate'] };
        }
      }
    }
    if (summary.verdict !== 'PASS' && summary.attribution_assessment) {
      summary.attribution_assessment = {
        ...summary.attribution_assessment,
        scoped_verdict: 'FAIL',
      };
    }

    summary.finished_at = new Date().toISOString();
    const companionBinding = sourceBindingResult && sourceBindingResult.ok
      ? sourceBindingResult.companion
      : null;
    const cleanSummary = writeEvidenceBundle(resolvedOutDir, summary, logLines, secretValues, companionBinding);
    const exitCode = cleanSummary.status === 'RUN' && cleanSummary.verdict === 'PASS' ? 0 : 1;
    return { summary: cleanSummary, exitCode };
  }
}

async function main() {
  const argv = process.argv.slice(2);
  const cfgIdx = argv.indexOf('--config');
  const outIdx = argv.indexOf('--out');
  const cfgPath = cfgIdx >= 0 ? argv[cfgIdx + 1] : process.env.BH07_INSTRUCTIONS_CONFIG;
  if (!cfgPath) throw new Error('--config <path> or BH07_INSTRUCTIONS_CONFIG is required');

  const rawCfg = JSON.parse(fs.readFileSync(cfgPath, 'utf8'));
  const cfg = validateConfig(rawCfg);
  const outDir = outIdx >= 0 ? argv[outIdx + 1] : (cfg.out_dir || path.join(ROOT, 'docs/reviews/bh07/payment_instructions_heap_evidence'));
  const { summary, exitCode } = await runMeasurement({ cfg, cfgPath, outDir });
  console.log(JSON.stringify({
    status: summary.status,
    verdict: summary.verdict,
    scoped_verdict: summary.attribution_assessment.scoped_verdict,
  }));
  process.exitCode = exitCode;
}

module.exports = {
  validateConfig,
  assertOutsideRepo,
  claimDumpsDirectory,
  deleteOwnedDumpsDirectory,
  finalizeRunResources,
  buildCleanupSummary,
  claimOutputDirectory,
  verifyServedBuild,
  streamSnapshotToFile,
  assertNoCanaryInEvaluate,
  checkOwnerPrecondition,
  extractJsConstructor,
  extractAndValidateSourceBinding,
  hasOrderedDtoRetainerChain,
  assessPathAttribution,
  computeSameDocumentAcrossCycles,
  isCycleCompleteAndPassing,
  waitForFlutterSemanticsReady,
  waitForStartupAndGuestBaseline,
  runMeasurement,
  findSentinelLeaks,
  redactSentinels,
  redactValue,
  renderReport,
  writeEvidenceBundle,
  hashArtifacts,
};

if (require.main === module) {
  main().catch((err) => {
    console.error(err.stack || err.message);
    process.exitCode = 1;
  });
}
