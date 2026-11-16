'use strict';

const { execFileSync } = require('node:child_process');
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');

const runner = require('./run_payment_instructions_heap.js');

const ROOT = path.resolve(__dirname, '..', '..');
const PY = process.env.PYTHON || 'python';
const ORACLE = path.join(__dirname, 'heap_oracle.py');
const LISTENER_GRAPH_PY = path.join(__dirname, 'finance_auth_listener_graph.py');

const CLAIM_SCOPE = 'auth_provider_rooted_listener_to_finance_provider_instructions_and_finance_only';
const OBSERVATION_MODE = 'hybrid_snapshot_plus_readonly_cdp_own_properties';

const COUNTER_FIELDS = [
  'ChangeNotifier__count',
  'ChangeNotifier__notificationCallStackDepth',
  'ChangeNotifier__reentrantlyRemovedListeners',
];

const CDP_VALUE_TYPES = new Set([
  'object', 'function', 'undefined', 'string', 'number', 'boolean', 'symbol', 'bigint',
]);

const STRUCTURAL_CLASS_ALLOWLIST = new Set([
  'AuthProvider',
  'FinanceProvider',
  'PaymentInstructions',
  'SessionFinance',
  'BoundClosure',
  'User',
  'tear_off',
  'Closure',
  'Object',
  'Array',
  '_InheritedProviderScopeElement',
  'SessionProvider',
  'ClubProvider',
]);

function isValidTimeOrigin(val) {
  return typeof val === 'number' && Number.isFinite(val) && val > 0;
}

function buildAllowedClasses(binding) {
  const allowed = new Set(STRUCTURAL_CLASS_ALLOWLIST);
  if (binding && typeof binding === 'object') {
    for (const sec of ['auth_provider', 'finance_provider', 'payment_instructions', 'session_finance', 'bound_closure']) {
      const cname = binding[sec] && binding[sec].constructor_name;
      if (typeof cname === 'string' && cname) {
        allowed.add(cname);
      }
    }
  }
  return allowed;
}

function sanitizeCdpValueType(rawType) {
  return (typeof rawType === 'string' && CDP_VALUE_TYPES.has(rawType)) ? rawType : 'unknown';
}

function sanitizeCdpClassName(val, allowedClasses) {
  if (!val || val.type !== 'object') return null;
  if (typeof val.className === 'string' && allowedClasses.has(val.className)) {
    return val.className;
  }
  return null;
}

function runCmd(cmd, args, opts = {}) {
  return execFileSync(cmd, args, {
    cwd: ROOT,
    encoding: 'utf8',
    maxBuffer: 64 * 1024 * 1024,
    shell: false,
    ...opts,
  });
}

async function cdpSend(cdp, method, params = {}, timeoutMs = 60000) {
  let timer = null;
  try {
    const res = await Promise.race([
      cdp.send(method, params),
      new Promise((_, reject) => {
        timer = setTimeout(() => reject(new Error(`${method}: CDP timeout after ${timeoutMs}ms`)), timeoutMs);
      }),
    ]);
    if (res && res.error) {
      throw new Error(`${method}: ${res.error.message || JSON.stringify(res.error)}`);
    }
    if (res && Object.prototype.hasOwnProperty.call(res, 'result')) {
      return res.result;
    }
    return res;
  } finally {
    if (timer) clearTimeout(timer);
  }
}

function extractListenerBinding({ buildDir, expectedMainJsSha = null, outFile = null }) {
  const args = ['-X', 'utf8', LISTENER_GRAPH_PY, 'bind', '--build-dir', buildDir];
  if (expectedMainJsSha) {
    args.push('--expected-main-js-sha', expectedMainJsSha);
  }
  if (outFile) {
    args.push('--out', outFile);
  }
  try {
    const raw = runCmd(PY, args);
    return outFile ? JSON.parse(fs.readFileSync(outFile, 'utf8')) : JSON.parse(raw);
  } catch (err) {
    if (err.status === 1 && err.stdout) {
      return JSON.parse(err.stdout);
    }
    throw err;
  }
}

function extractSafeDescriptorMeta(desc, { allowPrimitiveInt = false, allowedClasses = STRUCTURAL_CLASS_ALLOWLIST } = {}) {
  if (!desc) {
    return {
      present: false,
      has_getter: false,
      is_null: false,
      value_type: null,
      class_name: null,
      int_value: null,
    };
  }
  const hasGetter = Boolean(desc.get || desc.set);
  if (hasGetter || !Object.prototype.hasOwnProperty.call(desc, 'value') || !desc.value) {
    return {
      present: true,
      has_getter: hasGetter,
      is_null: false,
      value_type: null,
      class_name: null,
      int_value: null,
    };
  }
  const val = desc.value;
  const isNull = val.type === 'undefined'
    ? false
    : (val.type === 'object' && val.subtype === 'null');
  const intValue = (
    allowPrimitiveInt
    && val.type === 'number'
    && !val.unserializableValue
    && typeof val.value === 'number'
    && Number.isSafeInteger(val.value)
    && val.value >= 0
  )
    ? val.value
    : null;
  return {
    present: true,
    has_getter: false,
    is_null: isNull,
    value_type: isNull ? 'null' : sanitizeCdpValueType(val.type),
    class_name: isNull ? null : sanitizeCdpClassName(val, allowedClasses),
    int_value: intValue,
  };
}

function findUniqueOwnProperty(propList, name, errors, errPrefix) {
  const matches = (propList || []).filter((p) => p && p.name === name && p.isOwn !== false);
  if (matches.length > 1) {
    errors.push(`${errPrefix}_duplicate_${name}`);
    return { duplicate: true, desc: null };
  }
  return { duplicate: false, desc: matches.length === 1 ? matches[0] : null };
}

function readAuthOwnSnapshot(propList, errors, phase, allowedClasses = STRUCTURAL_CLASS_ALLOWLIST) {
  const counters = {};
  for (const field of COUNTER_FIELDS) {
    const found = findUniqueOwnProperty(propList, field, errors, phase);
    if (found.duplicate) {
      counters[field] = null;
      continue;
    }
    const meta = extractSafeDescriptorMeta(found.desc, { allowPrimitiveInt: true, allowedClasses });
    if (!meta.present) {
      errors.push(`${phase}_missing_${field}`);
      counters[field] = null;
    } else if (meta.has_getter) {
      errors.push(`${phase}_getter_${field}`);
      counters[field] = null;
    } else if (meta.int_value === null) {
      errors.push(`${phase}_non_integer_${field}`);
      counters[field] = null;
    } else {
      counters[field] = meta.int_value;
    }
  }
  const userFound = findUniqueOwnProperty(propList, '_currentUser', errors, phase);
  const userMeta = userFound.duplicate
    ? { present: false, has_getter: false, is_null: false, value_type: null, class_name: null }
    : extractSafeDescriptorMeta(userFound.desc, { allowedClasses });
  if (!userFound.duplicate && !userMeta.present) {
    errors.push(`${phase}_missing__currentUser`);
  } else if (userMeta.has_getter) {
    errors.push(`${phase}_getter__currentUser`);
  }
  return {
    counters,
    currentUser: {
      present: userMeta.present,
      has_getter: userMeta.has_getter,
      is_null: userMeta.is_null,
      value_type: userMeta.value_type,
      class_name: userMeta.class_name,
    },
  };
}

async function readTimeOrigin(cdp, measureTimeOriginHook = null) {
  if (measureTimeOriginHook) {
    return measureTimeOriginHook(cdp);
  }
  const res = await cdpSend(cdp, 'Runtime.evaluate', {
    expression: 'performance.timeOrigin',
    returnByValue: true,
  });
  return res && res.result ? res.result.value : null;
}

async function observeListenerScalarsAndFields({
  cdp,
  authHeapObjectId,
  financeHeapObjectId = null,
  instructionsField = '_instructions',
  financeField = '_finance',
  authClassName = 'AuthProvider',
  financeClassName = 'FinanceProvider',
  allowedClasses = STRUCTURAL_CLASS_ALLOWLIST,
  measureTimeOrigin = null,
}) {
  const objectGroup = `bh07_listener_obs_${crypto.randomBytes(6).toString('hex')}`;
  const cdpErrors = [];
  let obsResult = null;
  let priorError = null;
  let objectGroupReleased = false;

  try {
    const rawOriginBefore = await readTimeOrigin(cdp, measureTimeOrigin);
    const timeOriginBefore = isValidTimeOrigin(rawOriginBefore) ? rawOriginBefore : null;
    if (timeOriginBefore === null) {
      cdpErrors.push('invalid_time_origin_before');
    }

    const resolveObj = async (heapId, expectedClass) => {
      const resolved = await cdpSend(cdp, 'HeapProfiler.getObjectByHeapObjectId', {
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
      const res = await cdpSend(cdp, 'Runtime.getProperties', {
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

    const authRemoteId = await resolveObj(authHeapObjectId, authClassName);
    const authBefore = readAuthOwnSnapshot(
      await getOwnProps(authRemoteId, 'auth_before'),
      cdpErrors,
      'auth_before',
      allowedClasses,
    );

    let financeSelectedFields = null;
    if (financeHeapObjectId !== null && financeHeapObjectId !== undefined) {
      const finRemoteId = await resolveObj(financeHeapObjectId, financeClassName);
      const finProps = await getOwnProps(finRemoteId, 'finance');
      financeSelectedFields = {};
      for (const fname of [instructionsField, financeField]) {
        const found = findUniqueOwnProperty(finProps, fname, cdpErrors, 'finance');
        const meta = found.duplicate
          ? { present: false, has_getter: false, is_null: false, value_type: null, class_name: null }
          : extractSafeDescriptorMeta(found.desc, { allowedClasses });
        if (meta.has_getter) {
          cdpErrors.push(`finance_getter_${fname}`);
        }
        financeSelectedFields[fname] = {
          present: meta.present,
          has_getter: meta.has_getter,
          is_null: meta.is_null,
          value_type: meta.value_type,
          class_name: meta.class_name,
        };
      }
    }

    const authAfter = readAuthOwnSnapshot(
      await getOwnProps(authRemoteId, 'auth_after'),
      cdpErrors,
      'auth_after',
      allowedClasses,
    );
    const rawOriginAfter = await readTimeOrigin(cdp, measureTimeOrigin);
    const timeOriginAfter = isValidTimeOrigin(rawOriginAfter) ? rawOriginAfter : null;
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

    const countersMatch = COUNTER_FIELDS.every(
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
    if (financeHeapObjectId !== null && financeHeapObjectId !== undefined) {
      obsResult.finance_heap_object_id = String(financeHeapObjectId);
      obsResult.finance_selected_fields = financeSelectedFields;
    }
  } catch (err) {
    priorError = err;
  } finally {
    try {
      await cdpSend(cdp, 'Runtime.releaseObjectGroup', { objectGroup });
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

function unlinkIfExists(filePath) {
  try {
    if (filePath && fs.existsSync(filePath)) fs.unlinkSync(filePath);
  } catch (_) {}
}

function createListenerHooks({ cfg = {}, userHooks = {} } = {}) {
  let listenerBinding = null;
  let effectiveBuildDir = userHooks.buildDir || cfg.build_dir || path.join(ROOT, 'build', 'web');

  const hooks = {
    ...userHooks,
    buildDir: effectiveBuildDir,

    async extractSourceBinding({ buildDir, expectedMainJsSha, build }) {
      effectiveBuildDir = buildDir || effectiveBuildDir;
      const baseRes = userHooks.extractSourceBinding
        ? await userHooks.extractSourceBinding({ buildDir: effectiveBuildDir, expectedMainJsSha, build })
        : runner.extractAndValidateSourceBinding({ buildDir: effectiveBuildDir, expectedMainJsSha });
      if (!baseRes || baseRes.ok !== true) {
        throw new Error(`base source binding failed: ${(baseRes && baseRes.error) || 'unknown'}`);
      }
      const bound = userHooks.extractListenerBinding
        ? await userHooks.extractListenerBinding({ buildDir: effectiveBuildDir, expectedMainJsSha })
        : extractListenerBinding({ buildDir: effectiveBuildDir, expectedMainJsSha });
      if (!bound || bound.ok !== true) {
        throw new Error(`listener source binding failed: ${(bound && bound.error) || 'unknown'}`);
      }
      listenerBinding = bound;
      return baseRes;
    },

    async scanEpoch({ cdp, dumpsDir, label, sentinelsPath, classesPath, maxBytes, step, epName }) {
      if (!listenerBinding || listenerBinding.ok !== true) {
        throw new Error('listener source binding unavailable before scanEpoch');
      }

      const snapFile = path.join(dumpsDir, `${label}.heapsnapshot`);
      const bindingTmp = path.join(dumpsDir, `${label}_listener_binding.json`);
      const preScanTmp = path.join(dumpsDir, `${label}_listener_prescan.json`);
      const cdpTmp = path.join(dumpsDir, `${label}_listener_cdp.json`);

      let baseScan;
      let preScan;
      try {
        fs.writeFileSync(bindingTmp, JSON.stringify(listenerBinding), { mode: 0o600 });
        const streamFn = userHooks.streamSnapshotToFile || runner.streamSnapshotToFile;
        await streamFn({ cdp, outFile: snapFile, maxBytes });

        const rawBase = runCmd(PY, [
          '-X', 'utf8', ORACLE, 'scan',
          '--snapshot', snapFile, '--sentinels', sentinelsPath, '--classes', classesPath, '--paths',
        ]);
        baseScan = JSON.parse(rawBase);

        runCmd(PY, [
          '-X', 'utf8', LISTENER_GRAPH_PY, 'scan',
          '--snapshot', snapFile, '--binding', bindingTmp, '--epoch', epName, '--out', preScanTmp,
        ]);
        preScan = JSON.parse(fs.readFileSync(preScanTmp, 'utf8'));
      } finally {
        unlinkIfExists(snapFile);
      }

      let lgRecord;
      let obsTimeOrigin = null;
      try {
        const authIds = preScan.rooted_auth_heap_object_ids || [];
        const finIds = preScan.rooted_finance_heap_object_ids || [];
        let cdpObs = null;

        if (authIds.length === 1 && finIds.length <= 1) {
          try {
            cdpObs = await observeListenerScalarsAndFields({
              cdp,
              authHeapObjectId: authIds[0],
              financeHeapObjectId: finIds.length === 1 ? finIds[0] : null,
              authClassName: listenerBinding.auth_provider.constructor_name,
              financeClassName: listenerBinding.finance_provider.constructor_name,
              allowedClasses: buildAllowedClasses(listenerBinding),
              instructionsField: listenerBinding.finance_provider.instructions_field,
              financeField: listenerBinding.finance_provider.finance_field,
              measureTimeOrigin: userHooks.measureTimeOrigin || null,
            });
            obsTimeOrigin = isValidTimeOrigin(cdpObs.time_origin_before) ? cdpObs.time_origin_before : null;
          } catch (_obsErr) {
            cdpObs = {
              observation_mode: OBSERVATION_MODE,
              atomic_claim: false,
              object_group_released: false,
              cdp_errors: ['cdp_observation_exception'],
            };
            fs.writeFileSync(cdpTmp, JSON.stringify(cdpObs), { mode: 0o600 });
            lgRecord = JSON.parse(runCmd(PY, [
              '-X', 'utf8', LISTENER_GRAPH_PY, 'apply-cdp',
              '--prescan', preScanTmp, '--binding', bindingTmp, '--cdp', cdpTmp, '--epoch', epName,
            ]));
            baseScan.listener_graph = lgRecord;
            lastFailedEpoch = {
              cycle: step.cycle,
              actor: step.actor,
              epName,
              timeOrigin: null,
              scan: baseScan,
            };
            throw new Error(`cycle ${step.cycle} ${epName} listener_graph cdp_observation_exception`);
          }
        } else {
          cdpObs = {
            observation_mode: OBSERVATION_MODE,
            atomic_claim: false,
            object_group_released: true,
            cdp_errors: [`cardinality_invalid:auth=${authIds.length},finance=${finIds.length}`],
          };
        }

        fs.writeFileSync(cdpTmp, JSON.stringify(cdpObs), { mode: 0o600 });
        const cdpArgs = [
          '-X', 'utf8', LISTENER_GRAPH_PY, 'apply-cdp',
          '--prescan', preScanTmp, '--binding', bindingTmp, '--cdp', cdpTmp, '--epoch', epName,
        ];
        if (isValidTimeOrigin(obsTimeOrigin)) {
          cdpArgs.push('--time-origin', String(obsTimeOrigin));
        }
        lgRecord = JSON.parse(runCmd(PY, cdpArgs));
      } finally {
        unlinkIfExists(bindingTmp);
        unlinkIfExists(preScanTmp);
        unlinkIfExists(cdpTmp);
      }

      baseScan.listener_graph = lgRecord;

      const recordFailureDiag = () => {
        lastFailedEpoch = {
          cycle: step.cycle,
          actor: step.actor,
          epName,
          timeOrigin: isValidTimeOrigin(obsTimeOrigin) ? obsTimeOrigin : null,
          scan: baseScan,
        };
      };

      if (lgRecord.verdict === 'FAIL' || lgRecord.verdict === 'UNKNOWN') {
        recordFailureDiag();
        throw new Error(`cycle ${step.cycle} ${epName} listener_graph ${lgRecord.verdict}: ${(lgRecord.findings || []).join(',')}`);
      }
      if ((epName === 'owner_active' || epName === 'post_logout') && lgRecord.verdict !== 'PASS') {
        recordFailureDiag();
        throw new Error(`cycle ${step.cycle} ${epName} listener_graph invalid verdict ${lgRecord.verdict}`);
      }
      if (step.cycle === 2 && epName === 'baseline' && lgRecord.verdict !== 'PASS') {
        recordFailureDiag();
        throw new Error(`cycle 2 baseline listener_graph expected PASS, got ${lgRecord.verdict}`);
      }

      return baseScan;
    },

    async beforeAttribution(summary) {
      if (userHooks.beforeAttribution) {
        await userHooks.beforeAttribution(summary);
      }
      const cycleProblems = [];
      for (const cyc of summary.cycles || []) {
        for (const [epName, epScan] of Object.entries(cyc.epochs || {})) {
          const lg = epScan && epScan.listener_graph;
          if (!lg || (lg.verdict !== 'PASS' && lg.verdict !== 'NOT_RUN_LAZY')) {
            cycleProblems.push(`c${cyc.cycle}_${epName}:${lg ? lg.verdict : 'missing'}`);
          }
        }
      }
      summary.listener_graph_binding = listenerBinding;
      summary.listener_graph_assessment = {
        listener_graph_gate: cycleProblems.length === 0 ? 'PASS' : 'FAIL',
        claim_scope: CLAIM_SCOPE,
        observation_mode: OBSERVATION_MODE,
        atomic_claim: false,
        problems: cycleProblems,
      };
      if (cycleProblems.length > 0) {
        throw new Error(`listener_graph cross-cycle validation failed: ${cycleProblems.join(', ')}`);
      }
    },
  };

  let lastFailedEpoch = null;
  Object.defineProperty(hooks, '_getDiagnosticState', {
    enumerable: false,
    value: () => ({ listenerBinding, lastFailedEpoch }),
  });

  return hooks;
}

async function runFinanceAuthListener({ cfg, cfgPath, outDir, userHooks = {} }) {
  const hooks = createListenerHooks({ cfg, userHooks });
  const result = await runner.runMeasurement({ cfg, cfgPath, outDir, hooks });
  const diag = typeof hooks._getDiagnosticState === 'function' ? hooks._getDiagnosticState() : null;
  const failed = diag && diag.lastFailedEpoch;
  if (
    result
    && result.summary
    && result.summary.failure
    && failed
    && result.summary.failure.cycle === failed.cycle
    && result.summary.failure.epoch === failed.epName
  ) {
    const summary = result.summary;
    const cycles = summary.cycles || [];
    const targetCycle = cycles.find((c) => c && c.cycle === failed.cycle && c.actor === failed.actor);
    if (targetCycle) {
      targetCycle.epochs = targetCycle.epochs || {};
      if (!targetCycle.epochs[failed.epName]) {
        const attachedScan = { ...failed.scan };
        if (isValidTimeOrigin(failed.timeOrigin)) {
          attachedScan.time_origin = failed.timeOrigin;
        }
        targetCycle.epochs[failed.epName] = attachedScan;
      }
      const origin0 = cycles[0] && isValidTimeOrigin(cycles[0].time_origin) ? cycles[0].time_origin : null;
      if (
        origin0 !== null
        && isValidTimeOrigin(targetCycle.epochs[failed.epName].time_origin)
        && targetCycle.epochs[failed.epName].time_origin !== origin0
      ) {
        targetCycle.same_document = false;
      }
      summary.same_document_across_cycles = runner.computeSameDocumentAcrossCycles(cycles, origin0);
      if (!targetCycle.verdict || targetCycle.verdict.verdict === 'PASS') {
        targetCycle.verdict = {
          verdict: 'FAIL',
          incomplete: true,
          failed_stage: summary.failure.stage || null,
          failed_epoch: failed.epName,
          findings: [summary.failure.message || 'listener_graph failed'],
        };
      }
    }

    const cycleProblems = [];
    for (const cyc of cycles) {
      for (const [epName, epScan] of Object.entries(cyc.epochs || {})) {
        const lg = epScan && epScan.listener_graph;
        if (!lg || (lg.verdict !== 'PASS' && lg.verdict !== 'NOT_RUN_LAZY')) {
          cycleProblems.push(`c${cyc.cycle}_${epName}:${lg ? lg.verdict : 'missing'}`);
        }
      }
    }
    if (diag.listenerBinding) {
      summary.listener_graph_binding = diag.listenerBinding;
    }
    summary.listener_graph_assessment = {
      listener_graph_gate: 'FAIL',
      claim_scope: CLAIM_SCOPE,
      observation_mode: OBSERVATION_MODE,
      atomic_claim: false,
      problems: cycleProblems.length > 0 ? cycleProblems : [`c${failed.cycle}_${failed.epName}:FAIL`],
    };
    summary.verdict = 'FAIL';
    summary.status = 'FAIL';

    const secretValues = {};
    for (const k of ['owner_password', 'cohost_password', 'member_password', 'supabase_anon_key']) {
      if (cfg && cfg[k]) secretValues[k] = cfg[k];
    }
    const cleanSummary = runner.redactValue(summary, secretValues);
    result.summary = cleanSummary;
    result.exitCode = 1;

    const resolvedOutDir = path.resolve(outDir);
    const summaryPath = path.join(resolvedOutDir, 'summary.json');
    if (fs.existsSync(summaryPath)) {
      fs.writeFileSync(summaryPath, JSON.stringify(cleanSummary, null, 2) + '\n', 'utf8');
      fs.writeFileSync(path.join(resolvedOutDir, 'report.md'), runner.renderReport(cleanSummary), 'utf8');
      const filesToHash = ['summary.json', 'run.log', 'report.md']
        .filter((name) => fs.existsSync(path.join(resolvedOutDir, name)));
      if (fs.existsSync(path.join(resolvedOutDir, 'source_binding.json'))) {
        filesToHash.push('source_binding.json');
      }
      const hashFile = (file) => crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
      const manifest = filesToHash
        .map((name) => `${hashFile(path.join(resolvedOutDir, name))}  ${name}`).join('\n') + '\n';
      fs.writeFileSync(path.join(resolvedOutDir, 'hashes.sha256'), manifest, 'utf8');
    }
  }
  return result;
}

async function main() {
  const argv = process.argv.slice(2);
  const cfgIdx = argv.indexOf('--config');
  const outIdx = argv.indexOf('--out');
  const cfgPath = cfgIdx >= 0 ? argv[cfgIdx + 1] : process.env.BH07_INSTRUCTIONS_CONFIG;
  if (!cfgPath) throw new Error('--config <path> or BH07_INSTRUCTIONS_CONFIG is required');

  const rawCfg = JSON.parse(fs.readFileSync(cfgPath, 'utf8'));
  const cfg = runner.validateConfig(rawCfg);
  const outDir = outIdx >= 0
    ? argv[outIdx + 1]
    : (cfg.out_dir || path.join(ROOT, 'docs/reviews/bh07/finance_auth_listener_evidence'));
  const { summary, exitCode } = await runFinanceAuthListener({ cfg, cfgPath, outDir });
  console.log(JSON.stringify({
    status: summary.status,
    verdict: summary.verdict,
    listener_graph_gate: summary.listener_graph_assessment
      ? summary.listener_graph_assessment.listener_graph_gate
      : 'FAIL',
  }));
  process.exitCode = exitCode;
}

module.exports = {
  CLAIM_SCOPE,
  OBSERVATION_MODE,
  COUNTER_FIELDS,
  STRUCTURAL_CLASS_ALLOWLIST,
  isValidTimeOrigin,
  buildAllowedClasses,
  cdpSend,
  readTimeOrigin,
  extractSafeDescriptorMeta,
  findUniqueOwnProperty,
  readAuthOwnSnapshot,
  unlinkIfExists,
  runCmd,
  extractListenerBinding,
  observeListenerScalarsAndFields,
  createListenerHooks,
  runFinanceAuthListener,
};

if (require.main === module) {
  main().catch((err) => {
    console.error(err.stack || err.message);
    process.exitCode = 1;
  });
}
