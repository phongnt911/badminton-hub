import hashlib
import json
import tempfile
import unittest
import uuid
from pathlib import Path

from scripts.bh07_appheap import finance_auth_listener_graph as graph_mod
from scripts.bh07_appheap import test_payment_instructions_heap as pi_tests


def make_synthetic_listener_main_js(
    *,
    instructions_field='_instructions',
    finance_field='_finance',
    registration_getter='get$_onAuthChanged',
    registration_method='_onAuthChanged$0',
    include_auth_provider=True,
    include_bound_closure=True,
    include_tearoff_factory=True,
    include_session_finance=True,
    include_finance_field_use=True,
    include_registration=True,
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
            '    _._isSubmitting = _._isLoading = false;\n'
            '    _.ChangeNotifier__count = 0;\n'
            '    _.ChangeNotifier__listeners = t1;\n'
            '    _.ChangeNotifier__reentrantlyRemovedListeners = _.ChangeNotifier__notificationCallStackDepth = 0;\n'
            '  },'
        )
    parts.append(
        '  FinanceProvider: function FinanceProvider(t0, t1, t2, t3) {\n'
        '    var _ = this;\n'
        '    _._finance_provider$_repository = t0;\n'
        '    _.auth = t1;\n'
        '    _._finance_provider$_pendingRequests = t2;\n'
        f'    _.{instructions_field} = _._instructionsPlayerId = _._instructionsSessionId = null;\n'
        f'    _.{finance_field} = _._financeSessionId = null;\n'
        '    _.ChangeNotifier__count = 0;\n'
        '    _.ChangeNotifier__listeners = t3;\n'
        '    _.ChangeNotifier__reentrantlyRemovedListeners = _.ChangeNotifier__notificationCallStackDepth = 0;\n'
        '  },'
    )
    parts.append(
        '  PaymentInstructions: function PaymentInstructions(t0, t1, t2, t3, t4, t5, t6) {\n'
        '    var _ = this;\n'
        '    _.sessionId = t0;\n'
        '    _.playerId = t1;\n'
        '    _.receiverSnapshot = t6;\n'
        '  },'
    )
    if include_session_finance:
        parts.append(
            '  SessionFinance: function SessionFinance(t0, t1) {\n'
            '    var _ = this;\n'
            '    _.sessionId = t0;\n'
            '    _.lifecycle = t1;\n'
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
        'A.FinanceProvider.prototype = {\n'
        f'  _resetInstructions$0: function() {{ this.{instructions_field} = null; }},\n'
        '  fetchPaymentInstructions$1: function(s) {\n'
        '    var x = new A.PaymentInstructions(s, s, null, null, null, null, {});\n'
        f'    this.{instructions_field} = x;\n'
        f'    return this.{instructions_field};\n'
        '  },\n'
        + (
            f'  _resetFinance$0: function() {{ this.{finance_field} = null; }},\n'
            '  fetchSessionFinance$1: function(s) {\n'
            '    var f = new A.SessionFinance(s, "current");\n'
            f'    this.{finance_field} = f;\n'
            f'    return this.{finance_field};\n'
            '  },\n'
            if include_finance_field_use
            else ''
        )
        + '};'
    )
    parts.append(
        'A.PaymentInstructions.prototype = {\n'
        '  get$bankCode: function() { return this.receiverSnapshot.$index(0, "bank_code"); }\n'
        '};\n'
        'var r1 = "get_payment_instructions";\n'
        'var r2 = "receiver_snapshot";\n'
        'var r3 = "get_session_finance";\n'
        'A._CreateInheritedProviderState = function() { this._provider$_value = null; };\n'
        'A._CreateInheritedProviderState.prototype = { getValue: function() { return this._provider$_value; } };'
    )
    if include_registration:
        parts.append(
            'A.main_closure4.prototype = {\n'
            '  call$1(context) {\n'
            '    var t1 = A.Provider_of(context, false, type$.AuthProvider);\n'
            '    var t2 = new A.FinanceProvider(null, t1, null, null);\n'
            f'    t1.addListener$1(t2.{registration_getter}());\n'
            '    return t2;\n'
            '  }\n'
            '};\n'
            f'_instance_0_u(_ = A.FinanceProvider.prototype, "{registration_getter}", "{registration_method}", 0);'
        )
    return '\n'.join(parts) + '\n'


class SyntheticV8SnapshotBuilder:
    """Builds a minimal valid V8 .heapsnapshot accepted by heap_oracle.py."""

    NODE_TYPES = [
        'hidden', 'array', 'string', 'object', 'code', 'closure', 'regexp',
        'number', 'native', 'synthetic', 'concatenated string', 'sliced string',
        'symbol', 'bigint',
    ]
    EDGE_TYPES = ['context', 'element', 'property', 'internal', 'hidden', 'shortcut', 'weak']

    def __init__(self):
        self.strings = ['']
        self._str_map = {'': 0}
        self.nodes = []  # list of (type_idx, name_idx, id, self_size, edges_list)
        self._next_id = 10

    def intern(self, text):
        if text not in self._str_map:
            self._str_map[text] = len(self.strings)
            self.strings.append(text)
        return self._str_map[text]

    def add_node(self, node_type, name, *, obj_id=None):
        if obj_id is None:
            obj_id = self._next_id
            self._next_id += 2
        idx = len(self.nodes)
        self.nodes.append([self.NODE_TYPES.index(node_type), self.intern(name), obj_id, 32, []])
        return idx

    def add_edge(self, src, edge_type, name_or_index, dst):
        etype = self.EDGE_TYPES.index(edge_type)
        if edge_type in ('element', 'hidden'):
            ename = int(name_or_index)
        else:
            ename = self.intern(str(name_or_index))
        self.nodes[src][4].append((etype, ename, dst))

    def add_null_node(self):
        # Match real Chrome V8 native oddball + internal:to_string -> "null"
        n = self.add_node('native', 'system / Oddball')
        s = self.add_node('string', 'null')
        self.add_edge(n, 'internal', 'to_string', s)
        return n

    def add_number_node(self):
        return self.add_node('number', 'heap number')

    def build_bytes(self):
        # Ensure >= MIN_SNAPSHOT_BYTES (4096) for heap_oracle.parse_snapshot
        self.intern('padding_' + ('z' * 4200))
        node_width = 6
        flat_nodes = []
        flat_edges = []
        for ntype, nname, nid, ssize, edges in self.nodes:
            flat_nodes.extend([ntype, nname, nid, ssize, len(edges), 0])
            for etype, ename, dst in edges:
                flat_edges.extend([etype, ename, dst * node_width])
        doc = {
            'snapshot': {
                'meta': {
                    'node_fields': ['type', 'name', 'id', 'self_size', 'edge_count', 'detachedness'],
                    'node_types': [self.NODE_TYPES, 'string', 'number', 'number', 'number', 'number'],
                    'edge_fields': ['type', 'name_or_index', 'to_node'],
                    'edge_types': [self.EDGE_TYPES, 'string_or_number', 'node'],
                },
                'node_count': len(self.nodes),
                'edge_count': len(flat_edges) // 3,
            },
            'nodes': flat_nodes,
            'edges': flat_edges,
            'strings': self.strings,
        }
        return json.dumps(doc).encode('utf-8')


def build_tiny_listener_snapshot(
    *,
    auth_count=1,
    finance_count=1,
    finance_rooted=True,
    auth_rooted=True,
    slot_mode='direct',  # 'direct', 'backing', 'both_same', 'both_conflict'
    listener_slots=None,  # list of slot specs
    trailing_non_null=False,
    instructions_state='PaymentInstructions',  # 'PaymentInstructions', 'null', 'WrongClass'
    finance_state='SessionFinance',  # 'SessionFinance', 'null', 'WrongClass'
    current_user_null=False,
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
            u = b.add_node('object', 'User')
            b.add_edge(a, 'property', '_currentUser', u)
        b.add_edge(a, 'property', 'ChangeNotifier__count', b.add_number_node())
        b.add_edge(a, 'property', 'ChangeNotifier__notificationCallStackDepth', b.add_number_node())
        b.add_edge(a, 'property', 'ChangeNotifier__reentrantlyRemovedListeners', b.add_number_node())
        auth_nodes.append(a)

    fin_nodes = []
    for k in range(finance_count):
        f = b.add_node('object', 'FinanceProvider', obj_id=200 + k * 2)
        b.add_edge(gc_roots, 'element' if finance_rooted else 'weak', 30 + k, f)
        if auth_nodes:
            b.add_edge(f, 'property', 'auth', auth_nodes[0])
        if instructions_state == 'null':
            b.add_edge(f, 'property', '_instructions', null_node)
        else:
            b.add_edge(f, 'property', '_instructions', b.add_node('object', instructions_state))
        if finance_state == 'null':
            b.add_edge(f, 'property', '_finance', null_node)
        else:
            b.add_edge(f, 'property', '_finance', b.add_node('object', finance_state))
        fin_nodes.append(f)

    if auth_nodes:
        a0 = auth_nodes[0]
        arr = b.add_node('object', 'Object' if listeners_not_array else 'Array')
        b.add_edge(a0, 'property', 'ChangeNotifier__listeners', arr)
        backing = None
        if slot_mode in ('backing', 'both_same', 'both_conflict'):
            backing = b.add_node('array', '(FixedArray)')
            b.add_edge(arr, 'internal', 'elements', backing)

        if listener_slots is None:
            listener_slots = [
                {'kind': 'ui', 'method': 'markNeedsNotifyDependents$0', 'receiver_class': '_InheritedProviderScopeElement'},
                {'kind': 'finance', 'method': '_onAuthChanged$0', 'receiver_idx': 0},
            ]

        bound_closure_proto = b.add_node('object', 'BoundClosure')
        slot_nodes = []
        for idx, spec in enumerate(listener_slots):
            if spec is None or spec.get('kind') == 'null':
                target = null_node
            else:
                target = b.add_node('object', 'tear_off')
                if spec.get('on_instance_only'):
                    mstr = b.add_node('string', spec['method'])
                    b.add_edge(target, 'property', '$_name', mstr)
                elif spec.get('proto_is_provider'):
                    b.add_edge(target, 'property', '__proto__', fin_nodes[0])
                    mstr = b.add_node('string', spec['method'])
                    b.add_edge(fin_nodes[0], 'property', '$_name', mstr)
                else:
                    gen_proto = b.add_node('object', 'Object')
                    b.add_edge(gen_proto, 'property', '__proto__', bound_closure_proto)
                    if spec.get('method') is not None:
                        b.add_edge(gen_proto, 'property', '$_name', b.add_node('string', spec['method']))
                    b.add_edge(target, 'property', '__proto__', gen_proto)

                if 'receiver_idx' in spec:
                    b.add_edge(target, 'property', '_receiver', fin_nodes[spec['receiver_idx']])
                elif 'receiver_class' in spec:
                    rnode = b.add_node('object', spec['receiver_class'])
                    b.add_edge(gc_roots, 'element', 100 + idx, rnode)
                    b.add_edge(target, 'property', '_receiver', rnode)
            slot_nodes.append((idx, target))

            if slot_mode in ('direct', 'both_same', 'both_conflict'):
                b.add_edge(arr, 'element', idx, target)
            if slot_mode in ('backing', 'both_same'):
                b.add_edge(backing, 'element', idx, target)
            elif slot_mode == 'both_conflict':
                other = b.add_node('object', 'tear_off')
                b.add_edge(backing, 'element', idx, other)

        base_len = len(listener_slots)
        for extra in range(extra_array_slots):
            t_node = b.add_node('object', 'tear_off') if (trailing_non_null and extra == 0) else null_node
            if slot_mode == 'backing':
                b.add_edge(backing, 'element', base_len + extra, t_node)
            else:
                b.add_edge(arr, 'element', base_len + extra, t_node)

    return b.build_bytes()


def make_cdp_obs(
    *,
    auth_id='100',
    finance_id='200',
    count=2,
    depth=0,
    removed=0,
    after_count=None,
    after_depth=None,
    after_removed=None,
    current_user_null=False,
    after_current_user_null=None,
    instructions_null=False,
    instructions_class='PaymentInstructions',
    finance_null=False,
    finance_class='SessionFinance',
    released=True,
    time_origin=1234.5,
    time_origin_after=None,
):
    before = {
        'ChangeNotifier__count': count,
        'ChangeNotifier__notificationCallStackDepth': depth,
        'ChangeNotifier__reentrantlyRemovedListeners': removed,
    }
    after = {
        'ChangeNotifier__count': count if after_count is None else after_count,
        'ChangeNotifier__notificationCallStackDepth': depth if after_depth is None else after_depth,
        'ChangeNotifier__reentrantlyRemovedListeners': removed if after_removed is None else after_removed,
    }
    ac_null = current_user_null if after_current_user_null is None else after_current_user_null
    user_before = {
        'present': True,
        'has_getter': False,
        'is_null': current_user_null,
        'value_type': 'null' if current_user_null else 'object',
        'class_name': None if current_user_null else 'User',
    }
    user_after = {
        'present': True,
        'has_getter': False,
        'is_null': ac_null,
        'value_type': 'null' if ac_null else 'object',
        'class_name': None if ac_null else 'User',
    }
    obs = {
        'observation_mode': 'hybrid_snapshot_plus_readonly_cdp_own_properties',
        'atomic_claim': False,
        'auth_heap_object_id': auth_id,
        'time_origin_before': time_origin,
        'time_origin_after': time_origin if time_origin_after is None else time_origin_after,
        'before': before,
        'after': after,
        'counters_match': (before == after),
        'quiescent': (before == after and depth == 0 and removed == 0),
        'auth_current_user': dict(user_before),
        'auth_current_user_before': dict(user_before),
        'auth_current_user_after': dict(user_after),
        'cdp_errors': [],
        'object_group_released': released,
    }
    if finance_id is not None:
        obs['finance_heap_object_id'] = finance_id
        obs['finance_selected_fields'] = {
            '_instructions': {
                'present': True,
                'has_getter': False,
                'is_null': instructions_null,
                'value_type': 'null' if instructions_null else 'object',
                'class_name': None if instructions_null else instructions_class,
            },
            '_finance': {
                'present': True,
                'has_getter': False,
                'is_null': finance_null,
                'value_type': 'null' if finance_null else 'object',
                'class_name': None if finance_null else finance_class,
            },
        }
    return obs


class TestFinanceAuthListenerBinding(unittest.TestCase):
    def test_binding_rejects_comments_literals_missing_fields_and_sha_mismatch(self):
        good_js = make_synthetic_listener_main_js()
        with tempfile.TemporaryDirectory() as tmp:
            bdir = Path(tmp) / 'good'
            bdir.mkdir()
            (bdir / 'main.dart.js').write_bytes(good_js.encode('utf-8'))
            sha = hashlib.sha256(good_js.encode('utf-8')).hexdigest()

            res = graph_mod.extract_listener_source_binding(bdir, expected_main_js_sha=sha)
            self.assertIs(res.get('ok'), True, res)
            self.assertEqual(res['auth_provider']['listeners_field'], 'ChangeNotifier__listeners')
            self.assertEqual(res['bound_closure']['receiver_field'], '_receiver')
            self.assertEqual(res['finance_provider']['instructions_field'], '_instructions')
            self.assertEqual(res['finance_provider']['finance_field'], '_finance')
            self.assertEqual(res['finance_provider']['registration_method'], '_onAuthChanged$0')

            bad_sha = graph_mod.extract_listener_source_binding(bdir, expected_main_js_sha='0' * 64)
            self.assertIs(bad_sha.get('ok'), False)

            variants = {
                'block_comment': '/*\n' + good_js + '\n*/',
                'quoted_literal': 'var s = ' + json.dumps(good_js) + ';',
                'missing_auth_provider': make_synthetic_listener_main_js(include_auth_provider=False),
                'missing_bound_closure': make_synthetic_listener_main_js(include_bound_closure=False),
                'missing_session_finance': make_synthetic_listener_main_js(include_session_finance=False),
                'missing_finance_field_use': make_synthetic_listener_main_js(include_finance_field_use=False),
                'missing_registration': make_synthetic_listener_main_js(include_registration=False),
            }
            for label, src in variants.items():
                with self.subTest(label=label):
                    vdir = Path(tmp) / label
                    vdir.mkdir()
                    (vdir / 'main.dart.js').write_bytes(src.encode('utf-8'))
                    vsha = hashlib.sha256(src.encode('utf-8')).hexdigest()
                    bad = graph_mod.extract_listener_source_binding(vdir, expected_main_js_sha=vsha)
                    self.assertIs(bad.get('ok'), False, label)

    def test_prototype_budget_and_unterminated_vs_cap_distinction(self):
        base_src = make_synthetic_listener_main_js()
        self.assertEqual(graph_mod.pi_verifier.MAX_CONSTRUCTOR_SNIPPET_BYTES, 32768)
        cap = getattr(graph_mod, 'MAX_PROTOTYPE_BLOCK_BYTES', 256 << 10)
        self.assertGreater(cap, 32768)

        proto_anchor = 'A.FinanceProvider.prototype = {\n'
        proto_idx = base_src.index(proto_anchor) + len(proto_anchor)

        # Valid prototype > 32 KiB (within bounded prototype cap) succeeds.
        pad_40k = ''.join(f'  _pad{i}$0: function(a) {{ return a + {i}; }},\n' for i in range(1100))
        self.assertGreater(len(pad_40k.encode('utf-8')), 32768)
        self.assertLess(len(pad_40k.encode('utf-8')), cap - 4096)
        large_valid_src = base_src[:proto_idx] + pad_40k + base_src[proto_idx:]

        # Prototype exceeding cap (with real JS following after cap) rejects as exceeded_cap.
        over_chunks = []
        over_len = 0
        idx = 0
        while over_len <= cap + 2048:
            piece = f'  _over{idx}$0: function(a) {{ return a + {idx}; }},\n'
            over_chunks.append(piece)
            over_len += len(piece)
            idx += 1
        over_cap_src = base_src[:proto_idx] + ''.join(over_chunks) + base_src[proto_idx:]

        # Unterminated prototype reaching EOF within cap rejects as unterminated.
        close_proto_marker = '\n};'
        close_idx = base_src.index(close_proto_marker, proto_idx)
        unterminated_src = base_src[:close_idx] + '\n  // missing closing brace at EOF\n' + base_src[close_idx + len(close_proto_marker):]

        # Commented and string-literal fake >32 KiB prototypes reject.
        proto_end = close_idx + len(close_proto_marker)
        commented_src = (
            base_src[:base_src.index(proto_anchor)]
            + '/* ' + proto_anchor + pad_40k + base_src[proto_idx:proto_end] + ' */\n'
            + base_src[proto_end:]
        )
        literal_payload = (proto_anchor + pad_40k + base_src[proto_idx:proto_end]).replace('\n', '\\n').replace('"', '\\"')
        literal_src = (
            base_src[:base_src.index(proto_anchor)]
            + f'var _fakeProto = "{literal_payload}";\n'
            + base_src[proto_end:]
        )

        # Oversized constructor >32 KiB still fails constructor cap (untouched 32 KiB limit).
        ctor_anchor = 'FinanceProvider: function FinanceProvider('
        ctor_body_idx = base_src.index('{', base_src.index(ctor_anchor)) + 1
        ctor_pad = ''.join(f'var _c{i} = {i}; ' for i in range(2500))
        self.assertGreater(len(ctor_pad.encode('utf-8')), 32768)
        oversized_ctor_src = base_src[:ctor_body_idx] + ctor_pad + base_src[ctor_body_idx:]

        with tempfile.TemporaryDirectory() as tmp:
            ok_dir = Path(tmp) / 'large_valid'
            ok_dir.mkdir()
            (ok_dir / 'main.dart.js').write_bytes(large_valid_src.encode('utf-8'))
            ok_sha = hashlib.sha256(large_valid_src.encode('utf-8')).hexdigest()
            ok_res = graph_mod.extract_listener_source_binding(ok_dir, expected_main_js_sha=ok_sha)
            self.assertIs(ok_res.get('ok'), True, ok_res)

            rejects = {
                'over_cap': (over_cap_src, 'FinanceProvider_prototype_exceeded_cap'),
                'unterminated': (unterminated_src, 'FinanceProvider_prototype_unterminated'),
                'commented': (commented_src, None),
                'literal': (literal_src, None),
                'oversized_ctor': (oversized_ctor_src, None),
            }
            for label, (src, expected_err) in rejects.items():
                with self.subTest(label=label):
                    vdir = Path(tmp) / label
                    vdir.mkdir()
                    (vdir / 'main.dart.js').write_bytes(src.encode('utf-8'))
                    vsha = hashlib.sha256(src.encode('utf-8')).hexdigest()
                    bad = graph_mod.extract_listener_source_binding(vdir, expected_main_js_sha=vsha)
                    self.assertIs(bad.get('ok'), False, label)
                    if expected_err is not None:
                        self.assertEqual(bad.get('error'), expected_err, label)
                    if label in ('commented', 'literal'):
                        exe, _ = graph_mod.pi_verifier._executable_source(src)
                        self.assertEqual(
                            graph_mod._extract_prototype_block(exe, 'FinanceProvider'),
                            (None, 'FinanceProvider_prototype_missing_or_ambiguous'),
                            label,
                        )

    @staticmethod
    def make_actual_shape_listener_main_js(
        *,
        pad_prototype_over_32k=False,
        repo_rpc_name='get_session_finance',
        repo_return_expr='new A.SessionFinance(t1, "draft", 1, 1, "not_finalized", null, 0, 0, [], [], [], 50, 0)',
        decoy_rpc_literal=False,
        fetch_alias_init='this',
        fetch_alias_reassigned=False,
        fetch_assign_field='_finance',
        extra_ambiguous_field=None,
        reset_stmt='_this._finance = _this._financeSessionId = null;',
        reset_alias_init='this',
        comment_out_fetch=False,
        comment_out_reset=False,
        factory_repo_ctor='FinanceRepository',
        factory_auth_type='AuthProvider',
        factory_receiver_replaced=False,
        factory_wire_expr='t1.addListener$1(t2.get$_onAuthChanged())',
        factory_moved_wiring=False,
        factory_in_literal=False,
        optional_getter_field=None,
    ):
        pad_block = (
            ''.join(f'  _pad{i}$0: function(a) {{ return a + {i}; }},\n' for i in range(1100))
            if pad_prototype_over_32k
            else ''
        )
        extra_ctor = f'    _.{extra_ambiguous_field} = null;\n' if extra_ambiguous_field else ''
        extra_fetch_write = f'              $async$self.{extra_ambiguous_field} = finance;\n' if extra_ambiguous_field else ''
        extra_reset = f'        _this.{extra_ambiguous_field} = null;\n' if extra_ambiguous_field else ''
        reassigned_line = '      $async$self = otherObj;\n' if fetch_alias_reassigned else ''
        reset_line = f'        /* {reset_stmt} */' if comment_out_reset else f'        {reset_stmt}'
        decoy_line = '        var _decoy = "get_session_finance";\n' if decoy_rpc_literal else ''
        getter_block = (
            f'  get$finance() {{ return this.{optional_getter_field}; }},\n'
            if optional_getter_field
            else ''
        )

        fetch_method = (
            '  fetchSessionFinance$1(sessionId) {\n'
            '    var limit = 50, offset = 0;\n'
            '    return this.fetchSessionFinance$body$FinanceProvider(sessionId);\n'
            '  },\n'
            '  fetchSessionFinance$body$FinanceProvider(sessionId) {\n'
            '    var $async$goto = 0,\n'
            '      $async$completer = A._makeAsyncAwaitCompleter(type$.void),\n'
            f'      $async$handler = 1, $async$errorStack = [], $async$next = [], $async$self = {fetch_alias_init}, finance, limit, offset, generation, serial;\n'
            f'{reassigned_line}'
            '    var $async$fetchSessionFinance$1 = A._wrapJsFunctionForAsync(function($async$errorCode, $async$result) {\n'
            '      for (;;)\n'
            '        switch ($async$goto) {\n'
            '          case 0:\n'
            '            limit = 50; offset = 0;\n'
            '            generation = $async$self._finance_provider$_generation;\n'
            '            serial = ++$async$self._financeSerial;\n'
            '            if ($async$self._financeSessionId !== sessionId) {\n'
            '              $async$self._financeSessionId = sessionId;\n'
            '              $async$self._finance = null;\n'
            '            }\n'
            '            $async$goto = 6;\n'
            '            return A._asyncAwait($async$self._finance_provider$_repository.getSessionFinance$3$limit$offset(sessionId, limit, offset), $async$fetchSessionFinance$1);\n'
            '          case 6:\n'
            '            finance = $async$result;\n'
            '            if ($async$self._finance_provider$_generation === generation && $async$self._financeSessionId === sessionId)\n'
            f'              $async$self.{fetch_assign_field} = finance;\n'
            f'{extra_fetch_write}'
            '            $async$goto = 1;\n'
            '            break;\n'
            '          case 1:\n'
            '            return A._asyncReturn(null, $async$completer);\n'
            '        }\n'
            '    });\n'
            '    return A._asyncStartSync($async$fetchSessionFinance$1, $async$completer);\n'
            '  },\n'
        )
        if comment_out_fetch:
            fetch_block = '  /*\n' + fetch_method + '  */\n'
        else:
            fetch_block = fetch_method

        replace_stmt = '    t2 = otherProvider;\n' if factory_receiver_replaced else ''
        wire_stmt = '' if factory_moved_wiring else f'    {factory_wire_expr};\n'
        moved_fn = (
            'A.movedWire = function(t1, t2) {\n'
            f'  {factory_wire_expr};\n'
            '};\n'
            if factory_moved_wiring
            else ''
        )
        factory_code = (
            'A.main_closure4.prototype = {\n'
            '  call$1(context) {\n'
            '    var t3,\n'
            f'      t1 = A.Provider_of(context, false, type$.{factory_auth_type}),\n'
            '      t2 = $.$get$Supabase__instance().__Supabase_client_A;\n'
            f'    t2 = new A.{factory_repo_ctor}(t2);\n'
            '    t2 = new A.FinanceProvider(t2, t1, A.LinkedHashMap_LinkedHashMap$_empty(), $.$get$ChangeNotifier__emptyListeners());\n'
            '    t3 = t1._currentUser;\n'
            '    t3 = t3 == null ? null : t3.id;\n'
            '    t2._finance_provider$_authUserId = t3;\n'
            f'{replace_stmt}'
            f'{wire_stmt}'
            '    return t2;\n'
            '  }\n'
            '};\n'
        )
        factory_block = (
            f'var _decoyFactory = {json.dumps(factory_code)};\n'
            if factory_in_literal
            else factory_code
        )

        return (
            'var A = {\n'
            '  BoundClosure: function BoundClosure(t0, t1) {\n'
            '    this._receiver = t0;\n'
            '    this._interceptor = t1;\n'
            '  },\n'
            '  AuthProvider: function AuthProvider(t0, t1) {\n'
            '    var _ = this;\n'
            '    _._repository = t0;\n'
            '    _._currentUser = _._authSubscription = null;\n'
            '    _.ChangeNotifier__count = 0;\n'
            '    _.ChangeNotifier__listeners = t1;\n'
            '    _.ChangeNotifier__reentrantlyRemovedListeners = _.ChangeNotifier__notificationCallStackDepth = 0;\n'
            '  },\n'
            '  FinanceProvider: function FinanceProvider(t0, t1, t2, t3) {\n'
            '    var _ = this;\n'
            '    _._finance_provider$_repository = t0;\n'
            '    _.auth = t1;\n'
            '    _._finance_provider$_authUserId = null;\n'
            '    _._finance_provider$_generation = 0;\n'
            '    _._finance_provider$_disposed = false;\n'
            '    _._finance_provider$_pendingRequests = t2;\n'
            '    _._instructions = _._instructionsPlayerId = _._instructionsSessionId = null;\n'
            '    _._instructionsSerial = 0;\n'
            '    _._finance = _._financeSessionId = null;\n'
            f'{extra_ctor}'
            '    _._financeSerial = 0;\n'
            '    _.ChangeNotifier__count = 0;\n'
            '    _.ChangeNotifier__listeners = t3;\n'
            '    _.ChangeNotifier__reentrantlyRemovedListeners = _.ChangeNotifier__notificationCallStackDepth = 0;\n'
            '  },\n'
            '  PaymentInstructions: function PaymentInstructions(t0, t1, t2, t3, t4, t5, t6) {\n'
            '    var _ = this;\n'
            '    _.sessionId = t0;\n'
            '    _.playerId = t1;\n'
            '    _.receiverSnapshot = t6;\n'
            '  },\n'
            '  SessionFinance: function SessionFinance(t0, t1, t2, t3, t4, t5, t6, t7, t8, t9, t10, t11, t12) {\n'
            '    var _ = this;\n'
            '    _.sessionId = t0;\n'
            '    _.lifecycle = t1;\n'
            '  },\n'
            '  Closure_fromTearOff(parameters) {\n'
            '    var $prototype = Object.create(new A.BoundClosure(null, null).constructor.prototype);\n'
            '    var $constructor = function tear_off(a, b) { this.$initialize(a, b); };\n'
            '    $prototype.constructor = $constructor;\n'
            '    $constructor.prototype = $prototype;\n'
            '    $prototype.$_name = parameters.fs[0];\n'
            '    return $constructor;\n'
            '  }\n'
            '};\n'
            'A.FinanceRepository.prototype = {\n'
            '  getSessionFinance$3$limit$offset(sessionId, limit, offset) {\n'
            '    return this.getSessionFinance$body$FinanceRepository(sessionId, limit, offset);\n'
            '  },\n'
            '  getSessionFinance$body$FinanceRepository(sessionId, limit, offset) {\n'
            '    var $async$goto = 0, $async$completer = A._makeAsyncAwaitCompleter(type$.SessionFinance), $async$returnValue, $async$self = this, t1;\n'
            '    var $async$getSessionFinance$3$limit$offset = A._wrapJsFunctionForAsync(function($async$errorCode, $async$result) {\n'
            '      for (;;)\n'
            '        switch ($async$goto) {\n'
            '          case 0:\n'
            f'{decoy_line}'
            '            $async$goto = 3;\n'
            f'            return A._asyncAwait($async$self._finance_repository$_client.rpc$1$2$params("{repo_rpc_name}", A.LinkedHashMap_LinkedHashMap$_literal(["p_session_id", sessionId]), t1), $async$getSessionFinance$3$limit$offset);\n'
            '          case 3:\n'
            '            t1 = "s1";\n'
            f'            $async$returnValue = {repo_return_expr};\n'
            '            $async$goto = 1;\n'
            '            break;\n'
            '          case 1:\n'
            '            return A._asyncReturn($async$returnValue, $async$completer);\n'
            '        }\n'
            '    });\n'
            '    return A._asyncStartSync($async$getSessionFinance$3$limit$offset, $async$completer);\n'
            '  }\n'
            '};\n'
            'A.FinanceProvider.prototype = {\n'
            f'{pad_block}'
            '  _onAuthChanged$0() {\n'
            f'    var _this = {reset_alias_init}, t1 = _this.auth._currentUser, userId = t1 == null ? null : t1.id;\n'
            '    if (userId != _this._finance_provider$_authUserId) {\n'
            '      _this._finance_provider$_authUserId = userId;\n'
            '      _this._resetInstructions$0();\n'
            f'{reset_line}\n'
            f'{extra_reset}'
            '    }\n'
            '  },\n'
            '  _resetInstructions$0() {\n'
            '    var _this = this;\n'
            '    _this._instructions = _this._instructionsPlayerId = _this._instructionsSessionId = null;\n'
            '  },\n'
            '  fetchPaymentInstructions$body$FinanceProvider(sessionId, playerId) {\n'
            '    var $async$self = this;\n'
            '    $async$self._instructions = null;\n'
            '    return A._asyncAwait($async$self._finance_provider$_repository.getPaymentInstructions$2$playerId(sessionId, playerId), cb);\n'
            '  },\n'
            '  fetchPaymentInstructions$1(s) {\n'
            '    var x = new A.PaymentInstructions(s, s, null, null, null, null, {});\n'
            '    this._instructions = x;\n'
            '    return this._instructions;\n'
            '  },\n'
            f'{fetch_block}'
            f'{getter_block}'
            '};\n'
            'A.PaymentInstructions.prototype = {\n'
            '  get$bankCode() { return this.receiverSnapshot.$index(0, "bank_code"); }\n'
            '};\n'
            'var r1 = "get_payment_instructions";\n'
            'var r2 = "receiver_snapshot";\n'
            'A._CreateInheritedProviderState = function() { this._provider$_value = null; };\n'
            'A._CreateInheritedProviderState.prototype = { getValue() { return this._provider$_value; } };\n'
            f'{factory_block}'
            f'{moved_fn}'
            '_instance_0_u(_ = A.FinanceProvider.prototype, "get$_onAuthChanged", "_onAuthChanged$0", 0);\n'
        )

    def test_resume_result_overwrite_rejected(self):
        src = self.make_actual_shape_listener_main_js().replace(
            'finance = $async$result;',
            '$async$result = new A.SessionSummary(null); finance = $async$result;', 1)
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / 'main.dart.js').write_text(src, encoding='utf-8')
            result = graph_mod.extract_listener_source_binding(Path(tmp))
            self.assertIs(result.get('ok'), False, result)

    def test_actual_shape_async_factory_binding_contract_and_negative_controls(self):
        with tempfile.TemporaryDirectory() as tmp:
            # Positive actual-shape async repo + chained alias null reset + >32 KiB prototype + intervening auth init
            pos_src = self.make_actual_shape_listener_main_js(pad_prototype_over_32k=True)
            pos_dir = Path(tmp) / 'actual_positive'
            pos_dir.mkdir()
            (pos_dir / 'main.dart.js').write_bytes(pos_src.encode('utf-8'))
            pos_sha = hashlib.sha256(pos_src.encode('utf-8')).hexdigest()
            pos_res = graph_mod.extract_listener_source_binding(pos_dir, expected_main_js_sha=pos_sha)
            self.assertIs(pos_res.get('ok'), True, pos_res)
            self.assertEqual(pos_res['finance_provider']['instructions_field'], '_instructions')
            self.assertEqual(pos_res['finance_provider']['finance_field'], '_finance')
            self.assertEqual(pos_res['finance_provider']['registration_getter'], 'get$_onAuthChanged')
            self.assertEqual(pos_res['finance_provider']['registration_method'], '_onAuthChanged$0')

            negatives = {
                'wrongreceiver_replaced': dict(factory_receiver_replaced=True),
                'wrongreceiver_other_var': dict(factory_wire_expr='t1.addListener$1(otherFin.get$_onAuthChanged())'),
                'wrongauth_provider_type': dict(factory_auth_type='SessionProvider'),
                'wrongauth_listener_target': dict(factory_wire_expr='otherAuth.addListener$1(t2.get$_onAuthChanged())'),
                'alias_unverified_fetch': dict(fetch_alias_init='otherObj'),
                'alias_reassigned_fetch': dict(fetch_alias_reassigned=True),
                'alias_unverified_reset': dict(reset_alias_init='otherObj'),
                'RPCresult_wrong_model': dict(repo_return_expr='new A.SessionSummary(t1)'),
                'RPCresult_wrong_rpc_with_decoy': dict(repo_rpc_name='get_session_summary', decoy_rpc_literal=True),
                'RPCresult_wrong_factory_repo': dict(factory_repo_ctor='SessionRepository'),
                'field_not_in_ctor': dict(fetch_assign_field='_undeclaredFinance'),
                'field_is_instructions': dict(fetch_assign_field='_instructions'),
                'ambiguous_two_fields': dict(extra_ambiguous_field='_financeAlt'),
                'reset_missing_in_onAuthChanged': dict(reset_stmt=''),
                'reset_undefined_not_null': dict(reset_stmt='_this._finance = _this._financeSessionId = undefined;'),
                'method_wrong_tearoff_getter': dict(factory_wire_expr='t1.addListener$1(t2.get$otherMethod())'),
                'method_getter_without_call': dict(factory_wire_expr='t1.addListener$1(t2.get$_onAuthChanged)'),
                'method_moved_wiring': dict(factory_moved_wiring=True),
                'comment_wrapped_fetch': dict(comment_out_fetch=True),
                'comment_wrapped_reset': dict(comment_out_reset=True),
                'literal_wrapped_factory': dict(factory_in_literal=True),
                'optional_getter_mismatch': dict(optional_getter_field='_wrongField'),
            }
            for label, kwargs in negatives.items():
                with self.subTest(negative=label):
                    nsrc = self.make_actual_shape_listener_main_js(**kwargs)
                    ndir = Path(tmp) / label
                    ndir.mkdir()
                    (ndir / 'main.dart.js').write_bytes(nsrc.encode('utf-8'))
                    nsha = hashlib.sha256(nsrc.encode('utf-8')).hexdigest()
                    bad = graph_mod.extract_listener_source_binding(ndir, expected_main_js_sha=nsha)
                    self.assertIs(bad.get('ok'), False, label)


class TestFinanceAuthListenerGraphScanner(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.build_dir = Path(self._tmp.name) / 'web'
        self.build_dir.mkdir()
        js_text = make_synthetic_listener_main_js()
        (self.build_dir / 'main.dart.js').write_bytes(js_text.encode('utf-8'))
        self.main_sha = hashlib.sha256(js_text.encode('utf-8')).hexdigest()
        self.binding = graph_mod.extract_listener_source_binding(self.build_dir, expected_main_js_sha=self.main_sha)
        self.assertTrue(self.binding['ok'])

    def tearDown(self):
        self._tmp.cleanup()

    def test_positive_epochs_and_array_normalization_no_double_count(self):
        # Baseline lazy (Finance=0) -> NOT_RUN_LAZY (not PASS)
        base_raw = build_tiny_listener_snapshot(
            finance_count=0,
            current_user_null=True,
            listener_slots=[{'kind': 'ui', 'method': 'markNeedsNotifyDependents$0', 'receiver_class': '_InheritedProviderScopeElement'}],
        )
        base_obs = make_cdp_obs(finance_id=None, count=1, current_user_null=True)
        base_res = graph_mod.scan_snapshot(base_raw, binding=self.binding, epoch='baseline', cdp_observations=base_obs, time_origin=1234.5)
        self.assertEqual(base_res['verdict'], 'NOT_RUN_LAZY')

        # Owner active with direct, backing, and both_same array layouts (plus trailing null capacity)
        for mode in ('direct', 'backing', 'both_same'):
            with self.subTest(slot_mode=mode):
                owner_raw = build_tiny_listener_snapshot(slot_mode=mode, extra_array_slots=2)
                owner_obs = make_cdp_obs(count=2, current_user_null=False, instructions_null=False, finance_null=False)
                owner_res = graph_mod.scan_snapshot(owner_raw, binding=self.binding, epoch='owner_active', cdp_observations=owner_obs, time_origin=1234.5)
                self.assertEqual(owner_res['verdict'], 'PASS')
                self.assertEqual(owner_res['auth_provider']['records'][0]['listener_slots']['finance_match_count'], 1)

        # Post-logout: same live registration + both fields null
        logout_raw = build_tiny_listener_snapshot(instructions_state='null', finance_state='null', current_user_null=True)
        logout_obs = make_cdp_obs(count=2, current_user_null=True, instructions_null=True, finance_null=True)
        logout_res = graph_mod.scan_snapshot(logout_raw, binding=self.binding, epoch='post_logout', cdp_observations=logout_obs, time_origin=1234.5)
        self.assertEqual(logout_res['verdict'], 'PASS')

        # Post-actor: record-only allows legitimate refetch (non-null) OR null
        actor_refetch_raw = build_tiny_listener_snapshot(instructions_state='PaymentInstructions', finance_state='SessionFinance', current_user_null=False)
        actor_refetch_obs = make_cdp_obs(count=2, current_user_null=False, instructions_null=False, finance_null=False)
        actor_res = graph_mod.scan_snapshot(actor_refetch_raw, binding=self.binding, epoch='post_actor', cdp_observations=actor_refetch_obs, time_origin=1234.5)
        self.assertEqual(actor_res['verdict'], 'PASS')

    def test_negative_controls_duplicate_missing_wrong_receiver_method_non_null_postlogout(self):
        # 1. Duplicate rooted AuthProvider & duplicate rooted FinanceProvider & duplicate registration
        dup_auth = build_tiny_listener_snapshot(auth_count=2)
        self.assertEqual(
            graph_mod.scan_snapshot(dup_auth, binding=self.binding, epoch='owner_active', cdp_observations=make_cdp_obs(), time_origin=1234.5)['verdict'],
            'FAIL',
        )
        dup_fin = build_tiny_listener_snapshot(finance_count=2)
        self.assertEqual(
            graph_mod.scan_snapshot(dup_fin, binding=self.binding, epoch='owner_active', cdp_observations=make_cdp_obs(), time_origin=1234.5)['verdict'],
            'FAIL',
        )
        dup_reg = build_tiny_listener_snapshot(
            listener_slots=[
                {'kind': 'finance', 'method': '_onAuthChanged$0', 'receiver_idx': 0},
                {'kind': 'finance', 'method': '_onAuthChanged$0', 'receiver_idx': 0},
            ],
        )
        self.assertEqual(
            graph_mod.scan_snapshot(dup_reg, binding=self.binding, epoch='owner_active', cdp_observations=make_cdp_obs(), time_origin=1234.5)['verdict'],
            'FAIL',
        )

        # 2. Missing positive in owner_active (weak-only FinanceProvider with no strong retainer, missing registration, null field, wrong class)
        weak_fin = build_tiny_listener_snapshot(
            finance_rooted=False,
            listener_slots=[{'kind': 'ui', 'method': 'markNeedsNotifyDependents$0', 'receiver_class': '_InheritedProviderScopeElement'}],
        )
        self.assertEqual(
            graph_mod.scan_snapshot(weak_fin, binding=self.binding, epoch='owner_active', cdp_observations=make_cdp_obs(count=1, finance_id=None), time_origin=1234.5)['verdict'],
            'FAIL',
        )
        null_instr = build_tiny_listener_snapshot(instructions_state='null')
        self.assertEqual(
            graph_mod.scan_snapshot(null_instr, binding=self.binding, epoch='owner_active', cdp_observations=make_cdp_obs(instructions_null=True), time_origin=1234.5)['verdict'],
            'FAIL',
        )
        wrong_cls = build_tiny_listener_snapshot(finance_state='WrongModel')
        self.assertEqual(
            graph_mod.scan_snapshot(wrong_cls, binding=self.binding, epoch='owner_active', cdp_observations=make_cdp_obs(finance_class='WrongModel'), time_origin=1234.5)['verdict'],
            'FAIL',
        )
        no_reg = build_tiny_listener_snapshot(
            listener_slots=[{'kind': 'ui', 'method': 'markNeedsNotifyDependents$0', 'receiver_class': '_InheritedProviderScopeElement'}],
        )
        self.assertEqual(
            graph_mod.scan_snapshot(no_reg, binding=self.binding, epoch='owner_active', cdp_observations=make_cdp_obs(count=1), time_origin=1234.5)['verdict'],
            'FAIL',
        )

        # 3. Wrong receiver (tearoff bound to unrelated receiver class)
        wrong_recv = build_tiny_listener_snapshot(
            listener_slots=[{'kind': 'other', 'method': '_onAuthChanged$0', 'receiver_class': 'SessionProvider'}],
        )
        self.assertEqual(
            graph_mod.scan_snapshot(wrong_recv, binding=self.binding, epoch='owner_active', cdp_observations=make_cdp_obs(count=1), time_origin=1234.5)['verdict'],
            'FAIL',
        )

        # 4. Wrong method or method not on generated tearoff prototype
        wrong_method = build_tiny_listener_snapshot(
            listener_slots=[{'kind': 'finance', 'method': '_club_provider$_onAuthChanged$0', 'receiver_idx': 0}],
        )
        self.assertEqual(
            graph_mod.scan_snapshot(wrong_method, binding=self.binding, epoch='owner_active', cdp_observations=make_cdp_obs(count=1), time_origin=1234.5)['verdict'],
            'FAIL',
        )
        on_instance_only = build_tiny_listener_snapshot(
            listener_slots=[{'kind': 'finance', 'method': '_onAuthChanged$0', 'receiver_idx': 0, 'on_instance_only': True}],
        )
        self.assertEqual(
            graph_mod.scan_snapshot(on_instance_only, binding=self.binding, epoch='owner_active', cdp_observations=make_cdp_obs(count=1), time_origin=1234.5)['verdict'],
            'FAIL',
        )
        proto_is_provider = build_tiny_listener_snapshot(
            listener_slots=[{'kind': 'finance', 'method': '_onAuthChanged$0', 'receiver_idx': 0, 'proto_is_provider': True}],
        )
        self.assertEqual(
            graph_mod.scan_snapshot(proto_is_provider, binding=self.binding, epoch='owner_active', cdp_observations=make_cdp_obs(count=1), time_origin=1234.5)['verdict'],
            'FAIL',
        )

        # 5. Non-null field in post_logout (and in populated Cycle-2 baseline)
        non_null_logout = build_tiny_listener_snapshot(instructions_state='null', finance_state='SessionFinance', current_user_null=True)
        self.assertEqual(
            graph_mod.scan_snapshot(non_null_logout, binding=self.binding, epoch='post_logout', cdp_observations=make_cdp_obs(current_user_null=True, instructions_null=True, finance_null=False), time_origin=1234.5)['verdict'],
            'FAIL',
        )
        non_null_base = build_tiny_listener_snapshot(instructions_state='PaymentInstructions', finance_state='null', current_user_null=True)
        self.assertEqual(
            graph_mod.scan_snapshot(non_null_base, binding=self.binding, epoch='baseline', cdp_observations=make_cdp_obs(current_user_null=True, instructions_null=False, finance_null=True), time_origin=1234.5)['verdict'],
            'FAIL',
        )

    def test_unknown_layout_cap_counter_race_and_release_fail_never_clean(self):
        # Offline scan without CDP observations -> UNKNOWN (never PASS)
        owner_raw = build_tiny_listener_snapshot()
        offline_res = graph_mod.scan_snapshot(owner_raw, binding=self.binding, epoch='owner_active', cdp_observations=None, time_origin=1234.5)
        self.assertEqual(offline_res['verdict'], 'UNKNOWN')

        # Null hole inside active range [0 .. cdp_count - 1] -> UNKNOWN
        hole_raw = build_tiny_listener_snapshot(
            listener_slots=[
                {'kind': 'null'},
                {'kind': 'finance', 'method': '_onAuthChanged$0', 'receiver_idx': 0},
            ],
        )
        hole_res = graph_mod.scan_snapshot(hole_raw, binding=self.binding, epoch='owner_active', cdp_observations=make_cdp_obs(count=2), time_origin=1234.5)
        self.assertIn(hole_res['verdict'], ('UNKNOWN', 'FAIL'))
        self.assertNotEqual(hole_res['verdict'], 'PASS')

        # Unmapped slot inside active range (cdp count=3, snapshot has 2 slots) -> UNKNOWN
        unmapped_res = graph_mod.scan_snapshot(owner_raw, binding=self.binding, epoch='owner_active', cdp_observations=make_cdp_obs(count=3), time_origin=1234.5)
        self.assertNotEqual(unmapped_res['verdict'], 'PASS')

        # Conflicting direct vs internal:elements slots -> UNKNOWN
        conflict_raw = build_tiny_listener_snapshot(slot_mode='both_conflict')
        conflict_res = graph_mod.scan_snapshot(conflict_raw, binding=self.binding, epoch='owner_active', cdp_observations=make_cdp_obs(count=2), time_origin=1234.5)
        self.assertEqual(conflict_res['verdict'], 'UNKNOWN')

        # Listeners not an Array -> UNKNOWN
        not_arr_raw = build_tiny_listener_snapshot(listeners_not_array=True)
        self.assertEqual(
            graph_mod.scan_snapshot(not_arr_raw, binding=self.binding, epoch='owner_active', cdp_observations=make_cdp_obs(count=2), time_origin=1234.5)['verdict'],
            'UNKNOWN',
        )

        # Cap exceeded (cdp_count > MAX_ARRAY_SLOTS) -> UNKNOWN
        cap_res = graph_mod.scan_snapshot(owner_raw, binding=self.binding, epoch='owner_active', cdp_observations=make_cdp_obs(count=graph_mod.MAX_ARRAY_SLOTS + 1), time_origin=1234.5)
        self.assertEqual(cap_res['verdict'], 'UNKNOWN')

        # Trailing non-null slot >= active_count -> FAIL
        trail_raw = build_tiny_listener_snapshot(extra_array_slots=1, trailing_non_null=True)
        trail_res = graph_mod.scan_snapshot(trail_raw, binding=self.binding, epoch='owner_active', cdp_observations=make_cdp_obs(count=2), time_origin=1234.5)
        self.assertEqual(trail_res['verdict'], 'FAIL')

        # Counter race (before != after) and non-quiescent depth/removed -> FAIL / UNKNOWN
        race_res = graph_mod.scan_snapshot(owner_raw, binding=self.binding, epoch='owner_active', cdp_observations=make_cdp_obs(count=2, after_count=3), time_origin=1234.5)
        self.assertEqual(race_res['verdict'], 'FAIL')
        nonq_res = graph_mod.scan_snapshot(owner_raw, binding=self.binding, epoch='owner_active', cdp_observations=make_cdp_obs(count=2, depth=1), time_origin=1234.5)
        self.assertNotEqual(nonq_res['verdict'], 'PASS')

        # Snapshot vs CDP field mismatch -> FAIL
        mismatch_res = graph_mod.scan_snapshot(owner_raw, binding=self.binding, epoch='owner_active', cdp_observations=make_cdp_obs(count=2, instructions_null=True), time_origin=1234.5)
        self.assertEqual(mismatch_res['verdict'], 'FAIL')

        # Object group release failure -> FAIL
        rel_fail_res = graph_mod.scan_snapshot(owner_raw, binding=self.binding, epoch='owner_active', cdp_observations=make_cdp_obs(count=2, released=False), time_origin=1234.5)
        self.assertEqual(rel_fail_res['verdict'], 'FAIL')

    def test_fl3_cdp_time_origin_and_metadata_required_no_bool_coercion(self):
        owner_raw = build_tiny_listener_snapshot()

        # Missing or invalid CDP time_origin_before / time_origin_after or graph time_origin -> never PASS
        for label, obs_patch, top_origin in [
            ('missing_before_after', {'time_origin_before': None, 'time_origin_after': None}, 1234.5),
            ('missing_after', {'time_origin_after': None}, 1234.5),
            ('bool_before', {'time_origin_before': True}, 1234.5),
            ('zero_before', {'time_origin_before': 0, 'time_origin_after': 0}, 0),
            ('neg_before', {'time_origin_before': -5.0, 'time_origin_after': -5.0}, -5.0),
            ('nan_before', {'time_origin_before': float('nan')}, 1234.5),
            ('before_after_drift', {'time_origin_before': 1234.5, 'time_origin_after': 9999.0}, 1234.5),
            ('cdp_vs_graph_mismatch', {'time_origin_before': 9999.0, 'time_origin_after': 9999.0}, 1234.5),
            ('missing_top_origin', {}, None),
            ('bool_top_origin', {}, True),
        ]:
            with self.subTest(case=label):
                obs = make_cdp_obs()
                obs.update(obs_patch)
                res = graph_mod.scan_snapshot(owner_raw, binding=self.binding, epoch='owner_active', cdp_observations=obs, time_origin=top_origin)
                self.assertNotEqual(res['verdict'], 'PASS', label)
                self.assertFalse(res['ok'], label)

        # Missing / incomplete auth_current_user or before/after user shape mismatch -> FAIL
        for label, mut in [
            ('missing_auth_current_user', lambda o: o.pop('auth_current_user', None)),
            ('missing_auth_current_user_before', lambda o: o.pop('auth_current_user_before', None)),
            ('missing_auth_current_user_after', lambda o: o.pop('auth_current_user_after', None)),
            ('user_missing_present', lambda o: o['auth_current_user'].pop('present', None)),
            ('user_missing_value_type', lambda o: o['auth_current_user'].pop('value_type', None)),
            ('user_string_is_null_bool_coercion', lambda o: o['auth_current_user'].__setitem__('is_null', 'false')),
            ('user_none_is_null_bool_coercion', lambda o: o['auth_current_user'].__setitem__('is_null', None)),
            ('user_before_after_drift', lambda o: o['auth_current_user_after'].update({'is_null': True, 'value_type': 'null', 'class_name': None})),
            ('missing_selected_field_present', lambda o: o['finance_selected_fields']['_instructions'].pop('present', None)),
            ('string_selected_field_is_null', lambda o: o['finance_selected_fields']['_instructions'].__setitem__('is_null', 'false')),
            ('missing_quiescent_flag', lambda o: o.pop('quiescent', None)),
            ('atomic_claim_true', lambda o: o.__setitem__('atomic_claim', True)),
        ]:
            with self.subTest(case=label):
                obs = make_cdp_obs()
                mut(obs)
                res = graph_mod.scan_snapshot(owner_raw, binding=self.binding, epoch='owner_active', cdp_observations=obs, time_origin=1234.5)
                self.assertNotEqual(res['verdict'], 'PASS', label)
                self.assertFalse(res['ok'], label)

    def test_fl4_unexpected_private_strings_never_published(self):
        # Private strings in string nodes, unexpected class names, receiver string nodes, and prototype $_name
        secrets = {
            'bank_secret': 'PRIVATE_BANK_ACCT_9988776655',
            'bank_part': '9988776655',
            'ref_class': 'PRIVATE_REF_CLASS_XYZ443322',
            'ref_part': 'XYZ443322',
            'user_tok': 'PRIVATE_USER_TOKEN_ABC112233',
            'user_part': 'ABC112233',
            'recv_secret': 'PRIVATE_RECEIVER_STR_77665544',
            'recv_part': '77665544',
            'method_secret': 'PRIVATE_METHOD_NAME_33445566',
            'method_part': '33445566',
            'listeners_secret': 'PRIVATE_LISTENERS_STR_88990011',
            'listeners_part': '88990011',
        }

        def assert_no_secret_leak(obj, label):
            serialized = json.dumps(obj)
            for k, val in secrets.items():
                self.assertNotIn(val, serialized, f'{label} leaked {k}')

        # Case 1: String node in FinanceProvider._instructions and unexpected object class in _finance
        b = SyntheticV8SnapshotBuilder()
        root = b.add_node('synthetic', '(GC root)', obj_id=1)
        gc_roots = b.add_node('synthetic', '(GC roots)', obj_id=3)
        b.add_edge(root, 'element', 0, gc_roots)
        null_node = b.add_null_node()
        a = b.add_node('object', 'AuthProvider', obj_id=100)
        b.add_edge(gc_roots, 'element', 10, a)
        b.add_edge(a, 'property', '_currentUser', b.add_node('string', secrets['user_tok']))
        b.add_edge(a, 'property', 'ChangeNotifier__count', b.add_number_node())
        b.add_edge(a, 'property', 'ChangeNotifier__notificationCallStackDepth', b.add_number_node())
        b.add_edge(a, 'property', 'ChangeNotifier__reentrantlyRemovedListeners', b.add_number_node())
        f = b.add_node('object', 'FinanceProvider', obj_id=200)
        b.add_edge(gc_roots, 'element', 20, f)
        b.add_edge(f, 'property', 'auth', a)
        b.add_edge(f, 'property', '_instructions', b.add_node('string', secrets['bank_secret']))
        b.add_edge(f, 'property', '_finance', b.add_node('object', secrets['ref_class']))

        arr = b.add_node('object', 'Array')
        b.add_edge(a, 'property', 'ChangeNotifier__listeners', arr)
        bc_proto = b.add_node('object', 'BoundClosure')
        to0 = b.add_node('object', 'tear_off')
        gp0 = b.add_node('object', 'Object')
        b.add_edge(gp0, 'property', '__proto__', bc_proto)
        b.add_edge(gp0, 'property', '$_name', b.add_node('string', secrets['method_secret']))
        b.add_edge(to0, 'property', '__proto__', gp0)
        recv_str = b.add_node('string', secrets['recv_secret'])
        b.add_edge(gc_roots, 'element', 30, recv_str)
        b.add_edge(to0, 'property', '_receiver', recv_str)
        b.add_edge(arr, 'element', 0, to0)

        to1 = b.add_node('object', 'tear_off')
        gp1 = b.add_node('object', 'Object')
        b.add_edge(gp1, 'property', '__proto__', bc_proto)
        b.add_edge(gp1, 'property', '$_name', b.add_node('string', '_onAuthChanged$0'))
        b.add_edge(to1, 'property', '__proto__', gp1)
        b.add_edge(to1, 'property', '_receiver', f)
        b.add_edge(arr, 'element', 1, to1)

        res1 = graph_mod.scan_snapshot(
            b.build_bytes(),
            binding=self.binding,
            epoch='owner_active',
            cdp_observations=make_cdp_obs(count=2),
            time_origin=1234.5,
        )
        self.assertEqual(res1['verdict'], 'FAIL')
        assert_no_secret_leak(res1, 'case1_string_and_unknown_class')
        fin_fields = res1['finance_provider']['records'][0]['selected_fields']
        self.assertIsNone(fin_fields['_instructions']['class_name'])
        self.assertIs(fin_fields['_instructions']['is_null'], False)
        self.assertEqual(fin_fields['_instructions']['node_type'], 'string')
        self.assertIsNone(fin_fields['_finance']['class_name'])
        self.assertIs(fin_fields['_finance']['is_null'], False)
        self.assertEqual(fin_fields['_finance']['node_type'], 'object')
        self.assertIsNone(res1['auth_provider']['records'][0]['current_user']['class_name'])
        self.assertIs(res1['auth_provider']['records'][0]['current_user']['is_null'], False)

        # Case 2: listeners property points to a string node containing a private string
        b2 = SyntheticV8SnapshotBuilder()
        r2 = b2.add_node('synthetic', '(GC root)', obj_id=1)
        g2 = b2.add_node('synthetic', '(GC roots)', obj_id=3)
        b2.add_edge(r2, 'element', 0, g2)
        a2 = b2.add_node('object', 'AuthProvider', obj_id=100)
        b2.add_edge(g2, 'element', 10, a2)
        b2.add_edge(a2, 'property', '_currentUser', b2.add_null_node())
        b2.add_edge(a2, 'property', 'ChangeNotifier__listeners', b2.add_node('string', secrets['listeners_secret']))
        res2 = graph_mod.scan_snapshot(
            b2.build_bytes(),
            binding=self.binding,
            epoch='post_logout',
            cdp_observations=make_cdp_obs(count=1, finance_id=None, current_user_null=True),
            time_origin=1234.5,
        )
        self.assertEqual(res2['verdict'], 'UNKNOWN')
        assert_no_secret_leak(res2, 'case2_listeners_string')


class TestFinanceAuthListenerAuditor(unittest.TestCase):
    def _build_full_listener_bundle(self, bundle_dir, build_dir, *, mutate_fn=None):
        js_text = make_synthetic_listener_main_js()
        (build_dir / 'main.dart.js').write_bytes(js_text.encode('utf-8'))
        main_sha = hashlib.sha256(js_text.encode('utf-8')).hexdigest()
        pi_binding, companion = pi_tests._make_binding_payload(
            js_text,
            graph_mod.pi_verifier.extract_js_constructor(js_text, 'FinanceProvider')['snippet'],
            graph_mod.pi_verifier.extract_js_constructor(js_text, 'PaymentInstructions')['snippet'],
        )
        listener_binding = graph_mod.extract_listener_source_binding(build_dir, expected_main_js_sha=main_sha)
        self.assertTrue(listener_binding['ok'])

        raw_sentinels = {
            'canary_instr_a': str(uuid.uuid4()),
            'canary_instr_b': str(uuid.uuid4()),
            'probe': 'BH07INSTRPROBE-12345678',
        }
        pi_tests._build_valid_bundle(
            bundle_dir,
            sentinels_raw=raw_sentinels,
            frames_override={
                'canary_instr_a': [
                    'root',
                    'element -> synthetic',
                    'property:___InheritedProviderScopeElement__delega -> object',
                    'property:_provider$_value -> object',
                    'property:_instructions -> object',
                    'property:receiverSnapshot -> object',
                    'property:_strings -> object',
                    'property:canary_instr_a -> object',
                    'property:hashMapCellValue -> string',
                ],
                'canary_instr_b': [
                    'root',
                    'element -> synthetic',
                    'property:___InheritedProviderScopeElement__delega -> object',
                    'property:_provider$_value -> object',
                    'property:_instructions -> object',
                    'property:receiverSnapshot -> object',
                    'property:_last -> object',
                    'property:hashMapCellValue -> string',
                ],
            },
            dto_proven=True,
            scoped_verdict='PASS_DTO_ATTRIBUTED',
            main_js_sha=main_sha,
            source_binding=pi_binding,
            companion_binding=companion,
        )

        # Attach real scanned listener_graph records per epoch
        base1_raw = build_tiny_listener_snapshot(
            finance_count=0,
            current_user_null=True,
            listener_slots=[{'kind': 'ui', 'method': 'markNeedsNotifyDependents$0', 'receiver_class': '_InheritedProviderScopeElement'}],
        )
        base1_lg = graph_mod.scan_snapshot(base1_raw, binding=listener_binding, epoch='baseline', cdp_observations=make_cdp_obs(finance_id=None, count=1, current_user_null=True, time_origin=12345.6), time_origin=12345.6)
        base2_raw = build_tiny_listener_snapshot(instructions_state='null', finance_state='null', current_user_null=True)
        base2_lg = graph_mod.scan_snapshot(base2_raw, binding=listener_binding, epoch='baseline', cdp_observations=make_cdp_obs(count=2, current_user_null=True, instructions_null=True, finance_null=True, time_origin=12345.6), time_origin=12345.6)
        owner_raw = build_tiny_listener_snapshot()
        owner_lg = graph_mod.scan_snapshot(owner_raw, binding=listener_binding, epoch='owner_active', cdp_observations=make_cdp_obs(time_origin=12345.6), time_origin=12345.6)
        logout_raw = build_tiny_listener_snapshot(instructions_state='null', finance_state='null', current_user_null=True)
        logout_lg = graph_mod.scan_snapshot(logout_raw, binding=listener_binding, epoch='post_logout', cdp_observations=make_cdp_obs(current_user_null=True, instructions_null=True, finance_null=True, time_origin=12345.6), time_origin=12345.6)
        actor_raw = build_tiny_listener_snapshot()
        actor_lg = graph_mod.scan_snapshot(actor_raw, binding=listener_binding, epoch='post_actor', cdp_observations=make_cdp_obs(time_origin=12345.6), time_origin=12345.6)

        summary_path = bundle_dir / 'summary.json'
        summary = json.loads(summary_path.read_text(encoding='utf-8'))
        for idx, cycle in enumerate(summary['cycles']):
            cycle['epochs']['baseline']['listener_graph'] = base1_lg if idx == 0 else base2_lg
            cycle['epochs']['owner_active']['listener_graph'] = owner_lg
            cycle['epochs']['post_logout']['listener_graph'] = logout_lg
            cycle['epochs']['post_actor']['listener_graph'] = actor_lg
            for ep_scan in cycle['epochs'].values():
                ep_scan['listener_graph']['snapshot_sha256_12'] = ep_scan['sha256_12']
        summary['listener_graph_binding'] = listener_binding
        summary['listener_graph_assessment'] = {
            'listener_graph_gate': 'PASS',
            'claim_scope': graph_mod.CLAIM_SCOPE,
            'observation_mode': graph_mod.OBSERVATION_MODE,
            'atomic_claim': False,
        }
        if mutate_fn:
            mutate_fn(summary)

        summary_path.write_bytes((json.dumps(summary, indent=2) + '\n').encode('utf-8'))
        digest = hashlib.sha256(summary_path.read_bytes()).hexdigest()
        lines = (bundle_dir / 'hashes.sha256').read_text(encoding='utf-8').splitlines()
        new_lines = [f'{digest}  summary.json' if l.endswith('  summary.json') else l for l in lines]
        (bundle_dir / 'hashes.sha256').write_bytes(('\n'.join(new_lines) + '\n').encode('utf-8'))

    def test_verify_positive_and_auditor_rejects_forged_boolean_flags(self):
        with tempfile.TemporaryDirectory() as tmp:
            bdir = Path(tmp) / 'build'
            bdir.mkdir()
            ok_bundle = Path(tmp) / 'ok_bundle'
            self._build_full_listener_bundle(ok_bundle, bdir)
            problems, assessment = graph_mod.verify(ok_bundle, build_dir=bdir)
            self.assertEqual(problems, [])
            self.assertEqual(assessment['listener_graph_gate'], 'PASS')

            # Forged clean flag while owner_active Finance field is null -> MUST FAIL
            bad_bundle = Path(tmp) / 'forged_bundle'
            def _forge_non_null_logout_with_pass_flag(summary):
                lg = summary['cycles'][0]['epochs']['post_logout']['listener_graph']
                lg['finance_provider']['records'][0]['selected_fields']['_instructions'] = {
                    'node_type': 'object',
                    'class_name': 'PaymentInstructions',
                    'primitive_literal': None,
                    'is_null': False,
                }
                lg['verdict'] = 'PASS'
                lg['ok'] = True
            self._build_full_listener_bundle(bad_bundle, bdir, mutate_fn=_forge_non_null_logout_with_pass_flag)
            bad_problems, bad_assessment = graph_mod.verify(bad_bundle, build_dir=bdir)
            self.assertTrue(len(bad_problems) > 0)
            self.assertNotEqual(bad_assessment['listener_graph_gate'], 'PASS')

            # Missing listener_graph on an epoch -> MUST FAIL
            miss_bundle = Path(tmp) / 'miss_bundle'
            self._build_full_listener_bundle(
                miss_bundle,
                bdir,
                mutate_fn=lambda s: s['cycles'][1]['epochs']['owner_active'].pop('listener_graph', None),
            )
            miss_problems, _ = graph_mod.verify(miss_bundle, build_dir=bdir)
            self.assertTrue(len(miss_problems) > 0)

    def test_fl2_auditor_recomputes_all_slots_and_rejects_forged_aggregates(self):
        def _mut_reviewer_exact_mutant(summary):
            # Reviewer FL2 mutant: mutate active slot 1 while leaving aggregate counts intact
            slot1 = summary['cycles'][0]['epochs']['owner_active']['listener_graph']['auth_provider']['records'][0]['listener_slots']['active_slots'][1]
            slot1['receiver_heap_object_id'] = '999999'
            slot1['method_name'] = 'not_onAuthChanged'
            slot1['exact_finance_match'] = False

        def _mut_wrong_receiver_false_flag(summary):
            sl = summary['cycles'][0]['epochs']['owner_active']['listener_graph']['auth_provider']['records'][0]['listener_slots']
            slot1 = sl['active_slots'][1]
            slot1['receiver_heap_object_id'] = '999999'
            slot1['receiver_class'] = 'SessionProvider'
            slot1['receiver_is_rooted_finance'] = False
            slot1['receiver_matches_finance_class'] = False
            slot1['exact_finance_match'] = False
            slot1['kind'] = 'wrong_receiver'
            sl['finance_match_count'] = 1
            sl['wrong_receiver_count'] = 0

        def _mut_wrong_method_forged_match(summary):
            sl = summary['cycles'][0]['epochs']['owner_active']['listener_graph']['auth_provider']['records'][0]['listener_slots']
            slot1 = sl['active_slots'][1]
            slot1['method_name'] = 'not_onAuthChanged'
            slot1['method_on_generated_prototype'] = False
            slot1['bound_closure_on_proto_chain'] = False
            slot1['proto_is_provider'] = True

        def _mut_duplicate_finance_target_forged(summary):
            lg = summary['cycles'][0]['epochs']['owner_active']['listener_graph']
            sl = lg['auth_provider']['records'][0]['listener_slots']
            slot1_copy = dict(sl['active_slots'][1], index=0)
            sl['active_slots'][0] = slot1_copy
            sl['finance_match_count'] = 1
            sl['other_listener_count'] = 0

        def _mut_duplicate_finance_provider_forged(summary):
            lg = summary['cycles'][0]['epochs']['owner_active']['listener_graph']
            fin_recs = lg['finance_provider']['records']
            fin_recs.append(dict(fin_recs[0], heap_object_id='202'))
            lg['finance_provider']['strong_root_reachable_count'] = 1

        def _mut_reordered_indexes(summary):
            sl = summary['cycles'][0]['epochs']['owner_active']['listener_graph']['auth_provider']['records'][0]['listener_slots']
            sl['active_slots'] = [sl['active_slots'][1], sl['active_slots'][0]]

        def _mut_dropped_index(summary):
            sl = summary['cycles'][0]['epochs']['owner_active']['listener_graph']['auth_provider']['records'][0]['listener_slots']
            sl['active_slots'] = [sl['active_slots'][0]]
            sl['active_count'] = 1

        def _mut_duplicate_index(summary):
            sl = summary['cycles'][0]['epochs']['owner_active']['listener_graph']['auth_provider']['records'][0]['listener_slots']
            sl['active_slots'][1]['index'] = 0

        def _mut_invalid_slot_type(summary):
            sl = summary['cycles'][0]['epochs']['owner_active']['listener_graph']['auth_provider']['records'][0]['listener_slots']
            sl['active_slots'][0]['exact_finance_match'] = 'false'

        def _mut_cherrypick_slot0_bad_slot1(summary):
            # Finance at slot 0, bad receiver at slot 1, forged aggregate flags
            sl = summary['cycles'][0]['epochs']['owner_active']['listener_graph']['auth_provider']['records'][0]['listener_slots']
            s0 = dict(sl['active_slots'][1], index=0)
            s1 = dict(sl['active_slots'][0], index=1, method_name='_onAuthChanged$0', kind='wrong_receiver')
            sl['active_slots'] = [s0, s1]
            sl['finance_match_count'] = 1
            sl['wrong_receiver_count'] = 0
            sl['other_listener_count'] = 1

        mutants = {
            'reviewer_exact_mutant': _mut_reviewer_exact_mutant,
            'wrong_receiver_false_flag': _mut_wrong_receiver_false_flag,
            'wrong_method_forged_match': _mut_wrong_method_forged_match,
            'duplicate_finance_target_forged': _mut_duplicate_finance_target_forged,
            'duplicate_finance_provider_forged': _mut_duplicate_finance_provider_forged,
            'reordered_indexes': _mut_reordered_indexes,
            'dropped_index': _mut_dropped_index,
            'duplicate_index': _mut_duplicate_index,
            'invalid_slot_type': _mut_invalid_slot_type,
            'cherrypick_slot0_bad_slot1': _mut_cherrypick_slot0_bad_slot1,
        }

        with tempfile.TemporaryDirectory() as tmp:
            bdir = Path(tmp) / 'build'
            bdir.mkdir()
            for name, mut_fn in mutants.items():
                with self.subTest(mutant=name):
                    mdir = Path(tmp) / f'bundle_{name}'
                    self._build_full_listener_bundle(mdir, bdir, mutate_fn=mut_fn)
                    problems, assessment = graph_mod.verify(mdir, build_dir=bdir)
                    self.assertTrue(len(problems) > 0, f'{name} produced empty problems')
                    self.assertEqual(assessment['listener_graph_gate'], 'FAIL', name)

    def test_fl4_auditor_never_interpolates_untrusted_strings_into_problems(self):
        with tempfile.TemporaryDirectory() as tmp:
            bdir = Path(tmp) / 'build'
            bdir.mkdir()
            bpath = Path(tmp) / 'tampered_bundle'
            marker_cls = 'PRIVATE_TAMPERED_CLASS_918273'
            marker_err = 'PRIVATE_TAMPERED_CDP_ERR_645342'
            marker_reason = 'PRIVATE_TAMPERED_REASON_192837'

            def _tamper(summary):
                lg = summary['cycles'][0]['epochs']['post_actor']['listener_graph']
                lg['finance_provider']['records'][0]['selected_fields']['_instructions']['class_name'] = marker_cls
                lg['cdp_observations']['cdp_errors'] = [marker_err]
                lg['auth_provider']['records'][0]['listener_slots']['reason'] = marker_reason
                lg['auth_provider']['records'][0]['listener_slots']['normalization_ambiguous'] = True

            self._build_full_listener_bundle(bpath, bdir, mutate_fn=_tamper)
            problems, assessment = graph_mod.verify(bpath, build_dir=bdir)
            self.assertEqual(assessment['listener_graph_gate'], 'FAIL')
            joined = json.dumps(problems)
            for marker in (marker_cls, '918273', marker_err, '645342', marker_reason, '192837'):
                self.assertNotIn(marker, joined)


if __name__ == '__main__':
    unittest.main()
