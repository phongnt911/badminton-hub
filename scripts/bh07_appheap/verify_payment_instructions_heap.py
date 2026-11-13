"""Read-only evidence auditor for BH-07 V2b PaymentInstructions synthetic heap bundles.

Preserves existing `verify_evidence.py` and historical bundles untouched.
Validates:
- Bundle file completeness, LF-only UTF-8 without BOM, no symlinks/junctions, exact `hashes.sha256`.
- No raw `.heapsnapshot` / heap dumps in repo or bundle; no credentials or raw sentinel UUIDs.
- Clean git provenance, profile build provenance (`mode == 'profile'`, full artifact SHA-256 + `served_match`),
  and explicit provenance when reusing a served build.
- Unique 2 cycles (`1: cohost`, `2: member`), same-document `time_origin` stability across cycles,
  and all 4 required epochs per cycle (`baseline`, `owner_active`, `post_logout`, `post_actor`).
- `heap_oracle.py` `derive_expectations` + `decide(..., strict=True)` PASS.
- Both `canary_instr_a` and `canary_instr_b` loaded & strongly reachable in BOTH `owner_active` epochs,
  absent & unreachable in `baseline`, `post_logout`, `post_actor` (unknown/error/None fails closed).
- Disposable instructions cleanup receipt, zero payment/ledger/audit/operation mutations, and DB baseline
  fingerprint equality (excluding documented Auth state only). No `disposable_bank_*`/`disposable_ledger_*` keys.
- Honest retaining-path attribution assessment: distinguishes V8 root reachability vs DTO-level attribution.
  Missing app-path attribution cannot certify `PaymentInstructions` coverage PASS (leaves gate `UNKNOWN/NOT_RUN`
  with narrow `PASS_NARROW_RPC_PAYLOAD_ONLY` scope, and fails closed if `--require-dto-attribution` is passed).
"""
import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import heap_oracle  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = 'hashes.sha256'
REQUIRED_FILES = ('summary.json', 'report.md', 'run.log', MANIFEST)
EPOCHS = ('baseline', 'owner_active', 'post_logout', 'post_actor')
EXPECTED_ACTORS = {1: 'cohost', 2: 'member'}
REQUIRED_CANARIES = ('canary_instr_a', 'canary_instr_b')
FRAME_RE = re.compile(r'^([a-z_]+)(?::(.*))? -> (.+)$')
STRING_CHILD_TYPES = {'string', 'concatenated string', 'sliced string'}
CONTAINER_CHILD_TYPES = {'object', 'array'}
PROVIDER_HOLDER_EDGE = '_provider$_value'
VALID_MAP_ROOT_PROPS = {'_strings', '_first', '_last', '_nums', '_rest'}
VALID_MAP_LINK_PROPS = {'_next', '_previous'}
MAX_CONSTRUCTOR_SNIPPET_BYTES = 32768
MAX_SOURCE_BINDING_BYTES = 65536
FORBIDDEN_DTO_LABEL_WORDS = ('xmlhttprequest', 'responsetext', 'script', 'xhr')
RAW_HEAP_SUFFIXES = ('.heapsnapshot', '.heapprofile', '.heaptimeline')
SECRET_PATTERNS = (
    (r'eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}', 'JWT token'),
    (r'bh07-http-pass', 'test account password'),
    (r'SERVICE_ROLE_KEY|SUPABASE_ANON_KEY\s*=', 'service/anon key name with value'),
    (r'postgresql://[^\s"]+:[^\s"]+@', 'database URL with credentials'),
)
SOURCE_SECRET_PATTERNS = SECRET_PATTERNS + (
    (r'canary_instr_[ab]', 'raw canary marker'),
)
FORBIDDEN_MODEL_CLAIMS = (
    r'entire[_\s-]+model[_\s-]+clean',
    r'full[_\s-]+paymentinstructions[_\s-]+model[_\s-]+clean',
    r'all[_\s-]+fields[_\s-]+clean',
)
HEX12 = re.compile(r'[0-9a-f]{12}')
HEX64 = re.compile(r'[0-9a-f]{64}')
SHA1 = re.compile(r'[0-9a-f]{40}')
MANIFEST_LINE = re.compile(r'([0-9a-f]{64})  (.+)')


def _sha256_file(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as fp:
        for chunk in iter(lambda: fp.read(1 << 20), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _is_link(path):
    if path.is_symlink():
        return True
    junction = getattr(path, 'is_junction', None)
    return bool(junction and junction())


def _bundle_entries(evidence_dir):
    return sorted(evidence_dir.rglob('*'), key=lambda p: p.relative_to(evidence_dir).as_posix())


def _digests(evidence_dir):
    out = {}
    for path in _bundle_entries(evidence_dir):
        name = path.relative_to(evidence_dir).as_posix()
        if _is_link(path):
            out[name] = 'link'
        elif path.is_dir():
            out[name] = 'dir'
        else:
            out[name] = _sha256_file(path)
    return out


def _read_text(path, label, problems):
    data = path.read_bytes()
    if data.startswith(b'\xef\xbb\xbf'):
        problems.append(f'{label} has a UTF-8 BOM')
    if b'\r' in data:
        problems.append(f'{label} is not LF-only: it contains a CR byte')
    try:
        return data.decode('utf-8')
    except UnicodeDecodeError as exc:
        problems.append(f'{label} is not valid UTF-8: {exc}')
        return None


def _check_manifest(evidence_dir, problems):
    manifest_path = evidence_dir / MANIFEST
    text = _read_text(manifest_path, MANIFEST, problems)
    if text is None:
        return
    entries = {}
    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        match = MANIFEST_LINE.fullmatch(line)
        if not match:
            problems.append(f'{MANIFEST}:{number} malformed manifest line')
            continue
        digest, name = match.groups()
        unsafe = (name.startswith('/') or '\\' in name or ':' in name
                  or any(part in ('..', '') for part in name.split('/')))
        if unsafe or name == MANIFEST or name in entries:
            problems.append(f'{MANIFEST}:{number} invalid or duplicate path: {name}')
            continue
        entries[name] = digest

    files = set()
    for path in _bundle_entries(evidence_dir):
        name = path.relative_to(evidence_dir).as_posix()
        if _is_link(path):
            problems.append(f'bundle contains symlink/junction: {name}')
            continue
        if evidence_dir.resolve() not in path.resolve().parents:
            problems.append(f'bundle entry resolves outside bundle: {name}')
            continue
        if path.is_file():
            files.add(name)

    for name in sorted(set(entries) - files):
        problems.append(f'manifest lists missing file: {name}')
    for name in sorted(files - set(entries) - {MANIFEST}):
        problems.append(f'bundle file missing from manifest: {name}')
    for name, digest in sorted(entries.items()):
        if name in files and _sha256_file(evidence_dir / name) != digest:
            problems.append(f'hash mismatch: {name}')


def _check_build(summary, problems):
    env = summary.get('environment')
    build = env.get('build') if isinstance(env, dict) else None
    if not isinstance(build, dict):
        problems.append('summary.json environment.build must be an object')
        return
    if build.get('mode') != 'profile':
        problems.append(f'build.mode must be profile, got {build.get("mode")!r}')
    if build.get('reused') is True and build.get('explicit_provenance_verified') is not True:
        problems.append('reused build requires explicit_provenance_verified=True')
    if not build.get('started_at'):
        problems.append('build provenance lacks started_at')
    if build.get('served_match') is not True:
        problems.append('build.served_match must be True')
    artifacts = build.get('artifacts')
    if not isinstance(artifacts, dict) or not artifacts:
        problems.append('build provenance lacks artifacts')
    else:
        for req in ('index.html', 'main.dart.js'):
            if req not in artifacts:
                problems.append(f'build artifacts missing {req}')
        for name, digest in artifacts.items():
            if not isinstance(digest, str) or not HEX64.fullmatch(digest):
                problems.append(f'build artifact hash invalid for {name}')


def _check_contract(summary, problems):
    if summary.get('coverage_profile') != 'payment_instructions':
        problems.append(f'coverage_profile must be payment_instructions, got {summary.get("coverage_profile")!r}')
    contract = summary.get('instructions_coverage_contract')
    if not isinstance(contract, dict):
        problems.append('missing instructions_coverage_contract object')
        return
    expected = {
        'version': '1.0',
        'scope': 'synthetic_receiver_snapshot_map_values_only',
        'dto': 'PaymentInstructions',
        'provider_field': 'FinanceProvider._instructions',
        'actor_isolation': 'owner_only_disposable_club',
        'payment_mutation_forbidden': True,
    }
    for k, v in expected.items():
        if contract.get(k) != v:
            problems.append(f'instructions_coverage_contract.{k} must be {v!r}, got {contract.get(k)!r}')
    reqs = contract.get('required_owner_load')
    if not isinstance(reqs, list) or set(reqs) != set(REQUIRED_CANARIES):
        problems.append(f'required_owner_load must be {list(REQUIRED_CANARIES)}, got {reqs!r}')
    unattr = contract.get('rendered_strings_unattributed')
    if not isinstance(unattr, list) or set(unattr) != {'bank_code', 'account_number', 'account_name', 'reference'}:
        problems.append(f'rendered_strings_unattributed mismatch: {unattr!r}')


def _check_sentinels_and_leaks(summary, texts, problems):
    sentinels = summary.get('sentinels')
    if not isinstance(sentinels, dict):
        problems.append('summary.json sentinels must be an object')
        return
    for name in ('probe', *REQUIRED_CANARIES):
        meta = sentinels.get(name)
        if not isinstance(meta, dict):
            problems.append(f'missing sentinel metadata: {name}')
            continue
        if 'value' in meta:
            problems.append(f'sentinel {name} publishes raw value')
        if meta.get('available') is not True:
            problems.append(f'sentinel {name} must have available=True')
        if meta.get('rendered') is not False or meta.get('distinctive') is not True:
            problems.append(f'sentinel {name} must have rendered=False, distinctive=True')
        expected_scope = 'control' if name == 'probe' else 'finance'
        if meta.get('scope') != expected_scope:
            problems.append(f'sentinel {name} scope must be {expected_scope!r}')
        length = meta.get('length')
        digest = meta.get('sha256_12')
        if name in REQUIRED_CANARIES and length != 36:
            problems.append(f'sentinel {name} length must be 36, got {length!r}')
        if not isinstance(length, int) or length <= 0 or not HEX12.fullmatch(str(digest or '')):
            problems.append(f'sentinel {name} lacks valid length/sha256_12')
            continue
        for label, text in sorted(texts.items()):
            hit = any(
                hashlib.sha256(text[start:start + length].encode('utf-8')).hexdigest()[:12] == digest
                for start in range(max(0, len(text) - length + 1))
            )
            if hit:
                problems.append(f'{label} publishes the raw value of sentinel {name}')


def _is_valid_time_origin(val):
    return type(val) in (int, float) and math.isfinite(val) and val > 0


def _check_cycles(summary, problems):
    if summary.get('same_document_across_cycles') is not True:
        problems.append(f'same_document_across_cycles must be True, got {summary.get("same_document_across_cycles")!r}')

    cycles = summary.get('cycles')
    if not isinstance(cycles, list) or len(cycles) != 2:
        problems.append(f'summary must contain exactly 2 cycles, got {len(cycles) if isinstance(cycles, list) else type(cycles).__name__}')
        return
    seen_cycles = set()
    time_origins = []
    for cycle in cycles:
        if not isinstance(cycle, dict):
            problems.append('cycle entry must be an object')
            continue
        c_num = cycle.get('cycle')
        if type(c_num) is not int or c_num not in EXPECTED_ACTORS:
            problems.append(f'invalid cycle number: {c_num!r}')
            continue
        if c_num in seen_cycles:
            problems.append(f'duplicate cycle number: {c_num}')
            continue
        seen_cycles.add(c_num)
        if cycle.get('actor') != EXPECTED_ACTORS[c_num]:
            problems.append(f'cycle {c_num} actor must be {EXPECTED_ACTORS[c_num]!r}, got {cycle.get("actor")!r}')
        if cycle.get('same_document') is not True:
            problems.append(f'cycle {c_num} same_document must be True')
        origin = cycle.get('time_origin')
        if not _is_valid_time_origin(origin):
            problems.append(f'cycle {c_num} lacks valid numeric time_origin: {origin!r}')
        else:
            time_origins.append(origin)

        epochs = cycle.get('epochs')
        if not isinstance(epochs, dict) or set(epochs.keys()) != set(EPOCHS):
            problems.append(f'cycle {c_num} must contain exact epochs {EPOCHS}')
            continue

        for ep_name in EPOCHS:
            scan = epochs.get(ep_name)
            if not isinstance(scan, dict) or scan.get('ok') is not True:
                problems.append(f'cycle {c_num} {ep_name}: usable scan missing')
                continue
            ep_origin = scan.get('time_origin')
            if not _is_valid_time_origin(ep_origin):
                problems.append(f'cycle {c_num} {ep_name}: lacks valid numeric time_origin: {ep_origin!r}')
            elif _is_valid_time_origin(origin) and ep_origin != origin:
                problems.append(f'cycle {c_num} {ep_name}: time_origin mismatch {ep_origin} != {origin}')
            for p in heap_oracle.scan_problems(scan, require_paths=True):
                problems.append(f'cycle {c_num} {ep_name}: {p}')
            sent = scan.get('sentinels') or {}
            paths = scan.get('paths') or {}
            for cname in REQUIRED_CANARIES:
                rec = sent.get(cname) or {}
                prec = paths.get(cname) or {}
                if ep_name == 'owner_active':
                    if rec.get('present') is not True:
                        problems.append(f'cycle {c_num} owner_active: {cname} missing/not present')
                    if prec.get('reachable') is not True:
                        problems.append(f'cycle {c_num} owner_active: {cname} not reachable from GC root')
                else:
                    if rec.get('present') is not False:
                        problems.append(f'cycle {c_num} {ep_name}: {cname} expected present=False, got {rec.get("present")!r}')
                    if prec.get('reachable') is not False:
                        problems.append(f'cycle {c_num} {ep_name}: {cname} expected reachable=False, got {prec.get("reachable")!r}')

        expectations = heap_oracle.derive_expectations(epochs)
        verdict = heap_oracle.decide(epochs, expectations, True, 'profile', strict=True)
        if verdict.get('verdict') != 'PASS':
            problems.append(f'cycle {c_num} oracle verdict failed: {verdict.get("findings")}')

    if seen_cycles != set(EXPECTED_ACTORS):
        problems.append(f'cycles missing expected numbers {sorted(EXPECTED_ACTORS)}')
    if len(time_origins) == 2 and time_origins[0] != time_origins[1]:
        problems.append(f'time_origin changed across cycles: {time_origins[0]} != {time_origins[1]}')


def _check_cleanup(summary, problems):
    cleanup = summary.get('cleanup')
    if not isinstance(cleanup, dict):
        problems.append('summary.json cleanup must be an object')
        return
    for forbidden_prefix in ('disposable_bank_', 'disposable_ledger_'):
        if any(k.startswith(forbidden_prefix) for k in cleanup):
            problems.append(f'cleanup must not contain {forbidden_prefix}* keys')
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
            problems.append(f'cleanup.{field} must be True, got {cleanup.get(field)!r}')
    if cleanup.get('raw_snapshots_remaining') != 0:
        problems.append(f'cleanup.raw_snapshots_remaining must be 0, got {cleanup.get("raw_snapshots_remaining")!r}')
    if cleanup.get('recovery_state_retained') is not False:
        problems.append(
            f'cleanup.recovery_state_retained must be False, got {cleanup.get("recovery_state_retained")!r}'
        )
    if cleanup.get('recovery_state_error'):
        problems.append(
            f'cleanup.recovery_state_error must be absent/empty, got {cleanup.get("recovery_state_error")!r}'
        )

    sentinels = summary.get('sentinels') or {}
    for cname in REQUIRED_CANARIES:
        meta_sha = (sentinels.get(cname) or {}).get('sha256_12')
        rec_sha = cleanup.get(f'{cname}_sha256_12')
        if meta_sha and rec_sha and meta_sha != rec_sha:
            problems.append(f'cleanup {cname}_sha256_12 {rec_sha!r} mismatches summary.sentinels {meta_sha!r}')


def _parse_frame(frame):
    if not isinstance(frame, str) or frame == '...':
        return None
    m = FRAME_RE.fullmatch(frame)
    if not m:
        return None
    kind, label, child = m.groups()
    return {'kind': kind, 'label': label or '', 'child': child}


def _canonical_json(value):
    if isinstance(value, dict):
        items = ','.join(
            f'{json.dumps(k)}:{_canonical_json(value[k])}'
            for k in sorted(value.keys())
        )
        return '{' + items + '}'
    if isinstance(value, list):
        return '[' + ','.join(_canonical_json(v) for v in value) + ']'
    return json.dumps(value)


def _sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def _find_closing_brace(text, open_index, max_bytes=MAX_CONSTRUCTOR_SNIPPET_BYTES):
    depth = 0
    limit = min(len(text), open_index + max_bytes + 1)
    i = open_index
    while i < limit:
        ch = text[i]
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                return i
        elif ch in ("'", '"', '`'):
            quote = ch
            i += 1
            while i < limit:
                if text[i] == '\\':
                    i += 2
                    continue
                if text[i] == quote:
                    break
                i += 1
        elif ch == '/' and i + 1 < limit:
            nxt = text[i + 1]
            if nxt == '/':
                i += 2
                while i < limit and text[i] != '\n':
                    i += 1
            elif nxt == '*':
                i += 2
                while i + 1 < limit and not (text[i] == '*' and text[i + 1] == '/'):
                    i += 1
                i += 1
        i += 1
    return -1


def _executable_source(js_text):
    # Offset-preserving conservative mask: comments/literals are never code proof.
    tokens = re.compile(r'''//[^\r\n]*|/\*[\s\S]*?(?:\*/|$)|"(?:\\[\s\S]|[^"\\])*(?:"|$)|'(?:\\[\s\S]|[^'\\])*(?:'|$)|`(?:\\[\s\S]|[^`\\])*(?:`|$)|/(?:\\[^\r\n]|\[(?:\\[^\r\n]|[^\]\\\r\n])*\]|[^/\\[\r\n])+/[a-z]*''')
    strings = set()

    def mask(match):
        token = match.group()
        if token[0] in ('"', "'") and token[-1] == token[0]:
            strings.add(token[1:-1])
        return re.sub(r'[^\r\n]', ' ', token)

    return tokens.sub(mask, js_text), strings


def extract_js_constructor(js_text, class_name, code=None):
    if code is None:
        code, _ = _executable_source(js_text)
    esc = re.escape(class_name)
    pattern = re.compile(
        rf'(?:^|[,{{\n\r]\s*)({esc}\s*:\s*function(?:\s+{esc})?\s*\(([^)]*)\)\s*\{{)'
    )
    matches = []
    for m in pattern.finditer(code):
        full_header = m.group(1)
        header_start = m.start() + m.group(0).index(full_header)
        open_brace_idx = header_start + len(full_header) - 1
        close_brace_idx = _find_closing_brace(code, open_brace_idx)
        if close_brace_idx < 0:
            continue
        snippet = js_text[header_start:close_brace_idx + 1]
        body = code[open_brace_idx + 1:close_brace_idx]
        params = [s.strip() for s in (m.group(2) or '').split(',') if s.strip()]
        matches.append({
            'name': class_name,
            'params': params,
            'body': body,
            'snippet': snippet,
            'start': header_start,
            'end': close_brace_idx + 1,
            'sha256': _sha256_bytes(snippet.encode('utf-8')),
        })
        if len(matches) > 1:
            return {'ok': False, 'error': f'ambiguous {class_name} constructor definition'}
    if len(matches) != 1:
        return {'ok': False, 'error': f'missing {class_name} constructor definition'}
    return {'ok': True, **matches[0]}


def _parse_constructor_assignments(body):
    receivers = ['this']
    seen_receivers = {'this'}
    for am in re.finditer(r'\b(?:var|let|const)\s+([A-Za-z_$][A-Za-z0-9_$]*)\s*=\s*this\b', body):
        name = am.group(1)
        if name not in seen_receivers:
            seen_receivers.add(name)
            receivers.append(name)
    recv_pat = '|'.join(re.escape(r) for r in receivers)
    chain_re = re.compile(rf'((?:(?:{recv_pat})\.[A-Za-z_$][A-Za-z0-9_$]*\s*=\s*)+)([^;\n\}}]+)')
    prop_re = re.compile(rf'(?:{recv_pat})\.([A-Za-z_$][A-Za-z0-9_$]*)')
    assignments = []
    for cm in chain_re.finditer(body):
        rhs = cm.group(2).strip()
        lhs_group = cm.group(1)
        for pm in prop_re.finditer(lhs_group):
            assignments.append({'prop': pm.group(1), 'rhs': rhs})
    return {'receivers': receivers, 'assignments': assignments}


def _collect_strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from _collect_strings(item)
    elif isinstance(value, dict):
        for val in value.values():
            yield from _collect_strings(val)


def _has_source_secret(snippets):
    for text in snippets:
        if not isinstance(text, str):
            continue
        for pat, _desc in SOURCE_SECRET_PATTERNS:
            if re.search(pat, text):
                return True
    return False


def extract_and_validate_source_binding(build_dir, expected_main_js_sha=None):
    if not build_dir:
        return {'ok': False, 'main_dart_js_sha256': expected_main_js_sha, 'error': 'missing_build_dir'}
    bdir = Path(build_dir)
    if _is_link(bdir) or not bdir.is_dir():
        return {'ok': False, 'main_dart_js_sha256': expected_main_js_sha, 'error': 'build_dir_missing_or_symlink'}
    main_js_path = bdir / 'main.dart.js'
    if _is_link(main_js_path) or not main_js_path.is_file():
        return {'ok': False, 'main_dart_js_sha256': expected_main_js_sha, 'error': 'main_dart_js_missing_or_symlink'}
    raw_bytes = main_js_path.read_bytes()
    actual_sha = _sha256_bytes(raw_bytes)
    if expected_main_js_sha is not None:
        if not isinstance(expected_main_js_sha, str) or not HEX64.fullmatch(expected_main_js_sha) or actual_sha != expected_main_js_sha:
            return {
                'ok': False,
                'main_dart_js_sha256': actual_sha,
                'expected_main_dart_js_sha256': expected_main_js_sha,
                'error': 'main_dart_js_sha256_mismatch',
            }
    try:
        js_text = raw_bytes.decode('utf-8')
    except UnicodeDecodeError as exc:
        return {'ok': False, 'main_dart_js_sha256': actual_sha, 'error': f'main_dart_js_invalid_utf8: {exc}'}

    code, strings = _executable_source(js_text)
    fp_ctor = extract_js_constructor(js_text, 'FinanceProvider', code)
    if not fp_ctor.get('ok'):
        return {'ok': False, 'main_dart_js_sha256': actual_sha, 'error': fp_ctor.get('error')}
    pi_ctor = extract_js_constructor(js_text, 'PaymentInstructions', code)
    if not pi_ctor.get('ok'):
        return {'ok': False, 'main_dart_js_sha256': actual_sha, 'error': pi_ctor.get('error')}

    fp_parsed = _parse_constructor_assignments(fp_ctor['body'])
    repo_fields = list(dict.fromkeys(
        a['prop'] for a in fp_parsed['assignments']
        if re.fullmatch(r'(?:_[A-Za-z0-9_]+\$)?_repository', a['prop'])
    ))
    has_auth = any(a['prop'] == 'auth' for a in fp_parsed['assignments'])
    has_player_id_null = any(
        re.fullmatch(r'(?:_[A-Za-z0-9_]+\$)?_instructionsPlayerId', a['prop']) and a['rhs'] == 'null'
        for a in fp_parsed['assignments']
    )
    has_session_id_null = any(
        re.fullmatch(r'(?:_[A-Za-z0-9_]+\$)?_instructionsSessionId', a['prop']) and a['rhs'] == 'null'
        for a in fp_parsed['assignments']
    )
    instr_candidates = list(dict.fromkeys(
        a['prop'] for a in fp_parsed['assignments']
        if re.fullmatch(r'(?:_[A-Za-z0-9_]+\$)?_instructions', a['prop']) and a['rhs'] == 'null'
    ))
    if len(repo_fields) != 1 or not has_auth or not has_player_id_null or not has_session_id_null or len(instr_candidates) != 1:
        return {'ok': False, 'main_dart_js_sha256': actual_sha, 'error': 'finance_provider_constructor_contract_failed'}
    instructions_field = instr_candidates[0]
    repository_field = repo_fields[0]

    js_without_fp = code[:fp_ctor['start']] + code[fp_ctor['end']:]
    esc_instr = re.escape(instructions_field)
    fp_non_null_assign = re.search(rf'[A-Za-z_$][A-Za-z0-9_$]*\.{esc_instr}\s*=\s*(?!null\b|undefined\b)[^;\n\}}]+', js_without_fp)
    fp_null_reset = re.search(rf'[A-Za-z_$][A-Za-z0-9_$]*\.{esc_instr}\s*=\s*null\b', js_without_fp)
    fp_read = re.search(rf'[A-Za-z_$][A-Za-z0-9_$]*\.{esc_instr}(?![A-Za-z0-9_$])\s*(?:===|!==|[^=])', js_without_fp)
    if (
        not fp_non_null_assign
        or not fp_null_reset
        or not fp_read
        or 'fetchPaymentInstructions' not in code
        or 'get_payment_instructions' not in strings
    ):
        return {'ok': False, 'main_dart_js_sha256': actual_sha, 'error': 'finance_provider_field_use_unverified'}

    pi_parsed = _parse_constructor_assignments(pi_ctor['body'])
    pi_params = set(pi_ctor['params'])
    rs_candidates = list(dict.fromkeys(
        a['prop'] for a in pi_parsed['assignments']
        if re.fullmatch(r'(?:_[A-Za-z0-9_]+\$)?receiverSnapshot', a['prop']) and a['rhs'] in pi_params
    ))
    if len(rs_candidates) != 1:
        return {'ok': False, 'main_dart_js_sha256': actual_sha, 'error': 'payment_instructions_constructor_contract_failed'}
    receiver_snapshot_field = rs_candidates[0]

    js_without_pi = code[:pi_ctor['start']] + code[pi_ctor['end']:]
    esc_rs = re.escape(receiver_snapshot_field)
    pi_read = re.search(rf'[A-Za-z_$][A-Za-z0-9_$]*\.{esc_rs}(?![A-Za-z0-9_$])\s*(?:===|!==|[^=])', js_without_pi)
    if not pi_read or 'receiver_snapshot' not in strings:
        return {'ok': False, 'main_dart_js_sha256': actual_sha, 'error': 'payment_instructions_field_use_unverified'}

    prov_assign = re.search(r'[A-Za-z_$][A-Za-z0-9_$]*\._provider\$_value\s*=\s*[^;,\n}]+', code)
    prov_read = re.search(r'[A-Za-z_$][A-Za-z0-9_$]*\._provider\$_value(?![A-Za-z0-9_$])\s*(?:===|!==|[^=])', code)
    if not prov_assign or not prov_read:
        return {'ok': False, 'main_dart_js_sha256': actual_sha, 'error': 'provider_holder_field_use_unverified'}

    if _has_source_secret([fp_ctor['snippet'], pi_ctor['snippet']]):
        return {'ok': False, 'main_dart_js_sha256': actual_sha, 'error': 'sensitive_pattern_in_source_binding_snippets'}

    core = {
        'finance_provider': {
            'constructor_name': 'FinanceProvider',
            'constructor_sha256': fp_ctor['sha256'],
            'field_use_verified': True,
            'instructions_field': instructions_field,
            'repository_field': repository_field,
        },
        'main_dart_js_sha256': actual_sha,
        'payment_instructions': {
            'constructor_name': 'PaymentInstructions',
            'constructor_sha256': pi_ctor['sha256'],
            'field_use_verified': True,
            'receiver_snapshot_field': receiver_snapshot_field,
        },
        'provider_holder_edge': PROVIDER_HOLDER_EDGE,
    }
    binding_sha = _sha256_bytes(_canonical_json(core).encode('utf-8'))
    sanitized = {'ok': True, **core, 'binding_sha256': binding_sha}
    return {'ok': True, 'sanitized': sanitized}


def _compute_binding_sha(binding):
    core = {
        'finance_provider': binding.get('finance_provider'),
        'main_dart_js_sha256': binding.get('main_dart_js_sha256'),
        'payment_instructions': binding.get('payment_instructions'),
        'provider_holder_edge': binding.get('provider_holder_edge'),
    }
    return _sha256_bytes(_canonical_json(core).encode('utf-8'))


def _validate_binding_metadata(binding, expected_main_js_sha, label, problems):
    if not isinstance(binding, dict) or binding.get('ok') is not True:
        problems.append(f'{label}: missing valid ok=True source_binding')
        return False
    main_sha = binding.get('main_dart_js_sha256')
    if not isinstance(main_sha, str) or not HEX64.fullmatch(main_sha):
        problems.append(f'{label}: invalid main_dart_js_sha256')
        return False
    if expected_main_js_sha and main_sha != expected_main_js_sha:
        problems.append(f'{label}: main_dart_js_sha256 {main_sha} != build artifact {expected_main_js_sha}')
        return False
    if binding.get('provider_holder_edge') != PROVIDER_HOLDER_EDGE:
        problems.append(f'{label}: provider_holder_edge must be {PROVIDER_HOLDER_EDGE!r}')
        return False
    fp = binding.get('finance_provider')
    pi = binding.get('payment_instructions')
    if not isinstance(fp, dict) or not isinstance(pi, dict):
        problems.append(f'{label}: missing finance_provider or payment_instructions metadata')
        return False
    if (
        fp.get('constructor_name') != 'FinanceProvider'
        or fp.get('field_use_verified') is not True
        or not fp.get('instructions_field')
        or not fp.get('repository_field')
        or not HEX64.fullmatch(str(fp.get('constructor_sha256') or ''))
    ):
        problems.append(f'{label}: invalid finance_provider binding fields')
        return False
    if (
        pi.get('constructor_name') != 'PaymentInstructions'
        or pi.get('field_use_verified') is not True
        or not pi.get('receiver_snapshot_field')
        or not HEX64.fullmatch(str(pi.get('constructor_sha256') or ''))
    ):
        problems.append(f'{label}: invalid payment_instructions binding fields')
        return False
    if set(fp.keys()) != {'constructor_name', 'constructor_sha256', 'field_use_verified', 'instructions_field', 'repository_field'}:
        problems.append(f'{label}: unexpected finance_provider keys')
        return False
    if set(pi.keys()) != {'constructor_name', 'constructor_sha256', 'field_use_verified', 'receiver_snapshot_field'}:
        problems.append(f'{label}: unexpected payment_instructions keys')
        return False
    if binding.get('binding_sha256') != _compute_binding_sha(binding):
        problems.append(f'{label}: binding_sha256 mismatch')
        return False
    return True


def _validate_companion_binding_artifact(raw_text, summary_binding, expected_main_js_sha, problems):
    if len(raw_text.encode('utf-8')) > MAX_SOURCE_BINDING_BYTES:
        problems.append('source_binding.json exceeds bounded artifact limit')
        return False
    try:
        doc = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        problems.append(f'source_binding.json invalid JSON: {exc}')
        return False
    if not isinstance(doc, dict) or doc.get('ok') is not True:
        problems.append('source_binding.json must be an ok=True object')
        return False
    if _has_source_secret(_collect_strings(doc)):
        problems.append('source_binding.json contains forbidden secret/canary pattern')
        return False

    fp_full = doc.get('finance_provider')
    pi_full = doc.get('payment_instructions')
    if not isinstance(fp_full, dict) or not isinstance(pi_full, dict):
        problems.append('source_binding.json missing finance_provider or payment_instructions')
        return False

    fp_snippet = fp_full.get('constructor_snippet')
    pi_snippet = pi_full.get('constructor_snippet')
    for cname, snip, expected_sha in (
        ('FinanceProvider', fp_snippet, fp_full.get('constructor_sha256')),
        ('PaymentInstructions', pi_snippet, pi_full.get('constructor_sha256')),
    ):
        if not isinstance(snip, str) or not snip or len(snip.encode('utf-8')) > MAX_CONSTRUCTOR_SNIPPET_BYTES:
            problems.append(f'source_binding.json {cname} constructor_snippet missing or exceeds size limit')
            return False
        if _sha256_bytes(snip.encode('utf-8')) != expected_sha:
            problems.append(f'source_binding.json {cname} constructor_snippet hash mismatch')
            return False
        if not isinstance(full_snip_list := (fp_full if cname == 'FinanceProvider' else pi_full).get('field_use_snippets'), list) or not full_snip_list:
            problems.append(f'source_binding.json {cname} missing field_use_snippets')
            return False
        if any(not isinstance(s, str) or len(s.encode('utf-8')) > 512 for s in full_snip_list):
            problems.append(f'source_binding.json {cname} field_use_snippets invalid/oversized')
            return False

    prov_snips = doc.get('provider_holder_snippets')
    if not isinstance(prov_snips, list) or not prov_snips or any(not isinstance(s, str) or len(s.encode('utf-8')) > 512 for s in prov_snips):
        problems.append('source_binding.json missing valid provider_holder_snippets')
        return False

    normalized = {
        'ok': doc.get('ok'),
        'main_dart_js_sha256': doc.get('main_dart_js_sha256'),
        'provider_holder_edge': doc.get('provider_holder_edge'),
        'finance_provider': {
            k: fp_full.get(k)
            for k in ('constructor_name', 'constructor_sha256', 'field_use_verified', 'instructions_field', 'repository_field')
        },
        'payment_instructions': {
            k: pi_full.get(k)
            for k in ('constructor_name', 'constructor_sha256', 'field_use_verified', 'receiver_snapshot_field')
        },
        'binding_sha256': doc.get('binding_sha256'),
    }
    if not _validate_binding_metadata(normalized, expected_main_js_sha, 'source_binding.json', problems):
        return False
    if summary_binding and summary_binding.get('binding_sha256') != doc.get('binding_sha256'):
        problems.append('source_binding.json binding_sha256 mismatches summary.json attribution_assessment.source_binding')
        return False
    return True


def _has_ordered_dto_retainer_chain(frames, source_binding=None, canary_name=None, path_record=None):
    """Require bound ordered retainer chain: _provider$_value -> bound instructions -> bound receiverSnapshot -> map -> string."""
    if not isinstance(source_binding, dict) or source_binding.get('ok') is not True:
        return False
    fp = source_binding.get('finance_provider') or {}
    pi = source_binding.get('payment_instructions') or {}
    expected_instr = fp.get('instructions_field')
    expected_rs = pi.get('receiver_snapshot_field')
    if (
        source_binding.get('provider_holder_edge') != PROVIDER_HOLDER_EDGE
        or fp.get('field_use_verified') is not True
        or not expected_instr
        or pi.get('field_use_verified') is not True
        or not expected_rs
    ):
        return False

    if not isinstance(frames, list) or len(frames) < 6 or frames[0] != 'root' or '...' in frames:
        return False
    if path_record is not None:
        if path_record.get('reachable') is not True or path_record.get('exact') is not True:
            return False
        if path_record.get('path_len') != len(frames) - 1:
            return False
        expected_p_sha = _sha256_bytes('\n'.join(frames).encode('utf-8'))[:12]
        if path_record.get('path_sha256_12') != expected_p_sha:
            return False

    parsed = [_parse_frame(f) for f in frames[1:]]
    if any(p is None for p in parsed):
        return False
    if any(any(w in f['label'].lower() for w in FORBIDDEN_DTO_LABEL_WORDS) for f in parsed):
        return False

    allowed_canaries = {canary_name} if canary_name else set(REQUIRED_CANARIES)
    for idx in range(len(parsed) - 4):
        holder = parsed[idx]
        step1 = parsed[idx + 1]
        step2 = parsed[idx + 2]
        if (
            holder['kind'] == 'property'
            and holder['label'] == PROVIDER_HOLDER_EDGE
            and holder['child'] == 'object'
            and step1['kind'] == 'property'
            and step1['label'] == expected_instr
            and step1['child'] == 'object'
            and step2['kind'] == 'property'
            and step2['label'] == expected_rs
            and step2['child'] == 'object'
        ):
            suffix = parsed[idx + 3:]
            if len(suffix) < 2:
                continue
            map_root = suffix[0]
            intermediates = suffix[1:-1]
            leaf = suffix[-1]
            if (
                map_root['kind'] != 'property'
                or map_root['child'] != 'object'
                or map_root['label'] not in VALID_MAP_ROOT_PROPS
            ):
                continue
            if leaf['kind'] != 'property' or leaf['label'] != 'hashMapCellValue' or leaf['child'] not in STRING_CHILD_TYPES:
                continue
            if map_root['label'] == '_strings':
                if len(intermediates) != 1:
                    continue
                key_edge = intermediates[0]
                if key_edge['kind'] != 'property' or key_edge['child'] != 'object' or key_edge['label'] not in allowed_canaries:
                    continue
                return True
            if map_root['label'] in ('_first', '_last'):
                if any(f['kind'] != 'property' or f['child'] != 'object' or f['label'] not in VALID_MAP_LINK_PROPS for f in intermediates):
                    continue
                return True
            if any(f['kind'] not in ('property', 'element') or f['child'] not in CONTAINER_CHILD_TYPES for f in intermediates):
                continue
            return True
    return False


def _check_attribution_and_claims(summary, texts, problems, require_dto_attribution=False, build_dir=None):
    for label, text in sorted(texts.items()):
        for pat, desc in ((p, p) for p in FORBIDDEN_MODEL_CLAIMS):
            if re.search(pat, text, re.IGNORECASE):
                problems.append(f'{label} makes forbidden whole-model claim ({desc})')

    attr = summary.get('attribution_assessment')
    if not isinstance(attr, dict):
        problems.append('summary.json missing attribution_assessment object')
        return {'scoped_verdict': 'FAIL', 'payment_instructions_coverage_gate': 'FAIL'}

    if attr.get('root_reachability_measured') is not True:
        problems.append('attribution_assessment.root_reachability_measured must be True')

    dto_proven = attr.get('dto_attribution_proven')
    if type(dto_proven) is not bool:
        problems.append('attribution_assessment.dto_attribution_proven must be a boolean')
        return {'scoped_verdict': 'FAIL', 'payment_instructions_coverage_gate': 'FAIL'}

    expected_main_sha = (((summary.get('environment') or {}).get('build') or {}).get('artifacts') or {}).get('main.dart.js')
    summary_binding = attr.get('source_binding')

    if 'source_binding.json' in texts:
        _validate_companion_binding_artifact(
            texts['source_binding.json'],
            summary_binding if isinstance(summary_binding, dict) and summary_binding.get('ok') is True else None,
            expected_main_sha,
            problems,
        )

    owner_records = []
    for cycle in summary.get('cycles') or []:
        if not isinstance(cycle, dict):
            continue
        owner_ep = (cycle.get('epochs') or {}).get('owner_active') or {}
        paths = owner_ep.get('paths') or {}
        for cname in REQUIRED_CANARIES:
            prec = paths.get(cname) or {}
            owner_records.append((cname, prec))

    if dto_proven:
        attribution_ok = True
        if not _validate_binding_metadata(summary_binding, expected_main_sha, 'attribution_assessment.source_binding', problems):
            attribution_ok = False
        if 'source_binding.json' not in texts:
            problems.append('dto_attribution_proven=True requires source_binding.json companion artifact in bundle')
            attribution_ok = False
        if not build_dir:
            problems.append('dto_attribution_proven=True requires --build-dir with exact main.dart.js for independent validation')
            attribution_ok = False
            recomputed = None
        else:
            recomputed = extract_and_validate_source_binding(build_dir, expected_main_sha)
            if not recomputed.get('ok'):
                problems.append(f'independent --build-dir source binding validation failed: {recomputed.get("error")}')
                attribution_ok = False
            elif isinstance(summary_binding, dict) and recomputed['sanitized'].get('binding_sha256') != summary_binding.get('binding_sha256'):
                problems.append('recomputed main.dart.js source binding mismatches summary attribution_assessment.source_binding')
                attribution_ok = False

        effective_binding = recomputed['sanitized'] if (recomputed and recomputed.get('ok')) else (summary_binding if isinstance(summary_binding, dict) and summary_binding.get('ok') is True else None)
        all_paths_attributed = (
            len(owner_records) == 4
            and all(
                _has_ordered_dto_retainer_chain(
                    prec.get('frames'),
                    source_binding=effective_binding,
                    canary_name=cname,
                    path_record=prec,
                )
                for cname, prec in owner_records
            )
        )
        if not all_paths_attributed:
            problems.append('dto_attribution_proven=True claimed without exact bound ordered retainer chain (_provider$_value -> bound instructions -> bound receiverSnapshot -> map -> string) in all owner_active paths')
            attribution_ok = False
        proven_frames = attr.get('proven_frames')
        if not isinstance(proven_frames, list) or not _has_ordered_dto_retainer_chain(proven_frames, source_binding=effective_binding):
            problems.append('dto_attribution_proven=True requires proven_frames matching exact bound ordered retainer chain')
            attribution_ok = False
        if attr.get('scoped_verdict') != 'PASS_DTO_ATTRIBUTED':
            problems.append(f'scoped_verdict must be PASS_DTO_ATTRIBUTED when dto_attribution_proven=True, got {attr.get("scoped_verdict")!r}')
            attribution_ok = False
        if attr.get('claim_scope') != 'payment_instructions_receiver_snapshot_only':
            problems.append(f'claim_scope must be payment_instructions_receiver_snapshot_only when dto_attribution_proven=True, got {attr.get("claim_scope")!r}')
            attribution_ok = False
        if attr.get('payment_instructions_coverage_gate') != 'PASS':
            problems.append(f'payment_instructions_coverage_gate must be PASS when dto_attribution_proven=True, got {attr.get("payment_instructions_coverage_gate")!r}')
            attribution_ok = False
        gate_status = 'PASS' if attribution_ok else 'UNKNOWN/NOT_RUN'
    else:
        if attr.get('scoped_verdict') != 'PASS_NARROW_RPC_PAYLOAD_ONLY':
            problems.append(f'scoped_verdict must be PASS_NARROW_RPC_PAYLOAD_ONLY when dto_attribution_proven=False, got {attr.get("scoped_verdict")!r}')
        if attr.get('claim_scope') != 'narrow_rpc_payload_retention_only':
            problems.append(f'claim_scope must be narrow_rpc_payload_retention_only, got {attr.get("claim_scope")!r}')
        if attr.get('payment_instructions_coverage_gate') == 'PASS':
            problems.append('payment_instructions_coverage_gate cannot be PASS without app-level DTO path attribution')
        gate_status = 'UNKNOWN/NOT_RUN'
        if require_dto_attribution:
            problems.append('DTO-level retaining-path attribution is unproven (PaymentInstructions gate remains UNKNOWN/NOT_RUN)')

    report_text = texts.get('report.md') or ''
    if attr.get('scoped_verdict') and str(attr.get('scoped_verdict')) not in report_text:
        problems.append('report.md must record the exact scoped_verdict from summary.json')

    return {
        'scoped_verdict': attr.get('scoped_verdict'),
        'dto_attribution_proven': dto_proven if gate_status == 'PASS' else False,
        'payment_instructions_coverage_gate': gate_status,
    }


def verify(evidence_dir, *, require_dto_attribution=False, repo_root=ROOT, build_dir=None):
    """Audit a PaymentInstructions heap evidence bundle read-only. Returns (problems, assessment)."""
    problems = []
    evidence_dir = Path(evidence_dir)
    if not evidence_dir.is_dir():
        return [f'evidence dir missing: {evidence_dir}'], {'scoped_verdict': 'FAIL', 'payment_instructions_coverage_gate': 'FAIL'}

    before = _digests(evidence_dir)

    for name in REQUIRED_FILES:
        path = evidence_dir / name
        if not path.is_file() or _is_link(path):
            problems.append(f'missing required file: {name}')

    for path in Path(repo_root).rglob('*'):
        if path.is_file() and not _is_link(path) and path.suffix in RAW_HEAP_SUFFIXES:
            problems.append(f'raw heap artifact present in repo: {path}')

    for path in _bundle_entries(evidence_dir):
        if path.suffix in RAW_HEAP_SUFFIXES:
            problems.append(f'raw heap artifact in bundle: {path.name}')

    _check_manifest(evidence_dir, problems)

    texts = {}
    for path in _bundle_entries(evidence_dir):
        if _is_link(path) or not path.is_file():
            continue
        label = path.relative_to(evidence_dir).as_posix()
        text = _read_text(path, label, problems)
        if text is not None:
            texts[label] = text

    summary = None
    if 'summary.json' in texts:
        try:
            summary = json.loads(texts['summary.json'])
        except json.JSONDecodeError as exc:
            problems.append(f'summary.json invalid JSON: {exc}')

    assessment = {'scoped_verdict': 'FAIL', 'payment_instructions_coverage_gate': 'FAIL'}
    if not isinstance(summary, dict):
        problems.append('summary.json must be a JSON object')
    else:
        if summary.get('status') != 'RUN' or summary.get('verdict') != 'PASS':
            problems.append(f'summary status/verdict must be RUN/PASS, got {summary.get("status")!r}/{summary.get("verdict")!r}')
        if summary.get('git_dirty') is True:
            problems.append('summary records git_dirty=True')
        if not SHA1.fullmatch(str(summary.get('tested_source_sha') or '')):
            problems.append('summary lacks full 40-char tested_source_sha')
        _check_build(summary, problems)
        _check_contract(summary, problems)
        _check_cycles(summary, problems)
        _check_cleanup(summary, problems)
        _check_sentinels_and_leaks(summary, texts, problems)
        assessment = _check_attribution_and_claims(
            summary,
            texts,
            problems,
            require_dto_attribution=require_dto_attribution,
            build_dir=build_dir,
        )

    for label, text in sorted(texts.items()):
        for pattern, name in SECRET_PATTERNS:
            if re.search(pattern, text):
                problems.append(f'{label} contains a {name}')

    if before != _digests(evidence_dir):
        problems.append('audit modified the bundle')

    return problems, assessment


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dir', required=True, help='Path to PaymentInstructions heap evidence directory')
    parser.add_argument('--build-dir', default=None,
                        help='Path to served profile build directory containing exact matching main.dart.js')
    parser.add_argument('--require-dto-attribution', action='store_true',
                        help='Fail closed if app-level DTO retaining-path attribution is unproven')
    args = parser.parse_args(argv)

    problems, assessment = verify(
        args.dir,
        require_dto_attribution=args.require_dto_attribution,
        build_dir=args.build_dir,
    )
    for problem in problems:
        print(f'FAIL {problem}')
    if problems:
        return 1
    print(json.dumps({'status': 'PASS', **assessment}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
