#!/usr/bin/env python3
"""Finite AuthProvider -> FinanceProvider listener-graph scanner and strict verifier."""

from __future__ import annotations

import argparse
import array
import hashlib
import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.bh07_appheap import heap_oracle
from scripts.bh07_appheap import verify_payment_instructions_heap as pi_verifier

MAX_ARRAY_SLOTS = 4096
MAX_ARRAY_BACKING_NODES = 16
MAX_PROTO_CHAIN_DEPTH = 8
MAX_PROTOTYPE_BLOCK_BYTES = 256 << 10
MAX_INPUT_BYTES = 64 << 20

CLAIM_SCOPE = 'auth_provider_rooted_listener_to_finance_provider_instructions_and_finance_only'
OBSERVATION_MODE = 'hybrid_snapshot_plus_readonly_cdp_own_properties'

ALLOWED_EPOCHS = ('baseline', 'owner_active', 'post_logout', 'post_actor')
EXPECTED_CYCLE_ACTORS = ((1, 'cohost'), (2, 'member'))
COUNTER_FIELDS = (
    'ChangeNotifier__count',
    'ChangeNotifier__notificationCallStackDepth',
    'ChangeNotifier__reentrantlyRemovedListeners',
)
PROTOTYPE_DISALLOWED_CLASSES = frozenset({
    'AuthProvider',
    'FinanceProvider',
    'PaymentInstructions',
    'SessionFinance',
})
ALLOWED_V8_NODE_TYPES = frozenset({
    'hidden', 'array', 'string', 'object', 'code', 'closure', 'regexp',
    'number', 'native', 'synthetic', 'concatenated string', 'sliced string',
    'symbol', 'bigint',
})
STRUCTURAL_CLASS_ALLOWLIST = frozenset({
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
})
STRUCTURAL_SLOT_NODE_CLASSES = frozenset({
    'tear_off',
    'Closure',
    'BoundClosure',
    'Object',
})
STRUCTURAL_METHOD_ALLOWLIST = frozenset({
    'markNeedsNotifyDependents$0',
    '_session_provider$_onAuthChanged$0',
    '_club_provider$_onAuthChanged$0',
})
KNOWN_CDP_ERROR_RE = re.compile(
    r'^(?:'
    r'(?:auth_before|auth_after)_(?:missing|getter|non_integer|duplicate)_(?:_currentUser|ChangeNotifier__(?:count|notificationCallStackDepth|reentrantlyRemovedListeners))'
    r'|(?:auth_before|auth_after|finance)_get_properties_invalid'
    r'|auth_current_user_before_after_mismatch'
    r'|finance_(?:getter|duplicate)_[A-Za-z_$][A-Za-z0-9_$]{0,48}'
    r'|invalid_time_origin_(?:before|after)'
    r'|time_origin_changed_during_cdp_observation'
    r'|cardinality_invalid:auth=\d+,finance=\d+'
    r'|cdp_observation_exception'
    r')$'
)
KNOWN_SLOT_REASON_RE = re.compile(
    r'^(?:'
    r'missing_listeners_property'
    r'|listeners_not_array:(?:hidden|array|string|object|code|closure|regexp|number|native|synthetic|concatenated string|sliced string|symbol|bigint|unknown)'
    r'|unexpected_backing_type:(?:hidden|array|string|object|code|closure|regexp|number|native|synthetic|concatenated string|sliced string|symbol|bigint|unknown)'
    r'|(?:duplicate_direct_element_conflict|backing_slot_conflict|negative_slot_index|direct_vs_backing_conflict):-?\d+'
    r'|backing_node_cap_exceeded'
    r'|cdp_count_cap_exceeded'
    r'|snapshot_slot_cap_exceeded'
    r')$'
)
KNOWN_GATE_VALUES = frozenset({'PASS', 'FAIL', 'UNKNOWN', 'NOT_RUN', 'NOT_RUN_LAZY'})


def _is_valid_time_origin(val: object) -> bool:
    return isinstance(val, (int, float)) and not isinstance(val, bool) and math.isfinite(val) and val > 0


def _allowed_classes(binding: dict | None) -> frozenset[str]:
    classes = set(STRUCTURAL_CLASS_ALLOWLIST)
    if isinstance(binding, dict):
        for section in ('auth_provider', 'finance_provider', 'payment_instructions', 'session_finance', 'bound_closure'):
            sec = binding.get(section)
            if isinstance(sec, dict):
                cname = sec.get('constructor_name')
                if isinstance(cname, str) and cname:
                    classes.add(cname)
    return frozenset(classes)


def _allowed_methods(binding: dict | None) -> frozenset[str]:
    methods = set(STRUCTURAL_METHOD_ALLOWLIST)
    if isinstance(binding, dict):
        fp = binding.get('finance_provider')
        if isinstance(fp, dict):
            rm = fp.get('registration_method')
            if isinstance(rm, str) and rm:
                methods.add(rm)
    return frozenset(methods)


def _sanitize_node_type(raw_type: object) -> str:
    if isinstance(raw_type, str) and raw_type in ALLOWED_V8_NODE_TYPES:
        return raw_type
    return 'unknown'


def _sanitize_class_label(ntype: str, raw_name: object, allowed_classes: frozenset[str]) -> tuple[str | None, bool]:
    if ntype == 'object' and isinstance(raw_name, str) and raw_name in allowed_classes:
        return raw_name, True
    return None, False


def _sanitize_method_label(raw_method: object, allowed_methods: frozenset[str]) -> tuple[str | None, bool]:
    if isinstance(raw_method, str) and raw_method in allowed_methods:
        return raw_method, True
    return None, False


def _sanitize_cdp_error(raw_val: object) -> str:
    if isinstance(raw_val, str) and KNOWN_CDP_ERROR_RE.match(raw_val):
        return raw_val
    return 'cdp_error_unrecognized'


def _sanitize_slot_reason(raw_val: object) -> str:
    if isinstance(raw_val, str) and KNOWN_SLOT_REASON_RE.match(raw_val):
        return raw_val
    return 'unrecognized_reason'


def _sanitize_gate(raw_val: object) -> str:
    if isinstance(raw_val, str) and raw_val in KNOWN_GATE_VALUES:
        return raw_val
    return 'invalid'


def _sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _canonical_sha256(obj: object) -> str:
    payload = json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('utf-8')
    return hashlib.sha256(payload).hexdigest()


def _extract_closure_from_tearoff_body(js_text: str, exe_code: str) -> dict:
    """Extract Closure_fromTearOff body from executable JS without matching comments/literals."""
    patterns = (
        re.compile(r'\bClosure_fromTearOff\s*:\s*function\s*\([^)]*\)\s*\{'),
        re.compile(r'\bClosure_fromTearOff\s*\([^)]*\)\s*\{'),
    )
    for pat in patterns:
        matches = list(pat.finditer(exe_code))
        if len(matches) == 1:
            m = matches[0]
            brace_open = exe_code.index('{', m.start())
            brace_close = pi_verifier._find_closing_brace(exe_code, brace_open)
            if brace_close < 0:
                return {'ok': False, 'error': 'closure_from_tearoff_unclosed_brace'}
            return {'ok': True, 'snippet': js_text[m.start():brace_close + 1], 'exe': exe_code[m.start():brace_close + 1]}
        if len(matches) > 1:
            return {'ok': False, 'error': 'closure_from_tearoff_ambiguous'}
    return {'ok': False, 'error': 'closure_from_tearoff_missing'}


def _extract_prototype_span(
    exe_code: str,
    class_name: str,
    *,
    max_bytes: int = MAX_PROTOTYPE_BLOCK_BYTES,
) -> tuple[int | None, int | None, str | None]:
    pat = re.compile(rf'\bA\.{re.escape(class_name)}\.prototype\s*=\s*\{{')
    matches = list(pat.finditer(exe_code))
    if len(matches) != 1:
        return None, None, f'{class_name}_prototype_missing_or_ambiguous'
    open_idx = exe_code.index('{', matches[0].start())
    close_idx = pi_verifier._find_closing_brace(exe_code, open_idx, max_bytes=max_bytes)
    if close_idx < 0:
        if open_idx + max_bytes + 1 < len(exe_code):
            return None, None, f'{class_name}_prototype_exceeded_cap'
        return None, None, f'{class_name}_prototype_unterminated'
    return matches[0].start(), close_idx + 1, None


def _extract_prototype_block(
    exe_code: str,
    class_name: str,
    *,
    max_bytes: int = MAX_PROTOTYPE_BLOCK_BYTES,
) -> tuple[str | None, str | None]:
    start_idx, end_idx, err = _extract_prototype_span(exe_code, class_name, max_bytes=max_bytes)
    if err or start_idx is None or end_idx is None:
        return None, err
    return exe_code[start_idx:end_idx], None


def _assignment_targets(ctor_res: dict) -> set[str]:
    parsed = pi_verifier._parse_constructor_assignments(ctor_res.get('body') or '')
    return {item['prop'] for item in (parsed.get('assignments') or [])}


def _extract_prototype_methods(
    proto_exe: str,
    proto_start_offset: int = 0,
    *,
    max_method_bytes: int = pi_verifier.MAX_CONSTRUCTOR_SNIPPET_BYTES,
) -> tuple[dict[str, list[dict]], str | None]:
    """Parse top-level prototype methods from masked prototype block without matching nested blocks."""
    open_brace = proto_exe.find('{')
    if open_brace < 0:
        return {}, 'prototype_missing_open_brace'

    method_re = re.compile(
        r'([A-Za-z_$][A-Za-z0-9_$]*)\s*(?::\s*function(?:\s+[A-Za-z_$][A-Za-z0-9_$]*)?)?\s*\(([^()]*)\)\s*\{'
    )
    js_keywords = {'if', 'for', 'while', 'switch', 'catch', 'with', 'function', 'else', 'try', 'finally'}
    methods: dict[str, list[dict]] = {}
    pos = open_brace + 1
    limit = len(proto_exe)

    while pos < limit:
        while pos < limit and (proto_exe[pos].isspace() or proto_exe[pos] == ','):
            pos += 1
        if pos >= limit or proto_exe[pos] == '}':
            break

        m = method_re.match(proto_exe, pos)
        if m and m.group(1) not in js_keywords:
            mname = m.group(1)
            m_open = m.end() - 1
            m_close = pi_verifier._find_closing_brace(proto_exe, m_open, max_bytes=max_method_bytes)
            if m_close < 0:
                return {}, f'prototype_method_unclosed_or_exceeded_cap:{mname}'
            params = [p.strip() for p in (m.group(2) or '').split(',') if p.strip()]
            methods.setdefault(mname, []).append({
                'name': mname,
                'params': params,
                'body': proto_exe[m_open + 1:m_close],
                'body_abs_start': proto_start_offset + m_open + 1,
                'body_abs_end': proto_start_offset + m_close,
            })
            pos = m_close + 1
            continue

        # Skip scalar/object/array prototype entry (e.g. $signature: 51) at brace depth 0.
        paren = 0
        bracket = 0
        brace = 0
        while pos < limit:
            ch = proto_exe[pos]
            if ch == '(':
                paren += 1
            elif ch == ')':
                paren = max(0, paren - 1)
            elif ch == '[':
                bracket += 1
            elif ch == ']':
                bracket = max(0, bracket - 1)
            elif ch == '{':
                brace += 1
            elif ch == '}':
                if brace > 0:
                    brace -= 1
                elif paren == 0 and bracket == 0:
                    break
            elif ch == ',' and paren == 0 and bracket == 0 and brace == 0:
                pos += 1
                break
            pos += 1

    return methods, None


def _verified_this_aliases(body_exe: str) -> list[str]:
    """Return ['this', ...] aliases explicitly bound to `this` and never reassigned in body_exe."""
    aliases = ['this']
    seen = {'this'}
    alias_pat = re.compile(
        r'(?:^|[;,\{\n\r]|\b(?:var|let|const)\s)\s*([A-Za-z_$][A-Za-z0-9_$]*)\s*=\s*this\b(?![A-Za-z0-9_$.])'
    )
    for m in alias_pat.finditer(body_exe):
        name = m.group(1)
        if name in seen:
            continue
        # Reject any alias reassigned to a non-`this` value anywhere in the method.
        reassign_re = re.compile(
            rf'(?<![.\w$]){re.escape(name)}\s*=(?!=)(?!\s*this\b(?![A-Za-z0-9_$.]))'
        )
        if reassign_re.search(body_exe):
            continue
        seen.add(name)
        aliases.append(name)
    return aliases


def _extract_paren_args(code: str, open_paren_idx: int) -> tuple[list[str], int] | tuple[None, int]:
    """Extract top-level comma arguments starting at `(` inside masked executable code."""
    if open_paren_idx < 0 or open_paren_idx >= len(code) or code[open_paren_idx] != '(':
        return None, -1
    paren = 0
    bracket = 0
    brace = 0
    args: list[str] = []
    arg_start = open_paren_idx + 1
    i = open_paren_idx
    while i < len(code):
        ch = code[i]
        if ch == '(':
            paren += 1
        elif ch == ')':
            paren -= 1
            if paren == 0 and bracket == 0 and brace == 0:
                tail = code[arg_start:i].strip()
                if tail or args:
                    args.append(tail)
                return args, i
        elif ch == '[':
            bracket += 1
        elif ch == ']':
            bracket = max(0, bracket - 1)
        elif ch == '{':
            brace += 1
        elif ch == '}':
            brace = max(0, brace - 1)
        elif ch == ',' and paren == 1 and bracket == 0 and brace == 0:
            args.append(code[arg_start:i].strip())
            arg_start = i + 1
        i += 1
    return None, -1


def _verify_repo_session_finance_method(
    js_text: str,
    repo_methods: dict[str, list[dict]],
    method_name: str,
) -> bool:
    """Verify FinanceRepository method executes RPC 'get_session_finance' and returns new A.SessionFinance(...)."""
    entries = repo_methods.get(method_name)
    if not entries or len(entries) != 1:
        return False
    target = entries[0]
    delegate_m = re.fullmatch(
        r'\s*return\s+this\.([A-Za-z_$][A-Za-z0-9_$]*)\s*\([^;{}]*\)\s*;?\s*',
        target['body'],
    )
    if delegate_m:
        del_name = delegate_m.group(1)
        if del_name == method_name:
            return False
        del_entries = repo_methods.get(del_name)
        if not del_entries or len(del_entries) != 1:
            return False
        target = del_entries[0]

    t_exe = target['body']
    t_js = js_text[target['body_abs_start']:target['body_abs_end']]

    # Executable .rpc*("get_session_finance", ...) check using exact offset alignment between exe_code and js_text
    has_rpc = False
    for m in re.finditer(r'\.rpc(?:\$[A-Za-z0-9_$]+)?\s*\(', t_exe):
        idx = m.end()
        while idx < len(t_js) and t_js[idx].isspace():
            idx += 1
        lit = t_js[idx:idx + 21]
        if (
            lit in ('"get_session_finance"', "'get_session_finance'")
            and t_exe[idx:idx + 21] == (' ' * 21)
        ):
            after_lit = t_exe[idx + 21:].lstrip()
            if after_lit.startswith(',') or after_lit.startswith(')'):
                has_rpc = True
                break
    if not has_rpc:
        return False

    # Must construct and return new A.SessionFinance(...)
    if re.search(r'\breturn\s+(?:A\._asyncReturn\s*\(\s*)?new\s+A\.SessionFinance\s*\(', t_exe):
        return True

    ret_vars: list[str] = []
    for rm in re.finditer(
        r'(?:^|[;,\{\n\r]|\b(?:var|let|const)\s)\s*([A-Za-z_$][A-Za-z0-9_$]*)\s*=\s*new\s+A\.SessionFinance\s*\(',
        t_exe,
    ):
        rvar = rm.group(1)
        after_ctor = t_exe[rm.end():]
        if re.search(rf'(?<![.\w$]){re.escape(rvar)}\s*=(?!=)(?!\s*new\s+A\.SessionFinance\b)', after_ctor):
            continue
        ret_vars.append(rvar)

    for rvar in ret_vars:
        if re.search(rf'\breturn\s+A\._asyncReturn\s*\(\s*{re.escape(rvar)}\s*,', t_exe) or re.search(
            rf'\breturn\s+{re.escape(rvar)}\b(?![.\w$])', t_exe
        ):
            return True
    return False


def _derive_async_repo_finance_candidates(
    body_exe: str,
    *,
    repository_field: str,
    js_text: str,
    repo_methods: dict[str, list[dict]],
) -> set[str]:
    """Derive FinanceProvider field candidates written from an awaited verified FinanceRepository call."""
    candidates: set[str] = set()
    aliases = _verified_this_aliases(body_exe)
    alias_set = set(aliases)
    alias_pat = '|'.join(re.escape(a) for a in aliases)

    wrap_matches = list(re.finditer(
        r'A\._wrapJsFunctionForAsync\s*\(\s*function\s*\(\s*([A-Za-z_$][A-Za-z0-9_$]*)\s*,\s*([A-Za-z_$][A-Za-z0-9_$]*)\s*\)\s*\{',
        body_exe,
    ))
    if len(wrap_matches) != 1:
        return candidates
    wm = wrap_matches[0]
    res_param = wm.group(2)
    async_open = wm.end() - 1
    async_close = pi_verifier._find_closing_brace(body_exe, async_open, max_bytes=pi_verifier.MAX_CONSTRUCTOR_SNIPPET_BYTES)
    if async_close < 0:
        return candidates
    async_body = body_exe[async_open + 1:async_close]

    cb_var = None
    cb_m = re.search(r'(?:^|[;,\{\n\r]|\b(?:var|let|const)\s)\s*([A-Za-z_$][A-Za-z0-9_$]*)\s*=\s*$', body_exe[:wm.start()])
    if cb_m:
        cb_var = cb_m.group(1)

    await_re = re.compile(
        r'\breturn\s+A\._asyncAwait\s*\(\s*'
        rf'([A-Za-z_$][A-Za-z0-9_$]*)\.{re.escape(repository_field)}\.([A-Za-z_$][A-Za-z0-9_$]*)\s*\('
    )
    for am in await_re.finditer(async_body):
        recv, repo_method = am.group(1), am.group(2)
        if recv not in alias_set:
            continue
        if not _verify_repo_session_finance_method(js_text, repo_methods, repo_method):
            continue

        outer_open = async_body.find('(', am.start() + len('return A._asyncAwait'))
        await_args, _ = _extract_paren_args(async_body, outer_open)
        if not await_args or len(await_args) < 2:
            continue
        if cb_var is not None and await_args[-1].strip() != cb_var:
            continue

        before_await = async_body[:am.start()]
        last_case_pos = max(before_await.rfind('case '), before_await.rfind('default:'))
        local_pre = before_await[last_case_pos if last_case_pos >= 0 else 0:]
        goto_matches = list(re.finditer(r'\$async\$goto\s*=\s*(\d+)\s*;', local_pre))
        if not goto_matches:
            continue
        resume_case = goto_matches[-1].group(1)

        case_matches = list(re.finditer(rf'\bcase\s+{re.escape(resume_case)}\s*:', async_body))
        if len(case_matches) != 1:
            continue
        case_start = case_matches[0].end()
        case_end_m = re.search(r'\b(?:break\s*;|case\s+\d+\s*:|default\s*:)', async_body[case_start:])
        case_slice = async_body[case_start:case_start + case_end_m.start()] if case_end_m else async_body[case_start:]

        # Resume values are trusted only while unchanged. Conservatively reject
        # writes anywhere in this resume case, including compound/update forms.
        result_write = re.compile(
            rf'(?<![.\w$]){re.escape(res_param)}\s*(?:=(?!=)|[+*/%&|^\-]=|\+\+|--)'
            rf'|(?:\+\+|--)\s*{re.escape(res_param)}(?![\w$])'
        )
        if result_write.search(case_slice):
            continue
        res_vars = [res_param]
        for vm in re.finditer(
            rf'(?:^|[;,\{{\n\r]|\b(?:var|let|const)\s)\s*([A-Za-z_$][A-Za-z0-9_$]*)\s*=\s*{re.escape(res_param)}\b(?![A-Za-z0-9_$.])',
            case_slice,
        ):
            vname = vm.group(1)
            if not re.search(
                rf'(?<![.\w$]){re.escape(vname)}\s*(?:=(?!=)|[+*/%&|^\-]=|\+\+|--)'
                rf'|(?:\+\+|--)\s*{re.escape(vname)}(?![\w$])',
                case_slice[vm.end():],
            ):
                res_vars.append(vname)
        res_pat = '|'.join(re.escape(v) for v in dict.fromkeys(res_vars))

        write_re = re.compile(
            rf'(?<![.\w$])(?:{alias_pat})\.([A-Za-z_$][A-Za-z0-9_$]*)\s*=\s*(?:{res_pat})\b(?![A-Za-z0-9_$.])'
        )
        for wm_write in write_re.finditer(case_slice):
            candidates.add(wm_write.group(1))
    return candidates


def _derive_direct_session_finance_candidates(body_exe: str) -> set[str]:
    """Derive FinanceProvider field candidates from proven direct new A.SessionFinance(...) in fetchSessionFinance."""
    candidates: set[str] = set()
    aliases = _verified_this_aliases(body_exe)
    alias_pat = '|'.join(re.escape(a) for a in aliases)
    for m in re.finditer(rf'(?<![.\w$])(?:{alias_pat})\.([A-Za-z_$][A-Za-z0-9_$]*)\s*=\s*new\s+A\.SessionFinance\b', body_exe):
        candidates.add(m.group(1))
    for m in re.finditer(
        r'(?:^|[;,\{\n\r]|\b(?:var|let|const)\s)\s*([A-Za-z_$][A-Za-z0-9_$]*)\s*=\s*new\s+A\.SessionFinance\b',
        body_exe,
    ):
        vname = m.group(1)
        rest = body_exe[m.end():]
        assign_m = re.search(
            rf'(?<![.\w$])(?:{alias_pat})\.([A-Za-z_$][A-Za-z0-9_$]*)\s*=\s*{re.escape(vname)}\b(?![A-Za-z0-9_$.])',
            rest,
        )
        if assign_m and not re.search(rf'(?<![.\w$]){re.escape(vname)}\s*=(?!=)', rest[:assign_m.start()]):
            candidates.add(assign_m.group(1))
    return candidates


def _has_aliased_null_reset(method_body: str, field_name: str) -> bool:
    aliases = _verified_this_aliases(method_body)
    alias_pat = '|'.join(re.escape(a) for a in aliases)
    reset_re = re.compile(
        rf'(?<![.\w$])(?:{alias_pat})\.{re.escape(field_name)}\s*=\s*(?:(?:[A-Za-z_$][A-Za-z0-9_$]*\.)*[A-Za-z_$][A-Za-z0-9_$]*\s*=\s*)*null\b'
    )
    return bool(reset_re.search(method_body))


def _verify_finance_reset_and_optional_getter(
    fp_methods: dict[str, list[dict]],
    *,
    field_name: str,
    reg_method: str,
) -> bool:
    """Require aliased null reset in _onAuthChanged/reset helper and verify getter if present."""
    # Check optional Dart getter if not tree-shaken/inlined; if present, it must return this exact field.
    for gname in ('get$finance', 'get$sessionFinance'):
        gentries = fp_methods.get(gname)
        if gentries is not None:
            if len(gentries) != 1:
                return False
            gbody = gentries[0]['body']
            g_aliases = _verified_this_aliases(gbody)
            g_pat = '|'.join(re.escape(a) for a in g_aliases)
            if not re.search(rf'\breturn\s+(?:{g_pat})\.{re.escape(field_name)}\b(?![A-Za-z0-9_$])', gbody):
                return False

    reg_entries = fp_methods.get(reg_method)
    if reg_entries is not None:
        if len(reg_entries) != 1:
            return False
        reg_body = reg_entries[0]['body']
        if _has_aliased_null_reset(reg_body, field_name):
            return True
        reg_aliases = _verified_this_aliases(reg_body)
        reg_pat = '|'.join(re.escape(a) for a in reg_aliases)
        for cm in re.finditer(rf'(?<![.\w$])(?:{reg_pat})\.([A-Za-z_$][A-Za-z0-9_$]*)\s*\(\s*\)', reg_body):
            helper = cm.group(1)
            if helper.startswith('fetchSessionFinance'):
                continue
            hentries = fp_methods.get(helper)
            if hentries and len(hentries) == 1 and _has_aliased_null_reset(hentries[0]['body'], field_name):
                return True
        return False

    # Legacy synthetic prototype without explicit _onAuthChanged$0: require reset in non-fetch method (e.g. _resetFinance$0).
    for mname, entries in fp_methods.items():
        if mname.startswith('fetchSessionFinance'):
            continue
        if len(entries) == 1 and _has_aliased_null_reset(entries[0]['body'], field_name):
            return True
    return False


def _find_enclosing_function_bounds(exe_code: str, pos: int) -> tuple[int, int] | tuple[None, None]:
    """Walk backward from `pos` in masked JS to find enclosing function/method `{ ... }`."""
    depth = 0
    min_idx = max(0, pos - pi_verifier.MAX_CONSTRUCTOR_SNIPPET_BYTES)
    control_kw_re = re.compile(r'\b(?:if|for|while|switch|catch|with)\s*\([^()]*\)\s*$')
    fn_header_re = re.compile(
        r'(?:function(?:\s+[A-Za-z_$][A-Za-z0-9_$]*)?|[A-Za-z_$][A-Za-z0-9_$]*\s*(?::\s*function(?:\s+[A-Za-z_$][A-Za-z0-9_$]*)?)?)\s*\([^()]*\)\s*$'
    )
    i = pos - 1
    while i >= min_idx:
        ch = exe_code[i]
        if ch == '}':
            depth += 1
        elif ch == '{':
            if depth > 0:
                depth -= 1
            else:
                prefix = exe_code[max(0, i - 220):i]
                if not control_kw_re.search(prefix) and fn_header_re.search(prefix):
                    close_idx = pi_verifier._find_closing_brace(exe_code, i, max_bytes=pi_verifier.MAX_CONSTRUCTOR_SNIPPET_BYTES)
                    if close_idx > pos:
                        return i, close_idx
                    return None, None
        i -= 1
    return None, None


def _has_control_or_depth_break(code: str) -> bool:
    """Return True if `code` opens unclosed braces, exits outer block, or contains return/throw/removeListener."""
    if re.search(r'\b(?:return|throw)\b|\.removeListener\b', code):
        return True
    depth = 0
    for ch in code:
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth < 0:
                return True
    return depth != 0


def _verify_factory_listener_wiring(
    exe_code: str,
    *,
    fp_ctor: dict,
    repository_field: str,
    reg_getter: str,
    require_repo_ctor: bool,
) -> bool:
    """Verify bounded factory constructs FinanceProvider with verified AuthProvider and wires addListener$1(fin.<reg_getter>())."""
    fp_parsed = pi_verifier._parse_constructor_assignments(fp_ctor.get('body') or '')
    fp_params = fp_ctor.get('params') or []
    auth_indices = {
        fp_params.index(a['rhs'])
        for a in (fp_parsed.get('assignments') or [])
        if a['prop'] == 'auth' and a['rhs'] in fp_params
    }
    repo_indices = {
        fp_params.index(a['rhs'])
        for a in (fp_parsed.get('assignments') or [])
        if a['prop'] == repository_field and a['rhs'] in fp_params
    }
    if len(auth_indices) != 1 or len(repo_indices) != 1:
        return False
    auth_param_idx = next(iter(auth_indices))
    repo_param_idx = next(iter(repo_indices))

    valid_wirings = 0
    for m in re.finditer(r'\bnew\s+A\.FinanceProvider\s*\(', exe_code):
        fn_open, fn_close = _find_enclosing_function_bounds(exe_code, m.start())
        if fn_open is None or fn_close is None:
            continue
        fn_body = exe_code[fn_open + 1:fn_close]
        rel_pos = m.start() - (fn_open + 1)

        # Ensure `new A.FinanceProvider(` sits at brace depth 0 of the enclosing factory body.
        depth = 0
        depth_ok = True
        for ch in fn_body[:rel_pos]:
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth < 0:
                    depth_ok = False
                    break
        if not depth_ok or depth != 0:
            continue

        pre_ctor = fn_body[:rel_pos]
        lhs_m = re.search(r'(?:^|[;,\{\n\r]|\b(?:var|let|const)\s)\s*([A-Za-z_$][A-Za-z0-9_$]*)\s*=\s*$', pre_ctor)
        if not lhs_m:
            continue
        fin_var = lhs_m.group(1)

        open_paren_rel = fn_body.index('(', rel_pos)
        args, close_paren_rel = _extract_paren_args(fn_body, open_paren_rel)
        if args is None or close_paren_rel < 0 or len(args) <= max(auth_param_idx, repo_param_idx):
            continue

        auth_arg = args[auth_param_idx].strip()
        repo_arg = args[repo_param_idx].strip()
        if not re.fullmatch(r'[A-Za-z_$][A-Za-z0-9_$]*', auth_arg):
            continue

        # Auth argument variable must come from Provider_of(..., type$.AuthProvider) or new A.AuthProvider(...) and not be reassigned.
        auth_init_matches = list(re.finditer(
            rf'(?:^|[;,\{{\n\r]|\b(?:var|let|const)\s)\s*{re.escape(auth_arg)}\s*=\s*'
            r'(?:A\.Provider_of\s*\([^;{}]*\btype\$\.AuthProvider\s*\)|new\s+A\.AuthProvider\s*\([^;{}]*\))',
            pre_ctor[:lhs_m.start()],
        ))
        if not auth_init_matches:
            continue
        last_auth_init = auth_init_matches[-1]
        if re.search(rf'(?<![.\w$]){re.escape(auth_arg)}\s*=(?!=)', pre_ctor[last_auth_init.end():lhs_m.start()]):
            continue

        # When async FinanceRepository path is active, verify repo argument was constructed as FinanceRepository.
        if require_repo_ctor:
            if not re.fullmatch(r'[A-Za-z_$][A-Za-z0-9_$]*', repo_arg):
                if not re.match(r'^new\s+A\.FinanceRepository\s*\(', repo_arg):
                    continue
            else:
                repo_init_matches = list(re.finditer(
                    rf'(?:^|[;,\{{\n\r]|\b(?:var|let|const)\s)\s*{re.escape(repo_arg)}\s*=\s*new\s+A\.FinanceRepository\s*\(',
                    pre_ctor[:lhs_m.start()],
                ))
                if not repo_init_matches:
                    continue
                last_repo_init = repo_init_matches[-1]
                if re.search(rf'(?<![.\w$]){re.escape(repo_arg)}\s*=(?!=)', pre_ctor[last_repo_init.end():lhs_m.start()]):
                    continue

        after_ctor = fn_body[close_paren_rel + 1:]
        wire_re = re.compile(
            rf'(?<![.\w$]){re.escape(auth_arg)}\.addListener\$1\s*\(\s*{re.escape(fin_var)}\.{re.escape(reg_getter)}\s*\(\s*\)\s*\)'
        )
        wire_matches = list(wire_re.finditer(after_ctor))
        if len(wire_matches) != 1:
            continue
        wm = wire_matches[0]
        intervening = after_ctor[:wm.start()]
        post_wire = after_ctor[wm.end():]

        if re.search(rf'(?<![.\w$]){re.escape(fin_var)}\s*=(?!=)', intervening):
            continue
        if re.search(rf'(?<![.\w$]){re.escape(auth_arg)}\s*=(?!=)', intervening):
            continue
        if _has_control_or_depth_break(intervening):
            continue

        ret_m = re.search(rf'\breturn\s+{re.escape(fin_var)}\b(?![A-Za-z0-9_$.])', post_wire)
        if not ret_m:
            continue
        before_ret = post_wire[:ret_m.start()]
        if re.search(rf'(?<![.\w$]){re.escape(fin_var)}\s*=(?!=)', before_ret) or _has_control_or_depth_break(before_ret):
            continue

        valid_wirings += 1

    return valid_wirings == 1


def extract_listener_source_binding(build_dir: Path | str, expected_main_js_sha: str | None = None) -> dict:
    """Derive fail-closed AuthProvider -> FinanceProvider listener binding from actual main.dart.js."""
    bdir = Path(build_dir)
    main_js = bdir / 'main.dart.js'
    if not main_js.exists() or main_js.is_symlink() or not main_js.is_file():
        return {'ok': False, 'error': 'main_dart_js_missing_or_symlink'}

    raw = main_js.read_bytes()
    actual_sha = _sha256_bytes(raw)
    if expected_main_js_sha is not None and actual_sha != expected_main_js_sha:
        return {
            'ok': False,
            'error': 'main_dart_js_sha_mismatch',
            'main_dart_js_sha256': actual_sha,
            'expected_main_dart_js_sha256': expected_main_js_sha,
        }

    base_res = pi_verifier.extract_and_validate_source_binding(bdir, expected_main_js_sha=actual_sha)
    if not base_res.get('ok'):
        return {
            'ok': False,
            'error': f"base_binding_failed:{base_res.get('error', 'unknown')}",
            'main_dart_js_sha256': actual_sha,
            'base_binding': base_res,
        }
    base_binding = base_res['sanitized']

    js_text = raw.decode('utf-8', errors='replace')
    exe_code, strings = pi_verifier._executable_source(js_text)

    # 1. AuthProvider constructor & required ChangeNotifier/user fields
    auth_ctor = pi_verifier.extract_js_constructor(js_text, 'AuthProvider', code=exe_code)
    if not auth_ctor.get('ok'):
        return {'ok': False, 'error': f"auth_ctor:{auth_ctor.get('error')}", 'main_dart_js_sha256': actual_sha}
    auth_props = _assignment_targets(auth_ctor)
    required_auth = ('ChangeNotifier__listeners', *COUNTER_FIELDS, '_currentUser')
    missing_auth = [f for f in required_auth if f not in auth_props]
    if missing_auth:
        return {'ok': False, 'error': f'auth_ctor_missing_fields:{",".join(missing_auth)}', 'main_dart_js_sha256': actual_sha}

    # 2. BoundClosure constructor & Closure_fromTearOff $_name/BoundClosure proof
    bc_ctor = pi_verifier.extract_js_constructor(js_text, 'BoundClosure', code=exe_code)
    if not bc_ctor.get('ok'):
        return {'ok': False, 'error': f"bound_closure_ctor:{bc_ctor.get('error')}", 'main_dart_js_sha256': actual_sha}
    bc_props = _assignment_targets(bc_ctor)
    if '_receiver' not in bc_props or '_interceptor' not in bc_props:
        return {'ok': False, 'error': 'bound_closure_missing_receiver_or_interceptor', 'main_dart_js_sha256': actual_sha}

    tearoff_fn = _extract_closure_from_tearoff_body(js_text, exe_code)
    if not tearoff_fn.get('ok'):
        return {'ok': False, 'error': tearoff_fn.get('error'), 'main_dart_js_sha256': actual_sha}
    tearoff_exe = tearoff_fn['exe']
    if not (
        re.search(r'\bBoundClosure\b', tearoff_exe)
        and re.search(r'\$\_name\b', tearoff_exe)
        and re.search(r'Object\.create\b', tearoff_exe)
    ):
        return {'ok': False, 'error': 'closure_from_tearoff_missing_prototype_binding', 'main_dart_js_sha256': actual_sha}

    # 3. SessionFinance constructor + FinanceProvider _finance read/clear proof
    sf_ctor = pi_verifier.extract_js_constructor(js_text, 'SessionFinance', code=exe_code)
    if not sf_ctor.get('ok'):
        return {'ok': False, 'error': f"session_finance_ctor:{sf_ctor.get('error')}", 'main_dart_js_sha256': actual_sha}

    fp_ctor = pi_verifier.extract_js_constructor(js_text, 'FinanceProvider', code=exe_code)
    if not fp_ctor.get('ok'):
        return {'ok': False, 'error': f"finance_ctor:{fp_ctor.get('error')}", 'main_dart_js_sha256': actual_sha}
    fp_parsed = pi_verifier._parse_constructor_assignments(fp_ctor.get('body') or '')
    fp_assignments = fp_parsed.get('assignments') or []
    fp_props = {item['prop'] for item in fp_assignments}
    fp_null_props = {item['prop'] for item in fp_assignments if item['rhs'] == 'null'}
    if 'auth' not in fp_props:
        return {'ok': False, 'error': 'finance_ctor_missing_auth_field', 'main_dart_js_sha256': actual_sha}

    instructions_field = base_binding['finance_provider']['instructions_field']
    repository_field = base_binding['finance_provider']['repository_field']
    fp_proto_start, fp_proto_end, proto_err = _extract_prototype_span(exe_code, 'FinanceProvider')
    if proto_err or fp_proto_start is None or fp_proto_end is None:
        return {'ok': False, 'error': proto_err or 'finance_prototype_missing', 'main_dart_js_sha256': actual_sha}
    proto_exe = exe_code[fp_proto_start:fp_proto_end]
    fp_methods, fp_methods_err = _extract_prototype_methods(proto_exe, fp_proto_start)
    if fp_methods_err:
        return {'ok': False, 'error': fp_methods_err, 'main_dart_js_sha256': actual_sha}

    # Verify executable registration _instance_0_u on A.FinanceProvider.prototype
    # Note: _executable_source replaces string literals with spaces in exe_code; inspect executable statement span in js_text!
    inst_pat = re.compile(
        r'_instance_0_u\s*\(\s*_\s*=\s*A\.FinanceProvider\.prototype\s*,\s*'
        r'"([A-Za-z_$][A-Za-z0-9_$]*)"\s*,\s*"([A-Za-z_$][A-Za-z0-9_$]*)"\s*,\s*0\s*\)'
    )
    exe_inst_stubs = list(re.finditer(r'_instance_0_u\s*\(\s*_\s*=\s*A\.FinanceProvider\.prototype\b', exe_code))
    if len(exe_inst_stubs) != 1:
        return {'ok': False, 'error': 'finance_tearoff_registration_missing_or_ambiguous', 'main_dart_js_sha256': actual_sha}
    stub_start = exe_inst_stubs[0].start()
    inst_match = inst_pat.match(js_text[stub_start:stub_start + 300])
    if not inst_match:
        return {'ok': False, 'error': 'finance_tearoff_registration_parse_failed', 'main_dart_js_sha256': actual_sha}
    reg_getter, reg_method = inst_match.group(1), inst_match.group(2)

    repo_methods: dict[str, list[dict]] = {}
    repo_start, repo_end, repo_err = _extract_prototype_span(exe_code, 'FinanceRepository')
    if not repo_err and repo_start is not None and repo_end is not None:
        parsed_repo_methods, repo_methods_err = _extract_prototype_methods(exe_code[repo_start:repo_end], repo_start)
        if not repo_methods_err:
            repo_methods = parsed_repo_methods

    async_candidates: set[str] = set()
    direct_candidates: set[str] = set()
    for mname, entries in fp_methods.items():
        if not mname.startswith('fetchSessionFinance'):
            continue
        if len(entries) != 1:
            return {'ok': False, 'error': f'finance_fetch_method_ambiguous:{mname}', 'main_dart_js_sha256': actual_sha}
        mbody = entries[0]['body']
        if repo_methods:
            async_candidates.update(_derive_async_repo_finance_candidates(
                mbody,
                repository_field=repository_field,
                js_text=js_text,
                repo_methods=repo_methods,
            ))
        direct_candidates.update(_derive_direct_session_finance_candidates(mbody))

    fin_candidates = async_candidates | direct_candidates
    valid_fin_fields = [
        f for f in sorted(fin_candidates)
        if f != instructions_field
        and f in fp_null_props
        and _verify_finance_reset_and_optional_getter(fp_methods, field_name=f, reg_method=reg_method)
    ]
    if len(valid_fin_fields) != 1:
        return {
            'ok': False,
            'error': f'finance_field_ambiguous_or_missing:{valid_fin_fields}',
            'main_dart_js_sha256': actual_sha,
        }
    finance_field = valid_fin_fields[0]

    # Verify SessionFinance RPC literal string present in dart2js literal table
    has_sf_rpc = any('get_session_finance' in s for s in strings)
    if not has_sf_rpc:
        return {'ok': False, 'error': 'missing_get_session_finance_rpc_literal', 'main_dart_js_sha256': actual_sha}

    # 4. Verify executable AuthProvider.addListener$1(fin.<reg_getter>()) wiring inside bounded factory body
    if not _verify_factory_listener_wiring(
        exe_code,
        fp_ctor=fp_ctor,
        repository_field=repository_field,
        reg_getter=reg_getter,
        require_repo_ctor=(finance_field in async_candidates),
    ):
        return {'ok': False, 'error': 'finance_addListener_wiring_missing_in_executable_js', 'main_dart_js_sha256': actual_sha}

    binding = {
        'ok': True,
        'claim_scope': CLAIM_SCOPE,
        'main_dart_js_sha256': actual_sha,
        'base_binding': base_binding,
        'auth_provider': {
            'constructor_name': 'AuthProvider',
            'listeners_field': 'ChangeNotifier__listeners',
            'count_field': 'ChangeNotifier__count',
            'depth_field': 'ChangeNotifier__notificationCallStackDepth',
            'removed_field': 'ChangeNotifier__reentrantlyRemovedListeners',
            'current_user_field': '_currentUser',
        },
        'bound_closure': {
            'constructor_name': 'BoundClosure',
            'receiver_field': '_receiver',
            'interceptor_field': '_interceptor',
            'tearoff_name_property': '$_name',
        },
        'finance_provider': {
            'constructor_name': 'FinanceProvider',
            'auth_field': 'auth',
            'instructions_field': instructions_field,
            'finance_field': finance_field,
            'registration_getter': reg_getter,
            'registration_method': reg_method,
        },
        'payment_instructions': {
            'constructor_name': base_binding['payment_instructions']['constructor_name'],
            'receiver_snapshot_field': base_binding['payment_instructions']['receiver_snapshot_field'],
        },
        'session_finance': {
            'constructor_name': 'SessionFinance',
        },
    }
    binding['listener_binding_sha256'] = _canonical_sha256(binding)
    return binding


# --- V8 snapshot graph helpers ---------------------------------------------------------

def _snapshot_index(doc: dict) -> dict:
    meta = doc['snapshot']['meta']
    node_fields = meta['node_fields']
    layout, err = heap_oracle._layout(doc)
    if err or layout is None:
        raise ValueError(err or 'snapshot_layout_error')
    if 'id' not in node_fields:
        raise ValueError('snapshot_node_fields_missing_id')
    parent, parent_edge, reach_err = heap_oracle._root_reach(doc, layout)
    if reach_err or parent is None:
        raise ValueError(reach_err or 'snapshot_reach_error')

    nodes = doc['nodes']
    edges = doc['edges']
    strings = doc['strings']
    count = doc['snapshot']['node_count']
    width = layout['node_width']
    ewidth = layout['edge_width']
    count_i = layout['count_i']

    offsets = array.array('i', [0]) * (count + 1)
    total = 0
    for i in range(count):
        offsets[i] = total
        total += nodes[i * width + count_i]
    offsets[count] = total

    return {
        'doc': doc,
        'layout': layout,
        'nodes': nodes,
        'edges': edges,
        'strings': strings,
        'count': count,
        'width': width,
        'ewidth': ewidth,
        'id_i': node_fields.index('id'),
        'type_i': layout['type_i'],
        'name_i': layout['name_i'],
        'etype_i': layout['etype_i'],
        'ename_i': layout['ename_i'],
        'to_i': layout['to_i'],
        'node_type_names': layout['node_type_names'],
        'edge_type_names': layout['edge_type_names'],
        'offsets': offsets,
        'parent': parent,
        'parent_edge': parent_edge,
    }


def _node_type(idx_data: dict, node: int) -> str:
    return idx_data['node_type_names'][idx_data['nodes'][node * idx_data['width'] + idx_data['type_i']]]


def _node_name(idx_data: dict, node: int) -> str:
    return idx_data['strings'][idx_data['nodes'][node * idx_data['width'] + idx_data['name_i']]]


def _node_id(idx_data: dict, node: int) -> int:
    return idx_data['nodes'][node * idx_data['width'] + idx_data['id_i']]


def _is_rooted(idx_data: dict, node: int) -> bool:
    return node == 0 or idx_data['parent'][node] >= 0


def _iter_edges(idx_data: dict, node: int):
    offsets = idx_data['offsets']
    edges = idx_data['edges']
    strings = idx_data['strings']
    ewidth = idx_data['ewidth']
    etype_i = idx_data['etype_i']
    ename_i = idx_data['ename_i']
    to_i = idx_data['to_i']
    edge_type_names = idx_data['edge_type_names']
    width = idx_data['width']

    for rec in range(offsets[node], offsets[node + 1]):
        base = rec * ewidth
        etype = edge_type_names[edges[base + etype_i]]
        raw_label = edges[base + ename_i]
        label = raw_label if etype in ('element', 'hidden') else strings[raw_label]
        target = edges[base + to_i] // width
        yield etype, label, target


def _property_edges(idx_data: dict, node: int) -> dict[str, int]:
    props: dict[str, int] = {}
    for etype, label, target in _iter_edges(idx_data, node):
        if etype == 'property' and isinstance(label, str) and label not in props:
            props[label] = target
    return props


def _classify_nullish(idx_data: dict, node: int) -> tuple[bool, bool, str | None]:
    """Return (is_null, is_hole_or_undef, primitive_literal)."""
    ntype = _node_type(idx_data, node)
    nname = _node_name(idx_data, node)
    if ntype in ('native', 'hidden', 'object', 'synthetic'):
        if nname == 'null':
            return True, False, 'null'
        if nname == 'undefined':
            return False, True, 'undefined'
        if 'hole' in nname.lower():
            return False, True, 'the hole'
        for etype, label, target in _iter_edges(idx_data, node):
            if etype == 'internal' and label == 'to_string' and _node_type(idx_data, target) == 'string':
                s = _node_name(idx_data, target)
                if s == 'null':
                    return True, False, 'null'
                if s == 'undefined':
                    return False, True, 'undefined'
    return False, False, None


def _inspect_selected_field(
    idx_data: dict,
    node: int,
    field_name: str,
    *,
    allowed_classes: frozenset[str] = STRUCTURAL_CLASS_ALLOWLIST,
) -> dict:
    props = _property_edges(idx_data, node)
    if field_name not in props:
        return {
            'present': False,
            'node_type': None,
            'class_name': None,
            'class_recognized': False,
            'primitive_literal': None,
            'is_null': False,
        }
    target = props[field_name]
    safe_ntype = _sanitize_node_type(_node_type(idx_data, target))
    is_null, _, prim = _classify_nullish(idx_data, target)
    if is_null:
        safe_class = None
        recognized = True
    else:
        safe_class, recognized = _sanitize_class_label(safe_ntype, _node_name(idx_data, target), allowed_classes)
    return {
        'present': True,
        'node_type': safe_ntype,
        'class_name': safe_class,
        'class_recognized': recognized,
        'primitive_literal': prim,
        'is_null': is_null,
    }


def _normalize_listener_slots(idx_data: dict, listeners_node: int, cdp_count: int | None) -> dict:
    """Normalize JSArray direct element edges + internal:elements FixedArray backing without double-counting."""
    ntype = _node_type(idx_data, listeners_node)
    nname = _node_name(idx_data, listeners_node)
    if not (ntype == 'array' or (ntype == 'object' and nname == 'Array')):
        return {'normalization_ambiguous': True, 'reason': f'listeners_not_array:{_sanitize_node_type(ntype)}', 'slots': {}, 'caps_exceeded': False}

    direct_slots: dict[int, int] = {}
    backing_nodes: list[int] = []
    for etype, label, target in _iter_edges(idx_data, listeners_node):
        if etype == 'element' and isinstance(label, int):
            if label in direct_slots and direct_slots[label] != target:
                return {'normalization_ambiguous': True, 'reason': f'duplicate_direct_element_conflict:{label}', 'slots': {}, 'caps_exceeded': False}
            direct_slots[label] = target
        elif etype == 'internal' and label == 'elements':
            backing_nodes.append(target)

    if len(backing_nodes) > MAX_ARRAY_BACKING_NODES:
        return {'normalization_ambiguous': True, 'reason': 'backing_node_cap_exceeded', 'slots': {}, 'caps_exceeded': True}

    backing_slots: dict[int, int] = {}
    for bnode in backing_nodes:
        btype = _node_type(idx_data, bnode)
        if btype not in ('array', 'object'):
            return {'normalization_ambiguous': True, 'reason': f'unexpected_backing_type:{_sanitize_node_type(btype)}', 'slots': {}, 'caps_exceeded': False}
        for etype, label, target in _iter_edges(idx_data, bnode):
            if etype == 'element' and isinstance(label, int):
                if label in backing_slots and backing_slots[label] != target:
                    return {'normalization_ambiguous': True, 'reason': f'backing_slot_conflict:{label}', 'slots': {}, 'caps_exceeded': False}
                backing_slots[label] = target

    if cdp_count is not None and isinstance(cdp_count, int) and not isinstance(cdp_count, bool) and cdp_count > MAX_ARRAY_SLOTS:
        return {'normalization_ambiguous': True, 'reason': 'cdp_count_cap_exceeded', 'slots': {}, 'caps_exceeded': True}

    if len(direct_slots) > MAX_ARRAY_SLOTS * 2 or len(backing_slots) > MAX_ARRAY_SLOTS * 2:
        return {'normalization_ambiguous': True, 'reason': 'snapshot_slot_cap_exceeded', 'slots': {}, 'caps_exceeded': True}

    merged: dict[int, int] = dict(direct_slots)
    for idx, btarget in backing_slots.items():
        if idx < 0:
            return {'normalization_ambiguous': True, 'reason': f'negative_slot_index:{idx}', 'slots': {}, 'caps_exceeded': False}
        if idx in merged and merged[idx] != btarget:
            return {'normalization_ambiguous': True, 'reason': f'direct_vs_backing_conflict:{idx}', 'slots': {}, 'caps_exceeded': False}
        merged[idx] = btarget

    return {
        'normalization_ambiguous': False,
        'reason': None,
        'slots': merged,
        'caps_exceeded': False,
        'direct_slot_count': len(direct_slots),
        'backing_node_count': len(backing_nodes),
    }


def _inspect_tearoff(
    idx_data: dict,
    slot_node: int,
    *,
    binding: dict,
    rooted_finance_set: set[int],
    all_finance_set: set[int],
) -> dict:
    is_null, is_hole, _ = _classify_nullish(idx_data, slot_node)
    if is_null or is_hole:
        return {'is_null_or_hole': True, 'is_null': is_null}

    allowed_cls = _allowed_classes(binding)
    allowed_methods = _allowed_methods(binding)
    props = _property_edges(idx_data, slot_node)
    receiver_field = binding['bound_closure']['receiver_field']
    name_prop = binding['bound_closure']['tearoff_name_property']
    reg_method = binding['finance_provider']['registration_method']
    fin_class = binding['finance_provider']['constructor_name']

    recv_node = props.get(receiver_field)
    if recv_node is not None:
        raw_recv_id = _node_id(idx_data, recv_node)
        recv_id = str(int(raw_recv_id)) if (type(raw_recv_id) is int and raw_recv_id >= 0) else None
        recv_ntype = _sanitize_node_type(_node_type(idx_data, recv_node))
        recv_class, recv_recognized = _sanitize_class_label(recv_ntype, _node_name(idx_data, recv_node), allowed_cls)
    else:
        recv_id = None
        recv_class = None
        recv_recognized = False
    recv_is_rooted_finance = recv_node in rooted_finance_set if recv_node is not None else False
    recv_is_any_finance = recv_node in all_finance_set if recv_node is not None else False

    # Resolve $_name strictly from generated tearoff prototype (never instance-only, never provider node)
    raw_method_name = None
    method_on_gen_proto = False
    bound_closure_on_chain = False
    proto_is_provider = False

    cur = slot_node
    seen_proto = {cur}
    proto_hops = 0
    first_gen_proto_method = None
    cur_props = props
    while proto_hops < MAX_PROTO_CHAIN_DEPTH:
        nxt = cur_props.get('__proto__')
        if nxt is None or nxt in seen_proto:
            break
        seen_proto.add(nxt)
        proto_hops += 1
        nxt_name = _node_name(idx_data, nxt)
        if nxt_name in PROTOTYPE_DISALLOWED_CLASSES:
            proto_is_provider = True
            break
        nxt_props = _property_edges(idx_data, nxt)
        if first_gen_proto_method is None and name_prop in nxt_props:
            m_node = nxt_props[name_prop]
            if _node_type(idx_data, m_node) == 'string':
                first_gen_proto_method = _node_name(idx_data, m_node)
        # V8 names the generated Object.create(BoundClosure.prototype)
        # prototype BoundClosure too; inspect its own method before stopping.
        if nxt_name == 'BoundClosure':
            bound_closure_on_chain = True
            break
        cur = nxt
        cur_props = nxt_props

    if (not proto_is_provider) and bound_closure_on_chain and first_gen_proto_method is not None:
        raw_method_name = first_gen_proto_method
        method_on_gen_proto = True

    exact_method = method_on_gen_proto and raw_method_name == reg_method
    exact_finance_match = exact_method and recv_is_rooted_finance
    safe_method_name, method_recognized = (
        _sanitize_method_label(raw_method_name, allowed_methods) if method_on_gen_proto else (None, False)
    )
    slot_ntype = _sanitize_node_type(_node_type(idx_data, slot_node))
    safe_slot_class, _ = _sanitize_class_label(slot_ntype, _node_name(idx_data, slot_node), STRUCTURAL_SLOT_NODE_CLASSES)

    if exact_finance_match:
        kind = 'finance_listener'
    elif exact_method and not recv_is_rooted_finance:
        kind = 'wrong_receiver'
    elif recv_is_any_finance and not exact_method:
        kind = 'finance_wrong_method'
    else:
        kind = 'other_listener'

    return {
        'is_null_or_hole': False,
        'is_null': False,
        'kind': kind,
        'node_class': safe_slot_class,
        'method_name': safe_method_name,
        'method_recognized': method_recognized,
        'method_on_generated_prototype': method_on_gen_proto,
        'bound_closure_on_proto_chain': bound_closure_on_chain,
        'proto_is_provider': proto_is_provider,
        'receiver_heap_object_id': recv_id,
        'receiver_class': recv_class,
        'receiver_class_recognized': recv_recognized,
        'receiver_is_rooted_finance': recv_is_rooted_finance,
        'receiver_matches_finance_class': recv_class == fin_class,
        'exact_finance_match': exact_finance_match,
    }


def _evaluate_auth_and_slots(idx_data: dict, auth_nodes: list[int], rooted_finance_nodes: list[int], all_finance_nodes: list[int], binding: dict, cdp_count: int | None) -> list[dict]:
    records = []
    listeners_field = binding['auth_provider']['listeners_field']
    user_field = binding['auth_provider']['current_user_field']
    allowed_cls = _allowed_classes(binding)
    rooted_fin_set = set(rooted_finance_nodes)
    all_fin_set = set(all_finance_nodes)

    for a in auth_nodes:
        a_props = _property_edges(idx_data, a)
        user_info = _inspect_selected_field(idx_data, a, user_field, allowed_classes=allowed_cls)
        listeners_node = a_props.get(listeners_field)
        if listeners_node is None:
            slot_summary = {
                'normalization_ambiguous': True,
                'reason': 'missing_listeners_property',
                'caps_exceeded': False,
                'active_count': cdp_count,
                'active_slots': [],
                'unmapped_active_slots': [],
                'null_holes_in_active_range': [],
                'trailing_non_null_count': 0,
                'finance_match_count': 0,
                'wrong_receiver_count': 0,
                'finance_wrong_method_count': 0,
                'other_listener_count': 0,
            }
        else:
            norm = _normalize_listener_slots(idx_data, listeners_node, cdp_count)
            slots = norm['slots']
            active_slots = []
            unmapped = []
            null_holes = []
            trailing_non_null = 0
            finance_matches = 0
            wrong_recv = 0
            wrong_method = 0
            other_cnt = 0

            if not norm['normalization_ambiguous'] and cdp_count is not None and isinstance(cdp_count, int) and not isinstance(cdp_count, bool) and cdp_count >= 0:
                for idx in range(cdp_count):
                    if idx not in slots:
                        unmapped.append(idx)
                        continue
                    tinfo = _inspect_tearoff(
                        idx_data,
                        slots[idx],
                        binding=binding,
                        rooted_finance_set=rooted_fin_set,
                        all_finance_set=all_fin_set,
                    )
                    if tinfo.get('is_null_or_hole'):
                        null_holes.append(idx)
                    else:
                        if tinfo['kind'] == 'finance_listener':
                            finance_matches += 1
                        elif tinfo['kind'] == 'wrong_receiver':
                            wrong_recv += 1
                        elif tinfo['kind'] == 'finance_wrong_method':
                            wrong_method += 1
                        else:
                            other_cnt += 1
                    active_slots.append({'index': idx, **tinfo})

                for idx, snode in sorted(slots.items()):
                    if idx >= cdp_count:
                        is_null, is_hole, _ = _classify_nullish(idx_data, snode)
                        if not (is_null or is_hole):
                            trailing_non_null += 1

            slot_summary = {
                'normalization_ambiguous': norm['normalization_ambiguous'],
                'reason': norm.get('reason'),
                'caps_exceeded': norm.get('caps_exceeded', False),
                'active_count': cdp_count,
                'active_slots': active_slots,
                'unmapped_active_slots': unmapped,
                'null_holes_in_active_range': null_holes,
                'trailing_non_null_count': trailing_non_null,
                'finance_match_count': finance_matches,
                'wrong_receiver_count': wrong_recv,
                'finance_wrong_method_count': wrong_method,
                'other_listener_count': other_cnt,
            }

        records.append({
            'heap_object_id': str(_node_id(idx_data, a)),
            'current_user': user_info,
            'listener_slots': slot_summary,
        })
    return records


def _check_cdp_counters(cdp_obs: dict) -> tuple[bool, bool, str | None, int | None]:
    """Validate before/after CDP counters and quiescent depth/removed. Returns (ok, structural_unknown, err, count)."""
    if not isinstance(cdp_obs, dict):
        return False, True, 'missing_cdp_observations', None
    if cdp_obs.get('observation_mode') != OBSERVATION_MODE:
        return False, False, 'cdp_observation_mode_mismatch', None
    if cdp_obs.get('atomic_claim') is not False:
        return False, False, 'cdp_atomic_claim_must_be_false', None
    if cdp_obs.get('object_group_released') is not True:
        return False, False, 'cdp_object_group_not_released', None
    cdp_errs = cdp_obs.get('cdp_errors')
    if cdp_errs is not None and not isinstance(cdp_errs, list):
        return False, False, 'cdp_errors_invalid_type', None
    if cdp_errs:
        safe_errs = ','.join(_sanitize_cdp_error(x) for x in cdp_errs[:12])
        return False, False, f'cdp_errors:{safe_errs}', None

    before = cdp_obs.get('before')
    after = cdp_obs.get('after')
    if not isinstance(before, dict) or not isinstance(after, dict):
        return False, True, 'cdp_before_after_missing', None

    for key in COUNTER_FIELDS:
        bv = before.get(key)
        av = after.get(key)
        if type(bv) is not int or type(av) is not int or bv < 0 or av < 0:
            return False, False, f'cdp_counter_invalid:{key}', None
        if bv != av:
            return False, False, f'cdp_counter_race:{key}:{bv}->{av}', None

    if cdp_obs.get('counters_match') is not True:
        return False, False, 'cdp_counters_match_flag_not_true', None
    if cdp_obs.get('quiescent') is not True:
        return False, False, 'cdp_quiescent_flag_not_true', None

    if before['ChangeNotifier__notificationCallStackDepth'] != 0 or before['ChangeNotifier__reentrantlyRemovedListeners'] != 0:
        return False, False, 'cdp_non_quiescent_notifier', None

    return True, False, None, before['ChangeNotifier__count']


def _validate_snapshot_field_meta(
    meta: object,
    label: str,
    problems: list[str],
    *,
    allowed_classes: frozenset[str],
) -> dict | None:
    if not isinstance(meta, dict):
        problems.append(f'snapshot_field_not_dict:{label}')
        return None
    present = meta.get('present')
    is_null = meta.get('is_null')
    node_type = meta.get('node_type')
    class_name = meta.get('class_name')
    if type(present) is not bool:
        problems.append(f'snapshot_field_invalid_present:{label}')
        return None
    if present is not True:
        problems.append(f'snapshot_missing_field:{label}')
        return None
    if type(is_null) is not bool:
        problems.append(f'snapshot_field_invalid_is_null:{label}')
        return None
    if not isinstance(node_type, str) or node_type not in ALLOWED_V8_NODE_TYPES:
        problems.append(f'snapshot_field_invalid_node_type:{label}')
        return None
    if class_name is not None and (not isinstance(class_name, str) or not class_name):
        problems.append(f'snapshot_field_invalid_class_name:{label}')
        return None
    if is_null and class_name is not None:
        problems.append(f'snapshot_field_null_with_class:{label}')
        return None
    if class_name is not None and class_name not in allowed_classes:
        problems.append(f'snapshot_field_unrecognized_class:{label}')
        return None
    return meta


def _validate_cdp_field_meta(
    meta: object,
    label: str,
    problems: list[str],
    *,
    allowed_classes: frozenset[str],
) -> dict | None:
    if not isinstance(meta, dict):
        problems.append(f'cdp_field_missing_or_not_dict:{label}')
        return None
    present = meta.get('present')
    has_getter = meta.get('has_getter')
    is_null = meta.get('is_null')
    value_type = meta.get('value_type')
    class_name = meta.get('class_name')
    if type(has_getter) is not bool:
        problems.append(f'cdp_field_invalid_has_getter:{label}')
        return None
    if has_getter is True:
        problems.append(f'cdp_getter_detected:{label}')
        return None
    if type(present) is not bool:
        problems.append(f'cdp_field_invalid_present:{label}')
        return None
    if present is not True:
        problems.append(f'cdp_missing_field:{label}')
        return None
    if type(is_null) is not bool:
        problems.append(f'cdp_field_invalid_is_null:{label}')
        return None
    if not isinstance(value_type, str) or not value_type:
        problems.append(f'cdp_field_invalid_value_type:{label}')
        return None
    if class_name is not None and (not isinstance(class_name, str) or not class_name):
        problems.append(f'cdp_field_invalid_class_name:{label}')
        return None
    if is_null and (class_name is not None or value_type != 'null'):
        problems.append(f'cdp_field_invalid_null_shape:{label}')
        return None
    if class_name is not None and class_name not in allowed_classes:
        problems.append(f'cdp_field_unrecognized_class:{label}')
        return None
    return meta


def _recompute_and_validate_slots(
    slots_info: object,
    *,
    cdp_count: int | None,
    sole_fin_id: str | None,
    expected_fin_count_match: int,
    reg_method: str,
    fin_cls: str,
    problems: list[str],
) -> None:
    if not isinstance(slots_info, dict):
        problems.append('listener_slots_not_dict')
        return
    norm_ambig = slots_info.get('normalization_ambiguous')
    caps_exc = slots_info.get('caps_exceeded')
    if type(norm_ambig) is not bool:
        problems.append('listener_slots_invalid_normalization_ambiguous')
    if type(caps_exc) is not bool:
        problems.append('listener_slots_invalid_caps_exceeded')
    if caps_exc is True:
        problems.append('listener_array_caps_exceeded')
    if norm_ambig is True:
        problems.append(f"listener_array_ambiguous:{_sanitize_slot_reason(slots_info.get('reason'))}")

    unmapped = slots_info.get('unmapped_active_slots')
    if not isinstance(unmapped, list):
        problems.append('listener_slots_invalid_unmapped_list')
    elif unmapped:
        problems.append('unmapped_active_listener_slots')

    null_holes_reported = slots_info.get('null_holes_in_active_range')
    if not isinstance(null_holes_reported, list):
        problems.append('listener_slots_invalid_null_holes_list')

    trailing = slots_info.get('trailing_non_null_count')
    if type(trailing) is not int or trailing < 0:
        problems.append('listener_slots_invalid_trailing_count')
    elif trailing > 0:
        problems.append('trailing_non_null_listener_slot')

    active_slots = slots_info.get('active_slots')
    if not isinstance(active_slots, list):
        problems.append('listener_slots_active_slots_not_list')
        return

    active_count = slots_info.get('active_count')
    if cdp_count is not None:
        if type(active_count) is not int or active_count != cdp_count:
            problems.append('listener_slots_active_count_mismatch_cdp')
        if norm_ambig is False and caps_exc is False:
            if len(active_slots) != cdp_count:
                problems.append('active_slot_count_mismatch_cdp')

    if norm_ambig is True or caps_exc is True or cdp_count is None:
        if active_slots:
            problems.append('unexpected_active_slots_when_unscanned')
        return

    recomputed_null_holes: list[int] = []
    recomputed_finance_matches = 0
    recomputed_wrong_recv = 0
    recomputed_wrong_method = 0
    recomputed_other_cnt = 0
    seen_indices: set[int] = set()

    for pos, slot in enumerate(active_slots):
        if not isinstance(slot, dict):
            problems.append(f'slot_{pos}_not_dict')
            continue
        idx = slot.get('index')
        if type(idx) is not int or idx < 0 or idx >= cdp_count:
            problems.append(f'slot_{pos}_invalid_index')
            continue
        if idx in seen_indices:
            problems.append(f'slot_{pos}_duplicate_index')
            continue
        seen_indices.add(idx)
        if idx != pos:
            problems.append(f'slot_{pos}_non_contiguous_or_reordered_index')

        is_null_or_hole = slot.get('is_null_or_hole')
        is_null = slot.get('is_null')
        if type(is_null_or_hole) is not bool or type(is_null) is not bool:
            problems.append(f'slot_{pos}_invalid_null_flags')
            continue

        if is_null_or_hole is True:
            recomputed_null_holes.append(pos)
            continue
        if is_null is True:
            problems.append(f'slot_{pos}_contradictory_null_flags')
            continue

        kind = slot.get('kind')
        if kind not in ('finance_listener', 'wrong_receiver', 'finance_wrong_method', 'other_listener'):
            problems.append(f'slot_{pos}_invalid_kind')
            continue

        bool_fields = (
            'method_on_generated_prototype',
            'bound_closure_on_proto_chain',
            'proto_is_provider',
            'receiver_is_rooted_finance',
            'receiver_matches_finance_class',
            'exact_finance_match',
        )
        if any(type(slot.get(bf)) is not bool for bf in bool_fields):
            problems.append(f'slot_{pos}_non_bool_flag')
            continue

        proto_is_prov = slot['proto_is_provider']
        bc_on_chain = slot['bound_closure_on_proto_chain']
        method_on_proto = slot['method_on_generated_prototype']
        method_name = slot.get('method_name')
        recv_id = slot.get('receiver_heap_object_id')
        recv_cls = slot.get('receiver_class')
        recv_rooted_fin = slot['receiver_is_rooted_finance']
        recv_matches_fin_cls = slot['receiver_matches_finance_class']
        exact_fin_match = slot['exact_finance_match']

        if recv_matches_fin_cls != (recv_cls == fin_cls):
            problems.append(f'slot_{pos}_receiver_class_flag_mismatch')
        if recv_rooted_fin and (sole_fin_id is None or recv_id != sole_fin_id or recv_cls != fin_cls):
            problems.append(f'slot_{pos}_receiver_rooted_finance_mismatch')
        if method_on_proto and (proto_is_prov or not bc_on_chain or method_name is None):
            problems.append(f'slot_{pos}_invalid_prototype_method_flags')

        proto_valid_method = (
            (not proto_is_prov)
            and bc_on_chain
            and method_on_proto
            and (method_name == reg_method)
        )
        recv_matches_sole_fin = (
            (sole_fin_id is not None)
            and (recv_id == sole_fin_id)
            and (recv_cls == fin_cls)
            and recv_rooted_fin
            and recv_matches_fin_cls
        )
        recomputed_exact = proto_valid_method and recv_matches_sole_fin
        if exact_fin_match != recomputed_exact:
            problems.append(f'slot_{pos}_exact_finance_match_mismatch')

        targets_finance_candidate = (
            recv_rooted_fin
            or recv_matches_fin_cls
            or (sole_fin_id is not None and recv_id == sole_fin_id)
        )
        if recomputed_exact:
            recomputed_kind = 'finance_listener'
            recomputed_finance_matches += 1
        elif proto_valid_method and not recv_matches_sole_fin:
            recomputed_kind = 'wrong_receiver'
            recomputed_wrong_recv += 1
        elif targets_finance_candidate and not proto_valid_method:
            recomputed_kind = 'finance_wrong_method'
            recomputed_wrong_method += 1
        else:
            recomputed_kind = 'other_listener'
            recomputed_other_cnt += 1

        if kind != recomputed_kind:
            problems.append(f'slot_{pos}_kind_mismatch')

    if len(seen_indices) != cdp_count or seen_indices != set(range(cdp_count)):
        problems.append('active_slots_incomplete_or_missing_indices')

    agg_checks = (
        ('null_holes_in_active_range', recomputed_null_holes, 'null_holes_aggregate_mismatch'),
        ('finance_match_count', recomputed_finance_matches, 'finance_match_count_aggregate_mismatch'),
        ('wrong_receiver_count', recomputed_wrong_recv, 'wrong_receiver_count_aggregate_mismatch'),
        ('finance_wrong_method_count', recomputed_wrong_method, 'finance_wrong_method_count_aggregate_mismatch'),
        ('other_listener_count', recomputed_other_cnt, 'other_listener_count_aggregate_mismatch'),
    )
    for key, recomputed_val, err_code in agg_checks:
        reported_val = slots_info.get(key)
        if isinstance(recomputed_val, int):
            if type(reported_val) is not int or reported_val != recomputed_val:
                problems.append(err_code)
        elif reported_val != recomputed_val:
            problems.append(err_code)

    if recomputed_null_holes:
        problems.append('null_holes_in_active_listener_range')
    if recomputed_wrong_recv > 0:
        problems.append('finance_listener_wrong_receiver')
    if recomputed_wrong_method > 0:
        problems.append('finance_listener_wrong_method')
    if recomputed_finance_matches != expected_fin_count_match:
        problems.append(f'finance_match_count:{recomputed_finance_matches}!=expected:{expected_fin_count_match}')


def evaluate_listener_graph_record(
    record: dict,
    *,
    binding: dict,
    epoch: str,
    expected_time_origin: float | int | None = None,
) -> list[str]:
    """Independently re-evaluate one epoch's listener_graph record without trusting boolean clean flags."""
    problems: list[str] = []
    if epoch not in ALLOWED_EPOCHS:
        return ['invalid_epoch']
    if not isinstance(record, dict):
        return ['listener_graph_not_dict']
    if not binding or binding.get('ok') is not True:
        return ['listener_binding_invalid']

    allowed_cls = _allowed_classes(binding)

    if record.get('claim_scope') != CLAIM_SCOPE:
        problems.append('claim_scope_mismatch')
    if record.get('observation_mode') != OBSERVATION_MODE:
        problems.append('observation_mode_mismatch')
    if record.get('atomic_claim') is not False:
        problems.append('atomic_claim_must_be_false')
    rec_epoch = record.get('epoch')
    if rec_epoch != epoch:
        safe_rec_ep = rec_epoch if rec_epoch in ALLOWED_EPOCHS else 'unrecognized'
        problems.append(f'epoch_mismatch:{safe_rec_ep}!={epoch}')
    if record.get('binding_sha256') != binding.get('listener_binding_sha256'):
        problems.append('binding_sha256_mismatch')

    rec_origin = record.get('time_origin')
    if not _is_valid_time_origin(rec_origin):
        problems.append('invalid_or_missing_time_origin')
    if expected_time_origin is not None:
        if not _is_valid_time_origin(expected_time_origin) or rec_origin != expected_time_origin:
            problems.append('time_origin_mismatch')

    cdp_obs = record.get('cdp_observations')
    cdp_ok, cdp_unknown, cdp_err, cdp_count = _check_cdp_counters(cdp_obs)
    if not cdp_ok:
        problems.append(cdp_err or ('cdp_unknown' if cdp_unknown else 'cdp_failed'))

    if isinstance(cdp_obs, dict):
        t0 = cdp_obs.get('time_origin_before')
        t1 = cdp_obs.get('time_origin_after')
        if not _is_valid_time_origin(t0) or not _is_valid_time_origin(t1):
            problems.append('missing_or_invalid_cdp_time_origin')
        else:
            if t0 != t1:
                problems.append('cdp_time_origin_changed')
            if _is_valid_time_origin(rec_origin) and t0 != rec_origin:
                problems.append('cdp_time_origin_mismatch_graph')
            if expected_time_origin is not None and _is_valid_time_origin(expected_time_origin) and t0 != expected_time_origin:
                problems.append('cdp_time_origin_mismatch_epoch')

    auth_block = record.get('auth_provider') or {}
    fin_block = record.get('finance_provider') or {}
    auth_records = auth_block.get('records') or []
    fin_records = fin_block.get('records') or []

    rooted_auth_cnt = auth_block.get('strong_root_reachable_count')
    rooted_fin_cnt = fin_block.get('strong_root_reachable_count')
    if type(rooted_auth_cnt) is not int or not isinstance(auth_records, list) or rooted_auth_cnt != len(auth_records):
        problems.append('auth_record_count_mismatch')
    if type(rooted_fin_cnt) is not int or not isinstance(fin_records, list) or rooted_fin_cnt != len(fin_records):
        problems.append('finance_record_count_mismatch')

    if not isinstance(auth_records, list) or len(auth_records) != 1:
        got_auth = len(auth_records) if isinstance(auth_records, list) else 'invalid'
        problems.append(f'expected_1_rooted_auth_provider_got:{got_auth}')
        return problems

    auth_rec = auth_records[0]
    if not isinstance(auth_rec, dict):
        problems.append('auth_record_not_dict')
        return problems

    if isinstance(cdp_obs, dict) and str(cdp_obs.get('auth_heap_object_id')) != str(auth_rec.get('heap_object_id')):
        problems.append('cdp_auth_heap_object_id_mismatch')

    snap_user = _validate_snapshot_field_meta(
        auth_rec.get('current_user'),
        'auth_current_user',
        problems,
        allowed_classes=allowed_cls,
    )
    if isinstance(cdp_obs, dict):
        cdp_user = _validate_cdp_field_meta(
            cdp_obs.get('auth_current_user'),
            'cdp_auth_current_user',
            problems,
            allowed_classes=allowed_cls,
        )
        cdp_user_before = _validate_cdp_field_meta(
            cdp_obs.get('auth_current_user_before'),
            'cdp_auth_current_user_before',
            problems,
            allowed_classes=allowed_cls,
        )
        cdp_user_after = _validate_cdp_field_meta(
            cdp_obs.get('auth_current_user_after'),
            'cdp_auth_current_user_after',
            problems,
            allowed_classes=allowed_cls,
        )
        if cdp_user_before is not None and cdp_user_after is not None:
            if (
                cdp_user_before['is_null'] != cdp_user_after['is_null']
                or cdp_user_before['value_type'] != cdp_user_after['value_type']
                or cdp_user_before['class_name'] != cdp_user_after['class_name']
            ):
                problems.append('cdp_auth_current_user_before_after_mismatch')
        if cdp_user is not None and cdp_user_before is not None:
            if (
                cdp_user['is_null'] != cdp_user_before['is_null']
                or cdp_user['value_type'] != cdp_user_before['value_type']
                or cdp_user['class_name'] != cdp_user_before['class_name']
            ):
                problems.append('cdp_auth_current_user_summary_vs_before_mismatch')
        if snap_user is not None and cdp_user is not None:
            if snap_user['is_null'] != cdp_user['is_null'] or snap_user['class_name'] != cdp_user['class_name']:
                problems.append('auth_current_user_snapshot_vs_cdp_mismatch')

    if not isinstance(fin_records, list) or len(fin_records) > 1:
        got_fin = len(fin_records) if isinstance(fin_records, list) else 'invalid'
        problems.append(f'duplicate_rooted_finance_provider:{got_fin}')
        return problems

    sole_fin_id = str(fin_records[0].get('heap_object_id')) if len(fin_records) == 1 and isinstance(fin_records[0], dict) else None
    expected_fin_count_match = 1 if len(fin_records) == 1 else 0

    _recompute_and_validate_slots(
        auth_rec.get('listener_slots'),
        cdp_count=cdp_count,
        sole_fin_id=sole_fin_id,
        expected_fin_count_match=expected_fin_count_match,
        reg_method=binding['finance_provider']['registration_method'],
        fin_cls=binding['finance_provider']['constructor_name'],
        problems=problems,
    )

    instr_field = binding['finance_provider']['instructions_field']
    fin_field = binding['finance_provider']['finance_field']
    instr_cls = binding['payment_instructions']['constructor_name']
    sf_cls = binding['session_finance']['constructor_name']

    if len(fin_records) == 1:
        frec = fin_records[0]
        if not isinstance(frec, dict):
            problems.append('finance_record_not_dict')
            return problems
        if isinstance(cdp_obs, dict) and str(cdp_obs.get('finance_heap_object_id')) != str(frec.get('heap_object_id')):
            problems.append('cdp_finance_heap_object_id_mismatch')
        sfields = frec.get('selected_fields')
        cdp_sfields = cdp_obs.get('finance_selected_fields') if isinstance(cdp_obs, dict) else None
        if not isinstance(sfields, dict):
            problems.append('snapshot_selected_fields_not_dict')
            sfields = {}
        if not isinstance(cdp_sfields, dict):
            problems.append('missing_cdp_finance_selected_fields')

        validated_snap: dict[str, dict | None] = {}
        for fname in (instr_field, fin_field):
            snap_f = _validate_snapshot_field_meta(
                sfields.get(fname),
                fname,
                problems,
                allowed_classes=allowed_cls,
            )
            validated_snap[fname] = snap_f
            if isinstance(cdp_sfields, dict):
                cdp_f = _validate_cdp_field_meta(
                    cdp_sfields.get(fname),
                    fname,
                    problems,
                    allowed_classes=allowed_cls,
                )
                if snap_f is not None and cdp_f is not None:
                    if snap_f['is_null'] != cdp_f['is_null']:
                        problems.append(f'snapshot_vs_cdp_null_mismatch:{fname}')
                    if snap_f['class_name'] != cdp_f['class_name']:
                        problems.append(f'snapshot_vs_cdp_class_mismatch:{fname}')
                    if (not snap_f['is_null']) and ((snap_f['node_type'] == 'object') != (cdp_f['value_type'] == 'object')):
                        problems.append(f'snapshot_vs_cdp_type_mismatch:{fname}')

        snap_instr = validated_snap.get(instr_field)
        snap_fin = validated_snap.get(fin_field)
        if epoch == 'owner_active':
            if snap_user is None or snap_user['is_null'] is not False:
                problems.append('owner_active_current_user_is_null')
            if snap_instr is None or snap_instr['is_null'] is not False or snap_instr['class_name'] != instr_cls:
                problems.append('owner_active_instructions_not_populated_expected_class')
            if snap_fin is None or snap_fin['is_null'] is not False or snap_fin['class_name'] != sf_cls:
                problems.append('owner_active_finance_not_populated_expected_class')
        elif epoch in ('post_logout', 'baseline'):
            if snap_instr is None or snap_instr['is_null'] is not True:
                problems.append(f'{epoch}_instructions_not_null')
            if snap_fin is None or snap_fin['is_null'] is not True:
                problems.append(f'{epoch}_finance_not_null')
            if epoch == 'post_logout' and (snap_user is None or snap_user['is_null'] is not True):
                problems.append('post_logout_current_user_not_null')
        elif epoch == 'post_actor':
            for fname, exp_cls in ((instr_field, instr_cls), (fin_field, sf_cls)):
                sf_info = validated_snap.get(fname)
                if sf_info is not None and sf_info['is_null'] is False and sf_info['class_name'] != exp_cls:
                    problems.append(f'post_actor_wrong_class:{fname}')
    else:
        # 0 FinanceProvider instances
        if epoch in ('owner_active', 'post_logout'):
            problems.append(f'{epoch}_missing_finance_provider')

    return problems


def _decide_verdict(problems: list[str], *, rooted_fin_cnt: int, epoch: str, unknown_flags: bool) -> str:
    if unknown_flags:
        return 'UNKNOWN'
    if not problems:
        if rooted_fin_cnt == 0 and epoch in ('baseline', 'post_actor'):
            return 'NOT_RUN_LAZY'
        return 'PASS'
    return 'FAIL'


def scan_snapshot(
    raw_bytes: bytes,
    *,
    binding: dict,
    epoch: str,
    cdp_observations: dict | None = None,
    time_origin: float | int | None = None,
) -> dict:
    """Parse V8 snapshot once, extract structural Auth->Finance listener graph, and apply optional CDP observations."""
    if not binding or binding.get('ok') is not True:
        raise ValueError('valid listener_source_binding is required')
    if epoch not in ALLOWED_EPOCHS:
        raise ValueError(f'unsupported epoch: {epoch}')

    snap_sha12 = _sha256_bytes(raw_bytes)[:12]
    doc, parse_err, _ = heap_oracle.parse_snapshot(raw_bytes)
    if parse_err or doc is None:
        return {
            'claim_scope': CLAIM_SCOPE,
            'observation_mode': OBSERVATION_MODE,
            'atomic_claim': False,
            'epoch': epoch,
            'snapshot_sha256_12': snap_sha12,
            'time_origin': time_origin,
            'binding_sha256': binding.get('listener_binding_sha256'),
            'structure_ok': False,
            'ambiguous_layout': True,
            'caps_exceeded': False,
            'auth_provider': {'all_object_nodes': 0, 'strong_root_reachable_count': 0, 'records': []},
            'finance_provider': {'all_object_nodes': 0, 'strong_root_reachable_count': 0, 'records': []},
            'rooted_auth_heap_object_ids': [],
            'rooted_finance_heap_object_ids': [],
            'cdp_observations': cdp_observations,
            'findings': [parse_err or 'snapshot_parse_failed'],
            'verdict': 'UNKNOWN',
            'ok': False,
        }

    idx_data = _snapshot_index(doc)
    all_auth: list[int] = []
    all_fin: list[int] = []
    auth_cls = binding['auth_provider']['constructor_name']
    fin_cls = binding['finance_provider']['constructor_name']

    for ni in range(idx_data['count']):
        if _node_type(idx_data, ni) == 'object':
            cname = _node_name(idx_data, ni)
            if cname == auth_cls:
                all_auth.append(ni)
            elif cname == fin_cls:
                all_fin.append(ni)

    rooted_auth = [ni for ni in all_auth if _is_rooted(idx_data, ni)]
    rooted_fin = [ni for ni in all_fin if _is_rooted(idx_data, ni)]

    instr_field = binding['finance_provider']['instructions_field']
    fin_field = binding['finance_provider']['finance_field']
    allowed_cls = _allowed_classes(binding)
    fin_records = [
        {
            'heap_object_id': str(_node_id(idx_data, f)),
            'selected_fields': {
                instr_field: _inspect_selected_field(idx_data, f, instr_field, allowed_classes=allowed_cls),
                fin_field: _inspect_selected_field(idx_data, f, fin_field, allowed_classes=allowed_cls),
            },
        }
        for f in rooted_fin
    ]

    pre_scan = {
        'claim_scope': CLAIM_SCOPE,
        'observation_mode': OBSERVATION_MODE,
        'atomic_claim': False,
        'epoch': epoch,
        'snapshot_sha256_12': snap_sha12,
        'time_origin': time_origin,
        'binding_sha256': binding.get('listener_binding_sha256'),
        'structure_ok': True,
        'ambiguous_layout': False,
        'caps_exceeded': False,
        'auth_provider': {
            'all_object_nodes': len(all_auth),
            'strong_root_reachable_count': len(rooted_auth),
            'records': [],
        },
        'finance_provider': {
            'all_object_nodes': len(all_fin),
            'strong_root_reachable_count': len(rooted_fin),
            'records': fin_records,
        },
        'rooted_auth_heap_object_ids': [str(_node_id(idx_data, n)) for n in rooted_auth],
        'rooted_finance_heap_object_ids': [str(_node_id(idx_data, n)) for n in rooted_fin],
        '_internal': {
            'rooted_auth_nodes': rooted_auth,
            'rooted_fin_nodes': rooted_fin,
            'all_fin_nodes': all_fin,
        },
    }
    return apply_cdp_observations(
        pre_scan,
        binding=binding,
        epoch=epoch,
        cdp_observations=cdp_observations,
        time_origin=time_origin,
        _idx_data=idx_data,
    )


def apply_cdp_observations(
    pre_scan: dict,
    *,
    binding: dict,
    epoch: str,
    cdp_observations: dict | None,
    time_origin: float | int | None = None,
    raw_bytes: bytes | None = None,
    _idx_data: dict | None = None,
) -> dict:
    """Attach CDP observations onto an existing pre_scan and compute verdict without double-parsing when _idx_data is supplied."""
    rec = json.loads(json.dumps({k: v for k, v in pre_scan.items() if k != '_internal'}))
    if time_origin is not None:
        rec['time_origin'] = time_origin
    rec['cdp_observations'] = cdp_observations

    _, cdp_unknown, _, cdp_count = _check_cdp_counters(cdp_observations)

    if _idx_data is not None and '_internal' in pre_scan:
        internal = pre_scan['_internal']
        auth_recs = _evaluate_auth_and_slots(
            _idx_data,
            internal['rooted_auth_nodes'],
            internal['rooted_fin_nodes'],
            internal['all_fin_nodes'],
            binding,
            cdp_count,
        )
        rec['auth_provider']['records'] = auth_recs
    elif raw_bytes is not None:
        return scan_snapshot(raw_bytes, binding=binding, epoch=epoch, cdp_observations=cdp_observations, time_origin=rec['time_origin'])
    elif isinstance(cdp_observations, dict) is False or not rec['auth_provider']['records']:
        pass

    # Detect structural UNKNOWN conditions even before verdict evaluation
    auth_recs = rec['auth_provider']['records']
    rooted_auth_cnt = rec['auth_provider']['strong_root_reachable_count']
    rooted_fin_cnt = rec['finance_provider']['strong_root_reachable_count']
    unknown_flags = bool(rec.get('ambiguous_layout') or rec.get('caps_exceeded') or cdp_unknown)
    if rooted_auth_cnt == 1 and rooted_fin_cnt <= 1:
        for ar in auth_recs:
            sl = ar.get('listener_slots') or {}
            if sl.get('caps_exceeded') or sl.get('normalization_ambiguous') or sl.get('unmapped_active_slots'):
                unknown_flags = True
                rec['ambiguous_layout'] = bool(sl.get('normalization_ambiguous') or rec.get('ambiguous_layout'))
                rec['caps_exceeded'] = bool(sl.get('caps_exceeded') or rec.get('caps_exceeded'))
    else:
        # Cardinality mismatch (0 or >1 rooted AuthProvider, or >1 rooted FinanceProvider) is a hard FAIL.
        unknown_flags = bool(not rec.get('structure_ok', True) or cdp_unknown)

    problems = evaluate_listener_graph_record(rec, binding=binding, epoch=epoch, expected_time_origin=rec.get('time_origin'))
    verdict = _decide_verdict(problems, rooted_fin_cnt=rooted_fin_cnt, epoch=epoch, unknown_flags=unknown_flags)
    rec['findings'] = problems
    rec['verdict'] = verdict
    rec['ok'] = verdict in ('PASS', 'NOT_RUN_LAZY')
    return rec


def _normalize_for_scan_cache(raw_bytes: bytes, binding: dict, epoch: str, time_origin: float | int | None = None) -> dict:
    """Two-step CLI scan: parse snapshot once without CDP, saving normalized slots/records so apply-cdp avoids second parse."""
    snap_sha12 = _sha256_bytes(raw_bytes)[:12]
    doc, parse_err, _ = heap_oracle.parse_snapshot(raw_bytes)
    if parse_err or doc is None:
        return {
            'claim_scope': CLAIM_SCOPE,
            'observation_mode': OBSERVATION_MODE,
            'atomic_claim': False,
            'epoch': epoch,
            'snapshot_sha256_12': snap_sha12,
            'time_origin': time_origin,
            'binding_sha256': binding.get('listener_binding_sha256'),
            'structure_ok': False,
            'ambiguous_layout': True,
            'caps_exceeded': False,
            'auth_provider': {'all_object_nodes': 0, 'strong_root_reachable_count': 0, 'records': []},
            'finance_provider': {'all_object_nodes': 0, 'strong_root_reachable_count': 0, 'records': []},
            'rooted_auth_heap_object_ids': [],
            'rooted_finance_heap_object_ids': [],
            '_cached_slots': [],
            'findings': [parse_err or 'snapshot_parse_failed'],
        }

    idx_data = _snapshot_index(doc)
    auth_cls = binding['auth_provider']['constructor_name']
    fin_cls = binding['finance_provider']['constructor_name']
    listeners_field = binding['auth_provider']['listeners_field']
    user_field = binding['auth_provider']['current_user_field']
    instr_field = binding['finance_provider']['instructions_field']
    fin_field = binding['finance_provider']['finance_field']

    all_auth = [i for i in range(idx_data['count']) if _node_type(idx_data, i) == 'object' and _node_name(idx_data, i) == auth_cls]
    all_fin = [i for i in range(idx_data['count']) if _node_type(idx_data, i) == 'object' and _node_name(idx_data, i) == fin_cls]
    rooted_auth = [i for i in all_auth if _is_rooted(idx_data, i)]
    rooted_fin = [i for i in all_fin if _is_rooted(idx_data, i)]
    rooted_fin_set = set(rooted_fin)
    all_fin_set = set(all_fin)
    allowed_cls = _allowed_classes(binding)

    fin_records = [
        {
            'heap_object_id': str(_node_id(idx_data, f)),
            'selected_fields': {
                instr_field: _inspect_selected_field(idx_data, f, instr_field, allowed_classes=allowed_cls),
                fin_field: _inspect_selected_field(idx_data, f, fin_field, allowed_classes=allowed_cls),
            },
        }
        for f in rooted_fin
    ]

    cached_auth = []
    for a in rooted_auth:
        a_props = _property_edges(idx_data, a)
        user_info = _inspect_selected_field(idx_data, a, user_field, allowed_classes=allowed_cls)
        listeners_node = a_props.get(listeners_field)
        if listeners_node is None:
            norm = {'normalization_ambiguous': True, 'reason': 'missing_listeners_property', 'caps_exceeded': False, 'slots': {}}
        else:
            norm = _normalize_listener_slots(idx_data, listeners_node, None)
        inspected_slots = {}
        for idx, snode in norm['slots'].items():
            inspected_slots[str(idx)] = _inspect_tearoff(
                idx_data,
                snode,
                binding=binding,
                rooted_finance_set=rooted_fin_set,
                all_finance_set=all_fin_set,
            )
        cached_auth.append({
            'heap_object_id': str(_node_id(idx_data, a)),
            'current_user': user_info,
            'normalization_ambiguous': norm['normalization_ambiguous'],
            'reason': norm.get('reason'),
            'caps_exceeded': norm.get('caps_exceeded', False),
            'slots': inspected_slots,
        })

    return {
        'claim_scope': CLAIM_SCOPE,
        'observation_mode': OBSERVATION_MODE,
        'atomic_claim': False,
        'epoch': epoch,
        'snapshot_sha256_12': snap_sha12,
        'time_origin': time_origin,
        'binding_sha256': binding.get('listener_binding_sha256'),
        'structure_ok': True,
        'ambiguous_layout': any(a['normalization_ambiguous'] for a in cached_auth),
        'caps_exceeded': any(a['caps_exceeded'] for a in cached_auth),
        'auth_provider': {
            'all_object_nodes': len(all_auth),
            'strong_root_reachable_count': len(rooted_auth),
            'records': [],
        },
        'finance_provider': {
            'all_object_nodes': len(all_fin),
            'strong_root_reachable_count': len(rooted_fin),
            'records': fin_records,
        },
        'rooted_auth_heap_object_ids': [str(_node_id(idx_data, n)) for n in rooted_auth],
        'rooted_finance_heap_object_ids': [str(_node_id(idx_data, n)) for n in rooted_fin],
        '_cached_auth': cached_auth,
    }


def apply_cdp_to_cached_prescan(pre_scan: dict, *, binding: dict, epoch: str, cdp_observations: dict | None, time_origin: float | int | None = None) -> dict:
    """Apply CDP observations to a cached pre-scan JSON emitted by `scan` CLI without re-reading the snapshot."""
    rec = {k: v for k, v in pre_scan.items() if k != '_cached_auth'}
    rec = json.loads(json.dumps(rec))
    if time_origin is not None:
        rec['time_origin'] = time_origin
    rec['cdp_observations'] = cdp_observations

    _, cdp_unknown, _, cdp_count = _check_cdp_counters(cdp_observations)
    caps_hit = bool(rec.get('caps_exceeded')) or (
        cdp_count is not None and isinstance(cdp_count, int) and not isinstance(cdp_count, bool) and cdp_count > MAX_ARRAY_SLOTS
    )
    if caps_hit:
        rec['caps_exceeded'] = True

    auth_recs = []
    for cached in pre_scan.get('_cached_auth') or []:
        slots = cached['slots']
        active_slots = []
        unmapped = []
        null_holes = []
        trailing_non_null = 0
        finance_matches = 0
        wrong_recv = 0
        wrong_method = 0
        other_cnt = 0

        if not cached['normalization_ambiguous'] and not caps_hit and cdp_count is not None and isinstance(cdp_count, int) and not isinstance(cdp_count, bool) and cdp_count >= 0:
            for idx in range(cdp_count):
                key = str(idx)
                if key not in slots:
                    unmapped.append(idx)
                    continue
                tinfo = slots[key]
                if tinfo.get('is_null_or_hole'):
                    null_holes.append(idx)
                else:
                    if tinfo['kind'] == 'finance_listener':
                        finance_matches += 1
                    elif tinfo['kind'] == 'wrong_receiver':
                        wrong_recv += 1
                    elif tinfo['kind'] == 'finance_wrong_method':
                        wrong_method += 1
                    else:
                        other_cnt += 1
                active_slots.append({'index': idx, **tinfo})

            for s_idx, tinfo in slots.items():
                if int(s_idx) >= cdp_count and not tinfo.get('is_null_or_hole'):
                    trailing_non_null += 1

        auth_recs.append({
            'heap_object_id': cached['heap_object_id'],
            'current_user': cached['current_user'],
            'listener_slots': {
                'normalization_ambiguous': cached['normalization_ambiguous'],
                'reason': 'cdp_count_cap_exceeded' if caps_hit and not cached['reason'] else cached['reason'],
                'caps_exceeded': caps_hit or cached['caps_exceeded'],
                'active_count': cdp_count,
                'active_slots': active_slots,
                'unmapped_active_slots': unmapped,
                'null_holes_in_active_range': null_holes,
                'trailing_non_null_count': trailing_non_null,
                'finance_match_count': finance_matches,
                'wrong_receiver_count': wrong_recv,
                'finance_wrong_method_count': wrong_method,
                'other_listener_count': other_cnt,
            },
        })
    rec['auth_provider']['records'] = auth_recs

    rooted_auth_cnt = rec['auth_provider']['strong_root_reachable_count']
    rooted_fin_cnt = rec['finance_provider']['strong_root_reachable_count']
    unknown_flags = bool(rec.get('ambiguous_layout') or rec.get('caps_exceeded') or cdp_unknown)
    if rooted_auth_cnt == 1 and rooted_fin_cnt <= 1:
        for ar in auth_recs:
            sl = ar['listener_slots']
            if sl.get('caps_exceeded') or sl.get('normalization_ambiguous') or sl.get('unmapped_active_slots'):
                unknown_flags = True
                rec['ambiguous_layout'] = bool(sl.get('normalization_ambiguous') or rec.get('ambiguous_layout'))
                rec['caps_exceeded'] = bool(sl.get('caps_exceeded') or rec.get('caps_exceeded'))
    else:
        unknown_flags = bool(not rec.get('structure_ok', True) or cdp_unknown)

    problems = evaluate_listener_graph_record(rec, binding=binding, epoch=epoch, expected_time_origin=rec.get('time_origin'))
    verdict = _decide_verdict(
        problems,
        rooted_fin_cnt=rooted_fin_cnt,
        epoch=epoch,
        unknown_flags=unknown_flags,
    )
    rec['findings'] = problems
    rec['verdict'] = verdict
    rec['ok'] = verdict in ('PASS', 'NOT_RUN_LAZY')
    return rec


def verify(evidence_dir: Path | str, *, build_dir: Path | str | None = None, repo_root: Path = ROOT) -> tuple[list[str], dict]:
    """Strict auditor: delegates base PaymentInstructions checks, validates finite 2-cycle listener graph contract."""
    edir = Path(evidence_dir)
    problems, base_assessment = pi_verifier.verify(
        edir,
        require_dto_attribution=True,
        repo_root=repo_root,
        build_dir=build_dir,
    )
    problems = list(problems)

    summary_path = edir / 'summary.json'
    if not summary_path.is_file():
        problems.append('missing_summary_json')
        return problems, {'listener_graph_gate': 'FAIL', 'base_assessment': base_assessment}

    summary = json.loads(summary_path.read_text(encoding='utf-8'))
    main_sha = (
        ((summary.get('environment') or {}).get('build') or {}).get('artifacts') or {}
    ).get('main.dart.js')
    eff_build_dir = Path(build_dir) if build_dir is not None else (repo_root / 'build' / 'web')
    recomputed_binding = extract_listener_source_binding(eff_build_dir, expected_main_js_sha=main_sha)
    if not recomputed_binding.get('ok'):
        problems.append(f"listener_source_binding_recompute_failed:{recomputed_binding.get('error')}")
        return problems, {'listener_graph_gate': 'FAIL', 'base_assessment': base_assessment}

    recorded_binding = summary.get('listener_graph_binding')
    if not isinstance(recorded_binding, dict) or recorded_binding.get('listener_binding_sha256') != recomputed_binding.get('listener_binding_sha256'):
        problems.append('summary_listener_graph_binding_mismatch')

    lg_assessment = summary.get('listener_graph_assessment')
    if not isinstance(lg_assessment, dict):
        problems.append('missing_listener_graph_assessment')
    else:
        if lg_assessment.get('claim_scope') != CLAIM_SCOPE:
            problems.append('listener_graph_assessment_scope_mismatch')
        if lg_assessment.get('observation_mode') != OBSERVATION_MODE:
            problems.append('listener_graph_assessment_mode_mismatch')
        if lg_assessment.get('atomic_claim') is not False:
            problems.append('listener_graph_assessment_atomic_claim_must_be_false')
        if lg_assessment.get('listener_graph_gate') != 'PASS':
            problems.append(f"listener_graph_gate_not_pass:{_sanitize_gate(lg_assessment.get('listener_graph_gate'))}")

    cycles = summary.get('cycles') or []
    if len(cycles) != 2:
        problems.append(f'expected_2_cycles_got:{len(cycles)}')
    else:
        for idx, (exp_num, exp_actor) in enumerate(EXPECTED_CYCLE_ACTORS):
            cyc = cycles[idx]
            if cyc.get('cycle') != exp_num or cyc.get('actor') != exp_actor:
                problems.append(f'cycle_{idx}_identity_mismatch')
            epochs = cyc.get('epochs') or {}
            if tuple(epochs.keys()) != ALLOWED_EPOCHS and set(epochs.keys()) != set(ALLOWED_EPOCHS):
                problems.append(f'cycle_{exp_num}_epochs_mismatch')
                continue
            for ep_name in ALLOWED_EPOCHS:
                ep_scan = epochs.get(ep_name) or {}
                lg_rec = ep_scan.get('listener_graph')
                if not isinstance(lg_rec, dict):
                    problems.append(f'c{exp_num}_{ep_name}_missing_listener_graph')
                    continue
                if lg_rec.get('snapshot_sha256_12') != ep_scan.get('sha256_12'):
                    problems.append(f'c{exp_num}_{ep_name}_snapshot_sha_mismatch')
                ep_origin = ep_scan.get('time_origin')
                if not _is_valid_time_origin(ep_origin):
                    problems.append(f'c{exp_num}_{ep_name}_invalid_epoch_time_origin')
                ep_problems = evaluate_listener_graph_record(
                    lg_rec,
                    binding=recomputed_binding,
                    epoch=ep_name,
                    expected_time_origin=ep_origin,
                )
                for p in ep_problems:
                    problems.append(f'c{exp_num}_{ep_name}:{p}')

                rooted_fin = (lg_rec.get('finance_provider') or {}).get('strong_root_reachable_count')
                auth_recs = (lg_rec.get('auth_provider') or {}).get('records') or []
                slot_ambig = any(
                    isinstance(ar, dict)
                    and isinstance(ar.get('listener_slots'), dict)
                    and (
                        ar['listener_slots'].get('normalization_ambiguous') is True
                        or ar['listener_slots'].get('caps_exceeded') is True
                        or bool(ar['listener_slots'].get('unmapped_active_slots'))
                    )
                    for ar in (auth_recs if isinstance(auth_recs, list) else [])
                )
                _, cdp_unk, _, _ = _check_cdp_counters(lg_rec.get('cdp_observations'))
                recomputed_verdict = _decide_verdict(
                    ep_problems,
                    rooted_fin_cnt=rooted_fin if (type(rooted_fin) is int) else 0,
                    epoch=ep_name,
                    unknown_flags=bool(lg_rec.get('ambiguous_layout') or lg_rec.get('caps_exceeded') or slot_ambig or cdp_unk),
                )
                if exp_num == 1 and ep_name == 'baseline':
                    allowed_verdicts = ('NOT_RUN_LAZY', 'PASS')
                elif exp_num == 2 and ep_name == 'baseline':
                    allowed_verdicts = ('PASS',)
                elif ep_name in ('owner_active', 'post_logout'):
                    allowed_verdicts = ('PASS',)
                else:
                    allowed_verdicts = ('PASS', 'NOT_RUN_LAZY')

                if recomputed_verdict not in allowed_verdicts:
                    problems.append(f'c{exp_num}_{ep_name}_recomputed_verdict:{recomputed_verdict}')

    gate = 'PASS' if not problems else 'FAIL'
    return problems, {
        'listener_graph_gate': gate,
        'claim_scope': CLAIM_SCOPE,
        'observation_mode': OBSERVATION_MODE,
        'atomic_claim': False,
        'base_assessment': base_assessment,
        'problem_count': len(problems),
    }


def _read_bounded_bytes(path: Path) -> bytes:
    size = path.stat().st_size
    if size > MAX_INPUT_BYTES:
        raise ValueError(f'input exceeds MAX_INPUT_BYTES ({size} > {MAX_INPUT_BYTES})')
    return path.read_bytes()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Finite AuthProvider -> FinanceProvider listener-graph CLI')
    sub = parser.add_subparsers(dest='cmd', required=True)

    p_bind = sub.add_parser('bind')
    p_bind.add_argument('--build-dir', required=True)
    p_bind.add_argument('--expected-main-js-sha', default=None)
    p_bind.add_argument('--out', default=None)

    p_scan = sub.add_parser('scan')
    p_scan.add_argument('--snapshot', required=True)
    p_scan.add_argument('--binding', required=True)
    p_scan.add_argument('--epoch', required=True, choices=ALLOWED_EPOCHS)
    p_scan.add_argument('--out', default=None)

    p_cdp = sub.add_parser('apply-cdp')
    p_cdp.add_argument('--prescan', required=True)
    p_cdp.add_argument('--binding', required=True)
    p_cdp.add_argument('--cdp', required=True)
    p_cdp.add_argument('--epoch', required=True, choices=ALLOWED_EPOCHS)
    p_cdp.add_argument('--time-origin', type=float, default=None)

    p_ver = sub.add_parser('verify')
    p_ver.add_argument('evidence_dir')
    p_ver.add_argument('--build-dir', default=None)

    args = parser.parse_args(argv)

    if args.cmd == 'bind':
        res = extract_listener_source_binding(Path(args.build_dir), expected_main_js_sha=args.expected_main_js_sha)
        text = json.dumps(res, indent=2) + '\n'
        if args.out:
            Path(args.out).write_text(text, encoding='utf-8')
        else:
            sys.stdout.write(text)
        return 0 if res.get('ok') else 1

    if args.cmd == 'scan':
        raw = Path(args.snapshot).read_bytes()
        binding = json.loads(_read_bounded_bytes(Path(args.binding)).decode('utf-8'))
        res = _normalize_for_scan_cache(raw, binding=binding, epoch=args.epoch)
        text = json.dumps(res, indent=2) + '\n'
        if args.out:
            Path(args.out).write_text(text, encoding='utf-8')
        else:
            sys.stdout.write(text)
        return 0 if res.get('structure_ok') else 1

    if args.cmd == 'apply-cdp':
        prescan = json.loads(_read_bounded_bytes(Path(args.prescan)).decode('utf-8'))
        binding = json.loads(_read_bounded_bytes(Path(args.binding)).decode('utf-8'))
        cdp_obs = json.loads(_read_bounded_bytes(Path(args.cdp)).decode('utf-8'))
        res = apply_cdp_to_cached_prescan(
            prescan,
            binding=binding,
            epoch=args.epoch,
            cdp_observations=cdp_obs,
            time_origin=args.time_origin,
        )
        sys.stdout.write(json.dumps(res, indent=2) + '\n')
        return 0

    if args.cmd == 'verify':
        problems, assessment = verify(
            Path(args.evidence_dir),
            build_dir=Path(args.build_dir) if args.build_dir else None,
        )
        out = {'ok': not problems, 'problems': problems, 'assessment': assessment}
        sys.stdout.write(json.dumps(out, indent=2) + '\n')
        return 0 if not problems else 1

    return 2


if __name__ == '__main__':
    raise SystemExit(main())
