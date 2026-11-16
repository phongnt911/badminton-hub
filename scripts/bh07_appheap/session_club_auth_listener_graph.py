#!/usr/bin/env python3
"""Finite AuthProvider -> SessionProvider / ClubProvider listener-graph scanner and strict verifier.

Companion to `finance_auth_listener_graph.py`. Reuses calibrated V8 heap snapshot traversal,
executable artifact-binding helpers, read-only CDP own-property invariants, and bundle checks
without duplicating the scanner or altering existing Finance contracts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.bh07_appheap import finance_auth_listener_graph as base_graph
from scripts.bh07_appheap import heap_oracle
from scripts.bh07_appheap import verify_payment_instructions_heap as pi_verifier

CLAIM_SCOPE = 'auth_provider_rooted_listener_to_session_and_club_provider_selected_fields_only'
OBSERVATION_MODE = base_graph.OBSERVATION_MODE
ALLOWED_EPOCHS = base_graph.ALLOWED_EPOCHS
EXPECTED_CYCLE_ACTORS = base_graph.EXPECTED_CYCLE_ACTORS
COUNTER_FIELDS = base_graph.COUNTER_FIELDS
MAX_ARRAY_SLOTS = base_graph.MAX_ARRAY_SLOTS
MAX_INPUT_BYTES = base_graph.MAX_INPUT_BYTES
MAX_PROTOTYPE_BLOCK_BYTES = base_graph.MAX_PROTOTYPE_BLOCK_BYTES

ALLOWED_V8_STRING_TYPES = frozenset({'string', 'concatenated string', 'sliced string'})
DISALLOWED_PROTO_CLASSES = base_graph.PROTOTYPE_DISALLOWED_CLASSES | frozenset({
    'SessionProvider',
    'ClubProvider',
    'Session',
    'Session0',
    'SessionHistoryPage',
    'Club',
    'BankAccount',
})
STRUCTURAL_CLASS_ALLOWLIST = base_graph.STRUCTURAL_CLASS_ALLOWLIST | frozenset({
    'SessionProvider',
    'ClubProvider',
    'Session',
    'Session0',
    'SessionHistoryPage',
    'Club',
    'BankAccount',
})
VALID_SLOT_KINDS = frozenset({
    'session_listener',
    'club_listener',
    'wrong_receiver',
    'target_wrong_method',
    'other_listener',
})
VALID_TARGET_GATES = frozenset({'PASS', 'FAIL', 'UNKNOWN', 'NOT_RUN', 'NOT_RUN_LAZY'})
VALID_OVERALL_GATES = frozenset({'PASS', 'PARTIAL_CLUB_BANK_NOT_RUN', 'FAIL', 'UNKNOWN', 'NOT_RUN'})

KNOWN_CDP_ERROR_RE = re.compile(
    r'^(?:'
    r'(?:auth_before|auth_after)_(?:missing|getter|non_integer|duplicate)_(?:_currentUser|ChangeNotifier__(?:count|notificationCallStackDepth|reentrantlyRemovedListeners))'
    r'|(?:auth_before|auth_after|session|club)_get_properties_invalid'
    r'|auth_current_user_before_after_mismatch'
    r'|(?:session|club)_(?:getter|duplicate|missing)_[A-Za-z_$][A-Za-z0-9_$]{0,64}'
    r'|invalid_time_origin_(?:before|after)'
    r'|time_origin_changed_during_cdp_observation'
    r'|cardinality_invalid:auth=\d+,session=\d+,club=\d+'
    r'|cdp_observation_exception'
    r')$'
)

DEFAULT_CYCLE_POST_ACTOR_CONTRACTS = {
    1: {
        'actor': 'cohost',
        'session': {
            'session_id': 'refetched',
            'current_session': 'refetched',
            'history': 'refetched',
        },
        'club': {
            'club_id': 'null',
            'current_club': 'null',
            'bank_account': 'null',
        },
    },
    2: {
        'actor': 'member',
        'session': {
            'session_id': 'null',
            'current_session': 'null',
            'history': 'refetched',
        },
        'club': {
            'club_id': 'null',
            'current_club': 'null',
            'bank_account': 'null',
        },
    },
}

FORBIDDEN_SESSION_CLUB_CLAIMS = (
    r'entire[_\s-]+provider[_\s-]+clean',
    r'entire[_\s-]+state[_\s-]+clean',
    r'full[_\s-]+sessionprovider[_\s-]+clean',
    r'full[_\s-]+clubprovider[_\s-]+clean',
    r'all[_\s-]+auth[_\s-]+listeners[_\s-]+clean',
    r'all[_\s-]+fields[_\s-]+clean',
)


def _sanitize_cdp_error(raw_val: object) -> str:
    if isinstance(raw_val, str) and KNOWN_CDP_ERROR_RE.match(raw_val):
        return raw_val
    return 'cdp_error_unrecognized'


def _sanitize_target_gate(raw_val: object) -> str:
    if isinstance(raw_val, str) and raw_val in VALID_TARGET_GATES:
        return raw_val
    return 'invalid'


def _sanitize_overall_gate(raw_val: object) -> str:
    if isinstance(raw_val, str) and raw_val in VALID_OVERALL_GATES:
        return raw_val
    return 'invalid'


def _allowed_classes(binding: dict | None) -> frozenset[str]:
    classes = set(STRUCTURAL_CLASS_ALLOWLIST)
    if isinstance(binding, dict):
        for sec in ('auth_provider', 'bound_closure', 'session_provider', 'club_provider'):
            info = binding.get(sec)
            if isinstance(info, dict):
                cname = info.get('constructor_name')
                if isinstance(cname, str) and cname:
                    classes.add(cname)
        models = binding.get('models')
        if isinstance(models, dict):
            for minfo in models.values():
                if isinstance(minfo, dict):
                    cname = minfo.get('constructor_name')
                    if isinstance(cname, str) and cname:
                        classes.add(cname)
    return frozenset(classes)


def _allowed_methods(binding: dict | None) -> frozenset[str]:
    methods = set(base_graph.STRUCTURAL_METHOD_ALLOWLIST)
    if isinstance(binding, dict):
        for sec in ('session_provider', 'club_provider'):
            info = binding.get(sec)
            if isinstance(info, dict):
                rm = info.get('registration_method')
                if isinstance(rm, str) and rm:
                    methods.add(rm)
    return frozenset(methods)


# --- Artifact-bound executable source verification helpers ----------------------------

def _extract_top_level_a_function(js_text: str, exe_code: str, fn_name: str) -> str | None:
    """Return executable body of top-level helper `A.<fn_name>` if uniquely defined."""
    esc = re.escape(fn_name)
    patterns = (
        re.compile(rf'(?<![.\w$]){esc}\s*:\s*function(?:\s+{esc})?\s*\([^)]*\)\s*\{{'),
        re.compile(rf'(?:^|[,\{{\n\r])\s*{esc}\s*\([^)]*\)\s*\{{'),
    )
    for pat in patterns:
        matches = list(pat.finditer(exe_code))
        if len(matches) == 1:
            open_idx = exe_code.index('{', matches[0].start())
            close_idx = pi_verifier._find_closing_brace(exe_code, open_idx)
            if close_idx > open_idx:
                return exe_code[open_idx + 1:close_idx]
        if len(matches) > 1:
            return None
    return None


def _split_top_level_items(code: str) -> list[tuple[str, str, int, int]]:
    """Split masked executable JS block into top-level ('stmt'|'block', text, start, end) items."""
    items: list[tuple[str, str, int, int]] = []
    paren = bracket = brace = 0
    start = 0
    n = len(code)
    i = 0
    while i < n:
        ch = code[i]
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
                if paren == 0 and bracket == 0 and brace == 0:
                    seg = code[start:i + 1].strip()
                    if seg:
                        items.append(('block', seg, start, i + 1))
                    start = i + 1
        elif ch == ';' and paren == 0 and bracket == 0 and brace == 0:
            seg = code[start:i].strip()
            if seg:
                items.append(('stmt', seg, start, i + 1))
            start = i + 1
        i += 1
    tail = code[start:].strip()
    if tail:
        items.append(('stmt', tail, start, n))
    return items


def _strip_leading_if_else(st: str) -> tuple[str, bool]:
    """Strip leading `else` or balanced `if (...)` without braces; return (inner_stmt, was_conditional)."""
    s = st.lstrip()
    cond = False
    while True:
        if re.match(r'^else(?![.\w$])\s*', s):
            s = re.sub(r'^else(?![.\w$])\s*', '', s, count=1).lstrip()
            cond = True
            continue
        m_if = re.match(r'^if\s*\(', s)
        if m_if:
            _, close_idx = base_graph._extract_paren_args(s, m_if.end() - 1)
            if close_idx > 0:
                s = s[close_idx + 1:].lstrip()
                cond = True
                continue
        break
    return s, cond


def _has_trivially_falsy_if_guard(st: str) -> bool:
    """Return True if a leading `if (...)` guard has a literal falsy condition."""
    s = st.lstrip()
    while True:
        if re.match(r'^else(?![.\w$])\s*', s):
            s = re.sub(r'^else(?![.\w$])\s*', '', s, count=1).lstrip()
            continue
        m_if = re.match(r'^if\s*\(', s)
        if m_if:
            _, close_idx = base_graph._extract_paren_args(s, m_if.end() - 1)
            if close_idx > 0:
                cond_inner = s[m_if.end():close_idx].strip()
                while cond_inner.startswith('(') and cond_inner.endswith(')'):
                    inner_close = _extract_balanced_call_end(cond_inner, 0)
                    if inner_close != len(cond_inner) - 1:
                        break
                    cond_inner = cond_inner[1:-1].strip()
                if cond_inner in ('false', '0', 'null', 'undefined', '!1', '!true', '""', "''"):
                    return True
                s = s[close_idx + 1:].lstrip()
                continue
        break
    return False


def _iter_top_level_decls(stmt_inner: str) -> list[str]:
    """Split top-level comma expressions/declarations (outside (), [], {}) after optional var/let/const."""
    s = re.sub(r'^(?:var|let|const)\s+', '', stmt_inner.strip())
    parts: list[str] = []
    paren = bracket = brace = 0
    start = 0
    for i, ch in enumerate(s):
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
            brace = max(0, brace - 1)
        elif ch == ',' and paren == 0 and bracket == 0 and brace == 0:
            piece = s[start:i].strip()
            if piece:
                parts.append(piece)
            start = i + 1
    tail = s[start:].strip()
    if tail:
        parts.append(tail)
    return parts


def _peel_assignments(expr_part: str) -> tuple[list[str], str]:
    """Peel chained `a = b.c = rhs` assignments into ([targets], rhs)."""
    targets: list[str] = []
    cur = expr_part.strip()
    while True:
        am = re.match(r'^([A-Za-z_$][A-Za-z0-9_$]*(?:\.[A-Za-z_$][A-Za-z0-9_$]*)?)\s*=(?!=)\s*(.+)$', cur, re.DOTALL)
        if not am:
            break
        targets.append(am.group(1))
        cur = am.group(2).strip()
    return targets, cur


def _extract_balanced_call_end(expr: str, open_paren_idx: int) -> int:
    """Return index of matching `)` for `(` at `open_paren_idx`, or -1."""
    _, close_idx = base_graph._extract_paren_args(expr, open_paren_idx)
    return close_idx


def _is_direct_model_ctor_expr(expr: str, model_class: str) -> bool:
    """Check `expr` is strictly a single `new A.<model_class>(...)` expression."""
    nm = re.match(rf'^new\s+A\.{re.escape(model_class)}\s*\(', expr.strip())
    if not nm:
        return False
    s = expr.strip()
    close_idx = _extract_balanced_call_end(s, nm.end() - 1)
    return close_idx >= 0 and s[close_idx + 1:].strip() == ''


def _verify_deserializer_body(fn_body: str, model_class: str) -> bool:
    """Verify every `return` inside deserializer returns a `new A.<model_class>(...)` value (no null/discard)."""
    return_exprs: list[str] = []
    for rm in re.finditer(r'(?<![.\w$])return(?![\w$])', fn_body):
        pos = rm.end()
        paren = bracket = brace = 0
        n = len(fn_body)
        while pos < n:
            ch = fn_body[pos]
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
                if brace == 0:
                    break
                brace -= 1
            elif ch == ';' and paren == 0 and bracket == 0 and brace == 0:
                break
            pos += 1
        return_exprs.append(fn_body[rm.end():pos].strip())

    if not return_exprs:
        return False

    esc_cls = re.escape(model_class)
    local_model_vars: set[str] = set()
    for m in re.finditer(
        rf'(?:^|[;,\{{\n\r]|\b(?:var|let|const)\s)\s*([A-Za-z_$][A-Za-z0-9_$]*)\s*=\s*new\s+A\.{esc_cls}\s*\(',
        fn_body,
    ):
        vname = m.group(1)
        close_idx = _extract_balanced_call_end(fn_body, m.end() - 1)
        if close_idx < 0:
            continue
        after_stmt = fn_body[close_idx + 1:]
        if not re.match(r'\s*(?:;|,|\}|$)', after_stmt):
            continue
        if re.search(
            rf'(?<![.\w$]){re.escape(vname)}\s*(?:=(?!=)|[+*/%&|^\-]=|\+\+|--)|(?:\+\+|--)\s*{re.escape(vname)}(?![\w$])',
            fn_body[close_idx + 1:],
        ):
            continue
        local_model_vars.add(vname)

    for ret in return_exprs:
        if _is_direct_model_ctor_expr(ret, model_class):
            continue
        if re.fullmatch(r'[A-Za-z_$][A-Za-z0-9_$]*', ret) and ret in local_model_vars:
            continue
        return False
    return True


def _resolve_model_class_from_deserializer(
    js_text: str,
    exe_code: str,
    *,
    deserializer_name: str,
    fallback_candidates: tuple[str, ...],
) -> tuple[str | None, dict | None]:
    """Bind compiled JS model class name from its executable deserializer or constructor."""
    fn_body = _extract_top_level_a_function(js_text, exe_code, deserializer_name)
    if fn_body is not None:
        ctors = set(re.findall(r'(?<![.\w$])new\s+A\.([A-Za-z_$][A-Za-z0-9_$]*)\s*\(', fn_body))
        for cname in sorted(ctors):
            if _verify_deserializer_body(fn_body, cname):
                ctor = pi_verifier.extract_js_constructor(js_text, cname, code=exe_code)
                if ctor.get('ok'):
                    return cname, ctor
        return None, None

    for cand in fallback_candidates:
        ctor = pi_verifier.extract_js_constructor(js_text, cand, code=exe_code)
        if ctor.get('ok'):
            return cand, ctor
    return None, None


_IDENT_ONLY_RE = re.compile(r'^[A-Za-z_$][A-Za-z0-9_$]*$')
_TYPE_DOT_RE = re.compile(r'^type\$\.[A-Za-z_$][A-Za-z0-9_$]*$')


def _verified_a_aliases_with_defs(body_exe: str) -> tuple[list[str], dict[str, int]]:
    """Return (['A', ...], first_def_offsets) for un-reassigned locals explicitly bound to `A`."""
    aliases = ['A']
    seen = {'A'}
    first_def: dict[str, int] = {'A': -1}
    alias_pat = re.compile(
        r'(?:^|[;,\{\n\r]|\b(?:var|let|const)\s)\s*([A-Za-z_$][A-Za-z0-9_$]*)\s*=\s*A(?![.\w$])'
    )
    for m in alias_pat.finditer(body_exe):
        aname = m.group(1)
        if aname in seen:
            continue
        reassign_re = re.compile(
            rf'(?<![.\w$]){re.escape(aname)}\s*(?:=(?!=)(?!\s*A(?![.\w$]))|[+*/%&|^\-]=|\+\+|--)'
            rf'|(?:\+\+|--)\s*{re.escape(aname)}(?![\w$])'
            rf'|(?<![.\w$]){re.escape(aname)}\.[A-Za-z_$][A-Za-z0-9_$]*\s*=(?!=)'
        )
        if reassign_re.search(body_exe):
            continue
        seen.add(aname)
        aliases.append(aname)
        first_def[aname] = m.start()
    return aliases, first_def


def _verified_type_aliases_with_defs(body_exe: str) -> tuple[set[str], dict[str, int]]:
    """Return (alias_set, first_def_offsets) for un-reassigned locals explicitly bound to `type$.<Type>`."""
    if re.search(r'(?<![.\w$])type\$\s*(?:=(?!=)|[+*/%&|^\-]=|\.[A-Za-z_$][A-Za-z0-9_$]*\s*=(?!=))', body_exe):
        return set(), {}
    aliases: set[str] = set()
    first_def: dict[str, int] = {}
    alias_pat = re.compile(
        r'(?:^|[;,\{\n\r]|\b(?:var|let|const)\s)\s*([A-Za-z_$][A-Za-z0-9_$]*)\s*=\s*(type\$\.[A-Za-z_$][A-Za-z0-9_$]*)(?![.\w$])'
    )
    for m in alias_pat.finditer(body_exe):
        aname = m.group(1)
        texpr = m.group(2)
        if aname in aliases or aname == 'type$':
            continue
        reassign_re = re.compile(
            rf'(?<![.\w$]){re.escape(aname)}\s*(?:=(?!=)(?!\s*{re.escape(texpr)}(?![.\w$]))|[+*/%&|^\-]=|\+\+|--)'
            rf'|(?:\+\+|--)\s*{re.escape(aname)}(?![\w$])'
            rf'|(?<![.\w$]){re.escape(aname)}\.[A-Za-z_$][A-Za-z0-9_$]*\s*=(?!=)'
        )
        if reassign_re.search(body_exe):
            continue
        aliases.add(aname)
        first_def[aname] = m.start()
    return aliases, first_def


def _has_top_level_comma(expr: str) -> bool:
    """Return True if `expr` contains a comma `,` at depth 0 outside (), [], {}."""
    paren = bracket = brace = 0
    for ch in expr:
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
            brace = max(0, brace - 1)
        elif ch == ',' and paren == 0 and bracket == 0 and brace == 0:
            return True
    return False


def _invalidate_untracked_writes_in_decl(
    decl: str,
    *,
    rhs: str,
    targets: list[str],
    tracked_vars: set[str],
    protected_var: str | None = None,
    tracked_fields: set[str] | None = None,
    alias_pat: str | None = None,
) -> None:
    """Discard tracked locals/fields written inside compound ops, nested expressions, or non-peeled decls."""
    scan_span = rhs if targets else decl
    for v in list(tracked_vars):
        if v == protected_var:
            continue
        if re.search(rf'(?<![.\w$]){re.escape(v)}\s*(?:[+*/%&|^\-]=|\+\+|--)|(?:\+\+|--)\s*{re.escape(v)}(?![\w$])', decl):
            tracked_vars.discard(v)
        elif re.search(rf'(?<![.\w$]){re.escape(v)}\s*=(?!=)', scan_span):
            tracked_vars.discard(v)
    if tracked_fields is not None and alias_pat:
        for af in list(tracked_fields):
            if re.search(rf'(?<![.\w$])(?:{alias_pat})\.{re.escape(af)}\s*(?:[+*/%&|^\-]=|\+\+|--)', decl) or re.search(
                rf'(?<![.\w$])(?:{alias_pat})\.{re.escape(af)}\s*(?:=(?!=)|[+*/%&|^\-]=|\+\+|--)', scan_span
            ):
                tracked_fields.discard(af)


def _strip_outer_parens_no_comma(expr: str) -> str | None:
    """Strip grouping parentheses iff the expression has no top-level comma sequence operator."""
    s = expr.strip()
    while s.startswith('('):
        close_idx = _extract_balanced_call_end(s, 0)
        if close_idx != len(s) - 1:
            break
        inner = s[1:-1].strip()
        if not inner or _has_top_level_comma(inner):
            return None
        s = inner
    if not s or _has_top_level_comma(s):
        return None
    return s


def _is_valid_type_cast_receiver(
    recv: str,
    *,
    body_exe: str | None = None,
    type_alias_set: set[str] | None = None,
    type_alias_defs: dict[str, int] | None = None,
    stmt_abs_pos: int = 10**9,
) -> bool:
    if _TYPE_DOT_RE.fullmatch(recv):
        if body_exe and re.search(
            r'(?<![.\w$])type\$\s*(?:=(?!=)|[+*/%&|^\-]=|\.[A-Za-z_$][A-Za-z0-9_$]*\s*=(?!=))',
            body_exe,
        ):
            return False
        return True
    return bool(
        type_alias_set
        and recv in type_alias_set
        and (type_alias_defs or {}).get(recv, 10**9) < stmt_abs_pos
    )


def _is_value_preserving_rpc_expr(
    expr: str,
    *,
    source_vars: set[str],
    a_alias_set: set[str],
    a_alias_defs: dict[str, int],
    type_alias_set: set[str] | None = None,
    type_alias_defs: dict[str, int] | None = None,
    body_exe: str | None = None,
    stmt_abs_pos: int = 10**9,
    _depth: int = 0,
) -> bool:
    """Recognize only dart2js value-preserving expressions over `source_vars` (no comma/ternary/discard ops)."""
    if _depth > 8 or not source_vars:
        return False
    s = _strip_outer_parens_no_comma(expr)
    if not s:
        return False
    if _IDENT_ONLY_RE.fullmatch(s):
        return s in source_vars

    cm = re.match(
        r'^([A-Za-z_$][A-Za-z0-9_$]*(?:\.[A-Za-z_$][A-Za-z0-9_$]*)?)\.([A-Za-z_$][A-Za-z0-9_$]*)\s*\(',
        s,
    )
    if not cm:
        return False
    recv, method = cm.group(1), cm.group(2)
    args, close_idx = base_graph._extract_paren_args(s, cm.end() - 1)
    if args is None or close_idx != len(s) - 1 or not args:
        return False

    if method == '_as' and len(args) == 1 and _is_valid_type_cast_receiver(
        recv,
        body_exe=body_exe,
        type_alias_set=type_alias_set,
        type_alias_defs=type_alias_defs,
        stmt_abs_pos=stmt_abs_pos,
    ):
        return _is_value_preserving_rpc_expr(
            args[0],
            source_vars=source_vars,
            a_alias_set=a_alias_set,
            a_alias_defs=a_alias_defs,
            type_alias_set=type_alias_set,
            type_alias_defs=type_alias_defs,
            body_exe=body_exe,
            stmt_abs_pos=stmt_abs_pos,
            _depth=_depth + 1,
        )

    if (
        method == 'LinkedHashMap_LinkedHashMap$from'
        and 1 <= len(args) <= 3
        and '.' not in recv
        and recv in a_alias_set
        and (recv == 'A' or a_alias_defs.get(recv, 10**9) < stmt_abs_pos)
    ):
        return _is_value_preserving_rpc_expr(
            args[0],
            source_vars=source_vars,
            a_alias_set=a_alias_set,
            a_alias_defs=a_alias_defs,
            type_alias_set=type_alias_set,
            type_alias_defs=type_alias_defs,
            body_exe=body_exe,
            stmt_abs_pos=stmt_abs_pos,
            _depth=_depth + 1,
        )

    return False


def _is_value_preserving_ctor_arg(
    expr: str,
    *,
    source_vars: set[str],
    a_alias_set: set[str],
    a_alias_defs: dict[str, int],
    type_alias_set: set[str] | None = None,
    type_alias_defs: dict[str, int] | None = None,
    body_exe: str | None = None,
    stmt_abs_pos: int = 10**9,
) -> bool:
    if _is_value_preserving_rpc_expr(
        expr,
        source_vars=source_vars,
        a_alias_set=a_alias_set,
        a_alias_defs=a_alias_defs,
        type_alias_set=type_alias_set,
        type_alias_defs=type_alias_defs,
        body_exe=body_exe,
        stmt_abs_pos=stmt_abs_pos,
    ):
        return True
    s = _strip_outer_parens_no_comma(expr)
    if not s:
        return False
    pm = re.fullmatch(r'([A-Za-z_$][A-Za-z0-9_$]*)\.[A-Za-z_$][A-Za-z0-9_$]*', s)
    if pm:
        return pm.group(1) in source_vars
    im = re.match(r'^([A-Za-z_$][A-Za-z0-9_$]*)\.\$index\s*\(', s)
    if im and im.group(1) in source_vars:
        args, close_idx = base_graph._extract_paren_args(s, im.end() - 1)
        return bool(args and close_idx == len(s) - 1)
    return False


def _find_top_level_first_arg_span(code: str, open_paren_idx: int) -> tuple[int, int] | tuple[None, None]:
    """Return exact (start, end) character span of the first call argument inside `code[open_paren_idx:]`."""
    if open_paren_idx < 0 or open_paren_idx >= len(code) or code[open_paren_idx] != '(':
        return None, None
    paren = bracket = brace = 0
    for i in range(open_paren_idx, len(code)):
        ch = code[i]
        if ch == '(':
            paren += 1
        elif ch == ')':
            paren -= 1
            if paren == 0 and bracket == 0 and brace == 0:
                return open_paren_idx + 1, i
        elif ch == '[':
            bracket += 1
        elif ch == ']':
            bracket = max(0, bracket - 1)
        elif ch == '{':
            brace += 1
        elif ch == '}':
            brace = max(0, brace - 1)
        elif ch == ',' and paren == 1 and bracket == 0 and brace == 0:
            return open_paren_idx + 1, i
    return None, None


def _rhs_produces_model_from_vars(
    rhs: str,
    *,
    source_vars: set[str],
    valid_desers: set[str],
    a_alias_set: set[str],
    a_alias_defs: dict[str, int],
    stmt_abs_pos: int,
    model_class: str,
    allow_model_ctor: bool,
    type_alias_set: set[str] | None = None,
    type_alias_defs: dict[str, int] | None = None,
    body_exe: str | None = None,
) -> bool:
    """Verify RHS invokes an un-reassigned deserializer/ctor consuming a value-preserving RPC arg0 with no trailing discard."""
    s = _strip_outer_parens_no_comma(rhs)
    if not s or not source_vars:
        return False

    cm = re.match(r'^([A-Za-z_$][A-Za-z0-9_$]*)\.([A-Za-z_$][A-Za-z0-9_$]*)\s*\(', s)
    if cm:
        a_alias, dname = cm.group(1), cm.group(2)
        if (
            dname in valid_desers
            and a_alias in a_alias_set
            and (a_alias == 'A' or a_alias_defs.get(a_alias, 10**9) < stmt_abs_pos)
        ):
            args, close_idx = base_graph._extract_paren_args(s, cm.end() - 1)
            if args is None or close_idx != len(s) - 1 or not args:
                return False
            max_args = 3 if 'fromResponse' in dname else 1
            if len(args) > max_args:
                return False
            return _is_value_preserving_rpc_expr(
                args[0],
                source_vars=source_vars,
                a_alias_set=a_alias_set,
                a_alias_defs=a_alias_defs,
                type_alias_set=type_alias_set,
                type_alias_defs=type_alias_defs,
                body_exe=body_exe,
                stmt_abs_pos=stmt_abs_pos,
            )
        return False

    if allow_model_ctor:
        nm = re.match(rf'^new\s+([A-Za-z_$][A-Za-z0-9_$]*)\.{re.escape(model_class)}\s*\(', s)
        if nm:
            a_alias = nm.group(1)
            if a_alias not in a_alias_set or (a_alias != 'A' and a_alias_defs.get(a_alias, 10**9) >= stmt_abs_pos):
                return False
            args, close_idx = base_graph._extract_paren_args(s, nm.end() - 1)
            if args is None or close_idx != len(s) - 1 or not args:
                return False
            return any(
                _is_value_preserving_ctor_arg(
                    arg,
                    source_vars=source_vars,
                    a_alias_set=a_alias_set,
                    a_alias_defs=a_alias_defs,
                    type_alias_set=type_alias_set,
                    type_alias_defs=type_alias_defs,
                    body_exe=body_exe,
                    stmt_abs_pos=stmt_abs_pos,
                )
                for arg in args
            )
        return False

    return False


def _verify_repo_rpc_model_method(
    js_text: str,
    exe_code: str,
    repo_methods: dict[str, list[dict]],
    method_name: str,
    *,
    rpc_name: str,
    model_class: str,
    deserializer_names: tuple[str, ...] = (),
) -> bool:
    """Verify async repository method awaits exact executable RPC literal and returns `model_class` from its result."""
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
    self_aliases = set(base_graph._verified_this_aliases(t_exe))
    a_aliases, a_alias_defs = _verified_a_aliases_with_defs(t_exe)
    a_alias_set = set(a_aliases)
    type_alias_set, type_alias_defs = _verified_type_aliases_with_defs(t_exe)

    valid_desers: set[str] = set()
    for dname in deserializer_names:
        fn_body = _extract_top_level_a_function(js_text, exe_code, dname)
        if fn_body is not None and _verify_deserializer_body(fn_body, model_class):
            valid_desers.add(dname)

    wrap_matches = list(re.finditer(
        r'A\._wrapJsFunctionForAsync\s*\(\s*function\s*\(\s*([A-Za-z_$][A-Za-z0-9_$]*)\s*,\s*([A-Za-z_$][A-Za-z0-9_$]*)\s*\)\s*\{',
        t_exe,
    ))
    if len(wrap_matches) != 1:
        return False
    wm = wrap_matches[0]
    res_param = wm.group(2)
    async_open = wm.end() - 1
    async_close = pi_verifier._find_closing_brace(t_exe, async_open, max_bytes=pi_verifier.MAX_CONSTRUCTOR_SNIPPET_BYTES)
    if async_close < 0:
        return False
    async_exe = t_exe[async_open + 1:async_close]
    async_js = t_js[async_open + 1:async_close]

    cb_m = re.search(r'(?:^|[;,\{\n\r]|\b(?:var|let|const)\s)\s*([A-Za-z_$][A-Za-z0-9_$]*)\s*=\s*$', t_exe[:wm.start()])
    if not cb_m:
        return False
    cb_var = cb_m.group(1)

    start_m = re.search(
        rf'(?<![.\w$])return\s+A\._asyncStartSync\s*\(\s*{re.escape(cb_var)}\s*,\s*([A-Za-z_$][A-Za-z0-9_$]*)\s*\)',
        t_exe[async_close + 1:],
    )
    completer_var = start_m.group(1) if start_m else None

    quoted_double = f'"{rpc_name}"'
    quoted_single = f"'{rpc_name}'"
    lit_len = len(quoted_double)

    await_re = re.compile(r'(?<![.\w$])return\s+A\._asyncAwait\s*\(')
    for am in await_re.finditer(async_exe):
        open_idx = am.end() - 1
        await_args, _ = base_graph._extract_paren_args(async_exe, open_idx)
        if not await_args or len(await_args) < 2 or await_args[-1].strip() != cb_var:
            continue
        arg0_start, arg0_end = _find_top_level_first_arg_span(async_exe, open_idx)
        if arg0_start is None or arg0_end is None:
            continue
        arg0_exe = async_exe[arg0_start:arg0_end]
        arg0_js = async_js[arg0_start:arg0_end]

        awaited_rpc_ok = False
        rpc_call_re = re.compile(
            r'(?<![.\w$])([A-Za-z_$][A-Za-z0-9_$]*)(?:\.[A-Za-z_$][A-Za-z0-9_$]*)?\.rpc(?:\$[A-Za-z0-9_$]+)?\s*\('
        )
        for rm in rpc_call_re.finditer(arg0_exe):
            if rm.group(1) not in self_aliases:
                continue
            idx = rm.end()
            while idx < len(arg0_js) and arg0_js[idx].isspace():
                idx += 1
            lit = arg0_js[idx:idx + lit_len]
            if lit in (quoted_double, quoted_single) and arg0_exe[idx:idx + lit_len] == (' ' * lit_len):
                after_lit = arg0_exe[idx + lit_len:].lstrip()
                if after_lit.startswith(',') or after_lit.startswith(')'):
                    awaited_rpc_ok = True
                    break
        if not awaited_rpc_ok:
            continue

        before_await = async_exe[:am.start()]
        last_case_pos = max(before_await.rfind('case '), before_await.rfind('default:'))
        local_pre = before_await[last_case_pos if last_case_pos >= 0 else 0:]
        goto_matches = list(re.finditer(r'\$async\$goto\s*=\s*(\d+)\s*;', local_pre))
        if not goto_matches:
            continue
        resume_case = goto_matches[-1].group(1)
        case_slice = _extract_case_slice(async_exe, resume_case)
        if case_slice is None:
            continue

        result_write = re.compile(
            rf'(?<![.\w$]){re.escape(res_param)}\s*(?:=(?!=)|[+*/%&|^\-]=|\+\+|--)'
            rf'|(?:\+\+|--)\s*{re.escape(res_param)}(?![\w$])'
        )
        if result_write.search(case_slice):
            continue

        res_vars: set[str] = {res_param}
        model_vars: set[str] = set()
        pending_goto: str | None = None
        case_base_in_t_exe = (async_open + 1) + async_exe.index(case_slice)

        for kind, text, item_rel_start, _ in _split_top_level_items(case_slice):
            if kind == 'block':
                res_pat = '|'.join(re.escape(v) for v in sorted(res_vars))
                is_null_guard = bool(
                    re.match(rf'^\s*if\s*\(\s*(?:{res_pat})\s*===?\s*null\s*\)\s*\{{', text)
                    and re.search(r'(?<![.\w$])break\s*;', text)
                )
                if not is_null_guard:
                    for mv in list(model_vars):
                        if re.search(rf'(?<![.\w$]){re.escape(mv)}\s*(?:=(?!=)|[+*/%&|^\-]=|\+\+|--)', text):
                            model_vars.discard(mv)
                    for rv in list(res_vars):
                        if rv != res_param and re.search(rf'(?<![.\w$]){re.escape(rv)}\s*(?:=(?!=)|[+*/%&|^\-]=|\+\+|--)', text):
                            res_vars.discard(rv)
                continue

            inner_stmt, was_cond = _strip_leading_if_else(text)
            stmt_abs_in_t_exe = case_base_in_t_exe + item_rel_start

            ret_async_m = re.match(r'^return\s+A\._asyncReturn\s*\(', inner_stmt)
            if ret_async_m and not was_cond:
                rargs, rclose = base_graph._extract_paren_args(inner_stmt, ret_async_m.end() - 1)
                if rargs and len(rargs) == 2 and rclose >= 0 and inner_stmt[rclose + 1:].strip() == '':
                    ret_expr, ret_comp = rargs[0].strip(), rargs[1].strip()
                    ret_ident = _strip_outer_parens_no_comma(ret_expr)
                    if (completer_var is None or ret_comp == completer_var) and (
                        (ret_ident and _IDENT_ONLY_RE.fullmatch(ret_ident) and ret_ident in model_vars)
                        or _rhs_produces_model_from_vars(
                            ret_expr,
                            source_vars=res_vars,
                            valid_desers=valid_desers,
                            a_alias_set=a_alias_set,
                            a_alias_defs=a_alias_defs,
                            stmt_abs_pos=stmt_abs_in_t_exe,
                            model_class=model_class,
                            allow_model_ctor=True,
                            type_alias_set=type_alias_set,
                            type_alias_defs=type_alias_defs,
                            body_exe=t_exe,
                        )
                    ):
                        return True
                return False

            for decl in _iter_top_level_decls(inner_stmt):
                targets, rhs = _peel_assignments(decl)
                _invalidate_untracked_writes_in_decl(
                    decl, rhs=rhs, targets=targets, tracked_vars=res_vars, protected_var=res_param,
                )
                _invalidate_untracked_writes_in_decl(
                    decl, rhs=rhs, targets=targets, tracked_vars=model_vars,
                )
                if not targets:
                    continue
                if '$async$goto' in targets and re.fullmatch(r'\d+', rhs):
                    if not was_cond:
                        pending_goto = rhs
                    continue

                rhs_ident = _strip_outer_parens_no_comma(rhs)
                rhs_is_model = (
                    (not was_cond)
                    and (
                        bool(rhs_ident and _IDENT_ONLY_RE.fullmatch(rhs_ident) and rhs_ident in model_vars)
                        or _rhs_produces_model_from_vars(
                            rhs,
                            source_vars=res_vars,
                            valid_desers=valid_desers,
                            a_alias_set=a_alias_set,
                            a_alias_defs=a_alias_defs,
                            stmt_abs_pos=stmt_abs_in_t_exe,
                            model_class=model_class,
                            allow_model_ctor=True,
                            type_alias_set=type_alias_set,
                            type_alias_defs=type_alias_defs,
                            body_exe=t_exe,
                        )
                    )
                )
                rhs_uses_res = (not rhs_is_model) and (not was_cond) and _is_value_preserving_rpc_expr(
                    rhs,
                    source_vars=res_vars,
                    a_alias_set=a_alias_set,
                    a_alias_defs=a_alias_defs,
                    type_alias_set=type_alias_set,
                    type_alias_defs=type_alias_defs,
                    body_exe=t_exe,
                    stmt_abs_pos=stmt_abs_in_t_exe,
                )
                for tgt in targets:
                    if '.' in tgt:
                        continue
                    if rhs_is_model:
                        model_vars.add(tgt)
                        res_vars.discard(tgt)
                    elif rhs_uses_res:
                        res_vars.add(tgt)
                        model_vars.discard(tgt)
                    else:
                        model_vars.discard(tgt)
                        if tgt != res_param:
                            res_vars.discard(tgt)

        if pending_goto is None or not model_vars:
            continue
        ret_slice = _extract_case_slice(async_exe, pending_goto)
        if ret_slice is None:
            continue

        comp_pat = re.escape(completer_var) if completer_var else r'[A-Za-z_$][A-Za-z0-9_$]*'
        for rv in sorted(model_vars):
            ret_match = re.search(
                rf'(?<![.\w$])return\s+A\._asyncReturn\s*\(\s*{re.escape(rv)}\s*,\s*{comp_pat}\s*\)',
                ret_slice,
            )
            if not ret_match:
                continue
            write_before_ret = re.search(
                rf'(?<![.\w$]){re.escape(rv)}\s*(?:=(?!=)|[+*/%&|^\-]=|\+\+|--)',
                ret_slice[:ret_match.start()],
            )
            if not write_before_ret:
                return True
    return False


def _extract_case_slice(async_body: str, case_label: str) -> str | None:
    """Extract a switch case slice up to its depth-0 break or next case/default without stopping inside inner blocks."""
    case_matches = list(re.finditer(rf'(?<![.\w$])case\s+{re.escape(case_label)}\s*:', async_body))
    if len(case_matches) != 1:
        return None
    case_start = case_matches[0].end()
    n = len(async_body)
    depth = 0
    i = case_start
    end_re = re.compile(r'(?<![.\w$])(?:break\s*;|case\s+\d+\s*:|default\s*:)')
    while i < n:
        ch = async_body[i]
        if ch == '{':
            depth += 1
        elif ch == '}':
            if depth == 0:
                return async_body[case_start:i]
            depth -= 1
        elif depth == 0 and ch in ('b', 'c', 'd'):
            if end_re.match(async_body, i):
                return async_body[case_start:i]
        i += 1
    return async_body[case_start:]


def _derive_async_repo_candidates_ext(
    body_exe: str,
    *,
    repository_field: str,
    js_text: str,
    exe_code: str,
    repo_methods: dict[str, list[dict]],
    rpc_name: str,
    model_class: str,
    deserializer_names: tuple[str, ...] = (),
    allow_model_ctor_from_res: bool = False,
) -> set[str]:
    """Derive provider fields written from an awaited verified repository RPC returning `model_class`."""
    candidates: set[str] = set()
    aliases = base_graph._verified_this_aliases(body_exe)
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
        r'(?<![.\w$])return\s+A\._asyncAwait\s*\(\s*'
        rf'([A-Za-z_$][A-Za-z0-9_$]*)\.{re.escape(repository_field)}\.([A-Za-z_$][A-Za-z0-9_$]*)\s*\('
    )
    for am in await_re.finditer(async_body):
        recv, repo_method = am.group(1), am.group(2)
        if recv not in alias_set:
            continue
        if not _verify_repo_rpc_model_method(
            js_text,
            exe_code,
            repo_methods,
            repo_method,
            rpc_name=rpc_name,
            model_class=model_class,
            deserializer_names=deserializer_names,
        ):
            continue

        outer_open = async_body.find('(', async_body.find('_asyncAwait', am.start()))
        await_args, _ = base_graph._extract_paren_args(async_body, outer_open)
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
        case_slice = _extract_case_slice(async_body, resume_case)
        if case_slice is None:
            continue

        result_write = re.compile(
            rf'(?<![.\w$]){re.escape(res_param)}\s*(?:=(?!=)|[+*/%&|^\-]=|\+\+|--)'
            rf'|(?:\+\+|--)\s*{re.escape(res_param)}(?![\w$])'
        )
        if result_write.search(case_slice):
            continue

        # Track resume slice + 1-hop dart2js guard/continuation slices sequentially for writes & post-write overwrites
        candidate_slices = [case_slice]
        hop_targets: list[str] = []
        for next_goto in re.finditer(
            r'\$async\$goto\s*=\s*[^;]*?\?\s*(\d+)\s*:\s*(\d+)\s*;|'
            r'\$async\$goto\s*=\s*(\d+)\s*;',
            case_slice,
        ):
            for g in next_goto.groups():
                if g and g not in hop_targets:
                    hop_targets.append(g)

        for g in hop_targets:
            hop_slice = _extract_case_slice(async_body, g)
            if hop_slice is not None and hop_slice not in candidate_slices and not result_write.search(hop_slice):
                candidate_slices.append(hop_slice)

        a_aliases, a_alias_defs = _verified_a_aliases_with_defs(body_exe)
        a_alias_set = set(a_aliases)
        type_alias_set, type_alias_defs = _verified_type_aliases_with_defs(body_exe)

        model_or_res_vars: set[str] = {res_param}
        derived_list_vars: set[str] = set()
        active_fields: set[str] = set()
        field_lhs_re = re.compile(rf'^(?:{alias_pat})\.([A-Za-z_$][A-Za-z0-9_$]*)$')
        esc_cls = re.escape(model_class)

        def _is_history_list_expr(expr_text: str, pos_in_body: int, depth: int = 0) -> bool:
            if not allow_model_ctor_from_res or depth > 6:
                return False
            s = _strip_outer_parens_no_comma(expr_text)
            if not s:
                return False
            if _IDENT_ONLY_RE.fullmatch(s):
                return s in derived_list_vars
            pm = re.fullmatch(r'([A-Za-z_$][A-Za-z0-9_$]*)\.[A-Za-z_$][A-Za-z0-9_$]*', s)
            if pm:
                return pm.group(1) in model_or_res_vars
            cm = re.match(
                r'^([A-Za-z_$][A-Za-z0-9_$]*(?:\.[A-Za-z_$][A-Za-z0-9_$]*)?)\.([A-Za-z_$][A-Za-z0-9_$]*)\s*\(',
                s,
            )
            if not cm:
                return False
            recv, method = cm.group(1), cm.group(2)
            args, close_idx = base_graph._extract_paren_args(s, cm.end() - 1)
            if args is None or close_idx != len(s) - 1 or not args:
                return False
            if method == '_as' and len(args) == 1 and _is_valid_type_cast_receiver(
                recv,
                body_exe=body_exe,
                type_alias_set=type_alias_set,
                type_alias_defs=type_alias_defs,
                stmt_abs_pos=pos_in_body,
            ):
                return _is_history_list_expr(args[0], pos_in_body, depth + 1)
            if (
                method == 'List_List$_of'
                and 1 <= len(args) <= 2
                and '.' not in recv
                and recv in a_alias_set
                and (recv == 'A' or a_alias_defs.get(recv, 10**9) < pos_in_body)
            ):
                return _is_history_list_expr(args[0], pos_in_body, depth + 1)
            if method == '_uniqueSessions$1' and len(args) == 1 and '.' not in recv and recv in alias_set:
                return _is_history_list_expr(args[0], pos_in_body, depth + 1)
            return False

        def _is_provider_model_expr(expr_text: str, pos_in_body: int, depth: int = 0) -> bool:
            if depth > 6:
                return False
            s = _strip_outer_parens_no_comma(expr_text)
            if not s:
                return False
            if _IDENT_ONLY_RE.fullmatch(s):
                return s in model_or_res_vars
            cm = re.match(
                r'^([A-Za-z_$][A-Za-z0-9_$]*(?:\.[A-Za-z_$][A-Za-z0-9_$]*)?)\.([A-Za-z_$][A-Za-z0-9_$]*)\s*\(',
                s,
            )
            if cm:
                recv, method = cm.group(1), cm.group(2)
                args, close_idx = base_graph._extract_paren_args(s, cm.end() - 1)
                if (
                    args is not None
                    and close_idx == len(s) - 1
                    and len(args) == 1
                    and method == '_as'
                    and _is_valid_type_cast_receiver(
                        recv,
                        body_exe=body_exe,
                        type_alias_set=type_alias_set,
                        type_alias_defs=type_alias_defs,
                        stmt_abs_pos=pos_in_body,
                    )
                ):
                    return _is_provider_model_expr(args[0], pos_in_body, depth + 1)
                return False
            if allow_model_ctor_from_res:
                nm = re.match(rf'^new\s+([A-Za-z_$][A-Za-z0-9_$]*)\.{esc_cls}\s*\(', s)
                if nm:
                    a_alias = nm.group(1)
                    if a_alias not in a_alias_set or (a_alias != 'A' and a_alias_defs.get(a_alias, 10**9) >= pos_in_body):
                        return False
                    args, close_idx = base_graph._extract_paren_args(s, nm.end() - 1)
                    if args is None or close_idx != len(s) - 1 or not args:
                        return False
                    return _is_history_list_expr(args[0], pos_in_body, depth + 1)
            return False

        for sl in candidate_slices:
            sl_base = (async_open + 1) + async_body.index(sl)
            for kind, text, item_rel_start, _ in _split_top_level_items(sl):
                if kind == 'block':
                    for mv in list(model_or_res_vars):
                        if mv != res_param and re.search(rf'(?<![.\w$]){re.escape(mv)}\s*(?:=(?!=)|[+*/%&|^\-]=|\+\+|--)', text):
                            model_or_res_vars.discard(mv)
                    for lv in list(derived_list_vars):
                        if re.search(rf'(?<![.\w$]){re.escape(lv)}\s*(?:=(?!=)|[+*/%&|^\-]=|\+\+|--)', text):
                            derived_list_vars.discard(lv)
                    for af in list(active_fields):
                        if re.search(rf'(?<![.\w$])(?:{alias_pat})\.{re.escape(af)}\s*(?:=(?!=)|[+*/%&|^\-]=)', text):
                            active_fields.discard(af)
                    continue

                if _has_trivially_falsy_if_guard(text):
                    continue
                inner_stmt, _ = _strip_leading_if_else(text)
                stmt_abs_in_body = sl_base + item_rel_start
                for decl in _iter_top_level_decls(inner_stmt):
                    targets, rhs = _peel_assignments(decl)
                    _invalidate_untracked_writes_in_decl(
                        decl, rhs=rhs, targets=targets, tracked_vars=model_or_res_vars, protected_var=res_param,
                        tracked_fields=active_fields, alias_pat=alias_pat,
                    )
                    _invalidate_untracked_writes_in_decl(
                        decl, rhs=rhs, targets=targets, tracked_vars=derived_list_vars,
                    )
                    if not targets:
                        continue
                    is_model_rhs = _is_provider_model_expr(rhs, stmt_abs_in_body)
                    is_hist_list_rhs = (not is_model_rhs) and _is_history_list_expr(rhs, stmt_abs_in_body)

                    for tgt in targets:
                        fm = field_lhs_re.match(tgt)
                        if fm:
                            fname = fm.group(1)
                            if is_model_rhs:
                                active_fields.add(fname)
                            else:
                                active_fields.discard(fname)
                        elif '.' not in tgt and tgt != res_param:
                            if is_model_rhs:
                                model_or_res_vars.add(tgt)
                                derived_list_vars.discard(tgt)
                            elif is_hist_list_rhs:
                                derived_list_vars.add(tgt)
                                model_or_res_vars.discard(tgt)
                            else:
                                model_or_res_vars.discard(tgt)
                                derived_list_vars.discard(tgt)

        candidates.update(active_fields)
    return candidates


def _derive_direct_model_candidates(body_exe: str, model_class: str) -> set[str]:
    """Derive provider field candidates assigned `new A.<model_class>(...)` inside `body_exe` (repo-absent fallback only)."""
    candidates: set[str] = set()
    aliases = base_graph._verified_this_aliases(body_exe)
    alias_pat = '|'.join(re.escape(a) for a in aliases)
    esc_cls = re.escape(model_class)
    for m in re.finditer(rf'(?<![.\w$])(?:{alias_pat})\.([A-Za-z_$][A-Za-z0-9_$]*)\s*=\s*new\s+A\.{esc_cls}\s*\(', body_exe):
        fname = m.group(1)
        close_idx = _extract_balanced_call_end(body_exe, m.end() - 1)
        if close_idx >= 0 and not re.search(rf'(?<![.\w$])(?:{alias_pat})\.{re.escape(fname)}\s*=\s*null\b', body_exe[close_idx + 1:]):
            candidates.add(fname)
    for m in re.finditer(
        rf'(?:^|[;,\{{\n\r]|\b(?:var|let|const)\s)\s*([A-Za-z_$][A-Za-z0-9_$]*)\s*=\s*new\s+A\.{esc_cls}\s*\(',
        body_exe,
    ):
        vname = m.group(1)
        rest = body_exe[m.end():]
        assign_m = re.search(
            rf'(?<![.\w$])(?:{alias_pat})\.([A-Za-z_$][A-Za-z0-9_$]*)\s*=\s*{re.escape(vname)}\b(?![A-Za-z0-9_$.])',
            rest,
        )
        if assign_m and not re.search(rf'(?<![.\w$]){re.escape(vname)}\s*=(?!=)', rest[:assign_m.start()]):
            fname = assign_m.group(1)
            if not re.search(rf'(?<![.\w$])(?:{alias_pat})\.{re.escape(fname)}\s*=\s*null\b', rest[assign_m.end():]):
                candidates.add(fname)
    return candidates


def _derive_id_field_candidates(method_entry: dict, *, id_param_index: int = 0) -> set[str]:
    """Derive field assigned directly from the first detail-ID parameter of a fetch method (without overwrite)."""
    params = method_entry.get('params') or []
    if len(params) <= id_param_index:
        return set()
    id_param = params[id_param_index]
    body_exe = method_entry.get('body') or ''
    if re.search(rf'(?<![.\w$]){re.escape(id_param)}\s*=(?!=)', body_exe):
        return set()
    aliases = base_graph._verified_this_aliases(body_exe)
    alias_pat = '|'.join(re.escape(a) for a in aliases)
    candidates: set[str] = set()
    for m in re.finditer(
        rf'(?<![.\w$])(?:{alias_pat})\.([A-Za-z_$][A-Za-z0-9_$]*)\s*=(?!=)',
        body_exe,
    ):
        fname = m.group(1)
        pos = m.end()
        paren = bracket = brace = 0
        n = len(body_exe)
        while pos < n:
            ch = body_exe[pos]
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
                if brace == 0:
                    break
                brace -= 1
            elif ch in (';', ',') and paren == 0 and bracket == 0 and brace == 0:
                break
            pos += 1
        rhs_clean = _strip_outer_parens_no_comma(body_exe[m.end():pos])
        if rhs_clean != id_param:
            continue
        if not re.search(rf'(?<![.\w$])(?:{alias_pat})\.{re.escape(fname)}\s*(?:=(?!=)|[+*/%&|^\-]=)', body_exe[pos:]):
            candidates.add(fname)
    return candidates


def _verify_field_reset_and_optional_getters(
    methods: dict[str, list[dict]],
    *,
    field_name: str,
    reg_method: str,
    getter_names: tuple[str, ...],
    skip_method_prefixes: tuple[str, ...],
) -> bool:
    """Require null reset reachable from `_onAuthChanged` (or direct helper) and verify getters if present."""
    for gname in getter_names:
        gentries = methods.get(gname)
        if gentries is not None:
            if len(gentries) != 1:
                return False
            gbody = gentries[0]['body']
            g_aliases = base_graph._verified_this_aliases(gbody)
            g_pat = '|'.join(re.escape(a) for a in g_aliases)
            if not re.search(rf'\breturn\s+(?:{g_pat})\.{re.escape(field_name)}\b(?![A-Za-z0-9_$])', gbody):
                return False

    reg_entries = methods.get(reg_method)
    if reg_entries is None or len(reg_entries) != 1:
        return False
    reg_body = reg_entries[0]['body']
    if base_graph._has_aliased_null_reset(reg_body, field_name):
        return True

    reg_aliases = base_graph._verified_this_aliases(reg_body)
    reg_pat = '|'.join(re.escape(a) for a in reg_aliases)
    for cm in re.finditer(rf'(?<![.\w$])(?:{reg_pat})\.([A-Za-z_$][A-Za-z0-9_$]*)\s*\(\s*\)', reg_body):
        helper = cm.group(1)
        if any(helper.startswith(p) for p in skip_method_prefixes):
            continue
        hentries = methods.get(helper)
        if hentries and len(hentries) == 1 and base_graph._has_aliased_null_reset(hentries[0]['body'], field_name):
            return True
    return False


def _extract_provider_tearoff_registration(js_text: str, exe_code: str, provider_class: str) -> tuple[str | None, str | None, str | None]:
    """Extract sole `_instance_0_u(_ = A.<provider_class>.prototype, getter, method, 0)` registration."""
    prov_esc = re.escape(provider_class)
    exe_inst_stubs = list(re.finditer(rf'_instance_0_u\s*\(\s*_\s*=\s*A\.{prov_esc}\.prototype\b', exe_code))
    if len(exe_inst_stubs) != 1:
        return None, None, f'{provider_class}_tearoff_registration_missing_or_ambiguous'
    stub_start = exe_inst_stubs[0].start()
    inst_pat = re.compile(
        rf'_instance_0_u\s*\(\s*_\s*=\s*A\.{prov_esc}\.prototype\s*,\s*'
        r'"([A-Za-z_$][A-Za-z0-9_$]*)"\s*,\s*"([A-Za-z_$][A-Za-z0-9_$]*)"\s*,\s*0\s*\)'
    )
    inst_match = inst_pat.match(js_text[stub_start:stub_start + 300])
    if not inst_match:
        return None, None, f'{provider_class}_tearoff_registration_parse_failed'
    return inst_match.group(1), inst_match.group(2), None


def _extract_repo_methods(exe_code: str, repo_class: str) -> dict[str, list[dict]]:
    repo_start, repo_end, repo_err = base_graph._extract_prototype_span(exe_code, repo_class)
    if not repo_err and repo_start is not None and repo_end is not None:
        parsed, merr = base_graph._extract_prototype_methods(exe_code[repo_start:repo_end], repo_start)
        if not merr:
            return parsed
    return {}


def extract_listener_source_binding(build_dir: Path | str, expected_main_js_sha: str | None = None) -> dict:
    """Derive fail-closed AuthProvider -> SessionProvider/ClubProvider bindings from main.dart.js."""
    bdir = Path(build_dir)
    main_js = bdir / 'main.dart.js'
    if not main_js.exists() or pi_verifier._is_link(main_js) or not main_js.is_file():
        return {'ok': False, 'error': 'main_dart_js_missing_or_symlink'}

    try:
        raw = base_graph._read_bounded_bytes(main_js)
    except ValueError:
        return {'ok': False, 'error': 'main_dart_js_exceeds_max_bytes'}
    actual_sha = base_graph._sha256_bytes(raw)
    if expected_main_js_sha is not None:
        if (
            not isinstance(expected_main_js_sha, str)
            or not pi_verifier.HEX64.fullmatch(expected_main_js_sha)
            or actual_sha != expected_main_js_sha
        ):
            return {
                'ok': False,
                'error': 'main_dart_js_sha_mismatch',
                'main_dart_js_sha256': actual_sha,
                'expected_main_dart_js_sha256': expected_main_js_sha,
            }

    js_text = raw.decode('utf-8', errors='replace')
    exe_code, strings = pi_verifier._executable_source(js_text)

    # 1. AuthProvider constructor & ChangeNotifier counters + _currentUser
    auth_ctor = pi_verifier.extract_js_constructor(js_text, 'AuthProvider', code=exe_code)
    if not auth_ctor.get('ok'):
        return {'ok': False, 'error': f"auth_ctor:{auth_ctor.get('error')}", 'main_dart_js_sha256': actual_sha}
    auth_props = base_graph._assignment_targets(auth_ctor)
    required_auth = ('ChangeNotifier__listeners', *COUNTER_FIELDS, '_currentUser')
    missing_auth = [f for f in required_auth if f not in auth_props]
    if missing_auth:
        return {'ok': False, 'error': f'auth_ctor_missing_fields:{",".join(missing_auth)}', 'main_dart_js_sha256': actual_sha}

    # 2. BoundClosure & Closure_fromTearOff generated prototype contract
    bc_ctor = pi_verifier.extract_js_constructor(js_text, 'BoundClosure', code=exe_code)
    if not bc_ctor.get('ok'):
        return {'ok': False, 'error': f"bound_closure_ctor:{bc_ctor.get('error')}", 'main_dart_js_sha256': actual_sha}
    bc_props = base_graph._assignment_targets(bc_ctor)
    if '_receiver' not in bc_props or '_interceptor' not in bc_props:
        return {'ok': False, 'error': 'bound_closure_missing_receiver_or_interceptor', 'main_dart_js_sha256': actual_sha}

    tearoff_fn = base_graph._extract_closure_from_tearoff_body(js_text, exe_code)
    if not tearoff_fn.get('ok'):
        return {'ok': False, 'error': tearoff_fn.get('error'), 'main_dart_js_sha256': actual_sha}
    tearoff_exe = tearoff_fn['exe']
    if not (
        re.search(r'\bBoundClosure\b', tearoff_exe)
        and re.search(r'\$\_name\b', tearoff_exe)
        and re.search(r'Object\.create\b', tearoff_exe)
    ):
        return {'ok': False, 'error': 'closure_from_tearoff_missing_prototype_binding', 'main_dart_js_sha256': actual_sha}

    # 3. Model constructors from executable deserializers / constructors
    session_cls, session_ctor = _resolve_model_class_from_deserializer(
        js_text,
        exe_code,
        deserializer_name='Session_Session$fromJson',
        fallback_candidates=('Session0', 'Session'),
    )
    if not session_cls or not session_ctor:
        return {'ok': False, 'error': 'session_model_ctor_missing', 'main_dart_js_sha256': actual_sha}

    history_cls, history_ctor = _resolve_model_class_from_deserializer(
        js_text,
        exe_code,
        deserializer_name='SessionHistoryPage_SessionHistoryPage$fromResponse',
        fallback_candidates=('SessionHistoryPage',),
    )
    if not history_cls or not history_ctor:
        return {'ok': False, 'error': 'session_history_page_ctor_missing', 'main_dart_js_sha256': actual_sha}

    club_cls, club_ctor = _resolve_model_class_from_deserializer(
        js_text,
        exe_code,
        deserializer_name='Club_Club$fromJson',
        fallback_candidates=('Club', 'Club0'),
    )
    if not club_cls or not club_ctor:
        return {'ok': False, 'error': 'club_model_ctor_missing', 'main_dart_js_sha256': actual_sha}

    bank_cls, bank_ctor = _resolve_model_class_from_deserializer(
        js_text,
        exe_code,
        deserializer_name='BankAccount_BankAccount$fromJson',
        fallback_candidates=('BankAccount', 'BankAccount0'),
    )
    if not bank_cls or not bank_ctor:
        return {'ok': False, 'error': 'bank_account_model_ctor_missing', 'main_dart_js_sha256': actual_sha}

    # 4. SessionProvider constructor, prototype, tearoff, fields, reset, factory wiring
    sp_ctor = pi_verifier.extract_js_constructor(js_text, 'SessionProvider', code=exe_code)
    if not sp_ctor.get('ok'):
        return {'ok': False, 'error': f"session_ctor:{sp_ctor.get('error')}", 'main_dart_js_sha256': actual_sha}
    sp_assignments = (pi_verifier._parse_constructor_assignments(sp_ctor.get('body') or '')).get('assignments') or []
    sp_props = {item['prop'] for item in sp_assignments}
    sp_null_props = {item['prop'] for item in sp_assignments if item['rhs'] == 'null'}
    sp_repo_fields = [
        f for f in sorted({item['prop'] for item in sp_assignments if re.fullmatch(r'(?:_[A-Za-z0-9_]+\$)?_repository', item['prop'])})
    ]
    if 'auth' not in sp_props or len(sp_repo_fields) != 1:
        return {'ok': False, 'error': 'session_ctor_missing_auth_or_repo', 'main_dart_js_sha256': actual_sha}
    sp_repo_field = sp_repo_fields[0]

    sp_start, sp_end, sp_proto_err = base_graph._extract_prototype_span(exe_code, 'SessionProvider')
    if sp_proto_err or sp_start is None or sp_end is None:
        return {'ok': False, 'error': sp_proto_err or 'SessionProvider_prototype_missing', 'main_dart_js_sha256': actual_sha}
    sp_methods, sp_merr = base_graph._extract_prototype_methods(exe_code[sp_start:sp_end], sp_start)
    if sp_merr:
        return {'ok': False, 'error': sp_merr, 'main_dart_js_sha256': actual_sha}

    sp_reg_getter, sp_reg_method, sp_reg_err = _extract_provider_tearoff_registration(js_text, exe_code, 'SessionProvider')
    if sp_reg_err or not sp_reg_getter or not sp_reg_method:
        return {'ok': False, 'error': sp_reg_err, 'main_dart_js_sha256': actual_sha}

    sess_repo_methods = _extract_repo_methods(exe_code, 'SessionRepository')
    sp_async_detail: set[str] = set()
    sp_direct_detail: set[str] = set()
    sp_id_cands: set[str] = set()
    for mname, entries in sp_methods.items():
        if not mname.startswith('fetchSessionDetail'):
            continue
        if len(entries) != 1:
            return {'ok': False, 'error': f'session_detail_fetch_ambiguous:{mname}', 'main_dart_js_sha256': actual_sha}
        entry = entries[0]
        if sess_repo_methods:
            cands = _derive_async_repo_candidates_ext(
                entry['body'],
                repository_field=sp_repo_field,
                js_text=js_text,
                exe_code=exe_code,
                repo_methods=sess_repo_methods,
                rpc_name='get_session_public_detail',
                model_class=session_cls,
                deserializer_names=('Session_Session$fromJson',),
            )
            if cands:
                sp_async_detail.update(cands)
                sp_id_cands.update(_derive_id_field_candidates(entry))
        else:
            direct = _derive_direct_model_candidates(entry['body'], session_cls)
            if direct:
                sp_direct_detail.update(direct)
                sp_id_cands.update(_derive_id_field_candidates(entry))

    sp_detail_cands = [
        f for f in sorted(sp_async_detail | sp_direct_detail)
        if f in sp_null_props
        and _verify_field_reset_and_optional_getters(
            sp_methods,
            field_name=f,
            reg_method=sp_reg_method,
            getter_names=('get$currentSession',),
            skip_method_prefixes=('fetchSessionDetail', 'fetchSessionHistory'),
        )
    ]
    if len(sp_detail_cands) != 1:
        return {'ok': False, 'error': f'session_current_session_field_invalid:{sp_detail_cands}', 'main_dart_js_sha256': actual_sha}
    current_session_field = sp_detail_cands[0]

    sp_valid_ids = [
        f for f in sorted(sp_id_cands)
        if f != current_session_field
        and f in sp_null_props
        and _verify_field_reset_and_optional_getters(
            sp_methods,
            field_name=f,
            reg_method=sp_reg_method,
            getter_names=('get$currentSessionId',),
            skip_method_prefixes=('fetchSessionDetail', 'fetchSessionHistory'),
        )
    ]
    if len(sp_valid_ids) != 1:
        return {'ok': False, 'error': f'session_id_field_invalid:{sp_valid_ids}', 'main_dart_js_sha256': actual_sha}
    session_id_field = sp_valid_ids[0]

    sp_async_hist: set[str] = set()
    sp_direct_hist: set[str] = set()
    for mname, entries in sp_methods.items():
        if not mname.startswith('fetchSessionHistory'):
            continue
        if len(entries) != 1:
            return {'ok': False, 'error': f'session_history_fetch_ambiguous:{mname}', 'main_dart_js_sha256': actual_sha}
        entry = entries[0]
        body_exe = entry['body']
        if sess_repo_methods:
            sp_async_hist.update(_derive_async_repo_candidates_ext(
                body_exe,
                repository_field=sp_repo_field,
                js_text=js_text,
                exe_code=exe_code,
                repo_methods=sess_repo_methods,
                rpc_name='list_my_session_history',
                model_class=history_cls,
                deserializer_names=('SessionHistoryPage_SessionHistoryPage$fromResponse',),
                allow_model_ctor_from_res=True,
            ))
        else:
            sp_direct_hist.update(_derive_direct_model_candidates(body_exe, history_cls))

    sp_valid_hist = [
        f for f in sorted(sp_async_hist | sp_direct_hist)
        if f not in (current_session_field, session_id_field)
        and f in sp_null_props
        and _verify_field_reset_and_optional_getters(
            sp_methods,
            field_name=f,
            reg_method=sp_reg_method,
            getter_names=('get$history',),
            skip_method_prefixes=('fetchSessionDetail', 'fetchSessionHistory'),
        )
    ]
    if len(sp_valid_hist) != 1:
        return {'ok': False, 'error': f'session_history_field_invalid:{sp_valid_hist}', 'main_dart_js_sha256': actual_sha}
    history_field = sp_valid_hist[0]

    if 'get_session_public_detail' not in strings or 'list_my_session_history' not in strings:
        return {'ok': False, 'error': 'missing_session_rpc_literals', 'main_dart_js_sha256': actual_sha}

    if not base_graph._verify_factory_listener_wiring(
        exe_code,
        fp_ctor=sp_ctor,
        repository_field=sp_repo_field,
        reg_getter=sp_reg_getter,
        require_repo_ctor=bool(sess_repo_methods),
        provider_class='SessionProvider',
        repo_class='SessionRepository',
    ):
        return {'ok': False, 'error': 'session_addListener_wiring_missing_in_executable_js', 'main_dart_js_sha256': actual_sha}

    # 5. ClubProvider constructor, prototype, tearoff, fields, reset, factory wiring
    cp_ctor = pi_verifier.extract_js_constructor(js_text, 'ClubProvider', code=exe_code)
    if not cp_ctor.get('ok'):
        return {'ok': False, 'error': f"club_ctor:{cp_ctor.get('error')}", 'main_dart_js_sha256': actual_sha}
    cp_assignments = (pi_verifier._parse_constructor_assignments(cp_ctor.get('body') or '')).get('assignments') or []
    cp_props = {item['prop'] for item in cp_assignments}
    cp_null_props = {item['prop'] for item in cp_assignments if item['rhs'] == 'null'}
    cp_repo_fields = [
        f for f in sorted({item['prop'] for item in cp_assignments if re.fullmatch(r'(?:_[A-Za-z0-9_]+\$)?_repository', item['prop'])})
    ]
    if 'auth' not in cp_props or len(cp_repo_fields) != 1:
        return {'ok': False, 'error': 'club_ctor_missing_auth_or_repo', 'main_dart_js_sha256': actual_sha}
    cp_repo_field = cp_repo_fields[0]

    cp_start, cp_end, cp_proto_err = base_graph._extract_prototype_span(exe_code, 'ClubProvider')
    if cp_proto_err or cp_start is None or cp_end is None:
        return {'ok': False, 'error': cp_proto_err or 'ClubProvider_prototype_missing', 'main_dart_js_sha256': actual_sha}
    cp_methods, cp_merr = base_graph._extract_prototype_methods(exe_code[cp_start:cp_end], cp_start)
    if cp_merr:
        return {'ok': False, 'error': cp_merr, 'main_dart_js_sha256': actual_sha}

    cp_reg_getter, cp_reg_method, cp_reg_err = _extract_provider_tearoff_registration(js_text, exe_code, 'ClubProvider')
    if cp_reg_err or not cp_reg_getter or not cp_reg_method:
        return {'ok': False, 'error': cp_reg_err, 'main_dart_js_sha256': actual_sha}

    club_repo_methods = _extract_repo_methods(exe_code, 'ClubRepository')
    cp_async_club: set[str] = set()
    cp_direct_club: set[str] = set()
    cp_id_cands: set[str] = set()
    for mname, entries in cp_methods.items():
        if not mname.startswith('fetchClubDetails'):
            continue
        if len(entries) != 1:
            return {'ok': False, 'error': f'club_details_fetch_ambiguous:{mname}', 'main_dart_js_sha256': actual_sha}
        entry = entries[0]
        if club_repo_methods:
            cands = _derive_async_repo_candidates_ext(
                entry['body'],
                repository_field=cp_repo_field,
                js_text=js_text,
                exe_code=exe_code,
                repo_methods=club_repo_methods,
                rpc_name='get_club_detail',
                model_class=club_cls,
                deserializer_names=('Club_Club$fromJson',),
            )
            if cands:
                cp_async_club.update(cands)
                cp_id_cands.update(_derive_id_field_candidates(entry))
        else:
            direct = _derive_direct_model_candidates(entry['body'], club_cls)
            if direct:
                cp_direct_club.update(direct)
                cp_id_cands.update(_derive_id_field_candidates(entry))

    cp_valid_clubs = [
        f for f in sorted(cp_async_club | cp_direct_club)
        if f in cp_null_props
        and _verify_field_reset_and_optional_getters(
            cp_methods,
            field_name=f,
            reg_method=cp_reg_method,
            getter_names=('get$currentClub',),
            skip_method_prefixes=('fetchClubDetails', 'fetchClubBankAccount'),
        )
    ]
    if len(cp_valid_clubs) != 1:
        return {'ok': False, 'error': f'club_current_club_field_invalid:{cp_valid_clubs}', 'main_dart_js_sha256': actual_sha}
    current_club_field = cp_valid_clubs[0]

    cp_valid_ids = [
        f for f in sorted(cp_id_cands)
        if f != current_club_field
        and f in cp_null_props
        and _verify_field_reset_and_optional_getters(
            cp_methods,
            field_name=f,
            reg_method=cp_reg_method,
            getter_names=('get$currentClubId',),
            skip_method_prefixes=('fetchClubDetails', 'fetchClubBankAccount'),
        )
    ]
    if len(cp_valid_ids) != 1:
        return {'ok': False, 'error': f'club_id_field_invalid:{cp_valid_ids}', 'main_dart_js_sha256': actual_sha}
    club_id_field = cp_valid_ids[0]

    cp_async_bank: set[str] = set()
    cp_direct_bank: set[str] = set()
    for mname, entries in cp_methods.items():
        if not mname.startswith('fetchClubBankAccount'):
            continue
        if len(entries) != 1:
            return {'ok': False, 'error': f'club_bank_fetch_ambiguous:{mname}', 'main_dart_js_sha256': actual_sha}
        entry = entries[0]
        if club_repo_methods:
            cp_async_bank.update(_derive_async_repo_candidates_ext(
                entry['body'],
                repository_field=cp_repo_field,
                js_text=js_text,
                exe_code=exe_code,
                repo_methods=club_repo_methods,
                rpc_name='get_club_bank_account',
                model_class=bank_cls,
                deserializer_names=('BankAccount_BankAccount$fromJson',),
            ))
        else:
            cp_direct_bank.update(_derive_direct_model_candidates(entry['body'], bank_cls))

    cp_valid_banks = [
        f for f in sorted(cp_async_bank | cp_direct_bank)
        if f not in (current_club_field, club_id_field)
        and f in cp_null_props
        and _verify_field_reset_and_optional_getters(
            cp_methods,
            field_name=f,
            reg_method=cp_reg_method,
            getter_names=('get$currentBankAccount',),
            skip_method_prefixes=('fetchClubDetails', 'fetchClubBankAccount'),
        )
    ]
    if len(cp_valid_banks) != 1:
        return {'ok': False, 'error': f'club_bank_account_field_invalid:{cp_valid_banks}', 'main_dart_js_sha256': actual_sha}
    bank_account_field = cp_valid_banks[0]

    if 'get_club_detail' not in strings or 'get_club_bank_account' not in strings:
        return {'ok': False, 'error': 'missing_club_rpc_literals', 'main_dart_js_sha256': actual_sha}

    if not base_graph._verify_factory_listener_wiring(
        exe_code,
        fp_ctor=cp_ctor,
        repository_field=cp_repo_field,
        reg_getter=cp_reg_getter,
        require_repo_ctor=bool(club_repo_methods),
        provider_class='ClubProvider',
        repo_class='ClubRepository',
    ):
        return {'ok': False, 'error': 'club_addListener_wiring_missing_in_executable_js', 'main_dart_js_sha256': actual_sha}

    binding = {
        'ok': True,
        'claim_scope': CLAIM_SCOPE,
        'main_dart_js_sha256': actual_sha,
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
        'models': {
            'session': {'constructor_name': session_cls},
            'session_history_page': {'constructor_name': history_cls},
            'club': {'constructor_name': club_cls},
            'bank_account': {'constructor_name': bank_cls},
        },
        'session_provider': {
            'constructor_name': 'SessionProvider',
            'auth_field': 'auth',
            'repository_field': sp_repo_field,
            'session_id_field': session_id_field,
            'current_session_field': current_session_field,
            'history_field': history_field,
            'registration_getter': sp_reg_getter,
            'registration_method': sp_reg_method,
        },
        'club_provider': {
            'constructor_name': 'ClubProvider',
            'auth_field': 'auth',
            'repository_field': cp_repo_field,
            'club_id_field': club_id_field,
            'current_club_field': current_club_field,
            'bank_account_field': bank_account_field,
            'registration_getter': cp_reg_getter,
            'registration_method': cp_reg_method,
        },
    }
    binding['listener_binding_sha256'] = base_graph._canonical_sha256(binding)
    return binding


# --- V8 snapshot scanning & slot classification ----------------------------------------

def _is_valid_heap_object_id(val: object) -> bool:
    """Return True iff `val` is a non-empty decimal V8 heap object ID string."""
    return isinstance(val, str) and bool(re.fullmatch(r'[1-9][0-9]*', val))


def _inspect_field_with_object_id(
    idx_data: dict,
    node: int,
    field_name: str,
    *,
    allowed_classes: frozenset[str],
) -> dict:
    meta = base_graph._inspect_selected_field(idx_data, node, field_name, allowed_classes=allowed_classes)
    target_id = None
    if meta.get('present') and not meta.get('is_null') and meta.get('node_type') == 'object' and meta.get('class_recognized'):
        props = base_graph._property_edges(idx_data, node)
        target = props.get(field_name)
        if target is not None:
            raw_id = base_graph._node_id(idx_data, target)
            if type(raw_id) is int and raw_id > 0:
                target_id = str(raw_id)
    meta['target_heap_object_id'] = target_id
    return meta


def _inspect_session_club_tearoff(
    idx_data: dict,
    slot_node: int,
    *,
    binding: dict,
    rooted_session_set: set[int],
    all_session_set: set[int],
    rooted_club_set: set[int],
    all_club_set: set[int],
) -> dict:
    allowed_cls = _allowed_classes(binding)
    allowed_methods = _allowed_methods(binding)
    sp = binding['session_provider']
    cp = binding['club_provider']

    core = base_graph._inspect_tearoff_core(
        idx_data,
        slot_node,
        receiver_field=binding['bound_closure']['receiver_field'],
        name_prop=binding['bound_closure']['tearoff_name_property'],
        allowed_classes=allowed_cls,
        disallowed_proto_classes=DISALLOWED_PROTO_CLASSES,
    )
    if core.get('is_null_or_hole'):
        return core

    recv_node = core['recv_node']
    recv_id = core['receiver_heap_object_id']
    recv_class = core['receiver_class']
    recv_recognized = core['receiver_class_recognized']
    raw_method_name = core['raw_method_name']
    method_on_gen_proto = core['method_on_generated_prototype']
    bound_closure_on_chain = core['bound_closure_on_proto_chain']
    proto_is_provider = core['proto_is_provider']
    safe_slot_class = core['node_class']

    sp_method = sp['registration_method']
    sp_cls = sp['constructor_name']
    cp_method = cp['registration_method']
    cp_cls = cp['constructor_name']

    recv_is_rooted_session = recv_node in rooted_session_set if recv_node is not None else False
    recv_is_any_session = recv_node in all_session_set if recv_node is not None else False
    recv_is_rooted_club = recv_node in rooted_club_set if recv_node is not None else False
    recv_is_any_club = recv_node in all_club_set if recv_node is not None else False

    exact_sp_method = method_on_gen_proto and raw_method_name == sp_method
    exact_cp_method = method_on_gen_proto and raw_method_name == cp_method
    exact_session_match = exact_sp_method and recv_is_rooted_session
    exact_club_match = exact_cp_method and recv_is_rooted_club

    safe_method_name, method_recognized = (
        base_graph._sanitize_method_label(raw_method_name, allowed_methods) if method_on_gen_proto else (None, False)
    )

    matched_target = None
    wrong_receiver_target = None
    wrong_method_target = None
    if exact_session_match:
        kind = 'session_listener'
        matched_target = 'session_provider'
    elif exact_club_match:
        kind = 'club_listener'
        matched_target = 'club_provider'
    elif exact_sp_method and not recv_is_rooted_session:
        kind = 'wrong_receiver'
        wrong_receiver_target = 'session_provider'
    elif exact_cp_method and not recv_is_rooted_club:
        kind = 'wrong_receiver'
        wrong_receiver_target = 'club_provider'
    elif recv_is_any_session and not exact_sp_method:
        kind = 'target_wrong_method'
        wrong_method_target = 'session_provider'
    elif recv_is_any_club and not exact_cp_method:
        kind = 'target_wrong_method'
        wrong_method_target = 'club_provider'
    else:
        kind = 'other_listener'

    return {
        'is_null_or_hole': False,
        'is_null': False,
        'kind': kind,
        'matched_target': matched_target,
        'wrong_receiver_target': wrong_receiver_target,
        'wrong_method_target': wrong_method_target,
        'node_class': safe_slot_class,
        'method_name': safe_method_name,
        'method_recognized': method_recognized,
        'method_on_generated_prototype': method_on_gen_proto,
        'bound_closure_on_proto_chain': bound_closure_on_chain,
        'proto_is_provider': proto_is_provider,
        'receiver_heap_object_id': recv_id,
        'receiver_class': recv_class,
        'receiver_class_recognized': recv_recognized,
        'receiver_is_rooted_session': recv_is_rooted_session,
        'receiver_matches_session_class': recv_class == sp_cls,
        'exact_session_match': exact_session_match,
        'receiver_is_rooted_club': recv_is_rooted_club,
        'receiver_matches_club_class': recv_class == cp_cls,
        'exact_club_match': exact_club_match,
    }


def _build_slot_summary_from_normalized(
    slots: dict[int, dict],
    *,
    norm_ambig: bool,
    reason: str | None,
    caps_exc: bool,
    cdp_count: int | None,
) -> dict:
    active_slots = []
    unmapped = []
    null_holes = []
    trailing_non_null = 0
    session_matches = 0
    club_matches = 0
    wrong_recv = 0
    wrong_method = 0
    other_cnt = 0

    if not norm_ambig and not caps_exc and cdp_count is not None and type(cdp_count) is int and cdp_count >= 0:
        for idx in range(cdp_count):
            if idx not in slots:
                unmapped.append(idx)
                continue
            tinfo = slots[idx]
            if tinfo.get('is_null_or_hole'):
                null_holes.append(idx)
            else:
                kind = tinfo['kind']
                if kind == 'session_listener':
                    session_matches += 1
                elif kind == 'club_listener':
                    club_matches += 1
                elif kind == 'wrong_receiver':
                    wrong_recv += 1
                elif kind == 'target_wrong_method':
                    wrong_method += 1
                else:
                    other_cnt += 1
            active_slots.append({'index': idx, **tinfo})

        for idx, tinfo in slots.items():
            if idx >= cdp_count and not tinfo.get('is_null_or_hole'):
                trailing_non_null += 1

    return {
        'normalization_ambiguous': norm_ambig,
        'reason': 'cdp_count_cap_exceeded' if caps_exc and not reason else reason,
        'caps_exceeded': caps_exc,
        'active_count': cdp_count,
        'active_slots': active_slots,
        'unmapped_active_slots': unmapped,
        'null_holes_in_active_range': null_holes,
        'trailing_non_null_count': trailing_non_null,
        'session_match_count': session_matches,
        'club_match_count': club_matches,
        'wrong_receiver_count': wrong_recv,
        'target_wrong_method_count': wrong_method,
        'other_listener_count': other_cnt,
    }


def _recompute_and_validate_session_club_slots(
    slots_info: object,
    *,
    cdp_count: int | None,
    binding: dict,
    sole_session_id: str | None,
    sole_club_id: str | None,
    expected_session_matches: int,
    expected_club_matches: int,
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
        problems.append(f"listener_array_ambiguous:{base_graph._sanitize_slot_reason(slots_info.get('reason'))}")

    unmapped = slots_info.get('unmapped_active_slots')
    if not isinstance(unmapped, list):
        problems.append('listener_slots_invalid_unmapped_list')
    elif unmapped:
        problems.append('unmapped_active_listener_slots')

    if not isinstance(slots_info.get('null_holes_in_active_range'), list):
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
        if norm_ambig is False and caps_exc is False and len(active_slots) != cdp_count:
            problems.append('active_slot_count_mismatch_cdp')

    if norm_ambig is True or caps_exc is True or cdp_count is None:
        if active_slots:
            problems.append('unexpected_active_slots_when_unscanned')
        return

    sp = binding['session_provider']
    cp = binding['club_provider']
    sp_method, sp_cls = sp['registration_method'], sp['constructor_name']
    cp_method, cp_cls = cp['registration_method'], cp['constructor_name']

    recomputed_null_holes: list[int] = []
    recomputed_sp_matches = 0
    recomputed_cp_matches = 0
    recomputed_wrong_recv = 0
    recomputed_wrong_method = 0
    recomputed_other = 0
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
        if is_null_or_hole:
            recomputed_null_holes.append(pos)
            continue
        if is_null:
            problems.append(f'slot_{pos}_contradictory_null_flags')
            continue

        kind = slot.get('kind')
        if kind not in VALID_SLOT_KINDS:
            problems.append(f'slot_{pos}_invalid_kind')
            continue

        bool_fields = (
            'method_on_generated_prototype',
            'bound_closure_on_proto_chain',
            'proto_is_provider',
            'receiver_is_rooted_session',
            'receiver_matches_session_class',
            'exact_session_match',
            'receiver_is_rooted_club',
            'receiver_matches_club_class',
            'exact_club_match',
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

        if slot['receiver_matches_session_class'] != (recv_cls == sp_cls):
            problems.append(f'slot_{pos}_session_receiver_class_flag_mismatch')
        if slot['receiver_matches_club_class'] != (recv_cls == cp_cls):
            problems.append(f'slot_{pos}_club_receiver_class_flag_mismatch')
        if slot['receiver_is_rooted_session'] and (sole_session_id is None or recv_id != sole_session_id or recv_cls != sp_cls):
            problems.append(f'slot_{pos}_receiver_rooted_session_mismatch')
        if slot['receiver_is_rooted_club'] and (sole_club_id is None or recv_id != sole_club_id or recv_cls != cp_cls):
            problems.append(f'slot_{pos}_receiver_rooted_club_mismatch')
        if method_on_proto and (proto_is_prov or not bc_on_chain or method_name is None):
            problems.append(f'slot_{pos}_invalid_prototype_method_flags')

        proto_ok = (not proto_is_prov) and bc_on_chain and method_on_proto
        proto_sp_method = proto_ok and (method_name == sp_method)
        proto_cp_method = proto_ok and (method_name == cp_method)

        recv_sole_sp = (
            sole_session_id is not None
            and recv_id == sole_session_id
            and recv_cls == sp_cls
            and slot['receiver_is_rooted_session']
            and slot['receiver_matches_session_class']
        )
        recv_sole_cp = (
            sole_club_id is not None
            and recv_id == sole_club_id
            and recv_cls == cp_cls
            and slot['receiver_is_rooted_club']
            and slot['receiver_matches_club_class']
        )

        rec_exact_sp = proto_sp_method and recv_sole_sp
        rec_exact_cp = proto_cp_method and recv_sole_cp
        if slot['exact_session_match'] != rec_exact_sp:
            problems.append(f'slot_{pos}_exact_session_match_mismatch')
        if slot['exact_club_match'] != rec_exact_cp:
            problems.append(f'slot_{pos}_exact_club_match_mismatch')

        targets_sp = slot['receiver_is_rooted_session'] or slot['receiver_matches_session_class'] or (sole_session_id is not None and recv_id == sole_session_id)
        targets_cp = slot['receiver_is_rooted_club'] or slot['receiver_matches_club_class'] or (sole_club_id is not None and recv_id == sole_club_id)

        if rec_exact_sp:
            rec_kind = 'session_listener'
            recomputed_sp_matches += 1
        elif rec_exact_cp:
            rec_kind = 'club_listener'
            recomputed_cp_matches += 1
        elif (proto_sp_method and not recv_sole_sp) or (proto_cp_method and not recv_sole_cp):
            rec_kind = 'wrong_receiver'
            recomputed_wrong_recv += 1
        elif (targets_sp and not proto_sp_method) or (targets_cp and not proto_cp_method):
            rec_kind = 'target_wrong_method'
            recomputed_wrong_method += 1
        else:
            rec_kind = 'other_listener'
            recomputed_other += 1

        if kind != rec_kind:
            problems.append(f'slot_{pos}_kind_mismatch')

    if len(seen_indices) != cdp_count or seen_indices != set(range(cdp_count)):
        problems.append('active_slots_incomplete_or_missing_indices')

    agg_checks = (
        ('null_holes_in_active_range', recomputed_null_holes, 'null_holes_aggregate_mismatch'),
        ('session_match_count', recomputed_sp_matches, 'session_match_count_aggregate_mismatch'),
        ('club_match_count', recomputed_cp_matches, 'club_match_count_aggregate_mismatch'),
        ('wrong_receiver_count', recomputed_wrong_recv, 'wrong_receiver_count_aggregate_mismatch'),
        ('target_wrong_method_count', recomputed_wrong_method, 'target_wrong_method_count_aggregate_mismatch'),
        ('other_listener_count', recomputed_other, 'other_listener_count_aggregate_mismatch'),
    )
    for key, rec_val, err_code in agg_checks:
        rep_val = slots_info.get(key)
        if isinstance(rec_val, int):
            if type(rep_val) is not int or rep_val != rec_val:
                problems.append(err_code)
        elif rep_val != rec_val:
            problems.append(err_code)

    if recomputed_null_holes:
        problems.append('null_holes_in_active_listener_range')
    if recomputed_wrong_recv > 0:
        problems.append('listener_wrong_receiver')
    if recomputed_wrong_method > 0:
        problems.append('listener_target_wrong_method')
    if recomputed_sp_matches != expected_session_matches:
        problems.append(f'session_match_count:{recomputed_sp_matches}!=expected:{expected_session_matches}')
    if recomputed_cp_matches != expected_club_matches:
        problems.append(f'club_match_count:{recomputed_cp_matches}!=expected:{expected_club_matches}')


def _check_cdp_block(cdp_obs: object) -> tuple[bool, bool, str | None, int | None]:
    if not isinstance(cdp_obs, dict):
        return False, True, 'missing_cdp_observations', None
    cdp_errs = cdp_obs.get('cdp_errors')
    if isinstance(cdp_errs, list) and cdp_errs:
        safe_errs = ','.join(_sanitize_cdp_error(x) for x in cdp_errs[:12])
        return False, False, f'cdp_errors:{safe_errs}', None
    return base_graph._check_cdp_counters(cdp_obs)


def _validate_snapshot_cdp_field_pair(
    *,
    field_name: str,
    expected_kind: str,
    expected_class: str | None,
    snap_sfields: dict,
    cdp_sfields: object,
    allowed_cls: frozenset[str],
    problems: list[str],
) -> dict | None:
    snap_f = base_graph._validate_snapshot_field_meta(
        snap_sfields.get(field_name),
        field_name,
        problems,
        allowed_classes=allowed_cls,
    )
    if snap_f is not None:
        if snap_f.get('is_null') is False:
            if expected_kind == 'string':
                if snap_f.get('node_type') not in ALLOWED_V8_STRING_TYPES or snap_f.get('class_name') is not None:
                    problems.append(f'snapshot_field_wrong_type:{field_name}')
                if snap_f.get('target_heap_object_id') is not None:
                    problems.append(f'snapshot_field_unexpected_target_heap_object_id:{field_name}')
            else:
                if snap_f.get('node_type') != 'object' or snap_f.get('class_name') != expected_class:
                    problems.append(f'snapshot_field_wrong_class:{field_name}')
                if not _is_valid_heap_object_id(snap_f.get('target_heap_object_id')):
                    problems.append(f'snapshot_field_missing_or_invalid_target_heap_object_id:{field_name}')
        elif snap_f.get('is_null') is True and snap_f.get('target_heap_object_id') is not None:
            problems.append(f'snapshot_field_null_with_target_heap_object_id:{field_name}')

    if isinstance(cdp_sfields, dict):
        cdp_f = base_graph._validate_cdp_field_meta(
            cdp_sfields.get(field_name),
            field_name,
            problems,
            allowed_classes=allowed_cls,
        )
        if cdp_f is not None and cdp_f.get('is_null') is False:
            if expected_kind == 'string':
                if cdp_f.get('value_type') != 'string' or cdp_f.get('class_name') is not None:
                    problems.append(f'cdp_field_wrong_type:{field_name}')
            else:
                if cdp_f.get('value_type') != 'object' or cdp_f.get('class_name') != expected_class:
                    problems.append(f'cdp_field_wrong_class:{field_name}')

        if snap_f is not None and cdp_f is not None:
            if snap_f['is_null'] != cdp_f['is_null']:
                problems.append(f'snapshot_vs_cdp_null_mismatch:{field_name}')
            elif not snap_f['is_null']:
                if expected_kind == 'string':
                    if (snap_f['node_type'] not in ALLOWED_V8_STRING_TYPES) or (cdp_f['value_type'] != 'string'):
                        problems.append(f'snapshot_vs_cdp_string_type_mismatch:{field_name}')
                else:
                    if snap_f['class_name'] != cdp_f['class_name']:
                        problems.append(f'snapshot_vs_cdp_class_mismatch:{field_name}')
                    if (snap_f['node_type'] == 'object') != (cdp_f['value_type'] == 'object'):
                        problems.append(f'snapshot_vs_cdp_type_mismatch:{field_name}')
    return snap_f


def _check_post_actor_field_contract(
    *,
    rule: object,
    label: str,
    smeta: dict | None,
    prev_key: str | None,
    prev_ids: dict,
    problems: list[str],
) -> None:
    """Enforce explicit `refetched` vs `null` post-actor contract; never allow missing/None IDs to pass."""
    if smeta is None:
        return
    if rule == 'refetched':
        if smeta.get('is_null') is not False:
            problems.append(f'post_actor_{label}_expected_refetched_got_null')
            return
        if prev_key is not None:
            cur_tid = smeta.get('target_heap_object_id')
            owner_tid = prev_ids.get(prev_key)
            cur_valid = _is_valid_heap_object_id(cur_tid)
            owner_valid = _is_valid_heap_object_id(owner_tid)
            if not cur_valid:
                problems.append(f'post_actor_{label}_missing_or_invalid_target_heap_object_id')
            if not owner_valid:
                problems.append(f'post_actor_{label}_missing_or_invalid_owner_target_heap_object_id')
            if cur_valid and owner_valid and cur_tid == owner_tid:
                problems.append(f'post_actor_{label}_reused_owner_object_id')
    elif rule == 'null':
        if smeta.get('is_null') is not True:
            problems.append(f'post_actor_{label}_stale_non_null')
    else:
        problems.append(f'post_actor_unknown_policy:{label}')


def evaluate_session_club_record(
    record: dict,
    *,
    binding: dict,
    epoch: str,
    cycle_num: int | None = None,
    actor: str | None = None,
    expected_time_origin: float | int | None = None,
    require_bank_account: bool = False,
    previous_owner_field_ids: dict | None = None,
    post_actor_contract: dict | None = None,
) -> tuple[list[str], dict]:
    """Independently evaluate one epoch's Session/Club listener-graph record without trusting booleans."""
    problems: list[str] = []
    target_status = {
        'session_provider': 'FAIL',
        'club_provider_core': 'FAIL',
        'club_provider_bank_account': 'FAIL',
        'bank_populated_at_epoch': False,
    }
    if epoch not in ALLOWED_EPOCHS:
        return ['invalid_epoch'], target_status
    if not isinstance(record, dict):
        return ['listener_graph_not_dict'], target_status
    if not binding or binding.get('ok') is not True:
        return ['listener_binding_invalid'], target_status

    allowed_cls = _allowed_classes(binding)
    if record.get('claim_scope') != CLAIM_SCOPE:
        problems.append('claim_scope_mismatch')
    if record.get('observation_mode') != OBSERVATION_MODE:
        problems.append('observation_mode_mismatch')
    if record.get('atomic_claim') is not False:
        problems.append('atomic_claim_must_be_false')
    rec_epoch = record.get('epoch')
    if rec_epoch != epoch:
        safe_ep = rec_epoch if rec_epoch in ALLOWED_EPOCHS else 'unrecognized'
        problems.append(f'epoch_mismatch:{safe_ep}!={epoch}')
    if record.get('binding_sha256') != binding.get('listener_binding_sha256'):
        problems.append('binding_sha256_mismatch')

    rec_origin = record.get('time_origin')
    if not base_graph._is_valid_time_origin(rec_origin):
        problems.append('invalid_or_missing_time_origin')
    if expected_time_origin is not None:
        if not base_graph._is_valid_time_origin(expected_time_origin) or rec_origin != expected_time_origin:
            problems.append('time_origin_mismatch')

    cdp_obs = record.get('cdp_observations')
    cdp_ok, cdp_unknown, cdp_err, cdp_count = _check_cdp_block(cdp_obs)
    if not cdp_ok:
        problems.append(cdp_err or ('cdp_unknown' if cdp_unknown else 'cdp_failed'))

    if isinstance(cdp_obs, dict):
        t0 = cdp_obs.get('time_origin_before')
        t1 = cdp_obs.get('time_origin_after')
        if not base_graph._is_valid_time_origin(t0) or not base_graph._is_valid_time_origin(t1):
            problems.append('missing_or_invalid_cdp_time_origin')
        else:
            if t0 != t1:
                problems.append('cdp_time_origin_changed')
            if base_graph._is_valid_time_origin(rec_origin) and t0 != rec_origin:
                problems.append('cdp_time_origin_mismatch_graph')
            if expected_time_origin is not None and base_graph._is_valid_time_origin(expected_time_origin) and t0 != expected_time_origin:
                problems.append('cdp_time_origin_mismatch_epoch')

    auth_block = record.get('auth_provider') or {}
    sp_block = record.get('session_provider') or {}
    cp_block = record.get('club_provider') or {}
    auth_records = auth_block.get('records') or []
    sp_records = sp_block.get('records') or []
    cp_records = cp_block.get('records') or []

    if type(auth_block.get('strong_root_reachable_count')) is not int or not isinstance(auth_records, list) or auth_block.get('strong_root_reachable_count') != len(auth_records):
        problems.append('auth_record_count_mismatch')
    if type(sp_block.get('strong_root_reachable_count')) is not int or not isinstance(sp_records, list) or sp_block.get('strong_root_reachable_count') != len(sp_records):
        problems.append('session_record_count_mismatch')
    if type(cp_block.get('strong_root_reachable_count')) is not int or not isinstance(cp_records, list) or cp_block.get('strong_root_reachable_count') != len(cp_records):
        problems.append('club_record_count_mismatch')

    if not isinstance(auth_records, list) or len(auth_records) != 1:
        got_auth = len(auth_records) if isinstance(auth_records, list) else 'invalid'
        problems.append(f'expected_1_rooted_auth_provider_got:{got_auth}')
        return problems, target_status

    auth_rec = auth_records[0]
    if not isinstance(auth_rec, dict):
        problems.append('auth_record_not_dict')
        return problems, target_status

    if isinstance(cdp_obs, dict) and str(cdp_obs.get('auth_heap_object_id')) != str(auth_rec.get('heap_object_id')):
        problems.append('cdp_auth_heap_object_id_mismatch')

    snap_user = base_graph._validate_snapshot_field_meta(
        auth_rec.get('current_user'),
        'auth_current_user',
        problems,
        allowed_classes=allowed_cls,
    )
    if isinstance(cdp_obs, dict):
        cdp_user = base_graph._validate_cdp_field_meta(cdp_obs.get('auth_current_user'), 'cdp_auth_current_user', problems, allowed_classes=allowed_cls)
        cdp_user_before = base_graph._validate_cdp_field_meta(cdp_obs.get('auth_current_user_before'), 'cdp_auth_current_user_before', problems, allowed_classes=allowed_cls)
        cdp_user_after = base_graph._validate_cdp_field_meta(cdp_obs.get('auth_current_user_after'), 'cdp_auth_current_user_after', problems, allowed_classes=allowed_cls)
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

    if epoch in ('owner_active', 'post_actor') and (snap_user is None or snap_user['is_null'] is not False):
        problems.append(f'{epoch}_current_user_is_null')
    if epoch == 'post_logout' and (snap_user is None or snap_user['is_null'] is not True):
        problems.append('post_logout_current_user_not_null')
    if epoch == 'baseline' and (snap_user is None or snap_user['is_null'] is not True):
        problems.append('baseline_current_user_not_null')

    sp_dup = not isinstance(sp_records, list) or len(sp_records) > 1
    cp_dup = not isinstance(cp_records, list) or len(cp_records) > 1
    if sp_dup:
        got_sp = len(sp_records) if isinstance(sp_records, list) else 'invalid'
        problems.append(f'duplicate_rooted_session_provider:{got_sp}')
    if cp_dup:
        got_cp = len(cp_records) if isinstance(cp_records, list) else 'invalid'
        problems.append(f'duplicate_rooted_club_provider:{got_cp}')

    sole_sp_id = str(sp_records[0].get('heap_object_id')) if (not sp_dup and len(sp_records) == 1 and isinstance(sp_records[0], dict)) else None
    sole_cp_id = str(cp_records[0].get('heap_object_id')) if (not cp_dup and len(cp_records) == 1 and isinstance(cp_records[0], dict)) else None

    if not sp_dup and not cp_dup:
        _recompute_and_validate_session_club_slots(
            auth_rec.get('listener_slots'),
            cdp_count=cdp_count,
            binding=binding,
            sole_session_id=sole_sp_id,
            sole_club_id=sole_cp_id,
            expected_session_matches=1 if sole_sp_id is not None else 0,
            expected_club_matches=1 if sole_cp_id is not None else 0,
            problems=problems,
        )

    common_prob_count = len(problems)

    # Resolve post_actor policy explicitly (never silently treat refetch vs leak interchangeably)
    if post_actor_contract is None and cycle_num in DEFAULT_CYCLE_POST_ACTOR_CONTRACTS:
        post_actor_contract = DEFAULT_CYCLE_POST_ACTOR_CONTRACTS[cycle_num]
        if actor and post_actor_contract.get('actor') != actor:
            problems.append(f'unexpected_cycle_{cycle_num}_actor')

    sp_info = binding['session_provider']
    models = binding['models']
    sess_cls = models['session']['constructor_name']
    hist_cls = models['session_history_page']['constructor_name']
    club_cls = models['club']['constructor_name']
    bank_cls = models['bank_account']['constructor_name']

    # --- Evaluate SessionProvider target ---
    sp_problems: list[str] = []
    if len(sp_records) == 1:
        srec = sp_records[0]
        if not isinstance(srec, dict):
            sp_problems.append('session_record_not_dict')
        else:
            if isinstance(cdp_obs, dict) and str(cdp_obs.get('session_heap_object_id')) != str(srec.get('heap_object_id')):
                sp_problems.append('cdp_session_heap_object_id_mismatch')
            sfields = srec.get('selected_fields')
            cdp_sfields = cdp_obs.get('session_selected_fields') if isinstance(cdp_obs, dict) else None
            if not isinstance(sfields, dict):
                sp_problems.append('snapshot_session_selected_fields_not_dict')
                sfields = {}
            if not isinstance(cdp_sfields, dict):
                sp_problems.append('missing_cdp_session_selected_fields')

            sid_f = sp_info['session_id_field']
            csess_f = sp_info['current_session_field']
            hist_f = sp_info['history_field']
            validated_sp = {}
            for fname, exp_kind, exp_cls in (
                (sid_f, 'string', None),
                (csess_f, 'object', sess_cls),
                (hist_f, 'object', hist_cls),
            ):
                validated_sp[fname] = _validate_snapshot_cdp_field_pair(
                    field_name=fname,
                    expected_kind=exp_kind,
                    expected_class=exp_cls,
                    snap_sfields=sfields,
                    cdp_sfields=cdp_sfields,
                    allowed_cls=allowed_cls,
                    problems=sp_problems,
                )

            snap_sid = validated_sp.get(sid_f)
            snap_csess = validated_sp.get(csess_f)
            snap_hist = validated_sp.get(hist_f)

            if epoch == 'owner_active':
                if snap_sid is None or snap_sid['is_null'] is not False:
                    sp_problems.append('owner_active_current_session_id_is_null')
                if snap_csess is None or snap_csess['is_null'] is not False:
                    sp_problems.append('owner_active_current_session_not_populated')
                if snap_hist is None or snap_hist['is_null'] is not False:
                    sp_problems.append('owner_active_session_history_not_populated')
            elif epoch in ('baseline', 'post_logout'):
                for label, smeta in (('current_session_id', snap_sid), ('current_session', snap_csess), ('session_history', snap_hist)):
                    if smeta is None or smeta['is_null'] is not True:
                        sp_problems.append(f'{epoch}_{label}_not_null')
            elif epoch == 'post_actor':
                sp_policy = (post_actor_contract or {}).get('session') or {}
                prev = previous_owner_field_ids or {}
                for policy_key, label, smeta, prev_key in (
                    ('session_id', 'current_session_id', snap_sid, None),
                    ('current_session', 'current_session', snap_csess, 'current_session'),
                    ('history', 'session_history', snap_hist, 'session_history'),
                ):
                    _check_post_actor_field_contract(
                        rule=sp_policy.get(policy_key, 'null'),
                        label=label,
                        smeta=smeta,
                        prev_key=prev_key,
                        prev_ids=prev,
                        problems=sp_problems,
                    )
    elif len(sp_records) == 0:
        if cycle_num == 1 and epoch == 'baseline':
            pass
        elif cycle_num is None and epoch == 'baseline':
            pass
        else:
            sp_problems.append(f'{epoch}_missing_session_provider')

    # --- Evaluate ClubProvider target (core + bank_account separated cleanly) ---
    cp_info = binding['club_provider']
    cp_core_problems: list[str] = []
    cp_bank_problems: list[str] = []
    bank_populated_here = False

    if len(cp_records) == 1:
        crec = cp_records[0]
        if not isinstance(crec, dict):
            cp_core_problems.append('club_record_not_dict')
            cp_bank_problems.append('club_record_not_dict')
        else:
            if isinstance(cdp_obs, dict) and str(cdp_obs.get('club_heap_object_id')) != str(crec.get('heap_object_id')):
                cp_core_problems.append('cdp_club_heap_object_id_mismatch')
                cp_bank_problems.append('cdp_club_heap_object_id_mismatch')
            cfields = crec.get('selected_fields')
            cdp_cfields = cdp_obs.get('club_selected_fields') if isinstance(cdp_obs, dict) else None
            if not isinstance(cfields, dict):
                cp_core_problems.append('snapshot_club_selected_fields_not_dict')
                cfields = {}
            if not isinstance(cdp_cfields, dict):
                cp_core_problems.append('missing_cdp_club_selected_fields')

            cid_f = cp_info['club_id_field']
            cclub_f = cp_info['current_club_field']
            cbank_f = cp_info['bank_account_field']

            snap_cid = _validate_snapshot_cdp_field_pair(
                field_name=cid_f,
                expected_kind='string',
                expected_class=None,
                snap_sfields=cfields,
                cdp_sfields=cdp_cfields,
                allowed_cls=allowed_cls,
                problems=cp_core_problems,
            )
            snap_cclub = _validate_snapshot_cdp_field_pair(
                field_name=cclub_f,
                expected_kind='object',
                expected_class=club_cls,
                snap_sfields=cfields,
                cdp_sfields=cdp_cfields,
                allowed_cls=allowed_cls,
                problems=cp_core_problems,
            )
            snap_cbank = _validate_snapshot_cdp_field_pair(
                field_name=cbank_f,
                expected_kind='object',
                expected_class=bank_cls,
                snap_sfields=cfields,
                cdp_sfields=cdp_cfields,
                allowed_cls=allowed_cls,
                problems=cp_bank_problems,
            )

            if epoch == 'owner_active':
                if snap_cid is None or snap_cid['is_null'] is not False:
                    cp_core_problems.append('owner_active_current_club_id_is_null')
                if snap_cclub is None or snap_cclub['is_null'] is not False:
                    cp_core_problems.append('owner_active_current_club_not_populated')
                if snap_cbank is None:
                    cp_bank_problems.append('owner_active_current_bank_account_unverified')
                elif snap_cbank['is_null'] is False:
                    bank_populated_here = True
                elif require_bank_account:
                    cp_bank_problems.append('owner_active_current_bank_account_not_populated')
            elif epoch in ('baseline', 'post_logout'):
                for label, smeta in (('current_club_id', snap_cid), ('current_club', snap_cclub)):
                    if smeta is None or smeta['is_null'] is not True:
                        cp_core_problems.append(f'{epoch}_{label}_not_null')
                if snap_cbank is None or snap_cbank['is_null'] is not True:
                    cp_bank_problems.append(f'{epoch}_current_bank_account_not_null')
            elif epoch == 'post_actor':
                cp_policy = (post_actor_contract or {}).get('club') or {}
                prev = previous_owner_field_ids or {}
                for policy_key, label, smeta, prev_key, dest_list in (
                    ('club_id', 'current_club_id', snap_cid, None, cp_core_problems),
                    ('current_club', 'current_club', snap_cclub, 'current_club', cp_core_problems),
                    ('bank_account', 'current_bank_account', snap_cbank, 'current_bank_account', cp_bank_problems),
                ):
                    _check_post_actor_field_contract(
                        rule=cp_policy.get(policy_key, 'null'),
                        label=label,
                        smeta=smeta,
                        prev_key=prev_key,
                        prev_ids=prev,
                        problems=dest_list,
                    )
    elif len(cp_records) == 0:
        if (cycle_num == 1 or cycle_num is None) and epoch == 'baseline':
            pass
        else:
            cp_core_problems.append(f'{epoch}_missing_club_provider')
            cp_bank_problems.append(f'{epoch}_missing_club_provider')

    problems.extend(sp_problems)
    problems.extend(cp_core_problems)
    for bp in cp_bank_problems:
        if bp not in problems:
            problems.append(bp)

    has_common_problem = common_prob_count > 0
    if cdp_unknown or record.get('ambiguous_layout') or record.get('caps_exceeded'):
        sp_verdict = 'UNKNOWN'
        cp_core_verdict = 'UNKNOWN'
        cp_bank_verdict = 'UNKNOWN'
    else:
        if has_common_problem or sp_problems:
            sp_verdict = 'FAIL'
        elif len(sp_records) == 0 and (cycle_num == 1 or cycle_num is None) and epoch == 'baseline':
            sp_verdict = 'NOT_RUN_LAZY'
        else:
            sp_verdict = 'PASS'

        if has_common_problem or cp_core_problems:
            cp_core_verdict = 'FAIL'
        elif len(cp_records) == 0 and (cycle_num == 1 or cycle_num is None) and epoch == 'baseline':
            cp_core_verdict = 'NOT_RUN_LAZY'
        else:
            cp_core_verdict = 'PASS'

        if has_common_problem or cp_bank_problems:
            cp_bank_verdict = 'FAIL'
        elif len(cp_records) == 0 and (cycle_num == 1 or cycle_num is None) and epoch == 'baseline':
            cp_bank_verdict = 'NOT_RUN_LAZY'
        elif epoch == 'owner_active' and not bank_populated_here:
            cp_bank_verdict = 'NOT_RUN'
        else:
            cp_bank_verdict = 'PASS'

    target_status = {
        'session_provider': sp_verdict,
        'club_provider_core': cp_core_verdict,
        'club_provider_bank_account': cp_bank_verdict,
        'bank_populated_at_epoch': bank_populated_here,
    }
    return problems, target_status


def _decide_epoch_verdict(target_status: dict, *, unknown_flags: bool) -> str:
    if unknown_flags:
        return 'UNKNOWN'
    vals = (
        target_status['session_provider'],
        target_status['club_provider_core'],
        target_status['club_provider_bank_account'],
    )
    if any(v == 'UNKNOWN' for v in vals):
        return 'UNKNOWN'
    if any(v == 'FAIL' for v in vals):
        return 'FAIL'
    if target_status['session_provider'] == 'NOT_RUN_LAZY' or target_status['club_provider_core'] == 'NOT_RUN_LAZY':
        return 'NOT_RUN_LAZY'
    return 'PASS'


def _build_prescan_base(raw_bytes: bytes, binding: dict, epoch: str, time_origin: float | int | None) -> tuple[dict, dict | None]:
    snap_sha12 = base_graph._sha256_bytes(raw_bytes)[:12]
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
            'session_provider': {'all_object_nodes': 0, 'strong_root_reachable_count': 0, 'records': []},
            'club_provider': {'all_object_nodes': 0, 'strong_root_reachable_count': 0, 'records': []},
            'rooted_auth_heap_object_ids': [],
            'rooted_session_heap_object_ids': [],
            'rooted_club_heap_object_ids': [],
            'findings': [parse_err or 'snapshot_parse_failed'],
            'verdict': 'UNKNOWN',
            'ok': False,
        }, None
    return {'snap_sha12': snap_sha12, 'doc': doc}, base_graph._snapshot_index(doc)


def scan_snapshot(
    raw_bytes: bytes,
    *,
    binding: dict,
    epoch: str,
    cycle_num: int | None = None,
    actor: str | None = None,
    cdp_observations: dict | None = None,
    time_origin: float | int | None = None,
    require_bank_account: bool = False,
    previous_owner_field_ids: dict | None = None,
) -> dict:
    """Parse V8 snapshot once, extract Auth -> Session/Club listener graph, and apply CDP observations."""
    if not binding or binding.get('ok') is not True:
        raise ValueError('valid listener_source_binding is required')
    if epoch not in ALLOWED_EPOCHS:
        raise ValueError(f'unsupported epoch: {epoch}')

    meta_or_err, idx_data = _build_prescan_base(raw_bytes, binding, epoch, time_origin)
    if idx_data is None:
        meta_or_err['cdp_observations'] = cdp_observations
        return meta_or_err

    auth_cls = binding['auth_provider']['constructor_name']
    sp = binding['session_provider']
    cp = binding['club_provider']
    sp_cls = sp['constructor_name']
    cp_cls = cp['constructor_name']

    all_auth: list[int] = []
    all_sp: list[int] = []
    all_cp: list[int] = []
    for ni in range(idx_data['count']):
        if base_graph._node_type(idx_data, ni) == 'object':
            cname = base_graph._node_name(idx_data, ni)
            if cname == auth_cls:
                all_auth.append(ni)
            elif cname == sp_cls:
                all_sp.append(ni)
            elif cname == cp_cls:
                all_cp.append(ni)

    rooted_auth = [ni for ni in all_auth if base_graph._is_rooted(idx_data, ni)]
    rooted_sp = [ni for ni in all_sp if base_graph._is_rooted(idx_data, ni)]
    rooted_cp = [ni for ni in all_cp if base_graph._is_rooted(idx_data, ni)]
    allowed_cls = _allowed_classes(binding)

    sp_records = [
        {
            'heap_object_id': str(base_graph._node_id(idx_data, n)),
            'selected_fields': {
                sp['session_id_field']: _inspect_field_with_object_id(idx_data, n, sp['session_id_field'], allowed_classes=allowed_cls),
                sp['current_session_field']: _inspect_field_with_object_id(idx_data, n, sp['current_session_field'], allowed_classes=allowed_cls),
                sp['history_field']: _inspect_field_with_object_id(idx_data, n, sp['history_field'], allowed_classes=allowed_cls),
            },
        }
        for n in rooted_sp
    ]
    cp_records = [
        {
            'heap_object_id': str(base_graph._node_id(idx_data, n)),
            'selected_fields': {
                cp['club_id_field']: _inspect_field_with_object_id(idx_data, n, cp['club_id_field'], allowed_classes=allowed_cls),
                cp['current_club_field']: _inspect_field_with_object_id(idx_data, n, cp['current_club_field'], allowed_classes=allowed_cls),
                cp['bank_account_field']: _inspect_field_with_object_id(idx_data, n, cp['bank_account_field'], allowed_classes=allowed_cls),
            },
        }
        for n in rooted_cp
    ]

    pre_scan = {
        'claim_scope': CLAIM_SCOPE,
        'observation_mode': OBSERVATION_MODE,
        'atomic_claim': False,
        'epoch': epoch,
        'snapshot_sha256_12': meta_or_err['snap_sha12'],
        'time_origin': time_origin,
        'binding_sha256': binding.get('listener_binding_sha256'),
        'structure_ok': True,
        'ambiguous_layout': False,
        'caps_exceeded': False,
        'auth_provider': {'all_object_nodes': len(all_auth), 'strong_root_reachable_count': len(rooted_auth), 'records': []},
        'session_provider': {'all_object_nodes': len(all_sp), 'strong_root_reachable_count': len(rooted_sp), 'records': sp_records},
        'club_provider': {'all_object_nodes': len(all_cp), 'strong_root_reachable_count': len(rooted_cp), 'records': cp_records},
        'rooted_auth_heap_object_ids': [str(base_graph._node_id(idx_data, n)) for n in rooted_auth],
        'rooted_session_heap_object_ids': [str(base_graph._node_id(idx_data, n)) for n in rooted_sp],
        'rooted_club_heap_object_ids': [str(base_graph._node_id(idx_data, n)) for n in rooted_cp],
        '_internal': {
            'rooted_auth_nodes': rooted_auth,
            'rooted_sp_nodes': rooted_sp,
            'all_sp_nodes': all_sp,
            'rooted_cp_nodes': rooted_cp,
            'all_cp_nodes': all_cp,
        },
    }
    return apply_cdp_observations(
        pre_scan,
        binding=binding,
        epoch=epoch,
        cycle_num=cycle_num,
        actor=actor,
        cdp_observations=cdp_observations,
        time_origin=time_origin,
        require_bank_account=require_bank_account,
        previous_owner_field_ids=previous_owner_field_ids,
        _idx_data=idx_data,
    )


def apply_cdp_observations(
    pre_scan: dict,
    *,
    binding: dict,
    epoch: str,
    cycle_num: int | None = None,
    actor: str | None = None,
    cdp_observations: dict | None,
    time_origin: float | int | None = None,
    require_bank_account: bool = False,
    previous_owner_field_ids: dict | None = None,
    _idx_data: dict | None = None,
) -> dict:
    """Attach CDP observations onto an existing pre_scan without double-parsing."""
    rec = json.loads(json.dumps({k: v for k, v in pre_scan.items() if k != '_internal'}))
    if time_origin is not None:
        rec['time_origin'] = time_origin
    rec['cdp_observations'] = cdp_observations

    _, cdp_unknown, _, cdp_count = _check_cdp_block(cdp_observations)
    allowed_cls = _allowed_classes(binding)
    listeners_field = binding['auth_provider']['listeners_field']
    user_field = binding['auth_provider']['current_user_field']

    if _idx_data is not None and '_internal' in pre_scan:
        internal = pre_scan['_internal']
        rooted_sp_set = set(internal['rooted_sp_nodes'])
        all_sp_set = set(internal['all_sp_nodes'])
        rooted_cp_set = set(internal['rooted_cp_nodes'])
        all_cp_set = set(internal['all_cp_nodes'])

        auth_recs = []
        for a in internal['rooted_auth_nodes']:
            a_props = base_graph._property_edges(_idx_data, a)
            user_info = base_graph._inspect_selected_field(_idx_data, a, user_field, allowed_classes=allowed_cls)
            listeners_node = a_props.get(listeners_field)
            if listeners_node is None:
                slot_summary = _build_slot_summary_from_normalized(
                    {}, norm_ambig=True, reason='missing_listeners_property', caps_exc=False, cdp_count=cdp_count,
                )
            else:
                norm = base_graph._normalize_listener_slots(_idx_data, listeners_node, cdp_count)
                inspected = {
                    idx: _inspect_session_club_tearoff(
                        _idx_data,
                        snode,
                        binding=binding,
                        rooted_session_set=rooted_sp_set,
                        all_session_set=all_sp_set,
                        rooted_club_set=rooted_cp_set,
                        all_club_set=all_cp_set,
                    )
                    for idx, snode in norm['slots'].items()
                }
                slot_summary = _build_slot_summary_from_normalized(
                    inspected,
                    norm_ambig=norm['normalization_ambiguous'],
                    reason=norm.get('reason'),
                    caps_exc=norm.get('caps_exceeded', False),
                    cdp_count=cdp_count,
                )
            auth_recs.append({
                'heap_object_id': str(base_graph._node_id(_idx_data, a)),
                'current_user': user_info,
                'listener_slots': slot_summary,
            })
        rec['auth_provider']['records'] = auth_recs

    return _finalize_record_with_verdict(
        rec,
        binding=binding,
        epoch=epoch,
        cycle_num=cycle_num,
        actor=actor,
        cdp_unknown=cdp_unknown,
        require_bank_account=require_bank_account,
        previous_owner_field_ids=previous_owner_field_ids,
    )


def _finalize_record_with_verdict(
    rec: dict,
    *,
    binding: dict,
    epoch: str,
    cycle_num: int | None,
    actor: str | None,
    cdp_unknown: bool,
    require_bank_account: bool,
    previous_owner_field_ids: dict | None,
) -> dict:
    auth_recs = rec['auth_provider']['records']
    rooted_auth_cnt = rec['auth_provider']['strong_root_reachable_count']
    rooted_sp_cnt = rec['session_provider']['strong_root_reachable_count']
    rooted_cp_cnt = rec['club_provider']['strong_root_reachable_count']
    unknown_flags = bool(rec.get('ambiguous_layout') or rec.get('caps_exceeded') or cdp_unknown)

    if rooted_auth_cnt == 1 and rooted_sp_cnt <= 1 and rooted_cp_cnt <= 1:
        for ar in auth_recs:
            sl = ar.get('listener_slots') or {}
            if sl.get('caps_exceeded') or sl.get('normalization_ambiguous') or sl.get('unmapped_active_slots'):
                unknown_flags = True
                rec['ambiguous_layout'] = bool(sl.get('normalization_ambiguous') or rec.get('ambiguous_layout'))
                rec['caps_exceeded'] = bool(sl.get('caps_exceeded') or rec.get('caps_exceeded'))
    else:
        unknown_flags = bool(not rec.get('structure_ok', True) or cdp_unknown)

    problems, target_status = evaluate_session_club_record(
        rec,
        binding=binding,
        epoch=epoch,
        cycle_num=cycle_num,
        actor=actor,
        expected_time_origin=rec.get('time_origin'),
        require_bank_account=require_bank_account,
        previous_owner_field_ids=previous_owner_field_ids,
    )
    verdict = _decide_epoch_verdict(target_status, unknown_flags=unknown_flags)
    rec['target_status'] = target_status
    rec['findings'] = problems
    rec['verdict'] = verdict
    rec['ok'] = verdict in ('PASS', 'NOT_RUN_LAZY')
    return rec


def _normalize_for_scan_cache(raw_bytes: bytes, binding: dict, epoch: str, time_origin: float | int | None = None) -> dict:
    """Two-step CLI pre-scan preserving normalized slots and selected fields without CDP."""
    meta_or_err, idx_data = _build_prescan_base(raw_bytes, binding, epoch, time_origin)
    if idx_data is None:
        meta_or_err['_cached_auth'] = []
        return meta_or_err

    auth_cls = binding['auth_provider']['constructor_name']
    sp = binding['session_provider']
    cp = binding['club_provider']
    sp_cls = sp['constructor_name']
    cp_cls = cp['constructor_name']
    listeners_field = binding['auth_provider']['listeners_field']
    user_field = binding['auth_provider']['current_user_field']
    allowed_cls = _allowed_classes(binding)

    all_auth = [i for i in range(idx_data['count']) if base_graph._node_type(idx_data, i) == 'object' and base_graph._node_name(idx_data, i) == auth_cls]
    all_sp = [i for i in range(idx_data['count']) if base_graph._node_type(idx_data, i) == 'object' and base_graph._node_name(idx_data, i) == sp_cls]
    all_cp = [i for i in range(idx_data['count']) if base_graph._node_type(idx_data, i) == 'object' and base_graph._node_name(idx_data, i) == cp_cls]
    rooted_auth = [i for i in all_auth if base_graph._is_rooted(idx_data, i)]
    rooted_sp = [i for i in all_sp if base_graph._is_rooted(idx_data, i)]
    rooted_cp = [i for i in all_cp if base_graph._is_rooted(idx_data, i)]

    sp_records = [
        {
            'heap_object_id': str(base_graph._node_id(idx_data, n)),
            'selected_fields': {
                sp['session_id_field']: _inspect_field_with_object_id(idx_data, n, sp['session_id_field'], allowed_classes=allowed_cls),
                sp['current_session_field']: _inspect_field_with_object_id(idx_data, n, sp['current_session_field'], allowed_classes=allowed_cls),
                sp['history_field']: _inspect_field_with_object_id(idx_data, n, sp['history_field'], allowed_classes=allowed_cls),
            },
        }
        for n in rooted_sp
    ]
    cp_records = [
        {
            'heap_object_id': str(base_graph._node_id(idx_data, n)),
            'selected_fields': {
                cp['club_id_field']: _inspect_field_with_object_id(idx_data, n, cp['club_id_field'], allowed_classes=allowed_cls),
                cp['current_club_field']: _inspect_field_with_object_id(idx_data, n, cp['current_club_field'], allowed_classes=allowed_cls),
                cp['bank_account_field']: _inspect_field_with_object_id(idx_data, n, cp['bank_account_field'], allowed_classes=allowed_cls),
            },
        }
        for n in rooted_cp
    ]

    cached_auth = []
    rooted_sp_set, all_sp_set = set(rooted_sp), set(all_sp)
    rooted_cp_set, all_cp_set = set(rooted_cp), set(all_cp)
    for a in rooted_auth:
        a_props = base_graph._property_edges(idx_data, a)
        user_info = base_graph._inspect_selected_field(idx_data, a, user_field, allowed_classes=allowed_cls)
        listeners_node = a_props.get(listeners_field)
        if listeners_node is None:
            norm = {'normalization_ambiguous': True, 'reason': 'missing_listeners_property', 'caps_exceeded': False, 'slots': {}}
        else:
            norm = base_graph._normalize_listener_slots(idx_data, listeners_node, None)
        inspected_slots = {
            str(idx): _inspect_session_club_tearoff(
                idx_data,
                snode,
                binding=binding,
                rooted_session_set=rooted_sp_set,
                all_session_set=all_sp_set,
                rooted_club_set=rooted_cp_set,
                all_club_set=all_cp_set,
            )
            for idx, snode in norm['slots'].items()
        }
        cached_auth.append({
            'heap_object_id': str(base_graph._node_id(idx_data, a)),
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
        'snapshot_sha256_12': meta_or_err['snap_sha12'],
        'time_origin': time_origin,
        'binding_sha256': binding.get('listener_binding_sha256'),
        'structure_ok': True,
        'ambiguous_layout': any(a['normalization_ambiguous'] for a in cached_auth),
        'caps_exceeded': any(a['caps_exceeded'] for a in cached_auth),
        'auth_provider': {'all_object_nodes': len(all_auth), 'strong_root_reachable_count': len(rooted_auth), 'records': []},
        'session_provider': {'all_object_nodes': len(all_sp), 'strong_root_reachable_count': len(rooted_sp), 'records': sp_records},
        'club_provider': {'all_object_nodes': len(all_cp), 'strong_root_reachable_count': len(rooted_cp), 'records': cp_records},
        'rooted_auth_heap_object_ids': [str(base_graph._node_id(idx_data, n)) for n in rooted_auth],
        'rooted_session_heap_object_ids': [str(base_graph._node_id(idx_data, n)) for n in rooted_sp],
        'rooted_club_heap_object_ids': [str(base_graph._node_id(idx_data, n)) for n in rooted_cp],
        '_cached_auth': cached_auth,
    }


def apply_cdp_to_cached_prescan(
    pre_scan: dict,
    *,
    binding: dict,
    epoch: str,
    cycle_num: int | None = None,
    actor: str | None = None,
    cdp_observations: dict | None,
    time_origin: float | int | None = None,
    require_bank_account: bool = False,
    previous_owner_field_ids: dict | None = None,
) -> dict:
    """Attach CDP observations onto cached CLI `scan` output without re-reading the snapshot."""
    rec = json.loads(json.dumps({k: v for k, v in pre_scan.items() if k != '_cached_auth'}))
    if time_origin is not None:
        rec['time_origin'] = time_origin
    rec['cdp_observations'] = cdp_observations

    _, cdp_unknown, _, cdp_count = _check_cdp_block(cdp_observations)
    caps_hit = bool(rec.get('caps_exceeded')) or (
        cdp_count is not None and type(cdp_count) is int and cdp_count > MAX_ARRAY_SLOTS
    )
    if caps_hit:
        rec['caps_exceeded'] = True

    auth_recs = []
    for cached in pre_scan.get('_cached_auth') or []:
        slots_int = {int(k): v for k, v in (cached.get('slots') or {}).items()}
        slot_summary = _build_slot_summary_from_normalized(
            slots_int,
            norm_ambig=bool(cached.get('normalization_ambiguous')),
            reason=cached.get('reason'),
            caps_exc=caps_hit or bool(cached.get('caps_exceeded')),
            cdp_count=cdp_count,
        )
        auth_recs.append({
            'heap_object_id': cached['heap_object_id'],
            'current_user': cached['current_user'],
            'listener_slots': slot_summary,
        })
    rec['auth_provider']['records'] = auth_recs

    return _finalize_record_with_verdict(
        rec,
        binding=binding,
        epoch=epoch,
        cycle_num=cycle_num,
        actor=actor,
        cdp_unknown=cdp_unknown,
        require_bank_account=require_bank_account,
        previous_owner_field_ids=previous_owner_field_ids,
    )


def extract_owner_field_object_ids(owner_record: dict, binding: dict) -> dict:
    """Recompute V8 heap object IDs of Owner's non-null object selected fields for strict non-reuse checks."""
    out: dict[str, str] = {}
    if not isinstance(owner_record, dict) or not isinstance(binding, dict):
        return out
    sp = binding.get('session_provider') or {}
    cp = binding.get('club_provider') or {}

    sp_recs = (owner_record.get('session_provider') or {}).get('records') or []
    if len(sp_recs) == 1 and isinstance(sp_recs[0], dict):
        sf = sp_recs[0].get('selected_fields') or {}
        if isinstance(sf, dict):
            for out_key, fname in (('current_session', sp.get('current_session_field')), ('session_history', sp.get('history_field'))):
                meta = sf.get(fname) if fname else None
                if (
                    isinstance(meta, dict)
                    and meta.get('present') is True
                    and meta.get('is_null') is False
                    and meta.get('node_type') == 'object'
                    and meta.get('class_recognized') is True
                    and _is_valid_heap_object_id(meta.get('target_heap_object_id'))
                ):
                    out[out_key] = meta['target_heap_object_id']

    cp_recs = (owner_record.get('club_provider') or {}).get('records') or []
    if len(cp_recs) == 1 and isinstance(cp_recs[0], dict):
        cf = cp_recs[0].get('selected_fields') or {}
        if isinstance(cf, dict):
            for out_key, fname in (('current_club', cp.get('current_club_field')), ('current_bank_account', cp.get('bank_account_field'))):
                meta = cf.get(fname) if fname else None
                if (
                    isinstance(meta, dict)
                    and meta.get('present') is True
                    and meta.get('is_null') is False
                    and meta.get('node_type') == 'object'
                    and meta.get('class_recognized') is True
                    and _is_valid_heap_object_id(meta.get('target_heap_object_id'))
                ):
                    out[out_key] = meta['target_heap_object_id']
    return out


# --- Cross-cycle bundle verification & anti-forgery auditor --------------------------

def _check_bundle_cleanup(summary: dict, problems: list[str]) -> None:
    cleanup = summary.get('cleanup')
    if not isinstance(cleanup, dict):
        problems.append('summary.json cleanup must be an object')
        return
    required_true = (
        'ok',
        'dump_dir_outside_repo',
        'dumps_dir_removed',
        'chrome_profile_dir_removed',
        'disposable_instructions_club_created',
        'disposable_instructions_session_created',
        'disposable_instructions_removed',
        'disposable_instructions_verified_absent',
        'disposable_instructions_cleanup_verified',
        'zero_mutation_verified',
        'baseline_fingerprint_equal',
        'public_rows_schema_roles_equal',
        'auth_rows_excluded',
    )
    for field in required_true:
        if cleanup.get(field) is not True:
            problems.append(f'cleanup.{field} must be True')
    if cleanup.get('raw_snapshots_remaining') != 0:
        problems.append('cleanup.raw_snapshots_remaining must be 0')
    if cleanup.get('recovery_state_retained') is not False:
        problems.append('cleanup.recovery_state_retained must be False')
    if cleanup.get('recovery_state_error'):
        problems.append('cleanup.recovery_state_error must be empty')


def _recompute_bundle_target_gates(
    *,
    per_cycle_statuses: list[dict],
    any_unknown: bool,
    any_fail_common: bool,
) -> dict:
    def _aggregate_target(key: str, *, allow_not_run_owner: bool = False) -> str:
        if any_unknown:
            return 'UNKNOWN'
        if any_fail_common:
            return 'FAIL'
        statuses = []
        for idx, cdict in enumerate(per_cycle_statuses):
            cnum = idx + 1
            for ep_name in ALLOWED_EPOCHS:
                st = (cdict.get(ep_name) or {}).get(key, 'FAIL')
                if st == 'UNKNOWN':
                    return 'UNKNOWN'
                if st == 'FAIL':
                    return 'FAIL'
                if ep_name == 'baseline' and cnum == 1:
                    if st not in ('PASS', 'NOT_RUN_LAZY'):
                        return 'FAIL'
                elif allow_not_run_owner and ep_name == 'owner_active':
                    if st not in ('PASS', 'NOT_RUN'):
                        return 'FAIL'
                else:
                    if st != 'PASS':
                        return 'FAIL'
                statuses.append((ep_name, st))
        if allow_not_run_owner:
            owner_sts = [st for ep, st in statuses if ep == 'owner_active']
            if all(st == 'PASS' for st in owner_sts):
                return 'PASS'
            if all(st == 'NOT_RUN' for st in owner_sts):
                return 'NOT_RUN'
            return 'FAIL'
        return 'PASS'

    sp_gate = _aggregate_target('session_provider')
    cp_core_gate = _aggregate_target('club_provider_core')
    cp_bank_gate = _aggregate_target('club_provider_bank_account', allow_not_run_owner=True)

    if 'UNKNOWN' in (sp_gate, cp_core_gate, cp_bank_gate):
        overall = 'UNKNOWN'
    elif 'FAIL' in (sp_gate, cp_core_gate, cp_bank_gate):
        overall = 'FAIL'
    elif sp_gate == 'PASS' and cp_core_gate == 'PASS' and cp_bank_gate == 'PASS':
        overall = 'PASS'
    elif sp_gate == 'PASS' and cp_core_gate == 'PASS' and cp_bank_gate == 'NOT_RUN':
        overall = 'PARTIAL_CLUB_BANK_NOT_RUN'
    else:
        overall = 'NOT_RUN'

    return {
        'session_listener_gate': sp_gate,
        'club_core_listener_gate': cp_core_gate,
        'club_bank_account_gate': cp_bank_gate,
        'session_club_listener_gate': overall,
    }


def verify(
    evidence_dir: Path | str,
    *,
    build_dir: Path | str | None = None,
    repo_root: Path = ROOT,
    require_bank_account: bool = False,
) -> tuple[list[str], dict]:
    """Strict read-only auditor for 2-cycle Auth -> Session/Club listener-graph evidence bundles."""
    edir = Path(evidence_dir)
    fail_assessment = {
        'session_listener_gate': 'FAIL',
        'club_core_listener_gate': 'FAIL',
        'club_bank_account_gate': 'FAIL',
        'session_club_listener_gate': 'FAIL',
        'claim_scope': CLAIM_SCOPE,
        'observation_mode': OBSERVATION_MODE,
        'atomic_claim': False,
    }
    if not edir.is_dir():
        return ['evidence_dir_missing'], fail_assessment

    before = pi_verifier._digests(edir)
    problems: list[str] = []

    for name in pi_verifier.REQUIRED_FILES:
        p = edir / name
        if not p.is_file() or pi_verifier._is_link(p):
            problems.append(f'missing_required_file:{name}')

    for p in Path(repo_root).rglob('*'):
        if p.is_file() and not pi_verifier._is_link(p) and p.suffix in pi_verifier.RAW_HEAP_SUFFIXES:
            problems.append(f'raw_heap_artifact_in_repo:{p.name}')

    for p in pi_verifier._bundle_entries(edir):
        if p.suffix in pi_verifier.RAW_HEAP_SUFFIXES:
            problems.append(f'raw_heap_artifact_in_bundle:{p.name}')

    pi_verifier._check_manifest(edir, problems)

    texts: dict[str, str] = {}
    for p in pi_verifier._bundle_entries(edir):
        if pi_verifier._is_link(p) or not p.is_file():
            continue
        label = p.relative_to(edir).as_posix()
        text = pi_verifier._read_text(p, label, problems)
        if text is not None:
            texts[label] = text

    for label, text in sorted(texts.items()):
        for pat, desc in pi_verifier.SECRET_PATTERNS:
            if re.search(pat, text):
                problems.append(f'{label}_contains_secret:{desc}')
        for pat in FORBIDDEN_SESSION_CLUB_CLAIMS:
            if re.search(pat, text, re.IGNORECASE):
                problems.append(f'{label}_makes_forbidden_whole_provider_claim')

    summary = None
    if 'summary.json' in texts:
        try:
            summary = json.loads(texts['summary.json'])
        except json.JSONDecodeError:
            problems.append('summary_json_invalid')

    if not isinstance(summary, dict):
        problems.append('summary_not_dict')
        if before != pi_verifier._digests(edir):
            problems.append('audit_modified_bundle')
        return problems, {**fail_assessment, 'problem_count': len(problems)}

    if summary.get('status') != 'RUN':
        problems.append('summary_status_not_run')
    if summary.get('git_dirty') is True:
        problems.append('summary_git_dirty_true')
    if not pi_verifier.SHA1.fullmatch(str(summary.get('tested_source_sha') or '')):
        problems.append('summary_missing_tested_source_sha')
    if summary.get('same_document_across_cycles') is not True:
        problems.append('same_document_across_cycles_not_true')

    pi_verifier._check_build(summary, problems)
    _check_bundle_cleanup(summary, problems)

    # Check redactions / no leaked private UUID markers
    sent_meta = summary.get('sentinels') or {}
    if isinstance(sent_meta, dict):
        for sname, sinfo in sent_meta.items():
            if not isinstance(sinfo, dict):
                continue
            if 'value' in sinfo:
                problems.append(f'sentinel_publishes_raw_value:{sname}')
            slen = sinfo.get('length')
            shex = sinfo.get('sha256_12')
            if isinstance(slen, int) and slen > 0 and pi_verifier.HEX12.fullmatch(str(shex or '')):
                for label, text in sorted(texts.items()):
                    hit = any(
                        hashlib.sha256(text[st:st + slen].encode('utf-8')).hexdigest()[:12] == shex
                        for st in range(max(0, len(text) - slen + 1))
                    )
                    if hit:
                        problems.append(f'{label}_leaked_raw_sentinel:{sname}')

    main_sha = (((summary.get('environment') or {}).get('build') or {}).get('artifacts') or {}).get('main.dart.js')
    eff_build_dir = Path(build_dir) if build_dir is not None else (repo_root / 'build' / 'web')
    recomputed_binding = extract_listener_source_binding(eff_build_dir, expected_main_js_sha=main_sha)
    if not recomputed_binding.get('ok'):
        problems.append(f"source_binding_recompute_failed:{recomputed_binding.get('error')}")
        if before != pi_verifier._digests(edir):
            problems.append('audit_modified_bundle')
        return problems, {**fail_assessment, 'problem_count': len(problems)}

    recorded_binding = summary.get('listener_graph_binding')
    if not isinstance(recorded_binding, dict) or recorded_binding.get('listener_binding_sha256') != recomputed_binding.get('listener_binding_sha256'):
        problems.append('summary_listener_graph_binding_mismatch')

    if 'source_binding.json' in texts:
        try:
            companion_b = json.loads(texts['source_binding.json'])
            if not isinstance(companion_b, dict) or companion_b.get('listener_binding_sha256') != recomputed_binding.get('listener_binding_sha256'):
                problems.append('companion_source_binding_mismatch')
        except json.JSONDecodeError:
            problems.append('companion_source_binding_invalid_json')
    else:
        problems.append('missing_source_binding_json')

    cycles = summary.get('cycles') or []
    per_cycle_statuses: list[dict] = []
    cycle_origins: list[float] = []
    any_unknown = False
    any_fail_common = False

    if not isinstance(cycles, list) or len(cycles) != 2:
        problems.append('expected_2_cycles')
        any_fail_common = True
    else:
        for idx, (exp_num, exp_actor) in enumerate(EXPECTED_CYCLE_ACTORS):
            cyc = cycles[idx]
            if not isinstance(cyc, dict) or cyc.get('cycle') != exp_num or cyc.get('actor') != exp_actor:
                problems.append(f'cycle_{idx}_identity_mismatch')
                any_fail_common = True
                continue
            if cyc.get('same_document') is not True:
                problems.append(f'c{exp_num}_same_document_not_true')
                any_fail_common = True
            cyc_origin = cyc.get('time_origin')
            if not base_graph._is_valid_time_origin(cyc_origin):
                problems.append(f'c{exp_num}_invalid_time_origin')
                any_fail_common = True
            else:
                cycle_origins.append(cyc_origin)

            epochs = cyc.get('epochs') or {}
            if not isinstance(epochs, dict) or set(epochs.keys()) != set(ALLOWED_EPOCHS):
                problems.append(f'c{exp_num}_epochs_mismatch')
                any_fail_common = True
                continue

            owner_ep_lg = (epochs.get('owner_active') or {}).get('listener_graph') or {}
            prev_owner_ids = extract_owner_field_object_ids(owner_ep_lg, recomputed_binding)
            for holder_label, holder in (
                (f'c{exp_num}', cyc),
                (f'c{exp_num}_owner_active', epochs.get('owner_active')),
                (f'c{exp_num}_owner_active_lg', owner_ep_lg),
                (f'c{exp_num}_post_actor', epochs.get('post_actor')),
                (f'c{exp_num}_post_actor_lg', (epochs.get('post_actor') or {}).get('listener_graph')),
            ):
                if not isinstance(holder, dict):
                    continue
                for claim_key in ('previous_owner_field_ids', 'owner_field_ids', 'owner_field_object_ids'):
                    if claim_key in holder and holder.get(claim_key) != prev_owner_ids:
                        problems.append(f'{holder_label}_claimed_{claim_key}_mismatch')

            cyc_statuses: dict[str, dict] = {}
            for ep_name in ALLOWED_EPOCHS:
                ep_scan = epochs.get(ep_name) or {}
                lg_rec = ep_scan.get('listener_graph')
                if not isinstance(lg_rec, dict):
                    problems.append(f'c{exp_num}_{ep_name}_missing_listener_graph')
                    any_fail_common = True
                    continue
                if lg_rec.get('snapshot_sha256_12') != ep_scan.get('sha256_12'):
                    problems.append(f'c{exp_num}_{ep_name}_snapshot_sha_mismatch')
                ep_origin = ep_scan.get('time_origin')
                if not base_graph._is_valid_time_origin(ep_origin):
                    problems.append(f'c{exp_num}_{ep_name}_invalid_epoch_time_origin')
                elif base_graph._is_valid_time_origin(cyc_origin) and ep_origin != cyc_origin:
                    problems.append(f'c{exp_num}_{ep_name}_time_origin_mismatch')

                ep_problems, target_status = evaluate_session_club_record(
                    lg_rec,
                    binding=recomputed_binding,
                    epoch=ep_name,
                    cycle_num=exp_num,
                    actor=exp_actor,
                    expected_time_origin=ep_origin,
                    require_bank_account=require_bank_account,
                    previous_owner_field_ids=prev_owner_ids if ep_name == 'post_actor' else None,
                )
                for p in ep_problems:
                    problems.append(f'c{exp_num}_{ep_name}:{p}')

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
                _, cdp_unk, _, _ = _check_cdp_block(lg_rec.get('cdp_observations'))
                ep_unknown = bool(lg_rec.get('ambiguous_layout') or lg_rec.get('caps_exceeded') or slot_ambig or cdp_unk)
                if ep_unknown:
                    any_unknown = True

                recomputed_ep_verdict = _decide_epoch_verdict(target_status, unknown_flags=ep_unknown)
                allowed_ep = ('NOT_RUN_LAZY', 'PASS') if (exp_num == 1 and ep_name == 'baseline') else ('PASS',)
                if recomputed_ep_verdict not in allowed_ep:
                    problems.append(f'c{exp_num}_{ep_name}_recomputed_verdict:{recomputed_ep_verdict}')
                cyc_statuses[ep_name] = target_status
            per_cycle_statuses.append(cyc_statuses)

        if len(cycle_origins) == 2 and cycle_origins[0] != cycle_origins[1]:
            problems.append('time_origin_changed_across_cycles')
            any_fail_common = True

    if len(per_cycle_statuses) != 2:
        any_fail_common = True

    recomputed_gates = _recompute_bundle_target_gates(
        per_cycle_statuses=per_cycle_statuses,
        any_unknown=any_unknown,
        any_fail_common=any_fail_common,
    )

    if require_bank_account and recomputed_gates['club_bank_account_gate'] != 'PASS':
        problems.append(f"require_bank_account_failed:{recomputed_gates['club_bank_account_gate']}")

    sc_assess = summary.get('session_club_assessment')
    if not isinstance(sc_assess, dict):
        problems.append('missing_session_club_assessment')
    else:
        if sc_assess.get('claim_scope') != CLAIM_SCOPE:
            problems.append('assessment_claim_scope_mismatch')
        if sc_assess.get('observation_mode') != OBSERVATION_MODE:
            problems.append('assessment_observation_mode_mismatch')
        if sc_assess.get('atomic_claim') is not False:
            problems.append('assessment_atomic_claim_must_be_false')
        for gkey in ('session_listener_gate', 'club_core_listener_gate', 'club_bank_account_gate'):
            if sc_assess.get(gkey) != recomputed_gates[gkey]:
                problems.append(f'forged_or_mismatched_{gkey}:reported={_sanitize_target_gate(sc_assess.get(gkey))}')
        if sc_assess.get('session_club_listener_gate') != recomputed_gates['session_club_listener_gate']:
            problems.append(
                f"forged_or_mismatched_overall_gate:reported={_sanitize_overall_gate(sc_assess.get('session_club_listener_gate'))}"
            )

    expected_summary_verdict = 'PASS' if recomputed_gates['session_club_listener_gate'] == 'PASS' else (
        'PARTIAL_NOT_RUN' if recomputed_gates['session_club_listener_gate'] == 'PARTIAL_CLUB_BANK_NOT_RUN' else 'FAIL'
    )
    if summary.get('verdict') != expected_summary_verdict:
        problems.append(f'summary_verdict_mismatch:{_sanitize_overall_gate(summary.get("verdict"))}')

    # Enforce honest PASS gate separation: overall PASS strictly forbids club_bank NOT_RUN
    if summary.get('verdict') == 'PASS' and recomputed_gates['club_bank_account_gate'] != 'PASS':
        problems.append('summary_verdict_cannot_be_pass_with_unrun_club_bank')

    if before != pi_verifier._digests(edir):
        problems.append('audit_modified_bundle')

    final_overall_gate = 'FAIL' if problems else recomputed_gates['session_club_listener_gate']
    assessment = {
        **recomputed_gates,
        'session_club_listener_gate': final_overall_gate,
        'verified_ok': not problems,
        'claim_scope': CLAIM_SCOPE,
        'observation_mode': OBSERVATION_MODE,
        'atomic_claim': False,
        'problem_count': len(problems),
    }
    return problems, assessment


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Finite AuthProvider -> SessionProvider/ClubProvider listener-graph CLI')
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
    p_cdp.add_argument('--cycle', type=int, default=None)
    p_cdp.add_argument('--actor', default=None)
    p_cdp.add_argument('--time-origin', type=float, default=None)
    p_cdp.add_argument('--previous-owner-ids', default=None)
    p_cdp.add_argument('--require-bank-account', action='store_true')

    p_ver = sub.add_parser('verify')
    p_ver.add_argument('evidence_dir')
    p_ver.add_argument('--build-dir', default=None)
    p_ver.add_argument('--require-bank-account', action='store_true')

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
        binding = json.loads(base_graph._read_bounded_bytes(Path(args.binding)).decode('utf-8'))
        res = _normalize_for_scan_cache(raw, binding=binding, epoch=args.epoch)
        text = json.dumps(res, indent=2) + '\n'
        if args.out:
            Path(args.out).write_text(text, encoding='utf-8')
        else:
            sys.stdout.write(text)
        return 0 if res.get('structure_ok') else 1

    if args.cmd == 'apply-cdp':
        prescan = json.loads(base_graph._read_bounded_bytes(Path(args.prescan)).decode('utf-8'))
        binding = json.loads(base_graph._read_bounded_bytes(Path(args.binding)).decode('utf-8'))
        cdp_obs = json.loads(base_graph._read_bounded_bytes(Path(args.cdp)).decode('utf-8'))
        prev_ids = json.loads(base_graph._read_bounded_bytes(Path(args.previous_owner_ids)).decode('utf-8')) if args.previous_owner_ids else None
        res = apply_cdp_to_cached_prescan(
            prescan,
            binding=binding,
            epoch=args.epoch,
            cycle_num=args.cycle,
            actor=args.actor,
            cdp_observations=cdp_obs,
            time_origin=args.time_origin,
            require_bank_account=args.require_bank_account,
            previous_owner_field_ids=prev_ids,
        )
        sys.stdout.write(json.dumps(res, indent=2) + '\n')
        return 0

    if args.cmd == 'verify':
        problems, assessment = verify(
            Path(args.evidence_dir),
            build_dir=Path(args.build_dir) if args.build_dir else None,
            require_bank_account=args.require_bank_account,
        )
        out = {'ok': not problems, 'problems': problems, 'assessment': assessment}
        sys.stdout.write(json.dumps(out, indent=2) + '\n')
        return 0 if not problems else 1

    return 2


if __name__ == '__main__':
    raise SystemExit(main())
