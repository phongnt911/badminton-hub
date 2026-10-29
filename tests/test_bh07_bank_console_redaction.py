"""Unit test for console and publication redaction on bank coverage failure.

Embedded probe based on reviewer fault-injection probe (.tmp/bank_console_probe.cjs).
Verifies that when a POST error occurs during disposable bank fixture creation,
raw bank account number and receiver name are:
1. Registered in RAW_SENTINEL_VALUES before the POST attempt.
2. Attempted to POST.
3. NEVER leaked to console lines (stdout/stderr).
4. NEVER leaked into published artifacts (summary/log/report).

Uses fake FS and HTTP fetch mocks (no real DB, no live browser/CDP).
"""

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

BANK_CONSOLE_PROBE_JS = r"""
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { createRequire } = require('node:module');

const file = path.resolve('scripts/bh07_appheap/run_app_profile_heap.js');
const requireLocal = createRequire(file);
const files = new Map(), dirs = new Set(), clubs = new Map(), members = new Map();
let number = '', name = '';
const consoleLines = [];
const fakeFs = {
  ...fs,
  mkdirSync(p) { dirs.add(String(p)); },
  writeFileSync(p, data) { files.set(String(p), Buffer.from(data)); },
  readFileSync(p, ...args) {
    if (files.has(String(p))) return args[0] === 'utf8' ? files.get(String(p)).toString('utf8') : files.get(String(p));
    return fs.readFileSync(p, ...args);
  },
  existsSync(p) { return files.has(String(p)) || dirs.has(String(p)); },
  readdirSync() { return []; },
  rmSync(p) { dirs.delete(String(p)); },
};
const env = { API_URL: 'http://127.0.0.1:54321', SERVICE_ROLE_KEY: 'synthetic-test-value' };
const context = vm.createContext({
  module: { exports: {} },
  __dirname: path.dirname(file),
  __filename: file,
  process: {
    ...process,
    argv: [process.execPath, file, '--bank-coverage'],
    env: { BH07_APPHEAP_EVIDENCE: path.resolve('build/fake-bank-probe-output') },
  },
  console: {
    log(...args) { consoleLines.push(args.join(' ')); },
    error(...args) { consoleLines.push(args.join(' ')); },
  },
  Buffer,
  URL,
  setTimeout,
  clearTimeout,
  require(id) {
    if (id === 'node:fs') return fakeFs;
    if (id === 'node:child_process') return {
      execFileSync: (cmd, args) => (cmd === 'git' && args[0] === 'rev-parse' ? 'a'.repeat(40) : ''),
      spawn() { throw new Error('unexpected spawn'); },
    };
    return requireLocal(id);
  },
  fetch: async (url, options = {}) => {
    const parsed = new URL(url);
    const table = parsed.pathname.split('/').pop();
    const id = (parsed.searchParams.get('id') || '').replace(/^eq\./, '');
    if (options.method === 'POST') {
      const row = JSON.parse(options.body)[0];
      if (table === 'clubs') clubs.set(row.id, row);
      if (table === 'club_members') members.set(row.id, row);
      if (table === 'club_bank_accounts') {
        number = row.account_number;
        name = row.account_name;
        return { ok: false, status: 400, text: async () => `invalid bank row ${number} ${name}` };
      }
      return { ok: true };
    }
    if (options.method === 'DELETE') {
      clubs.delete(id);
      members.delete(id);
      return { ok: true };
    }
    let rows = [];
    if (table === 'clubs' && parsed.searchParams.get('select') === 'owner_user_id') rows = [{ owner_user_id: 'test-owner' }];
    else if (table === 'clubs') rows = clubs.has(id) ? [clubs.get(id)] : [];
    else if (table === 'club_members') rows = members.has(id) ? [members.get(id)] : [];
    else if (table === 'club_bank_accounts' && parsed.searchParams.has('club_id')) rows = [{ account_number: 'old-control', account_name: 'old-control-name' }];
    return { ok: true, json: async () => rows };
  },
});
vm.runInContext(fs.readFileSync(file, 'utf8') + '\nmodule.exports.probeMain = main;', context, { filename: file });
context.probeEnv = env;
vm.runInContext(`
supabaseEnv = () => probeEnv;
ensureExtraExpense = async () => {};
ensureExtraPayment = async () => {};
removeExtraExpense = async () => ({ id: 'expense', created: true, removed: true, verified_absent: true });
removeExtraPayment = async () => ({ id: 'payment', created: true, removed: true, verified_absent: true });
`, context);
context.module.exports.probeMain().then(() => {
  const payload = [...files.values()].map((b) => b.toString('utf8')).join('\n');
  console.log(JSON.stringify({
    bank_post_attempted: !!number,
    raw_number_in_console: !!number && consoleLines.join('\n').includes(number),
    raw_name_in_console: !!name && consoleLines.join('\n').includes(name),
    raw_number_in_publication: !!number && payload.includes(number),
    raw_name_in_publication: !!name && payload.includes(name),
    raw_values_registered_before_error: Object.keys(context.module.exports.RAW_SENTINEL_VALUES).includes('bank'),
  }, null, 2));
}).catch((error) => {
  console.error(error.message);
  process.exitCode = 1;
});
"""


class TestBankConsoleRedaction(unittest.TestCase):
    """Test suite ensuring console and publication redaction on injected bank POST failure."""

    def test_bank_console_redaction_probe(self):
        """Run the embedded fake-failure probe and assert all contract booleans."""
        proc = subprocess.run(
            ['node', '-'],
            input=BANK_CONSOLE_PROBE_JS,
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            encoding='utf-8',
        )
        if proc.returncode != 0 and not proc.stdout.strip():
            # Fallback using a temporary file if stdin pipe differs
            with tempfile.NamedTemporaryFile('w', suffix='.cjs', delete=False, encoding='utf-8') as tf:
                tf.write(BANK_CONSOLE_PROBE_JS)
                tf_path = tf.name
            try:
                proc = subprocess.run(
                    ['node', tf_path],
                    cwd=str(ROOT),
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                )
            finally:
                Path(tf_path).unlink(missing_ok=True)

        self.assertEqual(
            proc.returncode, 0,
            f"Probe process exited with code {proc.returncode}.\nStderr: {proc.stderr}\nStdout: {proc.stdout}"
        )

        data = json.loads(proc.stdout.strip())

        # Assert contract booleans
        self.assertTrue(data['bank_post_attempted'], "bank_post_attempted must be true")
        self.assertFalse(data['raw_number_in_console'], "raw_number_in_console must be false")
        self.assertFalse(data['raw_name_in_console'], "raw_name_in_console must be false")
        self.assertFalse(data['raw_number_in_publication'], "raw_number_in_publication must be false")
        self.assertFalse(data['raw_name_in_publication'], "raw_name_in_publication must be false")
        self.assertTrue(data['raw_values_registered_before_error'], "raw_values_registered_before_error must be true")


if __name__ == '__main__':
    unittest.main()
