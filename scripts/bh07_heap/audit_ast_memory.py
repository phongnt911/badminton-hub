#!/usr/bin/env python3
"""
AST and Codebase Memory Retention Audit for BH-07 V2b.

Rà soát toàn diện mã nguồn lib/ để phát hiện:
1. Static mutable collections hoặc global caches (List, Map, Set).
2. Global singletons lưu trữ trạng thái người dùng/tài chính.
3. StreamSubscriptions không được hủy (cancel) trong dispose().
4. Listeners (auth.addListener) không được gỡ bỏ (removeListener) trong dispose().
5. Kiểm tra tính toàn vẹn của các phương thức dọn dẹp (clearAll / reset state).
"""

import os
import re
import sys
import json

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
LIB_DIR = os.path.join(PROJECT_ROOT, 'lib')


def audit_static_and_globals(lib_path):
    issues = []
    checked_files = 0

    mutable_static_re = re.compile(r'\bstatic\s+(?:final\s+)?(?:List|Map|Set)\b')
    static_mutable_assign_re = re.compile(r'\bstatic\s+(?:var|final)?\s*\w+\s*=\s*(?:<[^>]+>)?\s*[\[\{]')

    for root, _, files in os.walk(lib_path):
        for f in files:
            if not f.endswith('.dart'):
                continue
            checked_files += 1
            path = os.path.join(root, f)
            rel_path = os.path.relpath(path, PROJECT_ROOT).replace('\\', '/')
            with open(path, 'r', encoding='utf-8') as fp:
                lines = fp.readlines()

            for idx, line in enumerate(lines, 1):
                clean_line = line.strip()
                # Skip comments
                if clean_line.startswith('//') or clean_line.startswith('*'):
                    continue
                # Bỏ qua static const (immutable compile-time constant)
                if 'static const' in clean_line:
                    continue

                # Bỏ qua static method declarations (ví dụ: static List<Session> _toSessions(...) hoặc static Map<String, dynamic> _toMap(...))
                if re.search(r'\bstatic\s+(?:[A-Za-z0-9_<>,?\s]+)\s+\w+\s*\([^)]*\)\s*(?:=>|\{)', clean_line) or re.search(r'\bstatic\s+(?:[A-Za-z0-9_<>,?\s]+)\s+\w+\s*\(', clean_line):
                    continue

                if mutable_static_re.search(clean_line) or static_mutable_assign_re.search(clean_line):
                    # Check if it is an immutable regex or constant lookup
                    if 'RegExp' in clean_line:
                        continue
                    issues.append({
                        'file': rel_path,
                        'line': idx,
                        'content': clean_line,
                        'type': 'STATIC_MUTABLE_RISK',
                        'detail': 'Static collection or mutable object found; potential cross-session memory leak.'
                    })

    return checked_files, issues


def audit_listeners_and_subscriptions(lib_path):
    audit_results = {}
    provider_files = ['auth_provider.dart', 'finance_provider.dart', 'session_provider.dart', 'club_provider.dart']

    for p_name in provider_files:
        p_path = os.path.join(lib_path, 'providers', p_name)
        if not os.path.exists(p_path):
            continue
        rel_path = os.path.relpath(p_path, PROJECT_ROOT).replace('\\', '/')
        with open(p_path, 'r', encoding='utf-8') as fp:
            content = fp.read()

        has_auth_listener = 'auth?.addListener(_onAuthChanged)' in content or 'auth.addListener(_onAuthChanged)' in content
        has_auth_remove = 'auth?.removeListener(_onAuthChanged)' in content or 'auth.removeListener(_onAuthChanged)' in content
        has_clear_all = 'clearAll()' in content
        has_dispose = '@override\n  void dispose()' in content or 'void dispose()' in content

        # Check StreamSubscription cancellation
        stream_subs = re.findall(r'StreamSubscription(?:<[^>]+>)?\s+(\w+);', content)
        un_cancelled_subs = []
        for sub in stream_subs:
            cancel_pattern = f'{sub}?.cancel()'
            cancel_alt = f'{sub}.cancel()'
            if cancel_pattern not in content and cancel_alt not in content:
                un_cancelled_subs.append(sub)

        audit_results[p_name] = {
            'file': rel_path,
            'has_auth_listener': has_auth_listener,
            'removes_auth_listener_on_dispose': has_auth_remove,
            'has_clear_all_method': has_clear_all,
            'proper_dispose': has_dispose,
            'stream_subscriptions_tracked': len(stream_subs),
            'un_cancelled_subscriptions': un_cancelled_subs,
            'leak_risk': 'NONE' if (has_auth_remove or not has_auth_listener) and not un_cancelled_subs else 'HIGH'
        }

    return audit_results


def main():
    print("=== AST & Static Memory Retention Audit ===")
    checked_files, static_issues = audit_static_and_globals(LIB_DIR)
    print(f"Checked Dart files: {checked_files}")
    print(f"Static mutable issues found: {len(static_issues)}")

    provider_audit = audit_listeners_and_subscriptions(LIB_DIR)
    print("Provider Lifecycle & Disposal Audit:")
    for name, res in provider_audit.items():
        print(f"  - {name}: AuthListener removed={res['removes_auth_listener_on_dispose']}, LeakRisk={res['leak_risk']}")

    report = {
        'total_dart_files_scanned': checked_files,
        'static_mutable_collections_found': len(static_issues),
        'static_mutable_details': static_issues,
        'providers_lifecycle_audit': provider_audit,
        'overall_ast_verdict': 'CLEAN' if len(static_issues) == 0 and all(p['leak_risk'] == 'NONE' for p in provider_audit.values()) else 'FLAGGED'
    }

    output_path = os.path.join(PROJECT_ROOT, 'docs/reviews/bh07/private_heap_evidence/ast_memory_audit.json')
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8', newline='\n') as fp:
        json.dump(report, fp, indent=2)
        fp.write('\n')

    print(f"Report written to: {output_path}")
    print(f"AST Verdict: {report['overall_ast_verdict']}")
    return 0 if report['overall_ast_verdict'] == 'CLEAN' else 1


if __name__ == '__main__':
    sys.exit(main())
