"""TDD controls for BH-07 V2b club ledger Web-profile heap coverage.

Verifies:
1. Model & UI Contracts:
   - ClubLedgerEntry DTO: transactionId (UUID), direction, amountVnd, title, sourceType.
   - UI: ClubFundScreen._entryTile renders title/source, uses transactionId only in Key and RPC,
     never as visible rendered text.
   - UI: ClubFundScreen.initState handles initialAction='income' by opening manual dialog;
     dialog has exact 'Huỷ' button to cancel; screen renders 'Giao dịch' list.
2. Oracle Positive and Mutant Controls:
   - ledger_transaction_id (unrendered, distinctive, scope: finance) gated in owner_active
     and absent/unreachable at baseline, post_logout, and post_actor across both cycles.
   - Mutants: baseline collision, post-logout retention, forged scope/rendered.
3. Real Auditor CLI Tests (_clone_and_audit on finance_heap_evidence):
   - Opt-in ledger_coverage_contract v1.0 with required_owner_load=['ledger_transaction_id'].
   - Mandatory declared metadata for ledger_transaction_id.
   - Owner load requirement: owner_active must have present=True and reachable=True.
   - Strict cleanup receipts: disposable_ledger_created, disposable_ledger_removed,
     disposable_ledger_verified_absent, and matching disposable_ledger_id_sha256_12.
   - Mutants fail-closed (exit 1) with ledger-specific findings.
   - Legacy finance evidence passes untouched (exit 0).

Run: python -X utf8 -m unittest tests.test_bh07_ledger_heap_coverage -v
"""
import copy
import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ORACLE_PATH = ROOT / 'scripts/bh07_appheap/heap_oracle.py'
VERIFIER_PATH = ROOT / 'scripts/bh07_appheap/verify_evidence.py'
FINANCE_MODEL_PATH = ROOT / 'lib/models/finance.dart'
CLUB_FUND_SCREEN_PATH = ROOT / 'lib/screens/club_fund_screen.dart'
FINANCE_EVIDENCE_SOURCE = ROOT / 'docs/reviews/bh07/finance_heap_evidence'

_spec = importlib.util.spec_from_file_location('heap_oracle', ORACLE_PATH)
ORACLE = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ORACLE)


def path_record(reachable, root_kind='global_handles', path_len=3):
    if not reachable:
        return {'reachable': False, 'string_nodes': 0, 'exact': False}
    return {
        'reachable': True,
        'root_kind': root_kind,
        'path_len': path_len,
        'frames': ['root', f'internal:({root_kind}) -> synthetic',
                   'property:_ledger -> object', 'property:transactionId -> string'],
        'path_sha256_12': '0123456789ab',
        'string_nodes': 1,
        'exact': True,
    }


def make_ledger_scans(classes, active_sentinels, logout_sentinels, actor_sentinels, baseline_sentinels=None):
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


class TestLedgerModelAndUIContracts(unittest.TestCase):
    """Ensure ClubLedgerEntry and ClubFundScreen UI meet unrendered sentinel requirements."""

    @classmethod
    def setUpClass(cls):
        with open(FINANCE_MODEL_PATH, 'r', encoding='utf-8') as f:
            cls.model_code = f.read()
        with open(CLUB_FUND_SCREEN_PATH, 'r', encoding='utf-8') as f:
            cls.screen_code = f.read()

    def test_club_ledger_entry_fields_exact(self):
        match = re.search(r'class ClubLedgerEntry\s*\{([^}]+)\}', self.model_code)
        self.assertIsNotNone(match, 'ClubLedgerEntry class must exist in lib/models/finance.dart')
        body = match.group(1)
        self.assertIn('transactionId', body)
        self.assertIn('direction', body)
        self.assertIn('amountVnd', body)
        self.assertIn('title', body)
        self.assertIn('sourceType', body)

    def test_ledger_tile_renders_title_and_uses_transaction_id_only_in_key_rpc(self):
        self.assertIn('_entryTile', self.screen_code)
        self.assertIn('title: Text(entry.title', self.screen_code)
        self.assertIn("Key('bh06c-reverse-ledger-${entry.transactionId}')", self.screen_code)
        self.assertNotIn('Text(entry.transactionId)', self.screen_code,
                         'transactionId must NEVER be wrapped in a Text widget')

    def test_fund_screen_opens_dialog_and_provides_cancel_button(self):
        self.assertIn('_openManualDialog', self.screen_code)
        self.assertIn("'Huỷ'", self.screen_code,
                      "Manual dialog must offer exact 'Huỷ' button to dismiss without submit")
        self.assertIn('Giao dịch', self.screen_code,
                      "Fund screen must render 'Giao dịch' list header")

    def test_button_helper_supports_text_and_aria_and_rejects_wrong_role_or_label(self):
        script = """
const { button } = require('./scripts/bh07_appheap/run_app_profile_heap.js');
const check = button('Huỷ');
const results = {
  text_match: check({ role: 'button', text: 'Huỷ' }),
  aria_match: check({ role: 'button', aria: 'Huỷ', text: '' }),
  tag_text_match: check({ tag: 'BUTTON', text: '  Huỷ  ' }),
  tag_aria_match: check({ tag: 'BUTTON', aria: 'Huỷ' }),
  never_ghi_so: check({ role: 'button', text: 'Ghi sổ' }),
  never_ghi_so_aria: check({ role: 'button', aria: 'Ghi sổ' }),
  reject_wrong_role: check({ role: 'dialog', text: 'Huỷ' }),
  reject_wrong_tag: check({ tag: 'DIV', text: 'Huỷ' }),
  reject_substring: check({ role: 'button', text: 'Huỷ bỏ' }),
};
console.log(JSON.stringify(results));
"""
        res = subprocess.run(['node', '-e', script], cwd=str(ROOT), capture_output=True, text=True, check=True)
        data = json.loads(res.stdout)
        self.assertTrue(data['text_match'])
        self.assertTrue(data['aria_match'])
        self.assertTrue(data['tag_text_match'])
        self.assertTrue(data['tag_aria_match'])
        self.assertFalse(data['never_ghi_so'])
        self.assertFalse(data['never_ghi_so_aria'])
        self.assertFalse(data['reject_wrong_role'])
        self.assertFalse(data['reject_wrong_tag'])
        self.assertFalse(data['reject_substring'])

    def test_open_owner_ledger_fake_cdp_supports_aria_only_and_never_clicks_ghi_so(self):
        script = """
const { openOwnerLedger } = require('./scripts/bh07_appheap/run_app_profile_heap.js');
function makeFakeCdp(cancelElement) {
  const clicked = [];
  return {
    clicked,
    async getAllSemantics() { return [{ role: 'tab', aria: 'Tài Khoản' }]; },
    async clickBack() {},
    async clickSemantic(predicate, label) {
      if (label === 'Clubs tab') return;
      if (label === 'Select disposable test club') return;
      if (label === 'Click THU QUY') return;
      if (label === 'Cancel manual transaction dialog') {
        if (!predicate(cancelElement)) throw new Error('cancel button predicate failed');
        clicked.push(cancelElement);
        return;
      }
    },
    async waitForSemantic(predicate, label) { return true; }
  };
}

async function run() {
  const cdp1 = makeFakeCdp({ role: 'button', text: 'Huỷ' });
  await openOwnerLedger(cdp1, 'Test Club', 'Fixture Title');

  const cdp2 = makeFakeCdp({ role: 'button', aria: 'Huỷ', text: '' });
  await openOwnerLedger(cdp2, 'Test Club', 'Fixture Title');

  let ghiSoThrew = false;
  const cdp3 = makeFakeCdp({ role: 'button', text: 'Ghi sổ' });
  try {
    await openOwnerLedger(cdp3, 'Test Club', 'Fixture Title');
  } catch (err) {
    ghiSoThrew = true;
  }

  let wrongRoleThrew = false;
  const cdp4 = makeFakeCdp({ role: 'dialog', text: 'Huỷ' });
  try {
    await openOwnerLedger(cdp4, 'Test Club', 'Fixture Title');
  } catch (err) {
    wrongRoleThrew = true;
  }

  console.log(JSON.stringify({
    textSuccess: cdp1.clicked.length === 1,
    ariaSuccess: cdp2.clicked.length === 1,
    ghiSoThrew,
    wrongRoleThrew
  }));
}
run();
"""
        res = subprocess.run(['node', '-e', script], cwd=str(ROOT), capture_output=True, text=True, check=True)
        data = json.loads(res.stdout)
        self.assertTrue(data['textSuccess'])
        self.assertTrue(data['ariaSuccess'])
        self.assertTrue(data['ghiSoThrew'])
        self.assertTrue(data['wrongRoleThrew'])


class TestLedgerHeapCoverageOracle(unittest.TestCase):
    """Oracle controls for ledger_transaction_id sentinel."""

    def setUp(self):
        self.classes = {
            'probe': {'rendered': False, 'distinctive': True, 'scope': 'control'},
            'expense_id': {'rendered': False, 'distinctive': True, 'scope': 'finance'},
            'expense_id_2': {'rendered': False, 'distinctive': True, 'scope': 'finance'},
            'ledger_transaction_id': {'rendered': False, 'distinctive': True, 'scope': 'finance'},
        }

    def test_positive_control_with_ledger_coverage(self):
        active = ['expense_id', 'expense_id_2', 'ledger_transaction_id']
        scans = make_ledger_scans(self.classes, active, [], [])
        expectations = ORACLE.derive_expectations(scans)

        self.assertTrue(expectations['owner_active'].get('ledger_transaction_id'),
                        'ledger_transaction_id must be gated in owner_active')
        self.assertFalse(expectations['post_logout'].get('ledger_transaction_id'),
                         'ledger_transaction_id must be expected absent in post_logout')

        verdict = ORACLE.decide(scans, expectations, cleanup_ok=True, mode='profile', strict=True)
        self.assertEqual(verdict['verdict'], 'PASS', f"Expected PASS, got findings: {verdict.get('findings')}")

    def test_baseline_collision_fails(self):
        active = ['expense_id', 'expense_id_2', 'ledger_transaction_id']
        scans = make_ledger_scans(self.classes, active, [], [], baseline_sentinels={'probe', 'ledger_transaction_id'})
        exp = ORACLE.derive_expectations(scans)
        verdict = ORACLE.decide(scans, exp, cleanup_ok=True, mode='profile', strict=True)
        self.assertEqual(verdict['verdict'], 'FAIL')
        self.assertTrue(any('ledger_transaction_id' in f for f in verdict.get('findings', [])))

    def test_missing_owner_ledger_fails(self):
        active = ['expense_id', 'expense_id_2']
        scans = make_ledger_scans(self.classes, active, [], [])
        exp = ORACLE.derive_expectations(scans)
        verdict = ORACLE.decide(scans, exp, cleanup_ok=True, mode='profile', strict=True)
        self.assertEqual(verdict['verdict'], 'FAIL')
        self.assertTrue(any('ledger_transaction_id' in f for f in verdict.get('findings', [])))

    def test_post_logout_retention_fails(self):
        active = ['expense_id', 'expense_id_2', 'ledger_transaction_id']
        logout = ['ledger_transaction_id']
        scans = make_ledger_scans(self.classes, active, logout, [])
        exp = ORACLE.derive_expectations(scans)
        verdict = ORACLE.decide(scans, exp, cleanup_ok=True, mode='profile', strict=True)
        self.assertEqual(verdict['verdict'], 'FAIL')
        self.assertTrue(any('ledger_transaction_id' in f for f in verdict.get('findings', [])))

    def test_forged_rendered_or_scope_fails(self):
        forged_classes = copy.deepcopy(self.classes)
        forged_classes['ledger_transaction_id']['rendered'] = True
        scans = make_ledger_scans(forged_classes, ['ledger_transaction_id'], [], [])
        exp = ORACLE.derive_expectations(scans)
        self.assertFalse(exp['owner_active'].get('ledger_transaction_id'),
                         'rendered sentinel must not be gated as an unrendered finance absence gate')


class TestLedgerCoverageAuditorCLI(unittest.TestCase):
    """Real auditor CLI tests with clones of finance_heap_evidence."""

    def setUp(self):
        self.assertTrue(FINANCE_EVIDENCE_SOURCE.is_dir(), f"Evidence missing: {FINANCE_EVIDENCE_SOURCE}")
        self.original = json.loads((FINANCE_EVIDENCE_SOURCE / 'summary.json').read_bytes())

    def _clone_and_audit(self, summary_data):
        tmp_dir = ROOT / 'build' if (ROOT / 'build').is_dir() else None
        with tempfile.TemporaryDirectory(prefix='bh07_ledger_audit_test_', dir=tmp_dir) as tmp:
            directory = Path(tmp)
            for item in FINANCE_EVIDENCE_SOURCE.iterdir():
                if item.is_file():
                    shutil.copyfile(item, directory / item.name)
            (directory / 'summary.json').write_bytes(
                (json.dumps(summary_data, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
            )
            renderer = (
                "const fs=require('fs');const r=require(process.argv[1]);"
                "fs.writeFileSync(process.argv[3], r.renderReport(JSON.parse(fs.readFileSync(process.argv[2], 'utf8'))));"
            )
            subprocess.run(
                ['node', '-e', renderer, str(ROOT / 'scripts/bh07_appheap/run_app_profile_heap.js'),
                 str(directory / 'summary.json'), str(directory / 'report.md')],
                check=True,
                capture_output=True,
                encoding='utf-8',
            )
            manifest_lines = []
            for name in ('summary.json', 'report.md', 'run.log'):
                digest = hashlib.sha256((directory / name).read_bytes()).hexdigest()
                manifest_lines.append(f"{digest}  {name}\n")
            (directory / 'hashes.sha256').write_bytes(''.join(manifest_lines).encode('utf-8'))

            result = subprocess.run(
                ['python', '-X', 'utf8', str(VERIFIER_PATH), '--dir', str(directory)],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                encoding='utf-8',
            )
            return result

    def _make_positive_ledger_data(self):
        data = copy.deepcopy(self.original)
        txn_id = 'aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee'
        txn_sha12 = hashlib.sha256(txn_id.encode('utf-8')).hexdigest()[:12]
        data['coverage_profile'] = 'ledger'
        data['ledger_coverage_contract'] = {
            'version': '1.0',
            'required_owner_load': ['ledger_transaction_id'],
        }
        data['sentinels']['ledger_transaction_id'] = {
            'available': True,
            'length': 36,
            'sha256_12': txn_sha12,
            'kind': 'disposable club ledger transaction ID from club_transactions (never rendered)',
            'scope': 'finance',
            'rendered': False,
            'distinctive': True,
        }
        for cycle in data['cycles']:
            for epoch_name, epoch in cycle['epochs'].items():
                is_owner = (epoch_name == 'owner_active')
                epoch['sentinels']['ledger_transaction_id'] = {
                    'present': is_owner,
                    'occurrences': 1 if is_owner else 0,
                    'rendered': False,
                    'distinctive': True,
                    'scope': 'finance',
                }
                epoch['paths']['ledger_transaction_id'] = path_record(is_owner)
        club_id = 'cccccccc-1111-4111-8111-111111111111'
        club_sha12 = hashlib.sha256(club_id.encode('utf-8')).hexdigest()[:12]
        bank_id = 'bbbbbbbb-2222-4222-8222-222222222222'
        bank_sha12 = hashlib.sha256(bank_id.encode('utf-8')).hexdigest()[:12]
        data['cleanup'].update(
            disposable_club_created=True,
            disposable_club_id_sha256_12=club_sha12,
            disposable_club_removed=True,
            disposable_club_verified_absent=True,
            disposable_bank_created=True,
            disposable_bank_id_sha256_12=bank_sha12,
            disposable_bank_removed=True,
            disposable_bank_verified_absent=True,
            disposable_ledger_created=True,
            disposable_ledger_id_sha256_12=txn_sha12,
            disposable_ledger_removed=True,
            disposable_ledger_verified_absent=True,
        )
        return data

    def test_legacy_finance_evidence_exit0(self):
        data = copy.deepcopy(self.original)
        result = self._clone_and_audit(data)
        self.assertEqual(result.returncode, 0, f"Legacy finance evidence failed auditor CLI:\n{result.stdout}\n{result.stderr}")

    def test_ledger_profile_positive_exit0(self):
        data = self._make_positive_ledger_data()
        result = self._clone_and_audit(data)
        self.assertEqual(result.returncode, 0, f"Ledger positive failed auditor CLI:\n{result.stdout}\n{result.stderr}")

    def test_missing_contract_fails_exit1(self):
        data = self._make_positive_ledger_data()
        data.pop('ledger_coverage_contract')
        result = self._clone_and_audit(data)
        self.assertEqual(result.returncode, 1)
        self.assertIn('ledger_coverage_contract', result.stdout)

    def test_invalid_contract_version_fails_exit1(self):
        data = self._make_positive_ledger_data()
        data['ledger_coverage_contract']['version'] = '2.0'
        result = self._clone_and_audit(data)
        self.assertEqual(result.returncode, 1)
        self.assertIn('version', result.stdout.lower())

    def test_missing_metadata_fails_exit1(self):
        data = self._make_positive_ledger_data()
        data['sentinels'].pop('ledger_transaction_id')
        result = self._clone_and_audit(data)
        self.assertEqual(result.returncode, 1)
        self.assertIn('ledger_transaction_id', result.stdout)

    def test_invalid_sentinel_class_fails_exit1(self):
        data = self._make_positive_ledger_data()
        data['sentinels']['ledger_transaction_id']['rendered'] = True
        result = self._clone_and_audit(data)
        self.assertEqual(result.returncode, 1)

    def test_missing_owner_load_fails_exit1(self):
        data = self._make_positive_ledger_data()
        for cycle in data['cycles']:
            owner_epoch = cycle['epochs']['owner_active']
            owner_epoch['sentinels']['ledger_transaction_id']['present'] = False
            owner_epoch['sentinels']['ledger_transaction_id']['occurrences'] = 0
            owner_epoch['paths']['ledger_transaction_id'] = path_record(False)
        result = self._clone_and_audit(data)
        self.assertEqual(result.returncode, 1)
        self.assertIn('owner', result.stdout.lower())

    def test_owner_unreachable_fails_exit1(self):
        data = self._make_positive_ledger_data()
        for cycle in data['cycles']:
            owner_epoch = cycle['epochs']['owner_active']
            owner_epoch['paths']['ledger_transaction_id'] = path_record(False)
        result = self._clone_and_audit(data)
        self.assertEqual(result.returncode, 1)
        self.assertIn('owner', result.stdout.lower())

    def test_post_logout_retention_fails_exit1(self):
        data = self._make_positive_ledger_data()
        for cycle in data['cycles']:
            logout_epoch = cycle['epochs']['post_logout']
            logout_epoch['sentinels']['ledger_transaction_id']['present'] = True
            logout_epoch['sentinels']['ledger_transaction_id']['occurrences'] = 1
            logout_epoch['paths']['ledger_transaction_id'] = path_record(True)
        result = self._clone_and_audit(data)
        self.assertEqual(result.returncode, 1)

    def test_post_actor_retention_fails_exit1(self):
        data = self._make_positive_ledger_data()
        for cycle in data['cycles']:
            actor_epoch = cycle['epochs']['post_actor']
            actor_epoch['sentinels']['ledger_transaction_id']['present'] = True
            actor_epoch['sentinels']['ledger_transaction_id']['occurrences'] = 1
            actor_epoch['paths']['ledger_transaction_id'] = path_record(True)
        result = self._clone_and_audit(data)
        self.assertEqual(result.returncode, 1)

    def test_missing_cleanup_receipt_fails_exit1(self):
        data = self._make_positive_ledger_data()
        data['cleanup']['disposable_ledger_verified_absent'] = False
        result = self._clone_and_audit(data)
        self.assertEqual(result.returncode, 1)
        self.assertIn('verified_absent', result.stdout)

    def test_string_cleanup_receipt_fails_exit1(self):
        data = self._make_positive_ledger_data()
        data['cleanup']['disposable_ledger_verified_absent'] = 'true'
        result = self._clone_and_audit(data)
        self.assertEqual(result.returncode, 1)
        self.assertIn('verified_absent', result.stdout)

    def test_wrong_receipt_sha12_fails_exit1(self):
        data = self._make_positive_ledger_data()
        data['cleanup']['disposable_ledger_id_sha256_12'] = '000000000000'
        result = self._clone_and_audit(data)
        self.assertEqual(result.returncode, 1)
        self.assertIn('receipt', result.stdout.lower())

    def test_parent_club_omitted_fails_exit1(self):
        data = self._make_positive_ledger_data()
        data['cleanup'].pop('disposable_club_created')
        result = self._clone_and_audit(data)
        self.assertEqual(result.returncode, 1)
        self.assertIn('disposable_club_created', result.stdout)

    def test_parent_club_removed_false_fails_exit1(self):
        data = self._make_positive_ledger_data()
        data['cleanup']['disposable_club_removed'] = False
        result = self._clone_and_audit(data)
        self.assertEqual(result.returncode, 1)
        self.assertIn('disposable_club_removed', result.stdout)

    def test_parent_club_verified_absent_string_fails_exit1(self):
        data = self._make_positive_ledger_data()
        data['cleanup']['disposable_club_verified_absent'] = 'true'
        result = self._clone_and_audit(data)
        self.assertEqual(result.returncode, 1)
        self.assertIn('disposable_club_verified_absent', result.stdout)

    def test_parent_club_error_fails_exit1(self):
        data = self._make_positive_ledger_data()
        data['cleanup']['disposable_club_error'] = 'club deletion constraint failed'
        result = self._clone_and_audit(data)
        self.assertEqual(result.returncode, 1)
        self.assertIn('disposable club cleanup reported an error', result.stdout)

    def test_parent_bank_omitted_fails_exit1(self):
        data = self._make_positive_ledger_data()
        data['cleanup'].pop('disposable_bank_created')
        result = self._clone_and_audit(data)
        self.assertEqual(result.returncode, 1)
        self.assertIn('disposable_bank_created', result.stdout)

    def test_parent_bank_removed_false_fails_exit1(self):
        data = self._make_positive_ledger_data()
        data['cleanup']['disposable_bank_removed'] = False
        result = self._clone_and_audit(data)
        self.assertEqual(result.returncode, 1)
        self.assertIn('disposable_bank_removed', result.stdout)

    def test_parent_bank_verified_absent_string_fails_exit1(self):
        data = self._make_positive_ledger_data()
        data['cleanup']['disposable_bank_verified_absent'] = 'true'
        result = self._clone_and_audit(data)
        self.assertEqual(result.returncode, 1)
        self.assertIn('disposable_bank_verified_absent', result.stdout)

    def test_parent_bank_error_fails_exit1(self):
        data = self._make_positive_ledger_data()
        data['cleanup']['disposable_bank_error'] = 'bank deletion failed'
        result = self._clone_and_audit(data)
        self.assertEqual(result.returncode, 1)
        self.assertIn('disposable bank cleanup reported an error', result.stdout)

    def test_parent_bank_sha12_mismatch_fails_exit1(self):
        data = self._make_positive_ledger_data()
        data['sentinels']['bank_account_id'] = {
            'available': True,
            'length': 36,
            'sha256_12': '111122223333',
            'kind': 'disposable bank account id',
            'scope': 'finance',
            'rendered': False,
            'distinctive': True,
        }
        data['cleanup']['disposable_bank_id_sha256_12'] = '999988887777'
        result = self._clone_and_audit(data)
        self.assertEqual(result.returncode, 1)
        self.assertIn('disposable bank receipt sha256_12', result.stdout)


if __name__ == '__main__':
    unittest.main()
