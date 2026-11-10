"""Capture a NEW synthetic diagnostic fixture; never claim exact R1 replay/runtime."""
import contextlib
import datetime
import hashlib
import io
import json
import runpy
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
destination = HERE / 'diagnostic_capture_20261109.json'
if destination.exists():
    raise SystemExit('Refusing to overwrite captured evidence')
paths = [ROOT / 'scripts/bh07_backup/run_v4_concurrent_rehearsal.py',
         ROOT / 'scripts/bh07_backup/v4_concurrent_probe.py',
         HERE / 'probes.py']
before = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
stream = io.StringIO()
with contextlib.redirect_stdout(stream):
    scope = runpy.run_path(str(HERE / 'probes.py'))
after = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
if before != after:
    raise SystemExit('Source changed during capture; no evidence saved')
payload = {
    'kind': 'new synthetic diagnostic capture; not DB runtime or original R1 replay',
    'captured_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'source_sha256': before,
    'canonical_summary': scope['base'],
    'synthetic_source_fingerprint': scope['fp'](3),
    'synthetic_restored_fingerprint': scope['fp'](1),
    'results': json.loads(stream.getvalue()),
}
destination.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'saved': destination.name, 'cases': len(payload['results']),
                  'sha256': hashlib.sha256(destination.read_bytes()).hexdigest()}))
