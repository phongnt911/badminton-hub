// Execute the current fixture helpers with an in-memory HTTP stub, never the real DB.
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),{createRequire}=require('node:module');
const file=path.resolve('scripts/bh07_appheap/run_app_profile_heap.js');const source=fs.readFileSync(file,'utf8');
let present=true,calls=[];
const context={require:createRequire(file),module:{exports:{}},__dirname:path.dirname(file),process,console,setTimeout,clearTimeout,fetch:async(url,opts={})=>{
 const method=opts.method||'GET';calls.push(method);
 if(method==='DELETE'){present=false;return {ok:true,status:204};}
 return {ok:true,status:200,json:async()=>present?[{id:context.reviewAPI.EXTRA_EXPENSE.id,title:'existing independent fixture',status:'posted'}]:[]};
}};
vm.createContext(context);vm.runInContext(source+'\nglobalThis.reviewAPI={ensureExtraExpense,removeExtraExpense,EXTRA_EXPENSE,findSentinelLeaks};',context);
(async()=>{
 await context.reviewAPI.ensureExtraExpense({API_URL:'http://127.0.0.1:0',SERVICE_ROLE_KEY:'stub-only'});
 const clean=await context.reviewAPI.removeExtraExpense({API_URL:'http://127.0.0.1:0',SERVICE_ROLE_KEY:'stub-only'});
 const needle='PRIVATE_CANARY_'+('q'.repeat(65));const leak=context.reviewAPI.findSentinelLeaks(['property:'+needle.slice(0,40)+' -> string'],{label:needle});
 console.log(JSON.stringify({preexisting:true,post_calls:calls.filter(x=>x==='POST').length,delete_calls:calls.filter(x=>x==='DELETE').length,remaining:present,cleanup_result:clean,truncated_private_label_sanitizer_findings:leak},null,2));
})().catch(e=>{console.error(e);process.exitCode=1;});
