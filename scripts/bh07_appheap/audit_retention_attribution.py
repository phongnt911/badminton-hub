"""Audit script for BH-07 V2b retention attribution and coverage mapping.

This tool performs an objective, reproducible investigation of:
1. The 8 residual risk rendered-title retention entries published in QA evidence
   (`docs/reviews/bh07/review_runtime_b13e468_evidence/summary.json`).
2. The exact retainer path frames from GC roots to `segmentationCache`.
3. The peer non-rendered sentinels (`expense_id`, `expense_id_2`) checking app-level
   release of the underlying `FinanceExpense` model instances.
4. The completeness of the private models/caches/listeners coverage map for V2b §4.4.

It operates read-only on the evidence bundle and produces structured audit JSONs.
No raw heap dumps or sensitive credentials are ever read or published.
"""
import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from heap_oracle import scan_problems  # noqa: E402

QA_EVIDENCE_DIR = ROOT / 'docs/reviews/bh07/review_runtime_b13e468_evidence'
R1_EVIDENCE_DIR = ROOT / 'docs/reviews/bh07/retained_path_r1_evidence'
OUT_EVIDENCE_DIR = ROOT / 'docs/reviews/bh07/retention_attribution_evidence'

EXPECTED_FLUTTER_VERSION_PREFIX = 'Flutter 3.47.6'
EXPECTED_CHROME_PREFIX = 'Chrome/155.'
EXPECTED_BUILD_MODE = 'profile'
EXPECTED_RESIDUAL_RISK_COUNT = 8
EXPECTED_PATH_LEN = 12

EXPECTED_COMBINATIONS = {
    (1, 'post_logout', 'expense'),
    (1, 'post_logout', 'expense2'),
    (1, 'post_actor', 'expense'),
    (1, 'post_actor', 'expense2'),
    (2, 'post_logout', 'expense'),
    (2, 'post_logout', 'expense2'),
    (2, 'post_actor', 'expense'),
    (2, 'post_actor', 'expense2'),
}

ENTITIES_INVENTORY = [
    {
        'id': 'expense_titles',
        'entity': 'Session Expense Title',
        'model': 'lib/models/finance.dart:222 (FinanceExpense.title)',
        'provider': 'lib/providers/finance_provider.dart:180 (_finance.expenses)',
        'screen': 'lib/screens/session_finance_screen.dart:620 (_expenseTile)',
        'scope': 'finance',
        'rendered': True,
        'distinctive': True,
        'measured_status': 'PARTIALLY_VERIFIED_RESIDUAL_ENGINE_CACHE',
        'gap': 'Rendered string retained in Flutter Web engine segmentationCache (unattributed residual risk); not measured on Dart VM desktop/mobile.',
    },
    {
        'id': 'expense_ids',
        'entity': 'Session Expense ID',
        'model': 'lib/models/finance.dart:222 (FinanceExpense.expenseId)',
        'provider': 'lib/providers/finance_provider.dart:180 (_finance.expenses)',
        'screen': 'lib/screens/session_finance_screen.dart (unrendered model key)',
        'scope': 'finance',
        'rendered': False,
        'distinctive': True,
        'measured_status': 'VERIFIED_CLEAN_LOCAL_WEB_PROFILE',
        'gap': 'Gated on 2 expense IDs on Web profile (V8); Dart VM desktop/mobile NOT RUN.',
    },
    {
        'id': 'session_charges',
        'entity': 'Session Charges',
        'model': 'lib/models/finance.dart:258 (FinanceCharge: playerId, displayName, amountDueVnd)',
        'provider': 'lib/providers/finance_provider.dart:180 (_finance.charges)',
        'screen': 'lib/screens/session_finance_screen.dart:648 (_chargesSection)',
        'scope': 'finance',
        'rendered': True,  # amounts/names rendered, playerId unrendered
        'distinctive': True,
        'measured_status': 'NOT_MEASURED_IN_APP_HEAP',
        'gap': 'Tested in Provider-level unit test only; no sentinel declared in run_app_profile_heap.js.',
    },
    {
        'id': 'session_payments',
        'entity': 'Session Payments',
        'model': 'lib/models/finance.dart:279 (FinancePayment: paymentId, playerId, amountVnd, method, status, reference, confirmedAt, createdAt)',
        'provider': 'lib/providers/finance_provider.dart:180 (_finance.payments)',
        'screen': 'lib/screens/session_finance_screen.dart:696 (_paymentsSection)',
        'scope': 'finance',
        'rendered': True,  # amounts/reference rendered, paymentId unrendered
        'distinctive': True,
        'measured_status': 'NOT_MEASURED_IN_APP_HEAP',
        'gap': 'Tested in Provider-level unit test only; no payment sentinel declared in run_app_profile_heap.js.',
    },
    {
        'id': 'club_bank_account',
        'entity': 'Club Bank Account Number',
        'model': 'lib/models/club.dart:122 (BankAccount: id, clubId, userId, bankCode, accountNumber, accountName, status)',
        'provider': 'lib/providers/club_provider.dart:112 (_currentBankAccount)',
        'screen': 'lib/screens/clubs_screen.dart:472 (_showConfigureBankDialog)',
        'scope': 'bank',
        'rendered': False,
        'distinctive': False,  # 10 digits collides with UUID suffixes
        'measured_status': 'NOT_MEASURED_IN_APP_HEAP',
        'gap': 'Bank screen was never opened in openOwnerFinance; 10 digits collided with fixture UUID; need distinctive alphanumeric or UUID account sentinel.',
    },
    {
        'id': 'bank_receiver',
        'entity': 'Bank Account Holder / Receiver',
        'model': 'lib/models/club.dart:122 (BankAccount.accountName) / lib/models/finance.dart:34 (PaymentInstructions.receiverSnapshot)',
        'provider': 'lib/providers/club_provider.dart:112 / finance_provider.dart:101',
        'screen': 'lib/screens/clubs_screen.dart / payment QR dialog',
        'scope': 'bank',
        'rendered': False,
        'distinctive': True,
        'measured_status': 'NOT_MEASURED_IN_APP_HEAP',
        'gap': 'Declared in summary.json but occurrences: 0 in owner_active because flow never visited bank or payment instructions screens.',
    },
    {
        'id': 'payment_instructions',
        'entity': 'Payment Instructions & VietQR',
        'model': 'lib/models/finance.dart:34 (PaymentInstructions: sessionId, playerId, displayName, billingState, activeRevisionId, sourceVersion, amountDueVnd, totalPaidVnd, outstandingVnd, reference, receiverSnapshot, hasReceiver, canPay)',
        'provider': 'lib/providers/finance_provider.dart:101 (_instructions)',
        'screen': 'lib/screens/session_finance_screen.dart:458 (player QR instructions)',
        'scope': 'finance',
        'rendered': True,
        'distinctive': True,
        'measured_status': 'NOT_MEASURED_IN_APP_HEAP',
        'gap': 'Tested in Provider-level unit test only; player payment instructions flow not executed in Web profile heap runner.',
    },
    {
        'id': 'club_ledger',
        'entity': 'Club Ledger Entries & Balance',
        'model': 'lib/models/finance.dart:402 (ClubLedgerEntry) / 447 (ClubLedger)',
        'provider': 'lib/providers/finance_provider.dart (_ledger)',
        'screen': 'lib/screens/club_fund_screen.dart:179 (ClubFundScreen)',
        'scope': 'finance',
        'rendered': True,
        'distinctive': True,
        'measured_status': 'NOT_MEASURED_IN_APP_HEAP',
        'gap': 'ClubFundScreen was never visited in run_app_profile_heap.js; tested in Provider-level unit test only.',
    },
    {
        'id': 'session_summary_totals',
        'entity': 'Session Summary Aggregate Financial Totals',
        'model': 'lib/models/finance.dart:98 (SessionSummary: expensesTotalVnd, amountDueTotalVnd, totalPaidVnd, outstandingTotalVnd)',
        'provider': 'lib/providers/finance_provider.dart (_summary)',
        'screen': 'lib/screens/session_summary_screen.dart:58 (SessionSummaryScreen)',
        'scope': 'finance',
        'rendered': True,
        'distinctive': False,  # numeric totals like 200000 are not distinctive
        'measured_status': 'PARTIALLY_VISITED_UNGATED',
        'gap': 'SessionSummaryScreen visited in openOwnerFinance, but numeric aggregates were not distinctive sentinels.',
    },
    {
        'id': 'roster_identities',
        'entity': 'Shared Club Roster Player IDs',
        'model': 'lib/models/session.dart:237 (SessionPlayer.id)',
        'provider': 'lib/providers/session_provider.dart',
        'screen': 'lib/screens/session_detail_screen.dart',
        'scope': 'identity',
        'rendered': False,
        'distinctive': True,
        'measured_status': 'REPORTED_NOTE_NOT_GATED',
        'gap': 'Reachable at post_cohost (path len 18); identity entitlement cannot be established by heap measurement alone.',
    },
    {
        'id': 'auth_listeners',
        'entity': 'Auth Change Listeners & State Dispatch',
        'model': 'lib/providers/auth_provider.dart -> addListener(_onAuthChanged)',
        'provider': 'FinanceProvider, ClubProvider, SessionProvider',
        'screen': 'All screens',
        'scope': 'control',
        'rendered': False,
        'distinctive': True,
        'measured_status': 'NOT_RUN_WEB_HEAP_OBJECT_GRAPH',
        'gap': 'AST zero-static and Provider test verify balance of listeners in unit harness, but Web profile heap object graph of active listener nodes was NOT RUN.',
    },
]


def source_record_problems(data):
    """Validate the source records, not just the derived risk matrix."""
    problems = []
    expected_actors = {1: 'cohost', 2: 'member'}
    cycles = data.get('cycles', [])
    cycle_ids = [c.get('cycle') for c in cycles if isinstance(c, dict)]
    if (len(cycle_ids) != 2 or any(type(n) is not int for n in cycle_ids)
            or set(cycle_ids) != set(expected_actors)):
        problems.append('Cycle payloads must contain unique integer cycles 1 and 2')
    for cycle in cycles:
        number = cycle.get('cycle')
        if cycle.get('actor') != expected_actors.get(number):
            problems.append('Cycle actor does not match the Owner-to-Cohost/Member contract')
        epochs = cycle.get('epochs', {})
        for epoch_name in ('baseline', 'owner_active', 'post_logout', 'post_actor'):
            scan = epochs.get(epoch_name)
            if not isinstance(scan, dict) or scan.get('ok') is not True:
                problems.append(f'{epoch_name}: usable scan missing')
                continue
            if scan_problems(scan, require_paths=True):
                problems.append(f'{epoch_name}: invalid scan/count/path schema')
                continue
            for name, record in scan['sentinels'].items():
                path = scan['paths'][name]
                if path['reachable'] and (not record['present'] or path.get('string_nodes', 0) < 1):
                    problems.append(f'{epoch_name}: reachable path contradicts sentinel presence')
                if not record['present'] and (path['reachable'] or path.get('string_nodes') != 0):
                    problems.append(f'{epoch_name}: absent sentinel contradicts path node count')
                if path['reachable']:
                    frames = path['frames']
                    digest = hashlib.sha256('\n'.join(frames).encode('utf-8')).hexdigest()[:12]
                    if path['path_len'] != len(frames) - 1 or path['path_sha256_12'] != digest:
                        problems.append(f'{epoch_name}: path length/hash does not match frames')
            for name in ('expense', 'expense2', 'expense_id', 'expense_id_2'):
                record = scan['sentinels'].get(name, {})
                rendered = name in ('expense', 'expense2')
                if (record.get('scope') != 'finance' or record.get('rendered') is not rendered
                        or record.get('distinctive') is not True):
                    problems.append(f'{epoch_name}: finance sentinel class missing or inconsistent')
    for risk in data.get('residual_risks', []):
        matching = [c for c in cycles if c.get('cycle') == risk.get('cycle')]
        if len(matching) != 1:
            problems.append('Risk record has no unique source cycle')
            continue
        scan = matching[0].get('epochs', {}).get(risk.get('epoch'), {})
        path = scan.get('paths', {}).get(risk.get('sentinel'), {})
        if (any(risk.get(key) != path.get(key) for key in ('path_len', 'root_kind', 'path_sha256_12'))
                or risk.get('class') != 'rendered' or risk.get('attribution') != 'unattributed'):
            problems.append('Risk class/root/length/hash does not match its source path')
    return problems


def audit_summary_json(summary_path):
    """Deep audit of summary.json for attribution analysis."""
    if not os.path.exists(summary_path):
        raise FileNotFoundError(f'Evidence summary not found: {summary_path}')

    with open(summary_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 1. Environment check
    env = data.get('environment', {})
    flutter = env.get('flutter', '')
    chrome = env.get('chrome', '')
    build = env.get('build', {})
    mode = build.get('mode', '')

    env_consistent = (
        EXPECTED_FLUTTER_VERSION_PREFIX in flutter
        and EXPECTED_CHROME_PREFIX in chrome
        and mode == EXPECTED_BUILD_MODE
    )

    # 2. Residual risks check
    residual_risks = data.get('residual_risks', [])
    if not isinstance(residual_risks, list) or len(residual_risks) != EXPECTED_RESIDUAL_RISK_COUNT:
        raise ValueError(f'Expected {EXPECTED_RESIDUAL_RISK_COUNT} residual risks, found {len(residual_risks) if isinstance(residual_risks, list) else 0}')

    # Validate all 8 cycle/epoch/sentinel combinations without duplicates or omissions
    combinations_found = set()
    duplicate_found = False
    rr_matrix = {}
    for rr in residual_risks:
        cycle = rr.get('cycle')
        epoch = rr.get('epoch')
        sentinel = rr.get('sentinel')
        path_len = rr.get('path_len')
        attribution = rr.get('attribution')
        path_hash = rr.get('path_sha256_12')
        combo = (cycle, epoch, sentinel)
        if combo in combinations_found:
            duplicate_found = True
        combinations_found.add(combo)
        key = f'cycle_{cycle}_{epoch}_{sentinel}'
        rr_matrix[key] = {
            'path_len': path_len,
            'attribution': attribution,
            'path_sha256_12': path_hash,
            'class': rr.get('class'),
            'root_kind': rr.get('root_kind'),
        }

    combinations_valid = (not duplicate_found) and (combinations_found == EXPECTED_COMBINATIONS)

    # 3. Retainer path inspection in cycles
    cycles = data.get('cycles', [])
    if len(cycles) != 2:
        raise ValueError(f'Expected 2 cycles, found {len(cycles)}')

    cycle_findings = []
    for c in cycles:
        cycle_no = c.get('cycle')
        actor = c.get('actor')
        epochs = c.get('epochs', {})

        # Inspect owner_active
        owner_active = epochs.get('owner_active', {})
        oa_sentinels = owner_active.get('sentinels', {})
        oa_paths = owner_active.get('paths', {})
        expense_id_owner_s = oa_sentinels.get('expense_id', {})
        expense_id_owner_p = oa_paths.get('expense_id', {})
        expense_id_2_owner_s = oa_sentinels.get('expense_id_2', {})
        expense_id_2_owner_p = oa_paths.get('expense_id_2', {})

        # Peer sentinel verification (no default 0; occurrences must be explicit integer)
        def _check_owner_peer(s_dict, p_dict):
            return (
                isinstance(s_dict, dict)
                and s_dict.get('present') is True
                and ('occurrences' in s_dict)
                and (type(s_dict['occurrences']) is int)
                and s_dict['occurrences'] == 1
                and isinstance(p_dict, dict)
                and p_dict.get('reachable') is True
                and p_dict.get('path_len') == 20
            )

        def _check_post_peer(s_dict, p_dict):
            return (
                isinstance(s_dict, dict)
                and s_dict.get('present') is False
                and ('occurrences' in s_dict)
                and (type(s_dict['occurrences']) is int)
                and s_dict['occurrences'] == 0
                and isinstance(p_dict, dict)
                and p_dict.get('reachable') is False
            )

        peer_clean = (
            _check_owner_peer(expense_id_owner_s, expense_id_owner_p)
            and _check_owner_peer(expense_id_2_owner_s, expense_id_2_owner_p)
        )

        for e_name in ['post_logout', 'post_actor']:
            e_dict = epochs.get(e_name, {})
            e_sentinels = e_dict.get('sentinels', {})
            e_paths = e_dict.get('paths', {})
            s1 = e_sentinels.get('expense_id')
            p1 = e_paths.get('expense_id')
            s2 = e_sentinels.get('expense_id_2')
            p2 = e_paths.get('expense_id_2')
            if not (_check_post_peer(s1, p1) and _check_post_peer(s2, p2)):
                peer_clean = False

        # Rendered path verification: must check both expense and expense2 at both post_logout and post_actor
        rendered_paths_valid = True
        for e_name in ['post_logout', 'post_actor']:
            e_dict = epochs.get(e_name, {})
            e_paths = e_dict.get('paths', {})
            for s_name in ['expense', 'expense2']:
                p_obj = e_paths.get(s_name)
                if not isinstance(p_obj, dict):
                    rendered_paths_valid = False
                    break
                if p_obj.get('reachable') is not True or p_obj.get('path_len') != EXPECTED_PATH_LEN:
                    rendered_paths_valid = False
                    break
                frames = p_obj.get('frames', [])
                if not (
                    any('segmentationCache' in f for f in frames)
                    and any('_itemMap' in f for f in frames)
                    and any('_strings' in f for f in frames)
                    and any('hashMapCellKey' in f for f in frames)
                ):
                    rendered_paths_valid = False
                    break
                # Cross-check with residual_risks record
                rr_key = f'cycle_{cycle_no}_{e_name}_{s_name}'
                rr_entry = rr_matrix.get(rr_key)
                if not rr_entry:
                    rendered_paths_valid = False
                    break
                if rr_entry.get('path_len') != p_obj.get('path_len'):
                    rendered_paths_valid = False
                    break

        cycle_findings.append({
            'cycle': cycle_no,
            'actor': actor,
            'peer_sentinels_clean': peer_clean,
            'rendered_paths_valid': rendered_paths_valid,
        })

    return {
        'source_record_problems': source_record_problems(data),
        'tested_source_sha': data.get('tested_source_sha'),
        'git_dirty': data.get('git_dirty'),
        'environment': {
            'flutter': flutter,
            'chrome': chrome,
            'build_mode': mode,
            'consistent': env_consistent,
        },
        'residual_risks_count': len(residual_risks),
        'residual_risks_combinations_valid': combinations_valid,
        'residual_risks_matrix': rr_matrix,
        'cycle_findings': cycle_findings,
    }


def analyze_attribution(summary_audit):
    """Synthesize evidence into an objective attribution conclusion.

    Fail-closed: if preconditions (environment consistency, peer clean release,
    rendered paths through cache, risk count, combinations validity) fail, verdict must be FAIL and UNATTRIBUTED.
    """
    env_consistent = summary_audit.get('environment', {}).get('consistent', False)
    all_peers_clean = all(cf.get('peer_sentinels_clean', False) for cf in summary_audit.get('cycle_findings', []))
    all_rendered_paths_valid = (
        len(summary_audit.get('cycle_findings', [])) == 2
        and all(cf.get('rendered_paths_valid', False) for cf in summary_audit.get('cycle_findings', []))
    )
    count_ok = summary_audit.get('residual_risks_count') == EXPECTED_RESIDUAL_RISK_COUNT
    combinations_ok = summary_audit.get('residual_risks_combinations_valid', False)
    source_problems = summary_audit.get('source_record_problems', ['Source validation missing'])

    preconditions_valid = (
        env_consistent
        and all_peers_clean
        and all_rendered_paths_valid
        and count_ok
        and combinations_ok
        and not source_problems
    )

    failure_reasons = []
    failure_reasons.extend(source_problems)
    if not env_consistent:
        failure_reasons.append('Environment inconsistent with expected Flutter/Chrome/build')
    if not all_peers_clean:
        failure_reasons.append('Peer non-rendered sentinels were not cleanly released post-logout (app model leak detected or unverified)')
    if not all_rendered_paths_valid:
        failure_reasons.append('Rendered title retainer paths invalid, missing, or do not traverse engine segmentationCache across all cycles/epochs/sentinels')
    if not count_ok:
        failure_reasons.append(f'Residual risks count mismatch (expected {EXPECTED_RESIDUAL_RISK_COUNT}, got {summary_audit.get("residual_risks_count")})')
    if not combinations_ok:
        failure_reasons.append('Residual risks combinations invalid or duplicated (must contain exactly 8 distinct cycle/epoch/sentinel sets)')

    engine_criteria = {
        'path_leads_to_segmentationCache': all_rendered_paths_valid,
        'cache_capacity': 10000,
        'cache_eviction_lifecycle_hook_present': False,
        'cache_scope': 'flutter_web_sdk/lib/_engine/engine/text_fragmenter.dart',
    }

    # AT2: Separate scoped two-ID observation from app-wide retention (which remains UNKNOWN)
    app_criteria = {
        'unrendered_peer_sentinels_occurrences_post_logout': 0 if all_peers_clean else 'LEAK_OR_UNVERIFIED',
        'observed_two_expense_ids_clean': all_peers_clean,
        'app_wide_model_retention_proven': False,
        'app_wide_model_retention': 'UNKNOWN',
        'app_static_mutable_caches': 0,
        'provider_clear_implemented': True,
    }

    if not preconditions_valid:
        attribution_verdict = {
            'valid': False,
            'status': 'FAIL',
            'rendered_title_retained': True,
            'primary_retainer_component': 'UNATTRIBUTED',
            'app_model_retention': 'UNKNOWN_OR_UNCLEAN',
            'observed_peer_ids_absent': False,
            'app_wide_retention_proven': False,
            'peer_sentinel_proof_valid': all_peers_clean,
            'preconditions_valid': False,
            'failure_reasons': failure_reasons,
            'unattributed_status_justification': (
                'Preconditions failed. Retention cannot be attributed to engine LRU cache while controls fail or evidence is incomplete.'
            ),
        }
    else:
        attribution_verdict = {
            'valid': True,
            'status': 'SUPPORTED_HYPOTHESIS_WITH_LIMITS',
            'rendered_title_retained': True,
            'primary_retainer_component': 'Flutter Web Engine (dart._engine.segmentationCache)',
            'app_model_retention': 'SCOPED_TWO_IDS_CLEAN_APP_WIDE_UNKNOWN',
            'observed_peer_ids_absent': True,
            'app_wide_retention_proven': False,
            'peer_sentinel_proof_valid': True,
            'preconditions_valid': True,
            'failure_reasons': [],
            'unattributed_status_justification': (
                'Single-path BFS in QA bundle traverses engine segmentationCache. '
                'Unrendered peer sentinels drop to 0 occurrences post-logout, supporting the hypothesis '
                'that the underlying FinanceExpense model instance was freed by app provider. '
                'However, by readiness §4.4 and AGENTS.md, residual risk remains officially unattributed '
                'because single-path BFS does not establish full exhaustiveness and native Dart VM is NOT RUN.'
            ),
        }

    observed = {
        'bfs_path_length': 12,
        'bfs_path_target': 'dart._engine.segmentationCache._itemMap._strings',
        'unrendered_peer_sentinels_occurrences_post_logout': 0 if all_peers_clean else 'FAILED',
        'observed_two_expense_ids_absent': all_peers_clean,
        'measured_scope': 'V8 / dart2js web profile on Chrome 155',
    }
    supported_hypothesis = {
        'component': 'Flutter Web Engine text segmentation LRU cache',
        'cache_capacity': 10000,
        'source_reference': 'flutter_web_sdk/lib/_engine/engine/text_fragmenter.dart:43',
    }
    unknown_and_limits = {
        'single_path_exhaustiveness_proven': False,
        'secondary_app_paths_possible': True,
        'app_wide_retention_status': 'UNKNOWN',
        'dart_vm_desktop_mobile_status': 'NOT_RUN',
        'untested_private_entities_count': 9,
        'v2b_readiness_status': 'CHUA_NGHIEM_THU',
        'residual_risk_official_classification': 'unattributed',
    }

    return {
        'engine_criteria': engine_criteria,
        'app_criteria': app_criteria,
        'attribution_verdict': attribution_verdict,
        'observed': observed,
        'supported_hypothesis': supported_hypothesis,
        'unknown_and_limits': unknown_and_limits,
    }


def build_coverage_map_audit():
    """Audit the coverage map completeness and classify technical gaps."""
    summary = {
        'total_entities': len(ENTITIES_INVENTORY),
        'verified_clean_web_profile': 0,
        'partially_verified_engine_residual': 0,
        'partially_visited_ungated': 0,
        'verified_provider_harness_only': 0,
        'reported_note_not_gated': 0,
        'not_measured_in_app_heap': 0,
        'not_run_web_heap_object_graph': 0,
    }

    for item in ENTITIES_INVENTORY:
        status = item['measured_status']
        if status == 'VERIFIED_CLEAN_LOCAL_WEB_PROFILE':
            summary['verified_clean_web_profile'] += 1
        elif status == 'PARTIALLY_VERIFIED_RESIDUAL_ENGINE_CACHE':
            summary['partially_verified_engine_residual'] += 1
        elif status == 'PARTIALLY_VISITED_UNGATED':
            summary['partially_visited_ungated'] += 1
        elif status == 'VERIFIED_PROVIDER_HARNESS':
            summary['verified_provider_harness_only'] += 1
        elif status == 'REPORTED_NOTE_NOT_GATED':
            summary['reported_note_not_gated'] += 1
        elif status == 'NOT_MEASURED_IN_APP_HEAP':
            summary['not_measured_in_app_heap'] += 1
        elif status == 'NOT_RUN_WEB_HEAP_OBJECT_GRAPH':
            summary['not_run_web_heap_object_graph'] += 1

    return {
        'summary': summary,
        'inventory': ENTITIES_INVENTORY,
    }


def main():
    parser = argparse.ArgumentParser(description='Audit BH-07 retention attribution and coverage map.')
    parser.add_argument('--summary', default=str(QA_EVIDENCE_DIR / 'summary.json'),
                        help='Path to QA evidence summary.json')
    parser.add_argument('--out-dir', default=str(OUT_EVIDENCE_DIR),
                        help='Output evidence directory')
    args = parser.parse_args()

    summary_path = Path(args.summary)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f'Auditing summary: {summary_path}')
    summary_audit = audit_summary_json(summary_path)
    print(f'Tested SHA: {summary_audit["tested_source_sha"]}')
    print(f'Residual risks count: {summary_audit["residual_risks_count"]}')

    attribution = analyze_attribution(summary_audit)
    verdict = attribution['attribution_verdict']
    print(f'Attribution result: {verdict["primary_retainer_component"]}')
    print(f'Attribution status: {verdict["status"]} (valid={verdict["valid"]})')

    coverage_audit = build_coverage_map_audit()
    print(f'Coverage entities analyzed: {coverage_audit["summary"]["total_entities"]}')
    print(f' - Verified clean Web profile: {coverage_audit["summary"]["verified_clean_web_profile"]}')
    print(f' - Not measured in app heap: {coverage_audit["summary"]["not_measured_in_app_heap"]}')
    print(f' - Not run web heap object graph: {coverage_audit["summary"]["not_run_web_heap_object_graph"]}')

    # Save structured audit artifacts before deciding exit code
    attr_out = out_dir / 'attribution_audit.json'
    with open(attr_out, 'w', encoding='utf-8') as f:
        json.dump({'summary_audit': summary_audit, 'attribution': attribution}, f, indent=2)
    print(f'Wrote: {attr_out}')

    cov_out = out_dir / 'coverage_audit.json'
    with open(cov_out, 'w', encoding='utf-8') as f:
        json.dump(coverage_audit, f, indent=2)
    print(f'Wrote: {cov_out}')

    if not verdict['valid']:
        print(f'[FAIL] Attribution audit failed preconditions: {verdict.get("failure_reasons")}', file=sys.stderr)
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
