'use strict';

const assert = require('node:assert/strict');
const { execFileSync } = require('node:child_process');
const crypto = require('node:crypto');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const ROOT = path.resolve(__dirname, '..', '..');
const PY = process.env.PYTHON || 'python';
const LISTENER_GRAPH_PY = path.join(__dirname, 'finance_auth_listener_graph.py');
const RUNNER_MOD = require('./run_finance_auth_listener.js');

function sha256Hex(bufOrText) {
  return crypto.createHash('sha256').update(bufOrText).digest('hex');
}

function makeMockCdp({
  authCount = 2,
  authAfterCount = authCount,
  depth = 0,
  afterDepth = depth,
  removed = 0,
  afterRemoved = removed,
  currentUserNull = false,
  afterCurrentUserNull = currentUserNull,
  missingCurrentUser = false,
  duplicateCurrentUser = false,
  duplicateAuthCounter = false,
  duplicateFinanceField = false,
  instructionsNull = false,
  instructionsClass = 'PaymentInstructions',
  instructionsType = 'object',
  financeNull = false,
  financeClass = 'SessionFinance',
  instructionsIsGetter = false,
  missingAuthCounter = false,
  nonIntAuthCounter = false,
  unsafeIntAuthCounter = false,
  releaseFails = false,
  readThrows = false,
  timeOriginBefore = 12345.6,
  timeOriginAfter = 12345.6,
  secretCanary = null,
  legacyObjectWireShape = false,
  authRemoteClass = 'AuthProvider',
  authRemoteType = 'object',
  financeRemoteClass = 'FinanceProvider',
  financeRemoteType = 'object',
} = {}) {
  const calls = [];
  let authReadNum = 0;
  let evalNum = 0;
  const authObjId = '{"injectedScriptId":1,"id":701}';
  const finObjId = '{"injectedScriptId":1,"id":702}';

  return {
    calls,
    async send(method, params = {}) {
      calls.push({ method, params: JSON.parse(JSON.stringify(params)) });
      if (method === 'Runtime.evaluate') {
        evalNum += 1;
        const val = evalNum === 1 ? timeOriginBefore : timeOriginAfter;
        return { result: { result: { type: typeof val, value: val } } };
      }
      if (method === 'HeapProfiler.getObjectByHeapObjectId') {
        if (readThrows) {
          throw new Error('simulated HeapProfiler.getObjectByHeapObjectId failure');
        }
        if (legacyObjectWireShape) {
          if (String(params.objectId) === '100') {
            return { result: { object: { objectId: authObjId, type: authRemoteType, className: authRemoteClass } } };
          }
          if (String(params.objectId) === '200') {
            return { result: { object: { objectId: finObjId, type: financeRemoteType, className: financeRemoteClass } } };
          }
          return { result: { object: null } };
        }
        // Real CDP wire shape BEFORE cdpSend unwraps outer .result -> { result: RemoteObject }
        if (String(params.objectId) === '100') {
          return { result: { result: { objectId: authObjId, type: authRemoteType, className: authRemoteClass } } };
        }
        if (String(params.objectId) === '200') {
          return { result: { result: { objectId: finObjId, type: financeRemoteType, className: financeRemoteClass } } };
        }
        return { result: { result: null } };
      }
      if (method === 'Runtime.getProperties') {
        assert.equal(params.ownProperties, true, 'must read ownProperties=true');
        assert.equal(params.generatePreview, false, 'must set generatePreview=false');
        if (params.objectId === authObjId) {
          authReadNum += 1;
          const cnt = authReadNum === 1 ? authCount : authAfterCount;
          const dep = authReadNum === 1 ? depth : afterDepth;
          const rem = authReadNum === 1 ? removed : afterRemoved;
          const uNull = authReadNum === 1 ? currentUserNull : afterCurrentUserNull;
          const props = [
            {
              name: 'ChangeNotifier__notificationCallStackDepth',
              isOwn: true,
              value: { type: 'number', value: dep },
            },
            {
              name: 'ChangeNotifier__reentrantlyRemovedListeners',
              isOwn: true,
              value: { type: 'number', value: rem },
            },
          ];
          if (!missingCurrentUser) {
            props.push({
              name: '_currentUser',
              isOwn: true,
              value: uNull
                ? { type: 'object', subtype: 'null', value: null }
                : { type: 'object', className: 'User', objectId: '{"injectedScriptId":1,"id":703}' },
            });
            if (duplicateCurrentUser) {
              props.push({
                name: '_currentUser',
                isOwn: true,
                value: { type: 'object', subtype: 'null', value: null },
              });
            }
          }
          if (!missingAuthCounter) {
            const valObj = nonIntAuthCounter
              ? { type: 'string', value: String(cnt) }
              : unsafeIntAuthCounter
                ? { type: 'number', value: 1e21 }
                : { type: 'number', value: cnt };
            props.push({
              name: 'ChangeNotifier__count',
              isOwn: true,
              value: valObj,
            });
            if (duplicateAuthCounter) {
              props.push({
                name: 'ChangeNotifier__count',
                isOwn: true,
                value: { type: 'number', value: cnt },
              });
            }
          }
          return { result: { result: props } };
        }
        if (params.objectId === finObjId) {
          const instrDesc = instructionsIsGetter
            ? { name: '_instructions', isOwn: true, get: { type: 'function', objectId: '{"injectedScriptId":1,"id":709}' } }
            : {
              name: '_instructions',
              isOwn: true,
              value: instructionsNull
                ? { type: 'object', subtype: 'null', value: null }
                : instructionsType === 'string'
                  ? {
                    type: 'string',
                    value: secretCanary || 'RAW_PRIVATE_STRING',
                    description: secretCanary || 'RAW_PRIVATE_STRING',
                  }
                  : {
                    type: instructionsType,
                    className: instructionsClass,
                    objectId: '{"injectedScriptId":1,"id":704}',
                    description: secretCanary ? `PaymentInstructions(${secretCanary})` : 'PaymentInstructions',
                  },
            };
          const finDesc = {
            name: '_finance',
            isOwn: true,
            value: financeNull
              ? { type: 'object', subtype: 'null', value: null }
              : { type: 'object', className: financeClass, objectId: '{"injectedScriptId":1,"id":705}' },
          };
          const finProps = [instrDesc, finDesc];
          if (duplicateFinanceField) {
            finProps.push({ ...instrDesc });
          }
          return { result: { result: finProps } };
        }
        throw new Error(`unexpected Runtime.getProperties objectId: ${params.objectId}`);
      }
      if (method === 'Runtime.releaseObjectGroup') {
        if (releaseFails) {
          throw new Error('simulated Runtime.releaseObjectGroup failure');
        }
        return { result: {} };
      }
      throw new Error(`unexpected CDP method in mock: ${method}`);
    },
  };
}

function buildSyntheticTestBundleSnapshot({
  outFile,
  canaries,
  probe,
  financeCount = 1,
  instructionsState = 'PaymentInstructions',
  instructionsString = null,
  financeState = 'SessionFinance',
  currentUserNull = false,
  includeCanaryChain = false,
  includeProbe = true,
  wrongReceiver = false,
  wrongMethod = false,
  customMethod = null,
}) {
  const pyScript = `
import json, sys
from pathlib import Path
from scripts.bh07_appheap.test_finance_auth_listener_graph import SyntheticV8SnapshotBuilder

cfg = json.loads(sys.argv[1])
b = SyntheticV8SnapshotBuilder()
root = b.add_node('synthetic', '(GC root)', obj_id=1)
gc_roots = b.add_node('synthetic', '(GC roots)', obj_id=3)
b.add_edge(root, 'element', 0, gc_roots)
null_node = b.add_null_node()

auth = b.add_node('object', 'AuthProvider', obj_id=100)
b.add_edge(gc_roots, 'element', 10, auth)
if cfg['current_user_null']:
    b.add_edge(auth, 'property', '_currentUser', null_node)
else:
    b.add_edge(auth, 'property', '_currentUser', b.add_node('object', 'User'))
b.add_edge(auth, 'property', 'ChangeNotifier__count', b.add_number_node())
b.add_edge(auth, 'property', 'ChangeNotifier__notificationCallStackDepth', b.add_number_node())
b.add_edge(auth, 'property', 'ChangeNotifier__reentrantlyRemovedListeners', b.add_number_node())

fin_nodes = []
for idx in range(cfg['finance_count']):
    f = b.add_node('object', 'FinanceProvider', obj_id=200 + idx * 2)
    if cfg['include_canary_chain'] and idx == 0:
        scope = b.add_node('object', '_InheritedProviderScopeElement')
        b.add_edge(gc_roots, 'element', 20 + idx, scope)
        deleg = b.add_node('object', '_CreateInheritedProviderState')
        b.add_edge(scope, 'property', '___InheritedProviderScopeElement__delega', deleg)
        b.add_edge(deleg, 'property', '_provider$_value', f)
    else:
        b.add_edge(gc_roots, 'element', 20 + idx, f)
    b.add_edge(f, 'property', 'auth', auth)
    if cfg.get('instructions_string') is not None:
        b.add_edge(f, 'property', '_instructions', b.add_node('string', cfg['instructions_string']))
    elif cfg['instructions_state'] == 'null':
        b.add_edge(f, 'property', '_instructions', null_node)
    else:
        pi = b.add_node('object', cfg['instructions_state'])
        b.add_edge(f, 'property', '_instructions', pi)
        if cfg['include_canary_chain']:
            rs = b.add_node('object', '_LinkedHashMap')
            b.add_edge(pi, 'property', 'receiverSnapshot', rs)
            mstrings = b.add_node('object', '_LinkedHashMapCell')
            b.add_edge(rs, 'property', '_strings', mstrings)
            for cname, cval in cfg['canaries'].items():
                cell = b.add_node('object', '_LinkedHashMapCell')
                s = b.add_node('string', cval)
                b.add_edge(mstrings, 'property', cname, cell)
                b.add_edge(cell, 'property', 'hashMapCellValue', s)
    if cfg['finance_state'] == 'null':
        b.add_edge(f, 'property', '_finance', null_node)
    else:
        b.add_edge(f, 'property', '_finance', b.add_node('object', cfg['finance_state']))
    fin_nodes.append(f)

if cfg['include_probe'] and cfg.get('probe'):
    pnode = b.add_node('string', cfg['probe'])
    b.add_edge(gc_roots, 'element', 60, pnode)

arr = b.add_node('object', 'Array')
b.add_edge(auth, 'property', 'ChangeNotifier__listeners', arr)
bc_proto = b.add_node('object', 'BoundClosure')

slots = [
    ('markNeedsNotifyDependents$0', None),
]
if cfg['finance_count'] > 0:
    mname = cfg.get('custom_method') or ('wrongMethod$0' if cfg['wrong_method'] else '_onAuthChanged$0')
    slots.append((
        mname,
        'wrong' if cfg['wrong_receiver'] else 'fin0',
    ))

for idx, (mname, recv_kind) in enumerate(slots):
    to = b.add_node('object', 'tear_off')
    gp = b.add_node('object', 'Object')
    b.add_edge(gp, 'property', '__proto__', bc_proto)
    b.add_edge(gp, 'property', '$_name', b.add_node('string', mname))
    b.add_edge(to, 'property', '__proto__', gp)
    if recv_kind == 'fin0':
        b.add_edge(to, 'property', '_receiver', fin_nodes[0])
    elif recv_kind == 'wrong':
        wnode = b.add_node('object', 'SessionProvider', obj_id=998)
        b.add_edge(gc_roots, 'element', 80, wnode)
        b.add_edge(to, 'property', '_receiver', wnode)
    else:
        unode = b.add_node('object', '_InheritedProviderScopeElement')
        b.add_edge(gc_roots, 'element', 81, unode)
        b.add_edge(to, 'property', '_receiver', unode)
    b.add_edge(arr, 'element', idx, to)

Path(cfg['out_file']).write_bytes(b.build_bytes())
`;
  const payload = JSON.stringify({
    out_file: outFile,
    canaries,
    probe,
    finance_count: financeCount,
    instructions_state: instructionsState,
    instructions_string: instructionsString,
    finance_state: financeState,
    current_user_null: currentUserNull,
    include_canary_chain: includeCanaryChain,
    include_probe: includeProbe,
    wrong_receiver: wrongReceiver,
    wrong_method: wrongMethod,
    custom_method: customMethod,
  });
  execFileSync(PY, ['-X', 'utf8', '-c', pyScript, payload], { cwd: ROOT, stdio: 'pipe' });
}

function makeSyntheticMainJs({ includeRegistration = true } = {}) {
  const pyScript = `
import sys
from scripts.bh07_appheap.test_finance_auth_listener_graph import make_synthetic_listener_main_js
sys.stdout.write(make_synthetic_listener_main_js(include_registration=(sys.argv[1] == '1')))
`;
  return execFileSync(PY, ['-X', 'utf8', '-c', pyScript, includeRegistration ? '1' : '0'], {
    cwd: ROOT,
    encoding: 'utf8',
    stdio: ['ignore', 'pipe', 'pipe'],
  });
}

function makeActualShapeMainJs({ factoryReceiverReplaced = false } = {}) {
  const pyScript = `
import sys
from scripts.bh07_appheap.test_finance_auth_listener_graph import TestFinanceAuthListenerBinding
sys.stdout.write(TestFinanceAuthListenerBinding.make_actual_shape_listener_main_js(
    factory_receiver_replaced=(sys.argv[1] == '1'),
))
`;
  return execFileSync(PY, ['-X', 'utf8', '-c', pyScript, factoryReceiverReplaced ? '1' : '0'], {
    cwd: ROOT,
    encoding: 'utf8',
    stdio: ['ignore', 'pipe', 'pipe'],
  });
}

function buildMockRunSetup(tmpRoot, { epochMutator = null, throwCaptureAt = null, dbCleanupFails = false } = {}) {
  const buildDir = path.join(tmpRoot, 'build_web');
  fs.mkdirSync(buildDir, { recursive: true });
  const jsText = makeSyntheticMainJs({ includeRegistration: true });
  fs.writeFileSync(path.join(buildDir, 'main.dart.js'), jsText, 'utf8');
  const mainSha = sha256Hex(Buffer.from(jsText, 'utf8'));

  const dumpsDir = path.join(tmpRoot, 'private_dumps');
  const statePath = path.join(tmpRoot, 'private_fixture_state.json');
  const outDir = path.join(tmpRoot, 'evidence_out');
  const cfgPath = path.join(tmpRoot, 'private_cfg.json');

  const canaries = {
    canary_instr_a: '11111111-2222-4333-8444-555555555555',
    canary_instr_b: 'aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee',
  };
  const cfg = {
    web_url: 'http://127.0.0.1:8088',
    build_dir: buildDir,
    dumps_dir: dumpsDir,
    state_path: statePath,
    reuse_existing_server: true,
    max_snapshot_bytes: 32 * 1024 * 1024,
    owner_email: 'ownera@example.test',
    owner_password: 'OwnerTestPassword!1',
    cohost_email: 'cohosta@example.test',
    cohost_password: 'CohostTestPassword!2',
    member_email: 'membera@example.test',
    member_password: 'MemberTestPassword!3',
    supabase_url: 'https://example.supabase.co',
    supabase_anon_key: 'anon-test-key-value',
  };
  fs.writeFileSync(cfgPath, JSON.stringify(cfg), 'utf8');

  let currentProbe = null;
  let activeEpochKey = null;
  let activeCycleNum = null;
  let epochCdpInstance = null;
  let snapshotStreams = 0;

  const createEpochCdp = () => {
    const key = `c${activeCycleNum}_${activeEpochKey}`;
    if (epochMutator && epochMutator[key] && epochMutator[key].cdpOpts) {
      return makeMockCdp(epochMutator[key].cdpOpts);
    }
    if (activeEpochKey === 'baseline') {
      return activeCycleNum === 1
        ? makeMockCdp({ authCount: 1, currentUserNull: true, instructionsNull: true, financeNull: true })
        : makeMockCdp({ authCount: 2, currentUserNull: true, instructionsNull: true, financeNull: true });
    }
    if (activeEpochKey === 'post_logout') {
      return makeMockCdp({ authCount: 2, currentUserNull: true, instructionsNull: true, financeNull: true });
    }
    return makeMockCdp({ authCount: 2, currentUserNull: false, instructionsNull: false, financeNull: false });
  };

  const cdpProxy = {
    async send(method, params) {
      if (!epochCdpInstance) epochCdpInstance = createEpochCdp();
      return epochCdpInstance.send(method, params);
    },
    async close() {},
  };

  const userHooks = {
    buildDir,
    getGitProvenance: () => ({ tested_source_sha: 'a'.repeat(40), git_dirty: false }),
    prepareBuild: async () => ({
      mode: 'profile',
      reused: true,
      explicit_provenance_verified: true,
      started_at: new Date().toISOString(),
      artifacts_root: 'build/web',
      artifacts: {
        'main.dart.js': mainSha,
        'index.html': sha256Hex('<html></html>'),
        'flutter_bootstrap.js': sha256Hex(''),
      },
      served_match: true,
    }),
    createFixture: () => {
      fs.writeFileSync(
        statePath,
        JSON.stringify({ sentinel_1: canaries.canary_instr_a, sentinel_2: canaries.canary_instr_b }),
        'utf8',
      );
      return {
        session_title: 'BH07-Disposable-Session',
        disposable_instructions_club_created: true,
        disposable_instructions_session_created: true,
      };
    },
    startSession: async () => ({ cdp: cdpProxy, browser: null, ownServer: null }),
    waitForStartupReady: async () => {},
    measureTimeOrigin: async () => 12345.6,
    performEpochAction: async ({ step, epName, probeValue }) => {
      activeCycleNum = step.cycle;
      activeEpochKey = epName;
      currentProbe = probeValue;
      epochCdpInstance = createEpochCdp();
    },
    checkFixtureZeroMutations: () => ({ ok: true, counts: {} }),
    cleanupFixture: () => {
      if (dbCleanupFails) {
        throw new Error('simulated DB cleanup timeout');
      }
      return {
        disposable_instructions_club_created: true,
        disposable_instructions_session_created: true,
        disposable_instructions_removed: true,
        disposable_instructions_verified_absent: true,
        disposable_instructions_cleanup_verified: true,
        zero_mutation_verified: true,
        baseline_fingerprint_equal: true,
        public_rows_schema_roles_equal: true,
        auth_rows_excluded: true,
      };
    },
    shutdownBrowser: async () => ({ exited: true, profileRemoved: true, error: null }),
    streamSnapshotToFile: async ({ outFile, maxBytes }) => {
      snapshotStreams += 1;
      assert.ok(maxBytes > 0);
      const key = `c${activeCycleNum}_${activeEpochKey}`;
      if (throwCaptureAt === key) {
        fs.writeFileSync(outFile, '{"truncated":true', 'utf8');
        throw new Error(`simulated capture failure at ${key}`);
      }
      const override = (epochMutator && epochMutator[key] && epochMutator[key].snapOpts) || {};
      let defaults;
      if (activeEpochKey === 'baseline') {
        defaults = activeCycleNum === 1
          ? { financeCount: 0, instructionsState: 'null', financeState: 'null', currentUserNull: true, includeCanaryChain: false }
          : { financeCount: 1, instructionsState: 'null', financeState: 'null', currentUserNull: true, includeCanaryChain: false };
      } else if (activeEpochKey === 'owner_active') {
        defaults = { financeCount: 1, instructionsState: 'PaymentInstructions', financeState: 'SessionFinance', currentUserNull: false, includeCanaryChain: true };
      } else if (activeEpochKey === 'post_logout') {
        defaults = { financeCount: 1, instructionsState: 'null', financeState: 'null', currentUserNull: true, includeCanaryChain: false };
      } else {
        // post_actor: allow non-null legitimate actor refetch without failing gate
        defaults = { financeCount: 1, instructionsState: 'PaymentInstructions', financeState: 'SessionFinance', currentUserNull: false, includeCanaryChain: false };
      }
      buildSyntheticTestBundleSnapshot({
        outFile,
        canaries,
        probe: currentProbe,
        ...defaults,
        ...override,
      });
    },
  };

  return {
    cfg,
    cfgPath,
    outDir,
    buildDir,
    dumpsDir,
    statePath,
    canaries,
    userHooks,
    getSnapshotStreams: () => snapshotStreams,
  };
}

async function testObserveListenerScalarsAndFields() {
  const canarySecret = '99999999-8888-4777-8666-555555555555';
  const goodCdp = makeMockCdp({ secretCanary: canarySecret });
  const obs = await RUNNER_MOD.observeListenerScalarsAndFields({
    cdp: goodCdp,
    authHeapObjectId: '100',
    financeHeapObjectId: '200',
    instructionsField: '_instructions',
    financeField: '_finance',
  });
  assert.equal(obs.observation_mode, 'hybrid_snapshot_plus_readonly_cdp_own_properties');
  assert.equal(obs.atomic_claim, false);
  assert.equal(obs.object_group_released, true);
  assert.equal(obs.before.ChangeNotifier__count, 2);
  assert.equal(obs.after.ChangeNotifier__count, 2);
  assert.equal(obs.counters_match, true);
  assert.equal(obs.quiescent, true);
  assert.equal(obs.finance_selected_fields._instructions.class_name, 'PaymentInstructions');
  assert.equal(obs.finance_selected_fields._instructions.is_null, false);
  assert.equal(obs.finance_selected_fields._finance.class_name, 'SessionFinance');

  const serialized = JSON.stringify(obs);
  assert.ok(!serialized.includes('injectedScriptId'), 'must never persist raw CDP objectId handles');
  assert.ok(!serialized.includes(canarySecret), 'must never persist canary or DTO description strings');
  assert.equal(
    goodCdp.calls.filter((c) => c.method === 'Runtime.releaseObjectGroup').length,
    1,
    'must release object group once in finally',
  );

  // Release failure MUST throw even when all prior reads succeeded
  const releaseFailCdp = makeMockCdp({ releaseFails: true });
  await assert.rejects(
    () => RUNNER_MOD.observeListenerScalarsAndFields({
      cdp: releaseFailCdp,
      authHeapObjectId: '100',
      financeHeapObjectId: '200',
      instructionsField: '_instructions',
      financeField: '_finance',
    }),
    /releaseObjectGroup/,
  );

  // Read failure MUST still execute Runtime.releaseObjectGroup in finally
  const readFailCdp = makeMockCdp({ readThrows: true });
  await assert.rejects(
    () => RUNNER_MOD.observeListenerScalarsAndFields({
      cdp: readFailCdp,
      authHeapObjectId: '100',
      financeHeapObjectId: '200',
      instructionsField: '_instructions',
      financeField: '_finance',
    }),
    /getObjectByHeapObjectId/,
  );
  assert.equal(
    readFailCdp.calls.filter((c) => c.method === 'Runtime.releaseObjectGroup').length,
    1,
    'must attempt Runtime.releaseObjectGroup in finally even after read failure',
  );

  // Getter/accessor descriptor MUST be flagged/rejected without evaluation
  const getterCdp = makeMockCdp({ instructionsIsGetter: true });
  const getterObs = await RUNNER_MOD.observeListenerScalarsAndFields({
    cdp: getterCdp,
    authHeapObjectId: '100',
    financeHeapObjectId: '200',
    instructionsField: '_instructions',
    financeField: '_finance',
  });
  assert.equal(getterObs.finance_selected_fields._instructions.has_getter, true);
  assert.equal(
    getterCdp.calls.filter((c) => c.method === 'Runtime.evaluate').length,
    2,
    'only performance.timeOrigin calls allowed; must never evaluate getters',
  );

  // Missing / non-int / unsafe-int Auth counter must surface fail-closed violation
  for (const [label, opts] of [
    ['missingAuthCounter', { missingAuthCounter: true }],
    ['nonIntAuthCounter', { nonIntAuthCounter: true }],
    ['unsafeIntAuthCounter', { unsafeIntAuthCounter: true }],
    ['duplicateAuthCounter', { duplicateAuthCounter: true }],
  ]) {
    const badObs = await RUNNER_MOD.observeListenerScalarsAndFields({
      cdp: makeMockCdp(opts),
      authHeapObjectId: '100',
      financeHeapObjectId: '200',
      instructionsField: '_instructions',
      financeField: '_finance',
    });
    assert.equal(badObs.before.ChangeNotifier__count, null, label);
    assert.ok(badObs.cdp_errors.length > 0, label);
    assert.equal(badObs.counters_match, false, label);
  }

  // FL1: Old wrong wire shape { result: { object: ... } } MUST reject, AND releaseObjectGroup in finally!
  const legacyWireCdp = makeMockCdp({ legacyObjectWireShape: true });
  await assert.rejects(
    () => RUNNER_MOD.observeListenerScalarsAndFields({
      cdp: legacyWireCdp,
      authHeapObjectId: '100',
      financeHeapObjectId: '200',
      instructionsField: '_instructions',
      financeField: '_finance',
    }),
    /HeapProfiler\.getObjectByHeapObjectId/,
  );
  assert.equal(
    legacyWireCdp.calls.filter((c) => c.method === 'Runtime.releaseObjectGroup').length,
    1,
    'must release object group even when legacy wrong wire shape rejects',
  );

  // FL1: Wrong RemoteObject className or type MUST reject!
  for (const [label, opts] of [
    ['wrongAuthClass', { authRemoteClass: 'SessionProvider' }],
    ['wrongAuthType', { authRemoteType: 'string' }],
    ['wrongFinanceClass', { financeRemoteClass: 'SessionProvider' }],
    ['wrongFinanceType', { financeRemoteType: 'undefined' }],
  ]) {
    const badRemoteCdp = makeMockCdp(opts);
    await assert.rejects(
      () => RUNNER_MOD.observeListenerScalarsAndFields({
        cdp: badRemoteCdp,
        authHeapObjectId: '100',
        financeHeapObjectId: '200',
        instructionsField: '_instructions',
        financeField: '_finance',
      }),
      /HeapProfiler\.getObjectByHeapObjectId/,
      label,
    );
    assert.equal(
      badRemoteCdp.calls.filter((c) => c.method === 'Runtime.releaseObjectGroup').length,
      1,
      label,
    );
  }

  // FL3: auth_current_user shape (present/value_type/class_name/is_null), missing/dup _currentUser, before/after drift, invalid timeOrigin
  assert.equal(obs.auth_current_user.present, true);
  assert.equal(obs.auth_current_user.has_getter, false);
  assert.equal(obs.auth_current_user.value_type, 'object');
  assert.equal(obs.auth_current_user.class_name, 'User');
  assert.equal(obs.auth_current_user.is_null, false);
  assert.deepEqual(obs.auth_current_user_before, obs.auth_current_user);
  assert.deepEqual(obs.auth_current_user_after, obs.auth_current_user);

  const missingUserObs = await RUNNER_MOD.observeListenerScalarsAndFields({
    cdp: makeMockCdp({ missingCurrentUser: true }),
    authHeapObjectId: '100',
    financeHeapObjectId: '200',
    instructionsField: '_instructions',
    financeField: '_finance',
  });
  assert.equal(missingUserObs.auth_current_user.present, false);
  assert.ok(missingUserObs.cdp_errors.some((e) => e.includes('missing__currentUser')));

  const dupUserObs = await RUNNER_MOD.observeListenerScalarsAndFields({
    cdp: makeMockCdp({ duplicateCurrentUser: true }),
    authHeapObjectId: '100',
    financeHeapObjectId: '200',
    instructionsField: '_instructions',
    financeField: '_finance',
  });
  assert.ok(dupUserObs.cdp_errors.some((e) => e.includes('duplicate__currentUser')));

  const dupFinObs = await RUNNER_MOD.observeListenerScalarsAndFields({
    cdp: makeMockCdp({ duplicateFinanceField: true }),
    authHeapObjectId: '100',
    financeHeapObjectId: '200',
    instructionsField: '_instructions',
    financeField: '_finance',
  });
  assert.ok(dupFinObs.cdp_errors.some((e) => e.includes('finance_duplicate__instructions')));

  const driftUserObs = await RUNNER_MOD.observeListenerScalarsAndFields({
    cdp: makeMockCdp({ currentUserNull: false, afterCurrentUserNull: true }),
    authHeapObjectId: '100',
    financeHeapObjectId: '200',
    instructionsField: '_instructions',
    financeField: '_finance',
  });
  assert.ok(driftUserObs.cdp_errors.includes('auth_current_user_before_after_mismatch'));

  const badOriginObs = await RUNNER_MOD.observeListenerScalarsAndFields({
    cdp: makeMockCdp({ timeOriginBefore: 12345.6, timeOriginAfter: 99999.0 }),
    authHeapObjectId: '100',
    financeHeapObjectId: '200',
    instructionsField: '_instructions',
    financeField: '_finance',
  });
  assert.ok(badOriginObs.cdp_errors.some((e) => e.includes('time_origin')));

  // FL4: CDP string/unknown className never leaks raw value or unexpected className
  const privateMarker = 'BANK_SECRET_VAL_77889900';
  const strInstrObs = await RUNNER_MOD.observeListenerScalarsAndFields({
    cdp: makeMockCdp({ instructionsType: 'string', secretCanary: privateMarker }),
    authHeapObjectId: '100',
    financeHeapObjectId: '200',
    instructionsField: '_instructions',
    financeField: '_finance',
  });
  assert.equal(strInstrObs.finance_selected_fields._instructions.value_type, 'string');
  assert.equal(strInstrObs.finance_selected_fields._instructions.class_name, null);
  assert.equal(strInstrObs.finance_selected_fields._instructions.is_null, false);
  assert.ok(!JSON.stringify(strInstrObs).includes(privateMarker));
  assert.ok(!JSON.stringify(strInstrObs).includes('77889900'));
}

async function testExtractListenerBinding() {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'bh07_listener_bind_'));
  try {
    const jsOk = makeSyntheticMainJs({ includeRegistration: true });
    fs.writeFileSync(path.join(tmp, 'main.dart.js'), jsOk, 'utf8');
    const shaOk = sha256Hex(Buffer.from(jsOk, 'utf8'));

    const resOk = RUNNER_MOD.extractListenerBinding({ buildDir: tmp, expectedMainJsSha: shaOk });
    assert.equal(resOk.ok, true);
    assert.equal(resOk.finance_provider.registration_method, '_onAuthChanged$0');

    const resBadSha = RUNNER_MOD.extractListenerBinding({ buildDir: tmp, expectedMainJsSha: '0'.repeat(64) });
    assert.equal(resBadSha.ok, false);

    const jsNoReg = makeSyntheticMainJs({ includeRegistration: false });
    fs.writeFileSync(path.join(tmp, 'main.dart.js'), jsNoReg, 'utf8');
    const shaNoReg = sha256Hex(Buffer.from(jsNoReg, 'utf8'));
    const resNoReg = RUNNER_MOD.extractListenerBinding({ buildDir: tmp, expectedMainJsSha: shaNoReg });
    assert.equal(resNoReg.ok, false);

    const jsActualOk = makeActualShapeMainJs({ factoryReceiverReplaced: false });
    fs.writeFileSync(path.join(tmp, 'main.dart.js'), jsActualOk, 'utf8');
    const shaActualOk = sha256Hex(Buffer.from(jsActualOk, 'utf8'));
    const resActualOk = RUNNER_MOD.extractListenerBinding({ buildDir: tmp, expectedMainJsSha: shaActualOk });
    assert.equal(resActualOk.ok, true);
    assert.equal(resActualOk.finance_provider.finance_field, '_finance');
    assert.equal(resActualOk.finance_provider.registration_method, '_onAuthChanged$0');

    const jsActualBad = makeActualShapeMainJs({ factoryReceiverReplaced: true });
    fs.writeFileSync(path.join(tmp, 'main.dart.js'), jsActualBad, 'utf8');
    const shaActualBad = sha256Hex(Buffer.from(jsActualBad, 'utf8'));
    const resActualBad = RUNNER_MOD.extractListenerBinding({ buildDir: tmp, expectedMainJsSha: shaActualBad });
    assert.equal(resActualBad.ok, false);
  } finally {
    fs.rmSync(tmp, { recursive: true, force: true });
  }
}

async function testMockedTwoCycleRuns() {
  // 1. Valid 2-cycle run -> PASS, single snapshot per epoch, verify exits 0
  const okTmp = fs.mkdtempSync(path.join(os.tmpdir(), 'bh07_listener_ok_'));
  try {
    const setup = buildMockRunSetup(okTmp);
    const { summary, exitCode } = await RUNNER_MOD.runFinanceAuthListener({
      cfg: setup.cfg,
      cfgPath: setup.cfgPath,
      outDir: setup.outDir,
      userHooks: setup.userHooks,
    });
    assert.equal(exitCode, 0);
    assert.equal(summary.status, 'RUN');
    assert.equal(summary.verdict, 'PASS');
    assert.equal(setup.getSnapshotStreams(), 8, 'must capture exactly 1 snapshot per epoch (8 total)');
    assert.equal(summary.cycles[0].epochs.baseline.listener_graph.verdict, 'NOT_RUN_LAZY');
    assert.equal(summary.cycles[0].epochs.owner_active.listener_graph.verdict, 'PASS');
    assert.equal(summary.cycles[0].epochs.post_logout.listener_graph.verdict, 'PASS');
    assert.equal(summary.cycles[0].epochs.post_actor.listener_graph.verdict, 'PASS');
    assert.equal(summary.cycles[1].epochs.baseline.listener_graph.verdict, 'PASS');
    assert.equal(summary.listener_graph_assessment.listener_graph_gate, 'PASS');
    assert.ok(!fs.existsSync(setup.dumpsDir), 'private dumpsDir must be cleaned up');
    assert.ok(!fs.existsSync(setup.statePath), 'fixture state file must be unlinked when DB cleanup succeeded');

    let verifyOut;
    try {
      verifyOut = execFileSync(
        PY,
        ['-X', 'utf8', LISTENER_GRAPH_PY, 'verify', setup.outDir, '--build-dir', setup.buildDir],
        { cwd: ROOT, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] },
      );
    } catch (verErr) {
      throw new Error(`verify failed: ${verErr.stdout || ''} ${verErr.stderr || verErr.message}`);
    }
    const parsedVerify = JSON.parse(verifyOut);
    assert.equal(parsedVerify.ok, true);
    assert.equal(parsedVerify.assessment.listener_graph_gate, 'PASS');
  } finally {
    fs.rmSync(okTmp, { recursive: true, force: true });
  }

  // 2. Invalid owner_active (wrong receiver) -> hook throws, partial c1.baseline AND failed c1.owner_active preserved, temp dumps deleted, exit 1
  const ownerFailTmp = fs.mkdtempSync(path.join(os.tmpdir(), 'bh07_listener_owner_fail_'));
  try {
    const setup = buildMockRunSetup(ownerFailTmp, {
      epochMutator: { c1_owner_active: { snapOpts: { wrongReceiver: true } } },
    });
    const { summary, exitCode } = await RUNNER_MOD.runFinanceAuthListener({
      cfg: setup.cfg,
      cfgPath: setup.cfgPath,
      outDir: setup.outDir,
      userHooks: setup.userHooks,
    });
    assert.equal(exitCode, 1);
    assert.equal(summary.verdict, 'FAIL');
    assert.equal(summary.failure.epoch, 'owner_active');
    assert.ok(summary.cycles[0].epochs.baseline.listener_graph, 'partial epoch c1.baseline must be preserved');
    assert.ok(summary.cycles[0].epochs.owner_active, 'failed current epoch c1.owner_active must be preserved');
    assert.ok(summary.cycles[0].epochs.owner_active.listener_graph, 'failed current epoch listener_graph must be preserved');
    assert.equal(summary.cycles[0].epochs.owner_active.listener_graph.verdict, 'FAIL');
    assert.equal(summary.cycles[0].epochs.owner_active.time_origin, 12345.6);
    assert.equal(summary.cycles[0].verdict.verdict, 'FAIL');
    assert.equal(summary.cycles[0].verdict.incomplete, true);
    assert.equal(summary.listener_graph_assessment.listener_graph_gate, 'FAIL');

    const diskSummary = JSON.parse(fs.readFileSync(path.join(setup.outDir, 'summary.json'), 'utf8'));
    assert.equal(diskSummary.cycles[0].epochs.owner_active.listener_graph.verdict, 'FAIL');
    const manifestLines = fs.readFileSync(path.join(setup.outDir, 'hashes.sha256'), 'utf8').trim().split(/\r?\n/);
    for (const line of manifestLines) {
      const [hex, fname] = line.split(/\s+/);
      assert.equal(sha256Hex(fs.readFileSync(path.join(setup.outDir, fname))), hex, `hash mismatch for ${fname}`);
    }

    assert.ok(!fs.existsSync(setup.dumpsDir), 'private dumpsDir must be removed on owner_active failure');
    assert.throws(
      () => execFileSync(PY, ['-X', 'utf8', LISTENER_GRAPH_PY, 'verify', setup.outDir, '--build-dir', setup.buildDir], { cwd: ROOT, stdio: 'pipe' }),
    );
  } finally {
    fs.rmSync(ownerFailTmp, { recursive: true, force: true });
  }

  // 3. Invalid post_logout (stale non-null _finance) -> hook throws, partial epochs AND failed post_logout kept, exit 1
  const logoutFailTmp = fs.mkdtempSync(path.join(os.tmpdir(), 'bh07_listener_logout_fail_'));
  try {
    const setup = buildMockRunSetup(logoutFailTmp, {
      epochMutator: {
        c1_post_logout: {
          snapOpts: { financeState: 'SessionFinance' },
          cdpOpts: { authCount: 2, currentUserNull: true, instructionsNull: true, financeNull: false },
        },
      },
    });
    const { summary, exitCode } = await RUNNER_MOD.runFinanceAuthListener({
      cfg: setup.cfg,
      cfgPath: setup.cfgPath,
      outDir: setup.outDir,
      userHooks: setup.userHooks,
    });
    assert.equal(exitCode, 1);
    assert.equal(summary.verdict, 'FAIL');
    assert.equal(summary.failure.epoch, 'post_logout');
    assert.ok(summary.cycles[0].epochs.baseline.listener_graph);
    assert.ok(summary.cycles[0].epochs.owner_active.listener_graph);
    assert.ok(summary.cycles[0].epochs.post_logout.listener_graph, 'failed c1.post_logout listener_graph must be preserved');
    assert.equal(summary.cycles[0].epochs.post_logout.listener_graph.verdict, 'FAIL');
    assert.equal(summary.cycles[0].verdict.verdict, 'FAIL');
  } finally {
    fs.rmSync(logoutFailTmp, { recursive: true, force: true });
  }

  // 4. CDP counter race on c2_owner_active -> hook throws, cycle 1 preserved AND failed c2_owner_active preserved, exit 1
  const raceTmp = fs.mkdtempSync(path.join(os.tmpdir(), 'bh07_listener_race_'));
  try {
    const setup = buildMockRunSetup(raceTmp, {
      epochMutator: {
        c2_owner_active: {
          cdpOpts: { authCount: 2, authAfterCount: 3, currentUserNull: false, instructionsNull: false, financeNull: false },
        },
      },
    });
    const { summary, exitCode } = await RUNNER_MOD.runFinanceAuthListener({
      cfg: setup.cfg,
      cfgPath: setup.cfgPath,
      outDir: setup.outDir,
      userHooks: setup.userHooks,
    });
    assert.equal(exitCode, 1);
    assert.equal(summary.verdict, 'FAIL');
    assert.equal(summary.failure.cycle, 2);
    assert.equal(summary.failure.epoch, 'owner_active');
    assert.equal(summary.cycles[0].verdict.verdict, 'PASS');
    assert.ok(summary.cycles[1].epochs.owner_active.listener_graph, 'failed c2.owner_active listener_graph must be preserved');
    assert.equal(summary.cycles[1].epochs.owner_active.listener_graph.verdict, 'FAIL');
    assert.equal(summary.cycles[1].verdict.verdict, 'FAIL');
  } finally {
    fs.rmSync(raceTmp, { recursive: true, force: true });
  }

  // 5. FL4 end-to-end: unexpected private strings in snapshot & CDP NEVER appear in summary.json/report.md/run.log FAIL bundle
  const leakTmp = fs.mkdtempSync(path.join(os.tmpdir(), 'bh07_listener_fl4_e2e_'));
  try {
    const privStr = 'BANK_ACCT_PRIVATE_5544332211';
    const privMethod = 'PROTO_SECRET_METHOD_66778899';
    const setup = buildMockRunSetup(leakTmp, {
      epochMutator: {
        c1_owner_active: {
          snapOpts: {
            instructionsString: privStr,
            customMethod: privMethod,
            includeCanaryChain: false,
          },
          cdpOpts: {
            authCount: 2,
            currentUserNull: false,
            instructionsType: 'string',
            secretCanary: privStr,
            financeNull: false,
          },
        },
      },
    });
    const { summary, exitCode } = await RUNNER_MOD.runFinanceAuthListener({
      cfg: setup.cfg,
      cfgPath: setup.cfgPath,
      outDir: setup.outDir,
      userHooks: setup.userHooks,
    });
    assert.equal(exitCode, 1);
    assert.equal(summary.verdict, 'FAIL');
    assert.ok(summary.cycles[0].epochs.owner_active.listener_graph, 'failed FL4 epoch diagnostic must be preserved');
    const bundleFiles = ['summary.json', 'report.md', 'run.log'].map((f) => fs.readFileSync(path.join(setup.outDir, f), 'utf8'));
    for (const marker of [privStr, '5544332211', privMethod, '66778899']) {
      for (const content of bundleFiles) {
        assert.ok(!content.includes(marker), `FAIL bundle leaked unexpected private marker ${marker}`);
      }
    }
  } finally {
    fs.rmSync(leakTmp, { recursive: true, force: true });
  }

  // 6. Capture failure + DB cleanup failure -> private heap dumps removed, recovery statePath preserved!
  const cleanFailTmp = fs.mkdtempSync(path.join(os.tmpdir(), 'bh07_listener_cleanup_fail_'));
  try {
    const setup = buildMockRunSetup(cleanFailTmp, {
      throwCaptureAt: 'c1_owner_active',
      dbCleanupFails: true,
    });
    const { summary, exitCode } = await RUNNER_MOD.runFinanceAuthListener({
      cfg: setup.cfg,
      cfgPath: setup.cfgPath,
      outDir: setup.outDir,
      userHooks: setup.userHooks,
    });
    assert.equal(exitCode, 1);
    assert.equal(summary.verdict, 'FAIL');
    assert.ok(!fs.existsSync(setup.dumpsDir), 'private heap dumps dir MUST be removed even on DB cleanup failure');
    assert.equal(summary.cleanup.dumps_dir_removed, true);
    assert.ok(fs.existsSync(setup.statePath), 'original fixture recovery statePath MUST be preserved on DB cleanup failure');
    assert.equal(summary.cleanup.recovery_state_retained, true);
  } finally {
    fs.rmSync(cleanFailTmp, { recursive: true, force: true });
  }
}

async function main() {
  await testObserveListenerScalarsAndFields();
  await testExtractListenerBinding();
  await testMockedTwoCycleRuns();
  console.log('ALL_FINANCE_AUTH_LISTENER_CONTROLS_PASS');
}

main().catch((err) => {
  console.error(err && err.stack ? err.stack : String(err));
  process.exit(1);
});
