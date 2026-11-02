const fs=require('node:fs');
const path=require('node:path');
const {CdpClient}=require(path.resolve('scripts/bh07_browser/run_browser_verification'));
async function main(){
  const version=await (await fetch('http://127.0.0.1:62343/json/version',{signal:AbortSignal.timeout(2000)})).json();
  const cdp=new CdpClient(version.webSocketDebuggerUrl);
  await cdp.connect();
  const normal=await Promise.race([cdp.send('Browser.getVersion'),new Promise(resolve=>setTimeout(()=>resolve({timeout:true}),1000))]);
  const raw=await Promise.race([new Promise(resolve=>{const id=cdp.nextId++;cdp.pending.set(id,resolve);cdp.ws.send(JSON.stringify({id,method:'Browser.getVersion',params:{}}));}),new Promise(resolve=>setTimeout(()=>resolve({timeout:true}),1000))]);
  const result={normal_error:normal.error||null,normal_timeout:!!normal.timeout,raw_error:raw.error||null,raw_has_version:!!raw.result?.product};
  fs.writeFileSync(path.join(path.resolve('build'),'bkr9_protocol_result.json'),JSON.stringify(result,null,2)+'\n');
  console.log(JSON.stringify(result,null,2));
  cdp.ws.close();
}
main().catch(e=>{console.log(JSON.stringify({error:e.message}));process.exitCode=1;});
