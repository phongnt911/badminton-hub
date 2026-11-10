"""Runtime boundary regressions. Fake DB/HTTP; real subprocess pipes, no Docker."""
import copy
from contextlib import nullcontext
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import Mock, patch
import urllib.error
import urllib.parse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.bh07_backup import run_v4_concurrent_rehearsal as runner
import test_bh07_v4_backup_concurrency as fixtures

PAY = '60000000-0000-4000-8000-000000000001'
REQ = 'c0000000-0000-4000-8000-000000000001'
ACTOR = 'a0000000-0000-4000-8000-000000000001'


class RuntimeCollectionTests(unittest.TestCase):
    def rows(self):
        return {
            'payments': [{'id': PAY, 'session_player_id': runner.PLAYER,
                          'amount_vnd': 10000, 'status': 'confirmed'}],
            'club_transactions': [{'id': 'ledger', 'source_payment_id': PAY,
                                   'amount_vnd': 10000, 'direction': 'income',
                                   'source_type': 'payment'}],
            'audit_events': [{'id': 'audit', 'request_id': REQ, 'actor_user_id': ACTOR,
                              'entity_id': PAY, 'entity_type': 'payment',
                              'action': 'CASH_PAYMENT_RECORDED', 'session_id': runner.SESSION}],
            'operation_requests': [{'request_id': REQ, 'actor_user_id': ACTOR,
                                    'operation': 'record_cash_payment',
                                    'result': {'payment_id': PAY, 'status': 'confirmed',
                                               'amount_vnd': 10000}}],
        }

    def db(self, rows):
        def query(container, statement):
            # A database boundary enforcing the actual migration's column names.
            self.assertNotIn("'request_id', request_id", statement)
            self.assertNotIn("'player_id', player_id", statement)
            self.assertNotIn("'amount', amount)", statement)
            self.assertIn('WHERE', statement)
            for table in rows:
                if 'FROM public.' + table + ' ' in statement:
                    if table in ('operation_requests', 'audit_events'):
                        self.assertIn(ACTOR, statement)
                        self.assertIn(REQ, statement)
                    if table == 'operation_requests':
                        self.assertIn('record_cash_payment', statement)
                    return json.dumps(rows[table])
            self.fail('unexpected SQL: ' + statement)
        return query

    def test_collects_real_schema_and_binds_request_actor(self):
        with patch.object(runner, 'sql', side_effect=self.db(self.rows())):
            ev = runner.query_row_evidence('owned-db', PAY, REQ, ACTOR)
        self.assertEqual(ev['payment']['player_id'], runner.PLAYER)
        self.assertEqual(ev['payment']['request_id'], REQ)
        self.assertEqual(ev['ledger']['amount'], 10000)
        self.assertEqual(ev['audit']['id'], 'audit')

    def test_missing_and_duplicate_rows_never_get_fabricated(self):
        for table in self.rows():
            for count in (0, 2):
                with self.subTest(table=table, count=count):
                    rows = self.rows()
                    rows[table] *= count
                    with patch.object(runner, 'sql', side_effect=self.db(rows)):
                        with self.assertRaises(ValueError):
                            runner.query_row_evidence('owned-db', PAY, REQ, ACTOR)

    def test_misbound_audit_is_rejected_even_if_order_is_reversed(self):
        rows = self.rows()
        rows['audit_events'][0]['request_id'] = 'other-request'
        with patch.object(runner, 'sql', side_effect=self.db(rows)):
            with self.assertRaises(ValueError):
                runner.query_row_evidence('owned-db', PAY, REQ, ACTOR)

    def test_scoped_counts_exclude_unrelated_seed(self):
        ops = {'p0': {'payment_id': PAY, 'request_id': REQ, 'actor_user_id': ACTOR}}
        with patch.object(runner, 'sql', side_effect=self.db(self.rows())):
            state = runner.workload_rows('owned-db', ops)
        self.assertEqual({k: len(v) for k, v in state.items()},
                         {table: 1 for table in self.rows()})

    def test_snapshot_uses_machine_protocol_and_releases_transaction(self):
        popen = subprocess.Popen
        children = []
        def start(args, **kwargs):
            self.assertIn('-X', args)
            self.assertIn('-qAt', args)
            child = popen([sys.executable, '-u', '-c',
                           "import sys; sys.stdin.readline(); sys.stdin.readline(); "
                           "print('SNAPSHOT:00000003-00000018-1',flush=True); sys.stdin.read()"], **kwargs)
            children.append(child)
            return child
        with patch.object(runner.subprocess, 'Popen', side_effect=start):
            with runner.held_snapshot('owned-db', timeout=2) as (snapshot, process):
                self.assertEqual(snapshot, '00000003-00000018-1')
                self.assertIsNone(process.poll())
        self.assertIsNotNone(children[0].poll())

    def test_snapshot_blocked_stdout_has_real_timeout_and_no_child_leak(self):
        popen = subprocess.Popen
        children = []
        def start(args, **kwargs):
            child = popen([sys.executable, '-u', '-c', 'import time; time.sleep(30)'], **kwargs)
            children.append(child)
            return child
        start_time = time.monotonic()
        with patch.object(runner.subprocess, 'Popen', side_effect=start):
            with self.assertRaises(TimeoutError):
                with runner.held_snapshot('owned-db', timeout=0.1):
                    self.fail('must not acquire a snapshot')
        self.assertLess(time.monotonic() - start_time, 5)
        self.assertIsNotNone(children[0].poll())

    def test_snapshot_rejects_command_tag_instead_of_using_BEGIN(self):
        popen = subprocess.Popen
        def start(args, **kwargs):
            return popen([sys.executable, '-u', '-c', "print('BEGIN',flush=True)"], **kwargs)
        with patch.object(runner.subprocess, 'Popen', side_effect=start):
            with self.assertRaises(ValueError):
                with runner.held_snapshot('owned-db', timeout=2):
                    self.fail('BEGIN is not a snapshot ID')

    def test_dump_completion_is_not_delayed_until_writer_join(self):
        def dump_cmd(*args, **kwargs):
            time.sleep(0.02)
            return subprocess.CompletedProcess([], 0, b'dump', b'')
        def writer():
            start = time.time()
            time.sleep(0.12)
            return {'start': start, 'end': time.time(), 'status': 200}

        class MockObserver:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
            def observe(self):
                now = time.time()
                return {'dump_pid': 12, 'dump_application_name': 'pg_dump',
                        'dump_query': 'COPY public.payments',
                        'observed_start': now, 'observed_end': now + 0.001}

        with patch.object(runner, 'cmd', side_effect=dump_cmd), \
             patch.object(runner, 'open_dump_observer', return_value=MockObserver()):
            result = runner.dump_with_writers('owned-db', 'snapshot', writer, writer)
        self.assertLess(result['dump_end'], result['writer_a']['end'])
        self.assertFalse(result['overlap_verified'])

    def test_observer_cannot_match_itself(self):
        def observer(container, statement):
            self.assertIn('pid <> pg_backend_pid()', statement)
            self.assertIn("application_name = 'pg_dump'", statement)
            self.assertNotIn(" OR query LIKE", statement)
            return '[]'
        with patch.object(runner, 'sql', side_effect=observer):
            self.assertIsNone(runner.observe_dump('owned-db'))

    def test_replay_detects_same_count_changed_data_in_any_table(self):
        before = {table: {'rows': 4, 'sha256': 'a' * 64} for table in runner.REQUIRED_TABLES}
        before['_schema'] = 'b' * 64
        for table in before:
            with self.subTest(table=table):
                after = copy.deepcopy(before)
                if table == '_schema':
                    after[table] = 'c' * 64
                else:
                    after[table]['sha256'] = 'c' * 64
                with patch.object(runner, 'fingerprint', side_effect=[before, after]) as fp:
                    with self.assertRaises(ValueError):
                        runner.replay_and_fingerprint('db', lambda: (200, {'payment_id': PAY}))
                self.assertEqual(fp.call_count, 2)

    def test_successful_collector_can_be_audited_without_preclaimed_PASS(self):
        fixture = fixtures.V4FailClosedValidatorTests()
        fixture.setUp()
        summary = copy.deepcopy(fixture.valid_summary)
        summary.pop('status')
        summary['execution_completed'] = True
        runner.finish_summary(summary, fixture.valid_source_fingerprint, fixture.valid_restored_fingerprint)
        self.assertEqual(summary['status'], 'PASS')
        summary['status'] = 'FAIL'
        summary['failure_type'] = 'RuntimeError'
        runner.finish_summary(summary, fixture.valid_source_fingerprint, fixture.valid_restored_fingerprint)
        self.assertEqual(summary['status'], 'FAIL')

    def test_auditor_rejects_ledger_mutation_even_with_equal_payment_hash(self):
        fixture = fixtures.V4FailClosedValidatorTests()
        fixture.setUp()
        summary = copy.deepcopy(fixture.valid_summary)
        replay = summary['restored_verification']['replay_evidence']
        replay['before_state'] = copy.deepcopy(fixture.valid_restored_fingerprint)
        replay['before_state']['_schema'] = 'b' * 64
        replay['after_state'] = copy.deepcopy(replay['before_state'])
        replay['after_state']['public.club_transactions']['sha256'] = '9' * 64
        result = runner.validate_v4_rehearsal(summary, fixture.valid_source_fingerprint,
                                               fixture.valid_restored_fingerprint)
        self.assertFalse(result['ok'])

    def test_auditor_rejects_sample_outside_writer_intersection(self):
        fixture = fixtures.V4FailClosedValidatorTests()
        fixture.setUp()
        fixture.valid_summary['writers_concurrency']['db_observation_receipt'].update(
            observed_start=100.01, observed_end=100.02)
        result = runner.validate_v4_rehearsal(fixture.valid_summary, fixture.valid_source_fingerprint,
                                               fixture.valid_restored_fingerprint)
        self.assertFalse(result['ok'])

    def _run_orchestration_scenario(self, *, measured_fn=None, exporter_poll=None,
                                    command_fn=None, login_fn=None, replay_fn=None):
        """Runs runner.main with mock harness, parameterized for negative/positive diagnostics tests."""
        ids = iter('60000000-0000-4000-8000-00000000000' + str(i) for i in (1, 2, 3))
        p0 = None
        def rpc(url, token, operation, payload, headers=None):
            nonlocal p0
            if p0 is None:
                p0 = next(ids)
                return 200, {'payment_id': p0}
            return 200, {'payment_id': next(ids)}

        def evidence(db, pay, req, actor):
            amount = {'1': 10000, '2': 15000, '3': 20000}.get(pay[-1], 10000)
            return {'payment': {'id': pay, 'amount_vnd': amount, 'request_id': req,
                                'player_id': runner.PLAYER},
                    'ledger': {'id': 'ledger-' + pay, 'source_payment_id': pay, 'amount': amount},
                    'audit': {'id': 'audit-' + pay, 'request_id': req, 'session_id': runner.SESSION},
                    'request': {'request_id': req, 'payment_id': pay, 'operation': 'record_cash_payment',
                                'result': {'payment_id': pay, 'status': 'confirmed', 'amount_vnd': amount}}}

        def collect(db, ops):
            values = list(ops.values()) if 'src-db' in db else [ops['p0_precommit']]
            return {'payments': [{'id': op['payment_id']} for op in values],
                    'club_transactions': [{'id': op['transaction_id']} for op in values],
                    'audit_events': [{'id': op['audit_event_id']} for op in values],
                    'operation_requests': [{'request_id': op['request_id']} for op in values]}

        def default_measured(db, snapshot, wa, wb):
            base = time.time()
            a, b = wa(), wb()
            a.update(start=base + .1, end=base + .5)
            b.update(start=base + .2, end=base + .6)
            return {'dump': subprocess.CompletedProcess([], 0, b'dump', b''),
                    'dump_start': base, 'dump_end': base + 1,
                    'writer_a': a, 'writer_b': b, 'overlap_verified': True,
                    'initial_observation': {'dump_pid': 12, 'dump_application_name': 'pg_dump',
                                            'dump_query': 'COPY tooling_rehearsal.rehearsal_padding',
                                            'observed_start': base + .05, 'observed_end': base + .08},
                    'observation': {'dump_pid': 12, 'dump_application_name': 'pg_dump',
                                    'dump_query': 'COPY public.payments', 'observed_during_active_dump': True,
                                    'observed_start': base + .3, 'observed_end': base + .35}}
        measured = measured_fn or default_measured

        def command(args, **kwargs):
            if command_fn is not None:
                custom_res = command_fn(args, **kwargs)
                if custom_res is not None:
                    if isinstance(custom_res, Exception):
                        raise custom_res
                    if hasattr(custom_res, 'returncode') and custom_res.returncode != 0:
                        op = kwargs.get('op')
                        safe_op = runner.resolve_safe_operation(op, args)
                        raise runner.command_error(safe_op, custom_res.returncode)
                    return custom_res
            if args[:2] == ['git', 'rev-parse']:
                return subprocess.CompletedProcess(args, 0, b'a' * 40, b'')
            if 'inspect' in args:
                error = ('network ' + args[-1] + ' not found' if 'network' in args
                         else 'no such object: ' + args[-1])
                return subprocess.CompletedProcess(args, 1, b'', error.encode())
            return subprocess.CompletedProcess(args, 0,
                                               b'127.0.0.1:12345' if 'port' in args else b'', b'')

        full_state = {table: {'rows': 4, 'sha256': 'e' * 64} for table in runner.REQUIRED_TABLES}
        full_state['_schema'] = 'f' * 64
        process = Mock()
        process.poll.return_value = exporter_poll

        canonical_padding_stats = json.dumps({
            'rows': runner.DEFAULT_PADDING_ROWS,
            'bytes': runner.DEFAULT_PADDING_ROWS * 992,
            'digest': 'a' * 32,
        })

        def fake_orchestration_sql(container, statement):
            if 'tooling_rehearsal' in statement:
                if 'SELECT json_build_object' in statement:
                    return canonical_padding_stats
                return ''
            return ACTOR

        default_replay_result = (200, {'payment_id': PAY}, full_state, full_state)
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / 'evidence'
            with patch.object(sys, 'argv', ['runner', '--out', str(out)]), \
                 patch.object(runner, 'cmd', side_effect=command), \
                 patch.object(runner.runpy, 'run_path', return_value={'anon': 'fake', 'password': 'fake', 'secret': 'fake'}), \
                 patch.object(runner, 'sql', side_effect=fake_orchestration_sql), \
                 patch.object(runner, 'login', side_effect=login_fn if login_fn is not None else (lambda *a, **kw: 'fake')), \
                 patch.object(runner, 'rpc', side_effect=rpc), \
                 patch.object(runner, 'query_row_evidence', side_effect=evidence), \
                 patch.object(runner, 'held_snapshot', return_value=nullcontext(('00000003-00000018-1', process))), \
                 patch.object(runner, 'dump_with_writers', side_effect=measured), \
                 patch.object(runner, 'workload_rows', side_effect=collect), \
                 patch.object(runner, 'replay_and_fingerprint', side_effect=replay_fn if replay_fn is not None else (lambda *a, **kw: default_replay_result)):
                code = runner.main()
            receipt = json.loads((out / 'summary.json').read_text(encoding='utf-8'))
        return code, receipt

    def test_main_wires_scoped_collection_replay_and_success_audit(self):
        """Run the actual main orchestration against fake external services, no live DB."""
        code, receipt = self._run_orchestration_scenario()
        self.assertEqual(code, 0, receipt.get('findings'))
        self.assertEqual(receipt['status'], 'PASS')
        self.assertTrue(receipt['execution_completed'])
        self.assertEqual(receipt['restored_verification']['payments_count'], 1)

    def test_main_diagnostics_no_copy_observation_writers_not_sent(self):
        """Proves persisted summary retains safe diagnostics when no COPY backend was observed and writers were not sent."""
        def measured_no_copy(db, snapshot, wa, wb):
            base = 1000.0
            return {
                'dump': subprocess.CompletedProcess(
                    ['docker', 'exec', 'pg_dump'], 0,
                    stdout=b'SECRET_DUMP_PAYLOAD_UNOBSERVED_ABC123',
                    stderr=b'SECRET_DUMP_STDERR_UNOBSERVED_XYZ456'),
                'dump_start': base,
                'dump_end': base + 0.5,
                'writer_a': None,
                'writer_b': None,
                'overlap_verified': False,
                'observation': None,
            }

        code, receipt = self._run_orchestration_scenario(measured_fn=measured_no_copy, exporter_poll=None)
        self.assertEqual(code, 1)
        self.assertEqual(receipt['status'], 'FAIL')
        self.assertEqual(receipt['failure_type'], 'ValueError')
        self.assertNotIn('execution_completed', receipt)
        self.assertTrue(receipt['cleanup']['ok'])

        # Verify structured diagnostics retained before raise
        self.assertIn('diagnostics', receipt)
        diag = receipt['diagnostics']
        self.assertEqual(diag['dump_exit_code'], 0)
        self.assertEqual(diag['dump_start'], 1000.0)
        self.assertEqual(diag['dump_end'], 1000.5)
        obs = diag.get('observation') if 'observation' in diag else diag.get('observed_sample')
        self.assertIsNone(obs)
        self.assertFalse(diag['overlap_verified'])
        self.assertIsNone(diag['exporter_returncode'])
        # Writer not sent markers
        for w_key in ('writer_a', 'writer_b'):
            self.assertTrue(diag[w_key] is None or diag[w_key] == {'sent': False},
                            f'{w_key} must be None or {{"sent": False}}, got {diag[w_key]!r}')

        # Assert secrets and raw dump output cannot enter persisted diagnostics or summary
        diag_json = json.dumps(diag)
        self.assertNotIn('SECRET_DUMP_PAYLOAD', diag_json)
        self.assertNotIn('SECRET_DUMP_STDERR', diag_json)
        self.assertNotIn('CompletedProcess', diag_json)
        summary_json = json.dumps(receipt)
        self.assertNotIn('SECRET_DUMP_PAYLOAD', summary_json)
        self.assertNotIn('SECRET_DUMP_STDERR', summary_json)

    def test_main_diagnostics_insufficient_writer_overlap(self):
        """Proves persisted summary retains safe diagnostics when writers executed with insufficient overlap."""
        def measured_insufficient_overlap(db, snapshot, wa, wb):
            base = 2000.0
            a = {'status': 200, 'res': {'payment_id': 'SECRET_PAYMENT_A_ID'},
                 'req_id': 'SECRET_REQ_A_ID', 'amount': 15000,
                 'start': base + 0.1, 'end': base + 0.3}
            b = {'status': 200, 'res': {'payment_id': 'SECRET_PAYMENT_B_ID'},
                 'req_id': 'SECRET_REQ_B_ID', 'amount': 20000,
                 'start': base + 0.4, 'end': base + 0.6}
            return {
                'dump': subprocess.CompletedProcess([], 0, b'dump_bytes', b''),
                'dump_start': base,
                'dump_end': base + 1.0,
                'writer_a': a,
                'writer_b': b,
                'overlap_verified': False,
                'observation': {
                    'dump_pid': 42,
                    'dump_application_name': 'pg_dump',
                    'dump_query': 'COPY public.payments TO stdout; -- SECRET_SQL_MARKER',
                    'observed_during_active_dump': True,
                    'observed_start': base + 0.2,
                    'observed_end': base + 0.25,
                },
            }

        code, receipt = self._run_orchestration_scenario(measured_fn=measured_insufficient_overlap, exporter_poll=None)
        self.assertEqual(code, 1)
        self.assertEqual(receipt['status'], 'FAIL')
        self.assertEqual(receipt['failure_type'], 'ValueError')
        self.assertNotIn('execution_completed', receipt)
        self.assertTrue(receipt['cleanup']['ok'])

        self.assertIn('diagnostics', receipt)
        diag = receipt['diagnostics']
        self.assertEqual(diag['dump_exit_code'], 0)
        self.assertEqual(diag['dump_start'], 2000.0)
        self.assertEqual(diag['dump_end'], 2001.0)
        self.assertFalse(diag['overlap_verified'])
        self.assertIsNone(diag['exporter_returncode'])
        # Writer safe fields only
        self.assertEqual(diag['writer_a']['status'], 200)
        self.assertEqual(diag['writer_a']['start'], 2000.1)
        self.assertEqual(diag['writer_a']['end'], 2000.3)
        self.assertEqual(diag['writer_b']['status'], 200)
        self.assertEqual(diag['writer_b']['start'], 2000.4)
        self.assertEqual(diag['writer_b']['end'], 2000.6)
        obs = diag.get('observation') if 'observation' in diag else diag.get('observed_sample')
        self.assertIsNotNone(obs)
        self.assertEqual(obs['dump_pid'], 42)

        # Assert no payment reference, request ID, SQL query text, or secret markers
        diag_json = json.dumps(diag)
        self.assertNotIn('SECRET_PAYMENT_A_ID', diag_json)
        self.assertNotIn('SECRET_PAYMENT_B_ID', diag_json)
        self.assertNotIn('SECRET_REQ_A_ID', diag_json)
        self.assertNotIn('SECRET_SQL_MARKER', diag_json)
        self.assertNotIn('dump_query', diag_json)

    def test_main_diagnostics_dump_nonzero_exit(self):
        """Proves persisted summary captures dump nonzero exit code without capturing stdout/stderr."""
        def measured_dump_nonzero(db, snapshot, wa, wb):
            base = 3000.0
            a, b = wa(), wb()
            a.update(start=base + 0.1, end=base + 0.3)
            b.update(start=base + 0.15, end=base + 0.35)
            return {
                'dump': subprocess.CompletedProcess(
                    ['pg_dump'], 2,
                    stdout=b'SECRET_STDOUT_DUMP_CORRUPT',
                    stderr=b'SECRET_STDERR_DUMP_FATAL: server closed connection'),
                'dump_start': base,
                'dump_end': base + 0.8,
                'writer_a': a,
                'writer_b': b,
                'overlap_verified': False,
                'observation': None,
            }

        code, receipt = self._run_orchestration_scenario(measured_fn=measured_dump_nonzero, exporter_poll=None)
        self.assertEqual(code, 1)
        self.assertEqual(receipt['status'], 'FAIL')
        self.assertIn('diagnostics', receipt)
        diag = receipt['diagnostics']
        self.assertEqual(diag['dump_exit_code'], 2)
        self.assertEqual(diag['dump_start'], 3000.0)
        self.assertEqual(diag['dump_end'], 3000.8)
        self.assertFalse(diag['overlap_verified'])

        # Raw process output must never be captured in persisted diagnostics or summary
        diag_json = json.dumps(diag)
        self.assertNotIn('SECRET_STDOUT_DUMP_CORRUPT', diag_json)
        self.assertNotIn('SECRET_STDERR_DUMP_FATAL', diag_json)
        self.assertNotIn('CompletedProcess', diag_json)

    def test_main_diagnostics_exporter_exited_early(self):
        """Proves persisted summary records exporter returncode when transaction exporter died prematurely."""
        def measured_exporter_dead(db, snapshot, wa, wb):
            base = 4000.0
            a, b = wa(), wb()
            a.update(start=base + 0.1, end=base + 0.4)
            b.update(start=base + 0.15, end=base + 0.45)
            return {
                'dump': subprocess.CompletedProcess([], 0, b'dump', b''),
                'dump_start': base,
                'dump_end': base + 0.5,
                'writer_a': a,
                'writer_b': b,
                'overlap_verified': True,
                'observation': {'dump_pid': 99, 'dump_application_name': 'pg_dump',
                                'dump_query': 'COPY public.payments',
                                'observed_during_active_dump': True,
                                'observed_start': base + 0.2, 'observed_end': base + 0.25},
            }

        code, receipt = self._run_orchestration_scenario(measured_fn=measured_exporter_dead, exporter_poll=137)
        self.assertEqual(code, 1)
        self.assertEqual(receipt['status'], 'FAIL')
        self.assertEqual(receipt['failure_type'], 'ValueError')
        self.assertNotIn('execution_completed', receipt)
        self.assertTrue(receipt['cleanup']['ok'])

        self.assertIn('diagnostics', receipt)
        diag = receipt['diagnostics']
        self.assertEqual(diag['exporter_returncode'], 137)
        self.assertEqual(diag['dump_exit_code'], 0)
        self.assertTrue(diag['overlap_verified'])

    def test_main_diagnostics_successful_control_unchanged(self):
        """Proves successful rehearsal retains safe diagnostics while preserving PASS status and completed execution."""
        code, receipt = self._run_orchestration_scenario(exporter_poll=None)
        self.assertEqual(code, 0, receipt.get('findings'))
        self.assertEqual(receipt['status'], 'PASS')
        self.assertTrue(receipt['execution_completed'])
        self.assertEqual(receipt['restored_verification']['payments_count'], 1)
        self.assertTrue(receipt['cleanup']['ok'])

        self.assertIn('diagnostics', receipt)
        diag = receipt['diagnostics']
        self.assertEqual(diag['dump_exit_code'], 0)
        self.assertTrue(diag['overlap_verified'])
        self.assertIsNone(diag['exporter_returncode'])
        self.assertEqual(diag['writer_a']['status'], 200)
        self.assertEqual(diag['writer_b']['status'], 200)
        self.assertIsNotNone(diag.get('initial_observation'))
        self.assertIsNotNone(diag.get('observation'))
        self.assertEqual(diag['initial_observation']['dump_pid'], 12)
        self.assertEqual(diag['observation']['dump_pid'], 12)

    def test_padding_fixture_wiring_and_bounds(self):
        """Verifies tooling padding fixture schema, bounded rows, and restore digest verification."""
        executed_sqls = []
        def fake_sql(container, statement):
            executed_sqls.append((container, statement))
            if 'SELECT json_build_object' in statement:
                return json.dumps({'rows': 40000, 'bytes': 39680000, 'digest': '0123456789abcdef' * 2})
            return ''

        with patch.object(runner, 'sql', side_effect=fake_sql):
            stats = runner.setup_padding_fixture('src-db', rows=40000)
            self.assertEqual(stats['rows'], 40000)
            self.assertEqual(stats['bytes'], 39680000)
            self.assertLessEqual(stats['bytes'], runner.MAX_PADDING_BUDGET_BYTES)

            # Assert SQL targets dedicated tooling schema and not public/auth
            setup_sql = executed_sqls[0][1]
            self.assertIn('CREATE SCHEMA IF NOT EXISTS tooling_rehearsal', setup_sql)
            self.assertIn('CREATE TABLE tooling_rehearsal.rehearsal_padding', setup_sql)
            self.assertNotIn('public.', setup_sql)
            self.assertNotIn('auth.', setup_sql)

            # Assert digest SQL query hashes payload content
            stats_sql = executed_sqls[1][1]
            self.assertIn('md5(payload)', stats_sql)

            # Faithful restore verification
            restored = runner.verify_restored_padding_fixture('target-db', stats)
            self.assertEqual(restored['digest'], stats['digest'])

            # Mismatch detection
            with self.assertRaises(ValueError):
                runner.verify_restored_padding_fixture('target-db', {**stats, 'rows': 39999})
            with self.assertRaises(ValueError):
                runner.verify_restored_padding_fixture('target-db', {**stats, 'digest': '0' * 32})

    def test_padding_fixture_rejects_malformed_empty_wrong_type_missing_field(self):
        """CW1 regression: rejects non-JSON, empty, wrong type, or missing fields without fake fallback."""
        valid_expected = {
            'schema': runner.TOOLING_SCHEMA,
            'table': runner.PADDING_TABLE,
            'rows': 40000,
            'bytes': 39680000,
            'digest': 'a' * 32,
        }
        invalid_payloads = [
            '',
            'not-json',
            '[]',
            '123',
            'null',
            json.dumps({'bytes': 39680000, 'digest': 'a' * 32}),  # missing rows
            json.dumps({'rows': 40000, 'digest': 'a' * 32}),  # missing bytes
            json.dumps({'rows': 40000, 'bytes': 39680000}),  # missing digest
            json.dumps({'rows': '40000', 'bytes': 39680000, 'digest': 'a' * 32}),  # rows str
            json.dumps({'rows': True, 'bytes': 39680000, 'digest': 'a' * 32}),  # rows bool
            json.dumps({'rows': -1, 'bytes': 39680000, 'digest': 'a' * 32}),  # rows negative
            json.dumps({'rows': 0, 'bytes': 39680000, 'digest': 'a' * 32}),  # rows zero
            json.dumps({'rows': 40000, 'bytes': 'not-int', 'digest': 'a' * 32}),  # bytes str
            json.dumps({'rows': 40000, 'bytes': True, 'digest': 'a' * 32}),  # bytes bool
            json.dumps({'rows': 40000, 'bytes': -1, 'digest': 'a' * 32}),  # bytes negative
            json.dumps({'rows': 40000, 'bytes': 300 * 1024 * 1024, 'digest': 'a' * 32}),  # exceeds budget
            json.dumps({'rows': 40000, 'bytes': 39680000, 'digest': 'invalid-digest'}),  # malformed digest
            json.dumps({'rows': 40000, 'bytes': 39680000, 'digest': 12345}),  # wrong type digest
            json.dumps({'rows': 40000, 'bytes': 39680000, 'digest': 'a' * 33}),  # CW2 P2: non-exact 33 chars
            json.dumps({'rows': 40000, 'bytes': 39680000, 'digest': 'a' * 40}),  # CW2 P2: non-exact 40 chars (e.g. git sha)
            json.dumps({'rows': 40000, 'bytes': 39680000, 'digest': 'a' * 63}),  # CW2 P2: non-exact 63 chars
        ]
        for bad_raw in invalid_payloads:
            with self.subTest(bad_raw=bad_raw):
                with patch.object(runner, 'sql', return_value=bad_raw):
                    with self.assertRaises(ValueError):
                        runner.setup_padding_fixture('src-db', rows=40000)
                    with self.assertRaises(ValueError):
                        runner.verify_restored_padding_fixture('target-db', valid_expected)

    def test_padding_fixture_accepts_exact_32_and_64_hex_digest(self):
        """CW2 P2: verifies parser accepts exactly 32 and 64-character hex digests."""
        for length in (32, 64):
            with self.subTest(length=length):
                digest_val = 'c' * length
                valid_raw = json.dumps({'rows': 40000, 'bytes': 39680000, 'digest': digest_val})
                with patch.object(runner, 'sql', return_value=valid_raw):
                    stats = runner.setup_padding_fixture('src-db', rows=40000)
                    self.assertEqual(stats['digest'], digest_val)
                    restored = runner.verify_restored_padding_fixture('target-db', stats)
                    self.assertEqual(restored['digest'], digest_val)

    def test_resource_budget_preflight(self):
        """Verifies disk resource preflight check rejects insufficient disk space."""
        with patch.object(runner.shutil, 'disk_usage', return_value=Mock(free=4 * 1024 * 1024 * 1024)):
            runner.check_resource_budget(Path('.'))  # Should not raise

        # A bounded ~246MiB fixture also needs room for source, target, dump and WAL.
        with patch.object(runner.shutil, 'disk_usage', return_value=Mock(free=1024 * 1024 * 1024)):
            with self.assertRaises(RuntimeError):
                runner.check_resource_budget(Path('.'))

        with patch.object(runner.shutil, 'disk_usage', return_value=Mock(free=100 * 1024 * 1024)):
            with self.assertRaises(RuntimeError) as ctx:
                runner.check_resource_budget(Path('.'))
            self.assertIn('Insufficient disk space', str(ctx.exception))

    def test_main_orchestration_includes_padding_fixture_and_verification(self):
        """Proves full main run records padding fixture metadata and verifies it upon restore."""
        code, receipt = self._run_orchestration_scenario()
        self.assertEqual(code, 0, receipt.get('findings'))
        self.assertEqual(receipt['status'], 'PASS')
        self.assertIn('padding_fixture', receipt)
        pad = receipt['padding_fixture']
        self.assertEqual(pad['schema'], runner.TOOLING_SCHEMA)
        self.assertEqual(pad['table'], runner.PADDING_TABLE)
        self.assertEqual(pad['rows'], runner.DEFAULT_PADDING_ROWS)
        self.assertTrue(pad['restored_match'])

        # Restored verification section also captures matching fixture
        self.assertIn('padding_fixture', receipt['restored_verification'])
        self.assertTrue(receipt['restored_verification']['padding_fixture']['restored_match'])

        # Financial invariants strictly preserved
        self.assertEqual(receipt['restored_verification']['payments_count'], 1)
        self.assertEqual(receipt['restored_verification']['club_transactions_count'], 1)
        self.assertEqual(receipt['restored_verification']['audit_events_count'], 1)
        self.assertEqual(receipt['restored_verification']['operation_requests_count'], 1)

    def test_main_diagnostics_distinguishes_initial_from_overlap_sample(self):
        """Proves safe diagnostics distinguishes initial COPY observation from absent overlap observation."""
        def measured_initial_only(db, snapshot, wa, wb):
            base = 5000.0
            a, b = wa(), wb()
            a.update(start=base + 0.1, end=base + 0.3)
            b.update(start=base + 0.15, end=base + 0.35)
            return {
                'dump': subprocess.CompletedProcess([], 0, b'dump', b''),
                'dump_start': base,
                'dump_end': base + 1.0,
                'writer_a': a,
                'writer_b': b,
                'overlap_verified': False,
                'initial_observation': {
                    'dump_pid': 77,
                    'dump_application_name': 'pg_dump',
                    'dump_query': 'COPY tooling_rehearsal.rehearsal_padding TO stdout; -- SECRET_QUERY',
                    'observed_start': base + 0.05,
                    'observed_end': base + 0.08,
                },
                'observation': None,
            }

        code, receipt = self._run_orchestration_scenario(measured_fn=measured_initial_only, exporter_poll=None)
        self.assertEqual(code, 1)
        self.assertEqual(receipt['status'], 'FAIL')
        self.assertIn('diagnostics', receipt)
        diag = receipt['diagnostics']
        self.assertFalse(diag['overlap_verified'])

        # Initial observation is retained with safe fields
        init_obs = diag.get('initial_observation')
        self.assertIsNotNone(init_obs)
        self.assertEqual(init_obs['dump_pid'], 77)
        self.assertEqual(init_obs['dump_application_name'], 'pg_dump')
        self.assertEqual(init_obs['observed_start'], 5000.05)
        self.assertEqual(init_obs['observed_end'], 5000.08)

        # Overlap observation is None
        self.assertIsNone(diag.get('observation'))

        # Writers were sent and have safe timing
        self.assertEqual(diag['writer_a']['status'], 200)
        self.assertEqual(diag['writer_b']['status'], 200)

        # No secret markers or query text in diagnostics
        diag_str = json.dumps(diag)
        self.assertNotIn('SECRET_QUERY', diag_str)
        self.assertNotIn('dump_query', diag_str)

    def test_old_short_dump_behavior_rejected_without_padding(self):
        """Proves old short dump behavior (0.4s seed dump, no COPY captured) is rejected fail-closed."""
        def measured_short_seed_dump(db, snapshot, wa, wb):
            base = 6000.0
            return {
                'dump': subprocess.CompletedProcess([], 0, b'small_seed_dump', b''),
                'dump_start': base,
                'dump_end': base + 0.402,
                'writer_a': None,
                'writer_b': None,
                'overlap_verified': False,
                'initial_observation': None,
                'observation': None,
            }

        code, receipt = self._run_orchestration_scenario(measured_fn=measured_short_seed_dump, exporter_poll=None)
        self.assertEqual(code, 1)
        self.assertEqual(receipt['status'], 'FAIL')
        self.assertEqual(receipt['failure_type'], 'ValueError')
        self.assertEqual(receipt['error_message'], 'No verified concurrent HTTP commits during active snapshot dump')
        diag = receipt.get('diagnostics')
        self.assertIsNotNone(diag)
        self.assertIsNone(diag['initial_observation'])
        self.assertIsNone(diag['observation'])
        self.assertIsNone(diag['writer_a'])
        self.assertIsNone(diag['writer_b'])
        self.assertFalse(diag['overlap_verified'])

    def test_validator_rejects_malformed_or_overbudget_padding_fixture(self):
        """Verifies validator fail-closed enforcement of padding fixture constraints."""
        fixture = fixtures.V4FailClosedValidatorTests()
        fixture.setUp()

        # Legacy control without padding passes
        res_legacy = runner.validate_v4_rehearsal(
            fixture.valid_summary, fixture.valid_source_fingerprint, fixture.valid_restored_fingerprint
        )
        self.assertTrue(res_legacy['ok'], res_legacy.get('findings'))

        # Valid with padding fixture in both source and restored receipts
        pad_stat = {
            'schema': runner.TOOLING_SCHEMA,
            'table': runner.PADDING_TABLE,
            'rows': 40000,
            'bytes': 39680000,
            'digest': '0123456789abcdef' * 2,
            'restored_match': True,
        }
        valid = copy.deepcopy(fixture.valid_summary)
        valid['padding_fixture'] = copy.deepcopy(pad_stat)
        valid['restored_verification']['padding_fixture'] = copy.deepcopy(pad_stat)

        res = runner.validate_v4_rehearsal(valid, fixture.valid_source_fingerprint, fixture.valid_restored_fingerprint)
        self.assertTrue(res['ok'], res.get('findings'))

        # CW2 P2: Valid with 64-char hex digest (accepts exact 64)
        valid_64 = copy.deepcopy(valid)
        valid_64['padding_fixture']['digest'] = '0123456789abcdef' * 4
        valid_64['restored_verification']['padding_fixture']['digest'] = '0123456789abcdef' * 4
        res_64 = runner.validate_v4_rehearsal(valid_64, fixture.valid_source_fingerprint, fixture.valid_restored_fingerprint)
        self.assertTrue(res_64['ok'], res_64.get('findings'))

        # Missing restored receipt (CW2 reviewer control reproduction)
        missing_rest = copy.deepcopy(valid)
        del missing_rest['restored_verification']['padding_fixture']
        res = runner.validate_v4_rehearsal(missing_rest, fixture.valid_source_fingerprint, fixture.valid_restored_fingerprint)
        self.assertFalse(res['ok'])
        self.assertTrue(any('missing_restored_padding_fixture' in f for f in res.get('findings', [])))

        # Missing source receipt
        missing_src = copy.deepcopy(valid)
        del missing_src['padding_fixture']
        res = runner.validate_v4_rehearsal(missing_src, fixture.valid_source_fingerprint, fixture.valid_restored_fingerprint)
        self.assertFalse(res['ok'])
        self.assertTrue(any('missing_padding_fixture' in f for f in res.get('findings', [])))

        # Invalid digest string (CW2 reviewer control reproduction: 'invalid-digest')
        invalid_dig = copy.deepcopy(valid)
        invalid_dig['padding_fixture']['digest'] = 'invalid-digest'
        invalid_dig['restored_verification']['padding_fixture']['digest'] = 'invalid-digest'
        res = runner.validate_v4_rehearsal(invalid_dig, fixture.valid_source_fingerprint, fixture.valid_restored_fingerprint)
        self.assertFalse(res['ok'])
        self.assertTrue(any('invalid_padding_fixture' in f for f in res.get('findings', [])))

        # CW2 P2: Reject matching source/target receipts with non-exact 32/64 digest lengths (33, 40, 63)
        for bad_len in (33, 40, 63):
            with self.subTest(bad_len=bad_len):
                non_exact = copy.deepcopy(valid)
                non_exact['padding_fixture']['digest'] = 'a' * bad_len
                non_exact['restored_verification']['padding_fixture']['digest'] = 'a' * bad_len
                res_ne = runner.validate_v4_rehearsal(non_exact, fixture.valid_source_fingerprint, fixture.valid_restored_fingerprint)
                self.assertFalse(res_ne['ok'])
                self.assertTrue(any('invalid_padding_fixture' in f for f in res_ne.get('findings', [])))

        # Digest mismatch between source and restored
        mismatch_dig = copy.deepcopy(valid)
        mismatch_dig['restored_verification']['padding_fixture']['digest'] = 'b' * 32
        res = runner.validate_v4_rehearsal(mismatch_dig, fixture.valid_source_fingerprint, fixture.valid_restored_fingerprint)
        self.assertFalse(res['ok'])
        self.assertTrue(any('padding_fixture_mismatch' in f for f in res.get('findings', [])))

        # Rows mismatch between source and restored
        mismatch_rows = copy.deepcopy(valid)
        mismatch_rows['restored_verification']['padding_fixture']['rows'] = 39999
        res = runner.validate_v4_rehearsal(mismatch_rows, fixture.valid_source_fingerprint, fixture.valid_restored_fingerprint)
        self.assertFalse(res['ok'])
        self.assertTrue(any('padding_fixture_mismatch' in f for f in res.get('findings', [])))

        # Bytes mismatch between source and restored
        mismatch_bytes = copy.deepcopy(valid)
        mismatch_bytes['restored_verification']['padding_fixture']['bytes'] = 12345
        res = runner.validate_v4_rehearsal(mismatch_bytes, fixture.valid_source_fingerprint, fixture.valid_restored_fingerprint)
        self.assertFalse(res['ok'])
        self.assertTrue(any('padding_fixture_mismatch' in f for f in res.get('findings', [])))

        # Over budget (>256 MiB)
        overbudget = copy.deepcopy(valid)
        overbudget['padding_fixture']['bytes'] = 300 * 1024 * 1024
        overbudget['restored_verification']['padding_fixture']['bytes'] = 300 * 1024 * 1024
        res = runner.validate_v4_rehearsal(overbudget, fixture.valid_source_fingerprint, fixture.valid_restored_fingerprint)
        self.assertFalse(res['ok'])
        self.assertTrue(any('exceeds 256MiB' in f for f in res.get('findings', [])))

        # Wrong schema (e.g. attempting to put padding in public)
        wrong_schema = copy.deepcopy(valid)
        wrong_schema['padding_fixture']['schema'] = 'public'
        wrong_schema['restored_verification']['padding_fixture']['schema'] = 'public'
        res = runner.validate_v4_rehearsal(wrong_schema, fixture.valid_source_fingerprint, fixture.valid_restored_fingerprint)
        self.assertFalse(res['ok'])
        self.assertTrue(any('invalid_padding_fixture' in f for f in res.get('findings', [])))

        # restored_match False
        unmatched = copy.deepcopy(valid)
        unmatched['padding_fixture']['restored_match'] = False
        unmatched['restored_verification']['padding_fixture']['restored_match'] = False
        res = runner.validate_v4_rehearsal(unmatched, fixture.valid_source_fingerprint, fixture.valid_restored_fingerprint)
        self.assertFalse(res['ok'])
        self.assertTrue(any('restored_match must be True' in f for f in res.get('findings', [])))

    def test_post_restore_failure_target_auth_start(self):
        """Proves summary retains target_auth_start stage and command identity without secret markers."""
        def bad_auth_cmd(args, **kwargs):
            if args[:3] == ['docker', 'run', '-d'] and any('target-auth' in str(a) for a in args):
                return subprocess.CompletedProcess(
                    args, 1,
                    stdout=b'SECRET_GOTRUE_STDOUT_PAYLOAD_123',
                    stderr=b'SECRET_GOTRUE_STDERR_FATAL_456')
            return None

        code, receipt = self._run_orchestration_scenario(command_fn=bad_auth_cmd)
        self.assertEqual(code, 1)
        self.assertEqual(receipt['status'], 'FAIL')
        self.assertEqual(receipt['failure_type'], 'RuntimeError')
        self.assertEqual(receipt['stage'], runner.STAGE_TARGET_AUTH_START)
        self.assertEqual(receipt['execution_stage'], runner.STAGE_TARGET_AUTH_START)
        self.assertIn('command_failure', receipt)
        self.assertEqual(receipt['command_failure']['operation'], runner.OP_TARGET_AUTH_START)
        self.assertEqual(receipt['command_failure']['exit_code'], 1)
        self.assertEqual(receipt['failed_operation']['operation'], runner.OP_TARGET_AUTH_START)
        self.assertEqual(receipt['failed_operation']['exit_code'], 1)
        self.assertEqual(receipt['error_message'], 'target_auth_start exited 1')
        self.assertTrue(receipt['cleanup']['ok'])
        self.assertNotIn('execution_completed', receipt)

        # Exclusion of secrets and raw args
        raw_receipt = json.dumps(receipt)
        self.assertNotIn('SECRET_GOTRUE_STDOUT_PAYLOAD_123', raw_receipt)
        self.assertNotIn('SECRET_GOTRUE_STDERR_FATAL_456', raw_receipt)
        self.assertNotIn('ghcr.io/supabase/gotrue', receipt.get('error_message', ''))

    def test_post_restore_failure_target_rest_start(self):
        """Proves summary retains target_rest_start stage and command identity without secret markers."""
        def bad_rest_cmd(args, **kwargs):
            if args[:3] == ['docker', 'run', '-d'] and any('target-rest' in str(a) for a in args):
                return subprocess.CompletedProcess(
                    args, 1,
                    stdout=b'SECRET_POSTGREST_STDOUT_789',
                    stderr=b'SECRET_POSTGREST_STDERR_012')
            return None

        code, receipt = self._run_orchestration_scenario(command_fn=bad_rest_cmd)
        self.assertEqual(code, 1)
        self.assertEqual(receipt['status'], 'FAIL')
        self.assertEqual(receipt['failure_type'], 'RuntimeError')
        self.assertEqual(receipt['stage'], runner.STAGE_TARGET_REST_START)
        self.assertEqual(receipt['execution_stage'], runner.STAGE_TARGET_REST_START)
        self.assertIn('command_failure', receipt)
        self.assertEqual(receipt['command_failure']['operation'], runner.OP_TARGET_REST_START)
        self.assertEqual(receipt['command_failure']['exit_code'], 1)
        self.assertEqual(receipt['error_message'], 'target_rest_start exited 1')
        self.assertTrue(receipt['cleanup']['ok'])
        self.assertNotIn('execution_completed', receipt)

        raw_receipt = json.dumps(receipt)
        self.assertNotIn('SECRET_POSTGREST_STDOUT_789', raw_receipt)
        self.assertNotIn('SECRET_POSTGREST_STDERR_012', raw_receipt)
        self.assertNotIn('ghcr.io/supabase/postgrest', receipt.get('error_message', ''))

    def test_post_restore_failure_network_attachment(self):
        """Proves summary retains network_attachment stage and command identity upon network connect failure."""
        def bad_net_cmd(args, **kwargs):
            if args[:3] == ['docker', 'network', 'connect']:
                return subprocess.CompletedProcess(
                    args, 1,
                    stdout=b'SECRET_NET_CONNECT_OUT',
                    stderr=b'SECRET_NET_CONNECT_ERR')
            return None

        code, receipt = self._run_orchestration_scenario(command_fn=bad_net_cmd)
        self.assertEqual(code, 1)
        self.assertEqual(receipt['status'], 'FAIL')
        self.assertEqual(receipt['failure_type'], 'RuntimeError')
        self.assertEqual(receipt['stage'], runner.STAGE_NETWORK_ATTACHMENT)
        self.assertEqual(receipt['execution_stage'], runner.STAGE_NETWORK_ATTACHMENT)
        self.assertIn('command_failure', receipt)
        self.assertEqual(receipt['command_failure']['operation'], runner.OP_TARGET_NETWORK_ATTACH)
        self.assertEqual(receipt['command_failure']['exit_code'], 1)
        self.assertEqual(receipt['error_message'], 'target_network_attach exited 1')
        self.assertTrue(receipt['cleanup']['ok'])
        self.assertNotIn('execution_completed', receipt)

        raw_receipt = json.dumps(receipt)
        self.assertNotIn('SECRET_NET_CONNECT_OUT', raw_receipt)
        self.assertNotIn('SECRET_NET_CONNECT_ERR', raw_receipt)

    def test_post_restore_failure_port_discovery(self):
        """Proves summary retains port_discovery stage and command identity upon docker port failure."""
        def bad_port_cmd(args, **kwargs):
            if args[:2] == ['docker', 'port']:
                return subprocess.CompletedProcess(
                    args, 1,
                    stdout=b'SECRET_PORT_OUT',
                    stderr=b'SECRET_PORT_ERR: container not running')
            return None

        code, receipt = self._run_orchestration_scenario(command_fn=bad_port_cmd)
        self.assertEqual(code, 1)
        self.assertEqual(receipt['status'], 'FAIL')
        self.assertEqual(receipt['failure_type'], 'RuntimeError')
        self.assertEqual(receipt['stage'], runner.STAGE_PORT_DISCOVERY)
        self.assertEqual(receipt['execution_stage'], runner.STAGE_PORT_DISCOVERY)
        self.assertIn('command_failure', receipt)
        self.assertEqual(receipt['command_failure']['operation'], runner.OP_TARGET_PORT_DISCOVERY)
        self.assertEqual(receipt['command_failure']['exit_code'], 1)
        self.assertEqual(receipt['error_message'], 'target_port_discovery exited 1')
        self.assertTrue(receipt['cleanup']['ok'])
        self.assertNotIn('execution_completed', receipt)

        raw_receipt = json.dumps(receipt)
        self.assertNotIn('SECRET_PORT_OUT', raw_receipt)
        self.assertNotIn('SECRET_PORT_ERR', raw_receipt)

    def test_post_restore_failure_auth_health_login(self):
        """Proves summary retains auth_health_login stage and safe metadata when target Auth smoke check fails."""
        source_calls = [0]
        def fail_target_login(url, *args, **kwargs):
            if source_calls[0] < 2:
                source_calls[0] += 1
                return 'fake-source-token'
            raise urllib.error.URLError('SECRET_AUTH_SMOKE_CONNECTION_REFUSED')

        with patch.object(runner.time, 'sleep', return_value=None):
            code, receipt = self._run_orchestration_scenario(login_fn=fail_target_login)
        self.assertEqual(code, 1)
        self.assertEqual(receipt['status'], 'FAIL')
        self.assertEqual(receipt['stage'], runner.STAGE_AUTH_HEALTH_LOGIN)
        self.assertEqual(receipt['execution_stage'], runner.STAGE_AUTH_HEALTH_LOGIN)
        self.assertEqual(receipt['failure_type'], 'AssertionError')
        self.assertEqual(receipt['error_message'], 'target auth health check failed')
        self.assertTrue(receipt['cleanup']['ok'])
        self.assertNotIn('execution_completed', receipt)

        raw_receipt = json.dumps(receipt)
        self.assertNotIn('SECRET_AUTH_SMOKE_CONNECTION_REFUSED', raw_receipt)

    def test_post_restore_failure_replay_collection(self):
        """Proves summary retains replay_fingerprint_collection stage when replay detects data mutation."""
        def mutating_replay(*args, **kwargs):
            raise ValueError('SECRET_REPLAY_MUTATION: state changed during replay')

        code, receipt = self._run_orchestration_scenario(replay_fn=mutating_replay)
        self.assertEqual(code, 1)
        self.assertEqual(receipt['status'], 'FAIL')
        self.assertEqual(receipt['stage'], runner.STAGE_REPLAY_FINGERPRINT_COLLECTION)
        self.assertEqual(receipt['execution_stage'], runner.STAGE_REPLAY_FINGERPRINT_COLLECTION)
        self.assertEqual(receipt['failure_type'], 'ValueError')
        self.assertEqual(receipt['error_message'], 'target replay verification failed')
        self.assertTrue(receipt['cleanup']['ok'])
        self.assertNotIn('execution_completed', receipt)

        raw_receipt = json.dumps(receipt)
        self.assertNotIn('SECRET_REPLAY_MUTATION', raw_receipt)

    def test_safe_operation_whitelist_rejects_arbitrary_user_text(self):
        """Proves operation resolution rejects untrusted input and restricts to whitelist constants."""
        self.assertEqual(runner.resolve_safe_operation('DROP TABLE users; --'), runner.OP_DOCKER_GENERIC)
        self.assertEqual(runner.resolve_safe_operation('untrusted_user_text'), runner.OP_DOCKER_GENERIC)
        self.assertEqual(runner.resolve_safe_operation(runner.OP_TARGET_AUTH_START), runner.OP_TARGET_AUTH_START)
        self.assertEqual(runner.resolve_safe_operation(runner.OP_TARGET_REST_START), runner.OP_TARGET_REST_START)
        self.assertEqual(runner.resolve_safe_operation(runner.OP_TARGET_NETWORK_ATTACH), runner.OP_TARGET_NETWORK_ATTACH)
        self.assertEqual(runner.resolve_safe_operation(runner.OP_TARGET_PORT_DISCOVERY), runner.OP_TARGET_PORT_DISCOVERY)
        self.assertEqual(runner.resolve_safe_operation(None, ['docker', 'port', 'c', '123']), runner.OP_TARGET_PORT_DISCOVERY)
        self.assertEqual(runner.resolve_safe_operation(None, ['docker', 'network', 'connect', 'b', 'c']), runner.OP_TARGET_NETWORK_ATTACH)

        for unhashable in ([], {}, set(), [1, 2], {'op': 'val'}):
            self.assertEqual(runner.resolve_safe_operation(unhashable), runner.OP_DOCKER_GENERIC)

        for unhashable in ([], {}, set(), [1, 2], 123, None):
            with self.assertRaises(ValueError):
                runner.set_stage({}, unhashable)

        err = runner.command_error('INJECTED_CMD_STRING_SECRET', 127)
        self.assertEqual(err.operation, runner.OP_DOCKER_GENERIC)
        self.assertEqual(err.exit_code, 127)
        self.assertEqual(str(err), 'docker exited 127')
        self.assertNotIn('INJECTED_CMD_STRING_SECRET', str(err))

        err_bad_exit = runner.command_error(runner.OP_TARGET_AUTH_START, 'not_an_int')
        self.assertEqual(err_bad_exit.exit_code, 1)
        self.assertIs(type(err_bad_exit.exit_code), int)

    def test_publication_sink_rejects_unhashable_and_malformed_metadata_vectors(self):
        """Proves publication sink rejects unhashable operations/exits without TypeError, falling back to safe labels."""
        def unhashable_failure(args, **kwargs):
            if kwargs.get('op') == runner.OP_TARGET_AUTH_START:
                err = RuntimeError('internal command failure')
                err.operation = ['unhashable', 'list']
                err.exit_code = {'unhashable': 'dict'}
                return err
            return None

        code, receipt = self._run_orchestration_scenario(command_fn=unhashable_failure)
        self.assertEqual(code, 1)
        self.assertEqual(receipt['status'], 'FAIL')
        self.assertEqual(receipt['stage'], runner.STAGE_TARGET_AUTH_START)
        self.assertEqual(receipt['error_message'], runner.STAGE_DEFAULT_ERROR_LABELS[runner.STAGE_TARGET_AUTH_START])
        self.assertNotIn('command_failure', receipt)
        self.assertNotIn('failed_operation', receipt)
        self.assertTrue(receipt['cleanup']['ok'])

    def test_validator_rejects_unhashable_and_malformed_metadata_vectors(self):
        """Proves validator handles unhashable/non-dict metadata without TypeError, producing specific findings."""
        base_summary = {'status': 'PASS', 'git_dirty': False, 'tested_source_sha': '0' * 40}

        # Case 1: unhashable operation and non-int exit_code in command_failure
        s1 = copy.deepcopy(base_summary)
        s1['command_failure'] = {'operation': ['unhashable'], 'exit_code': {'code': 1}}
        res1 = runner.validate_v4_rehearsal(s1, None, None)
        self.assertFalse(res1['ok'])
        self.assertTrue(any('unwhitelisted_operation' in f for f in res1['findings']))
        self.assertTrue(any('invalid_exit_code' in f for f in res1['findings']))

        # Case 2: non-dict failed_operation alias must not silently pass
        s2 = copy.deepcopy(base_summary)
        s2['failed_operation'] = ['not', 'a', 'dict']
        res2 = runner.validate_v4_rehearsal(s2, None, None)
        self.assertFalse(res2['ok'])
        self.assertTrue(any('invalid_failed_operation' in f for f in res2['findings']))

        # Case 3: unhashable stage
        s3 = copy.deepcopy(base_summary)
        s3['stage'] = ['unhashable_stage_list']
        res3 = runner.validate_v4_rehearsal(s3, None, None)
        self.assertFalse(res3['ok'])
        self.assertTrue(any('unrecognized_stage' in f for f in res3['findings']))

        # Case 4: unhashable diagnostics nested metadata
        s4 = copy.deepcopy(base_summary)
        s4['diagnostics'] = {
            'command_failure': {'operation': {}, 'exit_code': 'str'},
            'failed_operation': [],
            'failed_exit_code': [],
            'stage': {},
        }
        res4 = runner.validate_v4_rehearsal(s4, None, None)
        self.assertFalse(res4['ok'])
        self.assertTrue(any('unwhitelisted_operation' in f for f in res4['findings']))
        self.assertTrue(any('invalid_exit_code' in f for f in res4['findings']))
        self.assertTrue(any('unrecognized_stage' in f for f in res4['findings']))

    def test_main_successful_run_records_completed_stage(self):
        """Proves successful main run transitions to completed stage while passing all checks."""
        code, receipt = self._run_orchestration_scenario()
        self.assertEqual(code, 0, receipt.get('findings'))
        self.assertEqual(receipt['status'], 'PASS')
        self.assertTrue(receipt['execution_completed'])
        self.assertEqual(receipt['stage'], runner.STAGE_COMPLETED)
        self.assertEqual(receipt['execution_stage'], runner.STAGE_COMPLETED)
        self.assertNotIn('command_failure', receipt)
        self.assertTrue(receipt['cleanup']['ok'])

    def test_target_auth_env_includes_valid_loopback_site_url(self):
        """Intercepts target_auth_start boundary, reads live envfile, and verifies valid loopback GOTRUE_SITE_URL."""
        captured_site_url = None
        target_auth_started = False

        def intercept_auth_start(args, **kwargs):
            nonlocal captured_site_url, target_auth_started
            if kwargs.get('op') == runner.OP_TARGET_AUTH_START:
                target_auth_started = True
                self.assertIn('--env-file', args)
                env_idx = args.index('--env-file') + 1
                env_path = Path(args[env_idx])
                self.assertTrue(env_path.is_file(), "target auth env file must exist while container starts")
                content = env_path.read_text(encoding='utf-8')
                for line in content.splitlines():
                    line = line.strip()
                    if line.startswith('GOTRUE_SITE_URL='):
                        captured_site_url = line.split('=', 1)[1].strip()
            return None

        code, receipt = self._run_orchestration_scenario(command_fn=intercept_auth_start)
        self.assertTrue(target_auth_started, "target_auth_start boundary was not intercepted")
        self.assertIsNotNone(captured_site_url, "GOTRUE_SITE_URL is missing from target auth envfile")
        self.assertTrue(bool(captured_site_url), "GOTRUE_SITE_URL must not be empty")

        parsed = urllib.parse.urlparse(captured_site_url)
        self.assertIn(parsed.scheme, ('http', 'https'))
        self.assertIn(parsed.hostname, ('127.0.0.1', 'localhost', '::1'))
        self.assertEqual(captured_site_url, 'http://127.0.0.1:3000')

        self.assertEqual(code, 0, receipt.get('findings'))
        self.assertEqual(receipt['status'], 'PASS')
        self.assertTrue(receipt['execution_completed'])


class ObserverCleanupFailureTests(unittest.TestCase):
    def observer(self, running=False, reader_alive=False):
        observer = runner.PersistentDumpObserver('fake-owned-container')
        observer.process = Mock()
        observer.process.poll.return_value = None if running else 0
        observer.reader = Mock(ident=1)
        observer.reader.is_alive.return_value = reader_alive
        return observer

    def test_cleanup_rejects_kill_denial_and_live_process(self):
        observer = self.observer(running=True)
        observer.process.wait.side_effect = subprocess.TimeoutExpired('observer', 1)
        observer.process.kill.side_effect = PermissionError('synthetic denial')
        with self.assertRaisesRegex(RuntimeError, 'cleanup unverified'):
            observer.close()
        self.assertEqual(observer.process.wait.call_count, 2)
        observer.process.kill.assert_called_once()

    def test_cleanup_rejects_final_wait_timeout_even_after_kill(self):
        observer = self.observer(running=True)
        observer.process.wait.side_effect = subprocess.TimeoutExpired('observer', 1)
        with self.assertRaisesRegex(RuntimeError, 'cleanup unverified'):
            observer.close()

    def test_cleanup_rejects_live_reader_without_closing_its_stdout(self):
        observer = self.observer(reader_alive=True)
        with self.assertRaisesRegex(RuntimeError, 'cleanup unverified'):
            observer.close()
        observer.reader.join.assert_called_once_with(timeout=2.0)
        # Closing a buffered stream held by blocked readline can itself block.
        observer.process.stdout.close.assert_not_called()

    def test_cleanup_rejects_stream_close_failure(self):
        observer = self.observer()
        observer.process.stderr.close.side_effect = OSError('synthetic close error')
        with self.assertRaisesRegex(RuntimeError, 'cleanup unverified'):
            observer.close()

    def test_context_does_not_hide_cleanup_failure_after_body_error(self):
        observer = self.observer(running=True)
        observer.process.wait.side_effect = subprocess.TimeoutExpired('observer', 1)
        original = ValueError('original workload failure')
        with self.assertRaisesRegex(RuntimeError, 'cleanup unverified') as caught:
            try:
                raise original
            except ValueError:
                observer.__exit__(ValueError, original, original.__traceback__)
        self.assertIs(caught.exception.__context__, original)

    def test_verified_cleanup_closes_all_streams_and_is_repeatable(self):
        observer = self.observer()
        observer.close()
        observer.close()
        for stream in (observer.process.stdin, observer.process.stdout, observer.process.stderr):
            self.assertEqual(stream.close.call_count, 2)
        observer.process.kill.assert_not_called()


class PersistentDumpObserverTests(unittest.TestCase):
    """Exercises the PersistentDumpObserver protocol over real subprocess pipes without Docker."""

    def test_observer_protocol_happy_path_and_timing(self):
        popen = subprocess.Popen
        children = []

        # Simulated psql responder supporting WARMED_UP and sequence markers
        responder_code = (
            "import sys, re\n"
            "line = sys.stdin.readline()\n"
            "if 'WARMED_UP' in line:\n"
            "    sys.stdout.write('WARMED_UP:0:READY\\n')\n"
            "    sys.stdout.flush()\n"
            "while True:\n"
            "    q = sys.stdin.readline()\n"
            "    if not q:\n"
            "        break\n"
            "    m = re.search(r'OBSERVATION:(\\d+):', q)\n"
            "    if m:\n"
            "        seq = m.group(1)\n"
            "        if seq == '1':\n"
            "            sys.stdout.write(f'OBSERVATION:{seq}:[{{\"dump_pid\":409,\"dump_application_name\":\"pg_dump\",\"dump_query\":\"COPY tooling_rehearsal.rehearsal_padding\"}}]\\n')\n"
            "        else:\n"
            "            sys.stdout.write(f'OBSERVATION:{seq}:[]\\n')\n"
            "        sys.stdout.flush()\n"
        )

        def start(args, **kwargs):
            self.assertIn('-X', args)
            self.assertIn('-qAt', args)
            child = popen([sys.executable, '-u', '-c', responder_code], **kwargs)
            children.append(child)
            return child

        with patch.object(runner.subprocess, 'Popen', side_effect=start):
            with runner.open_dump_observer('test-db', timeout=2.0) as obs:
                t_before = time.time()
                sample1 = obs.observe()
                t_after = time.time()
                self.assertIsNotNone(sample1)
                self.assertEqual(sample1['dump_pid'], 409)
                self.assertEqual(sample1['dump_application_name'], 'pg_dump')
                self.assertGreaterEqual(sample1['observed_start'], t_before)
                self.assertLessEqual(sample1['observed_end'], t_after)

                sample2 = obs.observe()
                self.assertIsNone(sample2)

        self.assertEqual(len(children), 1)
        self.assertIsNotNone(children[0].poll())

    def test_observer_protocol_eof_detected_fail_closed(self):
        popen = subprocess.Popen
        children = []

        # Responder warms up and then immediately exits, causing EOF on first query
        responder_code = (
            "import sys\n"
            "line = sys.stdin.readline()\n"
            "if 'WARMED_UP' in line:\n"
            "    sys.stdout.write('WARMED_UP:0:READY\\n')\n"
            "    sys.stdout.flush()\n"
            "sys.exit(0)\n"
        )

        def start(args, **kwargs):
            child = popen([sys.executable, '-u', '-c', responder_code], **kwargs)
            children.append(child)
            return child

        with patch.object(runner.subprocess, 'Popen', side_effect=start):
            with self.assertRaises(RuntimeError) as ctx:
                with runner.open_dump_observer('test-db', timeout=2.0) as obs:
                    obs.observe()
            self.assertIn('closed stdout unexpectedly', str(ctx.exception))
        self.assertIsNotNone(children[0].poll())

    def test_observer_protocol_malformed_marker_rejected(self):
        popen = subprocess.Popen
        children = []

        responder_code = (
            "import sys\n"
            "sys.stdin.readline()\n"
            "sys.stdout.write('WARMED_UP:0:READY\\n')\n"
            "sys.stdout.flush()\n"
            "sys.stdin.readline()\n"
            "sys.stdout.write('MALFORMED_NO_MARKER\\n')\n"
            "sys.stdout.flush()\n"
        )

        def start(args, **kwargs):
            child = popen([sys.executable, '-u', '-c', responder_code], **kwargs)
            children.append(child)
            return child

        with patch.object(runner.subprocess, 'Popen', side_effect=start):
            with self.assertRaises(ValueError) as ctx:
                with runner.open_dump_observer('test-db', timeout=2.0) as obs:
                    obs.observe()
            self.assertIn('Observer protocol violation', str(ctx.exception))
        self.assertIsNotNone(children[0].poll())

    def test_observer_protocol_malformed_json_rejected(self):
        popen = subprocess.Popen
        children = []

        responder_code = (
            "import sys\n"
            "sys.stdin.readline()\n"
            "sys.stdout.write('WARMED_UP:0:READY\\n')\n"
            "sys.stdout.flush()\n"
            "sys.stdin.readline()\n"
            "sys.stdout.write('OBSERVATION:1:not-a-json-payload\\n')\n"
            "sys.stdout.flush()\n"
        )

        def start(args, **kwargs):
            child = popen([sys.executable, '-u', '-c', responder_code], **kwargs)
            children.append(child)
            return child

        with patch.object(runner.subprocess, 'Popen', side_effect=start):
            with self.assertRaises(ValueError) as ctx:
                with runner.open_dump_observer('test-db', timeout=2.0) as obs:
                    obs.observe()
            self.assertIn('Malformed JSON from observer', str(ctx.exception))
        self.assertIsNotNone(children[0].poll())

    def test_observer_protocol_ambiguous_rows_rejected(self):
        popen = subprocess.Popen
        children = []

        responder_code = (
            "import sys\n"
            "sys.stdin.readline()\n"
            "sys.stdout.write('WARMED_UP:0:READY\\n')\n"
            "sys.stdout.flush()\n"
            "sys.stdin.readline()\n"
            "sys.stdout.write('OBSERVATION:1:[{\"dump_pid\":1},{\"dump_pid\":2}]\\n')\n"
            "sys.stdout.flush()\n"
        )

        def start(args, **kwargs):
            child = popen([sys.executable, '-u', '-c', responder_code], **kwargs)
            children.append(child)
            return child

        with patch.object(runner.subprocess, 'Popen', side_effect=start):
            with self.assertRaises(ValueError) as ctx:
                with runner.open_dump_observer('test-db', timeout=2.0) as obs:
                    obs.observe()
            self.assertIn('Ambiguous pg_dump backend observation', str(ctx.exception))
        self.assertIsNotNone(children[0].poll())

    def test_observer_protocol_warmup_timeout_and_no_child_leak(self):
        popen = subprocess.Popen
        children = []

        def start(args, **kwargs):
            child = popen([sys.executable, '-u', '-c', 'import time; time.sleep(30)'], **kwargs)
            children.append(child)
            return child

        t0 = time.monotonic()
        with patch.object(runner.subprocess, 'Popen', side_effect=start):
            with self.assertRaises(TimeoutError) as ctx:
                with runner.open_dump_observer('test-db', timeout=0.1):
                    self.fail('must not warm up')
            self.assertIn('warmup timed out', str(ctx.exception))
        self.assertLess(time.monotonic() - t0, 5.0)
        self.assertEqual(len(children), 1)
        self.assertIsNotNone(children[0].poll())

    def test_observer_protocol_query_timeout_and_no_child_leak(self):
        popen = subprocess.Popen
        children = []

        responder_code = (
            "import sys, time\n"
            "sys.stdin.readline()\n"
            "sys.stdout.write('WARMED_UP:0:READY\\n')\n"
            "sys.stdout.flush()\n"
            "sys.stdin.readline()\n"
            "time.sleep(30)\n"
        )

        def start(args, **kwargs):
            child = popen([sys.executable, '-u', '-c', responder_code], **kwargs)
            children.append(child)
            return child

        t0 = time.monotonic()
        with patch.object(runner.subprocess, 'Popen', side_effect=start):
            with self.assertRaises(TimeoutError) as ctx:
                with runner.open_dump_observer('test-db', timeout=0.1) as obs:
                    obs.observe(timeout=0.1)
            self.assertIn('query timed out', str(ctx.exception))
        self.assertLess(time.monotonic() - t0, 5.0)
        self.assertEqual(len(children), 1)
        self.assertIsNotNone(children[0].poll())

    def test_dump_with_writers_wiring_with_mock_observer(self):
        """Verifies dump_with_writers correctly synchronizes with observer and captures overlap."""
        def dump_cmd(*args, **kwargs):
            time.sleep(0.08)
            return subprocess.CompletedProcess([], 0, b'fake-dump', b'')

        base = time.time()
        def writer_a():
            return {'status': 200, 'res': {'payment_id': 'pa'}, 'req_id': 'ra', 'amount': 15000,
                    'start': base + 0.02, 'end': base + 0.06}
        def writer_b():
            return {'status': 200, 'res': {'payment_id': 'pb'}, 'req_id': 'rb', 'amount': 20000,
                    'start': base + 0.03, 'end': base + 0.05}

        call_count = 0
        class MockObserver:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
            def observe(self):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    # Initial observation before writers launched
                    return {'dump_pid': 500, 'dump_application_name': 'pg_dump',
                            'dump_query': 'COPY tooling_rehearsal.rehearsal_padding',
                            'observed_start': base + 0.005, 'observed_end': base + 0.008}
                # Observation during concurrent writer execution
                return {'dump_pid': 500, 'dump_application_name': 'pg_dump',
                        'dump_query': 'COPY public.payments',
                        'observed_start': base + 0.035, 'observed_end': base + 0.038}

        with patch.object(runner, 'cmd', side_effect=dump_cmd), \
             patch.object(runner, 'open_dump_observer', return_value=MockObserver()):
            result = runner.dump_with_writers('test-db', 'snap-1', writer_a, writer_b)

        self.assertTrue(result['overlap_verified'])
        self.assertIsNotNone(result['initial_observation'])
        self.assertEqual(result['initial_observation']['dump_pid'], 500)
        self.assertIsNotNone(result['observation'])
        self.assertEqual(result['observation']['dump_pid'], 500)
        self.assertTrue(result['observation']['observed_during_active_dump'])
        self.assertEqual(result['writer_a']['status'], 200)
        self.assertEqual(result['writer_b']['status'], 200)

    def test_dump_with_writers_no_initial_observation_aborts_without_writers(self):
        """Verifies that if observer never sees COPY, writers are never sent and fails closed."""
        def dump_cmd(*args, **kwargs):
            return subprocess.CompletedProcess([], 0, b'fake-dump', b'')

        wa_called = False
        wb_called = False
        def writer_a():
            nonlocal wa_called
            wa_called = True
            return {'status': 200, 'start': 1, 'end': 2}
        def writer_b():
            nonlocal wb_called
            wb_called = True
            return {'status': 200, 'start': 1, 'end': 2}

        class MockEmptyObserver:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
            def observe(self):
                return None

        with patch.object(runner, 'cmd', side_effect=dump_cmd), \
             patch.object(runner, 'open_dump_observer', return_value=MockEmptyObserver()):
            result = runner.dump_with_writers('test-db', 'snap-1', writer_a, writer_b)

        self.assertFalse(result['overlap_verified'])
        self.assertIsNone(result['initial_observation'])
        self.assertIsNone(result['observation'])
        self.assertIsNone(result['writer_a'])
        self.assertIsNone(result['writer_b'])
        self.assertFalse(wa_called)
        self.assertFalse(wb_called)


if __name__ == '__main__':
    unittest.main()
