#!/usr/bin/env python3
"""
AST and Codebase Memory Retention Audit for BH-07 V2b.

Rà soát mã nguồn lib/ để phát hiện:
1. Static mutable collections và inferred constructors (List, Map, Set).
2. Global / Top-level mutable collections.
3. StreamSubscriptions không được hủy (.cancel()) trong dispose().
4. Listeners (auth.addListener) không được gỡ bỏ (removeListener) trong dispose().
5. Kiểm tra phương thức dọn dẹp state (clearAll / reset).
"""

import os
import re
import sys
import json

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
LIB_DIR = os.path.join(PROJECT_ROOT, 'lib')


def extract_dispose_body(content):
    """
    Trích xuất chính xác thân hàm dispose() { ... } bằng cách cân bằng ngoặc nhọn.
    Trả về chuỗi nội dung bên trong cặp ngoặc nhọn của dispose, hoặc None nếu không có.
    """
    match = re.search(r'(?:@override\s+)?void\s+dispose\s*\(\s*\)\s*\{', content)
    if not match:
        return None

    start_idx = match.end() - 1  # vị trí dấu {
    brace_depth = 0
    end_idx = None
    for i in range(start_idx, len(content)):
        char = content[i]
        if char == '{':
            brace_depth += 1
        elif char == '}':
            brace_depth -= 1
            if brace_depth == 0:
                end_idx = i
                break

    if end_idx is not None:
        return content[start_idx + 1:end_idx]
    return content[start_idx + 1:]


def audit_static_and_globals(target_dir):
    """
    Quét static mutable collections và global/top-level variables.
    Bao gồm:
    - Typed static: static List/Map/Set ...
    - Inferred static: static final leak = List.empty(...) / <Object>[]
    - Global / top-level: final leak = <Object>[] / List.empty(...)
    - Bỏ qua: static const, const, methods, RegExp, immutable patterns.
    """
    issues = []
    checked_files = 0

    collection_types = r'(?:List|Map|Set)'
    collection_ctors = r'(?:(?:List|Map|Set)(?:<[^>]+>)?\.(?:empty|filled|from|of|generate|identity))'
    collection_literals = r'(?:<[^>]+>)?\s*[\[\{]'

    for root, _, files in os.walk(target_dir):
        for f in files:
            if not f.endswith('.dart'):
                continue
            checked_files += 1
            path = os.path.join(root, f)
            rel_path = os.path.relpath(path, PROJECT_ROOT).replace('\\', '/')
            with open(path, 'r', encoding='utf-8') as fp:
                lines = fp.readlines()

            brace_depth = 0
            for idx, line in enumerate(lines, 1):
                clean_line = line.strip()

                # Bỏ qua comments
                if clean_line.startswith('//') or clean_line.startswith('*') or clean_line.startswith('/*'):
                    continue

                # Cập nhật brace_depth cơ bản (không tính string literals phức tạp)
                # Đếm { và } trong dòng không chứa comment
                code_part = clean_line.split('//')[0]
                brace_open = code_part.count('{')
                brace_close = code_part.count('}')

                # Bỏ qua static const hoặc const (compile-time constant)
                if 'static const ' in clean_line or clean_line.startswith('const '):
                    brace_depth += (brace_open - brace_close)
                    continue

                # Bỏ qua RegExp
                if 'RegExp(' in clean_line:
                    brace_depth += (brace_open - brace_close)
                    continue

                # Bỏ qua static method declarations (có ngoặc tròn tham số và dấu mở hàm hoặc mũi tên =>)
                is_static_method = bool(
                    re.search(r'\bstatic\s+(?:[A-Za-z0-9_<>,?\s]+)\s+\w+\s*\([^)]*\)\s*(?:=>|\{)', clean_line) or
                    re.search(r'\bstatic\s+(?:[A-Za-z0-9_<>,?\s]+)\s+\w+\s*\(', clean_line)
                )

                # 1. Static mutable trong class
                if 'static ' in clean_line and not is_static_method:
                    is_typed = re.search(r'\bstatic\s+(?:final\s+)?' + collection_types + r'\b', clean_line)
                    is_inferred = re.search(r'\bstatic\s+(?:final\s+|var\s+)?\w+\s*=\s*' + collection_ctors, clean_line) or \
                                  re.search(r'\bstatic\s+(?:final\s+|var\s+)?\w+\s*=\s*' + collection_literals, clean_line)

                    # Đảm bảo không phải const assignment (ví dụ static final list = const [];)
                    if (is_typed or is_inferred) and '= const ' not in clean_line and not clean_line.endswith('const [];'):
                        issues.append({
                            'file': rel_path,
                            'line': idx,
                            'content': clean_line,
                            'type': 'STATIC_MUTABLE_RISK',
                            'detail': 'Static mutable collection or constructor found; cross-session retention risk.'
                        })

                # 2. Global / Top-level variables (ở ngoài class / brace_depth == 0)
                # Kiểm tra nếu ở ngoài class (brace_depth == 0 trước khi cộng brace của dòng này)
                if brace_depth == 0 and not clean_line.startswith('import ') and not clean_line.startswith('export ') and not clean_line.startswith('part '):
                    is_global_var = bool(re.search(r'^(?:final\s+|var\s+|(?:List|Map|Set)(?:<[^>]+>)?\s+)\w+\s*=', clean_line))
                    if is_global_var:
                        is_global_coll = re.search(r'=\s*' + collection_ctors, clean_line) or \
                                         re.search(r'=\s*' + collection_literals, clean_line) or \
                                         re.search(r'^(?:List|Map|Set)', clean_line)
                        if is_global_coll and '= const ' not in clean_line:
                            issues.append({
                                'file': rel_path,
                                'line': idx,
                                'content': clean_line,
                                'type': 'GLOBAL_MUTABLE_RISK',
                                'detail': 'Global/Top-level mutable collection found; potential memory leak.'
                            })

                brace_depth += (brace_open - brace_close)
                if brace_depth < 0:
                    brace_depth = 0

    return checked_files, issues


def audit_listeners_and_subscriptions(target_dir):
    """
    Rà soát vòng đời Provider:
    - AuthListener: phải được gỡ bỏ bằng removeListener TRONG THÂN HÀM dispose().
    - StreamSubscription: phải bắt cả nullable (?) và kiểm tra .cancel() TRONG THÂN HÀM dispose().
    - LeakRisk = 'HIGH' nếu không dispose đúng phạm vi.
    """
    audit_results = {}
    provider_files = ['auth_provider.dart', 'finance_provider.dart', 'session_provider.dart', 'club_provider.dart']

    for p_name in provider_files:
        p_path = os.path.join(target_dir, 'providers', p_name)
        if not os.path.exists(p_path):
            continue
        rel_path = os.path.relpath(p_path, PROJECT_ROOT).replace('\\', '/')
        with open(p_path, 'r', encoding='utf-8') as fp:
            content = fp.read()

        dispose_body = extract_dispose_body(content)
        has_dispose = dispose_body is not None

        has_auth_listener = bool(re.search(r'auth(?:\?\.|\.)addListener\(_onAuthChanged\)', content))

        # Kiểm tra removeListener CÓ NẰM TRONG dispose_body HAY KHÔNG
        removes_in_dispose = False
        if has_dispose and dispose_body:
            removes_in_dispose = bool(re.search(r'auth(?:\?\.|\.)removeListener\(_onAuthChanged\)', dispose_body))

        has_clear_all = 'clearAll()' in content

        # Check StreamSubscription (bắt cả nullable: StreamSubscription<int>? _sub hoặc StreamSubscription? _sub)
        stream_subs = re.findall(r'StreamSubscription(?:<[^>]+>)?\??\s+(\w+)\s*;', content)
        un_cancelled_subs = []
        for sub in stream_subs:
            cancel_pattern = re.compile(rf'{sub}(?:\?\.|\.)cancel\(\)')
            # Phải được cancel() TRONG dispose_body
            if not has_dispose or not dispose_body or not cancel_pattern.search(dispose_body):
                un_cancelled_subs.append(sub)

        # Đánh giá Leak Risk
        leak_risk = 'NONE'
        if has_auth_listener and not removes_in_dispose:
            leak_risk = 'HIGH'
        elif un_cancelled_subs:
            leak_risk = 'HIGH'
        elif not has_dispose and (has_auth_listener or stream_subs):
            leak_risk = 'HIGH'

        audit_results[p_name] = {
            'file': rel_path,
            'has_auth_listener': has_auth_listener,
            'removes_auth_listener_on_dispose': removes_in_dispose,
            'has_clear_all_method': has_clear_all,
            'proper_dispose': has_dispose,
            'stream_subscriptions_tracked': len(stream_subs),
            'un_cancelled_subscriptions': un_cancelled_subs,
            'leak_risk': leak_risk
        }

    return audit_results


def run_self_controls():
    """Tự kiểm tra 5 controls tương thích với reviewer probes."""
    import tempfile
    import shutil
    from pathlib import Path

    print("Running AST memory audit self-controls...")
    with tempfile.TemporaryDirectory(prefix='ast-self-check-') as d:
        d = Path(d)
        cases = {
            'typed_static_list': ('class X {\n static List<Object> leak = <Object>[];\n}', 1),
            'inferred_static_constructor': ('class X {\n static final leak = List<Object>.empty(growable: true);\n}', 1),
            'global_list': ('final leak = <Object>[];', 1)
        }
        for name, (code, exp_issues) in cases.items():
            p = d / name
            p.mkdir()
            (p / 'sample.dart').write_text(code, encoding='utf-8')
            _, issues = audit_static_and_globals(str(p))
            assert len(issues) == exp_issues, f"Control {name} failed: got {len(issues)}, expected {exp_issues}"
            print(f"  [PASS] static_control: {name} detected {len(issues)} issue(s)")

        sub_cases = {
            'nullable_uncancelled': (
                'class X {\n StreamSubscription<int>? _sub;\n void dispose() {}\n}',
                True,  # uncancelled > 0
                'HIGH'
            ),
            'remove_outside_dispose': (
                'class X {\n void init() { auth.addListener(_onAuthChanged); }\n void unused() { auth.removeListener(_onAuthChanged); }\n void dispose() {}\n}',
                False, # removes_auth_listener_on_dispose is False
                'HIGH'
            )
        }
        for name, (code, check_cond, exp_risk) in sub_cases.items():
            lib = d / name
            (lib / 'providers').mkdir(parents=True)
            (lib / 'providers/auth_provider.dart').write_text(code, encoding='utf-8')
            res = audit_listeners_and_subscriptions(str(lib))['auth_provider.dart']
            assert res['leak_risk'] == exp_risk, f"Control {name} risk failed: got {res['leak_risk']}, exp {exp_risk}"
            if name == 'remove_outside_dispose':
                assert res['removes_auth_listener_on_dispose'] is False
            elif name == 'nullable_uncancelled':
                assert len(res['un_cancelled_subscriptions']) > 0
            print(f"  [PASS] subscription_control: {name} correctly flagged as {res['leak_risk']}")

    print("All AST self-controls passed successfully!")


def main():
    if '--test-controls' in sys.argv:
        run_self_controls()
        return 0

    print("=== AST & Static Memory Retention Audit ===")
    checked_files, static_issues = audit_static_and_globals(LIB_DIR)
    print(f"Checked Dart files: {checked_files}")
    print(f"Static mutable issues found: {len(static_issues)}")

    provider_audit = audit_listeners_and_subscriptions(LIB_DIR)
    print("Provider Lifecycle & Disposal Audit:")
    for name, res in provider_audit.items():
        print(f"  - {name}: AuthListener removed={res['removes_auth_listener_on_dispose']}, LeakRisk={res['leak_risk']}, StreamSubs={res['stream_subscriptions_tracked']}")

    clean = len(static_issues) == 0 and all(p['leak_risk'] == 'NONE' for p in provider_audit.values())
    report = {
        'total_dart_files_scanned': checked_files,
        'static_mutable_collections_found': len(static_issues),
        'static_mutable_details': static_issues,
        'providers_lifecycle_audit': provider_audit,
        'overall_ast_verdict': 'CLEAN' if clean else 'FLAGGED'
    }

    output_path = os.path.join(PROJECT_ROOT, 'docs/reviews/bh07/private_heap_evidence/ast_memory_audit.json')
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8', newline='\n') as fp:
        json.dump(report, fp, indent=2)
        fp.write('\n')

    print(f"Report written to: {output_path}")
    print(f"AST Verdict: {report['overall_ast_verdict']}")
    return 0 if clean else 1


if __name__ == '__main__':
    sys.exit(main())
