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

    def test_main_wires_scoped_collection_replay_and_success_audit(self):
        """Run the actual main orchestration against fake external services, no live DB."""
        ids = iter('60000000-0000-4000-8000-00000000000' + str(i) for i in (1, 2, 3))
        p0 = None
        def rpc(url, token, operation, payload, headers=None):
            nonlocal p0
            if p0 is None:
                p0 = next(ids)
                return 200, {'payment_id': p0}
            return 200, {'payment_id': next(ids)}
        def evidence(db, pay, req, actor):
            return {'payment': {'id': pay, 'amount_vnd': 10000, 'request_id': req,
                                'player_id': runner.PLAYER},
                    'ledger': {'id': 'ledger-' + pay, 'source_payment_id': pay, 'amount': 10000},
                    'audit': {'id': 'audit-' + pay, 'request_id': req, 'session_id': runner.SESSION},
                    'request': {'request_id': req, 'payment_id': pay, 'operation': 'record_cash_payment',
                                'result': {'payment_id': pay, 'status': 'confirmed', 'amount_vnd': 10000}}}
        def collect(db, ops):
            values = list(ops.values()) if 'src-db' in db else [ops['p0_precommit']]
            return {'payments': [{'id': op['payment_id']} for op in values],
                    'club_transactions': [{'id': op['transaction_id']} for op in values],
                    'audit_events': [{'id': op['audit_event_id']} for op in values],
                    'operation_requests': [{'request_id': op['request_id']} for op in values]}
        def measured(db, snapshot, wa, wb):
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
        process.poll.return_value = None
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / 'evidence'
            # Amounts are actual input intent amounts in this fake DB, not prefilled constants.
            def actual_evidence(db, pay, req, actor):
                row = evidence(db, pay, req, actor)
                amount = {'1': 10000, '2': 15000, '3': 20000}[pay[-1]]
                row['payment']['amount_vnd'] = row['ledger']['amount'] = amount
                row['request']['result']['amount_vnd'] = amount
                return row
            with patch.object(sys, 'argv', ['runner', '--out', str(out)]), \
                 patch.object(runner, 'cmd', side_effect=command), \
                 patch.object(runner.runpy, 'run_path', return_value={'anon': 'fake', 'password': 'fake', 'secret': 'fake'}), \
                 patch.object(runner, 'sql', return_value=ACTOR), \
                 patch.object(runner, 'login', return_value='fake'), \
                 patch.object(runner, 'rpc', side_effect=rpc), \
                 patch.object(runner, 'query_row_evidence', side_effect=actual_evidence), \
                 patch.object(runner, 'held_snapshot', return_value=nullcontext(('00000003-00000018-1', process))), \
                 patch.object(runner, 'dump_with_writers', side_effect=measured), \
                 patch.object(runner, 'workload_rows', side_effect=collect), \
                 patch.object(runner, 'replay_and_fingerprint', return_value=(200, {'payment_id': PAY}, full_state, full_state)):
                code = runner.main()
            receipt = json.loads((out / 'summary.json').read_text(encoding='utf-8'))
        self.assertEqual(code, 0, receipt.get('findings'))
        self.assertEqual(receipt['status'], 'PASS')
        self.assertTrue(receipt['execution_completed'])
        self.assertEqual(receipt['restored_verification']['payments_count'], 1)


if __name__ == '__main__':
    unittest.main()
