"""Regression and contract controls for BH-07 V4 concurrent backup/restore rehearsal.

V4 requires:
1. Isolated local Docker stack (staging-like, no shared dev/prod DB).
2. Explicit PostgreSQL snapshot exported from a held transaction (`pg_export_snapshot()`)
   and passed to `pg_dump --snapshot=<id>` so visibility is exact and deterministic.
3. Pre-snapshot payment (P0) by finance-authorized actor committed before snapshot;
   must be present in both source and restored DB.
4. Two authenticated concurrent HTTP writers (OwnerA and FinanceA, never unprivileged Member)
   submitting financial RPC mutations (`record_cash_payment`) with real execution overlap
   while the `pg_dump` backend is actively connected.
5. Successful post-snapshot concurrent payments committed after snapshot must be
   present in source DB but strictly absent from restored DB.
6. Exact restored cardinality and invariant checks:
   - payments, club_transactions, audit_events, operation_requests.
   - FK / unique integrity.
   - Idempotent replay against restored DB produces identical IDs and zero row growth.
7. Independent fail-closed validator that rejects:
   - Missing / malformed receipts or exposed secrets.
   - Absence of true writer overlap during active dump backend.
   - Snapshot mismatch.
   - Missing precommit or included post-snapshot late commit.
   - Missing or duplicate ledger / audit entries.
   - Unverified cleanup or lingering Docker containers / networks.

Run:
python -m unittest tests.test_bh07_v4_backup_concurrency -v
"""
import base64
import copy
import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from scripts.bh07_backup.run_v4_concurrent_rehearsal import (
        validate_v4_rehearsal,
        V4CoordinationBarrier,
        ACTUAL_BASE_SHA,
        digest,
    )
except ImportError as _import_err:
    validate_v4_rehearsal = None
    V4CoordinationBarrier = None
    ACTUAL_BASE_SHA = 'b72c563d9e519986dbd88ec98bcc3f015a41a442'
    digest = lambda raw: '0' * 64
    _MISSING_IMPORT_ERROR = str(_import_err)
else:
    _MISSING_IMPORT_ERROR = None


class V4ContractImportCheck(unittest.TestCase):
    """Verifies that the required V4 contracts are imported from run_v4_concurrent_rehearsal."""

    def test_v4_contracts_exist(self):
        self.assertIsNone(
            _MISSING_IMPORT_ERROR,
            f"V4 implementation contracts missing: {_MISSING_IMPORT_ERROR}."
        )
        self.assertTrue(callable(validate_v4_rehearsal))
        self.assertTrue(callable(V4CoordinationBarrier))


class V4FailClosedValidatorTests(unittest.TestCase):
    """Exercises the real validation decisions of validate_v4_rehearsal against positive and negative cases."""

    def setUp(self):
        if _MISSING_IMPORT_ERROR:
            self.fail(f"Cannot exercise validator; contract missing: {_MISSING_IMPORT_ERROR}")

        self.session_id = '10000000-0000-4000-8000-000000000001'
        self.player_id = '30000000-0000-4000-8000-000000000001'
        self.p0_req_id = 'c0000000-0000-4000-8000-000000000001'
        self.p0_pay_id = '60000000-0000-4000-8000-000000000001'
        self.p0_tx_id = '70000000-0000-4000-8000-000000000001'
        self.p0_audit_id = '80000000-0000-4000-8000-000000000001'

        self.p1a_req_id = 'c0000000-0000-4000-8000-00000000001a'
        self.p1a_pay_id = '60000000-0000-4000-8000-00000000001a'
        self.p1a_tx_id = '70000000-0000-4000-8000-00000000001a'
        self.p1a_audit_id = '80000000-0000-4000-8000-00000000001a'

        self.p1b_req_id = 'c0000000-0000-4000-8000-00000000001b'
        self.p1b_pay_id = '60000000-0000-4000-8000-00000000001b'
        self.p1b_tx_id = '70000000-0000-4000-8000-00000000001b'
        self.p1b_audit_id = '80000000-0000-4000-8000-00000000001b'

        self.snapshot_id = '00000003-0000001B-1'

        p0_ev = {
            'payment': {'id': self.p0_pay_id, 'amount_vnd': 10000, 'request_id': self.p0_req_id, 'player_id': self.player_id},
            'ledger': {'id': self.p0_tx_id, 'source_payment_id': self.p0_pay_id, 'amount': 10000},
            'audit': {'id': self.p0_audit_id, 'request_id': self.p0_req_id, 'session_id': self.session_id},
            'request': {
                'request_id': self.p0_req_id,
                'payment_id': self.p0_pay_id,
                'operation': 'record_cash_payment',
                'status': 'confirmed',
                'result': {'payment_id': self.p0_pay_id, 'amount_vnd': 10000, 'status': 'confirmed'},
            },
        }
        p1a_ev = {
            'payment': {'id': self.p1a_pay_id, 'amount_vnd': 15000, 'request_id': self.p1a_req_id, 'player_id': self.player_id},
            'ledger': {'id': self.p1a_tx_id, 'source_payment_id': self.p1a_pay_id, 'amount': 15000},
            'audit': {'id': self.p1a_audit_id, 'request_id': self.p1a_req_id, 'session_id': self.session_id},
            'request': {
                'request_id': self.p1a_req_id,
                'payment_id': self.p1a_pay_id,
                'operation': 'record_cash_payment',
                'status': 'confirmed',
                'result': {'payment_id': self.p1a_pay_id, 'amount_vnd': 15000, 'status': 'confirmed'},
            },
        }
        p1b_ev = {
            'payment': {'id': self.p1b_pay_id, 'amount_vnd': 20000, 'request_id': self.p1b_req_id, 'player_id': self.player_id},
            'ledger': {'id': self.p1b_tx_id, 'source_payment_id': self.p1b_pay_id, 'amount': 20000},
            'audit': {'id': self.p1b_audit_id, 'request_id': self.p1b_req_id, 'session_id': self.session_id},
            'request': {
                'request_id': self.p1b_req_id,
                'payment_id': self.p1b_pay_id,
                'operation': 'record_cash_payment',
                'status': 'confirmed',
                'result': {'payment_id': self.p1b_pay_id, 'amount_vnd': 20000, 'status': 'confirmed'},
            },
        }

        # Canonical positive summary receipt
        self.valid_summary = {
            'status': 'PASS',
            'tested_source_sha': ACTUAL_BASE_SHA,
            'git_dirty': False,
            'snapshot': {
                'snapshot_id': self.snapshot_id,
                'snapshot_exported_epoch': 100.00,
                'export_tx_held': True,
                'pg_dump_snapshot_arg': f'--snapshot={self.snapshot_id}',
                'pg_dump_completed': True,
                'pg_dump_exit_code': 0,
            },
            'actors': {
                'p0_writer': 'ownera',
                'writer_a': 'ownera',
                'writer_b': 'financea',
            },
            'writers_concurrency': {
                'p0_committed_epoch': 99.80,
                'writer_a_started_epoch': 100.10,
                'writer_a_committed_epoch': 100.40,
                'writer_b_started_epoch': 100.15,
                'writer_b_committed_epoch': 100.45,
                'pg_dump_backend_active_start': 100.05,
                'pg_dump_backend_active_end': 100.60,
                'pg_stat_activity_dump_observed': True,
                'db_observation_receipt': {
                    'dump_pid': 12345,
                    'dump_application_name': 'pg_dump',
                    'dump_query': 'COPY public.payments TO STDOUT',
                    'observed_during_active_dump': True,
                },
                'overlap_verified': True,
                'writers_executed_during_dump': True,
            },
            'source_operations': {
                'p0_precommit': {
                    'request_id': self.p0_req_id,
                    'payment_id': self.p0_pay_id,
                    'transaction_id': self.p0_tx_id,
                    'audit_event_id': self.p0_audit_id,
                    'status': 200,
                    'amount_vnd': 10000,
                    'row_evidence': p0_ev,
                    'relational_digest': digest(p0_ev),
                },
                'p1a_concurrent': {
                    'request_id': self.p1a_req_id,
                    'payment_id': self.p1a_pay_id,
                    'transaction_id': self.p1a_tx_id,
                    'audit_event_id': self.p1a_audit_id,
                    'status': 200,
                    'amount_vnd': 15000,
                    'row_evidence': p1a_ev,
                    'relational_digest': digest(p1a_ev),
                },
                'p1b_concurrent': {
                    'request_id': self.p1b_req_id,
                    'payment_id': self.p1b_pay_id,
                    'transaction_id': self.p1b_tx_id,
                    'audit_event_id': self.p1b_audit_id,
                    'status': 200,
                    'amount_vnd': 20000,
                    'row_evidence': p1b_ev,
                    'relational_digest': digest(p1b_ev),
                },
            },
            'restored_verification': {
                'p0_present_in_restore': True,
                'p1a_present_in_restore': False,
                'p1b_present_in_restore': False,
                'exact_cardinality_match': True,
                'payments_count': 1,
                'club_transactions_count': 1,
                'audit_events_count': 1,
                'operation_requests_count': 1,
                'restored_payment_ids': [self.p0_pay_id],
                'restored_transaction_ids': [self.p0_tx_id],
                'restored_audit_ids': [self.p0_audit_id],
                'restored_request_ids': [self.p0_req_id],
                'restored_row_evidence': copy.deepcopy(p0_ev),
                'replay_p0_idempotent': True,
                'replay_p0_growth': {'payments': 0, 'club_transactions': 0, 'audit_events': 0, 'operation_requests': 0},
                'replay_evidence': {
                    'replay_status': 200,
                    'replay_payment_id': self.p0_pay_id,
                    'before_replay_fingerprint': 'e' * 64,
                    'after_replay_fingerprint': 'e' * 64,
                    'fingerprint_unchanged': True,
                },
            },
            'cleanup': {
                'ok': True,
                'containers_verified_absent': True,
                'networks_verified_absent': True,
                'owned_resources_manifest': ['bh07-v4-src-db', 'bh07-v4-target-db', 'bh07-v4-net'],
                'resources_verified_absent': ['bh07-v4-src-db', 'bh07-v4-target-db', 'bh07-v4-net'],
                'private_dumps_removed': True,
                'cleanup_errors': [],
            },
        }

        # Canonical positive table fingerprints
        self.valid_source_fingerprint = {
            'public.payments': {'rows': 3, 'sha256': 'a' * 64},
            'public.club_transactions': {'rows': 3, 'sha256': 'b' * 64},
            'public.audit_events': {'rows': 3, 'sha256': 'c' * 64},
            'public.operation_requests': {'rows': 3, 'sha256': 'd' * 64},
        }
        self.valid_restored_fingerprint = {
            'public.payments': {'rows': 1, 'sha256': 'e' * 64},
            'public.club_transactions': {'rows': 1, 'sha256': 'f' * 64},
            'public.audit_events': {'rows': 1, 'sha256': '1' * 64},
            'public.operation_requests': {'rows': 1, 'sha256': '2' * 64},
        }

    def test_canonical_positive_receipt_passes(self):
        """A well-formed receipt with true overlap, snapshot boundary, and clean verification passes."""
        result = validate_v4_rehearsal(
            self.valid_summary,
            self.valid_source_fingerprint,
            self.valid_restored_fingerprint,
        )
        self.assertTrue(result.get('ok'))
        self.assertEqual(result.get('verdict'), 'PASS')
        self.assertEqual(result.get('findings'), [])

    def test_reject_unauthorized_member_finance_writer(self):
        """Review requirement: finance writes must be authorized Owner/Treasurer; Member is forbidden."""
        tampered = copy.deepcopy(self.valid_summary)
        tampered['actors']['writer_b'] = 'membera'
        result = validate_v4_rehearsal(tampered, self.valid_source_fingerprint, self.valid_restored_fingerprint)
        self.assertFalse(result.get('ok'))
        self.assertEqual(result.get('verdict'), 'FAIL')
        self.assertTrue(any('unauthorized_finance_actor' in f for f in result.get('findings', [])))

    def test_reject_unauthorized_outsider_finance_writer(self):
        """Review requirement: outsider role must be refused as finance writer."""
        tampered = copy.deepcopy(self.valid_summary)
        tampered['actors']['writer_a'] = 'outsider'
        result = validate_v4_rehearsal(tampered, self.valid_source_fingerprint, self.valid_restored_fingerprint)
        self.assertFalse(result.get('ok'))
        self.assertEqual(result.get('verdict'), 'FAIL')
        self.assertTrue(any('unauthorized_finance_actor' in f for f in result.get('findings', [])))

    def test_reject_missing_writer_overlap(self):
        """Review requirement: must reject if writers did not execute while pg_dump backend was active."""
        tampered = copy.deepcopy(self.valid_summary)
        tampered['writers_concurrency']['overlap_verified'] = False
        result = validate_v4_rehearsal(tampered, self.valid_source_fingerprint, self.valid_restored_fingerprint)
        self.assertFalse(result.get('ok'))
        self.assertEqual(result.get('verdict'), 'FAIL')
        self.assertTrue(any('no_writer_overlap' in f for f in result.get('findings', [])))

    def test_reject_writers_finished_before_dump_started(self):
        """Review requirement: timing bounds must prove concurrent overlap, not sequential execution."""
        tampered = copy.deepcopy(self.valid_summary)
        tampered['writers_concurrency']['writer_a_committed_epoch'] = 99.40
        tampered['writers_concurrency']['writer_b_committed_epoch'] = 99.50
        tampered['writers_concurrency']['pg_dump_backend_active_start'] = 100.05
        result = validate_v4_rehearsal(tampered, self.valid_source_fingerprint, self.valid_restored_fingerprint)
        self.assertFalse(result.get('ok'))
        self.assertEqual(result.get('verdict'), 'FAIL')
        self.assertTrue(any('writer_timing_mismatch' in f or 'no_writer_overlap' in f for f in result.get('findings', [])))

    def test_reject_writers_started_after_dump_finished(self):
        """Review requirement: writers starting after pg_dump finished do not overlap."""
        tampered = copy.deepcopy(self.valid_summary)
        tampered['writers_concurrency']['writer_a_started_epoch'] = 100.65
        tampered['writers_concurrency']['pg_dump_backend_active_end'] = 100.60
        result = validate_v4_rehearsal(tampered, self.valid_source_fingerprint, self.valid_restored_fingerprint)
        self.assertFalse(result.get('ok'))
        self.assertEqual(result.get('verdict'), 'FAIL')
        self.assertTrue(any('writer_timing_mismatch' in f or 'no_writer_overlap' in f for f in result.get('findings', [])))

    def test_reject_nan_or_invalid_timing(self):
        """Review requirement: NaN or non-numeric timing stamps must fail-closed."""
        tampered = copy.deepcopy(self.valid_summary)
        tampered['writers_concurrency']['writer_a_started_epoch'] = float('nan')
        result = validate_v4_rehearsal(tampered, self.valid_source_fingerprint, self.valid_restored_fingerprint)
        self.assertFalse(result.get('ok'))
        self.assertEqual(result.get('verdict'), 'FAIL')
        self.assertTrue(any('invalid_timing' in f for f in result.get('findings', [])))

    def test_reject_inverted_start_end_timing(self):
        """Review requirement: writer end before start must be rejected."""
        tampered = copy.deepcopy(self.valid_summary)
        tampered['writers_concurrency']['writer_a_started_epoch'] = 100.50
        tampered['writers_concurrency']['writer_a_committed_epoch'] = 100.20
        result = validate_v4_rehearsal(tampered, self.valid_source_fingerprint, self.valid_restored_fingerprint)
        self.assertFalse(result.get('ok'))
        self.assertEqual(result.get('verdict'), 'FAIL')
        self.assertTrue(any('invalid_timing' in f for f in result.get('findings', [])))

    def test_reject_missing_pg_stat_activity_observation(self):
        """Review requirement: barrier state from notify alone cannot prove DB backend activity."""
        tampered = copy.deepcopy(self.valid_summary)
        tampered['writers_concurrency']['pg_stat_activity_dump_observed'] = False
        result = validate_v4_rehearsal(tampered, self.valid_source_fingerprint, self.valid_restored_fingerprint)
        self.assertFalse(result.get('ok'))
        self.assertEqual(result.get('verdict'), 'FAIL')
        self.assertTrue(any('dump_backend_not_observed' in f for f in result.get('findings', [])))

    def test_reject_snapshot_mismatch_or_omitted_snapshot_flag(self):
        """Review requirement: export an explicit PostgreSQL snapshot and use pg_dump --snapshot."""
        tampered = copy.deepcopy(self.valid_summary)
        tampered['snapshot']['pg_dump_snapshot_arg'] = ''
        result = validate_v4_rehearsal(tampered, self.valid_source_fingerprint, self.valid_restored_fingerprint)
        self.assertFalse(result.get('ok'))
        self.assertEqual(result.get('verdict'), 'FAIL')
        self.assertTrue(any('missing_snapshot_flag' in f or 'snapshot_mismatch' in f for f in result.get('findings', [])))

    def test_reject_snapshot_held_false(self):
        """Review requirement: held transaction must remain held until dump completes."""
        tampered = copy.deepcopy(self.valid_summary)
        tampered['snapshot']['export_tx_held'] = False
        result = validate_v4_rehearsal(tampered, self.valid_source_fingerprint, self.valid_restored_fingerprint)
        self.assertFalse(result.get('ok'))
        self.assertEqual(result.get('verdict'), 'FAIL')
        self.assertTrue(any('snapshot_tx_not_held' in f for f in result.get('findings', [])))

    def test_reject_pg_dump_failure(self):
        """Review requirement: dump failure or non-zero exit code must be rejected."""
        tampered = copy.deepcopy(self.valid_summary)
        tampered['snapshot']['pg_dump_completed'] = False
        tampered['snapshot']['pg_dump_exit_code'] = 1
        result = validate_v4_rehearsal(tampered, self.valid_source_fingerprint, self.valid_restored_fingerprint)
        self.assertFalse(result.get('ok'))
        self.assertEqual(result.get('verdict'), 'FAIL')
        self.assertTrue(any('dump_failed' in f for f in result.get('findings', [])))

    def test_reject_precommit_committed_after_snapshot(self):
        """Review requirement: precommit P0 committed after snapshot export must fail boundary check."""
        tampered = copy.deepcopy(self.valid_summary)
        tampered['writers_concurrency']['p0_committed_epoch'] = 100.10
        result = validate_v4_rehearsal(tampered, self.valid_source_fingerprint, self.valid_restored_fingerprint)
        self.assertFalse(result.get('ok'))
        self.assertEqual(result.get('verdict'), 'FAIL')
        self.assertTrue(any('precommit_order_violation' in f for f in result.get('findings', [])))

    def test_reject_missing_precommit_in_restore(self):
        """Pre-snapshot payment P0 committed before snapshot must be in restore."""
        tampered = copy.deepcopy(self.valid_summary)
        tampered['restored_verification']['p0_present_in_restore'] = False
        result = validate_v4_rehearsal(tampered, self.valid_source_fingerprint, self.valid_restored_fingerprint)
        self.assertFalse(result.get('ok'))
        self.assertEqual(result.get('verdict'), 'FAIL')
        self.assertTrue(any('missing_precommit' in f for f in result.get('findings', [])))

    def test_reject_included_late_commit_in_restore(self):
        """Post-snapshot concurrent payment committed after snapshot must NOT be in restore."""
        tampered = copy.deepcopy(self.valid_summary)
        tampered['restored_verification']['p1a_present_in_restore'] = True
        result = validate_v4_rehearsal(tampered, self.valid_source_fingerprint, self.valid_restored_fingerprint)
        self.assertFalse(result.get('ok'))
        self.assertEqual(result.get('verdict'), 'FAIL')
        self.assertTrue(any('included_late_commit' in f for f in result.get('findings', [])))

    def test_reject_missing_restored_ledger_entry(self):
        """Payment in restored DB without corresponding ledger transaction must be rejected."""
        tampered = copy.deepcopy(self.valid_summary)
        tampered['restored_verification']['club_transactions_count'] = 0
        tampered['restored_verification']['restored_transaction_ids'] = []
        result = validate_v4_rehearsal(tampered, self.valid_source_fingerprint, self.valid_restored_fingerprint)
        self.assertFalse(result.get('ok'))
        self.assertEqual(result.get('verdict'), 'FAIL')
        self.assertTrue(any('ledger_invariant_failed' in f or 'cardinality_mismatch' in f for f in result.get('findings', [])))

    def test_reject_missing_restored_audit_entry(self):
        """Payment in restored DB without corresponding audit event must be rejected."""
        tampered = copy.deepcopy(self.valid_summary)
        tampered['restored_verification']['audit_events_count'] = 0
        tampered['restored_verification']['restored_audit_ids'] = []
        result = validate_v4_rehearsal(tampered, self.valid_source_fingerprint, self.valid_restored_fingerprint)
        self.assertFalse(result.get('ok'))
        self.assertEqual(result.get('verdict'), 'FAIL')
        self.assertTrue(any('audit_invariant_failed' in f or 'cardinality_mismatch' in f for f in result.get('findings', [])))

    def test_reject_duplicate_ledger_entry(self):
        """More ledger entries than payments in restored DB must be rejected."""
        tampered = copy.deepcopy(self.valid_summary)
        tampered['restored_verification']['club_transactions_count'] = 2
        result = validate_v4_rehearsal(tampered, self.valid_source_fingerprint, self.valid_restored_fingerprint)
        self.assertFalse(result.get('ok'))
        self.assertEqual(result.get('verdict'), 'FAIL')
        self.assertTrue(any('ledger_invariant_failed' in f or 'cardinality_mismatch' in f for f in result.get('findings', [])))

    def test_reject_fingerprint_row_count_mismatch(self):
        """If fingerprint table row counts do not match verified expectation, reject."""
        tampered_fp = copy.deepcopy(self.valid_restored_fingerprint)
        tampered_fp['public.payments']['rows'] = 2
        result = validate_v4_rehearsal(self.valid_summary, self.valid_source_fingerprint, tampered_fp)
        self.assertFalse(result.get('ok'))
        self.assertEqual(result.get('verdict'), 'FAIL')
        self.assertTrue(any('fingerprint_mismatch' in f for f in result.get('findings', [])))

    def test_reject_idempotency_replay_growth(self):
        """Replaying P0 request against restored DB must produce 0 growth in payments/ledger/audit."""
        tampered = copy.deepcopy(self.valid_summary)
        tampered['restored_verification']['replay_p0_growth']['payments'] = 1
        result = validate_v4_rehearsal(tampered, self.valid_source_fingerprint, self.valid_restored_fingerprint)
        self.assertFalse(result.get('ok'))
        self.assertEqual(result.get('verdict'), 'FAIL')
        self.assertTrue(any('idempotency_replay_failed' in f for f in result.get('findings', [])))

    def test_reject_truthy_nonboolean_flags(self):
        """Review requirement: nonboolean truthy flags (e.g. 1 or 'true') must be rejected."""
        tampered = copy.deepcopy(self.valid_summary)
        tampered['snapshot']['export_tx_held'] = 1
        result = validate_v4_rehearsal(tampered, self.valid_source_fingerprint, self.valid_restored_fingerprint)
        self.assertFalse(result.get('ok'))
        self.assertEqual(result.get('verdict'), 'FAIL')
        self.assertTrue(any('strict_type_violation' in f for f in result.get('findings', [])))

    def test_reject_string_as_amount_type(self):
        """Review requirement: amount_vnd must be strictly int, not string."""
        tampered = copy.deepcopy(self.valid_summary)
        tampered['source_operations']['p0_precommit']['amount_vnd'] = '10000'
        result = validate_v4_rehearsal(tampered, self.valid_source_fingerprint, self.valid_restored_fingerprint)
        self.assertFalse(result.get('ok'))
        self.assertEqual(result.get('verdict'), 'FAIL')
        self.assertTrue(any('strict_type_violation' in f for f in result.get('findings', [])))

    def test_reject_cleanup_claimed_true_with_empty_resource_list(self):
        """Review requirement: cleanup claimed true with resource list not verified must be rejected."""
        tampered = copy.deepcopy(self.valid_summary)
        tampered['cleanup']['resources_verified_absent'] = []
        result = validate_v4_rehearsal(tampered, self.valid_source_fingerprint, self.valid_restored_fingerprint)
        self.assertFalse(result.get('ok'))
        self.assertEqual(result.get('verdict'), 'FAIL')
        self.assertTrue(any('unverified_cleanup_resources' in f for f in result.get('findings', [])))

    def test_reject_unverified_or_failed_cleanup(self):
        """Containers, networks, and private dump files must be verified absent."""
        tampered = copy.deepcopy(self.valid_summary)
        tampered['cleanup']['ok'] = False
        tampered['cleanup']['cleanup_errors'] = ['container still exists: bh07-v4-target-db']
        result = validate_v4_rehearsal(tampered, self.valid_source_fingerprint, self.valid_restored_fingerprint)
        self.assertFalse(result.get('ok'))
        self.assertEqual(result.get('verdict'), 'FAIL')
        self.assertTrue(any('cleanup_failed' in f for f in result.get('findings', [])))

    def test_reject_exposed_secrets(self):
        """Ensure JWTs or service credentials are not exposed in receipt summary."""
        tampered = copy.deepcopy(self.valid_summary)
        # Construct synthetic token dynamically without embedding literal credentials
        seg1 = base64.urlsafe_b64encode(b'{"alg":"none"}').decode('utf-8').rstrip('=')
        seg2 = base64.urlsafe_b64encode(b'{"sub":"user"}').decode('utf-8').rstrip('=')
        seg3 = base64.urlsafe_b64encode(b'sig').decode('utf-8').rstrip('=')
        tampered['leak'] = f"{seg1}.{seg2}.{seg3}"
        result = validate_v4_rehearsal(tampered, self.valid_source_fingerprint, self.valid_restored_fingerprint)
        self.assertFalse(result.get('ok'))
        self.assertEqual(result.get('verdict'), 'FAIL')
        self.assertTrue(any('exposed_secret' in f for f in result.get('findings', [])))

    def test_reject_missing_source_fingerprint(self):
        """Mandatory source fingerprint: rejecting if None."""
        result = validate_v4_rehearsal(self.valid_summary, None, self.valid_restored_fingerprint)
        self.assertFalse(result.get('ok'))
        self.assertEqual(result.get('verdict'), 'FAIL')
        self.assertTrue(any('missing_source_fingerprint' in f for f in result.get('findings', [])))

    def test_reject_missing_restored_fingerprint(self):
        """Mandatory restored fingerprint: rejecting if None."""
        result = validate_v4_rehearsal(self.valid_summary, self.valid_source_fingerprint, None)
        self.assertFalse(result.get('ok'))
        self.assertEqual(result.get('verdict'), 'FAIL')
        self.assertTrue(any('missing_restored_fingerprint' in f for f in result.get('findings', [])))

    def test_reject_missing_both_fingerprints(self):
        """Mandatory fingerprints: rejecting if both None."""
        result = validate_v4_rehearsal(self.valid_summary, None, None)
        self.assertFalse(result.get('ok'))
        self.assertEqual(result.get('verdict'), 'FAIL')

    def test_reject_malformed_fingerprint_hashes(self):
        """Fingerprint SHA-256 must be valid 64-char hex."""
        tampered_fp = copy.deepcopy(self.valid_restored_fingerprint)
        tampered_fp['public.payments']['sha256'] = 'not-a-sha256'
        result = validate_v4_rehearsal(self.valid_summary, self.valid_source_fingerprint, tampered_fp)
        self.assertFalse(result.get('ok'))
        self.assertEqual(result.get('verdict'), 'FAIL')
        self.assertTrue(any('malformed_restored_hashes' in f for f in result.get('findings', [])))

    def test_reject_source_count_mismatch(self):
        """Source fingerprint table row count must match expected scoped operations."""
        tampered_fp = copy.deepcopy(self.valid_source_fingerprint)
        tampered_fp['public.payments']['rows'] = 999
        result = validate_v4_rehearsal(self.valid_summary, tampered_fp, self.valid_restored_fingerprint)
        self.assertFalse(result.get('ok'))
        self.assertEqual(result.get('verdict'), 'FAIL')
        self.assertTrue(any('source_count_mismatch' in f for f in result.get('findings', [])))

    def test_reject_wrong_numeric_amount(self):
        """Scoped operation amounts must match expected contractual values."""
        tampered = copy.deepcopy(self.valid_summary)
        tampered['source_operations']['p0_precommit']['amount_vnd'] = 99999
        result = validate_v4_rehearsal(tampered, self.valid_source_fingerprint, self.valid_restored_fingerprint)
        self.assertFalse(result.get('ok'))
        self.assertEqual(result.get('verdict'), 'FAIL')
        self.assertTrue(any('amount_mismatch' in f for f in result.get('findings', [])))

    def test_reject_duplicate_source_payment_id(self):
        """Operations cannot share payment IDs."""
        tampered = copy.deepcopy(self.valid_summary)
        tampered['source_operations']['p1a_concurrent']['payment_id'] = self.p0_pay_id
        result = validate_v4_rehearsal(tampered, self.valid_source_fingerprint, self.valid_restored_fingerprint)
        self.assertFalse(result.get('ok'))
        self.assertEqual(result.get('verdict'), 'FAIL')
        self.assertTrue(any('duplicate_source_payment_id' in f for f in result.get('findings', [])))

    def test_reject_duplicate_source_request_id(self):
        """Operations cannot share request IDs."""
        tampered = copy.deepcopy(self.valid_summary)
        tampered['source_operations']['p1a_concurrent']['request_id'] = self.p0_req_id
        result = validate_v4_rehearsal(tampered, self.valid_source_fingerprint, self.valid_restored_fingerprint)
        self.assertFalse(result.get('ok'))
        self.assertEqual(result.get('verdict'), 'FAIL')
        self.assertTrue(any('duplicate_source_request_id' in f for f in result.get('findings', [])))

    def test_reject_substituted_restored_payment_id(self):
        """Restored payment IDs must strictly match precommit P0 payment ID."""
        tampered = copy.deepcopy(self.valid_summary)
        tampered['restored_verification']['restored_payment_ids'] = ['other-payment']
        result = validate_v4_rehearsal(tampered, self.valid_source_fingerprint, self.valid_restored_fingerprint)
        self.assertFalse(result.get('ok'))
        self.assertEqual(result.get('verdict'), 'FAIL')
        self.assertTrue(any('substituted_restored_payment_id' in f for f in result.get('findings', [])))

    def test_reject_failed_status(self):
        """Receipt with status FAIL must be rejected."""
        tampered = copy.deepcopy(self.valid_summary)
        tampered['status'] = 'FAIL'
        result = validate_v4_rehearsal(tampered, self.valid_source_fingerprint, self.valid_restored_fingerprint)
        self.assertFalse(result.get('ok'))
        self.assertEqual(result.get('verdict'), 'FAIL')
        self.assertTrue(any('failed_status' in f for f in result.get('findings', [])))

    def test_reject_dirty_source(self):
        """Dirty source must be rejected (provenance clean contract)."""
        tampered = copy.deepcopy(self.valid_summary)
        tampered['git_dirty'] = True
        result = validate_v4_rehearsal(tampered, self.valid_source_fingerprint, self.valid_restored_fingerprint)
        self.assertFalse(result.get('ok'))
        self.assertEqual(result.get('verdict'), 'FAIL')
        self.assertTrue(any('dirty_source' in f for f in result.get('findings', [])))

    def test_reject_invalid_source_sha(self):
        """Invalid or malformed git SHA must be rejected."""
        tampered = copy.deepcopy(self.valid_summary)
        tampered['tested_source_sha'] = 'invalid'
        result = validate_v4_rehearsal(tampered, self.valid_source_fingerprint, self.valid_restored_fingerprint)
        self.assertFalse(result.get('ok'))
        self.assertEqual(result.get('verdict'), 'FAIL')
        self.assertTrue(any('invalid_source_sha' in f for f in result.get('findings', [])))

    def test_reject_cleanup_missing_network(self):
        """Cleanup manifest must include verified network."""
        tampered = copy.deepcopy(self.valid_summary)
        tampered['cleanup']['resources_verified_absent'] = ['bh07-v4-src-db', 'bh07-v4-target-db']
        result = validate_v4_rehearsal(tampered, self.valid_source_fingerprint, self.valid_restored_fingerprint)
        self.assertFalse(result.get('ok'))
        self.assertEqual(result.get('verdict'), 'FAIL')
        self.assertTrue(any('unverified_cleanup_resources' in f or 'cleanup_resource_mismatch' in f for f in result.get('findings', [])))

    def test_reject_serial_writers_inside_dump(self):
        """Review requirement V4-R4: non-overlapping serial writer windows must be rejected."""
        tampered = copy.deepcopy(self.valid_summary)
        tampered['writers_concurrency']['writer_a_started_epoch'] = 100.10
        tampered['writers_concurrency']['writer_a_committed_epoch'] = 100.20
        tampered['writers_concurrency']['writer_b_started_epoch'] = 100.30
        tampered['writers_concurrency']['writer_b_committed_epoch'] = 100.40
        result = validate_v4_rehearsal(tampered, self.valid_source_fingerprint, self.valid_restored_fingerprint)
        self.assertFalse(result.get('ok'))
        self.assertEqual(result.get('verdict'), 'FAIL')
        self.assertTrue(any('no_writer_overlap' in f for f in result.get('findings', [])))

    def test_reject_unrelated_cleanup_resources(self):
        """Review requirement V4-R5: verified absent list must belong to rehearsal owned namespace."""
        tampered = copy.deepcopy(self.valid_summary)
        tampered['cleanup']['resources_verified_absent'] = ['unrelated-src-db', 'unrelated-target-db', 'unrelated-net']
        result = validate_v4_rehearsal(tampered, self.valid_source_fingerprint, self.valid_restored_fingerprint)
        self.assertFalse(result.get('ok'))
        self.assertEqual(result.get('verdict'), 'FAIL')
        self.assertTrue(any('unrelated_cleanup_resources' in f or 'cleanup_resource_mismatch' in f for f in result.get('findings', [])))

    def test_reject_cleanup_duplicate_resources(self):
        """Duplicate entries in cleanup list must fail-closed."""
        tampered = copy.deepcopy(self.valid_summary)
        tampered['cleanup']['resources_verified_absent'] = ['bh07-v4-src-db', 'bh07-v4-src-db', 'bh07-v4-target-db', 'bh07-v4-net']
        result = validate_v4_rehearsal(tampered, self.valid_source_fingerprint, self.valid_restored_fingerprint)
        self.assertFalse(result.get('ok'))
        self.assertEqual(result.get('verdict'), 'FAIL')
        self.assertTrue(any('cleanup_duplicate_resources' in f for f in result.get('findings', [])))

    def test_reject_missing_db_observation_receipt(self):
        """DB observation receipt is mandatory to verify real pg_dump activity."""
        tampered = copy.deepcopy(self.valid_summary)
        del tampered['writers_concurrency']['db_observation_receipt']
        result = validate_v4_rehearsal(tampered, self.valid_source_fingerprint, self.valid_restored_fingerprint)
        self.assertFalse(result.get('ok'))
        self.assertEqual(result.get('verdict'), 'FAIL')
        self.assertTrue(any('dump_backend_not_observed' in f for f in result.get('findings', [])))

    def test_reject_invalid_dump_pid(self):
        """Dump PID in observation receipt must be positive int."""
        tampered = copy.deepcopy(self.valid_summary)
        tampered['writers_concurrency']['db_observation_receipt']['dump_pid'] = 0
        result = validate_v4_rehearsal(tampered, self.valid_source_fingerprint, self.valid_restored_fingerprint)
        self.assertFalse(result.get('ok'))
        self.assertEqual(result.get('verdict'), 'FAIL')
        self.assertTrue(any('dump_backend_not_observed' in f for f in result.get('findings', [])))

    def test_reject_relational_amount_mismatch_in_row_evidence(self):
        """Row evidence payment amount must match operation amount."""
        tampered = copy.deepcopy(self.valid_summary)
        tampered['source_operations']['p0_precommit']['row_evidence']['payment']['amount_vnd'] = 99999
        result = validate_v4_rehearsal(tampered, self.valid_source_fingerprint, self.valid_restored_fingerprint)
        self.assertFalse(result.get('ok'))
        self.assertEqual(result.get('verdict'), 'FAIL')
        self.assertTrue(any('relational_evidence_mismatch' in f or 'relational_digest_mismatch' in f for f in result.get('findings', [])))

    def test_reject_relational_fk_mismatch_in_row_evidence(self):
        """Row evidence ledger source_payment_id must match operation payment_id."""
        tampered = copy.deepcopy(self.valid_summary)
        tampered['source_operations']['p0_precommit']['row_evidence']['ledger']['source_payment_id'] = '00000000-0000-4000-8000-000000000099'
        result = validate_v4_rehearsal(tampered, self.valid_source_fingerprint, self.valid_restored_fingerprint)
        self.assertFalse(result.get('ok'))
        self.assertEqual(result.get('verdict'), 'FAIL')
        self.assertTrue(any('relational_evidence_mismatch' in f or 'relational_digest_mismatch' in f for f in result.get('findings', [])))

    def test_reject_relational_digest_mismatch(self):
        """Relational digest must match hash of canonical row evidence."""
        tampered = copy.deepcopy(self.valid_summary)
        tampered['source_operations']['p0_precommit']['relational_digest'] = 'f' * 64
        result = validate_v4_rehearsal(tampered, self.valid_source_fingerprint, self.valid_restored_fingerprint)
        self.assertFalse(result.get('ok'))
        self.assertEqual(result.get('verdict'), 'FAIL')
        self.assertTrue(any('relational_digest_mismatch' in f for f in result.get('findings', [])))

    def test_reject_replay_data_mutation(self):
        """Restored DB fingerprint changing after replay must be rejected."""
        tampered = copy.deepcopy(self.valid_summary)
        tampered['restored_verification']['replay_evidence']['after_replay_fingerprint'] = '9' * 64
        result = validate_v4_rehearsal(tampered, self.valid_source_fingerprint, self.valid_restored_fingerprint)
        self.assertFalse(result.get('ok'))
        self.assertEqual(result.get('verdict'), 'FAIL')
        self.assertTrue(any('replay_data_mutation' in f for f in result.get('findings', [])))

    def test_reject_request_payment_wrong_valid_digest(self):
        """Row evidence request payment_id mismatch must be rejected even with recomputed digest."""
        tampered = copy.deepcopy(self.valid_summary)
        op = tampered['source_operations']['p0_precommit']
        op['row_evidence']['request']['payment_id'] = '60000000-0000-4000-8000-000000000099'
        op['relational_digest'] = digest(op['row_evidence'])
        tampered['restored_verification']['restored_row_evidence'] = copy.deepcopy(op['row_evidence'])
        result = validate_v4_rehearsal(tampered, self.valid_source_fingerprint, self.valid_restored_fingerprint)
        self.assertFalse(result.get('ok'))
        self.assertEqual(result.get('verdict'), 'FAIL')
        self.assertTrue(any('relational_evidence_mismatch' in f for f in result.get('findings', [])))

    def test_reject_invalid_equal_replay_fingerprints(self):
        """Replay fingerprints must be valid 64-char hex SHA256, not arbitrary equal strings."""
        tampered = copy.deepcopy(self.valid_summary)
        tampered['restored_verification']['replay_evidence']['before_replay_fingerprint'] = 'not-a-digest'
        tampered['restored_verification']['replay_evidence']['after_replay_fingerprint'] = 'not-a-digest'
        result = validate_v4_rehearsal(tampered, self.valid_source_fingerprint, self.valid_restored_fingerprint)
        self.assertFalse(result.get('ok'))
        self.assertEqual(result.get('verdict'), 'FAIL')
        self.assertTrue(any('invalid_replay_fingerprint' in f or 'replay_fingerprint_mismatch' in f for f in result.get('findings', [])))

    def test_reject_wrong_stored_request_status(self):
        """Stored request with failed status (500/FAIL) must be rejected even with recomputed digest."""
        tampered = copy.deepcopy(self.valid_summary)
        op = tampered['source_operations']['p0_precommit']
        op['row_evidence']['request']['status'] = 500
        op['relational_digest'] = digest(op['row_evidence'])
        tampered['restored_verification']['restored_row_evidence'] = copy.deepcopy(op['row_evidence'])
        result = validate_v4_rehearsal(tampered, self.valid_source_fingerprint, self.valid_restored_fingerprint)
        self.assertFalse(result.get('ok'))
        self.assertEqual(result.get('verdict'), 'FAIL')
        self.assertTrue(any('relational_evidence_mismatch' in f for f in result.get('findings', [])))

    def test_reject_missing_stored_request(self):
        """Missing stored request in row evidence must be rejected."""
        tampered = copy.deepcopy(self.valid_summary)
        op = tampered['source_operations']['p0_precommit']
        op['row_evidence'].pop('request')
        op['relational_digest'] = digest(op['row_evidence'])
        tampered['restored_verification']['restored_row_evidence'] = copy.deepcopy(op['row_evidence'])
        result = validate_v4_rehearsal(tampered, self.valid_source_fingerprint, self.valid_restored_fingerprint)
        self.assertFalse(result.get('ok'))
        self.assertEqual(result.get('verdict'), 'FAIL')
        self.assertTrue(any('missing_stored_request' in f for f in result.get('findings', [])))

    def test_reject_replay_fingerprint_mismatch_with_restored_db(self):
        """Replay before/after fingerprint must match the restored database payments sha256."""
        tampered = copy.deepcopy(self.valid_summary)
        tampered['restored_verification']['replay_evidence']['before_replay_fingerprint'] = '1' * 64
        tampered['restored_verification']['replay_evidence']['after_replay_fingerprint'] = '1' * 64
        result = validate_v4_rehearsal(tampered, self.valid_source_fingerprint, self.valid_restored_fingerprint)
        self.assertFalse(result.get('ok'))
        self.assertEqual(result.get('verdict'), 'FAIL')
        self.assertTrue(any('replay_fingerprint_mismatch' in f for f in result.get('findings', [])))

    def test_reject_stored_result_payment_id_mismatch(self):
        """Stored result payment_id inside request must match operation payment_id."""
        tampered = copy.deepcopy(self.valid_summary)
        op = tampered['source_operations']['p0_precommit']
        op['row_evidence']['request']['result']['payment_id'] = '60000000-0000-4000-8000-000000000099'
        op['relational_digest'] = digest(op['row_evidence'])
        tampered['restored_verification']['restored_row_evidence'] = copy.deepcopy(op['row_evidence'])
        result = validate_v4_rehearsal(tampered, self.valid_source_fingerprint, self.valid_restored_fingerprint)
        self.assertFalse(result.get('ok'))
        self.assertEqual(result.get('verdict'), 'FAIL')
        self.assertTrue(any('relational_evidence_mismatch' in f for f in result.get('findings', [])))

    def test_reject_stored_result_amount_mismatch(self):
        """Stored result amount_vnd inside request must match operation amount."""
        tampered = copy.deepcopy(self.valid_summary)
        op = tampered['source_operations']['p0_precommit']
        op['row_evidence']['request']['result']['amount_vnd'] = 99999
        op['relational_digest'] = digest(op['row_evidence'])
        tampered['restored_verification']['restored_row_evidence'] = copy.deepcopy(op['row_evidence'])
        result = validate_v4_rehearsal(tampered, self.valid_source_fingerprint, self.valid_restored_fingerprint)
        self.assertFalse(result.get('ok'))
        self.assertEqual(result.get('verdict'), 'FAIL')
        self.assertTrue(any('relational_evidence_mismatch' in f for f in result.get('findings', [])))


class V4CoordinationBarrierTests(unittest.TestCase):
    """Verifies deterministic coordination between dump thread and concurrent HTTP writer threads."""

    def test_barrier_requires_snapshot_and_active_backend(self):
        if _MISSING_IMPORT_ERROR:
            self.fail(f"Coordination barrier missing: {_MISSING_IMPORT_ERROR}")

        barrier = V4CoordinationBarrier(timeout_seconds=5.0)
        self.assertFalse(barrier.is_dump_active())

        barrier.notify_dump_started(snapshot_id='00000003-0000001B-1')
        self.assertTrue(barrier.is_dump_active())
        self.assertEqual(barrier.get_snapshot_id(), '00000003-0000001B-1')

        ready = barrier.wait_until_dump_active(timeout=1.0)
        self.assertTrue(ready)

        barrier.notify_dump_finished()
        self.assertFalse(barrier.is_dump_active())


if __name__ == '__main__':
    unittest.main()
