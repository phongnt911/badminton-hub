"""Tests for BH-07 bank and receiver owner graph reachability and baseline discrimination.

Verifies the reviewer owner graph probe:
- Positive control: bank_positive -> oracle PASS, auditor exit 0
- Mutant 1: rendered_owner_values_unreachable -> oracle FAIL, auditor exit 1
- Mutant 2: rendered_baseline_path_retained -> oracle FAIL, auditor exit 1
"""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
PROBE_PATH = ROOT / 'docs/reviews/bh07/bank_receiver_heap_review_r2_evidence/owner_graph_probe.py'


class TestBankOwnerGraphProbe(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Inspect and import reviewer probe without modifying it
        cls.spec = importlib.util.spec_from_file_location('owner_graph_probe', PROBE_PATH)
        cls.probe = importlib.util.module_from_spec(cls.spec)
        cls.spec.loader.exec_module(cls.probe)
        cls.results = cls.probe.results

    def test_probe_root_matches_repo_root(self):
        """Ensure probe root resolves to repository root."""
        self.assertEqual(self.probe.root.resolve(), ROOT.resolve())

    def test_bank_positive_control(self):
        """Positive control: valid owner graph paths and baseline discrimination pass."""
        case = self.results['bank_positive']
        self.assertEqual(case['oracle_verdict'], 'PASS', f"Expected PASS, output:\n{case['output']}")
        self.assertEqual(case['auditor_exit'], 0, f"Expected auditor exit 0, output:\n{case['output']}")

    def test_rendered_owner_values_unreachable_mutant(self):
        """Mutant 1: rendered bank/receiver present in count but unreachable at Owner fails."""
        case = self.results['rendered_owner_values_unreachable']
        self.assertEqual(case['oracle_verdict'], 'FAIL', f"Expected FAIL, output:\n{case['output']}")
        self.assertEqual(case['auditor_exit'], 1, f"Expected auditor exit 1, output:\n{case['output']}")

    def test_rendered_baseline_path_retained_mutant(self):
        """Mutant 2: rendered bank/receiver path reachable at baseline despite count 0 fails."""
        case = self.results['rendered_baseline_path_retained']
        self.assertEqual(case['oracle_verdict'], 'FAIL', f"Expected FAIL, output:\n{case['output']}")
        self.assertEqual(case['auditor_exit'], 1, f"Expected auditor exit 1, output:\n{case['output']}")


if __name__ == '__main__':
    unittest.main()
