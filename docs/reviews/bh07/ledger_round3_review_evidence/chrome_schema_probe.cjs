// Reviewer diagnostic only: fresh about:blank Chrome, no app, credentials or DB.
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const crypto = require('node:crypto');
const {spawnSync} = require('node:child_process');
const root = path.resolve(__dirname, '../../../..');
const {startChromeLogged, extractScanDiagnostic} = require(path.join(root, 'scripts/bh07_appheap/run_app_profile_heap.js'));
const {shutdownOwnedBrowser} = require(path.join(root, 'scripts/bh07_appheap/owned_browser_cleanup.js'));
const {CdpClient} = require(path.join(root, 'scripts/bh07_browser/run_browser_verification.js'));
async function main() {
  const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'bh07_reviewer_schema_'));
  let browser, cdp;
  const result = {surface:'fresh Chrome about:blank', app_runtime:false, db_access:false};
  try {
    browser = await startChromeLogged(path.join(temp, 'chrome.log'), {port:9338});
    result.chrome = browser.version.Browser;
    result.v8 = browser.version['V8-Version'];
    cdp = new CdpClient(browser.version.webSocketDebuggerUrl);
    await cdp.connect();
    await cdp.createTab('about:blank');
    const chunks = [];
    const original = cdp.ws.onmessage;
    cdp.ws.onmessage = event => {
      original(event);
      const message = JSON.parse(event.data);
      if (message.method === 'HeapProfiler.addHeapSnapshotChunk') chunks.push(message.params.chunk);
    };
    const send = async (method, params) => {
      let timer;
      try { return await Promise.race([cdp.send(method, params), new Promise((_, reject) => {timer=setTimeout(()=>reject(Error('cdp_timeout')),30000);})]); }
      finally {clearTimeout(timer);}
    };
    await send('HeapProfiler.enable');
    await send('HeapProfiler.takeHeapSnapshot', {reportProgress:false});
    const bytes = chunks.join('');
    result.snapshot_bytes = Buffer.byteLength(bytes);
    result.snapshot_sha256 = crypto.createHash('sha256').update(bytes).digest('hex');
    result.top_level_keys = Object.keys(JSON.parse(bytes));
    const snapshot = path.join(temp, 'blank.heapsnapshot');
    const sentinels = path.join(temp, 'sentinels.json');
    fs.writeFileSync(snapshot, bytes);
    fs.writeFileSync(sentinels, JSON.stringify({probe:'synthetic-schema-review-marker'}));
    const scanned = spawnSync('python', ['-X','utf8',path.join(root,'scripts/bh07_appheap/heap_oracle.py'),'scan','--snapshot',snapshot,'--sentinels',sentinels,'--paths'], {encoding:'utf8',timeout:60000});
    result.oracle_exit = scanned.status;
    result.scan_diagnostic = extractScanDiagnostic({status:scanned.status,stdout:scanned.stdout,stderr:scanned.stderr,code:scanned.error?.code});
  } finally {
    if (cdp?.ws) cdp.ws.close();
    if (browser) {
      const cleanup = await shutdownOwnedBrowser(browser);
      result.browser_exited = cleanup.exited;
      result.profile_removed = cleanup.profileRemoved && !fs.existsSync(browser.userDataDir);
    }
    fs.rmSync(temp, {recursive:true,force:true});
    result.raw_dump_directory_removed = !fs.existsSync(temp);
    console.log(JSON.stringify(result,null,2));
    if (!result.browser_exited || !result.profile_removed || !result.raw_dump_directory_removed) process.exitCode=1;
  }
}
main().catch(()=>{console.error('reviewer_schema_probe_failed');process.exitCode=1;});
