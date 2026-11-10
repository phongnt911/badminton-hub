import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from scripts.bh07_backup.v4_concurrent_probe import build_canonical_summary
from scripts.bh07_backup.run_v4_concurrent_rehearsal import validate_v4_rehearsal

TABLES = ('payments', 'club_transactions', 'audit_events', 'operation_requests')

def fp(rows):
    return {'public.' + table: {'rows': rows, 'sha256': 'a' * 64} for table in TABLES}

def result(name, summary, source, restored):
    try:
        verdict = validate_v4_rehearsal(summary, source, restored)
        return {'name': name, 'ok': verdict.get('ok'), 'verdict': verdict.get('verdict'),
                'findings': verdict.get('findings')}
    except Exception as exc:
        return {'name': name, 'error_type': type(exc).__name__}

base = build_canonical_summary()
cases = [result('author_positive', base, fp(3), fp(1)),
         result('missing_both_fingerprints', base, None, None),
         result('missing_source_fingerprint', base, None, fp(1)),
         result('source_count_999', base, fp(999), fp(1))]
bad = fp(1)
for table in bad.values():
    table['sha256'] = 'not-a-sha256'
cases.append(result('malformed_restored_hashes', base, fp(3), bad))

mutants = (
    ('wrong_numeric_amount', lambda s: s['source_operations']['p0_precommit'].__setitem__('amount_vnd', 99999)),
    ('duplicate_source_payment_id', lambda s: s['source_operations']['p1a_concurrent'].__setitem__('payment_id', s['source_operations']['p0_precommit']['payment_id'])),
    ('duplicate_source_request_id', lambda s: s['source_operations']['p1a_concurrent'].__setitem__('request_id', s['source_operations']['p0_precommit']['request_id'])),
    ('substituted_restored_payment_id', lambda s: s['restored_verification'].__setitem__('restored_payment_ids', ['other-payment'])),
    ('failed_status', lambda s: s.__setitem__('status', 'FAIL')),
    ('dirty_source', lambda s: s.__setitem__('git_dirty', True)),
    ('invalid_source_sha', lambda s: s.__setitem__('tested_source_sha', 'invalid')),
)
for name, mutate in mutants:
    summary = copy.deepcopy(base)
    mutate(summary)
    cases.append(result(name, summary, fp(3), fp(1)))
print(json.dumps(cases, ensure_ascii=True, indent=2))
