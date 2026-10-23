const fs=require('fs');
(async()=>{const pages=await(await fetch('http://127.0.0.1:9335/json/list')).json();const page=pages.find(x=>x.type==='page'&&x.url.includes('8088'));const w=new WebSocket(page.webSocketDebuggerUrl);await new Promise((r,j)=>{w.onopen=r;w.onerror=j});let id=0;const samples=[];
const save=()=>fs.writeFileSync('/workspace/scratch/bh07-review-02cd0ed/document-observer.json',JSON.stringify(samples,null,2)+'\n');
w.onmessage=e=>{const m=JSON.parse(e.data);if(m.result?.result?.value){const v=m.result.result.value;v.observedUTC=new Date().toISOString();samples.push(v);save()}};
const timer=setInterval(()=>w.send(JSON.stringify({id:++id,method:'Runtime.evaluate',params:{expression:"(()=>{const t=document.body.innerText;return {timeOrigin:performance.timeOrigin,hash:location.hash,financeCard:t.includes('Tài chính tổng hợp'),countOnly:t.includes('Chỉ xem số lượng'),guest:t.includes('Bạn đang xem dưới dạng khách'),ownerProfile:t.includes('ownera@example.test'),cohostProfile:t.includes('cohosta@example.test')}})()",returnByValue:true}})),1000);
w.onclose=()=>{clearInterval(timer);save();process.exit(0)};setTimeout(()=>{clearInterval(timer);save();w.close()},240000);
})().catch(e=>{console.error(e.message);process.exit(1)});
