const assert = require('node:assert/strict');
const { validateLateResponse } = require('./late_response_assertions');
const { FIXTURE } = require('./assertions');
const base = {
  actor: 'cohosta', ownerPositive: true, ownerNegativePassed: true, method: 'POST', status: 200, sessionId: FIXTURE.uiSessionId,
  ownerFinance: true, expenses: 200000, bodyHash: 'real-body-sha', deliveredHash: 'real-body-sha',
  heldAt: 1, guestAt: 2, loginAt: 3, releaseAt: 4, deliveredAt: 5,
  originBefore: 1234, originAfter: 1234, ownerProfile: true, targetProfile: 'cohosta@example.test',
  guestVerified: true, tokenCleared: true,
  samples: Array.from({ length: 3 }, () => ({ financeCard: false, ownerProfile: false, summaryEntryForMember: false })), surface: [{ text: 'Chỉ xem số lượng' }],
  clipboard: `🏸 Tổng kết: ${FIXTURE.uiSessionTitle}\n📍 HTTP Venue A · HTTP Club A\n⏰ 12:00 - 14:00 23/10/2026\n${FIXTURE.cohostCountsLine}`,
};
const cases = [
  ['cohost positive', base, true],
  ['member positive', { ...base, actor: 'membera', targetProfile: 'membera@example.test', memberHistoryEmpty: true }, true],
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
    ['finance card leak', { samples: [{ financeCard: true }, {}, {}] }],
    ['clipboard leak', { clipboard: base.clipboard + '\nĐã thu: 999 VNĐ' }],
    ['cohost surface leak', { surface: [{ text: 'Chỉ xem số lượng\nTài chính tổng hợp' }] }],
  ].map(([name, patch]) => [name, { ...base, ...patch }, false]),
  ['Member gains copy', { ...base, actor: 'membera', targetProfile: 'membera@example.test', memberHistoryEmpty: true, copyAvailable: true }, false],
];
const results = cases.map(([name, witness, expected]) => {
  const errors = validateLateResponse(witness); const actual = errors.length === 0;
  assert.equal(actual, expected, `${name}: ${errors.join('; ')}`);
  return { name, expected: expected ? 'PASS' : 'FAIL', actual: actual ? 'PASS' : 'FAIL', errors };
});
console.log(JSON.stringify(results, null, 2));
console.log(`Controls: ${results.length}/${results.length} behave as expected`);
