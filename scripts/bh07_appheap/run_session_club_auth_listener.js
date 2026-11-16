'use strict';

// Companion runner for BH-07 Web AuthProvider -> SessionProvider / ClubProvider
// listener-graph and selected-field reset measurements.
// Preserves all Finance/PaymentInstructions tooling, CLIs, contracts, and evidence bundles.

const crypto = require('node:crypto');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawn } = require('node:child_process');

const buildGuard = require('./build_guard.js');
const { shutdownOwnedBrowser } = require('./owned_browser_cleanup.js');
const piRunner = require('./run_payment_instructions_heap.js');
const finRunner = require('./run_finance_auth_listener.js');

const ROOT = piRunner.ROOT;
const PY = piRunner.PY;
const SESSION_CLUB_GRAPH_PY = path.join(__dirname, 'session_club_auth_listener_graph.py');

const CLAIM_SCOPE = 'auth_provider_rooted_listener_to_session_and_club_provider_selected_fields_only';
const OBSERVATION_MODE = finRunner.OBSERVATION_MODE;
const MAX_SOURCE_BINDING_BYTES = 65536;

const DEFAULT_SELECTED_FIELDS = {
  session: {
    sessionIdField: '_currentSessionId',
    currentSessionField: '_currentSession',
    historyField: '_session_provider$_history',
  },
  club: {
    clubIdField: '_currentClubId',
    currentClubField: '_currentClub',
    bankAccountField: '_currentBankAccount',
  },
};

function buildSessionClubAllowedClasses(binding) {
  const allowed = finRunner.buildAllowedClasses(binding);
  for (const name of [
    'SessionProvider',
    'ClubProvider',
    'Session',
    'Session0',
    'SessionHistoryPage',
    'Club',
    'BankAccount',
  ]) {
    allowed.add(name);
  }
  if (binding && typeof binding === 'object') {
    for (const sec of ['auth_provider', 'bound_closure', 'session_provider', 'club_provider']) {
      const cname = binding[sec] && binding[sec].constructor_name;
      if (typeof cname === 'string' && cname) {
        allowed.add(cname);
      }
    }
    if (binding.models && typeof binding.models === 'object') {
      for (const m of Object.values(binding.models)) {
        if (m && typeof m.constructor_name === 'string' && m.constructor_name) {
          allowed.add(m.constructor_name);
        }
      }
    }
  }
  return allowed;
}

function extractSessionClubBinding({ buildDir, expectedMainJsSha = null, outFile = null }) {
  const args = ['-X', 'utf8', SESSION_CLUB_GRAPH_PY, 'bind', '--build-dir', buildDir];
  if (expectedMainJsSha) {
    args.push('--expected-main-js-sha', expectedMainJsSha);
  }
  if (outFile) {
    args.push('--out', outFile);
  }
  try {
    const raw = finRunner.runCmd(PY, args);
    return outFile ? JSON.parse(fs.readFileSync(outFile, 'utf8')) : JSON.parse(raw);
  } catch (err) {
    if (err.status === 1 && err.stdout) {
      return JSON.parse(err.stdout);
    }
    throw err;
  }
}

function sanitizeFieldSet(propsList, fieldNames, cdpErrors, prefix, allowedClasses) {
  const out = {};
  for (const fname of fieldNames) {
    const found = finRunner.findUniqueOwnProperty(propsList, fname, cdpErrors, prefix);
    const meta = found.duplicate
      ? { present: false, has_getter: false, is_null: false, value_type: null, class_name: null }
      : finRunner.extractSafeDescriptorMeta(found.desc, { allowedClasses });
    if (meta.has_getter) {
      cdpErrors.push(`${prefix}_getter_${fname}`);
    }
    out[fname] = {
      present: meta.present,
      has_getter: meta.has_getter,
      is_null: meta.is_null,
      value_type: meta.value_type,
      class_name: meta.class_name,
    };
  }
  return out;
}

async function observeAuthAndTargetProviders({
  cdp,
  authHeapObjectId,
  sessionHeapObjectId = null,
  clubHeapObjectId = null,
  binding = null,
  authClassName = 'AuthProvider',
  sessionClassName = 'SessionProvider',
  clubClassName = 'ClubProvider',
  sessionFields = null,
  clubFields = null,
  allowedClasses = null,
  measureTimeOrigin = null,
}) {
  const effAllowed = allowedClasses || buildSessionClubAllowedClasses(binding);
  const spInfo = (binding && binding.session_provider) || {};
  const cpInfo = (binding && binding.club_provider) || {};
  const spFields = sessionFields || [
    spInfo.session_id_field || DEFAULT_SELECTED_FIELDS.session.sessionIdField,
    spInfo.current_session_field || DEFAULT_SELECTED_FIELDS.session.currentSessionField,
    spInfo.history_field || DEFAULT_SELECTED_FIELDS.session.historyField,
  ];
  const cpFields = clubFields || [
    cpInfo.club_id_field || DEFAULT_SELECTED_FIELDS.club.clubIdField,
    cpInfo.current_club_field || DEFAULT_SELECTED_FIELDS.club.currentClubField,
    cpInfo.bank_account_field || DEFAULT_SELECTED_FIELDS.club.bankAccountField,
  ];

  const objectGroup = `bh07_sc_listener_obs_${crypto.randomBytes(6).toString('hex')}`;
  const cdpErrors = [];
  let obsResult = null;
  let priorError = null;
  let objectGroupReleased = false;

  try {
    const rawOriginBefore = await finRunner.readTimeOrigin(cdp, measureTimeOrigin);
    const timeOriginBefore = finRunner.isValidTimeOrigin(rawOriginBefore) ? rawOriginBefore : null;
    if (timeOriginBefore === null) {
      cdpErrors.push('invalid_time_origin_before');
    }

    const resolveObj = async (heapId, expectedClass) => {
      const resolved = await finRunner.cdpSend(cdp, 'HeapProfiler.getObjectByHeapObjectId', {
        objectId: String(heapId),
        objectGroup,
      });
      const remote = resolved && resolved.result;
      if (
        !remote
        || typeof remote !== 'object'
        || !remote.objectId
        || typeof remote.objectId !== 'string'
        || remote.type !== 'object'
        || remote.className !== expectedClass
      ) {
        throw new Error(`HeapProfiler.getObjectByHeapObjectId identity mismatch for ${expectedClass}`);
      }
      return remote.objectId;
    };

    const getOwnProps = async (remoteObjId, phaseLabel) => {
      const res = await finRunner.cdpSend(cdp, 'Runtime.getProperties', {
        objectId: remoteObjId,
        ownProperties: true,
        generatePreview: false,
      });
      if (!res || !Array.isArray(res.result)) {
        cdpErrors.push(`${phaseLabel}_get_properties_invalid`);
        return [];
      }
      return res.result;
    };

    const authRemoteId = await resolveObj(authHeapObjectId, (binding && binding.auth_provider && binding.auth_provider.constructor_name) || authClassName);
    const authBefore = finRunner.readAuthOwnSnapshot(
      await getOwnProps(authRemoteId, 'auth_before'),
      cdpErrors,
      'auth_before',
      effAllowed,
    );

    let sessionSelectedFields = null;
    if (sessionHeapObjectId !== null && sessionHeapObjectId !== undefined) {
      const spRemoteId = await resolveObj(sessionHeapObjectId, spInfo.constructor_name || sessionClassName);
      const spProps = await getOwnProps(spRemoteId, 'session');
      sessionSelectedFields = sanitizeFieldSet(spProps, spFields, cdpErrors, 'session', effAllowed);
    }

    let clubSelectedFields = null;
    if (clubHeapObjectId !== null && clubHeapObjectId !== undefined) {
      const cpRemoteId = await resolveObj(clubHeapObjectId, cpInfo.constructor_name || clubClassName);
      const cpProps = await getOwnProps(cpRemoteId, 'club');
      clubSelectedFields = sanitizeFieldSet(cpProps, cpFields, cdpErrors, 'club', effAllowed);
    }

    const authAfter = finRunner.readAuthOwnSnapshot(
      await getOwnProps(authRemoteId, 'auth_after'),
      cdpErrors,
      'auth_after',
      effAllowed,
    );
    const rawOriginAfter = await finRunner.readTimeOrigin(cdp, measureTimeOrigin);
    const timeOriginAfter = finRunner.isValidTimeOrigin(rawOriginAfter) ? rawOriginAfter : null;
    if (timeOriginAfter === null) {
      cdpErrors.push('invalid_time_origin_after');
    } else if (timeOriginBefore !== null && timeOriginBefore !== timeOriginAfter) {
      cdpErrors.push('time_origin_changed_during_cdp_observation');
    }

    const userBefore = authBefore.currentUser;
    const userAfter = authAfter.currentUser;
    if (
      userBefore.present !== userAfter.present
      || userBefore.has_getter !== userAfter.has_getter
      || userBefore.is_null !== userAfter.is_null
      || userBefore.value_type !== userAfter.value_type
      || userBefore.class_name !== userAfter.class_name
    ) {
      cdpErrors.push('auth_current_user_before_after_mismatch');
    }

    const countersMatch = finRunner.COUNTER_FIELDS.every(
      (f) => Number.isSafeInteger(authBefore.counters[f])
        && authBefore.counters[f] >= 0
        && authBefore.counters[f] === authAfter.counters[f],
    );
    const quiescent = countersMatch
      && authBefore.counters.ChangeNotifier__notificationCallStackDepth === 0
      && authBefore.counters.ChangeNotifier__reentrantlyRemovedListeners === 0;

    obsResult = {
      observation_mode: OBSERVATION_MODE,
      atomic_claim: false,
      auth_heap_object_id: String(authHeapObjectId),
      time_origin_before: timeOriginBefore,
      time_origin_after: timeOriginAfter,
      before: authBefore.counters,
      after: authAfter.counters,
      counters_match: countersMatch,
      quiescent,
      auth_current_user: userBefore,
      auth_current_user_before: userBefore,
      auth_current_user_after: userAfter,
      cdp_errors: cdpErrors,
    };
    if (sessionHeapObjectId !== null && sessionHeapObjectId !== undefined) {
      obsResult.session_heap_object_id = String(sessionHeapObjectId);
      obsResult.session_selected_fields = sessionSelectedFields;
    }
    if (clubHeapObjectId !== null && clubHeapObjectId !== undefined) {
      obsResult.club_heap_object_id = String(clubHeapObjectId);
      obsResult.club_selected_fields = clubSelectedFields;
    }
  } catch (err) {
    priorError = err;
  } finally {
    try {
      await finRunner.cdpSend(cdp, 'Runtime.releaseObjectGroup', { objectGroup });
      objectGroupReleased = true;
    } catch (relErr) {
      const relMsg = relErr && relErr.message ? relErr.message : String(relErr);
      if (priorError) {
        priorError = new Error(`${priorError.message}; Runtime.releaseObjectGroup also failed: ${relMsg}`);
      } else {
        priorError = new Error(`Runtime.releaseObjectGroup failed: ${relMsg}`);
      }
    }
  }

  if (priorError) {
    throw priorError;
  }
  obsResult.object_group_released = objectGroupReleased;
  return obsResult;
}

async function openOwnerSessionAndClub(cdp, fixtureMeta) {
  if (!fixtureMeta || !fixtureMeta.session_title || !fixtureMeta.club_name) {
    throw new Error('fixtureMeta.session_title and fixtureMeta.club_name are required for Owner UI preconditions');
  }

  // 1. Load SessionHistory + SessionDetail into SessionProvider (zero writes)
  await piRunner.returnHomeTabs(cdp);
  await cdp.clickSemantic((e) => e.role === 'tab' && e.aria === 'Buổi Chơi', 'Sessions tab');
  await cdp.clickSemantic((e) => piRunner.textOf(e).includes('Lịch sử buổi'), 'History entry');
  await cdp.clickSemantic((e) => piRunner.textOf(e).includes(fixtureMeta.session_title), 'Disposable session row');
  await cdp.waitForSemantic(
    (e) => piRunner.textOf(e).includes('Tài chính & thu tiền') || piRunner.textOf(e).includes('Tổng kết buổi'),
    'Owner session detail loaded',
  );
  await piRunner.wait(400);

  // 2. Load Clubs + ClubDetail + ClubBankAccount attempt into ClubProvider (zero writes)
  await piRunner.returnHomeTabs(cdp);
  await cdp.clickSemantic((e) => e.role === 'tab' && (e.aria === 'CLB & Quỹ' || piRunner.textOf(e).includes('CLB & Quỹ')), 'Clubs tab');
  await cdp.clickSemantic((e) => piRunner.textOf(e).includes(fixtureMeta.club_name), 'Disposable club card');
  await cdp.waitForSemantic((e) => piRunner.textOf(e).includes('Tài khoản quỹ'), 'ClubDetailScreen tabs loaded');
  await cdp.clickSemantic((e) => piRunner.textOf(e).includes('Tài khoản quỹ'), 'Club bank tab');
  await cdp.waitForSemantic(
    (e) => piRunner.textOf(e).includes('ĐANG DÙNG') || piRunner.textOf(e).includes('Chưa cấu hình tài khoản ngân hàng nhận quỹ'),
    'Club bank account state settled',
  );
  await piRunner.wait(400);
}

async function openMemberHistorySettled(cdp) {
  await piRunner.openMemberHistory(cdp);
  await cdp.waitForSemantic(
    (e) => piRunner.textOf(e).includes('Bộ lọc')
      && (piRunner.textOf(e).includes('Chưa có buổi nào')
        || piRunner.textOf(e).includes('Hoàn thành')
        || piRunner.textOf(e).includes('Đã huỷ')
        || piRunner.textOf(e).includes('Tải thêm')),
    'Member session history settled',
  ).catch(async () => {
    await piRunner.wait(1000);
  });
}

function renderSessionClubReport(summary) {
  const sc = summary.session_club_assessment || {};
  const binding = summary.listener_graph_binding || {};
  const sp = binding.session_provider || {};
  const cp = binding.club_provider || {};
  const models = binding.models || {};
  const lines = [
    '# BH-07 V2b — AuthProvider -> SessionProvider / ClubProvider Finite Listener Graph',
    '',
    `- Gate: ${summary.gate}`,
    `- Status: **${summary.status}** (verdict: **${summary.verdict || 'null'}**)`,
    `- Overall listener gate: **${sc.session_club_listener_gate || 'FAIL'}**`,
    `- SessionProvider gate: **${sc.session_listener_gate || 'FAIL'}**`,
    `- ClubProvider core gate: **${sc.club_core_listener_gate || 'FAIL'}**`,
    `- ClubProvider currentBankAccount gate: **${sc.club_bank_account_gate || 'NOT_RUN'}**`,
    `- Claim scope: \`${summary.claim_scope || CLAIM_SCOPE}\``,
    `- Observation mode: \`${OBSERVATION_MODE}\` (atomic_claim=false)`,
    `- Tested source: \`${summary.tested_source_sha}\` (git dirty: ${summary.git_dirty})`,
    `- Same document across cycles: ${Boolean(summary.same_document_across_cycles)}`,
    `- Source binding sha256: \`${binding.listener_binding_sha256 || 'unverified'}\``,
    `- Selected SessionProvider fields: \`${sp.session_id_field || '?'}\`, \`${sp.current_session_field || '?'}\` (${(models.session || {}).constructor_name || '?'}), \`${sp.history_field || '?'}\` (${(models.session_history_page || {}).constructor_name || '?'})`,
    `- Selected ClubProvider fields: \`${cp.club_id_field || '?'}\`, \`${cp.current_club_field || '?'}\` (${(models.club || {}).constructor_name || '?'}), \`${cp.bank_account_field || '?'}\` (${(models.bank_account || {}).constructor_name || '?'})`,
    '',
    '## Cycles & Epochs (2 cycles / 8 epochs)',
    '',
    '| cycle | actor | same doc | epoch | snap sha12 | overall | session | club core | club bank |',
    '| --- | --- | --- | --- | --- | --- | --- | --- | --- |',
  ];

  for (const cyc of summary.cycles || []) {
    for (const epName of piRunner.REQUIRED_EPOCHS) {
      const ep = (cyc.epochs || {})[epName] || {};
      const lg = ep.listener_graph || {};
      const ts = lg.target_status || {};
      lines.push(
        `| ${cyc.cycle} | ${cyc.actor} | ${cyc.same_document} | ${epName} | ${ep.sha256_12 || 'n/a'} `
        + `| ${lg.verdict || 'missing'} | ${ts.session_provider || 'n/a'} | ${ts.club_provider_core || 'n/a'} `
        + `| ${ts.club_provider_bank_account || 'n/a'} |`,
      );
    }
  }

  lines.push('', '## Findings', '');
  const findings = summary.findings || [];
  lines.push(...(findings.length ? findings.map((f) => `- ${f}`) : ['- none']));
  lines.push('', '## Cleanup', '', `- ${JSON.stringify(summary.cleanup || {})}`, '');
  lines.push('## Claim Limits', '',
    '- Covers ONLY AuthProvider -> SessionProvider (`_currentSessionId`, `_currentSession`, `_session_provider$_history`) and AuthProvider -> ClubProvider (`_currentClubId`, `_currentClub`, `_currentBankAccount`) in Chromium/Edge V8 heap + CDP own-properties.',
    '- Does NOT certify uninspected SessionProvider/ClubProvider fields (`_mySessions`, `_publicSessions`, `_currentPlayers`, `_clubs`, `_currentMembers`, `_rosterMembers`), full `auth_listeners`, other providers, or native mobile/desktop VMs.',
    '- Hybrid snapshot + CDP own-property counters are explicitly non-atomic (`atomic_claim: false`).',
    '- If `club_bank_account_gate` is `NOT_RUN`, existing disposable instructions fixture created no `club_bank_accounts` row for its disposable club; do not infer `BankAccount` clear coverage without extending the disposable fixture.', '');
  return lines.join('\n');
}

function writeSessionClubEvidence(outDir, summary, logLines, secretValues, companionBinding = null) {
  const bindingStrings = companionBinding ? piRunner.collectStrings(companionBinding) : [];
  const leaks = piRunner.findSentinelLeaks(
    [...piRunner.collectStrings(summary), ...logLines, ...bindingStrings],
    secretValues,
  );
  if (leaks.length > 0) {
    summary.findings = [...(summary.findings || []),
      `raw sensitive marker reached publication (${leaks.join(', ')}); redacted, run failed`];
    summary.verdict = 'FAIL';
    summary.status = 'FAIL';
    if (summary.session_club_assessment) {
      summary.session_club_assessment.session_club_listener_gate = 'FAIL';
    }
  }
  const cleanSummary = piRunner.redactValue(summary, secretValues);
  const cleanJson = JSON.stringify(cleanSummary, null, 2) + '\n';
  const cleanLogs = logLines.map((line) => piRunner.redactSentinels(line, secretValues)).join('\n') + '\n';
  const cleanReport = renderSessionClubReport(cleanSummary);

  fs.writeFileSync(path.join(outDir, 'summary.json'), cleanJson, 'utf8');
  fs.writeFileSync(path.join(outDir, 'run.log'), cleanLogs, 'utf8');
  fs.writeFileSync(path.join(outDir, 'report.md'), cleanReport, 'utf8');

  const filesToHash = ['summary.json', 'run.log', 'report.md'];
  if (companionBinding && companionBinding.ok === true) {
    const cleanBinding = piRunner.redactValue(companionBinding, secretValues);
    const bindingJson = JSON.stringify(cleanBinding, null, 2) + '\n';
    if (Buffer.byteLength(bindingJson, 'utf8') > MAX_SOURCE_BINDING_BYTES) {
      throw new Error('source_binding.json exceeded bounded artifact limit');
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

function aggregateTargetGate(cycles, key, { allowNotRunOwner = false } = {}) {
  if (!Array.isArray(cycles) || cycles.length !== 2) return 'FAIL';
  const statuses = [];
  for (let i = 0; i < cycles.length; i += 1) {
    const cyc = cycles[i];
    const cnum = i + 1;
    for (const epName of piRunner.REQUIRED_EPOCHS) {
      const ep = cyc && cyc.epochs && cyc.epochs[epName];
      const lg = ep && ep.listener_graph;
      const st = (lg && lg.target_status && lg.target_status[key]) || 'FAIL';
      if (st === 'UNKNOWN') return 'UNKNOWN';
      if (st === 'FAIL') return 'FAIL';
      if (cnum === 1 && epName === 'baseline') {
        if (st !== 'PASS' && st !== 'NOT_RUN_LAZY') return 'FAIL';
      } else if (allowNotRunOwner && epName === 'owner_active') {
        if (st !== 'PASS' && st !== 'NOT_RUN') return 'FAIL';
      } else if (st !== 'PASS') {
        return 'FAIL';
      }
      statuses.push({ epName, st });
    }
  }
  if (allowNotRunOwner) {
    const ownerSts = statuses.filter((s) => s.epName === 'owner_active').map((s) => s.st);
    if (ownerSts.every((s) => s === 'PASS')) return 'PASS';
    if (ownerSts.every((s) => s === 'NOT_RUN')) return 'NOT_RUN';
    return 'FAIL';
  }
  return 'PASS';
}

function isValidHeapObjectId(val) {
  return typeof val === 'string' && /^[1-9][0-9]*$/.test(val);
}

function extractOwnerObjectIdsFromRecord(lgRec, binding) {
  const out = {};
  const sp = (binding && binding.session_provider) || {};
  const cp = (binding && binding.club_provider) || {};
  const spRec = ((lgRec && lgRec.session_provider && lgRec.session_provider.records) || [])[0];
  if (spRec && spRec.selected_fields) {
    const cs = spRec.selected_fields[sp.current_session_field];
    const hs = spRec.selected_fields[sp.history_field];
    if (cs && cs.present === true && cs.is_null === false && isValidHeapObjectId(cs.target_heap_object_id)) {
      out.current_session = cs.target_heap_object_id;
    }
    if (hs && hs.present === true && hs.is_null === false && isValidHeapObjectId(hs.target_heap_object_id)) {
      out.session_history = hs.target_heap_object_id;
    }
  }
  const cpRec = ((lgRec && lgRec.club_provider && lgRec.club_provider.records) || [])[0];
  if (cpRec && cpRec.selected_fields) {
    const cc = cpRec.selected_fields[cp.current_club_field];
    const cb = cpRec.selected_fields[cp.bank_account_field];
    if (cc && cc.present === true && cc.is_null === false && isValidHeapObjectId(cc.target_heap_object_id)) {
      out.current_club = cc.target_heap_object_id;
    }
    if (cb && cb.present === true && cb.is_null === false && isValidHeapObjectId(cb.target_heap_object_id)) {
      out.current_bank_account = cb.target_heap_object_id;
    }
  }
  return out;
}

async function runSessionClubAuthListener({
  cfg,
  cfgPath,
  outDir,
  requireBankAccount = false,
  userHooks = {},
}) {
  const resolvedOutDir = piRunner.claimOutputDirectory(outDir);
  const dumpsClaim = piRunner.claimDumpsDirectory(cfg.dumps_dir, ROOT);
  const dumpsDir = dumpsClaim.dir;
  const statePath = cfg.state_path;
  const fsMod = userHooks.fsMod || fs;

  const logLines = [];
  const secretValues = {};
  if (cfg.owner_password) secretValues.owner_password = cfg.owner_password;
  if (cfg.cohost_password) secretValues.cohost_password = cfg.cohost_password;
  if (cfg.member_password) secretValues.member_password = cfg.member_password;
  if (cfg.supabase_anon_key) secretValues.supabase_anon_key = cfg.supabase_anon_key;

  const log = (msg) => {
    const line = `[${new Date().toISOString()}] ${piRunner.redactSentinels(msg, secretValues)}`;
    console.log(line);
    logLines.push(line);
  };

  const gitProv = userHooks.getGitProvenance
    ? userHooks.getGitProvenance()
    : {
      tested_source_sha: piRunner.runCmd('git', ['rev-parse', 'HEAD']).trim(),
      git_dirty: piRunner.runCmd('git', ['status', '--porcelain']).trim() !== '',
    };

  const summary = {
    gate: 'V2b — AuthProvider -> SessionProvider / ClubProvider finite listener graph',
    coverage_profile: 'session_club_auth_listener',
    claim_scope: CLAIM_SCOPE,
    observation_mode: OBSERVATION_MODE,
    atomic_claim: false,
    require_bank_account: Boolean(requireBankAccount),
    status: 'NOT RUN',
    verdict: null,
    measurement_surface: 'Flutter Web profile build + V8 heap snapshot + read-only CDP own-properties',
    oracle: 'artifact-bound constructor/tearoff/reset verification + finite SessionProvider/ClubProvider listener subgraph',
    tested_source_sha: gitProv.tested_source_sha,
    git_dirty: gitProv.git_dirty,
    same_document_across_cycles: false,
    environment: { os: `${process.platform} ${os.release()}`, node: process.version },
    sentinels: {},
    cycles: [],
    notes: [],
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
  let listenerBinding = null;
  let lastFailedEpoch = null;
  const effectiveBuildDir = userHooks.buildDir || cfg.build_dir || piRunner.BUILD_DIR;

  try {
    currentStage = 'build_provenance';
    if (userHooks.prepareBuild) {
      summary.environment.build = await userHooks.prepareBuild();
    } else if (cfg.reuse_existing_server === true) {
      const prov = cfg.provenance || JSON.parse(fs.readFileSync(cfg.provenance_path, 'utf8'));
      summary.environment.build = await piRunner.verifyServedBuild({
        webUrl: cfg.web_url,
        buildDir: effectiveBuildDir,
        provenance: prov,
      });
    } else {
      const webPort = Number(new URL(cfg.web_url).port) || 8088;
      await buildGuard.assertPortFree(webPort);
      const before = buildGuard.snapshotArtifacts(effectiveBuildDir);
      const startedAt = Date.now();
      piRunner.runCmd(process.platform === 'win32' ? 'flutter.bat' : 'flutter', [
        'build', 'web', '--profile',
        '--dart-define=APP_ENV=test',
        `--dart-define=SUPABASE_URL=${cfg.supabase_url}`,
        `--dart-define=SUPABASE_ANON_KEY=${cfg.supabase_anon_key}`,
      ], { shell: process.platform === 'win32' });
      buildGuard.assertArtifactsFresh(effectiveBuildDir, startedAt, before);
      ownServer = spawn(PY, ['-m', 'http.server', String(webPort), '--bind', '127.0.0.1', '--directory', effectiveBuildDir], {
        cwd: ROOT,
        stdio: 'ignore',
      });
      await piRunner.wait(1000);
      summary.environment.build = await piRunner.verifyServedBuild({
        webUrl: cfg.web_url,
        buildDir: effectiveBuildDir,
        provenance: {
          mode: 'profile',
          started_at: new Date(startedAt).toISOString(),
          artifacts: buildGuard.hashArtifacts(effectiveBuildDir),
        },
      });
      summary.environment.build.reused = false;
    }

    currentStage = 'source_binding';
    const expectedMainJsSha = summary.environment.build && summary.environment.build.artifacts
      ? summary.environment.build.artifacts['main.dart.js']
      : null;
    listenerBinding = userHooks.extractListenerBinding
      ? await userHooks.extractListenerBinding({ buildDir: effectiveBuildDir, expectedMainJsSha })
      : extractSessionClubBinding({ buildDir: effectiveBuildDir, expectedMainJsSha });
    if (!listenerBinding || listenerBinding.ok !== true) {
      throw new Error(`session/club listener source binding failed: ${(listenerBinding && listenerBinding.error) || 'unknown'}`);
    }
    summary.listener_graph_binding = listenerBinding;

    currentStage = 'fixture_create';
    const fixtureMeta = userHooks.createFixture
      ? userHooks.createFixture({ cfgPath, statePath })
      : JSON.parse(piRunner.runCmd(PY, ['-X', 'utf8', piRunner.FIXTURE_CLI, 'create', '--config', cfgPath, '--state', statePath], { shell: false }));
    fixtureCreated = true;

    const privState = JSON.parse(fs.readFileSync(statePath, 'utf8'));
    for (const skey of ['club_id', 'club_member_id', 'session_id', 'player_id', 'revision_id', 'charge_id', 'marker_id', 'sentinel_1', 'sentinel_2']) {
      if (privState[skey]) secretValues[`fixture_${skey}`] = privState[skey];
    }
    const probeValue = `BH07SCLISTENERPROBE-${crypto.randomBytes(4).toString('hex')}`;
    secretValues.probe = probeValue;
    summary.sentinels = {
      probe: {
        available: true,
        length: probeValue.length,
        sha256_12: piRunner.sha12(probeValue),
        rendered: false,
        distinctive: true,
        scope: 'control',
      },
    };

    currentStage = 'browser_start';
    if (userHooks.startSession) {
      const session = await userHooks.startSession({ dumpsDir, cfg });
      browser = session.browser;
      cdp = session.cdp;
    } else {
      browser = await piRunner.startBrowserLogged(path.join(dumpsDir, 'browser.log'), cfg);
      const { CdpClient } = piRunner;
      cdp = new CdpClient(browser.version.webSocketDebuggerUrl);
      await cdp.connect();
      await cdp.createTab(cfg.web_url);
      summary.environment.chrome = browser.version.Browser;
    }

    currentStage = 'startup_semantics_placeholder';
    if (userHooks.waitForStartupReady) {
      await userHooks.waitForStartupReady(cdp, secretValues);
    } else {
      await piRunner.waitForStartupAndGuestBaseline(cdp, secretValues);
    }

    currentStage = 'initial_time_origin';
    const measuredOrigin = await finRunner.readTimeOrigin(cdp, userHooks.measureTimeOrigin || null);
    if (!finRunner.isValidTimeOrigin(measuredOrigin)) {
      throw new Error(`invalid initial performance.timeOrigin: ${measuredOrigin}`);
    }
    origin0 = measuredOrigin;

    const actors = [
      { cycle: 1, actor: 'cohost', email: cfg.cohost_email || 'cohosta@example.test', password: cfg.cohost_password },
      { cycle: 2, actor: 'member', email: cfg.member_email || 'membera@example.test', password: cfg.member_password },
    ];
    const allowedClasses = buildSessionClubAllowedClasses(listenerBinding);

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
      let ownerFieldIds = null;

      const scanOneEpoch = async (epName, label) => {
        currentEpoch = epName;
        currentStage = `${epName}_scan`;
        cycleRecord.last_stage = currentStage;

        const epOrigin = await finRunner.readTimeOrigin(cdp, userHooks.measureTimeOrigin || null);
        if (!finRunner.isValidTimeOrigin(epOrigin) || epOrigin !== origin0) {
          cycleRecord.same_document = false;
          throw new Error(`cycle ${step.cycle} ${epName} document reloaded (${origin0} != ${epOrigin})`);
        }

        const snapFile = path.join(dumpsDir, `${label}.heapsnapshot`);
        const bindingTmp = path.join(dumpsDir, `${label}_sc_binding.json`);
        const preScanTmp = path.join(dumpsDir, `${label}_sc_prescan.json`);
        const cdpTmp = path.join(dumpsDir, `${label}_sc_cdp.json`);
        const prevIdsTmp = path.join(dumpsDir, `${label}_sc_prev_ids.json`);

        let preScan;
        let snapSizeBytes;
        try {
          fs.writeFileSync(bindingTmp, JSON.stringify(listenerBinding), { mode: 0o600 });
          const streamFn = userHooks.streamSnapshotToFile || piRunner.streamSnapshotToFile;
          await streamFn({ cdp, outFile: snapFile, maxBytes: cfg.max_snapshot_bytes });
          snapSizeBytes = fs.statSync(snapFile).size;
          finRunner.runCmd(PY, [
            '-X', 'utf8', SESSION_CLUB_GRAPH_PY, 'scan',
            '--snapshot', snapFile, '--binding', bindingTmp, '--epoch', epName, '--out', preScanTmp,
          ]);
          preScan = JSON.parse(fs.readFileSync(preScanTmp, 'utf8'));
        } finally {
          finRunner.unlinkIfExists(snapFile);
        }

        let lgRecord;
        let obsTimeOrigin = null;
        try {
          const authIds = preScan.rooted_auth_heap_object_ids || [];
          const spIds = preScan.rooted_session_heap_object_ids || [];
          const cpIds = preScan.rooted_club_heap_object_ids || [];
          let cdpObs = null;

          if (authIds.length === 1 && spIds.length <= 1 && cpIds.length <= 1) {
            try {
              cdpObs = await observeAuthAndTargetProviders({
                cdp,
                authHeapObjectId: authIds[0],
                sessionHeapObjectId: spIds.length === 1 ? spIds[0] : null,
                clubHeapObjectId: cpIds.length === 1 ? cpIds[0] : null,
                binding: listenerBinding,
                allowedClasses,
                measureTimeOrigin: userHooks.measureTimeOrigin || null,
              });
              obsTimeOrigin = finRunner.isValidTimeOrigin(cdpObs.time_origin_before) ? cdpObs.time_origin_before : null;
            } catch (_obsErr) {
              cdpObs = {
                observation_mode: OBSERVATION_MODE,
                atomic_claim: false,
                object_group_released: false,
                cdp_errors: ['cdp_observation_exception'],
              };
            }
          } else {
            cdpObs = {
              observation_mode: OBSERVATION_MODE,
              atomic_claim: false,
              object_group_released: true,
              cdp_errors: [`cardinality_invalid:auth=${authIds.length},session=${spIds.length},club=${cpIds.length}`],
            };
          }

          fs.writeFileSync(cdpTmp, JSON.stringify(cdpObs), { mode: 0o600 });
          const cdpArgs = [
            '-X', 'utf8', SESSION_CLUB_GRAPH_PY, 'apply-cdp',
            '--prescan', preScanTmp, '--binding', bindingTmp, '--cdp', cdpTmp,
            '--epoch', epName, '--cycle', String(step.cycle), '--actor', step.actor,
          ];
          if (finRunner.isValidTimeOrigin(obsTimeOrigin)) {
            cdpArgs.push('--time-origin', String(obsTimeOrigin));
          } else {
            cdpArgs.push('--time-origin', String(epOrigin));
          }
          if (epName === 'post_actor') {
            fs.writeFileSync(prevIdsTmp, JSON.stringify(ownerFieldIds || {}), { mode: 0o600 });
            cdpArgs.push('--previous-owner-ids', prevIdsTmp);
          }
          if (requireBankAccount) {
            cdpArgs.push('--require-bank-account');
          }
          lgRecord = JSON.parse(finRunner.runCmd(PY, cdpArgs));
        } finally {
          finRunner.unlinkIfExists(bindingTmp);
          finRunner.unlinkIfExists(preScanTmp);
          finRunner.unlinkIfExists(cdpTmp);
          finRunner.unlinkIfExists(prevIdsTmp);
        }

        const epochRecord = {
          epoch: epName,
          ok: Boolean(lgRecord && lgRecord.ok),
          time_origin: epOrigin,
          size_bytes: snapSizeBytes,
          sha256_12: preScan.snapshot_sha256_12,
          listener_graph: lgRecord,
        };
        cycleRecord.epochs[epName] = epochRecord;
        cycleRecord.same_document = Object.values(cycleRecord.epochs).every((e) => e && e.time_origin === origin0);

        const failDiag = () => {
          lastFailedEpoch = { cycle: step.cycle, actor: step.actor, epName, timeOrigin: epOrigin, scan: epochRecord };
        };
        if (!lgRecord || lgRecord.verdict === 'FAIL' || lgRecord.verdict === 'UNKNOWN') {
          failDiag();
          throw new Error(`cycle ${step.cycle} ${epName} listener_graph ${lgRecord ? lgRecord.verdict : 'missing'}: ${((lgRecord && lgRecord.findings) || []).join(',')}`);
        }
        if (epName !== 'baseline' && lgRecord.verdict !== 'PASS') {
          failDiag();
          throw new Error(`cycle ${step.cycle} ${epName} listener_graph invalid verdict ${lgRecord.verdict}`);
        }
        if (step.cycle === 2 && epName === 'baseline' && lgRecord.verdict !== 'PASS') {
          failDiag();
          throw new Error(`cycle 2 baseline listener_graph expected PASS, got ${lgRecord.verdict}`);
        }
        if (epName === 'owner_active') {
          ownerFieldIds = extractOwnerObjectIdsFromRecord(lgRecord, listenerBinding);
        }
      };

      const runEpochAction = async (epName, defaultFn) => {
        if (userHooks.performEpochAction) {
          await userHooks.performEpochAction({ cdp, step, epName, fixtureMeta, probeValue });
        } else {
          await defaultFn();
        }
      };

      currentStage = 'baseline_probe';
      cycleRecord.last_stage = currentStage;
      await runEpochAction('baseline', async () => {
        await piRunner.safeEvaluate(cdp, `window.__bh07scProbe = ${JSON.stringify(probeValue)}`, secretValues);
      });
      await scanOneEpoch('baseline', `c${step.cycle}_baseline`);

      currentStage = 'owner_session_and_club';
      cycleRecord.last_stage = currentStage;
      await runEpochAction('owner_active', async () => {
        await piRunner.loginActor(cdp, cfg.owner_email || 'ownera@example.test', cfg.owner_password, secretValues);
        await openOwnerSessionAndClub(cdp, fixtureMeta);
        await piRunner.safeEvaluate(cdp, `window.__bh07scProbe = ${JSON.stringify(probeValue)}`, secretValues);
      });
      await scanOneEpoch('owner_active', `c${step.cycle}_owner_active`);

      currentStage = 'zero_mutation_check';
      cycleRecord.last_stage = currentStage;
      const mutRes = userHooks.checkFixtureZeroMutations
        ? userHooks.checkFixtureZeroMutations({ cfgPath, statePath })
        : JSON.parse(piRunner.runCmd(PY, ['-X', 'utf8', piRunner.FIXTURE_CLI, 'check', '--config', cfgPath, '--state', statePath], { shell: false }));
      if (!mutRes.ok) {
        throw new Error(`cycle ${step.cycle} zero-mutation gate failed: ${JSON.stringify(mutRes.counts)}`);
      }

      currentStage = 'owner_logout';
      cycleRecord.last_stage = currentStage;
      await runEpochAction('post_logout', async () => {
        await piRunner.logoutActor(cdp, secretValues);
      });
      await scanOneEpoch('post_logout', `c${step.cycle}_post_logout`);

      currentStage = 'actor_navigation';
      cycleRecord.last_stage = currentStage;
      await runEpochAction('post_actor', async () => {
        await piRunner.loginActor(cdp, step.email, step.password, secretValues);
        if (step.actor === 'cohost') await piRunner.openCohostSummary(cdp);
        else await openMemberHistorySettled(cdp);
      });
      await scanOneEpoch('post_actor', `c${step.cycle}_post_${step.actor}`);

      if (step.cycle === 1) {
        currentStage = 'cycle1_logout';
        cycleRecord.last_stage = currentStage;
        await runEpochAction('cycle1_logout', async () => {
          await piRunner.logoutActor(cdp, secretValues);
        });
      }

      const ownerBankSt = cycleRecord.epochs.owner_active.listener_graph.target_status.club_provider_bank_account;
      cycleRecord.verdict = {
        verdict: ownerBankSt === 'PASS' ? 'PASS' : (requireBankAccount ? 'FAIL' : 'PARTIAL_NOT_RUN'),
        incomplete: false,
        findings: ownerBankSt === 'NOT_RUN'
          ? ['ClubProvider._currentBankAccount unpopulated at owner_active (existing fixture has no club_bank_accounts row); gate reported NOT_RUN']
          : [],
      };
      cycleRecord.last_stage = 'completed';
      activeCycle = null;
    }

    currentStage = 'cross_cycle_assessment';
    summary.same_document_across_cycles = piRunner.computeSameDocumentAcrossCycles(summary.cycles, origin0);
    const spGate = aggregateTargetGate(summary.cycles, 'session_provider');
    const cpCoreGate = aggregateTargetGate(summary.cycles, 'club_provider_core');
    const cpBankGate = aggregateTargetGate(summary.cycles, 'club_provider_bank_account', { allowNotRunOwner: true });

    let overallGate = 'FAIL';
    if (spGate === 'UNKNOWN' || cpCoreGate === 'UNKNOWN' || cpBankGate === 'UNKNOWN') {
      overallGate = 'UNKNOWN';
    } else if (spGate === 'PASS' && cpCoreGate === 'PASS' && cpBankGate === 'PASS') {
      overallGate = 'PASS';
    } else if (spGate === 'PASS' && cpCoreGate === 'PASS' && cpBankGate === 'NOT_RUN') {
      overallGate = requireBankAccount ? 'FAIL' : 'PARTIAL_CLUB_BANK_NOT_RUN';
    } else if (spGate === 'FAIL' || cpCoreGate === 'FAIL' || cpBankGate === 'FAIL') {
      overallGate = 'FAIL';
    } else {
      overallGate = 'NOT_RUN';
    }

    summary.session_club_assessment = {
      session_listener_gate: spGate,
      club_core_listener_gate: cpCoreGate,
      club_bank_account_gate: cpBankGate,
      session_club_listener_gate: overallGate,
      claim_scope: CLAIM_SCOPE,
      observation_mode: OBSERVATION_MODE,
      atomic_claim: false,
    };

    if (cpBankGate === 'NOT_RUN') {
      summary.notes.push(
        'ClubProvider._currentBankAccount remained null at owner_active because disposable_instructions_fixture.py does not seed public.club_bank_accounts; club_bank_account_gate is honestly reported NOT_RUN.',
      );
    }
    const okOverall = (overallGate === 'PASS' || (!requireBankAccount && overallGate === 'PARTIAL_CLUB_BANK_NOT_RUN'))
      && summary.same_document_across_cycles === true;
    summary.status = okOverall ? 'RUN' : 'FAIL';
    summary.verdict = overallGate === 'PASS' ? 'PASS' : (overallGate === 'PARTIAL_CLUB_BANK_NOT_RUN' && okOverall ? 'PARTIAL_NOT_RUN' : 'FAIL');
  } catch (err) {
    summary.status = 'FAIL';
    summary.verdict = 'FAIL';
    const safeErr = piRunner.sanitizeDiagnostic(err && err.message ? err.message : String(err), secretValues);
    summary.error = safeErr;
    summary.failure = {
      stage: currentStage,
      epoch: currentEpoch,
      cycle: activeCycle ? activeCycle.cycle : null,
      actor: activeCycle ? activeCycle.actor : null,
      message: safeErr,
    };
    if (activeCycle) {
      activeCycle.verdict = {
        verdict: 'FAIL',
        incomplete: true,
        failed_stage: currentStage,
        failed_epoch: currentEpoch || null,
        findings: [safeErr],
      };
    }
    if (
      lastFailedEpoch
      && activeCycle
      && lastFailedEpoch.cycle === activeCycle.cycle
      && lastFailedEpoch.actor === activeCycle.actor
      && !activeCycle.epochs[lastFailedEpoch.epName]
    ) {
      activeCycle.epochs[lastFailedEpoch.epName] = lastFailedEpoch.scan;
    }
    summary.findings.push(safeErr);
    summary.session_club_assessment = {
      session_listener_gate: 'FAIL',
      club_core_listener_gate: 'FAIL',
      club_bank_account_gate: 'FAIL',
      session_club_listener_gate: 'FAIL',
      claim_scope: CLAIM_SCOPE,
      observation_mode: OBSERVATION_MODE,
      atomic_claim: false,
    };
    log(`aborted at stage=${currentStage}${currentEpoch ? ` epoch=${currentEpoch}` : ''}: ${safeErr}`);
  } finally {
    if (cdp) await cdp.close().catch(() => {});
    if (browser) {
      const shut = userHooks.shutdownBrowser
        ? await userHooks.shutdownBrowser(browser)
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
    if (userHooks.cleanupFixture) {
      try {
        fixtureReceipt = userHooks.cleanupFixture({ cfgPath, statePath, fixtureCreated });
      } catch (cleanErr) {
        fixtureReceipt = {
          disposable_instructions_cleanup_verified: false,
          error: piRunner.sanitizeDiagnostic(cleanErr.message, secretValues),
        };
      }
    } else if ((fixtureCreated && fs.existsSync(statePath)) || fs.existsSync(statePath)) {
      try {
        fixtureReceipt = JSON.parse(piRunner.runVerdict(PY, ['-X', 'utf8', piRunner.FIXTURE_CLI, 'cleanup', '--config', cfgPath, '--state', statePath], { shell: false }));
      } catch (cleanErr) {
        fixtureReceipt = {
          disposable_instructions_cleanup_verified: false,
          error: piRunner.sanitizeDiagnostic(cleanErr.message, secretValues),
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

    const res = piRunner.finalizeRunResources({
      dumpsClaim,
      statePath,
      fixtureCleanupVerified: fixtureReceipt.disposable_instructions_cleanup_verified === true,
      rootDir: ROOT,
      fsMod,
    });
    summary.cleanup = piRunner.buildCleanupSummary({
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
      if (summary.session_club_assessment) {
        summary.session_club_assessment.session_club_listener_gate = 'FAIL';
      }
      summary.findings.push('cleanup or zero-mutation/baseline verification failed');
    }

    summary.same_document_across_cycles = piRunner.computeSameDocumentAcrossCycles(summary.cycles, origin0);
    if (!summary.same_document_across_cycles && summary.verdict !== 'FAIL') {
      summary.verdict = 'FAIL';
      summary.status = 'FAIL';
      if (summary.session_club_assessment) {
        summary.session_club_assessment.session_club_listener_gate = 'FAIL';
      }
    }

    summary.finished_at = new Date().toISOString();
    const companionBinding = listenerBinding && listenerBinding.ok ? listenerBinding : null;
    const cleanSummary = writeSessionClubEvidence(resolvedOutDir, summary, logLines, secretValues, companionBinding);
    const exitCode = (cleanSummary.status === 'RUN' && (cleanSummary.verdict === 'PASS' || (!requireBankAccount && cleanSummary.verdict === 'PARTIAL_NOT_RUN'))) ? 0 : 1;
    return { summary: cleanSummary, exitCode };
  }
}

async function main() {
  const argv = process.argv.slice(2);
  const cfgIdx = argv.indexOf('--config');
  const outIdx = argv.indexOf('--out');
  const requireBank = argv.includes('--require-bank-account');
  const cfgPath = cfgIdx >= 0 ? argv[cfgIdx + 1] : process.env.BH07_INSTRUCTIONS_CONFIG;
  if (!cfgPath) throw new Error('--config <path> or BH07_INSTRUCTIONS_CONFIG is required');

  const rawCfg = JSON.parse(fs.readFileSync(cfgPath, 'utf8'));
  const cfg = piRunner.validateConfig(rawCfg);
  const outDir = outIdx >= 0
    ? argv[outIdx + 1]
    : (cfg.out_dir || path.join(ROOT, 'docs/reviews/bh07/session_club_auth_listener_evidence'));

  const { summary, exitCode } = await runSessionClubAuthListener({
    cfg,
    cfgPath,
    outDir,
    requireBankAccount: requireBank,
  });
  console.log(JSON.stringify({
    status: summary.status,
    verdict: summary.verdict,
    assessment: summary.session_club_assessment,
  }));
  process.exitCode = exitCode;
}

module.exports = {
  CLAIM_SCOPE,
  OBSERVATION_MODE,
  DEFAULT_SELECTED_FIELDS,
  buildSessionClubAllowedClasses,
  extractSessionClubBinding,
  observeAuthAndTargetProviders,
  openOwnerSessionAndClub,
  openMemberHistorySettled,
  renderSessionClubReport,
  writeSessionClubEvidence,
  runSessionClubAuthListener,
};

if (require.main === module) {
  main().catch((err) => {
    console.error(err.stack || err.message);
    process.exitCode = 1;
  });
}
