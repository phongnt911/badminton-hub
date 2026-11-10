"""Standalone regression probe for BH-07 V4 concurrent backup/restore validation.

Runs independent positive controls and semantic mutants without requiring a live
Docker daemon. Confirms fail-closed behavior across:
- Mandatory validated fingerprints and SHA-256 hex digests.
- Exact scoped amounts, relational integrity, and unique operation IDs.
- Restored snapshot membership and absence of post-snapshot late commits.
- Provenance: clean working tree (git_dirty False) and valid 40-char SHA.
- Unauthorized actor rejection.
- Concurrency timing overlap & pg_stat_activity observation.
- Explicit snapshot export & held transaction invariant.
- 1:1:1:1 relational ledger/audit/request invariant and zero idempotency growth.
- Strict typing, nonboolean truthy rejection, and cleanup verification.
- Secret leakage detection for synthetic tokens.

Run:
python scripts/bh07_backup/v4_concurrent_probe.py
"""
import base64
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.bh07_backup.run_v4_concurrent_rehearsal import (
    validate_v4_rehearsal,
    V4CoordinationBarrier,
    ACTUAL_BASE_SHA,
    digest,
)

TABLES = ('payments', 'club_transactions', 'audit_events', 'operation_requests')


def fp(rows, sha_hex='a' * 64):
    return {'public.' + table: {'rows': rows, 'sha256': sha_hex} for table in TABLES}


def make_synthetic_token():
    seg1 = base64.urlsafe_b64encode(b'{"alg":"none"}').decode('utf-8').rstrip('=')
    seg2 = base64.urlsafe_b64encode(b'{"sub":"user"}').decode('utf-8').rstrip('=')
    seg3 = base64.urlsafe_b64encode(b'sig').decode('utf-8').rstrip('=')
    return f"{seg1}.{seg2}.{seg3}"


def build_canonical_summary():
    p0_ev = {
        'payment': {'id': '6000-00', 'amount_vnd': 10000, 'request_id': 'c000-00', 'player_id': '3000-00'},
        'ledger': {'id': '7000-00', 'source_payment_id': '6000-00', 'amount': 10000},
        'audit': {'id': '8000-00', 'request_id': 'c000-00', 'session_id': '1000-00'},
        'request': {
            'request_id': 'c000-00',
            'payment_id': '6000-00',
            'operation': 'record_cash_payment',
            'status': 'confirmed',
            'result': {'payment_id': '6000-00', 'amount_vnd': 10000, 'status': 'confirmed'},
        },
    }
    p1a_ev = {
        'payment': {'id': '6000-1a', 'amount_vnd': 15000, 'request_id': 'c000-1a', 'player_id': '3000-00'},
        'ledger': {'id': '7000-1a', 'source_payment_id': '6000-1a', 'amount': 15000},
        'audit': {'id': '8000-1a', 'request_id': 'c000-1a', 'session_id': '1000-00'},
        'request': {
            'request_id': 'c000-1a',
            'payment_id': '6000-1a',
            'operation': 'record_cash_payment',
            'status': 'confirmed',
            'result': {'payment_id': '6000-1a', 'amount_vnd': 15000, 'status': 'confirmed'},
        },
    }
    p1b_ev = {
        'payment': {'id': '6000-1b', 'amount_vnd': 20000, 'request_id': 'c000-1b', 'player_id': '3000-00'},
        'ledger': {'id': '7000-1b', 'source_payment_id': '6000-1b', 'amount': 20000},
        'audit': {'id': '8000-1b', 'request_id': 'c000-1b', 'session_id': '1000-00'},
        'request': {
            'request_id': 'c000-1b',
            'payment_id': '6000-1b',
            'operation': 'record_cash_payment',
            'status': 'confirmed',
            'result': {'payment_id': '6000-1b', 'amount_vnd': 20000, 'status': 'confirmed'},
        },
    }

    return {
        'status': 'PASS',
        'tested_source_sha': ACTUAL_BASE_SHA,
        'git_dirty': False,
        'snapshot': {
            'snapshot_id': '00000003-0000001B-1',
            'snapshot_exported_epoch': 100.00,
            'export_tx_held': True,
            'pg_dump_snapshot_arg': '--snapshot=00000003-0000001B-1',
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
            'p0_precommit': {'request_id': 'c000-00', 'payment_id': '6000-00', 'transaction_id': '7000-00', 'audit_event_id': '8000-00', 'status': 200, 'amount_vnd': 10000, 'row_evidence': p0_ev, 'relational_digest': digest(p0_ev)},
            'p1a_concurrent': {'request_id': 'c000-1a', 'payment_id': '6000-1a', 'transaction_id': '7000-1a', 'audit_event_id': '8000-1a', 'status': 200, 'amount_vnd': 15000, 'row_evidence': p1a_ev, 'relational_digest': digest(p1a_ev)},
            'p1b_concurrent': {'request_id': 'c000-1b', 'payment_id': '6000-1b', 'transaction_id': '7000-1b', 'audit_event_id': '8000-1b', 'status': 200, 'amount_vnd': 20000, 'row_evidence': p1b_ev, 'relational_digest': digest(p1b_ev)},
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
            'restored_payment_ids': ['6000-00'],
            'restored_transaction_ids': ['7000-00'],
            'restored_audit_ids': ['8000-00'],
            'restored_request_ids': ['c000-00'],
            'restored_row_evidence': copy.deepcopy(p0_ev),
            'replay_p0_idempotent': True,
            'replay_p0_growth': {'payments': 0, 'club_transactions': 0, 'audit_events': 0, 'operation_requests': 0},
            'replay_evidence': {
                'replay_status': 200,
                'replay_payment_id': '6000-00',
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


def main():
    print("=== BH-07 V4 Concurrent Backup Validation Probe ===")
    controls_passed = 0

    canonical_source_fp = fp(3)
    canonical_restored_fp = fp(1, sha_hex='e' * 64)

    # 1. Canonical positive control
    canonical = build_canonical_summary()
    res = validate_v4_rehearsal(canonical, canonical_source_fp, canonical_restored_fp)
    assert res['ok'] is True and res['verdict'] == 'PASS', f"Canonical positive control failed: {res}"
    controls_passed += 1
    print("  [OK] Canonical positive control")

    # 2. Semantic mutants on summary
    mutants = [
        ('unauthorized_member', lambda s: s['actors'].__setitem__('writer_b', 'membera'), 'unauthorized_finance_actor'),
        ('unauthorized_outsider', lambda s: s['actors'].__setitem__('writer_a', 'outsider'), 'unauthorized_finance_actor'),
        ('no_overlap_flag', lambda s: s['writers_concurrency'].__setitem__('overlap_verified', False), 'no_writer_overlap'),
        ('dump_not_observed', lambda s: s['writers_concurrency'].__setitem__('pg_stat_activity_dump_observed', False), 'dump_backend_not_observed'),
        ('writers_before_dump', lambda s: s['writers_concurrency'].__setitem__('writer_a_committed_epoch', 99.0), 'writer_timing_mismatch'),
        ('nan_timing', lambda s: s['writers_concurrency'].__setitem__('writer_a_started_epoch', float('nan')), 'invalid_timing'),
        ('missing_snapshot_flag', lambda s: s['snapshot'].__setitem__('pg_dump_snapshot_arg', ''), 'missing_snapshot_flag'),
        ('snapshot_tx_not_held', lambda s: s['snapshot'].__setitem__('export_tx_held', False), 'snapshot_tx_not_held'),
        ('dump_failure', lambda s: s['snapshot'].__setitem__('pg_dump_exit_code', 1), 'dump_failed'),
        ('precommit_order_violation', lambda s: s['writers_concurrency'].__setitem__('p0_committed_epoch', 101.0), 'precommit_order_violation'),
        ('missing_precommit_restore', lambda s: s['restored_verification'].__setitem__('p0_present_in_restore', False), 'missing_precommit'),
        ('included_late_commit_restore', lambda s: s['restored_verification'].__setitem__('p1a_present_in_restore', True), 'included_late_commit'),
        ('missing_restored_ledger', lambda s: s['restored_verification'].__setitem__('club_transactions_count', 0), 'ledger_invariant_failed'),
        ('missing_restored_audit', lambda s: s['restored_verification'].__setitem__('audit_events_count', 0), 'audit_invariant_failed'),
        ('idempotency_replay_growth', lambda s: s['restored_verification']['replay_p0_growth'].__setitem__('payments', 1), 'idempotency_replay_failed'),
        ('truthy_nonboolean', lambda s: s['snapshot'].__setitem__('export_tx_held', 1), 'strict_type_violation'),
        ('amount_as_string', lambda s: s['source_operations']['p0_precommit'].__setitem__('amount_vnd', '10000'), 'strict_type_violation'),
        ('wrong_numeric_amount', lambda s: s['source_operations']['p0_precommit'].__setitem__('amount_vnd', 99999), 'amount_mismatch'),
        ('duplicate_source_payment_id', lambda s: s['source_operations']['p1a_concurrent'].__setitem__('payment_id', s['source_operations']['p0_precommit']['payment_id']), 'duplicate_source_payment_id'),
        ('duplicate_source_request_id', lambda s: s['source_operations']['p1a_concurrent'].__setitem__('request_id', s['source_operations']['p0_precommit']['request_id']), 'duplicate_source_request_id'),
        ('substituted_restored_payment_id', lambda s: s['restored_verification'].__setitem__('restored_payment_ids', ['other-payment']), 'substituted_restored_payment_id'),
        ('failed_status', lambda s: s.__setitem__('status', 'FAIL'), 'failed_status'),
        ('dirty_source', lambda s: s.__setitem__('git_dirty', True), 'dirty_source'),
        ('invalid_source_sha', lambda s: s.__setitem__('tested_source_sha', 'invalid'), 'invalid_source_sha'),
        ('cleanup_missing_network', lambda s: s['cleanup'].__setitem__('resources_verified_absent', ['bh07-v4-src-db', 'bh07-v4-target-db']), 'unverified_cleanup_resources'),
        ('serial_writers_inside_dump', lambda s: s['writers_concurrency'].update(writer_a_started_epoch=100.10, writer_a_committed_epoch=100.20, writer_b_started_epoch=100.30, writer_b_committed_epoch=100.40), 'no_writer_overlap'),
        ('unrelated_cleanup_resources', lambda s: s['cleanup'].__setitem__('resources_verified_absent', ['unrelated-src-db', 'unrelated-target-db', 'unrelated-net']), 'unrelated_cleanup_resources'),
        ('cleanup_duplicate_resources', lambda s: s['cleanup'].__setitem__('resources_verified_absent', ['bh07-v4-src-db', 'bh07-v4-src-db', 'bh07-v4-target-db', 'bh07-v4-net']), 'cleanup_duplicate_resources'),
        ('missing_db_observation_receipt', lambda s: s['writers_concurrency'].__delitem__('db_observation_receipt'), 'dump_backend_not_observed'),
        ('invalid_dump_pid', lambda s: s['writers_concurrency']['db_observation_receipt'].__setitem__('dump_pid', 0), 'dump_backend_not_observed'),
        ('relational_amount_mismatch', lambda s: s['source_operations']['p0_precommit']['row_evidence']['payment'].__setitem__('amount_vnd', 99999), 'relational_evidence_mismatch'),
        ('relational_fk_mismatch', lambda s: s['source_operations']['p0_precommit']['row_evidence']['ledger'].__setitem__('source_payment_id', 'wrong-id'), 'relational_evidence_mismatch'),
        ('relational_digest_mismatch', lambda s: s['source_operations']['p0_precommit'].__setitem__('relational_digest', 'f' * 64), 'relational_digest_mismatch'),
        ('replay_data_mutation', lambda s: s['restored_verification']['replay_evidence'].__setitem__('after_replay_fingerprint', '9' * 64), 'replay_data_mutation'),
        ('request_payment_wrong_valid_digest', lambda s: (
            s['source_operations']['p0_precommit']['row_evidence']['request'].__setitem__('payment_id', '6000-99'),
            s['source_operations']['p0_precommit'].__setitem__('relational_digest', digest(s['source_operations']['p0_precommit']['row_evidence'])),
            s['restored_verification'].__setitem__('restored_row_evidence', copy.deepcopy(s['source_operations']['p0_precommit']['row_evidence']))
        ), 'relational_evidence_mismatch'),
        ('invalid_equal_replay_fingerprints', lambda s: (
            s['restored_verification']['replay_evidence'].__setitem__('before_replay_fingerprint', 'not-a-digest'),
            s['restored_verification']['replay_evidence'].__setitem__('after_replay_fingerprint', 'not-a-digest')
        ), 'invalid_replay_fingerprint'),
        ('wrong_stored_request_status', lambda s: (
            s['source_operations']['p0_precommit']['row_evidence']['request'].__setitem__('status', 500),
            s['source_operations']['p0_precommit'].__setitem__('relational_digest', digest(s['source_operations']['p0_precommit']['row_evidence'])),
            s['restored_verification'].__setitem__('restored_row_evidence', copy.deepcopy(s['source_operations']['p0_precommit']['row_evidence']))
        ), 'relational_evidence_mismatch'),
        ('missing_stored_request', lambda s: (
            s['source_operations']['p0_precommit']['row_evidence'].pop('request'),
            s['source_operations']['p0_precommit'].__setitem__('relational_digest', digest(s['source_operations']['p0_precommit']['row_evidence'])),
            s['restored_verification'].__setitem__('restored_row_evidence', copy.deepcopy(s['source_operations']['p0_precommit']['row_evidence']))
        ), 'missing_stored_request'),
        ('replay_fingerprint_mismatch_with_restored_db', lambda s: (
            s['restored_verification']['replay_evidence'].__setitem__('before_replay_fingerprint', '1' * 64),
            s['restored_verification']['replay_evidence'].__setitem__('after_replay_fingerprint', '1' * 64)
        ), 'replay_fingerprint_mismatch'),
        ('cleanup_failed', lambda s: s['cleanup'].__setitem__('ok', False), 'cleanup_failed'),
        ('unverified_cleanup_resources', lambda s: s['cleanup'].__setitem__('resources_verified_absent', []), 'unverified_cleanup_resources'),
        ('exposed_secret', lambda s: s.__setitem__('leak', make_synthetic_token()), 'exposed_secret'),
    ]

    for name, tamper_fn, expected_finding in mutants:
        mutant_summary = build_canonical_summary()
        tamper_fn(mutant_summary)
        m_res = validate_v4_rehearsal(mutant_summary, canonical_source_fp, canonical_restored_fp)
        assert m_res['ok'] is False and m_res['verdict'] == 'FAIL', f"Mutant {name} should have failed, got: {m_res}"
        assert any(expected_finding in f for f in m_res['findings']), (
            f"Mutant {name} expected finding '{expected_finding}', got: {m_res['findings']}"
        )
        controls_passed += 1
        print(f"  [OK] Mutant {name} -> rejected with '{expected_finding}'")

    # 3. Fingerprint controls
    fp_mutants = [
        ('missing_both_fingerprints', None, None, 'missing_source_fingerprint'),
        ('missing_source_fingerprint', None, canonical_restored_fp, 'missing_source_fingerprint'),
        ('missing_restored_fingerprint', canonical_source_fp, None, 'missing_restored_fingerprint'),
        ('source_count_999', fp(999), canonical_restored_fp, 'source_count_mismatch'),
        ('malformed_restored_hashes', canonical_source_fp, fp(1, sha_hex='not-a-sha256'), 'malformed_restored_hashes'),
    ]
    for name, s_fp, r_fp, expected_finding in fp_mutants:
        m_res = validate_v4_rehearsal(build_canonical_summary(), s_fp, r_fp)
        assert m_res['ok'] is False and m_res['verdict'] == 'FAIL', f"FP Mutant {name} should have failed, got: {m_res}"
        assert any(expected_finding in f for f in m_res['findings']), (
            f"FP Mutant {name} expected finding '{expected_finding}', got: {m_res['findings']}"
        )
        controls_passed += 1
        print(f"  [OK] FP Mutant {name} -> rejected with '{expected_finding}'")

    # 4. Barrier test
    barrier = V4CoordinationBarrier()
    assert not barrier.is_dump_active()
    barrier.notify_dump_started('snap-01')
    assert barrier.is_dump_active()
    assert barrier.get_snapshot_id() == 'snap-01'
    assert barrier.wait_until_dump_active(1.0)
    barrier.notify_dump_finished()
    assert not barrier.is_dump_active()
    controls_passed += 1
    print("  [OK] Coordination barrier positive flow")

    print(f"\nAll {controls_passed} controls passed.")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
