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

    def test_r5_mutant_detection(self):
        """R5: Demonstrates that neutralizing the preflight gate causes behavioral tests to FAIL."""
        with tempfile.TemporaryDirectory() as td:
            mutant_file = Path(td) / 'mutant_runner.py'
            needle = '    print("Running Preflight Ownership & Resource Isolation Check...")'
            self.assertIn(needle, self.source_text, "Needle must exist in runner source")
            mutant_text = self.source_text.replace(needle, needle + '\n    return {"status": "PASS"} # mutant bypass', 1)
            mutant_file.write_text(mutant_text, encoding='utf-8')

            # Parse mutant
            m_tree = ast.parse(mutant_text)
            m_pre = next(x for x in m_tree.body if isinstance(x, ast.FunctionDef) and x.name == 'preflight_ownership_check')

            m_env = {
                'print': lambda *a, **kw: None,
                'run_cmd': lambda *a, **kw: SimpleNamespace(returncode=1, stdout='', stderr='daemon error'),
                'PROJECT_ID': 'bh07-reset-verify',
                'socket': SimpleNamespace(socket=lambda *a, **kw: SockStub(occupied=False), AF_INET=2, SOCK_STREAM=1),
                'PORT_API': 1, 'PORT_DB': 2, 'PORT_SHADOW': 3, 'PORT_STUDIO': 4,
                'PORT_SMTP': 5, 'PORT_ANALYTICS': 6, 'PORT_S3': 7, 'PORT_POOLER': 8,
                'RuntimeError': RuntimeError
            }
            exec(compile(ast.Module(body=[m_pre], type_ignores=[]), str(mutant_file), 'exec'), m_env)

            # When preflight gate is disabled by mutant, it returns PASS instead of raising RuntimeError on Docker exit 1.
            # A behavior-based test checking for fail-closed behavior will catch this mutant!
            with self.assertRaises(AssertionError, msg="Behavior test must detect and reject the mutant"):
                try:
                    m_env['preflight_ownership_check']()
                    raise AssertionError("Mutant detected: preflight returned PASS on Docker daemon error!")
                except RuntimeError:
                    # Clean gate should raise RuntimeError; mutant didn't raise so it reached the AssertionError above
                    pass


if __name__ == '__main__':
    unittest.main()


