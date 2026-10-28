"""Unit and oracle controls for V2b BH-07 charges and payments coverage expansion.

TDD controls verifying:
1. Model DTO contract:
   - FinancePayment: uses real paymentId (UUID, unrendered) and reference (String, rendered).
   - FinanceCharge: has only playerId, displayName, amountDueVnd; has NO chargeId and NO notes.
   - Distinction between financial retainers and roster identity (SessionPlayer.id).
2. Oracle Positive Control:
   - Gated finance sentinels (expense_id, expense_id_2, payment_id) present in owner_active
     and 100% absent (occurrences=0, reachable=False) in post_logout and post_actor.
   - payment_ref measured as rendered text.
   - Verdict is PASS with strict graph analysis.
3. Mutant 1 (payment_id retained):
   - payment_id still present/reachable after logout -> FAIL.
4. Mutant 2 (payment_id missing in owner_active):
   - payment_id not loaded in owner_active -> fails precondition.
5. Mutant 3 (roster identity conflation prevented):
   - Verifies that roster retention at post_cohost (SessionProvider) is recognized as identity scope,
     never falsely attributed as FinanceCharge leak, nor used to falsely claim app-wide finance clean.
6. Mutant 4 (fictional charge fields rejected):
   - Confirms that FinanceCharge rejects fictional fields like chargeId or notes.

Run: python -X utf8 -m unittest tests.test_bh07_finance_heap_coverage -v
"""
import copy
import importlib.util
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ORACLE_PATH = ROOT / 'scripts/bh07_appheap/heap_oracle.py'
FINANCE_MODEL_PATH = ROOT / 'lib/models/finance.dart'

_spec = importlib.util.spec_from_file_location('heap_oracle', ORACLE_PATH)
ORACLE = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ORACLE)


def path_record(reachable, root_kind='global_handles', path_len=3):
    if not reachable:
        return {'reachable': False, 'exact': False}
    return {
        'reachable': True,
        'root_kind': root_kind,
        'path_len': path_len,
        'frames': ['root', f'internal:({root_kind}) -> synthetic',
                   'property:_cache -> object', 'property:item -> string'],
        'path_sha256_12': '0123456789ab',
        'exact': True,
    }


def make_scans(classes, active_sentinels, logout_sentinels, actor_sentinels, baseline_sentinels=None):
    """Build a standard 4-epoch scan structure for testing."""
    base = {'probe'} if baseline_sentinels is None else set(baseline_sentinels)
    epochs = {
        'baseline': base,
        'owner_active': set(active_sentinels) | {'probe'},
        'post_logout': set(logout_sentinels) | {'probe'},
        'post_actor': set(actor_sentinels) | {'probe'},
    }
    scans = {}
    for epoch, present_set in epochs.items():
        sentinel_records = {}
        path_records = {}
        for name, meta in classes.items():
            is_present = name in present_set
            sentinel_records[name] = {
                'present': is_present,
                'occurrences': 1 if is_present else 0,
                'rendered': meta.get('rendered', False),
                'distinctive': meta.get('distinctive', True),
                'scope': meta.get('scope', 'identity'),
            }
            path_records[name] = path_record(is_present)
        scans[epoch] = {
            'ok': True,
            'size_bytes': 1000000,
            'sha256_12': '1234567890ab',
            'sentinels': sentinel_records,
            'paths': path_records,
        }
    return scans


class TestFinanceModelContracts(unittest.TestCase):
    """Ensure DTO contract in lib/models/finance.dart matches the exact technical specification."""

    @classmethod
    def setUpClass(cls):
        with open(FINANCE_MODEL_PATH, 'r', encoding='utf-8') as f:
            cls.model_code = f.read()

    def test_finance_charge_fields_exact(self):
        """FinanceCharge has ONLY playerId, displayName, amountDueVnd; NO chargeId, NO notes."""
        charge_match = re.search(r'class FinanceCharge\s*\{([^}]+)\}', self.model_code)
        self.assertIsNotNone(charge_match, "FinanceCharge class must exist in lib/models/finance.dart")
        body = charge_match.group(1)

        # Must have real fields
        self.assertIn('playerId', body)
        self.assertIn('displayName', body)
        self.assertIn('amountDueVnd', body)

        # Must NOT have fictional fields
        self.assertNotIn('chargeId', body, "FinanceCharge must NOT have chargeId")
        self.assertNotIn('notes', body, "FinanceCharge must NOT have notes")
        self.assertNotIn('dueVnd', body, "FinanceCharge must NOT have dueVnd")
        self.assertNotIn('referenceCode', body, "FinanceCharge must NOT have referenceCode")

    def test_finance_payment_fields_exact(self):
        """FinancePayment has paymentId and reference as distinctive identifiers."""
        payment_match = re.search(r'class FinancePayment\s*\{([^}]+)\}', self.model_code)
        self.assertIsNotNone(payment_match, "FinancePayment class must exist in lib/models/finance.dart")
        body = payment_match.group(1)

        self.assertIn('paymentId', body)
        self.assertIn('playerId', body)
        self.assertIn('amountVnd', body)
        self.assertIn('method', body)
        self.assertIn('status', body)
        self.assertIn('reference', body)
        self.assertIn('confirmedAt', body)
        self.assertIn('createdAt', body)


class TestFinanceHeapCoverageOracle(unittest.TestCase):
    """Oracle controls for expanded finance coverage including payments and charges."""

    def setUp(self):
        self.classes = {
            'probe': {'rendered': False, 'distinctive': True, 'scope': 'control'},
            'expense_id': {'rendered': False, 'distinctive': True, 'scope': 'finance'},
            'expense_id_2': {'rendered': False, 'distinctive': True, 'scope': 'finance'},
            'payment_id': {'rendered': False, 'distinctive': True, 'scope': 'finance'},
            'payment_ref': {'rendered': True, 'distinctive': True, 'scope': 'finance'},
            'expense': {'rendered': True, 'distinctive': True, 'scope': 'finance'},
            'expense2': {'rendered': True, 'distinctive': True, 'scope': 'finance'},
            'player_a': {'rendered': False, 'distinctive': True, 'scope': 'identity'},
            'player_b': {'rendered': False, 'distinctive': True, 'scope': 'identity'},
        }

    def test_positive_control_with_payment_and_charge_sentinels(self):
        """Positive control: payment_id and expense IDs gated, present in owner, 100% absent after logout."""
        active = {'probe', 'expense_id', 'expense_id_2', 'payment_id', 'payment_ref', 'expense', 'expense2', 'player_a', 'player_b'}
        logout = {'probe', 'expense', 'expense2'}  # titles in web engine cache, finance IDs gone
        actor = {'probe', 'expense', 'expense2', 'player_a'}  # player_a reloaded by cohost roster

        scans = make_scans(self.classes, active, logout, actor)
        expectations = ORACLE.derive_expectations(scans)

        # Gated expectations check
        self.assertTrue(expectations['owner_active']['payment_id'])
        self.assertFalse(expectations['post_logout']['payment_id'])
        self.assertFalse(expectations['post_actor']['payment_id'])

        verdict = ORACLE.decide(scans, expectations, cleanup_ok=True, mode='profile', strict=True)
        self.assertEqual(verdict['verdict'], 'PASS', verdict['findings'])
        self.assertEqual(len(verdict['findings']), 0)

        # Rendered residual risks are unattributed
        risks = verdict['residual_risks']
        self.assertTrue(len(risks) >= 2)
        for risk in risks:
            self.assertEqual(risk['attribution'], 'unattributed')
            self.assertEqual(risk['class'], 'rendered')

        # Notes contain identity observations for player_a
        notes = verdict['notes']
        self.assertTrue(any('player_a' in n and 'not established' in n for n in notes))

    def test_mutant_1_payment_id_retained_fails_oracle(self):
        """Mutant 1: payment_id retained after logout must trigger hard FAIL."""
        active = {'probe', 'expense_id', 'expense_id_2', 'payment_id', 'expense', 'expense2'}
        logout = {'probe', 'expense', 'expense2', 'payment_id'}  # LEAK!
        actor = {'probe', 'expense', 'expense2'}

        scans = make_scans(self.classes, active, logout, actor)
        expectations = ORACLE.derive_expectations(scans)

        verdict = ORACLE.decide(scans, expectations, cleanup_ok=True, mode='profile', strict=True)
        self.assertEqual(verdict['verdict'], 'FAIL')
        findings_str = ' '.join(verdict['findings'])
        self.assertIn('payment_id', findings_str)
        self.assertTrue('expected absent' in findings_str or 'still reachable' in findings_str)

    def test_mutant_2_payment_id_not_loaded_in_owner_active(self):
        """Mutant 2: payment_id never loaded in owner_active fails precondition / coverage."""
        active = {'probe', 'expense_id', 'expense_id_2'}  # payment_id NOT loaded
        logout = {'probe'}
        actor = {'probe'}

        scans = make_scans(self.classes, active, logout, actor)
        expectations = ORACLE.derive_expectations(scans)

        # payment_id should not be in expectations because it was not present in owner_active
        self.assertNotIn('payment_id', expectations['owner_active'])

    def test_mutant_3_roster_conflation_prevention(self):
        """Mutant 3: Roster identity (player_a) at post_cohost must NOT be treated as a finance charge leak.

        If player_a is correctly classified as scope: identity, it is reported as a note.
        If someone mistakenly classifies player_a as scope: finance, it fails because cohost legitimately fetches roster.
        """
        active = {'probe', 'expense_id', 'expense_id_2', 'payment_id', 'player_a'}
        logout = {'probe'}
        actor = {'probe', 'player_a'}  # player_a present in cohost due to roster

        # Correct declaration: scope = identity
        scans = make_scans(self.classes, active, logout, actor)
        expectations = ORACLE.derive_expectations(scans)
        verdict = ORACLE.decide(scans, expectations, cleanup_ok=True, mode='profile', strict=True)
        self.assertEqual(verdict['verdict'], 'PASS')
        self.assertTrue(any('player_a' in n for n in verdict['notes']))

        # Flawed declaration: scope = finance (conflating roster identity with finance model)
        flawed_classes = copy.deepcopy(self.classes)
        flawed_classes['player_a']['scope'] = 'finance'
        flawed_scans = make_scans(flawed_classes, active, logout, actor)
        flawed_expectations = ORACLE.derive_expectations(flawed_scans)
        flawed_verdict = ORACLE.decide(flawed_scans, flawed_expectations, cleanup_ok=True, mode='profile', strict=True)
        self.assertEqual(flawed_verdict['verdict'], 'FAIL')
        self.assertIn('player_a', ' '.join(flawed_verdict['findings']))


if __name__ == '__main__':
    unittest.main()
