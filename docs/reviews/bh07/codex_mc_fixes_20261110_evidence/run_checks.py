"""Codex self-checks only. No Docker or live service calls."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
FILES = [
    'scripts/bh07_backup/run_v4_concurrent_rehearsal.py',
    'scripts/bh07_backup/v4_concurrent_probe.py',
    'tests/test_bh07_v4_backup_concurrency.py',
    'tests/test_bh07_v4_runtime_collection.py',
]


def manifest():
    return {name: {
        'sha256': hashlib.sha256((ROOT / name).read_bytes()).hexdigest(),
        'git_blob': subprocess.check_output(['git', 'hash-object', '--path', name, name],
                                            cwd=ROOT).decode().strip(),
    } for name in FILES}


before = manifest()
environment = os.environ.copy()
environment['PATH'] = str(Path(sys.executable).parent) + os.pathsep + environment['PATH']
checks = [
    ('targeted', ['-m', 'unittest', 'test_bh07_v4_backup_concurrency',
                  'test_bh07_v4_codex_supplemental', 'test_bh07_v4_runtime_collection'], ROOT / 'tests'),
    ('full_python', ['-m', 'unittest', 'discover', '-s', 'tests'], ROOT),
    ('probe', ['scripts/bh07_backup/v4_concurrent_probe.py'], ROOT),
]
results = []
for label, arguments, cwd in checks:
    started = time.monotonic()
    with (OUT / (label + '.log')).open('wb') as log:
        process = subprocess.run([sys.executable, *arguments], cwd=cwd, env=environment,
                                 stdout=log, stderr=subprocess.STDOUT, timeout=360)
    result = {'name': label, 'command': [sys.executable, *arguments], 'cwd': str(cwd),
              'exit': process.returncode, 'seconds': round(time.monotonic() - started, 3)}
    results.append(result)
    print(json.dumps(result), flush=True)

after = manifest()
summary = {'base_sha': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip(),
           'candidate': 'uncommitted Codex MC1-MC6 fix, source hashes pinned below',
           'attribution': 'Codex implementer self-check, not independent runtime QA',
           'checks': results, 'source_before': before, 'source_after': after,
           'source_unchanged_during_checks': before == after,
           'runtime_Docker_HTTP_DB_dump_restore': 'NOT RUN', 'Flutter': 'NOT RUN: no SDK on PATH'}
(OUT / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
raise SystemExit(0 if before == after and all(r['exit'] == 0 for r in results) else 1)
