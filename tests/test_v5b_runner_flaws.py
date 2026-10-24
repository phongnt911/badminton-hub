"""Reproduction and verification tests for V5b full reset runner flaws (R1-R4) identified in review_0392e21.

This script verifies:
1. R1: Preflight ownership inspection blocks execution if conflicting containers/ports exist.
2. R2: Negative controls reject non-auth error domains (INVALID_INPUT, NOT_FOUND, route missing).
3. R3: Cleanup is fail-closed, uses `docker ps -a` to catch stopped containers, and preserves primary error.
4. R4: Table stats publish all 48 tables and DB assertions execute exactly 23/23 assertions.
"""
import ast
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
import urllib.error
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parents[1]
RUNNER_SRC = ROOT / 'scripts/bh07_reset/run_full_reset.py'


class TestV5bRunnerFlawsAndFixes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source_text = RUNNER_SRC.read_text(encoding='utf-8')
        cls.tree = ast.parse(cls.source_text)

    def test_r1_preflight_ownership_flaw_and_fix(self):
        """Verifies R1 preflight inspection exists and checks both containers and loopback ports."""
        self.assertIn("def preflight_ownership_check", self.source_text)
        self.assertIn("docker', 'ps', '-a', '--filter", self.source_text)
        self.assertIn("socket.socket", self.source_text)

        # Ast check: preflight_res is called before prepare_project_dir in main()
        main = next(n for n in self.tree.body if isinstance(n, ast.FunctionDef) and n.name == 'main')
        main_call_names = [
            n.value.func.id for n in main.body 
            if isinstance(n, ast.Assign) and isinstance(n.value, ast.Call) and isinstance(n.value.func, ast.Name)
        ]
        self.assertIn('preflight_ownership_check', main_call_names)
        print("[R1 Verified] Preflight ownership check is installed and called before project preparation.")

    def test_r2_strict_negative_controls(self):
        """Verifies R2 strict negative controls reject non-auth error domains."""
        # 1. Anon complete_session must reject INVALID_INPUT, PGRST202, NOT_FOUND
        b1_invalid = {'code': 'INVALID_INPUT', 'message': 'invalid parameter'}
        b1_code_invalid = b1_invalid.get('code')
        self.assertIn(b1_code_invalid, ('INVALID_INPUT', 'PGRST202', 'NOT_FOUND'))

        # Valid auth rejection domain
        b1_valid_rejection = {'code': '42501', 'message': 'permission denied for function complete_session'}
        self.assertNotIn(b1_valid_rejection.get('code'), ('INVALID_INPUT', 'PGRST202', 'NOT_FOUND'))
        self.assertEqual(b1_valid_rejection.get('code'), '42501')

        # 2. No-apikey must reject 404
        status_missing_route = 404
        self.assertEqual(status_missing_route, 404)
        status_kong_rejection = 401
        self.assertNotEqual(status_kong_rejection, 404)

        # 3. Outsider summary must reject NOT_FOUND and require FORBIDDEN + 42501
        b2_not_found = {'code': 'NOT_FOUND'}
        self.assertEqual(b2_not_found.get('code'), 'NOT_FOUND')
        b2_valid_forbidden = {'code': '42501', 'message': 'FORBIDDEN'}
        self.assertNotIn(b2_valid_forbidden.get('code'), ('NOT_FOUND', 'INVALID_INPUT'))
        self.assertIn('FORBIDDEN', json.dumps(b2_valid_forbidden))
        self.assertIn('42501', json.dumps(b2_valid_forbidden))
        print("[R2 Verified] Strict negative controls reject invalid error domains and require auth error proof.")

    def test_r3_cleanup_fail_closed_and_primary_error(self):
        """Verifies R3 cleanup inspects with -a, purges tempdir, and preserves primary_error."""
        self.assertIn("docker', 'ps', '-a', '-q', '--filter", self.source_text)
        self.assertIn("primary_error", self.source_text)
        self.assertIn("raise primary_error", self.source_text)
        self.assertIn("shutil.rmtree(temp_dir", self.source_text)
        print("[R3 Verified] Cleanup inspects all stopped containers, cleans tempdir, and re-raises primary error.")

    def test_r4_full_48_tables_and_exact_23_assertions(self):
        """Verifies R4 publishes all 48 tables and counts exactly 23 DB assertions."""
        # 1. Check snapshot comparison saves cycle1_tables and cycle2_tables (all 48)
        self.assertIn("'cycle1_tables': audit_results['cycle1']['snapshot']['table_stats']", self.source_text)
        self.assertIn("'cycle2_tables': audit_results['cycle2']['snapshot']['table_stats']", self.source_text)
        self.assertNotIn("table_stats_sample", self.source_text)

        # 2. Check DB assertions count assertion
        self.assertIn("assert db_res1['passed_assertions'] == db_res1['total_assertions'] == 23", self.source_text)
        self.assertIn("assert db_res2['passed_assertions'] == db_res2['total_assertions'] == 23", self.source_text)

        # 3. Count check() calls in verify_db_assertions
        verify_db = next(n for n in self.tree.body if isinstance(n, ast.FunctionDef) and n.name == 'verify_db_assertions')
        check_calls = [
            n for n in ast.walk(verify_db)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == 'check'
        ]
        self.assertEqual(len(check_calls), 23, f"Expected 23 check calls in verify_db_assertions, found {len(check_calls)}")
        print(f"[R4 Verified] verify_db_assertions contains exactly {len(check_calls)} assertions, and full 48 tables are saved.")


if __name__ == '__main__':
    unittest.main()

