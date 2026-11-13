const fs = require('fs');
const assert = require('assert/strict');
const source = fs.readFileSync('scripts/bh07_browser/web_lifecycle_scenario.js','utf8');
const sid = '11111111-1111-4111-8111-111111111111';
const rid = '22222222-2222-4222-8222-222222222222';
const marker = '  const context = page.context();';
assert.equal(source.split(marker).length,2);
const instrumented = source.replace("const SESSION_ID = '__BH07_SESSION_ID__';", `const SESSION_ID = '${sid}';`).replace(marker, `  return { canonicalJson, validateCompletePayloadObject, parseStrictJsonBody, onRequest, requests:capturedCompleteRequests, errors:completeCaptureErrors, start(){captureCompleteRequests=true;} };\n${marker}`);
const fn = new Function('return ('+instrumented+'\n)')();
(async()=>{
 const h = await fn({url:()=> 'http://127.0.0.1:8088/',on(){}});
 const valid = {p_session_id:sid,p_expected_version:2,p_request_id:rid};
 assert.deepEqual(h.validateCompletePayloadObject(valid,'test'),valid);
 assert.equal(h.canonicalJson(valid),h.canonicalJson({p_request_id:rid,p_expected_version:2,p_session_id:sid}));
 let rejects=0;
 for(const bad of [null,[],{...valid,extra:1},{...valid,p_expected_version:'2'},{...valid,p_expected_version:3},{...valid,p_session_id:rid},{...valid,p_request_id:'wrong'},Object.fromEntries(Object.entries(valid).filter(([k])=>k!=='p_request_id'))]){
  assert.throws(()=>h.validateCompletePayloadObject(bad,'test'));rejects++;
 }
 for(const body of ['{','', 'null','[]']) assert.equal(h.parseStrictJsonBody(body).ok,false);
 const url='http://127.0.0.1:54321/rest/v1/rpc/complete_session';
 const req=(u,body,method='POST')=>({url:()=>u,postData:()=>body,method:()=>method});
 h.start();
 h.onRequest(req(url,JSON.stringify(valid)));assert.equal(h.requests.length,1);
 h.onRequest(req(url,JSON.stringify(valid),'OPTIONS'));
 h.onRequest(req(url.replace(':54321',':54322'),JSON.stringify(valid)));
 h.onRequest(req(url,JSON.stringify({...valid,p_session_id:rid})));
 assert.equal(h.requests.length,1);
 h.onRequest(req(url,'{'));assert.equal(h.errors.length,1);
 await assert.rejects(fn({url:()=> 'https://example.com/',on(){throw Error('interacted')}}),/Guard failed: initial page origin/);
 console.log(JSON.stringify({expression:'PASS',payload_rejections:rejects,canonical_order:'PASS',json_rejections:4,request_filter_controls:4,external_origin:'PASS'}));
})().catch(e=>{console.error(e.message);process.exitCode=1;});
