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
    """Derive the expectations from the scans, never from the bundle's own claim."""
    owner = (scans.get('owner_active') or {}).get('sentinels') or {}
    expectations = {epoch: {'probe': True, 'bank': epoch == 'owner_active'} for epoch in EPOCHS}
    if (owner.get('expense') or {}).get('present') is True:
        for epoch in EPOCHS:
            expectations[epoch]['expense'] = epoch == 'owner_active'
    return expectations


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
        verdict = heap_oracle.decide(scans, expectations_from(scans), True, build.get('mode'))
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
        start = lines.index(CYCLE_HEADER) + 1
        if start < len(lines) and set(lines[start]) <= set('| -'):
            start += 1
        actual = []
        for line in lines[start:]:
            if not line.startswith('|'):
                break
            cells = [cell.strip() for cell in line.strip().strip('|').split('|')]
            if len(cells) != CYCLE_CELLS:
                problems.append(f'report.md cycle row has {len(cells)} columns: {line!r}')
                continue
            actual.append(cells)
        expected = _expected_report_rows(summary)
        if actual != expected:
            missing = [row for row in expected if row not in actual]
            extra = [row for row in actual if row not in expected]
            problems.append(f'report.md cycle rows do not match summary.json '
                            f'(missing {missing[:2]}, extra {extra[:2]})')

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


def _check_sentinels(summary, texts, problems):
    """Published metadata is hash/length only, and no file may carry the raw value.

    The raw value never reaches the bundle, so match every window of the published
    length against the published sha256[:12]. That catches a value pasted into a log,
    the report, an unmanifested extra file or any nested metadata field.
    """
    sentinels = summary.get('sentinels')
    if not isinstance(sentinels, dict):
        return
    for name, meta in sorted(sentinels.items()):
        if not isinstance(meta, dict):
            problems.append(f'sentinel {name} metadata is not an object')
            continue
        if 'value' in meta:
            problems.append(f'sentinel {name} publishes its raw value')
        digest = meta.get('sha256_12')
        if digest is not None and not HEX12.fullmatch(str(digest)):
            problems.append(f'sentinel {name} has a malformed sha256_12')
        length = meta.get('length')
        if not isinstance(length, int) or length <= 0 or not HEX12.fullmatch(str(digest or '')):
            continue
        for label, text in sorted(texts.items()):
            hit = any(hashlib.sha256(text[start:start + length].encode('utf-8')).hexdigest()[:12] == digest
                      for start in range(max(0, len(text) - length + 1)))
            if hit:
                problems.append(f'{label} publishes the raw value of sentinel {name}')


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
    print(f'PASS: evidence bundle at {Path(args.dir).relative_to(ROOT)} is complete, hash-consistent, '
          'internally consistent with the oracle, free of raw heap dumps and credentials')
    return 0


if __name__ == '__main__':
    sys.exit(main())
