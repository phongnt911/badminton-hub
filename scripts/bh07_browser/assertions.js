// Shared BR2/BR3 predicates for the BH-07 browser verification suite.
//
// The real browser runner and the negative-control runner both import these
// functions. A negative control therefore exercises the predicate that is
// actually used against the UI, not a copied regex or an old source block.

const FIXTURE = Object.freeze({
  clubAId: 'aaaaaaaa-1111-4111-8111-111111111111',
  clubBId: 'bbbbbbbb-2222-4222-8222-222222222222',
  uiSessionId: '10000000-0000-4000-8000-000000000099',
  clubBHistorySessionId: '20000000-0000-4000-8000-000000000001',
  uiSessionTitle: 'UI Flow Session published to complete',
  clubBHistoryTitle: 'HTTP club B history',
  managerFinance: Object.freeze({
    'Tổng chi phí': '200,000 VNĐ',
    'Tổng phải thu': '200,000 VNĐ',
    'Đã thu': '0 VNĐ',
    'Còn phải thu': '200,000 VNĐ',
  }),
  cohostCountsLine: '👥 Có mặt: 1 · Vắng: 0 · Đã xác nhận: 2',
  cohostExpectedTitles: Object.freeze(['UI Flow Session published to complete']),
  memberExpectedTitles: Object.freeze([]),
  historyFixtureTitles: Object.freeze([
    'UI Flow Session published to complete',
    'HTTP finance after complete',
    'HTTP cancelled history',
    'HTTP private history',
    'HTTP club B history',
    'HTTP concurrency complete replay',
    'HTTP concurrency complete competing',
    'HTTP concurrency payments',
    'HTTP concurrency transport drop',
  ]),
});

const OFFLINE_ERROR_MESSAGE = 'Đã xảy ra lỗi. Vui lòng thử lại sau.';
const OFFLINE_SUCCESS_MESSAGE = 'Đã kết thúc buổi chơi.';
const FINANCE_LABELS = [
  'Tổng chi phí',
  'Tổng phải thu',
  'Đã thu',
  'Còn phải thu',
  'Tiền sân',
  'Tiền cầu',
  'Phụ thu',
  'Chi phí',
  'Thu chi',
  'Số dư',
  'Quỹ CLB',
];
const PRIVATE_PATTERNS = [
  { label: 'phone number', re: /(?:\+84|0)\d{8,10}/ },
  {
    label: 'contact/bank/account/receiver field',
    re: /stk|số tài khoản|so tai khoan|ngân hàng|ngan hang|bank|account|receiver|người nhận|nguoi nhan|liên hệ|lien he|điện thoại|dien thoai|sđt|sdt/i,
  },
  { label: 'secret/token field', re: /secret|password|bearer|token/i },
  { label: 'private fixture marker', re: /BH07[- ]?PRIVATE|\+84900000004|0000000007|0000000008/i },
];
const MONEY_RE = /(?:\d{1,3}(?:[.,]\d{3})+|\d+)\s*(?:vnđ|vnd|đ)(?![\p{L}\p{N}_])/iu;
const HISTORY_ERROR_TEXTS = [
  'Không tải được lịch sử',
  'Chưa làm mới được lịch sử',
  'Cần đăng nhập',
];
const HISTORY_FORBIDDEN_TEXTS = [
  'HTTP Club B',
  'HTTP club B history',
  'Ba Ngòi',
  'Quỹ CLB',
  'Số dư',
  'Tổng chi phí',
  'Tổng phải thu',
  'Đã thu',
  'Còn phải thu',
];

function normalizeText(value) {
  return String(value == null ? '' : value)
    .replace(/\u00a0/g, ' ')
    .replace(/\r\n?/g, '\n')
    .trim();
}

function semanticTexts(elements) {
  return (Array.isArray(elements) ? elements : [])
    .map((element) => {
      const parts = [element && element.text, element && element.aria]
        .map(normalizeText)
        .filter(Boolean);
      return parts.join('\n');
    })
    .filter(Boolean);
}

function semanticJoined(elements) {
  return semanticTexts(elements).join('\n');
}

function lineCount(joined, needle) {
  return normalizeText(joined)
    .split('\n')
    .filter((line) => line.includes(needle)).length;
}

function extractLabeledValues(text, label) {
  const values = [];
  for (const line of normalizeText(text).split('\n')) {
    const marker = `${label}:`;
    const index = line.indexOf(marker);
    if (index >= 0) values.push(line.slice(index + marker.length).trim());
  }
  return values;
}

function privacyErrors(text) {
  const errors = [];
  for (const pattern of PRIVATE_PATTERNS) {
    if (pattern.re.test(text)) errors.push(`private ${pattern.label} leaked`);
  }
  return errors;
}

function validateOfflineUiState(elements) {
  const joined = semanticJoined(elements);
  const errors = [];
  if (!joined.includes(OFFLINE_ERROR_MESSAGE)) {
    errors.push(`offline error message "${OFFLINE_ERROR_MESSAGE}" was not rendered`);
  }
  if (joined.includes(OFFLINE_SUCCESS_MESSAGE)) {
    errors.push('false success message was rendered while offline');
  }
  if (!joined.includes('Tài chính buổi') && !joined.includes('Kết thúc buổi chơi')) {
    errors.push('finance screen/route was not retained after the offline failure');
  }
  return errors;
}

function validateCompleteRequests(requests) {
  const errors = [];
  if (!Array.isArray(requests) || requests.length !== 2) {
    errors.push(`expected exactly 2 complete_session POST requests, got ${Array.isArray(requests) ? requests.length : 'not-an-array'}`);
    return errors;
  }
  requests.forEach((request, index) => {
    if (!request || request.method !== 'POST' || !String(request.url || '').includes('/rpc/complete_session')) {
      errors.push(`request ${index + 1} is not a POST to /rpc/complete_session`);
    }
    if (!request || !request.postData || typeof request.postData !== 'object') {
      errors.push(`request ${index + 1} is missing valid postData`);
    }
  });
  if (errors.length > 0) return errors;

  const first = requests[0].postData;
  const second = requests[1].postData;
  if (!first.p_request_id || first.p_request_id !== second.p_request_id) {
    errors.push('request_id differs between the offline request and the retry');
  }
  if (first.p_session_id !== second.p_session_id) {
    errors.push('session id differs between the offline request and the retry');
  }
  if (first.p_expected_version !== second.p_expected_version) {
    errors.push('expected version differs between the offline request and the retry');
  }
  const canonical = (value) => JSON.stringify(
    Object.keys(value || {}).sort().reduce((acc, key) => {
      acc[key] = value[key];
      return acc;
    }, {}),
  );
  if (canonical(first) !== canonical(second)) {
    errors.push('full complete_session payload differs between the offline request and the retry');
  }
  return errors;
}

function validateManagerClipboard(text, expected = FIXTURE.managerFinance) {
  const normalized = normalizeText(text);
  const errors = [];
  if (!normalized) return ['manager clipboard is empty'];
  if (!normalized.includes(FIXTURE.uiSessionTitle)) {
    errors.push(`manager clipboard is missing session title "${FIXTURE.uiSessionTitle}"`);
  }
  if (!normalized.includes(FIXTURE.cohostCountsLine)) {
    errors.push('manager clipboard is missing the exact attendance-count line');
  }

  for (const [label, expectedValue] of Object.entries(expected)) {
    const values = extractLabeledValues(normalized, label);
    if (values.length !== 1) {
      errors.push(`${label}: expected exactly one field, got ${values.length}`);
    } else if (values[0] !== expectedValue) {
      errors.push(`${label}: expected "${expectedValue}", got "${values[0]}"`);
    }
  }
  // This fixture has exactly four metadata lines and four finance lines.
  // A blacklist of known finance labels cannot reject an unknown extra field.
  const lines = normalized.split('\n').map((line) => line.trim()).filter(Boolean);
  const metadataPatterns = [
    /^🏸 Tổng kết: UI Flow Session published to complete$/,
    /^📍 .+$/,
    /^⏰ .+$/,
    /^👥 Có mặt: 1 · Vắng: 0 · Đã xác nhận: 2$/,
  ];
  const financeLines = Object.entries(expected).map(([label, value], index) =>
    `${['💰', '🧾', '✅', '⏳'][index]} ${label}: ${value}`);
  for (const pattern of metadataPatterns) {
    const matches = lines.filter((line) => pattern.test(line));
    if (matches.length !== 1) errors.push(`expected exactly one metadata line matching ${pattern}`);
    if (matches.some((line) => MONEY_RE.test(line))) errors.push('money value in manager metadata');
  }
  for (const line of lines) {
    if (!metadataPatterns.some((pattern) => pattern.test(line)) && !financeLines.includes(line)) {
      errors.push(`manager clipboard contains a non-allowed line: "${line}"`);
    }
  }
  if (lines.length !== metadataPatterns.length + financeLines.length) {
    errors.push('manager clipboard has an unexpected line count');
  }
  for (const label of FINANCE_LABELS) {
    if (Object.prototype.hasOwnProperty.call(expected, label)) continue;
    if (lineCount(normalized, `${label}:`) > 0) {
      errors.push(`unexpected finance field "${label}"`);
    }
  }
  if (/—/.test(normalized)) {
    errors.push('null finance marker "—" is not allowed for the fixture contract');
  }
  errors.push(...privacyErrors(normalized));

  // BR3_MANAGER_GATE: the only place manager clipboard acceptance is decided.
  // A mutation of this gate must make run_negative_controls.js fail.
  const managerGatePassed = errors.length === 0;
  if (managerGatePassed) {
    return [];
  }
  return errors;
}

function validateCohostClipboard(text) {
  const normalized = normalizeText(text);
  const errors = [];
  if (!normalized) return ['cohost clipboard is empty'];
  const lines = normalized.split('\n').map((line) => line.trim()).filter(Boolean);
  const allowedLinePatterns = [
    /^🏸 Tổng kết(?: buổi chơi|: .+)$/,
    /^📍 .+$/,
    /^⏰ .+$/,
    /^👥 Có mặt: \d+ · Vắng: \d+ · Đã xác nhận: \d+$/,
  ];
  for (const line of lines) {
    if (!allowedLinePatterns.some((pattern) => pattern.test(line))) {
      errors.push(`cohost clipboard contains a non-allowed line: "${line}"`);
    }
  }
  const countLines = lines.filter((line) => line.startsWith('👥 '));
  if (countLines.length !== 1) {
    errors.push(`cohost clipboard must contain exactly one count line, got ${countLines.length}`);
  } else if (countLines[0] !== FIXTURE.cohostCountsLine) {
    errors.push(`cohost count line expected "${FIXTURE.cohostCountsLine}", got "${countLines[0]}"`);
  }
  if (lines.length > 4) {
    errors.push(`cohost clipboard has ${lines.length} lines; at most 4 are allowed`);
  }
  for (const label of FINANCE_LABELS) {
    if (normalized.includes(label)) errors.push(`cohost clipboard leaked finance field "${label}"`);
  }
  if (MONEY_RE.test(normalized)) errors.push('cohost clipboard leaked a money value');
  if (/—/.test(normalized)) errors.push('cohost clipboard contains the null finance marker "—"');
  errors.push(...privacyErrors(normalized));
  return errors;
}

function validateCohostSummarySurface(elements) {
  const joined = semanticJoined(elements);
  const errors = [];
  if (!joined.includes('Chỉ xem số lượng')) {
    errors.push('cohost management-only note is missing');
  }
  for (const cardLabel of ['Tài chính tổng hợp', 'Chi phí & Thu chi']) {
    if (joined.includes(cardLabel)) errors.push(`cohost finance card "${cardLabel}" is visible`);
  }
  for (const label of FINANCE_LABELS) {
    if (joined.includes(label)) errors.push(`cohost UI leaked finance field "${label}"`);
  }
  if (MONEY_RE.test(joined)) errors.push('cohost UI leaked a money value');
  if (/—/.test(joined)) errors.push('cohost UI contains the null finance marker "—"');
  errors.push(...privacyErrors(joined));
  return errors;
}

function validateHistoryCall(call, expectedClubId) {
  const errors = [];
  if (!call || !call.postData || typeof call.postData !== 'object') {
    return ['history call has no parsed request payload'];
  }
  const actual = call.postData.p_club_id == null ? null : call.postData.p_club_id;
  if (actual !== expectedClubId) {
    errors.push(`history club filter expected ${expectedClubId === null ? 'null' : expectedClubId}, got ${actual === null ? 'null' : actual}`);
  }
  return errors;
}

// The browser capture always supplies an HTTP status. Failed HTTP/JSON
// responses remain errors, never an empty successful history projection.
function parseHistoryResponse(response) {
  if (!response || response.status !== 200) return { error: 'history HTTP response was not 200' };
  try {
    return JSON.parse(response.body);
  } catch (_) {
    return { error: 'history response was not valid JSON' };
  }
}

function validateHistoryResponse(body, expectedIds) {
  if (!Array.isArray(body)) return ['history response body is not an array'];
  if (body.some((row) => !row || typeof row !== 'object' || typeof row.id !== 'string')) {
    return ['history response contains an invalid session row'];
  }
  return validateHistoryIds(body.map((row) => row.id), expectedIds);
}

function validateHistoryIds(actualIds, expectedIds) {
  const errors = [];
  if (!Array.isArray(actualIds)) return ['history response ids are not an array'];
  if (!Array.isArray(expectedIds)) return ['expected history ids are not an array'];
  const actual = Array.from(new Set(actualIds.map(String))).sort();
  const expected = Array.from(new Set(expectedIds.map(String))).sort();
  if (JSON.stringify(actual) !== JSON.stringify(expected)) {
    errors.push(`history response ids expected ${JSON.stringify(expected)}, got ${JSON.stringify(actual)}`);
  }
  return errors;
}

function validateHistorySurface(elements, expectedTitles, expectedEmpty, allFixtureTitles = FIXTURE.historyFixtureTitles) {
  const joined = semanticJoined(elements);
  const errors = [];
  if (!joined) return ['history screen rendered no semantic text'];
  errors.push(...privacyErrors(joined));
  if (MONEY_RE.test(joined)) errors.push('history UI leaked a money value');

  for (const errorText of HISTORY_ERROR_TEXTS) {
    if (joined.includes(errorText)) errors.push(`history rendered error state "${errorText}"`);
  }
  for (const forbidden of HISTORY_FORBIDDEN_TEXTS) {
    if (joined.includes(forbidden)) errors.push(`history leaked forbidden text "${forbidden}"`);
  }

  if (expectedEmpty) {
    if (!joined.includes('Chưa có buổi nào')) {
      errors.push('member history did not render the empty state "Chưa có buổi nào"');
    }
    for (const title of allFixtureTitles) {
      if (joined.includes(title)) errors.push(`member history rendered out-of-scope session "${title}"`);
    }
    const rowMarkers = joined.split('Xem chi tiết').length - 1;
    if (rowMarkers > 0) errors.push(`member history rendered ${rowMarkers} session row marker(s)`);
    return errors;
  }

  if (!Array.isArray(expectedTitles) || expectedTitles.length === 0) {
    errors.push('expected history titles are missing');
    return errors;
  }
  for (const title of expectedTitles) {
    if (!joined.includes(title)) errors.push(`history is missing expected session "${title}"`);
  }
  for (const title of allFixtureTitles) {
    if (expectedTitles.includes(title)) continue;
    if (joined.includes(title)) errors.push(`history rendered unexpected session "${title}"`);
  }
  if (joined.includes('Chưa có buổi nào')) {
    errors.push('history rendered the empty state although sessions were expected');
  }
  const rowMarkers = joined.split('Xem chi tiết').length - 1;
  if (rowMarkers !== expectedTitles.length) {
    errors.push(`history rendered ${rowMarkers} row marker(s); expected ${expectedTitles.length}`);
  }
  return errors;
}

module.exports = {
  FIXTURE,
  OFFLINE_ERROR_MESSAGE,
  OFFLINE_SUCCESS_MESSAGE,
  semanticTexts,
  validateOfflineUiState,
  validateCompleteRequests,
  validateManagerClipboard,
  validateCohostClipboard,
  validateCohostSummarySurface,
  validateHistoryCall,
  validateHistoryIds,
  parseHistoryResponse,
  validateHistoryResponse,
  validateHistorySurface,
};
