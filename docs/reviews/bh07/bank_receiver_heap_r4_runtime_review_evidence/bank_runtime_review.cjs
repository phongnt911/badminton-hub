// Reviewer wrapper: credentials and captured child output never leave memory.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const {execFileSync, spawn} = require('node:child_process');
const root = path.resolve(__dirname, '..');
const hash = value => crypto.createHash('sha256').update(value).digest('hex');
async function main() {
  const raw = execFileSync('npx', ['--yes', 'supabase@2.121.0', 'status', '-o', 'env'],
    {cwd: root, encoding:'utf8', shell:true, stdio:['ignore','pipe','pipe'], timeout:60000});
  const env = {};
  for (const line of raw.split(/\r?\n/)) { const m = line.trim().match(/^([A-Z_]+)="(.*)"$/); if(m) env[m[1]]=m[2]; }
  if (!['http://127.0.0.1:54321', 'http://localhost:54321'].includes(env.API_URL) || !env.SERVICE_ROLE_KEY) throw Error('local_environment_unavailable');
  const tables = ['clubs','club_members','club_bank_accounts','session_expenses','payments'];
  async function snapshot() {
    const output = {};
    for (const table of tables) {
      const res = await fetch(`${env.API_URL}/rest/v1/${table}?select=*&order=id`, {
        headers:{apikey:env.SERVICE_ROLE_KEY,Authorization:`Bearer ${env.SERVICE_ROLE_KEY}`}, signal:AbortSignal.timeout(20000)});
      if(!res.ok) throw Error(`snapshot_http_${res.status}_${table}`);
      const rows = await res.json();
      output[table] = {count:rows.length, sha256:hash(JSON.stringify(rows)), id_hashes:rows.map(row=>hash(String(row.id)).slice(0,12))};
    }
    return output;
  }
  const before = await snapshot();
  if (process.argv.includes('--preflight')) { console.log(JSON.stringify({preflight:'PASS',tables:Object.fromEntries(Object.entries(before).map(([k,v])=>[k,{count:v.count,sha256:v.sha256}]))})); return; }
  const out = path.join(root,'docs/reviews/bh07/bank_receiver_heap_r4_runtime_evidence');
  if(fs.existsSync(out)) throw Error('fresh_output_required');
  const child = spawn(process.execPath,['scripts/bh07_appheap/run_app_profile_heap.js','--bank-coverage'],
    {cwd:root,env:{...process.env,BH07_APPHEAP_EVIDENCE:out},stdio:['ignore','pipe','pipe']});
  const buffers=[];
  child.stdout.on('data',chunk=>buffers.push(chunk)); child.stderr.on('data',chunk=>buffers.push(chunk));
  const code = await new Promise((resolve,reject)=>{child.on('error',reject);child.on('close',resolve);});
  const after = await snapshot();
  const preserve = tables.every(t=>before[t].count===after[t].count && before[t].sha256===after[t].sha256);
  const summaryPath = path.join(out,'summary.json');
  const summary = fs.existsSync(summaryPath)?JSON.parse(fs.readFileSync(summaryPath,'utf8')):{};
  const receiptAbsent = ['disposable_club_id_sha256_12','disposable_bank_id_sha256_12'].every((key,i)=>
    summary.cleanup?.[key] && !after[i===0?'clubs':'club_bank_accounts'].id_hashes.includes(summary.cleanup[key]));
  const result = {child_exit:code,status:summary.status,verdict:summary.verdict,tested_source_sha:summary.tested_source_sha,
    git_dirty:summary.git_dirty,cycles:summary.cycles?.length,preexisting_rows_preserved:preserve,receipt_ids_absent:receiptAbsent,
    before,after,captured_output_bytes:Buffer.concat(buffers).length,captured_output_sha256:hash(Buffer.concat(buffers))};
  fs.writeFileSync(path.join(root,'build/bank_runtime_independent_check.json'),JSON.stringify(result,null,2)+'\n');
  console.log(JSON.stringify({...result,before:undefined,after:undefined},null,2));
  if(code!==0 || !preserve || !receiptAbsent || summary.status!=='RUN' || summary.verdict!=='PASS') process.exitCode=1;
}
main().catch(error=>{ console.log(JSON.stringify({reviewer_wrapper:'FAILED',error_code:/^[a-z_0-9]+$/.test(error.message)?error.message:'diagnostic_withheld',error_sha256:hash(String(error.message))}));process.exitCode=1; });
