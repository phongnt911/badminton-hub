"""Unit, RED control, anti-forgery, and integration tests for session_club_auth_listener_graph.py."""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from unittest import mock
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.bh07_appheap import session_club_auth_listener_graph as sc_graph
from scripts.bh07_appheap import test_finance_auth_listener_graph as fin_tests

SyntheticV8SnapshotBuilder = fin_tests.SyntheticV8SnapshotBuilder


def make_synthetic_sc_main_js(
    *,
    session_model_cls='Session0',
    include_session_deserializer=True,
    include_club_deserializer=True,
    include_bank_deserializer=True,
    session_id_field='_currentSessionId',
    current_session_field='_currentSession',
    history_field='_session_provider$_history',
    club_id_field='_currentClubId',
    current_club_field='_currentClub',
    bank_account_field='_currentBankAccount',
    sp_reg_getter='get$_session_provider$_onAuthChanged',
    sp_reg_method='_session_provider$_onAuthChanged$0',
    cp_reg_getter='get$_club_provider$_onAuthChanged',
    cp_reg_method='_club_provider$_onAuthChanged$0',
    include_auth_provider=True,
    include_bound_closure=True,
    include_tearoff_factory=True,
    include_sp_registration=True,
    include_cp_registration=True,
    include_sp_reset=True,
    include_cp_reset=True,
    include_cp_bank_reset=True,
    include_session_wiring=True,
    include_club_wiring=True,
    use_dart2js_async_shape=True,
):
    parts = ['var A = {']
    if include_bound_closure:
        parts.append(
            '  BoundClosure: function BoundClosure(t0, t1) {\n'
            '    this._receiver = t0;\n'
            '    this._interceptor = t1;\n'
            '  },'
        )
    if include_auth_provider:
        parts.append(
            '  AuthProvider: function AuthProvider(t0, t1) {\n'
            '    var _ = this;\n'
            '    _._repository = t0;\n'
            '    _._currentUser = _._authSubscription = null;\n'
            '    _.ChangeNotifier__count = 0;\n'
            '    _.ChangeNotifier__listeners = t1;\n'
            '    _.ChangeNotifier__reentrantlyRemovedListeners = _.ChangeNotifier__notificationCallStackDepth = 0;\n'
            '  },'
        )

    parts.append(
        '  SessionRepository: function SessionRepository(t0) { this._session_repository$_client = t0; },\n'
        '  ClubRepository: function ClubRepository(t0) { this._club_repository$_client = t0; },\n'
        '  SessionProvider: function SessionProvider(t0, t1, t2) {\n'
        '    var _ = this;\n'
        '    _._session_provider$_repository = t0;\n'
        '    _.auth = t1;\n'
        f'    _.{session_id_field} = _.{current_session_field} = _.{history_field} = null;\n'
        '    _.ChangeNotifier__count = 0;\n'
        '    _.ChangeNotifier__listeners = t2;\n'
        '    _.ChangeNotifier__reentrantlyRemovedListeners = _.ChangeNotifier__notificationCallStackDepth = 0;\n'
        '  },\n'
        '  ClubProvider: function ClubProvider(t0, t1, t2) {\n'
        '    var _ = this;\n'
        '    _._club_provider$_repository = t0;\n'
        '    _.auth = t1;\n'
        f'    _.{club_id_field} = _.{current_club_field} = _.{bank_account_field} = null;\n'
        '    _.ChangeNotifier__count = 0;\n'
        '    _.ChangeNotifier__listeners = t2;\n'
        '    _.ChangeNotifier__reentrantlyRemovedListeners = _.ChangeNotifier__notificationCallStackDepth = 0;\n'
        '  },\n'
        f'  {session_model_cls}: function {session_model_cls}(t0, t1) {{ this.id = t0; this.title = t1; }},\n'
        '  SessionHistoryPage: function SessionHistoryPage(t0) { this.sessions = t0; },\n'
        '  Club: function Club(t0, t1) { this.id = t0; this.name = t1; },\n'
        '  BankAccount: function BankAccount(t0, t1) { this.id = t0; this.bankCode = t1; },'
    )

    if include_session_deserializer:
        parts.append(
            '  Session_Session$fromJson(json) {\n'
            f'    return new A.{session_model_cls}(json.$index(0, "id"), json.$index(0, "title"));\n'
            '  },\n'
            '  SessionHistoryPage_SessionHistoryPage$fromResponse(resp, limit, offset) {\n'
            '    return new A.SessionHistoryPage(resp);\n'
            '  },'
        )
    if include_club_deserializer:
        parts.append(
            '  Club_Club$fromJson(json) {\n'
            '    return new A.Club(json.$index(0, "id"), json.$index(0, "name"));\n'
            '  },'
        )
    if include_bank_deserializer:
        parts.append(
            '  BankAccount_BankAccount$fromJson(json) {\n'
            '    return new A.BankAccount(json.$index(0, "id"), json.$index(0, "bank_code"));\n'
            '  },'
        )

    if include_tearoff_factory:
        parts.append(
            '  Closure_fromTearOff(parameters) {\n'
            '    var $prototype = Object.create(new A.BoundClosure(null, null).constructor.prototype);\n'
            '    var $constructor = function tear_off(a, b) { this.$initialize(a, b); };\n'
            '    $prototype.constructor = $constructor;\n'
            '    $constructor.prototype = $prototype;\n'
            '    $prototype.$_name = parameters.fs[0];\n'
            '    return $constructor;\n'
            '  }'
        )
    parts.append('};')

    parts.append(
        'A.SessionRepository.prototype = {\n'
        '  getSessionDetail$1(sessionId) { return this.getSessionDetail$body$SessionRepository(sessionId); },\n'
        '  getSessionDetail$body$SessionRepository(sessionId) {\n'
        '    var $async$goto = 0, $async$completer = A._makeAsyncAwaitCompleter(type$.Session), $async$returnValue, $async$self = this, $async$temp1 = A;\n'
        '    var $async$getSessionDetail$1 = A._wrapJsFunctionForAsync(function($async$errorCode, $async$result) {\n'
        '      for (;;) switch ($async$goto) {\n'
        '        case 0: $async$goto = 3; return A._asyncAwait($async$self._session_repository$_client.rpc$1$2$params("get_session_public_detail", {}, null), $async$getSessionDetail$1);\n'
        '        case 3: $async$returnValue = $async$temp1.Session_Session$fromJson($async$result); $async$goto = 1; break;\n'
        '        case 1: return A._asyncReturn($async$returnValue, $async$completer);\n'
        '      }\n'
        '    });\n'
        '    return A._asyncStartSync($async$getSessionDetail$1, $async$completer);\n'
        '  },\n'
        '  listMySessionHistory$3$filter$limit$offset(filter, limit, offset) {\n'
        '    var $async$goto = 0, $async$completer = A._makeAsyncAwaitCompleter(type$.SessionHistoryPage), $async$returnValue, $async$self = this;\n'
        '    var $async$fn = A._wrapJsFunctionForAsync(function($async$errorCode, $async$result) {\n'
        '      for (;;) switch ($async$goto) {\n'
        '        case 0: $async$goto = 3; return A._asyncAwait($async$self._session_repository$_client.rpc$1$2$params("list_my_session_history", {}, null), $async$fn);\n'
        '        case 3: $async$returnValue = A.SessionHistoryPage_SessionHistoryPage$fromResponse($async$result, limit, offset); $async$goto = 1; break;\n'
        '        case 1: return A._asyncReturn($async$returnValue, $async$completer);\n'
        '      }\n'
        '    });\n'
        '    return A._asyncStartSync($async$fn, $async$completer);\n'
        '  }\n'
        '};\n'
        'A.ClubRepository.prototype = {\n'
        '  getClubDetail$1(clubId) { return this.getClubDetail$body$ClubRepository(clubId); },\n'
        '  getClubDetail$body$ClubRepository(clubId) {\n'
        '    var $async$goto = 0, $async$completer = A._makeAsyncAwaitCompleter(type$.Club), $async$returnValue, $async$self = this, $async$temp1 = A;\n'
        '    var $async$getClubDetail$1 = A._wrapJsFunctionForAsync(function($async$errorCode, $async$result) {\n'
        '      for (;;) switch ($async$goto) {\n'
        '        case 0: $async$goto = 3; return A._asyncAwait($async$self._club_repository$_client.rpc$1$2$params("get_club_detail", {}, null), $async$getClubDetail$1);\n'
        '        case 3: $async$returnValue = $async$temp1.Club_Club$fromJson($async$result); $async$goto = 1; break;\n'
        '        case 1: return A._asyncReturn($async$returnValue, $async$completer);\n'
        '      }\n'
        '    });\n'
        '    return A._asyncStartSync($async$getClubDetail$1, $async$completer);\n'
        '  },\n'
        '  getClubBankAccount$1(clubId) { return this.getClubBankAccount$body$ClubRepository(clubId); },\n'
        '  getClubBankAccount$body$ClubRepository(clubId) {\n'
        '    var $async$goto = 0, $async$completer = A._makeAsyncAwaitCompleter(type$.nullable_BankAccount), $async$returnValue, $async$self = this;\n'
        '    var $async$getClubBankAccount$1 = A._wrapJsFunctionForAsync(function($async$errorCode, $async$result) {\n'
        '      for (;;) switch ($async$goto) {\n'
        '        case 0: $async$goto = 3; return A._asyncAwait($async$self._club_repository$_client.rpc$1$2$params("get_club_bank_account", {}, null), $async$getClubBankAccount$1);\n'
        '        case 3: $async$returnValue = A.BankAccount_BankAccount$fromJson($async$result); $async$goto = 1; break;\n'
        '        case 1: return A._asyncReturn($async$returnValue, $async$completer);\n'
        '      }\n'
        '    });\n'
        '    return A._asyncStartSync($async$getClubBankAccount$1, $async$completer);\n'
        '  }\n'
        '};'
    )

    sp_reset_block = (
        f'      _this.{current_session_field} = _this.{session_id_field} = null;\n'
        '      _this._resetHistory$0();\n'
    ) if include_sp_reset else '      _this._noop = null;\n'

    parts.append(
        'A.SessionProvider.prototype = {\n'
        '  _resetHistory$0() {\n'
        '    var _this = this;\n'
        + (f'    _this.{history_field} = null;\n' if include_sp_reset else '    _this._noop = null;\n') +
        '  },\n'
        f'  {sp_reg_method}() {{\n'
        '    var _this = this;\n'
        + sp_reset_block +
        '  },\n'
        '  fetchSessionDetail$1(sessionId) { return this.fetchSessionDetail$body$SessionProvider(sessionId); },\n'
        '  fetchSessionDetail$body$SessionProvider(sessionId) {\n'
        '    var $async$goto = 0, $async$completer = A._makeAsyncAwaitCompleter(type$.void), $async$self = this, session;\n'
        '    var $async$fetchSessionDetail$1 = A._wrapJsFunctionForAsync(function($async$errorCode, $async$result) {\n'
        '      for (;;) switch ($async$goto) {\n'
        f'        case 0: $async$self.{session_id_field} = sessionId; $async$goto = 7;\n'
        '          return A._asyncAwait($async$self._session_provider$_repository.getSessionDetail$1(sessionId), $async$fetchSessionDetail$1);\n'
        f'        case 7: session = $async$result; $async$self.{current_session_field} = session; $async$goto = 1; break;\n'
        '        case 1: return A._asyncReturn(null, $async$completer);\n'
        '      }\n'
        '    });\n'
        '    return A._asyncStartSync($async$fetchSessionDetail$1, $async$completer);\n'
        '  },\n'
        '  fetchSessionHistory$body$SessionProvider(filter, limit, loadMore) {\n'
        '    var $async$goto = 0, $async$completer = A._makeAsyncAwaitCompleter(type$.void), $async$self = this, page;\n'
        '    var $async$fn = A._wrapJsFunctionForAsync(function($async$errorCode, $async$result) {\n'
        '      for (;;) switch ($async$goto) {\n'
        '        case 0: $async$goto = 7; return A._asyncAwait($async$self._session_provider$_repository.listMySessionHistory$3$filter$limit$offset(filter, limit, 0), $async$fn);\n'
        + (
            f'        case 7: page = $async$result; $async$self.{history_field} = new A.SessionHistoryPage(page.sessions); $async$goto = 1; break;\n'
            if use_dart2js_async_shape else
            f'        case 7: $async$self.{history_field} = $async$result; $async$goto = 1; break;\n'
        ) +
        '        case 1: return A._asyncReturn(null, $async$completer);\n'
        '      }\n'
        '    });\n'
        '    return A._asyncStartSync($async$fn, $async$completer);\n'
        '  }\n'
        '};'
    )

    cp_reset_lines = ''
    if include_cp_reset:
        cp_reset_lines += f'    _this.{current_club_field} = _this.{club_id_field} = null;\n'
    if include_cp_bank_reset:
        cp_reset_lines += f'    _this.{bank_account_field} = null;\n'

    parts.append(
        'A.ClubProvider.prototype = {\n'
        f'  {cp_reg_method}() {{\n'
        '    var _this = this;\n'
        + cp_reset_lines +
        '  },\n'
        '  fetchClubDetails$1(clubId) { return this.fetchClubDetails$body$ClubProvider(clubId); },\n'
        '  fetchClubDetails$body$ClubProvider(clubId) {\n'
        '    var $async$goto = 0, $async$completer = A._makeAsyncAwaitCompleter(type$.void), $async$self = this, club, generation;\n'
        '    var $async$fetchClubDetails$1 = A._wrapJsFunctionForAsync(function($async$errorCode, $async$result) {\n'
        '      for (;;) switch ($async$goto) {\n'
        f'        case 0: $async$self.{club_id_field} = clubId; $async$goto = 6;\n'
        '          return A._asyncAwait($async$self._club_provider$_repository.getClubDetail$1(clubId), $async$fetchClubDetails$1);\n'
        + (
            '        case 6: club = $async$result; $async$goto = $async$self._club_provider$_generation === generation ? 7 : 8; break;\n'
            f'        case 7: $async$self.{current_club_field} = club; $async$goto = 8; break;\n'
            '        case 8: return A._asyncReturn(null, $async$completer);\n'
            if use_dart2js_async_shape else
            f'        case 6: $async$self.{current_club_field} = $async$result; $async$goto = 8; break;\n'
            '        case 8: return A._asyncReturn(null, $async$completer);\n'
        ) +
        '      }\n'
        '    });\n'
        '    return A._asyncStartSync($async$fetchClubDetails$1, $async$completer);\n'
        '  },\n'
        '  fetchClubBankAccount$1(clubId) { return this.fetchClubBankAccount$body$ClubProvider(clubId); },\n'
        '  fetchClubBankAccount$body$ClubProvider(clubId) {\n'
        '    var $async$goto = 0, $async$completer = A._makeAsyncAwaitCompleter(type$.void), $async$self = this, bank;\n'
        '    var $async$fetchClubBankAccount$1 = A._wrapJsFunctionForAsync(function($async$errorCode, $async$result) {\n'
        '      for (;;) switch ($async$goto) {\n'
        '        case 0: $async$goto = 7;\n'
        '          return A._asyncAwait($async$self._club_provider$_repository.getClubBankAccount$1(clubId), $async$fetchClubBankAccount$1);\n'
        f'        case 7: bank = $async$result; $async$self.{bank_account_field} = bank; $async$goto = 1; break;\n'
        '        case 1: return A._asyncReturn(null, $async$completer);\n'
        '      }\n'
        '    });\n'
        '    return A._asyncStartSync($async$fetchClubBankAccount$1, $async$completer);\n'
        '  }\n'
        '};'
    )

    if include_club_wiring:
        parts.append(
            'A.main_closure2.prototype = {\n'
            '  call$1(context) {\n'
            '    var t1 = A.Provider_of(context, false, type$.AuthProvider);\n'
            '    var r = new A.ClubRepository(null);\n'
            '    var t3 = new A.ClubProvider(r, t1, null);\n'
            f'    t1.addListener$1(t3.{cp_reg_getter}());\n'
            '    return t3;\n'
            '  }\n'
            '};'
        )
    if include_session_wiring:
        parts.append(
            'A.main_closure3.prototype = {\n'
            '  call$1(context) {\n'
            '    var t1 = A.Provider_of(context, false, type$.AuthProvider);\n'
            '    var r = new A.SessionRepository(null);\n'
            '    var t4 = new A.SessionProvider(r, t1, null);\n'
            f'    t1.addListener$1(t4.{sp_reg_getter}());\n'
            '    return t4;\n'
            '  }\n'
            '};'
        )
    if include_sp_registration:
        parts.append(f'_instance_0_u(_ = A.SessionProvider.prototype, "{sp_reg_getter}", "{sp_reg_method}", 0);')
    if include_cp_registration:
        parts.append(f'_instance_0_u(_ = A.ClubProvider.prototype, "{cp_reg_getter}", "{cp_reg_method}", 0);')

    return '\n'.join(parts) + '\n'


def build_sc_snapshot(
    *,
    auth_count=1,
    session_count=1,
    club_count=1,
    auth_rooted=True,
    session_rooted=True,
    club_rooted=True,
    current_user_null=False,
    session_id_state='string',       # 'string' | 'null' | 'Session0'
    current_session_state='Session0',  # 'Session0' | 'null' | 'WrongClass'
    current_session_obj_id=410,
    history_state='SessionHistoryPage',  # 'SessionHistoryPage' | 'null' | 'WrongClass'
    history_obj_id=420,
    club_id_state='string',          # 'string' | 'null' | 'Club'
    current_club_state='Club',       # 'Club' | 'null' | 'WrongClass'
    current_club_obj_id=510,
    bank_account_state='BankAccount',  # 'BankAccount' | 'null' | 'WrongClass'
    bank_account_obj_id=520,
    slot_mode='direct',
    listener_slots=None,
    trailing_non_null=False,
    extra_array_slots=0,
    listeners_not_array=False,
):
    b = SyntheticV8SnapshotBuilder()
    root = b.add_node('synthetic', '(GC root)', obj_id=1)
    gc_roots = b.add_node('synthetic', '(GC roots)', obj_id=3)
    b.add_edge(root, 'element', 0, gc_roots)
    null_node = b.add_null_node()

    auth_nodes = []
    for k in range(auth_count):
        a = b.add_node('object', 'AuthProvider', obj_id=100 + k * 2)
        b.add_edge(gc_roots, 'element' if auth_rooted else 'weak', 10 + k, a)
        if current_user_null:
            b.add_edge(a, 'property', '_currentUser', null_node)
        else:
            b.add_edge(a, 'property', '_currentUser', b.add_node('object', 'User'))
        b.add_edge(a, 'property', 'ChangeNotifier__count', b.add_number_node())
        b.add_edge(a, 'property', 'ChangeNotifier__notificationCallStackDepth', b.add_number_node())
        b.add_edge(a, 'property', 'ChangeNotifier__reentrantlyRemovedListeners', b.add_number_node())
        auth_nodes.append(a)

    sp_nodes = []
    for k in range(session_count):
        sp = b.add_node('object', 'SessionProvider', obj_id=200 + k * 2)
        b.add_edge(gc_roots, 'element' if session_rooted else 'weak', 30 + k, sp)
        if auth_nodes:
            b.add_edge(sp, 'property', 'auth', auth_nodes[0])
        if session_id_state == 'null':
            b.add_edge(sp, 'property', '_currentSessionId', null_node)
        elif session_id_state == 'string':
            b.add_edge(sp, 'property', '_currentSessionId', b.add_node('string', 'session-uuid-internal'))
        else:
            b.add_edge(sp, 'property', '_currentSessionId', b.add_node('object', session_id_state))

        if current_session_state == 'null':
            b.add_edge(sp, 'property', '_currentSession', null_node)
        else:
            b.add_edge(sp, 'property', '_currentSession', b.add_node('object', current_session_state, obj_id=current_session_obj_id + k * 2))

        if history_state == 'null':
            b.add_edge(sp, 'property', '_session_provider$_history', null_node)
        else:
            b.add_edge(sp, 'property', '_session_provider$_history', b.add_node('object', history_state, obj_id=history_obj_id + k * 2))
        sp_nodes.append(sp)

    cp_nodes = []
    for k in range(club_count):
        cp = b.add_node('object', 'ClubProvider', obj_id=300 + k * 2)
        b.add_edge(gc_roots, 'element' if club_rooted else 'weak', 50 + k, cp)
        if auth_nodes:
            b.add_edge(cp, 'property', 'auth', auth_nodes[0])
        if club_id_state == 'null':
            b.add_edge(cp, 'property', '_currentClubId', null_node)
        elif club_id_state == 'string':
            b.add_edge(cp, 'property', '_currentClubId', b.add_node('string', 'club-uuid-internal'))
        else:
            b.add_edge(cp, 'property', '_currentClubId', b.add_node('object', club_id_state))

        if current_club_state == 'null':
            b.add_edge(cp, 'property', '_currentClub', null_node)
        else:
            b.add_edge(cp, 'property', '_currentClub', b.add_node('object', current_club_state, obj_id=current_club_obj_id + k * 2))

        if bank_account_state == 'null':
            b.add_edge(cp, 'property', '_currentBankAccount', null_node)
        else:
            b.add_edge(cp, 'property', '_currentBankAccount', b.add_node('object', bank_account_state, obj_id=bank_account_obj_id + k * 2))
        cp_nodes.append(cp)

    if auth_nodes:
        a0 = auth_nodes[0]
        arr = b.add_node('object', 'Object' if listeners_not_array else 'Array')
        b.add_edge(a0, 'property', 'ChangeNotifier__listeners', arr)
        backing = None
        if slot_mode in ('backing', 'both_same', 'both_conflict'):
            backing = b.add_node('array', '(FixedArray)')
            b.add_edge(arr, 'internal', 'elements', backing)

        if listener_slots is None:
            listener_slots = []
            if sp_nodes:
                listener_slots.append({'receiver_kind': 'session', 'receiver_idx': 0, 'method': '_session_provider$_onAuthChanged$0'})
            if cp_nodes:
                listener_slots.append({'receiver_kind': 'club', 'receiver_idx': 0, 'method': '_club_provider$_onAuthChanged$0'})

        bound_closure_proto = b.add_node('object', 'BoundClosure')
        slot_nodes = []
        for idx, spec in enumerate(listener_slots):
            if spec is None or spec.get('kind') == 'null':
                target = null_node
            else:
                target = b.add_node('object', 'tear_off')
                if spec.get('on_instance_only'):
                    b.add_edge(target, 'property', '$_name', b.add_node('string', spec['method']))
                elif spec.get('proto_is_provider'):
                    pnode = sp_nodes[0] if sp_nodes else cp_nodes[0]
                    b.add_edge(target, 'property', '__proto__', pnode)
                    b.add_edge(pnode, 'property', '$_name', b.add_node('string', spec['method']))
                else:
                    gen_proto = b.add_node('object', spec.get('generated_prototype_class', 'Object'))
                    b.add_edge(gen_proto, 'property', '__proto__', bound_closure_proto)
                    if spec.get('method') is not None:
                        b.add_edge(gen_proto, 'property', '$_name', b.add_node('string', spec['method']))
                    b.add_edge(target, 'property', '__proto__', gen_proto)

                rkind = spec.get('receiver_kind')
                ridx = spec.get('receiver_idx', 0)
                recv_etype = 'weak' if spec.get('weak_receiver') else 'property'
                if rkind == 'session' and ridx < len(sp_nodes):
                    b.add_edge(target, recv_etype, '_receiver', sp_nodes[ridx])
                elif rkind == 'club' and ridx < len(cp_nodes):
                    b.add_edge(target, recv_etype, '_receiver', cp_nodes[ridx])
                elif 'receiver_class' in spec:
                    rnode = b.add_node('object', spec['receiver_class'])
                    b.add_edge(gc_roots, 'element', 100 + idx, rnode)
                    b.add_edge(target, recv_etype, '_receiver', rnode)
            slot_nodes.append(target)

        if trailing_non_null:
            slot_nodes.append(b.add_node('object', 'Closure'))

        for _ in range(extra_array_slots):
            slot_nodes.append(null_node)

        for idx, target in enumerate(slot_nodes):
            if slot_mode in ('direct', 'both_same', 'both_conflict'):
                b.add_edge(arr, 'element', idx, target)
            if slot_mode in ('backing', 'both_same'):
                b.add_edge(backing, 'element', idx, target)
            elif slot_mode == 'both_conflict':
                b.add_edge(backing, 'element', idx, b.add_node('object', 'Closure'))

    return b.build_bytes()


def make_sc_cdp(
    *,
    auth_id='100',
    session_id='200',
    club_id='300',
    include_session=True,
    include_club=True,
    count=2,
    after_count=None,
    depth=0,
    removed=0,
    user_null=False,
    after_user_null=None,
    session_id_null=False,
    session_id_type='string',
    current_session_null=False,
    current_session_class='Session0',
    history_null=False,
    history_class='SessionHistoryPage',
    club_id_null=False,
    club_id_type='string',
    current_club_null=False,
    current_club_class='Club',
    bank_null=False,
    bank_class='BankAccount',
    time_origin_before=12345.6,
    time_origin_after=12345.6,
    object_group_released=True,
    atomic_claim=False,
    cdp_errors=None,
):
    if after_count is None:
        after_count = count
    if after_user_null is None:
        after_user_null = user_null

    user_before = {
        'present': True,
        'has_getter': False,
        'is_null': user_null,
        'value_type': 'null' if user_null else 'object',
        'class_name': None if user_null else 'User',
    }
    user_after = {
        'present': True,
        'has_getter': False,
        'is_null': after_user_null,
        'value_type': 'null' if after_user_null else 'object',
        'class_name': None if after_user_null else 'User',
    }

    obs = {
        'observation_mode': sc_graph.OBSERVATION_MODE,
        'atomic_claim': atomic_claim,
        'auth_heap_object_id': auth_id,
        'time_origin_before': time_origin_before,
        'time_origin_after': time_origin_after,
        'before': {
            'ChangeNotifier__count': count,
            'ChangeNotifier__notificationCallStackDepth': depth,
            'ChangeNotifier__reentrantlyRemovedListeners': removed,
        },
        'after': {
            'ChangeNotifier__count': after_count,
            'ChangeNotifier__notificationCallStackDepth': depth,
            'ChangeNotifier__reentrantlyRemovedListeners': removed,
        },
        'counters_match': count == after_count,
        'quiescent': count == after_count and depth == 0 and removed == 0,
        'auth_current_user': user_before,
        'auth_current_user_before': user_before,
        'auth_current_user_after': user_after,
        'cdp_errors': list(cdp_errors or []),
        'object_group_released': object_group_released,
    }
    if include_session and session_id is not None:
        obs['session_heap_object_id'] = session_id
        obs['session_selected_fields'] = {
            '_currentSessionId': {
                'present': True,
                'has_getter': False,
                'is_null': session_id_null,
                'value_type': 'null' if session_id_null else session_id_type,
                'class_name': None if (session_id_null or session_id_type == 'string') else 'Session0',
            },
            '_currentSession': {
                'present': True,
                'has_getter': False,
                'is_null': current_session_null,
                'value_type': 'null' if current_session_null else 'object',
                'class_name': None if current_session_null else current_session_class,
            },
            '_session_provider$_history': {
                'present': True,
                'has_getter': False,
                'is_null': history_null,
                'value_type': 'null' if history_null else 'object',
                'class_name': None if history_null else history_class,
            },
        }
    if include_club and club_id is not None:
        obs['club_heap_object_id'] = club_id
        obs['club_selected_fields'] = {
            '_currentClubId': {
                'present': True,
                'has_getter': False,
                'is_null': club_id_null,
                'value_type': 'null' if club_id_null else club_id_type,
                'class_name': None if (club_id_null or club_id_type == 'string') else 'Club',
            },
            '_currentClub': {
                'present': True,
                'has_getter': False,
                'is_null': current_club_null,
                'value_type': 'null' if current_club_null else 'object',
                'class_name': None if current_club_null else current_club_class,
            },
            '_currentBankAccount': {
                'present': True,
                'has_getter': False,
                'is_null': bank_null,
                'value_type': 'null' if bank_null else 'object',
                'class_name': None if bank_null else bank_class,
            },
        }
    return obs


def _write_lf(path: Path, text: str) -> None:
    path.write_bytes(text.encode('utf-8'))


def _build_full_sc_bundle(
    bundle_dir: Path,
    build_dir: Path,
    *,
    bank_populated: bool = True,
    require_bank_account: bool = False,
    mutate_fn=None,
) -> None:
    bundle_dir.mkdir(parents=True, exist_ok=True)
    main_js = make_synthetic_sc_main_js()
    _write_lf(build_dir / 'main.dart.js', main_js)
    _write_lf(build_dir / 'index.html', '<html></html>\n')
    main_sha = hashlib.sha256((build_dir / 'main.dart.js').read_bytes()).hexdigest()
    idx_sha = hashlib.sha256((build_dir / 'index.html').read_bytes()).hexdigest()

    binding = sc_graph.extract_listener_source_binding(build_dir, expected_main_js_sha=main_sha)
    assert binding['ok'] is True, binding

    def _epoch_rec(cycle_num, actor, ep_name, prev_ids=None):
        if cycle_num == 1 and ep_name == 'baseline':
            snap = build_sc_snapshot(
                auth_count=1, session_count=1, club_count=0,
                current_user_null=True,
                session_id_state='null', current_session_state='null', history_state='null',
                listener_slots=[{'receiver_kind': 'session', 'receiver_idx': 0, 'method': '_session_provider$_onAuthChanged$0'}],
            )
            cdp = make_sc_cdp(
                include_session=True, include_club=False, count=1,
                user_null=True, session_id_null=True, current_session_null=True, history_null=True,
            )
        elif ep_name == 'baseline':
            snap = build_sc_snapshot(
                auth_count=1, session_count=1, club_count=1,
                current_user_null=True,
                session_id_state='null', current_session_state='null', history_state='null',
                club_id_state='null', current_club_state='null', bank_account_state='null',
            )
            cdp = make_sc_cdp(
                count=2, user_null=True,
                session_id_null=True, current_session_null=True, history_null=True,
                club_id_null=True, current_club_null=True, bank_null=True,
            )
        elif ep_name == 'owner_active':
            snap = build_sc_snapshot(
                auth_count=1, session_count=1, club_count=1,
                current_user_null=False,
                session_id_state='string', current_session_state='Session0',
                current_session_obj_id=410 + cycle_num * 100,
                history_state='SessionHistoryPage', history_obj_id=420 + cycle_num * 100,
                club_id_state='string', current_club_state='Club',
                current_club_obj_id=510 + cycle_num * 100,
                bank_account_state='BankAccount' if bank_populated else 'null',
                bank_account_obj_id=520 + cycle_num * 100,
            )
            cdp = make_sc_cdp(
                count=2, user_null=False,
                session_id_null=False, current_session_null=False, history_null=False,
                club_id_null=False, current_club_null=False, bank_null=not bank_populated,
            )
        elif ep_name == 'post_logout':
            snap = build_sc_snapshot(
                auth_count=1, session_count=1, club_count=1,
                current_user_null=True,
                session_id_state='null', current_session_state='null', history_state='null',
                club_id_state='null', current_club_state='null', bank_account_state='null',
            )
            cdp = make_sc_cdp(
                count=2, user_null=True,
                session_id_null=True, current_session_null=True, history_null=True,
                club_id_null=True, current_club_null=True, bank_null=True,
            )
        else:  # post_actor
            is_cohost = actor == 'cohost'
            snap = build_sc_snapshot(
                auth_count=1, session_count=1, club_count=1,
                current_user_null=False,
                session_id_state='string' if is_cohost else 'null',
                current_session_state='Session0' if is_cohost else 'null',
                current_session_obj_id=810 + cycle_num * 100,
                history_state='SessionHistoryPage', history_obj_id=820 + cycle_num * 100,
                club_id_state='null', current_club_state='null', bank_account_state='null',
            )
            cdp = make_sc_cdp(
                count=2, user_null=False,
                session_id_null=not is_cohost, current_session_null=not is_cohost, history_null=False,
                club_id_null=True, current_club_null=True, bank_null=True,
            )

        lg = sc_graph.scan_snapshot(
            snap,
            binding=binding,
            epoch=ep_name,
            cycle_num=cycle_num,
            actor=actor,
            cdp_observations=cdp,
            time_origin=12345.6,
            require_bank_account=require_bank_account,
            previous_owner_field_ids=prev_ids,
        )
        assert lg['ok'] is True, f'c{cycle_num}_{ep_name} unexpected fail: {lg}'
        return {
            'epoch': ep_name,
            'ok': True,
            'time_origin': 12345.6,
            'size_bytes': len(snap),
            'sha256_12': lg['snapshot_sha256_12'],
            'listener_graph': lg,
        }

    cycles = []
    for cnum, actor in ((1, 'cohost'), (2, 'member')):
        epochs = {}
        epochs['baseline'] = _epoch_rec(cnum, actor, 'baseline')
        epochs['owner_active'] = _epoch_rec(cnum, actor, 'owner_active')
        prev_ids = sc_graph.extract_owner_field_object_ids(epochs['owner_active']['listener_graph'], binding)
        epochs['post_logout'] = _epoch_rec(cnum, actor, 'post_logout')
        epochs['post_actor'] = _epoch_rec(cnum, actor, 'post_actor', prev_ids=prev_ids)
        cycles.append({
            'cycle': cnum,
            'actor': actor,
            'same_document': True,
            'time_origin': 12345.6,
            'epochs': epochs,
            'verdict': {'verdict': 'PASS' if bank_populated else 'PARTIAL_NOT_RUN'},
        })

    overall_gate = 'PASS' if bank_populated else 'PARTIAL_CLUB_BANK_NOT_RUN'
    summary = {
        'gate': 'V2b — AuthProvider -> SessionProvider / ClubProvider finite listener graph',
        'coverage_profile': 'session_club_auth_listener',
        'claim_scope': sc_graph.CLAIM_SCOPE,
        'observation_mode': sc_graph.OBSERVATION_MODE,
        'atomic_claim': False,
        'status': 'RUN',
        'verdict': 'PASS' if bank_populated else 'PARTIAL_NOT_RUN',
        'tested_source_sha': 'a' * 40,
        'git_dirty': False,
        'same_document_across_cycles': True,
        'environment': {
            'build': {
                'mode': 'profile',
                'reused': False,
                'started_at': '2026-11-16T01:00:00Z',
                'served_match': True,
                'artifacts': {'index.html': idx_sha, 'main.dart.js': main_sha},
            }
        },
        'sentinels': {'probe': {'available': True, 'length': 24, 'sha256_12': '0123456789ab'}},
        'listener_graph_binding': binding,
        'session_club_assessment': {
            'session_listener_gate': 'PASS',
            'club_core_listener_gate': 'PASS',
            'club_bank_account_gate': 'PASS' if bank_populated else 'NOT_RUN',
            'session_club_listener_gate': overall_gate,
            'claim_scope': sc_graph.CLAIM_SCOPE,
            'observation_mode': sc_graph.OBSERVATION_MODE,
            'atomic_claim': False,
        },
        'cycles': cycles,
        'cleanup': {
            'ok': True,
            'dump_dir_outside_repo': True,
            'dumps_dir_removed': True,
            'chrome_profile_dir_removed': True,
            'disposable_instructions_club_created': True,
            'disposable_instructions_session_created': True,
            'disposable_instructions_removed': True,
            'disposable_instructions_verified_absent': True,
            'disposable_instructions_cleanup_verified': True,
            'zero_mutation_verified': True,
            'baseline_fingerprint_equal': True,
            'public_rows_schema_roles_equal': True,
            'auth_rows_excluded': True,
            'raw_snapshots_remaining': 0,
            'recovery_state_retained': False,
        },
    }
    if mutate_fn:
        mutate_fn(summary)

    _write_lf(bundle_dir / 'summary.json', json.dumps(summary, indent=2) + '\n')
    _write_lf(bundle_dir / 'source_binding.json', json.dumps(binding, indent=2) + '\n')
    _write_lf(bundle_dir / 'run.log', 'synthetic log\n')
    _write_lf(bundle_dir / 'report.md', '# Report\n')

    manifest = []
    for fname in ('summary.json', 'source_binding.json', 'run.log', 'report.md'):
        digest = hashlib.sha256((bundle_dir / fname).read_bytes()).hexdigest()
        manifest.append(f'{digest}  {fname}')
    _write_lf(bundle_dir / 'hashes.sha256', '\n'.join(manifest) + '\n')


class TestSourceBinding(unittest.TestCase):
    def test_executable_binding_succeeds_and_rejects_comment_or_literal_masking(self):
        with tempfile.TemporaryDirectory() as tmp:
            bdir = Path(tmp)
            js = make_synthetic_sc_main_js(use_dart2js_async_shape=True)
            _write_lf(bdir / 'main.dart.js', js)
            sha = hashlib.sha256(js.encode('utf-8')).hexdigest()

            res = sc_graph.extract_listener_source_binding(bdir, expected_main_js_sha=sha)
            self.assertTrue(res['ok'], res)
            self.assertEqual(res['models']['session']['constructor_name'], 'Session0')
            self.assertEqual(res['models']['club']['constructor_name'], 'Club')
            self.assertEqual(res['models']['bank_account']['constructor_name'], 'BankAccount')
            self.assertEqual(res['session_provider']['session_id_field'], '_currentSessionId')
            self.assertEqual(res['session_provider']['current_session_field'], '_currentSession')
            self.assertEqual(res['session_provider']['history_field'], '_session_provider$_history')
            self.assertEqual(res['club_provider']['club_id_field'], '_currentClubId')
            self.assertEqual(res['club_provider']['current_club_field'], '_currentClub')
            self.assertEqual(res['club_provider']['bank_account_field'], '_currentBankAccount')

            bad_sha = sc_graph.extract_listener_source_binding(bdir, expected_main_js_sha='f' * 64)
            self.assertFalse(bad_sha['ok'])

            for label, mutated in (
                ('block_comment', '/*\n' + js + '\n*/'),
                ('quoted_string', 'var fake = ' + json.dumps(js) + ';'),
                ('missing_sp_reg', make_synthetic_sc_main_js(include_sp_registration=False)),
                ('missing_cp_reg', make_synthetic_sc_main_js(include_cp_registration=False)),
                ('missing_sp_reset', make_synthetic_sc_main_js(include_sp_reset=False)),
                ('missing_cp_reset', make_synthetic_sc_main_js(include_cp_reset=False)),
                ('missing_cp_bank_reset', make_synthetic_sc_main_js(include_cp_bank_reset=False)),
                ('missing_session_wiring', make_synthetic_sc_main_js(include_session_wiring=False)),
                ('missing_club_wiring', make_synthetic_sc_main_js(include_club_wiring=False)),
            ):
                with self.subTest(label=label):
                    _write_lf(bdir / 'main.dart.js', mutated)
                    r = sc_graph.extract_listener_source_binding(bdir)
                    self.assertFalse(r['ok'], f'{label} unexpectedly succeeded: {r}')

    @unittest.skipUnless((ROOT / 'build' / 'web' / 'main.dart.js').is_file(), 'build/web/main.dart.js not present')
    def test_real_build_web_main_dart_js_binding_if_present(self):
        res = sc_graph.extract_listener_source_binding(ROOT / 'build' / 'web')
        self.assertTrue(res['ok'], res)
        self.assertEqual(res['models']['session']['constructor_name'], 'Session0')
        self.assertEqual(res['session_provider']['registration_method'], '_session_provider$_onAuthChanged$0')
        self.assertEqual(res['club_provider']['registration_method'], '_club_provider$_onAuthChanged$0')

    def test_sc1_oversized_main_dart_js_fails_closed_via_base_bounded_reader(self):
        with tempfile.TemporaryDirectory() as tmp:
            bdir = Path(tmp)
            js = make_synthetic_sc_main_js()
            _write_lf(bdir / 'main.dart.js', js)
            with mock.patch.object(sc_graph.base_graph, 'MAX_INPUT_BYTES', 128):
                res = sc_graph.extract_listener_source_binding(bdir)
                self.assertFalse(res['ok'])
                self.assertEqual(res.get('error'), 'main_dart_js_exceeds_max_bytes')

    def test_sc2_async_a_alias_positive_and_negative_controls(self):
        with tempfile.TemporaryDirectory() as tmp:
            bdir = Path(tmp)
            # Positive control: ALL repo deserializers go exclusively through $async$temp1 = A (no direct A. calls)
            js_pos = make_synthetic_sc_main_js().replace(
                'A.SessionHistoryPage_SessionHistoryPage$fromResponse($async$result, limit, offset)',
                '$async$temp1.SessionHistoryPage_SessionHistoryPage$fromResponse($async$result, limit, offset)',
            ).replace(
                'var $async$goto = 0, $async$completer = A._makeAsyncAwaitCompleter(type$.SessionHistoryPage), $async$returnValue, $async$self = this;',
                'var $async$goto = 0, $async$completer = A._makeAsyncAwaitCompleter(type$.SessionHistoryPage), $async$returnValue, $async$self = this, $async$temp1 = A;',
            )
            _write_lf(bdir / 'main.dart.js', js_pos)
            pos_res = sc_graph.extract_listener_source_binding(bdir)
            self.assertTrue(pos_res['ok'], pos_res)

            # Negative SC2 controls: comment-masked, string-masked, overwritten, obj-property, post-use, or wrong alias
            base_js = make_synthetic_sc_main_js()
            neg_variants = {
                'comment_masked_alias': base_js.replace(
                    'var $async$goto = 0, $async$completer = A._makeAsyncAwaitCompleter(type$.Session), $async$returnValue, $async$self = this, $async$temp1 = A;',
                    '/* var $async$temp1 = A; */ var $async$goto = 0, $async$completer = A._makeAsyncAwaitCompleter(type$.Session), $async$returnValue, $async$self = this, $async$temp1 = FakeA;',
                ),
                'string_masked_alias': base_js.replace(
                    'var $async$goto = 0, $async$completer = A._makeAsyncAwaitCompleter(type$.Session), $async$returnValue, $async$self = this, $async$temp1 = A;',
                    'var s = "$async$temp1 = A;"; var $async$goto = 0, $async$completer = A._makeAsyncAwaitCompleter(type$.Session), $async$returnValue, $async$self = this, $async$temp1 = FakeA;',
                ),
                'overwritten_alias': base_js.replace(
                    'case 0: $async$goto = 3;',
                    'case 0: $async$temp1 = EvilA; $async$goto = 3;',
                    1,
                ),
                'compound_mutated_alias': base_js.replace(
                    'case 0: $async$goto = 3;',
                    'case 0: $async$temp1 += 1; $async$goto = 3;',
                    1,
                ),
                'unbound_identifier_alias': base_js.replace(
                    '$async$temp1.Session_Session$fromJson($async$result)',
                    'FakeA.Session_Session$fromJson($async$result)',
                ),
                'obj_property_alias': base_js.replace(
                    'var $async$goto = 0, $async$completer = A._makeAsyncAwaitCompleter(type$.Session), $async$returnValue, $async$self = this, $async$temp1 = A;',
                    'var obj = {}; obj.$async$temp1 = A; var $async$goto = 0, $async$completer = A._makeAsyncAwaitCompleter(type$.Session), $async$returnValue, $async$self = this;',
                ),
            }
            for label, mutated in neg_variants.items():
                with self.subTest(label=label):
                    _write_lf(bdir / 'main.dart.js', mutated)
                    r = sc_graph.extract_listener_source_binding(bdir)
                    self.assertFalse(r['ok'], f'{label} unexpectedly succeeded: {r}')

    def test_sc4_rpc_to_provider_value_flow_rejects_discarded_overwritten_null(self):
        # 1. Exact SC4 offline probe on _verify_repo_rpc_model_method must return False
        probe_repo_js = (
            'var A = {\n'
            '  Session0: function Session0(t0, t1) { this.id = t0; this.title = t1; },\n'
            '  Session_Session$fromJson(j) { return new A.Session0(j.$index(0, "id"), j.$index(0, "title")); }\n'
            '};\n'
            'A.SessionRepository.prototype = {\n'
            '  getSessionDetail$1(id) { this.client.rpc("get_session_public_detail"); A.Session_Session$fromJson(id); return null; }\n'
            '};\n'
        )
        probe_exe, _ = sc_graph.pi_verifier._executable_source(probe_repo_js)
        probe_methods = sc_graph._extract_repo_methods(probe_exe, 'SessionRepository')
        self.assertFalse(sc_graph._verify_repo_rpc_model_method(
            probe_repo_js,
            probe_exe,
            probe_methods,
            'getSessionDetail$1',
            rpc_name='get_session_public_detail',
            model_class='Session0',
            deserializer_names=('Session_Session$fromJson',),
        ))

        # Direct helper RED/GREEN controls for SC4 value-preserving expression grammar
        self.assertFalse(sc_graph._rhs_produces_model_from_vars(
            '$async$temp1.Session_Session$fromJson(($async$result, {}))',
            source_vars={'$async$result'},
            valid_desers={'Session_Session$fromJson'},
            a_alias_set={'A', '$async$temp1'},
            a_alias_defs={'A': -1, '$async$temp1': 10},
            stmt_abs_pos=200,
            model_class='Session0',
            allow_model_ctor=True,
        ))
        self.assertFalse(sc_graph._rhs_produces_model_from_vars(
            '$async$temp1.Session_Session$fromJson(false ? $async$result : {})',
            source_vars={'$async$result'},
            valid_desers={'Session_Session$fromJson'},
            a_alias_set={'A', '$async$temp1'},
            a_alias_defs={'A': -1, '$async$temp1': 10},
            stmt_abs_pos=200,
            model_class='Session0',
            allow_model_ctor=True,
        ))
        self.assertFalse(sc_graph._rhs_produces_model_from_vars(
            'new A.Session0(($async$result, {}), "t")',
            source_vars={'$async$result'},
            valid_desers={'Session_Session$fromJson'},
            a_alias_set={'A'},
            a_alias_defs={'A': -1},
            stmt_abs_pos=200,
            model_class='Session0',
            allow_model_ctor=True,
        ))
        self.assertTrue(sc_graph._rhs_produces_model_from_vars(
            '$async$temp1.Session_Session$fromJson($async$temp2.LinkedHashMap_LinkedHashMap$from($async$temp3._as($async$result), t1, t2))',
            source_vars={'$async$result'},
            valid_desers={'Session_Session$fromJson'},
            a_alias_set={'A', '$async$temp1', '$async$temp2'},
            a_alias_defs={'A': -1, '$async$temp1': 10, '$async$temp2': 20},
            type_alias_set={'$async$temp3'},
            type_alias_defs={'$async$temp3': 30},
            stmt_abs_pos=200,
            model_class='Session0',
            allow_model_ctor=True,
        ))

        base_js = make_synthetic_sc_main_js()
        with tempfile.TemporaryDirectory() as tmp:
            bdir = Path(tmp)
            # 2. Full binding positive control with real main.dart.js null-response guard in getClubBankAccount & appending in fetchSessionHistory
            real_compat_js = base_js.replace(
                'case 3: $async$returnValue = A.BankAccount_BankAccount$fromJson($async$result); $async$goto = 1; break;',
                'case 3: response = $async$result; if (response == null) { $async$returnValue = null; $async$goto = 1; break; } '
                '$async$returnValue = A.BankAccount_BankAccount$fromJson(A.LinkedHashMap_LinkedHashMap$from(type$.Map_dynamic_dynamic._as(response), t1, t2)); $async$goto = 1; break;',
            ).replace(
                'var $async$goto = 0, $async$completer = A._makeAsyncAwaitCompleter(type$.nullable_BankAccount), $async$returnValue, $async$self = this;',
                'var $async$goto = 0, $async$completer = A._makeAsyncAwaitCompleter(type$.nullable_BankAccount), $async$returnValue, $async$self = this, t1, t2, response;',
            ).replace(
                'case 7: page = $async$result; $async$self._session_provider$_history = new A.SessionHistoryPage(page.sessions); $async$goto = 1; break;',
                'case 7: page = $async$result; if (appending) { t2 = A.List_List$_of(previous.sessions, type$.Session); merged0 = $async$self._uniqueSessions$1(t2); } '
                'else merged0 = $async$self._uniqueSessions$1(page.sessions); merged = merged0; '
                '$async$self._session_provider$_history = new A.SessionHistoryPage(merged, limit, 0, page.get$hasMore()); $async$goto = 1; break;',
            )
            _write_lf(bdir / 'main.dart.js', real_compat_js)
            compat_res = sc_graph.extract_listener_source_binding(bdir)
            self.assertTrue(compat_res['ok'], compat_res)

            # 3. Full binding negative controls for discarded, ignored, overwritten, or null-return flows
            neg_flows = {
                'repo_sync_discarded_and_return_null': base_js.replace(
                    'getSessionDetail$body$SessionRepository(sessionId) {',
                    'getSessionDetail$body$SessionRepository(sessionId) { this._session_repository$_client.rpc("get_session_public_detail"); A.Session_Session$fromJson(sessionId); return null; }, _unused() {',
                ),
                'repo_unawaited_rpc_and_dummy_await': base_js.replace(
                    'case 0: $async$goto = 3; return A._asyncAwait($async$self._session_repository$_client.rpc$1$2$params("get_session_public_detail", {}, null), $async$getSessionDetail$1);',
                    'case 0: $async$self._session_repository$_client.rpc$1$2$params("get_session_public_detail", {}, null); $async$goto = 3; return A._asyncAwait(otherPromise(), $async$getSessionDetail$1);',
                ),
                'repo_deser_ignores_async_result': base_js.replace(
                    '$async$temp1.Session_Session$fromJson($async$result)',
                    '$async$temp1.Session_Session$fromJson(sessionId)',
                ),
                'repo_deser_discarded_return_null': base_js.replace(
                    '$async$returnValue = $async$temp1.Session_Session$fromJson($async$result);',
                    '$async$temp1.Session_Session$fromJson($async$result); $async$returnValue = null;',
                ),
                'repo_temp_var_overwritten_before_return': base_js.replace(
                    '$async$returnValue = $async$temp1.Session_Session$fromJson($async$result);',
                    'var tmp = $async$temp1.Session_Session$fromJson($async$result); tmp = null; $async$returnValue = tmp;',
                ),
                'repo_return_value_overwritten_in_resume_case': base_js.replace(
                    '$async$returnValue = $async$temp1.Session_Session$fromJson($async$result);',
                    '$async$returnValue = $async$temp1.Session_Session$fromJson($async$result); $async$returnValue = null;',
                ),
                'repo_return_value_overwritten_in_return_case': base_js.replace(
                    'case 1: return A._asyncReturn($async$returnValue, $async$completer);',
                    'case 1: $async$returnValue = null; return A._asyncReturn($async$returnValue, $async$completer);',
                    1,
                ),
                'poisoned_deserializer_can_return_null': base_js.replace(
                    'Session_Session$fromJson(json) {\n'
                    '    return new A.Session0(json.$index(0, "id"), json.$index(0, "title"));\n'
                    '  },',
                    'Session_Session$fromJson(json) {\n'
                    '    if (false) return new A.Session0(json.$index(0, "id"), json.$index(0, "title"));\n'
                    '    return null;\n'
                    '  },',
                ),
                'provider_overwrites_current_session_after_assign': base_js.replace(
                    '$async$self._currentSession = session;',
                    '$async$self._currentSession = session; $async$self._currentSession = null;',
                ),
                'provider_history_ignores_awaited_page': base_js.replace(
                    '$async$self._session_provider$_history = new A.SessionHistoryPage(page.sessions);',
                    '$async$self._session_provider$_history = new A.SessionHistoryPage([]);',
                ),
                'repo_deser_comma_discard': base_js.replace(
                    '$async$returnValue = $async$temp1.Session_Session$fromJson($async$result);',
                    '$async$returnValue = $async$temp1.Session_Session$fromJson(($async$result, {}));',
                ),
                'repo_deser_false_ternary_discard': base_js.replace(
                    '$async$returnValue = $async$temp1.Session_Session$fromJson($async$result);',
                    '$async$returnValue = $async$temp1.Session_Session$fromJson(false ? $async$result : {});',
                ),
                'repo_alias_comma_discard': base_js.replace(
                    '$async$returnValue = $async$temp1.Session_Session$fromJson($async$result);',
                    'var bogus = ($async$result, {}); $async$returnValue = $async$temp1.Session_Session$fromJson(bogus);',
                ),
                'repo_alias_false_ternary_discard': base_js.replace(
                    '$async$returnValue = $async$temp1.Session_Session$fromJson($async$result);',
                    'var bogus = false ? $async$result : {}; $async$returnValue = $async$temp1.Session_Session$fromJson(bogus);',
                ),
                'repo_model_alias_comma_discard': base_js.replace(
                    '$async$returnValue = $async$temp1.Session_Session$fromJson($async$result);',
                    'var m = $async$temp1.Session_Session$fromJson($async$result); var bogus = (m, null); $async$returnValue = bogus;',
                ),
                'repo_model_alias_false_ternary_discard': base_js.replace(
                    '$async$returnValue = $async$temp1.Session_Session$fromJson($async$result);',
                    'var m = $async$temp1.Session_Session$fromJson($async$result); var bogus = false ? m : null; $async$returnValue = bogus;',
                ),
                'repo_history_wrong_arg_position': base_js.replace(
                    'A.SessionHistoryPage_SessionHistoryPage$fromResponse($async$result, limit, offset)',
                    'A.SessionHistoryPage_SessionHistoryPage$fromResponse([], $async$result, offset)',
                ),
                'provider_alias_comma_discard': base_js.replace(
                    'session = $async$result; $async$self._currentSession = session;',
                    'session = ($async$result, {}); $async$self._currentSession = session;',
                ),
                'provider_alias_false_ternary_discard': base_js.replace(
                    'session = $async$result; $async$self._currentSession = session;',
                    'session = false ? $async$result : {}; $async$self._currentSession = session;',
                ),
                'provider_history_ctor_comma_discard': base_js.replace(
                    '$async$self._session_provider$_history = new A.SessionHistoryPage(page.sessions);',
                    '$async$self._session_provider$_history = new A.SessionHistoryPage((page.sessions, []));',
                ),
                'provider_history_ctor_false_ternary_discard': base_js.replace(
                    '$async$self._session_provider$_history = new A.SessionHistoryPage(page.sessions);',
                    '$async$self._session_provider$_history = new A.SessionHistoryPage(false ? page.sessions : []);',
                ),
                'provider_history_res_in_trailing_arg_only': base_js.replace(
                    '$async$self._session_provider$_history = new A.SessionHistoryPage(page.sessions);',
                    '$async$self._session_provider$_history = new A.SessionHistoryPage([], 10, 0, page.get$hasMore());',
                ),
                'provider_id_ternary_discard': base_js.replace(
                    '$async$self._currentSessionId = sessionId;',
                    '$async$self._currentSessionId = sessionId ? "" : "";',
                ),
                'repo_parenthesized_overwrite_null': base_js.replace(
                    '$async$returnValue = $async$temp1.Session_Session$fromJson($async$result);',
                    '$async$returnValue = $async$temp1.Session_Session$fromJson($async$result); ($async$returnValue = null);',
                ),
                'provider_parenthesized_overwrite_null': base_js.replace(
                    '$async$self._currentSession = session;',
                    '$async$self._currentSession = session; ($async$self._currentSession = null);',
                ),
            }
            for label, mutated in neg_flows.items():
                with self.subTest(label=label):
                    _write_lf(bdir / 'main.dart.js', mutated)
                    r = sc_graph.extract_listener_source_binding(bdir)
                    self.assertFalse(r['ok'], f'{label} unexpectedly succeeded: {r}')


class TestRedControlsScanner(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.bdir = Path(self._tmp.name)
        js = make_synthetic_sc_main_js()
        _write_lf(self.bdir / 'main.dart.js', js)
        self.binding = sc_graph.extract_listener_source_binding(self.bdir)
        assert self.binding['ok'] is True

    def tearDown(self):
        self._tmp.cleanup()

    def test_wrong_receiver_rejected(self):
        # RED: mismatched, missing, weak/genuinely unrooted, or non-provider receiver MUST FAIL
        for label, snap_kwargs, slots in (
            ('session_bound_to_club', {}, [
                {'receiver_kind': 'club', 'receiver_idx': 0, 'method': '_session_provider$_onAuthChanged$0'},
                {'receiver_kind': 'club', 'receiver_idx': 0, 'method': '_club_provider$_onAuthChanged$0'},
            ]),
            ('session_missing_receiver', {}, [
                {'receiver_kind': None, 'method': '_session_provider$_onAuthChanged$0'},
                {'receiver_kind': 'club', 'receiver_idx': 0, 'method': '_club_provider$_onAuthChanged$0'},
            ]),
            ('session_weak_receiver_and_unrooted', {'session_rooted': False}, [
                {'receiver_kind': 'session', 'receiver_idx': 0, 'weak_receiver': True, 'method': '_session_provider$_onAuthChanged$0'},
                {'receiver_kind': 'club', 'receiver_idx': 0, 'method': '_club_provider$_onAuthChanged$0'},
            ]),
            ('club_bound_to_weak_receiver', {}, [
                {'receiver_kind': 'session', 'receiver_idx': 0, 'method': '_session_provider$_onAuthChanged$0'},
                {'receiver_kind': 'club', 'receiver_idx': 0, 'weak_receiver': True, 'method': '_club_provider$_onAuthChanged$0'},
            ]),
            ('session_bound_to_user_object', {}, [
                {'receiver_class': 'User', 'method': '_session_provider$_onAuthChanged$0'},
                {'receiver_kind': 'club', 'receiver_idx': 0, 'method': '_club_provider$_onAuthChanged$0'},
            ]),
            ('club_bound_to_object', {}, [
                {'receiver_kind': 'session', 'receiver_idx': 0, 'method': '_session_provider$_onAuthChanged$0'},
                {'receiver_class': 'Object', 'method': '_club_provider$_onAuthChanged$0'},
            ]),
        ):
            with self.subTest(label=label):
                snap = build_sc_snapshot(listener_slots=slots, **snap_kwargs)
                cdp = make_sc_cdp(bank_null=False)
                res = sc_graph.scan_snapshot(snap, binding=self.binding, epoch='owner_active', cycle_num=1, actor='cohost', cdp_observations=cdp, time_origin=12345.6)
                self.assertEqual(res['verdict'], 'FAIL')

    def test_callback_only_rooting_of_providers_passes(self):
        # Honest positive: strong AuthProvider -> listeners -> tear_off -> _receiver strongly roots Session/Club even with weak direct GC root
        for label, snap_kwargs in (
            ('session_callback_only_rooted', {'session_rooted': False}),
            ('club_callback_only_rooted', {'club_rooted': False}),
        ):
            with self.subTest(label=label):
                snap = build_sc_snapshot(**snap_kwargs)
                cdp = make_sc_cdp(bank_null=False)
                res = sc_graph.scan_snapshot(snap, binding=self.binding, epoch='owner_active', cycle_num=1, actor='cohost', cdp_observations=cdp, time_origin=12345.6)
                self.assertEqual(res['verdict'], 'PASS', res)

    def test_wrong_method_and_prototype_spoof_rejected(self):
        for label, slots in (
            ('wrong_method_on_session', [
                {'receiver_kind': 'session', 'receiver_idx': 0, 'method': 'wrongMethod$0'},
                {'receiver_kind': 'club', 'receiver_idx': 0, 'method': '_club_provider$_onAuthChanged$0'},
            ]),
            ('instance_only_spoof', [
                {'receiver_kind': 'session', 'receiver_idx': 0, 'method': '_session_provider$_onAuthChanged$0', 'on_instance_only': True},
                {'receiver_kind': 'club', 'receiver_idx': 0, 'method': '_club_provider$_onAuthChanged$0'},
            ]),
            ('proto_is_provider_spoof', [
                {'receiver_kind': 'session', 'receiver_idx': 0, 'method': '_session_provider$_onAuthChanged$0'},
                {'receiver_kind': 'club', 'receiver_idx': 0, 'method': '_club_provider$_onAuthChanged$0', 'proto_is_provider': True},
            ]),
        ):
            with self.subTest(label=label):
                snap = build_sc_snapshot(listener_slots=slots)
                cdp = make_sc_cdp(bank_null=False)
                res = sc_graph.scan_snapshot(snap, binding=self.binding, epoch='owner_active', cycle_num=1, actor='cohost', cdp_observations=cdp, time_origin=12345.6)
                self.assertEqual(res['verdict'], 'FAIL')

    def test_duplicate_provider_and_duplicate_listener_rejected(self):
        dup_sp = build_sc_snapshot(session_count=2)
        self.assertEqual(
            sc_graph.scan_snapshot(dup_sp, binding=self.binding, epoch='owner_active', cycle_num=1, actor='cohost', cdp_observations=make_sc_cdp(), time_origin=12345.6)['verdict'],
            'FAIL',
        )

        dup_cp = build_sc_snapshot(club_count=2)
        self.assertEqual(
            sc_graph.scan_snapshot(dup_cp, binding=self.binding, epoch='owner_active', cycle_num=1, actor='cohost', cdp_observations=make_sc_cdp(), time_origin=12345.6)['verdict'],
            'FAIL',
        )

        dup_listener = build_sc_snapshot(
            listener_slots=[
                {'receiver_kind': 'session', 'receiver_idx': 0, 'method': '_session_provider$_onAuthChanged$0'},
                {'receiver_kind': 'session', 'receiver_idx': 0, 'method': '_session_provider$_onAuthChanged$0'},
                {'receiver_kind': 'club', 'receiver_idx': 0, 'method': '_club_provider$_onAuthChanged$0'},
            ],
        )
        res = sc_graph.scan_snapshot(dup_listener, binding=self.binding, epoch='owner_active', cycle_num=1, actor='cohost', cdp_observations=make_sc_cdp(count=3), time_origin=12345.6)
        self.assertEqual(res['verdict'], 'FAIL')

    def test_zero_provider_after_required_load_vs_lazy_baseline(self):
        # Cycle 1 baseline with ClubProvider=0 (SessionProvider=1) -> NOT_RUN_LAZY for ClubProvider, PASS for SessionProvider
        snap_lazy = build_sc_snapshot(
            session_count=1, club_count=0, current_user_null=True,
            session_id_state='null', current_session_state='null', history_state='null',
            listener_slots=[{'receiver_kind': 'session', 'receiver_idx': 0, 'method': '_session_provider$_onAuthChanged$0'}],
        )
        cdp_lazy = make_sc_cdp(include_club=False, count=1, user_null=True, session_id_null=True, current_session_null=True, history_null=True)
        res_c1_base = sc_graph.scan_snapshot(snap_lazy, binding=self.binding, epoch='baseline', cycle_num=1, actor='cohost', cdp_observations=cdp_lazy, time_origin=12345.6)
        self.assertEqual(res_c1_base['verdict'], 'NOT_RUN_LAZY')
        self.assertEqual(res_c1_base['target_status']['session_provider'], 'PASS')
        self.assertEqual(res_c1_base['target_status']['club_provider_core'], 'NOT_RUN_LAZY')

        # Zero provider in owner_active, post_logout, Cycle 2 baseline, or post_actor MUST FAIL
        for cnum, ep in ((1, 'owner_active'), (1, 'post_logout'), (2, 'baseline'), (1, 'post_actor')):
            with self.subTest(cnum=cnum, ep=ep):
                res_bad = sc_graph.scan_snapshot(snap_lazy, binding=self.binding, epoch=ep, cycle_num=cnum, actor='cohost', cdp_observations=cdp_lazy, time_origin=12345.6)
                self.assertEqual(res_bad['verdict'], 'FAIL')

    def test_stale_selected_fields_at_logout_rejected(self):
        for label, s_kwargs, c_kwargs in (
            ('stale_session_id', {'session_id_state': 'string', 'current_session_state': 'null', 'history_state': 'null', 'club_id_state': 'null', 'current_club_state': 'null', 'bank_account_state': 'null'}, {'session_id_null': False, 'current_session_null': True, 'history_null': True, 'club_id_null': True, 'current_club_null': True, 'bank_null': True}),
            ('stale_current_session', {'session_id_state': 'null', 'current_session_state': 'Session0', 'history_state': 'null', 'club_id_state': 'null', 'current_club_state': 'null', 'bank_account_state': 'null'}, {'session_id_null': True, 'current_session_null': False, 'history_null': True, 'club_id_null': True, 'current_club_null': True, 'bank_null': True}),
            ('stale_history', {'session_id_state': 'null', 'current_session_state': 'null', 'history_state': 'SessionHistoryPage', 'club_id_state': 'null', 'current_club_state': 'null', 'bank_account_state': 'null'}, {'session_id_null': True, 'current_session_null': True, 'history_null': False, 'club_id_null': True, 'current_club_null': True, 'bank_null': True}),
            ('stale_club_id', {'session_id_state': 'null', 'current_session_state': 'null', 'history_state': 'null', 'club_id_state': 'string', 'current_club_state': 'null', 'bank_account_state': 'null'}, {'session_id_null': True, 'current_session_null': True, 'history_null': True, 'club_id_null': False, 'current_club_null': True, 'bank_null': True}),
            ('stale_current_club', {'session_id_state': 'null', 'current_session_state': 'null', 'history_state': 'null', 'club_id_state': 'null', 'current_club_state': 'Club', 'bank_account_state': 'null'}, {'session_id_null': True, 'current_session_null': True, 'history_null': True, 'club_id_null': True, 'current_club_null': False, 'bank_null': True}),
            ('stale_bank_account', {'session_id_state': 'null', 'current_session_state': 'null', 'history_state': 'null', 'club_id_state': 'null', 'current_club_state': 'null', 'bank_account_state': 'BankAccount'}, {'session_id_null': True, 'current_session_null': True, 'history_null': True, 'club_id_null': True, 'current_club_null': True, 'bank_null': False}),
        ):
            with self.subTest(label=label):
                snap = build_sc_snapshot(current_user_null=True, **s_kwargs)
                cdp = make_sc_cdp(user_null=True, **c_kwargs)
                res = sc_graph.scan_snapshot(snap, binding=self.binding, epoch='post_logout', cycle_num=1, actor='cohost', cdp_observations=cdp, time_origin=12345.6)
                self.assertEqual(res['verdict'], 'FAIL')

    def test_mismatched_snapshot_cdp_counters_timeorigin_and_getters_rejected(self):
        snap_ok = build_sc_snapshot()
        controls = [
            ('session_id_mismatch', make_sc_cdp(session_id='999'), 'FAIL'),
            ('club_id_mismatch', make_sc_cdp(club_id='999'), 'FAIL'),
            ('field_null_mismatch', make_sc_cdp(current_session_null=True), 'FAIL'),
            ('counter_drift', make_sc_cdp(count=2, after_count=3), 'FAIL'),
            ('non_quiescent_depth', make_sc_cdp(depth=1), 'FAIL'),
            ('time_origin_drift', make_sc_cdp(time_origin_before=12345.6, time_origin_after=99999.0), 'FAIL'),
            ('object_group_leaked', make_sc_cdp(object_group_released=False), 'FAIL'),
            ('getter_cdp_error', make_sc_cdp(cdp_errors=['session_getter__currentSession']), 'FAIL'),
            ('atomic_claim_forged', make_sc_cdp(atomic_claim=True), 'FAIL'),
        ]
        for label, cdp, exp_verdict in controls:
            with self.subTest(label=label):
                res = sc_graph.scan_snapshot(snap_ok, binding=self.binding, epoch='owner_active', cycle_num=1, actor='cohost', cdp_observations=cdp, time_origin=12345.6)
                self.assertEqual(res['verdict'], exp_verdict)

        # Missing getter flag rejection in descriptor validation
        cdp_getter_flag = make_sc_cdp()
        cdp_getter_flag['club_selected_fields']['_currentClub']['has_getter'] = True
        res_g = sc_graph.scan_snapshot(snap_ok, binding=self.binding, epoch='owner_active', cycle_num=1, actor='cohost', cdp_observations=cdp_getter_flag, time_origin=12345.6)
        self.assertEqual(res_g['verdict'], 'FAIL')

    def test_post_actor_legitimate_refetch_vs_reused_owner_object_vs_member_stale_leak(self):
        # Valid Cohost post_actor: refetched new Session0 + History with fresh heap_object_ids
        snap_cohost_ok = build_sc_snapshot(
            current_session_obj_id=810, history_obj_id=820,
            club_id_state='null', current_club_state='null', bank_account_state='null',
        )
        cdp_cohost_ok = make_sc_cdp(club_id_null=True, current_club_null=True, bank_null=True)
        res_ok = sc_graph.scan_snapshot(
            snap_cohost_ok, binding=self.binding, epoch='post_actor', cycle_num=1, actor='cohost',
            cdp_observations=cdp_cohost_ok, time_origin=12345.6,
            previous_owner_field_ids={'current_session': '410', 'session_history': '420'},
        )
        self.assertEqual(res_ok['verdict'], 'PASS')

        # Missing previous_owner_field_ids in post_actor MUST FAIL (no implicit None != owner allowance)
        res_missing_prev = sc_graph.scan_snapshot(
            snap_cohost_ok, binding=self.binding, epoch='post_actor', cycle_num=1, actor='cohost',
            cdp_observations=cdp_cohost_ok, time_origin=12345.6,
            previous_owner_field_ids=None,
        )
        self.assertEqual(res_missing_prev['verdict'], 'FAIL')

        # Reused exact Owner Session0 heap_object_id -> FAIL
        snap_cohost_stale_id = build_sc_snapshot(
            current_session_obj_id=410, history_obj_id=820,
            club_id_state='null', current_club_state='null', bank_account_state='null',
        )
        res_reused = sc_graph.scan_snapshot(
            snap_cohost_stale_id, binding=self.binding, epoch='post_actor', cycle_num=1, actor='cohost',
            cdp_observations=cdp_cohost_ok, time_origin=12345.6,
            previous_owner_field_ids={'current_session': '410', 'session_history': '420'},
        )
        self.assertEqual(res_reused['verdict'], 'FAIL')

        # Member post_actor with stale non-null _currentSession -> FAIL
        snap_member_leak = build_sc_snapshot(
            session_id_state='null', current_session_state='Session0', current_session_obj_id=810,
            history_state='SessionHistoryPage', history_obj_id=820,
            club_id_state='null', current_club_state='null', bank_account_state='null',
        )
        cdp_member_leak = make_sc_cdp(
            session_id_null=True, current_session_null=False, history_null=False,
            club_id_null=True, current_club_null=True, bank_null=True,
        )
        res_mem_leak = sc_graph.scan_snapshot(
            snap_member_leak, binding=self.binding, epoch='post_actor', cycle_num=2, actor='member',
            cdp_observations=cdp_member_leak, time_origin=12345.6,
            previous_owner_field_ids={'current_session': '410', 'session_history': '420'},
        )
        self.assertEqual(res_mem_leak['verdict'], 'FAIL')


class TestStrictVerifierAndAntiForgery(unittest.TestCase):
    def test_valid_full_bank_and_partial_bank_not_run_honesty(self):
        with tempfile.TemporaryDirectory() as tmp:
            bdir = Path(tmp) / 'build'
            bdir.mkdir()
            full_dir = Path(tmp) / 'full_ok'
            _build_full_sc_bundle(full_dir, bdir, bank_populated=True, require_bank_account=True)
            probs, assess = sc_graph.verify(full_dir, build_dir=bdir, require_bank_account=True)
            self.assertEqual(probs, [], probs)
            self.assertEqual(assess['session_club_listener_gate'], 'PASS')
            self.assertEqual(assess['club_bank_account_gate'], 'PASS')

            partial_dir = Path(tmp) / 'partial_ok'
            _build_full_sc_bundle(partial_dir, bdir, bank_populated=False, require_bank_account=False)
            p_partial, a_partial = sc_graph.verify(partial_dir, build_dir=bdir, require_bank_account=False)
            self.assertEqual(p_partial, [], p_partial)
            self.assertEqual(a_partial['club_bank_account_gate'], 'NOT_RUN')
            self.assertEqual(a_partial['session_club_listener_gate'], 'PARTIAL_CLUB_BANK_NOT_RUN')

            # STRICT mode rejects partial NOT_RUN bank account
            p_strict, a_strict = sc_graph.verify(partial_dir, build_dir=bdir, require_bank_account=True)
            self.assertTrue(len(p_strict) > 0)
            self.assertEqual(a_strict['session_club_listener_gate'], 'FAIL')

    def test_red_fake_pass_on_unpopulated_bank_rejected(self):
        def _forge_pass(summary):
            summary['verdict'] = 'PASS'
            summary['session_club_assessment']['club_bank_account_gate'] = 'PASS'
            summary['session_club_assessment']['session_club_listener_gate'] = 'PASS'

        with tempfile.TemporaryDirectory() as tmp:
            bdir = Path(tmp) / 'build'
            bdir.mkdir()
            bad_dir = Path(tmp) / 'forged_pass'
            _build_full_sc_bundle(bad_dir, bdir, bank_populated=False, mutate_fn=_forge_pass)
            probs, assess = sc_graph.verify(bad_dir, build_dir=bdir)
            self.assertTrue(len(probs) > 0)
            self.assertEqual(assess['session_club_listener_gate'], 'FAIL')

    def test_red_mutants_forged_slots_binding_cleanup_and_fl4_secrets(self):
        marker_cls = 'PRIVATE_TAMPERED_CLASS_994411'
        marker_err = 'PRIVATE_TAMPERED_CDP_773322'
        marker_reason = 'PRIVATE_TAMPERED_REASON_661188'

        mutants = {
            'forged_slot_kind': lambda s: s['cycles'][0]['epochs']['owner_active']['listener_graph']['auth_provider']['records'][0]['listener_slots']['active_slots'][0].__setitem__('exact_session_match', False),
            'binding_sha_tamper': lambda s: s['listener_graph_binding'].__setitem__('listener_binding_sha256', '0' * 64),
            'time_origin_skew': lambda s: s['cycles'][1].__setitem__('time_origin', 77777.0),
            'cleanup_not_ok': lambda s: s['cleanup'].__setitem__('ok', False),
            'secret_leak_in_summary': lambda s: s.setdefault('notes', []).append('eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.synthetic_payload_leak'),
            'whole_provider_claim': lambda s: s.setdefault('notes', []).append('entire provider clean'),
            'fl4_untrusted_strings': lambda s: (
                s['cycles'][0]['epochs']['post_actor']['listener_graph']['club_provider']['records'][0]['selected_fields']['_currentClub'].__setitem__('class_name', marker_cls),
                s['cycles'][0]['epochs']['post_actor']['listener_graph']['cdp_observations']['cdp_errors'].append(marker_err),
                s['cycles'][0]['epochs']['post_actor']['listener_graph']['auth_provider']['records'][0]['listener_slots'].__setitem__('reason', marker_reason),
                s['cycles'][0]['epochs']['post_actor']['listener_graph']['auth_provider']['records'][0]['listener_slots'].__setitem__('normalization_ambiguous', True),
            ),
        }

        with tempfile.TemporaryDirectory() as tmp:
            bdir = Path(tmp) / 'build'
            bdir.mkdir()
            for name, mfn in mutants.items():
                with self.subTest(mutant=name):
                    mdir = Path(tmp) / f'bundle_{name}'
                    _build_full_sc_bundle(mdir, bdir, bank_populated=True, mutate_fn=mfn)
                    probs, assess = sc_graph.verify(mdir, build_dir=bdir)
                    self.assertTrue(len(probs) > 0, name)
                    self.assertEqual(assess['session_club_listener_gate'], 'FAIL', name)
                    if name == 'fl4_untrusted_strings':
                        joined = json.dumps(probs)
                        for m in (marker_cls, '994411', marker_err, '773322', marker_reason, '661188'):
                            self.assertNotIn(m, joined)

    def test_sc3_missing_or_invalid_target_heap_object_id_and_claimed_map_rejected(self):
        sc3_mutants = {
            'post_actor_missing_session_id': lambda s: s['cycles'][0]['epochs']['post_actor']['listener_graph']['session_provider']['records'][0]['selected_fields']['_currentSession'].pop('target_heap_object_id', None),
            'owner_and_post_actor_missing_session_id': lambda s: (
                s['cycles'][0]['epochs']['owner_active']['listener_graph']['session_provider']['records'][0]['selected_fields']['_currentSession'].pop('target_heap_object_id', None),
                s['cycles'][0]['epochs']['post_actor']['listener_graph']['session_provider']['records'][0]['selected_fields']['_currentSession'].pop('target_heap_object_id', None),
            ),
            'owner_and_post_actor_missing_history_id': lambda s: (
                s['cycles'][1]['epochs']['owner_active']['listener_graph']['session_provider']['records'][0]['selected_fields']['_session_provider$_history'].__setitem__('target_heap_object_id', None),
                s['cycles'][1]['epochs']['post_actor']['listener_graph']['session_provider']['records'][0]['selected_fields']['_session_provider$_history'].__setitem__('target_heap_object_id', None),
            ),
            'owner_invalid_zero_or_non_digit_club_id': lambda s: s['cycles'][0]['epochs']['owner_active']['listener_graph']['club_provider']['records'][0]['selected_fields']['_currentClub'].__setitem__('target_heap_object_id', '0'),
            'owner_invalid_int_bank_id': lambda s: s['cycles'][0]['epochs']['owner_active']['listener_graph']['club_provider']['records'][0]['selected_fields']['_currentBankAccount'].__setitem__('target_heap_object_id', 620),
            'claimed_map_cannot_hide_reused_owner_id': lambda s: (
                s['cycles'][0].__setitem__('previous_owner_field_ids', {'current_session': '9999', 'session_history': '9998', 'current_club': '9997', 'current_bank_account': '9996'}),
                s['cycles'][0]['epochs']['post_actor']['listener_graph']['session_provider']['records'][0]['selected_fields']['_currentSession'].__setitem__('target_heap_object_id', s['cycles'][0]['epochs']['owner_active']['listener_graph']['session_provider']['records'][0]['selected_fields']['_currentSession']['target_heap_object_id']),
            ),
        }

        with tempfile.TemporaryDirectory() as tmp:
            bdir = Path(tmp) / 'build'
            bdir.mkdir()
            for name, mfn in sc3_mutants.items():
                with self.subTest(mutant=name):
                    mdir = Path(tmp) / f'sc3_{name}'
                    _build_full_sc_bundle(mdir, bdir, bank_populated=True, mutate_fn=mfn)
                    probs, assess = sc_graph.verify(mdir, build_dir=bdir)
                    self.assertTrue(len(probs) > 0, name)
                    self.assertEqual(assess['session_club_listener_gate'], 'FAIL', name)
                    if name == 'claimed_map_cannot_hide_reused_owner_id':
                        self.assertTrue(any('reused_owner_object_id' in p for p in probs), probs)
                    elif 'missing' in name:
                        self.assertTrue(any('target_heap_object_id' in p for p in probs), probs)


if __name__ == '__main__':
    unittest.main()
