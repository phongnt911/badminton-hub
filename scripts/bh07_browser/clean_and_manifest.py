#!/usr/bin/env python3
"""
Audit and verification script for BH-07 browser evidence.

Modes:
  --verify (default): READ-ONLY audit. Fails with a non-zero exit code if a
                      file is missing/extra/altered, if text is not strict
                      UTF-8 without BOM/CR, or if a secret/JWT outside the
                      public allowlist is found. It never writes any file.
  --generate:          Normalizes evidence text to UTF-8 without BOM and LF,
                      scans for secrets, and writes hashes.sha256.

The public demo anon JWT is the only JWT allowed in evidence. Every other JWT
is decoded and rejected, including tokens whose base64 payload contains a
service_role claim. The scanner never searches for the literal role string
inside base64 text.
"""

import argparse
import base64
import hashlib
import json
import os
import re
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
DEFAULT_EVIDENCE_DIR = os.path.join(PROJECT_ROOT, 'docs/reviews/bh07/browser_evidence')
DEFAULT_MANIFEST_PATH = os.path.join(DEFAULT_EVIDENCE_DIR, 'hashes.sha256')
TEXT_EXTS = {'.log', '.json', '.md', '.txt'}

# The only public token allowed in published evidence. It is the local demo
# anon key already present in the reproduction commands.
ALLOWED_JWTS = {
    'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.'
    'eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.'
    'CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0'
}
JWT_RE = re.compile(r'eyJ[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}')

SECRET_PATTERNS = [
    (re.compile(r'sb_secret_[A-Za-z0-9_-]+'), 'Supabase Secret Key'),
    (re.compile(r'ghp_[A-Za-z0-9_]{36}'), 'GitHub Personal Access Token'),
    (re.compile(r'github_pat_[A-Za-z0-9_]+'), 'GitHub Fine-Grained Token'),
    (re.compile(r'xox[baprs]-[A-Za-z0-9-]+'), 'Slack Token'),
    (re.compile(r'AKIA[0-9A-Z]{16}'), 'AWS Access Key'),
    (re.compile(r'AIza[0-9A-Za-z-_]{35}'), 'Google API Key'),
    (re.compile(r'PRIVATE KEY-----'), 'Private Key Header'),
]


def decode_base64url_json(segment):
    padding = '=' * (-len(segment) % 4)
    raw = base64.urlsafe_b64decode((segment + padding).encode('ascii'))
    return json.loads(raw.decode('utf-8'))


def scan_text_for_secrets(text):
    hits = []

    for token in JWT_RE.findall(text):
        if token in ALLOWED_JWTS:
            continue
        try:
            parts = token.split('.')
            header = decode_base64url_json(parts[0])
            payload = decode_base64url_json(parts[1])
        except Exception:
            hits.append(('Non-allowlisted or malformed JWT', token[:16] + '...'))
            continue
        role = payload.get('role') if isinstance(payload, dict) else None
        alg = header.get('alg') if isinstance(header, dict) else None
        if role == 'service_role':
            hits.append(('Service Role JWT outside public allowlist', f'{token[:16]}... role={role} alg={alg}'))
        else:
            hits.append(('JWT outside public allowlist', f'{token[:16]}... role={role} alg={alg}'))

    for pattern, description in SECRET_PATTERNS:
        for match in pattern.findall(text):
            hits.append((description, str(match)[:15] + '...'))
    return hits


def strict_text(data, rel_path, errors):
    if data.startswith(b'\xef\xbb\xbf'):
        errors.append(f'BOM DETECTED in {rel_path}')
    if b'\r' in data:
        errors.append(f'CRLF/CR DETECTED in {rel_path}')
    try:
        return data.decode('utf-8')
    except UnicodeDecodeError as exc:
        errors.append(f'INVALID UTF-8 in {rel_path}: {exc}')
        return None


def iter_actual_files(evidence_dir):
    for root, dirs, files in os.walk(evidence_dir):
        dirs.sort()
        for name in sorted(files):
            if name == 'hashes.sha256':
                continue
            full_path = os.path.join(root, name)
            rel_path = os.path.relpath(full_path, evidence_dir).replace('\\', '/')
            yield full_path, rel_path


def read_manifest(manifest_path, errors):
    if not os.path.exists(manifest_path):
        errors.append(f'Manifest not found: {manifest_path}')
        return {}
    with open(manifest_path, 'rb') as fp:
        raw = fp.read()
    if raw.startswith(b'\xef\xbb\xbf'):
        errors.append('hashes.sha256 starts with UTF-8 BOM')
        return {}
    if b'\r' in raw:
        errors.append('hashes.sha256 contains CRLF/CR')
        return {}
    try:
        text = raw.decode('utf-8')
    except UnicodeDecodeError as exc:
        errors.append(f'hashes.sha256 is not strict UTF-8: {exc}')
        return {}

    entries = {}
    for line in text.splitlines():
        if not line.strip():
            continue
        match = re.fullmatch(r'([0-9a-f]{64})  (.+)', line)
        if not match:
            errors.append(f'Malformed manifest line: {line}')
            continue
        sha, rel_path = match.groups()
        if rel_path.startswith('/') or rel_path.startswith('\\') or '..' in rel_path.split('/'):
            errors.append(f'Unsafe manifest path: {rel_path}')
            continue
        if rel_path in entries:
            errors.append(f'Duplicate manifest path: {rel_path}')
            continue
        entries[rel_path] = sha
    return entries


def run_generate(evidence_dir, manifest_path):
    print('=== [GENERATE MODE] Normalizing evidence and generating hashes.sha256 ===')
    errors = []
    if not os.path.isdir(evidence_dir):
        print(f'FATAL: evidence directory not found: {evidence_dir}')
        return 1

    for full_path, rel_path in iter_actual_files(evidence_dir):
        if os.path.splitext(rel_path)[1].lower() not in TEXT_EXTS:
            continue
        with open(full_path, 'rb') as fp:
            data = fp.read()
        has_bom = data.startswith(b'\xef\xbb\xbf')
        clean = data[3:] if has_bom else data
        clean = clean.replace(b'\r\n', b'\n').replace(b'\r', b'\n')
        try:
            text = clean.decode('utf-8')
        except UnicodeDecodeError as exc:
            errors.append(f'INVALID UTF-8 in {rel_path}: {exc}')
            continue
        encoded = text.encode('utf-8')
        if has_bom or encoded != data:
            with open(full_path, 'wb') as fp:
                fp.write(encoded)
            print(f'Normalized {rel_path} (BOM/CRLF -> UTF-8 LF)')

    for full_path, rel_path in iter_actual_files(evidence_dir):
        if os.path.splitext(rel_path)[1].lower() not in TEXT_EXTS:
            continue
        with open(full_path, 'rb') as fp:
            data = fp.read()
        text = strict_text(data, rel_path, errors)
        if text is None:
            continue
        for description, value in scan_text_for_secrets(text):
            errors.append(f'SECRET DETECTED in {rel_path}: {description} {value}')

    if errors:
        print('GENERATE FAILED:')
        for error in errors:
            print(f'  [X] {error}')
        return 1

    entries = []
    for full_path, rel_path in iter_actual_files(evidence_dir):
        with open(full_path, 'rb') as fp:
            sha = hashlib.sha256(fp.read()).hexdigest()
        entries.append((rel_path, sha))
    entries.sort(key=lambda item: item[0])
    with open(manifest_path, 'wb') as fp:
        for rel_path, sha in entries:
            fp.write(f'{sha}  {rel_path}\n'.encode('utf-8'))
    print(f'Generated {manifest_path} with {len(entries)} entries; 0 secret; strict UTF-8 LF.')
    return 0


def run_verify(evidence_dir, manifest_path):
    print('=== [READ-ONLY VERIFY MODE] Auditing manifest, integrity, encoding and secrets ===')
    errors = []
    if not os.path.isdir(evidence_dir):
        print(f'FATAL: evidence directory not found: {evidence_dir}')
        return 1
    if not os.path.exists(manifest_path):
        print(f'FATAL: manifest not found: {manifest_path}')
        return 1

    manifest = read_manifest(manifest_path, errors)
    actual_files = set()
    actual_hashes = {}

    for full_path, rel_path in iter_actual_files(evidence_dir):
        actual_files.add(rel_path)
        with open(full_path, 'rb') as fp:
            data = fp.read()
        actual_hashes[rel_path] = hashlib.sha256(data).hexdigest()

        if rel_path not in manifest:
            errors.append(f'EXTRA FILE (not in manifest): {rel_path}')
        elif manifest[rel_path] != actual_hashes[rel_path]:
            errors.append(
                f'HASH MISMATCH for {rel_path}: expected {manifest[rel_path]}, got {actual_hashes[rel_path]}'
            )

        if os.path.splitext(rel_path)[1].lower() in TEXT_EXTS:
            text = strict_text(data, rel_path, errors)
            if text is not None:
                for description, value in scan_text_for_secrets(text):
                    errors.append(f'SECRET DETECTED in {rel_path}: {description} {value}')

    for rel_path in sorted(manifest):
        if rel_path not in actual_files:
            errors.append(f'MISSING FILE (declared in manifest): {rel_path}')

    if errors:
        print(f'\nAUDIT FAILED with {len(errors)} error(s):')
        for error in errors:
            print(f'  [X] {error}')
        return 1

    print(
        f'ALL CHECKS PASSED: {len(actual_files)}/{len(manifest)} files verified, '
        f'0 secret/JWT outside allowlist, strict UTF-8 LF.'
    )
    return 0


def main():
    parser = argparse.ArgumentParser(description='BH-07 browser evidence verifier')
    parser.add_argument('--generate', action='store_true', help='generate hashes.sha256 (writes files)')
    parser.add_argument('--verify', action='store_true', help='read-only verification (default)')
    parser.add_argument('--evidence-dir', default=DEFAULT_EVIDENCE_DIR, help='evidence directory override')
    parser.add_argument('--manifest', default=None, help='manifest path override (default: <evidence>/hashes.sha256)')
    args = parser.parse_args()

    evidence_dir = os.path.abspath(args.evidence_dir)
    manifest_path = os.path.abspath(args.manifest) if args.manifest else os.path.join(evidence_dir, 'hashes.sha256')

    if args.generate:
        return run_generate(evidence_dir, manifest_path)
    return run_verify(evidence_dir, manifest_path)


if __name__ == '__main__':
    sys.exit(main())
