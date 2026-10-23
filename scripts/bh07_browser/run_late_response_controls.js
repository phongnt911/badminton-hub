const assert = require('node:assert/strict');
const { validateLateResponse } = require('./late_response_assertions');
const { FIXTURE } = require('./assertions');
const base = {
  actor: 'cohosta', ownerPositive: true, ownerNegativePassed: true, method: 'POST', status: 200, sessionId: FIXTURE.uiSessionId,
  ownerFinance: true, expenses: 200000, bodyHash: 'real-body-sha', deliveredHash: 'real-body-sha',
  heldAt: 1, guestAt: 2, loginAt: 3, releaseAt: 4, deliveredAt: 5,
  originBefore: 1234, originAfter: 1234, ownerProfile: true, targetProfile: 'cohosta@example.test',
  guestVerified: true, tokenCleared: true,
  samples: Array.from({ length: 3 }, () => ({ financeCard: false, ownerProfile: false, summaryEntryForMember: false, privacyErrors: [] })), surface: [{ text: 'Chỉ xem số lượng' }],
  clipboard: `🏸 Tổng kết: ${FIXTURE.uiSessionTitle}\n📍 HTTP Venue A · HTTP Club A\n⏰ 12:00 - 14:00 23/10/2026\n${FIXTURE.cohostCountsLine}`,
};
const member = { ...base, actor: 'membera', targetProfile: 'membera@example.test', memberHistoryEmpty: true, copyAvailable: false, summaryEntry: false, surface: [{ text: 'Lịch sử buổi\nChưa có buổi nào' }] };
const cases = [
  ['cohost positive', base, true],
  ['member positive', member, true],
  ...[
    ['no Owner positive', { ownerPositive: false }],
    ['missing real Owner negative control', { ownerNegativePassed: false }],
    ['preflight mistaken for POST', { method: 'OPTIONS' }],
    ['wrong HTTP status', { status: 403 }],
    ['wrong session', { sessionId: 'other' }],
    ['not privileged response', { ownerFinance: false }],
    ['wrong fixture amount', { expenses: 0 }],
    ['changed body', { deliveredHash: 'different' }],
    ['released before login', { releaseAt: 2 }],
    ['not delivered', { deliveredAt: 0 }],
    ['reload hides stale state', { originAfter: 4321 }],
    ['wrong actor', { targetProfile: 'ownera@example.test' }],
    ['no guest UI', { guestVerified: false }],
    ['token remains', { tokenCleared: false }],
    ['no samples', { samples: [] }],
    ['finance card leak', { samples: base.samples.map((sample, index) => ({ ...sample, financeCard: index === 0 })) }],
    ['clipboard leak', { clipboard: base.clipboard + '\nĐã thu: 999 VNĐ' }],
    ['cohost surface leak', { surface: [{ text: 'Chỉ xem số lượng\nTài chính tổng hợp' }] }],
  ].map(([name, patch]) => [name, { ...base, ...patch }, false]),
  ['Member gains copy', { ...member, copyAvailable: true }, false],
];
const results = cases.map(([name, witness, expected]) => {
  const errors = validateLateResponse(witness); const actual = errors.length === 0;
  assert.equal(actual, expected, `${name}: ${errors.join('; ')}`);
  return { name, expected: expected ? 'PASS' : 'FAIL', actual: actual ? 'PASS' : 'FAIL', errors };
});
console.log(JSON.stringify(results, null, 2));
console.log(`Controls: ${results.length}/${results.length} behave as expected`);

// Mutation checks run the real predicate with one guard disabled in memory.
// Each isolated control must expose its own regression, without other errors.
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync(require.resolve('./late_response_assertions'), 'utf8');
for (const [guard, replacement, control] of [
  ['w.copyAvailable !== false', 'false', 'Member gains copy'],
  ['sample.financeCard !== false', 'false', 'finance card leak'],
]) {
  assert.ok(source.includes(guard), `guard not found: ${guard}`);
  const moduleCopy = { exports: {} };
  vm.runInNewContext(source.replace(guard, replacement), { module: moduleCopy, require });
  const mutant = moduleCopy.exports.validateLateResponse;
  const mismatches = cases.filter(([, witness, expected]) => (mutant(witness).length === 0) !== expected);
  assert.ok(mismatches.some(([name]) => name === control), `mutant escaped isolated control: ${control}`);
  console.log(`Mutation caught: ${control}`);
}
