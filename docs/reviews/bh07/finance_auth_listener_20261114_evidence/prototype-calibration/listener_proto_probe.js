const fs=require('node:fs'),os=require('node:os'),path=require('node:path'),crypto=require('node:crypto');
const {spawn,execFileSync}=require('node:child_process');
const {CdpClient}=require('../scripts/bh07_browser/run_browser_verification');
const {assertPortFree,assertServedMatches,hashArtifacts}=require('../scripts/bh07_appheap/build_guard');
const {streamSnapshotToFile,waitForStartupAndGuestBaseline}=require('../scripts/bh07_appheap/run_payment_instructions_heap');
const {shutdownOwnedBrowser}=require('../scripts/bh07_appheap/owned_browser_cleanup');
const root=path.resolve(__dirname,'..'),out=path.join(__dirname,'listener-proto-20261114-r1');
fs.mkdirSync(out);const temp=fs.mkdtempSync(path.join(os.tmpdir(),'bh07-listener-baseline-'));
const profile=path.join(temp,'profile'),dump=path.join(temp,'guest.heapsnapshot');
const summary={scope:'Guest-only layout calibration; Auth listener gate NOT_RUN',source:execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim(),git_dirty:execFileSync('git',['status','--porcelain'],{encoding:'utf8'}).trim()!=='',started_at:new Date().toISOString()};
let proc,cdp,version;
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
(async()=>{try{
 await assertPortFree(9339);await assertServedMatches('http://127.0.0.1:8088','build/web');
 const artifacts=hashArtifacts('build/web');
 for(const [f,sha] of Object.entries(artifacts)){const r=await fetch('http://127.0.0.1:8088/'+f);if(!r.ok||crypto.createHash('sha256').update(Buffer.from(await r.arrayBuffer())).digest('hex')!==sha)throw Error('served artifact mismatch');}
 summary.artifacts=artifacts;summary.all_served_artifacts_match=true;
 proc=spawn('C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',['--headless=new','--disable-gpu','--no-first-run','--no-default-browser-check','--disable-background-networking','--remote-debugging-port=9339','--user-data-dir='+profile,'about:blank'],{stdio:'ignore'});
 for(let i=0;i<50;i++){await sleep(200);try{const r=await fetch('http://127.0.0.1:9339/json/version');if(r.ok){version=await r.json();break;}}catch{}}
 if(!version)throw Error('owned browser startup failed');
 summary.browser=version.Browser;cdp=new CdpClient(version.webSocketDebuggerUrl);await cdp.connect();await cdp.createTab('http://127.0.0.1:8088');
 await waitForStartupAndGuestBaseline(cdp,{});summary.guest_ui_confirmed=true;summary.time_origin=await cdp.evaluate('performance.timeOrigin');
 await streamSnapshotToFile({cdp,outFile:dump});
 execFileSync('python',['.build/listener_proto_scan.py',dump,path.join(out,'layout.json')],{cwd:root,stdio:'pipe'});
 const layout=JSON.parse(fs.readFileSync(path.join(out,'layout.json')));
 const ids=layout.rooted_auth_heap_object_ids;if(ids.length!==1)throw Error('ambiguous rooted AuthProvider');
 const objectGroup='bh07-guest-auth-calibration-'+crypto.randomUUID();let released=false;
 try{
  const remote=await cdp.send('HeapProfiler.getObjectByHeapObjectId',{objectId:ids[0],objectGroup});
  if(remote.error||remote.result?.result?.className!=='AuthProvider')throw Error('AuthProvider remote identity mismatch');
  const props=await cdp.send('Runtime.getProperties',{objectId:remote.result.result.objectId,ownProperties:true,generatePreview:false});
  if(props.error)throw Error('scalar descriptor read failed');
  const values={};
  for(const name of ['ChangeNotifier__count','ChangeNotifier__notificationCallStackDepth','ChangeNotifier__reentrantlyRemovedListeners']){
   const matches=props.result.result.filter(d=>d.name===name && d.isOwn===true);
   if(matches.length!==1||matches[0].value?.type!=='number'||!Number.isSafeInteger(matches[0].value.value)||matches[0].value.value<0)throw Error('counter unavailable');
   values[name]=matches[0].value.value;
  }
  summary.auth_structural_counters=values;
  summary.scalar_observer={method:'HeapProfiler.getObjectByHeapObjectId then Runtime.getProperties ownProperties; no getters/evaluate',heap_object_id:ids[0],class_name:'AuthProvider'};
 }finally{
  const done=await cdp.send('Runtime.releaseObjectGroup',{objectGroup});if(done.error)throw Error('observer object group release failed');released=true;
  summary.scalar_observer_group_released=released;
 }
 summary.calibration_status='MEASURED';summary.full_listener_gate='NOT_RUN';
}catch(e){summary.error=e.message;summary.calibration_status='FAIL';process.exitCode=1;}finally{
 if(cdp)await cdp.close().catch(()=>{});
 const cleanup=await shutdownOwnedBrowser({proc,userDataDir:profile,closeBrowser:version?async()=>{const b=new CdpClient(version.webSocketDebuggerUrl);try{await b.connect();await b.send('Browser.close');}finally{b.ws?.close();}}:undefined});
 if(fs.existsSync(dump))fs.unlinkSync(dump);
 if(!fs.existsSync(profile))fs.rmdirSync(temp);
 summary.cleanup={browser_exited:cleanup.exited,profile_removed:cleanup.profileRemoved,dump_absent:!fs.existsSync(dump),owned_temp_absent:!fs.existsSync(temp)};
 if(!Object.values(summary.cleanup).every(x=>x===true))process.exitCode=1;
 summary.finished_at=new Date().toISOString();fs.writeFileSync(path.join(out,'provenance.json'),JSON.stringify(summary,null,2)+'\n');
 console.log(JSON.stringify({calibration:summary.calibration_status,listener_gate:'NOT_RUN',cleanup:summary.cleanup}));
}})().catch(e=>{console.error(e.message);process.exitCode=1});
