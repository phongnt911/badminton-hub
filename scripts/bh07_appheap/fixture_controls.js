// Controls for the run-only expense fixture (review 9fadecc RP1).
//
// The measurement widens its gated set with one expense row it creates itself. That row must
// never leave the local stack, and the run must never claim a row it did not create: a
// pre-existing row with the same id is a refusal before any mutation, a DELETE is only
// issued for the row this run wrote, and "cleaned up" is only reported when a read-back by
// id proves the row is gone.
//
// The helpers live in the runner, so this harness loads that file in a VM with an in-memory
// PostgREST stub and drives every ownership path. No database, no network, no real fixture.
//
// Usage: node scripts/bh07_appheap/fixture_controls.js [--self-test]
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { createRequire } = require('node:module');

const RUNNER = path.resolve(__dirname, 'run_app_profile_heap.js');
const ENV = { API_URL: 'http://127.0.0.1:54321', SERVICE_ROLE_KEY: 'stub-only' };
const SEEDED = {
  id: '50000000-0000-4000-8000-000000000099',
  session_id: '10000000-0000-4000-8000-000000000099',
  title: 'Tiền thuê sân 2h',
  status: 'posted',
  created_by: '11111111-1111-4111-8111-111111111111',
};

function stub(table = [SEEDED], options = {}) {
  const rows = new Map(table.map((row) => [row.id, { ...row }]));
  const calls = [];
  const eq = (params, name) => {
    const raw = params.get(name);
    const match = raw && /^eq\.(.*)$/.exec(raw);
    return match ? match[1] : null;
  };
  const select = (params) => {
    let out = [...rows.values()];
    for (const name of ['id', 'session_id']) {
      const want = eq(params, name);
      if (want !== null) out = out.filter((row) => row[name] === want);
    }
    return out;
  };
  const fetch = async (url, init = {}) => {
    const method = (init.method || 'GET').toUpperCase();
    const parsed = new URL(url);
    calls.push(method);
    if (!parsed.pathname.endsWith('/session_expenses') && !parsed.pathname.endsWith('/payments') && !parsed.pathname.endsWith('/session_players')) {
      return { ok: false, status: 404, text: async () => 'unexpected table' };
    }
    if (parsed.pathname.endsWith('/session_players')) {
      return { ok: true, status: 200, json: async () => [{ user_id: '11111111-1111-4111-8111-111111111111' }] };
    }
    if (method === 'GET') return { ok: true, status: 200, json: async () => select(parsed.searchParams) };
    if (method === 'POST') {
      const body = JSON.parse(init.body);
      if (options.postRejects) {
        if (options.commitDespiteReject) for (const row of body) rows.set(row.id, { ...row });
        return { ok: false, status: 503, text: async () => 'gateway timeout' };
      }
      for (const row of body) rows.set(row.id, { ...row });
      return { ok: true, status: 201, text: async () => '' };
    }
    if (method === 'DELETE') {
      if (options.deleteRejects) return { ok: false, status: 500, text: async () => 'delete failed' };
      for (const row of select(parsed.searchParams)) rows.delete(row.id);
      return { ok: true, status: 204, text: async () => '' };
    }
    return { ok: false, status: 405, text: async () => 'method not allowed' };
  };
  return { fetch, calls, rows };
}

function loadRunner(fetchImpl) {
  const source = fs.readFileSync(RUNNER, 'utf8');
  const context = {
    require: createRequire(RUNNER), module: { exports: {} }, __dirname: path.dirname(RUNNER),
    process, console, setTimeout, clearTimeout, URL, fetch: fetchImpl,
  };
  vm.createContext(context);
  vm.runInContext(`${source}\nglobalThis.fx = { ensureExtraExpense, removeExtraExpense, `
    + 'ensureExtraPayment, removeExtraPayment, fixtureCleanupOk, EXTRA_EXPENSE, EXTRA_PAYMENT };', context);
  return context.fx;
}

const cases = [];
function control(name, body) {
  cases.push([name, body]);
}

function check(condition, message) {
  if (!condition) throw new Error(message);
}

control('collision_refused', async () => {
  const existing = { ...SEEDED, id: 'placeholder', title: 'existing independent fixture' };
  const table = stub([SEEDED]);
  const loaded = loadRunner(table.fetch);
  existing.id = loaded.EXTRA_EXPENSE.id;
  table.rows.set(existing.id, existing);
  const created = await loaded.ensureExtraExpense(ENV);
  check(created.created === false, `created=${JSON.stringify(created)}`);
  check(created.refused === 'run_only_fixture_id_exists', `refused=${created.refused}`);
  check(!table.calls.includes('POST'), 'a refused collision must not post');
  const cleanup = await loaded.removeExtraExpense(ENV);
  check(!table.calls.includes('DELETE'), 'a row this run did not create must not be deleted');
  check(cleanup.removed === false && cleanup.verified_absent === false, JSON.stringify(cleanup));
  check(table.rows.size === 2, `rows=${table.rows.size}`);
  check(loaded.fixtureCleanupOk(cleanup) === false, 'a refused collision cannot report a clean fixture');
});

control('create_then_clean', async () => {
  const table = stub();
  const fx = loadRunner(table.fetch);
  // The gated id is a substring test: a title that embeds it would be counted as retained
  // finance data through the engine's text cache (measured in this round's first run).
  check(!fx.EXTRA_EXPENSE.title.includes(fx.EXTRA_EXPENSE.id), 'the run title must not embed the gated id');
  const created = await fx.ensureExtraExpense(ENV);
  check(created.created === true, JSON.stringify(created));
  check(table.calls.filter((c) => c === 'POST').length === 1, JSON.stringify(table.calls));
  check(table.rows.size === 2, `rows=${table.rows.size}`);
  const cleanup = await fx.removeExtraExpense(ENV);
  check(cleanup.removed === true && cleanup.verified_absent === true, JSON.stringify(cleanup));
  check(table.rows.size === 1 && table.rows.has(SEEDED.id), 'only the run-only row may be deleted');
  check(fx.fixtureCleanupOk(cleanup) === true, 'ownership plus verified absence is a clean fixture');
});

control('post_rejected_row_committed', async () => {
  const table = stub([SEEDED], { postRejects: true, commitDespiteReject: true });
  const fx = loadRunner(table.fetch);
  let failed = null;
  try { await fx.ensureExtraExpense(ENV); } catch (error) { failed = error.message; }
  check(failed, 'an unanswered POST must not continue the run');
  const cleanup = await fx.removeExtraExpense(ENV);
  check(cleanup.removed === true && cleanup.verified_absent === true, JSON.stringify(cleanup));
  check(table.rows.size === 1, `the committed row must be removed, rows=${table.rows.size}`);
});

control('post_rejected_row_absent', async () => {
  const table = stub([SEEDED], { postRejects: true });
  const fx = loadRunner(table.fetch);
  let failed = null;
  try { await fx.ensureExtraExpense(ENV); } catch (error) { failed = error.message; }
  check(failed, 'a rejected POST must not continue the run');
  const cleanup = await fx.removeExtraExpense(ENV);
  check(cleanup.verified_absent === true, JSON.stringify(cleanup));
  check(fx.fixtureCleanupOk(cleanup) === true, 'nothing owned and nothing left is a clean fixture');
});

control('delete_rejected', async () => {
  const table = stub([SEEDED], { deleteRejects: true });
  const fx = loadRunner(table.fetch);
  await fx.ensureExtraExpense(ENV);
  const cleanup = await fx.removeExtraExpense(ENV);
  check(cleanup.removed === false && cleanup.verified_absent === false, JSON.stringify(cleanup));
  check(typeof cleanup.error === 'string' && cleanup.error.includes('delete failed'), JSON.stringify(cleanup));
  check(fx.fixtureCleanupOk(cleanup) === false, 'a failed cleanup cannot be reported as clean');
});

control('remote_endpoint_refused', async () => {
  const table = stub();
  const fx = loadRunner(table.fetch);
  let failed = null;
  try {
    await fx.ensureExtraExpense({ ...ENV, API_URL: 'https://project-ref.supabase.co' });
  } catch (error) { failed = error.message; }
  check(failed && failed.includes('local'), `failed=${failed}`);
  check(table.calls.length === 0, `no request may leave the machine: ${JSON.stringify(table.calls)}`);
});

control('payment_collision_refused', async () => {
  const existing = { id: 'placeholder', session_player_id: 'p1', amount_vnd: 50000, reference: 'REF-OLD' };
  const table = stub([existing]);
  const loaded = loadRunner(table.fetch);
  existing.id = loaded.EXTRA_PAYMENT.id;
  table.rows.set(existing.id, existing);
  const created = await loaded.ensureExtraPayment(ENV);
  check(created.created === false, `created=${JSON.stringify(created)}`);
  check(created.refused === 'run_only_fixture_id_exists', `refused=${created.refused}`);
  check(!table.calls.includes('POST'), 'a refused payment collision must not post');
  const cleanup = await loaded.removeExtraPayment(ENV);
  check(!table.calls.includes('DELETE'), 'a payment row this run did not create must not be deleted');
  check(cleanup.removed === false && cleanup.verified_absent === false, JSON.stringify(cleanup));
  check(loaded.fixtureCleanupOk(cleanup) === false, 'a refused payment collision cannot report a clean fixture');
});

control('payment_create_then_clean', async () => {
  const table = stub([]);
  const fx = loadRunner(table.fetch);
  const created = await fx.ensureExtraPayment(ENV);
  check(created.created === true, JSON.stringify(created));
  check(table.calls.filter((c) => c === 'POST').length === 1, JSON.stringify(table.calls));
  const cleanup = await fx.removeExtraPayment(ENV);
  check(cleanup.removed === true && cleanup.verified_absent === true, JSON.stringify(cleanup));
  check(table.rows.size === 0, 'payment row must be cleaned up');
  check(fx.fixtureCleanupOk(cleanup) === true, 'payment ownership plus verified absence is clean');
});

async function main() {
  const failures = [];
  for (const [name, body] of cases) {
    try {
      await body();
      console.log(`ok ${name}`);
    } catch (error) {
      failures.push(`${name}: ${error.message}`);
    }
  }
  console.log(`fixture controls: ${cases.length - failures.length}/${cases.length} controls passed`);
  for (const failure of failures) console.log(`FAIL ${failure}`);
  if (failures.length) process.exitCode = 1;
}

main().catch((error) => { console.error(error); process.exitCode = 1; });
