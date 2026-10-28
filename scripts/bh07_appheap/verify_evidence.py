"""Read-only audit of the BH-07 app-profile heap evidence bundle.

The bundle is the only thing a reviewer sees: the raw V8 dumps are deleted after the
run. So this auditor must refuse a bundle that lies. It:

- requires the exact published file set to be covered by `hashes.sha256` (no extras,
  no duplicates, no traversal/absolute paths, no symlink/junction entries at all);
- reads every published file as bytes, rejecting a BOM, any CR (strict LF), and any
  byte that is not valid UTF-8, then scans that text for credentials *and* for the raw
  value of every published sentinel (matched by its published length + sha256[:12], so
  the auditor never needs the secret itself);
- requires `summary.json` to be an object with every required field regardless of
  truthiness, and type-checks the nested data instead of skipping it when falsy;
- recomputes the per-cycle and overall verdict from the recorded scans with the same
  oracle the runner used, with the expectations derived from the scans themselves, so
  a missing cycle/epoch, a failed scan, a dead probe or a leak cannot stay PASS;
- parses `report.md` (status/verdict line, build line, every cycle row, findings) and
  requires it to agree with `summary.json` row by row, so a hand-edited Markdown verdict
  cannot survive next to a PASS JSON;
- requires the two actor paths, single-document evidence and profile build provenance
  (artifact hashes plus proof that the served bytes are those artifacts);
- proves it changed nothing: every published file hash is compared before and after.

It never writes, never re-runs the measurement and never needs the raw heap.

Usage: python verify_evidence.py [--dir docs/reviews/bh07/app_profile_heap_evidence]
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import heap_oracle  # noqa: E402  (same directory, one source of truth for the verdict)

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DIR = ROOT / 'docs/reviews/bh07/app_profile_heap_evidence'
MANIFEST = 'hashes.sha256'
REQUIRED_FILES = ('summary.json', 'report.md', 'run.log', MANIFEST)
EPOCHS = ('baseline', 'owner_active', 'post_logout', 'post_actor')
CYCLE_ACTORS = ('cohost', 'member')
# Sentinels the bundle must describe: the live control plus at least one unrendered finance
# value, so a bundle cannot publish only engine-cache-tainted or identity values.
GATING_SENTINELS = ('probe',)
RAW_HEAP_SUFFIXES = ('.heapsnapshot', '.heapprofile', '.heaptimeline')
SECRET_PATTERNS = (
    (r'eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}', 'JWT token'),
    (r'bh07-http-pass', 'test account password'),
    (r'SERVICE_ROLE_KEY|SUPABASE_ANON_KEY\s*=', 'service/anon key name with value'),
    (r'postgresql://[^\s"]+:[^\s"]+@', 'database URL with credentials'),
)
REQUIRED_SUMMARY_FIELDS = ('gate', 'status', 'measurement_surface', 'oracle', 'tested_source_sha',
                           'cycles', 'cleanup', 'environment', 'sentinels', 'verdict')
HEX12 = re.compile(r'[0-9a-f]{12}')
HEX64 = re.compile(r'[0-9a-f]{64}')
SHA1 = re.compile(r'[0-9a-f]{40}')
MANIFEST_LINE = re.compile(r'([0-9a-f]{64})  (.+)')
CYCLE_HEADER = '| cycle | actor path | same document | epoch | snapshot bytes | snapshot sha256[:12] | present sentinels |'
CYCLE_CELLS = 7
PATH_HEADER = '| cycle | epoch | sentinel | reachable | root kind | path length | path sha256[:12] |'
PATH_CELLS = 7
SENTINEL_HEADER = '| sentinel | kind | class | length | sha256[:12] |'
SENTINEL_CELLS = 5
RISK_HEADER = '| cycle | epoch | sentinel | root kind | path length | path sha256[:12] |'
RISK_CELLS = 6
# A rendered text sentinel is retained by the web engine's segmentation cache, not by the
# app; it must still be published instead of silently passing as clean.
RENDERED_RISK_SECTIONS = ('Residual risks', 'Notes')


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as fp:
        for chunk in iter(lambda: fp.read(1 << 20), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _is_link(path):
    """True for symlinks and Windows junctions: both can point outside the bundle."""
    if path.is_symlink():
        return True
    junction = getattr(path, 'is_junction', None)
    return bool(junction and junction())


def _bundle_entries(evidence_dir):
    """Every entry, not just regular files: a link that is skipped is a link that passes."""
    return sorted(evidence_dir.rglob('*'), key=lambda p: p.relative_to(evidence_dir).as_posix())


def _digests(evidence_dir):
    digests = {}
    for path in _bundle_entries(evidence_dir):
        name = path.relative_to(evidence_dir).as_posix()
        if _is_link(path):
            digests[name] = 'link'
        elif path.is_dir():
            digests[name] = 'dir'
        else:
            digests[name] = sha256_file(path)
    return digests


def _read_text(path, label, problems):
    """Bytes first: universal-newline reads and errors='replace' both hide faults."""
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


def _manifest_entries(evidence_dir, problems):
    path = evidence_dir / MANIFEST
    text = _read_text(path, MANIFEST, problems)
    if text is None:
        return None
    entries = {}
    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        match = MANIFEST_LINE.fullmatch(line)
        if not match:
            problems.append(f'{MANIFEST}:{number} is not "<sha256>  <relative path>"')
            continue
        digest, name = match.groups()
        unsafe = (name.startswith('/') or '\\' in name or ':' in name
                  or any(part in ('..', '') for part in name.split('/')))
        if unsafe:
            problems.append(f'{MANIFEST}:{number} has an unsafe path: {name}')
            continue
        if name == MANIFEST:
            problems.append(f'{MANIFEST}:{number} lists the manifest itself')
            continue
        if name in entries:
            problems.append(f'{MANIFEST}:{number} lists {name} twice')
            continue
        entries[name] = digest
    return entries


def _check_coverage(evidence_dir, entries, problems):
    files = set()
    for path in _bundle_entries(evidence_dir):
        name = path.relative_to(evidence_dir).as_posix()
        if _is_link(path):
            # Review 57ec02c AH3-A: a directory link is never part of the inventory, so
            # filtering to files first made it invisible. Any link is rejected up front.
            problems.append(f'bundle contains a symlink or junction: {name}')
            continue
        if evidence_dir.resolve() not in path.resolve().parents:
            problems.append(f'bundle entry resolves outside the bundle: {name}')
            continue
        if path.is_file():
            files.add(name)

    for name in sorted(set(entries) - files):
        problems.append(f'manifest lists missing file: {name}')
    for name in sorted(files - set(entries) - {MANIFEST}):
        problems.append(f'bundle file is not in the manifest: {name}')
    for name, digest in sorted(entries.items()):
        target = evidence_dir / name
        if name not in files:
            continue
        actual = sha256_file(target)
        if actual != digest:
            problems.append(f'hash mismatch: {name} ({digest[:12]} != {actual[:12]})')
    if len(entries) < 3:
        problems.append(f'manifest has only {len(entries)} entries')


def expectations_from(scans):
    """Derive the expectations from the scans, never from the bundle's own claim.

    Delegated to the oracle so the auditor cannot drift from the runner's own rule
    (review 2d16369 kept retained paths NOT RUN; this gate is the missing half).
    """
    return heap_oracle.derive_expectations(scans)


def _js_bool(value):
    return 'true' if value is True else 'false'


def _check_summary_shape(summary, problems):
    """A falsy object is still an object with a schema: never skip the field gate."""
    if not isinstance(summary, dict):
        problems.append(f'summary.json must be a JSON object, got {type(summary).__name__}')
        return False
    for field in REQUIRED_SUMMARY_FIELDS:
        if field not in summary:
            problems.append(f'summary.json missing field: {field}')
    for field in ('environment', 'sentinels', 'cleanup'):
        if field in summary and not isinstance(summary[field], dict):
            problems.append(f'summary.json field {field} must be an object')
    return True


def _check_build(summary, problems):
    environment = summary.get('environment')
    build = (environment.get('build') if isinstance(environment, dict) else None) or {}
    if not isinstance(build, dict):
        problems.append('summary.json environment.build must be an object')
        build = {}
    if build.get('mode') != 'profile':
        problems.append(f'status RUN requires a profile build, got mode {build.get("mode")!r}')
    if build.get('reused'):
        problems.append('build.reused is set: a reused build cannot prove profile provenance')
    if not build.get('started_at'):
        problems.append('build provenance lacks started_at')
    artifacts = build.get('artifacts')
    if not isinstance(artifacts, dict) or not artifacts:
        problems.append('build provenance lacks artifact hashes')
    else:
        for name in ('index.html', 'main.dart.js'):
            if name not in artifacts:
                problems.append(f'build artifact hashes do not cover {name}')
        for name, digest in artifacts.items():
            if not isinstance(digest, str) or not HEX64.fullmatch(digest):
                problems.append(f'build artifact hash for {name} is not a sha256')
    if build.get('served_match') is not True:
        problems.append('served bytes were not proven to match the built artifact')
    return build


def _check_cycles(summary, build, problems):
    cycles = summary.get('cycles')
    if not isinstance(cycles, list) or len(cycles) != len(CYCLE_ACTORS):
        problems.append(f'summary must record exactly {len(CYCLE_ACTORS)} cycles, got '
                        f'{cycles if not isinstance(cycles, list) else len(cycles)}')
        return []
    actors = []
    recomputed = []
    for index, cycle in enumerate(cycles, 1):
        label = f'cycle {index}'
        if not isinstance(cycle, dict):
            problems.append(f'{label}: entry is not an object')
            recomputed.append({'verdict': 'FAIL', 'findings': [f'{label}: entry is not an object']})
            continue
        if cycle.get('cycle') != index:
            problems.append(f'{label}: cycle number is {cycle.get("cycle")!r}')
        actor = cycle.get('actor')
        actors.append(actor)
        if actor not in CYCLE_ACTORS:
            problems.append(f'{label}: actor path {actor!r} is not one of {CYCLE_ACTORS}')
        if cycle.get('same_document') is not True:
            problems.append(f'{label}: single-document evidence missing')
        if not isinstance(cycle.get('time_origin'), (int, float)):
            problems.append(f'{label}: time_origin missing')
        scans = cycle.get('epochs')
        if not isinstance(scans, dict):
            problems.append(f'{label}: epochs must be an object')
            recomputed.append({'verdict': 'FAIL', 'findings': [f'{label}: epochs must be an object']})
            continue
        missing = sorted(set(EPOCHS) - set(scans))
        unexpected = sorted(set(scans) - set(EPOCHS))
        if missing or unexpected:
            problems.append(f'{label}: epochs missing {missing} unexpected {unexpected}')
        for epoch, scan in sorted(scans.items()):
            if not isinstance(scan, dict):
                problems.append(f'{label} {epoch}: scan is not an object')
                scans[epoch] = {'ok': False, 'error': 'scan is not an object'}
                continue
            # Same validator the oracle verdict uses, so a contradictory count can never
            # be certified "internally consistent" (review 0f11bb4 AH9), and a bundle that
            # skipped the retained-path analysis is not "no retention found".
            for problem in heap_oracle.scan_problems(scan, require_paths=True):
                problems.append(f'{label} {epoch}: {problem}')
        verdict = heap_oracle.decide(scans, expectations_from(scans), True, build.get('mode'),
                                     strict=True)
        stored = cycle.get('verdict') if isinstance(cycle.get('verdict'), dict) else {}
        if stored.get('verdict') != verdict['verdict']:
            problems.append(f'{label}: recorded verdict {stored.get("verdict")!r} but the recorded '
                            f'scans decide {verdict["verdict"]!r} {verdict["findings"]}')
        elif stored.get('findings') != verdict['findings']:
            problems.append(f'{label}: recorded verdict findings {stored.get("findings")} do not match '
                            f'the recorded scans {verdict["findings"]}')
        recomputed.append(verdict)
    if sorted(a for a in actors if a) != sorted(CYCLE_ACTORS):
        problems.append(f'both actor paths must be measured exactly once, got {actors}')

    overall = 'PASS' if all(v['verdict'] == 'PASS' for v in recomputed) else 'FAIL'
    if summary.get('verdict') != overall:
        problems.append(f'overall verdict {summary.get("verdict")!r} does not match the cycles ({overall})')
    findings = [f'cycle {index}: {finding}'
                for index, verdict in enumerate(recomputed, 1) for finding in verdict['findings']]
    if summary.get('findings') != findings:
        problems.append(f'summary findings {summary.get("findings")} do not match the cycles {findings}')
    notes = [f'cycle {index}: {note}'
             for index, verdict in enumerate(recomputed, 1) for note in verdict.get('notes') or []]
    if summary.get('notes') != notes:
        problems.append(f'summary notes {summary.get("notes")} do not match the cycles {notes}')
    risks = [{'cycle': index, **risk}
             for index, verdict in enumerate(recomputed, 1) for risk in verdict.get('residual_risks') or []]
    if summary.get('residual_risks') != risks:
        problems.append(f'summary residual risks {summary.get("residual_risks")} do not match the '
                        f'cycles {risks}')
    return recomputed


def _section(text, title):
    """Lines of a `## title` section, stopping at the next heading."""
    lines = text.splitlines()
    try:
        start = lines.index(f'## {title}') + 1
    except ValueError:
        return None
    body = []
    for line in lines[start:]:
        if line.startswith('#'):
            break
        body.append(line)
    return body


def _expected_report_rows(summary):
    rows = []
    for cycle in summary.get('cycles') or []:
        if not isinstance(cycle, dict):
            continue
        for epoch, scan in (cycle.get('epochs') or {}).items():
            if not isinstance(scan, dict):
                continue
            present = ', '.join(name for name, value in (scan.get('sentinels') or {}).items()
                                if isinstance(value, dict) and value.get('present')) or 'none'
            rows.append([str(cycle.get('cycle')), f'Owner -> logout -> {cycle.get("actor")}',
                         _js_bool(cycle.get('same_document')), epoch,
                         str(scan.get('size_bytes', 'n/a')), str(scan.get('sha256_12') or 'n/a'), present])
    return rows


def _expected_path_rows(summary):
    """One row per recorded sentinel, so a Markdown path table must match the JSON."""
    rows = []
    for cycle in summary.get('cycles') or []:
        if not isinstance(cycle, dict):
            continue
        for epoch, scan in (cycle.get('epochs') or {}).items():
            paths = scan.get('paths') if isinstance(scan, dict) else None
            if not isinstance(paths, dict):
                continue
            for name in sorted(paths):
                record = paths[name] if isinstance(paths[name], dict) else {}
                reachable = record.get('reachable') is True
                rows.append([
                    str(cycle.get('cycle')), epoch, name, _js_bool(reachable),
                    str(record.get('root_kind') or 'n/a') if reachable else 'n/a',
                    str(record.get('path_len') or 'n/a') if reachable else 'n/a',
                    str(record.get('path_sha256_12') or 'n/a') if reachable else 'n/a',
                ])
    return rows


def _sentinel_class_cell(meta):
    """Same wording the runner prints, so the table can be compared field by field."""
    meta = meta if isinstance(meta, dict) else {}
    rendered = 'rendered' if meta.get('rendered') is True else 'not rendered'
    distinctive = 'distinctive' if meta.get('distinctive') is True else 'not distinctive'
    return f"{meta.get('scope') or 'identity'}, {rendered}, {distinctive}"


def _expected_sentinel_rows(summary):
    """Declaration table rows: the class the gate read must be the class in the report."""
    rows = []
    for name, meta in (summary.get('sentinels') or {}).items():
        meta = meta if isinstance(meta, dict) else {}
        length = meta.get('length')
        rows.append([str(name), str(meta.get('kind') or 'n/a'), _sentinel_class_cell(meta),
                     'n/a' if length is None else str(length), str(meta.get('sha256_12') or 'n/a')])
    return rows


def _check_cleanup_receipt(text, summary, problems):
    """The run-only fixture cleanup must be published in the report, not only in the JSON."""
    body = _section(text, 'Cleanup')
    if body is None:
        problems.append('report.md is missing the Cleanup section')
        return
    payloads = [line[2:] for line in body if line.startswith('- {')]
    if len(payloads) != 1:
        problems.append(f'report.md must publish exactly one cleanup receipt, found {len(payloads)}')
        return
    try:
        reported = json.loads(payloads[0])
    except json.JSONDecodeError as exc:
        problems.append(f'report.md cleanup receipt is not JSON: {exc}')
        return
    if reported != summary.get('cleanup'):
        problems.append(f'report.md cleanup receipt {reported} does not match summary.json '
                        f'{summary.get("cleanup")}')


def _expected_risk_rows(summary):
    """One row per published residual risk, so the Markdown cannot soften the JSON."""
    risks = summary.get('residual_risks')
    if not isinstance(risks, list) or not risks:
        return [['none', 'n/a', 'n/a', 'n/a', 'n/a', 'n/a']]
    rows = []
    for risk in risks:
        if not isinstance(risk, dict):
            rows.append(['invalid', 'invalid', 'invalid', 'invalid', 'invalid', 'invalid'])
            continue
        rows.append([str(risk.get('cycle')), str(risk.get('epoch')), str(risk.get('sentinel')),
                     str(risk.get('root_kind') or 'n/a'),
                     str(risk.get('path_len') or 'n/a'), str(risk.get('path_sha256_12') or 'n/a')])
    return rows


def _table_rows(lines, header, cells):
    """Data rows of one Markdown table, or None when the header itself is missing."""
    if header not in lines:
        return None
    start = lines.index(header) + 1
    if start < len(lines) and set(lines[start]) <= set('| -'):
        start += 1
    rows = []
    for line in lines[start:]:
        if not line.startswith('|'):
            break
        row = [cell.strip() for cell in line.strip().strip('|').split('|')]
        rows.append(row if len(row) == cells else None)
    return rows


def _check_report(evidence_dir, summary, build, problems):
    """Parse the Markdown; substring presence is not agreement (review 57ec02c AH2-B)."""
    path = evidence_dir / 'report.md'
    text = _read_text(path, 'report.md', problems)
    if text is None:
        return
    lines = [line.rstrip() for line in text.splitlines()]

    status = f'- Status: **{summary.get("status")}**'
    if summary.get('verdict'):
        status += f' (verdict {summary["verdict"]})'
    status_lines = [line for line in lines if line.startswith('- Status: ')]
    if len(status_lines) != 1:
        problems.append(f'report.md must contain exactly one status line, found {len(status_lines)}')
    elif status_lines[0] != status:
        problems.append(f'report.md status line {status_lines[0]!r} does not match summary {status!r}')

    source = (f'- Tested source: `{summary.get("tested_source_sha")}` '
              f'(git dirty: {_js_bool(summary.get("git_dirty"))})')
    if source not in lines:
        problems.append('report.md tested-source line does not match summary.json')

    artifacts = build.get('artifacts') if isinstance(build, dict) else None
    build_line = (f'- Build: mode={build.get("mode", "n/a")} reused={_js_bool(build.get("reused"))} '
                  f'artifacts={len(artifacts) if isinstance(artifacts, dict) else 0} '
                  f'served_match={_js_bool(build.get("served_match"))}')
    if build_line not in lines:
        problems.append('report.md build line does not match summary.json provenance')

    if CYCLE_HEADER not in lines:
        problems.append('report.md is missing the cycle table header')
    else:
        actual = _table_rows(lines, CYCLE_HEADER, CYCLE_CELLS) or []
        if any(row is None for row in actual):
            problems.append('report.md cycle rows have the wrong column count')
            actual = [row for row in actual if row is not None]
        expected = _expected_report_rows(summary)
        if actual != expected:
            missing = [row for row in expected if row not in actual]
            extra = [row for row in actual if row not in expected]
            problems.append(f'report.md cycle rows do not match summary.json '
                            f'(missing {missing[:2]}, extra {extra[:2]})')

    sentinel_rows = _table_rows(lines, SENTINEL_HEADER, SENTINEL_CELLS)
    if sentinel_rows is None:
        problems.append('report.md is missing the sentinel declaration table header')
    else:
        if any(row is None for row in sentinel_rows):
            problems.append('report.md sentinel rows have the wrong column count')
            sentinel_rows = [row for row in sentinel_rows if row is not None]
        expected_sentinels = _expected_sentinel_rows(summary)
        if sentinel_rows != expected_sentinels:
            problems.append(f'report.md sentinel declaration rows do not match summary.json '
                            f'({sentinel_rows[:2]} != {expected_sentinels[:2]})')

    path_rows = _table_rows(lines, PATH_HEADER, PATH_CELLS)
    if path_rows is None:
        problems.append('report.md is missing the retained-path table header')
    else:
        if any(row is None for row in path_rows):
            problems.append('report.md retained-path rows have the wrong column count')
            path_rows = [row for row in path_rows if row is not None]
        expected_paths = _expected_path_rows(summary)
        if path_rows != expected_paths:
            missing = [row for row in expected_paths if row not in path_rows]
            extra = [row for row in path_rows if row not in expected_paths]
            problems.append(f'report.md retained-path rows do not match summary.json '
                            f'(missing {missing[:2]}, extra {extra[:2]})')

    risk_rows = _table_rows(lines, RISK_HEADER, RISK_CELLS)
    if risk_rows is None:
        problems.append('report.md is missing the residual-risk table header')
    else:
        if any(row is None for row in risk_rows):
            problems.append('report.md residual-risk rows have the wrong column count')
            risk_rows = [row for row in risk_rows if row is not None]
        expected_risks = _expected_risk_rows(summary)
        if risk_rows != expected_risks:
            problems.append(f'report.md residual-risk rows do not match summary.json '
                            f'({risk_rows[:2]} != {expected_risks[:2]})')

    notes_body = _section(text, 'Notes')
    if notes_body is None:
        problems.append('report.md is missing the Notes section')
    else:
        reported_notes = [line[2:] for line in notes_body if line.startswith('- ')]
        expected_notes = list(summary.get('notes') or [])
        if not expected_notes and reported_notes == ['none']:
            reported_notes = []
        if reported_notes != expected_notes:
            problems.append(f'report.md notes do not match summary.json '
                            f'({reported_notes} != {expected_notes})')

    findings_body = _section(text, 'Findings')
    if findings_body is None:
        problems.append('report.md is missing the Findings section')
    else:
        reported = [line[2:] for line in findings_body if line.startswith('- ')]
        expected = list(summary.get('findings') or [])
        if summary.get('error'):
            expected.append(f'run aborted: {summary["error"]}')
        if not reported:
            reported = []
        if not expected and reported == ['none']:
            reported = []
        if reported != expected:
            problems.append(f'report.md findings do not match summary.json ({reported} != {expected})')

    _check_cleanup_receipt(text, summary, problems)


def _check_cleanup(summary, problems):
    cleanup = summary.get('cleanup')
    if not isinstance(cleanup, dict):
        problems.append('summary.json cleanup must be an object')
        return
    for field in ('ok', 'dump_dir_outside_repo', 'dumps_dir_removed', 'chrome_profile_dir_removed'):
        if cleanup.get(field) is not True:
            problems.append(f'status RUN requires verified heap dump cleanup: {field}')
    if cleanup.get('raw_snapshots_remaining') != 0:
        problems.append('status RUN requires zero raw heap snapshots left on disk')
    # Review 9fadecc RP6: this measurement posts a row of its own, so the bundle must prove
    # it created that row, deleted it, and verified its absence. `cleanup.ok` alone is the
    # aggregate a runner writes for itself, never evidence.
    if cleanup.get('run_only_fixture_created') is not True:
        problems.append('status RUN requires a run-only fixture this run created: '
                        f'run_only_fixture_created={cleanup.get("run_only_fixture_created")!r}')
    if not HEX12.fullmatch(str(cleanup.get('run_only_fixture_id_sha256_12') or '')):
        problems.append('status RUN requires the run-only fixture id_sha256_12 receipt: '
                        f'{cleanup.get("run_only_fixture_id_sha256_12")!r}')
    for field in ('extra_expense_removed', 'extra_expense_verified_absent'):
        if cleanup.get(field) is not True:
            problems.append(f'status RUN requires a verified run-only fixture cleanup: '
                            f'{field}={cleanup.get(field)!r}')
    if 'extra_expense_error' in cleanup:
        problems.append(f'run-only fixture cleanup reported an error: {cleanup["extra_expense_error"]}')

    if 'run_only_payment_created' in cleanup:
        if cleanup.get('run_only_payment_created') is not True:
            problems.append('status RUN requires run_only_payment_created=True: '
                            f'run_only_payment_created={cleanup.get("run_only_payment_created")!r}')
        if not HEX12.fullmatch(str(cleanup.get('run_only_payment_id_sha256_12') or '')):
            problems.append('status RUN requires the run-only payment id_sha256_12 receipt: '
                            f'{cleanup.get("run_only_payment_id_sha256_12")!r}')
        for field in ('extra_payment_removed', 'extra_payment_verified_absent'):
            if cleanup.get(field) is not True:
                problems.append(f'status RUN requires a verified run-only payment fixture cleanup: '
                                f'{field}={cleanup.get(field)!r}')
        if 'extra_payment_error' in cleanup:
            problems.append(f'run-only payment fixture cleanup reported an error: {cleanup["extra_payment_error"]}')


def _scan_sentinel_names(summary):
    """Every sentinel name any scan claims, so metadata coverage can be checked."""
    names = set()
    for cycle in summary.get('cycles') or []:
        if not isinstance(cycle, dict):
            continue
        for scan in (cycle.get('epochs') or {}).values():
            if isinstance(scan, dict) and isinstance(scan.get('sentinels'), dict):
                names.update(scan['sentinels'])
    return names


def _scan_sentinel_classes(summary):
    """The class each scan recorded per sentinel, so the declaration can be cross-checked."""
    classes = {}
    for cycle in summary.get('cycles') or []:
        if not isinstance(cycle, dict):
            continue
        for epoch, scan in (cycle.get('epochs') or {}).items():
            if not isinstance(scan, dict) or not isinstance(scan.get('sentinels'), dict):
                continue
            for name, record in scan['sentinels'].items():
                if not isinstance(record, dict):
                    continue
                classes.setdefault(name, {})[f'cycle {cycle.get("cycle")} {epoch}'] = record
    return classes


def _check_sentinels(summary, texts, problems):
    """Published metadata is hash/length only, and no file may carry the raw value.

    Review 76334e2 AH8: a missing `length`/`sha256_12` used to `continue`, which disabled
    the detector while the bundle still passed. Identification metadata is mandatory for
    every gating sentinel and for every sentinel a scan claims; an optional sentinel that
    could not be measured must say `available: false` explicitly and must not be claimed.

    Review 9fadecc RP4: the declaration is what the gate reads, so it must agree with the
    class every scan recorded. A scope downgraded in one place while the scans still gate
    the value leaves the reader unable to tell which classification the run used.
    """
    sentinels = summary.get('sentinels')
    if not isinstance(sentinels, dict) or not sentinels:
        problems.append('summary.json must publish sentinel metadata')
        return
    claimed = _scan_sentinel_names(summary)
    for name in GATING_SENTINELS:
        if name not in sentinels:
            problems.append(f'sentinel {name} metadata is missing')
    for name in sorted(claimed - set(sentinels)):
        problems.append(f'a scan records sentinel {name} that has no published metadata')
    scan_classes = _scan_sentinel_classes(summary)
    finance_gated = []
    for name, meta in sorted(sentinels.items()):
        if not isinstance(meta, dict):
            problems.append(f'sentinel {name} metadata is not an object')
            continue
        if 'value' in meta:
            problems.append(f'sentinel {name} publishes its raw value')
        if meta.get('available') is False:
            for field in ('length', 'sha256_12'):
                if meta.get(field) is not None:
                    problems.append(f'sentinel {name} is marked unavailable but publishes {field}')
            if name in claimed:
                problems.append(f'sentinel {name} is marked unavailable but a scan claims it')
            continue
        # The class is what the gate reads, so it must be published and must agree with
        # what every scan recorded for that sentinel.
        for field in ('rendered', 'distinctive'):
            if type(meta.get(field)) is not bool:
                problems.append(f'sentinel {name} metadata lacks a boolean {field}')
        if meta.get('scope') not in heap_oracle.SENTINEL_SCOPES:
            problems.append(f'sentinel {name} metadata has an unknown scope: {meta.get("scope")!r}')
        elif meta.get('scope') == 'finance' and meta.get('rendered') is False:
            finance_gated.append(name)
        for where, recorded in sorted(scan_classes.get(name, {}).items()):
            for field in ('rendered', 'distinctive', 'scope'):
                if recorded.get(field) != meta.get(field):
                    problems.append(f'{where}: sentinel {name} {field} is {recorded.get(field)!r} but '
                                    f'the published declaration says {meta.get(field)!r}')
        length = meta.get('length')
        digest = meta.get('sha256_12')
        identifiable = True
        if type(length) is not int or length <= 0:
            problems.append(f'sentinel {name} metadata lacks a positive integer length: {length!r}')
            identifiable = False
        if not HEX12.fullmatch(str(digest or '')):
            problems.append(f'sentinel {name} metadata lacks a valid sha256_12: {digest!r}')
            identifiable = False
        if not identifiable:
            continue
        for label, text in sorted(texts.items()):
            hit = any(hashlib.sha256(text[start:start + length].encode('utf-8')).hexdigest()[:12] == digest
                      for start in range(max(0, len(text) - length + 1)))
            if hit:
                problems.append(f'{label} publishes the raw value of sentinel {name}')
    if not finance_gated:
        problems.append('no unrendered finance sentinel is published: the gate would not cover '
                        'financial data')


def verify(evidence_dir):
    problems = []
    evidence_dir = Path(evidence_dir)
    if not evidence_dir.is_dir():
        return [f'evidence dir missing: {evidence_dir}']
    before = _digests(evidence_dir)

    for name in REQUIRED_FILES:
        path = evidence_dir / name
        if not path.is_file() or _is_link(path):
            problems.append(f'missing required file: {name}')

    for path in ROOT.rglob('*'):
        if path.is_file() and not _is_link(path) and path.suffix in RAW_HEAP_SUFFIXES:
            problems.append(f'raw heap artifact present in repo: {path.relative_to(ROOT)}')

    for path in _bundle_entries(evidence_dir):
        if path.suffix in RAW_HEAP_SUFFIXES:
            problems.append(f'raw heap artifact published in the bundle: {path.name}')

    entries = _manifest_entries(evidence_dir, problems)
    if entries is not None:
        _check_coverage(evidence_dir, entries, problems)

    texts = {}
    for path in _bundle_entries(evidence_dir):
        if _is_link(path) or not path.is_file():
            continue
        label = path.relative_to(evidence_dir).as_posix()
        text = _read_text(path, label, problems)
        if text is not None:
            texts[label] = text

    summary = None
    summary_readable = False
    if 'summary.json' in texts or (evidence_dir / 'summary.json').is_file():
        summary_text = texts.get('summary.json')
        if summary_text is not None:
            summary_readable = True
            try:
                summary = json.loads(summary_text)
            except json.JSONDecodeError as exc:
                problems.append(f'summary.json is not valid JSON: {exc}')
    if summary_readable and not isinstance(summary, dict):
        problems.append(f'summary.json must be a JSON object, got {json.dumps(summary)[:40]}')
        summary = None
    if isinstance(summary, dict):
        _check_summary_shape(summary, problems)
        status = summary.get('status')
        if status != 'RUN':
            problems.append(f'summary status is {status!r}, not RUN: the gate has no successful measurement')
        if status == 'RUN' and summary.get('verdict') != 'PASS':
            problems.append('status RUN requires verdict PASS')
        if summary.get('git_dirty') is True:
            problems.append('summary records a dirty working tree')
        if not SHA1.fullmatch(str(summary.get('tested_source_sha') or '')):
            problems.append('summary.json lacks a full tested_source_sha')
        build = _check_build(summary, problems)
        _check_cycles(summary, build, problems)
        _check_cleanup(summary, problems)
        _check_report(evidence_dir, summary, build, problems)
        _check_sentinels(summary, texts, problems)

    for label, text in sorted(texts.items()):
        for pattern, name in SECRET_PATTERNS:
            if re.search(pattern, text):
                problems.append(f'{label} contains a {name}')

    after = _digests(evidence_dir)
    if before != after:
        problems.append('the audit modified the bundle')
    return problems


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dir', default=str(DEFAULT_DIR))
    args = parser.parse_args()
    problems = verify(args.dir)
    for problem in problems:
        print(f'FAIL {problem}')
    if problems:
        return 1
    print(f'PASS: evidence bundle at {Path(args.dir).resolve().relative_to(ROOT.resolve())} is complete, hash-consistent, '
          'internally consistent with the oracle, free of raw heap dumps and credentials')
    return 0


if __name__ == '__main__':
    sys.exit(main())
