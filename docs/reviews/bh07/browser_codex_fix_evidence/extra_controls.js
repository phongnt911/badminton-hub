const fs=require('fs'),vm=require('vm');
const root='/workspace/badminton-hub';
const A=require(root+'/scripts/bh07_browser/assertions.js');
const manager=[`🏸 Tổng kết: ${A.FIXTURE.uiSessionTitle}`,'📍 HTTP Venue A · HTTP Club A','⏰ 23:30 22/10/2026 - 01:40 23/10/2026',A.FIXTURE.cohostCountsLine,'💰 Tổng chi phí: 200,000 VNĐ','🧾 Tổng phải thu: 200,000 VNĐ','✅ Đã thu: 0 VNĐ','⏳ Còn phải thu: 200,000 VNĐ'].join('\n');
const cohost=manager.split('\n').slice(0,4).join('\n');
const els=t=>[{text:t,aria:''}];
const cases=[
 ['manager valid baseline','PASS',()=>A.validateManagerClipboard(manager)],
 ['manager unknown financial field','FAIL',()=>A.validateManagerClipboard(manager+'\n📉 Hoàn tiền: 999 VNĐ')],
 ['cohost valid baseline','PASS',()=>A.validateCohostClipboard(cohost)],
 ['cohost money appended to place line','FAIL',()=>A.validateCohostClipboard(cohost.replace('HTTP Club A','HTTP Club A · 999 VNĐ'))],
 ['cohost UI bare currency leak','FAIL',()=>A.validateCohostSummarySurface(els('Chỉ xem số lượng\nSố lượng người\nCó mặt\n1\nVắng\n0\nĐã xác nhận\n2\n999 VNĐ'))],
 ['member valid empty baseline','PASS',()=>A.validateHistorySurface(els('Lịch sử buổi\nChưa có buổi nào'),[],true)],
 ['member empty screen with bank account','FAIL',()=>A.validateHistorySurface(els('Lịch sử buổi\nChưa có buổi nào\nSTK: 123456789012'),[],true)],
];
async function main(){
 const rows=[];
 for(const [name,expected,run] of cases){const errors=await run();rows.push({name,expected,actual:errors.length?'FAIL':'PASS',errors});}
 const source=fs.readFileSync(root+'/scripts/bh07_browser/run_browser_verification.js','utf8');
 const start=source.indexOf('    const memberHistoryElements = await cdp.getAllSemantics();');
 const end=source.indexOf("    await cdp.screenshot('10_member_isolated_history.png'",start);
 if(start<0||end<0)throw Error('Current member gate missing');
 const block=source.slice(start,end);
 for(const [name,body,expected] of [['valid empty response',[],'PASS'],['FORBIDDEN response object',{code:'42501',message:'FORBIDDEN'},'FAIL']]){
  const context={...A,cdp:{getAllSemantics:async()=>els('Lịch sử buổi\nChưa có buổi nào')},memberHistoryCalls:[{postData:{p_club_id:null}}],memberHistoryResponses:[{body}]};
  let actual='PASS',error=null;try{await vm.runInNewContext('(async()=>{'+block+'})()',context);}catch(e){actual='FAIL';error=e.message;}
  rows.push({name,expected,actual,error});
 }
 fs.writeFileSync('/workspace/scratch/bh07-codex-fix/extra-controls.json',JSON.stringify(rows,null,2)+'\n');
 console.log(JSON.stringify(rows,null,2));
 const mismatches=rows.filter(x=>x.expected!==x.actual).length;
 console.log('Mismatches:',mismatches);
 process.exitCode=mismatches?1:0;
}
main().catch(e=>{console.error(e);process.exit(1)});
