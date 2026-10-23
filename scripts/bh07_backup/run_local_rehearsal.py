"""Local-only PostgreSQL/Auth recovery rehearsal. Never accepts a remote DB URL.

Creates its own source fixture stack, dumps roles/database privately, restores
into a new cluster and tests real GoTrue/PostgREST plus idempotent cash replay.
Only hashes/counts/results are published; dumps, roles/passwords/tokens are not.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import runpy
import shutil
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parents[2]
SETUP = ROOT / 'docs/reviews/bh07/late_response_evidence/run_local_stack.py'
SOURCE = 'bh07-http-review-db'
NETWORK = 'bh07-http-review-network'
SOURCE_NAMES = ['bh07-http-review-kong', 'bh07-http-review-rest', 'bh07-http-review-auth', SOURCE]
SESSION = '10000000-0000-4000-8000-000000000001'
PLAYER = '30000000-0000-4000-8000-000000000001'
OPEN = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def cmd(args, data=None, accept_error=False):
    p = subprocess.run(args, input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if p.returncode and not accept_error:
        # Never log a password-bearing argument, SQL dump or raw error payload.
        raise RuntimeError(f'{args[0]} exited {p.returncode}')
    return p


def sql(container, query):
    return cmd(['docker', 'exec', '-i', container, 'psql', '-U', 'postgres', '-d', 'postgres', '-At', '-v', 'ON_ERROR_STOP=1'], query.encode()).stdout.decode().strip()


def digest(raw):
    if not isinstance(raw, bytes):
        raw = json.dumps(raw, sort_keys=True, separators=(',', ':')).encode()
    return hashlib.sha256(raw).hexdigest()


def same_snapshot(expected, actual):
    return expected == actual


def public_rows(snapshot):
    return {key: value for key, value in snapshot.items() if key.startswith('public.')}


def fingerprint(container):
    tables = json.loads(sql(container, "SELECT json_agg(json_build_array(schemaname,tablename) ORDER BY schemaname,tablename) FROM pg_tables WHERE schemaname IN ('public','auth')"))
    result = {}
    for schema, table in tables:
        ident = '"' + schema.replace('"', '""') + '"."' + table.replace('"', '""') + '"'
        rows = json.loads(sql(container, f"SELECT COALESCE(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text),'[]'::jsonb) FROM {ident} t"))
        result[f'{schema}.{table}'] = {'rows': len(rows), 'sha256': digest(rows)}
    schema_dump = cmd(['docker', 'exec', container, 'pg_dump', '-U', 'postgres', '--schema-only', 'postgres']).stdout.decode()
    # PostgreSQL17 uses a random psql restriction nonce; it is not schema data.
    schema_dump = re.sub(r'(?m)^\\(?:un)?restrict .*\n?', '', schema_dump)
    result['_schema'] = digest(schema_dump.encode())
    result['_sequences'] = json.loads(sql(container, "SELECT COALESCE(jsonb_agg(to_jsonb(s) ORDER BY schemaname,sequencename),'[]'::jsonb) FROM pg_sequences s WHERE schemaname IN ('public','auth')"))
    result['_roles'] = json.loads(sql(container, "SELECT jsonb_agg(to_jsonb(r) ORDER BY rolname) FROM (SELECT rolname,rolsuper,rolinherit,rolcreaterole,rolcreatedb,rolcanlogin,rolreplication,rolbypassrls,rolconnlimit,rolvaliduntil,rolconfig FROM pg_roles WHERE rolname NOT LIKE 'pg_%') r"))
    return result


def http(url, body, headers=None):
    if urllib.request.urlparse(url).hostname not in ('127.0.0.1', 'localhost', '::1'):
        raise ValueError('Only loopback HTTP is allowed')
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={'Content-Type': 'application/json', **(headers or {})})
    try:
        with OPEN.open(req, timeout=20) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read())


def login(auth_url, actor, headers=None, password='bh07-http-pass-123456'):
    status, body = http(auth_url + '/token?grant_type=password', {'email': actor + '@example.test', 'password': password}, headers)
    assert status == 200 and body.get('access_token'), 'Real password sign-in failed'
    return body['access_token']


def rpc(rest_url, token, name, payload, headers=None):
    return http(rest_url + '/' + name, payload, {**(headers or {}), 'Authorization': 'Bearer ' + token})


def projections(auth, rest, headers=None):
    result = {}
    for actor in ['ownera', 'cohosta', 'outsider']:
        token = login(auth, actor, headers)
        status, body = rpc(rest, token, 'get_session_summary', {'p_session_id': SESSION}, headers)
        if actor == 'outsider':
            assert status == 403 and 'FORBIDDEN' in body.get('message', '')
        else:
            assert status == 200
            assert body['can_view_finance'] == (actor == 'ownera')
            if actor == 'cohosta':
                for key in ['billing_state', 'active_revision_id', 'revision_no', 'source_version', 'expenses_total_vnd', 'amount_due_total_vnd', 'total_paid_vnd', 'outstanding_total_vnd']:
                    assert key in body and body[key] is None
        result[actor] = {'status': status, 'body': body}
    anonymous_status, anonymous_body = http(rest + '/get_session_summary', {'p_session_id': SESSION}, headers)
    assert anonymous_status in (401, 403) and anonymous_body.get('code') == '42501'
    result['anonymous'] = {'status': anonymous_status, 'body': anonymous_body}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path, help='New scratch output directory; never writes a dump here')
    args = parser.parse_args()
    out = args.out.resolve()
    if out.exists():
        raise ValueError('Output must not already exist')
    source_sha = cmd(['git', 'rev-parse', 'HEAD']).stdout.decode().strip()
    dirty = cmd(['git', 'status', '--porcelain']).stdout.decode().strip()
    for name in SOURCE_NAMES:
        if cmd(['docker', 'inspect', name], accept_error=True).returncode == 0:
            raise ValueError('Fixture container already exists; refusing to touch it')
    if cmd(['docker', 'network', 'inspect', NETWORK], accept_error=True).returncode == 0:
        raise ValueError('Fixture network already exists; refusing to touch it')
    out.mkdir(parents=True)
    private = Path(tempfile.mkdtemp(prefix='bh07-backup-'))
    target = 'bh07-restore-' + uuid.uuid4().hex[:8]
    owned = []
    started = time.monotonic()
    summary = {'base_sha': '74305bb343fbaf548cb5eea38a77475cc3a21b39', 'tested_source_sha': source_sha, 'dirty_before_run': dirty, 'mode': 'local fixture only; Codex implementation/self-verification', 'checks': []}

    def check(name, ok):
        summary['checks'].append({'name': name, 'pass': bool(ok)})
        assert ok, name
        print('PASS:', name, flush=True)

    def target_run(name, image, env, ports=None):
        env_path = private / (name + '.env')
        env_path.write_text(''.join(f'{k}={v}\n' for k, v in env.items())); env_path.chmod(0o600)
        cmd(['docker', 'run', '-d', '--name', name, '--network', NETWORK, '--env-file', str(env_path), *(ports or []), image])
        owned.append(name)

    try:
        setup = SETUP.read_text()
        setup = setup.replace("root=Path('/workspace/badminton-hub')", f'root=Path({str(ROOT)!r})')
        setup = setup.replace("out=Path('/workspace/scratch/bh07-late-response')", f'out=Path({str(out)!r})')
        setup = setup.replace("private=Path('/tmp/bh07-http-review-runtime')", f'private=Path({str(private / "source-runtime")!r})')
        script = private / 'setup.py'; script.write_text(setup)
        # All fixed-name resources were absent at preflight and are ours only.
        owned.extend(SOURCE_NAMES)
        ns = runpy.run_path(str(script))
        headers = {'apikey': ns['anon']}
        auth = 'http://127.0.0.1:54321/auth/v1'
        rest = 'http://127.0.0.1:54321/rest/v1/rpc'
        token = login(auth, 'ownera', headers)
        request_id = str(uuid.uuid4())
        payload = {'p_player_id': PLAYER, 'p_amount_vnd': 10000, 'p_reference': 'BH07 restore replay', 'p_request_id': request_id}
        status, payment = rpc(rest, token, 'record_cash_payment', payload, headers)
        check('source cash committed via real Owner RPC', status == 200 and bool(payment.get('payment_id')))
        payment_id = str(uuid.UUID(payment['payment_id']))
        expected_projection = projections(auth, rest, headers)
        check('source Owner/cohost/outsider ACL controls', True)
        cmd(['docker', 'stop', 'bh07-http-review-auth'])
        before = fingerprint(SOURCE)
        check('fixture has financial/audit/idempotency data', all(before['public.' + t]['rows'] > 0 for t in ['payments', 'club_transactions', 'audit_events', 'operation_requests']))
        dump_started = time.monotonic()
        archive = cmd(['docker', 'exec', SOURCE, 'pg_dump', '-U', 'postgres', '--format=custom', '--create', 'postgres']).stdout
        roles = cmd(['docker', 'exec', SOURCE, 'pg_dumpall', '-U', 'postgres', '--globals-only']).stdout
        (private / 'database.dump').write_bytes(archive); (private / 'roles.sql').write_bytes(roles)
        summary['backup'] = {'sha256': digest(archive), 'bytes': len(archive), 'globals_sha256': digest(roles), 'seconds': round(time.monotonic() - dump_started, 3)}
        bad = cmd(['docker', 'exec', '-i', SOURCE, 'pg_restore', '--list'], b'corrupt archive control', accept_error=True)
        check('corrupt archive rejected', bad.returncode != 0)
        restore_started = time.monotonic()
        target_run(target, 'postgres:17', {'POSTGRES_PASSWORD': ns['password']})
        for _ in range(40):
            if cmd(['docker', 'exec', target, 'pg_isready', '-U', 'postgres'], accept_error=True).returncode == 0:
                break
            time.sleep(0.5)
        # postgres exists in every fresh official image; retain its ALTER ROLE
        # settings/password but skip exactly its duplicate CREATE statement.
        globals_sql = roles.decode()
        check('bootstrap role filter is exact', globals_sql.count('CREATE ROLE postgres;') == 1)
        globals_sql = globals_sql.replace('CREATE ROLE postgres;\n', '', 1)
        cmd(['docker', 'exec', '-i', target, 'psql', '-U', 'postgres', '-v', 'ON_ERROR_STOP=1'], globals_sql.encode())
        cmd(['docker', 'exec', '-i', target, 'pg_restore', '-U', 'postgres', '--clean', '--if-exists', '--create', '--exit-on-error', '-d', 'template1'], archive)
        restored = fingerprint(target)
        check('all public/Auth rows schema roles sequences match', same_snapshot(before, restored))
        (out / 'source_fingerprints.json').write_text(json.dumps(before, indent=2) + '\n')
        (out / 'restored_fingerprints.json').write_text(json.dumps(restored, indent=2) + '\n')
        pw, secret = ns['password'], ns['secret']
        target_run(target + '-auth', 'ghcr.io/supabase/gotrue:v2.197.0', {'GOTRUE_API_HOST': '0.0.0.0', 'GOTRUE_API_PORT': 9999, 'API_EXTERNAL_URL': 'http://127.0.0.1', 'GOTRUE_SITE_URL': 'http://127.0.0.1', 'GOTRUE_DB_DRIVER': 'postgres', 'GOTRUE_DB_DATABASE_URL': f'postgres://supabase_auth_admin:{pw}@{target}:5432/postgres?search_path=auth', 'GOTRUE_JWT_SECRET': secret, 'GOTRUE_JWT_AUD': 'authenticated', 'GOTRUE_JWT_EXP': 3600, 'GOTRUE_JWT_DEFAULT_GROUP_NAME': 'authenticated', 'GOTRUE_JWT_ADMIN_ROLES': 'service_role', 'GOTRUE_EXTERNAL_EMAIL_ENABLED': 'true', 'GOTRUE_DISABLE_SIGNUP': 'false'}, ['-p', '127.0.0.1::9999'])
        target_run(target + '-rest', 'ghcr.io/supabase/postgrest:v16.4', {'PGRST_DB_URI': f'postgres://authenticator:{pw}@{target}:5432/postgres', 'PGRST_DB_SCHEMAS': 'public', 'PGRST_DB_ANON_ROLE': 'anon', 'PGRST_JWT_SECRET': secret, 'PGRST_SERVER_PORT': 3000}, ['-p', '127.0.0.1::3000'])
        for suffix in ['-auth', '-rest']:
            cmd(['docker', 'network', 'connect', 'bridge', target + suffix])
        def endpoint(name, port):
            address = cmd(['docker', 'port', name, str(port) + '/tcp']).stdout.decode().strip()
            assert address.startswith('127.0.0.1:')
            return 'http://' + address
        new_auth = endpoint(target + '-auth', 9999); new_rest = endpoint(target + '-rest', 3000) + '/rpc'
        for _ in range(40):
            try:
                recovered_projection = projections(new_auth, new_rest)
                break
            except (urllib.error.URLError, ConnectionError, AssertionError):
                time.sleep(0.5)
        else:
            raise RuntimeError('Restored Auth/PostgREST did not pass recovery smoke')
        check('real Auth/JWT/ACL projections preserved after restore', expected_projection == recovered_projection)
        wrong_status, _ = http(new_auth + '/token?grant_type=password', {'email': 'ownera@example.test', 'password': 'wrong-fixture-password'})
        check('wrong password still rejected after restore', wrong_status == 400)
        owner = login(new_auth, 'ownera')
        status, replay = rpc(new_rest, owner, 'record_cash_payment', payload)
        check('same request after restore returns same payment ID', status == 200 and replay.get('payment_id') == payment_id)
        count_sql = f"SELECT json_build_array((SELECT count(*) FROM payments WHERE id='{payment_id}'),(SELECT count(*) FROM club_transactions WHERE source_payment_id='{payment_id}'),(SELECT count(*) FROM operation_requests WHERE request_id='{request_id}'))"
        check('restore retry is exactly one payment ledger operation', json.loads(sql(target, count_sql)) == [1, 1, 1])
        status, after_replay = rpc(new_rest, owner, 'get_session_summary', {'p_session_id': SESSION})
        check('server aggregate/outstanding unchanged by replay', status == 200 and after_replay == expected_projection['ownera']['body'])
        summary['recovery_seconds'] = round(time.monotonic() - restore_started, 3)
        public_before_tamper = public_rows(fingerprint(target))
        old_audit = json.loads(sql(target, 'SELECT count(*) FROM audit_events'))
        sql(target, f"DELETE FROM audit_events WHERE session_id='{SESSION}'")
        new_audit = json.loads(sql(target, 'SELECT count(*) FROM audit_events'))
        check('missing audit-row negative control detected', new_audit < old_audit and not same_snapshot(public_before_tamper, public_rows(fingerprint(target))))
        sql(target, 'REVOKE EXECUTE ON FUNCTION public.get_session_summary(uuid) FROM authenticated')
        denied_status, _ = rpc(new_rest, owner, 'get_session_summary', {'p_session_id': SESSION})
        acl_oracle_failed = False
        try:
            projections(new_auth, new_rest)
        except AssertionError:
            acl_oracle_failed = True
        check('lost RPC grant negative control detected via HTTP', denied_status == 403 and acl_oracle_failed)
        summary['projection_hashes'] = {actor: digest(value) for actor, value in expected_projection.items()}
        summary['status'] = 'PASS local rehearsal; pending review'
    except Exception as error:
        summary['status'] = 'FAIL'
        summary['failure_type'] = type(error).__name__
        # Do not emit a potential secret-bearing subprocess/HTTP exception.
        print('FAIL stage:', type(error).__name__, flush=True)
    finally:
        for name in reversed(owned):
            cmd(['docker', 'rm', '-f', '-v', name], accept_error=True)
        cmd(['docker', 'network', 'rm', NETWORK], accept_error=True)
        shutil.rmtree(private, ignore_errors=True)
        summary['private_dumps_keys_removed'] = not private.exists()
        summary['elapsed_seconds'] = round(time.monotonic() - started, 3)
        summary['passed'] = sum(item['pass'] for item in summary['checks'])
        (out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    return 0 if summary['status'].startswith('PASS') else 1


if __name__ == '__main__':
    raise SystemExit(main())
