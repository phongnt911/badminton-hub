"""Independent semantic controls with recomputed digests and frozen inputs."""
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
destination = HERE / 'post_r2_capture_20261109.json'
if destination.exists():
    raise SystemExit('Refusing to overwrite captured evidence')
paths = [ROOT / 'scripts/bh07_backup/run_v4_concurrent_rehearsal.py',
         ROOT / 'tests/test_bh07_v4_backup_concurrency.py', Path(__file__).resolve()]
before = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
scope = runpy.run_path(str(paths[1]))
validate = scope['validate_v4_rehearsal']
fixture = scope['V4FailClosedValidatorTests']()
fixture.setUp()
base, source, restored = fixture.valid_summary, fixture.valid_source_fingerprint, fixture.valid_restored_fingerprint
row = base['source_operations']['p0_precommit']['row_evidence']
expected = base['source_operations']['p0_precommit']['relational_digest']
options = ({'sort_keys': True, 'separators': (',', ':')}, {'sort_keys': True})
serialization = next((option for option in options if hashlib.sha256(
    json.dumps(row, **option).encode('utf-8')).hexdigest() == expected), None)
if serialization is None:
    raise SystemExit('Unknown canonical digest encoding; no semantic result claimed')

cases = [('positive', copy.deepcopy(base))]
value = copy.deepcopy(base)
value['writers_concurrency'].update(writer_a_started_epoch=100.10, writer_a_committed_epoch=100.20,
                                    writer_b_started_epoch=100.30, writer_b_committed_epoch=100.40)
cases.append(('serial_writers', value))
value = copy.deepcopy(base)
value['cleanup']['resources_verified_absent'] = ['unrelated-src-db', 'unrelated-target-db', 'unrelated-net']
cases.append(('unrelated_cleanup', value))
for name, section, field, changed in (
    ('ledger_amount_wrong_valid_digest', 'ledger', 'amount', 99999),
    ('audit_request_wrong_valid_digest', 'audit', 'request_id', 'c0000000-0000-4000-8000-000000000099'),
    ('request_payment_wrong_valid_digest', 'request', 'payment_id', '60000000-0000-4000-8000-000000000099'),
):
    value = copy.deepcopy(base)
    op = value['source_operations']['p0_precommit']
    op['row_evidence'][section][field] = changed
    op['relational_digest'] = hashlib.sha256(json.dumps(op['row_evidence'], **serialization).encode('utf-8')).hexdigest()
    value['restored_verification']['restored_row_evidence'] = copy.deepcopy(op['row_evidence'])
    cases.append((name, value))

results = []
for name, summary in cases:
    try:
        result = validate(summary, source, restored)
    except Exception as exc:
        result = {'exception_type': type(exc).__name__}
    results.append({'name': name, 'summary': summary, 'result': result})
after = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
if before != after:
    raise SystemExit('Source changed during capture')
payload = {'kind': 'new synthetic post-correction-2 controls; not DB runtime',
           'captured_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
           'source_sha256': before, 'source_fp': source, 'restored_fp': restored,
           'digest_serialization': serialization, 'cases': results}
destination.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + '\n', encoding='utf-8')
for item in results:
    print(json.dumps({'name': item['name'], 'result': item['result']}))
raise SystemExit(0 if results[0]['result'].get('ok') is True and
                 all(item['result'].get('ok') is False for item in results[1:]) else 1)
