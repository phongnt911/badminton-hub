// Execute the current runner's reuse-build branch only; no browser/DB/mock app.
const fs=require('node:fs'),vm=require('node:vm');
const src=fs.readFileSync('scripts/bh07_appheap/run_app_profile_heap.js','utf8');
const code=src.match(/if \(reuseBuild\) \{([\s\S]*?)\n    \} else \{/)[1];
const context={summary:{environment:{}},reuseBuild:true};
vm.runInNewContext(code,context);
console.log(JSON.stringify({control:'source reuse-build branch, no build artifact supplied',build:context.summary.environment.build},null,2));
