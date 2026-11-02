"""Tests for BH-07 owned browser lifecycle and profile cleanup (BKR9 round 4).

Covers:
1. Graceful exit + locked-profile retries
2. Already-exited process handling
3. Graceful hang with proc exit and cleanup result still emitted (no unref)
4. Exit timeout does NOT remove live profile
5. Removal failure returns explicit profileRemoved=False
6. Unrelated / historical profiles remain completely untouched
7. Occupied DEBUG_PORT rejects before spawn or filesystem profile mutation
8. Async ENOENT startup failure cleans own profile with no uncaught exception
9. Startup polling timeout cleans up owned proc and profile
10. Preexisting PID-derived profile directory triggers refusal and remains untouched
"""

import json
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
HELPER_PATH = (ROOT / 'scripts/bh07_appheap/owned_browser_cleanup.js').as_posix()
RUNNER_PATH = (ROOT / 'scripts/bh07_appheap/run_app_profile_heap.js').as_posix()


def run_node_eval(script_body: str, timeout_sec: float = 15.0) -> dict:
    """Execute a Node script that prints a JSON result line, returning the parsed dict."""
    cmd = ['node', '-e', script_body]
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=timeout_sec)
    if proc.returncode != 0:
        raise RuntimeError(
            f"Node process exited with {proc.returncode}\n"
            f"STDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
        )
    lines = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    if not lines:
        raise ValueError(f"No output from node script. STDERR:\n{proc.stderr}")
    return json.loads(lines[-1])


class TestOwnedBrowserCleanup(unittest.TestCase):
    def test_graceful_exit_and_locked_profile_retries(self):
        """Proc exits gracefully, profile removal retries on lock (EBUSY) and succeeds."""
        script = f"""
        const {{ EventEmitter }} = require('node:events');
        const {{ shutdownOwnedBrowser }} = require({json.dumps(HELPER_PATH)});

        (async () => {{
          const proc = new EventEmitter();
          proc.exitCode = null;
          proc.signalCode = null;
          proc.pid = 12345;

          let closeCalled = false;
          const closeBrowser = async () => {{
            closeCalled = true;
            proc.exitCode = 0;
            proc.emit('exit', 0, null);
          }};

          let attempts = 0;
          let dirExists = true;
          const fakeFs = {{
            existsSync: () => dirExists,
            rmSync: () => {{
              attempts++;
              if (attempts < 3) {{
                throw new Error('EBUSY: resource locked');
              }}
              dirExists = false;
            }}
          }};

          const res = await shutdownOwnedBrowser(
            {{ proc, userDataDir: '/mock/profile/dir', closeBrowser }},
            {{ fs: fakeFs, retryDelayMs: 10, maxRetries: 10 }}
          );

          console.log(JSON.stringify({{ ...res, attempts, closeCalled }}));
        }})();
        """
        out = run_node_eval(script)
        self.assertTrue(out['exited'])
        self.assertTrue(out['profileRemoved'])
        self.assertIsNone(out['error'])
        self.assertTrue(out['closeCalled'])
        self.assertEqual(out['attempts'], 3)

    def test_already_exited_proc(self):
        """Already-exited launcher invokes closeBrowser if present, avoids kill, and removes profile."""
        script = f"""
        const {{ EventEmitter }} = require('node:events');
        const {{ shutdownOwnedBrowser }} = require({json.dumps(HELPER_PATH)});

        (async () => {{
          const proc = new EventEmitter();
          proc.exitCode = 0;
          proc.signalCode = null;
          proc.pid = 12345;
          let killCalled = false;
          proc.kill = () => {{ killCalled = true; }};

          let closeCalled = false;
          const closeBrowser = async () => {{ closeCalled = true; }};

          let dirExists = true;
          const fakeFs = {{
            existsSync: () => dirExists,
            rmSync: () => {{ dirExists = false; }}
          }};

          const res = await shutdownOwnedBrowser(
            {{ proc, userDataDir: '/mock/profile', closeBrowser }},
            {{ fs: fakeFs }}
          );

          console.log(JSON.stringify({{ ...res, closeCalled, killCalled, dirExists }}));
        }})();
        """
        out = run_node_eval(script)
        self.assertTrue(out['exited'])
        self.assertTrue(out['profileRemoved'])
        self.assertIsNone(out['error'])
        self.assertTrue(out['closeCalled'])
        self.assertFalse(out['killCalled'])
        self.assertFalse(out['dirExists'])

    def test_exited_launcher_with_live_browser_callback_releases_locked_profile(self):
        """Exited launcher stub still invokes closeBrowser, releasing locked profile."""
        script = f"""
        const {{ EventEmitter }} = require('node:events');
        const {{ shutdownOwnedBrowser }} = require({json.dumps(HELPER_PATH)});

        (async () => {{
          // Real Windows evidence: launcher stub exited code 0, but Chrome browser is running
          const proc = new EventEmitter();
          proc.exitCode = 0;
          proc.signalCode = null;
          proc.pid = 98168;

          let browserAlive = true;
          let closeCalled = false;
          let killCalled = false;
          proc.kill = () => {{ killCalled = true; }};

          const closeBrowser = async () => {{
            closeCalled = true;
            // closeBrowser triggers CDP Browser.close so descendants release file locks
            browserAlive = false;
          }};

          let attempts = 0;
          let dirExists = true;
          const fakeFs = {{
            existsSync: () => dirExists,
            rmSync: () => {{
              attempts++;
              if (browserAlive) {{
                throw new Error('EBUSY: resource locked by Chrome descendants');
              }}
              dirExists = false;
            }}
          }};

          const res = await shutdownOwnedBrowser(
            {{ proc, userDataDir: '/mock/profile', closeBrowser }},
            {{ fs: fakeFs, retryDelayMs: 5, maxRetries: 5 }}
          );

          console.log(JSON.stringify({{ ...res, closeCalled, killCalled, dirExists, attempts }}));
        }})();
        """
        out = run_node_eval(script)
        self.assertTrue(out['exited'])
        self.assertTrue(out['profileRemoved'])
        self.assertIsNone(out['error'])
        self.assertTrue(out['closeCalled'])
        self.assertFalse(out['killCalled'])
        self.assertFalse(out['dirExists'])
        self.assertEqual(out['attempts'], 1)

    def test_graceful_hang_with_proc_exit_and_cleanup_result_emitted(self):
        """Hanging closeBrowser triggers SIGTERM fallback, proc exits, cleanup succeeds."""
        script = f"""
        const {{ EventEmitter }} = require('node:events');
        const {{ shutdownOwnedBrowser }} = require({json.dumps(HELPER_PATH)});

        (async () => {{
          const proc = new EventEmitter();
          proc.exitCode = null;
          proc.signalCode = null;
          proc.pid = 9988;

          let killedWith = null;
          proc.kill = (sig) => {{
            killedWith = sig;
            proc.exitCode = 143;
            proc.signalCode = sig;
            proc.emit('exit', 143, sig);
          }};

          const closeBrowser = () => new Promise(() => {{}});

          let dirExists = true;
          const fakeFs = {{
            existsSync: () => dirExists,
            rmSync: () => {{ dirExists = false; }}
          }};

          const res = await shutdownOwnedBrowser(
            {{ proc, userDataDir: '/mock/profile', closeBrowser }},
            {{ fs: fakeFs, timeoutMs: 50, retryDelayMs: 5 }}
          );

          console.log(JSON.stringify({{ ...res, killedWith, dirExists }}));
        }})();
        """
        out = run_node_eval(script)
        self.assertTrue(out['exited'])
        self.assertTrue(out['profileRemoved'])
        self.assertIsNone(out['error'])
        self.assertEqual(out['killedWith'], 'SIGTERM')
        self.assertFalse(out['dirExists'])

    def test_exit_timeout_does_not_rm_live_profile(self):
        """If proc fails to exit, userDataDir is NEVER removed and success is never claimed."""
        script = f"""
        const {{ EventEmitter }} = require('node:events');
        const {{ shutdownOwnedBrowser }} = require({json.dumps(HELPER_PATH)});

        (async () => {{
          const proc = new EventEmitter();
          proc.exitCode = null;
          proc.signalCode = null;
          proc.pid = 7777;
          proc.kill = () => {{}};

          let rmSyncCalled = false;
          const fakeFs = {{
            existsSync: () => true,
            rmSync: () => {{ rmSyncCalled = true; }}
          }};

          const res = await shutdownOwnedBrowser(
            {{ proc, userDataDir: '/mock/profile' }},
            {{ fs: fakeFs, timeoutMs: 50 }}
          );

          console.log(JSON.stringify({{ ...res, rmSyncCalled }}));
        }})();
        """
        out = run_node_eval(script)
        self.assertFalse(out['exited'])
        self.assertFalse(out['profileRemoved'])
        self.assertIsNotNone(out['error'])
        self.assertFalse(out['rmSyncCalled'])

    def test_rm_failure_explicit_false(self):
        """If profile removal persistently fails, returns profileRemoved=False with error."""
        script = f"""
        const {{ EventEmitter }} = require('node:events');
        const {{ shutdownOwnedBrowser }} = require({json.dumps(HELPER_PATH)});

        (async () => {{
          const proc = new EventEmitter();
          proc.exitCode = 0;
          proc.signalCode = null;

          let attempts = 0;
          const fakeFs = {{
            existsSync: () => true,
            rmSync: () => {{
              attempts++;
              throw new Error('EPERM: operation not permitted');
            }}
          }};

          const res = await shutdownOwnedBrowser(
            {{ proc, userDataDir: '/mock/locked_dir' }},
            {{ fs: fakeFs, retryDelayMs: 5, maxRetries: 3 }}
          );

          console.log(JSON.stringify({{ ...res, attempts }}));
        }})();
        """
        out = run_node_eval(script)
        self.assertTrue(out['exited'])
        self.assertFalse(out['profileRemoved'])
        self.assertIn('EPERM', str(out['error']))
        self.assertEqual(out['attempts'], 4)

    def test_unrelated_profile_untouched(self):
        """Only the exact owned profile directory is removed; unrelated profiles stay intact."""
        script = f"""
        const fs = require('node:fs');
        const path = require('node:path');
        const os = require('node:os');
        const {{ EventEmitter }} = require('node:events');
        const {{ shutdownOwnedBrowser }} = require({json.dumps(HELPER_PATH)});

        (async () => {{
          const tmpBase = fs.mkdtempSync(path.join(os.tmpdir(), 'test_bkr9_'));
          const ownDir = path.join(tmpBase, 'bh07_appheap_chrome_own');
          const unrelatedDir = path.join(tmpBase, 'bh07_appheap_chrome_99999');

          fs.mkdirSync(ownDir);
          fs.mkdirSync(unrelatedDir);
          fs.writeFileSync(path.join(unrelatedDir, 'keep_me.txt'), 'important');

          const proc = new EventEmitter();
          proc.exitCode = 0;

          const res = await shutdownOwnedBrowser({{ proc, userDataDir: ownDir }}, {{ timeoutMs: 100 }});

          const ownExists = fs.existsSync(ownDir);
          const unrelatedExists = fs.existsSync(unrelatedDir);
          const unrelatedFileExists = fs.existsSync(path.join(unrelatedDir, 'keep_me.txt'));

          fs.rmSync(tmpBase, {{ recursive: true, force: true }});

          console.log(JSON.stringify({{ ...res, ownExists, unrelatedExists, unrelatedFileExists }}));
        }})();
        """
        out = run_node_eval(script)
        self.assertTrue(out['exited'])
        self.assertTrue(out['profileRemoved'])
        self.assertFalse(out['ownExists'])
        self.assertTrue(out['unrelatedExists'])
        self.assertTrue(out['unrelatedFileExists'])

    def test_occupied_debug_port_no_spawn_or_fs_mutation(self):
        """Occupied debug port rejects immediately before profile creation or process spawn."""
        script = f"""
        const net = require('node:net');
        const path = require('node:path');
        const os = require('node:os');
        const fs = require('node:fs');
        const {{ startChromeLogged }} = require({json.dumps(RUNNER_PATH)});

        (async () => {{
          const server = net.createServer().listen(0, '127.0.0.1', async () => {{
            const occupiedPort = server.address().port;
            const logFile = path.join(os.tmpdir(), 'dummy_chrome.log');
            let rejected = false;
            let errMessage = '';
            try {{
              await startChromeLogged(logFile, {{ port: occupiedPort }});
            }} catch (e) {{
              rejected = true;
              errMessage = e.message;
            }} finally {{
              server.close();
            }}
            const expectedDir = path.join(os.tmpdir(), 'bh07_appheap_chrome_' + process.pid);
            const dirExists = fs.existsSync(expectedDir);
            console.log(JSON.stringify({{ rejected, errMessage, dirExists }}));
          }});
        }})();
        """
        out = run_node_eval(script)
        self.assertTrue(out['rejected'])
        self.assertIn('port', out['errMessage'])
        self.assertIn('refusing to reuse', out['errMessage'])
        self.assertFalse(out['dirExists'])

    def test_async_enoent_startup_cleans_own_profile_no_uncaught_error(self):
        """Async spawn error (ENOENT) is caught cleanly, cleans own profile and propagates."""
        script = f"""
        const path = require('node:path');
        const os = require('node:os');
        const fs = require('node:fs');
        const {{ startChromeLogged }} = require({json.dumps(RUNNER_PATH)});

        (async () => {{
          const logFile = path.join(os.tmpdir(), 'dummy_enoent.log');
          const bogusPath = path.join(os.tmpdir(), 'non_existent_chrome_binary_xyz123.exe');
          let rejected = false;
          let errCode = '';
          const expectedDir = path.join(os.tmpdir(), 'bh07_appheap_chrome_' + process.pid);

          try {{
            await startChromeLogged(logFile, {{ chromePath: bogusPath, port: 59336 }});
          }} catch (e) {{
            rejected = true;
            errCode = e.code || e.message;
          }}

          const dirExists = fs.existsSync(expectedDir);
          console.log(JSON.stringify({{ rejected, errCode, dirExists }}));
        }})();
        """
        out = run_node_eval(script)
        self.assertTrue(out['rejected'])
        self.assertIn('ENOENT', str(out['errCode']))
        self.assertFalse(out['dirExists'])

    def test_start_polling_timeout_cleanup(self):
        """Startup polling timeout kills spawned proc and completely cleans profile."""
        script = f"""
        const path = require('node:path');
        const os = require('node:os');
        const fs = require('node:fs');
        const {{ startChromeLogged }} = require({json.dumps(RUNNER_PATH)});

        (async () => {{
          const logFile = path.join(os.tmpdir(), 'dummy_timeout.log');
          const nodeBinary = process.execPath;
          let rejected = false;
          let errMessage = '';
          const expectedDir = path.join(os.tmpdir(), 'bh07_appheap_chrome_' + process.pid);

          try {{
            await startChromeLogged(logFile, {{
              chromePath: nodeBinary,
              port: 59337,
              maxAttempts: 3,
              pollIntervalMs: 20,
              fetchTimeoutMs: 50,
            }});
          }} catch (e) {{
            rejected = true;
            errMessage = e.message;
          }}

          const dirExists = fs.existsSync(expectedDir);
          console.log(JSON.stringify({{ rejected, errMessage, dirExists }}));
        }})();
        """
        out = run_node_eval(script)
        self.assertTrue(out['rejected'])
        self.assertIn('failed to start', out['errMessage'].lower())
        self.assertFalse(out['dirExists'])

    def test_preexisting_canary_dir_refused_and_untouched(self):
        """Preexisting PID-derived profile directory triggers immediate refusal and remains untouched."""
        script = f"""
        const path = require('node:path');
        const os = require('node:os');
        const fs = require('node:fs');
        const {{ startChromeLogged }} = require({json.dumps(RUNNER_PATH)});

        (async () => {{
          const canaryDir = path.join(os.tmpdir(), 'bh07_appheap_chrome_' + process.pid);
          fs.mkdirSync(canaryDir, {{ recursive: true }});
          const canaryFile = path.join(canaryDir, 'canary.txt');
          fs.writeFileSync(canaryFile, 'do_not_delete');

          const logFile = path.join(os.tmpdir(), 'dummy_canary.log');
          let rejected = false;
          let errMessage = '';

          try {{
            await startChromeLogged(logFile, {{ port: 59338 }});
          }} catch (e) {{
            rejected = true;
            errMessage = e.message;
          }}

          const dirExists = fs.existsSync(canaryDir);
          const fileExists = fs.existsSync(canaryFile);
          const content = fileExists ? fs.readFileSync(canaryFile, 'utf8') : '';

          // Cleanup test canary directory
          fs.rmSync(canaryDir, {{ recursive: true, force: true }});

          console.log(JSON.stringify({{ rejected, errMessage, dirExists, fileExists, content }}));
        }})();
        """
        out = run_node_eval(script)
        self.assertTrue(out['rejected'])
        self.assertIn('preexisting chrome profile directory', out['errMessage'])
        self.assertIn('refusing to overwrite', out['errMessage'])
        self.assertTrue(out['dirExists'])
        self.assertTrue(out['fileExists'])
        self.assertEqual(out['content'], 'do_not_delete')


if __name__ == '__main__':
    unittest.main()
