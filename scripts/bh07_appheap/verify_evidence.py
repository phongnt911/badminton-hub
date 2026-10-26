"""Read-only audit of the BH-07 app-profile heap evidence bundle.

The bundle is the only thing a reviewer sees: the raw V8 dumps are deleted after the
run. So this auditor must refuse a bundle that lies. It:

- requires the exact published file set to be covered by `hashes.sha256` (no extras,
  no duplicates, no traversal/absolute/symlink paths, manifest cannot hash itself);
- reads every published file as bytes, rejecting a BOM, any CR (strict LF), and any
  byte that is not valid UTF-8, then scans that text for credentials;
- recomputes the per-cycle and overall verdict from the recorded scans with the same
  oracle the runner used, with the expectations derived from the scans themselves, so
  a missing cycle/epoch, a failed scan, a dead probe or a leak cannot stay PASS;
- requires the two actor paths, single-document evidence and profile build provenance
  (artifact hashes plus proof that the served bytes are those artifacts);
- proves it changed nothing: every file hash is compared before and after.

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


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as fp:
        for chunk in iter(lambda: fp.read(1 << 20), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _bundle_files(evidence_dir):
    return sorted(p for p in evidence_dir.rglob('*') if p.is_file())


def _digests(evidence_dir):
    return {p.relative_to(evidence_dir).as_posix(): sha256_file(p) for p in _bundle_files(evidence_dir)}


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
    on_disk = {p.relative_to(evidence_dir).as_posix() for p in _bundle_files(evidence_dir)}
    for name in sorted(set(entries) - on_disk):
        problems.append(f'manifest lists missing file: {name}')
    for name in sorted(on_disk - set(entries) - {MANIFEST}):
        problems.append(f'bundle file is not in the manifest: {name}')
    for path in _bundle_files(evidence_dir):
        if path.is_symlink():
            problems.append(f'bundle file is a symlink: {path.name}')
        elif evidence_dir.resolve() not in path.resolve().parents:
            problems.append(f'bundle file resolves outside the bundle: {path.name}')
    for name, digest in sorted(entries.items()):
        target = evidence_dir / name
        if not target.is_file():
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


def _check_build(summary, problems):
    build = (summary.get('environment') or {}).get('build') or {}
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
                        f'{len(cycles) if isinstance(cycles, list) else cycles!r}')
        return
    actors = []
    recomputed = []
    for index, cycle in enumerate(cycles, 1):
        label = f'cycle {index}'
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
        scans = cycle.get('epochs') or {}
        missing = sorted(set(EPOCHS) - set(scans))
        unexpected = sorted(set(scans) - set(EPOCHS))
        if missing or unexpected:
            problems.append(f'{label}: epochs missing {missing} unexpected {unexpected}')
        verdict = heap_oracle.decide(scans, expectations_from(scans), True, build.get('mode'))
        stored = cycle.get('verdict') or {}
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


def _check_report(evidence_dir, summary, problems):
    path = evidence_dir / 'report.md'
    text = _read_text(path, 'report.md', problems)
    if text is None:
        return
    if f'- Status: **{summary.get("status")}**' not in text:
        problems.append(f'report.md status line does not say {summary.get("status")}')
    if f'- Tested source: `{summary.get("tested_source_sha")}`' not in text:
        problems.append('report.md tested-source line does not match summary.json')
    for cycle in summary.get('cycles') or []:
        for epoch, scan in (cycle.get('epochs') or {}).items():
            for field in ('size_bytes', 'sha256_12'):
                value = scan.get(field)
                if value is None or str(value) not in text:
                    problems.append(f'report.md does not report cycle {cycle.get("cycle")} {epoch} {field}')


def _check_cleanup(summary, problems):
    cleanup = summary.get('cleanup') or {}
    for field in ('ok', 'dump_dir_outside_repo', 'dumps_dir_removed', 'chrome_profile_dir_removed'):
        if cleanup.get(field) is not True:
            problems.append(f'status RUN requires verified heap dump cleanup: {field}')
    if cleanup.get('raw_snapshots_remaining') != 0:
        problems.append('status RUN requires zero raw heap snapshots left on disk')


def verify(evidence_dir):
    problems = []
    evidence_dir = Path(evidence_dir)
    if not evidence_dir.is_dir():
        return [f'evidence dir missing: {evidence_dir}']
    before = _digests(evidence_dir)

    for name in REQUIRED_FILES:
        if not (evidence_dir / name).is_file():
            problems.append(f'missing required file: {name}')

    for path in ROOT.rglob('*'):
        if path.is_file() and path.suffix in RAW_HEAP_SUFFIXES:
            problems.append(f'raw heap artifact present in repo: {path.relative_to(ROOT)}')

    for path in _bundle_files(evidence_dir):
        if path.suffix in RAW_HEAP_SUFFIXES:
            problems.append(f'raw heap artifact published in the bundle: {path.name}')

    entries = _manifest_entries(evidence_dir, problems)
    if entries is not None:
        _check_coverage(evidence_dir, entries, problems)

    summary = {}
    summary_path = evidence_dir / 'summary.json'
    if summary_path.is_file():
        text = _read_text(summary_path, 'summary.json', problems)
        if text is not None:
            try:
                summary = json.loads(text)
            except json.JSONDecodeError as exc:
                problems.append(f'summary.json is not valid JSON: {exc}')
    if summary:
        for field in REQUIRED_SUMMARY_FIELDS:
            if field not in summary:
                problems.append(f'summary.json missing field: {field}')
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
        if 'cycles' in summary:
            _check_cycles(summary, build, problems)
        _check_cleanup(summary, problems)
        for name, sentinel in (summary.get('sentinels') or {}).items():
            if 'value' in sentinel:
                problems.append(f'sentinel {name} publishes its raw value')
            digest = sentinel.get('sha256_12')
            if digest is not None and not HEX12.fullmatch(str(digest)):
                problems.append(f'sentinel {name} has a malformed sha256_12')
        if summary_path.is_file():
            _check_report(evidence_dir, summary, problems)

    for path in _bundle_files(evidence_dir):
        text = _read_text(path, path.relative_to(evidence_dir).as_posix(), problems)
        if text is None:
            continue
        for pattern, label in SECRET_PATTERNS:
            if re.search(pattern, text):
                problems.append(f'{path.name} contains a {label}')

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
