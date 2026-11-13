const fs=require('fs'),assert=require('assert/strict');
const source=fs.readFileSync('scripts/bh07_browser/web_payment_scenario.js','utf8');
const sid='11111111-1111-4111-8111-111111111111',player='22222222-2222-4222-8222-222222222222',pid='33333333-3333-4333-8333-333333333333',rid='44444444-4444-4444-8444-444444444444';
const marker="  try {\n    if (PHASE === 'submit') {";assert.equal(source.split(marker).length,2);
const instrumented=source.replace("const SESSION_ID = '__BH07_SESSION_ID__';",`const SESSION_ID = '${sid}';`).replace("const GUEST_PLAYER_ID = '__BH07_PLAYER_ID__';",`const GUEST_PLAYER_ID = '${player}';`).replace('const PAYMENT_ID = null;',`const PAYMENT_ID = '${pid}';`).replace(marker,'  return {validateSubmitRequestBody,validateConfirmRequestBody,parseStrictJsonBody,hasExactMoneyLabel,onRequest,submit:capturedSubmitRequests,errors:captureErrors,unexpected:unexpectedMutationPaths};\n'+marker);
const fn=new Function('return ('+instrumented+'\n)')();
(async()=>{
 const h=await fn({url:()=> 'http://127.0.0.1:8088/',context:()=>({}),on(){}});
 const valid={p_amount_vnd:100000,p_method:'bank_transfer',p_player_id:player,p_reference:null,p_request_id:rid};
 assert.deepEqual(h.validateSubmitRequestBody(valid),valid);
 let rejects=0;
 for(const bad of [{...valid,p_amount_vnd:100001},{...valid,p_player_id:sid},{...valid,p_method:'cash'},{...valid,p_reference:'not-null'},{...valid,p_request_id:'bad'},{...valid,extra:1}]){assert.throws(()=>h.validateSubmitRequestBody(bad));rejects++}
 h.validateConfirmRequestBody({p_payment_id:pid,p_request_id:rid});
 for(const bad of [{p_payment_id:sid,p_request_id:rid},{p_payment_id:pid,p_request_id:'bad'},{p_payment_id:pid,p_request_id:rid,extra:1}]){assert.throws(()=>h.validateConfirmRequestBody(bad));rejects++}
 assert(h.hasExactMoneyLabel('Phải trả 100,000 VNĐ','Phải trả',100000));
 assert(!h.hasExactMoneyLabel('Phải trả 100,001 VNĐ','Phải trả',100000));
 assert(!h.hasExactMoneyLabel('Phải trả 1,100,000 VNĐ','Phải trả',100000));
 for(const raw of ['{','[]','null',''])assert(!h.parseStrictJsonBody(raw).ok);
 const url='http://127.0.0.1:54321/rest/v1/rpc/submit_payment';const req=(u,body,method='POST')=>({url:()=>u,postData:()=>body,method:()=>method});
 h.onRequest(req(url,JSON.stringify(valid)));assert.equal(h.submit.length,1);
 h.onRequest(req(url,JSON.stringify({...valid,p_player_id:sid})));assert.equal(h.submit.length,2);assert.throws(()=>h.validateSubmitRequestBody(h.submit[1].body));
 h.onRequest(req(url,'{'));assert.equal(h.errors.length,1);
 h.onRequest(req(url,'{}','OPTIONS'));h.onRequest(req(url.replace(':54321',':54322'),'{}'));assert.equal(h.submit.length,2);
 h.onRequest(req(url.replace('submit_payment','confirm_payment'),'{}'));assert.equal(h.unexpected.length,1);
 await assert.rejects(fn({url:()=> 'https://example.com/'}),/Guard failed: initial page origin/);
 console.log(JSON.stringify({expression:'PASS',payload_mutants_rejected:rejects,money_controls:3,json_controls:4,request_filter_and_unexpected_mutation:'PASS',external_origin:'PASS'}));
})().catch(e=>{console.error(e.message);process.exitCode=1});
