"""Replay LGR3 against the current candidate; never opens a DB/browser."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from tests.test_bh07_ledger_heap_coverage import ORACLE, make_ledger_scans

classes = {
    'probe': {'rendered': False, 'distinctive': True, 'scope': 'control'},
    'expense_id': {'rendered': False, 'distinctive': True, 'scope': 'finance'},
    'expense_id_2': {'rendered': False, 'distinctive': True, 'scope': 'finance'},
    'ledger_transaction_id': {'rendered': False, 'distinctive': True, 'scope': 'finance'},
}
expenses = ['expense_id', 'expense_id_2']
results = {}
for name, active, baseline in (
    ('positive', expenses + ['ledger_transaction_id'], {'probe'}),
    ('missing_owner_ledger', expenses, {'probe'}),
    ('ledger_baseline_collision', expenses + ['ledger_transaction_id'], {'probe', 'ledger_transaction_id'}),
):
    scans = make_ledger_scans(classes, active, [], [], baseline_sentinels=baseline)
    verdict = ORACLE.decide(scans, ORACLE.derive_expectations(scans), cleanup_ok=True, mode='profile', strict=True)
    results[name] = {'verdict': verdict['verdict'], 'findings': verdict['findings']}
print(json.dumps(results, ensure_ascii=True, indent=2))
if results['positive']['verdict'] != 'PASS' or any(results[name]['verdict'] != 'FAIL' for name in results if name != 'positive'):
    raise SystemExit(1)
