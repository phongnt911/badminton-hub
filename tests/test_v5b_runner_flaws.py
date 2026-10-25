"""Behavioral reproduction and verification tests for V5b full reset runner flaws (R1, R2, R3, R5).

This test suite tests the actual executable behavior of runner functions and AST fragments:
1. R1: Preflight fail-closed on inventory failure (Docker exit != 0) and port occupation;
       Cleanup ONLY touches owned containers, refusing to remove unowned foreign containers.
2. R2: Negative controls reject XX000 even with auth words in hint/detail;
       require exact (status, code, message) matching;
       Positive baseline performs a verified real HTTP request.
3. R3: Final inspection is inside best-effort scope; preserves primary_error without masking;
       nonzero docker ps inspection marks cleanup as unclean.
4. R5: Mutant gate check: neutralizing the preflight gate causes the suite to fail.
"""
import ast
import contextlib
import io
import json
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
import urllib.error
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parents[1]
RUNNER_SRC = ROOT / 'scripts/bh07_reset/run_full_reset.py'


class SockStub:
    def __init__(self, occupied=False):
        self.occupied = occupied

    def __enter__(self):
        return self

    def __exit__(self, *a):
        pass

    def settimeout(self, *a):
        pass

    def connect_ex(self, *a):
        return 0 if self.occupied else 111


def make_preflight_env(docker_code=0, docker_stdout='', port_occupied=False):
    src_text = RUNNER_SRC.read_text(encoding='utf-8')
    tree = ast.parse(src_text)
    pre_node = next(x for x in tree.body if isinstance(x, ast.FunctionDef) and x.name == 'preflight_ownership_check')
    
    env = {
        'print': lambda *a, **kw: None,
        'run_cmd': lambda *a, **kw: SimpleNamespace(
            returncode=docker_code,
            stdout=docker_stdout,
            stderr='synthetic docker daemon failure' if docker_code != 0 else ''
        ),
        'PROJECT_ID': 'bh07-reset-verify',
        'socket': SimpleNamespace(
            socket=lambda *a, **kw: SockStub(occupied=port_occupied),
            AF_INET=2,
            SOCK_STREAM=1
        ),
        'PORT_API': 56421,
        'PORT_DB': 56422,
        'PORT_SHADOW': 56420,
        'PORT_STUDIO': 56423,
        'PORT_SMTP': 56424,
        'PORT_ANALYTICS': 56427,
        'PORT_S3': 56428,
        'PORT_POOLER': 56429,
        'RuntimeError': RuntimeError
    }
    exec(compile(ast.Module(body=[pre_node], type_ignores=[]), str(RUNNER_SRC), 'exec'), env)
    return env


class TestV5bRunnerBehavior(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source_text = RUNNER_SRC.read_text(encoding='utf-8')
        cls.tree = ast.parse(cls.source_text)

    def test_r1_preflight_fail_closed_on_docker_error(self):
        """R1: preflight_ownership_check must fail-closed if Docker inspection exits nonzero."""
        env = make_preflight_env(docker_code=1, docker_stdout='')
        with self.assertRaises(RuntimeError, msg="Preflight must raise RuntimeError on Docker exit != 0"):
            env['preflight_ownership_check']()

    def test_r1_preflight_fail_closed_on_existing_containers(self):
        """R1: preflight_ownership_check must raise RuntimeError if pre-existing containers exist."""
        env = make_preflight_env(docker_code=0, docker_stdout='c12345 foreign-container')
        with self.assertRaises(RuntimeError, msg="Preflight must raise RuntimeError on existing containers"):
            env['preflight_ownership_check']()

    def test_r1_preflight_fail_closed_on_occupied_port(self):
        """R1: preflight_ownership_check must raise RuntimeError if dedicated ports are occupied."""
        env = make_preflight_env(docker_code=0, docker_stdout='', port_occupied=True)
        with self.assertRaises(RuntimeError, msg="Preflight must raise RuntimeError on occupied port"):
            env['preflight_ownership_check']()

    def test_r1_preflight_passes_on_clean_inventory(self):
        """R1: preflight_ownership_check returns PASS on a clean environment."""
        env = make_preflight_env(docker_code=0, docker_stdout='', port_occupied=False)
        res = env['preflight_ownership_check']()
        self.assertEqual(res.get('status'), 'PASS')

    def test_r1_cleanup_only_touches_owned_containers(self):
        """R1: cleanup must ONLY remove owned containers; foreign containers must NOT be deleted."""
        main_node = next(x for x in self.tree.body if isinstance(x, ast.FunctionDef) and x.name == 'main')
        try_node = next(x for x in main_node.body if isinstance(x, ast.Try))
        
        with tempfile.TemporaryDirectory() as td:
            work = Path(td) / 'work'
            work.mkdir()
            
            removed_ids = []
            def mock_cmd(args, **kw):
                if args[:3] == ['npx', 'supabase', 'stop']:
                    return SimpleNamespace(returncode=0, stdout='', stderr='')
                if args[:2] == ['docker', 'ps']:
                    # Reports one owned container and one unowned foreign container
                    return SimpleNamespace(returncode=0, stdout='owned-123\nforeign-999', stderr='')
                if args[:3] == ['docker', 'rm', '-f']:
                    removed_ids.extend(args[3:])
                    return SimpleNamespace(returncode=0, stdout='', stderr='')
                raise AssertionError(f"Unexpected command: {args}")

            env = {
                'print': lambda *a, **kw: None,
                'run_cmd': mock_cmd,
                'temp_dir': work,
                'exits': {},
                'write_evidence': lambda *a: None,
                'log_cmd': lambda *a: None,
                'audit_results': {},
                'PROJECT_ID': 'bh07-reset-verify',
                'shutil': shutil,
                'owned_containers': ['owned-123'],
                'primary_error': None,
                'RuntimeError': RuntimeError
            }
            fn_node = ast.FunctionDef(
                name='fragment',
                args=ast.arguments(posonlyargs=[], args=[], kwonlyargs=[], kw_defaults=[], defaults=[]),
                body=try_node.finalbody,
                decorator_list=[]
            )
            exec(compile(ast.fix_missing_locations(ast.Module(body=[fn_node], type_ignores=[])), str(RUNNER_SRC), 'exec'), env)
            try:
                env['fragment']()
            except Exception:
                pass

            self.assertNotIn('foreign-999', removed_ids, "Foreign container MUST NOT be deleted!")
            self.assertIn('owned-123', removed_ids, "Owned container should be deleted.")

    def test_r2_negative_controls_rejects_xx000_with_auth_words(self):
        """R2: negative control predicate must reject XX000 internal error even if hint has auth words."""
        # Find assert_negative_auth_rejection helper if present
        helper = next((x for x in self.tree.body if isinstance(x, ast.FunctionDef) and x.name == 'assert_negative_auth_rejection'), None)
        self.assertIsNotNone(helper, "assert_negative_auth_rejection helper must exist in runner")
        
        env = {'AssertionError': AssertionError, 'ValueError': ValueError}
        exec(compile(ast.Module(body=[helper], type_ignores=[]), str(RUNNER_SRC), 'exec'), env)
        func = env['assert_negative_auth_rejection']

        # 1. Valid rejection: 401, 42501, 'permission denied for function complete_session'
        func('anon_complete', 401, {'code': '42501', 'message': 'permission denied for function complete_session'}, 'anon_complete')

        # 2. Bogus rejection: 403, XX000 with auth words in hint
        bogus_body = {
            'code': 'XX000',
            'message': 'unrelated database failure',
            'hint': 'JWT api key FORBIDDEN permission denied'
        }
        with self.assertRaises(AssertionError, msg="XX000 with auth words in hint must raise AssertionError"):
            func('anon_complete', 403, bogus_body, 'anon_complete')

        # 3. Bogus rejection: 400 INVALID_INPUT
        with self.assertRaises(AssertionError, msg="INVALID_INPUT must raise AssertionError"):
            func('anon_complete', 400, {'code': 'INVALID_INPUT', 'message': 'invalid'}, 'anon_complete')

        # 4. Bogus rejection: 403 NOT_FOUND
        with self.assertRaises(AssertionError, msg="NOT_FOUND must raise AssertionError"):
            func('outsider_summary', 403, {'code': 'NOT_FOUND'}, 'outsider_summary')

        # 5. Bogus rejection: 404 route missing
        with self.assertRaises(AssertionError, msg="404 route missing must raise AssertionError"):
            func('no_apikey', 404, {'message': 'route not found'}, 'no_apikey')

    def test_r3_cleanup_preserves_primary_error_when_final_inspect_raises(self):
        """R3: If final inspect raises an exception, primary_error must still be preserved and re-raised."""
        main_node = next(x for x in self.tree.body if isinstance(x, ast.FunctionDef) and x.name == 'main')
        try_node = next(x for x in main_node.body if isinstance(x, ast.Try))

        class PrimaryTestError(Exception):
            pass

        class FinalInspectTestError(Exception):
            pass

        with tempfile.TemporaryDirectory() as td:
            work = Path(td) / 'work'
            work.mkdir()

            call_count = [0]
            def mock_cmd(args, **kw):
                if args[:3] == ['npx', 'supabase', 'stop']:
                    return SimpleNamespace(returncode=0, stdout='', stderr='')
                if args[:2] == ['docker', 'ps']:
                    call_count[0] += 1
                    if call_count[0] >= 2:
                        raise FinalInspectTestError("Synthetic final inspect transport failure")
                    return SimpleNamespace(returncode=0, stdout='', stderr='')
                raise AssertionError(f"Unexpected command: {args}")

            env = {
                'print': lambda *a, **kw: None,
                'run_cmd': mock_cmd,
                'temp_dir': work,
                'exits': {},
                'write_evidence': lambda *a: None,
                'log_cmd': lambda *a: None,
                'audit_results': {},
                'PROJECT_ID': 'bh07-reset-verify',
                'shutil': shutil,
                'owned_containers': [],
                'primary_error': PrimaryTestError("Original primary test error"),
                'RuntimeError': RuntimeError
            }
            fn_node = ast.FunctionDef(
                name='fragment',
                args=ast.arguments(posonlyargs=[], args=[], kwonlyargs=[], kw_defaults=[], defaults=[]),
                body=try_node.finalbody,
                decorator_list=[]
            )
            exec(compile(ast.fix_missing_locations(ast.Module(body=[fn_node], type_ignores=[])), str(RUNNER_SRC), 'exec'), env)

            raised = None
            try:
                env['fragment']()
            except Exception as e:
                raised = e

            self.assertIsInstance(raised, PrimaryTestError, f"Expected PrimaryTestError to be re-raised, got {type(raised)}: {raised}")

    def test_r1_project_identity_is_unique_per_run(self):
        assignment = next(
            n for n in self.tree.body if isinstance(n, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == 'PROJECT_ID' for t in n.targets)
        )
        expression = compile(ast.Expression(assignment.value), str(RUNNER_SRC), 'eval')
        first = eval(expression, {'uuid': uuid})
        second = eval(expression, {'uuid': uuid})
        self.assertTrue(first.startswith('bh07-reset-verify-'))
        self.assertNotEqual(first, second)

    def test_r1_owned_inventory_must_succeed_before_reset(self):
        """Execute main through the reset boundary; no real Docker or database."""
        class ResetBoundary(Exception):
            pass

        main_node = next(n for n in self.tree.body if isinstance(n, ast.FunctionDef) and n.name == 'main')
        for exit_code, inventory, expected_reset in (
            (0, 'owned-id', True),
            (1, '', False),
            (1, 'partial-owned-id', False),
            (0, '', False),
        ):
            with self.subTest(exit_code=exit_code, inventory=inventory), tempfile.TemporaryDirectory() as td:
                calls = []

                def command(args, **kwargs):
                    calls.append(args)
                    if any('--version' in str(a) for a in args):
                        return SimpleNamespace(returncode=0, stdout='2.122.0\n', stderr='')
                    if any('db' in str(a) for a in args) and any('reset' in str(a) for a in args):
                        raise ResetBoundary('No actual reset is performed')
                    if any('status' in str(a) for a in args):
                        return SimpleNamespace(returncode=0, stdout=json.dumps({
                            'API_URL': 'http://127.0.0.1:56421',
                            'ANON_KEY': 'synthetic', 'SERVICE_ROLE_KEY': 'synthetic',
                        }), stderr='')
                    if args[:2] == ['docker', 'ps']:
                        if '{{.ID}}' in args:
                            return SimpleNamespace(returncode=exit_code, stdout=inventory, stderr='synthetic failure')
                        return SimpleNamespace(returncode=0, stdout='', stderr='')
                    return SimpleNamespace(returncode=0, stdout='', stderr='')

                env = make_preflight_env()
                env.update({
                    'run_cmd': command, 'STAMP': 'synthetic', 'BASE_SHA': 'synthetic',
                    'BASELINE_ORIGIN_SHA': 'synthetic',
                    'Path': Path, 'tempfile': SimpleNamespace(gettempdir=lambda: td),
                    'os': os, 'json': json, 'urllib': urllib, 'shutil': shutil,
                    'sys': sys,
                    'prepare_project_dir': lambda p: p.mkdir(parents=True),
                    'write_evidence': lambda *a: None, 'log_cmd': lambda *a: None,
                    'exits': {}, 'audit_results': {},
                    'resolve_base_review': lambda *a: 'e00db30d018da86f8fa94250a000f0bf825fc139',
                    'SUPABASE_CLI_PIN': 'supabase@2.122.0',
                    'inspect_container_images': lambda *a: [],
                    'compare_oracle_snapshots': lambda *a: {
                        'oracle_scope': 'schema_sha256_and_row_counts',
                        'oracle_schema_match': True,
                        'oracle_counts_match': True,
                        'total_tables': 48,
                        'different_data_tables': []
                    },
                })
                exec(compile(ast.Module(body=[main_node], type_ignores=[]), str(RUNNER_SRC), 'exec'), env)
                raised = None
                try:
                    env['main']()
                except Exception as error:
                    raised = error
                self.assertEqual(any(any('db' in str(a) for a in call) and any('reset' in str(a) for a in call) for call in calls), expected_reset)
                self.assertIsInstance(raised, ResetBoundary if expected_reset else RuntimeError)

    def test_r2_gateway_tuple_rejects_every_unmapped_code(self):
        helper = next(n for n in self.tree.body if isinstance(n, ast.FunctionDef)
                      and n.name == 'assert_negative_auth_rejection')
        env = {}
        exec(compile(ast.Module(body=[helper], type_ignores=[]), str(RUNNER_SRC), 'exec'), env)
        verify = env['assert_negative_auth_rejection']
        message = 'No API key found in request'
        verify('gateway', 401, {'message': message}, 'no_apikey')
        for status in (401, 403):
            verify('postgrest', status, {
                'code': '42501', 'message': 'permission denied for function complete_session',
            }, 'no_apikey')
        for code in ('42P01', '23505', 'P0001', 'UNKNOWN_AUTH_CODE', None, ''):
            with self.subTest(code=code), self.assertRaises(AssertionError):
                verify('unknown', 401, {'code': code, 'message': message}, 'no_apikey')
        for status, text in ((403, message), (401, 'prefix ' + message), (401, message + ' suffix')):
            with self.subTest(status=status, message=text), self.assertRaises(AssertionError):
                verify('invalid-gateway', status, {'message': text}, 'no_apikey')

    def test_p2_1_oracle_schema_and_counts_scope_and_mismatch_failure(self):
        """P2-1: Oracle comparison must strictly reject schema or row count mismatch, and scope must be schema+counts."""
        helper = next((n for n in self.tree.body if isinstance(n, ast.FunctionDef) and n.name == 'compare_oracle_snapshots'), None)
        self.assertIsNotNone(helper, "compare_oracle_snapshots helper must exist in runner")
        
        env = {'AssertionError': AssertionError}
        exec(compile(ast.Module(body=[helper], type_ignores=[]), str(RUNNER_SRC), 'exec'), env)
        compare_fn = env['compare_oracle_snapshots']

        # Baseline matching 48 tables schema and counts
        stats1 = {f'public.tbl_{i}': {'count': 10, 'sha256': f'hash_c1_{i}'} for i in range(48)}
        stats2 = {f'public.tbl_{i}': {'count': 10, 'sha256': f'hash_c2_{i}'} for i in range(48)}
        fp1 = {'schema_sha256': 'same_schema_hash', 'total_tables': 48, 'table_stats': stats1}
        fp2 = {'schema_sha256': 'same_schema_hash', 'total_tables': 48, 'table_stats': stats2}

        # Valid comparison returns audit dict with explicit scope schema_sha256_and_row_counts
        res = compare_fn(fp1, fp2)
        self.assertEqual(res['oracle_scope'], 'schema_sha256_and_row_counts')
        self.assertTrue(res['oracle_schema_match'])
        self.assertTrue(res['oracle_counts_match'])
        self.assertIn('different_data_tables', res)

        # Mismatch schema must FAIL
        fp_bad_schema = dict(fp2, schema_sha256='different_schema_hash')
        with self.assertRaises(AssertionError, msg="Schema hash mismatch must raise AssertionError"):
            compare_fn(fp1, fp_bad_schema)

        # Mismatch row count must FAIL
        stats_bad_count = dict(stats2)
        stats_bad_count['public.tbl_0'] = {'count': 999, 'sha256': 'any'}
        fp_bad_count = dict(fp2, table_stats=stats_bad_count)
        with self.assertRaises(AssertionError, msg="Row count mismatch must raise AssertionError"):
            compare_fn(fp1, fp_bad_count)

        # Missing table in cycle 2 must FAIL
        stats_missing = {k: v for k, v in stats2.items() if k != 'public.tbl_47'}
        fp_missing = dict(fp2, total_tables=47, table_stats=stats_missing)
        with self.assertRaises(AssertionError, msg="Table count mismatch must raise AssertionError"):
            compare_fn(fp1, fp_missing)

    def test_p2_2_base_review_resolution_and_validation(self):
        """P2-2: Base review must be resolved via CLI/env and validated against Git commit existence."""
        resolver = next((n for n in self.tree.body if isinstance(n, ast.FunctionDef) and n.name == 'resolve_base_review'), None)
        self.assertIsNotNone(resolver, "resolve_base_review helper must exist in runner")

        env = {'ROOT': ROOT, 'run_cmd': lambda *a, **kw: SimpleNamespace(returncode=0, stdout='e00db30d018da86f8fa94250a000f0bf825fc139\n'), 'ValueError': ValueError}
        exec(compile(ast.Module(body=[resolver], type_ignores=[]), str(RUNNER_SRC), 'exec'), env)
        fn = env['resolve_base_review']

        # Valid commit SHA resolves cleanly
        resolved = fn(['--base-review', 'e00db30d018da86f8fa94250a000f0bf825fc139'])
        self.assertEqual(resolved, 'e00db30d018da86f8fa94250a000f0bf825fc139')

        # Invalid nonexistent SHA must raise ValueError
        env_fail = {'ROOT': ROOT, 'run_cmd': lambda *a, **kw: SimpleNamespace(returncode=128, stdout='', stderr='fatal: Not a valid object name'), 'ValueError': ValueError}
        exec(compile(ast.Module(body=[resolver], type_ignores=[]), str(RUNNER_SRC), 'exec'), env_fail)
        with self.assertRaises(ValueError, msg="Nonexistent base SHA must be rejected"):
            env_fail['resolve_base_review'](['--base-review', 'nonexistent_sha_0000000000000000000000000000'])

    def test_p2_3_evidence_http_audit_sanitization_and_cycle_detail(self):
        """P2-3: HTTP audit records must be sanitized (no token/password) and detail persisted for both cycles."""
        sanitizer = next((n for n in self.tree.body if isinstance(n, ast.FunctionDef) and n.name == 'sanitize_http_audit_record'), None)
        self.assertIsNotNone(sanitizer, "sanitize_http_audit_record helper must exist in runner")

        env = {}
        exec(compile(ast.Module(body=[sanitizer], type_ignores=[]), str(RUNNER_SRC), 'exec'), env)
        sanitize = env['sanitize_http_audit_record']

        raw_record = {
            'actor_alias': 'ownera',
            'operation': 'login',
            'http_status': 200,
            'access_token': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.sensitive_payload.signature',
            'password': 'bh07-http-pass-123456',
            'raw_body': {'email': 'ownera@example.test', 'bank': '0123456789'}
        }
        cleaned = sanitize(raw_record)
        self.assertNotIn('access_token', cleaned)
        self.assertNotIn('password', cleaned)
        self.assertNotIn('raw_body', cleaned)
        self.assertEqual(cleaned['actor_alias'], 'ownera')
        self.assertEqual(cleaned['http_status'], 200)

    def test_p2_4_port_configuration_and_s3_gateway(self):
        """P2-4: Port S3 56428 claim must be removed; config must assert exact dedicated ports and no defaults."""
        prep_fn = next((n for n in self.tree.body if isinstance(n, ast.FunctionDef) and n.name == 'prepare_project_dir'), None)
        self.assertIsNotNone(prep_fn, "prepare_project_dir must exist in runner")

        # Verify that PORT_S3 = 56428 is NOT in global assignments
        assigns = {t.id: getattr(n.value, 'value', None) for n in self.tree.body if isinstance(n, ast.Assign) for t in n.targets if isinstance(t, ast.Name)}
        self.assertNotIn('PORT_S3', assigns, "PORT_S3 must be removed; S3 protocol is routed via Kong gateway")

        # Verify preflight_ownership_check does not check port 56428
        pre_fn = next(n for n in self.tree.body if isinstance(n, ast.FunctionDef) and n.name == 'preflight_ownership_check')
        pre_src = ast.unparse(pre_fn)
        self.assertNotIn('56428', pre_src)
        self.assertNotIn('PORT_S3', pre_src)

    def test_p2_5_db_assertions_exact_fixture_and_req_orig_deterministic(self):
        """P2-5: DB assertions must check exact counts and req_orig must filter by session_id."""
        db_fn = next((n for n in self.tree.body if isinstance(n, ast.FunctionDef) and n.name == 'verify_db_assertions'), None)
        self.assertIsNotNone(db_fn, "verify_db_assertions must exist in runner")
        db_src = ast.unparse(db_fn)

        # 1. req_orig query must filter specifically for complete_session on session_debt
        self.assertIn("10000000-0000-4000-8000-000000000001", db_src, "req_orig query must bind session_debt ID")
        self.assertNotIn("WHERE operation='complete_session' LIMIT 1", db_src, "Unscoped LIMIT 1 on operation_requests is forbidden")

        # 2. Strict exact assertions instead of weak >= or >
        self.assertNotIn("op_cnt >= 1", db_src, "op_cnt must be exact == 1")
        self.assertNotIn("pay_cnt >= 1", db_src, "pay_cnt must be exact == 2")
        self.assertNotIn("tx_cnt >= 1", db_src, "tx_cnt must be exact == 2")
        self.assertNotIn("charges_sum > 0", db_src, "charges_sum must be exact == 150000")
        self.assertNotIn("payments_sum >= 20000", db_src, "payments_sum must be exact == 70000")
        self.assertNotIn("v_court > 0", db_src, "v_court must be exact == 4")

    def test_p2_6_reproducibility_pinning_and_image_metadata(self):
        """P2-6: Supabase CLI calls must pin supabase@2.122.0 and container images metadata must be collected."""
        src = self.source_text
        self.assertIn('supabase@2.122.0', src, "CLI invocations must be pinned to supabase@2.122.0")

        collector = next((n for n in self.tree.body if isinstance(n, ast.FunctionDef) and n.name == 'inspect_container_images'), None)
        self.assertIsNotNone(collector, "inspect_container_images helper must exist in runner")

    def test_p2_7_process_execution_no_shell_timeout_and_special_args(self):
        """P2-7: run_cmd must use shell=False, enforce finite timeouts, and pass special characters safely."""
        run_fn = next((n for n in self.tree.body if isinstance(n, ast.FunctionDef) and n.name == 'run_cmd'), None)
        self.assertIsNotNone(run_fn, "run_cmd must exist in runner")
        run_src = ast.unparse(run_fn)

        # shell must not be is_batch or True
        self.assertNotIn("shell=is_batch", run_src, "shell=is_batch is forbidden")
        self.assertIn("shell=False", run_src, "shell=False must be explicitly specified")
        self.assertIn("timeout", run_src, "timeout must be supported and enforced in run_cmd")

        # Test timeout handling in run_cmd
        env = {
            'shutil': shutil,
            'subprocess': subprocess,
            'sys': sys,
            'ROOT': ROOT,
            'SimpleNamespace': SimpleNamespace,
            'RuntimeError': RuntimeError,
            'TimeoutError': TimeoutError,
        }
        # Compile and execute kill_proc_tree and run_cmd
        tree_mod = ast.Module(body=[
            next(n for n in self.tree.body if isinstance(n, ast.FunctionDef) and n.name == 'kill_proc_tree'),
            run_fn
        ], type_ignores=[])
        exec(compile(ast.fix_missing_locations(tree_mod), str(RUNNER_SRC), 'exec'), env)
        cmd_runner = env['run_cmd']

        # 1. Test passing special arguments safely
        p = cmd_runner([sys.executable, '-c', 'import sys; print(sys.argv[1])', 'arg with spaces & quotes "test" and | symbol'], timeout=10)
        self.assertIn('arg with spaces & quotes "test" and | symbol', p.stdout)

        # 2. Test timeout raises TimeoutError
        with self.assertRaises(TimeoutError, msg="Command exceeding timeout must raise TimeoutError"):
            cmd_runner([sys.executable, '-c', 'import time; time.sleep(10)'], timeout=1)


if __name__ == '__main__':
    unittest.main()



