// Actual writer with a synthetic valid short string value; no main/UI/HTTP/DB.
const fs=require('node:fs'),path=require('node:path'),os=require('node:os'),vm=require('node:vm'),{createRequire}=require('node:module');
const file=path.resolve('scripts/bh07_appheap/run_app_profile_heap.js');
function check(value) {
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'retained-json-review-'));
 try {
  const context={require:createRequire(file),module:{exports:{}},__dirname:path.dirname(file),process:{...process,env:{...process.env,BH07_APPHEAP_EVIDENCE:dir}},console,setTimeout,clearTimeout,URL};
  vm.createContext(context);vm.runInContext(fs.readFileSync(file,'utf8')+'\nglobalThis.review={writeEvidence,RAW_SENTINEL_VALUES};',context);
  context.review.RAW_SENTINEL_VALUES.sample=value;
  context.review.writeEvidence({gate:'synthetic control',status:'RUN',verdict:'PASS',findings:[],cycles:[],sentinels:{},cleanup:{ok:true},environment:{build:{mode:'profile',served_match:true,reused:false,artifacts:{}}},git_dirty:false,notes:['private:'+value]});
  const raw=fs.readFileSync(path.join(dir,'summary.json'),'utf8');let valid=true,detail='';
  try {JSON.parse(raw);} catch(e){valid=false;detail=e.name;}
  return {summary_json_valid:valid,error_type:detail,expected_json_valid:true,raw_placeholder_in_boolean:raw.includes('"ok": <redacted>')||raw.includes('"served_match": <redacted>')||raw.includes('"git_dirty": <redacted>')};
 } finally {fs.rmSync(dir,{recursive:true,force:true});}
}
console.log(JSON.stringify({ordinary_control:check('PRIVATE_SYNTHETIC_VALUE_12345'),short_true_value:check('true'),short_false_value:check('false')},null,2));
