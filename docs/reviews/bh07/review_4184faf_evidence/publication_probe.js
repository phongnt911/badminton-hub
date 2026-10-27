// Actual writer, isolated temp output and synthetic values; never starts main/UI/DB.
const fs=require('node:fs'),path=require('node:path'),os=require('node:os'),vm=require('node:vm'),{createRequire}=require('node:module');
const file=path.resolve('scripts/bh07_appheap/run_app_profile_heap.js');const dir=fs.mkdtempSync(path.join(os.tmpdir(),'retained-publication-review-'));
try {
 const context={require:createRequire(file),module:{exports:{}},__dirname:path.dirname(file),process:{...process,env:{...process.env,BH07_APPHEAP_EVIDENCE:dir}},console,setTimeout,clearTimeout,URL};
 vm.createContext(context);vm.runInContext(fs.readFileSync(file,'utf8')+'\nglobalThis.review={writeEvidence,RAW_SENTINEL_VALUES,logLines};',context);
 const value='PRIVATE_CANARY_abcdefghij0123456789klmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ';context.review.RAW_SENTINEL_VALUES.sample=value;context.review.logLines.push('diagnostic:'+value.slice(0,40));
 const summary={gate:'synthetic publication control',status:'RUN',verdict:'PASS',findings:[],cycles:[],sentinels:{},cleanup:{},environment:{}};
 context.review.writeEvidence(summary);
 const log=fs.readFileSync(path.join(dir,'run.log'),'utf8');const s=JSON.parse(fs.readFileSync(path.join(dir,'summary.json'),'utf8'));
 console.log(JSON.stringify({status:s.status,verdict:s.verdict,published_private_middle20:log.includes(value.slice(20,40)),published_full_value:log.includes(value),expected_private_fragment_absent:true,actual_private_fragment_absent:!log.includes(value.slice(20,40))},null,2));
} finally {fs.rmSync(dir,{recursive:true,force:true});}
