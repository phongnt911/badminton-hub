const fs=require('fs'),assert=require('assert/strict');
const source=fs.readFileSync('scripts/bh07_browser/web_copy_qr_scenario.js','utf8');
const marker="    if (MODE === 'cohost_copy') {";
assert.equal(source.split(marker).length,2);
const testSource=source.replace(marker,"    return {clipboardGranted, countCheck:typeof hasExactCohostCounts==='function'?hasExactCohostCounts:null};\n"+marker);
const fn=new Function('return ('+testSource+'\n)')();
let failures=0;
function check(name,action){try{action();console.log(name+' PASS')}catch{failures++;console.log(name+' FAIL')}}
async function grantCase(message){
 let clear=0;
 const context={grantPermissions:async()=>{if(message)throw Error(message)},clearPermissions:async()=>{clear++},setOffline:async()=>{}};
 const page={url:()=> 'http://127.0.0.1:8088/',context:()=>context,on(){},off(){}};
 try{return {result:await fn(page),clear}}catch(e){return {error:e.message,clear}}
}
(async()=>{
 const supported=await grantCase(null);assert(!supported.error);
 let count=supported.result.countCheck;
 if(!count){
  const start=source.indexOf("        if (!copiedText.includes('Có mặt:");
  const end=source.indexOf('\n\n        const forbiddenClipboardPatterns',start);
  assert(start>=0&&end>start);
  const raw=new Function('copiedText',source.slice(start,end)+'\nreturn true;');
  count=text=>{try{return raw(text)}catch{return false}};
 }
 check('exact_counts',()=>assert(count('👥 Có mặt: 2 · Vắng: 0 · Đã xác nhận: 2')));
 for(const n of [20,23,200])check('reject_confirmed_'+n,()=>assert(!count('👥 Có mặt: 2 · Vắng: 0 · Đã xác nhận: '+n)));
 for(const message of ['Unknown permission: clipboard-read','Unknown permission: clipboard-write']){
  const r=await grantCase(message);
  check('unsupported_skip',()=>assert(!r.error&&r.result.clipboardGranted===false));
  check('attempted_grants_cleanup',()=>assert.equal(r.clear,1));
 }
 for(const message of ['Target page, context or browser has been closed','Permission grant timed out','Permission denied']){
  const r=await grantCase(message);check('unexpected_grant_error',()=>assert(r.error));
 }
 console.log(JSON.stringify({failed_controls:failures}));if(failures)process.exitCode=1;
})().catch(e=>{console.error(e.message);process.exitCode=1});
