// BH-07 V2b: build/serve provenance guards for the app-profile heap run (review AH5).
//
// A profile heap measurement is only evidence if the bytes Chrome loaded are the bytes
// this run just built. These checks refuse a missing or stale artifact, a port another
// server already answers on, and a server that answers with different bytes.
const crypto = require('node:crypto');
const fs = require('node:fs');
const http = require('node:http');
const net = require('node:net');
const os = require('node:os');
const path = require('node:path');

const KEY_FILES = ['index.html', 'main.dart.js'];

function hashFile(file) {
  return crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
}

function listArtifacts(dir) {
  const found = [];
  const walk = (current) => {
    for (const entry of fs.readdirSync(current, { withFileTypes: true })) {
      const full = path.join(current, entry.name);
      if (entry.isDirectory()) walk(full);
      else found.push(path.relative(dir, full).split(path.sep).join('/'));
    }
  };
  walk(dir);
  return found.sort();
}

function hashArtifacts(dir) {
  return Object.fromEntries(listArtifacts(dir).map((name) => [name, hashFile(path.join(dir, name))]));
}

function snapshotArtifacts(dir) {
  return Object.fromEntries(KEY_FILES
    .filter((name) => fs.existsSync(path.join(dir, name)))
    .map((name) => [name, hashFile(path.join(dir, name))]));
}

// Fresh mtime proves the build wrote the file; identical bytes to the pre-build hash
// prove the rebuild produced this exact artifact even if Flutter skipped the write.
function assertArtifactsFresh(dir, startedAt, before = {}) {
  for (const name of KEY_FILES) {
    const file = path.join(dir, name);
    if (!fs.existsSync(file)) throw new Error(`build artifact missing: ${name}`);
    const fresh = fs.statSync(file).mtimeMs >= startedAt - 2000;
    if (!fresh && before[name] !== hashFile(file)) {
      throw new Error(`build artifact not produced by this run: ${name}`);
    }
  }
  return true;
}

// A connect test, not a bind test: on Windows a second bind can succeed while the old
// server keeps the socket, and the run would then measure someone else's build.
async function assertPortFree(port) {
  const occupied = await new Promise((resolve) => {
    const socket = net.connect({ port, host: '127.0.0.1' });
    socket.setTimeout(500);
    socket.once('connect', () => { socket.destroy(); resolve(true); });
    socket.once('error', () => { socket.destroy(); resolve(false); });
    socket.once('timeout', () => { socket.destroy(); resolve(false); });
  });
  if (occupied) throw new Error(`port ${port} is already answering, refusing to reuse another server`);
  return true;
}

async function assertServedMatches(baseUrl, dir) {
  for (const name of KEY_FILES) {
    const res = await fetch(`${baseUrl}/${name}`);
    if (!res.ok) throw new Error(`served ${name}: HTTP ${res.status}`);
    const served = crypto.createHash('sha256').update(Buffer.from(await res.arrayBuffer())).digest('hex');
    const local = hashFile(path.join(dir, name));
    if (served !== local) {
      throw new Error(`served ${name} does not match the built artifact (${served.slice(0, 12)} != ${local.slice(0, 12)})`);
    }
  }
  return true;
}

function serveDir(dir) {
  return http.createServer((req, res) => {
    const name = req.url.replace(/^\//, '') || 'index.html';
    const file = path.join(dir, name);
    if (!fs.existsSync(file)) { res.writeHead(404); res.end(); return; }
    res.writeHead(200);
    res.end(fs.readFileSync(file));
  });
}

const listen = (server) => new Promise((resolve) => server.listen(0, '127.0.0.1', () => resolve(server.address().port)));
const close = (server) => new Promise((resolve) => server.close(resolve));

async function selfTest() {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'bh07_build_guard_'));
  const buildDir = path.join(tmp, 'build');
  const otherDir = path.join(tmp, 'other');
  for (const dir of [buildDir, otherDir]) fs.mkdirSync(dir, { recursive: true });
  for (const name of KEY_FILES) fs.writeFileSync(path.join(otherDir, name), `different ${name}`);

  const controls = [];
  const record = (name, ok, detail) => controls.push({ name, ok, detail });
  const expectThrow = async (name, fn, needle) => {
    try {
      await fn();
      record(name, false, 'did not fail');
    } catch (error) {
      record(name, !needle || error.message.includes(needle), error.message);
    }
  };
  const expectPass = async (name, fn) => {
    try {
      await fn();
      record(name, true, 'accepted');
    } catch (error) {
      record(name, false, error.message);
    }
  };

  await expectThrow('missing_artifact', () => assertArtifactsFresh(buildDir, Date.now()), 'missing');

  const old = Date.now() - 3600 * 1000;
  for (const name of KEY_FILES) {
    fs.writeFileSync(path.join(buildDir, name), `old ${name}`);
    fs.utimesSync(path.join(buildDir, name), old / 1000, old / 1000);
  }
  await expectThrow('stale_artifact', () => assertArtifactsFresh(buildDir, Date.now()), 'not produced by this run');

  const before = snapshotArtifacts(buildDir);
  await expectPass('rebuilt_identical_artifact', () => assertArtifactsFresh(buildDir, Date.now(), before));

  const startedAt = Date.now();
  for (const name of KEY_FILES) fs.writeFileSync(path.join(buildDir, name), `fresh ${name}`);
  await expectPass('fresh_artifact', () => assertArtifactsFresh(buildDir, startedAt));

  const same = serveDir(buildDir);
  const samePort = await listen(same);
  await expectPass('served_match', () => assertServedMatches(`http://127.0.0.1:${samePort}`, buildDir));

  const different = serveDir(otherDir);
  const differentPort = await listen(different);
  await expectThrow('served_mismatch',
    () => assertServedMatches(`http://127.0.0.1:${differentPort}`, buildDir), 'does not match');

  await expectThrow('occupied_port', () => assertPortFree(samePort), 'already');

  const spare = serveDir(otherDir);
  const sparePort = await listen(spare);
  await close(spare);
  await expectPass('free_port', () => assertPortFree(sparePort));

  await close(same);
  await close(different);
  fs.rmSync(tmp, { recursive: true, force: true });

  for (const control of controls) console.log(`${control.ok ? 'ok' : 'FAIL'} ${control.name}: ${control.detail}`);
  const failed = controls.filter((control) => !control.ok).length;
  console.log(`self-test: ${controls.length - failed}/${controls.length} controls passed`);
  return failed === 0 ? 0 : 1;
}

module.exports = { hashArtifacts, snapshotArtifacts, assertArtifactsFresh, assertPortFree, assertServedMatches };

if (require.main === module) {
  if (process.argv.includes('--self-test')) {
    selfTest().then((code) => { process.exitCode = code; }, (error) => {
      console.error(error.stack || error.message);
      process.exitCode = 1;
    });
  } else {
    console.error('usage: node build_guard.js --self-test');
    process.exitCode = 2;
  }
}
