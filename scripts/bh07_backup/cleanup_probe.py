"""Regression probe for the local rehearsal cleanup gate.

The probe compiles the current cleanup `finally` block and final `return` from
`run_local_rehearsal.py` rather than copying the cleanup logic. It uses only
synthetic resource names, a temporary private directory, and a stateful Docker
stub; no real container, network, credential, dump or JWT is touched.

The five original controls are retained. Additional controls cover inspect
errors before/after removal, network removal failure, and remove commands that
return success without actually deleting the resource.
"""
import ast
import json
import shutil
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace

SOURCE = Path(__file__).resolve().parents[2] / 'scripts/bh07_backup/run_local_rehearsal.py'

CONTEXT_ERROR = (
    b'Failed to initialize: unable to resolve docker endpoint: context '
    b'"bh07-test-missing-context": context not found: open '
    b'/tmp/bh07-context-meta.json: no such file or directory'
)
DAEMON_ERROR = b'Cannot connect to the Docker daemon at unix:///var/run/docker.sock. Is the docker daemon running?'
PERMISSION_ERROR = b'permission denied while trying to connect to the Docker daemon socket'
TRANSPORT_ERROR = b'error during connect: connection refused'


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
    def __init__(self, containers, fail_rm=(), rm_noop=(), network_rm_fail=False, network_rm_noop=False,
                 inspect_error=None, after_remove_error=CONTEXT_ERROR,
                 inspect_error_after_remove=(), network_inspect_error_after_remove=False):
        self.containers = set(containers)
        self.network = True
        self.fail_rm = set(fail_rm)
        self.rm_noop = set(rm_noop)
        self.network_rm_fail = network_rm_fail
        self.network_rm_noop = network_rm_noop
        self.inspect_error = inspect_error
        self.after_remove_error = after_remove_error
        self.inspect_error_after_remove = set(inspect_error_after_remove)
        self.network_inspect_error_after_remove = network_inspect_error_after_remove
        self.inspect_calls = []
        self.rm_calls = []
        self.network_rm_calls = 0

    @staticmethod
    def result(code, stderr=b''):
        return SimpleNamespace(returncode=code, stderr=stderr, stdout=b'')

    def __call__(self, args, **kwargs):
        if args[:2] == ['docker', 'inspect']:
            name = args[2]
            self.inspect_calls.append(('container', name))
            if self.inspect_error is not None:
                return self.result(1, self.inspect_error)
            if name in self.containers:
                return self.result(0, b'[]')
            if name in self.inspect_error_after_remove:
                return self.result(1, self.after_remove_error)
            return self.result(1, ('Error: No such object: ' + name).encode())
        if args[:3] == ['docker', 'network', 'inspect']:
            self.inspect_calls.append(('network', 'synthetic-network'))
            if self.inspect_error is not None:
                return self.result(1, self.inspect_error)
            if self.network:
                return self.result(0, b'[]')
            if self.network_inspect_error_after_remove:
                return self.result(1, self.after_remove_error)
            return self.result(1, b'Error response from daemon: network synthetic-network not found')
        if args[:3] == ['docker', 'rm', '-f']:
            name = args[-1]
            self.rm_calls.append(name)
            if name in self.fail_rm:
                return self.result(1, b'remove failed')
            if name not in self.rm_noop:
                self.containers.discard(name)
            return self.result(0, b'')
        if args[:3] == ['docker', 'network', 'rm']:
            self.network_rm_calls += 1
            if self.network_rm_fail:
                return self.result(1, b'network remove failed')
            if not self.network_rm_noop:
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


def run_case(code, case, containers, *, fail_rm=(), rm_noop=(), network_rm_fail=False, network_rm_noop=False,
             private_remove=True, status='PASS local rehearsal; pending review', failure_type=None,
             inspect_error=None, inspect_error_after_remove=(), network_inspect_error_after_remove=False):
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
        docker = FakeDocker(
            containers, fail_rm=fail_rm, rm_noop=rm_noop, network_rm_fail=network_rm_fail,
            network_rm_noop=network_rm_noop, inspect_error=inspect_error,
            inspect_error_after_remove=inspect_error_after_remove,
            network_inspect_error_after_remove=network_inspect_error_after_remove,
        )
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
            'remaining_containers': sorted(docker.containers),
            'network_remaining': docker.network,
        }
        expected = {
            'positive': (0, 'PASS local rehearsal; pending review', True, False),
            'private_cleanup_failure': (1, 'FAIL', False, True),
            'docker_cleanup_failure': (1, 'FAIL', True, True),
            'cleanup_continues_after_error': (1, 'FAIL', True, True),
            'original_failure_preserved': (1, 'FAIL', False, True),
            'inspect_error_before_remove_context': (1, 'FAIL', True, True),
            'inspect_error_before_remove_daemon': (1, 'FAIL', True, True),
            'inspect_error_before_remove_permission': (1, 'FAIL', True, True),
            'inspect_error_before_remove_transport': (1, 'FAIL', True, True),
            'inspect_error_after_remove': (1, 'FAIL', True, True),
            'network_inspect_error_after_remove': (1, 'FAIL', True, True),
            'network_remove_failure': (1, 'FAIL', True, True),
            'container_remove_zero_but_remains': (1, 'FAIL', True, True),
            'network_remove_zero_but_remains': (1, 'FAIL', True, True),
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
        if case.startswith('inspect_error_before_remove_'):
            ok = ok and not docker.rm_calls and docker.network_rm_calls == 0
            ok = ok and len(docker.containers) == len(containers) and docker.network
        if case == 'inspect_error_after_remove':
            ok = ok and docker.rm_calls == list(reversed(list(containers)))
        if case == 'network_inspect_error_after_remove':
            ok = ok and docker.network_rm_calls == 1 and not docker.network
        if case == 'network_remove_failure':
            ok = ok and docker.network_rm_calls == 1 and docker.network
        if case in ('container_remove_zero_but_remains', 'network_remove_zero_but_remains'):
            ok = ok and docker.network_rm_calls == 1
            if case == 'container_remove_zero_but_remains':
                ok = ok and bool(docker.containers)
            else:
                ok = ok and docker.network
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
        run_case(code, 'inspect_error_before_remove_context', ['container-a'], inspect_error=CONTEXT_ERROR),
        run_case(code, 'inspect_error_before_remove_daemon', ['container-a'], inspect_error=DAEMON_ERROR),
        run_case(code, 'inspect_error_before_remove_permission', ['container-a'], inspect_error=PERMISSION_ERROR),
        run_case(code, 'inspect_error_before_remove_transport', ['container-a'], inspect_error=TRANSPORT_ERROR),
        run_case(code, 'inspect_error_after_remove', ['container-a'], inspect_error_after_remove={'container-a'}),
        run_case(code, 'network_inspect_error_after_remove', ['container-a'], network_inspect_error_after_remove=True),
        run_case(code, 'network_remove_failure', ['container-a'], network_rm_fail=True),
        run_case(code, 'container_remove_zero_but_remains', ['container-a'], rm_noop={'container-a'}),
        run_case(code, 'network_remove_zero_but_remains', ['container-a'], network_rm_noop=True),
    ]
    print(json.dumps(cases, indent=2))
    return 0 if all(case['ok'] for case in cases) else 1


if __name__ == '__main__':
    raise SystemExit(main())
