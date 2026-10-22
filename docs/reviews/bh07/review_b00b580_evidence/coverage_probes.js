const fs=require('fs');const vm=require('vm');
const src=fs.readFileSync('/workspace/badminton-hub/scripts/bh07_browser/run_browser_verification.js','utf8');
const results=[];
(async()=>{
 const start=src.indexOf("    log('--- TC03: Real Attendance Check-in ---');");const end=src.indexOf('  } catch (err)',start);const block=src.slice(start,end);
 const checks=[];const context={cdp:{clickSemantic:async()=>{},screenshot:async()=>{}},checks,log:()=>{},setTimeout:(fn)=>fn()};
 await vm.runInNewContext('(async()=>{'+block+'})()',context);
 results.push({control:'attendance request has no side effect, click resolves',expected:'FAIL',actual:checks[0]?.status});
 const managerCondition=src.match(/if \(!hasPhone && !hasBank && !hasSecret && hasFinances\)/)[0].slice(4,-1);
 const wrong='Tổng chi phí: 999 VNĐ\nCòn phải thu: 999 VNĐ';
 const managerAccepted=vm.runInNewContext(managerCondition,{hasPhone:/0\d{9,10}/.test(wrong),hasBank:/(stk|ngan hang|vietinbank|techcombank)/i.test(wrong),hasSecret:/secret|password|bearer/i.test(wrong),hasFinances:wrong.includes('Tổng chi phí:')&&wrong.includes('Còn phải thu:')});
 results.push({control:'manager clipboard wrong numeric totals',expected:'FAIL',actual:managerAccepted?'PASS':'FAIL'});
 const moneyGate=src.match(/const hasAnyMoney = ([^;]+);/)[1];
 const cohostCondition=src.match(/if \(hasManagementOnlyNote && !hasFinanceCard && !hasAnyMoney\)/)[0].slice(4,-1);
 for(const text of ['Đã thu: 50000 VNĐ','SĐT: 0987654321\nSTK: 123456789012']){
  const hasAnyMoney=vm.runInNewContext(moneyGate,{cohostClipboard:text});const accepted=vm.runInNewContext(cohostCondition,{hasManagementOnlyNote:true,hasFinanceCard:false,hasAnyMoney});
  results.push({control:'cohost clipboard leak: '+text,expected:'FAIL',actual:accepted?'PASS':'FAIL'});
 }
 fs.writeFileSync('/workspace/scratch/bh07-review-b00b580/coverage-probes.json',JSON.stringify(results,null,2)+'\n');console.log(JSON.stringify(results,null,2));process.exit(results.every(x=>x.actual==='FAIL')?0:1);
})().catch(e=>{console.error(e);process.exit(2)});
