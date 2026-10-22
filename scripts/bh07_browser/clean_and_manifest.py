#!/usr/bin/env python3
"""
Audit and verification script for BH-07 browser evidence.
Supports two strict modes:
  --verify (default): READ-ONLY audit. Fails with non-zero exit code if any file
                      is missing, extra, altered (hash mismatch), contains CRLF/BOM,
                      or contains secret patterns. NEVER rewrites or modifies files.
  --generate: Normalizes text files to UTF-8 without BOM and LF-only,
              scans for secrets, and generates hashes.sha256.
"""

import sys
import os
import hashlib
import re

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
EVIDENCE_DIR = os.path.join(PROJECT_ROOT, 'docs/reviews/bh07/browser_evidence')
MANIFEST_PATH = os.path.join(EVIDENCE_DIR, 'hashes.sha256')

TEXT_EXTS = {'.log', '.json', '.md', '.txt'}

# Regex patterns for secret detection
SECRET_PATTERNS = [
    (re.compile(r'sb_secret_[A-Za-z0-9_-]+'), "Supabase Secret Key"),
    (re.compile(r'ghp_[A-Za-z0-9_]{36}'), "GitHub Personal Access Token"),
    (re.compile(r'github_pat_[A-Za-z0-9_]+'), "GitHub Fine-Grained Token"),
    (re.compile(r'xox[baprs]-[A-Za-z0-9-]+'), "Slack Token"),
    (re.compile(r'AKIA[0-9A-Z]{16}'), "AWS Access Key"),
    (re.compile(r'AIza[0-9A-Za-z-_]{35}'), "Google API Key"),
    (re.compile(r'PR' + r'IVATE KEY-----'), "Private Key Header"),
]

# Allow public demo anon keys in documentation/commands
ANON_DEMO_JWT = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0"

def scan_file_for_secrets(full_path):
    hits = []
    with open(full_path, 'r', encoding='utf-8', errors='replace') as fp:
        content = fp.read()
    
    # Strip known public demo anon key before secret scanning
    sanitized = content.replace(ANON_DEMO_JWT, "[ANON_DEMO_PUBLIC_WHITELIST]")

    # Check for service role JWT
    if "service_role" in sanitized and "eyJ" in sanitized:
        # Check if actual service role token exists
        sr_matches = re.findall(r'eyJ[A-Za-z0-9-_=]+\.eyJ[A-Za-z0-9-_=]+\.[A-Za-z0-9-_.+/=]+', sanitized)
        for token in sr_matches:
            if "service_role" in token or "EGIM96RAZx35lJzdJsyH" in token:
                hits.append(("Service Role Privileged JWT", token[:15] + "..."))

    for pat, desc in SECRET_PATTERNS:
        matches = pat.findall(sanitized)
        for m in matches:
            hits.append((desc, str(m)[:15] + "..."))
    return hits

def run_generate():
    print("=== [GENERATE MODE] Normalizing files and generating hashes.sha256 ===")
    
    # 1. Normalize line endings and BOM
    for root, dirs, files in os.walk(EVIDENCE_DIR):
        for f in sorted(files):
            if f == 'hashes.sha256':
                continue
            ext = os.path.splitext(f)[1].lower()
            if ext in TEXT_EXTS:
                full_path = os.path.join(root, f)
                with open(full_path, 'rb') as fp:
                    data = fp.read()
                has_bom = data.startswith(b'\xef\xbb\xbf')
                cr_count = data.count(b'\r')
                if has_bom or cr_count > 0:
                    clean = data
                    if has_bom:
                        clean = clean[3:]
                    clean = clean.replace(b'\r\n', b'\n').replace(b'\r', b'\n')
                    with open(full_path, 'wb') as fp:
                        fp.write(clean)
                    print(f"Normalized {f}: stripped BOM={has_bom}, converted CR={cr_count}")

    # 2. Secret Scan
    secret_errors = []
    for root, dirs, files in os.walk(EVIDENCE_DIR):
        for f in sorted(files):
            if f == 'hashes.sha256':
                continue
            ext = os.path.splitext(f)[1].lower()
            if ext in TEXT_EXTS:
                full_path = os.path.join(root, f)
                hits = scan_file_for_secrets(full_path)
                if hits:
                    secret_errors.append((f, hits))

    if secret_errors:
        print("\nERROR: Secret scan failed in generate mode!")
        for f, hits in secret_errors:
            print(f"  File {f}: {hits}")
        sys.exit(1)
    print("Secret scan clean: 0 secrets found.")

    # 3. Generate Manifest
    entries = []
    for root, dirs, files in os.walk(EVIDENCE_DIR):
        for f in sorted(files):
            if f == 'hashes.sha256':
                continue
            full_path = os.path.join(root, f)
            rel_path = os.path.relpath(full_path, EVIDENCE_DIR).replace('\\', '/')
            with open(full_path, 'rb') as fp:
                sha = hashlib.sha256(fp.read()).hexdigest()
            entries.append((rel_path, sha))

    entries.sort(key=lambda x: x[0])
    with open(MANIFEST_PATH, 'wb') as fp:
        for rel_path, sha in entries:
            line = f"{sha}  {rel_path}\n"
            fp.write(line.encode('utf-8'))
    print(f"Successfully generated {MANIFEST_PATH} with {len(entries)} entries.\n")

def run_verify():
    print("=== [READ-ONLY VERIFY MODE] Auditing manifest, file integrity and secrets ===")
    
    if not os.path.exists(MANIFEST_PATH):
        print(f"FATAL: Manifest not found at {MANIFEST_PATH}")
        sys.exit(1)

    with open(MANIFEST_PATH, 'rb') as fp:
        manifest_raw = fp.read()

    if manifest_raw.startswith(b'\xef\xbb\xbf'):
        print("FATAL: hashes.sha256 starts with UTF-8 BOM!")
        sys.exit(1)
    if b'\r' in manifest_raw:
        print("FATAL: hashes.sha256 contains CRLF line endings!")
        sys.exit(1)

    expected_manifest = {}
    for line in manifest_raw.decode('utf-8').splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split('  ', 1)
        if len(parts) != 2:
            print(f"FATAL: Malformed manifest line: {line}")
            sys.exit(1)
        sha, rel_path = parts
        expected_manifest[rel_path] = sha

    print(f"Loaded {len(expected_manifest)} expected entries from manifest.")

    # Check for missing or corrupted files
    errors = []
    actual_files = set()
    for root, dirs, files in os.walk(EVIDENCE_DIR):
        for f in sorted(files):
            if f == 'hashes.sha256':
                continue
            full_path = os.path.join(root, f)
            rel_path = os.path.relpath(full_path, EVIDENCE_DIR).replace('\\', '/')
            actual_files.add(rel_path)

            with open(full_path, 'rb') as fp:
                data = fp.read()
            actual_sha = hashlib.sha256(data).hexdigest()

            if rel_path not in expected_manifest:
                errors.append(f"EXTRA FILE (not in manifest): {rel_path}")
            elif expected_manifest[rel_path] != actual_sha:
                errors.append(f"HASH MISMATCH for {rel_path}: expected {expected_manifest[rel_path]}, got {actual_sha}")

            ext = os.path.splitext(f)[1].lower()
            if ext in TEXT_EXTS:
                if data.startswith(b'\xef\xbb\xbf'):
                    errors.append(f"BOM DETECTED in {rel_path}")
                if b'\r' in data:
                    errors.append(f"CRLF DETECTED in {rel_path}")
                
                # Secret check
                hits = scan_file_for_secrets(full_path)
                if hits:
                    errors.append(f"SECRET DETECTED in {rel_path}: {hits}")

    # Check for files listed in manifest but missing on disk
    for rel_path in expected_manifest:
        if rel_path not in actual_files:
            errors.append(f"MISSING FILE (declared in manifest): {rel_path}")

    if errors:
        print(f"\nAUDIT FAILED with {len(errors)} error(s):")
        for err in errors:
            print(f"  [X] {err}")
        sys.exit(1)

    print(f"ALL CHECKS PASSED: {len(actual_files)}/{len(expected_manifest)} files verified, 0 secret, 100% UTF-8 LF.")
    sys.exit(0)

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--generate':
        run_generate()
    else:
        run_verify()
