// Test harness for production DisposableBankFixture with fake transport.
// Covers BKR2, BKR4, BKR6: preflight collision, POST 409 rejection vs lost ack reconciliation,
// foreign row rejection, exact schema, child-first cleanup order, delete error handling.

const { DisposableBankFixture, runFixtureScenario, sha12 } = require('./disposable_bank_fixture');

function makeFakeTransport(overrides = {}) {
  const calls = [];
  const state = {
    clubs: new Map(overrides.initialClubs || []),
    members: new Map(overrides.initialMembers || []),
    bankAccounts: new Map(overrides.initialBankAccounts || []),
  };

  const transport = {
    apiUrl: 'http://127.0.0.1:54321',
    calls,
    state,
    restGet: async (query) => {
      calls.push({ op: 'GET', query });
      if (overrides.onGet) {
        const custom = overrides.onGet(query, state);
        if (custom !== undefined) return custom;
      }
      if (query.startsWith('clubs?id=eq.')) {
        const id = query.split('id=eq.')[1].split('&')[0];
        const row = state.clubs.get(id);
        return row ? [row] : [];
      }
      if (query.startsWith('club_members?id=eq.')) {
        const id = query.split('id=eq.')[1].split('&')[0];
        const row = state.members.get(id);
        return row ? [row] : [];
      }
      if (query.startsWith('club_bank_accounts?id=eq.')) {
        const id = query.split('id=eq.')[1].split('&')[0];
        const row = state.bankAccounts.get(id);
        return row ? [row] : [];
      }
      return [];
    },
    restWrite: async (method, table, payload) => {
      calls.push({ op: method, table, payload });
      if (overrides.onWrite) {
        const custom = overrides.onWrite(method, table, payload, state);
        if (custom !== undefined) return custom;
      }
      if (method === 'POST') {
        const row = (payload && payload[0]) || {};
        if (table === 'clubs') {
          // Schema verification: must use owner_user_id, not created_by
          if (!row.owner_user_id) throw new Error('schema violation: clubs requires owner_user_id');
          if (row.created_by) throw new Error('schema violation: clubs has no created_by column');
          state.clubs.set(row.id, row);
        } else if (table === 'club_members') {
          if (!row.display_name) throw new Error('schema violation: club_members requires display_name');
          state.members.set(row.id, row);
        } else if (table === 'club_bank_accounts') {
          // Schema verification: must NOT have user_id column
          if (row.user_id !== undefined) throw new Error('schema violation: club_bank_accounts has no user_id column');
          state.bankAccounts.set(row.id, row);
        }
      } else if (method === 'DELETE') {
        const id = table.split('id=eq.')[1];
        if (table.startsWith('club_bank_accounts')) state.bankAccounts.delete(id);
        else if (table.startsWith('club_members')) state.members.delete(id);
        else if (table.startsWith('clubs')) state.clubs.delete(id);
      }
    },
  };
  return transport;
}

async function runScenario(scenario) {
  const clubId = '11111111-2222-3333-4444-555555555555';
  const memberId = '22222222-3333-4444-5555-666666666666';
  const bankId = '33333333-4444-5555-6666-777777777777';
  const ownerId = 'aaaaaaaa-0000-4000-8000-000000000001';

  if (scenario === 'positive_lifecycle') {
    const transport = makeFakeTransport({
      initialClubs: [['aaaaaaaa-1111-4111-8111-111111111111', { id: 'aaaaaaaa-1111-4111-8111-111111111111', owner_user_id: ownerId }]],
    });
    const fixture = new DisposableBankFixture({ clubId, memberId, bankId, ownerUserId: ownerId });
    await fixture.ensure(transport);
    const receipt = await fixture.cleanup(transport);

    // Verify deletion sequence: bank first, then member, then club
    const deleteOps = transport.calls.filter((c) => c.op === 'DELETE').map((c) => c.table.split('?')[0]);
    return {
      ok: fixture.createdClub && fixture.createdBank && receipt.verified_absent && receipt.removed,
      receipt,
      deleteOrder: deleteOps,
    };
  }

  if (scenario === 'preexisting_club_refusal') {
    const transport = makeFakeTransport({
      initialClubs: [[clubId, { id: clubId, owner_user_id: 'other-owner', name: 'Existing' }]],
    });
    const fixture = new DisposableBankFixture({ clubId, memberId, bankId, ownerUserId: ownerId });
    let threw = false;
    try {
      await fixture.ensure(transport);
    } catch (_) {
      threw = true;
    }
    const receipt = await fixture.cleanup(transport);
    const deleteCalls = transport.calls.filter((c) => c.op === 'DELETE');
    return {
      ok: threw && fixture.refused === 'preexisting_club_id_exists' && !fixture.created && deleteCalls.length === 0,
      refused: fixture.refused,
      deleteCallsCount: deleteCalls.length,
    };
  }

  if (scenario === 'post_409_conflict_not_owned') {
    // Simulates: preflight was clean, but POST returns 409 conflict
    const transport = makeFakeTransport({
      onWrite: (method, table) => {
        if (method === 'POST' && table === 'clubs') {
          const err = new Error('duplicate key value violates unique constraint');
          err.status = 409;
          throw err;
        }
      },
    });
    const fixture = new DisposableBankFixture({ clubId, memberId, bankId, ownerUserId: ownerId });
    let threw = false;
    try {
      await fixture.ensure(transport);
    } catch (_) {
      threw = true;
    }
    const receipt = await fixture.cleanup(transport);
    const deleteCalls = transport.calls.filter((c) => c.op === 'DELETE');
    return {
      ok: threw && !fixture.createdClub && !fixture.created && deleteCalls.length === 0,
      createdClub: fixture.createdClub,
      refused: fixture.refused,
      deleteCallsCount: deleteCalls.length,
    };
  }

  if (scenario === 'lost_post_reconciled_exact') {
    // Simulates: POST committed row to DB, but network timeout occurred on response
    let postCommitted = false;
    const transport = makeFakeTransport({
      onWrite: (method, table, payload, state) => {
        if (method === 'POST' && table === 'clubs') {
          state.clubs.set(payload[0].id, payload[0]);
          postCommitted = true;
          const err = new Error('ETIMEDOUT: network response lost');
          err.status = 0;
          throw err;
        }
      },
    });
    const fixture = new DisposableBankFixture({ clubId, memberId, bankId, ownerUserId: ownerId });
    let threw = false;
    try {
      await fixture.ensure(transport);
    } catch (_) {
      threw = true;
    }
    // Readback should have matched exact ID and Owner, so createdClub is true and cleanup deletes it
    const receipt = await fixture.cleanup(transport);
    const deleteClubs = transport.calls.filter((c) => c.op === 'DELETE' && c.table.startsWith('clubs'));
    return {
      ok: threw && fixture.createdClub && deleteClubs.length === 1 && receipt.verified_absent,
      createdClub: fixture.createdClub,
      deletedCommittedRow: deleteClubs.length === 1,
      receipt,
    };
  }

  if (scenario === 'lost_post_foreign_row_rejected') {
    // Simulates: POST timed out, but readback shows a row with DIFFERENT owner (someone else inserted)
    let postAttempts = 0;
    const transport = makeFakeTransport({
      onWrite: (method, table) => {
        if (method === 'POST' && table === 'clubs') {
          postAttempts += 1;
          const err = new Error('ECONNRESET');
          err.status = 0;
          throw err;
        }
      },
      onGet: (query) => {
        // Return foreign row only AFTER POST attempt, so preflight remains empty
        if (postAttempts > 0 && query.startsWith('clubs?id=eq.' + clubId)) {
          return [{ id: clubId, owner_user_id: 'stranger-id', name: 'Foreign Club' }];
        }
      },
    });
    const fixture = new DisposableBankFixture({ clubId, memberId, bankId, ownerUserId: ownerId });
    let threw = false;
    try {
      await fixture.ensure(transport);
    } catch (_) {
      threw = true;
    }
    const receipt = await fixture.cleanup(transport);
    const deleteCalls = transport.calls.filter((c) => c.op === 'DELETE');
    return {
      ok: threw && postAttempts === 1 && !fixture.createdClub && deleteCalls.length === 0,
      postAttempts,
      createdClub: fixture.createdClub,
      deleteCallsCount: deleteCalls.length,
    };
  }

  if (scenario === 'partial_creation_cleanup') {
    // Club and Member succeed, but Bank POST fails 409
    const transport = makeFakeTransport({
      onWrite: (method, table, payload, state) => {
        if (method === 'POST' && table === 'club_bank_accounts') {
          const err = new Error('duplicate key on active bank account');
          err.status = 409;
          throw err;
        }
      },
    });
    const fixture = new DisposableBankFixture({ clubId, memberId, bankId, ownerUserId: ownerId });
    let threw = false;
    try {
      await fixture.ensure(transport);
    } catch (_) {
      threw = true;
    }
    const receipt = await fixture.cleanup(transport);
    const deletedTables = transport.calls.filter((c) => c.op === 'DELETE').map((c) => c.table.split('?')[0]);
    return {
      ok: threw && fixture.createdClub && !fixture.createdBank && receipt.verified_absent,
      deletedTables,
      receipt,
    };
  }

  if (scenario === 'delete_failure_reported') {
    let postBankCalls = 0;
    let deleteCalls = 0;
    const transport = makeFakeTransport({
      onWrite: (method, table) => {
        if (method === 'POST' && table === 'club_bank_accounts') {
          postBankCalls += 1;
        }
        if (method === 'DELETE' && table.startsWith('club_bank_accounts')) {
          deleteCalls += 1;
          throw new Error('500 internal server error on delete');
        }
      },
      onGet: (query, state) => {
        // Return row only after DELETE failure, so preflight remains empty and creation succeeds
        if (deleteCalls > 0 && query.startsWith('club_bank_accounts?id=eq.' + bankId)) {
          return [{ id: bankId }];
        }
      },
    });
    const fixture = new DisposableBankFixture({ clubId, memberId, bankId, ownerUserId: ownerId });
    await fixture.ensure(transport);
    const receipt = await fixture.cleanup(transport);
    return {
      ok: postBankCalls === 1 && deleteCalls === 1 && !receipt.removed && !receipt.verified_absent && !receipt.disposable_bank_verified_absent,
      postBankCalls,
      deleteCalls,
      receipt,
    };
  }

  throw new Error(`unknown scenario ${scenario}`);
}

if (require.main === module) {
  const scenario = process.argv[2] || 'positive_lifecycle';
  runScenario(scenario)
    .then((res) => console.log(JSON.stringify(res)))
    .catch((err) => {
      console.error(err);
      process.exit(1);
    });
}

module.exports = { runScenario };
