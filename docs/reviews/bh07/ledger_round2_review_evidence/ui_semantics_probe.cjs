// Replay LGR6 against the current runner; no browser or DB is opened.
const path = require('node:path');
const realTimeout = global.setTimeout;
global.setTimeout = (fn) => realTimeout(fn, 0);
const {openOwnerLedger} = require(path.resolve(__dirname, '../../../..', 'scripts/bh07_appheap/run_app_profile_heap.js'));
async function scenario(ariaOnly) {
  const nodes = [
    {role:'tab', aria:'Buổi Chơi', text:''}, {role:'tab', aria:'CLB & Quỹ', text:''}, {role:'tab', aria:'Tài Khoản', text:''},
    {role:'button', aria:'Synthetic owned club', text:''}, {role:'button', aria:'THU QUỸ', text:''},
    {role:'button', aria:'Huỷ', text:ariaOnly ? '' : 'Huỷ'},
    {role:'text', aria:'Giao dịch', text:''}, {role:'text', aria:'Synthetic ledger title', text:''},
  ];
  const clicks = [];
  const fake = {
    getAllSemantics: async () => nodes,
    clickBack: async () => {},
    clickSemantic: async (predicate, label) => {
      const node = nodes.find(predicate); if (!node) throw Error(label); clicks.push(label); return node;
    },
    waitForSemantic: async (predicate, label) => {
      const node = nodes.find(predicate); if (!node) throw Error(label); return node;
    },
  };
  try { await openOwnerLedger(fake, 'Synthetic owned club', 'Synthetic ledger title'); return {pass:true, clicks}; }
  catch (error) { return {pass:false, step:error.message, clicks}; }
}
(async () => {
  const result = {text_cancel:await scenario(false), aria_only_cancel:await scenario(true)};
  console.log(JSON.stringify(result, null, 2));
  if (!result.text_cancel.pass || !result.aria_only_cancel.pass) process.exitCode=1;
})().catch(() => { process.exitCode=1; });
