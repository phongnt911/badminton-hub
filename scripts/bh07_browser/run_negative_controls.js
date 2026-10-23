// Execute the current BR2/BR3 predicates from assertions.js against synthetic
// negative and positive controls. Every case is awaited, every result is
// recorded, and the exact expected case count is enforced.
//
// This script intentionally fails when a required marker disappears, when a
// predicate throws, or when a positive control is rejected. It is not allowed
// to treat "old regex not found" as a successful control.

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const EVIDENCE_DIR = path.resolve(PROJECT_ROOT, 'docs/reviews/bh07/browser_evidence');
const RUNNER_PATH = path.resolve(__dirname, 'run_browser_verification.js');
const ASSERTIONS_PATH = path.resolve(__dirname, 'assertions.js');
const EXPECTED_CASE_COUNT = 27;

const A = require('./assertions');
const {
  FIXTURE,
  OFFLINE_ERROR_MESSAGE,
  OFFLINE_SUCCESS_MESSAGE,
} = A;

function elements(...texts) {
  return texts.map((text) => ({ tag: 'DIV', role: 'text', text, aria: null, x: 1, y: 1, w: 20, h: 20 }));
}

const managerClipboard = [
  `🏸 Tổng kết: ${FIXTURE.uiSessionTitle}`,
  '📍 HTTP Venue A · HTTP Club A',
  '⏰ 23:30 22/10/2026 - 01:40 23/10/2026',
  FIXTURE.cohostCountsLine,
  '💰 Tổng chi phí: 200,000 VNĐ',
  '🧾 Tổng phải thu: 200,000 VNĐ',
  '✅ Đã thu: 0 VNĐ',
  '⏳ Còn phải thu: 200,000 VNĐ',
].join('\n');

const cohostClipboard = [
  `🏸 Tổng kết: ${FIXTURE.uiSessionTitle}`,
  '📍 HTTP Venue A · HTTP Club A',
  '⏰ 23:30 22/10/2026 - 01:40 23/10/2026',
  FIXTURE.cohostCountsLine,
].join('\n');

const validCompleteRequests = [
  {
    url: 'http://127.0.0.1:54321/rpc/complete_session',
    method: 'POST',
    postData: {
      p_request_id: '00000000-0000-4000-8000-000000000001',
      p_session_id: FIXTURE.uiSessionId,
      p_expected_version: 3,
    },
  },
  {
    url: 'http://127.0.0.1:54321/rpc/complete_session',
    method: 'POST',
    postData: {
      p_request_id: '00000000-0000-4000-8000-000000000001',
      p_session_id: FIXTURE.uiSessionId,
      p_expected_version: 3,
    },
  },
];

const cases = [
  {
    name: 'offline positive: exact transport error is visible on the finance route',
    expected: 'PASS',
    run: () => A.validateOfflineUiState(elements('Tài chính buổi', OFFLINE_ERROR_MESSAGE)),
  },
  {
    name: 'offline negative: silent no-error/no-success UI',
    expected: 'FAIL',
    run: () => A.validateOfflineUiState(elements('Tài chính buổi', 'Kết thúc buổi chơi')),
  },
  {
    name: 'offline negative: success-only UI while offline',
    expected: 'FAIL',
    run: () => A.validateOfflineUiState(elements('Tài chính buổi', OFFLINE_SUCCESS_MESSAGE)),
  },
  {
    name: 'offline negative: error shown outside the finance lifecycle',
    expected: 'FAIL',
    run: () => A.validateOfflineUiState(elements('Tổng kết buổi', OFFLINE_ERROR_MESSAGE)),
  },
  {
    name: 'manager positive: all four exact aggregate fields',
    expected: 'PASS',
    run: () => A.validateManagerClipboard(managerClipboard),
  },
  {
    name: 'manager negative: one wrong aggregate field',
    expected: 'FAIL',
    run: () => A.validateManagerClipboard(managerClipboard.replace('Đã thu: 0 VNĐ', 'Đã thu: 50,000 VNĐ')),
  },
  {
    name: 'manager negative: outstanding field is the null marker',
    expected: 'FAIL',
    run: () => A.validateManagerClipboard(managerClipboard.replace('Còn phải thu: 200,000 VNĐ', 'Còn phải thu: —')),
  },
  {
    name: 'manager negative: missing aggregate field',
    expected: 'FAIL',
    run: () => A.validateManagerClipboard(managerClipboard.replace('✅ Đã thu: 0 VNĐ\n', '')),
  },
  {
    name: 'manager negative: title contains 200000 while finance fields are null',
    expected: 'FAIL',
    run: () => A.validateManagerClipboard([
      '🏸 Tổng kết: Buổi 200000',
      FIXTURE.cohostCountsLine,
      '💰 Tổng chi phí: —',
      '🧾 Tổng phải thu: —',
      '✅ Đã thu: —',
      '⏳ Còn phải thu: —',
    ].join('\n')),
  },
  {
    name: 'cohost positive: only header/place/time/count lines',
    expected: 'PASS',
    run: () => A.validateCohostClipboard(cohostClipboard),
  },
  {
    name: 'cohost negative: finance field with null marker',
    expected: 'FAIL',
    run: () => A.validateCohostClipboard(`${cohostClipboard}\n🧾 Tổng phải thu: —`),
  },
  {
    name: 'cohost negative: money value',
    expected: 'FAIL',
    run: () => A.validateCohostClipboard(`${cohostClipboard}\n✅ Đã thu: 50,000 VNĐ`),
  },
  {
    name: 'cohost negative: phone and bank account fields',
    expected: 'FAIL',
    run: () => A.validateCohostClipboard(`${cohostClipboard}\nSĐT: 0987654321\nSTK: 123456789012`),
  },
  {
    name: 'cohost UI positive: management-only surface with counts',
    expected: 'PASS',
    run: () => A.validateCohostSummarySurface(elements(
      'Chỉ xem số lượng',
      'Số lượng người',
      'Có mặt',
      '1',
      'Vắng',
      '1',
      'Đã xác nhận',
      '2',
    )),
  },
  {
    name: 'cohost UI negative: finance card is visible',
    expected: 'FAIL',
    run: () => A.validateCohostSummarySurface(elements('Chỉ xem số lượng', 'Tài chính tổng hợp')),
  },
  {
    name: 'cohost UI negative: finance field with null marker is visible',
    expected: 'FAIL',
    run: () => A.validateCohostSummarySurface(elements('Chỉ xem số lượng', 'Tổng phải thu: —')),
  },
  {
    name: 'history positive: Cohost Club A exact one permitted row',
    expected: 'PASS',
    run: () => A.validateHistorySurface(
      elements('Lịch sử buổi', 'HTTP Club A', FIXTURE.uiSessionTitle, 'Đã kết thúc', 'Xem chi tiết'),
      FIXTURE.cohostExpectedTitles,
      false,
    ),
  },
  {
    name: 'history negative: Cohost receives an extra Club B row',
    expected: 'FAIL',
    run: () => A.validateHistorySurface(
      elements('Lịch sử buổi', 'HTTP Club A', FIXTURE.uiSessionTitle, 'HTTP club B history', 'Xem chi tiết', 'Xem chi tiết'),
      FIXTURE.cohostExpectedTitles,
      false,
    ),
  },
  {
    name: 'history positive: Member exact empty state',
    expected: 'PASS',
    run: () => A.validateHistorySurface(
      elements('Lịch sử buổi', 'Tất cả CLB', 'Chưa có buổi nào', 'Các buổi đã kết thúc hoặc đã huỷ sẽ xuất hiện ở đây.'),
      FIXTURE.memberExpectedTitles,
      true,
    ),
  },
  {
    name: 'history negative: Member receives a Club B row',
    expected: 'FAIL',
    run: () => A.validateHistorySurface(
      elements('Lịch sử buổi', 'Chưa có buổi nào', 'HTTP club B history', 'Xem chi tiết'),
      FIXTURE.memberExpectedTitles,
      true,
    ),
  },
  {
    name: 'history negative: Member receives treasury/finance text',
    expected: 'FAIL',
    run: () => A.validateHistorySurface(
      elements('Lịch sử buổi', 'Chưa có buổi nào', 'Quỹ CLB', 'Số dư'),
      FIXTURE.memberExpectedTitles,
      true,
    ),
  },
  {
    name: 'history negative: error/empty ambiguity is rejected',
    expected: 'FAIL',
    run: () => A.validateHistorySurface(
      elements('Lịch sử buổi', 'Không tải được lịch sử', 'Chưa có buổi nào'),
      FIXTURE.memberExpectedTitles,
      true,
    ),
  },
  {
    name: 'history request negative: wrong club filter payload',
    expected: 'FAIL',
    run: () => A.validateHistoryCall({ postData: { p_club_id: FIXTURE.clubBId } }, FIXTURE.clubAId),
  },
  {
    name: 'history response negative: wrong ID set',
    expected: 'FAIL',
    run: () => A.validateHistoryIds([FIXTURE.clubBHistorySessionId], [FIXTURE.uiSessionId]),
  },
  {
    name: 'complete_session positive: two identical POST payloads',
    expected: 'PASS',
    run: () => A.validateCompleteRequests(validCompleteRequests),
  },
  {
    name: 'complete_session negative: missing retry request',
    expected: 'FAIL',
    run: () => A.validateCompleteRequests([validCompleteRequests[0]]),
  },
  {
    name: 'complete_session negative: full payload differs on retry',
    expected: 'FAIL',
    run: () => A.validateCompleteRequests([
      validCompleteRequests[0],
      { ...validCompleteRequests[1], postData: { ...validCompleteRequests[1].postData, p_expected_version: 9 } },
    ]),
  },
];

function requireMarkers() {
  const runner = fs.readFileSync(RUNNER_PATH, 'utf8');
  const assertions = fs.readFileSync(ASSERTIONS_PATH, 'utf8');
  const requiredRunnerMarkers = [
    'validateOfflineUiState(',
    'validateCompleteRequests(',
    'validateManagerClipboard(',
    'validateCohostClipboard(',
    'validateCohostSummarySurface(',
    'validateHistoryCall(',
    'validateHistoryIds(',
    'validateHistorySurface(',
  ];
  const requiredAssertionMarkers = [
    'BR3_MANAGER_GATE',
    'function validateManagerClipboard(',
    'function validateCohostClipboard(',
    'function validateHistorySurface(',
  ];
  const missing = [];
  for (const marker of requiredRunnerMarkers) {
    if (!runner.includes(marker)) missing.push(`runner marker missing: ${marker}`);
  }
  for (const marker of requiredAssertionMarkers) {
    if (!assertions.includes(marker)) missing.push(`assertion marker missing: ${marker}`);
  }
  return missing;
}

async function executeCase(testCase) {
  try {
    const errors = await testCase.run();
    if (!Array.isArray(errors)) {
      return { control: testCase.name, expected: testCase.expected, actual: 'HARNESS_ERROR', detail: 'predicate did not return an errors array' };
    }
    return {
      control: testCase.name,
      expected: testCase.expected,
      actual: errors.length === 0 ? 'PASS' : 'FAIL',
      detail: errors.join('; '),
    };
  } catch (err) {
    return {
      control: testCase.name,
      expected: testCase.expected,
      actual: 'HARNESS_ERROR',
      detail: err && err.stack ? err.stack : String(err),
    };
  }
}

async function main() {
  console.log('=== Running BH-07 current-predicate negative controls ===');
  const markerErrors = requireMarkers();
  const results = [];
  for (const testCase of cases) {
    // Await each case explicitly: no detached promises and no silent catch.
    results.push(await executeCase(testCase));
  }

  const mismatches = results.filter((result) => result.actual !== result.expected);
  const caseCountError = cases.length !== EXPECTED_CASE_COUNT
    ? `expected ${EXPECTED_CASE_COUNT} cases, built ${cases.length}`
    : results.length !== EXPECTED_CASE_COUNT
      ? `expected ${EXPECTED_CASE_COUNT} results, recorded ${results.length}`
      : null;
  const passed = markerErrors.length === 0 && caseCountError === null && mismatches.length === 0;

  console.log(JSON.stringify(results, null, 2));
  if (markerErrors.length > 0) {
    for (const error of markerErrors) console.error(`[X] ${error}`);
  }
  if (caseCountError) console.error(`[X] ${caseCountError}`);
  for (const mismatch of mismatches) {
    console.error(`[X] ${mismatch.control}: expected ${mismatch.expected}, got ${mismatch.actual}${mismatch.detail ? ` (${mismatch.detail})` : ''}`);
  }
  console.log(`\nRecorded ${results.length}/${EXPECTED_CASE_COUNT} cases; ${results.filter((result) => result.actual === 'PASS').length} PASS, ${results.filter((result) => result.actual === 'FAIL').length} FAIL, ${results.filter((result) => result.actual === 'HARNESS_ERROR').length} HARNESS_ERROR.`);
  console.log(`\nOVERALL NEGATIVE CONTROLS STATUS: ${passed ? 'GREEN (all current-predicate controls behave as expected)' : 'RED (predicate or harness failure)'}`);

  if (!fs.existsSync(EVIDENCE_DIR)) fs.mkdirSync(EVIDENCE_DIR, { recursive: true });
  let sourceSha = process.env.BH07_SOURCE_SHA || '';
  if (!sourceSha) {
    try {
      sourceSha = require('child_process').execSync('git rev-parse HEAD', {
        cwd: PROJECT_ROOT,
        encoding: 'utf8',
      }).trim();
    } catch (_) {
      sourceSha = 'UNKNOWN';
    }
  }
  const output = {
    generated_at_utc: new Date().toISOString(),
    source_sha: sourceSha,
    assertions_sha256: crypto.createHash('sha256').update(fs.readFileSync(ASSERTIONS_PATH)).digest('hex'),
    runner_sha256: crypto.createHash('sha256').update(fs.readFileSync(RUNNER_PATH)).digest('hex'),
    expected_case_count: EXPECTED_CASE_COUNT,
    recorded_case_count: results.length,
    marker_errors: markerErrors,
    case_count_error: caseCountError,
    mismatches,
    results,
  };
  fs.writeFileSync(path.resolve(EVIDENCE_DIR, 'negative_controls.json'), JSON.stringify(output, null, 2) + '\n', 'utf-8');
  process.exit(passed ? 0 : 1);
}

main().catch((err) => {
  console.error('FATAL negative-control harness error:', err && err.stack ? err.stack : err);
  process.exit(1);
});
