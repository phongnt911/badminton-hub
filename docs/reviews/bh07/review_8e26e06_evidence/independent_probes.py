import ast, json, tempfile, shutil, uuid
import urllib.request
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(r'C:\Users\POTA\Documents\GitHub\Open-Multi-agent-Pipeline\.review-bh07\worktree-8e26e06')
SRC = ROOT / 'scripts/bh07_reset/run_full_reset.py'
text = SRC.read_text(encoding='utf-8')
tree = ast.parse(text)
results = {}

# 1. PROJECT_ID uniqueness / shape
assign = next(n for n in tree.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'PROJECT_ID' for t in n.targets))
expr = compile(ast.Expression(assign.value), str(SRC), 'eval')
ids = [eval(expr, {'uuid': uuid}) for _ in range(32)]
results['project_id'] = {
    'count': len(ids),
    'unique': len(set(ids)) == len(ids),
    'prefix_ok': all(x.startswith('bh07-reset-verify-') for x in ids),
    'lengths': sorted({len(x) for x in ids}),
}

# 2. prepare_project_dir writes unique project id and dedicated ports; 18 migrations copied
def load_func(name):
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    env = {'Path': Path, 'shutil': shutil, 'ROOT': ROOT, 'PROJECT_ID': ids[0],
           'PORT_API': 56421, 'PORT_DB': 56422, 'PORT_SHADOW': 56420, 'PORT_STUDIO': 56423,
           'PORT_SMTP': 56424, 'PORT_ANALYTICS': 56427, 'PORT_S3': 56428, 'PORT_POOLER': 56429}
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(SRC), 'exec'), env)
    return env[name]

with tempfile.TemporaryDirectory() as td:
    work = Path(td) / 'proj'
    load_func('prepare_project_dir')(work)
    cfg = (work / 'supabase/config.toml').read_text(encoding='utf-8')
    mig = sorted((work / 'supabase/migrations').glob('*.sql'))
    results['prepare_project_dir'] = {
        'project_id_replaced': f'project_id = "{ids[0]}"' in cfg and 'project_id = "badminton-hub"' not in cfg,
        'ports': {str(p): (f'port = {p}' in cfg) for p in (56420,56421,56422,56423,56424,56427,56428,56429)},
        'migrations': len(mig),
        'first': mig[0].name if mig else None,
        'last': mig[-1].name if mig else None,
    }

# 3. Inventory after start: returncode before stdout, empty inventory stops.
class ResetBoundary(Exception):
    pass

main_node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'main')
pref_node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'preflight_ownership_check')
def run_main(exit_code, inventory):
    calls = []
    def command(args, **kwargs):
        calls.append(args)
        if args[:3] == ['npx', 'supabase', 'db']:
            raise ResetBoundary('reset boundary')
        if args[:3] == ['npx', 'supabase', 'status']:
            return SimpleNamespace(returncode=0, stdout=json.dumps({
                'API_URL': 'http://127.0.0.1:56421', 'ANON_KEY': 'synthetic',
                'SERVICE_ROLE_KEY': 'synthetic'}), stderr='')
        if args[:2] == ['docker', 'ps']:
            if '{{.ID}}' in args:
                return SimpleNamespace(returncode=exit_code, stdout=inventory, stderr='synthetic failure')
            return SimpleNamespace(returncode=0, stdout='', stderr='')
        if args[:3] == ['npx', 'supabase', 'start']:
            return SimpleNamespace(returncode=0, stdout='started', stderr='')
        if args[:3] == ['npx', 'supabase', 'stop']:
            return SimpleNamespace(returncode=0, stdout='stopped', stderr='')
        return SimpleNamespace(returncode=0, stdout='', stderr='')
    with tempfile.TemporaryDirectory() as td:
        env = {'print': lambda *a, **kw: None, 'STAMP': 'synthetic', 'BASE_SHA': 'synthetic',
               'PROJECT_ID': ids[0], 'PORT_API': 56421, 'PORT_DB': 56422, 'PORT_SHADOW': 56420,
               'PORT_STUDIO': 56423, 'PORT_SMTP': 56424, 'PORT_ANALYTICS': 56427, 'PORT_S3': 56428,
               'PORT_POOLER': 56429, 'run_cmd': command, 'Path': Path,
               'tempfile': SimpleNamespace(gettempdir=lambda: td), 'prepare_project_dir': lambda p: p.mkdir(parents=True),
               'write_evidence': lambda *a: None, 'log_cmd': lambda *a: None, 'exits': {}, 'audit_results': {},
               'json': json, 'urllib': __import__('urllib'), 'shutil': shutil, 'uuid': uuid,
               'preflight_ownership_check': lambda: {'status': 'PASS'}}
        exec(compile(ast.Module(body=[main_node], type_ignores=[]), str(SRC), 'exec'), env)
        error = None
        try:
            env['main']()
        except Exception as exc:
            error = type(exc).__name__
        attempted = any(a[:3] == ['npx', 'supabase', 'db'] for a in calls)
        return {'exit': exit_code, 'stdout': inventory, 'error': error, 'reset_attempted': attempted}
results['inventory_after_start'] = [
    run_main(1, ''),
    run_main(1, 'owned-id'),
    run_main(0, ''),
    run_main(0, 'owned-id'),
]

# 4. Gateway/PostgREST strict tuple cases
helper_node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'assert_negative_auth_rejection')
henv = {'AssertionError': AssertionError, 'ValueError': ValueError}
exec(compile(ast.Module(body=[helper_node], type_ignores=[]), str(SRC), 'exec'), henv)
verify = henv['assert_negative_auth_rejection']
cases = [
    ('gateway_valid_401_no_code', 'no_apikey', 401, {'message': 'No API key found in request'}, True),
    ('gateway_casefold', 'no_apikey', 401, {'message': 'NO API KEY FOUND IN REQUEST'}, True),
    ('gateway_403_no_code', 'no_apikey', 403, {'message': 'No API key found in request'}, False),
    ('gateway_401_code_42P01', 'no_apikey', 401, {'code': '42P01', 'message': 'No API key found in request'}, False),
    ('gateway_401_empty_code', 'no_apikey', 401, {'code': '', 'message': 'No API key found in request'}, False),
    ('gateway_401_null_code', 'no_apikey', 401, {'code': None, 'message': 'No API key found in request'}, False),
    ('gateway_401_prefix', 'no_apikey', 401, {'message': 'prefix No API key found in request'}, False),
    ('gateway_401_suffix', 'no_apikey', 401, {'message': 'No API key found in request suffix'}, False),
    ('postgrest_42501_401', 'no_apikey', 401, {'code': '42501', 'message': 'permission denied for function complete_session'}, True),
    ('postgrest_42501_403', 'anon_complete', 403, {'code': '42501', 'message': 'permission denied for function complete_session'}, True),
    ('anon_xx000_with_hint', 'anon_complete', 403, {'code': 'XX000', 'message': 'unrelated', 'hint': 'JWT api key FORBIDDEN permission denied'}, False),
    ('anon_invalid', 'anon_complete', 400, {'code': 'INVALID_INPUT'}, False),
    ('anon_route404', 'anon_complete', 404, {'message': 'route missing'}, False),
    ('outsider_42501_forbidden', 'outsider_summary', 403, {'code': '42501', 'message': 'FORBIDDEN'}, True),
    ('outsider_xx000', 'outsider_summary', 403, {'code': 'XX000', 'message': 'FORBIDDEN'}, False),
    ('outsider_wrong_code', 'outsider_summary', 403, {'code': 'P0001', 'message': 'FORBIDDEN'}, False),
    ('anon_42501_unauthenticated', 'anon_complete', 401, {'code': '42501', 'message': 'unauthenticated'}, True),
]
rows = []
for name, kind, status, body, expect in cases:
    try:
        verify(name, status, body, kind)
        accepted = True
    except (AssertionError, ValueError):
        accepted = False
    rows.append({'case': name, 'expected_accept': expect, 'actual_accept': accepted, 'ok': accepted == expect})
results['gateway_tuple'] = {'cases': len(rows), 'ok': all(r['ok'] for r in rows), 'rows': rows}

print(json.dumps(results, indent=2, ensure_ascii=False))
raise SystemExit(0 if all([results['project_id']['unique'], results['project_id']['prefix_ok'], results['prepare_project_dir']['project_id_replaced'], results['prepare_project_dir']['migrations'] == 18, results['gateway_tuple']['ok']] + [not r['reset_attempted'] for r in results['inventory_after_start'][:3]] + [results['inventory_after_start'][3]['reset_attempted']]) else 1)
