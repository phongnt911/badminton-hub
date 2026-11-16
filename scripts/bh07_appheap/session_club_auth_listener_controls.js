'use strict';

// Node unit & mocked 2-cycle/8-epoch RED->GREEN controls for run_session_club_auth_listener.js
// and session_club_auth_listener_graph.py CLI integration.

const assert = require('node:assert/strict');
const { execFileSync } = require('node:child_process');
const crypto = require('node:crypto');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const PY = process.env.PYTHON || 'python';
const SC_GRAPH_PY = path.join(__dirname, 'session_club_auth_listener_graph.py');
const SC_RUNNER = require('./run_session_club_auth_listener.js');

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
  sessionPresent = true,
  clubPresent = true,
  sessionIdNull = false,
  currentSessionNull = false,
  historyNull = false,
  clubIdNull = false,
  currentClubNull = false,
  bankNull = false,
  sessionGetter = false,
  clubGetter = false,
  duplicateClubField = false,
  nonIntCounter = false,
  unsafeIntCounter = false,
  timeOriginBefore = 12345.6,
  timeOriginAfter = 12345.6,
  secretMarker = null,
  legacyObjectWireShape = false,
  readThrows = false,
  releaseFails = false,
  authClass = 'AuthProvider',
  sessionClass = 'SessionProvider',
  clubClass = 'ClubProvider',
} = {}) {
  const calls = [];
  let authReadNum = 0;
  let evalNum = 0;
  const authObjId = '{"injectedScriptId":1,"id":701}';
  const spObjId = '{"injectedScriptId":1,"id":702}';
  const cpObjId = '{"injectedScriptId":1,"id":703}';

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
        const mapObj = {
          '100': { objectId: authObjId, type: 'object', className: authClass },
          '200': sessionPresent ? { objectId: spObjId, type: 'object', className: sessionClass } : null,
          '300': clubPresent ? { objectId: cpObjId, type: 'object', className: clubClass } : null,
        }[String(params.objectId)] || null;
        if (legacyObjectWireShape) {
          return { result: { object: mapObj } };
        }
        return { result: { result: mapObj } };
      }
      if (method === 'Runtime.getProperties') {
        assert.equal(params.ownProperties, true, 'must inspect ownProperties=true');
        assert.equal(params.generatePreview, false, 'must set generatePreview=false');
        if (params.objectId === authObjId) {
          authReadNum += 1;
          const cnt = authReadNum === 1 ? authCount : authAfterCount;
          const dep = authReadNum === 1 ? depth : afterDepth;
          const rem = authReadNum === 1 ? removed : afterRemoved;
          const uNull = authReadNum === 1 ? currentUserNull : afterCurrentUserNull;
          const cntVal = nonIntCounter
            ? { type: 'string', value: String(cnt) }
            : unsafeIntCounter
              ? { type: 'number', value: 1e21 }
              : { type: 'number', value: cnt };
          return {
            result: {
              result: [
                { name: 'ChangeNotifier__count', isOwn: true, value: cntVal },
                { name: 'ChangeNotifier__notificationCallStackDepth', isOwn: true, value: { type: 'number', value: dep } },
                { name: 'ChangeNotifier__reentrantlyRemovedListeners', isOwn: true, value: { type: 'number', value: rem } },
                {
                  name: '_currentUser',
                  isOwn: true,
                  value: uNull
                    ? { type: 'object', subtype: 'null', value: null }
                    : { type: 'object', className: 'User', objectId: '{"injectedScriptId":1,"id":710}' },
                },
              ],
            },
          };
        }
        if (params.objectId === spObjId) {
          const csDesc = sessionGetter
            ? { name: '_currentSession', isOwn: true, get: { type: 'function', objectId: '{"injectedScriptId":1,"id":799}' } }
            : {
              name: '_currentSession',
              isOwn: true,
              value: currentSessionNull
                ? { type: 'object', subtype: 'null', value: null }
                : { type: 'object', className: 'Session0', objectId: '{"injectedScriptId":1,"id":711}' },
            };
          return {
            result: {
              result: [
                {
                  name: '_currentSessionId',
                  isOwn: true,
                  value: sessionIdNull
                    ? { type: 'object', subtype: 'null', value: null }
                    : { type: 'string', value: secretMarker || 'RAW_SESSION_UUID_123456' },
                },
                csDesc,
                {
                  name: '_session_provider$_history',
                  isOwn: true,
                  value: historyNull
                    ? { type: 'object', subtype: 'null', value: null }
                    : { type: 'object', className: 'SessionHistoryPage', objectId: '{"injectedScriptId":1,"id":712}' },
                },
              ],
            },
          };
        }
        if (params.objectId === cpObjId) {
          const ccDesc = clubGetter
            ? { name: '_currentClub', isOwn: true, get: { type: 'function', objectId: '{"injectedScriptId":1,"id":798}' } }
            : {
              name: '_currentClub',
              isOwn: true,
              value: currentClubNull
                ? { type: 'object', subtype: 'null', value: null }
                : { type: 'object', className: 'Club', objectId: '{"injectedScriptId":1,"id":713}' },
            };
          const props = [
            {
              name: '_currentClubId',
              isOwn: true,
              value: clubIdNull
                ? { type: 'object', subtype: 'null', value: null }
                : { type: 'string', value: secretMarker || 'RAW_CLUB_UUID_654321' },
            },
            ccDesc,
            {
              name: '_currentBankAccount',
              isOwn: true,
              value: bankNull
                ? { type: 'object', subtype: 'null', value: null }
                : { type: 'object', className: 'BankAccount', objectId: '{"injectedScriptId":1,"id":714}' },
            },
          ];
          if (duplicateClubField) {
            props.push({ ...ccDesc });
          }
          return { result: { result: props } };
        }
        throw new Error(`unexpected objectId in mock CDP: ${params.objectId}`);
      }
      if (method === 'Runtime.releaseObjectGroup') {
        if (releaseFails) throw new Error('simulated releaseObjectGroup error');
        return { result: {} };
      }
      throw new Error(`unexpected CDP method: ${method}`);
    },
    async close() {},
  };
}

function makeSyntheticMainJs({ includeSpReg = true, includeBankReset = true } = {}) {
  return [
    'var A = {',
    '  BoundClosure: function BoundClosure(t0, t1) { this._receiver = t0; this._interceptor = t1; },',
    '  AuthProvider: function AuthProvider(t0, t1) {',
    '    var _ = this; _._repository = t0; _._currentUser = null;',
    '    _.ChangeNotifier__count = 0; _.ChangeNotifier__listeners = t1;',
    '    _.ChangeNotifier__reentrantlyRemovedListeners = _.ChangeNotifier__notificationCallStackDepth = 0;',
    '  },',
    '  SessionRepository: function SessionRepository(t0) { this._session_repository$_client = t0; },',
    '  ClubRepository: function ClubRepository(t0) { this._club_repository$_client = t0; },',
    '  SessionProvider: function SessionProvider(t0, t1, t2) {',
    '    var _ = this; _._session_provider$_repository = t0; _.auth = t1;',
    '    _._currentSessionId = _._currentSession = _._session_provider$_history = null;',
    '    _.ChangeNotifier__count = 0; _.ChangeNotifier__listeners = t2;',
    '    _.ChangeNotifier__reentrantlyRemovedListeners = _.ChangeNotifier__notificationCallStackDepth = 0;',
    '  },',
    '  ClubProvider: function ClubProvider(t0, t1, t2) {',
    '    var _ = this; _._club_provider$_repository = t0; _.auth = t1;',
    '    _._currentClubId = _._currentClub = _._currentBankAccount = null;',
    '    _.ChangeNotifier__count = 0; _.ChangeNotifier__listeners = t2;',
    '    _.ChangeNotifier__reentrantlyRemovedListeners = _.ChangeNotifier__notificationCallStackDepth = 0;',
    '  },',
    '  Session0: function Session0(t0, t1) { this.id = t0; this.title = t1; },',
    '  SessionHistoryPage: function SessionHistoryPage(t0) { this.sessions = t0; },',
    '  Club: function Club(t0, t1) { this.id = t0; this.name = t1; },',
    '  BankAccount: function BankAccount(t0, t1) { this.id = t0; this.bankCode = t1; },',
    '  Session_Session$fromJson(j) { return new A.Session0(j.$index(0, "id"), j.$index(0, "title")); },',
    '  SessionHistoryPage_SessionHistoryPage$fromResponse(r, l, o) { return new A.SessionHistoryPage(r); },',
    '  Club_Club$fromJson(j) { return new A.Club(j.$index(0, "id"), j.$index(0, "name")); },',
    '  BankAccount_BankAccount$fromJson(j) { return new A.BankAccount(j.$index(0, "id"), j.$index(0, "bank_code")); },',
    '  Closure_fromTearOff(p) {',
    '    var $prototype = Object.create(new A.BoundClosure(null, null).constructor.prototype);',
    '    var $constructor = function tear_off(a, b) { this.$initialize(a, b); };',
    '    $prototype.constructor = $constructor; $constructor.prototype = $prototype;',
    '    $prototype.$_name = p.fs[0]; return $constructor;',
    '  }',
    '};',
    'A.SessionRepository.prototype = {',
    '  getSessionDetail$1(sessionId) { return this.getSessionDetail$body$SessionRepository(sessionId); },',
    '  getSessionDetail$body$SessionRepository(sessionId) {',
    '    var $async$goto = 0, $async$completer = A._makeAsyncAwaitCompleter(type$.Session), $async$returnValue, $async$self = this, $async$temp1 = A;',
    '    var $async$fn = A._wrapJsFunctionForAsync(function($async$errorCode, $async$result) {',
    '      for (;;) switch ($async$goto) {',
    '        case 0: $async$goto = 3; return A._asyncAwait($async$self._session_repository$_client.rpc$1$2$params("get_session_public_detail", {}, null), $async$fn);',
    '        case 3: $async$returnValue = $async$temp1.Session_Session$fromJson($async$result); $async$goto = 1; break;',
    '        case 1: return A._asyncReturn($async$returnValue, $async$completer);',
    '      }',
    '    });',
    '    return A._asyncStartSync($async$fn, $async$completer);',
    '  },',
    '  listMySessionHistory$3$filter$limit$offset(filter, limit, offset) {',
    '    var $async$goto = 0, $async$completer = A._makeAsyncAwaitCompleter(type$.SessionHistoryPage), $async$returnValue, $async$self = this;',
    '    var $async$fn = A._wrapJsFunctionForAsync(function($async$errorCode, $async$result) {',
    '      for (;;) switch ($async$goto) {',
    '        case 0: $async$goto = 3; return A._asyncAwait($async$self._session_repository$_client.rpc$1$2$params("list_my_session_history", {}, null), $async$fn);',
    '        case 3: $async$returnValue = A.SessionHistoryPage_SessionHistoryPage$fromResponse($async$result, limit, offset); $async$goto = 1; break;',
    '        case 1: return A._asyncReturn($async$returnValue, $async$completer);',
    '      }',
    '    });',
    '    return A._asyncStartSync($async$fn, $async$completer);',
    '  }',
    '};',
    'A.ClubRepository.prototype = {',
    '  getClubDetail$1(clubId) { return this.getClubDetail$body$ClubRepository(clubId); },',
    '  getClubDetail$body$ClubRepository(clubId) {',
    '    var $async$goto = 0, $async$completer = A._makeAsyncAwaitCompleter(type$.Club), $async$returnValue, $async$self = this, $async$temp1 = A;',
    '    var $async$fn = A._wrapJsFunctionForAsync(function($async$errorCode, $async$result) {',
    '      for (;;) switch ($async$goto) {',
    '        case 0: $async$goto = 3; return A._asyncAwait($async$self._club_repository$_client.rpc$1$2$params("get_club_detail", {}, null), $async$fn);',
    '        case 3: $async$returnValue = $async$temp1.Club_Club$fromJson($async$result); $async$goto = 1; break;',
    '        case 1: return A._asyncReturn($async$returnValue, $async$completer);',
    '      }',
    '    });',
    '    return A._asyncStartSync($async$fn, $async$completer);',
    '  },',
    '  getClubBankAccount$1(clubId) { return this.getClubBankAccount$body$ClubRepository(clubId); },',
    '  getClubBankAccount$body$ClubRepository(clubId) {',
    '    var $async$goto = 0, $async$completer = A._makeAsyncAwaitCompleter(type$.nullable_BankAccount), $async$returnValue, $async$self = this;',
    '    var $async$fn = A._wrapJsFunctionForAsync(function($async$errorCode, $async$result) {',
    '      for (;;) switch ($async$goto) {',
    '        case 0: $async$goto = 3; return A._asyncAwait($async$self._club_repository$_client.rpc$1$2$params("get_club_bank_account", {}, null), $async$fn);',
    '        case 3: $async$returnValue = A.BankAccount_BankAccount$fromJson($async$result); $async$goto = 1; break;',
    '        case 1: return A._asyncReturn($async$returnValue, $async$completer);',
    '      }',
    '    });',
    '    return A._asyncStartSync($async$fn, $async$completer);',
    '  }',
    '};',
    'A.SessionProvider.prototype = {',
    '  _resetHistory$0() { var _this = this; _this._session_provider$_history = null; },',
    '  _session_provider$_onAuthChanged$0() { var _this = this; _this._currentSession = _this._currentSessionId = null; _this._resetHistory$0(); },',
    '  fetchSessionDetail$1(sessionId) { return this.fetchSessionDetail$body$SessionProvider(sessionId); },',
    '  fetchSessionDetail$body$SessionProvider(sessionId) {',
    '    var $async$goto = 0, $async$completer = A._makeAsyncAwaitCompleter(type$.void), $async$self = this, session;',
    '    var $async$fn = A._wrapJsFunctionForAsync(function($async$errorCode, $async$result) {',
    '      for (;;) switch ($async$goto) {',
    '        case 0: $async$self._currentSessionId = sessionId; $async$goto = 7;',
    '          return A._asyncAwait($async$self._session_provider$_repository.getSessionDetail$1(sessionId), $async$fn);',
    '        case 7: session = $async$result; $async$self._currentSession = session; $async$goto = 1; break;',
    '        case 1: return A._asyncReturn(null, $async$completer);',
    '      }',
    '    });',
    '    return A._asyncStartSync($async$fn, $async$completer);',
    '  },',
    '  fetchSessionHistory$body$SessionProvider(filter, limit, loadMore) {',
    '    var $async$goto = 0, $async$completer = A._makeAsyncAwaitCompleter(type$.void), $async$self = this, page;',
    '    var $async$fn = A._wrapJsFunctionForAsync(function($async$errorCode, $async$result) {',
    '      for (;;) switch ($async$goto) {',
    '        case 0: $async$goto = 7; return A._asyncAwait($async$self._session_provider$_repository.listMySessionHistory$3$filter$limit$offset(filter, limit, 0), $async$fn);',
    '        case 7: page = $async$result; $async$self._session_provider$_history = new A.SessionHistoryPage(page.sessions); $async$goto = 1; break;',
    '        case 1: return A._asyncReturn(null, $async$completer);',
    '      }',
    '    });',
    '    return A._asyncStartSync($async$fn, $async$completer);',
    '  }',
    '};',
    'A.ClubProvider.prototype = {',
    `  _club_provider$_onAuthChanged$0() { var _this = this; _this._currentClub = _this._currentClubId = null; ${includeBankReset ? '_this._currentBankAccount = null;' : ''} },`,
    '  fetchClubDetails$1(clubId) { return this.fetchClubDetails$body$ClubProvider(clubId); },',
    '  fetchClubDetails$body$ClubProvider(clubId) {',
    '    var $async$goto = 0, $async$completer = A._makeAsyncAwaitCompleter(type$.void), $async$self = this, club, generation;',
    '    var $async$fn = A._wrapJsFunctionForAsync(function($async$errorCode, $async$result) {',
    '      for (;;) switch ($async$goto) {',
    '        case 0: $async$self._currentClubId = clubId; $async$goto = 6;',
    '          return A._asyncAwait($async$self._club_provider$_repository.getClubDetail$1(clubId), $async$fn);',
    '        case 6: club = $async$result; $async$goto = $async$self._club_provider$_generation === generation ? 7 : 8; break;',
    '        case 7: $async$self._currentClub = club; $async$goto = 8; break;',
    '        case 8: return A._asyncReturn(null, $async$completer);',
    '      }',
    '    });',
    '    return A._asyncStartSync($async$fn, $async$completer);',
    '  },',
    '  fetchClubBankAccount$1(clubId) { return this.fetchClubBankAccount$body$ClubProvider(clubId); },',
    '  fetchClubBankAccount$body$ClubProvider(clubId) {',
    '    var $async$goto = 0, $async$completer = A._makeAsyncAwaitCompleter(type$.void), $async$self = this, bank;',
    '    var $async$fn = A._wrapJsFunctionForAsync(function($async$errorCode, $async$result) {',
    '      for (;;) switch ($async$goto) {',
    '        case 0: $async$goto = 7; return A._asyncAwait($async$self._club_provider$_repository.getClubBankAccount$1(clubId), $async$fn);',
    '        case 7: bank = $async$result; $async$self._currentBankAccount = bank; $async$goto = 1; break;',
    '        case 1: return A._asyncReturn(null, $async$completer);',
    '      }',
    '    });',
    '    return A._asyncStartSync($async$fn, $async$completer);',
    '  }',
    '};',
    'A.main_closure2.prototype = {',
    '  call$1(context) {',
    '    var t1 = A.Provider_of(context, false, type$.AuthProvider);',
    '    var r = new A.ClubRepository(null);',
    '    var t3 = new A.ClubProvider(r, t1, null);',
    '    t1.addListener$1(t3.get$_club_provider$_onAuthChanged());',
    '    return t3;',
    '  }',
    '};',
    'A.main_closure3.prototype = {',
    '  call$1(context) {',
    '    var t1 = A.Provider_of(context, false, type$.AuthProvider);',
    '    var r = new A.SessionRepository(null);',
    '    var t4 = new A.SessionProvider(r, t1, null);',
    '    t1.addListener$1(t4.get$_session_provider$_onAuthChanged());',
    '    return t4;',
    '  }',
    '};',
    includeSpReg ? '_instance_0_u(_ = A.SessionProvider.prototype, "get$_session_provider$_onAuthChanged", "_session_provider$_onAuthChanged$0", 0);' : '',
    '_instance_0_u(_ = A.ClubProvider.prototype, "get$_club_provider$_onAuthChanged", "_club_provider$_onAuthChanged$0", 0);',
  ].join('\n') + '\n';
}

function buildSyntheticSnapshotFile(outFile, {
  includeClub = true,
  currentUserNull = false,
  sessionIdNull = false,
  currentSessionNull = false,
  currentSessionObjId = 410,
  historyNull = false,
  historyObjId = 420,
  clubIdNull = false,
  currentClubNull = false,
  bankNull = false,
  wrongSessionReceiver = false,
  wrongMethod = null,
  secretMarker = null,
} = {}) {
  const NODE_TYPES = ['hidden', 'array', 'string', 'object', 'code', 'closure', 'regexp', 'number', 'native', 'synthetic', 'concatenated string', 'sliced string', 'symbol', 'bigint'];
  const EDGE_TYPES = ['context', 'element', 'property', 'internal', 'hidden', 'shortcut', 'weak'];
  const strings = [''];
  const smap = new Map([['', 0]]);
  const intern = (s) => {
    const key = String(s);
    if (!smap.has(key)) {
      smap.set(key, strings.length);
      strings.push(key);
    }
    return smap.get(key);
  };
  let nextId = 10;
  const nodes = [];
  const addNode = (ntype, name, objId = null) => {
    const id = objId !== null ? objId : (nextId += 2);
    const idx = nodes.length;
    nodes.push({ type: NODE_TYPES.indexOf(ntype), name: intern(name), id, edges: [] });
    return idx;
  };
  const addEdge = (src, etype, labelOrIdx, dst) => {
    const et = EDGE_TYPES.indexOf(etype);
    const nameOrIdx = (etype === 'element' || etype === 'hidden') ? Number(labelOrIdx) : intern(String(labelOrIdx));
    nodes[src].edges.push([et, nameOrIdx, dst]);
  };
  const addNull = () => {
    const o = addNode('native', 'system / Oddball');
    addEdge(o, 'internal', 'to_string', addNode('string', 'null'));
    return o;
  };

  const root = addNode('synthetic', '(GC root)', 1);
  const gcRoots = addNode('synthetic', '(GC roots)', 3);
  addEdge(root, 'element', 0, gcRoots);
  const nullNode = addNull();

  const auth = addNode('object', 'AuthProvider', 100);
  addEdge(gcRoots, 'element', 10, auth);
  addEdge(auth, 'property', '_currentUser', currentUserNull ? nullNode : addNode('object', 'User'));
  addEdge(auth, 'property', 'ChangeNotifier__count', addNode('number', 'heap number'));
  addEdge(auth, 'property', 'ChangeNotifier__notificationCallStackDepth', addNode('number', 'heap number'));
  addEdge(auth, 'property', 'ChangeNotifier__reentrantlyRemovedListeners', addNode('number', 'heap number'));

  const sp = addNode('object', 'SessionProvider', 200);
  addEdge(gcRoots, 'element', 20, sp);
  addEdge(sp, 'property', 'auth', auth);
  addEdge(sp, 'property', '_currentSessionId', sessionIdNull ? nullNode : addNode('string', secretMarker || 'RAW_SESSION_ID'));
  addEdge(sp, 'property', '_currentSession', currentSessionNull ? nullNode : addNode('object', 'Session0', currentSessionObjId));
  addEdge(sp, 'property', '_session_provider$_history', historyNull ? nullNode : addNode('object', 'SessionHistoryPage', historyObjId));

  let cp = null;
  if (includeClub) {
    cp = addNode('object', 'ClubProvider', 300);
    addEdge(gcRoots, 'element', 30, cp);
    addEdge(cp, 'property', 'auth', auth);
    addEdge(cp, 'property', '_currentClubId', clubIdNull ? nullNode : addNode('string', secretMarker || 'RAW_CLUB_ID'));
    addEdge(cp, 'property', '_currentClub', currentClubNull ? nullNode : addNode('object', 'Club'));
    addEdge(cp, 'property', '_currentBankAccount', bankNull ? nullNode : addNode('object', 'BankAccount'));
  }

  const arr = addNode('object', 'Array');
  addEdge(auth, 'property', 'ChangeNotifier__listeners', arr);
  const bcProto = addNode('object', 'BoundClosure');

  const addTearoffSlot = (slotIdx, recvNode, methodStr) => {
    const to = addNode('object', 'tear_off');
    const genProto = addNode('object', 'Object');
    addEdge(genProto, 'property', '__proto__', bcProto);
    addEdge(genProto, 'property', '$_name', addNode('string', methodStr));
    addEdge(to, 'property', '__proto__', genProto);
    addEdge(to, 'property', '_receiver', recvNode);
    addEdge(arr, 'element', slotIdx, to);
  };

  addTearoffSlot(0, (wrongSessionReceiver && cp !== null) ? cp : sp, '_session_provider$_onAuthChanged$0');
  if (includeClub) {
    addTearoffSlot(1, cp, wrongMethod || '_club_provider$_onAuthChanged$0');
  }

  intern('padding_' + 'x'.repeat(4200));
  const width = 6;
  const flatNodes = [];
  const flatEdges = [];
  for (const n of nodes) {
    flatNodes.push(n.type, n.name, n.id, 32, n.edges.length, 0);
    for (const [et, ni, dst] of n.edges) {
      flatEdges.push(et, ni, dst * width);
    }
  }
  assert.ok(flatEdges.every((v) => Number.isInteger(v)), 'synthetic snapshot edge table must contain only integers');
  const doc = {
    snapshot: {
      meta: {
        node_fields: ['type', 'name', 'id', 'self_size', 'edge_count', 'detachedness'],
        node_types: [NODE_TYPES, 'string', 'number', 'number', 'number', 'number'],
        edge_fields: ['type', 'name_or_index', 'to_node'],
        edge_types: [EDGE_TYPES, 'string_or_number', 'node'],
      },
      node_count: nodes.length,
      edge_count: flatEdges.length / 3,
    },
    nodes: flatNodes,
    edges: flatEdges,
    strings,
  };
  fs.writeFileSync(outFile, JSON.stringify(doc), 'utf8');
}

async function testObserveAuthAndTargetProviders() {
  // 1. Valid read-only CDP observation: releases objectGroup and uses generatePreview=false
  const validCdp = makeMockCdp();
  const obs = await SC_RUNNER.observeAuthAndTargetProviders({
    cdp: validCdp,
    authHeapObjectId: '100',
    sessionHeapObjectId: '200',
    clubHeapObjectId: '300',
  });
  assert.equal(obs.atomic_claim, false);
  assert.equal(obs.object_group_released, true);
  assert.equal(obs.cdp_errors.length, 0);
  assert.equal(obs.session_selected_fields._currentSessionId.value_type, 'string');
  assert.equal(obs.session_selected_fields._currentSession.class_name, 'Session0');
  assert.equal(obs.club_selected_fields._currentBankAccount.class_name, 'BankAccount');
  assert.ok(!validCdp.calls.some((c) => c.method === 'Runtime.callFunctionOn'));

  // 2. RED: getter rejected without evaluation & FL4 raw string marker never leaks
  const marker = 'SECRET_UUID_DO_NOT_PUBLISH_987654';
  const getterCdp = makeMockCdp({ sessionGetter: true, secretMarker: marker });
  const gObs = await SC_RUNNER.observeAuthAndTargetProviders({
    cdp: getterCdp,
    authHeapObjectId: '100',
    sessionHeapObjectId: '200',
    clubHeapObjectId: '300',
  });
  assert.equal(gObs.session_selected_fields._currentSession.has_getter, true);
  assert.ok(gObs.cdp_errors.includes('session_getter__currentSession'));
  assert.ok(!JSON.stringify(gObs).includes(marker));
  assert.ok(!JSON.stringify(gObs).includes('987654'));

  // 3. RED: readThrows still calls Runtime.releaseObjectGroup and rejects with original error
  const throwCdp = makeMockCdp({ readThrows: true });
  await assert.rejects(
    () => SC_RUNNER.observeAuthAndTargetProviders({ cdp: throwCdp, authHeapObjectId: '100', sessionHeapObjectId: '200' }),
    /simulated HeapProfiler\.getObjectByHeapObjectId failure/,
  );
  assert.ok(throwCdp.calls.some((c) => c.method === 'Runtime.releaseObjectGroup'));

  // 4. RED: legacy object wire shape rejected; unsafe integer counter & timeOrigin skew captured
  const legacyCdp = makeMockCdp({ legacyObjectWireShape: true });
  await assert.rejects(
    () => SC_RUNNER.observeAuthAndTargetProviders({ cdp: legacyCdp, authHeapObjectId: '100' }),
    /identity mismatch/,
  );
  assert.ok(legacyCdp.calls.some((c) => c.method === 'Runtime.releaseObjectGroup'));

  const badOriginObs = await SC_RUNNER.observeAuthAndTargetProviders({
    cdp: makeMockCdp({ unsafeIntCounter: true, timeOriginAfter: 99999.0 }),
    authHeapObjectId: '100',
    sessionHeapObjectId: '200',
  });
  assert.equal(badOriginObs.counters_match, false);
  assert.ok(badOriginObs.cdp_errors.includes('time_origin_changed_during_cdp_observation'));
}

async function testExtractSessionClubBinding() {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'bh07_sc_bind_'));
  try {
    const js = makeSyntheticMainJs({ includeSpReg: true, includeBankReset: true });
    fs.writeFileSync(path.join(tmp, 'main.dart.js'), js, 'utf8');
    const sha = sha256Hex(Buffer.from(js, 'utf8'));
    const ok = SC_RUNNER.extractSessionClubBinding({ buildDir: tmp, expectedMainJsSha: sha });
    assert.equal(ok.ok, true);
    assert.equal(ok.models.session.constructor_name, 'Session0');

    const badSha = SC_RUNNER.extractSessionClubBinding({ buildDir: tmp, expectedMainJsSha: '0'.repeat(64) });
    assert.equal(badSha.ok, false);

    fs.writeFileSync(path.join(tmp, 'main.dart.js'), makeSyntheticMainJs({ includeSpReg: false }), 'utf8');
    assert.equal(SC_RUNNER.extractSessionClubBinding({ buildDir: tmp }).ok, false);

    fs.writeFileSync(path.join(tmp, 'main.dart.js'), makeSyntheticMainJs({ includeBankReset: false }), 'utf8');
    assert.equal(SC_RUNNER.extractSessionClubBinding({ buildDir: tmp }).ok, false);

    // SC2 positive: ALL deserializers invoked via $async$temp1 = A
    const jsAllAlias = js
      .replace(
        'A.SessionHistoryPage_SessionHistoryPage$fromResponse($async$result, limit, offset)',
        '$async$temp1.SessionHistoryPage_SessionHistoryPage$fromResponse($async$result, limit, offset)',
      )
      .replace(
        'var $async$goto = 0, $async$completer = A._makeAsyncAwaitCompleter(type$.SessionHistoryPage), $async$returnValue, $async$self = this;',
        'var $async$goto = 0, $async$completer = A._makeAsyncAwaitCompleter(type$.SessionHistoryPage), $async$returnValue, $async$self = this, $async$temp1 = A;',
      );
    fs.writeFileSync(path.join(tmp, 'main.dart.js'), jsAllAlias, 'utf8');
    assert.equal(SC_RUNNER.extractSessionClubBinding({ buildDir: tmp }).ok, true);

    // SC2 negative: overwritten or comment-masked async alias rejected
    fs.writeFileSync(
      path.join(tmp, 'main.dart.js'),
      js.replace('case 0: $async$goto = 3;', 'case 0: $async$temp1 = EvilA; $async$goto = 3;'),
      'utf8',
    );
    assert.equal(SC_RUNNER.extractSessionClubBinding({ buildDir: tmp }).ok, false);

    fs.writeFileSync(
      path.join(tmp, 'main.dart.js'),
      js.replace(
        'var $async$goto = 0, $async$completer = A._makeAsyncAwaitCompleter(type$.Session), $async$returnValue, $async$self = this, $async$temp1 = A;',
        '/* var $async$temp1 = A; */ var $async$goto = 0, $async$completer = A._makeAsyncAwaitCompleter(type$.Session), $async$returnValue, $async$self = this, $async$temp1 = FakeA;',
      ),
      'utf8',
    );
    assert.equal(SC_RUNNER.extractSessionClubBinding({ buildDir: tmp }).ok, false);

    // SC4 negative: discarded/overwritten/null-return repo & provider flows rejected
    fs.writeFileSync(
      path.join(tmp, 'main.dart.js'),
      js.replace(
        'getSessionDetail$body$SessionRepository(sessionId) {',
        'getSessionDetail$body$SessionRepository(sessionId) { this._session_repository$_client.rpc("get_session_public_detail"); A.Session_Session$fromJson(sessionId); return null; }, _unused() {',
      ),
      'utf8',
    );
    assert.equal(SC_RUNNER.extractSessionClubBinding({ buildDir: tmp }).ok, false);

    fs.writeFileSync(
      path.join(tmp, 'main.dart.js'),
      js.replace(
        '$async$returnValue = $async$temp1.Session_Session$fromJson($async$result);',
        '$async$temp1.Session_Session$fromJson($async$result); $async$returnValue = null;',
      ),
      'utf8',
    );
    assert.equal(SC_RUNNER.extractSessionClubBinding({ buildDir: tmp }).ok, false);

    fs.writeFileSync(
      path.join(tmp, 'main.dart.js'),
      js.replace(
        '$async$returnValue = $async$temp1.Session_Session$fromJson($async$result);',
        '$async$returnValue = $async$temp1.Session_Session$fromJson($async$result); $async$returnValue = null;',
      ),
      'utf8',
    );
    assert.equal(SC_RUNNER.extractSessionClubBinding({ buildDir: tmp }).ok, false);

    // SC4 P1 mutants: comma/false-ternary discard & equivalent alias spoof rejected
    for (const mutant of [
      js.replace(
        '$async$returnValue = $async$temp1.Session_Session$fromJson($async$result);',
        '$async$returnValue = $async$temp1.Session_Session$fromJson(($async$result, {}));',
      ),
      js.replace(
        '$async$returnValue = $async$temp1.Session_Session$fromJson($async$result);',
        '$async$returnValue = $async$temp1.Session_Session$fromJson(false ? $async$result : {});',
      ),
      js.replace(
        '$async$returnValue = $async$temp1.Session_Session$fromJson($async$result);',
        'var bogus = ($async$result, {}); $async$returnValue = $async$temp1.Session_Session$fromJson(bogus);',
      ),
      js.replace(
        '$async$returnValue = $async$temp1.Session_Session$fromJson($async$result);',
        'var bogus = false ? $async$result : {}; $async$returnValue = $async$temp1.Session_Session$fromJson(bogus);',
      ),
    ]) {
      fs.writeFileSync(path.join(tmp, 'main.dart.js'), mutant, 'utf8');
      assert.equal(SC_RUNNER.extractSessionClubBinding({ buildDir: tmp }).ok, false);
    }
  } finally {
    fs.rmSync(tmp, { recursive: true, force: true });
  }
}

function buildMockRunSetup(tmpDir, {
  bankPopulated = true,
  requireBankAccount = false,
  epochMutator = {},
  throwCaptureAt = null,
  dbCleanupFails = false,
} = {}) {
  const buildDir = path.join(tmpDir, 'build');
  const dumpsDir = path.join(tmpDir, 'dumps');
  const outDir = path.join(tmpDir, 'out');
  const statePath = path.join(tmpDir, 'state.json');
  const cfgPath = path.join(tmpDir, 'cfg.json');
  fs.mkdirSync(buildDir, { recursive: true });
  const js = makeSyntheticMainJs();
  fs.writeFileSync(path.join(buildDir, 'main.dart.js'), js, 'utf8');
  fs.writeFileSync(path.join(buildDir, 'index.html'), '<html></html>\n', 'utf8');
  const mainSha = sha256Hex(Buffer.from(js, 'utf8'));
  const idxSha = sha256Hex(fs.readFileSync(path.join(buildDir, 'index.html')));

  const privMarker = 'PRIV_CLUB_UUID_MARKER_991188';
  const cfg = {
    db_container: 'bh07-android-db',
    supabase_url: 'http://127.0.0.1:54321',
    web_url: 'http://127.0.0.1:8088',
    owner_password: 'test-owner-password-not-secret',
    cohost_password: 'test-cohost-password-not-secret',
    member_password: 'test-member-password-not-secret',
    build_dir: buildDir,
    dumps_dir: dumpsDir,
    state_path: statePath,
    reuse_existing_server: true,
    provenance: {
      mode: 'profile',
      started_at: '2026-11-16T01:00:00Z',
      artifacts: { 'index.html': idxSha, 'main.dart.js': mainSha },
    },
  };
  fs.writeFileSync(cfgPath, JSON.stringify(cfg), 'utf8');

  let currentCtx = { cycle: 1, actor: 'cohost', epoch: 'baseline' };
  const mutKey = () => `c${currentCtx.cycle}_${currentCtx.epoch}`;
  const mockCdp = makeMockCdp();
  const wrappedCdp = {
    send: async (method, params) => {
      if (method === 'Runtime.evaluate' && /performance\.timeOrigin/.test((params && params.expression) || '')) {
        return { result: { result: { type: 'number', value: 12345.6 } } };
      }
      const m = epochMutator[mutKey()];
      if (m && m.cdpOpts) {
        return makeMockCdp(m.cdpOpts).send(method, params);
      }
      if (currentCtx.cycle === 1 && currentCtx.epoch === 'baseline') {
        return makeMockCdp({
          clubPresent: false, authCount: 1, currentUserNull: true,
          sessionIdNull: true, currentSessionNull: true, historyNull: true,
        }).send(method, params);
      }
      if (currentCtx.epoch === 'baseline' || currentCtx.epoch === 'post_logout') {
        return makeMockCdp({
          clubPresent: true, authCount: 2, currentUserNull: true,
          sessionIdNull: true, currentSessionNull: true, historyNull: true,
          clubIdNull: true, currentClubNull: true, bankNull: true,
        }).send(method, params);
      }
      if (currentCtx.epoch === 'owner_active') {
        return makeMockCdp({
          clubPresent: true, authCount: 2, currentUserNull: false,
          sessionIdNull: false, currentSessionNull: false, historyNull: false,
          clubIdNull: false, currentClubNull: false, bankNull: !bankPopulated,
        }).send(method, params);
      }
      const isCohost = currentCtx.actor === 'cohost';
      return makeMockCdp({
        clubPresent: true, authCount: 2, currentUserNull: false,
        sessionIdNull: !isCohost, currentSessionNull: !isCohost, historyNull: false,
        clubIdNull: true, currentClubNull: true, bankNull: true,
      }).send(method, params);
    },
    close: async () => {},
  };

  const userHooks = {
    buildDir,
    getGitProvenance: () => ({ tested_source_sha: 'b'.repeat(40), git_dirty: false }),
    prepareBuild: async () => ({
      mode: 'profile',
      reused: false,
      started_at: '2026-11-16T01:00:00Z',
      served_match: true,
      artifacts: { 'index.html': idxSha, 'main.dart.js': mainSha },
    }),
    createFixture: ({ statePath: spPath }) => {
      fs.writeFileSync(spPath, JSON.stringify({
        club_id: privMarker,
        club_member_id: '11111111-2222-4333-8444-555555555501',
        session_id: '11111111-2222-4333-8444-555555555502',
        player_id: '11111111-2222-4333-8444-555555555503',
        revision_id: '11111111-2222-4333-8444-555555555504',
        charge_id: '11111111-2222-4333-8444-555555555505',
        marker_id: '11111111-2222-4333-8444-555555555506',
        sentinel_1: '11111111-2222-4333-8444-555555555507',
        sentinel_2: '11111111-2222-4333-8444-555555555508',
      }), { mode: 0o600 });
      return { club_name: 'BH07 Club Mock', session_title: 'BH07 Session Mock' };
    },
    startSession: async () => ({
      browser: { userDataDir: null, proc: null },
      cdp: wrappedCdp,
    }),
    shutdownBrowser: async () => ({ exited: true, profileRemoved: true }),
    waitForStartupReady: async () => {},
    measureTimeOrigin: async () => 12345.6,
    performEpochAction: async ({ step, epName }) => {
      if (epName !== 'cycle1_logout') {
        currentCtx = { cycle: step.cycle, actor: step.actor, epoch: epName };
      }
    },
    streamSnapshotToFile: async ({ outFile }) => {
      if (throwCaptureAt && mutKey() === throwCaptureAt) {
        throw new Error('simulated snapshot capture failure');
      }
      const m = epochMutator[mutKey()];
      if (m && m.snapOpts) {
        buildSyntheticSnapshotFile(outFile, m.snapOpts);
        return;
      }
      if (currentCtx.cycle === 1 && currentCtx.epoch === 'baseline') {
        buildSyntheticSnapshotFile(outFile, {
          includeClub: false, currentUserNull: true,
          sessionIdNull: true, currentSessionNull: true, historyNull: true,
        });
      } else if (currentCtx.epoch === 'baseline' || currentCtx.epoch === 'post_logout') {
        buildSyntheticSnapshotFile(outFile, {
          includeClub: true, currentUserNull: true,
          sessionIdNull: true, currentSessionNull: true, historyNull: true,
          clubIdNull: true, currentClubNull: true, bankNull: true,
        });
      } else if (currentCtx.epoch === 'owner_active') {
        buildSyntheticSnapshotFile(outFile, {
          includeClub: true, currentUserNull: false,
          sessionIdNull: false, currentSessionNull: false,
          currentSessionObjId: 410 + currentCtx.cycle * 100,
          historyNull: false, historyObjId: 420 + currentCtx.cycle * 100,
          clubIdNull: false, currentClubNull: false, bankNull: !bankPopulated,
        });
      } else {
        const isCohost = currentCtx.actor === 'cohost';
        buildSyntheticSnapshotFile(outFile, {
          includeClub: true, currentUserNull: false,
          sessionIdNull: !isCohost, currentSessionNull: !isCohost,
          currentSessionObjId: 810 + currentCtx.cycle * 100,
          historyNull: false, historyObjId: 820 + currentCtx.cycle * 100,
          clubIdNull: true, currentClubNull: true, bankNull: true,
        });
      }
    },
    checkFixtureZeroMutations: () => ({ ok: true, counts: {} }),
    cleanupFixture: () => {
      if (dbCleanupFails) {
        return {
          disposable_instructions_club_created: true,
          disposable_instructions_session_created: true,
          disposable_instructions_removed: false,
          disposable_instructions_verified_absent: false,
          disposable_instructions_cleanup_verified: false,
          zero_mutation_verified: true,
          baseline_fingerprint_equal: false,
          public_rows_schema_roles_equal: false,
          auth_rows_excluded: true,
          error: 'simulated cleanup failure',
        };
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
  };

  return { cfg, cfgPath, outDir, buildDir, dumpsDir, statePath, privMarker, requireBankAccount, userHooks };
}

function runPyVerify(outDir, buildDir, { requireBank = false } = {}) {
  const args = ['-X', 'utf8', SC_GRAPH_PY, 'verify', outDir, '--build-dir', buildDir];
  if (requireBank) args.push('--require-bank-account');
  try {
    const out = execFileSync(PY, args, { encoding: 'utf8', shell: false });
    return { status: 0, payload: JSON.parse(out) };
  } catch (err) {
    return { status: err.status || 1, payload: err.stdout ? JSON.parse(err.stdout) : null };
  }
}

async function testMockedTwoCycleRuns() {
  // 1. Full bank populated 2-cycle/8-epoch run -> PASS & exit 0 & Python verify --require-bank-account exits 0
  const okTmp = fs.mkdtempSync(path.join(os.tmpdir(), 'bh07_sc_full_ok_'));
  try {
    const setup = buildMockRunSetup(okTmp, { bankPopulated: true, requireBankAccount: true });
    const { summary, exitCode } = await SC_RUNNER.runSessionClubAuthListener({
      cfg: setup.cfg, cfgPath: setup.cfgPath, outDir: setup.outDir,
      requireBankAccount: true, userHooks: setup.userHooks,
    });
    assert.equal(exitCode, 0);
    assert.equal(summary.status, 'RUN');
    assert.equal(summary.verdict, 'PASS');
    assert.equal(summary.session_club_assessment.session_listener_gate, 'PASS');
    assert.equal(summary.session_club_assessment.club_core_listener_gate, 'PASS');
    assert.equal(summary.session_club_assessment.club_bank_account_gate, 'PASS');
    assert.equal(summary.session_club_assessment.session_club_listener_gate, 'PASS');
    assert.equal(summary.cycles[0].epochs.baseline.listener_graph.verdict, 'NOT_RUN_LAZY');

    const pyVer = runPyVerify(setup.outDir, setup.buildDir, { requireBank: true });
    assert.equal(pyVer.status, 0, JSON.stringify(pyVer.payload));
    assert.equal(pyVer.payload.ok, true);
    assert.equal(pyVer.payload.assessment.session_club_listener_gate, 'PASS');
  } finally {
    fs.rmSync(okTmp, { recursive: true, force: true });
  }

  // 2. Partial fixture (bank unpopulated) -> honest NOT_RUN (never fake PASS); strict Python verify fails
  const partTmp = fs.mkdtempSync(path.join(os.tmpdir(), 'bh07_sc_partial_'));
  try {
    const setup = buildMockRunSetup(partTmp, { bankPopulated: false, requireBankAccount: false });
    const { summary, exitCode } = await SC_RUNNER.runSessionClubAuthListener({
      cfg: setup.cfg, cfgPath: setup.cfgPath, outDir: setup.outDir,
      requireBankAccount: false, userHooks: setup.userHooks,
    });
    assert.equal(exitCode, 0);
    assert.equal(summary.verdict, 'PARTIAL_NOT_RUN');
    assert.equal(summary.session_club_assessment.club_bank_account_gate, 'NOT_RUN');
    assert.equal(summary.session_club_assessment.session_club_listener_gate, 'PARTIAL_CLUB_BANK_NOT_RUN');

    const pyDefault = runPyVerify(setup.outDir, setup.buildDir, { requireBank: false });
    assert.equal(pyDefault.status, 0, JSON.stringify(pyDefault.payload));
    assert.equal(pyDefault.payload.assessment.session_club_listener_gate, 'PARTIAL_CLUB_BANK_NOT_RUN');

    const pyStrict = runPyVerify(setup.outDir, setup.buildDir, { requireBank: true });
    assert.equal(pyStrict.status, 1);
    assert.equal(pyStrict.payload.ok, false);
  } finally {
    fs.rmSync(partTmp, { recursive: true, force: true });
  }

  // 3. RED: wrong receiver + stale secret sessionId at Cycle 2 post_logout + FL4 redaction in FAIL bundle
  const redTmp = fs.mkdtempSync(path.join(os.tmpdir(), 'bh07_sc_red_'));
  try {
    const leakStr = 'SECRET_SESSION_STRING_MARKER_55449900';
    const setup = buildMockRunSetup(redTmp, {
      epochMutator: {
        c2_post_logout: {
          snapOpts: {
            includeClub: true, currentUserNull: true,
            sessionIdNull: false, currentSessionNull: true, historyNull: true,
            clubIdNull: true, currentClubNull: true, bankNull: true,
            wrongSessionReceiver: true, wrongMethod: 'tamperedMethod$0',
            secretMarker: leakStr,
          },
          cdpOpts: {
            clubPresent: true, authCount: 2, currentUserNull: true,
            sessionIdNull: false, currentSessionNull: true, historyNull: true,
            clubIdNull: true, currentClubNull: true, bankNull: true,
            secretMarker: leakStr,
          },
        },
      },
    });
    const { summary, exitCode } = await SC_RUNNER.runSessionClubAuthListener({
      cfg: setup.cfg, cfgPath: setup.cfgPath, outDir: setup.outDir, userHooks: setup.userHooks,
    });
    assert.equal(exitCode, 1);
    assert.equal(summary.verdict, 'FAIL');
    assert.equal(summary.cycles[1].epochs.post_logout.listener_graph.verdict, 'FAIL');
    const filesText = ['summary.json', 'report.md', 'run.log'].map((f) => fs.readFileSync(path.join(setup.outDir, f), 'utf8')).join('\n');
    for (const marker of [leakStr, '55449900', 'tamperedMethod', setup.privMarker]) {
      assert.ok(!filesText.includes(marker), `leaked secret/untrusted marker ${marker}`);
    }
  } finally {
    fs.rmSync(redTmp, { recursive: true, force: true });
  }

  // 4. RED: cleanup failure preserves recovery statePath & removes dumpsDir
  const clnTmp = fs.mkdtempSync(path.join(os.tmpdir(), 'bh07_sc_cleanup_'));
  try {
    const setup = buildMockRunSetup(clnTmp, { throwCaptureAt: 'c1_owner_active', dbCleanupFails: true });
    const { summary, exitCode } = await SC_RUNNER.runSessionClubAuthListener({
      cfg: setup.cfg, cfgPath: setup.cfgPath, outDir: setup.outDir, userHooks: setup.userHooks,
    });
    assert.equal(exitCode, 1);
    assert.equal(summary.verdict, 'FAIL');
    assert.ok(!fs.existsSync(setup.dumpsDir));
    assert.ok(fs.existsSync(setup.statePath));
    assert.equal(summary.cleanup.recovery_state_retained, true);
  } finally {
    fs.rmSync(clnTmp, { recursive: true, force: true });
  }

  // 5. RED (SC3): post_actor reusing Owner Session0 heap_object_id fails runner & Python verify
  const reuseTmp = fs.mkdtempSync(path.join(os.tmpdir(), 'bh07_sc_reuse_'));
  try {
    const setup = buildMockRunSetup(reuseTmp, {
      bankPopulated: true,
      requireBankAccount: true,
      epochMutator: {
        c1_post_actor: {
          snapOpts: {
            includeClub: true, currentUserNull: false,
            sessionIdNull: false, currentSessionNull: false,
            currentSessionObjId: 510,
            historyNull: false, historyObjId: 920,
            clubIdNull: true, currentClubNull: true, bankNull: true,
          },
        },
      },
    });
    const { summary, exitCode } = await SC_RUNNER.runSessionClubAuthListener({
      cfg: setup.cfg, cfgPath: setup.cfgPath, outDir: setup.outDir,
      requireBankAccount: true, userHooks: setup.userHooks,
    });
    assert.equal(exitCode, 1);
    assert.equal(summary.verdict, 'FAIL');
  } finally {
    fs.rmSync(reuseTmp, { recursive: true, force: true });
  }

  // 6. RED (SC3): removing target_heap_object_id from BOTH owner_active and post_actor still fails verify
  const stripTmp = fs.mkdtempSync(path.join(os.tmpdir(), 'bh07_sc_strip_'));
  try {
    const setup = buildMockRunSetup(stripTmp, { bankPopulated: true, requireBankAccount: true });
    const { exitCode } = await SC_RUNNER.runSessionClubAuthListener({
      cfg: setup.cfg, cfgPath: setup.cfgPath, outDir: setup.outDir,
      requireBankAccount: true, userHooks: setup.userHooks,
    });
    assert.equal(exitCode, 0);
    const sumPath = path.join(setup.outDir, 'summary.json');
    const sum = JSON.parse(fs.readFileSync(sumPath, 'utf8'));
    delete sum.cycles[0].epochs.owner_active.listener_graph.session_provider.records[0].selected_fields._currentSession.target_heap_object_id;
    delete sum.cycles[0].epochs.post_actor.listener_graph.session_provider.records[0].selected_fields._currentSession.target_heap_object_id;
    fs.writeFileSync(sumPath, JSON.stringify(sum, null, 2) + '\n', 'utf8');
    const manifest = ['summary.json', 'run.log', 'report.md', 'source_binding.json']
      .map((f) => `${sha256Hex(fs.readFileSync(path.join(setup.outDir, f)))}  ${f}`).join('\n') + '\n';
    fs.writeFileSync(path.join(setup.outDir, 'hashes.sha256'), manifest, 'utf8');
    const pyVer = runPyVerify(setup.outDir, setup.buildDir, { requireBank: true });
    assert.equal(pyVer.status, 1);
    assert.equal(pyVer.payload.ok, false);
    assert.ok(pyVer.payload.problems.some((p) => p.includes('target_heap_object_id')));
  } finally {
    fs.rmSync(stripTmp, { recursive: true, force: true });
  }
}

async function main() {
  await testObserveAuthAndTargetProviders();
  await testExtractSessionClubBinding();
  await testMockedTwoCycleRuns();
  console.log('ALL_SESSION_CLUB_AUTH_LISTENER_CONTROLS_PASS');
}

main().catch((err) => {
  console.error(err && err.stack ? err.stack : String(err));
  process.exit(1);
});
