"""Regression probe for the local rehearsal cleanup gate.

The probe compiles the current cleanup `finally` block and final `return` from
`run_local_rehearsal.py` rather than copying the cleanup logic. It uses only
synthetic resource names, a temporary private directory, and a stateful Docker
stub; no real container, network, credential, dump or JWT is touched.

Cases:
  * positive: all owned resources and the private path are removed -> exit 0
  * private cleanup failure -> non-zero and FAIL
  * Docker remove failure -> non-zero and FAIL
  * one Docker removal fails but the remaining resources are still attempted
  * an earlier run failure is preserved while cleanup also fails
"""
import ast
import json
import shutil
import sys
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace

SOURCE = Path(__file__).resolve().parents[2] / 'scripts/bh07_backup/run_local_rehearsal.py'


def load_probe():
    tree = ast.parse(SOURCE.read_text(encoding='utf-8'))
    main = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'main')
    block = next(node for node in main.body if isinstance(node, ast.Try))
    probe = ast.FunctionDef(
        name='probe',
        args=ast.arguments(posonlyargs=[], args=[], kwonlyargs=[], kw_defaults=[], defaults=[]),
        body=block.finalbody + [main.body[-1]],
        decorator_list=[],
    )
    code = compile(ast.fix_missing_locations(ast.Module(body=[probe], type_ignores=[])), str(SOURCE), 'exec')
    return code


class FakeDocker:
    def __init__(self, containers, fail_rm=()):
        self.containers = set(containers)
        self.network = True
        self.fail_rm = set(fail_rm)
        self.rm_calls = []
        self.network_rm_calls = 0

    @staticmethod
    def result(code, stderr=b''):
        return SimpleNamespace(returncode=code, stderr=stderr, stdout=b'')

    def __call__(self, args, **kwargs):
        if args[:2] == ['docker', 'inspect']:
            name = args[2]
            if name in self.containers:
                return self.result(0, b'[]')
            return self.result(1, ('Error: No such object: ' + name).encode())
        if args[:3] == ['docker', 'network', 'inspect']:
            if self.network:
                return self.result(0, b'[]')
            return self.result(1, b'Error response from daemon: network not found')
        if args[:3] == ['docker', 'rm', '-f']:
            name = args[-1]
            self.rm_calls.append(name)
            if name in self.fail_rm:
                return self.result(1, b'remove failed')
            self.containers.discard(name)
            return self.result(0, b'')
        if args[:3] == ['docker', 'network', 'rm']:
            self.network_rm_calls += 1
            self.network = False
            return self.result(0, b'')
        raise AssertionError('unexpected command in cleanup probe: ' + repr(args[:3]))


class FakeShutil:
    def __init__(self, remove):
        self.remove = remove
        self.calls = 0

    def rmtree(self, path, ignore_errors=False):
        self.calls += 1
        if self.remove:
            shutil.rmtree(path, ignore_errors=ignore_errors)


def run_case(code, case, containers, fail_rm=(), private_remove=True, status='PASS local rehearsal; pending review', failure_type=None):
    with tempfile.TemporaryDirectory(prefix='bh07-cleanup-probe-') as tmp:
        root = Path(tmp)
        private = root / 'private'
        private.mkdir()
        (private / 'database.dump').write_text('synthetic only')
        (private / 'roles.sql').write_text('synthetic only')
        out = root / 'out'
        out.mkdir()
        summary = {'status': status, 'checks': [{'pass': True}]}
        if failure_type:
            summary['failure_type'] = failure_type
        docker = FakeDocker(containers, fail_rm)
        fake_shutil = FakeShutil(private_remove)
        env = {
            'cmd': docker,
            'owned': list(containers),
            'NETWORK': 'synthetic-network',
            'shutil': fake_shutil,
            'private': private,
            'summary': summary,
            'time': time,
            'started': time.monotonic(),
            'out': out,
            'json': json,
        }
        exec(code, env)
        exit_code = env['probe']()
        record = {
            'case': case,
            'actual_exit': exit_code,
            'expected_exit_zero': case == 'positive',
            'status': summary.get('status'),
            'failure_type': summary.get('failure_type'),
            'private_dumps_keys_removed': summary.get('private_dumps_keys_removed'),
            'cleanup_failed': summary.get('cleanup_failed'),
            'cleanup_errors': summary.get('cleanup_errors', []),
            'container_rm_calls': list(docker.rm_calls),
            'network_rm_calls': docker.network_rm_calls,
            'private_rmtree_calls': fake_shutil.calls,
        }
        expected = {
            'positive': (0, 'PASS local rehearsal; pending review', True, False),
            'private_cleanup_failure': (1, 'FAIL', False, True),
            'docker_cleanup_failure': (1, 'FAIL', True, True),
            'cleanup_continues_after_error': (1, 'FAIL', True, True),
            'original_failure_preserved': (1, 'FAIL', False, True),
        }[case]
        ok = (
            exit_code == expected[0]
            and summary.get('status') == expected[1]
            and summary.get('private_dumps_keys_removed') is expected[2]
            and bool(summary.get('cleanup_failed')) is expected[3]
        )
        if case == 'cleanup_continues_after_error':
            ok = ok and set(docker.rm_calls) == set(containers) and docker.network_rm_calls == 1
        if case == 'original_failure_preserved':
            ok = ok and summary.get('failure_type') == 'RuntimeError'
        record['ok'] = ok
        return record


def main():
    code = load_probe()
    cases = [
        run_case(code, 'positive', ['container-a', 'container-b']),
        run_case(code, 'private_cleanup_failure', ['container-a', 'container-b'], private_remove=False),
        run_case(code, 'docker_cleanup_failure', ['container-a', 'container-b'], fail_rm={'container-a'}),
        run_case(code, 'cleanup_continues_after_error', ['container-a', 'container-b'], fail_rm={'container-a'}),
        run_case(code, 'original_failure_preserved', ['container-a'], private_remove=False, status='FAIL', failure_type='RuntimeError'),
    ]
    print(json.dumps(cases, indent=2))
    return 0 if all(case['ok'] for case in cases) else 1


if __name__ == '__main__':
    raise SystemExit(main())
