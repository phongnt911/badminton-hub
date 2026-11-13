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
FORBIDDEN_DTO_LABEL_WORDS = ('xmlhttprequest', 'responsetext', 'script', 'xhr')
RAW_HEAP_SUFFIXES = ('.heapsnapshot', '.heapprofile', '.heaptimeline')
SECRET_PATTERNS = (
    (r'eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}', 'JWT token'),
    (r'bh07-http-pass', 'test account password'),
    (r'SERVICE_ROLE_KEY|SUPABASE_ANON_KEY\s*=', 'service/anon key name with value'),
    (r'postgresql://[^\s"]+:[^\s"]+@', 'database URL with credentials'),
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


def _has_ordered_dto_retainer_chain(frames):
    """Require exact ordered property edges: _finance_provider$_instructions -> receiverSnapshot -> map -> string."""
    if not isinstance(frames, list) or len(frames) < 4 or frames[0] != 'root' or '...' in frames:
        return False
    parsed = [_parse_frame(f) for f in frames[1:]]
    if any(p is None for p in parsed):
        return False

    for idx in range(len(parsed) - 2):
        step1 = parsed[idx]
        step2 = parsed[idx + 1]
        if (step1['kind'] == 'property'
                and step1['label'] == '_finance_provider$_instructions'
                and step1['child'] in CONTAINER_CHILD_TYPES
                and step2['kind'] == 'property'
                and step2['label'] == 'receiverSnapshot'
                and step2['child'] in CONTAINER_CHILD_TYPES):
            suffix = parsed[idx + 2:]
            if not suffix:
                continue
            intermediates = suffix[:-1]
            leaf = suffix[-1]
            if any(any(w in f['label'].lower() for w in FORBIDDEN_DTO_LABEL_WORDS) for f in parsed[idx:]):
                continue
            if any(f['kind'] not in ('property', 'element', 'internal') or f['child'] not in CONTAINER_CHILD_TYPES
                   for f in intermediates):
                continue
            if leaf['kind'] in ('property', 'element', 'internal') and leaf['child'] in STRING_CHILD_TYPES:
                return True
    return False


def _check_attribution_and_claims(summary, texts, problems, require_dto_attribution=False):
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

    # Cross-check owner_active frames against dto_proven claim.
    owner_frames_list = []
    for cycle in summary.get('cycles') or []:
        if not isinstance(cycle, dict):
            continue
        owner_ep = (cycle.get('epochs') or {}).get('owner_active') or {}
        paths = owner_ep.get('paths') or {}
        for cname in REQUIRED_CANARIES:
            frames = (paths.get(cname) or {}).get('frames') or []
            owner_frames_list.append(frames)

    all_paths_attributed = (
        len(owner_frames_list) == 4
        and all(_has_ordered_dto_retainer_chain(frames) for frames in owner_frames_list)
    )

    if dto_proven:
        if not all_paths_attributed:
            problems.append('dto_attribution_proven=True claimed without ordered FinanceProvider._instructions -> receiverSnapshot -> map property chain in all owner_active paths')
        proven_frames = attr.get('proven_frames')
        if not isinstance(proven_frames, list) or not _has_ordered_dto_retainer_chain(proven_frames):
            problems.append('dto_attribution_proven=True requires proven_frames containing ordered FinanceProvider._instructions -> receiverSnapshot -> map property chain')
        if attr.get('scoped_verdict') != 'PASS_DTO_ATTRIBUTED':
            problems.append(f'scoped_verdict must be PASS_DTO_ATTRIBUTED when dto_attribution_proven=True, got {attr.get("scoped_verdict")!r}')
        gate_status = 'PASS'
    else:
        if attr.get('scoped_verdict') != 'PASS_NARROW_RPC_PAYLOAD_ONLY':
            problems.append(f'scoped_verdict must be PASS_NARROW_RPC_PAYLOAD_ONLY when dto_attribution_proven=False, got {attr.get("scoped_verdict")!r}')
        if attr.get('claim_scope') != 'narrow_rpc_payload_retention_only':
            problems.append(f'claim_scope must be narrow_rpc_payload_retention_only, got {attr.get("claim_scope")!r}')
        if attr.get('payment_instructions_coverage_gate') == 'PASS':
            problems.append('payment_instructions_coverage_gate cannot be PASS without app-level DTO path attribution')
        gate_status = 'UNKNOWN/NOT_RUN'
        if require_dto_attribution:
            problems.append('DTO-level retaining-path attribution is unproven under minification (PaymentInstructions gate remains UNKNOWN/NOT_RUN)')

    report_text = texts.get('report.md') or ''
    if attr.get('scoped_verdict') and str(attr.get('scoped_verdict')) not in report_text:
        problems.append('report.md must record the exact scoped_verdict from summary.json')

    return {
        'scoped_verdict': attr.get('scoped_verdict'),
        'dto_attribution_proven': dto_proven,
        'payment_instructions_coverage_gate': gate_status,
    }


def verify(evidence_dir, *, require_dto_attribution=False, repo_root=ROOT):
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
        assessment = _check_attribution_and_claims(summary, texts, problems, require_dto_attribution=require_dto_attribution)

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
    parser.add_argument('--require-dto-attribution', action='store_true',
                        help='Fail closed if app-level DTO retaining-path attribution is unproven')
    args = parser.parse_args(argv)

    problems, assessment = verify(args.dir, require_dto_attribution=args.require_dto_attribution)
    for problem in problems:
        print(f'FAIL {problem}')
    if problems:
        return 1
    print(json.dumps({'status': 'PASS', **assessment}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
