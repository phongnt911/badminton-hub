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
import array
import hashlib
import json
import os
import re
import sys
from collections import deque

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

# Retained-path gate: a graph answer is only meaningful if a few Owner-private finance
# values were actually gated in one cycle, not just the bank sentinel.
SHA12 = re.compile(r'[0-9a-f]{12}')
MIN_GATED_SENTINELS = 2
# Sentinel classes, declared by the runner per value:
# - `scope: finance` is the only gated scope: Owner-private money data that no other actor
#   may load. An `identity` roster id of the shared club is legitimately re-fetched by the
#   cohost, so it is published with its path and reported, never asserted absent.
# - `distinctive: false` (short digit runs) can match inside an unrelated UUID, so a hit is
#   not evidence that the Owner surface loaded the value (measured: `0000000007` only ever
#   matched the fixture UUID `...-000000000007`); those are reported but never gated.
# - `rendered: true` values are laid out as widget text, so the Flutter web engine's
#   segmentation LRU (`web_ui/lib/src/engine/text_fragmenter.dart`) keeps the string after
#   the app drops it. Retention there is a platform residual risk, not app state.
SENTINEL_SCOPES = ('finance', 'identity', 'control', 'bank')
GATED_SCOPES = ('finance',)
SENTINEL_CLASS_DEFAULTS = {'rendered': False, 'distinctive': True, 'scope': 'identity'}



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


def sentinel_class(classes, name):
    """Declared class of one sentinel, defaulting to the strictest reading.

    A value nobody classified is treated as an unrendered distinctive app-state value, so
    forgetting a declaration produces a red gate instead of a silent exemption.
    """
    given = (classes or {}).get(name)
    given = given if isinstance(given, dict) else {}
    scope = given.get('scope')
    return {
        'rendered': given.get('rendered') is True,
        'distinctive': given.get('distinctive') is not False,
        'scope': scope if scope in SENTINEL_SCOPES else SENTINEL_CLASS_DEFAULTS['scope'],
    }


def derive_expectations(scans):
    """Gating expectations derived from the scans themselves (one source of truth).

    `probe` must be live everywhere (the live control). Every other sentinel is gated only
    when it can carry the claim: it loaded while Owner was viewing, it was not already
    visible at the guest baseline (a value present before login cannot discriminate between
    "cleared" and "never loaded"), it is distinctive enough that a hit is not a substring
    coincidence, it is not rendered text (the web engine's segmentation cache keeps rendered
    strings regardless of app state), and it is Owner-private financial data.

    The last condition is the scope filter, and it is the one that keeps the gate honest:
    a roster id of the shared club is data the cohost is *authorized* to load, so a cohost
    path that re-fetches it says nothing about retention. Those values are published with
    their paths and reported, never asserted absent.
    """
    owner = (scans.get('owner_active') or {}).get('sentinels') or {}
    baseline = (scans.get('baseline') or {}).get('sentinels') or {}
    epochs = list(scans)
    expectations = {epoch: {'probe': True} for epoch in epochs}
    for name in sorted(set(owner) | set(baseline)):
        if name == 'probe':
            continue
        record = owner.get(name) if isinstance(owner.get(name), dict) else {}
        gateable = (record.get('present') is True
                    and record.get('distinctive') is True
                    and record.get('rendered') is not True
                    and record.get('scope') in GATED_SCOPES)
        seen_at_baseline = (baseline.get(name) or {}).get('present') is True
        if gateable and not seen_at_baseline:
            for epoch in epochs:
                expectations[epoch][name] = epoch == 'owner_active'
    return expectations


# --- retained paths ---------------------------------------------------------------
# A count proves the value is in the string table, not that a live object still
# references it nor which root keeps it alive. The snapshot is V8's own object graph, so
# the oracle answers that too: breadth-first from the synthetic root over strong edges,
# then walk the parent chain of every string node carrying a sentinel. Weak edges are
# not retention (V8's retained size ignores them) and are skipped, which is also the
# control that a "clean" answer cannot come from a broken graph walk.
STRING_NODE_TYPES = ('string', 'concatenated string', 'sliced string')
ROOT_KIND_BY_NAME = {
    '(GC roots)': 'gc_roots',
    '(Global handles)': 'global_handles',
    '(Bootstrapper)': 'bootstrapper',
    '(Document DOM trees)': 'document_dom_trees',
    '(Stack roots)': 'stack_roots',
    '(Handle scope)': 'handle_scope',
    '(External strings)': 'external_strings',
    '(Read-only roots)': 'read_only_roots',
    '(Debugger)': 'debugger',
    '(Shared heap)': 'shared_heap',
}
ROOT_KINDS = tuple(ROOT_KIND_BY_NAME.values()) + ('root', 'other')
MAX_PATH_NODES_PER_SENTINEL = 8
MAX_PATH_FRAMES = 24
MAX_PATH_EDGES = 4096
EDGE_LABEL_MAX = 40


def _layout(doc):
    """Field indexes of a snapshot, or the reason its layout cannot be walked."""
    meta = doc.get('snapshot') or {}
    fields = meta.get('meta') or {}
    node_fields = fields.get('node_fields')
    edge_fields = fields.get('edge_fields')
    node_types = fields.get('node_types')
    edge_types = fields.get('edge_types')
    if not isinstance(node_fields, list) or not isinstance(edge_fields, list):
        return None, 'snapshot_layout_missing_fields'
    for name in ('type', 'name', 'edge_count'):
        if name not in node_fields:
            return None, f'snapshot_node_fields_missing_{name}'
    for name in ('type', 'name_or_index', 'to_node'):
        if name not in edge_fields:
            return None, f'snapshot_edge_fields_missing_{name}'
    if not isinstance(node_types, list) or not node_types or not isinstance(node_types[0], list):
        return None, 'snapshot_node_types_missing'
    if not isinstance(edge_types, list) or not edge_types or not isinstance(edge_types[0], list):
        return None, 'snapshot_edge_types_missing'
    return {
        'node_width': len(node_fields),
        'edge_width': len(edge_fields),
        'type_i': node_fields.index('type'),
        'name_i': node_fields.index('name'),
        'count_i': node_fields.index('edge_count'),
        'etype_i': edge_fields.index('type'),
        'ename_i': edge_fields.index('name_or_index'),
        'to_i': edge_fields.index('to_node'),
        'node_type_names': node_types[0],
        'edge_type_names': edge_types[0],
    }, None


def _root_reach(doc, layout):
    """BFS from node 0 over strong edges; returns parent/parent-edge arrays.

    An edge whose target is not a node index is corruption. Silently dropping it would
    turn a damaged graph into "nothing retained", so it is reported instead.
    """
    nodes, edges, meta = doc['nodes'], doc['edges'], doc['snapshot']
    count, width, edge_width = meta['node_count'], layout['node_width'], layout['edge_width']
    count_i, to_i, etype_i = layout['count_i'], layout['to_i'], layout['etype_i']
    edge_type_names = layout['edge_type_names']
    weak = edge_type_names.index('weak') if 'weak' in edge_type_names else -1

    offsets = array.array('i', [0]) * (count + 1)
    total = 0
    for index in range(count):
        offsets[index] = total
        here = nodes[index * width + count_i]
        if not isinstance(here, int) or here < 0:
            return None, None, 'snapshot_edge_count_invalid'
        total += here
    offsets[count] = total
    if total != meta['edge_count']:
        return None, None, 'snapshot_edge_total_mismatch'

    parent = array.array('i', [-1]) * count
    parent_edge = array.array('i', [-1]) * count
    seen = bytearray(count)
    seen[0] = 1
    queue = deque([0])
    node_limit = count * width
    while queue:
        node = queue.popleft()
        for record in range(offsets[node], offsets[node + 1]):
            base = record * edge_width
            if weak >= 0 and edges[base + etype_i] == weak:
                continue
            target = edges[base + to_i]
            if not isinstance(target, int) or target < 0 or target % width or target >= node_limit:
                return None, None, 'snapshot_edge_target_invalid'
            child = target // width
            if seen[child]:
                continue
            seen[child] = 1
            parent[child] = node
            parent_edge[child] = record
            queue.append(child)
    return parent, parent_edge, None


def _chain(node, parent, parent_edge):
    """Root-to-node chain, or None when the node is not retained from the root."""
    chain = [node]
    seen = {node}
    while node != 0:
        node = parent[node]
        if node < 0 or node in seen or len(chain) > MAX_PATH_EDGES:
            return None
        seen.add(node)
        chain.append(node)
    chain.reverse()
    return chain


def _edge_frame(doc, layout, record, needles=()):
    """Edge kind plus property name only: never a string node's value.

    A property name can *be* a sentinel value: the engine's text cache keys entries by the
    text itself, which is how a rendered title shows up as `property:<title>`. Publishing
    that label would republish the value the gate is hiding, so a label carrying a sentinel
    is published as `<redacted>` and the frame stays attributive (type + edge kind).
    """
    edges, strings = doc['edges'], doc['strings']
    base = record * layout['edge_width']
    type_index = edges[base + layout['etype_i']]
    names = layout['edge_type_names']
    kind = names[type_index] if isinstance(type_index, int) and 0 <= type_index < len(names) else 'unknown'
    label = ''
    if kind in ('property', 'internal', 'shortcut'):
        raw = edges[base + layout['ename_i']]
        if isinstance(raw, int) and 0 <= raw < len(strings):
            label = strings[raw][:EDGE_LABEL_MAX]
            if any(needle in label for needle in needles if needle):
                label = '<redacted>'
    return f'{kind}:{label}' if label else kind


def _root_kind(chain, doc, layout):
    """V8 names the first-level root categories in a synthetic node; map or say other."""
    if len(chain) < 2:
        return 'root'
    node = chain[1]
    name_index = doc['nodes'][node * layout['node_width'] + layout['name_i']]
    strings = doc['strings']
    name = strings[name_index] if isinstance(name_index, int) and 0 <= name_index < len(strings) else ''
    return ROOT_KIND_BY_NAME.get(name, 'other')


def retained_paths(doc, sentinels):
    """Per sentinel: is it reachable from the root, through which edge path.

    Published frames are node types plus edge kinds/names. No string value is copied, so
    the path can be attached to the evidence bundle without leaking Owner data.
    """
    if not isinstance(sentinels, dict) or not sentinels:
        return {'error': 'no_sentinels_requested'}
    layout, error = _layout(doc)
    if error:
        return {'error': error}
    parent, parent_edge, error = _root_reach(doc, layout)
    if error:
        return {'error': error}

    strings, nodes = doc['strings'], doc['nodes']
    width, type_i, name_i = layout['node_width'], layout['type_i'], layout['name_i']
    type_names = layout['node_type_names']

    matched = {name: set() for name in sentinels}
    for string_index, value in enumerate(strings):
        for name, needle in sentinels.items():
            if needle in value:
                matched[name].add(string_index)

    targets = {name: [] for name in sentinels}
    for node_index in range(len(nodes) // width):
        base = node_index * width
        type_value = nodes[base + type_i]
        if not isinstance(type_value, int) or not (0 <= type_value < len(type_names)):
            continue
        if type_names[type_value] not in STRING_NODE_TYPES:
            continue
        name_index = nodes[base + name_i]
        for name, indexes in matched.items():
            if name_index in indexes and len(targets[name]) < MAX_PATH_NODES_PER_SENTINEL:
                targets[name].append(node_index)

    result = {}
    for name, node_indexes in targets.items():
        # Informational, never a gate: a value can legitimately be retained inside a
        # longer composed string. It only tells the reviewer whether the match is the
        # whole value (a unique fixture) or a substring (possibly a coincidence).
        exact = any(strings[index] == sentinels[name] for index in matched[name])
        chains = [chain for chain in
                  (_chain(node, parent, parent_edge) for node in node_indexes if node != 0)
                  if chain is not None]
        if not chains:
            result[name] = {'reachable': False, 'string_nodes': len(node_indexes), 'exact': exact}
            continue
        best = min(chains, key=len)
        frames = []
        for depth, node in enumerate(best):
            if depth == 0:
                frames.append('root')
                continue
            child_type = type_names[nodes[node * width + type_i]]
            frames.append(f'{_edge_frame(doc, layout, parent_edge[node], sentinels.values())} -> {child_type}')
        published = frames if len(frames) <= MAX_PATH_FRAMES else frames[:8] + ['...'] + frames[-8:]
        result[name] = {
            'reachable': True,
            'root_kind': _root_kind(best, doc, layout),
            'path_len': len(best) - 1,
            'frames': published,
            'path_sha256_12': hashlib.sha256('\n'.join(frames).encode('utf-8')).hexdigest()[:12],
            'string_nodes': len(node_indexes),
            'exact': exact,
        }
    return result


def scan(path, sentinels, with_paths=False, classes=None):
    """Validate one heap snapshot and count sentinel occurrences in its decoded strings.

    `classes` carries the per-sentinel declaration from the runner (`rendered`,
    `distinctive`, `scope`), recorded next to the count so the gate and the auditor read
    the same classification instead of guessing it from the value.
    """
    size = os.path.getsize(path)
    if size > MAX_SNAPSHOT_BYTES:
        return {
            'ok': False,
            'error': 'snapshot_too_large',
            'size_bytes': size,
            'sha256_12': None,
            'sentinels': {name: {'present': None, 'occurrences': None, **sentinel_class(classes, name)}
                          for name in sentinels},
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
        result['sentinels'] = {name: {'present': None, 'occurrences': None, **sentinel_class(classes, name)}
                               for name in sentinels}
        return result
    counts = count_sentinels(doc.get('strings') or [], sentinels)
    result['sentinels'] = {name: {'present': count > 0, 'occurrences': count, **sentinel_class(classes, name)}
                           for name, count in counts.items()}
    if with_paths:
        result['paths'] = retained_paths(doc, sentinels)
    return result


def _presence_problems(scan, require_classes=False):
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
        if require_classes:
            # The gate depends on these: an undeclared class is a schema fault, not a
            # default that quietly exempts a retained value.
            for field in ('rendered', 'distinctive'):
                if type(record.get(field)) is not bool:
                    problems.append(f'sentinel {name} {field} must be a boolean, got {record.get(field)!r}')
            if record.get('scope') not in SENTINEL_SCOPES:
                problems.append(f'sentinel {name} scope must be one of {SENTINEL_SCOPES}, '
                                f'got {record.get("scope")!r}')
    return problems


def path_problems(scan, require_paths=False):
    """Schema and fail-closed behaviour of the retained-path analysis in one scan.

    A path record is only evidence if it names a root, has a positive length, starts at
    the root and carries no value. When a bundle claims the richer measurement, a scan
    without the analysis is a problem rather than "no retention found", and every sentinel
    must declare the class the gate depends on.
    """
    if not isinstance(scan, dict):
        return ['scan is not an object']
    paths = scan.get('paths')
    if paths is None:
        return ['no retained-path analysis recorded'] if require_paths else []
    if not isinstance(paths, dict):
        return ['retained-path analysis is not an object']
    if 'error' in paths:
        return [f'retained-path analysis failed: {paths["error"]}']
    sentinels = scan.get('sentinels') if isinstance(scan.get('sentinels'), dict) else {}
    problems = []
    for name in sorted(set(paths) - set(sentinels)):
        problems.append(f'retained-path record for unclaimed sentinel {name}')
    for name in sorted(sentinels):
        record = paths.get(name)
        if not isinstance(record, dict):
            problems.append(f'sentinel {name} has no retained-path record')
            continue
        reachable = record.get('reachable')
        if type(reachable) is not bool:
            problems.append(f'sentinel {name} reachable must be a boolean, got {reachable!r}')
            continue
        if type(record.get('exact')) is not bool:
            problems.append(f'sentinel {name} exact must be a boolean, got {record.get("exact")!r}')
        if not reachable:
            if record.get('frames') or record.get('path_len') or record.get('root_kind'):
                problems.append(f'sentinel {name} is not reachable but publishes a path')
            continue
        if record.get('root_kind') not in ROOT_KINDS:
            problems.append(f'sentinel {name} has no valid root kind: {record.get("root_kind")!r}')
        length = record.get('path_len')
        if type(length) is not int or length < 1:
            problems.append(f'sentinel {name} path_len must be a positive integer, got {length!r}')
        frames = record.get('frames')
        if not isinstance(frames, list) or len(frames) < 2 or any(not isinstance(frame, str) for frame in frames):
            problems.append(f'sentinel {name} path frames are missing or not strings')
        elif frames[0] != 'root':
            problems.append(f'sentinel {name} path does not start at the root')
        if not SHA12.fullmatch(str(record.get('path_sha256_12') or '')):
            problems.append(f'sentinel {name} path lacks a valid path_sha256_12')
    return problems


def scan_problems(scan, require_paths=False):
    """Schema and count/presence consistency problems of one recorded scan.

    Shared by `decide()` (the runner verdict) and the evidence auditor, so a bundle can
    never be certified from a record the oracle itself would reject. Review 0f11bb4 AH9:
    `present` alone is not enough — an "absent but counted once" record used to pass.
    `require_paths` also demands the sentinel class, because that is what the gates use.
    """
    problems = _presence_problems(scan, require_classes=require_paths)
    problems.extend(path_problems(scan, require_paths))
    return problems


def decide(scans, expectations, cleanup_ok, mode, strict=False):
    """Turn per-epoch scans into one verdict shared by JSON, Markdown and exit code.

    A failed/incomplete scan is a hard failure, never "sentinel absent = clean".

    `strict` adds the retained-path gates of the richer bundle: a value that must be
    gone also needs no path from a GC root, a value that must be live needs one (that is
    the live control for the graph walk), and at least `MIN_GATED_SENTINELS` values — one
    of them a finance value — must be gated in one cycle so "only the bank sentinel
    loaded" cannot be reported as a clean graph.

    Two observations are published but never gate, because neither is app state:
    - `notes`: a non-distinctive sentinel (a short digit run) whose hit can be a substring
      of an unrelated value proves nothing about what the Owner surface loaded;
    - `residual_risks`: rendered text still present after logout/actor switch, kept by the
      web engine's segmentation cache rather than by an app provider.
    """
    findings = []
    notes = []
    residual_risks = []
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
        usable = scan_result.get('ok') is True
        if not usable:
            findings.append(f'{epoch}: snapshot unusable ({scan_result.get("error")})')
            verdict_ok = False
        problems = scan_problems(scan_result, strict)
        for problem in problems:
            findings.append(f'{epoch}: {problem}')
            verdict_ok = False
        if not usable:
            continue
        counted = scan_result.get('sentinels') if isinstance(scan_result.get('sentinels'), dict) else {}
        paths = scan_result.get('paths') if isinstance(scan_result.get('paths'), dict) else {}
        for sentinel, record in sorted(counted.items()):
            if not isinstance(record, dict):
                continue
            path = paths.get(sentinel) if isinstance(paths.get(sentinel), dict) else {}
            if record.get('distinctive') is False and record.get('present') is True:
                notes.append(f'{epoch}: sentinel {sentinel} is not distinctive; a hit can be a '
                             'substring of an unrelated value, so it is reported and never gated')
            if (record.get('present') is True and epoch != 'owner_active'
                    and record.get('scope') == 'identity'):
                notes.append(f'{epoch}: sentinel {sentinel} is shared-club identity data that the '
                             'current actor is authorized to fetch; it is reported with its path '
                             'and never gated')
            if record.get('rendered') is True and epoch != 'owner_active' and (
                    record.get('present') is True or path.get('reachable') is True):
                residual_risks.append({
                    'epoch': epoch, 'sentinel': sentinel,
                    'root_kind': path.get('root_kind'), 'path_len': path.get('path_len'),
                    'path_sha256_12': path.get('path_sha256_12'),
                })
        for sentinel, want_present in expected.items():
            got = (counted.get(sentinel) or {}).get('present')
            if want_present == 'either':
                continue
            if got != want_present:
                verdict_ok = False
                findings.append(
                    f'{epoch}: sentinel {sentinel} expected '
                    f'{"present" if want_present else "absent"}, got {got}')

        if not strict or 'error' in paths:
            continue
        for sentinel, want_present in expected.items():
            if want_present == 'either':
                continue
            record = paths.get(sentinel) if isinstance(paths.get(sentinel), dict) else {}
            reachable = record.get('reachable')
            if want_present is True and reachable is not True:
                verdict_ok = False
                findings.append(f'{epoch}: sentinel {sentinel} expected reachable from a GC root, got {reachable}')
            elif want_present is False and reachable is True:
                verdict_ok = False
                findings.append(f'{epoch}: sentinel {sentinel} still reachable from a GC root via '
                                f'{record.get("root_kind")} ({record.get("path_len")} edges)')

    if strict:
        gated = sorted(name for name, want in (expectations.get('owner_active') or {}).items()
                       if want is True and name != 'probe')
        if len(gated) < MIN_GATED_SENTINELS:
            verdict_ok = False
            findings.append(f'owner_active: only {len(gated)} sentinel(s) gated '
                            f'({", ".join(gated) or "none"}); the graph measurement needs at least '
                            f'{MIN_GATED_SENTINELS}')
        owner_sentinels = (scans.get('owner_active') or {}).get('sentinels') or {}
        finance = [name for name in gated
                   if (owner_sentinels.get(name) or {}).get('scope') == 'finance']
        if not finance:
            verdict_ok = False
            findings.append(f'owner_active: no finance value among the gated sentinels '
                            f'({", ".join(gated) or "none"}); the graph measurement would not cover '
                            'financial data')

    return {
        'verdict': 'PASS' if verdict_ok else 'FAIL',
        'findings': findings,
        'notes': notes,
        'residual_risks': residual_risks,
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

    def graph_body(weak_bank_edge=False, label='rootRef'):
        """Valid V8-shaped object graph: root -> (Global handles) -> object -> string."""
        meta = {
            'meta': {
                'node_fields': ['type', 'name', 'id', 'self_size', 'edge_count'],
                'node_types': [['hidden', 'synthetic', 'object', 'string'], 'string_or_number',
                               'number', 'number', 'number'],
                'edge_fields': ['type', 'name_or_index', 'to_node'],
                'edge_types': [['property', 'internal', 'weak'], 'string_or_number', 'node'],
            },
            'node_count': 5, 'edge_count': 4, 'trace_function_count': 0,
        }
        strings = ['', '(Global handles)', 'Object', 'SENTINEL-BANK-123', 'SENTINEL-PROBE-ALIVE',
                   label, 'z' * 4200]
        nodes = [1, 0, 1, 0, 1,
                 1, 1, 2, 0, 1,
                 2, 2, 3, 0, 2,
                 3, 3, 4, 0, 0,
                 3, 4, 5, 0, 0]
        bank_edge = 2 if weak_bank_edge else 0
        edges = [1, 0, 5,
                 1, 0, 10,
                 bank_edge, 5, 15,
                 0, 5, 20]
        return ('{"snapshot":' + json.dumps(meta, separators=(',', ':'))
                + ',"nodes":' + json.dumps(nodes) + ',"edges":' + json.dumps(edges)
                + ',"traces":[],"strings":[' + ','.join(json.dumps(s) for s in strings) + ']}').encode('utf-8')

    def path_record(reachable):
        if not reachable:
            return {'reachable': False, 'exact': False}
        return {'reachable': True, 'root_kind': 'global_handles', 'path_len': 3,
                'frames': ['root', 'internal:(Global handles) -> synthetic',
                           'property:_cache -> object', 'property:bankRef -> string'],
                'path_sha256_12': '0123456789ab', 'exact': True}

    # Sentinel classes as the runner declares them: the short bank digit run is not
    # distinctive, the expense ids are finance values, the roster id is identity (the
    # cohost may fetch it), the probe is the live control.
    classes = {
        'probe': {'rendered': False, 'distinctive': True, 'scope': 'control'},
        'bank': {'rendered': False, 'distinctive': False, 'scope': 'bank'},
        'expense': {'rendered': False, 'distinctive': True, 'scope': 'finance'},
        'expense2': {'rendered': False, 'distinctive': True, 'scope': 'finance'},
        'player': {'rendered': False, 'distinctive': True, 'scope': 'identity'},
    }

    def scan_record(bank_present, bank_reachable, expense_present, with_paths=True,
                    rendered=None, classes_override=None):
        table = classes_override if classes_override is not None else classes
        rendered = rendered or {}

        def record(name, present):
            declared = sentinel_class(table, name)
            declared['rendered'] = rendered.get(name, declared['rendered'])
            return {'present': present, 'occurrences': 1 if present else 0, **declared}

        result = {
            'ok': True,
            'sentinels': {
                'probe': record('probe', True),
                'bank': record('bank', bank_present),
                'expense': record('expense', expense_present),
                # Second finance value: the coverage control needs two of them, and the
                # roster id alone must never count as financial coverage.
                'expense2': record('expense2', expense_present),
                'player': record('player', expense_present),
            },
        }
        if with_paths:
            result['paths'] = {
                'probe': path_record(True),
                'bank': path_record(bank_reachable),
                'expense': path_record(expense_present),
                'expense2': path_record(expense_present),
                'player': path_record(expense_present),
            }
        return result

    checks = 0
    # Retained-path controls: the count cannot say which root holds a value, so the graph
    # walk has to find a real path, ignore weak edges, and refuse a table-only string.
    path = write(graph_body())
    graph = scan(path, sentinel, with_paths=True)
    checks += 1
    if not graph.get('ok'):
        failures.append(f'graph snapshot unusable: {graph.get("error")}')
    else:
        bank_path = graph['paths']['bank']
        if bank_path.get('reachable') is not True:
            failures.append('reachable sentinel must have a retainer path')
        if bank_path.get('root_kind') != 'global_handles':
            failures.append(f'expected a global_handles root, got {bank_path.get("root_kind")!r}')
        if not str((bank_path.get('frames') or [''])[0]) == 'root':
            failures.append('retainer path must start at the root')
        if graph['paths']['probe'].get('reachable') is not True:
            failures.append('the probe control must be reachable in the graph walk')
    checks += 1
    path = write(graph_body(weak_bank_edge=True))
    weak = scan(path, sentinel, with_paths=True)
    if weak['sentinels']['bank']['present'] is not True:
        failures.append('weak-edge control: the value is still in the string table')
    if weak['paths']['bank'].get('reachable') is not False:
        failures.append('a weak edge is not retention')
    checks += 1
    if weak['paths']['bank'].get('exact') is not True:
        failures.append('the weak-edge control still has an exact string match')

    # Measured on the real bundle: the engine's text cache keys entries by the text itself,
    # so an edge label can *be* the sentinel. The published frames must redact it.
    checks += 1
    labelled = scan(write(graph_body(label='SENTINEL-BANK-123')), sentinel, with_paths=True)
    frames = [frame for record in labelled['paths'].values()
              for frame in (record.get('frames') or [])]
    if not labelled.get('ok'):
        failures.append(f'labelled-graph snapshot unusable: {labelled.get("error")}')
    elif any('SENTINEL-BANK-123' in frame for frame in frames):
        failures.append('retained-path frames must not republish a sentinel value')
    elif not any('<redacted>' in frame for frame in frames):
        failures.append('a property label carrying a sentinel must be published as redacted')

    clean = {
        'baseline': scan_record(False, False, False),
        'owner_active': scan_record(True, True, True),
        'post_logout': scan_record(False, False, False),
    }
    expectations = derive_expectations(clean)
    checks += 1
    if decide(clean, expectations, True, 'profile', strict=True)['verdict'] != 'PASS':
        failures.append('clean retained-path scans must PASS the strict gate')
    checks += 1
    if decide(clean, expectations, True, 'profile')['verdict'] != 'PASS':
        failures.append('clean scans must PASS without the path gate')
    checks += 1
    retained = json.loads(json.dumps(clean))
    retained['post_logout'] = scan_record(False, False, True)
    if decide(retained, derive_expectations(retained), True, 'profile', strict=True)['verdict'] != 'FAIL':
        failures.append('a value still reachable after logout must FAIL')
    checks += 1
    unreachable_owner = json.loads(json.dumps(clean))
    unreachable_owner['owner_active']['paths']['expense'] = path_record(False)
    if decide(unreachable_owner, derive_expectations(unreachable_owner), True, 'profile',
              strict=True)['verdict'] != 'FAIL':
        failures.append('a gated sentinel without a path at Owner must FAIL')
    checks += 1
    missing_paths = json.loads(json.dumps(clean))
    for record in missing_paths.values():
        record.pop('paths', None)
    if decide(missing_paths, derive_expectations(missing_paths), True, 'profile',
              strict=True)['verdict'] != 'FAIL':
        failures.append('strict mode must reject a scan without retained-path analysis')
    checks += 1
    bank_only = {
        'baseline': scan_record(False, False, False),
        'owner_active': scan_record(True, True, False),
        'post_logout': scan_record(False, False, False),
    }
    if decide(bank_only, derive_expectations(bank_only), True, 'profile', strict=True)['verdict'] != 'FAIL':
        failures.append('bank-only coverage must FAIL the graph measurement')
    checks += 1
    # Measured in the real fixture: `0000000007` only ever matched the tail of
    # `10000000-0000-4000-8000-000000000007`, so a non-distinctive hit must not gate.
    coincidence = {
        'baseline': scan_record(False, False, False),
        'owner_active': scan_record(True, True, True),
        'post_logout': scan_record(False, False, False),
    }
    coincidence_verdict = decide(coincidence, derive_expectations(coincidence), True, 'profile', strict=True)
    if coincidence_verdict['verdict'] != 'PASS':
        failures.append('a non-distinctive sentinel must not be gated: '
                        f'{coincidence_verdict["verdict"]} {coincidence_verdict["findings"]}')
    if not any('not distinctive' in note for note in coincidence_verdict['notes']):
        failures.append('a non-distinctive hit must be reported as a note')
    checks += 1
    # Rendered text stays in the web engine's segmentation cache: reported, not gated.
    rendered = {
        'baseline': scan_record(False, False, False),
        'owner_active': scan_record(False, False, True),
        'post_logout': scan_record(False, False, True, rendered={'expense': True}),
    }
    rendered[ 'owner_active'] = scan_record(False, False, True, rendered={'expense': True})
    rendered_verdict = decide(rendered, derive_expectations(rendered), True, 'profile', strict=True)
    if rendered_verdict['verdict'] != 'FAIL':
        failures.append('rendered text alone leaves too little gated coverage: must FAIL')
    checks += 1
    with_id = {
        'baseline': scan_record(False, False, False, rendered={'expense': True}),
        'owner_active': scan_record(False, False, True, rendered={'expense': True}),
        'post_logout': scan_record(False, False, True, rendered={'expense': True}),
    }

    def add_sentinel(scans, name, declared, present_epochs):
        for epoch, scan in scans.items():
            scan['sentinels'][name] = {
                'present': epoch in present_epochs,
                'occurrences': 1 if epoch in present_epochs else 0,
                **sentinel_class({name: declared}, name)}
            scan['paths'][name] = path_record(epoch in present_epochs)

    # One unrendered finance id plus the identity id already in the record: two gateable
    # values, so the gate has a clean case with a rendered title still retained.
    add_sentinel(with_id, 'expense_id', {'scope': 'finance'}, {'owner_active'})
    add_sentinel(with_id, 'player', {'scope': 'identity'}, {'owner_active'})
    # The rendered title is the only thing still around after logout; the second finance id
    # must be gone, otherwise it is a real retention finding instead of a cache residual.
    add_sentinel(with_id, 'expense2', {'scope': 'finance'}, {'owner_active'})
    gate_with_id = decide(with_id, derive_expectations(with_id), True, 'profile', strict=True)
    if gate_with_id['verdict'] != 'PASS':
        failures.append('two unrendered gated ids plus a rendered title must PASS: '
                        f'{gate_with_id["verdict"]} {gate_with_id["findings"]}')
    if [risk['epoch'] for risk in gate_with_id['residual_risks']] != ['post_logout']:
        failures.append('retained rendered text must be published as a residual risk: '
                        f'{gate_with_id["residual_risks"]}')
    checks += 1
    no_finance = json.loads(json.dumps(with_id))
    for epoch in no_finance:
        no_finance[epoch]['sentinels']['expense_id']['scope'] = 'identity'
        no_finance[epoch]['sentinels']['expense2']['scope'] = 'identity'
    no_finance_verdict = decide(no_finance, derive_expectations(no_finance), True, 'profile', strict=True)
    if no_finance_verdict['verdict'] != 'FAIL':
        failures.append('a gated set without a finance value must FAIL')
    checks += 1
    # Measured in the real cohost cycle: the roster id is reachable again after the switch
    # because the cohost surface fetches the same shared-club list. Gating it would assert
    # something false, so it must be reported (with its path) and never fail the run.
    identity_retained = json.loads(json.dumps(with_id))
    post = identity_retained['post_actor'] = scan_record(False, False, False)
    add_sentinel(identity_retained, 'expense_id', {'scope': 'finance'}, {'owner_active'})
    post['sentinels']['player'] = {'present': True, 'occurrences': 1,
                                   **sentinel_class(classes, 'player')}
    post['paths']['player'] = path_record(True)
    identity_verdict = decide(identity_retained, derive_expectations(identity_retained), True,
                              'profile', strict=True)
    if identity_verdict['verdict'] != 'PASS':
        failures.append('an identity value an authorized actor re-fetches must not gate: '
                        f'{identity_verdict["verdict"]} {identity_verdict["findings"]}')
    if not any('authorized' in note for note in identity_verdict['notes']):
        failures.append('a re-fetched identity value must be reported as a note')
    checks += 1
    unclassified = json.loads(json.dumps(with_id))
    unclassified['post_logout']['sentinels']['expense_id'].pop('scope')
    if decide(unclassified, derive_expectations(unclassified), True, 'profile', strict=True)['verdict'] != 'FAIL':
        failures.append('strict mode must reject a sentinel without a declared class')
    checks += 1
    dead_probe = json.loads(json.dumps(clean))
    dead_probe['baseline']['paths']['probe'] = path_record(False)
    if decide(dead_probe, derive_expectations(dead_probe), True, 'profile', strict=True)['verdict'] != 'FAIL':
        failures.append('a probe without a retainer path means the graph walk is broken: must FAIL')
    checks += 1
    no_exact = json.loads(json.dumps(clean))
    no_exact['owner_active']['paths']['bank']['exact'] = 'yes'
    if decide(no_exact, derive_expectations(no_exact), True, 'profile', strict=True)['verdict'] != 'FAIL':
        failures.append('the exact flag must be a real boolean, not a truthy string')

    checks += 1
    leaked = json.loads(json.dumps(clean))
    leaked['baseline']['sentinels']['bank']['present'] = True
    if decide(leaked, expectations, True, 'profile')['verdict'] != 'FAIL':
        failures.append('leaked baseline must FAIL')
    checks += 1
    broken = json.loads(json.dumps(clean))
    broken['owner_active']['ok'] = False
    if decide(broken, expectations, True, 'profile')['verdict'] != 'FAIL':
        failures.append('unusable snapshot must FAIL')
    checks += 1
    if decide(clean, expectations, False, 'profile')['verdict'] != 'FAIL':
        failures.append('unverified cleanup must FAIL')
    checks += 1
    if decide(clean, expectations, True, 'debug')['verdict'] != 'FAIL':
        failures.append('non-profile build must FAIL')
    checks += 1
    # Review 0f11bb4 AH9: a count that contradicts its presence is not a usable record.
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
    p_scan.add_argument('--classes', help='per-sentinel rendered/distinctive/scope declarations')
    p_scan.add_argument('--paths', action='store_true',
                        help='also walk the retainer graph from the GC root')
    p_scan.add_argument('--out')

    p_decide = sub.add_parser('decide')
    p_decide.add_argument('--scans', required=True)
    p_decide.add_argument('--expectations', required=True)
    p_decide.add_argument('--cleanup-ok', required=True, choices=['true', 'false'])
    p_decide.add_argument('--mode', required=True)
    p_decide.add_argument('--require-paths', action='store_true',
                          help='gate on retained paths and minimum finance coverage')
    p_decide.add_argument('--out')

    sub.add_parser('self-test')

    p_expect = sub.add_parser('expectations')
    p_expect.add_argument('--scans', required=True)
    p_expect.add_argument('--out')

    args = parser.parse_args(argv)
    if args.cmd == 'self-test':
        return self_test()

    if args.cmd == 'scan':
        with open(args.sentinels, encoding='utf-8') as fp:
            sentinels = json.load(fp)
        classes = None
        if args.classes:
            with open(args.classes, encoding='utf-8') as fp:
                classes = json.load(fp)
        result = scan(args.snapshot, sentinels, with_paths=args.paths, classes=classes)
        payload = json.dumps(result, ensure_ascii=False, indent=2)
        if args.out:
            with open(args.out, 'w', encoding='utf-8', newline='\n') as fp:
                fp.write(payload + '\n')
        print(payload)
        return 0 if result['ok'] else 2

    with open(args.scans, encoding='utf-8') as fp:
        scans = json.load(fp)
    if args.cmd == 'expectations':
        payload = json.dumps(derive_expectations(scans), ensure_ascii=False, indent=2)
        if args.out:
            with open(args.out, 'w', encoding='utf-8', newline='\n') as fp:
                fp.write(payload + '\n')
        print(payload)
        return 0
    with open(args.expectations, encoding='utf-8') as fp:
        expectations = json.load(fp)
    verdict = decide(scans, expectations, args.cleanup_ok == 'true', args.mode,
                     strict=args.require_paths)
    payload = json.dumps(verdict, ensure_ascii=False, indent=2)
    if args.out:
        with open(args.out, 'w', encoding='utf-8', newline='\n') as fp:
            fp.write(payload + '\n')
    print(payload)
    return 0 if verdict['verdict'] == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
