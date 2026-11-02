const defaultFs = require('node:fs');

function isProcExited(proc) {
  if (!proc) return true;
  return (
    (proc.exitCode !== null && proc.exitCode !== undefined) ||
    (proc.signalCode !== null && proc.signalCode !== undefined)
  );
}

function waitForProcExit(proc, timeoutMs) {
  if (!proc || isProcExited(proc)) {
    return Promise.resolve(true);
  }

  return new Promise((resolve) => {
    let resolved = false;
    let timer = null;

    const onExit = (code, signal) => {
      if (resolved) return;
      resolved = true;
      if (code !== undefined && code !== null && proc.exitCode === null) {
        proc.exitCode = code;
      }
      if (signal !== undefined && signal !== null && proc.signalCode === null) {
        proc.signalCode = signal;
      }
      cleanup();
      resolve(true);
    };

    const cleanup = () => {
      if (timer) {
        clearTimeout(timer);
        timer = null;
      }
      if (typeof proc.removeListener === 'function') {
        proc.removeListener('exit', onExit);
        proc.removeListener('close', onExit);
      }
    };

    if (typeof proc.once === 'function') {
      proc.once('exit', onExit);
      proc.once('close', onExit);
    }

    if (isProcExited(proc)) {
      cleanup();
      return resolve(true);
    }

    if (timeoutMs <= 0) {
      cleanup();
      return resolve(isProcExited(proc));
    }

    // Timers must not unref: cleanup may be the last pending work before process exit.
    timer = setTimeout(() => {
      if (resolved) return;
      resolved = true;
      cleanup();
      resolve(isProcExited(proc));
    }, timeoutMs);
  });
}

/**
 * Shuts down an owned browser process and safely cleans up its user data directory.
 *
 * @param {object} browser
 * @param {import('node:child_process').ChildProcess} [browser.proc]
 * @param {string} [browser.userDataDir]
 * @param {() => Promise<void>|void} [browser.closeBrowser]
 * @param {object} [options]
 * @param {typeof import('node:fs')} [options.fs]
 * @param {(ms: number) => Promise<void>} [options.delay]
 * @param {number} [options.timeoutMs]
 * @param {number} [options.retryDelayMs]
 * @param {number} [options.maxRetries]
 * @returns {Promise<{ exited: boolean, profileRemoved: boolean, error: string | null }>}
 */
async function shutdownOwnedBrowser(browser = {}, options = {}) {
  const fsMod = options.fs || defaultFs;
  const delay = typeof options.delay === 'function'
    ? options.delay
    : (ms) => new Promise((resolve) => setTimeout(resolve, ms));
  const timeoutMs = options.timeoutMs || 5000;
  const retryDelayMs = options.retryDelayMs || 100;
  const maxRetries = options.maxRetries ?? 30;

  const proc = browser ? browser.proc : null;
  const userDataDir = browser ? browser.userDataDir : null;
  const closeBrowser = browser ? browser.closeBrowser : null;

  let exited = isProcExited(proc);
  let closeError = null;

  // 1. Call owned closeBrowser whenever supplied (bounded), even if launcher already exited
  if (typeof closeBrowser === 'function') {
    try {
      await Promise.race([
        Promise.resolve().then(() => closeBrowser()),
        new Promise((_, reject) => {
          setTimeout(() => reject(new Error(`closeBrowser timed out after ${timeoutMs}ms`)), timeoutMs);
        }),
      ]);
    } catch (err) {
      closeError = err;
    }

    exited = isProcExited(proc);
    if (!exited && proc) {
      exited = await waitForProcExit(proc, timeoutMs);
    }
  }

  // 2. If graceful close unavailable/timed out, signal ONLY this exact proc
  if (!exited && proc) {
    try {
      if (typeof proc.kill === 'function') {
        proc.kill('SIGTERM');
      } else if (proc.pid && typeof process.kill === 'function') {
        process.kill(proc.pid, 'SIGTERM');
      }
    } catch (killErr) {
      if (killErr && killErr.code === 'ESRCH') {
        exited = true;
      }
    }

    if (!exited) {
      exited = await waitForProcExit(proc, timeoutMs);
    }

    if (!exited) {
      try {
        if (typeof proc.kill === 'function') {
          proc.kill('SIGKILL');
        } else if (proc.pid && typeof process.kill === 'function') {
          process.kill(proc.pid, 'SIGKILL');
        }
      } catch (killErr) {
        if (killErr && killErr.code === 'ESRCH') {
          exited = true;
        }
      }

      if (!exited) {
        exited = await waitForProcExit(proc, timeoutMs);
      }
    }
  }

  // 3. Proc must be confirmed exited; never remove live profile
  if (!exited) {
    const errorMsg = (closeError && closeError.message)
      || `Owned browser process ${proc && proc.pid ? proc.pid : ''} failed to exit within timeout`.trim();
    return {
      exited: false,
      profileRemoved: false,
      error: errorMsg,
    };
  }

  // 4. Retry removal of exact browser.userDataDir bounded until !existsSync
  if (!userDataDir || typeof userDataDir !== 'string') {
    return {
      exited: true,
      profileRemoved: true,
      error: null,
    };
  }

  let profileRemoved = false;
  let rmError = null;

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      if (!fsMod.existsSync(userDataDir)) {
        profileRemoved = true;
        rmError = null;
        break;
      }
      fsMod.rmSync(userDataDir, { recursive: true, force: true });
    } catch (err) {
      rmError = err;
    }

    try {
      if (!fsMod.existsSync(userDataDir)) {
        profileRemoved = true;
        rmError = null;
        break;
      }
    } catch (err) {
      rmError = err;
    }

    if (attempt < maxRetries) {
      await delay(retryDelayMs);
    }
  }

  if (!profileRemoved) {
    return {
      exited: true,
      profileRemoved: false,
      error: rmError ? (rmError.message || String(rmError)) : `Failed to remove user data dir: ${userDataDir}`,
    };
  }

  return {
    exited: true,
    profileRemoved: true,
    error: null,
  };
}

module.exports = { shutdownOwnedBrowser };
