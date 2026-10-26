#!/usr/bin/env python3
"""
Orchestrator for BH-07 V2b Private Dart Heap / In-Memory Retention Verification.

Thực hiện:
1. Ghi nhận SHA, git dirty paths, source hashes của các file kiểm chứng.
2. Chạy AST Static Memory Audit trên mã nguồn lib/.
3. Chạy Integration Test đo Retained Objects qua Dart VM WeakReference & GC.
4. Tổng hợp bằng chứng sanitized, ánh xạ đúng trạng thái controls từ kết quả thực.
5. Tạo manifest hashes.sha256 và xác thực strict readonly UTF-8 LF.
"""

import datetime
import hashlib
import json
import os
import re
import subprocess
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
EVIDENCE_DIR = os.path.join(PROJECT_ROOT, 'docs/reviews/bh07/private_heap_evidence')

TESTED_SOURCE_FILES = [
    'test/integration/bh07_heap_verification_test.dart',
    'scripts/bh07_heap/audit_ast_memory.py',
    'scripts/bh07_heap/clean_and_manifest.py',
    'scripts/bh07_heap/run_heap_verification.py'
]


def get_git_info():
    """Ghi nhận provenance. Không đọc được Git thì trả UNKNOWN, tuyệt đối không coi là clean."""
    try:
        sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=PROJECT_ROOT, text=True).strip()
    except Exception as e:
        sha = 'UNKNOWN_SHA'
        rev_parse_error = f'ERROR: git rev-parse HEAD failed: {e}'
    else:
        rev_parse_error = None

    try:
        status_raw = subprocess.check_output(['git', 'status', '--porcelain'], cwd=PROJECT_ROOT, text=True).strip()
        dirty_files = [line.strip() for line in status_raw.splitlines() if line.strip()]
        is_dirty = len(dirty_files) > 0
    except Exception as e:
        # fail-closed: status lỗi => cleanliness UNKNOWN, không phải checkout sạch.
        is_dirty = 'UNKNOWN'
        dirty_files = [f'ERROR: git status --porcelain failed: {e}']

    if rev_parse_error:
        dirty_files = [rev_parse_error] + dirty_files

    # Compute source hashes of verification scripts/tests
    source_hashes = {}
    for rel in TESTED_SOURCE_FILES:
        p = os.path.join(PROJECT_ROOT, rel)
        if os.path.exists(p):
            with open(p, 'rb') as fp:
                source_hashes[rel] = hashlib.sha256(fp.read()).hexdigest()
        else:
            source_hashes[rel] = 'MISSING'

    return sha, is_dirty, dirty_files, source_hashes


def provenance_errors(sha, dirty, source_hashes, dirty_files=None):
    """Trả danh sách lỗi provenance; rỗng nghĩa là metadata đáng tin để công bố."""
    errors = []
    if not re.fullmatch(r'[0-9a-f]{40}', str(sha)):
        errors.append(f'ERROR: tested source SHA is not a resolvable commit: {sha}')
    if dirty not in (True, False):
        errors.append(f'ERROR: git cleanliness is {dirty}, not a proven clean/dirty checkout')
    for entry in dirty_files or []:
        if str(entry).startswith('ERROR:'):
            errors.append(str(entry))
    for rel, digest in (source_hashes or {}).items():
        if not re.fullmatch(r'[0-9a-f]{64}', str(digest)):
            errors.append(f'ERROR: source hash unavailable for {rel}: {digest}')
    return errors


def get_env_info():
    is_win = sys.platform == 'win32'
    dart_bin = 'dart.bat' if is_win else 'dart'
    flutter_bin = 'flutter.bat' if is_win else 'flutter'

    try:
        dart_ver = subprocess.check_output([dart_bin, '--version'], cwd=PROJECT_ROOT, text=True, shell=is_win).strip()
    except Exception as e:
        dart_ver = f'Error: {e}'

    try:
        flutter_ver_raw = subprocess.check_output([flutter_bin, '--version'], cwd=PROJECT_ROOT, text=True, shell=is_win).splitlines()
        flutter_ver = flutter_ver_raw[0] if flutter_ver_raw else 'Unknown'
    except Exception as e:
        flutter_ver = f'Error: {e}'

    return {
        'os': sys.platform,
        'dart_version': dart_ver,
        'flutter_version': flutter_ver
    }


def run_ast_audit():
    print("[1/4] Running AST Static Memory Audit...")
    cmd = [sys.executable, os.path.join(PROJECT_ROOT, 'scripts/bh07_heap/audit_ast_memory.py')]
    res = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True)
    print(res.stdout)
    if res.returncode != 0:
        print(f"AST Audit failed:\n{res.stderr}", file=sys.stderr)
        return False
    return True


def run_heap_tests():
    print("[2/4] Running Dart VM Retained Objects Verification Suite...")
    test_path = 'test/integration/bh07_heap_verification_test.dart'
    is_win = sys.platform == 'win32'
    flutter_bin = 'flutter.bat' if is_win else 'flutter'
    # --reporter json: verdict phải dựa trên event có tên test, không chỉ đếm dòng "All tests passed".
    cmd = [flutter_bin, 'test', '--reporter', 'json', test_path]
    log_path = os.path.join(EVIDENCE_DIR, 'heap_test_run.log')
    os.makedirs(EVIDENCE_DIR, exist_ok=True)

    res = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True, shell=is_win)
    with open(log_path, 'wb') as fp:
        log_content = "=== FLUTTER TEST JSON EVENTS (--reporter json) ===\n" + res.stdout
        if res.stderr:
            log_content += "\n=== STDERR ===\n" + res.stderr
        fp.write(log_content.encode('utf-8'))

    print(res.stdout)
    if res.returncode != 0:
        print(f"Flutter Heap Tests failed:\n{res.stderr}", file=sys.stderr)
        return False, res.stdout
    return True, res.stdout


# Test identity -> controls nó thực sự chứng minh. Thiếu/skip một identity thì control đó NOT_RUN.
EXPECTED_TESTS = {
    'Baseline Epoch: Initial providers state is empty, zero retained objects': [
        'baseline_initial_empty',
    ],
    'Full Cycle: Owner -> Logout -> Cohost -> Member retains NO sensitive Owner objects in Dart heap': [
        'owner_positive_retention_p1',
        'post_logout_negative_purge_n1',
        'cohost_switch_isolation_n2',
        'member_switch_isolation_n3',
    ],
    'Negative Control N4: Late-arriving response after logout is dropped & GC-collected': [
        'late_response_after_logout_n4',
    ],
    'Negative Control N5: Late-arriving response after actor switch is dropped & GC-collected': [
        'late_response_after_switch_n5',
    ],
    'Mutant Control M1: Static/global strong reference leak is reliably caught by Oracle': [
        'mutant_static_leak_detected_m1',
    ],
    'Mutant Control M2: Retained field on simulated failed clearAll is caught by Oracle': [
        'mutant_failed_clear_detected_m2',
    ],
    'SessionProvider & ClubProvider: Private session and club details are purged from heap on logout': [
        'session_club_purged_on_logout',
    ],
}
CONTROL_NAMES = [c for owned in EXPECTED_TESTS.values() for c in owned]
_RESULT_MAP = {'success': 'PASS', 'failure': 'FAIL', 'error': 'FAIL', 'skipped': 'NOT_RUN'}
# Event types của `flutter test --reporter json`; dùng để nhận diện stream protocol thật.
_JSON_EVENT_TYPES = {'start', 'suite', 'allSuites', 'group', 'testStart', 'testDone', 'print', 'error', 'done'}


def _parse_json_events(output):
    """Đọc event testStart/testDone trên toàn stream; diagnostics/pub output xen kẽ bị bỏ qua.

    Trả về (records, saw_protocol): `records` giữ **từng record theo testID** (id, name, result)
    để hai test ID khác nhau cùng full name không bị gộp mất multiplicity; result được chuẩn hoá
    'skipped' theo cờ `skipped` thật của protocol. `saw_protocol` cho biết stream có event JSON
    hợp lệ hay không (để không rơi về text parser khi event bị thiếu).
    """
    names, done, saw_protocol = {}, {}, False
    for line in (output or '').splitlines():
        line = line.strip()
        if not line.startswith('{'):
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict) or event.get('type') not in _JSON_EVENT_TYPES:
            continue
        saw_protocol = True
        kind = event['type']
        if kind == 'testStart':
            test = event.get('test') or {}
            names[test.get('id')] = test.get('name', '')
        elif kind == 'testDone':
            done[event.get('testID')] = (
                event.get('result', 'error'),
                bool(event.get('skipped')),
                bool(event.get('hidden')),
            )

    records = []
    for test_id, (result, skipped, hidden) in done.items():
        name = names.get(test_id)
        if name and not hidden:
            records.append({'id': test_id, 'name': name, 'result': 'skipped' if skipped else result})
    return records, saw_protocol


def _suite_report(verdict, results, controls, coverage, missing=None, unexpected=None, duplicates=None):
    if missing is None:
        missing = [name for name in EXPECTED_TESTS if name not in results]
    return {
        'suite_verdict': verdict,
        'tests_passed': sum(1 for r in results.values() if r == 'success'),
        'tests_failed': sum(1 for r in results.values() if r in ('failure', 'error')),
        'tests_skipped': sum(1 for r in results.values() if r == 'skipped'),
        'tests_expected': len(EXPECTED_TESTS),
        'tests_missing': missing,
        'tests_unexpected': list(unexpected or []),
        'tests_duplicate': list(duplicates or []),
        'identity_coverage': coverage,
        'controls': controls,
    }


def _verdict_from_results(records, test_ok):
    """Map từng record (theo testID) về đúng 7 expected identity; lạ/trùng không được tính coverage."""
    matched, unexpected, duplicates = {}, [], []
    for record in records:
        name, test_id, result = record['name'], record['id'], record['result']
        owners = [e for e in EXPECTED_TESTS if name == e or name.endswith(e)]
        if not owners:
            unexpected.append(f'{name} [testID {test_id}]')
        elif len(owners) > 1 or owners[0] in matched:
            duplicates.append(f'{name} [testID {test_id}]')
        else:
            matched[owners[0]] = result

    controls = {}
    missing, skipped_identities = [], []
    for name, owned in EXPECTED_TESTS.items():
        outcome = _RESULT_MAP.get(matched.get(name), 'NOT_RUN')
        if name not in matched:
            missing.append(name)
        elif outcome == 'NOT_RUN':
            skipped_identities.append(name)
        for control in owned:
            controls[control] = outcome

    if not records:
        coverage = 'NONE'
        verdict = 'NOT_RUN'
    else:
        if missing or skipped_identities:
            coverage = 'INCOMPLETE'
        elif unexpected or duplicates:
            coverage = 'UNVERIFIED'
        else:
            coverage = 'VERIFIED'
        clean = (not missing and not skipped_identities and not unexpected and not duplicates and test_ok
                 and all(v == 'PASS' for v in controls.values()))
        verdict = 'PASS' if clean else 'FAIL'
    return _suite_report(verdict, matched, controls, coverage, missing, unexpected, duplicates)


def _verdict_from_text(test_ok, output):
    """Fallback cho output text (không có tên test): chỉ PASS khi đếm đủ 7, coverage COUNT_ONLY."""
    text = output or ''
    counts = re.search(r'\+(\d+)(?:\s+~(\d+))?(?:\s+-(\d+))?:', text)
    passed = int(counts.group(1)) if counts else 0
    skipped = int(counts.group(2)) if counts and counts.group(2) else 0
    failed = int(counts.group(3)) if counts and counts.group(3) else 0
    results = {}
    for i in range(passed):
        results[f'<unidentified passing test {i}>'] = 'success'
    for i in range(failed):
        results[f'<unidentified failing test {i}>'] = 'failure'

    if 'No tests ran' in text or not text.strip():
        controls = {c: 'NOT_RUN' for c in CONTROL_NAMES}
        return _suite_report('NOT_RUN', {}, controls, 'NONE', list(EXPECTED_TESTS))

    if test_ok and 'All tests passed!' in text and passed == len(EXPECTED_TESTS) and not skipped:
        controls = {c: 'PASS' for c in CONTROL_NAMES}
        return _suite_report('PASS', results, controls, 'COUNT_ONLY', [])

    controls = {c: ('FAIL' if failed else 'NOT_RUN') for c in CONTROL_NAMES}
    return _suite_report('FAIL', results, controls, 'COUNT_ONLY' if passed else 'NONE', list(EXPECTED_TESTS))


def parse_test_results(test_ok, test_output):
    """
    Phân tích kết quả thực tế: đủ 7 test identity và từng control phải PASS thì suite mới PASS.
    Chế độ JSON được chọn khi stream có event protocol hợp lệ ở bất kỳ dòng nào, không dựa
    vào ký tự đầu output (Flutter in diagnostics/pub output trước JSON).
    """
    output = test_output or ''
    results, saw_protocol = _parse_json_events(output)
    if saw_protocol:
        return _verdict_from_results(results, test_ok)
    return _verdict_from_text(test_ok, output)


def generate_summary(sha, dirty, env_info, ast_ok, test_ok, test_output, dirty_files=None, source_hashes=None,
                     provenance_errors=None):
    print("[3/4] Generating Sanitized Summary & Report...")
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    dirty_files = dirty_files or []
    source_hashes = source_hashes or {}
    prov_errors = list(provenance_errors or [])
    cleanliness = 'UNKNOWN' if dirty not in (True, False) else ('DIRTY' if dirty else 'CLEAN')

    # Đọc kết quả thực tế từ ast_memory_audit.json
    ast_data = {}
    ast_audit_json_path = os.path.join(EVIDENCE_DIR, 'ast_memory_audit.json')
    if os.path.exists(ast_audit_json_path):
        try:
            with open(ast_audit_json_path, 'r', encoding='utf-8') as fp:
                ast_data = json.load(fp)
            static_mutables_count = ast_data.get('static_mutable_collections_found', 0)
            overall_ast_verdict = ast_data.get('overall_ast_verdict', 'CLEAN' if ast_ok else 'FAIL')
            disposal_ok = all(p.get('leak_risk') == 'NONE' for p in ast_data.get('providers_lifecycle_audit', {}).values())
            if not ast_ok:
                overall_ast_verdict = 'FAIL'
                disposal_ok = False
        except Exception:
            static_mutables_count = -1
            overall_ast_verdict = 'FAIL'
            disposal_ok = False
    else:
        static_mutables_count = 0 if ast_ok else -1
        overall_ast_verdict = 'CLEAN' if ast_ok else 'FAIL'
        disposal_ok = ast_ok

    results = parse_test_results(test_ok, test_output)
    suite_verdict = results['suite_verdict']
    tests_passed = results['tests_passed']
    tests_failed = results['tests_failed']
    controls = results['controls']

    summary = {
        'tested_source_sha': sha,
        'git_dirty': dirty,
        'git_dirty_paths': dirty_files,
        'source_hashes': source_hashes,
        'timestamp': now,
        'environment': env_info,
        'gate': 'V2b — Private Dart Heap / In-Memory Retention & Isolation',
        'provenance': {
            'git_cleanliness': cleanliness,
            'errors': prov_errors
        },
        'ast_audit': {
            'verdict': overall_ast_verdict,
            'static_mutables_found': static_mutables_count,
            'provider_lifecycle_proper_disposal': disposal_ok
        },
        'heap_test_suite': {
            'verdict': suite_verdict,
            'tests_expected': results['tests_expected'],
            'tests_total': tests_passed + tests_failed + results['tests_skipped'],
            'tests_passed': tests_passed,
            'tests_failed': tests_failed,
            'tests_skipped': results['tests_skipped'],
            'tests_missing': results['tests_missing'],
            'tests_unexpected': results['tests_unexpected'],
            'tests_duplicate': results['tests_duplicate'],
            'identity_coverage': results['identity_coverage'],
            'controls': controls
        },
        'app_profile_heap_snapshot': {
            'status': 'NOT RUN',
            'reason': (
                'Headless CLI environment lacks Chrome DevTools Protocol / Dart VM memory profiler dump pipeline '
                'for full app profile mode. Unit/Provider harness serves as supporting evidence only.'
            )
        },
        'sanitized': True,
        'sanitization_notes': '100% sanitized. Contains no raw bank account numbers, passwords, JWTs or PII.',
        'methodology': (
            'Dart VM WeakReference target observation combined with generational garbage collection '
            'allocation pressure on Provider/VM harness. Directly probes object retention '
            'across Owner -> Logout -> Cohost -> Member lifecycle.'
        ),
        'limitations': (
            'Measured in Dart VM Runtime Test Harness under Windows 64-bit environment. '
            'Full Chrome DevTools Protocol .heapsnapshot dump on production Web build is NOT RUN. '
            'Does NOT prove full app profile heap cleanliness beyond Provider harness scope. '
            'WeakReference target null means the harness no longer references the object; it is not a proof '
            'that every copy is gone from RAM. State remains Chờ review.'
        )
    }

    os.makedirs(EVIDENCE_DIR, exist_ok=True)
    summary_path = os.path.join(EVIDENCE_DIR, 'summary.json')
    with open(summary_path, 'wb') as fp:
        fp.write((json.dumps(summary, indent=2) + '\n').encode('utf-8'))

    # Báo cáo Markdown chi tiết: cùng verdict/count với JSON, không tự nâng thành PASS
    gate_ok = suite_verdict == 'PASS' and ast_ok and overall_ast_verdict == 'CLEAN' and not prov_errors
    if gate_ok:
        report_conclusion = "**Chờ review độc lập** (7/7 Provider test PASS, AST CLEAN; App profile heap: NOT RUN)."
        suite_claim = f"Đạt {tests_passed}/{results['tests_expected']} kiểm thử `WeakReference`"
    else:
        report_conclusion = (f"**FAIL / INCOMPLETE** (Suite verdict: {suite_verdict}, AST: {overall_ast_verdict}, "
                             f"Provenance: {'UNKNOWN' if prov_errors else 'OK'}, "
                             f"identity coverage: {results['identity_coverage']}).")
        suite_claim = (f"{tests_passed}/{results['tests_expected']} kiểm thử `WeakReference` success "
                       f"(verdict {suite_verdict}, coverage {results['identity_coverage']})")

    if cleanliness == 'UNKNOWN':
        dirty_section = "  - UNKNOWN (không đọc được `git status`; không phải checkout sạch đã chứng minh)"
    else:
        dirty_section = "\n".join([f"  - `{p}`" for p in dirty_files]) if dirty_files else "  - None (Clean checkout)"
    prov_section = "\n".join([f"  - {e}" for e in prov_errors]) if prov_errors else "  - None"

    provider_rows = '\n'.join(
        f"  - `{name}`: Leak risk **{info.get('leak_risk', 'UNKNOWN')}**, "
        f"removeListener trong dispose={info.get('removes_auth_listener_on_dispose')}, "
        f"uncancelled={info.get('un_cancelled_subscriptions')}"
        for name, info in sorted((ast_data.get('providers_lifecycle_audit') or {}).items())
    ) or '  - (không có dữ liệu provider trong ast_memory_audit.json)'
    scanned_files = ast_data.get('total_dart_files_scanned', 'UNKNOWN')
    unexpected_section = ', '.join(results['tests_unexpected']) or 'None'
    duplicate_section = ', '.join(results['tests_duplicate']) or 'None'

    report_md = f"""# Báo Cáo Kiểm Chứng Cổng V2b — Private Dart Heap / In-Memory Retention BH-07

- **Ngày thực thi:** {now}
- **Tested Source SHA:** `{sha}`
- **Git Dirty:** `{dirty}`
- **Git Cleanliness:** `{cleanliness}`
- **Provenance Errors:**
{prov_section}
- **Dirty Paths:**
{dirty_section}
- **Suite Verdict:** `{suite_verdict}` — **Identity Coverage:** `{results['identity_coverage']}`
- **Tests:** {tests_passed}/{results['tests_expected']} passed, {results['tests_failed']} failed, {results['tests_skipped']} skipped, missing: {len(results['tests_missing'])}
- **Unexpected visible identities:** {unexpected_section}
- **Duplicate identities:** {duplicate_section}
- **Gate:** `V2b — Đo private Dart heap/cache sau đổi actor`
- **Kết luận:** {report_conclusion}

---

## 1. Mục Tiêu & Phạm Vi Kiểm Chứng

Mục tiêu cổng V2b theo `docs/reviews/bh07/bh07_readiness.md` mục 4.4:
Đo lường trực tiếp bộ nhớ RAM / Dart Heap của ứng dụng, kiểm tra xem sau khi **Owner đăng xuất** và chuyển sang **Cohost/Member** trong cùng instance:
1. Không còn đối tượng tài chính nhạy cảm của Owner (`PaymentInstructions`, `SessionFinance`, `SessionSummary`, `ClubLedger`) bị lưu giữ trong heap.
2. Không rò rỉ bộ nhớ qua `static mutable`, global listeners hoặc stream subscriptions.
3. Không nuốt các phản hồi trả về trễ (late-arriving responses) sau khi đổi phiên làm việc.
4. Có baseline đối chứng, positive controls, negative controls và mutant controls.

### Phân định phạm vi rõ ràng (Khắc phục HP1):
- **Phần Provider / VM Test Harness (Bằng chứng bổ trợ):** {suite_claim} trên `FinanceProvider`, `SessionProvider`, `ClubProvider`. Kết quả chỉ nói về việc Provider/harness còn tham chiếu DTO hay không, không phải toàn bộ app profile.
- **Phần App Profile Heap Snapshot / Chrome DevTools Protocol:** **NOT RUN** do môi trường kiểm thử headless chưa có công cụ dump heapsnapshot của toàn bộ ứng dụng Flutter Web/Desktop thật.
- **Nguyên tắc:** Tuyệt đối không suy diễn từ kết quả Provider harness hoặc UI sạch thành toàn bộ ứng dụng profile đã sạch.


---

## 2. Kết Quả Kiểm Chứng Controls (Provider Harness)

| Mốc / Control | Loại Control | Kỳ vọng | Kết quả | Trạng thái |
|---|---|---|---|---|
| **Baseline Epoch** | Baseline | Trạng thái ban đầu rỗng, không có instance tài chính nào | 0 retained objects | **{controls['baseline_initial_empty']}** |
| **Owner Active (Epoch 1)** | Positive Control P1 | 4 đối tượng tài chính sống trong heap, Provider tham chiếu mạnh | `weakRef.target != null` | **{controls['owner_positive_retention_p1']}** |
| **Post-Logout Purge (Epoch 2)** | Negative Control N1 | Gọi `logout()`, `clearAll()` kích hoạt; GC thu hồi 100% 4 đối tượng nhạy cảm | `weakRef.target == null` (cả 4) | **{controls['post_logout_negative_purge_n1']}** |
| **Cohost Switch (Epoch 3)** | Negative Control N2 | Đổi sang Cohost trong cùng instance; dữ liệu Owner không hồi sinh; Cohost state độc lập | `weakRef.target == null`, không có tiền | **{controls['cohost_switch_isolation_n2']}** |
| **Member Switch (Epoch 4)** | Negative Control N3 | Đổi sang Member; đối tượng của Owner vẫn chết; Member nhận object mới | `weakRef.target == null`, new ref riêng | **{controls['member_switch_isolation_n3']}** |
| **Late Response Logout** | Negative Control N4 | Response tài chính trả về trễ sau logout bị drop hoàn toàn, GC thu hồi payload | `weakRef.target == null` | **{controls['late_response_after_logout_n4']}** |
| **Late Response Actor Switch** | Negative Control N5 | Response tài chính trả về trễ sau khi đổi sang Member bị drop, không rò rỉ | `weakRef.target == null` | **{controls['late_response_after_switch_n5']}** |
| **Static Cache Leak** | Mutant Control M1 | Cố tình giữ strong reference trong static list; Oracle phải phát hiện đối tượng còn sống | Oracle phát hiện FAIL leak | **{controls['mutant_static_leak_detected_m1']}** |
| **Skipped ClearAll** | Mutant Control M2 | Cố tình không dọn field khi đổi user; Oracle phải phát hiện đối tượng còn sống | Oracle phát hiện FAIL leak | **{controls['mutant_failed_clear_detected_m2']}** |
| **Session & Club Purge** | Negative Control | Chi tiết buổi và CLB nội bộ của Owner bị thu hồi sạch khỏi heap sau logout | `weakRef.target == null` | **{controls['session_club_purged_on_logout']}** |

---

## 3. Kết Quả AST Static Memory Audit

- **Tổng số file Dart quét:** {scanned_files} files trong `lib/`.
- **Static mutable collections found:** {static_mutables_count}
- **Provider Lifecycle & Stream Disposal (từ ast_memory_audit.json):**
{provider_rows}

---

## 4. Bảo Mật & Sanitization

- Toàn bộ bằng chứng trong bundle này đã được **sanitized 100%**:
  - Không chứa số tài khoản ngân hàng thật, mã bí mật, mật khẩu hay JWT token nhạy cảm.
  - Các giá trị đối soát chỉ sử dụng fixture giả lập, boolean flags, và mã băm SHA-256.

---

## 5. Giới Hạn Kỹ Thuật & Khuyến Nghị

1. **Phạm vi đã kiểm chứng:** Đo lường cơ chế quản lý bộ nhớ, chuỗi tham chiếu sống và thu hồi GC của Dart VM Runtime trên Provider harness độc lập.
2. **Giới hạn môi trường (NOT RUN):** Chưa trích xuất file `.heapsnapshot` nhị phân từ Chrome DevTools Memory Profiler trên bản build Web profile.
3. **Quy định bàn giao:** Cổng V2b thuộc Nhóm 3 (Cổng môi trường chuyên sâu). Người triển khai ghi nhận kết quả và giới hạn trung thực, ghi nhận trạng thái **Chờ review**, KHÔNG tự ý ghi "Đạt" hay tự ý nghiệm thu toàn bộ BH-07.
"""
    report_path = os.path.join(EVIDENCE_DIR, 'heap_verification_report.md')
    with open(report_path, 'wb') as fp:
        fp.write(report_md.encode('utf-8'))

    return suite_verdict


def generate_and_verify_manifest():
    print("[4/4] Generating & Verifying Manifest (strict UTF-8 LF readonly)...")
    cmd = [sys.executable, os.path.join(PROJECT_ROOT, 'scripts/bh07_heap/clean_and_manifest.py'), '--generate']
    res = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True)
    print(res.stdout)
    if res.returncode != 0:
        print(f"Manifest generation/verification failed:\n{res.stderr}", file=sys.stderr)
        return False
    return True


def main():
    print("=================================================================")
    print("=== BH-07 V2b: Private Dart Heap / In-Memory Retention Runner ===")
    print("=================================================================")

    sha, dirty, dirty_files, source_hashes = get_git_info()
    prov_errors = provenance_errors(sha, dirty, source_hashes, dirty_files)
    print(f"Tested Source SHA : {sha}")
    print(f"Git Dirty Status  : {dirty} ({len(dirty_files)} paths)")
    for err in prov_errors:
        print(f"PROVENANCE ERROR  : {err}", file=sys.stderr)

    env_info = get_env_info()
    print(f"Environment       : {env_info['os']} | {env_info['flutter_version']}")

    # Step 1: AST Audit
    ast_ok = run_ast_audit()

    # Step 2: Heap Tests
    test_ok, test_output = run_heap_tests()

    # Step 3: Summary and Report
    suite_verdict = generate_summary(sha, dirty, env_info, ast_ok, test_ok, test_output, dirty_files,
                                     source_hashes, prov_errors)

    # Step 4: Manifest
    manifest_ok = generate_and_verify_manifest()

    print("\n=================================================================")
    if ast_ok and suite_verdict == 'PASS' and manifest_ok and not prov_errors:
        print("=== RESULT: All V2b Heap Verification checks completed PASS! ===")
        print(f"=== Evidence bundle generated at: docs/reviews/bh07/private_heap_evidence/ ===")
        print("=== Ready for Independent Review handoff. ===")
        return 0
    else:
        print(f"=== RESULT: FAIL encountered during V2b Heap Verification! "
              f"(suite={suite_verdict}, ast_ok={ast_ok}, manifest_ok={manifest_ok}, "
              f"provenance_errors={len(prov_errors)}) ===", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
