"""Sentinel oracle for BH-07 app-profile V8 heap snapshots (Chrome DevTools Protocol).

Snapshot files are large and contain private app data. This module never copies or
publishes them: it streams each dump once, counts synthetic sentinel strings and
returns counts plus a truncated SHA-256 so a reviewer can compare runs without the
raw heap ever leaving the machine.

The oracle is deliberately dumb about *why* a string is present. Presence means the
string is reachable in the live JS heap at that epoch; absence means it was collected.

Usage:
  python heap_oracle.py scan --snapshot <file> --sentinels <sentinels.json> [--out <file>]
  python heap_oracle.py decide --scans <scans.json> --expectations <expectations.json> [--out <file>]
  python heap_oracle.py self-test
"""
import argparse
import hashlib
import json
import sys

# A real Chrome heap snapshot is a single JSON object with these top-level arrays.
# If they are missing the dump is truncated/aborted, and "sentinel absent" would be a
# false green, so scan() must refuse it instead of reporting zeros.
STRUCTURE_MARKERS = (b'"nodes":[', b'"edges":[', b'"strings":[')
MIN_SNAPSHOT_BYTES = 4096
CHUNK = 1 << 20


def scan(path, sentinels):
    """Count sentinel occurrences in one heap snapshot without loading it into memory."""
    encoded = {name: value.encode('utf-8') for name, value in sentinels.items()}
    overlap = max([len(v) for v in encoded.values()] + [len(m) for m in STRUCTURE_MARKERS] + [16])
    counts = {name: 0 for name in encoded}
    flags = {marker: False for marker in STRUCTURE_MARKERS}
    size = 0
    sha = hashlib.sha256()
    head = b''
    tail = b''
    carry = b''
    with open(path, 'rb') as fp:
        while True:
            chunk = fp.read(CHUNK)
            if not chunk:
                break
            size += len(chunk)
            sha.update(chunk)
            if len(head) < 64:
                head += chunk[:64 - len(head)]
            tail = chunk[-16:]
            window = carry + chunk
            for name, value in encoded.items():
                counts[name] += window.count(value)
            for marker in STRUCTURE_MARKERS:
                if not flags[marker] and marker in window:
                    flags[marker] = True
            carry = window[-overlap:]

    complete = (head.startswith(b'{"snapshot"') and size >= MIN_SNAPSHOT_BYTES
                and tail.rstrip().endswith(b'}') and all(flags.values()))
    result = {
        'ok': complete,
        'size_bytes': size,
        'sha256_12': sha.hexdigest()[:12],
        'sentinels': {name: {'present': count > 0, 'occurrences': count}
                      for name, count in counts.items()},
    }
    if not complete:
        result['error'] = 'snapshot_incomplete_or_unparsable'
        result['structure'] = {m.decode(): flags[m] for m in STRUCTURE_MARKERS}
    return result


def decide(scans, expectations, cleanup_ok, mode):
    """Turn per-epoch scans into one verdict shared by JSON, Markdown and exit code.

    A failed/incomplete scan is a hard failure, never "sentinel absent = clean".
    """
    findings = []
    verdict_ok = True

    if mode != 'profile':
        findings.append(f'build mode is {mode!r}, expected profile')
        verdict_ok = False
    if not cleanup_ok:
        findings.append('heap dump cleanup not verified')
        verdict_ok = False

    for epoch, expected in expectations.items():
        scan_result = scans.get(epoch)
        if not scan_result:
            findings.append(f'{epoch}: no snapshot recorded')
            verdict_ok = False
            continue
        if not scan_result.get('ok'):
            findings.append(f'{epoch}: snapshot unusable ({scan_result.get("error")})')
            verdict_ok = False
            continue
        for sentinel, want_present in expected.items():
            got = scan_result['sentinels'].get(sentinel, {}).get('present')
            if want_present == 'either':
                continue
            if got != want_present:
                verdict_ok = False
                findings.append(
                    f'{epoch}: sentinel {sentinel} expected '
                    f'{"present" if want_present else "absent"}, got {got}')

    return {
        'verdict': 'PASS' if verdict_ok else 'FAIL',
        'findings': findings,
        'epochs_checked': len(expectations),
    }


def self_test():
    """Positive/negative controls for the oracle itself, no browser required."""
    import tempfile
    from pathlib import Path

    def write(body):
        tmp = tempfile.NamedTemporaryFile('wb', suffix='.heapsnapshot', delete=False)
        tmp.write(body)
        tmp.close()
        return tmp.name

    sentinel = {'bank': 'SENTINEL-BANK-123', 'probe': 'SENTINEL-PROBE-ALIVE'}
    pad = b'"pad":"' + b'x' * 5000 + b'",'

    def snapshot(strings):
        body = (b'{"snapshot":{"meta":{}},' + pad + b'"nodes":[],"edges":[],"strings":['
                + b','.join(b'"' + s.encode() + b'"' for s in strings) + b']}')
        return body

    cases = []
    path = write(snapshot(['SENTINEL-BANK-123', 'SENTINEL-PROBE-ALIVE', 'other']))
    cases.append(('positive_present', scan(path, sentinel), True, True))
    path = write(snapshot(['SENTINEL-PROBE-ALIVE', 'other']))
    cases.append(('negative_absent', scan(path, sentinel), False, True))
    path = write(snapshot(['SENTINEL-BANK-123', 'SENTINEL-PROBE-ALIVE'])[:-40])
    cases.append(('truncated_is_not_absent', scan(path, sentinel), None, False))
    path = write(b'')
    cases.append(('empty_is_not_absent', scan(path, sentinel), None, False))

    failures = []
    for name, result, want_bank, want_ok in cases:
        if result['ok'] != want_ok:
            failures.append(f'{name}: ok={result["ok"]} expected {want_ok}')
        if want_bank is not None and result['sentinels']['bank']['present'] != want_bank:
            failures.append(f'{name}: bank present={result["sentinels"]["bank"]["present"]} expected {want_bank}')

    clean = {'baseline': {'ok': True, 'sentinels': {'probe': {'present': True}, 'bank': {'present': False}}},
             'owner': {'ok': True, 'sentinels': {'probe': {'present': True}, 'bank': {'present': True}}}}
    expectations = {'baseline': {'probe': True, 'bank': False}, 'owner': {'probe': True, 'bank': True}}
    if decide(clean, expectations, True, 'profile')['verdict'] != 'PASS':
        failures.append('clean scans must PASS')
    leaked = json.loads(json.dumps(clean))
    leaked['baseline']['sentinels']['bank']['present'] = True
    if decide(leaked, expectations, True, 'profile')['verdict'] != 'FAIL':
        failures.append('leaked baseline must FAIL')
    broken = json.loads(json.dumps(clean))
    broken['owner']['ok'] = False
    if decide(broken, expectations, True, 'profile')['verdict'] != 'FAIL':
        failures.append('unusable snapshot must FAIL')
    if decide(clean, expectations, False, 'profile')['verdict'] != 'FAIL':
        failures.append('unverified cleanup must FAIL')
    if decide(clean, expectations, True, 'debug')['verdict'] != 'FAIL':
        failures.append('non-profile build must FAIL')

    for failure in failures:
        print(f'FAIL {failure}')
    print(f'self-test: {len(cases) + 5 - len(failures)}/{len(cases) + 5} controls passed')
    return 0 if not failures else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='cmd', required=True)

    p_scan = sub.add_parser('scan')
    p_scan.add_argument('--snapshot', required=True)
    p_scan.add_argument('--sentinels', required=True)
    p_scan.add_argument('--out')

    p_decide = sub.add_parser('decide')
    p_decide.add_argument('--scans', required=True)
    p_decide.add_argument('--expectations', required=True)
    p_decide.add_argument('--cleanup-ok', required=True, choices=['true', 'false'])
    p_decide.add_argument('--mode', required=True)
    p_decide.add_argument('--out')

    sub.add_parser('self-test')

    args = parser.parse_args(argv)
    if args.cmd == 'self-test':
        return self_test()

    if args.cmd == 'scan':
        with open(args.sentinels, encoding='utf-8') as fp:
            sentinels = json.load(fp)
        result = scan(args.snapshot, sentinels)
        payload = json.dumps(result, ensure_ascii=False, indent=2)
        if args.out:
            with open(args.out, 'w', encoding='utf-8', newline='\n') as fp:
                fp.write(payload + '\n')
        print(payload)
        return 0 if result['ok'] else 2

    with open(args.scans, encoding='utf-8') as fp:
        scans = json.load(fp)
    with open(args.expectations, encoding='utf-8') as fp:
        expectations = json.load(fp)
    verdict = decide(scans, expectations, args.cleanup_ok == 'true', args.mode)
    payload = json.dumps(verdict, ensure_ascii=False, indent=2)
    if args.out:
        with open(args.out, 'w', encoding='utf-8', newline='\n') as fp:
            fp.write(payload + '\n')
    print(payload)
    return 0 if verdict['verdict'] == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
