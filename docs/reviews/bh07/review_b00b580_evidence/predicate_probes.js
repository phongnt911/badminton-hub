const fs=require('fs');const vm=require('vm');
const source=fs.readFileSync('/workspace/badminton-hub/scripts/bh07_browser/run_browser_verification.js','utf8');
const start=source.indexOf('    // Check captured requests for request_id & payload match');const end=source.indexOf('  } catch (err)',start);const block=source.slice(start,end);
const cases=[
{name:'no captured mutation requests',requests:[]},
{name:'different request_id and session',requests:[{postData:{p_request_id:'a',p_session_id:'sessionA',p_expected_version:1}},{postData:{p_request_id:'b',p_session_id:'sessionB',p_expected_version:9}}]},
{name:'same request id and session but changed version',requests:[{postData:{p_request_id:'a',p_session_id:'sessionA',p_expected_version:1}},{postData:{p_request_id:'a',p_session_id:'sessionA',p_expected_version:9}}]},
{name:'missing postData/preflight pair',requests:[{postData:null},{postData:{p_request_id:'a',p_session_id:'sessionA',p_expected_version:1}}]}
];
const results=[];
for(const c of cases){const checks=[];vm.runInNewContext(block,{capturedRequests:c.requests,checks,log:()=>{}});results.push({control:c.name,expected:'FAIL',actual:checks[0]?.status,detail:checks[0]?.detail});}
fs.writeFileSync('/workspace/scratch/bh07-review-b00b580/predicate-probes.json',JSON.stringify(results,null,2)+'\n');
console.log(JSON.stringify(results,null,2));
process.exit(results.every(r=>r.actual==='FAIL')?0:1);
