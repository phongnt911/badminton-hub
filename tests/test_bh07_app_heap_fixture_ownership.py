"""Controls for the run-only expense fixture the measurement creates (review 9fadecc RP1).

The run widens its gated set with one expense row of its own. The old helper adopted any
posted row that happened to carry the fixed id, and the `finally` block then deleted it
without ever having posted it: a leftover or foreign local row could be destroyed, and a
run that never created the row could still report a verified cleanup. These controls drive
every ownership path against an in-memory PostgREST stub (no database, no network).

Run: python -m unittest tests.test_bh07_app_heap_fixture_ownership -v
"""
import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTROLS = ROOT / 'scripts/bh07_appheap/fixture_controls.js'
PROBE = ROOT / 'docs/reviews/bh07/review_9fadecc_evidence/fixture_probe.js'
CASES = ('collision_refused', 'create_then_clean', 'post_rejected_row_committed',
         'post_rejected_row_absent', 'delete_rejected', 'remote_endpoint_refused')


class FixtureOwnershipControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = subprocess.run(['node', str(CONTROLS), '--self-test'],
                                    capture_output=True, text=True, cwd=ROOT)

    def test_every_ownership_path_is_covered(self):
        self.assertEqual(self.result.returncode, 0, self.result.stdout + self.result.stderr)
        for name in CASES:
            self.assertIn(f'ok {name}', self.result.stdout, self.result.stdout)
        self.assertNotIn('FAIL', self.result.stdout, self.result.stdout)
        self.assertIn('controls passed', self.result.stdout)


class ReviewerFixtureProbeReplay(unittest.TestCase):
    """Replay the reviewer's fixture probe unedited; only its observations change.

    The probe stubs a pre-existing posted row carrying the fixture id and used to print
    `delete_calls:1, cleanup_result:true`: the exact behaviour RP1 reported. It must now
    show a refusal, no POST, no DELETE, the row still present, and a leaked prefix of a
    long private value detected by the publication sanitizer (RP3).
    """

    @classmethod
    def setUpClass(cls):
        result = subprocess.run(['node', str(PROBE)], capture_output=True, text=True, cwd=ROOT)
        if result.returncode != 0:
            raise AssertionError(f'reviewer fixture probe failed: {result.stdout}{result.stderr}')
        cls.report = json.loads(result.stdout)

    def test_preexisting_row_is_not_adopted_or_deleted(self):
        self.assertEqual(self.report['post_calls'], 0, self.report)
        self.assertEqual(self.report['delete_calls'], 0, self.report)

    def test_preexisting_row_survives(self):
        self.assertIs(self.report['remaining'], True, self.report)

    def test_cleanup_is_not_reported_as_verified(self):
        cleanup = self.report['cleanup_result']
        self.assertIs(cleanup['removed'], False, cleanup)
        self.assertIs(cleanup['verified_absent'], False, cleanup)

    def test_truncated_private_label_is_detected(self):
        # The sanitizer now treats a usable prefix of a private value as private.
        self.assertIn('label', self.report['truncated_private_label_sanitizer_findings'],
                      self.report)


if __name__ == '__main__':
    unittest.main()
