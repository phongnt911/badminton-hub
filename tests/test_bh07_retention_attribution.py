"""Unit tests for BH-07 retention attribution and coverage mapping audit.

Controls:
1. Verifies 8 residual risks in QA runtime evidence (review_runtime_b13e468).
2. Verifies exact retainer path structure (length 12, segmentationCache).
3. Verifies non-rendered peer sentinel drop (expense_id occurrences 1 -> 0).
4. Verifies mutant detection (peer leaks, count mismatch).
5. Verifies coverage map completeness across all private financial/identity models.
"""
import copy
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QA_SUMMARY_PATH = ROOT / 'docs/reviews/bh07/review_runtime_b13e468_evidence/summary.json'

import sys
sys.path.insert(0, str(ROOT / 'scripts/bh07_appheap'))
import audit_retention_attribution as auditor  # noqa: E402


class TestRetentionAttribution(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.qa_summary_path = QA_SUMMARY_PATH
        with open(cls.qa_summary_path, 'r', encoding='utf-8') as f:
            cls.qa_raw_data = json.load(f)

    def test_audit_real_qa_summary(self):
        """Audits the genuine b13e468 QA evidence bundle summary."""
        result = auditor.audit_summary_json(self.qa_summary_path)

        # Environment & metadata
        self.assertEqual(result['tested_source_sha'], 'b13e468d33e0d96437b58bb2da6088bff689b9eb')
        self.assertFalse(result['git_dirty'])
        self.assertTrue(result['environment']['consistent'])
        self.assertIn('Flutter 3.47.6', result['environment']['flutter'])
        self.assertIn('Chrome/155.', result['environment']['chrome'])
        self.assertEqual(result['environment']['build_mode'], 'profile')

        # 8 Residual risks
        self.assertEqual(result['residual_risks_count'], 8)
        self.assertEqual(len(result['residual_risks_matrix']), 8)

        # Peer sentinels and path properties for both cycles
        self.assertEqual(len(result['cycle_findings']), 2)
        for cf in result['cycle_findings']:
            self.assertTrue(cf['peer_sentinels_clean'], f"Cycle {cf['cycle']} peer sentinels must be clean")
            self.assertEqual(cf['rendered_path_length'], 12)
            self.assertTrue(cf['path_has_segmentation_cache'])
            self.assertTrue(cf['path_has_item_map'])
            self.assertTrue(cf['path_has_strings'])
            self.assertTrue(cf['path_has_hash_map_key'])

        # Attribution analysis
        attribution = auditor.analyze_attribution(result)
        verdict = attribution['attribution_verdict']
        self.assertTrue(verdict['rendered_title_retained'])
        self.assertIn('segmentationCache', verdict['primary_retainer_component'])
        self.assertFalse(verdict['app_model_retention'])
        self.assertTrue(verdict['peer_sentinel_proof_valid'])

    def test_mutant_peer_sentinel_leak(self):
        """If expense_id were still present/reachable at post_logout, peer_clean must be False."""
        mutant = copy.deepcopy(self.qa_raw_data)
        # Inject leak in cycle 1 post_logout
        c1_post_logout_s = mutant['cycles'][0]['epochs']['post_logout']['sentinels']
        c1_post_logout_s['expense_id']['present'] = True
        c1_post_logout_s['expense_id']['occurrences'] = 1
        c1_post_logout_p = mutant['cycles'][0]['epochs']['post_logout']['paths']
        c1_post_logout_p['expense_id']['reachable'] = True

        import tempfile
        with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False, encoding='utf-8') as tf:
            json.dump(mutant, tf)
            temp_path = tf.name

        try:
            result = auditor.audit_summary_json(temp_path)
            self.assertFalse(result['cycle_findings'][0]['peer_sentinels_clean'])
            attribution = auditor.analyze_attribution(result)
            self.assertFalse(attribution['attribution_verdict']['peer_sentinel_proof_valid'])
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_mutant_residual_risk_count_mismatch(self):
        """If residual risks count is not 8, auditor must raise ValueError."""
        mutant = copy.deepcopy(self.qa_raw_data)
        mutant['residual_risks'] = mutant['residual_risks'][:7]  # truncated

        import tempfile
        with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False, encoding='utf-8') as tf:
            json.dump(mutant, tf)
            temp_path = tf.name

        try:
            with self.assertRaises(ValueError) as ctx:
                auditor.audit_summary_json(temp_path)
            self.assertIn('Expected 8 residual risks', str(ctx.exception))
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_coverage_map_completeness(self):
        """Verifies coverage map inventory spans all private models and correctly identifies gaps."""
        cov = auditor.build_coverage_map_audit()
        summary = cov['summary']
        inventory = cov['inventory']

        self.assertEqual(summary['total_entities'], 11)
        # Check specific critical gaps
        entity_ids = {item['id']: item for item in inventory}

        self.assertIn('expense_ids', entity_ids)
        self.assertEqual(entity_ids['expense_ids']['measured_status'], 'VERIFIED_CLEAN_LOCAL_WEB_PROFILE')

        self.assertIn('expense_titles', entity_ids)
        self.assertEqual(entity_ids['expense_titles']['measured_status'], 'PARTIALLY_VERIFIED_RESIDUAL_ENGINE_CACHE')

        self.assertIn('session_charges', entity_ids)
        self.assertEqual(entity_ids['session_charges']['measured_status'], 'NOT_MEASURED_IN_APP_HEAP')

        self.assertIn('session_payments', entity_ids)
        self.assertEqual(entity_ids['session_payments']['measured_status'], 'NOT_MEASURED_IN_APP_HEAP')

        self.assertIn('club_bank_account', entity_ids)
        self.assertEqual(entity_ids['club_bank_account']['measured_status'], 'NOT_MEASURED_IN_APP_HEAP')

        self.assertIn('bank_receiver', entity_ids)
        self.assertEqual(entity_ids['bank_receiver']['measured_status'], 'NOT_MEASURED_IN_APP_HEAP')

        self.assertIn('club_ledger', entity_ids)
        self.assertEqual(entity_ids['club_ledger']['measured_status'], 'NOT_MEASURED_IN_APP_HEAP')

        self.assertIn('payment_instructions', entity_ids)
        self.assertEqual(entity_ids['payment_instructions']['measured_status'], 'NOT_MEASURED_IN_APP_HEAP')

        # At least 6 entities are NOT_MEASURED_IN_APP_HEAP, confirming full V2b §4.4 cannot be marked complete
        self.assertGreaterEqual(summary['not_measured_in_app_heap'], 6)


if __name__ == '__main__':
    unittest.main()
