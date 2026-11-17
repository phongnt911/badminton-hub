"""Disposable private-club + unlisted-session fixture helper for BH-07 PaymentInstructions heap runs.

Creates an isolated private club owned exclusively by `ownera`, an unlisted completed session
whose `receiver_snapshot` carries two synthetic non-rendered UUIDv4 canary values
(`canary_instr_a`, `canary_instr_b`), one confirmed unpaid offline/guest `session_players` row
(`user_id = NULL`), an active `charge_revisions` row matching `sessions.billing_input_version`,
and one `session_charges` row (`amount_due_vnd = 100000`).

Safety guarantees:
- Target DB container must be strictly `bh07-android-db`.
- Target `supabase_url` must be strictly loopback on port `54321`.
- Never prints credentials or raw sentinel UUIDs to stdout or public receipts.
- Collision preflight refuses pre-existing UUIDs and never deletes unowned rows.
- Writes private state file (`insert_attempted=True, created=False`) BEFORE issuing SQL INSERT,
  so uncertain commits/timeouts can still verify ownership by `(id, ownership_marker)` and clean up.
- Enforces zero payment/ledger/audit/operation mutations and exact DB baseline fingerprint equality
  (public rows, schema, roles, non-auth sequences) excluding documented Auth state only.
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path
from urllib.parse import urlparse

ALLOWED_DB_CONTAINER = 'bh07-android-db'
ALLOWED_LOOPBACK_HOSTS = ('127.0.0.1', 'localhost', '::1')
ALLOWED_SUPABASE_PORT = 54321
MARKER_PREFIX = '[BH07-DISPOSABLE-INSTR:'
ROOT = Path(__file__).resolve().parents[2]
HEX64_RE = re.compile(r'^[0-9a-f]{64}$')


class FixtureError(RuntimeError):
    """Base error for disposable instructions fixture operations."""


class FixtureCollisionError(FixtureError):
    """Raised when a prospective fixture UUID already exists in the database."""


class OwnershipError(FixtureError):
    """Raised when a DB row lacks the expected run ownership marker."""


def validate_uuid(value, label='uuid'):
    """Validate and normalize a strict UUID string."""
    try:
        return str(uuid.UUID(str(value)))
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValueError(f'invalid {label}: expected UUID') from exc


def sha12(value):
    """Return first 12 hex characters of SHA-256 of stringified value."""
    return hashlib.sha256(str(value).encode('utf-8')).hexdigest()[:12]


def digest_json(obj):
    """Canonical SHA-256 hex digest of JSON-serializable data or raw bytes."""
    if not isinstance(obj, bytes):
        obj = json.dumps(obj, sort_keys=True, separators=(',', ':')).encode('utf-8')
    return hashlib.sha256(obj).hexdigest()


def load_and_validate_config(config_path=None, config_dict=None):
    """Load private local config JSON and enforce strict local-only DB/Supabase bounds."""
    if config_dict is not None:
        cfg = dict(config_dict)
    elif config_path:
        cfg = json.loads(Path(config_path).read_text(encoding='utf-8'))
    else:
        env_path = os.environ.get('BH07_INSTRUCTIONS_CONFIG')
        if not env_path:
            raise ValueError('config_path or BH07_INSTRUCTIONS_CONFIG is required')
        cfg = json.loads(Path(env_path).read_text(encoding='utf-8'))

    if not isinstance(cfg, dict):
        raise ValueError('config must be a JSON object')

    db_container = cfg.get('db_container', ALLOWED_DB_CONTAINER)
    if db_container != ALLOWED_DB_CONTAINER:
        raise ValueError(f'db_container must be strictly {ALLOWED_DB_CONTAINER!r}, got {db_container!r}')

    supabase_url = str(cfg.get('supabase_url') or '').strip()
    parsed = urlparse(supabase_url)
    host = (parsed.hostname or '').lower()
    if parsed.scheme not in ('http', 'https') or host not in ALLOWED_LOOPBACK_HOSTS:
        raise ValueError(f'supabase_url must be strictly loopback, got {supabase_url!r}')
    if parsed.port != ALLOWED_SUPABASE_PORT:
        raise ValueError(f'supabase_url port must be strictly {ALLOWED_SUPABASE_PORT}, got {parsed.port!r}')
    if parsed.username or parsed.password or parsed.path not in ('', '/') or parsed.query or parsed.fragment:
        raise ValueError('supabase_url must not contain credentials, path, query, or fragment')

    docker_exe = str(cfg.get('docker_exe') or os.environ.get('BH07_DOCKER_EXE') or 'docker').strip()
    if not docker_exe:
        raise ValueError('docker_exe must not be empty')

    owner_email = str(cfg.get('owner_email') or 'ownera@example.test').strip()
    if not re.fullmatch(r'[A-Za-z0-9_.+-]+@[A-Za-z0-9.-]+', owner_email):
        raise ValueError('invalid owner_email format')

    include_club_bank = cfg.get('include_club_bank', False)
    if not isinstance(include_club_bank, bool):
        raise ValueError('include_club_bank must be a strict boolean')

    return {
        **cfg,
        'db_container': db_container,
        'supabase_url': f'{parsed.scheme}://{host if ":" not in host else f"[{host}]"}:{ALLOWED_SUPABASE_PORT}',
        'docker_exe': docker_exe,
        'owner_email': owner_email,
        'include_club_bank': include_club_bank,
    }


def _sql_literal(value):
    """Format a safe SQL single-quoted literal for validated UUIDs or ASCII markers."""
    s = str(value)
    if '\x00' in s:
        raise ValueError('NUL byte not allowed in SQL literal')
    return "'" + s.replace("'", "''") + "'"


class DockerPsqlClient:
    """Executes SQL and schema dumps against bh07-android-db via docker exec."""

    def __init__(self, docker_exe, db_container=ALLOWED_DB_CONTAINER):
        if db_container != ALLOWED_DB_CONTAINER:
            raise ValueError(f'db_container must be {ALLOWED_DB_CONTAINER!r}')
        self.docker_exe = docker_exe
        self.db_container = db_container

    def _run(self, args, input_text=None):
        proc = subprocess.run(
            [self.docker_exe, *args],
            input=input_text,
            text=True,
            capture_output=True,
            encoding='utf-8',
        )
        if proc.returncode != 0:
            raise RuntimeError(f'{self.docker_exe} {" ".join(args[:2])} exited {proc.returncode}')
        return proc.stdout

    def query_json(self, sql):
        out = self._run(
            ['exec', '-i', self.db_container, 'psql', '-X', '-U', 'postgres', '-d', 'postgres',
             '-v', 'ON_ERROR_STOP=1', '-t', '-A'],
            input_text=sql,
        ).strip()
        return json.loads(out) if out else {}

    def exec_sql(self, sql, fixture=None):
        self._run(
            ['exec', '-i', self.db_container, 'psql', '-X', '-U', 'postgres', '-d', 'postgres',
             '-v', 'ON_ERROR_STOP=1', '-t', '-A'],
            input_text=sql,
        )

    def fingerprint(self):
        return capture_fingerprint(self.query_json, self._pg_dump_schema)

    def _pg_dump_schema(self):
        return self._run(['exec', self.db_container, 'pg_dump', '-U', 'postgres', '--schema-only', 'postgres'])


def capture_fingerprint(query_json_fn, pg_dump_fn):
    """Capture baseline fingerprint covering public rows, schema, roles, and sequences."""
    tables = query_json_fn(
        "SELECT COALESCE(json_agg(json_build_array(schemaname, tablename) ORDER BY schemaname, tablename), '[]'::json) "
        "FROM pg_tables WHERE schemaname IN ('public', 'auth');"
    )
    public = {}
    for schema, table in tables:
        if schema != 'public':
            continue
        ident = '"' + schema.replace('"', '""') + '"."' + table.replace('"', '""') + '"'
        rows = query_json_fn(
            f"SELECT COALESCE(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text), '[]'::jsonb) FROM {ident} t;"
        )
        public[f'{schema}.{table}'] = {'rows': len(rows), 'sha256': digest_json(rows)}

    schema_dump = pg_dump_fn()
    schema_dump = re.sub(r'(?m)^\\(?:un)?restrict .*\n?', '', schema_dump)
    sequences = query_json_fn(
        "SELECT COALESCE(jsonb_agg(to_jsonb(s) ORDER BY schemaname, sequencename), '[]'::jsonb) "
        "FROM pg_sequences s WHERE schemaname IN ('public', 'auth');"
    )
    roles = query_json_fn(
        "SELECT COALESCE(jsonb_agg(to_jsonb(r) ORDER BY rolname), '[]'::jsonb) FROM ("
        "SELECT rolname, rolsuper, rolinherit, rolcreaterole, rolcreatedb, rolcanlogin, "
        "rolreplication, rolbypassrls, rolconnlimit, rolvaliduntil, rolconfig "
        "FROM pg_roles WHERE rolname NOT LIKE 'pg_%') r;"
    )
    return {
        'public': public,
        'schema': digest_json(schema_dump.encode('utf-8')),
        'roles': roles,
        'sequences': sequences,
    }


def _is_link_or_junction(path_obj):
    if path_obj.is_symlink():
        return True
    junction = getattr(path_obj, 'is_junction', None)
    return bool(junction and junction())


def _is_inside_or_equal(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def validate_state_path(state_path, *, root_dir=ROOT):
    """Validate that a private fixture recovery state path is strictly outside repo/ancestors/symlinks."""
    raw = Path(state_path)
    resolved = raw.resolve()
    root_real = Path(root_dir).resolve()
    tmp_base = Path(tempfile.gettempdir()).resolve()

    if resolved == Path(resolved.anchor):
        raise ValueError(f'state_path cannot be filesystem root: {state_path}')
    if _is_inside_or_equal(resolved, root_real):
        raise ValueError(f'state_path must be strictly outside repository root: {state_path}')
    if _is_inside_or_equal(root_real, resolved):
        raise ValueError(f'state_path cannot be an ancestor of repository root: {state_path}')

    # Reject symlinks/junctions on the leaf and any existing components below OS temp root
    cur = Path(os.path.abspath(str(raw)))
    while True:
        if cur.exists() and _is_link_or_junction(cur):
            if cur.resolve() != tmp_base:
                raise ValueError(f'state_path must not traverse or target symlink/junction: {cur}')
        parent = cur.parent
        if parent == cur or cur.resolve() == tmp_base:
            break
        cur = parent
    return resolved


def _validate_fingerprint_shape(fp):
    if not isinstance(fp, dict) or not fp:
        return False
    pub = fp.get('public')
    if not isinstance(pub, dict) or not pub:
        return False
    for tbl, info in pub.items():
        if not isinstance(tbl, str) or not isinstance(info, dict):
            return False
        if type(info.get('rows')) is not int or info.get('rows') < 0:
            return False
        if not isinstance(info.get('sha256'), str) or not HEX64_RE.fullmatch(info['sha256']):
            return False
    schema = fp.get('schema')
    if not isinstance(schema, str) or not HEX64_RE.fullmatch(schema):
        return False
    roles = fp.get('roles')
    seqs = fp.get('sequences')
    if not isinstance(roles, list) or not isinstance(seqs, list):
        return False
    if any(not isinstance(s, dict) or not isinstance(s.get('schemaname'), str) or not isinstance(s.get('sequencename'), str)
           for s in seqs):
        return False
    return True


def compare_fingerprints(before, after):
    """Verify public rows, schema, roles, and sequences match; allow ONLY auth rows & refresh_tokens_id_seq.last_value delta."""
    if not _validate_fingerprint_shape(before) or not _validate_fingerprint_shape(after):
        return {
            'equal': False,
            'mismatches': ['missing_or_malformed_fingerprint'],
            'auth_refresh_sequence': [],
            'public_tables': 0,
            'public_rows': 0,
        }

    mismatches = []
    if before.get('public') != after.get('public'):
        mismatches.append('public_tables_mismatch')
    if before.get('schema') != after.get('schema'):
        mismatches.append('schema_mismatch')
    if before.get('roles') != after.get('roles'):
        mismatches.append('roles_mismatch')

    def _normalize_sequences(fp):
        normalized = []
        auth_refresh = None
        for seq in fp.get('sequences') or []:
            copy_seq = dict(seq)
            if copy_seq.get('schemaname') == 'auth' and copy_seq.get('sequencename') == 'refresh_tokens_id_seq':
                auth_refresh = copy_seq.get('last_value')
                copy_seq['last_value'] = None
            normalized.append(copy_seq)
        return normalized, auth_refresh

    before_seqs, before_auth_seq = _normalize_sequences(before)
    after_seqs, after_auth_seq = _normalize_sequences(after)
    if before_seqs != after_seqs:
        mismatches.append('sequences_mismatch')

    after_pub = after.get('public') or {}
    return {
        'equal': len(mismatches) == 0,
        'mismatches': mismatches,
        'auth_rows_excluded': True,
        'auth_refresh_sequence': [before_auth_seq, after_auth_seq],
        'public_tables': len(after_pub),
        'public_rows': sum(int(v.get('rows', 0)) for v in after_pub.values()),
        'before_sha256': digest_json(before),
        'after_sha256': digest_json(after),
    }


def _write_private_json_exclusive(path, data):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if target.exists() or _is_link_or_junction(target):
        raise FileExistsError(f'refusing to overwrite existing state file: {target}')
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, 'O_NOFOLLOW', 0)
    payload = (json.dumps(data, indent=2) + '\n').encode('utf-8')
    fd = os.open(str(target), flags, 0o600)
    try:
        os.write(fd, payload)
        os.fsync(fd)
    finally:
        os.close(fd)
    try:
        os.chmod(target, 0o600)
    except OSError:
        pass


def _write_private_json_atomic(path, data):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if target.exists() and _is_link_or_junction(target):
        raise ValueError(f'refusing to write through symlink/junction state file: {target}')
    tmp_path = target.parent / f'.{target.name}.{os.getpid()}.{uuid.uuid4().hex[:8]}.tmp'
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, 'O_NOFOLLOW', 0)
    payload = (json.dumps(data, indent=2) + '\n').encode('utf-8')
    fd = os.open(str(tmp_path), flags, 0o600)
    try:
        os.write(fd, payload)
        os.fsync(fd)
    except Exception:
        os.close(fd)
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise
    os.close(fd)
    os.replace(str(tmp_path), str(target))
    try:
        os.chmod(target, 0o600)
    except OSError:
        pass


def _require_nonempty_str(value, label):
    """Validate that a value is a non-empty string free of NUL bytes."""
    if not isinstance(value, str) or not value.strip() or '\x00' in value:
        raise ValueError(f'{label} must be a non-empty string without NUL bytes')
    return value


class DisposableInstructionsFixture:
    """Manages an isolated, UUID-owned disposable fixture for PaymentInstructions heap tests."""

    def __init__(self, *, run_id=None, club_id=None, club_member_id=None,
                 session_id=None, player_id=None, revision_id=None, charge_id=None,
                 marker_id=None, sentinel_1=None, sentinel_2=None, nonce=None,
                 owner_email='ownera@example.test',
                 include_club_bank=False, club_bank_account_id=None,
                 club_bank_code=None, club_account_number=None,
                 club_account_name=None,
                 club_bank_removed=False, club_bank_verified_absent=False,
                 preflight_absent=False, insert_attempted=False, created=False,
                 removed=False, verified_absent=False, refused=None, error=None):
        if not isinstance(include_club_bank, bool):
            raise ValueError('include_club_bank must be a strict boolean')
        if not isinstance(club_bank_removed, bool) or not isinstance(club_bank_verified_absent, bool):
            raise ValueError('club_bank_removed and club_bank_verified_absent must be strict booleans')

        self.run_id = validate_uuid(run_id or uuid.uuid4(), 'run_id')
        self.club_id = validate_uuid(club_id or uuid.uuid4(), 'club_id')
        self.club_member_id = validate_uuid(club_member_id or uuid.uuid4(), 'club_member_id')
        self.session_id = validate_uuid(session_id or uuid.uuid4(), 'session_id')
        self.player_id = validate_uuid(player_id or uuid.uuid4(), 'player_id')
        self.revision_id = validate_uuid(revision_id or uuid.uuid4(), 'revision_id')
        self.charge_id = validate_uuid(charge_id or uuid.uuid4(), 'charge_id')
        self.marker_id = validate_uuid(marker_id or uuid.uuid4(), 'marker_id')
        self.sentinel_1 = validate_uuid(sentinel_1 or uuid.uuid4(), 'sentinel_1')
        self.sentinel_2 = validate_uuid(sentinel_2 or uuid.uuid4(), 'sentinel_2')
        if self.sentinel_1 == self.sentinel_2:
            raise ValueError('sentinel_1 and sentinel_2 must be distinct')

        self.nonce = nonce or uuid.uuid4().hex[:8]
        self.owner_email = owner_email
        self.club_name = f'BH07 Instr Club {self.nonce}'
        self.session_title = f'BH07 Instr Session {self.nonce}'
        self.player_name = f'BH07 Guest {self.nonce}'
        self.marker_text = f'{MARKER_PREFIX}{self.marker_id}]'

        # Ensure rendered names never embed raw sentinel UUIDs.
        for label in (self.club_name, self.session_title, self.player_name, self.marker_text):
            if self.sentinel_1 in label or self.sentinel_2 in label:
                raise ValueError('rendered fixture field must not embed sentinel UUID')

        self.include_club_bank = include_club_bank
        if self.include_club_bank:
            if club_bank_account_id is not None and not isinstance(club_bank_account_id, str):
                raise ValueError('club_bank_account_id must be a UUID string')
            self.club_bank_account_id = validate_uuid(
                club_bank_account_id if club_bank_account_id is not None else uuid.uuid4(),
                'club_bank_account_id',
            )
            self.club_bank_code = _require_nonempty_str(
                club_bank_code if club_bank_code is not None else 'VCB',
                'club_bank_code',
            )
            self.club_account_number = _require_nonempty_str(
                club_account_number if club_account_number is not None else f'99990000{uuid.uuid4().int % 100000000:08d}',
                'club_account_number',
            )
            self.club_account_name = _require_nonempty_str(
                club_account_name if club_account_name is not None else f'BH07 SYNTH BANK {self.nonce.upper()}',
                'club_account_name',
            )
            for label in (self.club_bank_code, self.club_account_number, self.club_account_name):
                if (self.sentinel_1 in label or self.sentinel_2 in label
                        or self.club_id in label or self.club_bank_account_id in label):
                    raise ValueError('rendered bank field must not embed sentinel or entity UUID')
            self.club_bank_removed = club_bank_removed
            self.club_bank_verified_absent = club_bank_verified_absent
        else:
            if any(v is not None for v in (club_bank_account_id, club_bank_code, club_account_number, club_account_name)) or club_bank_removed or club_bank_verified_absent:
                raise ValueError('club_bank fields are forbidden when include_club_bank is false')
            self.club_bank_account_id = None
            self.club_bank_code = None
            self.club_account_number = None
            self.club_account_name = None
            self.club_bank_removed = False
            self.club_bank_verified_absent = False

        self.preflight_absent = bool(preflight_absent)
        self.insert_attempted = bool(insert_attempted)
        self.created = bool(created)
        self.removed = bool(removed)
        self.verified_absent = bool(verified_absent)
        self.refused = refused
        self.error = error
        self.before_fingerprint = None

    def to_private_state(self):
        """Serialize complete state (only for private temp path outside repo/published bundle)."""
        state = {
            'run_id': self.run_id,
            'club_id': self.club_id,
            'club_member_id': self.club_member_id,
            'session_id': self.session_id,
            'player_id': self.player_id,
            'revision_id': self.revision_id,
            'charge_id': self.charge_id,
            'marker_id': self.marker_id,
            'sentinel_1': self.sentinel_1,
            'sentinel_2': self.sentinel_2,
            'nonce': self.nonce,
            'owner_email': self.owner_email,
            'preflight_absent': self.preflight_absent,
            'insert_attempted': self.insert_attempted,
            'created': self.created,
            'removed': self.removed,
            'verified_absent': self.verified_absent,
            'refused': self.refused,
            'error': self.error,
            'before_fingerprint': self.before_fingerprint,
        }
        if self.include_club_bank:
            state.update({
                'include_club_bank': True,
                'club_bank_account_id': self.club_bank_account_id,
                'club_bank_code': self.club_bank_code,
                'club_account_number': self.club_account_number,
                'club_account_name': self.club_account_name,
                'club_bank_removed': self.club_bank_removed,
                'club_bank_verified_absent': self.club_bank_verified_absent,
            })
        return state

    @classmethod
    def from_state_file(cls, state_path):
        data = json.loads(Path(state_path).read_text(encoding='utf-8'))
        if not isinstance(data, dict):
            raise ValueError('state file must contain a JSON object')
        if 'include_club_bank' in data:
            inc = data['include_club_bank']
            if not isinstance(inc, bool):
                raise ValueError('include_club_bank in state must be a strict boolean')
        else:
            inc = False
        for flag_key in ('club_bank_removed', 'club_bank_verified_absent'):
            if flag_key in data and not isinstance(data[flag_key], bool):
                raise ValueError(f'{flag_key} in state must be a strict boolean')
        if inc:
            for req_key in ('club_bank_account_id', 'club_bank_code', 'club_account_number', 'club_account_name'):
                if req_key not in data or data[req_key] is None:
                    raise ValueError(f'{req_key} is required when include_club_bank is true')

        obj = cls(
            run_id=data['run_id'],
            club_id=data['club_id'],
            club_member_id=data['club_member_id'],
            session_id=data['session_id'],
            player_id=data['player_id'],
            revision_id=data['revision_id'],
            charge_id=data['charge_id'],
            marker_id=data['marker_id'],
            sentinel_1=data['sentinel_1'],
            sentinel_2=data['sentinel_2'],
            nonce=data['nonce'],
            owner_email=data.get('owner_email', 'ownera@example.test'),
            include_club_bank=inc,
            club_bank_account_id=data.get('club_bank_account_id'),
            club_bank_code=data.get('club_bank_code'),
            club_account_number=data.get('club_account_number'),
            club_account_name=data.get('club_account_name'),
            club_bank_removed=data.get('club_bank_removed', False),
            club_bank_verified_absent=data.get('club_bank_verified_absent', False),
            preflight_absent=data.get('preflight_absent', False),
            insert_attempted=data.get('insert_attempted', False),
            created=data.get('created', False),
            removed=data.get('removed', False),
            verified_absent=data.get('verified_absent', False),
            refused=data.get('refused'),
            error=data.get('error'),
        )
        obj.before_fingerprint = data.get('before_fingerprint')
        return obj

    def public_metadata(self):
        """Return safe, redacted fixture metadata for runner/logs (no raw sentinels or bank values)."""
        meta = {
            'club_name': self.club_name,
            'session_title': self.session_title,
            'player_name': self.player_name,
            'club_id': self.club_id,
            'session_id': self.session_id,
            'player_id': self.player_id,
            'sentinels': {
                'canary_instr_a': {'sha256_12': sha12(self.sentinel_1), 'length': len(self.sentinel_1)},
                'canary_instr_b': {'sha256_12': sha12(self.sentinel_2), 'length': len(self.sentinel_2)},
            },
        }
        if self.include_club_bank:
            meta['club_bank_included'] = True
            meta['club_bank'] = {
                'club_bank_account_id_sha256_12': sha12(self.club_bank_account_id),
                'bank_code_sha256_12': sha12(self.club_bank_code),
                'account_number_sha256_12': sha12(self.club_account_number),
                'account_name_sha256_12': sha12(self.club_account_name),
            }
        return meta

    def preflight(self, db):
        """Verify DB readiness, owner/venue anchors, and zero UUID collisions."""
        ping = db.query_json("SELECT json_build_object('ok', (SELECT 1));")
        if ping.get('ok') != 1:
            raise FixtureError('database readiness check failed')

        anchors = db.query_json(
            'SELECT json_build_object('
            f"'owner_id', (SELECT id FROM auth.users WHERE email = {_sql_literal(self.owner_email)} LIMIT 1), "
            "'venue_id', (SELECT id FROM public.venues WHERE status = 'active' ORDER BY id LIMIT 1));"
        )
        if not anchors.get('owner_id') or not anchors.get('venue_id'):
            raise FixtureError('required owner auth user or active venue anchor missing')

        bank_collision_expr = (
            f" + (SELECT count(*) FROM public.club_bank_accounts WHERE id = {_sql_literal(self.club_bank_account_id)} OR club_id = {_sql_literal(self.club_id)})"
            if self.include_club_bank else ''
        )
        collision = db.query_json(
            'SELECT json_build_object(\'collision_count\', '
            f"(SELECT count(*) FROM public.clubs WHERE id = {_sql_literal(self.club_id)}) + "
            f"(SELECT count(*) FROM public.club_members WHERE id = {_sql_literal(self.club_member_id)}) + "
            f"(SELECT count(*) FROM public.sessions WHERE id = {_sql_literal(self.session_id)}) + "
            f"(SELECT count(*) FROM public.session_players WHERE id = {_sql_literal(self.player_id)}) + "
            f"(SELECT count(*) FROM public.charge_revisions WHERE id = {_sql_literal(self.revision_id)}) + "
            f"(SELECT count(*) FROM public.session_charges WHERE id = {_sql_literal(self.charge_id)})"
            f"{bank_collision_expr});"
        )
        if int(collision.get('collision_count', -1)) != 0:
            self.preflight_absent = False
            self.refused = 'preexisting_uuid_collision'
            raise FixtureCollisionError('preflight collision: one or more fixture UUIDs already exist')

        self.preflight_absent = True
        return anchors

    def create(self, db, *, state_path=None, capture_baseline=False):
        """Preflight, persist attempted IDs exclusively before SQL, insert atomically, and verify readback."""
        validated_state = None
        if state_path:
            validated_state = validate_state_path(state_path)
            if validated_state.exists() or _is_link_or_junction(validated_state):
                raise FileExistsError(f'refusing to overwrite existing state file: {validated_state}')

        if capture_baseline:
            self.before_fingerprint = db.fingerprint()

        anchors = self.preflight(db)
        owner_id = validate_uuid(anchors['owner_id'], 'owner_id')
        venue_id = validate_uuid(anchors['venue_id'], 'venue_id')

        self.insert_attempted = True
        self.created = False
        if validated_state:
            _write_private_json_exclusive(validated_state, self.to_private_state())

        receiver_json = json.dumps({
            'bank_code': 'VCB',
            'account_number': '9999000012345678',
            'account_name': 'BH07 INSTR RECEIVER',
            'canary_instr_a': self.sentinel_1,
            'canary_instr_b': self.sentinel_2,
        }, separators=(',', ':'))

        bank_insert_sql = ''
        if self.include_club_bank:
            bank_insert_sql = f"""
INSERT INTO public.club_bank_accounts (id, club_id, bank_code, account_number, account_name, status)
VALUES ({_sql_literal(self.club_bank_account_id)}, {_sql_literal(self.club_id)}, {_sql_literal(self.club_bank_code)}, {_sql_literal(self.club_account_number)}, {_sql_literal(self.club_account_name)}, 'active');
"""

        insert_sql = f"""BEGIN;
INSERT INTO public.clubs (id, owner_user_id, name, description, visibility, status)
VALUES ({_sql_literal(self.club_id)}, {_sql_literal(owner_id)}, {_sql_literal(self.club_name)}, {_sql_literal(self.marker_text)}, 'private', 'active');

INSERT INTO public.club_members (id, club_id, user_id, display_name, role, status, joined_at)
VALUES ({_sql_literal(self.club_member_id)}, {_sql_literal(self.club_id)}, {_sql_literal(owner_id)}, 'Owner A', 'owner', 'active', now());
{bank_insert_sql}
INSERT INTO public.sessions (
  id, club_id, host_user_id, venue_id, title, description,
  starts_at, ends_at, capacity, court_count, visibility, lifecycle,
  approval_mode, fee_mode, member_fee_vnd, guest_fee_vnd, version, billing_input_version,
  receiver_snapshot
) VALUES (
  {_sql_literal(self.session_id)}, {_sql_literal(self.club_id)}, {_sql_literal(owner_id)}, {_sql_literal(venue_id)},
  {_sql_literal(self.session_title)}, {_sql_literal(self.marker_text)},
  now() - interval '10 minutes', now() - interval '1 minute', 8, 1, 'unlisted', 'completed',
  'auto_confirm', 'fixed', 100000, 100000, 1, 1,
  {_sql_literal(receiver_json)}::jsonb
);

INSERT INTO public.session_players (
  id, session_id, user_id, club_member_id, display_name,
  registration_status, attendance_status, source, participant_type,
  fee_exempt, requested_at, confirmed_at, created_by
) VALUES (
  {_sql_literal(self.player_id)}, {_sql_literal(self.session_id)}, NULL, NULL, {_sql_literal(self.player_name)},
  'confirmed', 'present', 'self', 'guest',
  false, now() - interval '20 minutes', now() - interval '15 minutes', {_sql_literal(owner_id)}
);

INSERT INTO public.charge_revisions (
  id, session_id, revision_no, source_version, status, allocation_total_vnd,
  fee_mode, reason, finalized_by, finalized_at
) VALUES (
  {_sql_literal(self.revision_id)}, {_sql_literal(self.session_id)}, 1, 1, 'active', 100000,
  'fixed', 'Synthetic instructions heap fixture', {_sql_literal(owner_id)}, now() - interval '10 minutes'
);

INSERT INTO public.session_charges (id, revision_id, session_player_id, amount_due_vnd)
VALUES ({_sql_literal(self.charge_id)}, {_sql_literal(self.revision_id)}, {_sql_literal(self.player_id)}, 100000);
COMMIT;"""

        db.exec_sql(insert_sql, fixture=self)

        bank_readback_fields = ''
        if self.include_club_bank:
            bank_readback_fields = (
                f", 'club_bank_count', (SELECT count(*) FROM public.club_bank_accounts WHERE id = {_sql_literal(self.club_bank_account_id)})"
                f", 'club_bank_for_club_count', (SELECT count(*) FROM public.club_bank_accounts WHERE club_id = {_sql_literal(self.club_id)})"
                f", 'club_bank_exact', EXISTS(SELECT 1 FROM public.club_bank_accounts WHERE id = {_sql_literal(self.club_bank_account_id)} AND club_id = {_sql_literal(self.club_id)} AND bank_code = {_sql_literal(self.club_bank_code)} AND account_number = {_sql_literal(self.club_account_number)} AND account_name = {_sql_literal(self.club_account_name)} AND status = 'active')"
                f", 'session_receiver_bank_unlinked', (SELECT receiver_club_bank_account_id IS NULL FROM public.sessions WHERE id = {_sql_literal(self.session_id)})"
            )
        readback = db.query_json(
            'SELECT json_build_object('
            "'readback_verify', true, "
            f"'ok', EXISTS(SELECT 1 FROM public.sessions WHERE id = {_sql_literal(self.session_id)}), "
            f"'club_private', (SELECT visibility = 'private' FROM public.clubs WHERE id = {_sql_literal(self.club_id)} AND description = {_sql_literal(self.marker_text)}), "
            f"'member_count', (SELECT count(*) FROM public.club_members WHERE club_id = {_sql_literal(self.club_id)}), "
            f"'session_owned', (SELECT description = {_sql_literal(self.marker_text)} FROM public.sessions WHERE id = {_sql_literal(self.session_id)}), "
            f"'player_guest', (SELECT user_id IS NULL AND registration_status = 'confirmed' FROM public.session_players WHERE id = {_sql_literal(self.player_id)}), "
            f"'billing_current', (SELECT public.session_billing_state({_sql_literal(self.session_id)}) = 'current'), "
            f"'canary_a', (SELECT receiver_snapshot->>'canary_instr_a' FROM public.sessions WHERE id = {_sql_literal(self.session_id)}), "
            f"'canary_b', (SELECT receiver_snapshot->>'canary_instr_b' FROM public.sessions WHERE id = {_sql_literal(self.session_id)})"
            f"{bank_readback_fields});"
        )
        bank_readback_ok = True
        if self.include_club_bank:
            bank_readback_ok = (
                int(readback.get('club_bank_count', -1)) == 1
                and int(readback.get('club_bank_for_club_count', -1)) == 1
                and readback.get('club_bank_exact') is True
                and readback.get('session_receiver_bank_unlinked') is True
            )
        if (readback.get('ok') is not True
                or readback.get('club_private') is not True
                or int(readback.get('member_count', 0)) != 1
                or readback.get('session_owned') is not True
                or readback.get('player_guest') is not True
                or readback.get('billing_current') is not True
                or readback.get('canary_a') != self.sentinel_1
                or readback.get('canary_b') != self.sentinel_2
                or not bank_readback_ok):
            self.error = 'post_insert_readback_mismatch'
            raise OwnershipError('fixture readback verification failed')

        mut = self.check_zero_mutations(db)
        if not mut['ok']:
            self.error = 'non_zero_mutations_at_create'
            raise FixtureError('newly created fixture has unexpected payment/ledger/audit mutations')

        self.created = True
        if validated_state:
            _write_private_json_atomic(validated_state, self.to_private_state())
        return self.public_metadata()

    def _query_ownership(self, db):
        bank_fields = ''
        if self.include_club_bank:
            bank_fields = (
                f", 'bank_id_count', (SELECT count(*) FROM public.club_bank_accounts WHERE id = {_sql_literal(self.club_bank_account_id)})"
                f", 'bank_club_count', (SELECT count(*) FROM public.club_bank_accounts WHERE club_id = {_sql_literal(self.club_id)})"
                f", 'bank_owned', coalesce((SELECT bool_and(club_id = {_sql_literal(self.club_id)} AND bank_code = {_sql_literal(self.club_bank_code)} AND account_number = {_sql_literal(self.club_account_number)} AND account_name = {_sql_literal(self.club_account_name)} AND status = 'active') FROM public.club_bank_accounts WHERE id = {_sql_literal(self.club_bank_account_id)}), false)"
            )
        return db.query_json(
            'SELECT json_build_object('
            "'ownership_check', true, "
            f"'session_count', (SELECT count(*) FROM public.sessions WHERE id = {_sql_literal(self.session_id)}), "
            f"'session_owned', coalesce((SELECT bool_and(description = {_sql_literal(self.marker_text)}) FROM public.sessions WHERE id = {_sql_literal(self.session_id)}), false), "
            f"'club_count', (SELECT count(*) FROM public.clubs WHERE id = {_sql_literal(self.club_id)}), "
            f"'club_owned', coalesce((SELECT bool_and(description = {_sql_literal(self.marker_text)}) FROM public.clubs WHERE id = {_sql_literal(self.club_id)}), false)"
            f"{bank_fields});"
        )

    def check_zero_mutations(self, db):
        """Assert zero payments, club_transactions, audit_events, and operation_requests on owned fixture."""
        own = self._query_ownership(db)
        if (int(own.get('session_count', 0)) != 1 or own.get('session_owned') is not True
                or int(own.get('club_count', 0)) != 1 or own.get('club_owned') is not True):
            raise OwnershipError('cannot verify zero mutations: fixture ownership mismatch')
        if self.include_club_bank and (
                int(own.get('bank_id_count', 0)) != 1
                or int(own.get('bank_club_count', 0)) != 1
                or own.get('bank_owned') is not True):
            raise OwnershipError('cannot verify zero mutations: fixture bank ownership mismatch')

        counts = db.query_json(
            'SELECT json_build_object('
            "'mutation_counts', true, "
            f"'payments', (SELECT count(*) FROM public.payments WHERE session_player_id IN (SELECT id FROM public.session_players WHERE session_id = {_sql_literal(self.session_id)})), "
            f"'club_transactions', (SELECT count(*) FROM public.club_transactions WHERE club_id = {_sql_literal(self.club_id)}), "
            f"'audit_events', (SELECT count(*) FROM public.audit_events WHERE session_id = {_sql_literal(self.session_id)} OR club_id = {_sql_literal(self.club_id)}), "
            f"'operation_requests', (SELECT count(*) FROM public.operation_requests WHERE result->>'session_id' = {_sql_literal(self.session_id)} OR result->>'club_id' = {_sql_literal(self.club_id)}));"
        )
        relevant = {
            'payments': int(counts.get('payments', -1)),
            'club_transactions': int(counts.get('club_transactions', -1)),
            'audit_events': int(counts.get('audit_events', -1)),
            'operation_requests': int(counts.get('operation_requests', -1)),
        }
        return {'ok': all(v == 0 for v in relevant.values()), 'counts': relevant}

    def cleanup(self, db, *, before_fingerprint=None, state_path=None):
        """Never throws. Verifies ownership, checks zero mutations, deletes child-first, checks fingerprint."""
        errors = []
        zero_mut_ok = False
        mutation_counts = None
        baseline_cmp = None
        baseline_equal = False

        if self.preflight_absent is False:
            errors.append(self.refused or 'preflight_collision_refused_delete')
            return self._build_receipt(
                zero_mutation_verified=False,
                mutation_counts=mutation_counts,
                baseline_equal=False,
                baseline_cmp=None,
                errors=errors,
            )

        try:
            own = self._query_ownership(db)
            s_count = int(own.get('session_count', 0))
            c_count = int(own.get('club_count', 0))
            s_owned = own.get('session_owned') is True
            c_owned = own.get('club_owned') is True
            b_id_count = int(own.get('bank_id_count', 0)) if self.include_club_bank else 0
            b_club_count = int(own.get('bank_club_count', 0)) if self.include_club_bank else 0
            b_owned = (own.get('bank_owned') is True) if self.include_club_bank else False

            bank_mismatch = False
            if self.include_club_bank:
                bank_mismatch = (
                    (b_id_count > 0 and (not b_owned or b_id_count != 1 or c_count != 1 or not c_owned))
                    or (b_club_count > 0 and (b_id_count != 1 or b_club_count != 1 or not b_owned))
                )

            if (s_count > 0 and not s_owned) or (c_count > 0 and not c_owned) or bank_mismatch:
                errors.append('ownership_mismatch_refused_delete')
            elif s_count > 0 or c_count > 0 or b_id_count > 0 or b_club_count > 0:
                if not self.insert_attempted:
                    errors.append('unattempted_fixture_found_refused_delete')
                else:
                    try:
                        mut = self.check_zero_mutations(db)
                        zero_mut_ok = mut['ok']
                        mutation_counts = mut['counts']
                        if not zero_mut_ok:
                            errors.append(f'unexpected_mutations_detected: {mutation_counts}')
                    except Exception as exc:
                        errors.append(f'zero_mutation_check_failed: {exc}')

                    bank_lock_sql = ''
                    bank_guard_sql = ''
                    bank_delete_sql = ''
                    if self.include_club_bank:
                        # Lock parent club first FOR UPDATE to block concurrent FK KEY SHARE insert/reparent
                        # until cleanup COMMITs, then lock matching bank rows FOR UPDATE before ownership checks.
                        bank_lock_sql = (
                            f"SELECT id FROM public.clubs WHERE id = {_sql_literal(self.club_id)} FOR UPDATE;\n"
                            f"SELECT id FROM public.club_bank_accounts WHERE id = {_sql_literal(self.club_bank_account_id)} OR club_id = {_sql_literal(self.club_id)} ORDER BY id FOR UPDATE;\n"
                        )
                        bank_guard_sql = f"""
  IF EXISTS (SELECT 1 FROM public.club_bank_accounts WHERE id = {_sql_literal(self.club_bank_account_id)} OR club_id = {_sql_literal(self.club_id)})
     AND ((SELECT count(*) FROM public.club_bank_accounts WHERE id = {_sql_literal(self.club_bank_account_id)}) <> 1
          OR (SELECT count(*) FROM public.club_bank_accounts WHERE club_id = {_sql_literal(self.club_id)}) <> 1
          OR NOT EXISTS (
            SELECT 1 FROM public.club_bank_accounts
            WHERE id = {_sql_literal(self.club_bank_account_id)}
              AND club_id = {_sql_literal(self.club_id)}
              AND bank_code = {_sql_literal(self.club_bank_code)}
              AND account_number = {_sql_literal(self.club_account_number)}
              AND account_name = {_sql_literal(self.club_account_name)}
              AND status = 'active'
          )
          OR NOT EXISTS (SELECT 1 FROM public.clubs WHERE id = {_sql_literal(self.club_id)} AND description = {_sql_literal(self.marker_text)})) THEN
    RAISE EXCEPTION 'ownership mismatch on club_bank_accounts';
  END IF;"""
                        bank_delete_sql = f"""DELETE FROM public.club_bank_accounts WHERE id = {_sql_literal(self.club_bank_account_id)} AND club_id = {_sql_literal(self.club_id)} AND bank_code = {_sql_literal(self.club_bank_code)} AND account_number = {_sql_literal(self.club_account_number)} AND account_name = {_sql_literal(self.club_account_name)} AND status = 'active';
DO $$ BEGIN
  IF EXISTS (SELECT 1 FROM public.club_bank_accounts WHERE id = {_sql_literal(self.club_bank_account_id)} OR club_id = {_sql_literal(self.club_id)}) THEN
    RAISE EXCEPTION 'club_bank_accounts still present before clubs delete';
  END IF;
END $$;
"""
                    delete_sql = f"""BEGIN;
{bank_lock_sql}DO $$ BEGIN
  IF EXISTS (SELECT 1 FROM public.sessions WHERE id = {_sql_literal(self.session_id)})
     AND NOT EXISTS (SELECT 1 FROM public.sessions WHERE id = {_sql_literal(self.session_id)} AND description = {_sql_literal(self.marker_text)}) THEN
    RAISE EXCEPTION 'ownership mismatch on sessions';
  END IF;
  IF EXISTS (SELECT 1 FROM public.clubs WHERE id = {_sql_literal(self.club_id)})
     AND NOT EXISTS (SELECT 1 FROM public.clubs WHERE id = {_sql_literal(self.club_id)} AND description = {_sql_literal(self.marker_text)}) THEN
    RAISE EXCEPTION 'ownership mismatch on clubs';
  END IF;{bank_guard_sql}
END $$;
DELETE FROM public.session_charges WHERE id = {_sql_literal(self.charge_id)} AND revision_id = {_sql_literal(self.revision_id)};
DELETE FROM public.charge_revisions WHERE id = {_sql_literal(self.revision_id)} AND session_id = {_sql_literal(self.session_id)};
DELETE FROM public.session_players WHERE id = {_sql_literal(self.player_id)} AND session_id = {_sql_literal(self.session_id)};
DELETE FROM public.sessions WHERE id = {_sql_literal(self.session_id)} AND description = {_sql_literal(self.marker_text)};
{bank_delete_sql}DELETE FROM public.club_members WHERE id = {_sql_literal(self.club_member_id)} AND club_id = {_sql_literal(self.club_id)};
DELETE FROM public.clubs WHERE id = {_sql_literal(self.club_id)} AND description = {_sql_literal(self.marker_text)};
COMMIT;"""
                    db.exec_sql(delete_sql, fixture=self)
                    self.removed = True
                    if self.include_club_bank and b_id_count > 0:
                        self.club_bank_removed = True
            else:
                zero_mut_ok = True
        except Exception as exc:
            errors.append(f'cleanup_exec_failed: {exc}')

        try:
            bank_rem_fields = ''
            if self.include_club_bank:
                bank_rem_fields = (
                    f", 'club_bank_accounts_by_id', (SELECT count(*) FROM public.club_bank_accounts WHERE id = {_sql_literal(self.club_bank_account_id)})"
                    f", 'club_bank_accounts_by_club', (SELECT count(*) FROM public.club_bank_accounts WHERE club_id = {_sql_literal(self.club_id)})"
                )
            rem = db.query_json(
                'SELECT json_build_object('
                "'remaining_counts', true, "
                f"'clubs', (SELECT count(*) FROM public.clubs WHERE id = {_sql_literal(self.club_id)}), "
                f"'club_members', (SELECT count(*) FROM public.club_members WHERE id = {_sql_literal(self.club_member_id)}), "
                f"'sessions', (SELECT count(*) FROM public.sessions WHERE id = {_sql_literal(self.session_id)}), "
                f"'session_players', (SELECT count(*) FROM public.session_players WHERE id = {_sql_literal(self.player_id)}), "
                f"'charge_revisions', (SELECT count(*) FROM public.charge_revisions WHERE id = {_sql_literal(self.revision_id)}), "
                f"'session_charges', (SELECT count(*) FROM public.session_charges WHERE id = {_sql_literal(self.charge_id)})"
                f"{bank_rem_fields});"
            )
            base_rem_total = sum(
                int(rem.get(k, 1))
                for k in ('clubs', 'club_members', 'sessions', 'session_players', 'charge_revisions', 'session_charges')
            )
            if self.include_club_bank:
                bank_rem_total = int(rem.get('club_bank_accounts_by_id', 1)) + int(rem.get('club_bank_accounts_by_club', 1))
                self.club_bank_verified_absent = (bank_rem_total == 0)
                rem_total = base_rem_total + bank_rem_total
            else:
                rem_total = base_rem_total
            self.verified_absent = (rem_total == 0)
            if not self.verified_absent:
                errors.append('rows_remaining_after_cleanup')
        except Exception as exc:
            self.verified_absent = False
            if self.include_club_bank:
                self.club_bank_verified_absent = False
            errors.append(f'verify_absent_failed: {exc}')

        use_before = before_fingerprint if before_fingerprint is not None else self.before_fingerprint
        if use_before is None or not _validate_fingerprint_shape(use_before):
            baseline_equal = False
            errors.append('missing_or_malformed_baseline_fingerprint')
        else:
            try:
                after_fp = db.fingerprint()
                baseline_cmp = compare_fingerprints(use_before, after_fp)
                baseline_equal = baseline_cmp['equal'] is True
                if not baseline_equal:
                    errors.append(f'baseline_fingerprint_mismatch: {baseline_cmp["mismatches"]}')
            except Exception as exc:
                baseline_equal = False
                errors.append(f'after_fingerprint_failed: {exc}')

        receipt = self._build_receipt(
            zero_mutation_verified=zero_mut_ok,
            mutation_counts=mutation_counts,
            baseline_equal=baseline_equal,
            baseline_cmp=baseline_cmp,
            errors=errors,
        )
        if state_path and receipt.get('disposable_instructions_cleanup_verified') is not True:
            self.error = receipt.get('error')
            try:
                _write_private_json_atomic(validate_state_path(state_path), self.to_private_state())
            except Exception:
                pass
        return receipt

    def _build_receipt(self, *, zero_mutation_verified, mutation_counts,
                       baseline_equal, baseline_cmp, errors):
        err_str = '; '.join(errors) if errors else self.error
        cleanup_verified = (
            self.verified_absent is True
            and zero_mutation_verified is True
            and baseline_equal is True
            and not err_str
            and (self.removed is True if self.created else True)
            and (
                (self.club_bank_verified_absent is True and (self.club_bank_removed is True if self.created else True))
                if self.include_club_bank else True
            )
        )
        receipt = {
            'disposable_instructions_club_id_sha256_12': sha12(self.club_id),
            'disposable_instructions_session_id_sha256_12': sha12(self.session_id),
            'canary_instr_a_sha256_12': sha12(self.sentinel_1),
            'canary_instr_b_sha256_12': sha12(self.sentinel_2),
            'disposable_instructions_club_created': self.created is True,
            'disposable_instructions_session_created': self.created is True,
            'disposable_instructions_removed': self.removed is True,
            'disposable_instructions_verified_absent': self.verified_absent is True,
            'disposable_instructions_cleanup_verified': cleanup_verified,
            'zero_mutation_verified': bool(zero_mutation_verified),
            'baseline_fingerprint_equal': bool(baseline_equal),
            'public_rows_schema_roles_equal': bool(baseline_equal),
            'auth_rows_excluded': True,
        }
        if self.include_club_bank:
            receipt.update({
                'disposable_instructions_club_bank_included': True,
                'disposable_instructions_club_bank_id_sha256_12': sha12(self.club_bank_account_id),
                'disposable_instructions_club_bank_account_number_sha256_12': sha12(self.club_account_number),
                'disposable_instructions_club_bank_account_name_sha256_12': sha12(self.club_account_name),
                'disposable_instructions_club_bank_created': self.created is True,
                'disposable_instructions_club_bank_removed': self.club_bank_removed is True,
                'disposable_instructions_club_bank_verified_absent': self.club_bank_verified_absent is True,
            })
        if mutation_counts is not None:
            receipt['mutation_counts'] = mutation_counts
        if baseline_cmp is not None:
            receipt['auth_refresh_sequence'] = baseline_cmp.get('auth_refresh_sequence', [])
            receipt['public_tables'] = baseline_cmp.get('public_tables')
            receipt['public_rows'] = baseline_cmp.get('public_rows')
            receipt['before_fingerprint_sha256'] = baseline_cmp.get('before_sha256')
            receipt['after_fingerprint_sha256'] = baseline_cmp.get('after_sha256')
        if err_str:
            receipt['error'] = err_str
        return receipt


def finalize_cli_cleanup(fixture, db, state_path):
    """Run DB cleanup, unlink recovery state only when verified absent, and fail closed if unlink fails."""
    receipt = fixture.cleanup(db, state_path=state_path)
    state_unlink_failed = False
    if receipt.get('disposable_instructions_cleanup_verified') is True and state_path.exists():
        try:
            state_path.unlink()
        except OSError as exc:
            state_unlink_failed = True
            receipt['recovery_state_error'] = f'state_unlink_failed: {exc}'
    receipt['recovery_state_retained'] = state_path.exists()
    ok = (
        receipt.get('disposable_instructions_cleanup_verified') is True
        and receipt['recovery_state_retained'] is False
        and not state_unlink_failed
    )
    return receipt, (0 if ok else 1)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='cmd', required=True)
    for name in ('create', 'check', 'cleanup'):
        p = sub.add_parser(name)
        p.add_argument('--config', required=True, help='Path to private local JSON config')
        p.add_argument('--state', required=True, help='Path to private state JSON outside repo/evidence')

    args = parser.parse_args(argv)
    cfg = load_and_validate_config(config_path=args.config)
    db = DockerPsqlClient(cfg['docker_exe'], cfg['db_container'])
    state_path = validate_state_path(args.state)

    if args.cmd == 'create':
        fixture = DisposableInstructionsFixture(
            owner_email=cfg['owner_email'],
            include_club_bank=cfg['include_club_bank'],
        )
        meta = fixture.create(db, state_path=state_path, capture_baseline=True)
        print(json.dumps(meta, indent=2))
        return 0

    fixture = DisposableInstructionsFixture.from_state_file(state_path)
    if args.cmd == 'check':
        res = fixture.check_zero_mutations(db)
        print(json.dumps(res, indent=2))
        return 0 if res['ok'] else 1

    receipt, exit_code = finalize_cli_cleanup(fixture, db, state_path)
    print(json.dumps(receipt, indent=2))
    return exit_code


if __name__ == '__main__':
    sys.exit(main())
