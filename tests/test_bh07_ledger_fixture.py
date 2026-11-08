"""Unit and behavior controls for DisposableLedgerFixture (fake HTTP transport).

Verifies:
1. Endpoint Protection:
   - Refuses non-local or missing API URLs on both ensure() and cleanup().
2. Preflight Collision Refusal:
   - If prospective transactionId exists, aborts with collision refusal.
   - Calling cleanup() after collision makes ZERO POSTs and ZERO DELETEs.
3. Schema Invariants (club_transactions):
   - POST sends exact columns: id, club_id, direction ('income'|'expense'), amount_vnd, title,
     source_type ('manual'), and created_by (owner anchor).
   - Rejects non-whitelisted columns (user_id, status, created_at, etc.).
4. Exact Readback on POST Success:
   - Successful POST 2xx must be verified with exact full-row readback before claiming creation.
   - If readback is missing or mismatches, helper marks creation false and throws; cleanup makes ZERO DELETEs.
5. Ambiguous POST Reconciliation:
   - If POST commits but network drops/throws, readback by ID reconciles ownership (created=True)
     and subsequent cleanup deletes and verifies absence.
6. Definite 403 Rejection & Non-Adoption:
   - If POST returns 403, helper never adopts matching row even if row appears, and cleanup never DELETEs it.
7. Delete Failure & No-Op Detection:
   - If DELETE fails or row remains after DELETE, cleanup reports verified_absent=False with error.
8. Child Lifecycle Isolation:
   - Takes clubId from existing parent DisposableBankFixture; does not POST/DELETE parent clubs.
9. No-Op DELETE when uncreated:
   - When fixture is uncreated, cleanup makes ZERO DELETEs.

Run: python -X utf8 -m unittest tests.test_bh07_ledger_fixture -v
"""
import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_HELPER = ROOT / 'scripts/bh07_appheap/disposable_ledger_fixture.js'


class TestDisposableLedgerFixture(unittest.TestCase):
    """Executes behavioral test harness against DisposableLedgerFixture with fake transport."""

    def _run_node_scenario(self, scenario_name):
        script = f"""
const path = require('node:path');
const file = path.resolve('{FIXTURE_HELPER.as_posix()}');
const {{ DisposableLedgerFixture, assertLocalEndpoint }} = require(file);

async function run() {{
  if ('{scenario_name}' === 'endpoint_guard') {{
    let threw = false;
    try {{
      assertLocalEndpoint('https://remote.supabase.co');
    }} catch (err) {{
      threw = true;
    }}
    let nullThrew = false;
    try {{
      assertLocalEndpoint(null);
    }} catch (err) {{
      nullThrew = true;
    }}
    console.log(JSON.stringify({{ ok: threw && nullThrew }}));
    return;
  }}

  if ('{scenario_name}' === 'cleanup_endpoint_guard_missing') {{
    const fixture = new DisposableLedgerFixture({{
      clubId: '11111111-2222-4333-8444-555555555555',
      transactionId: '22222222-3333-4444-8555-666666666666',
      ownerUserId: 'aaaaaaaa-0000-4000-8000-000000000001',
    }});
    let caught = false;
    try {{
      await fixture.cleanup({{ apiUrl: null }});
    }} catch (err) {{
      caught = true;
    }}
    console.log(JSON.stringify({{ ok: caught }}));
    return;
  }}

  if ('{scenario_name}' === 'cleanup_endpoint_guard_remote') {{
    const fixture = new DisposableLedgerFixture({{
      clubId: '11111111-2222-4333-8444-555555555555',
      transactionId: '22222222-3333-4444-8555-666666666666',
      ownerUserId: 'aaaaaaaa-0000-4000-8000-000000000001',
    }});
    let caught = false;
    try {{
      await fixture.cleanup({{ apiUrl: 'https://remote.supabase.co' }});
    }} catch (err) {{
      caught = true;
    }}
    console.log(JSON.stringify({{ ok: caught }}));
    return;
  }}

  const calls = [];
  const state = {{
    transactions: new Map(),
  }};

  const transport = {{
    apiUrl: 'http://127.0.0.1:54321',
    calls,
    state,
    restGet: async (query) => {{
      calls.push({{ op: 'GET', query }});
      if (query.includes('club_transactions?id=eq.')) {{
        const id = query.split('id=eq.')[1].split('&')[0];
        const row = state.transactions.get(id);
        return row ? [row] : [];
      }}
      return [];
    }},
    restWrite: async (method, table, payload) => {{
      calls.push({{ op: method, table, payload }});
      if (table.startsWith('clubs')) {{
        throw new Error('isolation violation: ledger helper must not mutate parent clubs table');
      }}
      if (method === 'POST' && table === 'club_transactions') {{
        const row = payload && payload[0];
        const allowedCols = new Set(['id', 'club_id', 'direction', 'amount_vnd', 'title', 'source_type', 'created_by']);
        for (const k of Object.keys(row)) {{
          if (!allowedCols.has(k)) throw new Error('schema violation: unexpected column ' + k);
        }}
        if (!row.id || !row.club_id || !row.direction || !row.amount_vnd || !row.created_by) {{
          throw new Error('schema violation: missing required club_transactions columns');
        }}
        if (row.source_type !== 'manual') {{
          throw new Error('schema violation: run-only fixture must have source_type manual');
        }}
        if ('{scenario_name}' === 'definite_403' || '{scenario_name}' === 'definite_403_matching_row_appears') {{
          const err = new Error('PostgREST POST club_transactions: 403 forbidden');
          err.status = 403;
          throw err;
        }}
        state.transactions.set(row.id, row);
        if ('{scenario_name}' === 'ambiguous_post_network_drop') {{
          const err = new Error('network connection reset');
          err.status = null;
          throw err;
        }}
      }} else if (method === 'DELETE' && table.startsWith('club_transactions')) {{
        if ('{scenario_name}' === 'delete_failure') {{
          throw new Error('PostgREST DELETE club_transactions: 500 internal error');
        }}
        if ('{scenario_name}' === 'delete_noop_row_remains') {{
          // Do not delete row from state
          return;
        }}
        const id = table.split('id=eq.')[1];
        state.transactions.delete(id);
      }}
    }},
  }};

  const fixture = new DisposableLedgerFixture({{
    clubId: '11111111-2222-4333-8444-555555555555',
    transactionId: '22222222-3333-4444-8555-666666666666',
    ownerUserId: 'aaaaaaaa-0000-4000-8000-000000000001',
    title: 'Fixture Ledger Thu Quy',
    amountVnd: 50000,
  }});

  if ('{scenario_name}' === 'post_success_readback_missing') {{
    transport.restGet = async (query) => {{
      calls.push({{ op: 'GET', query }});
      return [];
    }};
    let caught = false;
    try {{
      await fixture.ensure(transport);
    }} catch (err) {{
      caught = true;
    }}
    const receipt = await fixture.cleanup(transport);
    const deleteCalls = calls.filter(c => c.op === 'DELETE').length;
    console.log(JSON.stringify({{
      ok: caught && !fixture.created && deleteCalls === 0 && receipt.disposable_ledger_created === false,
      created: fixture.created,
      deleteCalls,
      receipt
    }}));
    return;
  }}

  if ('{scenario_name}' === 'post_success_readback_mismatch') {{
    let callCount = 0;
    transport.restGet = async (query) => {{
      calls.push({{ op: 'GET', query }});
      callCount++;
      if (callCount === 1) return []; // preflight collision check returns empty
      return [{{
        id: '22222222-3333-4444-8555-666666666666',
        club_id: '11111111-2222-4333-8444-555555555555',
        direction: 'income',
        amount_vnd: 50000,
        title: 'Fixture Ledger Thu Quy',
        source_type: 'manual',
        created_by: 'foreign-owner-uuid',
      }}];
    }};
    let caught = false;
    try {{
      await fixture.ensure(transport);
    }} catch (err) {{
      caught = true;
    }}
    const receipt = await fixture.cleanup(transport);
    const deleteCalls = calls.filter(c => c.op === 'DELETE').length;
    console.log(JSON.stringify({{
      ok: caught && !fixture.created && deleteCalls === 0 && receipt.disposable_ledger_created === false,
      created: fixture.created,
      deleteCalls,
      receipt
    }}));
    return;
  }}

  if ('{scenario_name}' === 'collision_then_cleanup_zero_ops') {{
    state.transactions.set('22222222-3333-4444-8555-666666666666', {{ id: '22222222-3333-4444-8555-666666666666' }});
    let caught = false;
    try {{
      await fixture.ensure(transport);
    }} catch (err) {{
      caught = true;
    }}
    const postCallsBeforeClean = calls.filter(c => c.op === 'POST').length;
    await fixture.cleanup(transport);
    const postCallsAfterClean = calls.filter(c => c.op === 'POST').length;
    const deleteCalls = calls.filter(c => c.op === 'DELETE').length;
    console.log(JSON.stringify({{
      ok: caught && postCallsAfterClean === 0 && deleteCalls === 0,
      postCalls: postCallsAfterClean,
      deleteCalls,
      refused: fixture.refused
    }}));
    return;
  }}

  if ('{scenario_name}' === 'ambiguous_post_network_drop') {{
    let caught = false;
    try {{
      await fixture.ensure(transport);
    }} catch (err) {{
      caught = true;
    }}
    const receipt = await fixture.cleanup(transport);
    console.log(JSON.stringify({{
      ok: caught && fixture.created && receipt.disposable_ledger_verified_absent,
      created: fixture.created,
      verifiedAbsent: receipt.disposable_ledger_verified_absent
    }}));
    return;
  }}

  if ('{scenario_name}' === 'definite_403') {{
    let caught = false;
    try {{
      await fixture.ensure(transport);
    }} catch (err) {{
      caught = true;
    }}
    await fixture.cleanup(transport);
    const deleteCalls = calls.filter(c => c.op === 'DELETE').length;
    console.log(JSON.stringify({{
      ok: caught && !fixture.created && deleteCalls === 0,
      created: fixture.created,
      deleteCalls
    }}));
    return;
  }}

  if ('{scenario_name}' === 'definite_403_matching_row_appears') {{
    let caught = false;
    try {{
      await fixture.ensure(transport);
    }} catch (err) {{
      caught = true;
    }}
    state.transactions.set('22222222-3333-4444-8555-666666666666', {{
      id: '22222222-3333-4444-8555-666666666666',
      club_id: '11111111-2222-4333-8444-555555555555',
      direction: 'income',
      amount_vnd: 50000,
      title: 'Fixture Ledger Thu Quy',
      source_type: 'manual',
      created_by: 'foreign-user-id'
    }});
    const receipt = await fixture.cleanup(transport);
    const deleteCalls = calls.filter(c => c.op === 'DELETE').length;
    console.log(JSON.stringify({{
      ok: caught && !fixture.created && deleteCalls === 0 && state.transactions.has('22222222-3333-4444-8555-666666666666'),
      created: fixture.created,
      deleteCalls,
      rowStillExists: state.transactions.has('22222222-3333-4444-8555-666666666666'),
      receipt
    }}));
    return;
  }}

  if ('{scenario_name}' === 'noop_delete_when_uncreated') {{
    const receipt = await fixture.cleanup(transport);
    const postCalls = calls.filter(c => c.op === 'POST').length;
    const deleteCalls = calls.filter(c => c.op === 'DELETE').length;
    console.log(JSON.stringify({{
      ok: !fixture.created && postCalls === 0 && deleteCalls === 0 && receipt.disposable_ledger_created === false,
      created: fixture.created,
      postCalls,
      deleteCalls,
      receipt
    }}));
    return;
  }}

  if ('{scenario_name}' === 'delete_failure') {{
    await fixture.ensure(transport);
    const receipt = await fixture.cleanup(transport);
    console.log(JSON.stringify({{
      ok: receipt.disposable_ledger_verified_absent === false && Boolean(receipt.disposable_ledger_error),
      receipt
    }}));
    return;
  }}

  if ('{scenario_name}' === 'delete_noop_row_remains') {{
    await fixture.ensure(transport);
    const receipt = await fixture.cleanup(transport);
    console.log(JSON.stringify({{
      ok: receipt.disposable_ledger_verified_absent === false && Boolean(receipt.disposable_ledger_error),
      receipt
    }}));
    return;
  }}

  if ('{scenario_name}' === 'exact_schema_and_child_isolation') {{
    await fixture.ensure(transport);
    const receipt = await fixture.cleanup(transport);
    const clubMutations = calls.filter(c => c.table && c.table.startsWith('clubs')).length;
    console.log(JSON.stringify({{
      ok: fixture.created && receipt.disposable_ledger_verified_absent && clubMutations === 0,
      receipt,
      clubMutations
    }}));
    return;
  }}
}}

run().catch(err => {{
  console.error(err);
  process.exit(1);
}});
"""
        proc = subprocess.run(
            ['node', '-e', script],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
            encoding='utf-8',
        )
        return proc

    def test_remote_and_missing_endpoint_refused(self):
        proc = self._run_node_scenario('endpoint_guard')
        self.assertEqual(proc.returncode, 0, f"Helper failed or missing:\n{proc.stdout}\n{proc.stderr}")
        data = json.loads(proc.stdout)
        self.assertTrue(data.get('ok'), data)

    def test_cleanup_refuses_missing_endpoint(self):
        proc = self._run_node_scenario('cleanup_endpoint_guard_missing')
        self.assertEqual(proc.returncode, 0, f"Helper failed or missing:\n{proc.stdout}\n{proc.stderr}")
        data = json.loads(proc.stdout)
        self.assertTrue(data.get('ok'), data)

    def test_cleanup_refuses_remote_endpoint(self):
        proc = self._run_node_scenario('cleanup_endpoint_guard_remote')
        self.assertEqual(proc.returncode, 0, f"Helper failed or missing:\n{proc.stdout}\n{proc.stderr}")
        data = json.loads(proc.stdout)
        self.assertTrue(data.get('ok'), data)

    def test_preflight_collision_aborts_with_zero_post_and_zero_delete(self):
        proc = self._run_node_scenario('collision_then_cleanup_zero_ops')
        self.assertEqual(proc.returncode, 0, f"Helper failed or missing:\n{proc.stdout}\n{proc.stderr}")
        data = json.loads(proc.stdout)
        self.assertTrue(data.get('ok'), data)
        self.assertEqual(data.get('postCalls'), 0)
        self.assertEqual(data.get('deleteCalls'), 0)

    def test_post_success_readback_missing_refuses_ownership(self):
        proc = self._run_node_scenario('post_success_readback_missing')
        self.assertEqual(proc.returncode, 0, f"Helper failed or missing:\n{proc.stdout}\n{proc.stderr}")
        data = json.loads(proc.stdout)
        self.assertTrue(data.get('ok'), data)
        self.assertFalse(data.get('created'))
        self.assertEqual(data.get('deleteCalls'), 0)

    def test_post_success_readback_mismatch_refuses_ownership(self):
        proc = self._run_node_scenario('post_success_readback_mismatch')
        self.assertEqual(proc.returncode, 0, f"Helper failed or missing:\n{proc.stdout}\n{proc.stderr}")
        data = json.loads(proc.stdout)
        self.assertTrue(data.get('ok'), data)
        self.assertFalse(data.get('created'))
        self.assertEqual(data.get('deleteCalls'), 0)

    def test_ambiguous_post_network_drop_reconciles_and_cleans(self):
        proc = self._run_node_scenario('ambiguous_post_network_drop')
        self.assertEqual(proc.returncode, 0, f"Helper failed or missing:\n{proc.stdout}\n{proc.stderr}")
        data = json.loads(proc.stdout)
        self.assertTrue(data.get('ok'), data)

    def test_definite_403_never_adopts_or_deletes(self):
        proc = self._run_node_scenario('definite_403')
        self.assertEqual(proc.returncode, 0, f"Helper failed or missing:\n{proc.stdout}\n{proc.stderr}")
        data = json.loads(proc.stdout)
        self.assertTrue(data.get('ok'), data)

    def test_definite_403_matching_row_appearing_is_never_adopted_or_deleted(self):
        proc = self._run_node_scenario('definite_403_matching_row_appears')
        self.assertEqual(proc.returncode, 0, f"Helper failed or missing:\n{proc.stdout}\n{proc.stderr}")
        data = json.loads(proc.stdout)
        self.assertTrue(data.get('ok'), data)
        self.assertFalse(data.get('created'))
        self.assertEqual(data.get('deleteCalls'), 0)
        self.assertTrue(data.get('rowStillExists'))

    def test_noop_delete_when_uncreated(self):
        proc = self._run_node_scenario('noop_delete_when_uncreated')
        self.assertEqual(proc.returncode, 0, f"Helper failed or missing:\n{proc.stdout}\n{proc.stderr}")
        data = json.loads(proc.stdout)
        self.assertTrue(data.get('ok'), data)
        self.assertFalse(data.get('created'))
        self.assertEqual(data.get('postCalls'), 0)
        self.assertEqual(data.get('deleteCalls'), 0)

    def test_delete_failure_reports_uncleaned(self):
        proc = self._run_node_scenario('delete_failure')
        self.assertEqual(proc.returncode, 0, f"Helper failed or missing:\n{proc.stdout}\n{proc.stderr}")
        data = json.loads(proc.stdout)
        self.assertTrue(data.get('ok'), data)

    def test_delete_noop_row_remains_reports_uncleaned(self):
        proc = self._run_node_scenario('delete_noop_row_remains')
        self.assertEqual(proc.returncode, 0, f"Helper failed or missing:\n{proc.stdout}\n{proc.stderr}")
        data = json.loads(proc.stdout)
        self.assertTrue(data.get('ok'), data)

    def test_exact_schema_and_child_isolation(self):
        proc = self._run_node_scenario('exact_schema_and_child_isolation')
        self.assertEqual(proc.returncode, 0, f"Helper failed or missing:\n{proc.stdout}\n{proc.stderr}")
        data = json.loads(proc.stdout)
        self.assertTrue(data.get('ok'), data)


if __name__ == '__main__':
    unittest.main()
