const fs=require('fs'),assert=require('assert/strict');
const source=fs.readFileSync('scripts/bh07_browser/web_copy_qr_scenario.js','utf8');
const marker='  const context = page.context();';
const fn=new Function('return ('+source.replace(marker,'  return {escapeRegex};\n'+marker)+'\n)')();
(async()=>{const h=await fn({url:()=> 'http://127.0.0.1:8088/'});for(const s of ['A.B','A+B','[ab]','(ab)','$value','x\\y']){const re=new RegExp('^'+h.escapeRegex(s)+'$');assert(re.test(s),'Literal escaping mismatch');assert(!re.test(s+'x'),'Boundary mismatch');}console.log('6 literal receiver regex controls PASS')})().catch(e=>{console.error(e.message);process.exitCode=1});
