"""Unit and oracle controls for BH-07 V2b bank and receiver Web-profile coverage.

TDD controls verifying:
1. Model & UI Contracts:
   - BankAccount model: id (UUID), accountNumber, accountName.
   - UI: both accountNumber and accountName are rendered as widget text in _buildBankTab.
2. Oracle Positive Control:
   - bank_account_id (unrendered, finance) present in owner_active and absent in post_logout/post_actor.
   - bank (rendered, bank scope) and receiver (rendered, bank scope) present in owner_active as load controls.
   - post-logout retention of rendered strings attributed strictly as 'unattributed' residual risk.
   - Overall verdict PASS.
3. Mutant 1 (missing owner load):
   - bank_account_id, bank, or receiver not present in owner_active -> fails precondition.
4. Mutant 2 (baseline collision):
   - bank_account_id or bank seen at baseline -> fails discrimination.
5. Mutant 3 (retained unrendered bank ID):
   - bank_account_id retained/reachable after logout -> FAIL.
6. Mutant 4 (dropped required metadata):
   - missing required contract key or required sentinel -> FAIL.
7. Mutant 5 (forged rendered/scope flags):
   - bank declared rendered: false or bank_account_id declared scope: identity -> FAIL.
8. Mutant 6 (missing cleanup / wrong receipt hash):
   - unverified absence or receipt hash mismatch -> FAIL.
9. Fixture ownership controls:
   - Pre-existing ID collision refusal, lost POST response reconciliation, child-first cleanup order,
     delete error handling.

Run: python -X utf8 -m unittest tests.test_bh07_bank_heap_coverage -v
"""
import copy
import hashlib
import importlib.util
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ORACLE_PATH = ROOT / 'scripts/bh07_appheap/heap_oracle.py'
VERIFIER_PATH = ROOT / 'scripts/bh07_appheap/verify_evidence.py'
CLUB_MODEL_PATH = ROOT / 'lib/models/club.dart'
CLUBS_SCREEN_PATH = ROOT / 'lib/screens/clubs_screen.dart'

_spec = importlib.util.spec_from_file_location('heap_oracle', ORACLE_PATH)
ORACLE = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ORACLE)

_v_spec = importlib.util.spec_from_file_location('verify_evidence', VERIFIER_PATH)
VERIFIER = importlib.util.module_from_spec(_v_spec)
_v_spec.loader.exec_module(VERIFIER)


def path_record(reachable, root_kind='global_handles', path_len=3):
    if not reachable:
        return {'reachable': False, 'exact': False}
    return {
        'reachable': True,
        'root_kind': root_kind,
        'path_len': path_len,
        'frames': ['root', f'internal:({root_kind}) -> synthetic',
                   'property:_currentBankAccount -> object', 'property:accountNumber -> string'],
        'path_sha256_12': '0123456789ab',
        'exact': True,
    }


def make_bank_scans(classes, active_sentinels, logout_sentinels, actor_sentinels, baseline_sentinels=None):
    """Build a standard 4-epoch scan structure with bank coverage sentinels."""
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


class TestBankModelAndUIContracts(unittest.TestCase):
    """Ensure BankAccount DTO and ClubsScreen UI rendering match the technical spec."""

    @classmethod
    def setUpClass(cls):
        with open(CLUB_MODEL_PATH, 'r', encoding='utf-8') as f:
            cls.model_code = f.read()
        with open(CLUBS_SCREEN_PATH, 'r', encoding='utf-8') as f:
            cls.screen_code = f.read()

    def test_bank_account_fields_exact(self):
        """BankAccount has id, clubId, bankCode, accountNumber, accountName."""
        match = re.search(r'class BankAccount\s*\{([^}]+)\}', self.model_code)
        self.assertIsNotNone(match, "BankAccount class must exist in lib/models/club.dart")
        body = match.group(1)
        self.assertIn('id', body)
        self.assertIn('clubId', body)
        self.assertIn('bankCode', body)
        self.assertIn('accountNumber', body)
        self.assertIn('accountName', body)
        self.assertIn('status', body)

    def test_bank_tab_renders_account_number_and_name(self):
        """ClubsScreen explicitly renders accountNumber and accountName as widget text."""
        self.assertIn('bank.accountNumber', self.screen_code,
                      "accountNumber must be rendered in ClubsScreen (_buildBankTab)")
        self.assertIn('bank.accountName', self.screen_code,
                      "accountName must be rendered in ClubsScreen (_buildBankTab)")


class TestBankHeapCoverageOracle(unittest.TestCase):
    """Oracle controls for bank/receiver coverage extension."""

    def setUp(self):
        self.classes = {
            'probe': {'rendered': False, 'distinctive': True, 'scope': 'control'},
            'expense_id': {'rendered': False, 'distinctive': True, 'scope': 'finance'},
            'expense_id_2': {'rendered': False, 'distinctive': True, 'scope': 'finance'},
            'bank_account_id': {'rendered': False, 'distinctive': True, 'scope': 'finance'},
            'bank': {'rendered': True, 'distinctive': True, 'scope': 'bank'},
            'receiver': {'rendered': True, 'distinctive': True, 'scope': 'bank'},
            'player_a': {'rendered': False, 'distinctive': True, 'scope': 'identity'},
            'player_b': {'rendered': False, 'distinctive': True, 'scope': 'identity'},
        }

    def test_positive_control_with_bank_coverage(self):
        """Positive control: bank_account_id gated and absent after logout; bank/receiver rendered."""
        active = ['expense_id', 'expense_id_2', 'bank_account_id', 'bank', 'receiver']
        # Rendered strings remain in web engine segmentationCache at post_logout/post_actor
        logout = ['bank', 'receiver']
        actor = ['bank', 'receiver']

        scans = make_bank_scans(self.classes, active, logout, actor)
        expectations = ORACLE.derive_expectations(scans)

        # bank_account_id must be gated as Owner-private finance
        self.assertTrue(expectations['owner_active'].get('bank_account_id'),
                        "bank_account_id must be gated in owner_active")
        self.assertFalse(expectations['post_logout'].get('bank_account_id'),
                         "bank_account_id must be expected absent in post_logout")

        verdict = ORACLE.decide(scans, expectations, cleanup_ok=True, mode='profile', strict=True)
        self.assertEqual(verdict['verdict'], 'PASS', f"Expected PASS, got findings: {verdict['findings']}")

        # Rendered bank and receiver should be reported as unattributed residual risks
        risk_sentinels = [r['sentinel'] for r in verdict['residual_risks']]
        self.assertIn('bank', risk_sentinels)
        self.assertIn('receiver', risk_sentinels)
        for r in verdict['residual_risks']:
            if r['sentinel'] in ('bank', 'receiver'):
                self.assertEqual(r['attribution'], 'unattributed')
                self.assertEqual(r['class'], 'rendered')

    def test_missing_owner_load_fails_precondition(self):
        """If bank_account_id, bank or receiver did not load in owner_active, measurement must FAIL."""
        # Case A: bank_account_id not loaded
        active_a = ['expense_id', 'expense_id_2', 'bank', 'receiver']
        scans_a = make_bank_scans(self.classes, active_a, ['bank'], ['bank'])
        exp_a = ORACLE.derive_expectations(scans_a)
        verdict_a = ORACLE.decide(scans_a, exp_a, cleanup_ok=True, mode='profile', strict=True)
        self.assertEqual(verdict_a['verdict'], 'FAIL')
        self.assertTrue(any('bank_account_id' in f for f in verdict_a['findings']),
                        f"Expected finding for missing bank_account_id, got: {verdict_a['findings']}")

        # Case B: rendered bank string not loaded
        active_b = ['expense_id', 'expense_id_2', 'bank_account_id', 'receiver']
        scans_b = make_bank_scans(self.classes, active_b, [], [])
        exp_b = ORACLE.derive_expectations(scans_b)
        verdict_b = ORACLE.decide(scans_b, exp_b, cleanup_ok=True, mode='profile', strict=True)
        self.assertEqual(verdict_b['verdict'], 'FAIL')
        self.assertTrue(any('bank' in f for f in verdict_b['findings']),
                        f"Expected finding for missing bank in owner_active, got: {verdict_b['findings']}")

    def test_baseline_collision_fails(self):
        """If bank_account_id or bank is present at baseline, discrimination fails -> FAIL."""
        active = ['expense_id', 'expense_id_2', 'bank_account_id', 'bank', 'receiver']
        scans = make_bank_scans(self.classes, active, ['bank'], ['bank'], baseline_sentinels={'bank_account_id'})
        exp = ORACLE.derive_expectations(scans)
        verdict = ORACLE.decide(scans, exp, cleanup_ok=True, mode='profile', strict=True)
        self.assertEqual(verdict['verdict'], 'FAIL')
        self.assertTrue(any('bank_account_id' in f for f in verdict['findings']),
                        f"Expected finding for baseline collision, got: {verdict['findings']}")

    def test_retained_unrendered_bank_id_fails(self):
        """If bank_account_id remains present or reachable after logout -> FAIL."""
        active = ['expense_id', 'expense_id_2', 'bank_account_id', 'bank', 'receiver']
        logout = ['bank_account_id', 'bank', 'receiver']
        actor = ['bank', 'receiver']
        scans = make_bank_scans(self.classes, active, logout, actor)
        exp = ORACLE.derive_expectations(scans)
        verdict = ORACLE.decide(scans, exp, cleanup_ok=True, mode='profile', strict=True)
        self.assertEqual(verdict['verdict'], 'FAIL')
        self.assertTrue(any('bank_account_id' in f and 'reachable' in f for f in verdict['findings']),
                        f"Expected retention finding, got: {verdict['findings']}")

    def test_forged_rendered_or_scope_flags_fails(self):
        """Forging bank as rendered: false or bank_account_id as identity must fail."""
        # Forging bank as unrendered
        forged_classes = copy.deepcopy(self.classes)
        forged_classes['bank']['rendered'] = False
        active = ['expense_id', 'expense_id_2', 'bank_account_id', 'bank', 'receiver']
        # If bank survives in web engine, treating it as unrendered will fail post_logout absence
        logout = ['bank', 'receiver']
        scans = make_bank_scans(forged_classes, active, logout, logout)
        exp = ORACLE.derive_expectations(scans)
        verdict = ORACLE.decide(scans, exp, cleanup_ok=True, mode='profile', strict=True)
        self.assertEqual(verdict['verdict'], 'FAIL')

        # Forging bank_account_id as identity
        forged_classes_2 = copy.deepcopy(self.classes)
        forged_classes_2['bank_account_id']['scope'] = 'identity'
        scans_2 = make_bank_scans(forged_classes_2, active, logout, logout)
        exp_2 = ORACLE.derive_expectations(scans_2)
        verdict_2 = ORACLE.decide(scans_2, exp_2, cleanup_ok=True, mode='profile', strict=True)
        self.assertEqual(verdict_2['verdict'], 'FAIL')


class TestBankFixtureControls(unittest.TestCase):
    """Controls exercising the real production DisposableBankFixture JS helper via fake transport (BKR2, BKR4, BKR6)."""

    @classmethod
    def setUpClass(cls):
        cls.scenario_script = ROOT / 'scripts/bh07_appheap/test_disposable_fixture_scenarios.js'
        cls.runner_script = ROOT / 'scripts/bh07_appheap/run_app_profile_heap.js'

    def _run_scenario(self, scenario_name):
        import subprocess
        result = subprocess.run(
            ['node', str(self.scenario_script), scenario_name],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            encoding='utf-8',
        )
        self.assertEqual(result.returncode, 0, f"Scenario {scenario_name} failed with stderr: {result.stderr}")
        return json.loads(result.stdout)

    def test_default_runner_bkr1_regression_fixed(self):
        """Regression test for BKR1: run_app_profile_heap.js exports and syntax must be valid."""
        import subprocess
        result = subprocess.run(
            ['node', '-e',
             "const r = require('./scripts/bh07_appheap/run_app_profile_heap.js');"
             "const assert = require('assert');"
             "assert.strictEqual(typeof r.ensureDisposableBank, 'function');"
             "assert.strictEqual(typeof r.removeDisposableBank, 'function');"
             "assert.strictEqual(typeof r.registerDisposableBankRedactions, 'function');"
             "assert.strictEqual(typeof r.claimOutputDirectory, 'function');"
             "assert.strictEqual(typeof r.isNestedUnderEvidence, 'function');"
             "assert.strictEqual(typeof r.DisposableBankFixture, 'function');"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            encoding='utf-8',
        )
        self.assertEqual(result.returncode, 0, f"run_app_profile_heap.js failed: {result.stderr}")

    def test_positive_lifecycle_and_child_first_cleanup(self):
        """BKR4/BKR6: positive lifecycle creates exact schema and deletes child-first."""
        res = self._run_scenario('positive_lifecycle')
        self.assertTrue(res['ok'])
        # Exact child-first delete order
        self.assertEqual(res['deleteOrder'], ['club_bank_accounts', 'club_members', 'clubs'])
        receipt = res['receipt']
        self.assertTrue(receipt['disposable_club_created'])
        self.assertTrue(receipt['disposable_bank_created'])
        self.assertTrue(receipt['disposable_club_removed'])
        self.assertTrue(receipt['disposable_bank_removed'])
        self.assertTrue(receipt['verified_absent'])

    def test_preexisting_club_refusal(self):
        """BKR2: preflight finding an existing club refuses before any POST or DELETE."""
        res = self._run_scenario('preexisting_club_refusal')
        self.assertTrue(res['ok'])
        self.assertEqual(res['refused'], 'preexisting_club_id_exists')
        self.assertEqual(res['deleteCallsCount'], 0)

    def test_post_409_conflict_not_owned(self):
        """BKR2: POST 409 conflict is a definite refusal; does not adopt foreign row or DELETE."""
        res = self._run_scenario('post_409_conflict_not_owned')
        self.assertTrue(res['ok'])
        self.assertFalse(res['createdClub'])
        self.assertEqual(res['deleteCallsCount'], 0)

    def test_lost_post_reconciled_exact(self):
        """BKR2: ambiguous network timeout reconciles ownership only when exact matching row exists."""
        res = self._run_scenario('lost_post_reconciled_exact')
        self.assertTrue(res['ok'])
        self.assertTrue(res['createdClub'])
        self.assertTrue(res['deletedCommittedRow'])

    def test_lost_post_foreign_row_rejected(self):
        """BKR2/BKR6: readback finding a foreign row with different owner/name is NOT adopted after POST attempt."""
        res = self._run_scenario('lost_post_foreign_row_rejected')
        self.assertTrue(res['ok'])
        self.assertEqual(res['postAttempts'], 1)
        self.assertFalse(res['createdClub'])
        self.assertEqual(res['deleteCallsCount'], 0)

    def test_partial_creation_cleanup(self):
        """BKR2/BKR6: when bank fails after club succeeds, club & member are cleaned up."""
        res = self._run_scenario('partial_creation_cleanup')
        self.assertTrue(res['ok'])
        self.assertIn('clubs', res['deletedTables'])
        self.assertIn('club_members', res['deletedTables'])
        self.assertNotIn('club_bank_accounts', res['deletedTables'])

    def test_delete_failure_reported(self):
        """BKR2/BKR6: failure to delete bank account results in verified_absent=false after reaching DELETE."""
        res = self._run_scenario('delete_failure_reported')
        self.assertTrue(res['ok'])
        self.assertEqual(res['postBankCalls'], 1)
        self.assertEqual(res['deleteCalls'], 1)
        receipt = res['receipt']
        self.assertFalse(receipt['verified_absent'])
        self.assertFalse(receipt['removed'])

    def test_production_http_adapter_403_definite_rejection_no_adoption(self):
        """BKR2: production restWrite preserves HTTP 403 status; helper never adopts readback or DELETEs."""
        import subprocess
        script = (
            "const { restGet, restWrite, makeEnvTransport, DisposableBankFixture } = "
            "require('./scripts/bh07_appheap/run_app_profile_heap.js');\n"
            "const assert = require('assert');\n"
            "let posted = false;\n"
            "let row = null;\n"
            "let deleted = false;\n"
            "global.fetch = async (url, options = {}) => {\n"
            "  const table = new URL(url).pathname.split('/').pop();\n"
            "  if (options.method === 'POST') {\n"
            "    posted = true;\n"
            "    row = JSON.parse(options.body)[0];\n"
            "    return { ok: false, status: 403, text: async () => 'permission denied' };\n"
            "  }\n"
            "  if (options.method === 'DELETE') {\n"
            "    deleted = true;\n"
            "    return { ok: true };\n"
            "  }\n"
            "  return { ok: true, json: async () => table === 'clubs' && posted && row ? [row] : [] };\n"
            "};\n"
            "const env = { API_URL: 'http://127.0.0.1:54321', SERVICE_ROLE_KEY: 'test-key' };\n"
            "const transport = makeEnvTransport(env);\n"
            "const fixture = new DisposableBankFixture({ ownerUserId: 'test-owner', clubName: 'test-owned-club' });\n"
            "(async () => {\n"
            "  let caughtStatus = null;\n"
            "  try {\n"
            "    await fixture.ensure(transport);\n"
            "  } catch (err) {\n"
            "    caughtStatus = err.status ?? null;\n"
            "  }\n"
            "  await fixture.cleanup(transport);\n"
            "  assert.strictEqual(caughtStatus, 403, 'Expected status 403 forwarded from adapter');\n"
            "  assert.strictEqual(fixture.createdClub, false, 'Helper must not adopt row after 403 rejection');\n"
            "  assert.strictEqual(deleted, false, 'Cleanup must not DELETE after 403 rejection');\n"
            "  console.log(JSON.stringify({ ok: true, status: caughtStatus }));\n"
            "})().catch(err => { console.error(err); process.exit(1); });\n"
        )
        result = subprocess.run(
            ['node', '-e', script],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, f"HTTP 403 production control failed: {result.stderr}")


class TestBankCoverageAuditorCLI(unittest.TestCase):
    """Real auditor CLI tests with clones of finance_heap_evidence (BKR5)."""

    def setUp(self):
        self.source = ROOT / 'docs/reviews/bh07/finance_heap_evidence'
        self.assertTrue(self.source.is_dir(), f"Evidence directory missing: {self.source}")
        self.original = json.loads((self.source / 'summary.json').read_bytes())

    def _clone_and_audit(self, summary_data):
        import shutil
        import subprocess
        import tempfile

        tmp_dir = ROOT / 'build' if (ROOT / 'build').is_dir() else None
        with tempfile.TemporaryDirectory(prefix='bh07_bank_audit_test_', dir=tmp_dir) as tmp:
            directory = Path(tmp)
            for item in self.source.iterdir():
                if item.is_file():
                    shutil.copyfile(item, directory / item.name)
            (directory / 'summary.json').write_bytes(
                (json.dumps(summary_data, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
            )
            # Re-render report.md using production run_app_profile_heap.js renderReport
            renderer = (
                "const fs=require('fs');const r=require(process.argv[1]);"
                "fs.writeFileSync(process.argv[3], r.renderReport(JSON.parse(fs.readFileSync(process.argv[2], 'utf8'))));"
            )
            subprocess.run(
                ['node', '-e', renderer, str(ROOT / 'scripts/bh07_appheap/run_app_profile_heap.js'),
                 str(directory / 'summary.json'), str(directory / 'report.md')],
                check=True,
                capture_output=True,
            )
            # Rehash hashes.sha256
            manifest_lines = []
            for name in ('summary.json', 'report.md', 'run.log'):
                digest = hashlib.sha256((directory / name).read_bytes()).hexdigest()
                manifest_lines.append(f"{digest}  {name}\n")
            (directory / 'hashes.sha256').write_bytes(''.join(manifest_lines).encode('utf-8'))

            result = subprocess.run(
                ['python', '-X', 'utf8', str(ROOT / 'scripts/bh07_appheap/verify_evidence.py'),
                 '--dir', str(directory)],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
            )
            return result

    def test_legacy_positive_exit0(self):
        """Legacy finance evidence clone without bank profile passes auditor CLI (exit 0)."""
        data = copy.deepcopy(self.original)
        result = self._clone_and_audit(data)
        self.assertEqual(result.returncode, 0, f"Legacy positive failed auditor CLI: {result.stdout}\n{result.stderr}")

    def test_bank_profile_missing_mandatory_bank_id_or_load_exit1(self):
        """Bank profile without bank_account_id/load fails auditor CLI (exit 1) fail-closed (BKR5)."""
        data = copy.deepcopy(self.original)
        data['coverage_profile'] = 'bank'
        data['bank_coverage_contract'] = {
            'version': '1.0',
            'required_owner_load': ['bank_account_id', 'bank', 'receiver'],
        }
        data['cleanup'].update(
            disposable_bank_created=True,
            disposable_club_created=True,
            disposable_bank_id_sha256_12='0123456789ab',
            disposable_club_id_sha256_12='abcdef012345',
            disposable_bank_removed=True,
            disposable_bank_verified_absent=True,
            disposable_club_removed=True,
            disposable_club_verified_absent=True,
        )
        result = self._clone_and_audit(data)
        self.assertEqual(result.returncode, 1, f"Expected auditor CLI to fail-closed with exit 1, got 0:\n{result.stdout}")
        self.assertIn('bank coverage profile requires bank_account_id in summary.sentinels metadata', result.stdout)


class TestBankCoverageOutputGuard(unittest.TestCase):
    """Production controls for fresh output ownership and refusal (BKR7)."""

    def test_refusal_on_preexisting_directory_preserves_bytes_and_no_mutation(self):
        """Runner must refuse existing target for --bank-coverage, leaving all files identical and 0 mutations."""
        import subprocess
        import tempfile

        tmp_dir = ROOT / 'build' if (ROOT / 'build').is_dir() else None
        with tempfile.TemporaryDirectory(prefix='bh07_guard_test_', dir=tmp_dir) as tmp:
            test_dir = Path(tmp) / 'existing_evidence'
            test_dir.mkdir(parents=True)
            file_a = test_dir / 'summary.json'
            file_a.write_text('{"sentinel": "preexisting_content"}', encoding='utf-8')
            file_b = test_dir / 'hashes.sha256'
            file_b.write_text('dummy_hash', encoding='utf-8')

            def get_dir_hashes(d):
                hashes = {}
                for p in d.rglob('*'):
                    if p.is_file():
                        hashes[p.relative_to(d).as_posix()] = hashlib.sha256(p.read_bytes()).hexdigest()
                return hashes

            before_hashes = get_dir_hashes(test_dir)

            # Fake fetch prevents live API access even if guard is broken and counts mutations
            runner_script = (
                "let apiMutations = 0;\n"
                "global.fetch = async (url, opts = {}) => {\n"
                "  if (opts && (opts.method === 'POST' || opts.method === 'DELETE' || opts.method === 'PATCH')) {\n"
                "    apiMutations++;\n"
                "  }\n"
                "  throw new Error('FATAL: live network contacted during output refusal test');\n"
                "};\n"
                "const r = require('./scripts/bh07_appheap/run_app_profile_heap.js');\n"
                "const target = process.argv[1];\n"
                "let refused = false;\n"
                "let caughtError = '';\n"
                "try {\n"
                "  r.claimOutputDirectory(target, true);\n"
                "} catch (err) {\n"
                "  refused = true;\n"
                "  caughtError = err.message;\n"
                "}\n"
                "console.log(JSON.stringify({ refused, caughtError, apiMutations }));\n"
            )
            result = subprocess.run(
                ['node', '-e', runner_script, str(test_dir)],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0)
            res = json.loads(result.stdout)
            self.assertTrue(res['refused'])
            self.assertIn('refusing to overwrite existing output directory for --bank-coverage', res['caughtError'])
            self.assertEqual(res['apiMutations'], 0, "No API mutations should occur on refusal")

            # Assert directory contents are 100% untouched
            after_hashes = get_dir_hashes(test_dir)
            self.assertEqual(before_hashes, after_hashes, "Existing directory bytes were modified on refusal!")
            # Assert no failure artifacts written into the refused directory
            self.assertFalse((test_dir / 'run.log').exists())
            self.assertFalse((test_dir / 'report.md').exists())

    def test_refusal_on_nested_under_evidence_bundle(self):
        """Runner must reject nesting output under an existing published evidence bundle."""
        import subprocess
        import tempfile

        tmp_dir = ROOT / 'build' if (ROOT / 'build').is_dir() else None
        with tempfile.TemporaryDirectory(prefix='bh07_nested_guard_', dir=tmp_dir) as tmp:
            canary_bundle = Path(tmp) / 'canary_evidence'
            canary_bundle.mkdir(parents=True)
            (canary_bundle / 'hashes.sha256').write_text('canary_hash_manifest\n', encoding='utf-8')
            (canary_bundle / 'summary.json').write_text('{"canary": true}\n', encoding='utf-8')

            def get_dir_hashes(d):
                return {p.relative_to(d).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                        for p in d.rglob('*') if p.is_file()}

            before_hashes = get_dir_hashes(canary_bundle)

            nested_target = canary_bundle / 'nested_sub_bundle'
            self.assertFalse(nested_target.exists())

            runner_script = (
                "let apiMutations = 0;\n"
                "global.fetch = async (url, opts = {}) => {\n"
                "  if (opts && (opts.method === 'POST' || opts.method === 'DELETE')) apiMutations++;\n"
                "  throw new Error('FATAL: live network contacted during nested refusal test');\n"
                "};\n"
                "const r = require('./scripts/bh07_appheap/run_app_profile_heap.js');\n"
                "const target = process.argv[1];\n"
                "let refused = false;\n"
                "let caughtError = '';\n"
                "try {\n"
                "  r.claimOutputDirectory(target, true);\n"
                "} catch (err) {\n"
                "  refused = true;\n"
                "  caughtError = err.message;\n"
                "}\n"
                "console.log(JSON.stringify({ refused, caughtError, apiMutations }));\n"
            )
            result = subprocess.run(
                ['node', '-e', runner_script, str(nested_target)],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0)
            res = json.loads(result.stdout)
            self.assertTrue(res['refused'])
            self.assertIn('refusing to nest bank evidence under existing evidence bundle', res['caughtError'])
            self.assertFalse(nested_target.exists(), "Nested target must not be created on refusal")
            self.assertEqual(res['apiMutations'], 0)

            # Assert canary bundle bytes are preserved
            after_hashes = get_dir_hashes(canary_bundle)
            self.assertEqual(before_hashes, after_hashes, "Canary bundle was modified!")

    def test_atomic_claim_and_collision_seam(self):
        """Production claimOutputDirectory seam verifies atomic creation and collision rejection."""
        import subprocess
        import tempfile

        tmp_dir = ROOT / 'build' if (ROOT / 'build').is_dir() else None
        with tempfile.TemporaryDirectory(prefix='bh07_atomic_claim_', dir=tmp_dir) as tmp:
            script = (
                "const r = require('./scripts/bh07_appheap/run_app_profile_heap.js');\n"
                "const assert = require('assert');\n"
                "const path = process.argv[1];\n"
                "const target = path + '/new_dir';\n"
                "// 1. Fresh creation succeeds\n"
                "const res = r.claimOutputDirectory(target, true);\n"
                "assert.strictEqual(res.claimed, true);\n"
                "// 2. Collision on existing directory throws\n"
                "assert.throws(() => r.claimOutputDirectory(target, true), /refusing to overwrite/);\n"
                "// 3. Default mode succeeds on existing directory\n"
                "const defRes = r.claimOutputDirectory(target, false);\n"
                "assert.strictEqual(defRes.claimed, true);\n"
                "console.log(JSON.stringify({ ok: true }));\n"
            )
            result = subprocess.run(
                ['node', '-e', script, str(tmp)],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, f"Atomic claim seam failed: {result.stderr}")

    def test_obsolete_bank_fixture_controls_deleted(self):
        """The disconnected bank_fixture_controls.py must not exist."""
        path = ROOT / 'scripts/bh07_appheap/bank_fixture_controls.py'
        self.assertFalse(path.exists(), f"Obsolete fixture copy {path} still exists!")


if __name__ == '__main__':
    unittest.main()
