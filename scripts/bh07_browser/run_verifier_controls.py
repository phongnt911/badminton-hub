#!/usr/bin/env python3
"""Exercise clean_and_manifest.py on disposable evidence copies.

The real evidence directory and manifest are never modified. Every fault is
introduced in a fresh copy, its manifest hash is updated when the fault is a
content-only fault, and the verifier must exit non-zero without touching the
copy's manifest or files.
"""

import base64
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
EVIDENCE_DIR = os.path.join(PROJECT_ROOT, 'docs/reviews/bh07/browser_evidence')
VERIFIER = os.path.join(PROJECT_ROOT, 'scripts/bh07_browser/clean_and_manifest.py')
OUTPUT_JSON = os.path.join(EVIDENCE_DIR, 'verifier_controls.json')
OUTPUT_LOG = os.path.join(EVIDENCE_DIR, 'verifier_controls.log')


def b64url(value):
    return base64.urlsafe_b64encode(value.encode('utf-8')).decode('ascii').rstrip('=')


def redact_control_output(text):
    # Never publish a token-shaped value or the fake secret from a fault log.
    text = re.sub(r'eyJ[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}', '[REDACTED_JWT]', text)
    text = re.sub(r'sb_secret_[A-Za-z0-9_-]+', 'sb_secret_[REDACTED]', text)
    return text


def snapshot(root):
    result = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        for name in sorted(filenames):
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, root).replace('\\', '/')
            with open(full, 'rb') as fp:
                result[rel] = hashlib.sha256(fp.read()).hexdigest()
    return result


def run_verifier(evidence_dir):
    proc = subprocess.run(
        [sys.executable, VERIFIER, '--verify', '--evidence-dir', evidence_dir],
        cwd=PROJECT_ROOT,
        text=True,
        encoding='utf-8',
        errors='replace',
        capture_output=True,
    )
    return proc.returncode, proc.stdout, proc.stderr


def run_generate(evidence_dir):
    proc = subprocess.run(
        [sys.executable, VERIFIER, '--generate', '--evidence-dir', evidence_dir],
        cwd=PROJECT_ROOT,
        text=True,
        encoding='utf-8',
        errors='replace',
        capture_output=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f'generate failed for control copy:\n{proc.stdout}\n{proc.stderr}')


def update_manifest_hash(evidence_dir, rel_path, content):
    path = os.path.join(evidence_dir, rel_path)
    with open(path, 'wb') as fp:
        fp.write(content if isinstance(content, bytes) else content.encode('utf-8'))
    sha = hashlib.sha256(open(path, 'rb').read()).hexdigest()
    manifest_path = os.path.join(evidence_dir, 'hashes.sha256')
    with open(manifest_path, 'r', encoding='utf-8') as fp:
        lines = fp.read().splitlines()
    updated = []
    matched = False
    for line in lines:
        if line.endswith(f'  {rel_path}'):
            updated.append(f'{sha}  {rel_path}')
            matched = True
        else:
            updated.append(line)
    if not matched:
        raise RuntimeError(f'{rel_path} not found in control manifest')
    with open(manifest_path, 'w', encoding='utf-8', newline='\n') as fp:
        fp.write('\n'.join(updated) + '\n')


def mutate_missing(root):
    os.remove(os.path.join(root, 'analyze.log'))


def mutate_extra(root):
    with open(os.path.join(root, 'unexpected-extra.txt'), 'w', encoding='utf-8', newline='\n') as fp:
        fp.write('extra evidence file\n')


def mutate_hash_mismatch(root):
    path = os.path.join(root, 'browser_runner.log')
    with open(path, 'a', encoding='utf-8', newline='\n') as fp:
        fp.write('\npost-manifest hash mismatch control\n')


def mutate_secret(root):
    path = os.path.join(root, 'commands.md')
    with open(path, 'rb') as fp:
        content = fp.read()
    # Build the fake token at runtime so the control script itself does not
    # contain a token-shaped literal that a repository scanner could flag.
    fake_secret = ('sb_' + 'secret_' + 'fake_control_value_123456').encode('ascii')
    update_manifest_hash(root, 'commands.md', content + b'\n' + fake_secret + b'\n')


def mutate_jwt(root):
    payload = {
        'iss': 'supabase-demo',
        'role': 'service_role',
        'exp': 1983812996,
    }
    token = '.'.join([
        b64url('{"alg":"HS256","typ":"JWT"}'),
        b64url(json.dumps(payload, separators=(',', ':'))),
        'ZmFrZS1zaWduYXR1cmU',
    ])
    path = os.path.join(root, 'commands.md')
    with open(path, 'rb') as fp:
        content = fp.read()
    update_manifest_hash(root, 'commands.md', content + b'\n' + token.encode('ascii') + b'\n')


def mutate_invalid_utf8(root):
    path = os.path.join(root, 'environment.json')
    with open(path, 'rb') as fp:
        content = fp.read()
    update_manifest_hash(root, 'environment.json', content + b'\n\xff\xfe invalid utf8 control\n')


def mutate_bom(root):
    path = os.path.join(root, 'environment.json')
    with open(path, 'rb') as fp:
        content = fp.read()
    update_manifest_hash(root, 'environment.json', b'\xef\xbb\xbf' + content)


def mutate_crlf(root):
    path = os.path.join(root, 'commands.md')
    with open(path, 'rb') as fp:
        content = fp.read()
    update_manifest_hash(root, 'commands.md', content.replace(b'\n', b'\r\n'))


CASES = [
    ('baseline public evidence', None, 0),
    ('missing declared file', mutate_missing, 1),
    ('extra undeclared file', mutate_extra, 1),
    ('hash mismatch', mutate_hash_mismatch, 1),
    ('fake sb_secret value', mutate_secret, 1),
    ('fake service_role JWT with valid hash', mutate_jwt, 1),
    ('invalid UTF-8 with valid hash', mutate_invalid_utf8, 1),
    ('UTF-8 BOM with valid hash', mutate_bom, 1),
    ('CRLF with valid hash', mutate_crlf, 1),
]


def main():
    temp_root = tempfile.mkdtemp(prefix='bh07-verifier-controls-')
    pristine = os.path.join(temp_root, 'pristine')
    shutil.copytree(EVIDENCE_DIR, pristine, ignore=shutil.ignore_patterns('hashes.sha256'))
    run_generate(pristine)

    log_lines = []
    results = []

    for name, mutation, expected_exit in CASES:
        case_dir = os.path.join(temp_root, 'case-' + str(len(results)))
        shutil.copytree(pristine, case_dir)
        if mutation is not None:
            mutation(case_dir)

        before = snapshot(case_dir)
        exit_code, stdout, stderr = run_verifier(case_dir)
        after = snapshot(case_dir)
        readonly = before == after
        ok = (exit_code == expected_exit) and readonly

        log_lines.append(f'=== {name} ===')
        log_lines.append(f'expected_exit={expected_exit} actual_exit={exit_code} readonly={readonly}')
        log_lines.append(redact_control_output(stdout.rstrip()))
        if stderr.strip():
            log_lines.append('STDERR: ' + redact_control_output(stderr.rstrip()))
        log_lines.append('')

        results.append({
            'control': name,
            'expected_exit': expected_exit,
            'actual_exit': exit_code,
            'readonly': readonly,
            'ok': ok,
        })

    all_ok = all(result['ok'] for result in results)
    output = {
        'source_sha': subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'], cwd=PROJECT_ROOT, text=True, encoding='utf-8'
        ).strip(),
        'verifier_sha256': hashlib.sha256(open(VERIFIER, 'rb').read()).hexdigest(),
        'controls': results,
        'all_ok': all_ok,
    }
    with open(OUTPUT_JSON, 'w', encoding='utf-8', newline='\n') as fp:
        json.dump(output, fp, ensure_ascii=False, indent=2)
        fp.write('\n')
    with open(OUTPUT_LOG, 'w', encoding='utf-8', newline='\n') as fp:
        fp.write('\n'.join(log_lines) + '\n')

    for result in results:
        marker = 'PASS' if result['ok'] else 'FAIL'
        print(
            f'{marker}: {result["control"]} (expected exit {result["expected_exit"]}, '
            f'got {result["actual_exit"]}, readonly={result["readonly"]})'
        )
    print(f'\nVerifier controls: {sum(1 for result in results if result["ok"])}/{len(results)} behaved as expected.')

    shutil.rmtree(temp_root, ignore_errors=True)
    return 0 if all_ok else 1


if __name__ == '__main__':
    sys.exit(main())
