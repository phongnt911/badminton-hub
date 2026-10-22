const fs=require('fs');
(async()=>{
 let page;for(let i=0;i<40;i++){try{const pages=await(await fetch('http://127.0.0.1:9335/json/list')).json();page=pages.find(p=>p.type==='page'&&p.url.includes('8088'));if(page)break;}catch{}await new Promise(r=>setTimeout(r,200));}
 if(!page)throw Error('No reviewer browser page');
 const ws=new WebSocket(page.webSocketDebuggerUrl);await new Promise((r,j)=>{ws.onopen=r;ws.onerror=j});
 let id=0;const rows=[];const pending=new Map();
 const save=()=>fs.writeFileSync('/workspace/scratch/bh07-review-b00b580/network-observer.json',JSON.stringify(rows,null,2)+'\n');
 ws.onmessage=e=>{const m=JSON.parse(e.data);if(m.id&&pending.has(m.id)){pending.get(m.id)(m);pending.delete(m.id)}
 if(m.method==='Network.requestWillBeSent'&&m.params.request.url.includes('/rest/v1/rpc/')){let b=null;try{b=JSON.parse(m.params.request.postData)}catch{} const safe={};for(const k of ['p_request_id','p_session_id','p_expected_version'])if(b&&k in b)safe[k]=b[k];rows.push({event:'request',requestId:m.params.requestId,path:new URL(m.params.request.url).pathname,method:m.params.request.method,payload:safe});save()}
 if(m.method==='Network.responseReceived'&&m.params.response.url.includes('/rest/v1/rpc/')){rows.push({event:'response',requestId:m.params.requestId,path:new URL(m.params.response.url).pathname,status:m.params.response.status});save()}
 if(m.method==='Network.loadingFailed'){rows.push({event:'loadingFailed',requestId:m.params.requestId,error:m.params.errorText});save()}};
 ws.send(JSON.stringify({id:++id,method:'Network.enable'}));
 ws.onclose=()=>{save();process.exit(0)};
 setTimeout(()=>{save();ws.close();},300000);
})().catch(e=>{console.error(e.message);process.exit(1)});
