"""Read-only audit of the BH-07 app-profile heap evidence bundle.

Checks that the published bundle is complete, hash-consistent, free of raw heap dumps
and free of credentials/sentinel values, and that the summary admits what it did and
did not measure. It never writes and never re-runs the measurement.

Usage: python verify_evidence.py [--dir docs/reviews/bh07/app_profile_heap_evidence]
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DIR = ROOT / 'docs/reviews/bh07/app_profile_heap_evidence'
REQUIRED_FILES = ('summary.json', 'report.md', 'run.log', 'hashes.sha256')
RAW_HEAP_SUFFIXES = ('.heapsnapshot', '.heapprofile', '.heaptimeline')
SECRET_PATTERNS = (
    (r'eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}', 'JWT token'),
    (r'bh07-http-pass', 'test account password'),
    (r'SERVICE_ROLE_KEY|SUPABASE_ANON_KEY\s*=', 'service/anon key name with value'),
    (r'postgresql://[^\s"]+:[^\s"]+@', 'database URL with credentials'),
)
REQUIRED_SUMMARY_FIELDS = ('gate', 'status', 'measurement_surface', 'oracle', 'tested_source_sha',
                           'cycles', 'cleanup', 'environment', 'sentinels')


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as fp:
        for chunk in iter(lambda: fp.read(1 << 20), b''):
            digest.update(chunk)
    return digest.hexdigest()


def verify(evidence_dir):
    problems = []
    evidence_dir = Path(evidence_dir)
    if not evidence_dir.is_dir():
        return [f'evidence dir missing: {evidence_dir}']

    for name in REQUIRED_FILES:
        if not (evidence_dir / name).is_file():
            problems.append(f'missing required file: {name}')

    for path in ROOT.rglob('*'):
        if path.is_file() and path.suffix in RAW_HEAP_SUFFIXES:
            problems.append(f'raw heap artifact present in repo: {path.relative_to(ROOT)}')

    for path in evidence_dir.rglob('*'):
        if path.is_file() and path.suffix in RAW_HEAP_SUFFIXES:
            problems.append(f'raw heap artifact published in the bundle: {path.name}')

    manifest_path = evidence_dir / 'hashes.sha256'
    if manifest_path.is_file():
        entries = 0
        for line in manifest_path.read_text(encoding='utf-8').splitlines():
            if not line.strip():
                continue
            digest, _, name = line.partition('  ')
            target = evidence_dir / name.strip()
            if not target.is_file():
                problems.append(f'manifest lists missing file: {name}')
                continue
            actual = sha256_file(target)
            if actual != digest:
                problems.append(f'hash mismatch: {name} ({digest[:12]} != {actual[:12]})')
            entries += 1
        if entries < 3:
            problems.append(f'manifest has only {entries} entries')

    summary_path = evidence_dir / 'summary.json'
    summary = {}
    if summary_path.is_file():
        try:
            summary = json.loads(summary_path.read_text(encoding='utf-8'))
        except json.JSONDecodeError as exc:
            problems.append(f'summary.json is not valid JSON: {exc}')
        for field in REQUIRED_SUMMARY_FIELDS:
            if field not in summary:
                problems.append(f'summary.json missing field: {field}')
        if summary:
            status = summary.get('status')
            if status not in ('RUN', 'NOT RUN', 'FAIL'):
                problems.append(f'unexpected status: {status!r}')
            if status == 'RUN' and summary.get('verdict') != 'PASS':
                problems.append('status RUN requires verdict PASS')
            if status == 'RUN':
                cleanup = summary.get('cleanup') or {}
                for field in ('ok', 'dump_dir_outside_repo', 'dumps_dir_removed', 'chrome_profile_dir_removed'):
                    if cleanup.get(field) is not True:
                        problems.append(f'status RUN requires verified heap dump cleanup: {field}')
                if cleanup.get('raw_snapshots_remaining') != 0:
                    problems.append('status RUN requires zero raw heap snapshots left on disk')
            build = (summary.get('environment') or {}).get('build') or {}
            if status == 'RUN' and build.get('mode') != 'profile':
                problems.append('status RUN requires a profile build')
            for name, sentinel in (summary.get('sentinels') or {}).items():
                if 'value' in sentinel:
                    problems.append(f'sentinel {name} publishes its raw value')
            for cycle in summary.get('cycles') or []:
                if not cycle.get('same_document'):
                    problems.append(f'cycle {cycle.get("cycle")} did not prove a single document')
                for epoch, scan in (cycle.get('epochs') or {}).items():
                    if 'size_bytes' not in scan or 'sha256_12' not in scan:
                        problems.append(f'cycle {cycle.get("cycle")} epoch {epoch} lacks snapshot metadata')

    for name in REQUIRED_FILES:
        path = evidence_dir / name
        if not path.is_file() or path.suffix not in ('.json', '.md', '.log', '.sha256'):
            continue
        content = path.read_text(encoding='utf-8', errors='replace')
        for pattern, label in SECRET_PATTERNS:
            if re.search(pattern, content):
                problems.append(f'{name} contains a {label}')
        if '\r' in content:
            problems.append(f'{name} is not LF-only')
        if content.startswith('\ufeff'):
            problems.append(f'{name} has a BOM')

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
          'free of raw heap dumps and credentials')
    return 0


if __name__ == '__main__':
    sys.exit(main())
