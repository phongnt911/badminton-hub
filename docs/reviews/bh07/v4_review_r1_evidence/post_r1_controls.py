"""New frozen synthetic controls after correction 1; no DB/runtime claim."""
import copy
import datetime
import hashlib
import json
import runpy
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
from scripts.bh07_backup.run_v4_concurrent_rehearsal import validate_v4_rehearsal

destination = HERE / 'post_r1_capture_20261109.json'
if destination.exists():
    raise SystemExit('Refusing to overwrite captured evidence')
paths = [ROOT / 'scripts/bh07_backup/run_v4_concurrent_rehearsal.py',
         ROOT / 'tests/test_bh07_v4_backup_concurrency.py', Path(__file__).resolve()]
before = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
scope = runpy.run_path(str(paths[1]))
fixture = scope['V4FailClosedValidatorTests']()
fixture.setUp()
base = fixture.valid_summary
source = fixture.valid_source_fingerprint
restored = fixture.valid_restored_fingerprint
cases = [('positive', copy.deepcopy(base), copy.deepcopy(source), copy.deepcopy(restored))]

for name, field in [('duplicate_ledger_id', 'transaction_id'), ('duplicate_audit_id', 'audit_event_id')]:
    value = copy.deepcopy(base)
    value['source_operations']['p1a_concurrent'][field] = value['source_operations']['p0_precommit'][field]
    cases.append((name, value, copy.deepcopy(source), copy.deepcopy(restored)))
value = copy.deepcopy(base)
value['writers_concurrency'].update(writer_a_started_epoch=100.10, writer_a_committed_epoch=100.20,
                                    writer_b_started_epoch=100.30, writer_b_committed_epoch=100.40)
cases.append(('serial_writers_inside_dump', value, copy.deepcopy(source), copy.deepcopy(restored)))
value = copy.deepcopy(base)
value['cleanup']['resources_verified_absent'] = ['unrelated-src-db', 'unrelated-target-db', 'unrelated-net']
cases.append(('unrelated_cleanup_resources', value, copy.deepcopy(source), copy.deepcopy(restored)))
for name, count in [('boolean_restored_counts', True), ('float_restored_counts', 1.0)]:
    values = copy.deepcopy(restored)
    for table in values.values():
        table['rows'] = count
    cases.append((name, copy.deepcopy(base), copy.deepcopy(source), values))

results = []
for name, summary, src, dst in cases:
    try:
        result = validate_v4_rehearsal(summary, src, dst)
    except Exception as exc:
        result = {'exception_type': type(exc).__name__}
    results.append({'name': name, 'summary': summary, 'source_fp': src, 'restored_fp': dst,
                    'result': result})
after = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
if before != after:
    raise SystemExit('Source changed during capture')
payload = {'kind': 'new synthetic post-correction-1 controls; not DB runtime',
           'captured_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
           'source_sha256': before, 'cases': results}
destination.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + '\n', encoding='utf-8')
for item in results:
    print(json.dumps({'name': item['name'], 'result': item['result']}))
good = results[0]['result'].get('ok') is True
blocked = all(item['result'].get('ok') is False for item in results[1:])
raise SystemExit(0 if good and blocked else 1)
