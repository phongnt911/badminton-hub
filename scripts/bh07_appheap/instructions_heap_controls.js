const assert = require('node:assert/strict');
const { EventEmitter } = require('node:events');
const fs = require('node:fs');
const http = require('node:http');
const os = require('node:os');
const path = require('node:path');
const crypto = require('node:crypto');

const runner = require('./run_payment_instructions_heap');

async function runControls() {
  const results = [];
  const check = async (name, fn) => {
    try {
      await fn();
      results.push({ name, ok: true });
      console.log(`ok ${name}`);
    } catch (err) {
      results.push({ name, ok: false, error: err.stack || err.message });
      console.error(`FAIL ${name}: ${err.message}`);
    }
  };

  await check('config_rejects_non_loopback_or_wrong_container_and_bad_dumps_cap', async () => {
    assert.throws(() => runner.validateConfig({
      supabase_url: 'https://remote.supabase.co',
      db_container: 'bh07-android-db',
    }), /loopback/i);
    assert.throws(() => runner.validateConfig({
      supabase_url: 'http://127.0.0.1:54322',
      db_container: 'bh07-android-db',
    }), /54321/);
    assert.throws(() => runner.validateConfig({
      supabase_url: 'http://127.0.0.1:54321',
      db_container: 'wrong-container',
    }), /bh07-android-db/);
    assert.throws(() => runner.validateConfig({
      supabase_url: 'http://127.0.0.1:54321',
      db_container: 'bh07-android-db',
      dumps_dir: path.resolve(__dirname, 'dumps_inside_repo'),
    }), /outside/i);

    const existingTmp = fs.mkdtempSync(path.join(os.tmpdir(), 'bh07_instr_preexist_'));
    const childFile = path.join(existingTmp, 'valuable.txt');
    fs.writeFileSync(childFile, 'keep-me');
    try {
      // IH1: Reject preexisting target, filesystem root, repo ancestor, symlink/junction target, bad cap
      assert.throws(() => runner.validateConfig({
        supabase_url: 'http://127.0.0.1:54321',
        db_container: 'bh07-android-db',
        dumps_dir: existingTmp,
      }), /exist/i);
      const juncLink = path.join(existingTmp, 'junc_alias');
      const juncReal = path.join(existingTmp, 'junc_real');
      fs.mkdirSync(juncReal);
      fs.writeFileSync(path.join(juncReal, 'precious.txt'), 'safe');
      fs.symlinkSync(juncReal, juncLink, 'junction');
      assert.throws(() => runner.claimDumpsDirectory(path.join(juncLink, 'child')), /symlink|junction/i);
      assert.equal(fs.readFileSync(path.join(juncReal, 'precious.txt'), 'utf8'), 'safe');
      assert.throws(() => runner.validateConfig({
        supabase_url: 'http://127.0.0.1:54321',
        db_container: 'bh07-android-db',
        dumps_dir: path.parse(os.tmpdir()).root,
      }), /root|ancestor/i);
      assert.throws(() => runner.validateConfig({
        supabase_url: 'http://127.0.0.1:54321',
        db_container: 'bh07-android-db',
        dumps_dir: path.resolve(__dirname, '../../..'),
      }), /root|ancestor|outside/i);
      for (const badCap of [0, -1, 1.5, NaN, Infinity, '1024', 512 * 1024 * 1024 + 1]) {
        assert.throws(() => runner.validateConfig({
          supabase_url: 'http://127.0.0.1:54321',
          db_container: 'bh07-android-db',
          max_snapshot_bytes: badCap,
        }), /max_snapshot_bytes|safe integer|cap/i);
      }
      assert.equal(fs.readFileSync(childFile, 'utf8'), 'keep-me');
    } finally {
      fs.rmSync(existingTmp, { recursive: true, force: true });
    }
  });

  await check('canary_never_in_evaluate_or_insert_text', async () => {
    const s1 = crypto.randomUUID();
    const s2 = crypto.randomUUID();
    assert.throws(() => runner.assertNoCanaryInEvaluate(`window.x = "${s1}"`, { canary_instr_a: s1, canary_instr_b: s2 }), /canary/i);
    assert.throws(() => runner.assertNoCanaryInEvaluate(`prefix-${s2.slice(0, 22)}`, { canary_instr_a: s1, canary_instr_b: s2 }), /canary/i);
    assert.doesNotThrow(() => runner.assertNoCanaryInEvaluate('performance.timeOrigin', { canary_instr_a: s1, canary_instr_b: s2 }));
  });

  await check('served_build_verification_full_match_and_mismatch', async () => {
    const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'bh07_instr_build_'));
    try {
      fs.writeFileSync(path.join(tmp, 'index.html'), '<html>ok</html>');
      fs.writeFileSync(path.join(tmp, 'main.dart.js'), 'console.log("profile");');
      const hashes = runner.hashArtifacts(tmp);
      const server = http.createServer((req, res) => {
        const rel = req.url.replace(/^\//, '') || 'index.html';
        const fp = path.join(tmp, rel);
        if (!fs.existsSync(fp)) {
          res.writeHead(404);
          res.end();
          return;
        }
        res.writeHead(200);
        res.end(fs.readFileSync(fp));
      });
      await new Promise((r) => server.listen(0, '127.0.0.1', r));
      const port = server.address().port;
      try {
        const verified = await runner.verifyServedBuild({
          webUrl: `http://127.0.0.1:${port}`,
          buildDir: tmp,
          provenance: { mode: 'profile', artifacts: hashes, tested_source_sha: 'a'.repeat(40) },
        });
        assert.equal(verified.served_match, true);

      await assert.rejects(() => runner.verifyServedBuild({
        webUrl: `http://127.0.0.1:${port}`,
        buildDir: tmp,
        provenance: { mode: 'debug', artifacts: hashes, tested_source_sha: 'a'.repeat(40) },
      }), /profile/i);

        await assert.rejects(() => runner.verifyServedBuild({
          webUrl: `http://127.0.0.1:${port}`,
          buildDir: tmp,
          provenance: { mode: 'profile', artifacts: { ...hashes, 'main.dart.js': '0'.repeat(64) }, tested_source_sha: 'a'.repeat(40) },
        }), /mismatch|hash/i);
      } finally {
        await new Promise((r) => server.close(r));
      }
    } finally {
      fs.rmSync(tmp, { recursive: true, force: true });
    }
  });

  await check('snapshot_streaming_outside_repo_cap_and_write_error', async () => {
    const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'bh07_instr_snap_'));
    const unhandled = [];
    const onUnhandled = (err) => unhandled.push(err);
    process.on('unhandledRejection', onUnhandled);
    try {
      const makeMockCdp = (chunks, { finishedBeforeChunks = false, hangCommand = false } = {}) => {
        const cdp = {
          ws: { onmessage: () => {} },
          async send(method) {
            if (method === 'HeapProfiler.takeHeapSnapshot') {
              if (hangCommand) {
                setImmediate(() => {
                  for (const c of chunks) {
                    cdp.ws.onmessage({ data: JSON.stringify({ method: 'HeapProfiler.addHeapSnapshotChunk', params: { chunk: c } }) });
                  }
                });
                return new Promise(() => {});
              }
              await new Promise((resolve) => setImmediate(() => {
                if (finishedBeforeChunks) {
                  cdp.ws.onmessage({ data: JSON.stringify({ method: 'HeapProfiler.reportHeapSnapshotProgress', params: { finished: true } }) });
                }
                for (const c of chunks) {
                  cdp.ws.onmessage({ data: JSON.stringify({ method: 'HeapProfiler.addHeapSnapshotChunk', params: { chunk: c } }) });
                }
                if (!finishedBeforeChunks) {
                  cdp.ws.onmessage({ data: JSON.stringify({ method: 'HeapProfiler.reportHeapSnapshotProgress', params: { finished: true } }) });
                }
                resolve();
              }));
            }
            return { result: {} };
          },
        };
        return cdp;
      };

      const okFile = path.join(tmp, 'ok.heapsnapshot');
      const okRes = await runner.streamSnapshotToFile({
        cdp: makeMockCdp(['{"snapshot":', '{}', '}']),
        outFile: okFile,
        maxBytes: 1024,
      });
      assert.equal(okRes.bytes, Buffer.byteLength('{"snapshot":{}}'));
      assert.equal(fs.readFileSync(okFile, 'utf8'), '{"snapshot":{}}');

      // IH2: reportHeapSnapshotProgress(finished:true) arrives BEFORE chunks -> all bytes preserved until command completes
      const orderFile = path.join(tmp, 'ordered.heapsnapshot');
      const orderRes = await runner.streamSnapshotToFile({
        cdp: makeMockCdp(['{"snapshot":', '{"meta":1}', '}'], { finishedBeforeChunks: true }),
        outFile: orderFile,
        maxBytes: 1024,
      });
      assert.equal(orderRes.bytes, Buffer.byteLength('{"snapshot":{"meta":1}}'));
      assert.equal(fs.readFileSync(orderFile, 'utf8'), '{"snapshot":{"meta":1}}');

      // IH1: Refuses preexisting target file (exclusive creation)
      await assert.rejects(() => runner.streamSnapshotToFile({
        cdp: makeMockCdp(['{}']),
        outFile: okFile,
        maxBytes: 1024,
      }), /EEXIST|exist|exclusive/i);

      // IH1 & IH2: Cap exceeded cleans up and rejects immediately even if command stalls, no unhandledRejection
      const capFile = path.join(tmp, 'cap.heapsnapshot');
      await assert.rejects(() => runner.streamSnapshotToFile({
        cdp: makeMockCdp(['123456', '789012'], { hangCommand: true }),
        outFile: capFile,
        maxBytes: 8,
        timeoutMs: 5000,
      }), /snapshot_cap_exceeded/);
      assert.equal(fs.existsSync(capFile), false);

      // IH2: Sync write error cleans up partial file cleanly without hanging
      const errFile = path.join(tmp, 'err.heapsnapshot');
      const failingFs = {
        ...fs,
        openSync: () => 999,
        writeSync: () => { throw new Error('ENOSPC'); },
        closeSync: () => {},
      };
      await assert.rejects(() => runner.streamSnapshotToFile({
        cdp: makeMockCdp(['abc'], { hangCommand: true }),
        outFile: errFile,
        maxBytes: 1024,
        fsMod: failingFs,
        timeoutMs: 5000,
      }), /snapshot_write_error/);
      assert.equal(fs.existsSync(errFile), false);

      await assert.rejects(() => runner.streamSnapshotToFile({
        cdp: makeMockCdp(['abc']),
        outFile: path.resolve(__dirname, 'inside.heapsnapshot'),
        maxBytes: 1024,
      }), /outside/i);

      // IH1: Owned dumps dir claim vs existing tree preservation
      const preexisting = path.join(tmp, 'preexisting_dir');
      fs.mkdirSync(preexisting);
      fs.writeFileSync(path.join(preexisting, 'keep.txt'), 'precious');
      assert.throws(() => runner.claimDumpsDirectory(preexisting), /exist/i);
      assert.throws(() => runner.deleteOwnedDumpsDirectory({ dir: preexisting, canonical_path: fs.realpathSync(preexisting), token: 'bad', tokenFile: path.join(preexisting, '.bh07_owned_dumps_dir.json') }), /token|owned/i);
      assert.equal(fs.readFileSync(path.join(preexisting, 'keep.txt'), 'utf8'), 'precious');

      const ownedPath = path.join(tmp, 'fresh_owned_dumps');
      const claim = runner.claimDumpsDirectory(ownedPath);
      assert.equal(fs.existsSync(claim.tokenFile), true);
      const delRes = runner.deleteOwnedDumpsDirectory(claim);
      assert.equal(delRes.removed, true);
      assert.equal(fs.existsSync(ownedPath), false);

      await new Promise((r) => setImmediate(r));
      assert.equal(unhandled.length, 0);
    } finally {
      process.off('unhandledRejection', onUnhandled);
      fs.rmSync(tmp, { recursive: true, force: true });
    }
  });

  await check('owner_precondition_and_attribution_and_raw_leak', async () => {
    const goodScan = {
      ok: true,
      sentinels: { canary_instr_a: { present: true }, canary_instr_b: { present: true } },
      paths: {
        canary_instr_a: { reachable: true, root_kind: 'global_handles', path_len: 3, frames: ['root', 'property:a -> object', 'property:canary_instr_a -> string'], path_sha256_12: 'a'.repeat(12) },
        canary_instr_b: { reachable: true, root_kind: 'global_handles', path_len: 3, frames: ['root', 'property:b -> object', 'property:canary_instr_b -> string'], path_sha256_12: 'b'.repeat(12) },
      },
    };
    assert.equal(runner.checkOwnerPrecondition(goodScan).ok, true);
    const badScan = JSON.parse(JSON.stringify(goodScan));
    badScan.paths.canary_instr_b.reachable = false;
    assert.equal(runner.checkOwnerPrecondition(badScan).ok, false);

    const attr = runner.assessPathAttribution([
      { cycle: 1, epochs: { owner_active: goodScan } },
      { cycle: 2, epochs: { owner_active: goodScan } },
    ]);
    assert.equal(attr.root_reachability_measured, true);
    assert.equal(attr.dto_attribution_proven, false);
    assert.equal(attr.claim_scope, 'narrow_rpc_payload_retention_only');
    assert.equal(attr.scoped_verdict, 'PASS_NARROW_RPC_PAYLOAD_ONLY');

    const rawS1 = crypto.randomUUID();
    const leaks = runner.findSentinelLeaks([`leaky ${rawS1}`], { canary_instr_a: rawS1 });
    assert.deepEqual(leaks, ['canary_instr_a']);

    // IH4: Negative controls - XHR buffer, single marker, non-property edge, reverse chain, unsourced fragment, truncated
    const badChains = [
      ['root', 'internal:(Global handles) -> synthetic', 'property:XMLHttpRequest -> object', 'property:responseText receiverSnapshot -> string'],
      ['root', 'internal:(Global handles) -> synthetic', 'property:receiverSnapshot -> object', 'property:canary_instr_a -> string'],
      ['root', 'internal:(Global handles) -> synthetic', 'internal:_finance_provider$_instructions -> object', 'property:receiverSnapshot -> object', 'property:canary_instr_a -> string'],
      ['root', 'internal:(Global handles) -> synthetic', 'property:receiverSnapshot -> object', 'property:_finance_provider$_instructions -> object', 'property:canary_instr_a -> string'],
      ['root', 'internal:(Global handles) -> synthetic', 'property:_instructions -> object', 'property:receiverSnapshot -> object', 'property:canary_instr_a -> string'],
      ['root', 'internal:(Global handles) -> synthetic', 'property:FinanceProvider -> object', 'property:PaymentInstructions -> object', 'property:receiverSnapshot -> string'],
      ['root', '...', 'property:_finance_provider$_instructions -> object', 'property:receiverSnapshot -> object', 'property:canary_instr_a -> string'],
    ];
    for (const badFrames of badChains) {
      const badAttrScan = JSON.parse(JSON.stringify(goodScan));
      badAttrScan.paths.canary_instr_a.frames = badFrames;
      badAttrScan.paths.canary_instr_b.frames = badFrames;
      const resBad = runner.assessPathAttribution([
        { cycle: 1, epochs: { owner_active: badAttrScan } },
        { cycle: 2, epochs: { owner_active: badAttrScan } },
      ]);
      assert.equal(resBad.dto_attribution_proven, false, `must reject chain: ${badFrames.join(' | ')}`);
      assert.equal(resBad.payment_instructions_coverage_gate, 'UNKNOWN/NOT_RUN');
      assert.equal(resBad.scoped_verdict, 'PASS_NARROW_RPC_PAYLOAD_ONLY');
    }

    // IH4: Positive control - source-bound ordered property chain through receiverSnapshot map to canary string
    const appScan = JSON.parse(JSON.stringify(goodScan));
    appScan.paths.canary_instr_a.frames = [
      'root',
      'internal:(Global handles) -> synthetic',
      'property:closure -> object',
      'property:_finance_provider$_instructions -> object',
      'property:receiverSnapshot -> object',
      'property:_map -> object',
      'property:canary_instr_a -> string',
    ];
    appScan.paths.canary_instr_b.frames = [
      'root',
      'internal:(Global handles) -> synthetic',
      'property:_finance_provider$_instructions -> object',
      'property:receiverSnapshot -> object',
      'element:3 -> string',
    ];
    const attrApp = runner.assessPathAttribution([
      { cycle: 1, epochs: { owner_active: appScan } },
      { cycle: 2, epochs: { owner_active: appScan } },
    ]);
    assert.equal(attrApp.dto_attribution_proven, true);
    assert.equal(attrApp.payment_instructions_coverage_gate, 'PASS');
    assert.equal(attrApp.scoped_verdict, 'PASS_DTO_ATTRIBUTED');

    // IH5: Recovery state stays outside dumpsDir and is preserved if DB cleanup fails while dumps are deleted
    const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'bh07_instr_recov_'));
    try {
      const stateFile = path.join(tmp, 'recovery_state.json');
      fs.writeFileSync(stateFile, JSON.stringify({ session_id: 's1', insert_attempted: true }), { mode: 0o600 });
      const ownedDump = runner.claimDumpsDirectory(path.join(tmp, 'owned_dumps'));
      fs.writeFileSync(path.join(ownedDump.dir, 'c1.heapsnapshot'), '{}');

      const kept = runner.finalizeRunResources({
        dumpsClaim: ownedDump,
        statePath: stateFile,
        fixtureCleanupVerified: false,
      });
      assert.equal(kept.dumpsRemoved, true);
      assert.equal(fs.existsSync(ownedDump.dir), false);
      assert.equal(kept.recoveryStateRetained, true);
      assert.equal(fs.existsSync(stateFile), true);

      const cleaned = runner.finalizeRunResources({
        dumpsClaim: null,
        statePath: stateFile,
        fixtureCleanupVerified: true,
      });
      assert.equal(cleaned.recoveryStateRetained, false);
      assert.equal(fs.existsSync(stateFile), false);
    } finally {
      fs.rmSync(tmp, { recursive: true, force: true });
    }
  });

  await check('ih5_cleanup_unlink_failure_vs_db_failure', async () => {
    const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'bh07_instr_ih5_'));
    try {
      // Subcase A: DB cleanup succeeds, state unlink fails -> cleanup.ok MUST be false, state exists, raw dumps deleted
      const stateA = path.join(tmp, 'state_a.json');
      const canarySecret = crypto.randomUUID();
      fs.writeFileSync(stateA, JSON.stringify({ sentinel_1: canarySecret }), { mode: 0o600 });
      const dumpsA = runner.claimDumpsDirectory(path.join(tmp, 'dumps_a'));
      fs.writeFileSync(path.join(dumpsA.dir, 'c1.heapsnapshot'), '{}');

      const failingUnlinkFs = {
        existsSync: (p) => fs.existsSync(p),
        unlinkSync: () => { const e = new Error('EPERM: operation not permitted'); e.code = 'EPERM'; throw e; },
      };
      const resA = runner.finalizeRunResources({
        dumpsClaim: dumpsA,
        statePath: stateA,
        fixtureCleanupVerified: true,
        fsMod: failingUnlinkFs,
      });
      assert.equal(resA.dumpsRemoved, true);
      assert.equal(fs.existsSync(dumpsA.dir), false);
      assert.equal(resA.recoveryStateRetained, true);
      assert.match(resA.recoveryStateError || '', /EPERM/);
      assert.equal(fs.existsSync(stateA), true);

      const cleanupA = runner.buildCleanupSummary({
        fixtureReceipt: {
          disposable_instructions_cleanup_verified: true,
          zero_mutation_verified: true,
          baseline_fingerprint_equal: true,
        },
        resourceResult: resA,
        browserCleanupOk: true,
      });
      assert.equal(cleanupA.dumps_dir_removed, true);
      assert.equal(cleanupA.raw_snapshots_remaining, 0);
      assert.equal(cleanupA.recovery_state_retained, true);
      assert.equal(cleanupA.ok, false);
      assert.equal(JSON.stringify(cleanupA).includes(canarySecret), false);

      // Subcase B: DB cleanup fails -> recovery state retained, dumps removed, cleanup.ok false
      const stateB = path.join(tmp, 'state_b.json');
      fs.writeFileSync(stateB, JSON.stringify({ sentinel_1: canarySecret }), { mode: 0o600 });
      const dumpsB = runner.claimDumpsDirectory(path.join(tmp, 'dumps_b'));
      fs.writeFileSync(path.join(dumpsB.dir, 'c1.heapsnapshot'), '{}');
      const resB = runner.finalizeRunResources({
        dumpsClaim: dumpsB,
        statePath: stateB,
        fixtureCleanupVerified: false,
      });
      assert.equal(resB.dumpsRemoved, true);
      assert.equal(fs.existsSync(dumpsB.dir), false);
      assert.equal(resB.recoveryStateRetained, true);
      assert.equal(fs.existsSync(stateB), true);
      const cleanupB = runner.buildCleanupSummary({
        fixtureReceipt: {
          disposable_instructions_cleanup_verified: false,
          zero_mutation_verified: false,
          baseline_fingerprint_equal: false,
        },
        resourceResult: resB,
        browserCleanupOk: true,
      });
      assert.equal(cleanupB.ok, false);
    } finally {
      fs.rmSync(tmp, { recursive: true, force: true });
    }
  });

  await check('run_measurement_post_cycles_failure_and_partial_cycle_evidence', async () => {
    const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'bh07_instr_run_'));
    const makeScan = (ownerPresent = false) => ({
      ok: true,
      size_bytes: 4096,
      sha256_12: 'deadbeef1234',
      sentinels: {
        probe: { present: true, occurrences: 1, rendered: false, distinctive: true, scope: 'control' },
        canary_instr_a: { present: ownerPresent, occurrences: ownerPresent ? 1 : 0, rendered: false, distinctive: true, scope: 'finance' },
        canary_instr_b: { present: ownerPresent, occurrences: ownerPresent ? 1 : 0, rendered: false, distinctive: true, scope: 'finance' },
      },
      paths: {
        probe: { reachable: true, root_kind: 'global_handles', path_len: 2, frames: ['root', 'property:probe -> string'], path_sha256_12: '1'.repeat(12) },
        canary_instr_a: ownerPresent
          ? { reachable: true, root_kind: 'global_handles', path_len: 3, frames: ['root', 'property:a -> object', 'property:canary_instr_a -> string'], path_sha256_12: 'a'.repeat(12) }
          : { reachable: false },
        canary_instr_b: ownerPresent
          ? { reachable: true, root_kind: 'global_handles', path_len: 3, frames: ['root', 'property:b -> object', 'property:canary_instr_b -> string'], path_sha256_12: 'b'.repeat(12) }
          : { reachable: false },
      },
    });
    const makeDeps = (stateFile, s1, s2, extraHooks = {}) => ({
      getGitProvenance: () => ({ tested_source_sha: 'a'.repeat(40), git_dirty: false }),
      prepareBuild: async () => ({ mode: 'profile', reused: true, explicit_provenance_verified: true, started_at: '2026-11-13T08:00:00.000Z', artifacts: { 'index.html': '1'.repeat(64), 'main.dart.js': '2'.repeat(64) }, served_match: true }),
      createFixture: () => {
        fs.writeFileSync(stateFile, JSON.stringify({ sentinel_1: s1, sentinel_2: s2, session_id: 's1' }), { mode: 0o600 });
        return { session_title: 'BH07 Instr Session test' };
      },
      checkFixtureZeroMutations: () => ({ ok: true, counts: { payments: 0, club_transactions: 0, audit_events: 0, operation_requests: 0 } }),
      cleanupFixture: () => {
        if (fs.existsSync(stateFile)) fs.unlinkSync(stateFile);
        return {
          disposable_instructions_club_created: true,
          disposable_instructions_session_created: true,
          disposable_instructions_removed: true,
          disposable_instructions_verified_absent: true,
          disposable_instructions_cleanup_verified: true,
          zero_mutation_verified: true,
          baseline_fingerprint_equal: true,
          public_rows_schema_roles_equal: true,
          auth_rows_excluded: true,
        };
      },
      startSession: async () => ({ browser: { userDataDir: path.join(tmp, 'nonexistent_chrome_profile') }, cdp: { close: async () => {} } }),
      waitForStartupReady: async () => {},
      measureTimeOrigin: async () => 54321.5,
      performEpochAction: async () => {},
      scanEpoch: async ({ epName }) => makeScan(epName === 'owner_active'),
      decideCycleVerdict: async () => ({ verdict: 'PASS', findings: [], notes: [], residual_risks: [], epochs_checked: 4 }),
      shutdownBrowser: async () => ({ exited: true, profileRemoved: true }),
      ...extraHooks,
    });

    try {
      // Subcase A: Failure AFTER both cycles complete, BEFORE attribution -> writes FAIL summary + cleanup, NO ReferenceError
      const s1 = crypto.randomUUID();
      const s2 = crypto.randomUUID();
      const outA = path.join(tmp, 'out_a');
      const stateA = path.join(tmp, 'state_a.json');
      const dumpsA = path.join(tmp, 'dumps_a');
      const cfgA = runner.validateConfig({
        supabase_url: 'http://127.0.0.1:54321',
        db_container: 'bh07-android-db',
        dumps_dir: dumpsA,
        state_path: stateA,
        reuse_existing_server: true,
        provenance: { mode: 'profile', artifacts: {} },
      });
      const resA = await runner.runMeasurement({
        cfg: cfgA,
        cfgPath: path.join(tmp, 'cfg_a.json'),
        outDir: outA,
        hooks: makeDeps(stateA, s1, s2, {
          beforeAttribution: async () => { throw new Error('simulated post-cycle failure before attribution'); },
        }),
      });
      assert.equal(resA.exitCode, 1);
      assert.equal(resA.summary.status, 'FAIL');
      assert.equal(resA.summary.verdict, 'FAIL');
      assert.equal(resA.summary.cleanup.ok, true);
      assert.equal(resA.summary.same_document_across_cycles, true);
      assert.equal(resA.summary.cycles.length, 2);
      assert.equal(resA.summary.attribution_assessment.scoped_verdict, 'FAIL');
      assert.equal(fs.existsSync(path.join(outA, 'summary.json')), true);
      assert.equal(fs.existsSync(dumpsA), false);

      // Subcase B: Early failure mid-cycle after baseline + owner_active -> preserves partial epochs + sanitized stage, remains FAIL
      const outB = path.join(tmp, 'out_b');
      const stateB = path.join(tmp, 'state_b.json');
      const dumpsB = path.join(tmp, 'dumps_b');
      const cfgB = runner.validateConfig({
        supabase_url: 'http://127.0.0.1:54321',
        db_container: 'bh07-android-db',
        dumps_dir: dumpsB,
        state_path: stateB,
        reuse_existing_server: true,
        provenance: { mode: 'profile', artifacts: {} },
      });
      const resB = await runner.runMeasurement({
        cfg: cfgB,
        cfgPath: path.join(tmp, 'cfg_b.json'),
        outDir: outB,
        hooks: makeDeps(stateB, s1, s2, {
          performEpochAction: async ({ epName }) => {
            if (epName === 'post_logout') {
              throw new Error(`simulated logout timeout leaking ${s1}`);
            }
          },
        }),
      });
      assert.equal(resB.exitCode, 1);
      assert.equal(resB.summary.status, 'FAIL');
      assert.equal(resB.summary.verdict, 'FAIL');
      assert.equal(resB.summary.same_document_across_cycles, false);
      assert.equal(resB.summary.attribution_assessment.scoped_verdict, 'FAIL');
      assert.equal(resB.summary.cycles.length, 1);
      assert.equal(resB.summary.cycles[0].actor, 'cohost');
      assert.ok(resB.summary.cycles[0].epochs.baseline);
      assert.ok(resB.summary.cycles[0].epochs.owner_active);
      assert.equal(resB.summary.cycles[0].epochs.post_logout, undefined);
      assert.equal(resB.summary.cycles[0].verdict.verdict, 'FAIL');
      assert.equal(resB.summary.cycles[0].verdict.incomplete, true);
      assert.equal(resB.summary.failure.stage, 'owner_logout');
      assert.equal(resB.summary.failure.epoch, 'post_logout');
      const writtenSummary = fs.readFileSync(path.join(outB, 'summary.json'), 'utf8');
      assert.equal(writtenSummary.includes(s1), false);
      assert.equal(writtenSummary.includes(s2), false);
    } finally {
      fs.rmSync(tmp, { recursive: true, force: true });
    }
  });

  await check('startup_semantics_placeholder_prewait', async () => {
    let calls = 0;
    let enabledCalls = 0;
    let waitSemanticCalls = 0;
    const mockCdp = {
      async evaluate(expr) {
        calls += 1;
        if (expr.includes('flt-semantics-placeholder')) {
          return calls >= 3;
        }
        return true;
      },
      async enableFlutterSemantics() {
        enabledCalls += 1;
      },
      async waitForSemantic(predicate, desc) {
        waitSemanticCalls += 1;
        assert.equal(predicate({ text: 'Bạn đang xem dưới dạng khách', aria: '' }), true);
        assert.match(desc, /Guest baseline/i);
      },
    };
    await runner.waitForStartupAndGuestBaseline(mockCdp, { canary_instr_a: 'a'.repeat(36) }, {
      placeholderTimeoutMs: 2000,
      pollMs: 10,
      guestTimeoutMs: 2000,
    });
    assert.equal(calls, 3);
    assert.equal(enabledCalls, 1);
    assert.equal(waitSemanticCalls, 1);

    const neverReadyCdp = {
      async evaluate() { return false; },
      async enableFlutterSemantics() {},
      async waitForSemantic() { throw new Error('should not reach waitForSemantic'); },
    };
    await assert.rejects(() => runner.waitForStartupAndGuestBaseline(neverReadyCdp, {}, {
      placeholderTimeoutMs: 50,
      pollMs: 10,
      guestTimeoutMs: 50,
    }), /semantics placeholder/i);
  });

  const failed = results.filter((r) => !r.ok);
  console.log(`controls: ${results.length - failed.length}/${results.length} passed`);
  if (failed.length > 0) process.exitCode = 1;
}

runControls().catch((err) => {
  console.error(err.stack || err.message);
  process.exitCode = 1;
});
