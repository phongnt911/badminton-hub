const fs=require('node:fs');
const path=require('node:path');
const os=require('node:os');
const net=require('node:net');
const {startChromeLogged}=require(path.resolve('scripts/bh07_appheap/run_app_profile_heap'));
const {shutdownOwnedBrowser}=require(path.resolve('scripts/bh07_appheap/owned_browser_cleanup'));
async function main(){
  const expected=path.join(os.tmpdir(),`bh07_appheap_chrome_${process.pid}`);
  if(fs.existsSync(expected))throw Error('preexisting_profile_refused');
  const server=net.createServer();
  await new Promise((resolve,reject)=>{server.once('error',reject);server.listen(0,'127.0.0.1',resolve);});
  const port=server.address().port;
  await new Promise(resolve=>server.close(resolve));
  const old=path.join(os.tmpdir(),'bh07_appheap_chrome_84440');
  const oldExisted=fs.existsSync(old);
  const browser=await startChromeLogged(path.join(path.resolve('build'),'bkr9_real_browser_stderr.log'),{port});
  const created=fs.existsSync(browser.userDataDir);
  const launcher_before={pid:browser.proc.pid,exitCode:browser.proc.exitCode,signalCode:browser.proc.signalCode};
  const receipt=await shutdownOwnedBrowser(browser);
  const result={created,port,launcher_before,receipt,profile_absent:!fs.existsSync(expected),old_profile_existence_preserved:fs.existsSync(old)===oldExisted};
  fs.writeFileSync(path.join(path.resolve('build'),'bkr9_real_browser_result.json'),JSON.stringify(result,null,2)+'\n');
  console.log(JSON.stringify(result,null,2));
  if(!created||!receipt.exited||!receipt.profileRemoved||!result.profile_absent||!result.old_profile_existence_preserved)process.exitCode=1;
}
main().catch(e=>{console.log(JSON.stringify({probe:'FAILED',error:e.message}));process.exitCode=1;});
