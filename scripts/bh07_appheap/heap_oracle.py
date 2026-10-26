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
Presence is counted on the **decoded** string table of the parsed snapshot, so a value
written literally and the same value written with JSON unicode escapes agree (review
76334e2).

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

# V8 writes one JSON object whose top-level members are the heap tables. `snapshot`
# comes first and `strings` last, and nothing but the documented optional tables may sit
# between them. A duplicate key or an unknown top-level member is corruption, not a
# snapshot: json.loads alone would silently keep the last duplicate.
SNAPSHOT_KEYS = ('nodes', 'edges', 'strings')
V8_TOP_LEVEL_KEYS = ('snapshot', 'nodes', 'edges', 'traces', 'trace_function_infos', 'trace_tree',
                     'samples', 'locations', 'strings')
META_REQUIRED = ('meta', 'node_count', 'edge_count')
META_FIELDS = ('node_fields', 'node_types', 'edge_fields', 'edge_types')
MIN_SNAPSHOT_BYTES = 4096
MAX_SNAPSHOT_BYTES = 2 << 30
# A full JSON parse is what proves the grammar; above this size the oracle refuses to
# answer rather than fall back to a marker scan (review 57ec02c AH1).
MAX_PARSE_BYTES = 512 << 20


class _DuplicateKey(ValueError):
    """Raised by the object_pairs_hook when one object repeats a key."""


def _reject_duplicate_keys(pairs):
    seen = set()
    for key, _ in pairs:
        if key in seen:
            raise _DuplicateKey(key)
        seen.add(key)
    return dict(pairs)


def _parse(buf):
    """Decode and parse the whole dump; return (document, error)."""
    if len(buf) > MAX_PARSE_BYTES:
        return None, 'snapshot_too_large_to_parse'
    try:
        text = buf.decode('utf-8')
    except UnicodeDecodeError as exc:
        return None, f'snapshot_is_not_utf8: {exc.reason} at byte {exc.start}'
    try:
        return json.loads(text, object_pairs_hook=_reject_duplicate_keys), None
    except _DuplicateKey as exc:
        return None, f'snapshot_duplicate_key: {exc}'
    except json.JSONDecodeError as exc:
        return None, f'snapshot_invalid_json: {exc.msg} at byte {exc.pos}'
    except RecursionError:
        return None, 'snapshot_nesting_too_deep'


def _structure(doc):
    """Check the parsed document is a complete, self-consistent V8 snapshot."""
    if not isinstance(doc, dict):
        return False, 'snapshot_not_json_object', {}
    keys = list(doc)
    if not keys or keys[0] != 'snapshot':
        return False, 'snapshot_does_not_start_with_snapshot_object', {}
    unknown = [key for key in keys if key not in V8_TOP_LEVEL_KEYS]
    if unknown:
        return False, f'snapshot_unexpected_top_level_key: {unknown[0]}', {}
    for key in ('snapshot',) + SNAPSHOT_KEYS:
        if key not in doc:
            return False, f'snapshot_table_missing_{key}', {}

    meta = doc['snapshot']
    if not isinstance(meta, dict):
        return False, 'snapshot_metadata_not_object', {}
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
    if type(meta['node_count']) is not int or type(meta['edge_count']) is not int:
        return False, 'snapshot_metadata_counts_not_integer', {}
    if meta['node_count'] < 0 or meta['edge_count'] < 0:
        return False, 'snapshot_metadata_counts_negative', {}

    if [key for key in keys if key in SNAPSHOT_KEYS] != list(SNAPSHOT_KEYS):
        return False, 'snapshot_tables_out_of_order', {}
    if keys[-1] != 'strings':
        return False, 'snapshot_does_not_end_with_string_table', {}

    nodes, edges, strings = doc['nodes'], doc['edges'], doc['strings']
    for name, table in (('node', nodes), ('edge', edges)):
        if not isinstance(table, list):
            return False, f'snapshot_{name}_table_not_array', {}
        if any(type(value) is not int for value in table):
            return False, f'snapshot_{name}_table_not_integers', {}
    if not isinstance(strings, list):
        return False, 'snapshot_string_table_not_array', {}
    if any(not isinstance(value, str) for value in strings):
        return False, 'snapshot_string_table_not_strings', {}
    if not strings:
        return False, 'snapshot_string_table_empty', {}

    expected_nodes = meta['node_count'] * len(fields['node_fields'])
    expected_edges = meta['edge_count'] * len(fields['edge_fields'])
    if len(nodes) != expected_nodes:
        return False, f'snapshot_node_count_mismatch: {len(nodes)} != {expected_nodes}', {}
    if len(edges) != expected_edges:
        return False, f'snapshot_edge_count_mismatch: {len(edges)} != {expected_edges}', {}

    return True, None, {
        'node_count': meta['node_count'],
        'edge_count': meta['edge_count'],
        'string_count': len(strings),
        'size_bytes': None,
    }


def parse_snapshot(buf):
    """Parse once and return (document, error, details) so callers reuse the decode.

    Review 76334e2 AH7: counting raw bytes made "ABC" and "\\u0041\\u0042\\u0043" disagree
    even though they are the same JSON value. Presence is decided from the parsed string
    table, never from the serialized representation.
    """
    if len(buf) < MIN_SNAPSHOT_BYTES:
        return None, 'snapshot_too_small', {}
    if len(buf) > MAX_SNAPSHOT_BYTES:
        return None, 'snapshot_too_large', {}
    doc, error = _parse(buf)
    if error:
        return None, error, {}
    ok, error, details = _structure(doc)
    if not ok:
        return None, error, {}
    details['size_bytes'] = len(buf)
    return doc, None, details


def validate(buf):
    """Prove the dump is a complete V8 snapshot by parsing its whole JSON grammar.

    Reviews 8914b2f and 57ec02c both found marker/regex scans that certified dumps with a
    missing separator, a stray token before `nodes` or the non-JSON integer `00`. The
    only reliable gate is the grammar itself, so the dump must parse as one JSON object
    (duplicate keys rejected), with the V8 tables in order and the counts matching.
    """
    doc, error, details = parse_snapshot(buf)
    return doc is not None, error, details


def count_sentinels(strings, sentinels):
    """Substring-count each sentinel in the decoded string table (exact, case-sensitive).

    V8 keeps every JS string in the `strings` table, so this is the complete set of
    values reachable at that epoch. Matching policy: a sentinel counts when it appears
    anywhere inside a decoded string value; occurrences are summed per value, which makes
    the result independent of how JSON escaped the characters.
    """
    counts = {name: 0 for name in sentinels}
    for value in strings:
        for name, needle in sentinels.items():
            if needle in value:
                counts[name] += value.count(needle)
    return counts


def scan(path, sentinels):
    """Validate one heap snapshot and count sentinel occurrences in its decoded strings."""
    size = os.path.getsize(path)
    if size > MAX_SNAPSHOT_BYTES:
        return {
            'ok': False,
            'error': 'snapshot_too_large',
            'size_bytes': size,
            'sha256_12': None,
            'sentinels': {name: {'present': None, 'occurrences': None} for name in sentinels},
        }
    with open(path, 'rb') as fp:
        buf = fp.read()

    doc, error, details = parse_snapshot(buf)
    result = {
        'ok': doc is not None,
        'size_bytes': len(buf),
        'sha256_12': hashlib.sha256(buf).hexdigest()[:12],
    }
    if details:
        result['structure'] = details
    if doc is None:
        result['error'] = error
        # Never let a caller read "sentinel absent" out of an unusable dump.
        result['sentinels'] = {name: {'present': None, 'occurrences': None} for name in sentinels}
        return result
    counts = count_sentinels(doc.get('strings') or [], sentinels)
    result['sentinels'] = {name: {'present': count > 0, 'occurrences': count}
                           for name, count in counts.items()}
    return result


def scan_problems(scan):
    """Schema and count/presence consistency problems of one recorded scan.

    Shared by `decide()` (the runner verdict) and the evidence auditor, so a bundle can
    never be certified from a record the oracle itself would reject. Review 0f11bb4 AH9:
    `present` alone is not enough — an "absent but counted once" record used to pass.
    """
    if not isinstance(scan, dict):
        return ['scan is not an object']
    ok = scan.get('ok')
    if type(ok) is not bool:
        return [f'scan ok must be a boolean, got {ok!r}']
    sentinels = scan.get('sentinels')
    if ok is False:
        claimed = []
        if isinstance(sentinels, dict):
            claimed = sorted(name for name, record in sentinels.items()
                             if isinstance(record, dict) and record.get('present') is not None)
        return ([f'unusable scan claims sentinel presence for {", ".join(claimed)}'] if claimed else [])
    if not isinstance(sentinels, dict) or not sentinels:
        return ['successful scan must record per-sentinel counts']
    problems = []
    for name, record in sorted(sentinels.items()):
        if not isinstance(record, dict):
            problems.append(f'sentinel {name} record is not an object')
            continue
        present = record.get('present')
        occurrences = record.get('occurrences')
        if type(present) is not bool:
            problems.append(f'sentinel {name} present must be a boolean, got {present!r}')
        if type(occurrences) is not int:
            problems.append(f'sentinel {name} occurrences must be an integer, got {occurrences!r}')
            continue
        if occurrences < 0:
            problems.append(f'sentinel {name} occurrences must not be negative, got {occurrences}')
        if type(present) is bool and present != (occurrences > 0):
            problems.append(f'sentinel {name} presence {present} contradicts occurrences {occurrences}')
    return problems


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
            for problem in scan_problems(scan_result):
                findings.append(f'{epoch}: {problem}')
            verdict_ok = False
            continue
        for problem in scan_problems(scan_result):
            findings.append(f'{epoch}: {problem}')
            verdict_ok = False
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
    nodes = '[0,0,0,0]'
    edges = '[0]'

    def snapshot(strings):
        body = ('{"snapshot":' + json.dumps(meta, separators=(',', ':'))
                + ',"nodes":' + nodes + ',"edges":' + edges + ',"traces":[]'
                + ',"strings":[' + ','.join(json.dumps(s) for s in list(strings) + ['z' * 4200]) + ']}')
        return body.encode('utf-8')

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
    # Review 57ec02c AH1: these three were certified as clean by the old marker scan.
    broken = snapshot(['SENTINEL-BANK-123', 'SENTINEL-PROBE-ALIVE']).replace(
        b'"SENTINEL-BANK-123","SENTINEL-PROBE-ALIVE"',
        b'"SENTINEL-BANK-123" "SENTINEL-PROBE-ALIVE"')
    path = write(broken)
    cases.append(('missing_separator_is_not_absent', scan(path, sentinel), None, False))
    broken = snapshot(['SENTINEL-PROBE-ALIVE']).replace(b',"nodes":', b',BROKEN,"nodes":')
    path = write(broken)
    cases.append(('garbage_before_nodes_is_not_absent', scan(path, sentinel), None, False))
    broken = snapshot(['SENTINEL-PROBE-ALIVE']).replace(b'"nodes":[0,', b'"nodes":[00,')
    path = write(broken)
    cases.append(('leading_zero_is_not_absent', scan(path, sentinel), None, False))
    broken = snapshot(['SENTINEL-PROBE-ALIVE']).replace(b'{"snapshot":', b'{"nodes":[0,0,0,0],"snapshot":')
    path = write(broken)
    cases.append(('duplicate_key_is_not_absent', scan(path, sentinel), None, False))

    failures = []
    for name, result, want_bank, want_ok in cases:
        if result['ok'] != want_ok:
            failures.append(f'{name}: ok={result["ok"]} expected {want_ok}')
        if want_bank is not None and result['sentinels']['bank']['present'] != want_bank:
            failures.append(f'{name}: bank present={result["sentinels"]["bank"]["present"]} expected {want_bank}')

    clean = {'baseline': {'ok': True, 'sentinels': {'probe': {'present': True, 'occurrences': 1},
                                                    'bank': {'present': False, 'occurrences': 0}}},
             'owner': {'ok': True, 'sentinels': {'probe': {'present': True, 'occurrences': 1},
                                                 'bank': {'present': True, 'occurrences': 1}}}}
    expectations = {'baseline': {'probe': True, 'bank': False}, 'owner': {'probe': True, 'bank': True}}
    checks = 5
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
    # Review 0f11bb4 AH9: a count that contradicts its presence is not a usable record.
    checks += 1
    contradictory = json.loads(json.dumps(clean))
    contradictory['baseline']['sentinels']['bank']['occurrences'] = 1
    if decide(contradictory, expectations, True, 'profile')['verdict'] != 'FAIL':
        failures.append('contradictory count must FAIL')

    for failure in failures:
        print(f'FAIL {failure}')
    print(f'self-test: {len(cases) + checks - len(failures)}/{len(cases) + checks} controls passed')
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
