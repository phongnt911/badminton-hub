const {spawnSync} = require('node:child_process');
const path = require('node:path');
if (process.argv.includes('--child')) {
  const {EventEmitter} = require('node:events');
  const {shutdownOwnedBrowser:shutdown} = require(path.resolve('scripts/bh07_appheap/owned_browser_cleanup'));
  const proc = Object.assign(new EventEmitter(), {pid: 1, exitCode: null, signalCode: null});
  setTimeout(() => {proc.exitCode=0;proc.emit('exit',0,null);},5);
  shutdown({proc,userDataDir:'fake-owned-profile',closeBrowser:()=>new Promise(()=>{})},
    {timeoutMs:30,fs:{existsSync:()=>false}})
    .then(result=>console.log(JSON.stringify(result)));
} else {
  const child=spawnSync(process.execPath,[__filename,'--child'],{cwd:process.cwd(),encoding:'utf8',timeout:2000});
  console.log(JSON.stringify({child_exit:child.status,cleanup_result_received:child.stdout.trim().length>0,error:child.error?.code||null}));
}
