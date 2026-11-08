// Execute the actual new finally metadata block with an unreadable dump directory.
// No files are removed and no DB/browser is opened.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const runner = path.resolve(__dirname, '../../../../scripts/bh07_appheap/run_app_profile_heap.js');
const source = fs.readFileSync(runner, 'utf8');
const start = source.indexOf('    const dumpsRemoved = !fs.existsSync(DUMPS);');
const end = source.indexOf('    // The run-only expense row', start);
if (start < 0 || end < 0) throw Error('probe block not found');
const context = {
  fs: { existsSync: () => true, readdirSync: () => { const error = Error('synthetic unreadable directory'); error.code = 'EACCES'; throw error; } },
  DUMPS: 'C:/synthetic-temp/owned-dumps', ROOT: 'C:/synthetic-repo',
  chromeDir: 'C:/synthetic-temp/owned-profile', browserCleanupOk: true,
  summary: { cleanup: {} }, dbCleanupReached: false,
};
let thrownCode = null;
try { vm.runInNewContext(source.slice(start, end) + '\ndbCleanupReached = true;', context); }
catch (error) { thrownCode = error.code || error.name; }
const result = { injected_error: 'EACCES', thrown_code: thrownCode, subsequent_db_cleanup_reached: context.dbCleanupReached };
console.log(JSON.stringify(result));
if (thrownCode !== 'EACCES' || context.dbCleanupReached !== false) process.exitCode = 1;
