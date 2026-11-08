// Independent reviewer: never print credentials, fixture values or captured child output.
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const crypto = require('node:crypto');
const { execFileSync, spawn, spawnSync } = require('node:child_process');
const root = process.cwd();
const hash = value => crypto.createHash('sha256').update(value).digest('hex');
const git = args => execFileSync('git', args, { cwd: root, encoding: 'utf8' }).trim();
const tables = ['clubs', 'club_members', 'club_bank_accounts', 'session_expenses', 'payments', 'club_transactions'];
const runName = process.argv.find(arg => arg.startsWith('--name='))?.slice(7) || 'ledger_heap_20261108_r1';

async function main() {
  if (!fs.existsSync(path.join(root, 'pubspec.yaml')) || !/^ledger_heap_[a-z0-9_]+$/.test(runName)) throw Error('invalid_workspace_or_name');
  const raw = execFileSync('npx', ['--no-install', 'supabase@2.121.0', 'status', '-o', 'env'],
    { cwd: root, encoding: 'utf8', shell: true, stdio: ['ignore', 'pipe', 'pipe'], timeout: 60000 });
  const env = {};
  for (const line of raw.split(/\r?\n/)) { const m = line.trim().match(/^([A-Z_]+)="(.*)"$/); if (m) env[m[1]] = m[2]; }
  if (!['http://127.0.0.1:54321', 'http://localhost:54321'].includes(env.API_URL) || !env.SERVICE_ROLE_KEY) throw Error('local_environment_unavailable');
  async function snapshot() {
    const output = {};
    for (const table of tables) {
      const res = await fetch(`${env.API_URL}/rest/v1/${table}?select=*&order=id&limit=1000`, {
        headers: { apikey: env.SERVICE_ROLE_KEY, Authorization: `Bearer ${env.SERVICE_ROLE_KEY}`, Prefer: 'count=exact' },
        signal: AbortSignal.timeout(20000) });
      if (!res.ok) throw Error(`snapshot_http_${res.status}_${table}`);
      const rows = await res.json();
      const total = Number((res.headers.get('content-range') || '').split('/')[1]);
      if (!Array.isArray(rows) || !Number.isInteger(total) || total !== rows.length) throw Error(`incomplete_snapshot_${table}`);
      output[table] = { count: rows.length, sha256: hash(JSON.stringify(rows)), id_hashes: rows.map(row => hash(String(row.id)).slice(0, 12)) };
    }
    return output;
  }
  const before = await snapshot();
  const head = git(['rev-parse', 'HEAD']);
  if (process.argv.includes('--preflight')) {
    console.log(JSON.stringify({ preflight: 'PASS', head, tables: Object.fromEntries(Object.entries(before).map(([key, value]) => [key, { count: value.count, sha256: value.sha256 }])) }));
    return;
  }
  if (git(['status', '--porcelain'])) throw Error('clean_source_required');
  const guard = require(path.join(root, 'scripts/bh07_appheap/build_guard.js'));
  await guard.assertPortFree(8088); await guard.assertPortFree(9337);
  const out = path.join(root, 'docs/reviews/bh07', `${runName}_evidence`);
  const reviewOut = path.join(root, 'build', `${runName}_independent_check.json`);
  if (fs.existsSync(out) || fs.existsSync(reviewOut)) throw Error('fresh_output_required');
  const protectedPaths = git(['ls-files', '--', 'lib', 'supabase', 'test', 'web', 'scripts', 'tests', 'pubspec.yaml', 'pubspec.lock', 'docs/reviews/bh07']).split(/\r?\n/).filter(Boolean);
  const protectedHashes = new Map(protectedPaths.map(file => [file, hash(fs.readFileSync(path.join(root, file)))]));
  const child = spawn(process.execPath, ['scripts/bh07_appheap/run_app_profile_heap.js', '--bank-coverage', '--ledger-coverage'],
    { cwd: root, env: { ...process.env, BH07_APPHEAP_EVIDENCE: out }, stdio: ['ignore', 'pipe', 'pipe'] });
  const buffers = [];
  child.stdout.on('data', chunk => buffers.push(chunk)); child.stderr.on('data', chunk => buffers.push(chunk));
  const code = await new Promise((resolve, reject) => { child.on('error', reject); child.on('close', resolve); });
  const after = await snapshot();
  const preserve = tables.every(table => before[table].count === after[table].count && before[table].sha256 === after[table].sha256);
  const summaryFile = path.join(out, 'summary.json');
  const summary = fs.existsSync(summaryFile) ? JSON.parse(fs.readFileSync(summaryFile, 'utf8')) : {};
  const audited = spawnSync('python', ['-X', 'utf8', 'scripts/bh07_appheap/verify_evidence.py', '--dir', out],
    { cwd: root, stdio: ['ignore', 'pipe', 'pipe'], timeout: 180000, maxBuffer: 8 * 1024 * 1024 });
  const auditorOutput = Buffer.concat([audited.stdout || Buffer.alloc(0), audited.stderr || Buffer.alloc(0)]);
  const headAfter = git(['rev-parse', 'HEAD']);
  const receiptAbsent = [['disposable_club_id_sha256_12', 'clubs'], ['disposable_bank_id_sha256_12', 'club_bank_accounts'], ['disposable_ledger_id_sha256_12', 'club_transactions']]
    .every(([key, table]) => summary.cleanup?.[key] && !after[table].id_hashes.includes(summary.cleanup[key]));
  const changedProtected = protectedPaths.filter(file => !fs.existsSync(path.join(root, file)) || hash(fs.readFileSync(path.join(root, file))) !== protectedHashes.get(file));
  const dumpsRemoved = !fs.existsSync(path.join(os.tmpdir(), `bh07_appheap_dumps_${child.pid}`));
  const profileRemoved = !fs.existsSync(path.join(os.tmpdir(), `bh07_appheap_chrome_${child.pid}`));
  const ledgerDeclared = summary.ledger_coverage_contract?.version === '1.0' && !!summary.sentinels?.ledger_transaction_id;
  const result = { child_exit: code, auditor_exit: audited.error ? null : audited.status,
    auditor_output_bytes: auditorOutput.length, auditor_output_sha256: hash(auditorOutput),
    status: summary.status, verdict: summary.verdict, expected_source_sha: head, head_after: headAfter, tested_source_sha: summary.tested_source_sha, ledger_declared: ledgerDeclared,
    git_dirty: summary.git_dirty, cycles: summary.cycles?.length, preexisting_rows_preserved: preserve, receipt_ids_absent: receiptAbsent,
    protected_file_count: protectedPaths.length, changed_protected_paths: changedProtected, dumps_removed: dumpsRemoved, profile_removed: profileRemoved,
    before, after, captured_output_bytes: Buffer.concat(buffers).length, captured_output_sha256: hash(Buffer.concat(buffers)) };
  fs.writeFileSync(reviewOut, JSON.stringify(result, null, 2) + '\n');
  console.log(JSON.stringify({ ...result, before: undefined, after: undefined }, null, 2));
  if (code !== 0 || audited.error || audited.status !== 0 || !ledgerDeclared || summary.cycles?.length !== 2 || headAfter !== head || !preserve || !receiptAbsent || changedProtected.length || !dumpsRemoved || !profileRemoved || summary.status !== 'RUN' || summary.verdict !== 'PASS' || summary.git_dirty !== false || summary.tested_source_sha !== head) process.exitCode = 1;
}
main().catch(error => { console.log(JSON.stringify({ reviewer_wrapper: 'FAILED', error_code: /^[a-z_0-9]+$/.test(error.message) ? error.message : 'diagnostic_withheld', error_sha256: hash(String(error.message)) })); process.exitCode = 1; });
