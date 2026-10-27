// Current exported publication sanitizer; synthetic canary only, no HTTP or DB.
const path=require('node:path');
const runner=require(path.resolve('scripts/bh07_appheap/run_app_profile_heap.js'));
const value='PRIVATE_CANARY_abcdefghij0123456789klmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ';
const input=value.slice(0,40);
const output=runner.redactSentinels(input,{sample:value});
const full=runner.redactSentinels(value,{sample:value});
const short=runner.redactSentinels(value.slice(0,20),{sample:value});
console.log(JSON.stringify({
 full_value_positive:{redacted_completely:full==='<redacted>'},
 prefix20_positive:{redacted_completely:short==='<redacted>'},
 prefix60:{redacted_completely:runner.redactSentinels(value.slice(0,60),{sample:value})==='<redacted>',private_middle40_survives:runner.redactSentinels(value.slice(0,60),{sample:value}).includes(value.slice(20,60))},
 prefix40:{input_length:input.length,detected_before:runner.findSentinelLeaks([input],{sample:value}),redacted_completely:output==='<redacted>',private_middle20_survives:output.includes(value.slice(20,40)),output_length:output.length,detected_after:runner.findSentinelLeaks([output],{sample:value})}
},null,2));
