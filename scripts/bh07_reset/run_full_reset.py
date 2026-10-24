"""V5b — Full Supabase CLI reset local verification runner for BH-07.

This script executes a 100% isolated, local Supabase CLI reset verification:
1. Spawns an independent Supabase CLI project using `--workdir` on dedicated ports (56421-56429),
   completely segregated from the default repository stack and any shared database.
2. Executes two full reset cycles (`supabase db reset --local --no-seed --yes`),
   loading all 18 repository migrations from zero.
3. In each cycle:
   - Creates deterministic Auth users via GoTrue Admin API.
   - Seeds the standardized BH-07 fixture into the freshly recreated database.
   - Verifies schema completeness, tables, RPCs, and RLS policies.
   - Verifies real HTTP Auth, JWT issuance, and ACL/RPC calls through loopback Kong/PostgREST.
   - Executes 23 core DB assertions directly against the freshly reset database.
   - Computes deterministic schema and table data fingerprints.
4. Compares Cycle 1 and Cycle 2 snapshots (Repeat Reset Oracle) to prove full repeatability.
5. Executes negative controls (unauthenticated calls, outsider access, unfinalized complete, overcollect, loopback guard).
6. Teardown: Stops and purges all isolated project containers and volumes.
7. Produces a verifiable evidence bundle with secret redaction and SHA256 manifest.
"""

import datetime
import hashlib
import json
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import uuid

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE_DIR = ROOT / 'docs/reviews/bh07/full_reset_evidence'
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

# A failed inventory may still stop this run's project, never another run's project.
PROJECT_ID = f'bh07-reset-verify-{uuid.uuid4().hex[:16]}'
CONTAINER_DB = f'supabase_db_{PROJECT_ID}'
CONTAINER_KONG = f'supabase_kong_{PROJECT_ID}'

# Dedicated non-conflicting loopback ports
PORT_API = 56421
PORT_DB = 56422
PORT_SHADOW = 56420
PORT_STUDIO = 56423
PORT_SMTP = 56424
PORT_ANALYTICS = 56427
PORT_S3 = 56428
PORT_POOLER = 56429

BASE_SHA = '6e5dba6c1b67c06bf98283b6bacac47ae2be3dc6'
STAMP = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')

OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))

exits = {}
commands_run = []
audit_results = {
    'cycle1': {'schema': None, 'http': None, 'db_assertions': None, 'snapshot': None},
    'cycle2': {'schema': None, 'http': None, 'db_assertions': None, 'snapshot': None},
    'oracle_match': False,
    'negative_controls': [],
    'cleanup': None,
}


def log_cmd(description, cmd_str):
    commands_run.append(f"# {description}\n{cmd_str}")


def protect_text(text: str) -> str:
    """Redacts JWTs, secret keys, and passwords from logs."""
    safe = text
    safe = re.sub(r'eyJ[A-Za-z0-9_\-\.]{20,}', '<redacted-jwt>', safe)
    safe = re.sub(r'sb_(publishable|secret)_[A-Za-z0-9_\-]+', '<redacted-key>', safe)
    safe = re.sub(r'(?i)("JWT_SECRET"\s*:\s*")[^"]+', r'\1<redacted>', safe)
    safe = re.sub(r'(?i)("S3_PROTOCOL_ACCESS_KEY_SECRET"\s*:\s*")[^"]+', r'\1<redacted>', safe)
    safe = re.sub(r'(?i)("S3_PROTOCOL_ACCESS_KEY_ID"\s*:\s*")[^"]+', r'\1<redacted>', safe)
    safe = re.sub(r'(?i)("DB_URL"\s*:\s*")[^"]+', r'\1<redacted>', safe)
    safe = re.sub(r'bh07-http-pass-[A-Za-z0-9]+', '<redacted-password>', safe)
    return safe


def write_evidence(filename: str, content: str):
    path = EVIDENCE_DIR / filename
    safe_content = protect_text(content)
    path.write_text(safe_content, encoding='utf-8', newline='\n')


def run_cmd(args, cwd=None, input_text=None, check=True):
    real_cmd = list(args)
    exe = shutil.which(real_cmd[0]) or real_cmd[0]
    real_cmd[0] = exe
    is_batch = sys.platform == 'win32' and exe.lower().endswith(('.cmd', '.bat'))
    p = subprocess.run(
        real_cmd,
        cwd=cwd or str(ROOT),
        input=input_text,
        text=True,
        encoding='utf-8',
        capture_output=True,
        shell=is_batch
    )
    if check and p.returncode != 0:
        raise RuntimeError(f"Command failed ({p.returncode}): {' '.join(args)}\nStderr: {p.stderr}\nStdout: {p.stdout}")
    return p


def sql(query: str, db='postgres') -> str:
    """Executes a SQL query inside the dedicated Supabase test container."""
    p = run_cmd(
        ['docker', 'exec', '-i', CONTAINER_DB, 'psql', '-U', 'postgres', '-d', db, '-At', '-v', 'ON_ERROR_STOP=1'],
        input_text=query
    )
    return p.stdout.strip()


def sql_run(query: str, db='postgres'):
    return subprocess.run(
        ['docker', 'exec', '-i', CONTAINER_DB, 'psql', '-U', 'postgres', '-d', db, '-At', '-v', 'ON_ERROR_STOP=1'],
        input=query, text=True, encoding='utf-8', capture_output=True
    )


def sql_as(actor_email: str, query: str, db='postgres', role='authenticated'):
    """Executes a SQL query within the session context of a specific Auth user."""
    actor_uid = sql(f"SELECT id::text FROM auth.users WHERE email='{actor_email}';", db=db)
    sql_script = f"""BEGIN;
SELECT set_config('request.jwt.claim.sub', '{actor_uid}', true);
SET LOCAL ROLE {role};
{query}
COMMIT;
"""
    return subprocess.run(
        ['docker', 'exec', '-i', CONTAINER_DB, 'psql', '-U', 'postgres', '-d', db, '-At', '-v', 'ON_ERROR_STOP=1'],
        input=sql_script, text=True, encoding='utf-8', capture_output=True
    )


def http_request(url: str, body=None, headers=None, method='POST'):
    parsed = urllib.request.urlparse(url)
    if parsed.hostname not in ('127.0.0.1', 'localhost', '::1'):
        raise ValueError(f"Loopback security guard: Refusing non-loopback URL {url}")
    req_headers = {'Content-Type': 'application/json'}
    if headers:
        req_headers.update(headers)
    data = json.dumps(body).encode('utf-8') if body is not None else None
    req = urllib.request.Request(url, data=data, headers=req_headers, method=method)
    try:
        with OPENER.open(req, timeout=20) as resp:
            content = resp.read().decode('utf-8')
            return resp.status, json.loads(content) if content else {}
    except urllib.error.HTTPError as err:
        err_content = err.read().decode('utf-8')
        try:
            return err.code, json.loads(err_content)
        except Exception:
            return err.code, {'error': err_content}


def digest(data) -> str:
    if isinstance(data, str):
        data = data.encode('utf-8')
    elif not isinstance(data, bytes):
        data = json.dumps(data, sort_keys=True, separators=(',', ':')).encode('utf-8')
    return hashlib.sha256(data).hexdigest()


def compute_db_fingerprint() -> dict:
    """Computes deterministic schema dump hash and row counts / data hashes."""
    # 1. Schema dump
    p = run_cmd(['docker', 'exec', CONTAINER_DB, 'pg_dump', '-U', 'postgres', '--schema-only', 'postgres'])
    schema_clean = re.sub(r'(?m)^\\(?:un)?restrict .*\n?', '', p.stdout)
    schema_clean = re.sub(r'(?m)^--.*$', '', schema_clean)
    schema_hash = digest(schema_clean.encode('utf-8'))

    # 2. Table row hashes & counts
    tables_json = sql("SELECT json_agg(json_build_array(schemaname, tablename) ORDER BY schemaname, tablename) FROM pg_tables WHERE schemaname IN ('public', 'auth');")
    tables = json.loads(tables_json) if tables_json else []
    table_stats = {}
    for schemaname, tablename in tables:
        ident = f'"{schemaname}"."{tablename}"'
        rows_json = sql(f"SELECT COALESCE(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text), '[]'::jsonb) FROM {ident} t;")
        rows = json.loads(rows_json) if rows_json else []
        table_stats[f"{schemaname}.{tablename}"] = {
            'count': len(rows),
            'sha256': digest(rows)
        }

    return {
        'schema_sha256': schema_hash,
        'table_stats': table_stats,
        'total_tables': len(tables),
    }


def preflight_ownership_check() -> dict:
    """Preflight check: verifies that no containers or ports matching the isolated test stack exist.
    
    Aborts immediately if unowned or conflicting resources are found to protect against
    interfering with pre-existing projects or shared databases.
    Fail-closed on any Docker inspection failure (nonzero exit code).
    """
    print("Running Preflight Ownership & Resource Isolation Check...")
    # 1. Container check (all containers, running or stopped)
    p_check = run_cmd(['docker', 'ps', '-a', '--filter', f'name={PROJECT_ID}', '--format', '{{.ID}} {{.Names}}'], check=False)
    if p_check.returncode != 0:
        raise RuntimeError(
            f"Preflight ABORT: Docker inspection failed with exit code {p_check.returncode}:\n{p_check.stderr.strip()}"
        )
    existing_containers = p_check.stdout.strip().splitlines() if p_check.stdout.strip() else []
    if existing_containers:
        raise RuntimeError(
            f"Preflight ABORT: Found {len(existing_containers)} pre-existing container(s) matching '{PROJECT_ID}':\n"
            + "\n".join(existing_containers)
            + "\nRefusing to start to prevent unowned resource interference. Clean them manually before proceeding."
        )

    # 2. Port check (ensure dedicated ports are free on loopback)
    target_ports = [
        ('API', PORT_API),
        ('DB', PORT_DB),
        ('Shadow', PORT_SHADOW),
        ('Studio', PORT_STUDIO),
        ('SMTP', PORT_SMTP),
        ('Analytics', PORT_ANALYTICS),
        ('S3', PORT_S3),
        ('Pooler', PORT_POOLER),
    ]
    occupied_ports = []
    for name, port in target_ports:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            result = s.connect_ex(('127.0.0.1', port))
            if result == 0:
                occupied_ports.append(f"{name}:{port}")

    if occupied_ports:
        raise RuntimeError(
            f"Preflight ABORT: Port(s) already in use on 127.0.0.1: {', '.join(occupied_ports)}.\n"
            "Refusing to start to avoid port collision with running services."
        )

    print("Preflight check PASS: 0 conflicting containers, all 8 dedicated ports free.")
    return {
        'status': 'PASS',
        'existing_containers_count': 0,
        'checked_ports': [p[1] for p in target_ports]
    }


def assert_negative_auth_rejection(control_name: str, status: int, body: dict, expected_type: str):
    """Strictly verifies that an HTTP error response is an authentic authentication/authorization rejection.
    
    Verifies the exact (status, code, message) tuple on concrete top-level fields.
    Rejects any unmapped or invalid error domain: XX000 (internal database error),
    INVALID_INPUT, NOT_FOUND, PGRST202, route 404, or transport errors.
    Never searches raw JSON or hint/detail fields for loose keywords.
    """
    if not isinstance(body, dict):
        raise AssertionError(f"[{control_name}] Expected JSON object response, got {type(body)}: {body}")
    
    code = str(body.get('code', ''))
    message = str(body.get('message', ''))
    
    # 1. Universal rejections of invalid/unrelated error domains
    disallowed_codes = ('XX000', 'INVALID_INPUT', 'NOT_FOUND', 'PGRST202')
    if code in disallowed_codes:
        raise AssertionError(f"[{control_name}] Received invalid error code '{code}': {body}")
    if status == 404:
        raise AssertionError(f"[{control_name}] Received HTTP 404 route missing, expected auth rejection: {body}")

    # 2. Per-control strict domain assertions
    if expected_type == 'anon_complete':
        # Unauthenticated anon calling complete_session:
        # Expected: PostgREST returns HTTP 401 or 403 with PostgreSQL permission denied SQLSTATE 42501
        if status not in (401, 403):
            raise AssertionError(f"[{control_name}] Expected HTTP 401 or 403, got {status}: {body}")
        if code != '42501':
            raise AssertionError(f"[{control_name}] Expected SQLSTATE '42501', got '{code}': {body}")
        if 'permission denied' not in message.lower() and 'unauthenticated' not in message.lower():
            raise AssertionError(f"[{control_name}] Expected permission denied message, got '{message}': {body}")

    elif expected_type == 'no_apikey':
        # Missing API key header entirely:
        # Gateway Kong returns 401 with 'No API key found in request'
        # OR PostgREST returns 401/403 with SQLSTATE 42501 permission denied
        if status not in (401, 403):
            raise AssertionError(f"[{control_name}] Expected HTTP 401 or 403, got {status}: {body}")
        if code == '42501':
            if 'permission denied' not in message.lower() and 'unauthenticated' not in message.lower():
                raise AssertionError(f"[{control_name}] Expected permission denied message for 42501, got '{message}': {body}")
        else:
            # Kong's documented variant has no SQLSTATE/code field and returns 401.
            if status != 401 or 'code' in body or message.casefold() != 'no api key found in request':
                raise AssertionError(f"[{control_name}] Unmapped gateway status/code/message: {status} {body}")

    elif expected_type == 'outsider_summary':
        # Authenticated outsider user calling private session summary:
        # Expected: HTTP 403 (or 400 wrapping RPC error) with code 42501 and domain message containing 'FORBIDDEN'
        if status not in (400, 403):
            raise AssertionError(f"[{control_name}] Expected HTTP 403 or 400, got {status}: {body}")
        if code != '42501':
            raise AssertionError(f"[{control_name}] Expected SQLSTATE '42501', got '{code}': {body}")
        if 'FORBIDDEN' not in message:
            raise AssertionError(f"[{control_name}] Expected 'FORBIDDEN' domain message, got '{message}': {body}")

    else:
        raise ValueError(f"Unknown expected_type: {expected_type}")


def prepare_project_dir(workdir: Path):
    """Generates the isolated supabase project with dedicated ports and migrations."""
    if workdir.exists():
        shutil.rmtree(workdir, ignore_errors=True)
    workdir.mkdir(parents=True, exist_ok=True)
    (workdir / "supabase").mkdir(parents=True, exist_ok=True)

    config_src = (ROOT / "supabase/config.toml").read_text(encoding="utf-8")
    cfg = config_src.replace('project_id = "badminton-hub"', f'project_id = "{PROJECT_ID}"')
    cfg = cfg.replace('port = 54321', f'port = {PORT_API}')
    cfg = cfg.replace('port = 54322', f'port = {PORT_DB}')
    cfg = cfg.replace('shadow_port = 54320', f'shadow_port = {PORT_SHADOW}')
    cfg = cfg.replace('port = 54323', f'port = {PORT_STUDIO}')
    cfg = cfg.replace('port = 54324', f'port = {PORT_SMTP}')
    cfg = cfg.replace('port = 54329', f'port = {PORT_POOLER}')
    cfg = cfg.replace('port = 54327', f'port = {PORT_ANALYTICS}')
    cfg = cfg.replace('port = 54328', f'port = {PORT_S3}')
    (workdir / "supabase/config.toml").write_text(cfg, encoding="utf-8")

    # Copy migrations
    shutil.copytree(ROOT / "supabase/migrations", workdir / "supabase/migrations")


def seed_auth_and_data(api_url: str, service_role_key: str):
    """Creates Auth users via GoTrue Admin API and applies seed.sql."""
    users = [
        {'email': 'ownera@example.test', 'name': 'Owner A'},
        {'email': 'financea@example.test', 'name': 'Finance A'},
        {'email': 'cohosta@example.test', 'name': 'Cohost A'},
        {'email': 'membera@example.test', 'name': 'Member A'},
        {'email': 'guesta@example.test', 'name': 'Guest A'},
        {'email': 'ownerb@example.test', 'name': 'Owner B'},
        {'email': 'outsider@example.test', 'name': 'Outsider'},
    ]
    headers = {
        'apikey': service_role_key,
        'Authorization': f'Bearer {service_role_key}',
    }
    user_ids = {}
    auth_lines = []
    for u in users:
        body = {
            'email': u['email'],
            'password': 'bh07-http-pass-123456',
            'email_confirm': True,
            'user_metadata': {'display_name': u['name']}
        }
        status, res = http_request(f"{api_url}/auth/v1/admin/users", body=body, headers=headers)
        if status not in (200, 201):
            raise RuntimeError(f"GoTrue Admin user creation failed for {u['email']}: {status} {res}")
        user_ids[u['email']] = res['id']
        auth_lines.append(f"created {u['email']} id={res['id']}")

    seed_path = ROOT / 'scripts/bh07_reset/seed.sql'
    seed_sql = seed_path.read_text(encoding='utf-8')
    p_seed = run_cmd(
        ['docker', 'exec', '-i', CONTAINER_DB, 'psql', '-U', 'postgres', '-d', 'postgres', '-v', 'ON_ERROR_STOP=1'],
        input_text=seed_sql
    )
    return auth_lines, p_seed.stdout


def verify_schema() -> dict:
    """Verifies presence of all core tables, functions, and RLS policies."""
    expected_tables = [
        'profiles', 'profile_private', 'app_roles', 'host_bank_accounts', 'club_bank_accounts',
        'clubs', 'club_members', 'member_contacts', 'venues', 'sessions', 'session_staff',
        'session_players', 'session_player_contacts', 'session_expenses', 'charge_revisions',
        'session_charges', 'payments', 'club_transactions', 'audit_events', 'waitlist_invitations',
        'operation_requests'
    ]
    missing_tables = []
    for tbl in expected_tables:
        found = sql(f"SELECT to_regclass('public.{tbl}');")
        if not found or found == '' or found == 'None':
            missing_tables.append(tbl)

    expected_rpcs = [
        'create_session', 'start_session', 'finalize_session_charges',
        'complete_session', 'get_session_summary', 'list_my_session_history',
        'get_session_finance', 'record_cash_payment', 'submit_payment',
        'confirm_payment', 'reverse_payment', 'reject_payment'
    ]
    missing_rpcs = []
    for rpc in expected_rpcs:
        cnt = int(sql(f"SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='public' AND p.proname='{rpc}';"))
        if cnt == 0:
            missing_rpcs.append(rpc)

    rls_check = sql("""
        SELECT count(*) FROM pg_tables
        WHERE schemaname='public' AND tablename IN ('sessions', 'payments', 'club_transactions', 'audit_events')
        AND rowsecurity = true;
    """)

    return {
        'expected_tables_count': len(expected_tables),
        'missing_tables': missing_tables,
        'expected_rpcs_count': len(expected_rpcs),
        'missing_rpcs': missing_rpcs,
        'rls_enforced_tables_count': int(rls_check),
        'schema_valid': (len(missing_tables) == 0 and len(missing_rpcs) == 0 and int(rls_check) >= 4)
    }


def verify_http_and_auth(api_url: str, anon_key: str) -> dict:
    """Tests password login, token acquisition, and RPC calls over HTTP."""
    results = {}
    tokens = {}
    actors = ['ownera', 'financea', 'cohosta', 'membera', 'guesta', 'ownerb', 'outsider']

    # 1. Login
    for actor in actors:
        status, body = http_request(
            f"{api_url}/auth/v1/token?grant_type=password",
            body={'email': f"{actor}@example.test", 'password': 'bh07-http-pass-123456'},
            headers={'apikey': anon_key}
        )
        assert status == 200 and 'access_token' in body, f"Login failed for {actor}: {status} {body}"
        tokens[actor] = body['access_token']
    results['login_count'] = len(tokens)

    # 2. Complete session via HTTP (session_debt from fixture: 10000000-0000-4000-8000-000000000001)
    session_debt = '10000000-0000-4000-8000-000000000001'
    ver = int(sql(f"SELECT version FROM public.sessions WHERE id='{session_debt}';"))
    req_id = str(uuid.uuid4())
    status, body = http_request(
        f"{api_url}/rest/v1/rpc/complete_session",
        body={'p_session_id': session_debt, 'p_expected_version': ver, 'p_request_id': req_id},
        headers={'apikey': anon_key, 'Authorization': f"Bearer {tokens['ownera']}"}
    )
    assert status == 200, f"HTTP complete_session failed: {status} {body}"
    results['http_complete_status'] = status

    # Replay same request_id -> idempotent
    status_rep, body_rep = http_request(
        f"{api_url}/rest/v1/rpc/complete_session",
        body={'p_session_id': session_debt, 'p_expected_version': ver, 'p_request_id': req_id},
        headers={'apikey': anon_key, 'Authorization': f"Bearer {tokens['ownera']}"}
    )
    assert status_rep == 200 and body_rep == body, "HTTP complete idempotent replay mismatch"
    results['http_complete_idempotent'] = True

    # 3. get_session_summary via HTTP:
    # - Owner A: sees finances (200)
    status_own, body_own = http_request(
        f"{api_url}/rest/v1/rpc/get_session_summary",
        body={'p_session_id': session_debt},
        headers={'apikey': anon_key, 'Authorization': f"Bearer {tokens['ownera']}"}
    )
    assert status_own == 200 and body_own.get('can_view_finance') is True and body_own.get('amount_due_total_vnd') is not None
    results['owner_summary_status'] = status_own

    # - Cohost A: management-only, no finance figures (200, amount_due is None)
    status_coh, body_coh = http_request(
        f"{api_url}/rest/v1/rpc/get_session_summary",
        body={'p_session_id': session_debt},
        headers={'apikey': anon_key, 'Authorization': f"Bearer {tokens['cohosta']}"}
    )
    assert status_coh == 200 and body_coh.get('can_view_finance') is False and body_coh.get('amount_due_total_vnd') is None
    results['cohost_summary_count_only'] = True

    # - Member A: FORBIDDEN (403)
    status_mem, body_mem = http_request(
        f"{api_url}/rest/v1/rpc/get_session_summary",
        body={'p_session_id': session_debt},
        headers={'apikey': anon_key, 'Authorization': f"Bearer {tokens['membera']}"}
    )
    assert status_mem in (400, 403) and 'FORBIDDEN' in json.dumps(body_mem)
    results['member_summary_forbidden'] = True

    # - Finance A: sees finances (200)
    status_fin, body_fin = http_request(
        f"{api_url}/rest/v1/rpc/get_session_summary",
        body={'p_session_id': session_debt},
        headers={'apikey': anon_key, 'Authorization': f"Bearer {tokens['financea']}"}
    )
    assert status_fin == 200 and body_fin.get('can_view_finance') is True
    results['finance_summary_status'] = status_fin

    # 4. list_my_session_history via HTTP
    status_hist_own, body_hist_own = http_request(
        f"{api_url}/rest/v1/rpc/list_my_session_history",
        body={'p_limit': 10, 'p_offset': 0},
        headers={'apikey': anon_key, 'Authorization': f"Bearer {tokens['ownera']}"}
    )
    assert status_hist_own == 200 and any(s['id'] == session_debt for s in body_hist_own)
    results['owner_history_found'] = True

    status_hist_mem, body_hist_mem = http_request(
        f"{api_url}/rest/v1/rpc/list_my_session_history",
        body={'p_limit': 10, 'p_offset': 0},
        headers={'apikey': anon_key, 'Authorization': f"Bearer {tokens['membera']}"}
    )
    assert status_hist_mem == 200 and len(body_hist_mem) == 0
    results['member_history_empty'] = True

    # 5. record_cash_payment via HTTP
    # Player debt member: 30000000-0000-4000-8000-000000000001
    player_debt = '30000000-0000-4000-8000-000000000001'
    status_cash, body_cash = http_request(
        f"{api_url}/rest/v1/rpc/record_cash_payment",
        body={'p_player_id': player_debt, 'p_amount_vnd': 20000, 'p_reference': 'Tiền mặt HTTP', 'p_request_id': str(uuid.uuid4())},
        headers={'apikey': anon_key, 'Authorization': f"Bearer {tokens['ownera']}"}
    )
    assert status_cash == 200 and body_cash.get('status') == 'confirmed'
    results['http_cash_payment_status'] = status_cash
    results['tokens'] = tokens
    return results


def verify_db_assertions() -> dict:
    """Executes 23 DB invariant and business logic assertions directly against the reset database."""
    # Proof of target DB identity
    db_meta = sql("SELECT json_build_object('database', current_database(), 'user', current_user, 'server_version', version(), 'container', inet_server_addr()::text, 'port', inet_server_port())::text;")
    print(f"Verified target DB metadata: {db_meta}")

    assertions = []

    def check(name, expr, detail=''):
        res = bool(expr)
        assertions.append({'name': name, 'pass': res, 'detail': detail})
        assert res, f"Assertion failed: {name} ({detail})"

    # 1. Lifecycle of session_debt is completed
    lc = sql("SELECT lifecycle FROM public.sessions WHERE id='10000000-0000-4000-8000-000000000001';")
    check("Session completed lifecycle", lc == 'completed', f"lifecycle={lc}")

    # 2. Audit event SESSION_COMPLETED recorded
    audit_comp = int(sql("SELECT count(*) FROM public.audit_events WHERE session_id='10000000-0000-4000-8000-000000000001' AND action='SESSION_COMPLETED';"))
    check("Audit event SESSION_COMPLETED present", audit_comp == 1, f"count={audit_comp}")

    # 3. Operation request stored
    op_cnt = int(sql("SELECT count(*) FROM public.operation_requests WHERE operation='complete_session';"))
    check("Operation request recorded", op_cnt >= 1, f"count={op_cnt}")

    # 4. Cash payment recorded and ledger entry created
    pay_cnt = int(sql("SELECT count(*) FROM public.payments WHERE session_player_id='30000000-0000-4000-8000-000000000001' AND status='confirmed';"))
    check("Confirmed payment exists", pay_cnt >= 1, f"count={pay_cnt}")

    # 5. Ledger transaction recorded
    tx_cnt = int(sql("SELECT count(*) FROM public.club_transactions WHERE source_type='payment';"))
    check("Ledger transaction exists", tx_cnt >= 1, f"count={tx_cnt}")

    # 6. Outstanding debt calculation
    charges_sum = int(sql("SELECT COALESCE(SUM(amount_due_vnd), 0) FROM public.session_charges WHERE session_player_id='30000000-0000-4000-8000-000000000001';"))
    payments_sum = int(sql("SELECT COALESCE(SUM(amount_vnd), 0) FROM public.payments WHERE session_player_id='30000000-0000-4000-8000-000000000001' AND status='confirmed';"))
    check("Charges and confirmed payments recorded correctly", charges_sum > 0 and payments_sum >= 20000, f"charges={charges_sum}, payments={payments_sum}")

    # 7. Unfinalized complete rejected (session_stale: 10000000-0000-4000-8000-000000000003)
    ver_stale = int(sql("SELECT version FROM public.sessions WHERE id='10000000-0000-4000-8000-000000000003';"))
    p_err1 = sql_as('ownera@example.test', f"SELECT public.complete_session('10000000-0000-4000-8000-000000000003'::uuid, {ver_stale}, gen_random_uuid());")
    check("Unfinalized complete rejected", p_err1.returncode != 0 and ('BILLING_STALE' in p_err1.stderr or 'BILLING_NOT_FINALIZED' in p_err1.stderr), p_err1.stderr)

    # 8. Version conflict check
    p_err2 = sql_as('ownera@example.test', "SELECT public.complete_session('10000000-0000-4000-8000-000000000004'::uuid, 9999, gen_random_uuid());")
    check("Version conflict rejected", p_err2.returncode != 0 and 'VERSION_CONFLICT' in p_err2.stderr, p_err2.stderr)

    # 9. Free session completion (session_free: 10000000-0000-4000-8000-000000000002)
    ver_free = int(sql("SELECT version FROM public.sessions WHERE id='10000000-0000-4000-8000-000000000002';"))
    p_free = sql_as('ownera@example.test', f"SELECT public.complete_session('10000000-0000-4000-8000-000000000002'::uuid, {ver_free}, gen_random_uuid());")
    check("Free session completed ok", p_free.returncode == 0, p_free.stderr)

    # 10. Free session lifecycle is completed
    lc_free = sql("SELECT lifecycle FROM public.sessions WHERE id='10000000-0000-4000-8000-000000000002';")
    check("Free session lifecycle completed", lc_free == 'completed')

    # 11. Overcollect payment rejected
    # player_free_guest has 0 debt
    p_over = sql_as('ownera@example.test', "SELECT public.record_cash_payment('30000000-0000-4000-8000-000000000003'::uuid, 50000, NULL, gen_random_uuid());")
    check("Overcollect payment rejected", p_over.returncode != 0 and 'PAYMENT_EXCEEDS_OUTSTANDING' in p_over.stderr, p_over.stderr)

    # 12. Complete already completed session fails with INVALID_STATE
    p_again = sql_as('ownera@example.test', "SELECT public.complete_session('10000000-0000-4000-8000-000000000001'::uuid, 2, gen_random_uuid());")
    check("Complete completed session with new request rejected", p_again.returncode != 0 and 'INVALID_STATE' in p_again.stderr, p_again.stderr)

    # 13. Idempotent replay on completed session
    req_orig = sql("SELECT request_id FROM public.operation_requests WHERE operation='complete_session' LIMIT 1;")
    p_rep = sql_as('ownera@example.test', f"SELECT public.complete_session('10000000-0000-4000-8000-000000000001'::uuid, 7, '{req_orig}'::uuid);")
    check("Idempotent replay succeeds without error", p_rep.returncode == 0, p_rep.stderr)

    # 14. Conflicting payload with same request_id rejected
    p_conf = sql_as('ownera@example.test', f"SELECT public.complete_session('10000000-0000-4000-8000-000000000001'::uuid, 999, '{req_orig}'::uuid);")
    check("Conflicting payload rejected with IDEMPOTENCY_CONFLICT", p_conf.returncode != 0 and 'IDEMPOTENCY_CONFLICT' in p_conf.stderr, p_conf.stderr)

    # 15. Active charge revision invariant
    rev_cnt = int(sql("SELECT count(*) FROM public.charge_revisions WHERE session_id='10000000-0000-4000-8000-000000000001' AND status='active';"))
    check("Exactly one active charge revision", rev_cnt == 1, f"active_revisions={rev_cnt}")

    # 16. Total charges invariant matches sum of player charges
    rev_total = int(sql("SELECT allocation_total_vnd FROM public.charge_revisions WHERE session_id='10000000-0000-4000-8000-000000000001' AND status='active';"))
    players_total = int(sql("SELECT COALESCE(SUM(amount_due_vnd), 0) FROM public.session_charges WHERE revision_id=(SELECT id FROM public.charge_revisions WHERE session_id='10000000-0000-4000-8000-000000000001' AND status='active');"))
    check("Revision total matches sum of charges", rev_total == players_total, f"rev={rev_total}, players={players_total}")

    # 17. Venue court count invariant
    v_court = int(sql("SELECT court_count FROM public.venues WHERE id='cccccccc-3333-4333-8333-333333333333';"))
    check("Venue court count is valid", v_court > 0, f"court_count={v_court}")

    # 18. Club membership invariant
    owner_role = sql("SELECT role FROM public.club_members WHERE club_id='aaaaaaaa-1111-4111-8111-111111111111' AND display_name='Owner A';")
    check("Owner member role is owner", owner_role == 'owner')

    # 19. Session visibility enum invariant
    vis = sql("SELECT visibility FROM public.sessions WHERE id='10000000-0000-4000-8000-000000000001';")
    check("Session visibility is valid enum", vis in ('public', 'unlisted', 'club_only'))

    # 20. Direct anonymous access to sensitive tables denied
    p_anon = sql_run("BEGIN; SET LOCAL ROLE anon; SELECT * FROM public.audit_events; ROLLBACK;")
    check("Anon direct query to audit_events denied", p_anon.returncode != 0 and 'permission denied' in p_anon.stderr, p_anon.stderr)

    # 21. Anonymous access to operation_requests denied
    p_anon_op = sql_run("BEGIN; SET LOCAL ROLE anon; SELECT * FROM public.operation_requests; ROLLBACK;")
    check("Anon direct query to operation_requests denied", p_anon_op.returncode != 0 and 'permission denied' in p_anon_op.stderr, p_anon_op.stderr)

    # 22. No orphaned payments
    orphaned_payments = int(sql("SELECT count(*) FROM public.payments p LEFT JOIN public.session_players sp ON sp.id=p.session_player_id WHERE sp.id IS NULL;"))
    check("Zero orphaned payments", orphaned_payments == 0)

    # 23. Ledger entries reference existing clubs
    orphaned_tx = int(sql("SELECT count(*) FROM public.club_transactions ct LEFT JOIN public.clubs c ON c.id=ct.club_id WHERE c.id IS NULL;"))
    check("Zero orphaned club transactions", orphaned_tx == 0)

    return {
        'target_db_metadata': json.loads(db_meta),
        'total_assertions': len(assertions),
        'passed_assertions': sum(1 for a in assertions if a['pass']),
        'assertions': assertions
    }


def main():
    print(f"=== Starting V5b Full Supabase CLI Reset Verification ===")
    print(f"Timestamp: {STAMP}")
    print(f"Base SHA: {BASE_SHA}")
    print(f"Dedicated project ID: {PROJECT_ID}")
    print(f"Dedicated ports: API={PORT_API}, DB={PORT_DB}, Studio={PORT_STUDIO}")

    # R1: Preflight check before anything is allocated or started
    preflight_res = preflight_ownership_check()
    audit_results['preflight'] = preflight_res

    # Check preconditions
    p_ver = run_cmd(['npx', 'supabase', '--version'])
    supabase_ver = p_ver.stdout.strip()
    print(f"Supabase CLI version: {supabase_ver}")

    p_doc = run_cmd(['docker', '--version'])
    docker_ver = p_doc.stdout.strip()
    print(f"Docker version: {docker_ver}")

    tested_sha = run_cmd(['git', 'rev-parse', 'HEAD']).stdout.strip()
    status_porcelain = run_cmd(['git', 'status', '--porcelain']).stdout.strip()
    dirty_files = [line.strip() for line in status_porcelain.splitlines()] if status_porcelain else []
    git_dirty = len(dirty_files) > 0
    print(f"Tested commit SHA: {tested_sha} (dirty={git_dirty}, files={len(dirty_files)})")

    # Temp workspace
    temp_dir = Path(tempfile.gettempdir()) / PROJECT_ID
    print(f"Setting up isolated project in: {temp_dir}")
    prepare_project_dir(temp_dir)
    log_cmd("Prepare isolated project directory", f"prepare_project_dir({temp_dir}) with dedicated ports {PORT_API}-{PORT_POOLER}")

    start_log = ""
    stop_log = ""
    primary_error = None
    owned_containers = []

    try:
        # Start isolated Supabase stack
        print("Starting isolated Supabase stack...")
        p_start = run_cmd(['npx', 'supabase', 'start', '--workdir', str(temp_dir)])
        exits['supabase_start'] = p_start.returncode
        start_log = p_start.stdout + "\n" + p_start.stderr
        write_evidence('start.log', start_log)
        log_cmd("Start isolated stack", f"npx supabase start --workdir {temp_dir}")

        # Track owned containers
        p_owned = run_cmd(['docker', 'ps', '-a', '--filter', f'name={PROJECT_ID}', '--format', '{{.ID}}'], check=False)
        if p_owned.returncode != 0:
            raise RuntimeError(f"Owned container inventory failed (exit {p_owned.returncode}); refusing reset")
        owned_containers = p_owned.stdout.strip().splitlines() if p_owned.stdout.strip() else []
        if not owned_containers:
            raise RuntimeError("Owned container inventory is empty; refusing reset")
        print(f"Owned project containers initialized ({len(owned_containers)} containers): {owned_containers}")

        # Get status
        p_stat = run_cmd(['npx', 'supabase', 'status', '--workdir', str(temp_dir), '-o', 'json'])
        status_info = json.loads(p_stat.stdout)
        api_url = status_info['API_URL']
        anon_key = status_info['ANON_KEY']
        service_role_key = status_info['SERVICE_ROLE_KEY']

        # Assert loopback isolation
        uri = urllib.request.urlparse(api_url)
        assert uri.hostname in ('127.0.0.1', 'localhost', '::1')
        assert uri.port == PORT_API

        # -------------------------------------------------------------
        # CYCLE 1
        # -------------------------------------------------------------
        print("\n--- Starting Reset Cycle 1 ---")
        p_reset1 = run_cmd(['npx', 'supabase', 'db', 'reset', '--workdir', str(temp_dir), '--local', '--no-seed', '--yes'])
        exits['reset_cycle1'] = p_reset1.returncode
        write_evidence('reset_cycle1.log', p_reset1.stdout + "\n" + p_reset1.stderr)
        log_cmd("Reset cycle 1", f"npx supabase db reset --workdir {temp_dir} --local --no-seed --yes")

        # Seed Cycle 1
        print("Seeding Auth users and data for Cycle 1...")
        auth_lines1, seed_out1 = seed_auth_and_data(api_url, service_role_key)
        write_evidence('auth_seed_cycle1.log', "\n".join(auth_lines1) + "\n" + seed_out1)

        # Verification Cycle 1
        print("Running Schema, HTTP, and DB Assertions for Cycle 1...")
        schema_res1 = verify_schema()
        assert schema_res1['schema_valid'], f"Cycle 1 schema validation failed: {schema_res1}"
        audit_results['cycle1']['schema'] = schema_res1

        http_res1 = verify_http_and_auth(api_url, anon_key)
        audit_results['cycle1']['http'] = http_res1

        db_res1 = verify_db_assertions()
        assert db_res1['passed_assertions'] == db_res1['total_assertions'] == 23, f"Cycle 1 DB assertions expected 23, got {db_res1['passed_assertions']}/{db_res1['total_assertions']}"
        audit_results['cycle1']['db_assertions'] = db_res1

        fp1 = compute_db_fingerprint()
        audit_results['cycle1']['snapshot'] = fp1
        print(f"Cycle 1 completed. Total tables: {fp1['total_tables']}, Schema SHA: {fp1['schema_sha256'][:16]}...")

        # -------------------------------------------------------------
        # CYCLE 2 (Repeat Reset Oracle)
        # -------------------------------------------------------------
        print("\n--- Starting Reset Cycle 2 (Repeat Reset Oracle) ---")
        p_reset2 = run_cmd(['npx', 'supabase', 'db', 'reset', '--workdir', str(temp_dir), '--local', '--no-seed', '--yes'])
        exits['reset_cycle2'] = p_reset2.returncode
        write_evidence('reset_cycle2.log', p_reset2.stdout + "\n" + p_reset2.stderr)
        log_cmd("Reset cycle 2", f"npx supabase db reset --workdir {temp_dir} --local --no-seed --yes")

        # Seed Cycle 2
        print("Seeding Auth users and data for Cycle 2...")
        auth_lines2, seed_out2 = seed_auth_and_data(api_url, service_role_key)
        write_evidence('auth_seed_cycle2.log', "\n".join(auth_lines2) + "\n" + seed_out2)

        # Verification Cycle 2
        print("Running Schema, HTTP, and DB Assertions for Cycle 2...")
        schema_res2 = verify_schema()
        assert schema_res2['schema_valid'], f"Cycle 2 schema validation failed: {schema_res2}"
        audit_results['cycle2']['schema'] = schema_res2

        http_res2 = verify_http_and_auth(api_url, anon_key)
        audit_results['cycle2']['http'] = http_res2

        db_res2 = verify_db_assertions()
        assert db_res2['passed_assertions'] == db_res2['total_assertions'] == 23, f"Cycle 2 DB assertions expected 23, got {db_res2['passed_assertions']}/{db_res2['total_assertions']}"
        audit_results['cycle2']['db_assertions'] = db_res2

        fp2 = compute_db_fingerprint()
        audit_results['cycle2']['snapshot'] = fp2
        print(f"Cycle 2 completed. Total tables: {fp2['total_tables']}, Schema SHA: {fp2['schema_sha256'][:16]}...")

        # -------------------------------------------------------------
        # ORACLE COMPARISON
        # -------------------------------------------------------------
        print("\n--- Comparing Oracle Snapshots ---")
        assert fp1['schema_sha256'] == fp2['schema_sha256'], f"Schema hash mismatch between Cycle 1 ({fp1['schema_sha256']}) and Cycle 2 ({fp2['schema_sha256']})!"
        assert fp1['total_tables'] == fp2['total_tables'] == 48, f"Table count mismatch or not 48: {fp1['total_tables']} vs {fp2['total_tables']}"

        count_mismatches = []
        for tbl, stat1 in fp1['table_stats'].items():
            stat2 = fp2['table_stats'].get(tbl)
            if not stat2:
                count_mismatches.append(f"Missing table in Cycle 2: {tbl}")
            elif stat1['count'] != stat2['count']:
                count_mismatches.append(f"Row count mismatch in {tbl}: cycle1={stat1['count']} vs cycle2={stat2['count']}")
        assert len(count_mismatches) == 0, f"Table row count mismatches found: {count_mismatches}"

        audit_results['oracle_match'] = True
        print(f"ORACLE PASS: Schema SHA256 and all {fp1['total_tables']} table row counts match 100% across both reset cycles!")

        # -------------------------------------------------------------
        # NEGATIVE CONTROLS (R2: Exact HTTP status + domain error code)
        # -------------------------------------------------------------
        print("\n--- Running Negative Controls ---")
        neg_results = []

        # Positive baseline control: verify valid get_session_summary via real HTTP request with Owner A
        session_debt = '10000000-0000-4000-8000-000000000001'
        owner_token = http_res2['tokens']['ownera']
        pos_st, pos_b = http_request(
            f"{api_url}/rest/v1/rpc/get_session_summary",
            body={'p_session_id': session_debt},
            headers={'apikey': anon_key, 'Authorization': f"Bearer {owner_token}"}
        )
        assert pos_st == 200, f"Positive baseline HTTP get_session_summary failed: {pos_st} {pos_b}"
        assert pos_b.get('can_view_finance') is True, f"Positive baseline unexpected finance view: {pos_b}"
        print(f"Positive baseline control PASS: status={pos_st}, can_view_finance={pos_b.get('can_view_finance')}")

        # Neg 1: Unauthenticated anon call to complete_session
        ver_latest = int(sql(f"SELECT version FROM public.sessions WHERE id='{session_debt}';"))
        st1, b1 = http_request(
            f"{api_url}/rest/v1/rpc/complete_session",
            body={'p_session_id': session_debt, 'p_expected_version': ver_latest, 'p_request_id': str(uuid.uuid4())},
            headers={'apikey': anon_key}
        )
        print(f"Neg 1 (anon complete_session): status={st1}, body={b1}")
        assert_negative_auth_rejection('anon_complete_rejected', st1, b1, 'anon_complete')
        neg_results.append({
            'control': 'anon_complete_rejected',
            'status': st1,
            'code': b1.get('code', ''),
            'rejected': True,
            'domain_verified': True
        })

        # Neg 1b: Request missing apikey entirely rejected by gateway / postgrest
        st1b, b1b = http_request(
            f"{api_url}/rest/v1/rpc/complete_session",
            body={'p_session_id': session_debt, 'p_expected_version': ver_latest, 'p_request_id': str(uuid.uuid4())},
            headers={}
        )
        print(f"Neg 1b (no-apikey request): status={st1b}, body={b1b}")
        assert_negative_auth_rejection('no_apikey_rejected', st1b, b1b, 'no_apikey')
        neg_results.append({
            'control': 'no_apikey_rejected',
            'status': st1b,
            'code': b1b.get('code', ''),
            'rejected': True,
            'domain_verified': True
        })

        # Neg 2: Outsider user access to private summary rejected
        login_st, login_b = http_request(
            f"{api_url}/auth/v1/token?grant_type=password",
            body={'email': 'outsider@example.test', 'password': 'bh07-http-pass-123456'},
            headers={'apikey': anon_key}
        )
        outsider_jwt = login_b['access_token']
        st2, b2 = http_request(
            f"{api_url}/rest/v1/rpc/get_session_summary",
            body={'p_session_id': session_debt},
            headers={'apikey': anon_key, 'Authorization': f'Bearer {outsider_jwt}'}
        )
        print(f"Neg 2 (outsider get_session_summary): status={st2}, body={b2}")
        assert_negative_auth_rejection('outsider_summary_forbidden', st2, b2, 'outsider_summary')
        neg_results.append({
            'control': 'outsider_summary_forbidden',
            'status': st2,
            'code': b2.get('code', ''),
            'rejected': True,
            'domain_verified': True
        })

        # Neg 3: Non-loopback URL rejected by client guard
        try:
            http_request("http://192.168.1.100:54321/rest/v1/")
            guard_pass = False
        except ValueError:
            guard_pass = True
        neg_results.append({'control': 'loopback_guard', 'rejected': guard_pass})
        assert guard_pass

        audit_results['negative_controls'] = neg_results
        write_evidence('negative_controls.log', json.dumps(neg_results, indent=2))
        print("Negative controls: ALL PASS (strict status and error domain verified)")

    except Exception as exc:
        primary_error = exc
        print(f"\n[FATAL] Primary execution error: {exc}")

    finally:
        # -------------------------------------------------------------
        # CLEANUP / TEARDOWN (R3: Fail-closed, best-effort continue, keep primary error)
        # -------------------------------------------------------------
        print("\n--- Teardown: Stopping and Cleaning Isolated Stack ---")
        cleanup_errors = []

        # 1. Stop supabase project
        try:
            p_stop = run_cmd(['npx', 'supabase', 'stop', '--workdir', str(temp_dir), '--no-backup'], check=False)
            exits['supabase_stop'] = p_stop.returncode
            stop_log = p_stop.stdout + "\n" + p_stop.stderr
            write_evidence('stop.log', stop_log)
            log_cmd("Stop isolated stack", f"npx supabase stop --workdir {temp_dir} --no-backup")
            if p_stop.returncode != 0:
                cleanup_errors.append(f"supabase stop exited with {p_stop.returncode}: {p_stop.stderr.strip()}")
        except Exception as stop_exc:
            cleanup_errors.append(f"supabase stop raised exception: {stop_exc}")

        # 2. Inspect and remove ONLY owned containers (fail-closed if inspection fails)
        try:
            p_check = run_cmd(['docker', 'ps', '-a', '-q', '--filter', f'name={PROJECT_ID}'], check=False)
            if p_check.returncode != 0:
                cleanup_errors.append(f"docker ps inspection failed ({p_check.returncode}): {p_check.stderr.strip()}")
            else:
                found_ids = p_check.stdout.strip().splitlines() if p_check.stdout.strip() else []
                # Segregate owned vs foreign
                owned_to_remove = [cid for cid in found_ids if cid in owned_containers]
                foreign_ids = [cid for cid in found_ids if cid not in owned_containers]

                if foreign_ids:
                    cleanup_errors.append(
                        f"Refusing to delete unowned foreign container(s) matching '{PROJECT_ID}': {foreign_ids}"
                    )
                if owned_to_remove:
                    print(f"Removing {len(owned_to_remove)} owned container(s)...")
                    p_rm = run_cmd(['docker', 'rm', '-f'] + owned_to_remove, check=False)
                    if p_rm.returncode != 0:
                        cleanup_errors.append(f"docker rm -f failed ({p_rm.returncode}): {p_rm.stderr.strip()}")
        except Exception as cont_exc:
            cleanup_errors.append(f"Container inspection/removal raised exception: {cont_exc}")

        # 3. Remove temp directory
        try:
            if temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)
            if temp_dir.exists():
                cleanup_errors.append(f"Tempdir {temp_dir} still exists after rmtree")
        except Exception as rmtree_exc:
            cleanup_errors.append(f"shutil.rmtree raised exception: {rmtree_exc}")

        # 4. Final verification of absence inside best-effort try block
        final_remaining = -1
        try:
            p_final = run_cmd(['docker', 'ps', '-a', '-q', '--filter', f'name={PROJECT_ID}'], check=False)
            if p_final.returncode != 0:
                cleanup_errors.append(f"docker ps final verification failed ({p_final.returncode}): {p_final.stderr.strip()}")
            else:
                final_ids = p_final.stdout.strip().splitlines() if p_final.stdout.strip() else []
                final_remaining = len(final_ids)
                if final_remaining > 0:
                    cleanup_errors.append(f"{final_remaining} container(s) remaining after teardown: {final_ids}")
        except Exception as final_exc:
            cleanup_errors.append(f"Final container verification raised exception: {final_exc}")

        clean_status = (final_remaining == 0 and len(cleanup_errors) == 0)
        audit_results['cleanup'] = {
            'stop_exit': exits.get('supabase_stop', -1),
            'remaining_containers_count': final_remaining if final_remaining >= 0 else 0,
            'cleanup_errors': cleanup_errors,
            'clean': clean_status
        }

        # 5. Handle errors: primary error ALWAYS takes precedence
        if primary_error is not None:
            print(f"Teardown finished. Re-raising primary error to prevent masking: {primary_error}")
            raise primary_error

        if cleanup_errors:
            raise RuntimeError(f"Cleanup failed with {len(cleanup_errors)} error(s): {'; '.join(cleanup_errors)}")

        print("Cleanup verified: 0 remaining containers, tempdir purged, 0 cleanup errors.")

    # -----------------------------------------------------------------
    # PRODUCE EVIDENCE BUNDLE (R4: Full evidence, provenance, and exact counts)
    # -----------------------------------------------------------------
    # All 48 tables full stats for both cycles
    write_evidence('snapshot_comparison.json', json.dumps({
        'oracle_match': audit_results['oracle_match'],
        'cycle1_schema_sha256': audit_results['cycle1']['snapshot']['schema_sha256'],
        'cycle2_schema_sha256': audit_results['cycle2']['snapshot']['schema_sha256'],
        'cycle1_total_tables': audit_results['cycle1']['snapshot']['total_tables'],
        'cycle2_total_tables': audit_results['cycle2']['snapshot']['total_tables'],
        'cycle1_tables': audit_results['cycle1']['snapshot']['table_stats'],
        'cycle2_tables': audit_results['cycle2']['snapshot']['table_stats'],
    }, indent=2))

    write_evidence('environment.json', json.dumps({
        'timestamp': STAMP,
        'base_sha': BASE_SHA,
        'tested_sha': tested_sha,
        'git_dirty': git_dirty,
        'git_dirty_files': dirty_files,
        'supabase_cli_version': supabase_ver,
        'docker_version': docker_ver,
        'os': sys.platform,
        'project_id': PROJECT_ID,
        'ports': {
            'api': PORT_API,
            'db': PORT_DB,
            'shadow': PORT_SHADOW,
            'studio': PORT_STUDIO,
            'smtp': PORT_SMTP,
            'analytics': PORT_ANALYTICS,
            's3': PORT_S3,
            'pooler': PORT_POOLER
        }
    }, indent=2))

    write_evidence('exits.json', json.dumps(exits, indent=2))

    write_evidence('commands.md', "# V5b Full Supabase Reset Verification Commands\n\n```powershell\n" + "\n\n".join(commands_run) + "\n```\n")

    summary_data = {
        'status': 'PASS',
        'verdict': 'Chờ review độc lập V5b full reset Supabase CLI',
        'tested_sha': tested_sha,
        'base_sha': BASE_SHA,
        'cycles_executed': 2,
        'oracle_repeat_match': audit_results['oracle_match'],
        'db_assertions_cycle1': audit_results['cycle1']['db_assertions']['passed_assertions'],
        'db_assertions_cycle2': audit_results['cycle2']['db_assertions']['passed_assertions'],
        'total_db_assertions_per_cycle': audit_results['cycle1']['db_assertions']['total_assertions'],
        'db_assertions_detail': audit_results['cycle1']['db_assertions']['assertions'],
        'schema_valid': audit_results['cycle1']['schema']['schema_valid'],
        'negative_controls_pass': all(n.get('rejected', False) for n in audit_results['negative_controls']),
        'cleanup_success': audit_results['cleanup']['clean'],
    }
    write_evidence('summary.json', json.dumps(summary_data, indent=2, ensure_ascii=False))

    # Manifest generation (hashes.sha256)
    manifest_lines = []
    for f in sorted(EVIDENCE_DIR.glob('*')):
        if f.is_file() and f.name != 'hashes.sha256':
            content = f.read_bytes()
            h = hashlib.sha256(content).hexdigest()
            manifest_lines.append(f"{h}  {f.name}")
    (EVIDENCE_DIR / 'hashes.sha256').write_text("\n".join(manifest_lines) + "\n", encoding='utf-8', newline='\n')

    print(f"\nManifest hashes.sha256 generated ({len(manifest_lines)} files).")
    print("\n=== V5b FULL SUPABASE CLI RESET VERIFICATION: ALL PASS ===")
    return 0


if __name__ == '__main__':
    sys.exit(main())

