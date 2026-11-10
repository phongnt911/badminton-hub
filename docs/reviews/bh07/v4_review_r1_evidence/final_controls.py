"""Frozen semantic controls for the final candidate; no DB execution."""
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
destination = HERE / 'final_capture_20261109.json'
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
op0 = base['source_operations']['p0_precommit']
options = ({'sort_keys': True, 'separators': (',', ':')}, {'sort_keys': True})
serialization = next((option for option in options if hashlib.sha256(
    json.dumps(op0['row_evidence'], **option).encode('utf-8')).hexdigest() == op0['relational_digest']), None)
if serialization is None:
    raise SystemExit('Unknown canonical digest encoding')
cases = [('positive', copy.deepcopy(base))]
for name, mutate in (
    ('stored_result_wrong_payment', lambda e: e['request']['result'].__setitem__('payment_id', '60000000-0000-4000-8000-000000000099')),
    ('stored_result_wrong_amount', lambda e: e['request']['result'].__setitem__('amount_vnd', 99999)),
    ('stored_result_wrong_status', lambda e: e['request']['result'].__setitem__('status', 'rejected')),
    ('missing_stored_result', lambda e: e['request'].pop('result')),
    ('wrong_request_operation', lambda e: e['request'].__setitem__('operation', 'confirm_payment')),
    ('wrong_ledger_amount', lambda e: e['ledger'].__setitem__('amount', 99999)),
    ('wrong_audit_request', lambda e: e['audit'].__setitem__('request_id', 'c0000000-0000-4000-8000-000000000099')),
):
    summary = copy.deepcopy(base)
    op = summary['source_operations']['p0_precommit']
    mutate(op['row_evidence'])
    op['relational_digest'] = hashlib.sha256(json.dumps(op['row_evidence'], **serialization).encode('utf-8')).hexdigest()
    summary['restored_verification']['restored_row_evidence'] = copy.deepcopy(op['row_evidence'])
    cases.append((name, summary))
for name, changed in [('invalid_equal_replay_digest', 'not-a-digest'), ('valid_but_wrong_equal_replay_digest', 'b' * 64)]:
    summary = copy.deepcopy(base)
    replay = summary['restored_verification']['replay_evidence']
    replay['before_replay_fingerprint'] = changed
    replay['after_replay_fingerprint'] = changed
    cases.append((name, summary))
summary = copy.deepcopy(base)
summary['restored_verification']['replay_evidence']['replay_payment_id'] = '60000000-0000-4000-8000-000000000099'
cases.append(('wrong_replay_response_payment', summary))
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
payload = {'kind': 'final candidate synthetic controls; not DB runtime',
           'captured_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
           'source_sha256': before, 'source_fp': source, 'restored_fp': restored,
           'digest_serialization': serialization, 'cases': results}
destination.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + '\n', encoding='utf-8')
for item in results:
    print(json.dumps({'name': item['name'], 'result': item['result']}))
raise SystemExit(0 if results[0]['result'].get('ok') is True and
                 all(item['result'].get('ok') is False for item in results[1:]) else 1)
