"""Unit tests for BH-07 retention attribution and coverage mapping audit.

Controls:
1. Verifies 8 residual risks in QA runtime evidence (review_runtime_b13e468).
2. Verifies exact retainer path structure (length 12, segmentationCache).
3. Verifies non-rendered peer sentinel drop (expense_id occurrences 1 -> 0).
4. Verifies mutant detection (AT1: fail-closed on peer leak, bad env, missing paths).
5. Verifies probe replay with original reviewer cases (positive -> exit 0; 3 mutants -> exit 1, UNATTRIBUTED).
6. Verifies extra controls replay from review_eda1ead (4 new mutants -> exit 1, UNATTRIBUTED).
7. Verifies AT2 consistency: no app-wide clean claims, observed_peer_ids_absent=True, app_wide_retention_proven=False.
8. Verifies coverage map field mapping against real Dart models (AT3).
9. Verifies auth_listeners marked NOT RUN on Web heap object graph (AT3).
"""
import copy
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QA_SUMMARY_PATH = ROOT / 'docs/reviews/bh07/review_runtime_b13e468_evidence/summary.json'

import sys
sys.path.insert(0, str(ROOT / 'scripts/bh07_appheap'))
import audit_retention_attribution as auditor  # noqa: E402


class TestRetentionAttribution(unittest.TestCase):

    def test_round_two_closure_probe_is_fail_closed(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / 'docs/reviews/bh07/review_5226a3d_evidence/closure_controls.py')],
            cwd=ROOT, capture_output=True, text=True, encoding='utf-8',
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        cases = json.loads(result.stdout)
        self.assertEqual(cases['positive']['exit'], 0)
        self.assertTrue(cases['positive']['verdict']['valid'])
        for name in ('duplicate_cycle_payload', 'rendered_presence_contradiction', 'risk_path_hash_mismatch'):
            with self.subTest(case=name):
                self.assertEqual(cases[name]['exit'], 1)
                self.assertFalse(cases[name]['verdict']['valid'])
                self.assertEqual(cases[name]['verdict']['primary_retainer_component'], 'UNATTRIBUTED')

    def test_cycle_actor_and_record_links_are_validated(self):
        for case in ('wrong_actor', 'risk_root_mismatch', 'risk_class_mismatch',
                     'scan_not_usable', 'path_frames_hash_mismatch', 'rendered_scope_mismatch'):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as td:
                data = copy.deepcopy(self.qa_raw_data)
                epoch = data['cycles'][0]['epochs']['post_logout']
                if case == 'wrong_actor':
                    data['cycles'][1]['actor'] = 'cohost'
                elif case == 'risk_root_mismatch':
                    data['residual_risks'][0]['root_kind'] = 'global_handles'
                elif case == 'risk_class_mismatch':
                    data['residual_risks'][0]['class'] = 'identity'
                elif case == 'scan_not_usable':
                    epoch['ok'] = False
                elif case == 'path_frames_hash_mismatch':
                    epoch['paths']['expense']['frames'][-1] = 'property:other -> string'
                elif case == 'rendered_scope_mismatch':
                    epoch['sentinels']['expense']['scope'] = 'identity'
                source = Path(td) / 'input.json'
                source.write_text(json.dumps(data), encoding='utf-8')
                output = Path(td) / 'out'
                run = subprocess.run(
                    [sys.executable, str(ROOT / 'scripts/bh07_appheap/audit_retention_attribution.py'),
                     '--summary', str(source), '--out-dir', str(output)],
                    capture_output=True, text=True, encoding='utf-8',
                )
                self.assertEqual(run.returncode, 1, run.stdout + run.stderr)
                verdict = json.loads((output / 'attribution_audit.json').read_text())['attribution']['attribution_verdict']
                self.assertFalse(verdict['valid'])
                self.assertFalse(verdict['app_wide_retention_proven'])
                self.assertEqual(verdict['status'], 'FAIL')

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
            self.assertTrue(cf['rendered_paths_valid'], f"Cycle {cf['cycle']} rendered paths must be valid")

        # Attribution analysis
        attribution = auditor.analyze_attribution(result)
        verdict = attribution['attribution_verdict']
        self.assertTrue(verdict['valid'])
        self.assertEqual(verdict['status'], 'SUPPORTED_HYPOTHESIS_WITH_LIMITS')
        self.assertTrue(verdict['rendered_title_retained'])
        self.assertIn('segmentationCache', verdict['primary_retainer_component'])
        self.assertTrue(verdict['peer_sentinel_proof_valid'])

        # AT2: No boolean False for entire app; scoped peer IDs verified
        self.assertTrue(verdict['observed_peer_ids_absent'])
        self.assertFalse(verdict['app_wide_retention_proven'])
        self.assertNotEqual(verdict.get('app_model_retention'), False)
        self.assertEqual(verdict.get('app_model_retention'), 'SCOPED_TWO_IDS_CLEAN_APP_WIDE_UNKNOWN')

        # Separation of concerns: observed, supported_hypothesis, unknown_and_limits
        self.assertIn('observed', attribution)
        self.assertIn('supported_hypothesis', attribution)
        self.assertIn('unknown_and_limits', attribution)
        self.assertTrue(attribution['unknown_and_limits']['secondary_app_paths_possible'])
        self.assertEqual(attribution['unknown_and_limits']['residual_risk_official_classification'], 'unattributed')

    def test_reviewer_probes_cases_fail_closed(self):
        """AT1: All 3 mutant cases from review_37b4954 probe must fail-closed (exit 1, UNATTRIBUTED)."""
        cases = ['positive', 'peer_retained', 'wrong_environment', 'missing_rendered_paths']
        for case in cases:
            s = copy.deepcopy(self.qa_raw_data)
            if case == 'peer_retained':
                e = s['cycles'][0]['epochs']['post_logout']
                e['sentinels']['expense_id'].update(present=True, occurrences=1)
                e['paths']['expense_id']['reachable'] = True
            elif case == 'wrong_environment':
                s['environment']['flutter'] = 'Wrong SDK'
                s['environment']['build']['mode'] = 'debug'
            elif case == 'missing_rendered_paths':
                for c in s['cycles']:
                    for e in c['epochs'].values():
                        e['paths'].pop('expense', None)
                        e['paths'].pop('expense2', None)

            with tempfile.TemporaryDirectory() as td:
                p = Path(td) / 'input.json'
                p.write_text(json.dumps(s), encoding='utf-8')
                v = auditor.audit_summary_json(p)
                claim = auditor.analyze_attribution(v)
                run = subprocess.run(
                    [sys.executable, str(ROOT / 'scripts/bh07_appheap/audit_retention_attribution.py'),
                     '--summary', str(p), '--out-dir', str(Path(td) / 'out')],
                    capture_output=True, text=True, encoding='utf-8'
                )

                verdict = claim['attribution_verdict']
                if case == 'positive':
                    self.assertEqual(run.returncode, 0, f"Positive control must exit 0: {run.stderr}")
                    self.assertTrue(verdict['valid'])
                    self.assertIn('segmentationCache', verdict['primary_retainer_component'])
                    self.assertTrue(verdict['observed_peer_ids_absent'])
                    self.assertFalse(verdict['app_wide_retention_proven'])
                else:
                    self.assertNotEqual(run.returncode, 0, f"Mutant {case} must exit non-zero: exit={run.returncode}")
                    self.assertFalse(verdict['valid'], f"Mutant {case} must not have valid verdict")
                    self.assertEqual(verdict['status'], 'FAIL')
                    self.assertEqual(verdict['primary_retainer_component'], 'UNATTRIBUTED')
                    self.assertEqual(verdict['app_model_retention'], 'UNKNOWN_OR_UNCLEAN')

    def test_reviewer_extra_controls_cases_fail_closed(self):
        """AT1: All 4 mutant cases from review_eda1ead extra_controls.py must fail-closed (exit 1, UNATTRIBUTED)."""
        mutant_names = [
            'expense2_path_missing',
            'post_actor_paths_missing',
            'duplicate_risk_record',
            'missing_post_logout_occurrences',
        ]
        for name in mutant_names:
            s = copy.deepcopy(self.qa_raw_data)
            if name == 'expense2_path_missing':
                for c in s['cycles']:
                    for e in ['post_logout', 'post_actor']:
                        c['epochs'][e]['paths'].pop('expense2', None)
            elif name == 'post_actor_paths_missing':
                for c in s['cycles']:
                    for key in ['expense', 'expense2']:
                        c['epochs']['post_actor']['paths'].pop(key, None)
            elif name == 'duplicate_risk_record':
                s['residual_risks'] = [copy.deepcopy(s['residual_risks'][0]) for _ in range(8)]
            elif name == 'missing_post_logout_occurrences':
                for c in s['cycles']:
                    for k in ['expense_id', 'expense_id_2']:
                        c['epochs']['post_logout']['sentinels'][k].pop('occurrences', None)

            with tempfile.TemporaryDirectory() as td:
                p = Path(td) / 'input.json'
                p.write_text(json.dumps(s), encoding='utf-8')
                v = auditor.audit_summary_json(p)
                claim = auditor.analyze_attribution(v)
                run = subprocess.run(
                    [sys.executable, str(ROOT / 'scripts/bh07_appheap/audit_retention_attribution.py'),
                     '--summary', str(p), '--out-dir', str(Path(td) / 'out')],
                    capture_output=True, text=True, encoding='utf-8'
                )

                verdict = claim['attribution_verdict']
                self.assertNotEqual(run.returncode, 0, f"Extra control {name} must exit non-zero: exit={run.returncode}")
                self.assertFalse(verdict['valid'], f"Extra control {name} must not have valid verdict")
                self.assertEqual(verdict['status'], 'FAIL')
                self.assertEqual(verdict['primary_retainer_component'], 'UNATTRIBUTED')
                self.assertEqual(verdict['app_model_retention'], 'UNKNOWN_OR_UNCLEAN')

    def test_coverage_map_completeness(self):
        """Verifies coverage map inventory spans all private models and correctly identifies gaps."""
        cov = auditor.build_coverage_map_audit()
        summary = cov['summary']
        inventory = cov['inventory']

        self.assertEqual(summary['total_entities'], 11)
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

        # AT3: auth_listeners must be NOT_RUN_WEB_HEAP_OBJECT_GRAPH
        self.assertIn('auth_listeners', entity_ids)
        self.assertEqual(entity_ids['auth_listeners']['measured_status'], 'NOT_RUN_WEB_HEAP_OBJECT_GRAPH')

        # At least 7 entities are not verified on Web heap
        self.assertGreaterEqual(summary['not_measured_in_app_heap'] + summary['not_run_web_heap_object_graph'], 7)

    def test_coverage_map_real_model_fields(self):
        """AT3: Verify inventory fields exist in actual Dart models (no hallucinated fields)."""
        finance_dart = (ROOT / 'lib/models/finance.dart').read_text(encoding='utf-8')
        club_dart = (ROOT / 'lib/models/club.dart').read_text(encoding='utf-8')

        # FinanceCharge
        self.assertIn('final String playerId;', finance_dart)
        self.assertIn('final String? displayName;', finance_dart)
        self.assertIn('final int amountDueVnd;', finance_dart)
        self.assertNotIn('chargeId', finance_dart.split('class FinanceCharge')[1].split('}')[0])
        self.assertNotIn('chargeVnd', finance_dart.split('class FinanceCharge')[1].split('}')[0])
        self.assertNotIn('notes', finance_dart.split('class FinanceCharge')[1].split('}')[0])

        # FinancePayment
        self.assertIn('final String paymentId;', finance_dart)
        self.assertIn('final String? reference;', finance_dart)
        self.assertNotIn('referenceCode', finance_dart.split('class FinancePayment')[1].split('}')[0])

        # PaymentInstructions
        self.assertIn('final Map<String, dynamic>? receiverSnapshot;', finance_dart)
        self.assertIn('final String? reference;', finance_dart)
        self.assertNotIn('accountHolder', finance_dart.split('class PaymentInstructions')[1].split('}')[0])
        self.assertNotIn('vietqrUrl', finance_dart.split('class PaymentInstructions')[1].split('}')[0])

        # SessionSummary
        self.assertIn('final int? expensesTotalVnd;', finance_dart)
        self.assertIn('final int? amountDueTotalVnd;', finance_dart)
        self.assertIn('final int? totalPaidVnd;', finance_dart)
        self.assertIn('final int? outstandingTotalVnd;', finance_dart)
        self.assertNotIn('totalExpensesVnd', finance_dart.split('class SessionSummary')[1].split('}')[0])
        self.assertNotIn('remainingVnd', finance_dart.split('class SessionSummary')[1].split('}')[0])

        # BankAccount
        self.assertIn('final String accountNumber;', club_dart)
        self.assertIn('final String accountName;', club_dart)


if __name__ == '__main__':
    unittest.main()
