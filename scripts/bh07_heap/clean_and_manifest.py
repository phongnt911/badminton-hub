#!/usr/bin/env python3
"""
Manifest and security audit script for BH-07 V2b Private Heap evidence.

Modes:
  --verify (default): Strict read-only audit. Fails if files are altered, missing, extra,
                      if manifest/evidence has CRLF/BOM/invalid UTF-8/malformed entries,
                      or if non-sanitized secrets/JWTs are found.
  --generate:         Normalizes text to UTF-8 LF without BOM, scans for secrets,
                      and writes hashes.sha256 in strict UTF-8 LF format.
  --test-controls:    Runs synthetic verify controls (positive, manifest_crlf,
                      hash_mismatch, missing, extra) to ensure verifier soundness.
"""

import argparse
import base64
import hashlib
import json
import os
import re
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
DEFAULT_EVIDENCE_DIR = os.path.join(PROJECT_ROOT, 'docs/reviews/bh07/private_heap_evidence')
DEFAULT_MANIFEST_PATH = os.path.join(DEFAULT_EVIDENCE_DIR, 'hashes.sha256')
TEXT_EXTS = {'.log', '.json', '.md', '.txt', '.sha256'}

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
    (re.compile(r'password\s*[:=]\s*[\'"][^\'"]+[\'"]', re.I), 'Hardcoded Password'),
]

MANIFEST_ENTRY_RE = re.compile(r'^[a-f0-9]{64}  [a-zA-Z0-9_.\-/]+$')


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
            payload = decode_base64url_json(parts[1])
            role = payload.get('role') if isinstance(payload, dict) else None
            hits.append(('JWT outside allowlist', f'{token[:16]}... role={role}'))
        except Exception:
            hits.append(('Malformed JWT', token[:16] + '...'))

    for pattern, desc in SECRET_PATTERNS:
        for match in pattern.findall(text):
            hits.append((desc, str(match)[:20] + '...'))

    return hits


def normalize_evidence_files(evidence_dir):
    modified = []
    for root, _, files in os.walk(evidence_dir):
        for name in files:
            path = os.path.join(root, name)
            if os.path.abspath(path) == os.path.abspath(os.path.join(evidence_dir, 'hashes.sha256')):
                continue
            ext = os.path.splitext(name)[1].lower()
            if ext not in TEXT_EXTS:
                continue

            with open(path, 'rb') as fp:
                data = fp.read()

            clean = data
            if clean.startswith(b'\xef\xbb\xbf'):
                clean = clean[3:]
            clean = clean.replace(b'\r\n', b'\n').replace(b'\r', b'\n')

            if clean != data:
                with open(path, 'wb') as fp:
                    fp.write(clean)
                modified.append(os.path.relpath(path, evidence_dir))

    return modified


def compute_hashes(evidence_dir):
    records = []
    for root, _, files in os.walk(evidence_dir):
        for name in sorted(files):
            path = os.path.join(root, name)
            if os.path.abspath(path) == os.path.abspath(os.path.join(evidence_dir, 'hashes.sha256')):
                continue
            rel_path = os.path.relpath(path, evidence_dir).replace('\\', '/')
            h = hashlib.sha256()
            with open(path, 'rb') as fp:
                while chunk := fp.read(65536):
                    h.update(chunk)
            records.append((rel_path, h.hexdigest()))
    records.sort(key=lambda r: r[0])
    return records


def verify_manifest(evidence_dir, manifest_path):
    """
    Xác thực nghiêm ngặt read-only:
    - hashes.sha256 không chứa BOM, không chứa CRLF (b'\r'), strict UTF-8 LF.
    - Định dạng từng dòng đúng cú pháp sha256sum: <64 hex>  <relative_path>.
    - Không trùng lặp đường dẫn.
    - Khớp hoàn toàn (không thiếu file, không dư file, không sai hash).
    - Toàn bộ text files không chứa BOM, CRLF, hay secrets.
    """
    if not os.path.exists(manifest_path):
        print(f"FAIL: Manifest not found at {manifest_path}", file=sys.stderr)
        return False

    errors = []

    # 1. Đọc manifest dưới dạng binary để kiểm tra BOM / CRLF
    with open(manifest_path, 'rb') as fp:
        raw_manifest = fp.read()

    if raw_manifest.startswith(b'\xef\xbb\xbf'):
        errors.append("BOM detected in manifest (hashes.sha256)")
    if b'\r' in raw_manifest:
        errors.append("CRLF detected in manifest (hashes.sha256)")

    try:
        manifest_text = raw_manifest.decode('utf-8')
    except UnicodeDecodeError as e:
        errors.append(f"Non-UTF8 encoding in manifest: {e}")
        manifest_text = ""

    expected = {}
    if manifest_text:
        lines = manifest_text.split('\n')
        # Bỏ dòng rỗng cuối nếu file kết thúc bằng \n
        if lines and lines[-1] == '':
            lines.pop()

        for idx, line in enumerate(lines, 1):
            if not line:
                errors.append(f"Manifest line {idx} is empty")
                continue
            if not MANIFEST_ENTRY_RE.match(line):
                errors.append(f"Manifest line {idx} is malformed: '{line}' (must be <64-hex><2-spaces><path>)")
                continue

            parts = line.split('  ', 1)
            sha, rel_name = parts[0], parts[1]
            if rel_name in expected:
                errors.append(f"Duplicate path in manifest: {rel_name}")
            expected[rel_name] = sha

    # 2. So sánh file hashes
    current_records = compute_hashes(evidence_dir)
    actual = {rel: sha for rel, sha in current_records}

    for rel, exp_sha in expected.items():
        if rel not in actual:
            errors.append(f"MISSING file: {rel}")
        elif actual[rel] != exp_sha:
            errors.append(f"HASH MISMATCH on {rel}: expected {exp_sha}, got {actual[rel]}")

    for rel in actual:
        if rel not in expected:
            errors.append(f"EXTRA file not in manifest: {rel}")

    # 3. Quét kiểm tra strict UTF-8 LF và secrets cho tất cả các file trong thư mục
    for root, _, files in os.walk(evidence_dir):
        for name in files:
            path = os.path.join(root, name)
            ext = os.path.splitext(name)[1].lower()
            if ext in TEXT_EXTS:
                with open(path, 'rb') as fp:
                    raw = fp.read()
                if raw.startswith(b'\xef\xbb\xbf'):
                    errors.append(f"BOM detected: {name}")
                if b'\r' in raw:
                    errors.append(f"CRLF detected: {name}")
                try:
                    text = raw.decode('utf-8')
                except UnicodeDecodeError as e:
                    errors.append(f"Non UTF-8 in {name}: {e}")
                    continue

                hits = scan_text_for_secrets(text)
                for desc, token in hits:
                    errors.append(f"SECRET LEAK in {name}: {desc} ({token})")

    if errors:
        print("=== VERIFY FAIL ===", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return False

    print(f"PASS: Verified {len(actual)} files in manifest. All strict UTF-8 LF, clean hashes, zero secret leaks.")
    return True


def generate_manifest(evidence_dir, manifest_path):
    modified = normalize_evidence_files(evidence_dir)
    if modified:
        print(f"Normalized line endings/BOM on {len(modified)} files.")

    records = compute_hashes(evidence_dir)
    lines = [f"{sha}  {rel}\n" for rel, sha in records]

    with open(manifest_path, 'wb') as fp:
        fp.write(''.join(lines).encode('utf-8'))

    print(f"Generated manifest with {len(records)} entries at {manifest_path}")
    return True


def run_self_controls():
    """Tự kiểm tra các control của verifier tương tự probes.py."""
    import tempfile
    import shutil
    from pathlib import Path

    print("Running verifier self-controls...")
    with tempfile.TemporaryDirectory(prefix='verify-self-check-') as d:
        d = Path(d)
        source = d / 'synthetic_valid_bundle'
        source.mkdir()
        (source / 'summary.json').write_bytes(b'{}\n')
        h = hashlib.sha256((source / 'summary.json').read_bytes()).hexdigest()
        (source / 'hashes.sha256').write_bytes(f"{h}  summary.json\n".encode('utf-8'))

        cases = ['positive', 'manifest_crlf', 'hash_mismatch', 'missing', 'extra']
        for case in cases:
            p = d / ('ev_' + case)
            shutil.copytree(source, p)
            mf = p / 'hashes.sha256'
            if case == 'manifest_crlf':
                mf.write_bytes(mf.read_bytes().replace(b'\n', b'\r\n'))
            elif case == 'hash_mismatch':
                (p / 'summary.json').write_bytes(b'{"changed": true}\n')
            elif case == 'missing':
                (p / 'summary.json').unlink()
            elif case == 'extra':
                (p / 'extra.txt').write_bytes(b'synthetic extra\n')

            before = {x.name: hashlib.sha256(x.read_bytes()).hexdigest() for x in p.iterdir()}
            ok = verify_manifest(str(p), str(p / 'hashes.sha256'))
            after = {x.name: hashlib.sha256(x.read_bytes()).hexdigest() for x in p.iterdir()}

            assert before == after, f"Case {case} mutated files!"
            if case == 'positive':
                assert ok is True, f"Positive case failed verify"
                print("  [PASS] verify_control: positive exit 0, readonly")
            else:
                assert ok is False, f"Negative case {case} passed verify unexpectedly!"
                print(f"  [PASS] verify_control: {case} exit 1, readonly")

    print("All verifier self-controls passed successfully!")


def main():
    parser = argparse.ArgumentParser(description="Evidence manifest and sanitizer audit")
    parser.add_argument('--verify', action='store_true', default=False, help="Read-only audit")
    parser.add_argument('--generate', action='store_true', default=False, help="Generate hashes.sha256")
    parser.add_argument('--dir', default=DEFAULT_EVIDENCE_DIR, help="Evidence directory")
    parser.add_argument('--test-controls', action='store_true', default=False, help="Run verifier self-controls")
    args = parser.parse_args()

    if args.test_controls:
        run_self_controls()
        sys.exit(0)

    manifest_path = os.path.join(args.dir, 'hashes.sha256')

    if args.generate:
        generate_manifest(args.dir, manifest_path)
        ok = verify_manifest(args.dir, manifest_path)
        sys.exit(0 if ok else 1)
    else:
        ok = verify_manifest(args.dir, manifest_path)
        sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
