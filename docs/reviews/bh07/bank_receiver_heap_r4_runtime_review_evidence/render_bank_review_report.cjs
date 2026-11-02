const fs=require('node:fs');
const path=require('node:path');
const {renderReport}=require(path.resolve('scripts/bh07_appheap/run_app_profile_heap'));
const summary=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));
fs.writeFileSync(process.argv[3],renderReport(summary)+'\n');
