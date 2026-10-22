import os
import hashlib
import re

evidence_dir = 'docs/reviews/bh07/browser_evidence'
text_exts = {'.log', '.json', '.md', '.txt'}

print("=== 1. Checking BOM & CRLF ===")
for root, dirs, files in os.walk(evidence_dir):
    for f in sorted(files):
        if f == 'hashes.sha256':
            continue
        ext = os.path.splitext(f)[1].lower()
        if ext in text_exts:
            full_path = os.path.join(root, f)
            with open(full_path, 'rb') as fp:
                data = fp.read()
            has_bom = data.startswith(b'\xef\xbb\xbf')
            cr_count = data.count(b'\r')
            if has_bom or cr_count > 0:
                print(f"Normalizing {f}: BOM={has_bom}, CR_count={cr_count}")
                clean = data
                if has_bom:
                    clean = clean[3:]
                clean = clean.replace(b'\r\n', b'\n').replace(b'\r', b'\n')
                with open(full_path, 'wb') as fp:
                    fp.write(clean)
            else:
                print(f"OK {f}: no BOM, CR=0")

print("\n=== 2. Secret Scan ===")
secret_patterns = [
    re.compile(r'ghp_[A-Za-z0-9_]{36}'),
    re.compile(r'github_pat_[A-Za-z0-9_]+'),
    re.compile(r'xox[baprs]-[A-Za-z0-9-]+'),
    re.compile(r'AKIA[0-9A-Z]{16}'),
    re.compile(r'AIza[0-9A-Za-z-_]{35}'),
    re.compile(r'PR' + r'IVATE KEY-----'),
]

suspicious_hits = []
for root, dirs, files in os.walk(evidence_dir):
    for f in sorted(files):
        if f == 'hashes.sha256':
            continue
        ext = os.path.splitext(f)[1].lower()
        if ext in text_exts:
            full_path = os.path.join(root, f)
            with open(full_path, 'r', encoding='utf-8', errors='replace') as fp:
                content = fp.read()
            for pat in secret_patterns:
                m = pat.search(content)
                if m:
                    suspicious_hits.append((f, pat.pattern, m.group(0)[:10]))

if suspicious_hits:
    print(f"WARNING: Found {len(suspicious_hits)} suspicious hits:")
    for hit in suspicious_hits:
        print(f"  {hit}")
else:
    print("Secret scan clean: 0 secret patterns matched.")

print("\n=== 3. Generating hashes.sha256 ===")
manifest_entries = []
for root, dirs, files in os.walk(evidence_dir):
    for f in sorted(files):
        if f == 'hashes.sha256':
            continue
        full_path = os.path.join(root, f)
        rel_path = os.path.relpath(full_path, evidence_dir).replace('\\', '/')
        with open(full_path, 'rb') as fp:
            data = fp.read()
        sha = hashlib.sha256(data).hexdigest()
        manifest_entries.append((rel_path, sha, len(data)))

manifest_entries.sort(key=lambda x: x[0])

manifest_path = os.path.join(evidence_dir, 'hashes.sha256')
with open(manifest_path, 'wb') as fp:
    for rel_path, sha, size in manifest_entries:
        line = f"{sha}  {rel_path}\n"
        fp.write(line.encode('utf-8'))

print(f"Generated manifest with {len(manifest_entries)} entries at {manifest_path}:")
for rel_path, sha, size in manifest_entries:
    print(f"  {sha[:12]}...  {rel_path} ({size} bytes)")

print("\n=== 4. Verifying Manifest ===")
verified_count = 0
with open(manifest_path, 'rb') as fp:
    manifest_bytes = fp.read()
    assert not manifest_bytes.startswith(b'\xef\xbb\xbf'), "hashes.sha256 has BOM!"
    assert manifest_bytes.count(b'\r') == 0, "hashes.sha256 has CR/CRLF!"
    lines = manifest_bytes.decode('utf-8').splitlines()

for line in lines:
    parts = line.strip().split('  ', 1)
    if len(parts) == 2:
        expected_sha, rel_path = parts
        full_path = os.path.join(evidence_dir, rel_path.replace('/', os.sep))
        with open(full_path, 'rb') as fp:
            actual_sha = hashlib.sha256(fp.read()).hexdigest()
        assert expected_sha == actual_sha, f"Hash mismatch for {rel_path}!"
        verified_count += 1

print(f"Verification successful: {verified_count}/{len(manifest_entries)} hashes match perfectly!")
