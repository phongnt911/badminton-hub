const { FIXTURE, validateCohostClipboard, validateCohostSummarySurface, validateHistorySurface } = require('./assertions');

function validateLateResponse(w) {
  const errors = [];
  if (!['cohosta', 'membera'].includes(w.actor)) errors.push('unknown target actor');
  if (!w.ownerNegativePassed) errors.push('actual Owner UI negative control did not reject privilege');
  if (!w.ownerPositive) errors.push('owner finance UI/clipboard positive control missing');
  if (w.method !== 'POST' || w.status !== 200 || w.sessionId !== FIXTURE.uiSessionId || w.ownerFinance !== true || w.expenses !== 200000) {
    errors.push('not a real privileged Owner summary 200 for the fixture');
  }
  if (!w.bodyHash || w.bodyHash !== w.deliveredHash) errors.push('held/delivered response body mismatch');
  if (!w.heldAt || !(w.heldAt < w.guestAt && w.guestAt < w.loginAt && w.loginAt < w.releaseAt && w.releaseAt <= w.deliveredAt)) {
    errors.push('response did not remain held across logout and target login');
  }
  if (!w.originBefore || w.originBefore !== w.originAfter) errors.push('SPA document changed');
  if (!w.ownerProfile || w.targetProfile !== `${w.actor}@example.test`) errors.push('UI actor identity not verified');
  if (!w.guestVerified || !w.tokenCleared) errors.push('logout guest/token precondition missing');
  if (!Array.isArray(w.samples) || w.samples.length < 3) errors.push('missing post-release UI samples');
  for (const sample of w.samples || []) {
    if (sample.financeCard !== false || sample.ownerProfile !== false || sample.summaryEntryForMember !== false || !Array.isArray(sample.privacyErrors) || sample.privacyErrors.length > 0) errors.push('stale privileged UI leaked');
  }
  if (w.actor === 'cohosta') {
    errors.push(...validateCohostSummarySurface(w.surface), ...validateCohostClipboard(w.clipboard));
  } else {
    errors.push(...validateHistorySurface(w.surface, [], true));
    if (w.copyAvailable !== false || w.summaryEntry !== false || w.memberHistoryEmpty !== true) {
      errors.push('Member gained summary/copy or lost isolated empty history');
    }
  }
  return errors;
}
module.exports = { validateLateResponse };
