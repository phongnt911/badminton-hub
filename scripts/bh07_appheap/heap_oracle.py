"""Sentinel oracle for BH-07 app-profile V8 heap snapshots (Chrome DevTools Protocol).

Snapshot files are large and contain private app data. This module never copies or
publishes them: it reads each dump once, proves it is a complete V8 snapshot, counts
synthetic sentinel strings and returns counts plus a truncated SHA-256 so a reviewer
can compare runs without the raw heap ever leaving the machine.

A dump that is truncated, has a missing run of bytes, is not JSON, or whose node/edge
tables disagree with the snapshot metadata is *unusable*: the oracle then refuses to
answer instead of reporting "sentinel absent", because absent-from-a-broken-dump is
not evidence that the data was collected.

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
import os
import re
import sys

# V8 writes one JSON object whose top-level arrays are the heap tables. `strings` is
# always written last, so it must end the document; anything after it is corruption.
SNAPSHOT_KEYS = ('nodes', 'edges', 'strings')
ARRAY_KEY_RE = {key: re.compile(rb'"%s"\s*:\s*\[' % key.encode()) for key in SNAPSHOT_KEYS}
MIDDLE_KEYS_RE = re.compile(
    rb'(?:\s*,\s*"(?:traces|trace_function_infos|trace_tree|samples|locations)"\s*:\s*\[[^\]]*\])*\s*,?\s*')
INT_TOKEN_RE = re.compile(rb'-?\d+')
STRING_TOKEN_RE = re.compile(rb'"(?:[^"\\\x00-\x1f]|\\.)*"')
META_REQUIRED = ('meta', 'node_count', 'edge_count')
META_FIELDS = ('node_fields', 'node_types', 'edge_fields', 'edge_types')
MIN_SNAPSHOT_BYTES = 4096
MAX_SNAPSHOT_BYTES = 2 << 30
CHUNK = 1 << 20


def _metadata(buf):
    """Strictly parse the small `"snapshot"` object at the start of the dump."""
    if not buf.startswith(b'{"snapshot"'):
        return None, 'snapshot_does_not_start_with_snapshot_object', 0
    brace = buf.find(b'{', len(b'{"snapshot"'))
    if brace < 0:
        return None, 'snapshot_metadata_missing', 0
    depth = 0
    in_string = False
    escaped = False
    for index in range(brace, min(len(buf), brace + (1 << 20))):
        char = buf[index:index + 1]
        if in_string:
            if escaped:
                escaped = False
            elif char == b'\\':
                escaped = True
            elif char == b'"':
                in_string = False
            continue
        if char == b'"':
            in_string = True
        elif char == b'{':
            depth += 1
        elif char == b'}':
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(buf[brace:index + 1]), None, index + 1
                except json.JSONDecodeError as exc:
                    return None, f'snapshot_metadata_invalid_json: {exc.msg}', 0
    return None, 'snapshot_metadata_unterminated', 0


def _array_span(buf, key, start):
    """Return (key_start, open, close) byte offsets of the first `"key":[ ... ]`."""
    match = ARRAY_KEY_RE[key].search(buf, start)
    if not match:
        return None
    open_index = match.end() - 1
    # The string table contains `]` inside its literals, so it needs a real scan.
    close_index = _string_table_close(buf, open_index) if key == 'strings' else buf.find(b']', open_index)
    if close_index < 0:
        return None
    return match.start(), open_index, close_index


def _string_table_close(buf, open_index):
    """Offset of the `]` closing the string table, ignoring `]` inside literals."""
    depth = 0
    in_string = False
    escaped = False
    for index in range(open_index, len(buf)):
        char = buf[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == 0x5C:
                escaped = True
            elif char == 0x22:
                in_string = False
            continue
        if char == 0x22:
            in_string = True
        elif char == 0x5B:
            depth += 1
        elif char == 0x5D:
            depth -= 1
            if depth == 0:
                return index
    return -1


def _int_elements(segment):
    """Count the integers of a flat numeric table, rejecting anything else."""
    if not segment.strip():
        return 0
    parts = segment.split(b',')
    for part in parts:
        if not INT_TOKEN_RE.fullmatch(part.strip()):
            return None
    return len(parts)


def _string_elements(segment):
    """Count the JSON string literals of the string table, rejecting anything else."""
    if not segment.strip():
        return 0
    tokens = STRING_TOKEN_RE.findall(segment)
    if not tokens:
        return None
    leftover = STRING_TOKEN_RE.sub(b'', segment).strip(b' \t\r\n,')
    if leftover:
        return None
    return len(tokens)


def validate(buf):
    """Prove the dump is a complete, self-consistent V8 snapshot (no full JSON parse)."""
    if len(buf) < MIN_SNAPSHOT_BYTES:
        return False, 'snapshot_too_small', {}
    if len(buf) > MAX_SNAPSHOT_BYTES:
        return False, 'snapshot_too_large', {}

    meta, error, cursor = _metadata(buf)
    if meta is None:
        return False, error, {}
    for key in META_REQUIRED:
        if key not in meta:
            return False, f'snapshot_metadata_missing_{key}', {}
    if not isinstance(meta['meta'], dict):
        return False, 'snapshot_metadata_meta_not_object', {}
    fields = meta['meta']
    for key in META_FIELDS:
        if not isinstance(fields.get(key), list) or not fields[key]:
            return False, f'snapshot_metadata_missing_{key}', {}
    for name, type_name in (('node_fields', 'node_types'), ('edge_fields', 'edge_types')):
        if len(fields[type_name]) != len(fields[name]):
            return False, f'snapshot_metadata_{type_name}_length_mismatch', {}
    if not isinstance(meta['node_count'], int) or not isinstance(meta['edge_count'], int):
        return False, 'snapshot_metadata_counts_not_integer', {}
    if meta['node_count'] < 0 or meta['edge_count'] < 0:
        return False, 'snapshot_metadata_counts_negative', {}

    spans = {}
    for key in SNAPSHOT_KEYS:
        span = _array_span(buf, key, cursor)
        if span is None:
            return False, f'snapshot_table_missing_{key}', {}
        spans[key] = span
        cursor = span[2] + 1
    if not (spans['nodes'][1] < spans['edges'][1] < spans['strings'][1]):
        return False, 'snapshot_tables_out_of_order', {}

    # Nothing but traces/samples/locations may sit between the edge and string tables.
    if not MIDDLE_KEYS_RE.fullmatch(buf[spans['edges'][2] + 1:spans['strings'][0]]):
        return False, 'snapshot_unexpected_content_between_tables', {}

    # The string table is last: only the closing brace may follow it.
    if buf.rindex(b']') != spans['strings'][2] or not re.fullmatch(rb'\s*\}\s*', buf[spans['strings'][2] + 1:]):
        return False, 'snapshot_does_not_end_with_string_table', {}

    node_elements = _int_elements(buf[spans['nodes'][1] + 1:spans['nodes'][2]])
    edge_elements = _int_elements(buf[spans['edges'][1] + 1:spans['edges'][2]])
    string_elements = _string_elements(buf[spans['strings'][1] + 1:spans['strings'][2]])
    if node_elements is None:
        return False, 'snapshot_node_table_not_integers', {}
    if edge_elements is None:
        return False, 'snapshot_edge_table_not_integers', {}
    if string_elements is None:
        return False, 'snapshot_string_table_not_strings', {}
    if string_elements == 0:
        return False, 'snapshot_string_table_empty', {}

    expected_nodes = meta['node_count'] * len(fields['node_fields'])
    expected_edges = meta['edge_count'] * len(fields['edge_fields'])
    if node_elements != expected_nodes:
        return False, f'snapshot_node_count_mismatch: {node_elements} != {expected_nodes}', {}
    if edge_elements != expected_edges:
        return False, f'snapshot_edge_count_mismatch: {edge_elements} != {expected_edges}', {}

    return True, None, {
        'node_count': meta['node_count'],
        'edge_count': meta['edge_count'],
        'string_count': string_elements,
        'size_bytes': len(buf),
    }


def scan(path, sentinels):
    """Validate one heap snapshot and count sentinel occurrences inside it."""
    encoded = {name: value.encode('utf-8') for name, value in sentinels.items()}
    size = os.path.getsize(path)
    if size > MAX_SNAPSHOT_BYTES:
        return {
            'ok': False,
            'error': 'snapshot_too_large',
            'size_bytes': size,
            'sha256_12': None,
            'sentinels': {name: {'present': None, 'occurrences': None} for name in encoded},
        }
    with open(path, 'rb') as fp:
        buf = fp.read()

    ok, error, details = validate(buf)
    counts = {name: buf.count(value) for name, value in encoded.items()}
    result = {
        'ok': ok,
        'size_bytes': len(buf),
        'sha256_12': hashlib.sha256(buf).hexdigest()[:12],
        'sentinels': {name: {'present': count > 0, 'occurrences': count}
                      for name, count in counts.items()},
    }
    if details:
        result['structure'] = details
    if not ok:
        result['error'] = error
        # Never let a caller read "sentinel absent" out of an unusable dump.
        for name in result['sentinels']:
            result['sentinels'][name]['present'] = None
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

    for epoch in sorted(set(scans) - set(expectations)):
        findings.append(f'{epoch}: unexpected snapshot epoch')
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
    meta = {
        'meta': {'node_fields': ['type', 'name'], 'node_types': [['object'], 'string'],
                 'edge_fields': ['type'], 'edge_types': [['property']]},
        'node_count': 2, 'edge_count': 1, 'trace_function_count': 0,
    }
    pad = '"pad":"' + 'x' * 5000 + '",'

    def snapshot(strings):
        return (b'{"snapshot":' + json.dumps(meta, separators=(',', ':')).encode()
                + b',' + pad.encode() + b'"nodes":[0,0,0,0],"edges":[0],'
                + b'"strings":[' + b','.join(b'"' + s.encode() + b'"' for s in strings) + b']}')

    cases = []
    path = write(snapshot(['SENTINEL-BANK-123', 'SENTINEL-PROBE-ALIVE', 'other']))
    cases.append(('positive_present', scan(path, sentinel), True, True))
    path = write(snapshot(['SENTINEL-PROBE-ALIVE', 'other']))
    cases.append(('negative_absent', scan(path, sentinel), False, True))
    path = write(snapshot(['SENTINEL-BANK-123', 'SENTINEL-PROBE-ALIVE'])[:-2])
    cases.append(('truncated_is_not_absent', scan(path, sentinel), None, False))
    path = write(b'{"snapshot":BROKEN,' + b'x' * 5000 + b',"nodes":[],"edges":[],"strings":["a"]}')
    cases.append(('invalid_json_is_not_absent', scan(path, sentinel), None, False))
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
