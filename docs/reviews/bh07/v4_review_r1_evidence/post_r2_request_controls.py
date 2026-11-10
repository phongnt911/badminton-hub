"""Supplementary controls against the immutable post-R2 positive input."""
import copy
import datetime
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
runner = ROOT / 'scripts/bh07_backup/run_v4_concurrent_rehearsal.py'
input_path = HERE / 'post_r2_capture_20261109.json'
destination = HERE / 'post_r2_request_capture_20261109.json'
if destination.exists():
    raise SystemExit('Refusing to overwrite evidence')
before = hashlib.sha256(runner.read_bytes()).hexdigest()
captured = json.loads(input_path.read_text(encoding='utf-8'))
expected = captured['source_sha256']['scripts\\bh07_backup\\run_v4_concurrent_rehearsal.py']
if before != expected:
    raise SystemExit('Runner changed since immutable positive capture')
from scripts.bh07_backup.run_v4_concurrent_rehearsal import validate_v4_rehearsal

base = captured['cases'][0]['summary']
serialization = dict(captured['digest_serialization'])
serialization['separators'] = tuple(serialization['separators']) if 'separators' in serialization else None
if serialization['separators'] is None:
    del serialization['separators']
cases = [('positive', copy.deepcopy(base))]
for name, action in (
    ('wrong_stored_request_id', lambda ev: ev['request'].__setitem__('request_id', 'c0000000-0000-4000-8000-000000000099')),
    ('wrong_stored_request_status', lambda ev: ev['request'].__setitem__('status', 500)),
    ('missing_stored_request', lambda ev: ev.pop('request')),
):
    summary = copy.deepcopy(base)
    op = summary['source_operations']['p0_precommit']
    action(op['row_evidence'])
    op['relational_digest'] = hashlib.sha256(json.dumps(op['row_evidence'], **serialization).encode()).hexdigest()
    summary['restored_verification']['restored_row_evidence'] = copy.deepcopy(op['row_evidence'])
    cases.append((name, summary))
summary = copy.deepcopy(base)
summary['restored_verification']['replay_evidence']['before_replay_fingerprint'] = 'not-a-digest'
summary['restored_verification']['replay_evidence']['after_replay_fingerprint'] = 'not-a-digest'
cases.append(('invalid_equal_replay_fingerprints', summary))
results = []
for name, summary in cases:
    try:
        result = validate_v4_rehearsal(summary, captured['source_fp'], captured['restored_fp'])
    except Exception as exc:
        result = {'exception_type': type(exc).__name__}
    results.append({'name': name, 'summary': summary, 'result': result})
if hashlib.sha256(runner.read_bytes()).hexdigest() != before:
    raise SystemExit('Source changed during capture')
payload = {'kind': 'new synthetic request/replay controls, no DB runtime',
           'captured_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
           'runner_sha256': before, 'input_sha256': hashlib.sha256(input_path.read_bytes()).hexdigest(),
           'source_fp': captured['source_fp'], 'restored_fp': captured['restored_fp'], 'cases': results}
destination.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + '\n', encoding='utf-8')
for item in results:
    print(json.dumps({'name': item['name'], 'result': item['result']}))
raise SystemExit(0 if results[0]['result'].get('ok') is True and
                 all(item['result'].get('ok') is False for item in results[1:]) else 1)
