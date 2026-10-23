const fs=require('fs'),vm=require('vm'),{execFileSync}=require('child_process'),{createRequire}=require('module');
const req=createRequire('/workspace/badminton-hub/scripts/bh07_browser/run_late_response_controls.js');
const old=fs.readFileSync('/workspace/scratch/bh07-branch-close/old_controls.js','utf8');
const helper=fs.readFileSync('/workspace/badminton-hub/scripts/bh07_browser/late_response_assertions.js','utf8');
let escaped=0;
for(const [guard,name] of [['w.copyAvailable !== false','Member gains copy'],['sample.financeCard !== false','finance card leak']]) {
 const m={exports:{}};vm.runInNewContext(helper.replace(guard,'false'),{module:m,require:req});
 const context={require:req,console:{log:()=>{}},mutant:m.exports.validateLateResponse,result:null};
 vm.runInNewContext(old+'\nresult = cases.filter(([, w, expected]) => (mutant(w).length===0)!==expected).map(([name])=>name);',context);
 const caught=context.result.includes(name);console.log(JSON.stringify({name,mutationCaughtByOldControl:caught}));if(!caught)escaped++;
}
if(escaped) {console.error(`${escaped} mutants escape old controls`);process.exitCode=1;}
