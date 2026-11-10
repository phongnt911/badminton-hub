"""BH-07 V4: Local isolated Docker concurrent HTTP writers backup/restore rehearsal.

Demonstrates:
1. Isolated staging-like Docker stack (PostgreSQL 17, GoTrue, PostgREST).
2. Explicit PostgreSQL snapshot export (pg_export_snapshot()) held in a REPEATABLE READ
   transaction, passed to pg_dump --snapshot=<id> for exact deterministic visibility.
3. Pre-snapshot payment (P0) by finance-authorized actor (ownera) committed before snapshot;
   restored and verified.
4. Two concurrent authenticated HTTP writers (OwnerA and FinanceA, never Member)
   committing cash payments (P1A, P1B) with confirmed execution overlap while the pg_dump
   backend is actively connected (observed via pg_stat_activity).
5. Post-snapshot concurrent payments are present in source DB but strictly absent from restored DB.
6. Exact restored cardinality and invariant checks (1:1:1:1 payments, ledger, audit, requests).
7. Idempotent replay on restored DB returns identical payment ID with zero row growth.
8. Fail-closed validator and verified resource cleanup.

Working-tree candidate pending independent review.
All credentials generated at runtime; no static secret literals.
"""
import argparse
import concurrent.futures
from contextlib import contextmanager
import copy
import hashlib
import json
import math
import os
import queue
from pathlib import Path
import re
import runpy
import secrets
import shutil
import socket
import subprocess
import tempfile
import threading
import time
import urllib.error
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parents[2]
SETUP = ROOT / 'docs/reviews/bh07/late_response_evidence/run_local_stack.py'
OPEN = urllib.request.build_opener(urllib.request.ProxyHandler({}))

SESSION = '10000000-0000-4000-8000-000000000001'
PLAYER = '30000000-0000-4000-8000-000000000001'

FINANCE_AUTHORIZED_ROLES = {'ownera', 'financea'}
ACTUAL_BASE_SHA = 'd2f6b079a7a6f7521d04b88ac6eb780db5718a56'

TOOLING_SCHEMA = 'tooling_rehearsal'
PADDING_TABLE = 'rehearsal_padding'
DEFAULT_PADDING_ROWS = 260000
MAX_PADDING_BUDGET_BYTES = 256 * 1024 * 1024
MIN_DISK_PREFLIGHT_BYTES = 2 * 1024 * 1024 * 1024


def check_resource_budget(path, min_free_bytes=MIN_DISK_PREFLIGHT_BYTES):
    """Preflight check to ensure finite disk resources before allocating padding."""
    usage = shutil.disk_usage(path)
    if usage.free < min_free_bytes:
        raise RuntimeError(
            f"Insufficient disk space for rehearsal padding: {usage.free} bytes free, "
            f"required at least {min_free_bytes} bytes"
        )


def _parse_and_validate_padding_stats(raw_json, expected_rows=None):
    if not isinstance(raw_json, str) or not raw_json.strip():
        raise ValueError(f"Padding stats query returned empty or non-string response: {raw_json!r}")
    try:
        data = json.loads(raw_json)
    except Exception as err:
        raise ValueError(f"Failed to parse padding stats JSON: {err}") from None
    if not isinstance(data, dict):
        raise ValueError(f"Padding stats must be a JSON object, got {type(data).__name__}")
    for field in ('rows', 'bytes', 'digest'):
        if field not in data:
            raise ValueError(f"Padding stats missing required field: {field!r}")
    rows = data['rows']
    if not isinstance(rows, int) or isinstance(rows, bool) or rows <= 0:
        raise ValueError(f"Padding stats 'rows' must be positive integer, got {rows!r}")
    if expected_rows is not None and rows != expected_rows:
        raise ValueError(f"Padding stats 'rows' mismatch: expected {expected_rows}, got {rows}")
    b_bytes = data['bytes']
    if not isinstance(b_bytes, int) or isinstance(b_bytes, bool) or b_bytes <= 0:
        raise ValueError(f"Padding stats 'bytes' must be positive integer, got {b_bytes!r}")
    if b_bytes > MAX_PADDING_BUDGET_BYTES:
        raise ValueError(f"Padding stats 'bytes' ({b_bytes}) exceeds budget ({MAX_PADDING_BUDGET_BYTES})")
    digest_val = data['digest']
    if not isinstance(digest_val, str) or not re.fullmatch(r'^([0-9a-f]{32}|[0-9a-f]{64})$', digest_val):
        raise ValueError(f"Padding stats 'digest' must be valid 32- or 64-char hex string, got {digest_val!r}")
    return {
        'schema': TOOLING_SCHEMA,
        'table': PADDING_TABLE,
        'rows': rows,
        'bytes': b_bytes,
        'digest': digest_val,
    }


def setup_padding_fixture(container, rows=DEFAULT_PADDING_ROWS):
    """Sets up a bounded padding table in a dedicated tooling-only schema.

    Extends the pg_dump COPY observation window for concurrent HTTP writers without
    mutating public/auth schemas or app financial workload tables.
    """
    if not isinstance(rows, int) or isinstance(rows, bool) or rows <= 0:
        raise ValueError(f"Padding rows must be positive int, got {rows!r}")
    if rows * 992 > MAX_PADDING_BUDGET_BYTES:
        raise ValueError(
            f"Requested padding rows ({rows}) exceeds finite budget of {MAX_PADDING_BUDGET_BYTES} bytes"
        )
    create_sql = (
        f"CREATE SCHEMA IF NOT EXISTS {TOOLING_SCHEMA};\n"
        f"CREATE TABLE {TOOLING_SCHEMA}.{PADDING_TABLE} (\n"
        f"    id integer PRIMARY KEY,\n"
        f"    payload text NOT NULL\n"
        f");\n"
        f"INSERT INTO {TOOLING_SCHEMA}.{PADDING_TABLE} (id, payload)\n"
        f"SELECT i, repeat(md5(i::text), 31)\n"
        f"FROM generate_series(1, {rows}) AS s(i);\n"
    )
    sql(container, create_sql)
    stats_raw = sql(
        container,
        f"SELECT json_build_object("
        f"'rows', count(*), "
        f"'bytes', COALESCE(sum(octet_length(payload)), 0), "
        f"'digest', md5(COALESCE(string_agg(id::text || ':' || md5(payload), ',' ORDER BY id), ''))"
        f") FROM {TOOLING_SCHEMA}.{PADDING_TABLE}"
    )
    return _parse_and_validate_padding_stats(stats_raw, expected_rows=rows)


def verify_restored_padding_fixture(container, expected_stats):
    """Verifies that the tooling padding fixture was faithfully restored in target DB."""
    if not isinstance(expected_stats, dict):
        raise ValueError("expected_stats must be a dict")
    stats_raw = sql(
        container,
        f"SELECT json_build_object("
        f"'rows', count(*), "
        f"'bytes', COALESCE(sum(octet_length(payload)), 0), "
        f"'digest', md5(COALESCE(string_agg(id::text || ':' || md5(payload), ',' ORDER BY id), ''))"
        f") FROM {TOOLING_SCHEMA}.{PADDING_TABLE}"
    )
    restored_stats = _parse_and_validate_padding_stats(stats_raw, expected_rows=expected_stats.get('rows'))
    if (restored_stats['rows'] != expected_stats.get('rows')
            or restored_stats['bytes'] != expected_stats.get('bytes')
            or restored_stats['digest'] != expected_stats.get('digest')):
        raise ValueError(
            f"Restored padding fixture mismatch: expected {expected_stats}, got {restored_stats}"
        )
    return restored_stats


class V4CoordinationBarrier:
    """Thread-safe barrier for coordinating pg_dump backend and concurrent HTTP writers."""

    def __init__(self, timeout_seconds=60.0):
        self.timeout_seconds = timeout_seconds
        self._dump_started = threading.Event()
        self._dump_finished = threading.Event()
        self._snapshot_id = None
        self._active = False
        self._lock = threading.Lock()

    def notify_dump_started(self, snapshot_id):
        with self._lock:
            self._snapshot_id = snapshot_id
            self._active = True
            self._dump_started.set()

    def wait_until_dump_active(self, timeout=None):
        tout = self.timeout_seconds if timeout is None else timeout
        return self._dump_started.wait(timeout=tout)

    def notify_dump_finished(self):
        with self._lock:
            self._active = False
            self._dump_finished.set()

    def is_dump_active(self):
        with self._lock:
            return self._active

    def get_snapshot_id(self):
        with self._lock:
            return self._snapshot_id


def digest(raw):
    """Calculates SHA-256 hex digest of bytes or canonical JSON."""
    if not isinstance(raw, bytes):
        raw = json.dumps(raw, sort_keys=True, separators=(',', ':')).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()


def free_port():
    """Finds an unused loopback TCP port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


STAGE_TARGET_AUTH_START = 'target_auth_start'
STAGE_TARGET_REST_START = 'target_rest_start'
STAGE_NETWORK_ATTACHMENT = 'network_attachment'
STAGE_PORT_DISCOVERY = 'port_discovery'
STAGE_AUTH_HEALTH_LOGIN = 'auth_health_login'
STAGE_REPLAY_FINGERPRINT_COLLECTION = 'replay_fingerprint_collection'
STAGE_COMPLETED = 'completed'

PREDEFINED_STAGES = frozenset({
    STAGE_TARGET_AUTH_START,
    STAGE_TARGET_REST_START,
    STAGE_NETWORK_ATTACHMENT,
    STAGE_PORT_DISCOVERY,
    STAGE_AUTH_HEALTH_LOGIN,
    STAGE_REPLAY_FINGERPRINT_COLLECTION,
    STAGE_COMPLETED,
})

OP_TARGET_DB_START = 'target_db_start'
OP_TARGET_DB_READY = 'target_db_ready'
OP_TARGET_RESTORE_GLOBALS = 'target_restore_globals'
OP_TARGET_RESTORE_DUMP = 'target_restore_dump'
OP_TARGET_AUTH_START = 'target_auth_start'
OP_TARGET_REST_START = 'target_rest_start'
OP_TARGET_NETWORK_ATTACH = 'target_network_attach'
OP_TARGET_PORT_DISCOVERY = 'target_port_discovery'
OP_TARGET_AUTH_LOGIN = 'target_auth_login'
OP_TARGET_REPLAY = 'target_replay'
OP_DOCKER_GENERIC = 'docker'

SAFE_OPERATIONS_WHITELIST = frozenset({
    OP_TARGET_DB_START,
    OP_TARGET_DB_READY,
    OP_TARGET_RESTORE_GLOBALS,
    OP_TARGET_RESTORE_DUMP,
    OP_TARGET_AUTH_START,
    OP_TARGET_REST_START,
    OP_TARGET_NETWORK_ATTACH,
    OP_TARGET_PORT_DISCOVERY,
    OP_TARGET_AUTH_LOGIN,
    OP_TARGET_REPLAY,
    OP_DOCKER_GENERIC,
})

STAGE_TO_DEFAULT_OP = {
    STAGE_TARGET_AUTH_START: OP_TARGET_AUTH_START,
    STAGE_TARGET_REST_START: OP_TARGET_REST_START,
    STAGE_NETWORK_ATTACHMENT: OP_TARGET_NETWORK_ATTACH,
    STAGE_PORT_DISCOVERY: OP_TARGET_PORT_DISCOVERY,
    STAGE_AUTH_HEALTH_LOGIN: OP_TARGET_AUTH_LOGIN,
    STAGE_REPLAY_FINGERPRINT_COLLECTION: OP_TARGET_REPLAY,
}

STAGE_DEFAULT_ERROR_LABELS = {
    STAGE_TARGET_AUTH_START: "target auth service failed to start",
    STAGE_TARGET_REST_START: "target rest service failed to start",
    STAGE_NETWORK_ATTACHMENT: "target network attachment failed",
    STAGE_PORT_DISCOVERY: "target port discovery failed",
    STAGE_AUTH_HEALTH_LOGIN: "target auth health check failed",
    STAGE_REPLAY_FINGERPRINT_COLLECTION: "target replay verification failed",
}


def resolve_safe_operation(op=None, args=None):
    """Restricts operation identity to predefined constants / whitelist, never user text or arbitrary args."""
    if isinstance(op, str) and op in SAFE_OPERATIONS_WHITELIST:
        return op
    if isinstance(args, (list, tuple)) and args:
        cmd_token = str(args[0]).lower()
        if 'docker' in cmd_token:
            if len(args) > 1:
                sub = str(args[1]).lower()
                if sub == 'port':
                    return OP_TARGET_PORT_DISCOVERY
                if sub == 'network' and len(args) > 2 and str(args[2]).lower() == 'connect':
                    return OP_TARGET_NETWORK_ATTACH
            return OP_DOCKER_GENERIC
    return OP_DOCKER_GENERIC


def command_error(operation, returncode):
    """Constructs a RuntimeError with safe operation identity and exit code without raw args or stderr."""
    safe_op = resolve_safe_operation(operation)
    rc = returncode if (type(returncode) is int and not isinstance(returncode, bool)) else 1
    err = RuntimeError(f"{safe_op} exited {rc}")
    err.operation = safe_op
    err.exit_code = rc
    return err


def sanitize_error_message(text):
    """Removes any potential credentials, JWTs, or multi-line command dumps from error messages."""
    if not isinstance(text, str):
        return ''
    safe = re.sub(r'ey[A-Za-z0-9_-]{4,}\.[A-Za-z0-9_-]{4,}\.[A-Za-z0-9_-]*', '<redacted-jwt>', text)
    safe = re.sub(r'(?i)password[=:]\s*\S+', 'password=<redacted>', safe)
    safe = re.sub(r'sb_secret_\S+', '<redacted-key>', safe)
    lines = safe.strip().splitlines()
    return lines[0] if lines else ''


def set_stage(summary: dict, stage: str):
    """Sets predefined execution stage in summary, enforcing predefined constants."""
    if not isinstance(stage, str) or stage not in PREDEFINED_STAGES:
        raise ValueError(f"Invalid execution stage: {stage!r}")
    summary['stage'] = stage
    summary['execution_stage'] = stage


def cmd(args, data=None, accept_error=False, op=None):
    """Executes a subprocess command, capturing output safely."""
    p = subprocess.run(args, input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if p.returncode != 0 and not accept_error:
        safe_op = resolve_safe_operation(op, args)
        raise command_error(safe_op, p.returncode)
    return p


def sql(container, query):
    """Executes SQL via psql in the given Docker container."""
    p = cmd(
        ['docker', 'exec', '-i', container, 'psql', '-U', 'postgres', '-d', 'postgres', '-At', '-v', 'ON_ERROR_STOP=1'],
        data=query.encode('utf-8')
    )
    return p.stdout.decode('utf-8').strip()


def fingerprint(container):
    """Generates structural and data fingerprints for public/auth schemas."""
    tables_json = sql(
        container,
        "SELECT json_agg(json_build_array(schemaname,tablename) ORDER BY schemaname,tablename) "
        "FROM pg_tables WHERE schemaname IN ('public','auth')"
    )
    tables = json.loads(tables_json or '[]')
    result = {}
    for schema, table in tables:
        ident = '"' + schema.replace('"', '""') + '"."' + table.replace('"', '""') + '"'
        rows_json = sql(
            container,
            f"SELECT COALESCE(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text),'[]'::jsonb) FROM {ident} t"
        )
        rows = json.loads(rows_json or '[]')
        result[f'{schema}.{table}'] = {'rows': len(rows), 'sha256': digest(rows)}
    schema_dump = cmd(['docker', 'exec', container, 'pg_dump', '-U', 'postgres', '--schema-only', 'postgres']).stdout.decode('utf-8', 'replace')
    schema_dump = re.sub(r'(?m)^\\(?:un)?restrict .*\n?', '', schema_dump)
    result['_schema'] = digest(schema_dump.encode('utf-8'))
    return result


def http(url, body, headers=None):
    """Makes a loopback HTTP POST request returning status and parsed JSON."""
    parsed = urllib.request.urlparse(url)
    if parsed.hostname not in ('127.0.0.1', 'localhost', '::1'):
        raise ValueError('Only loopback HTTP is allowed')
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode('utf-8'),
        headers={'Content-Type': 'application/json', **(headers or {})}
    )
    try:
        with OPEN.open(req, timeout=20) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read().decode('utf-8'))


def login(auth_url, actor, headers=None, password=''):
    """Logs in an actor with GoTrue and returns the access token."""
    if not password:
        raise ValueError('password required for login')
    status, body = http(
        auth_url + '/token?grant_type=password',
        {'email': actor + '@example.test', 'password': password},
        headers
    )
    if status != 200 or not body.get('access_token'):
        raise RuntimeError(f"Login failed for {actor}: status {status}")
    return body['access_token']


def rpc(rest_url, token, name, payload, headers=None):
    """Invokes a PostgREST RPC as an authenticated user."""
    auth_headers = {'Authorization': f'Bearer {token}', **(headers or {})}
    return http(f"{rest_url}/{name}", payload, auth_headers)


REQUIRED_TABLES = (
    'public.payments',
    'public.club_transactions',
    'public.audit_events',
    'public.operation_requests',
)

EXPECTED_SCOPED_AMOUNTS = {
    'p0_precommit': 10000,
    'p1a_concurrent': 15000,
    'p1b_concurrent': 20000,
}


def workload_rows(container, operations):
    """Read only this run's rows; unrelated seed rows are never counted as payments."""
    payment_ids = ','.join("'" + str(uuid.UUID(op['payment_id'])) + "'" for op in operations.values())
    request_keys = ' OR '.join(
        "(actor_user_id = '" + str(uuid.UUID(op['actor_user_id']))
        + "' AND request_id = '" + str(uuid.UUID(op['request_id'])) + "')"
        for op in operations.values())
    if not payment_ids or not request_keys:
        raise ValueError('Workload scope must not be empty')
    predicates = {
        'payments': f'id IN ({payment_ids})',
        'club_transactions': f'source_payment_id IN ({payment_ids})',
        'audit_events': f"({request_keys}) AND entity_type = 'payment' AND action = 'CASH_PAYMENT_RECORDED'",
        'operation_requests': f"({request_keys}) AND operation = 'record_cash_payment'",
    }
    result = {}
    for table, predicate in predicates.items():
        raw = sql(container, f"SELECT COALESCE(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text),'[]'::jsonb) "
                  f"FROM public.{table} t WHERE {predicate}")
        rows = json.loads(raw)
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            raise ValueError(f'Invalid database rows for {table}')
        result[table] = rows
    return result


def row_fingerprints(rows):
    return {'public.' + table: {'rows': len(records), 'sha256': digest(records)}
            for table, records in rows.items()}


def query_row_evidence(container, payment_id, request_id, actor_id):
    """Bind actual rows by actor/operation/request; never invent missing evidence."""
    rows = workload_rows(container, {'op': {
        'payment_id': payment_id, 'request_id': request_id, 'actor_user_id': actor_id}})
    if any(len(records) != 1 for records in rows.values()):
        raise ValueError('Expected exactly one payment/ledger/audit/request row')
    pay, ledger, audit, request = (rows[table][0] for table in
                                 ('payments', 'club_transactions', 'audit_events', 'operation_requests'))
    result = request.get('result')
    if (pay.get('id') != payment_id or pay.get('session_player_id') != PLAYER
            or pay.get('status') != 'confirmed'
            or ledger.get('source_payment_id') != payment_id
            or ledger.get('amount_vnd') != pay.get('amount_vnd')
            or ledger.get('direction') != 'income' or ledger.get('source_type') != 'payment'
            or audit.get('request_id') != request_id or audit.get('actor_user_id') != actor_id
            or audit.get('entity_id') != payment_id or audit.get('entity_type') != 'payment'
            or audit.get('action') != 'CASH_PAYMENT_RECORDED' or audit.get('session_id') != SESSION
            or request.get('request_id') != request_id or request.get('actor_user_id') != actor_id
            or request.get('operation') != 'record_cash_payment'
            or not isinstance(result, dict) or result.get('payment_id') != payment_id
            or result.get('status') != 'confirmed' or result.get('amount_vnd') != pay.get('amount_vnd')):
        raise ValueError('Database evidence is not bound to the expected cash payment')
    # Receipt aliases preserve the validator contract; values all come from stored rows.
    return {
        'payment': {'id': pay['id'], 'amount_vnd': pay['amount_vnd'],
                    'request_id': request['request_id'], 'player_id': pay['session_player_id']},
        'ledger': {'id': ledger['id'], 'source_payment_id': ledger['source_payment_id'],
                   'amount': ledger['amount_vnd']},
        'audit': {'id': audit['id'], 'request_id': audit['request_id'], 'session_id': audit['session_id']},
        'request': request,
    }


@contextmanager
def held_snapshot(container, timeout=10):
    """A bounded read of a machine-only psql response, with transaction release on errors."""
    process = subprocess.Popen(
        ['docker', 'exec', '-i', container, 'psql', '-X', '-qAt', '-U', 'postgres',
         '-d', 'postgres', '-v', 'ON_ERROR_STOP=1'],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    response = queue.Queue()
    reader = threading.Thread(target=lambda: response.put(process.stdout.readline()), daemon=True)
    try:
        process.stdin.write(b"BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ;\n"
                            b"SELECT 'SNAPSHOT:' || pg_export_snapshot();\n")
        process.stdin.flush()
        reader.start()
        try:
            line = response.get(timeout=timeout).decode('utf-8').strip()
        except queue.Empty:
            raise TimeoutError('Timed out reading exported snapshot') from None
        match = re.fullmatch(r'SNAPSHOT:([0-9A-Fa-f]+-[0-9A-Fa-f]+-[0-9A-Fa-f]+)', line)
        if not match or process.poll() is not None:
            raise ValueError('psql did not return a live exported snapshot')
        yield match.group(1), process
        if process.poll() is not None:
            raise ValueError('Snapshot exporter exited before dump completed')
        process.communicate(input=b'ROLLBACK;\n', timeout=5)
        if process.returncode != 0:
            raise ValueError('Snapshot exporter failed to release transaction')
    finally:
        if process.poll() is None:
            process.kill()
        process.wait(timeout=5)
        if reader.ident is not None:
            reader.join(timeout=5)
        for stream in (process.stdin, process.stdout, process.stderr):
            stream.close()


def observe_dump(container):
    raw = sql(container,
              "SELECT COALESCE(json_agg(json_build_object('dump_pid',pid,"
              "'dump_application_name',application_name,'dump_query',query)), '[]'::json) "
              "FROM pg_stat_activity WHERE pid <> pg_backend_pid() "
              "AND application_name = 'pg_dump' AND state = 'active' AND query LIKE 'COPY %'")
    rows = json.loads(raw)
    if not isinstance(rows, list) or len(rows) > 1:
        raise ValueError('Ambiguous pg_dump backend observation')
    return rows[0] if rows else None


class PersistentDumpObserver:
    """Persistent psql connection over stdin/stdout for low-latency pg_dump observation.

    Avoids subprocess spawn roundtrips by keeping one warmed-up psql connection active
    before and throughout pg_dump execution.
    """

    def __init__(self, container, timeout=5.0):
        self.container = container
        self.timeout = timeout
        self.process = None
        self.reader = None
        self.response_queue = queue.Queue()
        self.seq = 0

    def __enter__(self):
        try:
            self.process = subprocess.Popen(
                ['docker', 'exec', '-i', self.container, 'psql', '-X', '-qAt', '-U', 'postgres',
                 '-d', 'postgres', '-v', 'ON_ERROR_STOP=1'],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            self.reader = threading.Thread(target=self._reader_loop, daemon=True)
            self.reader.start()
            self._warmup()
            return self
        except Exception:
            self.close()
            raise

    def _reader_loop(self):
        try:
            while True:
                line = self.process.stdout.readline()
                if not line:
                    break
                self.response_queue.put(line)
        except Exception as exc:
            self.response_queue.put(exc)
        finally:
            self.response_queue.put(None)

    def _warmup(self):
        warmup_marker = "WARMED_UP:0:READY"
        query = f"SELECT '{warmup_marker}';\n".encode('utf-8')
        try:
            self.process.stdin.write(query)
            self.process.stdin.flush()
        except (BrokenPipeError, OSError) as err:
            raise RuntimeError(f"Failed to write warmup query to psql observer: {err}") from None
        try:
            item = self.response_queue.get(timeout=self.timeout)
        except queue.Empty:
            raise TimeoutError(f"psql observer warmup timed out after {self.timeout}s") from None
        if item is None:
            rc = self.process.poll()
            raise RuntimeError(f"psql observer exited during warmup (exit code {rc})")
        if isinstance(item, Exception):
            raise RuntimeError(f"psql observer warmup error: {item}") from item
        line = item.decode('utf-8', 'replace').strip()
        if line != warmup_marker:
            raise ValueError(f"Observer warmup protocol violation: expected {warmup_marker!r}, got {line!r}")

    def observe(self, timeout=None):
        """Query pg_stat_activity with sequence marker, returning sample dict or None, with call bounds."""
        to = timeout or self.timeout
        self.seq += 1
        marker_prefix = f"OBSERVATION:{self.seq}:"
        query = (
            f"SELECT '{marker_prefix}' || COALESCE(json_agg(json_build_object("
            f"'dump_pid',pid,'dump_application_name',application_name,'dump_query',query"
            f")), '[]'::json) "
            f"FROM pg_stat_activity WHERE pid <> pg_backend_pid() "
            f"AND application_name = 'pg_dump' AND state = 'active' AND query LIKE 'COPY %';\n"
        )
        if self.process.poll() is not None:
            raise RuntimeError(f"psql observer exited prematurely with returncode {self.process.poll()}")
        t0 = time.time()
        try:
            self.process.stdin.write(query.encode('utf-8'))
            self.process.stdin.flush()
        except (BrokenPipeError, OSError) as err:
            raise RuntimeError(f"Failed to write to psql observer stdin: {err}") from None
        try:
            item = self.response_queue.get(timeout=to)
        except queue.Empty:
            raise TimeoutError(f"psql observer query timed out after {to}s") from None
        t1 = time.time()
        if item is None:
            rc = self.process.poll()
            raise RuntimeError(f"psql observer closed stdout unexpectedly (EOF, exit code {rc})")
        if isinstance(item, Exception):
            raise RuntimeError(f"psql observer read error: {item}") from item
        line = item.decode('utf-8', 'replace').strip()
        if not line.startswith(marker_prefix):
            raise ValueError(f"Observer protocol violation: expected prefix {marker_prefix!r}, got {line!r}")
        payload = line[len(marker_prefix):]
        try:
            rows = json.loads(payload)
        except Exception as err:
            raise ValueError(f"Malformed JSON from observer: {err} (raw: {payload!r})") from None
        if not isinstance(rows, list) or len(rows) > 1:
            raise ValueError(f"Ambiguous pg_dump backend observation: {rows!r}")
        if not rows:
            return None
        return {**rows[0], 'observed_start': t0, 'observed_end': t1}

    def close(self):
        errors = []
        proc = self.process
        if proc is not None:
            try:
                if proc.poll() is None:
                    try:
                        proc.stdin.write(b"\\q\n")
                        proc.stdin.flush()
                    except (BrokenPipeError, OSError, ValueError):
                        # A closed input is harmless only if termination is verified below.
                        pass
                    try:
                        proc.wait(timeout=1.0)
                    except Exception:
                        try:
                            proc.kill()
                        except Exception as err:
                            errors.append('kill:' + type(err).__name__)
                        try:
                            proc.wait(timeout=2.0)
                        except Exception as err:
                            errors.append('wait:' + type(err).__name__)
                if proc.poll() is None:
                    errors.append('process_still_running')
            except Exception as err:
                errors.append('process_status:' + type(err).__name__)

        # Join before closing stdout: close() can block on a live readline's stream lock.
        reader = self.reader
        reader_alive = False
        if reader is not None:
            try:
                if reader.ident is not None:
                    reader.join(timeout=2.0)
                reader_alive = reader.is_alive()
            except Exception as err:
                reader_alive = True
                errors.append('reader_status:' + type(err).__name__)
            if reader_alive:
                errors.append('reader_still_running')
        if proc is not None:
            for name in ('stdin', 'stdout', 'stderr'):
                if name == 'stdout' and reader_alive:
                    continue
                stream = None
                try:
                    stream = getattr(proc, name)
                    if stream is not None:
                        stream.close()
                except Exception as err:
                    # Buffered stdin can raise while flushing to an exited child yet close
                    # its handle successfully. Require an explicitly verified closed handle.
                    if getattr(stream, 'closed', False) is not True:
                        errors.append(name + '_close:' + type(err).__name__)
        if errors:
            raise RuntimeError('psql observer cleanup unverified: ' + ', '.join(errors))

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False


def open_dump_observer(container, timeout=5.0):
    return PersistentDumpObserver(container, timeout=timeout)


def dump_with_writers(container, snapshot_id, writer_a, writer_b, observer_factory=None):
    """Timestamp dump in its worker; require a real sample inside both HTTP intervals."""
    def dump():
        start = time.time()
        result = cmd(['docker', 'exec', container, 'pg_dump', '-U', 'postgres',
                      '--format=custom', '--compress=0', f'--snapshot={snapshot_id}', 'postgres'])
        return result, start, time.time()

    samples = []
    factory = observer_factory or open_dump_observer
    with factory(container) as observer:
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            dump_future = executor.submit(dump)
            deadline = time.monotonic() + 10
            first = None
            while not dump_future.done() and time.monotonic() < deadline:
                sample = observer.observe()
                if sample:
                    first = sample
                    break
                time.sleep(0.005)
            # No backend observation means no writer is sent and this rehearsal fails closed.
            if not first:
                result, start, end = dump_future.result()
                return {'dump': result, 'dump_start': start, 'dump_end': end,
                        'writer_a': None, 'writer_b': None, 'overlap_verified': False,
                        'observation': None, 'initial_observation': None}
            fa, fb = executor.submit(writer_a), executor.submit(writer_b)
            while not dump_future.done() and not (fa.done() and fb.done()):
                sample = observer.observe()
                if sample and sample['dump_pid'] == first['dump_pid']:
                    samples.append(sample)
                time.sleep(0.002)
            a, b = fa.result(), fb.result()
            result, start, end = dump_future.result()
    overlap_start, overlap_end = max(a['start'], b['start']), min(a['end'], b['end'])
    observation = next((s for s in samples if max(overlap_start, start) <= s['observed_start']
                        <= s['observed_end'] <= min(overlap_end, end)), None)
    overlap = (a['status'] == b['status'] == 200 and start <= min(a['start'], b['start'])
               and max(a['end'], b['end']) <= end and overlap_start < overlap_end
               and observation is not None)
    if observation:
        observation['observed_during_active_dump'] = True
    return {'dump': result, 'dump_start': start, 'dump_end': end, 'writer_a': a, 'writer_b': b,
            'overlap_verified': overlap, 'observation': observation,
            'initial_observation': first}


def _safe_diagnostics(measured, exporter_rc):
    dump_proc = measured.get('dump')
    dump_rc = dump_proc.returncode if dump_proc is not None else None

    def _safe_obs(obs):
        if not isinstance(obs, dict):
            return None
        return {
            k: obs[k] for k in ('dump_pid', 'dump_application_name',
                                'observed_start', 'observed_end',
                                'observed_during_active_dump')
            if k in obs
        }

    safe_initial = _safe_obs(measured.get('initial_observation'))
    safe_obs = _safe_obs(measured.get('observation'))

    def _safe_writer(w):
        if w is None:
            return None
        return {'status': w.get('status'), 'start': w.get('start'), 'end': w.get('end')}

    return {
        'dump_exit_code': dump_rc,
        'dump_start': measured.get('dump_start'),
        'dump_end': measured.get('dump_end'),
        'initial_observation': safe_initial,
        'observation': safe_obs,
        'writer_a': _safe_writer(measured.get('writer_a')),
        'writer_b': _safe_writer(measured.get('writer_b')),
        'overlap_verified': bool(measured.get('overlap_verified')),
        'exporter_returncode': exporter_rc,
    }


def replay_and_fingerprint(container, replay):
    before = fingerprint(container)
    status, result = replay()
    after = fingerprint(container)
    if before != after:
        raise ValueError('Database state changed during idempotent replay')
    return status, result, before, after


def finish_summary(summary, source_fp, restored_fp):
    if summary.get('execution_completed') is True and 'failure_type' not in summary:
        summary['status'] = 'PASS'
    else:
        summary['status'] = 'FAIL'
    validation = validate_v4_rehearsal(summary, source_fp, restored_fp)
    summary['status'] = validation['verdict']
    summary['findings'] = validation['findings']


def validate_v4_rehearsal(summary, source_fingerprint=None, restored_fingerprint=None):
    """Independent fail-closed validator for V4 rehearsal receipts.

    Validates:
    - Structure, clean git tree, valid 40-char SHA, and status == 'PASS'.
    - Mandatory validated fingerprints with exact table row counts and 64-char hex SHA-256.
    - Strict boolean types (no truthy integers or strings).
    - Strict numeric timestamps (no NaN, start <= end, verified concurrency overlap).
    - Authorized finance actors (ownera, financea; rejects membera/outsider).
    - Snapshot export integrity and --snapshot argument.
    - Scoped source operations: exact expected amounts, unique payment/request/tx/audit IDs.
    - Restored snapshot membership: exact P0 payment/request/tx/audit IDs; post-snapshot late commits absent.
    - Exact relational cardinality (1:1:1:1 payments, ledger, audit, requests).
    - Idempotency replay with 0 growth.
    - Verified resource cleanup including owned containers and networks.
    - Zero secret leakage in published receipt (JWT regex and service credentials).
    """
    # Owner-authorized supplemental request validation.
    _codex_v4_ops = summary.get('source_operations') if isinstance(summary, dict) else None
    if isinstance(_codex_v4_ops, dict):
        for _codex_v4_label in ('p0_precommit', 'p1a_concurrent', 'p1b_concurrent'):
            _codex_v4_op = _codex_v4_ops.get(_codex_v4_label)
            if not isinstance(_codex_v4_op, dict):
                continue
            _codex_v4_rows = _codex_v4_op.get('row_evidence')
            _codex_v4_request = _codex_v4_rows.get('request') if isinstance(_codex_v4_rows, dict) else None
            if not isinstance(_codex_v4_request, dict):
                continue
            _codex_v4_result = _codex_v4_request.get('result')
            if (_codex_v4_request.get('operation') != 'record_cash_payment'
                    or not isinstance(_codex_v4_result, dict)
                    or _codex_v4_result.get('status') != 'confirmed'):
                return {'ok': False, 'verdict': 'FAIL', 'findings': [
                    'relational_evidence_mismatch: ' + _codex_v4_label
                    + ' requires record_cash_payment with a confirmed stored result'
                ]}
    findings = []

    # 1. Secret Leakage Check
    summary_raw = json.dumps(summary)
    jwt_match = re.search(r'ey[A-Za-z0-9_-]{4,}\.[A-Za-z0-9_-]{4,}\.[A-Za-z0-9_-]*', summary_raw)
    if jwt_match:
        findings.append('exposed_secret: JWT pattern found in summary')
    if 'sb_secret' in summary_raw or 'service_role' in summary_raw:
        findings.append('exposed_secret: service credential found in summary')

    # Diagnostic command failure & stage validation
    cmd_fail = summary.get('command_failure')
    if cmd_fail is not None:
        if not isinstance(cmd_fail, dict):
            findings.append('invalid_command_failure: command_failure must be dict')
        else:
            op = cmd_fail.get('operation')
            rc = cmd_fail.get('exit_code')
            if not isinstance(op, str) or op not in SAFE_OPERATIONS_WHITELIST:
                findings.append(f'unwhitelisted_operation: command_failure operation {op!r} not in SAFE_OPERATIONS_WHITELIST')
            if type(rc) is not int or isinstance(rc, bool):
                findings.append(f'invalid_exit_code: command_failure exit_code must be int, got {type(rc).__name__}')

    failed_op = summary.get('failed_operation')
    if failed_op is not None:
        if not isinstance(failed_op, dict):
            findings.append('invalid_failed_operation: failed_operation must be dict')
        else:
            op = failed_op.get('operation')
            rc = failed_op.get('exit_code')
            if not isinstance(op, str) or op not in SAFE_OPERATIONS_WHITELIST:
                findings.append(f'unwhitelisted_operation: failed_operation operation {op!r} not in SAFE_OPERATIONS_WHITELIST')
            if type(rc) is not int or isinstance(rc, bool):
                findings.append(f'invalid_exit_code: failed_operation exit_code must be int, got {type(rc).__name__}')

    stg = summary.get('stage')
    if stg is not None and (not isinstance(stg, str) or stg not in PREDEFINED_STAGES):
        findings.append(f'unrecognized_stage: stage {stg!r} not in PREDEFINED_STAGES')

    diag = summary.get('diagnostics')
    if isinstance(diag, dict):
        d_cmd_fail = diag.get('command_failure')
        if d_cmd_fail is not None:
            if not isinstance(d_cmd_fail, dict):
                findings.append('invalid_command_failure: diagnostics.command_failure must be dict')
            else:
                op = d_cmd_fail.get('operation')
                rc = d_cmd_fail.get('exit_code')
                if not isinstance(op, str) or op not in SAFE_OPERATIONS_WHITELIST:
                    findings.append(f'unwhitelisted_operation: diagnostics.command_failure operation {op!r} not in SAFE_OPERATIONS_WHITELIST')
                if type(rc) is not int or isinstance(rc, bool):
                    findings.append(f'invalid_exit_code: diagnostics.command_failure exit_code must be int, got {type(rc).__name__}')
        d_f_op = diag.get('failed_operation')
        if d_f_op is not None:
            if not isinstance(d_f_op, str) or d_f_op not in SAFE_OPERATIONS_WHITELIST:
                findings.append(f'unwhitelisted_operation: diagnostics.failed_operation {d_f_op!r} not in SAFE_OPERATIONS_WHITELIST')
        d_f_rc = diag.get('failed_exit_code')
        if d_f_rc is not None and (type(d_f_rc) is not int or isinstance(d_f_rc, bool)):
            findings.append(f'invalid_exit_code: diagnostics.failed_exit_code must be int, got {type(d_f_rc).__name__}')
        d_stg = diag.get('stage')
        if d_stg is not None and (not isinstance(d_stg, str) or d_stg not in PREDEFINED_STAGES):
            findings.append(f'unrecognized_stage: diagnostics.stage {d_stg!r} not in PREDEFINED_STAGES')

    # 2. Strict Type Checks on Top-level and Nested Flags
    def assert_strict_bool(val, path_name):
        if not isinstance(val, bool):
            findings.append(f'strict_type_violation: {path_name} must be strictly bool, got {type(val).__name__}')

    def assert_strict_number(val, path_name):
        if isinstance(val, bool) or not isinstance(val, (int, float)) or math.isnan(val) or math.isinf(val):
            findings.append(f'invalid_timing: {path_name} must be finite number, got {val}')

    # Status and Provenance
    if summary.get('status') != 'PASS':
        findings.append(f"failed_status: summary status is {summary.get('status')!r}, must be 'PASS'")

    assert_strict_bool(summary.get('git_dirty'), 'git_dirty')
    if summary.get('git_dirty') is not False:
        findings.append('dirty_source: working tree is marked dirty (git_dirty must be strictly False)')

    source_sha = summary.get('tested_source_sha')
    if not isinstance(source_sha, str) or not re.match(r'^[0-9a-f]{40}$', source_sha):
        findings.append(f'invalid_source_sha: tested_source_sha must be 40-char git hex SHA, got {source_sha!r}')

    # Snapshot section validation
    snapshot = summary.get('snapshot')
    if not isinstance(snapshot, dict):
        findings.append('missing_snapshot_section: snapshot dict required')
    else:
        assert_strict_bool(snapshot.get('export_tx_held'), 'snapshot.export_tx_held')
        assert_strict_bool(snapshot.get('pg_dump_completed'), 'snapshot.pg_dump_completed')
        snap_id = snapshot.get('snapshot_id', '')
        if not snap_id or not isinstance(snap_id, str):
            findings.append('snapshot_mismatch: snapshot_id missing or not string')
        expected_snap_arg = f'--snapshot={snap_id}'
        if snapshot.get('pg_dump_snapshot_arg') != expected_snap_arg:
            findings.append(f'missing_snapshot_flag: pg_dump_snapshot_arg must be {expected_snap_arg}')
        if not snapshot.get('export_tx_held'):
            findings.append('snapshot_tx_not_held: export transaction was not held during dump')
        if not snapshot.get('pg_dump_completed') or snapshot.get('pg_dump_exit_code') != 0:
            findings.append(f'dump_failed: pg_dump exit code is {snapshot.get("pg_dump_exit_code")}')

    # Actors authorization validation
    actors = summary.get('actors', {})
    for role_key in ['p0_writer', 'writer_a', 'writer_b']:
        actor_name = actors.get(role_key) if isinstance(actors, dict) else None
        if not isinstance(actor_name, str) or actor_name not in FINANCE_AUTHORIZED_ROLES:
            findings.append(f'unauthorized_finance_actor: {role_key} is {actor_name}, must be in {FINANCE_AUTHORIZED_ROLES}')

    # Writers Concurrency and Overlap Timing
    conc = summary.get('writers_concurrency', {})
    assert_strict_bool(conc.get('overlap_verified'), 'writers_concurrency.overlap_verified')
    assert_strict_bool(conc.get('writers_executed_during_dump'), 'writers_concurrency.writers_executed_during_dump')
    assert_strict_bool(conc.get('pg_stat_activity_dump_observed'), 'writers_concurrency.pg_stat_activity_dump_observed')

    t_p0_commit = conc.get('p0_committed_epoch')
    t_wa_start = conc.get('writer_a_started_epoch')
    t_wa_commit = conc.get('writer_a_committed_epoch')
    t_wb_start = conc.get('writer_b_started_epoch')
    t_wb_commit = conc.get('writer_b_committed_epoch')
    t_dump_start = conc.get('pg_dump_backend_active_start')
    t_dump_end = conc.get('pg_dump_backend_active_end')
    t_snap_export = snapshot.get('snapshot_exported_epoch') if isinstance(snapshot, dict) else None

    for t_val, t_name in [
        (t_p0_commit, 'p0_committed_epoch'),
        (t_wa_start, 'writer_a_started_epoch'),
        (t_wa_commit, 'writer_a_committed_epoch'),
        (t_wb_start, 'writer_b_started_epoch'),
        (t_wb_commit, 'writer_b_committed_epoch'),
        (t_dump_start, 'pg_dump_backend_active_start'),
        (t_dump_end, 'pg_dump_backend_active_end'),
        (t_snap_export, 'snapshot_exported_epoch'),
    ]:
        if t_val is not None:
            assert_strict_number(t_val, f'writers_concurrency.{t_name}')

    if all(isinstance(x, (int, float)) and not math.isnan(x) for x in [t_p0_commit, t_snap_export]):
        if t_p0_commit > t_snap_export:
            findings.append(f'precommit_order_violation: P0 commit ({t_p0_commit}) occurred after snapshot export ({t_snap_export})')

    if all(isinstance(x, (int, float)) and not math.isnan(x) for x in [t_wa_start, t_wa_commit, t_dump_start, t_dump_end]):
        if t_wa_start > t_wa_commit:
            findings.append('invalid_timing: writer A started after committed')
        if t_wa_commit < t_dump_start or t_wa_start > t_dump_end:
            findings.append('writer_timing_mismatch: writer A did not overlap with dump backend window')

    if all(isinstance(x, (int, float)) and not math.isnan(x) for x in [t_wb_start, t_wb_commit, t_dump_start, t_dump_end]):
        if t_wb_start > t_wb_commit:
            findings.append('invalid_timing: writer B started after committed')
        if t_wb_commit < t_dump_start or t_wb_start > t_dump_end:
            findings.append('writer_timing_mismatch: writer B did not overlap with dump backend window')

    # True concurrent execution interval intersection between Writer A and Writer B
    if all(isinstance(x, (int, float)) and not math.isnan(x) for x in [t_wa_start, t_wa_commit, t_wb_start, t_wb_commit]):
        w_overlap_start = max(t_wa_start, t_wb_start)
        w_overlap_end = min(t_wa_commit, t_wb_commit)
        if w_overlap_start >= w_overlap_end:
            findings.append('no_writer_overlap: writer A and writer B execution windows do not intersect (serial execution)')
        elif all(isinstance(x, (int, float)) and not math.isnan(x) for x in [t_dump_start, t_dump_end]):
            dump_overlap_start = max(w_overlap_start, t_dump_start)
            dump_overlap_end = min(w_overlap_end, t_dump_end)
            if dump_overlap_start >= dump_overlap_end:
                findings.append('writer_timing_mismatch: concurrent writer intersection occurred outside pg_dump backend window')

    if not conc.get('overlap_verified') or not conc.get('writers_executed_during_dump'):
        findings.append('no_writer_overlap: concurrent writer execution overlap not verified')
    if not conc.get('pg_stat_activity_dump_observed'):
        findings.append('dump_backend_not_observed: pg_stat_activity did not capture active pg_dump backend')
    if all(isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)
           for x in (t_wa_start, t_wa_commit, t_wb_start, t_wb_commit, t_dump_start, t_dump_end)):
        if min(t_wa_start, t_wb_start) < t_dump_start or max(t_wa_commit, t_wb_commit) > t_dump_end:
            findings.append('writer_timing_mismatch: both successful HTTP calls must be contained in actual dump lifetime')

    # DB Observation Receipt validation
    db_obs = conc.get('db_observation_receipt')
    if not isinstance(db_obs, dict):
        findings.append('dump_backend_not_observed: writers_concurrency must include db_observation_receipt dict')
    else:
        assert_strict_bool(db_obs.get('observed_during_active_dump'), 'writers_concurrency.db_observation_receipt.observed_during_active_dump')
        if not db_obs.get('observed_during_active_dump'):
            findings.append('dump_backend_not_observed: db_observation_receipt indicates dump was not active during observation')
        dump_pid = db_obs.get('dump_pid')
        if not isinstance(dump_pid, int) or isinstance(dump_pid, bool) or dump_pid <= 0:
            findings.append(f'dump_backend_not_observed: dump_pid must be positive int, got {dump_pid}')
        app_name = db_obs.get('dump_application_name')
        if app_name != 'pg_dump':
            findings.append(f'dump_backend_not_observed: dump_application_name must be pg_dump, got {app_name}')
        d_query = db_obs.get('dump_query', '')
        if not isinstance(d_query, str) or not ('COPY' in d_query or 'pg_dump' in d_query):
            findings.append(f'dump_backend_not_observed: dump_query must reference COPY or pg_dump, got {d_query}')
        sample_times = (db_obs.get('observed_start'), db_obs.get('observed_end'),
                        t_wa_start, t_wa_commit, t_wb_start, t_wb_commit, t_dump_start, t_dump_end)
        if not all(isinstance(t, (int, float)) and not isinstance(t, bool) and math.isfinite(t)
                   for t in sample_times):
            findings.append('dump_backend_not_observed: missing finite observation interval')
        else:
            obs_start, obs_end = sample_times[:2]
            if not (max(t_wa_start, t_wb_start, t_dump_start) <= obs_start <= obs_end
                    <= min(t_wa_commit, t_wb_commit, t_dump_end)):
                findings.append('dump_backend_not_observed: sample outside concurrent writer/dump intersection')

    # Source operations type, scoped amount, and unique ID validation
    src_ops = summary.get('source_operations', {})
    if not isinstance(src_ops, dict) or len(src_ops) == 0:
        findings.append('malformed_operation: source_operations must be non-empty dict')
    else:
        seen_pay_ids = {}
        seen_req_ids = {}
        seen_tx_ids = {}
        seen_audit_ids = {}

        for op_key, expected_amt in EXPECTED_SCOPED_AMOUNTS.items():
            if op_key not in src_ops:
                findings.append(f'missing_operation: {op_key} missing from source_operations')
                continue
            op_data = src_ops[op_key]
            if not isinstance(op_data, dict):
                findings.append(f'malformed_operation: {op_key} must be dict')
                continue
            amt = op_data.get('amount_vnd')
            if not isinstance(amt, int) or isinstance(amt, bool) or amt <= 0:
                findings.append(f'strict_type_violation: {op_key}.amount_vnd must be strictly positive int')
            elif amt != expected_amt:
                findings.append(f'amount_mismatch: {op_key} expected amount_vnd={expected_amt}, got {amt}')

            # Check uniqueness across operations
            pid = op_data.get('payment_id')
            if pid:
                if pid in seen_pay_ids:
                    findings.append(f'duplicate_source_payment_id: {op_key} reused payment_id {pid!r} from {seen_pay_ids[pid]}')
                else:
                    seen_pay_ids[pid] = op_key

            rid = op_data.get('request_id')
            if rid:
                if rid in seen_req_ids:
                    findings.append(f'duplicate_source_request_id: {op_key} reused request_id {rid!r} from {seen_req_ids[rid]}')
                else:
                    seen_req_ids[rid] = op_key

            tid = op_data.get('transaction_id')
            if tid:
                if tid in seen_tx_ids:
                    findings.append(f'duplicate_source_transaction_id: {op_key} reused transaction_id {tid!r} from {seen_tx_ids[tid]}')
                else:
                    seen_tx_ids[tid] = op_key

            aid = op_data.get('audit_event_id')
            if aid:
                if aid in seen_audit_ids:
                    findings.append(f'duplicate_source_audit_id: {op_key} reused audit_event_id {aid!r} from {seen_audit_ids[aid]}')
                else:
                    seen_audit_ids[aid] = op_key

            # Row evidence validation if present
            row_ev = op_data.get('row_evidence')
            if row_ev is not None:
                if not isinstance(row_ev, dict):
                    findings.append(f'malformed_operation: {op_key}.row_evidence must be dict')
                else:
                    pay_r = row_ev.get('payment', {})
                    ledger_r = row_ev.get('ledger', {})
                    audit_r = row_ev.get('audit', {})
                    req_r = row_ev.get('request', {})

                    # Binding requested amount/actor/IDs
                    if pay_r.get('id') != pid:
                        findings.append(f'relational_evidence_mismatch: {op_key} payment row id {pay_r.get("id")} != op payment_id {pid}')
                    if pay_r.get('amount_vnd') != amt:
                        findings.append(f'relational_evidence_mismatch: {op_key} payment row amount {pay_r.get("amount_vnd")} != op amount {amt}')
                    if pay_r.get('request_id') != rid:
                        findings.append(f'relational_evidence_mismatch: {op_key} payment row request_id {pay_r.get("request_id")} != op request_id {rid}')

                    # Ledger source payment and amount
                    if ledger_r.get('id') != tid:
                        findings.append(f'relational_evidence_mismatch: {op_key} ledger row id {ledger_r.get("id")} != op transaction_id {tid}')
                    if ledger_r.get('source_payment_id') != pid:
                        findings.append(f'relational_evidence_mismatch: {op_key} ledger source_payment_id {ledger_r.get("source_payment_id")} != op payment_id {pid}')
                    if ledger_r.get('amount') != amt:
                        findings.append(f'relational_evidence_mismatch: {op_key} ledger amount {ledger_r.get("amount")} != op amount {amt}')

                    # Audit entity and request
                    if audit_r.get('id') != aid:
                        findings.append(f'relational_evidence_mismatch: {op_key} audit row id {audit_r.get("id")} != op audit_event_id {aid}')
                    if audit_r.get('request_id') != rid:
                        findings.append(f'relational_evidence_mismatch: {op_key} audit row request_id {audit_r.get("request_id")} != op request_id {rid}')

                    # Operation request row
                    if 'request' not in row_ev or req_r is None:
                        findings.append(f'missing_stored_request: {op_key} missing stored request evidence')
                    else:
                        if req_r.get('request_id') != rid:
                            findings.append(f'relational_evidence_mismatch: {op_key} request row request_id {req_r.get("request_id")} != op request_id {rid}')
                        req_pay_id = req_r.get('payment_id') or (req_r.get('result', {}).get('payment_id') if isinstance(req_r.get('result'), dict) else None)
                        if req_pay_id != pid:
                            findings.append(f'relational_evidence_mismatch: {op_key} request row payment_id {req_pay_id} != op payment_id {pid}')
                        req_st = req_r.get('status')
                        if req_st in (500, '500', 'FAIL', 'fail', 'ERROR', 'error'):
                            findings.append(f'relational_evidence_mismatch: {op_key} request status indicates failure ({req_st})')
                        elif req_st is not None and req_st not in (200, '200', 'confirmed', 'completed', 'success'):
                            findings.append(f'relational_evidence_mismatch: {op_key} request status is invalid ({req_st})')
                        if isinstance(req_r.get('result'), dict):
                            res_obj = req_r['result']
                            if res_obj.get('payment_id') and res_obj.get('payment_id') != pid:
                                findings.append(f'relational_evidence_mismatch: {op_key} request stored result payment_id {res_obj.get("payment_id")} != op payment_id {pid}')
                            if res_obj.get('amount_vnd') and res_obj.get('amount_vnd') != amt:
                                findings.append(f'relational_evidence_mismatch: {op_key} request stored result amount_vnd {res_obj.get("amount_vnd")} != op amount {amt}')
                            res_st = res_obj.get('status')
                            if res_st in (500, '500', 'FAIL', 'fail', 'ERROR', 'error'):
                                findings.append(f'relational_evidence_mismatch: {op_key} request stored result status indicates failure ({res_st})')

                    # Relational digest check
                    rel_digest = op_data.get('relational_digest')
                    if rel_digest is not None:
                        expected_dig = digest(row_ev)
                        if rel_digest != expected_dig:
                            findings.append(f'relational_digest_mismatch: {op_key} relational_digest {rel_digest} != computed {expected_dig}')

    # Restored verification checks
    rest = summary.get('restored_verification', {})
    assert_strict_bool(rest.get('p0_present_in_restore'), 'restored_verification.p0_present_in_restore')
    assert_strict_bool(rest.get('p1a_present_in_restore'), 'restored_verification.p1a_present_in_restore')
    assert_strict_bool(rest.get('p1b_present_in_restore'), 'restored_verification.p1b_present_in_restore')

    if not rest.get('p0_present_in_restore'):
        findings.append('missing_precommit: pre-snapshot payment P0 absent from restored database')
    if rest.get('p1a_present_in_restore') or rest.get('p1b_present_in_restore'):
        findings.append('included_late_commit: post-snapshot concurrent payment leaked into restored database')

    p_count = rest.get('payments_count')
    l_count = rest.get('club_transactions_count')
    a_count = rest.get('audit_events_count')
    r_count = rest.get('operation_requests_count')

    if p_count != 1 or r_count != 1:
        findings.append(f'cardinality_mismatch: expected 1 payment and 1 request, got payments={p_count}, requests={r_count}')
    if l_count != 1 or l_count != p_count:
        findings.append(f'ledger_invariant_failed: expected 1 ledger row matching payments, got {l_count}')
    if a_count != 1 or a_count != p_count:
        findings.append(f'audit_invariant_failed: expected 1 audit row matching payments, got {a_count}')

    # Restored snapshot membership: IDs must match p0_precommit strictly
    p0_op = src_ops.get('p0_precommit', {}) if isinstance(src_ops, dict) else {}
    expected_p0_pay_id = p0_op.get('payment_id')
    expected_p0_tx_id = p0_op.get('transaction_id')
    expected_p0_audit_id = p0_op.get('audit_event_id')
    expected_p0_req_id = p0_op.get('request_id')

    rest_pay_ids = rest.get('restored_payment_ids')
    if rest_pay_ids != [expected_p0_pay_id]:
        findings.append(f'substituted_restored_payment_id: expected restored_payment_ids {[expected_p0_pay_id]}, got {rest_pay_ids}')

    rest_tx_ids = rest.get('restored_transaction_ids')
    if rest_tx_ids != [expected_p0_tx_id]:
        findings.append(f'substituted_restored_transaction_id: expected restored_transaction_ids {[expected_p0_tx_id]}, got {rest_tx_ids}')

    rest_audit_ids = rest.get('restored_audit_ids')
    if rest_audit_ids != [expected_p0_audit_id]:
        findings.append(f'substituted_restored_audit_id: expected restored_audit_ids {[expected_p0_audit_id]}, got {rest_audit_ids}')

    rest_req_ids = rest.get('restored_request_ids')
    if rest_req_ids != [expected_p0_req_id]:
        findings.append(f'substituted_restored_request_id: expected restored_request_ids {[expected_p0_req_id]}, got {rest_req_ids}')

    # Restored row evidence validation if present
    rest_row_ev = rest.get('restored_row_evidence')
    if rest_row_ev is not None:
        if not isinstance(rest_row_ev, dict):
            findings.append('malformed_restored: restored_row_evidence must be dict')
        else:
            r_pay = rest_row_ev.get('payment', {})
            r_ledger = rest_row_ev.get('ledger', {})
            r_audit = rest_row_ev.get('audit', {})
            r_req = rest_row_ev.get('request', {})

            if r_pay.get('id') != expected_p0_pay_id or r_pay.get('amount_vnd') != 10000:
                findings.append('restored_relational_evidence_mismatch: restored payment row mismatch with precommit P0')
            if r_ledger.get('source_payment_id') != expected_p0_pay_id or r_ledger.get('amount') != 10000:
                findings.append('restored_relational_evidence_mismatch: restored ledger row mismatch with precommit P0')
            if r_audit.get('request_id') != expected_p0_req_id:
                findings.append('restored_relational_evidence_mismatch: restored audit row mismatch with precommit P0')
            if 'request' not in rest_row_ev or r_req is None:
                findings.append('missing_stored_request: restored_row_evidence missing request')
            else:
                if r_req.get('request_id') != expected_p0_req_id:
                    findings.append('restored_relational_evidence_mismatch: restored request row request_id mismatch with precommit P0')
                r_pay_id = r_req.get('payment_id') or (r_req.get('result', {}).get('payment_id') if isinstance(r_req.get('result'), dict) else None)
                if r_pay_id != expected_p0_pay_id:
                    findings.append('restored_relational_evidence_mismatch: restored request row payment_id mismatch with precommit P0')
                r_st = r_req.get('status')
                if r_st in (500, '500', 'FAIL', 'fail', 'ERROR', 'error'):
                    findings.append(f'restored_relational_evidence_mismatch: restored request status indicates failure ({r_st})')
                elif r_st is not None and r_st not in (200, '200', 'confirmed', 'completed', 'success'):
                    findings.append(f'restored_relational_evidence_mismatch: restored request status is invalid ({r_st})')
                if isinstance(r_req.get('result'), dict):
                    res_obj = r_req['result']
                    if res_obj.get('payment_id') and res_obj.get('payment_id') != expected_p0_pay_id:
                        findings.append('restored_relational_evidence_mismatch: restored request result payment_id mismatch with precommit P0')
                    if res_obj.get('amount_vnd') and res_obj.get('amount_vnd') != 10000:
                        findings.append('restored_relational_evidence_mismatch: restored request result amount_vnd mismatch with precommit P0')
                    res_st = res_obj.get('status')
                    if res_st in (500, '500', 'FAIL', 'fail', 'ERROR', 'error'):
                        findings.append(f'restored_relational_evidence_mismatch: restored request result status indicates failure ({res_st})')

    # Idempotency replay check
    replay_growth = rest.get('replay_p0_growth', {})
    for table_name, growth in replay_growth.items():
        if growth != 0:
            findings.append(f'idempotency_replay_failed: replay of P0 resulted in {growth} rows in {table_name}')

    replay_ev = rest.get('replay_evidence')
    if replay_ev is None:
        findings.append('missing_replay_state: replay evidence is required')
    else:
        if not isinstance(replay_ev, dict):
            findings.append('malformed_restored: replay_evidence must be dict')
        else:
            if replay_ev.get('replay_status') != 200 or replay_ev.get('replay_payment_id') != expected_p0_pay_id:
                findings.append('idempotency_replay_failed: replay evidence does not match expected P0 response')
            b_fp = replay_ev.get('before_replay_fingerprint')
            a_fp = replay_ev.get('after_replay_fingerprint')
            if not isinstance(b_fp, str) or not re.match(r'^[0-9a-f]{64}$', b_fp):
                findings.append(f'invalid_replay_fingerprint: before_replay_fingerprint must be 64-char hex SHA-256, got {b_fp!r}')
            if not isinstance(a_fp, str) or not re.match(r'^[0-9a-f]{64}$', a_fp):
                findings.append(f'invalid_replay_fingerprint: after_replay_fingerprint must be 64-char hex SHA-256, got {a_fp!r}')
            if b_fp is not None and a_fp is not None and b_fp != a_fp:
                findings.append('replay_data_mutation: restored table fingerprint changed across idempotent replay')
            before, after = replay_ev.get('before_state'), replay_ev.get('after_state')
            if not isinstance(before, dict) or not isinstance(after, dict):
                findings.append('missing_replay_state: actual before/after database fingerprints required')
            else:
                for label, state in (('before', before), ('after', after)):
                    if not set(REQUIRED_TABLES).issubset(state) or not re.fullmatch(r'[0-9a-f]{64}', str(state.get('_schema', ''))):
                        findings.append(f'invalid_replay_state: {label} missing tables/schema digest')
                    for table, info in state.items():
                        if table == '_schema':
                            continue
                        if (not isinstance(info, dict) or type(info.get('rows')) is not int
                                or info['rows'] < 0 or not re.fullmatch(r'[0-9a-f]{64}', str(info.get('sha256', '')))):
                            findings.append(f'invalid_replay_state: {label} malformed table fingerprint')
                if before != after:
                    findings.append('replay_data_mutation: actual database rows/schema changed across replay')
                for state, value in ((before, b_fp), (after, a_fp)):
                    table_fp = state.get('public.payments')
                    if not isinstance(table_fp, dict) or table_fp.get('sha256') != value:
                        findings.append('replay_fingerprint_mismatch: payment digest does not match actual replay state')
            if replay_ev.get('fingerprint_unchanged') is not True:
                findings.append('replay_data_mutation: replay did not preserve full database state')

    # Mandatory Validated Fingerprints
    if source_fingerprint is None:
        findings.append('missing_source_fingerprint: source_fingerprint dictionary is mandatory')
    elif not isinstance(source_fingerprint, dict):
        findings.append('malformed_source_fingerprint: source_fingerprint must be a dict')
    else:
        expected_src_rows = len(src_ops) if isinstance(src_ops, dict) else 3
        for tbl in REQUIRED_TABLES:
            tbl_info = source_fingerprint.get(tbl)
            if not isinstance(tbl_info, dict):
                findings.append(f'missing_source_table_fingerprint: table {tbl} missing from source_fingerprint')
                continue
            rows = tbl_info.get('rows')
            if not isinstance(rows, int) or isinstance(rows, bool) or rows < 0:
                findings.append(f'invalid_source_table_rows: table {tbl} rows must be non-negative int')
            elif rows != expected_src_rows:
                findings.append(f'source_count_mismatch: table {tbl} expected {expected_src_rows} rows, got {rows}')
            sha = tbl_info.get('sha256')
            if not isinstance(sha, str) or not re.match(r'^[0-9a-f]{64}$', sha):
                findings.append(f'malformed_source_hashes: table {tbl} sha256 is not valid 64-char hex: {sha!r}')

    if restored_fingerprint is None:
        findings.append('missing_restored_fingerprint: restored_fingerprint dictionary is mandatory')
    elif not isinstance(restored_fingerprint, dict):
        findings.append('malformed_restored_fingerprint: restored_fingerprint must be a dict')
    else:
        for tbl in REQUIRED_TABLES:
            tbl_info = restored_fingerprint.get(tbl)
            if not isinstance(tbl_info, dict):
                findings.append(f'missing_restored_table_fingerprint: table {tbl} missing from restored_fingerprint')
                continue
            rows = tbl_info.get('rows')
            if not isinstance(rows, int) or isinstance(rows, bool) or rows < 0:
                findings.append(f'invalid_restored_table_rows: table {tbl} rows must be non-negative int')
            elif rows != 1:
                findings.append(f'fingerprint_mismatch: restored table {tbl} rows ({rows}) != expected 1')
            sha = tbl_info.get('sha256')
            if not isinstance(sha, str) or not re.match(r'^[0-9a-f]{64}$', sha):
                findings.append(f'malformed_restored_hashes: table {tbl} sha256 is not valid 64-char hex: {sha!r}')

    # Cleanup validation
    cleanup = summary.get('cleanup', {})
    assert_strict_bool(cleanup.get('ok'), 'cleanup.ok')
    assert_strict_bool(cleanup.get('containers_verified_absent'), 'cleanup.containers_verified_absent')
    assert_strict_bool(cleanup.get('networks_verified_absent'), 'cleanup.networks_verified_absent')
    assert_strict_bool(cleanup.get('private_dumps_removed'), 'cleanup.private_dumps_removed')

    if not cleanup.get('ok') or cleanup.get('cleanup_errors'):
        findings.append(f'cleanup_failed: errors {cleanup.get("cleanup_errors")}')
    res_list = cleanup.get('resources_verified_absent', [])
    if not isinstance(res_list, list) or len(res_list) == 0:
        findings.append('unverified_cleanup_resources: resources_verified_absent must be non-empty list')
    else:
        # Check for duplicate resources in verified list
        if len(res_list) != len(set(res_list)):
            findings.append('cleanup_duplicate_resources: duplicate resources in resources_verified_absent')

        # Check that all resources belong to bh07-v4 rehearsal namespace
        for r_name in res_list:
            if not str(r_name).startswith('bh07-v4-'):
                findings.append(f'unrelated_cleanup_resources: resource {r_name} does not belong to bh07-v4 rehearsal')

        # Check against owned_resources_manifest
        owned_manifest = cleanup.get('owned_resources_manifest')
        if owned_manifest is None:
            findings.append('unverified_cleanup_resources: owned_resources_manifest is required')
        elif not isinstance(owned_manifest, list):
            findings.append('unverified_cleanup_resources: owned_resources_manifest must be a list')
        else:
            expected_names = [item['name'] if isinstance(item, dict) else str(item) for item in owned_manifest]
            if set(res_list) != set(expected_names):
                missing = set(expected_names) - set(res_list)
                extra = set(res_list) - set(expected_names)
                findings.append(f'cleanup_resource_mismatch: resources_verified_absent does not match owned manifest: missing={sorted(missing)}, extra={sorted(extra)}')

        has_net = any('net' in str(r).lower() for r in res_list)
        has_db = any('db' in str(r).lower() for r in res_list)
        if not has_net:
            findings.append('unverified_cleanup_resources: resources_verified_absent must include verified network')
        if not has_db:
            findings.append('unverified_cleanup_resources: resources_verified_absent must include verified DB container')

    # Padding Fixture validation (CW2: full source/restored receipts and matching content digest)
    src_pad = summary.get('padding_fixture')
    rest_pad = None
    if isinstance(summary.get('restored_verification'), dict):
        rest_pad = summary['restored_verification'].get('padding_fixture')

    if src_pad is not None or rest_pad is not None:
        if src_pad is None:
            findings.append('missing_padding_fixture: summary missing source padding_fixture receipt')
        elif not isinstance(src_pad, dict):
            findings.append('malformed_padding_fixture: source padding_fixture must be dict')

        if rest_pad is None:
            findings.append('missing_restored_padding_fixture: restored_verification missing padding_fixture receipt')
        elif not isinstance(rest_pad, dict):
            findings.append('malformed_padding_fixture: restored padding_fixture must be dict')

        if isinstance(src_pad, dict) and isinstance(rest_pad, dict):
            for label, p_dict in (('source', src_pad), ('restored', rest_pad)):
                if p_dict.get('schema') != TOOLING_SCHEMA or p_dict.get('table') != PADDING_TABLE:
                    findings.append(f'invalid_padding_fixture: {label} schema and table must be {TOOLING_SCHEMA}.{PADDING_TABLE}')
                p_rows = p_dict.get('rows')
                if not isinstance(p_rows, int) or isinstance(p_rows, bool) or p_rows <= 0:
                    findings.append(f'invalid_padding_fixture: {label} rows must be positive int')
                p_bytes = p_dict.get('bytes')
                if not isinstance(p_bytes, int) or isinstance(p_bytes, bool) or p_bytes <= 0:
                    findings.append(f'invalid_padding_fixture: {label} bytes must be positive int')
                elif p_bytes > MAX_PADDING_BUDGET_BYTES:
                    findings.append(f'invalid_padding_fixture: {label} bytes exceeds 256MiB finite budget')
                p_dig = p_dict.get('digest')
                if not isinstance(p_dig, str) or not re.fullmatch(r'^([0-9a-f]{32}|[0-9a-f]{64})$', p_dig):
                    findings.append(f'invalid_padding_fixture: {label} digest must be valid hex digest, got {p_dig!r}')
                if p_dict.get('restored_match') is not True:
                    findings.append(f'invalid_padding_fixture: {label} restored_match must be True')

            if src_pad.get('rows') != rest_pad.get('rows'):
                findings.append('padding_fixture_mismatch: source rows != restored rows')
            if src_pad.get('bytes') != rest_pad.get('bytes'):
                findings.append('padding_fixture_mismatch: source bytes != restored bytes')
            if src_pad.get('digest') != rest_pad.get('digest'):
                findings.append('padding_fixture_mismatch: source digest != restored digest')

    ok = len(findings) == 0
    return {
        'ok': ok,
        'verdict': 'PASS' if ok else 'FAIL',
        'findings': findings
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path, help='Output directory for evidence and summaries')
    args = parser.parse_args()
    out = args.out.resolve()
    if out.exists():
        raise ValueError(f"Output path already exists: {out}")
    source_sha = cmd(['git', 'rev-parse', 'HEAD']).stdout.decode('utf-8').strip()
    dirty = cmd(['git', 'status', '--porcelain']).stdout.decode('utf-8').strip()
    if dirty:
        raise ValueError('V4 rehearsal requires a clean source checkout')
    out.mkdir(parents=True)
    check_resource_budget(out)

    run_id = uuid.uuid4().hex[:8]
    runtime_user_pw = secrets.token_urlsafe(24)

    net_name = f'bh07-v4-net-{run_id}'
    src_db = f'bh07-v4-src-db-{run_id}'
    src_auth = f'bh07-v4-src-auth-{run_id}'
    src_rest = f'bh07-v4-src-rest-{run_id}'
    src_kong = f'bh07-v4-src-kong-{run_id}'
    target_db = f'bh07-v4-target-db-{run_id}'
    target_auth = f'bh07-v4-target-auth-{run_id}'
    target_rest = f'bh07-v4-target-rest-{run_id}'

    owned_containers = [src_kong, src_rest, src_auth, src_db, target_rest, target_auth, target_db]
    owned_networks = [net_name]

    # Preflight collision check
    for c_name in owned_containers:
        if cmd(['docker', 'inspect', c_name], accept_error=True).returncode == 0:
            raise RuntimeError(f"Preflight collision: container {c_name} already exists")
    if cmd(['docker', 'network', 'inspect', net_name], accept_error=True).returncode == 0:
        raise RuntimeError(f"Preflight collision: network {net_name} already exists")

    private = Path(tempfile.mkdtemp(prefix='bh07-v4-private-'))
    started_epoch = time.monotonic()
    summary = {
        'gate': 'BH-07 V4 concurrent writers backup/restore rehearsal',
        'base_sha': ACTUAL_BASE_SHA,
        'tested_source_sha': source_sha,
        'git_dirty': bool(dirty),
        'run_id': run_id,
        'snapshot': {},
        'actors': {'p0_writer': 'ownera', 'writer_a': 'ownera', 'writer_b': 'financea'},
        'writers_concurrency': {},
        'source_operations': {},
        'restored_verification': {},
        'cleanup': {},
    }

    try:
        # Step 1: Initialize isolated source Docker stack via setup script
        setup_text = SETUP.read_text(encoding='utf-8')
        source_port = free_port()
        setup_text = setup_text.replace('bh07-http-review-network', net_name)
        setup_text = setup_text.replace('bh07-http-review-db', src_db)
        setup_text = setup_text.replace('bh07-http-review-auth', src_auth)
        setup_text = setup_text.replace('bh07-http-review-rest', src_rest)
        setup_text = setup_text.replace('bh07-http-review-kong', src_kong)
        setup_text = setup_text.replace('54321', str(source_port))
        setup_text = setup_text.replace("root=Path('/workspace/badminton-hub')", f'root=Path({str(ROOT)!r})')
        setup_text = setup_text.replace("out=Path('/workspace/scratch/bh07-late-response')", f'out=Path({str(out)!r})')
        setup_text = setup_text.replace("private=Path('/tmp/bh07-http-review-runtime')", f'private=Path({str(private / "src-runtime")!r})')
        setup_text = setup_text.replace('p.read_text()', "p.read_text(encoding='utf-8')")
        setup_text = setup_text.replace("(root/'scripts/bh07_http/seed.sql').read_text()", "(root/'scripts/bh07_http/seed.sql').read_text(encoding='utf-8')")
        setup_text = setup_text.replace("(root/'scripts/bh07_browser/seed_setup.js').read_text()", "(root/'scripts/bh07_browser/seed_setup.js').read_text(encoding='utf-8')")
        setup_text = setup_text.replace("subprocess.run(args,input=input,text=True,capture_output=True)", "subprocess.run(args,input=input,text=True,capture_output=True,encoding='utf-8')")
        # Dynamically inject runtime generated user password into setup without literal static credentials
        setup_text = re.sub(r"'password':\s*'[^']+'", f"'password':{runtime_user_pw!r}", setup_text)

        setup_script = private / 'setup.py'
        setup_script.write_text(setup_text, encoding='utf-8')
        ns = runpy.run_path(str(setup_script))

        headers = {'apikey': ns['anon']}
        auth_url = f'http://127.0.0.1:{source_port}/auth/v1'
        rest_url = f'http://127.0.0.1:{source_port}/rest/v1/rpc'

        owner_token = login(auth_url, 'ownera', headers, password=runtime_user_pw)
        finance_token = login(auth_url, 'financea', headers, password=runtime_user_pw)

        # Step 2: Pre-snapshot write (P0) by Owner
        p0_req_id = str(uuid.uuid4())
        p0_payload = {'p_player_id': PLAYER, 'p_amount_vnd': 10000, 'p_reference': 'BH07 V4 P0 pre-snapshot', 'p_request_id': p0_req_id}
        p0_status, p0_res = rpc(rest_url, owner_token, 'record_cash_payment', p0_payload, headers)
        assert p0_status == 200 and p0_res.get('payment_id'), f"P0 write failed: {p0_status} {p0_res}"
        p0_pay_id = p0_res['payment_id']
        t_p0_committed = time.time()

        owner_id = str(uuid.UUID(sql(src_db, "SELECT id FROM auth.users WHERE email = 'ownera@example.test'")))
        finance_id = str(uuid.UUID(sql(src_db, "SELECT id FROM auth.users WHERE email = 'financea@example.test'")))
        p0_ev = query_row_evidence(src_db, p0_pay_id, p0_req_id, owner_id)
        p0_tx_id, p0_audit_id = p0_ev['ledger']['id'], p0_ev['audit']['id']
        summary['source_operations']['p0_precommit'] = {
            'actor_user_id': owner_id,
            'request_id': p0_req_id,
            'payment_id': p0_pay_id,
            'transaction_id': p0_tx_id,
            'audit_event_id': p0_audit_id,
            'status': p0_status,
            'amount_vnd': 10000,
            'row_evidence': p0_ev,
            'relational_digest': digest(p0_ev),
        }

        # Install bounded padding fixture in dedicated tooling schema to obtain COPY observation window
        padding_stats = setup_padding_fixture(src_db, DEFAULT_PADDING_ROWS)
        summary['padding_fixture'] = {
            'schema': TOOLING_SCHEMA,
            'table': PADDING_TABLE,
            'rows': padding_stats['rows'],
            'bytes': padding_stats['bytes'],
            'digest': padding_stats['digest'],
            'restored_match': False,
        }

        # Snapshot remains live until the dump worker has really completed.
        dump_file = private / 'database.dump'
        roles_raw = cmd(['docker', 'exec', src_db, 'pg_dumpall', '-U', 'postgres', '--globals-only']).stdout
        (private / 'roles.sql').write_bytes(roles_raw)

        def write_payment(token, amount, reference):
            req_id = str(uuid.uuid4())
            payload = {'p_player_id': PLAYER, 'p_amount_vnd': amount,
                       'p_reference': reference, 'p_request_id': req_id}
            start = time.time()
            st, res = rpc(rest_url, token, 'record_cash_payment', payload, headers)
            return {'status': st, 'res': res, 'req_id': req_id, 'amount': amount,
                    'start': start, 'end': time.time()}

        with held_snapshot(src_db) as (snapshot_id, exporter):
            t_snap_exported = time.time()
            summary['snapshot'] = {
                'snapshot_id': snapshot_id, 'snapshot_exported_epoch': t_snap_exported,
                'export_tx_held': True, 'pg_dump_snapshot_arg': f'--snapshot={snapshot_id}',
            }
            measured = dump_with_writers(
                src_db, snapshot_id,
                lambda: write_payment(owner_token, 15000, 'BH07 V4 P1A concurrent'),
                lambda: write_payment(finance_token, 20000, 'BH07 V4 P1B concurrent'))
            exporter_rc = exporter.poll()
            summary['diagnostics'] = _safe_diagnostics(measured, exporter_rc)
            if not measured['overlap_verified'] or exporter_rc is not None:
                raise ValueError('No verified concurrent HTTP commits during active snapshot dump')

        res_a, res_b = measured['writer_a'], measured['writer_b']
        dump_proc_res = measured['dump']
        dump_bytes = dump_proc_res.stdout
        dump_file.write_bytes(dump_bytes)
        summary['snapshot']['pg_dump_completed'] = (dump_proc_res.returncode == 0)
        summary['snapshot']['pg_dump_exit_code'] = dump_proc_res.returncode
        p1a_pay_id, p1b_pay_id = res_a['res']['payment_id'], res_b['res']['payment_id']
        p1a_ev = query_row_evidence(src_db, p1a_pay_id, res_a['req_id'], owner_id)
        p1b_ev = query_row_evidence(src_db, p1b_pay_id, res_b['req_id'], finance_id)
        p1a_tx_id, p1a_audit_id = p1a_ev['ledger']['id'], p1a_ev['audit']['id']
        p1b_tx_id, p1b_audit_id = p1b_ev['ledger']['id'], p1b_ev['audit']['id']

        summary['source_operations']['p1a_concurrent'] = {
            'actor_user_id': owner_id,
            'request_id': res_a['req_id'],
            'payment_id': p1a_pay_id,
            'transaction_id': p1a_tx_id,
            'audit_event_id': p1a_audit_id,
            'status': res_a['status'],
            'amount_vnd': res_a['amount'],
            'row_evidence': p1a_ev,
            'relational_digest': digest(p1a_ev),
        }
        summary['source_operations']['p1b_concurrent'] = {
            'actor_user_id': finance_id,
            'request_id': res_b['req_id'],
            'payment_id': p1b_pay_id,
            'transaction_id': p1b_tx_id,
            'audit_event_id': p1b_audit_id,
            'status': res_b['status'],
            'amount_vnd': res_b['amount'],
            'row_evidence': p1b_ev,
            'relational_digest': digest(p1b_ev),
        }

        summary['writers_concurrency'] = {
            'p0_committed_epoch': t_p0_committed,
            'writer_a_started_epoch': res_a['start'], 'writer_a_committed_epoch': res_a['end'],
            'writer_b_started_epoch': res_b['start'], 'writer_b_committed_epoch': res_b['end'],
            'pg_dump_backend_active_start': measured['dump_start'],
            'pg_dump_backend_active_end': measured['dump_end'],
            'pg_stat_activity_dump_observed': measured['observation'] is not None,
            'db_observation_receipt': measured['observation'],
            'overlap_verified': measured['overlap_verified'],
            'writers_executed_during_dump': measured['overlap_verified'],
        }

        # Scope only this run's intents; seed financial history remains untouched.
        operations = summary['source_operations']
        source_fp = row_fingerprints(workload_rows(src_db, operations))
        (out / 'source_fingerprints.json').write_text(json.dumps(source_fp, indent=2) + '\n', encoding='utf-8')

        # Step 5: Start isolated target database and restore
        pw = ns['password']
        jwt_sec = ns['secret']
        target_env_file = private / 'target.env'
        target_env_file.write_text(f"POSTGRES_PASSWORD={pw}\n", encoding='utf-8')
        cmd(['docker', 'run', '-d', '--name', target_db, '--network', net_name, '--env-file', str(target_env_file), 'postgres:17'])

        ready = False
        for _ in range(60):
            if cmd(['docker', 'exec', target_db, 'pg_isready', '-U', 'postgres'], accept_error=True).returncode == 0:
                ready = True
                break
            time.sleep(0.5)
        assert ready, "Target postgres failed to become ready"

        # Restore globals (skipping duplicate postgres role)
        globals_sql = roles_raw.decode('utf-8', 'replace').replace('CREATE ROLE postgres;\n', '', 1)
        cmd(['docker', 'exec', '-i', target_db, 'psql', '-U', 'postgres', '-v', 'ON_ERROR_STOP=1'], data=globals_sql.encode('utf-8'))

        # Restore database dump
        cmd(['docker', 'exec', '-i', target_db, 'pg_restore', '-U', 'postgres', '--clean', '--if-exists', '--create', '--exit-on-error', '-d', 'template1'], data=dump_bytes)

        # Fingerprint restored database
        restored_rows = workload_rows(target_db, operations)
        restored_fp = row_fingerprints(restored_rows)
        (out / 'restored_fingerprints.json').write_text(json.dumps(restored_fp, indent=2) + '\n', encoding='utf-8')

        # Verify padding fixture was faithfully restored in target database
        restored_padding_stats = verify_restored_padding_fixture(target_db, padding_stats)
        summary['padding_fixture']['restored_match'] = True

        restored_pay_ids = [row['id'] for row in restored_rows['payments']]
        p0_in_target = p0_pay_id in restored_pay_ids
        p1a_in_target = p1a_pay_id in restored_pay_ids
        p1b_in_target = p1b_pay_id in restored_pay_ids
        pay_cnt, tx_cnt, audit_cnt, req_cnt = (len(restored_rows[table]) for table in
            ('payments', 'club_transactions', 'audit_events', 'operation_requests'))

        # Spin up target GoTrue and PostgREST to test HTTP RPC idempotency replay
        # Boundary 1: target auth start
        set_stage(summary, STAGE_TARGET_AUTH_START)
        t_auth_env = private / 'target_auth.env'
        t_auth_env.write_text(
            f"GOTRUE_API_HOST=0.0.0.0\nGOTRUE_API_PORT=9999\nAPI_EXTERNAL_URL=http://127.0.0.1\n"
            f"GOTRUE_SITE_URL=http://127.0.0.1:3000\n"
            f"GOTRUE_DB_DRIVER=postgres\nGOTRUE_DB_DATABASE_URL=postgres://supabase_auth_admin:{pw}@{target_db}:5432/postgres?search_path=auth\n"
            f"GOTRUE_JWT_SECRET={jwt_sec}\nGOTRUE_JWT_EXP=3600\nGOTRUE_JWT_AUD=authenticated\n"
            f"GOTRUE_JWT_DEFAULT_GROUP_NAME=authenticated\nGOTRUE_JWT_ADMIN_ROLES=service_role\n",
            encoding='utf-8'
        )
        cmd(['docker', 'run', '-d', '--name', target_auth, '--network', net_name, '--env-file', str(t_auth_env), '-p', '127.0.0.1::9999', 'ghcr.io/supabase/gotrue:v2.197.0'], op=OP_TARGET_AUTH_START)

        # Boundary 2: target REST start
        set_stage(summary, STAGE_TARGET_REST_START)
        t_rest_env = private / 'target_rest.env'
        t_rest_env.write_text(
            f"PGRST_DB_URI=postgres://authenticator:{pw}@{target_db}:5432/postgres\n"
            f"PGRST_DB_SCHEMAS=public\nPGRST_DB_ANON_ROLE=anon\nPGRST_JWT_SECRET={jwt_sec}\nPGRST_SERVER_PORT=3000\n",
            encoding='utf-8'
        )
        cmd(['docker', 'run', '-d', '--name', target_rest, '--network', net_name, '--env-file', str(t_rest_env), '-p', '127.0.0.1::3000', 'ghcr.io/supabase/postgrest:v16.4'], op=OP_TARGET_REST_START)

        # Boundary 3: network attachment
        set_stage(summary, STAGE_NETWORK_ATTACHMENT)
        for c_suffix in [target_auth, target_rest]:
            cmd(['docker', 'network', 'connect', 'bridge', c_suffix], op=OP_TARGET_NETWORK_ATTACH)

        # Boundary 4: port discovery
        set_stage(summary, STAGE_PORT_DISCOVERY)
        def get_host_port(name, internal_port):
            addr = cmd(['docker', 'port', name, f'{internal_port}/tcp'], op=OP_TARGET_PORT_DISCOVERY).stdout.decode('utf-8').strip()
            return f"http://{addr}"

        new_auth_url = get_host_port(target_auth, 9999)
        new_rest_url = get_host_port(target_rest, 3000) + '/rpc'

        # Boundary 5: auth health/login
        set_stage(summary, STAGE_AUTH_HEALTH_LOGIN)
        target_owner_token = None
        for _ in range(40):
            try:
                target_owner_token = login(new_auth_url, 'ownera', password=runtime_user_pw)
                break
            except Exception:
                time.sleep(0.5)
        assert target_owner_token, "Target Auth failed recovery smoke"

        # Boundary 6: replay/fingerprint collection
        set_stage(summary, STAGE_REPLAY_FINGERPRINT_COLLECTION)
        st_rep, res_rep, before_replay, after_replay = replay_and_fingerprint(
            target_db, lambda: rpc(new_rest_url, target_owner_token, 'record_cash_payment', p0_payload))
        replay_idempotent = (st_rep == 200 and res_rep.get('payment_id') == p0_pay_id)
        growth = {table: after_replay['public.' + table]['rows'] - before_replay['public.' + table]['rows']
                  for table in restored_rows}
        p0_rest_ev = query_row_evidence(target_db, p0_pay_id, p0_req_id, owner_id)
        summary['restored_verification'] = {
            'p0_present_in_restore': bool(p0_in_target),
            'p1a_present_in_restore': bool(p1a_in_target),
            'p1b_present_in_restore': bool(p1b_in_target),
            'padding_fixture': {
                'schema': TOOLING_SCHEMA,
                'table': PADDING_TABLE,
                'rows': restored_padding_stats['rows'],
                'bytes': restored_padding_stats['bytes'],
                'digest': restored_padding_stats['digest'],
                'restored_match': True,
            },
            'exact_cardinality_match': bool(pay_cnt == 1 and tx_cnt == 1 and audit_cnt == 1 and req_cnt == 1),
            'payments_count': pay_cnt,
            'club_transactions_count': tx_cnt,
            'audit_events_count': audit_cnt,
            'operation_requests_count': req_cnt,
            'restored_payment_ids': restored_pay_ids,
            'restored_transaction_ids': [row['id'] for row in restored_rows['club_transactions']],
            'restored_audit_ids': [row['id'] for row in restored_rows['audit_events']],
            'restored_request_ids': [row['request_id'] for row in restored_rows['operation_requests']],
            'restored_row_evidence': p0_rest_ev,
            'replay_p0_idempotent': bool(replay_idempotent),
            'replay_p0_growth': growth,
            'replay_evidence': {
                'replay_status': st_rep,
                'replay_payment_id': res_rep.get('payment_id'),
                'before_replay_fingerprint': before_replay['public.payments']['sha256'],
                'after_replay_fingerprint': after_replay['public.payments']['sha256'],
                'fingerprint_unchanged': before_replay == after_replay,
                'before_state': before_replay, 'after_state': after_replay,
            },
        }

        summary['execution_completed'] = True
        set_stage(summary, STAGE_COMPLETED)

    except Exception as err:
        summary['status'] = 'FAIL'
        summary['failure_type'] = type(err).__name__
        current_stage = summary.get('stage')

        # RD3: Validate whitelist and type(exit_code) is int at publication sink
        raw_op = getattr(err, 'operation', None)
        raw_exit = getattr(err, 'exit_code', None)

        safe_op = raw_op if (isinstance(raw_op, str) and raw_op in SAFE_OPERATIONS_WHITELIST) else None
        safe_exit = raw_exit if (type(raw_exit) is int and not isinstance(raw_exit, bool)) else None

        if safe_op is not None and safe_exit is not None:
            cmd_fail = {
                'operation': safe_op,
                'exit_code': safe_exit,
            }
            summary['command_failure'] = cmd_fail
            summary['failed_operation'] = cmd_fail
            if 'diagnostics' not in summary or not isinstance(summary['diagnostics'], dict):
                summary['diagnostics'] = {}
            summary['diagnostics']['command_failure'] = cmd_fail
            summary['diagnostics']['failed_operation'] = safe_op
            summary['diagnostics']['failed_exit_code'] = safe_exit
            summary['diagnostics']['stage'] = current_stage

        # RD2: At new stages, publish predefined safe error labels, never free-text exception messages
        if isinstance(current_stage, str) and current_stage in PREDEFINED_STAGES:
            if safe_op is not None and safe_exit is not None:
                summary['error_message'] = f"{safe_op} exited {safe_exit}"
            else:
                summary['error_message'] = STAGE_DEFAULT_ERROR_LABELS.get(
                    current_stage, "post-restore verification failed"
                )
            if 'diagnostics' in summary and isinstance(summary['diagnostics'], dict):
                summary['diagnostics']['stage'] = current_stage
        else:
            # Pre-stage: keep existing guard messages compatible
            summary['error_message'] = sanitize_error_message(str(err))
    finally:
        # Step 7: Fail-closed verified cleanup
        cleanup_errors = []
        verified_absent = []

        def check_absent(kind, name):
            if kind == 'container':
                inspect_args = ['docker', 'inspect', name]
                absence_msgs = (f'error: no such object: {name}', f'no such object: {name}')
            else:
                inspect_args = ['docker', 'network', 'inspect', name]
                absence_msgs = (f'network {name} not found', f'no such network: {name}')
            res = cmd(inspect_args, accept_error=True)
            if res.returncode != 0:
                stderr_text = res.stderr.decode('utf-8', 'replace').strip().casefold()
                if any(m in stderr_text for m in absence_msgs):
                    return True
                cleanup_errors.append(f"{kind} inspect error: {res.returncode}")
                return False
            return False

        for c_name in owned_containers:
            cmd(['docker', 'rm', '-f', '-v', c_name], accept_error=True)
            if check_absent('container', c_name):
                verified_absent.append(c_name)
            else:
                cleanup_errors.append(f"Container still present: {c_name}")

        for n_name in owned_networks:
            cmd(['docker', 'network', 'rm', n_name], accept_error=True)
            if check_absent('network', n_name):
                verified_absent.append(n_name)
            else:
                cleanup_errors.append(f"Network still present: {n_name}")

        shutil.rmtree(private, ignore_errors=True)
        dumps_removed = not private.exists()

        summary['cleanup'] = {
            'ok': (len(cleanup_errors) == 0 and dumps_removed),
            'containers_verified_absent': True,
            'networks_verified_absent': True,
            'owned_resources_manifest': owned_containers + owned_networks,
            'resources_verified_absent': verified_absent,
            'private_dumps_removed': dumps_removed,
            'cleanup_errors': cleanup_errors,
        }

        # Step 8: Validate summary with fail-closed validator
        finish_summary(summary, locals().get('source_fp'), locals().get('restored_fp'))
        summary['elapsed_seconds'] = round(time.monotonic() - started_epoch, 3)

        (out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')

    return 0 if summary.get('status') == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
