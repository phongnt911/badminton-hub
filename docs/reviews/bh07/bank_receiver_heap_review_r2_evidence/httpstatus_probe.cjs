// Reviewer probe: actual runner HTTP adapter + actual fixture helper, fake fetch only.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const {createRequire} = require('node:module');
const file = path.resolve('scripts/bh07_appheap/run_app_profile_heap.js');
const {DisposableBankFixture} = require(path.resolve('scripts/bh07_appheap/disposable_bank_fixture'));
let posted = false;
let row = null;
let deleted = false;
const sandbox = vm.createContext({
  module:{exports:{}}, require:createRequire(file), __dirname:path.dirname(file), __filename:file,
  process, console:{log(){},error(){}}, setTimeout,clearTimeout,Buffer,URL,
  fetch:async (url,options={}) => {
    const table = new URL(url).pathname.split('/').pop();
    if(options.method==='POST') {
      posted=true; row=JSON.parse(options.body)[0];
      return {ok:false,status:403,text:async()=> 'permission denied'};
    }
    if(options.method==='DELETE') {deleted=true; row=null; return {ok:true};}
    return {ok:true,json:async()=>table==='clubs' && posted && row ? [row] : []};
  },
});
vm.runInContext(fs.readFileSync(file,'utf8')+'\nmodule.exports.probeRest={restGet,restWrite};',sandbox,{filename:file});
const env={API_URL:'http://127.0.0.1:54321',SERVICE_ROLE_KEY:'synthetic-test-value'};
const rest=sandbox.module.exports.probeRest;
const transport={apiUrl:env.API_URL,restGet:q=>rest.restGet(env,q),restWrite:(m,q,b)=>rest.restWrite(env,m,q,b)};
const fixture=new DisposableBankFixture({ownerUserId:'test-owner',clubName:'test-owned-nonce'});
(async()=>{
  let errorStatus;
  try {await fixture.ensure(transport);} catch(error) {errorStatus=error.status ?? null;}
  await fixture.cleanup(transport);
  console.log(JSON.stringify({http_response:403,error_status_forwarded:errorStatus,
    claimed_club_after_definite_rejection:fixture.createdClub,deleted_club_after_rejection:deleted},null,2));
})().catch(error=>{console.error(error.message);process.exitCode=1;});
