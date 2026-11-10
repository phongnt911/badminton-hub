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
        with patch.object(runner, 'cmd', side_effect=dump_cmd), \
             patch.object(runner, 'sql', return_value=json.dumps([{
                 'dump_pid': 12, 'dump_application_name': 'pg_dump', 'dump_query': 'COPY public.payments'}])):
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

    def _run_orchestration_scenario(self, *, measured_fn=None, exporter_poll=None):
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
                    'observation': {'dump_pid': 12, 'dump_application_name': 'pg_dump',
                                    'dump_query': 'COPY public.payments', 'observed_during_active_dump': True,
                                    'observed_start': base + .3, 'observed_end': base + .35}}
        measured = measured_fn or default_measured

        def command(args, **kwargs):
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

        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / 'evidence'
            with patch.object(sys, 'argv', ['runner', '--out', str(out)]), \
                 patch.object(runner, 'cmd', side_effect=command), \
                 patch.object(runner.runpy, 'run_path', return_value={'anon': 'fake', 'password': 'fake', 'secret': 'fake'}), \
                 patch.object(runner, 'sql', return_value=ACTOR), \
                 patch.object(runner, 'login', return_value='fake'), \
                 patch.object(runner, 'rpc', side_effect=rpc), \
                 patch.object(runner, 'query_row_evidence', side_effect=evidence), \
                 patch.object(runner, 'held_snapshot', return_value=nullcontext(('00000003-00000018-1', process))), \
                 patch.object(runner, 'dump_with_writers', side_effect=measured), \
                 patch.object(runner, 'workload_rows', side_effect=collect), \
                 patch.object(runner, 'replay_and_fingerprint', return_value=(200, {'payment_id': PAY}, full_state, full_state)):
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


if __name__ == '__main__':
    unittest.main()
