#!/usr/bin/env python3
"""Prove run_negative_controls.js executes the current manager gate.

A disposable copy of the browser scripts is run twice:
  * unmodified copy: expected exit 0 (positive harness baseline)
  * copy with the BR3 manager gate changed to `if (true)`: expected exit 1

The real scripts and real evidence are never modified by the mutation.
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
SCRIPTS_DIR = os.path.join(PROJECT_ROOT, 'scripts/bh07_browser')
EVIDENCE_DIR = os.path.join(PROJECT_ROOT, 'docs/reviews/bh07/browser_evidence')
OUTPUT_JSON = os.path.join(EVIDENCE_DIR, 'mutant_negative_control.json')
OUTPUT_LOG = os.path.join(EVIDENCE_DIR, 'mutant_negative_control.log')
NODE = shutil.which('node') or 'node'
REAL_SOURCE_SHA = subprocess.check_output(
    ['git', 'rev-parse', 'HEAD'], cwd=PROJECT_ROOT, text=True, encoding='utf-8'
).strip()


def run_controls(project_root):
    env = os.environ.copy()
    env['BH07_SOURCE_SHA'] = REAL_SOURCE_SHA
    proc = subprocess.run(
        [NODE, os.path.join(project_root, 'scripts/bh07_browser/run_negative_controls.js')],
        cwd=project_root,
        text=True,
        encoding='utf-8',
        errors='replace',
        capture_output=True,
        env=env,
    )
    return proc.returncode, proc.stdout, proc.stderr


def main():
    temp_root = tempfile.mkdtemp(prefix='bh07-negative-mutant-')
    temp_scripts = os.path.join(temp_root, 'scripts/bh07_browser')
    os.makedirs(os.path.dirname(temp_scripts), exist_ok=True)
    shutil.copytree(SCRIPTS_DIR, temp_scripts)
    os.makedirs(os.path.join(temp_root, 'docs/reviews/bh07/browser_evidence'), exist_ok=True)

    baseline_exit, baseline_stdout, baseline_stderr = run_controls(temp_root)

    assertions_path = os.path.join(temp_scripts, 'assertions.js')
    with open(assertions_path, 'r', encoding='utf-8') as fp:
        source = fp.read()
    marker = (
        '  // BR3_MANAGER_GATE: the only place manager clipboard acceptance is decided.\n'
        '  // A mutation of this gate must make run_negative_controls.js fail.\n'
        '  const managerGatePassed = errors.length === 0;\n'
        '  if (managerGatePassed) {'
    )
    if marker not in source:
        print('FATAL: manager gate marker not found; refusing to report a mutant control')
        shutil.rmtree(temp_root, ignore_errors=True)
        return 1
    mutated = source.replace(marker, marker.replace('if (managerGatePassed) {', 'if (true) {'), 1)
    with open(assertions_path, 'w', encoding='utf-8', newline='\n') as fp:
        fp.write(mutated)

    mutant_exit, mutant_stdout, mutant_stderr = run_controls(temp_root)
    baseline_ok = baseline_exit == 0
    mutant_detected = mutant_exit != 0
    all_ok = baseline_ok and mutant_detected

    log = [
        '=== Unmodified control copy (positive harness baseline) ===',
        f'exit={baseline_exit}',
        baseline_stdout.rstrip(),
        baseline_stderr.rstrip(),
        '',
        '=== Copy with BR3 manager gate changed to if (true) ===',
        f'exit={mutant_exit}',
        mutant_stdout.rstrip(),
        mutant_stderr.rstrip(),
        '',
    ]
    with open(OUTPUT_LOG, 'w', encoding='utf-8', newline='\n') as fp:
        fp.write('\n'.join(log))

    output = {
        'source_sha': REAL_SOURCE_SHA,
        'negative_controls_sha256': hashlib.sha256(
            open(os.path.join(SCRIPTS_DIR, 'run_negative_controls.js'), 'rb').read()
        ).hexdigest(),
        'assertions_sha256': hashlib.sha256(
            open(os.path.join(SCRIPTS_DIR, 'assertions.js'), 'rb').read()
        ).hexdigest(),
        'baseline_exit': baseline_exit,
        'mutant_exit': mutant_exit,
        'baseline_ok': baseline_ok,
        'mutant_detected': mutant_detected,
        'all_ok': all_ok,
    }
    with open(OUTPUT_JSON, 'w', encoding='utf-8', newline='\n') as fp:
        json.dump(output, fp, ensure_ascii=False, indent=2)
        fp.write('\n')

    print(f'Unmodified negative-control copy: exit {baseline_exit} (expected 0)')
    print(f'if (true) manager-gate mutant copy: exit {mutant_exit} (expected non-zero)')
    print(f'Mutant control: {"PASS" if all_ok else "FAIL"}')
    shutil.rmtree(temp_root, ignore_errors=True)
    return 0 if all_ok else 1


if __name__ == '__main__':
    sys.exit(main())
