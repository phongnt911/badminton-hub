import json
from pathlib import Path
import re
import socket
import subprocess
import uuid

docker = r'C:\Users\PHONGNT\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe'
run = uuid.uuid4().hex
network = 'bh07-port-probe-net-' + run[:10]
label = 'bh07.port-probe=' + run
names = ['bh07-port-probe-' + kind + '-' + run[:10] for kind in ('dynamic', 'static', 'bridge')]
resources, observations, cleanup_errors = [], [], []

def command(args):
    return subprocess.run([docker, *args], capture_output=True, timeout=15)

def require(args):
    result = command(args)
    if result.returncode:
        raise RuntimeError('probe Docker command failed: ' + args[0])
    return result

def absent(kind, name):
    args = ['network', 'inspect', name] if kind == 'network' else ['inspect', name]
    result = command(args)
    if result.returncode == 0:
        return False
    message = result.stderr.decode('utf-8', 'replace').lower()
    if ('no such object' in message or 'not found' in message or 'no such network' in message):
        return True
    raise RuntimeError('probe ownership inspect failed')

try:
    for name in names:
        if not absent('container', name):
            raise RuntimeError('probe container collision')
    if not absent('network', network):
        raise RuntimeError('probe network collision')
    resources.append(('network', network))
    require(['network', 'create', '--internal', '--label', label, network])
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        fixed_port = sock.getsockname()[1]
    for case, name in zip(('dynamic_internal_first', 'static_internal_first', 'dynamic_bridge_first'), names):
        resources.append(('container', name))
        initial_network = 'bridge' if case == 'dynamic_bridge_first' else network
        binding = f'127.0.0.1:{fixed_port}:9999' if case == 'static_internal_first' else '127.0.0.1::9999'
        require(['run', '-d', '--name', name, '--label', label, '--network', initial_network,
                 '-p', binding, 'postgres:17', 'sleep', '60'])
        require(['network', 'connect', network if initial_network == 'bridge' else 'bridge', name])
        port = command(['port', name, '9999/tcp'])
        mapping = port.stdout.decode('utf-8', 'replace').strip()
        observations.append({'case': case, 'port_exit': port.returncode,
                             'loopback_mapping': mapping if re.fullmatch(r'127\.0\.0\.1:\d+', mapping) else None})
finally:
    for kind, name in reversed(resources):
        try:
            if absent(kind, name):
                continue
            args = ['network', 'inspect'] if kind == 'network' else ['inspect']
            obj = json.loads(require([*args, name]).stdout)[0]
            labels = obj.get('Labels', {}) if kind == 'network' else obj.get('Config', {}).get('Labels', {})
            if labels.get('bh07.port-probe') != run:
                raise RuntimeError('ownership label mismatch')
            require(['network', 'rm', name] if kind == 'network' else ['rm', '-f', '-v', name])
            if not absent(kind, name):
                raise RuntimeError('resource still present')
        except Exception as err:
            cleanup_errors.append(kind + ':' + type(err).__name__)
    report = {'run_id': run, 'kind': 'isolated Docker port metadata probe; no database initialized',
              'observations': observations, 'cleanup_ok': not cleanup_errors,
              'cleanup_errors': cleanup_errors}
    Path(__file__).with_name('docker-publication-probe-result.json').write_text(
        json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))
    if cleanup_errors:
        raise RuntimeError('probe cleanup unverified')
