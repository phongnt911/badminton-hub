import hashlib
import json
import os
import tempfile
import unittest
import uuid
from pathlib import Path

from scripts.bh07_appheap import disposable_instructions_fixture as fx
from scripts.bh07_appheap import verify_payment_instructions_heap as verifier


class FakeDb:
    """In-memory mock for DockerPsqlClient without touching any real DB or Docker."""

    def __init__(self, *, collision=False, fail_insert_after_commit=False,
                 foreign_session=False, mutation_counts=None):
        self.collision = collision
        self.fail_insert_after_commit = fail_insert_after_commit
        self.foreign_session = foreign_session
        self.mutation_counts = mutation_counts or {
            'payments': 0,
            'club_transactions': 0,
            'audit_events': 0,
            'operation_requests': 0,
        }
        self.clubs = {}
        self.club_members = {}
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
            return {'collision_count': 1 if self.collision else 0}
        if 'ownership_check' in sql:
            rows = list(self.sessions.values())
            if self.foreign_session:
                return {'session_count': 1, 'session_owned': False, 'club_count': 1, 'club_owned': False}
            if not rows:
                return {'session_count': 0, 'session_owned': False, 'club_count': len(self.clubs), 'club_owned': False}
            s = rows[0]
            c = list(self.clubs.values())[0] if self.clubs else {}
            return {
                'session_count': len(self.sessions),
                'session_owned': s.get('description') == s.get('_expected_marker'),
                'club_count': len(self.clubs),
                'club_owned': c.get('description') == c.get('_expected_marker'),
            }
        if 'readback_verify' in sql:
            if not self.sessions or not self.clubs:
                return {'ok': False}
            s = list(self.sessions.values())[0]
            return {
                'ok': True,
                'club_private': list(self.clubs.values())[0]['visibility'] == 'private',
                'member_count': len(self.club_members),
                'session_owned': True,
                'player_guest': list(self.session_players.values())[0]['user_id'] is None,
                'billing_current': True,
                'canary_a': s['receiver_snapshot']['canary_instr_a'],
                'canary_b': s['receiver_snapshot']['canary_instr_b'],
            }
        if 'mutation_counts' in sql:
            return dict(self.mutation_counts)
        if 'remaining_counts' in sql:
            total = (len(self.clubs) + len(self.club_members) + len(self.sessions)
                     + len(self.session_players) + len(self.charge_revisions) + len(self.session_charges))
            return {
                'clubs': len(self.clubs),
                'club_members': len(self.club_members),
                'sessions': len(self.sessions),
                'session_players': len(self.session_players),
                'charge_revisions': len(self.charge_revisions),
                'session_charges': len(self.session_charges),
                'total': total,
            }
        return {}

    def apply_fixture_insert(self, fixture):
        self.clubs[fixture.club_id] = {
            'id': fixture.club_id, 'visibility': 'private',
            'description': fixture.marker_text, '_expected_marker': fixture.marker_text,
        }
        self.club_members[fixture.club_member_id] = {'id': fixture.club_member_id, 'club_id': fixture.club_id}
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
            self.apply_fixture_insert(fixture)
            if self.fail_insert_after_commit:
                raise RuntimeError('simulated uncertain commit timeout after server commit')
        elif 'DELETE FROM public.sessions' in sql:
            if self.foreign_session:
                raise RuntimeError('ownership mismatch refused delete')
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


def _make_path(reachable, frames=None):
    if not reachable:
        return {'reachable': False, 'string_nodes': 0, 'exact': False}
    use_frames = frames or [
        'root',
        'internal:(Global handles) -> synthetic',
        'property:a -> object',
        'property:canary_instr_a -> string',
    ]
    digest = hashlib.sha256('\n'.join(use_frames).encode('utf-8')).hexdigest()[:12]
    return {
        'reachable': True,
        'root_kind': 'global_handles',
        'path_len': len(use_frames) - 1,
        'frames': use_frames,
        'path_sha256_12': digest,
        'string_nodes': 1,
        'exact': True,
    }


def _make_scan(present_map, frames_override=None, time_origin=12345.6):
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
        paths[name] = _make_path(pres, frames=frames)
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
                        extra_log_line=None, claim_entire_model=False):
    raw = sentinels_raw or {
        'canary_instr_a': str(uuid.uuid4()),
        'canary_instr_b': str(uuid.uuid4()),
        'probe': 'BH07INSTRPROBE-12345678',
    }
    c1_owner = _make_scan({'probe': True, 'canary_instr_a': True, 'canary_instr_b': owner_b_present}, frames_override)
    if not owner_b_reachable:
        c1_owner['paths']['canary_instr_b'] = _make_path(False)
    c2_owner = _make_scan({'probe': True, 'canary_instr_a': True, 'canary_instr_b': True}, frames_override)

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
            'attribution_status': 'proven' if dto_proven else 'unproven_under_minification',
            'claim_scope': 'narrow_rpc_payload_retention_only' if not claim_entire_model else 'entire_model_clean',
            'scoped_verdict': scoped_verdict,
            'proven_frames': (frames_override or {}).get('canary_instr_a') if dto_proven else [],
        },
        'environment': {
            'build': {
                'mode': 'profile',
                'reused': True,
                'explicit_provenance_verified': True,
                'started_at': '2026-11-13T08:00:00.000Z',
                'artifacts': {'index.html': '1' * 64, 'main.dart.js': '2' * 64},
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

    manifest = []
    for name in ('summary.json', 'report.md', 'run.log'):
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

    def test_positive_dto_attributed_with_unminified_frames(self):
        frames = [
            'root',
            'internal:(Global handles) -> synthetic',
            'property:closure -> object',
            'property:_finance_provider$_instructions -> object',
            'property:receiverSnapshot -> object',
            'property:_map -> object',
            'property:canary_instr_a -> string',
        ]
        with tempfile.TemporaryDirectory() as tmp:
            b = Path(tmp) / 'bundle'
            _build_valid_bundle(
                b,
                frames_override={'canary_instr_a': frames, 'canary_instr_b': frames},
                dto_proven=True,
                scoped_verdict='PASS_DTO_ATTRIBUTED',
            )
            problems, assessment = verifier.verify(b, require_dto_attribution=True)
            self.assertEqual(problems, [])
            self.assertEqual(assessment['payment_instructions_coverage_gate'], 'PASS')

    def test_mutant_xhr_script_reverse_fragment_dto_chains_rejected(self):
        # IH4: individual marker, XHR buffer, script/string intermediate, reverse order, fragment
        bad_chains = [
            ['root', 'property:XMLHttpRequest -> object', 'property:responseText receiverSnapshot -> string'],
            ['root', 'property:receiverSnapshot -> object', 'property:canary_instr_a -> string'],
            ['root', 'internal:_finance_provider$_instructions -> object', 'property:receiverSnapshot -> object', 'property:canary_instr_a -> string'],
            ['root', 'property:receiverSnapshot -> object', 'property:_finance_provider$_instructions -> object', 'property:canary_instr_a -> string'],
            ['root', 'property:_instructions -> object', 'property:receiverSnapshot -> object', 'property:canary_instr_a -> string'],
            ['root', 'property:_finance_provider$_instructions -> object', 'property:receiverSnapshot -> string'],
            ['root', '...', 'property:_finance_provider$_instructions -> object', 'property:receiverSnapshot -> object', 'property:canary_instr_a -> string'],
        ]
        for idx, frames in enumerate(bad_chains):
            with tempfile.TemporaryDirectory() as tmp:
                b = Path(tmp) / f'bad_{idx}'
                _build_valid_bundle(
                    b,
                    frames_override={'canary_instr_a': frames, 'canary_instr_b': frames},
                    dto_proven=True,
                    scoped_verdict='PASS_DTO_ATTRIBUTED',
                )
                problems, _ = verifier.verify(b, require_dto_attribution=True)
                self.assertTrue(len(problems) > 0, f'should reject {frames}')

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


if __name__ == '__main__':
    unittest.main()
