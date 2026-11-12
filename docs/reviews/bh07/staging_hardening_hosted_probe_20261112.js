const fs=require('node:fs');
const key=JSON.parse(fs.readFileSync('.build/bh07-staging-public-key.local.json','utf8')).key;
const base='https://mxqpukhfiugdwsjsbihj.supabase.co';
const z='00000000-0000-0000-0000-000000000000';
const helperCalls=[
['is_app_admin',{p_user_id:z}],
['is_club_owner',{p_club_id:z,p_user_id:z}],
['is_club_member_active',{p_club_id:z,p_user_id:z}],
['has_club_role',{p_club_id:z,p_user_id:z,p_roles:['member']}],
['is_session_host',{p_session_id:z,p_user_id:z}],
['has_session_staff_role',{p_session_id:z,p_user_id:z,p_roles:['cohost']}],
['has_session_management_access',{p_session_id:z,p_user_id:z}],
['has_session_finance_access',{p_session_id:z,p_user_id:z}],
['is_session_participant',{p_session_id:z,p_user_id:z}],
['has_session_player_finance_access',{p_session_player_id:z,p_user_id:z}]
];
const calls=helperCalls.map(([name,body])=>({name,path:'/rest/v1/rpc/'+name,body,kind:'deny'})).concat([
{name:'public_summary',path:'/rest/v1/public_session_summary?select=id&limit=1',kind:'public'},
{name:'venues',path:'/rest/v1/venues?select=id&limit=1',kind:'public'},
{name:'list_public_sessions',path:'/rest/v1/rpc/list_public_sessions',body:{},kind:'public'},
{name:'private_outstanding',path:'/rest/v1/player_outstanding?select=session_player_id&limit=1',kind:'deny'},
{name:'bank_guard',path:'/rest/v1/rpc/get_host_bank_account',body:{},kind:'deny'}
]);
(async()=>{
 const records=[];
 for(const c of calls){
  try {
   const r=await fetch(base+c.path,{method:c.body?'POST':'GET',headers:{apikey:key,'Content-Type':'application/json'},...(c.body?{body:JSON.stringify(c.body)}:{})});
   const j=await r.json();
   const ok=c.kind==='deny'?([401,403].includes(r.status)&&j?.code==='42501'):(r.status===200&&Array.isArray(j));
   records.push({name:c.name,status:r.status,...(Array.isArray(j)?{rows:j.length}:{code:j?.code}),passed:ok});
  } catch(e){records.push({name:c.name,error:e.name,passed:false});}
 }
 const report={project_ref:'mxqpukhfiugdwsjsbihj',scope:'anonymous empty-project hosted HTTP controls; not populated isolation or authenticated Auth',records,passed:records.every(r=>r.passed)};
 fs.writeFileSync('.build/bh07-staging-hosted-http-20261112.json',JSON.stringify(report,null,2));
 console.log(JSON.stringify(report));
 process.exitCode=report.passed?0:1;
})().catch(e=>{console.log(JSON.stringify({error:e.name}));process.exitCode=1;});
