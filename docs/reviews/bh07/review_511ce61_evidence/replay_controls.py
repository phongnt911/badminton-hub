"""Replay the original reviewer controls without changing source or historical evidence."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import runpy
import subprocess

ROOT = Path(__file__).resolve().parents[4]
tracked = subprocess.check_output(
    ['git', 'ls-files', 'docs/reviews/bh07/*evidence*/*'], cwd=ROOT, text=True
).splitlines()
def digests():
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
            for name in tracked if (ROOT / name).is_file()}
before = digests()
original_write_text = Path.write_text
output = io.StringIO()
try:
    # Match the handoff's Windows adapter: original probe payloads must be UTF-8 LF.
    Path.write_text = lambda self, data, *a, **k: self.write_bytes(
        data.encode('utf-8') if isinstance(data, str) else data)
    with contextlib.redirect_stdout(output):
        runpy.run_path(str(ROOT / 'docs/reviews/bh07/review_6f59f5e_evidence/probes.py'))
finally:
    Path.write_text = original_write_text
results = json.loads(output.getvalue())
readonly = before == digests()
correct = len(results) == 6 and all(
    record['auditor_exit'] == record['expected_auditor_exit']
    for record in results.values())
record = {'source': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT,
                                           text=True).strip(),
          'tracked_evidence_files_checked': len(before), 'historical_readonly': readonly,
          'all_six_controls_match': correct, 'controls': results}
(ROOT / 'build/review511-controls.json').write_bytes(
    (json.dumps(record, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
print(json.dumps(record, ensure_ascii=False, indent=2))
raise SystemExit(0 if correct and readonly else 1)
