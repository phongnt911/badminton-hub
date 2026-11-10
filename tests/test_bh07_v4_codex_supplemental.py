"""Owner-authorized fixes for the final V4 request/probe findings."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import test_bh07_v4_backup_concurrency as existing


class CodexStoredRequestRegression(unittest.TestCase):
    def setUp(self):
        fixture = existing.V4FailClosedValidatorTests()
        fixture.setUp()
        self.summary = copy.deepcopy(fixture.valid_summary)
        self.source = copy.deepcopy(fixture.valid_source_fingerprint)
        self.restored = copy.deepcopy(fixture.valid_restored_fingerprint)

    def check_changed_request(self, label, change):
        summary = copy.deepcopy(self.summary)
        operation = summary['source_operations'][label]
        change(operation['row_evidence']['request'])
        operation['relational_digest'] = hashlib.sha256(json.dumps(
            operation['row_evidence'], sort_keys=True, separators=(',', ':')
        ).encode('utf-8')).hexdigest()
        if label == 'p0_precommit':
            summary['restored_verification']['restored_row_evidence'] = copy.deepcopy(operation['row_evidence'])
        result = existing.validate_v4_rehearsal(summary, self.source, self.restored)
        self.assertIs(result['ok'], False, result)
        self.assertEqual(result['verdict'], 'FAIL', result)

    def test_valid_receipt_stays_valid(self):
        result = existing.validate_v4_rehearsal(self.summary, self.source, self.restored)
        self.assertIs(result['ok'], True, result)

    def test_stored_result_is_required_for_every_operation(self):
        for label in self.summary['source_operations']:
            with self.subTest(operation=label):
                self.check_changed_request(label, lambda request: request.pop('result'))

    def test_stored_result_must_be_an_object(self):
        for invalid in (None, [], False, 'confirmed', {}):
            with self.subTest(result=invalid):
                self.check_changed_request('p0_precommit', lambda request: request.__setitem__('result', invalid))

    def test_stored_status_must_be_confirmed(self):
        for label in self.summary['source_operations']:
            for invalid in ('rejected', 'submitted', None, 500):
                with self.subTest(operation=label, status=invalid):
                    self.check_changed_request(label, lambda request: request['result'].__setitem__('status', invalid))

    def test_request_operation_must_match_cash_workload(self):
        for label in self.summary['source_operations']:
            for invalid in ('confirm_payment', 'reverse_payment', None):
                with self.subTest(operation=label, rpc=invalid):
                    self.check_changed_request(label, lambda request: request.__setitem__('operation', invalid))

    def test_standalone_probe_passes_its_positive_and_mutants(self):
        completed = subprocess.run(
            [sys.executable, str(ROOT / 'scripts/bh07_backup/v4_concurrent_probe.py')],
            cwd=ROOT, capture_output=True, text=True, encoding='utf-8', errors='strict', timeout=30,
        )
        self.assertEqual(completed.returncode, 0, (completed.stdout + completed.stderr)[-3000:])
        self.assertIn('controls passed', completed.stdout)


if __name__ == '__main__':
    unittest.main()
