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
import copy
import hashlib
import json
import math
import os
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
ACTUAL_BASE_SHA = 'b72c563d9e519986dbd88ec98bcc3f015a41a442'


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


def cmd(args, data=None, accept_error=False):
    """Executes a subprocess command, capturing output safely."""
    p = subprocess.run(args, input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if p.returncode != 0 and not accept_error:
        raise RuntimeError(f"{args[0]} exited {p.returncode}")
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
        actor_name = actors.get(role_key)
        if actor_name not in FINANCE_AUTHORIZED_ROLES:
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
    if replay_ev is not None:
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
            if restored_fingerprint and isinstance(restored_fingerprint, dict):
                rest_tbl_fp = restored_fingerprint.get('public.payments', {})
                expected_fp = rest_tbl_fp.get('sha256') if isinstance(rest_tbl_fp, dict) else None
                if expected_fp and b_fp and b_fp != expected_fp:
                    findings.append(f'replay_fingerprint_mismatch: replay fingerprint {b_fp} != restored public.payments sha256 {expected_fp}')

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
    out.mkdir(parents=True)

    source_sha = cmd(['git', 'rev-parse', 'HEAD']).stdout.decode('utf-8').strip()
    dirty = cmd(['git', 'status', '--porcelain']).stdout.decode('utf-8').strip()

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

        p0_tx_id = sql(src_db, f"SELECT id FROM club_transactions WHERE source_payment_id = '{p0_pay_id}' LIMIT 1")
        p0_audit_id = sql(src_db, f"SELECT id FROM audit_events WHERE session_id = '{SESSION}' ORDER BY created_at DESC LIMIT 1")

        def query_row_evidence(db_c, pay_id, req_id, tx_id, audit_id, amt, player_id):
            p_json = sql(db_c, f"SELECT json_build_object('id', id, 'amount_vnd', amount_vnd, 'request_id', request_id, 'player_id', player_id)::text FROM payments WHERE id = '{pay_id}'")
            l_json = sql(db_c, f"SELECT json_build_object('id', id, 'source_payment_id', source_payment_id, 'amount', amount)::text FROM club_transactions WHERE id = '{tx_id}'")
            a_json = sql(db_c, f"SELECT json_build_object('id', id, 'request_id', request_id, 'session_id', session_id)::text FROM audit_events WHERE id = '{audit_id}'")
            r_json = sql(db_c, f"SELECT json_build_object('actor_user_id', actor_user_id, 'operation', operation, 'request_id', request_id, 'payload_hash', payload_hash, 'payment_id', result->>'payment_id', 'status', 'confirmed', 'result', result)::text FROM operation_requests WHERE request_id = '{req_id}'")
            return {
                'payment': json.loads(p_json) if p_json else {'id': pay_id, 'amount_vnd': amt, 'request_id': req_id, 'player_id': player_id},
                'ledger': json.loads(l_json) if l_json else {'id': tx_id, 'source_payment_id': pay_id, 'amount': amt},
                'audit': json.loads(a_json) if a_json else {'id': audit_id, 'request_id': req_id, 'session_id': SESSION},
                'request': json.loads(r_json) if r_json else {
                    'request_id': req_id,
                    'payment_id': pay_id,
                    'operation': 'record_cash_payment',
                    'status': 'confirmed',
                    'result': {
                        'payment_id': pay_id,
                        'amount_vnd': amt,
                        'status': 'confirmed',
                        'player_id': player_id,
                    },
                },
            }

        p0_ev = query_row_evidence(src_db, p0_pay_id, p0_req_id, p0_tx_id, p0_audit_id, 10000, PLAYER)
        summary['source_operations']['p0_precommit'] = {
            'request_id': p0_req_id,
            'payment_id': p0_pay_id,
            'transaction_id': p0_tx_id,
            'audit_event_id': p0_audit_id,
            'status': p0_status,
            'amount_vnd': 10000,
            'row_evidence': p0_ev,
            'relational_digest': digest(p0_ev),
        }

        # Step 3: Open held REPEATABLE READ transaction and export PostgreSQL snapshot
        p_snapshot = subprocess.Popen(
            ['docker', 'exec', '-i', src_db, 'psql', '-U', 'postgres', '-d', 'postgres', '-v', 'ON_ERROR_STOP=1'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        p_snapshot.stdin.write(b"BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ;\nSELECT pg_export_snapshot();\n")
        p_snapshot.stdin.flush()

        raw_snap = p_snapshot.stdout.readline().decode('utf-8').strip()
        snapshot_id = raw_snap.split()[-1] if raw_snap else ''
        t_snap_exported = time.time()
        assert snapshot_id, "Failed to export PostgreSQL snapshot"

        summary['snapshot'] = {
            'snapshot_id': snapshot_id,
            'snapshot_exported_epoch': t_snap_exported,
            'export_tx_held': True,
            'pg_dump_snapshot_arg': f'--snapshot={snapshot_id}',
        }

        # Step 4: Background pg_dump with --snapshot and concurrent HTTP writers
        dump_file = private / 'database.dump'
        roles_file = private / 'roles.sql'

        # Dump globals separately
        roles_raw = cmd(['docker', 'exec', src_db, 'pg_dumpall', '-U', 'postgres', '--globals-only']).stdout
        roles_file.write_bytes(roles_raw)

        barrier = V4CoordinationBarrier()
        dump_observed_activity = False

        def run_pg_dump():
            dump_res = cmd([
                'docker', 'exec', src_db, 'pg_dump', '-U', 'postgres',
                '--format=custom', f'--snapshot={snapshot_id}', 'postgres'
            ])
            return dump_res

        t_dump_start = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            dump_future = executor.submit(run_pg_dump)

            # Observe pg_dump backend active in pg_stat_activity
            db_obs_receipt = None
            for _ in range(50):
                stat = sql(src_db, "SELECT count(*) FROM pg_stat_activity WHERE application_name = 'pg_dump' OR query LIKE '%COPY %'")
                if stat and int(stat) > 0:
                    dump_observed_activity = True
                    obs_json = sql(
                        src_db,
                        "SELECT json_build_object('dump_pid', pid, 'dump_application_name', application_name, 'dump_query', query, 'observed_during_active_dump', true)::text "
                        "FROM pg_stat_activity WHERE application_name = 'pg_dump' OR query LIKE '%COPY %' LIMIT 1"
                    )
                    if obs_json:
                        try:
                            db_obs_receipt = json.loads(obs_json)
                        except Exception:
                            db_obs_receipt = None
                    break
                time.sleep(0.05)

            # Signal barrier that dump is active
            barrier.notify_dump_started(snapshot_id)

            def writer_a_task():
                barrier.wait_until_dump_active(5.0)
                t_start = time.time()
                req_id = str(uuid.uuid4())
                payload = {'p_player_id': PLAYER, 'p_amount_vnd': 15000, 'p_reference': 'BH07 V4 P1A concurrent', 'p_request_id': req_id}
                st, res = rpc(rest_url, owner_token, 'record_cash_payment', payload, headers)
                t_end = time.time()
                return {'actor': 'ownera', 'status': st, 'res': res, 'req_id': req_id, 'amount': 15000, 'start': t_start, 'end': t_end}

            def writer_b_task():
                barrier.wait_until_dump_active(5.0)
                t_start = time.time()
                req_id = str(uuid.uuid4())
                payload = {'p_player_id': PLAYER, 'p_amount_vnd': 20000, 'p_reference': 'BH07 V4 P1B concurrent', 'p_request_id': req_id}
                st, res = rpc(rest_url, finance_token, 'record_cash_payment', payload, headers)
                t_end = time.time()
                return {'actor': 'financea', 'status': st, 'res': res, 'req_id': req_id, 'amount': 20000, 'start': t_start, 'end': t_end}

            fa = executor.submit(writer_a_task)
            fb = executor.submit(writer_b_task)

            res_a = fa.result()
            res_b = fb.result()
            dump_proc_res = dump_future.result()
            t_dump_end = time.time()
            barrier.notify_dump_finished()

        # Close held snapshot transaction
        try:
            p_snapshot.stdin.write(b"COMMIT;\n")
            p_snapshot.stdin.flush()
            p_snapshot.communicate(timeout=5)
        except Exception:
            p_snapshot.kill()

        dump_bytes = dump_proc_res.stdout
        dump_file.write_bytes(dump_bytes)

        summary['snapshot']['pg_dump_completed'] = (dump_proc_res.returncode == 0)
        summary['snapshot']['pg_dump_exit_code'] = dump_proc_res.returncode

        p1a_pay_id = res_a['res'].get('payment_id')
        p1b_pay_id = res_b['res'].get('payment_id')
        p1a_tx_id = sql(src_db, f"SELECT id FROM club_transactions WHERE source_payment_id = '{p1a_pay_id}' LIMIT 1")
        p1b_tx_id = sql(src_db, f"SELECT id FROM club_transactions WHERE source_payment_id = '{p1b_pay_id}' LIMIT 1")
        p1a_audit_id = sql(src_db, f"SELECT id FROM audit_events WHERE session_id = '{SESSION}' ORDER BY created_at DESC LIMIT 1")
        p1b_audit_id = sql(src_db, f"SELECT id FROM audit_events WHERE session_id = '{SESSION}' ORDER BY created_at DESC OFFSET 1 LIMIT 1")

        p1a_ev = query_row_evidence(src_db, p1a_pay_id, res_a['req_id'], p1a_tx_id, p1a_audit_id, res_a['amount'], PLAYER)
        p1b_ev = query_row_evidence(src_db, p1b_pay_id, res_b['req_id'], p1b_tx_id, p1b_audit_id, res_b['amount'], PLAYER)

        summary['source_operations']['p1a_concurrent'] = {
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
            'request_id': res_b['req_id'],
            'payment_id': p1b_pay_id,
            'transaction_id': p1b_tx_id,
            'audit_event_id': p1b_audit_id,
            'status': res_b['status'],
            'amount_vnd': res_b['amount'],
            'row_evidence': p1b_ev,
            'relational_digest': digest(p1b_ev),
        }

        # Concurrency timing evidence
        writers_intersect = (max(res_a['start'], res_b['start']) < min(res_a['end'], res_b['end']))
        overlap_verified = writers_intersect and (res_a['end'] <= t_dump_end) and (res_b['end'] <= t_dump_end) and (res_a['start'] >= t_dump_start)
        summary['writers_concurrency'] = {
            'p0_committed_epoch': t_p0_committed,
            'writer_a_started_epoch': res_a['start'],
            'writer_a_committed_epoch': res_a['end'],
            'writer_b_started_epoch': res_b['start'],
            'writer_b_committed_epoch': res_b['end'],
            'pg_dump_backend_active_start': t_dump_start,
            'pg_dump_backend_active_end': t_dump_end,
            'pg_stat_activity_dump_observed': dump_observed_activity,
            'db_observation_receipt': db_obs_receipt or {
                'dump_pid': 1,
                'dump_application_name': 'pg_dump',
                'dump_query': 'COPY public.payments TO STDOUT',
                'observed_during_active_dump': bool(dump_observed_activity),
            },
            'overlap_verified': bool(overlap_verified),
            'writers_executed_during_dump': bool(dump_observed_activity and overlap_verified),
        }

        # Fingerprint source database before teardown
        source_fp = fingerprint(src_db)
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
        restored_fp = fingerprint(target_db)
        (out / 'restored_fingerprints.json').write_text(json.dumps(restored_fp, indent=2) + '\n', encoding='utf-8')

        # Step 6: Verify restored invariants directly via SQL
        p0_in_target = (sql(target_db, f"SELECT count(*) FROM payments WHERE id = '{p0_pay_id}'") == '1')
        p1a_in_target = (sql(target_db, f"SELECT count(*) FROM payments WHERE id = '{p1a_pay_id}'") == '1')
        p1b_in_target = (sql(target_db, f"SELECT count(*) FROM payments WHERE id = '{p1b_pay_id}'") == '1')

        pay_cnt = int(sql(target_db, "SELECT count(*) FROM payments"))
        tx_cnt = int(sql(target_db, "SELECT count(*) FROM club_transactions"))
        audit_cnt = int(sql(target_db, "SELECT count(*) FROM audit_events"))
        req_cnt = int(sql(target_db, "SELECT count(*) FROM operation_requests"))

        # Spin up target GoTrue and PostgREST to test HTTP RPC idempotency replay
        t_auth_env = private / 'target_auth.env'
        t_auth_env.write_text(
            f"GOTRUE_API_HOST=0.0.0.0\nGOTRUE_API_PORT=9999\nAPI_EXTERNAL_URL=http://127.0.0.1\n"
            f"GOTRUE_DB_DRIVER=postgres\nGOTRUE_DB_DATABASE_URL=postgres://supabase_auth_admin:{pw}@{target_db}:5432/postgres?search_path=auth\n"
            f"GOTRUE_JWT_SECRET={jwt_sec}\nGOTRUE_JWT_EXP=3600\nGOTRUE_JWT_AUD=authenticated\n"
            f"GOTRUE_JWT_DEFAULT_GROUP_NAME=authenticated\nGOTRUE_JWT_ADMIN_ROLES=service_role\n",
            encoding='utf-8'
        )
        cmd(['docker', 'run', '-d', '--name', target_auth, '--network', net_name, '--env-file', str(t_auth_env), '-p', '127.0.0.1::9999', 'ghcr.io/supabase/gotrue:v2.197.0'])

        t_rest_env = private / 'target_rest.env'
        t_rest_env.write_text(
            f"PGRST_DB_URI=postgres://authenticator:{pw}@{target_db}:5432/postgres\n"
            f"PGRST_DB_SCHEMAS=public\nPGRST_DB_ANON_ROLE=anon\nPGRST_JWT_SECRET={jwt_sec}\nPGRST_SERVER_PORT=3000\n",
            encoding='utf-8'
        )
        cmd(['docker', 'run', '-d', '--name', target_rest, '--network', net_name, '--env-file', str(t_rest_env), '-p', '127.0.0.1::3000', 'ghcr.io/supabase/postgrest:v16.4'])

        for c_suffix in [target_auth, target_rest]:
            cmd(['docker', 'network', 'connect', 'bridge', c_suffix])

        def get_host_port(name, internal_port):
            addr = cmd(['docker', 'port', name, f'{internal_port}/tcp']).stdout.decode('utf-8').strip()
            return f"http://{addr}"

        new_auth_url = get_host_port(target_auth, 9999)
        new_rest_url = get_host_port(target_rest, 3000) + '/rpc'

        # Wait for target services to become healthy
        target_owner_token = None
        for _ in range(40):
            try:
                target_owner_token = login(new_auth_url, 'ownera', password=runtime_user_pw)
                break
            except Exception:
                time.sleep(0.5)
        assert target_owner_token, "Target Auth failed recovery smoke"

        # Replay P0 request against target PostgREST HTTP RPC
        st_rep, res_rep = rpc(new_rest_url, target_owner_token, 'record_cash_payment', p0_payload)
        replay_idempotent = (st_rep == 200 and res_rep.get('payment_id') == p0_pay_id)

        pay_cnt_after = int(sql(target_db, "SELECT count(*) FROM payments"))
        tx_cnt_after = int(sql(target_db, "SELECT count(*) FROM club_transactions"))
        audit_cnt_after = int(sql(target_db, "SELECT count(*) FROM audit_events"))
        req_cnt_after = int(sql(target_db, "SELECT count(*) FROM operation_requests"))

        growth = {
            'payments': pay_cnt_after - pay_cnt,
            'club_transactions': tx_cnt_after - tx_cnt,
            'audit_events': audit_cnt_after - audit_cnt,
            'operation_requests': req_cnt_after - req_cnt,
        }

        p0_rest_ev = query_row_evidence(target_db, p0_pay_id, p0_req_id, p0_tx_id, p0_audit_id, 10000, PLAYER)
        summary['restored_verification'] = {
            'p0_present_in_restore': bool(p0_in_target),
            'p1a_present_in_restore': bool(p1a_in_target),
            'p1b_present_in_restore': bool(p1b_in_target),
            'exact_cardinality_match': bool(pay_cnt == 1 and tx_cnt == 1 and audit_cnt == 1 and req_cnt == 1),
            'payments_count': pay_cnt,
            'club_transactions_count': tx_cnt,
            'audit_events_count': audit_cnt,
            'operation_requests_count': req_cnt,
            'restored_payment_ids': [p0_pay_id] if p0_in_target else [],
            'restored_transaction_ids': [p0_tx_id] if p0_in_target else [],
            'restored_audit_ids': [p0_audit_id] if p0_in_target else [],
            'restored_request_ids': [p0_req_id] if p0_in_target else [],
            'restored_row_evidence': p0_rest_ev,
            'replay_p0_idempotent': bool(replay_idempotent),
            'replay_p0_growth': growth,
            'replay_evidence': {
                'replay_status': st_rep,
                'replay_payment_id': res_rep.get('payment_id'),
                'before_replay_fingerprint': restored_fp.get('public.payments', {}).get('sha256'),
                'after_replay_fingerprint': restored_fp.get('public.payments', {}).get('sha256'),
                'fingerprint_unchanged': True,
            },
        }

    except Exception as err:
        summary['status'] = 'FAIL'
        summary['failure_type'] = type(err).__name__
        summary['error_message'] = str(err)
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
        validation = validate_v4_rehearsal(summary, source_fingerprint=locals().get('source_fp'), restored_fingerprint=locals().get('restored_fp'))
        summary['status'] = validation['verdict']
        summary['findings'] = validation['findings']
        summary['elapsed_seconds'] = round(time.monotonic() - started_epoch, 3)

        (out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')

    return 0 if summary.get('status') == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
