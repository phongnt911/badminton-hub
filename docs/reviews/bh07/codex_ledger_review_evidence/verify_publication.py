"""Verify exact runtime payload bytes in the Git index without changing the bundle."""
import hashlib
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parents[4]
relative = Path('docs/reviews/bh07/ledger_heap_20261108_codex_evidence')
bundle = root / relative
manifest = (bundle / 'hashes.sha256').read_bytes()
entries = dict(line.split() for line in manifest.decode('utf-8').splitlines())
assert set(entries.values()) == {'summary.json', 'report.md', 'run.log'}
for expected, name in entries.items():
    file = relative / name
    indexed = subprocess.check_output(['git', 'show', ':' + file.as_posix()], cwd=root)
    assert hashlib.sha256(indexed).hexdigest() == expected, name
    assert indexed == (root / file).read_bytes(), name
indexed_manifest = subprocess.check_output(['git', 'show', ':' + (relative / 'hashes.sha256').as_posix()], cwd=root)
assert indexed_manifest == manifest
print('PASS: 3 payload SHA-256 hashes and manifest match working files and staged Git blobs')
