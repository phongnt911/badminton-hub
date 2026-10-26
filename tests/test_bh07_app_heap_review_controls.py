"""Replay of the reviewer's adversarial probes with unchanged expectations (AH1-AH4).

`docs/reviews/bh07/review_8914b2f_evidence/probes.py` is the reviewer's file, replayed
verbatim: the point is that the same inputs are now rejected, not that the probe was
edited to agree with the fix.

Run: python -m unittest tests.test_bh07_app_heap_review_controls -v
"""
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / 'docs/reviews/bh07/review_8914b2f_evidence/probes.py'

REJECTIONS = {
    'crlf': 'CR',
    'invalid_utf8': 'UTF-8',
    'unmanifested_secret_extra': 'manifest',
    'zero_cycles': 'cycle',
    'missing_epoch': 'post_actor',
    'leaked_failed_scan': 'verdict',
}


class ReviewerProbeReplay(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        result = subprocess.run([sys.executable, '-X', 'utf8', str(PROBE)],
                                capture_output=True, text=True, cwd=ROOT)
        if result.returncode != 0:
            raise AssertionError(f'reviewer probe failed: {result.stdout}{result.stderr}')
        cls.report = json.loads(result.stdout)

    def test_invalid_snapshot_is_not_clean(self):
        case = self.report['invalid_snapshot']
        self.assertFalse(case['valid_json'])
        self.assertFalse(case['scan']['ok'], case['scan'])
        self.assertIsNone(case['scan']['sentinels']['bank']['present'])
        self.assertEqual(case['decision']['verdict'], 'FAIL')

    def test_full_cycle_with_invalid_snapshot_fails(self):
        self.assertEqual(self.report['full_cycle_with_invalid_snapshot']['verdict'], 'FAIL')

    def test_auditor_cases_are_rejected(self):
        for case, needle in REJECTIONS.items():
            with self.subTest(case=case):
                problems = self.report[case]
                self.assertTrue(problems, f'{case}: auditor accepted the bundle')
                self.assertTrue(any(needle.lower() in p.lower() for p in problems),
                                f'{case}: expected {needle!r} in {problems}')


if __name__ == '__main__':
    unittest.main()
