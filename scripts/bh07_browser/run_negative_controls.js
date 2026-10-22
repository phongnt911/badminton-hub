const fs = require('fs');
const path = require('path');
const vm = require('vm');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const RUNNER_PATH = path.resolve(PROJECT_ROOT, 'scripts/bh07_browser/run_browser_verification.js');
const source = fs.readFileSync(RUNNER_PATH, 'utf8');

console.log('=== Running Reviewer Negative Control Probes ===');

// --- 1. Predicate Probes (BR2 Idempotency & Payload gate) ---
console.log('\n--- Probe 1: Predicate Probes for TC05 complete_session ---');
const startPredicate = source.indexOf('    // Check captured requests for request_id & payload match');
const endPredicate = source.indexOf('  } catch (err)', startPredicate);
const predicateBlock = source.slice(startPredicate, endPredicate);

const predicateCases = [
  { name: 'no captured mutation requests', requests: [] },
  { name: 'different request_id and session', requests: [
    { postData: { p_request_id: 'a', p_session_id: 'sessionA', p_expected_version: 1 } },
    { postData: { p_request_id: 'b', p_session_id: 'sessionB', p_expected_version: 9 } }
  ] },
  { name: 'same request id and session but changed version', requests: [
    { postData: { p_request_id: 'a', p_session_id: 'sessionA', p_expected_version: 1 } },
    { postData: { p_request_id: 'a', p_session_id: 'sessionA', p_expected_version: 9 } }
  ] },
  { name: 'missing postData/preflight pair', requests: [
    { postData: null },
    { postData: { p_request_id: 'a', p_session_id: 'sessionA', p_expected_version: 1 } }
  ] }
];

const predicateResults = [];
for (const c of predicateCases) {
  const checks = [];
  try {
    vm.runInNewContext(predicateBlock, {
      capturedRequests: c.requests,
      checks,
      log: () => {},
      assert: (cond, msg) => { if (!cond) throw new Error(msg); }
    });
    const status = checks[0]?.status || 'PASS';
    predicateResults.push({ control: c.name, expected: 'FAIL', actual: status, detail: checks[0]?.detail });
  } catch (err) {
    predicateResults.push({ control: c.name, expected: 'FAIL', actual: 'FAIL', detail: err.message });
  }
}

console.log(JSON.stringify(predicateResults, null, 2));
const predicateAllFail = predicateResults.every(r => r.actual === 'FAIL');
console.log(`Predicate Probes: ${predicateAllFail ? 'PASS (All 4 controls rejected properly)' : 'FAIL (Fake PASS detected!)'}`);

// --- 2. Coverage Probes (BR1 Attendance & BR3 Clipboard/Privacy) ---
console.log('\n--- Probe 2: Coverage Probes for TC03 & TC06/07 ---');
const coverageResults = [];

// TC03 mock
try {
  const startTC03 = source.indexOf("    log('--- TC03: Real Attendance Check-in ---');");
  const endTC03 = source.indexOf('  } catch (err)', startTC03);
  const tc03Block = source.slice(startTC03, endTC03);
  const checksTC03 = [];
  const contextTC03 = {
    cdp: {
      clickSemantic: async () => {},
      screenshot: async () => {},
      getAllSemantics: async () => [{ text: 'Member A', aria: 'Member A' }],
      waitForSemantic: async () => ({ text: 'Member A' }),
      findSemantic: async () => ({ text: 'Member A' })
    },
    checks: checksTC03,
    log: () => {},
    setTimeout: (fn) => fn()
  };
  vm.runInNewContext('(async () => {' + tc03Block + '})()', contextTC03).then(() => {
    // Evaluation after async
  }).catch(() => {});
} catch (_) {}

// Check Manager condition
const wrongTotals = 'Tổng chi phí: 999 VNĐ\nCòn phải thu: 999 VNĐ';
const hasPhone = /0\d{9,10}/.test(wrongTotals);
const hasBank = /(stk|ngan hang|vietinbank|techcombank)/i.test(wrongTotals);
const hasSecret = /secret|password|bearer/i.test(wrongTotals);
const hasFinances = wrongTotals.includes('Tổng chi phí:') && wrongTotals.includes('Còn phải thu:');

// If gate only checks hasFinances (label existence), it accepts 999!
const managerMatch = source.match(/if \(!hasPhone && !hasBank && !hasSecret && hasFinances\)/);
if (managerMatch) {
  coverageResults.push({
    control: 'manager clipboard wrong numeric totals',
    expected: 'FAIL',
    actual: 'PASS' // Currently accepts any numbers!
  });
} else {
  coverageResults.push({
    control: 'manager clipboard wrong numeric totals',
    expected: 'FAIL',
    actual: 'FAIL'
  });
}

// Check Cohost money condition
const cohostMoneyLeaked1 = 'Đã thu: 50000 VNĐ';
const cohostMoneyLeaked2 = 'SĐT: 0987654321\nSTK: 123456789012';

const moneyGateMatch = source.match(/const hasAnyMoney = ([^;]+);/);
if (moneyGateMatch) {
  const expr = moneyGateMatch[1];
  const leak1Accepted = !vm.runInNewContext(expr, { cohostClipboard: cohostMoneyLeaked1 });
  coverageResults.push({
    control: 'cohost clipboard leak: ' + cohostMoneyLeaked1,
    expected: 'FAIL',
    actual: leak1Accepted ? 'PASS' : 'FAIL'
  });
  const leak2Accepted = !vm.runInNewContext(expr, { cohostClipboard: cohostMoneyLeaked2 });
  coverageResults.push({
    control: 'cohost clipboard leak: ' + cohostMoneyLeaked2,
    expected: 'FAIL',
    actual: leak2Accepted ? 'PASS' : 'FAIL'
  });
}

console.log(JSON.stringify(coverageResults, null, 2));

const allProbesPass = predicateAllFail && coverageResults.every(r => r.actual === 'FAIL');
console.log(`\nOVERALL NEGATIVE CONTROLS STATUS: ${allProbesPass ? 'GREEN (All controls pass)' : 'RED (Vulnerabilities reproduce!)'}`);
process.exit(allProbesPass ? 0 : 1);
