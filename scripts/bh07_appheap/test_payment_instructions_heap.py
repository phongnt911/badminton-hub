import hashlib
import json
import os
import re
import tempfile
import unittest
from unittest import mock
import uuid
from pathlib import Path

from scripts.bh07_appheap import disposable_instructions_fixture as fx
from scripts.bh07_appheap import verify_payment_instructions_heap as verifier


class FakeDb:
    """In-memory mock for DockerPsqlClient without touching any real DB or Docker."""

    def __init__(self, *, collision=False, fail_insert_after_commit=False,
                 foreign_session=False, mutation_counts=None,
                 bank_collision=False, foreign_bank=False,
                 fail_bank_readback=False, leave_bank_on_delete=False,
                 session_linked_to_bank=False, rollback_on_insert_error=False,
                 on_before_delete_locks=None):
        self.collision = collision
        self.fail_insert_after_commit = fail_insert_after_commit
        self.foreign_session = foreign_session
        self.bank_collision = bank_collision
        self.foreign_bank = foreign_bank
        self.fail_bank_readback = fail_bank_readback
        self.leave_bank_on_delete = leave_bank_on_delete
        self.session_linked_to_bank = session_linked_to_bank
        self.rollback_on_insert_error = rollback_on_insert_error
        self.on_before_delete_locks = on_before_delete_locks
        self.mutation_counts = mutation_counts or {
            'payments': 0,
            'club_transactions': 0,
            'audit_events': 0,
            'operation_requests': 0,
        }
        self.clubs = {}
        self.club_members = {}
        self.club_bank_accounts = {}
        self.sessions = {}
        self.session_players = {}
        self.charge_revisions = {}
        self.session_charges = {}
        self.sql_log = []
        self.owner_id = '11111111-1111-4111-8111-111111111111'
        self.venue_id = 'cccccccc-3333-4333-8333-333333333333'
        self.fp_calls = 0
        self.public_override = None

    def query_json(self, sql):
        self.sql_log.append(('QUERY', sql))
        if "'ok'" in sql and 'readback_verify' not in sql and 'collision_count' not in sql:
            return {'ok': 1}
        if 'FROM auth.users' in sql:
            return {'owner_id': self.owner_id, 'venue_id': self.venue_id}
        if 'collision_count' in sql:
            if self.collision:
                return {'collision_count': 1}
            if 'public.club_bank_accounts' in sql:
                if self.bank_collision:
                    return {'collision_count': 1}
                for row in self.club_bank_accounts.values():
                    if f"id = '{row['id']}'" in sql or f"club_id = '{row['club_id']}'" in sql:
                        return {'collision_count': 1}
            return {'collision_count': 0}
        if 'ownership_check' in sql:
            rows = list(self.sessions.values())
            if self.foreign_session:
                res = {'session_count': 1, 'session_owned': False, 'club_count': 1, 'club_owned': False}
                if 'bank_id_count' in sql:
                    res.update({
                        'bank_id_count': len(self.club_bank_accounts),
                        'bank_club_count': len(self.club_bank_accounts),
                        'bank_owned': False,
                    })
                return res
            c = list(self.clubs.values())[0] if self.clubs else {}
            s = rows[0] if rows else {}
            res = {
                'session_count': len(self.sessions),
                'session_owned': bool(rows) and s.get('description') == s.get('_expected_marker'),
                'club_count': len(self.clubs),
                'club_owned': bool(self.clubs) and c.get('description') == c.get('_expected_marker'),
            }
            if 'bank_id_count' in sql:
                m_bid = re.search(r"'bank_id_count',\s*\(SELECT count\(\*\) FROM public\.club_bank_accounts WHERE id = '([^']+)'\)", sql)
                m_cid = re.search(r"'bank_club_count',\s*\(SELECT count\(\*\) FROM public\.club_bank_accounts WHERE club_id = '([^']+)'\)", sql)
                q_bid = m_bid.group(1) if m_bid else None
                q_cid = m_cid.group(1) if m_cid else None
                id_rows = [r for r in self.club_bank_accounts.values() if r['id'] == q_bid]
                club_rows = [r for r in self.club_bank_accounts.values() if r['club_id'] == q_cid]
                bank_owned = False
                if len(id_rows) == 1 and not self.foreign_bank:
                    r = id_rows[0]
                    bank_owned = (
                        r.get('status') == 'active'
                        and f"club_id = '{r['club_id']}'" in sql
                        and f"bank_code = '{r['bank_code']}'" in sql
                        and f"account_number = '{r['account_number']}'" in sql
                        and f"account_name = '{r['account_name']}'" in sql
                        and "status = 'active'" in sql
                    )
                res.update({
                    'bank_id_count': len(id_rows),
                    'bank_club_count': len(club_rows),
                    'bank_owned': bank_owned,
                })
            return res
        if 'readback_verify' in sql:
            if not self.sessions or not self.clubs:
                return {'ok': False}
            s = list(self.sessions.values())[0]
            res = {
                'ok': True,
                'club_private': list(self.clubs.values())[0]['visibility'] == 'private',
                'member_count': len(self.club_members),
                'session_owned': True,
                'player_guest': list(self.session_players.values())[0]['user_id'] is None,
                'billing_current': True,
                'canary_a': s['receiver_snapshot']['canary_instr_a'],
                'canary_b': s['receiver_snapshot']['canary_instr_b'],
            }
            if 'public.club_bank_accounts' in sql:
                m_bid = re.search(r"'club_bank_count',\s*\(SELECT count\(\*\) FROM public\.club_bank_accounts WHERE id = '([^']+)'\)", sql)
                m_cid = re.search(r"'club_bank_for_club_count',\s*\(SELECT count\(\*\) FROM public\.club_bank_accounts WHERE club_id = '([^']+)'\)", sql)
                q_bid = m_bid.group(1) if m_bid else None
                q_cid = m_cid.group(1) if m_cid else None
                id_rows = [r for r in self.club_bank_accounts.values() if r['id'] == q_bid]
                club_rows = [r for r in self.club_bank_accounts.values() if r['club_id'] == q_cid]
                exact = False
                if len(id_rows) == 1 and not self.fail_bank_readback:
                    r = id_rows[0]
                    exact = (
                        r.get('status') == 'active'
                        and f"club_id = '{r['club_id']}'" in sql
                        and f"bank_code = '{r['bank_code']}'" in sql
                        and f"account_number = '{r['account_number']}'" in sql
                        and f"account_name = '{r['account_name']}'" in sql
                        and "status = 'active'" in sql
                    )
                res.update({
                    'club_bank_count': len(id_rows),
                    'club_bank_for_club_count': len(club_rows),
                    'club_bank_exact': exact,
                    'session_receiver_bank_unlinked': not self.session_linked_to_bank,
                })
            return res
        if 'mutation_counts' in sql:
            return dict(self.mutation_counts)
        if 'remaining_counts' in sql:
            total = (len(self.clubs) + len(self.club_members) + len(self.sessions)
                     + len(self.session_players) + len(self.charge_revisions) + len(self.session_charges))
            res = {
                'clubs': len(self.clubs),
                'club_members': len(self.club_members),
                'sessions': len(self.sessions),
                'session_players': len(self.session_players),
                'charge_revisions': len(self.charge_revisions),
                'session_charges': len(self.session_charges),
                'total': total,
            }
            if 'public.club_bank_accounts' in sql:
                m_bid = re.search(r"'club_bank_accounts_by_id',\s*\(SELECT count\(\*\) FROM public\.club_bank_accounts WHERE id = '([^']+)'\)", sql)
                m_cid = re.search(r"'club_bank_accounts_by_club',\s*\(SELECT count\(\*\) FROM public\.club_bank_accounts WHERE club_id = '([^']+)'\)", sql)
                q_bid = m_bid.group(1) if m_bid else None
                q_cid = m_cid.group(1) if m_cid else None
                by_id = sum(1 for r in self.club_bank_accounts.values() if r['id'] == q_bid)
                by_club = sum(1 for r in self.club_bank_accounts.values() if r['club_id'] == q_cid)
                res['club_bank_accounts_by_id'] = by_id
                res['club_bank_accounts_by_club'] = by_club
                res['total'] = total + by_id + by_club
            return res
        return {}

    def apply_fixture_insert(self, fixture, sql=''):
        self.clubs[fixture.club_id] = {
            'id': fixture.club_id, 'visibility': 'private',
            'description': fixture.marker_text, '_expected_marker': fixture.marker_text,
        }
        self.club_members[fixture.club_member_id] = {'id': fixture.club_member_id, 'club_id': fixture.club_id}
        if getattr(fixture, 'include_club_bank', False) and 'INSERT INTO public.club_bank_accounts' in sql:
            assert sql.index('INSERT INTO public.clubs') < sql.index('INSERT INTO public.club_bank_accounts')
            assert sql.index('INSERT INTO public.club_bank_accounts') < sql.index('INSERT INTO public.sessions')
            self.club_bank_accounts[fixture.club_bank_account_id] = {
                'id': fixture.club_bank_account_id,
                'club_id': fixture.club_id,
                'bank_code': fixture.club_bank_code,
                'account_number': fixture.club_account_number,
                'account_name': fixture.club_account_name,
                'status': 'active',
            }
        self.sessions[fixture.session_id] = {
            'id': fixture.session_id, 'club_id': fixture.club_id,
            'description': fixture.marker_text, '_expected_marker': fixture.marker_text,
            'receiver_snapshot': {
                'bank_code': 'VCB',
                'account_number': '9999000012345678',
                'account_name': 'BH07 INSTR RECEIVER',
                'canary_instr_a': fixture.sentinel_1,
                'canary_instr_b': fixture.sentinel_2,
            },
        }
        self.session_players[fixture.player_id] = {'id': fixture.player_id, 'user_id': None}
        self.charge_revisions[fixture.revision_id] = {'id': fixture.revision_id, 'session_id': fixture.session_id}
        self.session_charges[fixture.charge_id] = {'id': fixture.charge_id, 'revision_id': fixture.revision_id}

    def exec_sql(self, sql, fixture=None):
        self.sql_log.append(('EXEC', sql))
        if 'INSERT INTO public.clubs' in sql and fixture is not None:
            if not (self.fail_insert_after_commit and self.rollback_on_insert_error):
                self.apply_fixture_insert(fixture, sql)
            if self.fail_insert_after_commit:
                raise RuntimeError('simulated uncertain commit timeout after server commit')
        elif 'DELETE FROM public.sessions' in sql:
            if self.on_before_delete_locks is not None:
                hook = self.on_before_delete_locks
                self.on_before_delete_locks = None
                hook(self, sql)
            if self.foreign_session:
                raise RuntimeError('ownership mismatch refused delete')
            if 'DELETE FROM public.club_bank_accounts' in sql:
                if self.foreign_bank:
                    raise RuntimeError('ownership mismatch on club_bank_accounts')
                m_lock_club = re.search(
                    r"SELECT id FROM public\.clubs WHERE id = '([^']+)' FOR UPDATE;",
                    sql,
                )
                m_lock_bank = re.search(
                    r"SELECT id FROM public\.club_bank_accounts WHERE id = '([^']+)' OR club_id = '([^']+)' ORDER BY id FOR UPDATE;",
                    sql,
                )
                assert m_lock_club is not None and m_lock_bank is not None
                q_cid = m_lock_club.group(1)
                q_bid = m_lock_bank.group(1)
                assert m_lock_bank.group(2) == q_cid
                assert (
                    sql.index('BEGIN;')
                    < m_lock_club.start()
                    < m_lock_bank.start()
                    < sql.index('DO $$')
                    < sql.index('DELETE FROM public.sessions')
                    < sql.index('DELETE FROM public.club_bank_accounts')
                    < sql.index('DELETE FROM public.clubs')
                    < sql.index('COMMIT;')
                )
                assert sql.count('BEGIN;') == 1 and sql.count('COMMIT;') == 1
                id_rows = [r for r in self.club_bank_accounts.values() if r['id'] == q_bid]
                club_rows = [r for r in self.club_bank_accounts.values() if r['club_id'] == q_cid]
                if id_rows or club_rows:
                    if len(id_rows) != 1 or len(club_rows) != 1 or id_rows[0] is not club_rows[0]:
                        raise RuntimeError('ownership mismatch on club_bank_accounts')
                    r = id_rows[0]
                    c_row = self.clubs.get(q_cid)
                    if (
                        r.get('status') != 'active'
                        or not c_row
                        or c_row.get('description') != c_row.get('_expected_marker')
                        or f"club_id = '{r['club_id']}'" not in sql
                        or f"bank_code = '{r['bank_code']}'" not in sql
                        or f"account_number = '{r['account_number']}'" not in sql
                        or f"account_name = '{r['account_name']}'" not in sql
                        or "status = 'active'" not in sql
                    ):
                        raise RuntimeError('ownership mismatch on club_bank_accounts')
                if not self.leave_bank_on_delete:
                    for bid in list(self.club_bank_accounts):
                        r = self.club_bank_accounts[bid]
                        if (
                            r.get('status') == 'active'
                            and f"id = '{r['id']}'" in sql
                            and f"club_id = '{r['club_id']}'" in sql
                            and f"bank_code = '{r['bank_code']}'" in sql
                            and f"account_number = '{r['account_number']}'" in sql
                            and f"account_name = '{r['account_name']}'" in sql
                            and "status = 'active'" in sql
                        ):
                            del self.club_bank_accounts[bid]
            self.session_charges.clear()
            self.charge_revisions.clear()
            self.session_players.clear()
            self.sessions.clear()
            self.club_members.clear()
            self.clubs.clear()

    def fingerprint(self):
        self.fp_calls += 1
        pub = self.public_override if (self.fp_calls > 1 and self.public_override is not None) else {
            'public.clubs': {'rows': 2, 'sha256': 'a' * 64},
            'public.payments': {'rows': 1, 'sha256': 'b' * 64},
        }
        return {
            'public': pub,
            'schema': 'c' * 64,
            'roles': [{'rolname': 'authenticated'}],
            'sequences': [
                {'schemaname': 'auth', 'sequencename': 'refresh_tokens_id_seq', 'last_value': 10 + self.fp_calls},
                {'schemaname': 'public', 'sequencename': 'other_seq', 'last_value': 1},
            ],
        }


class TestFixtureLifecycle(unittest.TestCase):
    def test_config_rejects_non_loopback_or_wrong_container(self):
        bad_configs = [
            {'db_container': 'supabase_db_badminton-hub', 'supabase_url': 'http://127.0.0.1:54321'},
            {'db_container': 'bh07-android-db', 'supabase_url': 'https://example.supabase.co'},
            {'db_container': 'bh07-android-db', 'supabase_url': 'http://127.0.0.1:54322'},
        ]
        for cfg in bad_configs:
            with self.assertRaises(ValueError):
                fx.load_and_validate_config(config_dict=cfg)

        valid = fx.load_and_validate_config(config_dict={
            'db_container': 'bh07-android-db',
            'supabase_url': 'http://127.0.0.1:54321',
            'docker_exe': 'docker',
            'owner_email': 'ownera@example.test',
        })
        self.assertEqual(valid['db_container'], 'bh07-android-db')

    def test_collision_refused_and_never_deletes(self):
        db = FakeDb(collision=True)
        fixture = fx.DisposableInstructionsFixture()
        with tempfile.TemporaryDirectory() as tmp:
            state_path = Path(tmp) / 'state.json'
            with self.assertRaises(fx.FixtureCollisionError):
                fixture.create(db, state_path=state_path)
            self.assertFalse(any(kind == 'EXEC' for kind, _ in db.sql_log))
            receipt = fixture.cleanup(db)
            self.assertFalse(receipt['disposable_instructions_club_created'])
            self.assertFalse(receipt['disposable_instructions_removed'])
            self.assertFalse(receipt['disposable_instructions_verified_absent'])
            self.assertFalse(receipt['disposable_instructions_cleanup_verified'])
            self.assertFalse(any('DELETE' in sql for _, sql in db.sql_log))

    def test_uncertain_commit_is_owned_and_cleaned_up(self):
        db = FakeDb(fail_insert_after_commit=True)
        fixture = fx.DisposableInstructionsFixture()
        with tempfile.TemporaryDirectory() as tmp:
            state_path = Path(tmp) / 'state.json'
            before_fp = db.fingerprint()
            with self.assertRaises(RuntimeError):
                fixture.create(db, state_path=state_path)
            self.assertTrue(state_path.exists())
            saved = json.loads(state_path.read_text(encoding='utf-8'))
            self.assertTrue(saved['insert_attempted'])
            self.assertFalse(saved['created'])

            reloaded = fx.DisposableInstructionsFixture.from_state_file(state_path)
            receipt = reloaded.cleanup(db, before_fingerprint=before_fp)
            self.assertTrue(receipt['disposable_instructions_removed'])
            self.assertTrue(receipt['disposable_instructions_verified_absent'])
            self.assertTrue(receipt['disposable_instructions_cleanup_verified'])
            self.assertTrue(receipt['baseline_fingerprint_equal'])
            raw = json.dumps(receipt)
            self.assertNotIn(fixture.sentinel_1, raw)
            self.assertNotIn(fixture.sentinel_2, raw)

    def test_ownership_mismatch_refuses_delete(self):
        db = FakeDb(foreign_session=True)
        fixture = fx.DisposableInstructionsFixture()
        db.sessions[fixture.session_id] = {'id': fixture.session_id, 'description': 'someone-elses-row'}
        fixture.preflight_absent = True
        fixture.insert_attempted = True
        fixture.created = True
        receipt = fixture.cleanup(db)
        self.assertFalse(receipt['disposable_instructions_removed'])
        self.assertFalse(receipt['disposable_instructions_verified_absent'])
        self.assertFalse(receipt['disposable_instructions_cleanup_verified'])
        self.assertIn('ownership', receipt['error'].lower())

    def test_zero_mutation_and_fingerprint_gates(self):
        db = FakeDb()
        fixture = fx.DisposableInstructionsFixture()
        with tempfile.TemporaryDirectory() as tmp:
            before_fp = db.fingerprint()
            fixture.create(db, state_path=Path(tmp) / 'state.json')
            db.mutation_counts['payments'] = 1
            mut = fixture.check_zero_mutations(db)
            self.assertFalse(mut['ok'])
            db.public_override = {'public.clubs': {'rows': 2, 'sha256': 'a' * 64},
                                  'public.payments': {'rows': 2, 'sha256': 'd' * 64}}
            receipt = fixture.cleanup(db, before_fingerprint=before_fp)
            self.assertFalse(receipt['zero_mutation_verified'])
            self.assertFalse(receipt['baseline_fingerprint_equal'])
            self.assertFalse(receipt['disposable_instructions_cleanup_verified'])

    def test_missing_empty_malformed_baseline_still_cleans_and_fails_receipt(self):
        # IH6: Missing, empty, or malformed baseline must STILL delete owned rows and fail receipt
        for bad_fp in (None, {}, {'public': {}}, 'malformed'):
            db = FakeDb()
            fixture = fx.DisposableInstructionsFixture()
            with tempfile.TemporaryDirectory() as tmp:
                state_path = Path(tmp) / f'state_{type(bad_fp).__name__}.json'
                fixture.create(db, state_path=state_path, capture_baseline=False)
                self.assertEqual(len(db.sessions), 1)
                receipt = fixture.cleanup(db, before_fingerprint=bad_fp)
                self.assertTrue(receipt['disposable_instructions_removed'])
                self.assertTrue(receipt['disposable_instructions_verified_absent'])
                self.assertFalse(receipt['baseline_fingerprint_equal'])
                self.assertFalse(receipt['public_rows_schema_roles_equal'])
                self.assertFalse(receipt['disposable_instructions_cleanup_verified'])
                self.assertEqual(len(db.sessions), 0)

    def test_compare_fingerprints_allows_only_refresh_seq_last_value(self):
        # IH6: Other auth sequences must match; only auth.refresh_tokens_id_seq.last_value may advance
        before = {
            'public': {'public.clubs': {'rows': 2, 'sha256': 'a' * 64}},
            'schema': 'b' * 64,
            'roles': [{'rolname': 'authenticated'}],
            'sequences': [
                {'schemaname': 'auth', 'sequencename': 'refresh_tokens_id_seq', 'last_value': 10, 'increment_by': 1},
                {'schemaname': 'auth', 'sequencename': 'users_id_seq', 'last_value': 5, 'increment_by': 1},
                {'schemaname': 'public', 'sequencename': 'other_seq', 'last_value': 1},
            ],
        }
        ok_after = json.loads(json.dumps(before))
        ok_after['sequences'][0]['last_value'] = 12
        self.assertTrue(fx.compare_fingerprints(before, ok_after)['equal'])

        bad_after = json.loads(json.dumps(ok_after))
        bad_after['sequences'][1]['last_value'] = 6
        cmp_bad = fx.compare_fingerprints(before, bad_after)
        self.assertFalse(cmp_bad['equal'])

    def test_recovery_state_exclusive_atomic_and_outside_repo(self):
        # IH5: Helper rejects inside-repo state path, exclusive write refuses existing state,
        # and cleanup failure retains recovery state on disk.
        with tempfile.TemporaryDirectory() as tmp:
            db = FakeDb()
            fixture = fx.DisposableInstructionsFixture()
            existing = Path(tmp) / 'already.json'
            existing.write_text('{}', encoding='utf-8')
            with self.assertRaises(FileExistsError):
                fixture.create(db, state_path=existing)

            inside_repo = Path(fx.__file__).resolve().parent / 'bad_state.json'
            with self.assertRaises(ValueError):
                fx.validate_state_path(inside_repo)

            # Simulate cleanup CLI failure retaining recovery state
            db_foreign = FakeDb(foreign_session=True)
            cfg_path = Path(tmp) / 'cfg.json'
            cfg_path.write_text(json.dumps({
                'db_container': 'bh07-android-db',
                'supabase_url': 'http://127.0.0.1:54321',
                'docker_exe': 'docker',
                'owner_email': 'ownera@example.test',
            }), encoding='utf-8')
            state_path = Path(tmp) / 'recovery.json'
            fx2 = fx.DisposableInstructionsFixture()
            db_foreign.sessions[fx2.session_id] = {'id': fx2.session_id, 'description': 'someone-elses-row'}
            fx2.preflight_absent = True
            fx2.insert_attempted = True
            fx2.created = True
            fx._write_private_json_exclusive(state_path, fx2.to_private_state())
            receipt = fx2.cleanup(db_foreign, before_fingerprint=db_foreign.fingerprint(), state_path=state_path)
            self.assertFalse(receipt['disposable_instructions_cleanup_verified'])
            self.assertTrue(state_path.exists())

    def test_include_club_bank_malformed_flag_and_default_off_compatibility(self):
        base_cfg = {
            'db_container': 'bh07-android-db',
            'supabase_url': 'http://127.0.0.1:54321',
            'docker_exe': 'docker',
            'owner_email': 'ownera@example.test',
        }
        default_cfg = fx.load_and_validate_config(config_dict=base_cfg)
        self.assertIs(default_cfg['include_club_bank'], False)

        for bad_flag in ('true', 'false', 1, 0, None, []):
            with self.assertRaises(ValueError):
                fx.load_and_validate_config(config_dict={**base_cfg, 'include_club_bank': bad_flag})
            with self.assertRaises(ValueError):
                fx.DisposableInstructionsFixture(include_club_bank=bad_flag)

        with tempfile.TemporaryDirectory() as tmp:
            db = FakeDb()
            fixture = fx.DisposableInstructionsFixture()
            self.assertIs(fixture.include_club_bank, False)
            meta = fixture.public_metadata()
            self.assertNotIn('club_bank_included', meta)
            self.assertNotIn('club_bank', meta)

            state_path = Path(tmp) / 'default_state.json'
            fixture.create(db, state_path=state_path, capture_baseline=True)
            state_data = json.loads(state_path.read_text(encoding='utf-8'))
            self.assertNotIn('include_club_bank', state_data)
            self.assertEqual(len(db.club_bank_accounts), 0)
            self.assertFalse(any('club_bank_accounts' in sql for _, sql in db.sql_log))

            receipt = fixture.cleanup(db, state_path=state_path)
            self.assertTrue(receipt['disposable_instructions_cleanup_verified'])
            self.assertFalse(any(k.startswith('disposable_instructions_club_bank_') for k in receipt))
            self.assertFalse(any(k.startswith(('disposable_bank_', 'disposable_ledger_')) for k in receipt))

            # Backward-compatible load of historical state lacking include_club_bank
            legacy_path = Path(tmp) / 'legacy_state.json'
            legacy_fx = fx.DisposableInstructionsFixture()
            legacy_state = legacy_fx.to_private_state()
            legacy_state.pop('include_club_bank', None)
            legacy_path.write_text(json.dumps(legacy_state), encoding='utf-8')
            reloaded_legacy = fx.DisposableInstructionsFixture.from_state_file(legacy_path)
            self.assertIs(reloaded_legacy.include_club_bank, False)

            # Reject malformed persisted include_club_bank states
            bad_states = [
                {**legacy_state, 'include_club_bank': 'true'},
                {**legacy_state, 'include_club_bank': 1},
                {**legacy_state, 'include_club_bank': None},
                {**legacy_state, 'include_club_bank': True},  # missing bank fields
                {
                    **legacy_state,
                    'include_club_bank': True,
                    'club_bank_account_id': str(uuid.uuid4()),
                    'club_bank_code': 'VCB',
                    'club_account_number': 9999000012345678,
                    'club_account_name': 'BH07 SYNTH BANK',
                },
                {
                    **legacy_state,
                    'include_club_bank': False,
                    'club_bank_account_id': str(uuid.uuid4()),
                },
            ]
            for idx, bad_state in enumerate(bad_states):
                bad_path = Path(tmp) / f'bad_state_{idx}.json'
                bad_path.write_text(json.dumps(bad_state), encoding='utf-8')
                with self.assertRaises(ValueError):
                    fx.DisposableInstructionsFixture.from_state_file(bad_path)

    def test_include_club_bank_opt_in_create_readback_reload_and_redaction(self):
        import contextlib
        import io

        with tempfile.TemporaryDirectory() as tmp:
            cfg_path = Path(tmp) / 'cfg.json'
            cfg_path.write_text(json.dumps({
                'db_container': 'bh07-android-db',
                'supabase_url': 'http://127.0.0.1:54321',
                'docker_exe': 'docker',
                'owner_email': 'ownera@example.test',
                'include_club_bank': True,
            }), encoding='utf-8')
            state_path = Path(tmp) / 'bank_state.json'
            db = FakeDb()

            with mock.patch.object(fx, 'DockerPsqlClient', return_value=db):
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf):
                    rc = fx.main(['create', '--config', str(cfg_path), '--state', str(state_path)])
                self.assertEqual(rc, 0)
                meta = json.loads(buf.getvalue())

                state_raw = json.loads(state_path.read_text(encoding='utf-8'))
                self.assertIs(state_raw['include_club_bank'], True)
                self.assertIs(state_raw['created'], True)
                self.assertIs(state_raw['insert_attempted'], True)
                bank_id = state_raw['club_bank_account_id']
                uuid.UUID(bank_id)
                self.assertEqual(state_raw['club_bank_code'], 'VCB')
                self.assertRegex(state_raw['club_account_number'], r'^99990000\d{8}$')
                self.assertTrue(state_raw['club_account_name'].startswith('BH07 SYNTH BANK '))

                self.assertIs(meta.get('club_bank_included'), True)
                self.assertEqual(meta['club_bank']['club_bank_account_id_sha256_12'], fx.sha12(bank_id))
                self.assertEqual(meta['club_bank']['bank_code_sha256_12'], fx.sha12(state_raw['club_bank_code']))
                self.assertEqual(meta['club_bank']['account_number_sha256_12'], fx.sha12(state_raw['club_account_number']))
                self.assertEqual(meta['club_bank']['account_name_sha256_12'], fx.sha12(state_raw['club_account_name']))

                meta_json = json.dumps(meta)
                for secret in (
                    bank_id,
                    state_raw['club_account_number'],
                    state_raw['club_account_name'],
                    state_raw['sentinel_1'],
                    state_raw['sentinel_2'],
                ):
                    self.assertNotIn(secret, meta_json)

                self.assertEqual(len(db.club_bank_accounts), 1)
                self.assertEqual(db.club_bank_accounts[bank_id]['status'], 'active')
                reloaded = fx.DisposableInstructionsFixture.from_state_file(state_path)
                self.assertIs(reloaded.include_club_bank, True)
                self.assertEqual(reloaded.club_bank_account_id, bank_id)
                self.assertEqual(reloaded.club_account_number, state_raw['club_account_number'])

                buf_chk = io.StringIO()
                with contextlib.redirect_stdout(buf_chk):
                    rc_chk = fx.main(['check', '--config', str(cfg_path), '--state', str(state_path)])
                self.assertEqual(rc_chk, 0)

                buf_cln = io.StringIO()
                with contextlib.redirect_stdout(buf_cln):
                    rc_cln = fx.main(['cleanup', '--config', str(cfg_path), '--state', str(state_path)])
                self.assertEqual(rc_cln, 0)
                receipt = json.loads(buf_cln.getvalue())

            self.assertFalse(state_path.exists())
            self.assertEqual(len(db.club_bank_accounts), 0)
            self.assertEqual(len(db.clubs), 0)
            self.assertIs(receipt['disposable_instructions_club_bank_included'], True)
            self.assertEqual(receipt['disposable_instructions_club_bank_id_sha256_12'], fx.sha12(bank_id))
            self.assertEqual(receipt['disposable_instructions_club_bank_account_number_sha256_12'], fx.sha12(state_raw['club_account_number']))
            self.assertEqual(receipt['disposable_instructions_club_bank_account_name_sha256_12'], fx.sha12(state_raw['club_account_name']))
            self.assertIs(receipt['disposable_instructions_club_bank_created'], True)
            self.assertIs(receipt['disposable_instructions_club_bank_removed'], True)
            self.assertIs(receipt['disposable_instructions_club_bank_verified_absent'], True)
            self.assertIs(receipt['disposable_instructions_cleanup_verified'], True)
            self.assertFalse(any(k.startswith(('disposable_bank_', 'disposable_ledger_')) for k in receipt))

            receipt_json = json.dumps(receipt)
            for secret in (
                bank_id,
                state_raw['club_account_number'],
                state_raw['club_account_name'],
                state_raw['sentinel_1'],
                state_raw['sentinel_2'],
            ):
                self.assertNotIn(secret, receipt_json)

            # Post-insert readback mismatch or accidental session link must fail closed
            for bad_db in (FakeDb(fail_bank_readback=True), FakeDb(session_linked_to_bank=True)):
                fx_bad = fx.DisposableInstructionsFixture(include_club_bank=True)
                with self.assertRaises(fx.OwnershipError):
                    fx_bad.create(bad_db, state_path=Path(tmp) / f'rb_{id(bad_db)}.json')

    def test_include_club_bank_uuid_collision_refused_and_never_deletes(self):
        with tempfile.TemporaryDirectory() as tmp:
            # Generic bank_collision flag
            db = FakeDb(bank_collision=True)
            fixture = fx.DisposableInstructionsFixture(include_club_bank=True)
            with self.assertRaises(fx.FixtureCollisionError):
                fixture.create(db, state_path=Path(tmp) / 'col_flag.json')
            self.assertFalse(any(kind == 'EXEC' for kind, _ in db.sql_log))
            receipt = fixture.cleanup(db)
            self.assertIs(receipt['disposable_instructions_club_bank_included'], True)
            self.assertFalse(receipt['disposable_instructions_club_bank_created'])
            self.assertFalse(receipt['disposable_instructions_club_bank_removed'])
            self.assertFalse(receipt['disposable_instructions_club_bank_verified_absent'])
            self.assertFalse(receipt['disposable_instructions_cleanup_verified'])
            self.assertFalse(any('DELETE' in sql for _, sql in db.sql_log))

            # Preexisting bank row matching bank_id or club_id must never be deleted
            for key_kind in ('bank_id', 'club_id'):
                db2 = FakeDb()
                fx2 = fx.DisposableInstructionsFixture(include_club_bank=True)
                existing_id = fx2.club_bank_account_id if key_kind == 'bank_id' else str(uuid.uuid4())
                existing_club = fx2.club_id if key_kind == 'club_id' else str(uuid.uuid4())
                db2.club_bank_accounts[existing_id] = {
                    'id': existing_id,
                    'club_id': existing_club,
                    'bank_code': 'TCB',
                    'account_number': '190011112222',
                    'account_name': 'REAL CLUB BANK',
                    'status': 'active',
                }
                with self.assertRaises(fx.FixtureCollisionError):
                    fx2.create(db2, state_path=Path(tmp) / f'col_{key_kind}.json')
                self.assertFalse(any(kind == 'EXEC' for kind, _ in db2.sql_log))
                rec2 = fx2.cleanup(db2)
                self.assertFalse(rec2['disposable_instructions_cleanup_verified'])
                self.assertIn(existing_id, db2.club_bank_accounts)
                self.assertFalse(any('DELETE' in sql for _, sql in db2.sql_log))

    def test_include_club_bank_uncertain_commit_recovery_and_rollback(self):
        with tempfile.TemporaryDirectory() as tmp:
            # (a) Timeout after commit on DB server -> recovery reloads bank fields and cleans child-first
            db_committed = FakeDb(fail_insert_after_commit=True)
            state_a = Path(tmp) / 'uncertain_committed.json'
            fx_a = fx.DisposableInstructionsFixture(include_club_bank=True)
            with self.assertRaises(RuntimeError):
                fx_a.create(db_committed, state_path=state_a, capture_baseline=True)
            self.assertTrue(state_a.exists())
            reloaded_a = fx.DisposableInstructionsFixture.from_state_file(state_a)
            self.assertIs(reloaded_a.include_club_bank, True)
            self.assertIs(reloaded_a.insert_attempted, True)
            self.assertIs(reloaded_a.created, False)
            self.assertEqual(len(db_committed.club_bank_accounts), 1)
            receipt_a, exit_a = fx.finalize_cli_cleanup(reloaded_a, db_committed, state_a)
            self.assertEqual(exit_a, 0)
            self.assertFalse(state_a.exists())
            self.assertEqual(len(db_committed.club_bank_accounts), 0)
            self.assertEqual(len(db_committed.clubs), 0)
            self.assertIs(receipt_a['disposable_instructions_club_bank_included'], True)
            self.assertIs(receipt_a['disposable_instructions_club_bank_created'], False)
            self.assertIs(receipt_a['disposable_instructions_club_bank_removed'], True)
            self.assertIs(receipt_a['disposable_instructions_club_bank_verified_absent'], True)
            self.assertIs(receipt_a['disposable_instructions_cleanup_verified'], True)

            # (b) Transaction rolled back on DB server -> zero DELETEs, absent verified
            db_rolled = FakeDb(fail_insert_after_commit=True, rollback_on_insert_error=True)
            state_b = Path(tmp) / 'uncertain_rolledback.json'
            fx_b = fx.DisposableInstructionsFixture(include_club_bank=True)
            with self.assertRaises(RuntimeError):
                fx_b.create(db_rolled, state_path=state_b, capture_baseline=True)
            reloaded_b = fx.DisposableInstructionsFixture.from_state_file(state_b)
            receipt_b, exit_b = fx.finalize_cli_cleanup(reloaded_b, db_rolled, state_b)
            self.assertEqual(exit_b, 0)
            self.assertFalse(state_b.exists())
            self.assertFalse(any('DELETE' in sql for _, sql in db_rolled.sql_log))
            self.assertIs(receipt_b['disposable_instructions_club_bank_created'], False)
            self.assertIs(receipt_b['disposable_instructions_club_bank_removed'], False)
            self.assertIs(receipt_b['disposable_instructions_club_bank_verified_absent'], True)
            self.assertIs(receipt_b['disposable_instructions_cleanup_verified'], True)

    def test_include_club_bank_foreign_reparented_extra_and_tampered_refuses_delete(self):
        with tempfile.TemporaryDirectory() as tmp:
            def _make_created(name):
                db = FakeDb()
                st = Path(tmp) / f'{name}.json'
                f = fx.DisposableInstructionsFixture(include_club_bank=True)
                f.create(db, state_path=st, capture_baseline=True)
                db.sql_log.clear()
                return db, st, f

            # (a) Reparented bank row: same bank_id, different club_id
            db_a, st_a, fx_a = _make_created('reparented')
            db_a.club_bank_accounts[fx_a.club_bank_account_id]['club_id'] = str(uuid.uuid4())
            with self.assertRaises(fx.OwnershipError):
                fx_a.check_zero_mutations(db_a)
            rec_a, code_a = fx.finalize_cli_cleanup(fx_a, db_a, st_a)
            self.assertEqual(code_a, 1)
            self.assertFalse(rec_a['disposable_instructions_cleanup_verified'])
            self.assertIn('ownership', rec_a.get('error', ''))
            self.assertTrue(st_a.exists())
            self.assertEqual(len(db_a.club_bank_accounts), 1)
            self.assertEqual(len(db_a.clubs), 1)
            self.assertFalse(any('DELETE' in sql for _, sql in db_a.sql_log))

            # (b1) Foreign bank row attached to our club_id (different id, alongside ours -> ON DELETE CASCADE hazard)
            db_b1, st_b1, fx_b1 = _make_created('extra_same_club')
            extra_id = str(uuid.uuid4())
            db_b1.club_bank_accounts[extra_id] = {
                'id': extra_id, 'club_id': fx_b1.club_id,
                'bank_code': 'ACB', 'account_number': '555566667777', 'account_name': 'REAL OTHER BANK', 'status': 'inactive',
            }
            with self.assertRaises(fx.OwnershipError):
                fx_b1.check_zero_mutations(db_b1)
            rec_b1, code_b1 = fx.finalize_cli_cleanup(fx_b1, db_b1, st_b1)
            self.assertEqual(code_b1, 1)
            self.assertFalse(rec_b1['disposable_instructions_cleanup_verified'])
            self.assertIn('ownership', rec_b1.get('error', ''))
            self.assertIn(extra_id, db_b1.club_bank_accounts)
            self.assertIn(fx_b1.club_id, db_b1.clubs)
            self.assertFalse(any('DELETE' in sql for _, sql in db_b1.sql_log))

            # (b2) Only foreign bank row attached to our club_id (ours missing)
            db_b2, st_b2, fx_b2 = _make_created('only_foreign_same_club')
            del db_b2.club_bank_accounts[fx_b2.club_bank_account_id]
            db_b2.club_bank_accounts[extra_id] = {
                'id': extra_id, 'club_id': fx_b2.club_id,
                'bank_code': 'ACB', 'account_number': '555566667777', 'account_name': 'REAL OTHER BANK', 'status': 'active',
            }
            rec_b2, code_b2 = fx.finalize_cli_cleanup(fx_b2, db_b2, st_b2)
            self.assertEqual(code_b2, 1)
            self.assertFalse(rec_b2['disposable_instructions_cleanup_verified'])
            self.assertIn(extra_id, db_b2.club_bank_accounts)
            self.assertIn(fx_b2.club_id, db_b2.clubs)
            self.assertFalse(any('DELETE' in sql for _, sql in db_b2.sql_log))

            # (c) Tampered bank fields (account_number, bank_code, account_name, status)
            for field_name, fake_val in (
                ('account_number', '1111222233334444'),
                ('bank_code', 'BIDV'),
                ('account_name', 'TAMPERED NAME'),
                ('status', 'inactive'),
            ):
                db_c, st_c, fx_c = _make_created(f'tamper_{field_name}')
                db_c.club_bank_accounts[fx_c.club_bank_account_id][field_name] = fake_val
                with self.assertRaises(fx.OwnershipError):
                    fx_c.check_zero_mutations(db_c)
                rec_c, code_c = fx.finalize_cli_cleanup(fx_c, db_c, st_c)
                self.assertEqual(code_c, 1)
                self.assertFalse(rec_c['disposable_instructions_cleanup_verified'])
                self.assertIn('ownership', rec_c.get('error', ''))
                self.assertEqual(len(db_c.club_bank_accounts), 1)
                self.assertFalse(any('DELETE' in sql for _, sql in db_c.sql_log))

            # (d) Orphan bank row when parent club is missing
            db_d, st_d, fx_d = _make_created('orphan_bank')
            db_d.clubs.clear()
            db_d.sessions.clear()
            with self.assertRaises(fx.OwnershipError):
                fx_d.check_zero_mutations(db_d)
            rec_d, code_d = fx.finalize_cli_cleanup(fx_d, db_d, st_d)
            self.assertEqual(code_d, 1)
            self.assertFalse(rec_d['disposable_instructions_cleanup_verified'])
            self.assertIn('ownership', rec_d.get('error', ''))
            self.assertEqual(len(db_d.club_bank_accounts), 1)
            self.assertFalse(any('DELETE' in sql for _, sql in db_d.sql_log))

    def test_include_club_bank_child_first_absence_and_baseline_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            # Verify child-first DELETE order + in-transaction SQL guard before deleting clubs
            db = FakeDb()
            st = Path(tmp) / 'order.json'
            fixture = fx.DisposableInstructionsFixture(include_club_bank=True)
            fixture.create(db, state_path=st, capture_baseline=True)
            rec_ok, exit_ok = fx.finalize_cli_cleanup(fixture, db, st)
            self.assertEqual(exit_ok, 0)
            self.assertIs(rec_ok['disposable_instructions_cleanup_verified'], True)
            delete_sqls = [sql for kind, sql in db.sql_log if kind == 'EXEC' and 'DELETE FROM public.club_bank_accounts' in sql]
            self.assertEqual(len(delete_sqls), 1)
            dsql = delete_sqls[0]
            pos_sess = dsql.index('DELETE FROM public.sessions')
            pos_bank = dsql.index('DELETE FROM public.club_bank_accounts')
            pos_club = dsql.index('DELETE FROM public.clubs')
            self.assertLess(pos_sess, pos_bank)
            self.assertLess(pos_bank, pos_club)
            between = dsql[pos_bank:pos_club]
            self.assertIn('public.club_bank_accounts', between)
            self.assertIn('RAISE EXCEPTION', between)

            # Verify absence verification fails closed if bank row persists after DELETE
            db_rem = FakeDb(leave_bank_on_delete=True)
            st_rem = Path(tmp) / 'leave_bank.json'
            fx_rem = fx.DisposableInstructionsFixture(include_club_bank=True)
            fx_rem.create(db_rem, state_path=st_rem, capture_baseline=True)
            rec_rem, exit_rem = fx.finalize_cli_cleanup(fx_rem, db_rem, st_rem)
            self.assertEqual(exit_rem, 1)
            self.assertTrue(st_rem.exists())
            self.assertFalse(rec_rem['disposable_instructions_club_bank_verified_absent'])
            self.assertFalse(rec_rem['disposable_instructions_verified_absent'])
            self.assertFalse(rec_rem['disposable_instructions_cleanup_verified'])
            self.assertIn('rows_remaining_after_cleanup', rec_rem.get('error', ''))

            # Verify baseline fingerprint drift/missing still deletes owned bank + club and fails receipt
            db_fp = FakeDb()
            db_fp.public_override = {
                'public.clubs': {'rows': 2, 'sha256': 'a' * 64},
                'public.payments': {'rows': 1, 'sha256': 'b' * 64},
                'public.club_bank_accounts': {'rows': 1, 'sha256': 'd' * 64},
            }
            st_fp = Path(tmp) / 'fp_drift.json'
            fx_fp = fx.DisposableInstructionsFixture(include_club_bank=True)
            fx_fp.create(db_fp, state_path=st_fp, capture_baseline=True)
            rec_fp, exit_fp = fx.finalize_cli_cleanup(fx_fp, db_fp, st_fp)
            self.assertEqual(exit_fp, 1)
            self.assertTrue(st_fp.exists())
            self.assertEqual(len(db_fp.club_bank_accounts), 0)
            self.assertEqual(len(db_fp.clubs), 0)
            self.assertIs(rec_fp['disposable_instructions_club_bank_removed'], True)
            self.assertIs(rec_fp['disposable_instructions_club_bank_verified_absent'], True)
            self.assertIs(rec_fp['disposable_instructions_removed'], True)
            self.assertIs(rec_fp['disposable_instructions_verified_absent'], True)
            self.assertIs(rec_fp['baseline_fingerprint_equal'], False)
            self.assertIs(rec_fp['disposable_instructions_cleanup_verified'], False)

    def test_include_club_bank_row_lock_order_and_toctou_interleaving_control(self):
        """Verify SQL FOR UPDATE lock order, default-off omission, and mocked pre-lock TOCTOU refusal.

        Note: FakeDb tests SQL statement placement and post-precheck in-transaction re-evaluation in
        memory; it does NOT prove PostgreSQL multi-connection FOR UPDATE / KEY SHARE lock blocking.
        """
        with tempfile.TemporaryDirectory() as tmp:
            # 1) Default-off cleanup SQL preserves exact lock-free behavior (zero FOR UPDATE)
            db_off = FakeDb()
            st_off = Path(tmp) / 'off_locks.json'
            fx_off = fx.DisposableInstructionsFixture(include_club_bank=False)
            fx_off.create(db_off, state_path=st_off, capture_baseline=True)
            rec_off, code_off = fx.finalize_cli_cleanup(fx_off, db_off, st_off)
            self.assertEqual(code_off, 0)
            self.assertTrue(rec_off['disposable_instructions_cleanup_verified'])
            self.assertFalse(any('FOR UPDATE' in sql for _, sql in db_off.sql_log))
            self.assertFalse(any('club_bank_accounts' in sql for _, sql in db_off.sql_log))

            # 2) Opt-in cleanup SQL places parent club lock immediately after BEGIN, then bank lock,
            #    then DO $$ re-evaluation guard, then child-first deletes through COMMIT
            db_on = FakeDb()
            st_on = Path(tmp) / 'on_locks.json'
            fx_on = fx.DisposableInstructionsFixture(include_club_bank=True)
            fx_on.create(db_on, state_path=st_on, capture_baseline=True)
            rec_on, code_on = fx.finalize_cli_cleanup(fx_on, db_on, st_on)
            self.assertEqual(code_on, 0)
            self.assertTrue(rec_on['disposable_instructions_cleanup_verified'])

            ownership_sqls = [sql for kind, sql in db_on.sql_log if kind == 'QUERY' and 'ownership_check' in sql]
            self.assertTrue(ownership_sqls)
            self.assertTrue(all("status = 'active'" in sql for sql in ownership_sqls))

            del_sqls = [sql for kind, sql in db_on.sql_log if kind == 'EXEC' and 'DELETE FROM public.club_bank_accounts' in sql]
            self.assertEqual(len(del_sqls), 1)
            dsql = del_sqls[0]
            club_lock_stmt = f"SELECT id FROM public.clubs WHERE id = '{fx_on.club_id}' FOR UPDATE;"
            bank_lock_stmt = (
                f"SELECT id FROM public.club_bank_accounts WHERE id = '{fx_on.club_bank_account_id}' "
                f"OR club_id = '{fx_on.club_id}' ORDER BY id FOR UPDATE;"
            )
            self.assertIn(club_lock_stmt, dsql)
            self.assertIn(bank_lock_stmt, dsql)
            pos_begin = dsql.index('BEGIN;')
            pos_club_lock = dsql.index(club_lock_stmt)
            pos_bank_lock = dsql.index(bank_lock_stmt)
            pos_do_guard = dsql.index('DO $$')
            pos_del_sess = dsql.index('DELETE FROM public.sessions')
            pos_del_bank = dsql.index('DELETE FROM public.club_bank_accounts')
            pos_del_club = dsql.index('DELETE FROM public.clubs')
            pos_commit = dsql.index('COMMIT;')
            self.assertEqual(dsql[pos_begin + len('BEGIN;'):pos_club_lock].strip(), '')
            self.assertEqual(dsql[pos_club_lock + len(club_lock_stmt):pos_bank_lock].strip(), '')
            self.assertLess(pos_bank_lock, pos_do_guard)
            self.assertLess(pos_do_guard, pos_del_sess)
            self.assertLess(pos_del_sess, pos_del_bank)
            self.assertLess(pos_del_bank, pos_del_club)
            self.assertLess(pos_del_club, pos_commit)
            self.assertEqual(dsql.count('BEGIN;'), 1)
            self.assertEqual(dsql.count('COMMIT;'), 1)
            guard_block = dsql[pos_do_guard:pos_del_sess]
            self.assertIn("status = 'active'", guard_block)
            del_bank_stmt = dsql[pos_del_bank:dsql.index(';', pos_del_bank) + 1]
            self.assertIn("status = 'active'", del_bank_stmt)

            # 3) Honest mocked TOCTOU interleaving control: concurrent write occurs AFTER
            #    _query_ownership & check_zero_mutations pass, right as delete_sql enters.
            for mode in ('concurrent_foreign_insert', 'concurrent_status_inactive', 'concurrent_reparent'):
                def _make_hook(interleave_mode, fixture_obj):
                    def _hook(mock_db, _sql):
                        if interleave_mode == 'concurrent_foreign_insert':
                            extra_bid = str(uuid.uuid4())
                            mock_db.club_bank_accounts[extra_bid] = {
                                'id': extra_bid,
                                'club_id': fixture_obj.club_id,
                                'bank_code': 'ACB',
                                'account_number': '555566667777',
                                'account_name': 'CONCURRENT OTHER BANK',
                                'status': 'inactive',
                            }
                        elif interleave_mode == 'concurrent_status_inactive':
                            mock_db.club_bank_accounts[fixture_obj.club_bank_account_id]['status'] = 'inactive'
                        elif interleave_mode == 'concurrent_reparent':
                            mock_db.club_bank_accounts[fixture_obj.club_bank_account_id]['club_id'] = str(uuid.uuid4())
                    return _hook

                db_i = FakeDb()
                st_i = Path(tmp) / f'interleave_{mode}.json'
                fx_i = fx.DisposableInstructionsFixture(include_club_bank=True)
                fx_i.create(db_i, state_path=st_i, capture_baseline=True)
                db_i.on_before_delete_locks = _make_hook(mode, fx_i)

                expected_banks = 2 if mode == 'concurrent_foreign_insert' else 1
                rec_i, code_i = fx.finalize_cli_cleanup(fx_i, db_i, st_i)
                self.assertEqual(code_i, 1, mode)
                self.assertTrue(st_i.exists(), mode)
                self.assertFalse(rec_i['disposable_instructions_cleanup_verified'], mode)
                self.assertFalse(rec_i['disposable_instructions_removed'], mode)
                self.assertFalse(rec_i['disposable_instructions_club_bank_removed'], mode)
                self.assertIn('ownership mismatch on club_bank_accounts', rec_i.get('error', ''), mode)
                self.assertEqual(len(db_i.club_bank_accounts), expected_banks, mode)
                self.assertEqual(len(db_i.clubs), 1, mode)
                self.assertEqual(len(db_i.sessions), 1, mode)


def _make_synthetic_main_js(*, instructions_field='_instructions', receiver_snapshot_field='receiverSnapshot',
                            include_provider_value=True, include_field_use=True):
    fp_ctor = (
        f'FinanceProvider: function FinanceProvider(t0, t1) {{\n'
        f'  var _ = this;\n'
        f'  _._finance_provider$_repository = t0;\n'
        f'  _.auth = t1;\n'
        f'  _.{instructions_field} = _._instructionsPlayerId = _._instructionsSessionId = null;\n'
        f'}}'
    )
    pi_ctor = (
        f'PaymentInstructions: function PaymentInstructions(t0, t1, t2, t3, t4, t5, t6) {{\n'
        f'  var _ = this;\n'
        f'  _.sessionId = t0;\n'
        f'  _.playerId = t1;\n'
        f'  _.{receiver_snapshot_field} = t6;\n'
        f'}}'
    )
    field_use = ''
    if include_field_use:
        field_use = (
            f'A.FinanceProvider.prototype = {{\n'
            f'  _resetInstructions$0: function() {{ this.{instructions_field} = null; }},\n'
            f'  fetchPaymentInstructions$1: function(s) {{\n'
            f'    var x = A.PaymentInstructions_fromJson(s);\n'
            f'    this.{instructions_field} = x;\n'
            f'    return this.{instructions_field};\n'
            f'  }},\n'
            f'  get$paymentInstructions: function() {{ return this.{instructions_field}; }}\n'
            f'}};\n'
            f'A.PaymentInstructions.prototype = {{\n'
            f'  get$bankCode: function() {{ return this.{receiver_snapshot_field}.$index(0, "bank_code"); }}\n'
            f'}};\n'
            f'A.PaymentInstructions_fromJson = function(j) {{\n'
            f'  return new A.PaymentInstructions(j["session_id"], j["player_id"], null, null, null, null, j["receiver_snapshot"]);\n'
            f'}};\n'
            f'var rpc = "get_payment_instructions";\n'
        )
    provider_use = ''
    if include_provider_value:
        provider_use = (
            'A._CreateInheritedProviderState = function() { this._provider$_value = null; };\n'
            'A._CreateInheritedProviderState.prototype = { getValue: function() { return this._provider$_value; } };\n'
        )
    js_text = f'var A = {{\n  {fp_ctor},\n  {pi_ctor}\n}};\n{field_use}{provider_use}'
    return js_text, fp_ctor, pi_ctor


def _make_binding_payload(main_js_text, fp_ctor, pi_ctor, *,
                          instructions_field='_instructions',
                          receiver_snapshot_field='receiverSnapshot'):
    main_sha = hashlib.sha256(main_js_text.encode('utf-8')).hexdigest()
    fp_sha = hashlib.sha256(fp_ctor.encode('utf-8')).hexdigest()
    pi_sha = hashlib.sha256(pi_ctor.encode('utf-8')).hexdigest()
    core = {
        'finance_provider': {
            'constructor_name': 'FinanceProvider',
            'constructor_sha256': fp_sha,
            'field_use_verified': True,
            'instructions_field': instructions_field,
            'repository_field': '_finance_provider$_repository',
        },
        'main_dart_js_sha256': main_sha,
        'payment_instructions': {
            'constructor_name': 'PaymentInstructions',
            'constructor_sha256': pi_sha,
            'field_use_verified': True,
            'receiver_snapshot_field': receiver_snapshot_field,
        },
        'provider_holder_edge': '_provider$_value',
    }
    binding_sha = hashlib.sha256(json.dumps(core, sort_keys=True, separators=(',', ':')).encode('utf-8')).hexdigest()
    sanitized = {'ok': True, **core, 'binding_sha256': binding_sha}
    companion = {
        'ok': True,
        'version': '1.0',
        'main_dart_js_sha256': main_sha,
        'provider_holder_edge': '_provider$_value',
        'provider_holder_snippets': [
            'this._provider$_value = null;',
            'return this._provider$_value;',
        ],
        'finance_provider': {
            **core['finance_provider'],
            'constructor_snippet': fp_ctor,
            'field_use_snippets': [
                f'this.{instructions_field} = x;',
                f'this.{instructions_field} = null;',
                f'return this.{instructions_field};',
            ],
        },
        'payment_instructions': {
            **core['payment_instructions'],
            'constructor_snippet': pi_ctor,
            'field_use_snippets': [
                f'return this.{receiver_snapshot_field}.$index(0, "bank_code");',
            ],
        },
        'binding_sha256': binding_sha,
    }
    return sanitized, companion


def _make_path(reachable, frames=None, *, exact=True, path_sha_override=None):
    if not reachable:
        return {'reachable': False, 'string_nodes': 0, 'exact': False}
    use_frames = frames or [
        'root',
        'internal:(Global handles) -> synthetic',
        'property:a -> object',
        'property:canary_instr_a -> string',
    ]
    digest = path_sha_override or hashlib.sha256('\n'.join(use_frames).encode('utf-8')).hexdigest()[:12]
    return {
        'reachable': True,
        'root_kind': 'global_handles',
        'path_len': len(use_frames) - 1,
        'frames': use_frames,
        'path_sha256_12': digest,
        'string_nodes': 1,
        'exact': exact,
    }


def _make_scan(present_map, frames_override=None, time_origin=12345.6, exact_override=None, path_sha_override=None):
    classes = {
        'probe': {'rendered': False, 'distinctive': True, 'scope': 'control'},
        'canary_instr_a': {'rendered': False, 'distinctive': True, 'scope': 'finance'},
        'canary_instr_b': {'rendered': False, 'distinctive': True, 'scope': 'finance'},
    }
    sentinels = {}
    paths = {}
    for name, cls in classes.items():
        pres = bool(present_map.get(name, False))
        sentinels[name] = {'present': pres, 'occurrences': 1 if pres else 0, **cls}
        frames = (frames_override or {}).get(name) if pres else None
        ex = (exact_override or {}).get(name, True)
        sha_ov = (path_sha_override or {}).get(name)
        paths[name] = _make_path(pres, frames=frames, exact=ex, path_sha_override=sha_ov)
    return {
        'ok': True,
        'time_origin': time_origin,
        'size_bytes': 8192,
        'sha256_12': 'abcdef012345',
        'sentinels': sentinels,
        'paths': paths,
    }


def _build_valid_bundle(bundle_dir: Path, *, sentinels_raw=None, frames_override=None,
                        dto_proven=False, scoped_verdict='PASS_NARROW_RPC_PAYLOAD_ONLY',
                        owner_b_present=True, owner_b_reachable=True,
                        cohost_a_present=False, cleanup_ok=True,
                        zero_mut=True, baseline_eq=True,
                        extra_log_line=None, claim_entire_model=False,
                        main_js_sha=None, source_binding=None,
                        companion_binding=None, exact_override=None,
                        path_sha_override=None):
    raw = sentinels_raw or {
        'canary_instr_a': str(uuid.uuid4()),
        'canary_instr_b': str(uuid.uuid4()),
        'probe': 'BH07INSTRPROBE-12345678',
    }
    c1_owner = _make_scan(
        {'probe': True, 'canary_instr_a': True, 'canary_instr_b': owner_b_present},
        frames_override, exact_override=exact_override, path_sha_override=path_sha_override,
    )
    if not owner_b_reachable:
        c1_owner['paths']['canary_instr_b'] = _make_path(False)
    c2_owner = _make_scan(
        {'probe': True, 'canary_instr_a': True, 'canary_instr_b': True},
        frames_override, exact_override=exact_override, path_sha_override=path_sha_override,
    )

    summary = {
        'gate': 'V2b — PaymentInstructions synthetic receiverSnapshot heap retention',
        'coverage_profile': 'payment_instructions',
        'status': 'RUN',
        'verdict': 'PASS',
        'measurement_surface': 'Flutter Web profile build + Chrome DevTools Protocol HeapProfiler (V8 heap snapshot)',
        'oracle': 'synthetic receiverSnapshot UUIDs scanned in live V8 heap snapshots via heap_oracle.py',
        'tested_source_sha': 'a' * 40,
        'git_dirty': False,
        'same_document_across_cycles': True,
        'instructions_coverage_contract': {
            'version': '1.0',
            'required_owner_load': ['canary_instr_a', 'canary_instr_b'],
            'scope': 'synthetic_receiver_snapshot_map_values_only',
            'dto': 'PaymentInstructions',
            'provider_field': 'FinanceProvider._instructions',
            'actor_isolation': 'owner_only_disposable_club',
            'payment_mutation_forbidden': True,
            'rendered_strings_unattributed': ['bank_code', 'account_number', 'account_name', 'reference'],
        },
        'attribution_assessment': {
            'root_reachability_measured': True,
            'dto_attribution_proven': dto_proven,
            'attribution_status': 'proven_artifact_bound' if dto_proven else 'unproven_under_minification',
            'claim_scope': (
                'entire_model_clean'
                if claim_entire_model
                else ('payment_instructions_receiver_snapshot_only' if dto_proven else 'narrow_rpc_payload_retention_only')
            ),
            'scoped_verdict': scoped_verdict,
            'payment_instructions_coverage_gate': 'PASS' if dto_proven else 'UNKNOWN/NOT_RUN',
            'proven_frames': (frames_override or {}).get('canary_instr_a') if dto_proven else [],
            **({'source_binding': source_binding} if source_binding is not None else {}),
        },
        'environment': {
            'build': {
                'mode': 'profile',
                'reused': True,
                'explicit_provenance_verified': True,
                'started_at': '2026-11-13T08:00:00.000Z',
                'artifacts': {'index.html': '1' * 64, 'main.dart.js': main_js_sha or ('2' * 64)},
                'served_match': True,
            },
            'chrome': 'Chrome/155.0.0.0',
            'flutter': 'Flutter 3.47.6',
        },
        'sentinels': {
            name: {
                'available': True,
                'sha256_12': hashlib.sha256(val.encode('utf-8')).hexdigest()[:12],
                'length': len(val),
                'kind': 'synthetic test value',
                'rendered': False,
                'distinctive': True,
                'scope': 'control' if name == 'probe' else 'finance',
            }
            for name, val in raw.items()
        },
        'cycles': [
            {
                'cycle': 1,
                'actor': 'cohost',
                'same_document': True,
                'time_origin': 12345.6,
                'epochs': {
                    'baseline': _make_scan({'probe': True}),
                    'owner_active': c1_owner,
                    'post_logout': _make_scan({'probe': True}),
                    'post_actor': _make_scan({'probe': True, 'canary_instr_a': cohost_a_present}),
                },
                'verdict': {'verdict': 'PASS', 'findings': [], 'notes': [], 'residual_risks': [], 'epochs_checked': 4},
            },
            {
                'cycle': 2,
                'actor': 'member',
                'same_document': True,
                'time_origin': 12345.6,
                'epochs': {
                    'baseline': _make_scan({'probe': True}),
                    'owner_active': c2_owner,
                    'post_logout': _make_scan({'probe': True}),
                    'post_actor': _make_scan({'probe': True}),
                },
                'verdict': {'verdict': 'PASS', 'findings': [], 'notes': [], 'residual_risks': [], 'epochs_checked': 4},
            },
        ],
        'notes': [],
        'residual_risks': [],
        'findings': [],
        'cleanup': {
            'ok': cleanup_ok,
            'dump_dir_outside_repo': True,
            'raw_snapshots_remaining': 0,
            'dumps_dir_removed': True,
            'chrome_profile_dir_removed': True,
            'recovery_state_retained': False,
            'disposable_instructions_club_created': True,
            'disposable_instructions_session_created': True,
            'disposable_instructions_removed': True,
            'disposable_instructions_verified_absent': True,
            'disposable_instructions_cleanup_verified': True,
            'canary_instr_a_sha256_12': hashlib.sha256(raw['canary_instr_a'].encode('utf-8')).hexdigest()[:12],
            'canary_instr_b_sha256_12': hashlib.sha256(raw['canary_instr_b'].encode('utf-8')).hexdigest()[:12],
            'zero_mutation_verified': zero_mut,
            'baseline_fingerprint_equal': baseline_eq,
            'public_rows_schema_roles_equal': baseline_eq,
            'auth_rows_excluded': True,
        },
    }

    report_lines = [
        '# V2b — PaymentInstructions synthetic receiverSnapshot heap retention',
        '',
        '- Status: **RUN** (verdict PASS)',
        f'- Scoped verdict: **{scoped_verdict}**',
        '- Attribution: root reachability measured; DTO-level attribution unproven under minification',
        '- Claim scope: narrow RPC payload retention only (synthetic receiverSnapshot keys only; no whole-model claim)',
        '',
    ]
    log_lines = ['[2026-11-13T08:00:00Z] run started']
    if extra_log_line:
        log_lines.append(extra_log_line)

    bundle_dir.mkdir(parents=True, exist_ok=True)
    (bundle_dir / 'summary.json').write_bytes((json.dumps(summary, indent=2) + '\n').encode('utf-8'))
    (bundle_dir / 'report.md').write_bytes(('\n'.join(report_lines) + '\n').encode('utf-8'))
    (bundle_dir / 'run.log').write_bytes(('\n'.join(log_lines) + '\n').encode('utf-8'))
    manifest_files = ['summary.json', 'report.md', 'run.log']
    if companion_binding is not None:
        (bundle_dir / 'source_binding.json').write_bytes((json.dumps(companion_binding, indent=2) + '\n').encode('utf-8'))
        manifest_files.append('source_binding.json')

    manifest = []
    for name in sorted(manifest_files):
        digest = hashlib.sha256((bundle_dir / name).read_bytes()).hexdigest()
        manifest.append(f'{digest}  {name}')
    (bundle_dir / 'hashes.sha256').write_bytes(('\n'.join(manifest) + '\n').encode('utf-8'))
    return raw


class TestInstructionsVerifier(unittest.TestCase):
    def test_positive_narrow_scoped_pass_and_strict_dto_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            bdir = Path(tmp) / 'bundle'
            _build_valid_bundle(bdir)
            problems, assessment = verifier.verify(bdir)
            self.assertEqual(problems, [])
            self.assertEqual(assessment['scoped_verdict'], 'PASS_NARROW_RPC_PAYLOAD_ONLY')
            # Fail-closed when DTO attribution is demanded under minification
            strict_problems, _ = verifier.verify(bdir, require_dto_attribution=True)
            self.assertTrue(any('attribution' in p.lower() for p in strict_problems))

    def test_mutant_missing_owner_canary_or_unreachable(self):
        with tempfile.TemporaryDirectory() as tmp:
            b1 = Path(tmp) / 'b1'
            _build_valid_bundle(b1, owner_b_present=False)
            p1, _ = verifier.verify(b1)
            self.assertTrue(any('canary_instr_b' in p for p in p1))

            b2 = Path(tmp) / 'b2'
            _build_valid_bundle(b2, owner_b_reachable=False)
            p2, _ = verifier.verify(b2)
            self.assertTrue(any('canary_instr_b' in p and 'reachable' in p for p in p2))

    def test_mutant_post_actor_leak_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            b = Path(tmp) / 'bundle'
            _build_valid_bundle(b, cohost_a_present=True)
            problems, _ = verifier.verify(b)
            self.assertTrue(any('canary_instr_a' in p for p in problems))

    def test_mutant_raw_sentinel_leak_in_log_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            b = Path(tmp) / 'bundle'
            leak_uuid = str(uuid.uuid4())
            _build_valid_bundle(
                b,
                sentinels_raw={'canary_instr_a': leak_uuid, 'canary_instr_b': str(uuid.uuid4()), 'probe': 'PROBE-123'},
                extra_log_line=f'leaked={leak_uuid}',
            )
            problems, _ = verifier.verify(b)
            self.assertTrue(any('raw value of sentinel canary_instr_a' in p for p in problems))

    def test_mutant_cleanup_and_baseline_failures(self):
        with tempfile.TemporaryDirectory() as tmp:
            b = Path(tmp) / 'bundle'
            _build_valid_bundle(b, cleanup_ok=False, zero_mut=False, baseline_eq=False)
            problems, _ = verifier.verify(b)
            self.assertTrue(any('zero_mutation_verified' in p for p in problems))
            self.assertTrue(any('baseline_fingerprint_equal' in p for p in problems))

    def test_mutant_fake_dto_attribution_or_entire_model_claim_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            b1 = Path(tmp) / 'b1'
            _build_valid_bundle(b1, dto_proven=True, scoped_verdict='PASS_DTO_ATTRIBUTED')
            p1, _ = verifier.verify(b1)
            self.assertTrue(any('dto_attribution_proven' in p or 'attribution' in p.lower() for p in p1))

            b2 = Path(tmp) / 'b2'
            _build_valid_bundle(b2, claim_entire_model=True)
            p2, _ = verifier.verify(b2)
            self.assertTrue(any('claim_scope' in p or 'entire_model' in p for p in p2))

    def _real_safe_frames(self, instructions_field='_instructions'):
        frames_a = [
            'root',
            'element -> synthetic',
            'property:___InheritedProviderScopeElement__delega -> object',
            'property:_provider$_value -> object',
            f'property:{instructions_field} -> object',
            'property:receiverSnapshot -> object',
            'property:_strings -> object',
            'property:canary_instr_a -> object',
            'property:hashMapCellValue -> string',
        ]
        frames_b = [
            'root',
            'element -> synthetic',
            'property:___InheritedProviderScopeElement__delega -> object',
            'property:_provider$_value -> object',
            f'property:{instructions_field} -> object',
            'property:receiverSnapshot -> object',
            'property:_last -> object',
            'property:hashMapCellValue -> string',
        ]
        return {'canary_instr_a': frames_a, 'canary_instr_b': frames_b}

    def test_positive_dto_attributed_with_exact_source_binding(self):
        js_text, fp_ctor, pi_ctor = _make_synthetic_main_js(instructions_field='_instructions')
        sanitized, companion = _make_binding_payload(js_text, fp_ctor, pi_ctor, instructions_field='_instructions')
        frames = self._real_safe_frames('_instructions')
        with tempfile.TemporaryDirectory() as tmp:
            build_dir = Path(tmp) / 'build_web'
            build_dir.mkdir()
            (build_dir / 'main.dart.js').write_bytes(js_text.encode('utf-8'))
            b = Path(tmp) / 'bundle'
            _build_valid_bundle(
                b,
                frames_override=frames,
                dto_proven=True,
                scoped_verdict='PASS_DTO_ATTRIBUTED',
                main_js_sha=sanitized['main_dart_js_sha256'],
                source_binding=sanitized,
                companion_binding=companion,
            )
            problems, assessment = verifier.verify(b, require_dto_attribution=True, build_dir=build_dir)
            self.assertEqual(problems, [])
            self.assertEqual(assessment['payment_instructions_coverage_gate'], 'PASS')
            self.assertEqual(assessment['scoped_verdict'], 'PASS_DTO_ATTRIBUTED')

            # Without --build-dir, snippets alone cannot prove DTO attribution (leaves UNKNOWN/NOT_RUN)
            no_dir_problems, no_dir_assessment = verifier.verify(b, require_dto_attribution=True)
            self.assertTrue(any('build' in p.lower() or 'main.dart.js' in p.lower() for p in no_dir_problems))
            self.assertEqual(no_dir_assessment['payment_instructions_coverage_gate'], 'UNKNOWN/NOT_RUN')

    def test_mutant_absent_binding_and_hash_mismatch_rejected(self):
        js_text, fp_ctor, pi_ctor = _make_synthetic_main_js(instructions_field='_instructions')
        sanitized, companion = _make_binding_payload(js_text, fp_ctor, pi_ctor, instructions_field='_instructions')
        frames = self._real_safe_frames('_instructions')
        with tempfile.TemporaryDirectory() as tmp:
            build_dir = Path(tmp) / 'build_web'
            build_dir.mkdir()
            (build_dir / 'main.dart.js').write_bytes(js_text.encode('utf-8'))

            # Absent binding in summary / companion even with real paths
            b_absent = Path(tmp) / 'b_absent'
            _build_valid_bundle(
                b_absent,
                frames_override=frames,
                dto_proven=True,
                scoped_verdict='PASS_DTO_ATTRIBUTED',
                main_js_sha=sanitized['main_dart_js_sha256'],
            )
            p_abs, a_abs = verifier.verify(b_absent, require_dto_attribution=True, build_dir=build_dir)
            self.assertTrue(len(p_abs) > 0)
            self.assertEqual(a_abs['payment_instructions_coverage_gate'], 'UNKNOWN/NOT_RUN')

            # Hash mismatch: build_dir/main.dart.js modified
            bad_build = Path(tmp) / 'bad_build_web'
            bad_build.mkdir()
            (bad_build / 'main.dart.js').write_bytes((js_text + '\n// tampered\n').encode('utf-8'))
            b_hash = Path(tmp) / 'b_hash'
            _build_valid_bundle(
                b_hash,
                frames_override=frames,
                dto_proven=True,
                scoped_verdict='PASS_DTO_ATTRIBUTED',
                main_js_sha=sanitized['main_dart_js_sha256'],
                source_binding=sanitized,
                companion_binding=companion,
            )
            p_hash, a_hash = verifier.verify(b_hash, require_dto_attribution=True, build_dir=bad_build)
            self.assertTrue(any('sha' in p.lower() or 'hash' in p.lower() or 'mismatch' in p.lower() for p in p_hash))
            self.assertEqual(a_hash['payment_instructions_coverage_gate'], 'UNKNOWN/NOT_RUN')

            # Constructor SHA mismatch in source_binding
            bad_ctor_binding = json.loads(json.dumps(sanitized))
            bad_ctor_binding['finance_provider']['constructor_sha256'] = '0' * 64
            b_ctor = Path(tmp) / 'b_ctor'
            _build_valid_bundle(
                b_ctor,
                frames_override=frames,
                dto_proven=True,
                scoped_verdict='PASS_DTO_ATTRIBUTED',
                main_js_sha=sanitized['main_dart_js_sha256'],
                source_binding=bad_ctor_binding,
                companion_binding=companion,
            )
            p_ctor, a_ctor = verifier.verify(b_ctor, require_dto_attribution=True, build_dir=build_dir)
            self.assertTrue(len(p_ctor) > 0)
            self.assertEqual(a_ctor['payment_instructions_coverage_gate'], 'UNKNOWN/NOT_RUN')

    def test_mutant_xhr_script_reverse_fragment_wrongfield_mismatchpayload_rejected(self):
        js_text, fp_ctor, pi_ctor = _make_synthetic_main_js(instructions_field='_instructions')
        sanitized, companion = _make_binding_payload(js_text, fp_ctor, pi_ctor, instructions_field='_instructions')
        bad_chains = [
            ['root', 'property:XMLHttpRequest -> object', 'property:responseText receiverSnapshot -> string'],
            ['root', 'property:receiverSnapshot -> object', 'property:_strings -> object', 'property:canary_instr_a -> object', 'property:hashMapCellValue -> string'],
            ['root', 'property:_provider$_value -> object', 'internal:_instructions -> object', 'property:receiverSnapshot -> object', 'property:_last -> object', 'property:hashMapCellValue -> string'],
            ['root', 'property:_provider$_value -> object', 'property:receiverSnapshot -> object', 'property:_instructions -> object', 'property:_last -> object', 'property:hashMapCellValue -> string'],
            ['root', 'property:___InheritedProviderScopeElement__delega -> object', 'property:_instructions -> object', 'property:receiverSnapshot -> object', 'property:_last -> object', 'property:hashMapCellValue -> string'],
            ['root', 'property:_provider$_value -> object', 'property:_finance_provider$_instructions -> object', 'property:receiverSnapshot -> object', 'property:_last -> object', 'property:hashMapCellValue -> string'],
            ['root', 'property:_provider$_value -> object', 'property:_instructionsPlayerId -> object', 'property:receiverSnapshot -> object', 'property:_last -> object', 'property:hashMapCellValue -> string'],
            ['root', 'property:_provider$_value -> object', 'property:_instructions -> object', 'property:receiverSnapshot -> object', 'property:arbitrary -> string'],
            ['root', '...', 'property:_provider$_value -> object', 'property:_instructions -> object', 'property:receiverSnapshot -> object', 'property:_last -> object', 'property:hashMapCellValue -> string'],
        ]
        with tempfile.TemporaryDirectory() as tmp:
            build_dir = Path(tmp) / 'build_web'
            build_dir.mkdir()
            (build_dir / 'main.dart.js').write_bytes(js_text.encode('utf-8'))
            for idx, bad_frames in enumerate(bad_chains):
                b = Path(tmp) / f'bad_{idx}'
                _build_valid_bundle(
                    b,
                    frames_override={'canary_instr_a': bad_frames, 'canary_instr_b': bad_frames},
                    dto_proven=True,
                    scoped_verdict='PASS_DTO_ATTRIBUTED',
                    main_js_sha=sanitized['main_dart_js_sha256'],
                    source_binding=sanitized,
                    companion_binding=companion,
                )
                problems, assessment = verifier.verify(b, require_dto_attribution=True, build_dir=build_dir)
                self.assertTrue(len(problems) > 0, f'should reject {bad_frames}')
                self.assertEqual(assessment['payment_instructions_coverage_gate'], 'UNKNOWN/NOT_RUN')

            # Mismatch payload: exact=False, path_sha256_12 mismatch, wrong canary key under _strings
            good_frames = self._real_safe_frames('_instructions')
            b_exact = Path(tmp) / 'b_exact'
            _build_valid_bundle(
                b_exact,
                frames_override=good_frames,
                dto_proven=True,
                scoped_verdict='PASS_DTO_ATTRIBUTED',
                main_js_sha=sanitized['main_dart_js_sha256'],
                source_binding=sanitized,
                companion_binding=companion,
                exact_override={'canary_instr_a': False},
            )
            p_exact, a_exact = verifier.verify(b_exact, require_dto_attribution=True, build_dir=build_dir)
            self.assertTrue(len(p_exact) > 0)
            self.assertEqual(a_exact['payment_instructions_coverage_gate'], 'UNKNOWN/NOT_RUN')

            b_psha = Path(tmp) / 'b_psha'
            _build_valid_bundle(
                b_psha,
                frames_override=good_frames,
                dto_proven=True,
                scoped_verdict='PASS_DTO_ATTRIBUTED',
                main_js_sha=sanitized['main_dart_js_sha256'],
                source_binding=sanitized,
                companion_binding=companion,
                path_sha_override={'canary_instr_a': 'deadbeef1234'},
            )
            p_psha, a_psha = verifier.verify(b_psha, require_dto_attribution=True, build_dir=build_dir)
            self.assertTrue(len(p_psha) > 0)
            self.assertEqual(a_psha['payment_instructions_coverage_gate'], 'UNKNOWN/NOT_RUN')

            # Mismatch payload: wrong canary key under _strings
            wrong_key_frames = {
                'canary_instr_a': [
                    'root',
                    'property:_provider$_value -> object',
                    'property:_instructions -> object',
                    'property:receiverSnapshot -> object',
                    'property:_strings -> object',
                    'property:canary_instr_b -> object',
                    'property:hashMapCellValue -> string',
                ],
                'canary_instr_b': good_frames['canary_instr_b'],
            }
            b_wkey = Path(tmp) / 'b_wkey'
            _build_valid_bundle(
                b_wkey,
                frames_override=wrong_key_frames,
                dto_proven=True,
                scoped_verdict='PASS_DTO_ATTRIBUTED',
                main_js_sha=sanitized['main_dart_js_sha256'],
                source_binding=sanitized,
                companion_binding=companion,
            )
            p_wkey, a_wkey = verifier.verify(b_wkey, require_dto_attribution=True, build_dir=build_dir)
            self.assertTrue(len(p_wkey) > 0)
            self.assertEqual(a_wkey['payment_instructions_coverage_gate'], 'UNKNOWN/NOT_RUN')

    def _rewrite_summary(self, b: Path, mutator):
        s_path = b / 'summary.json'
        data = json.loads(s_path.read_text(encoding='utf-8'))
        mutator(data)
        s_path.write_bytes((json.dumps(data, indent=2) + '\n').encode('utf-8'))
        digest = hashlib.sha256(s_path.read_bytes()).hexdigest()
        manifest_lines = (b / 'hashes.sha256').read_text(encoding='utf-8').splitlines()
        new_manifest = [f'{digest}  summary.json' if l.endswith('  summary.json') else l for l in manifest_lines]
        (b / 'hashes.sha256').write_bytes(('\n'.join(new_manifest) + '\n').encode('utf-8'))

    def test_mutant_duplicate_cycle_or_mismatched_time_origin_fails(self):
        # IH3: False/missing same_document_across_cycles, unequal time_origin, missing/mismatched epoch time_origin
        with tempfile.TemporaryDirectory() as tmp:
            b1 = Path(tmp) / 'b1'
            _build_valid_bundle(b1)
            self._rewrite_summary(b1, lambda d: d.__setitem__('same_document_across_cycles', False))
            p1, _ = verifier.verify(b1)
            self.assertTrue(any('same_document_across_cycles' in p for p in p1))

            b2 = Path(tmp) / 'b2'
            _build_valid_bundle(b2)
            def _drop_flag_and_skew_origin(d):
                d.pop('same_document_across_cycles', None)
                d['cycles'][1]['time_origin'] = 99999.0
            self._rewrite_summary(b2, _drop_flag_and_skew_origin)
            p2, _ = verifier.verify(b2)
            self.assertTrue(any('time_origin' in p for p in p2))

            b3 = Path(tmp) / 'b3'
            _build_valid_bundle(b3)
            self._rewrite_summary(b3, lambda d: d['cycles'][0]['epochs']['post_logout'].__setitem__('time_origin', 77777.0))
            p3, _ = verifier.verify(b3)
            self.assertTrue(any('time_origin' in p for p in p3))

            b4 = Path(tmp) / 'b4'
            _build_valid_bundle(b4)
            self._rewrite_summary(b4, lambda d: d['cycles'][0]['epochs']['baseline'].pop('time_origin', None))
            p4, _ = verifier.verify(b4)
            self.assertTrue(any('time_origin' in p for p in p4))

    def test_mutant_recovery_state_retained_or_error_fails_verifier(self):
        # IH5 P2: Verifier must reject PASS bundles with recovery_state_retained != False or recovery_state_error
        with tempfile.TemporaryDirectory() as tmp:
            b1 = Path(tmp) / 'b1'
            _build_valid_bundle(b1)
            self._rewrite_summary(b1, lambda d: d['cleanup'].__setitem__('recovery_state_retained', True))
            p1, _ = verifier.verify(b1)
            self.assertTrue(any('recovery_state_retained' in p for p in p1))

            b2 = Path(tmp) / 'b2'
            _build_valid_bundle(b2)
            self._rewrite_summary(b2, lambda d: d['cleanup'].pop('recovery_state_retained', None))
            p2, _ = verifier.verify(b2)
            self.assertTrue(any('recovery_state_retained' in p for p in p2))

            b3 = Path(tmp) / 'b3'
            _build_valid_bundle(b3)
            self._rewrite_summary(b3, lambda d: d['cleanup'].__setitem__('recovery_state_error', 'EPERM'))
            p3, _ = verifier.verify(b3)
            self.assertTrue(any('recovery_state_error' in p for p in p3))

    def test_cli_cleanup_unlink_failure_vs_db_failure(self):
        # IH5 P2: Successful DB cleanup + failed unlink -> exit 1, state exists, safe receipt;
        # Failed DB cleanup -> retains state and fails as before.
        with tempfile.TemporaryDirectory() as tmp:
            db_ok = FakeDb()
            fixture = fx.DisposableInstructionsFixture()
            before_fp = db_ok.fingerprint()
            state_path = Path(tmp) / 'state_unlink_fail.json'
            fixture.create(db_ok, state_path=state_path, capture_baseline=False)
            fixture.before_fingerprint = before_fp

            orig_unlink = Path.unlink
            def _fail_unlink(self_path, *args, **kwargs):
                if self_path == state_path:
                    raise PermissionError('simulated EPERM on unlink')
                return orig_unlink(self_path, *args, **kwargs)

            orig_path_unlink = Path.unlink
            Path.unlink = _fail_unlink
            try:
                receipt, code = fx.finalize_cli_cleanup(fixture, db_ok, state_path)
            finally:
                Path.unlink = orig_path_unlink

            self.assertEqual(code, 1)
            self.assertTrue(receipt['disposable_instructions_cleanup_verified'])
            self.assertTrue(receipt['recovery_state_retained'])
            self.assertIn('recovery_state_error', receipt)
            self.assertTrue(state_path.exists())
            self.assertEqual(len(db_ok.sessions), 0)
            raw_receipt = json.dumps(receipt)
            self.assertNotIn(fixture.sentinel_1, raw_receipt)
            self.assertNotIn(fixture.sentinel_2, raw_receipt)

            # DB cleanup failure still retains state and exits 1
            db_fail = FakeDb(foreign_session=True)
            fx_fail = fx.DisposableInstructionsFixture()
            db_fail.sessions[fx_fail.session_id] = {'id': fx_fail.session_id, 'description': 'foreign'}
            fx_fail.preflight_absent = True
            fx_fail.insert_attempted = True
            fx_fail.created = True
            state_fail = Path(tmp) / 'state_db_fail.json'
            fx._write_private_json_exclusive(state_fail, fx_fail.to_private_state())
            receipt2, code2 = fx.finalize_cli_cleanup(fx_fail, db_fail, state_fail)
            self.assertEqual(code2, 1)
            self.assertFalse(receipt2['disposable_instructions_cleanup_verified'])
            self.assertTrue(receipt2['recovery_state_retained'])
            self.assertTrue(state_fail.exists())


class TestExecutableSourceBinding(unittest.TestCase):
    def test_comments_and_literals_cannot_establish_binding(self):
        js, fp, _ = _make_synthetic_main_js()
        use_start = js.index('A.FinanceProvider.prototype')
        variants = {
            'block_comment_program': '/*\n' + js + '\n*/',
            'template_literal_program': 'const example = `\n' + js + '\n`;',
            'quoted_program': 'const example = ' + json.dumps(js) + ';',
            'commented_field_uses': js[:use_start] + '/*\n' + js[use_start:] + '\n*/',
            'commented_assignments': js.replace(fp, fp.replace('var _ = this;', '/* var _ = this;').replace('\n}', '\n*/ }')),
        }
        for label, source in variants.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory() as tmp:
                (Path(tmp) / 'main.dart.js').write_text(source, encoding='utf-8')
                result = verifier.extract_and_validate_source_binding(tmp)
                self.assertIs(result.get('ok'), False, label)


if __name__ == '__main__':
    unittest.main()
