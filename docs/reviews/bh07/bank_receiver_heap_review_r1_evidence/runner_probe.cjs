const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const {createRequire} = require('node:module');
const file = path.resolve('scripts/bh07_appheap/run_app_profile_heap.js');
const source = fs.readFileSync(file, 'utf8');
const localRequire = createRequire(file);
function load(fetch) {
  const context = vm.createContext({
    module: {exports: {}}, __dirname: path.dirname(file), __filename: file,
    process: {...process, argv: [process.execPath, file], env: {}},
    console: {log() {}, error() {}}, fetch, setTimeout, clearTimeout, Buffer, URL,
    require(id) {
      if (id === 'node:fs') return {...fs, mkdirSync() {}, writeFileSync() {},
        existsSync() {return false;}, readdirSync() {return [];}, rmSync() {}};
      if (id === 'node:child_process') return {
        execFileSync(command, args) {return command === 'git' && args[0] === 'rev-parse' ? 'a'.repeat(40) : '';},
        spawn() {throw new Error('unexpected spawn in fake-only probe');},
      };
      return localRequire(id);
    },
  });
  vm.runInContext(source + '\nmodule.exports.probe = {main, ensureDisposableBank, removeDisposableBank};', context, {filename: file});
  return context;
}
const env = {API_URL: 'http://127.0.0.1:54321', SERVICE_ROLE_KEY: 'synthetic-test-value'};
async function mainRegression() {
  const context = load(() => {throw new Error('unexpected live request');});
  vm.runInContext(`
    supabaseEnv = () => ({API_URL:'http://127.0.0.1:54321'});
    resolveSentinels = async () => ({bank:'control-bank',receiver:'control-name',expense:'expense',
      expense_id:'expense-id',expense2:'expense-2',expense_id_2:'expense-2-id',
      payment_id:'payment-id',payment_ref:'payment-ref',players:['a','b'],probe:'probe'});
    removeExtraExpense = async () => ({id:'expense',created:true,removed:true,verified_absent:true});
    removeExtraPayment = async () => ({id:'payment',created:true,removed:true,verified_absent:true});
    writeEvidence = (summary) => {globalThis.probeSummary = summary;};
  `, context);
  await context.module.exports.probe.main();
  return {status: context.probeSummary.status, error: context.probeSummary.error};
}
async function ownershipRace() {
  let raced = false;
  const deleted = new Set();
  const deletes = [];
  const context = load(async (url, options = {}) => {
    const table = new URL(url).pathname.split('/').pop();
    const method = options.method || 'GET';
    if (method === 'POST') {raced = true; return {ok:false,status:409,text:async()=> 'foreign row won collision'};}
    if (method === 'DELETE') {deletes.push(table); deleted.add(table); return {ok:true};}
    let rows = [];
    if (table === 'session_players') rows = [{user_id:'synthetic-member-not-owner'}];
    else if (raced && !deleted.has(table)) rows = [{id:'foreign-row',name:'foreign',owner_user_id:'other-actor'}];
    return {ok:true,json:async()=>rows};
  });
  try {await context.module.exports.probe.ensureDisposableBank(env);} catch (_) {}
  const state = vm.runInContext('disposableFixture', context);
  await context.module.exports.probe.removeDisposableBank(env);
  return {claimed_foreign_club: state.created_club, claimed_foreign_bank:state.created_bank,
    deleted_foreign_tables:deletes};
}
Promise.all([mainRegression(), ownershipRace()]).then(([main, ownership]) => {
  console.log(JSON.stringify({main_default:main,ownership_race:ownership},null,2));
}).catch(error => {console.error(error.message);process.exitCode=1;});
