"""Replay LGR7 using cloned bundles and the actual auditor CLI."""
import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from tests.test_bh07_ledger_heap_coverage import TestLedgerCoverageAuditorCLI

test = TestLedgerCoverageAuditorCLI()
test.setUp()
base = test._make_positive_ledger_data()
base['coverage_profile'] = 'ledger'
parent_keys = [key for key in base['cleanup'] if key.startswith(('disposable_bank_', 'disposable_club_'))]
cases = {'positive': copy.deepcopy(base)}
missing = copy.deepcopy(base)
for key in parent_keys:
    missing['cleanup'].pop(key)
cases['parent_receipts_omitted'] = missing
false_parent = copy.deepcopy(base)
false_parent['cleanup'].update(disposable_club_created=False, disposable_club_removed=False,
    disposable_club_verified_absent=False, disposable_bank_created=False,
    disposable_bank_removed=False, disposable_bank_verified_absent=False)
cases['parent_receipts_false'] = false_parent
bank_failure = copy.deepcopy(base)
bank_failure['cleanup'].update(disposable_bank_created=True, disposable_bank_removed=False,
    disposable_bank_verified_absent=False, disposable_bank_error='synthetic_parent_cleanup_failure')
cases['bank_cleanup_failure'] = bank_failure
results = {}
for name, data in cases.items():
    result = test._clone_and_audit(data)
    results[name] = {'exit': result.returncode, 'output': result.stdout.strip()}
print(json.dumps(results, ensure_ascii=True, indent=2))
if results['positive']['exit'] != 0 or any(results[name]['exit'] != 1 for name in results if name != 'positive'):
    raise SystemExit(1)
