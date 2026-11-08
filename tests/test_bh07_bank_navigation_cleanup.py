"""Regression tests for BH-07 V2b bank navigation and lifecycle cleanup.

BKR8: NavigationDestination contract verification and regression tests:
- Actual lib/main.dart navigation label is 'CLB & Quỹ' (Icons.group).
- Runner previously expected erroneous label 'Câu Lạc Bộ' causing runtime abort.
- Exercises exported production openOwnerBank from scripts/bh07_appheap/run_app_profile_heap.js
  against FakeCdp with mocked timers (zero live wait delay).
- Asserts actual 'CLB & Quỹ' label is accepted and recorded in semantic click sequence.
- Asserts erroneous 'Câu Lạc Bộ' label is refused with exact Clubs tab error.
- Asserts role enforcement (role must be 'tab') and variant coverage (aria vs text).

Run: python -X utf8 -m unittest tests.test_bh07_bank_navigation_cleanup -v
"""
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN_APP_PROFILE_HEAP = ROOT / 'scripts/bh07_appheap/run_app_profile_heap.js'
MAIN_DART = ROOT / 'lib/main.dart'

NODE_HARNESS = r'''
const origSetTimeout = global.setTimeout;
global.setTimeout = (fn, ms) => origSetTimeout(fn, 0);

const path = require('path');
const runnerPath = path.resolve(process.argv[1]);
const runner = require(runnerPath);
const { openOwnerBank } = runner;

if (typeof openOwnerBank !== 'function') {
  process.stderr.write('openOwnerBank export missing from ' + runnerPath + '\n');
  process.exit(2);
}

class FakeCdp {
  constructor(elements = []) {
    this.elements = elements;
    this.clicks = [];
    this.waits = [];
    this.backs = [];
  }

  async getAllSemantics() {
    return this.elements;
  }

  async findSemantic(predicate, timeoutMs = 8000) {
    const matches = this.elements.filter(predicate);
    if (matches.length > 0) {
      const buttonMatch = matches.find(m => m.role === 'button' || m.tag === 'BUTTON');
      if (buttonMatch) return buttonMatch;
      return matches[0];
    }
    return null;
  }

  async clickSemantic(predicate, stepName) {
    const el = await this.findSemantic(predicate);
    if (!el) {
      throw new Error(`Could not find semantic element to click for: ${stepName}`);
    }
    this.clicks.push({ stepName, el });
    return el;
  }

  async waitForSemantic(predicate, desc, timeoutMs = 10000) {
    const el = await this.findSemantic(predicate, timeoutMs);
    if (!el) {
      throw new Error(`Timed out waiting for semantic element: ${desc}`);
    }
    this.waits.push({ desc, el });
    return el;
  }

  async clickBack(stepName) {
    this.backs.push(stepName);
  }
}

let raw = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', chunk => { raw += chunk; });
process.stdin.on('end', async () => {
  try {
    const input = JSON.parse(raw);
    const cdp = new FakeCdp(input.elements || []);
    await openOwnerBank(cdp, input.clubName || 'BH07 Test Club', input.bankCode || 'VCB');
    process.stdout.write(JSON.stringify({
      ok: true,
      clicks: cdp.clicks,
      waits: cdp.waits,
      backs: cdp.backs,
    }));
  } catch (err) {
    process.stdout.write(JSON.stringify({
      ok: false,
      error: err.message,
    }));
    process.exit(1);
  }
});
'''


def run_open_owner_bank_harness(payload):
    result = subprocess.run(
        ['node', '-e', NODE_HARNESS, str(RUN_APP_PROFILE_HEAP)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        encoding='utf-8',
        cwd=ROOT,
    )
    data = {}
    if result.stdout.strip():
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError:
            data = {'raw_stdout': result.stdout}
    return result.returncode, data, result.stderr


class TestBankNavigationContract(unittest.TestCase):
    """BKR8: Verify actual semantic navigation contract in lib/main.dart."""

    def test_main_dart_has_clb_va_quy_navigation_destination(self):
        """lib/main.dart must declare 'CLB & Quỹ' as the NavigationDestination label."""
        self.assertTrue(MAIN_DART.is_file(), f"Missing main.dart at {MAIN_DART}")
        content = MAIN_DART.read_text(encoding='utf-8')

        # Check NavigationDestination contract
        self.assertIn("label: 'CLB & Quỹ'", content,
                      "lib/main.dart must define NavigationDestination with label: 'CLB & Quỹ'")
        self.assertIn("Icon(Icons.group)", content,
                      "lib/main.dart must use Icons.group for 'CLB & Quỹ'")

        # Ensure erroneous 'Câu Lạc Bộ' label is absent from NavigationDestination destinations
        destinations_match = re.search(r'destinations:\s*const\s*\[(.*?)\]', content, re.DOTALL)
        self.assertIsNotNone(destinations_match, "NavigationBar destinations list not found in lib/main.dart")
        destinations_text = destinations_match.group(1)
        self.assertNotIn("'Câu Lạc Bộ'", destinations_text,
                         "lib/main.dart destinations must not contain old erroneous label 'Câu Lạc Bộ'")
        self.assertIn("'CLB & Quỹ'", destinations_text,
                         "lib/main.dart destinations must contain actual label 'CLB & Quỹ'")


class TestBankNavigationRegression(unittest.TestCase):
    """BKR8: Regression tests exercising exported openOwnerBank with fake CDP."""

    def _build_valid_elements(self, club_tab_aria='CLB & Quỹ', club_tab_text='CLB & Quỹ', club_tab_role='tab'):
        return [
            # Main tabs satisfying home(cdp)
            {'role': 'tab', 'aria': 'Tài Khoản', 'text': 'Tài Khoản'},
            {'role': 'tab', 'aria': 'Buổi Chơi', 'text': 'Buổi Chơi'},
            {'role': 'tab', 'aria': 'Sân Nha Trang', 'text': 'Sân Nha Trang'},
            {'role': club_tab_role, 'aria': club_tab_aria, 'text': club_tab_text},
            {'role': 'tab', 'aria': 'Tiện Ích', 'text': 'Tiện Ích'},
            # Disposable club in clubs list
            {'role': 'button', 'aria': '', 'text': 'BH07 Disposable Test Club 1234'},
            # Bank tab inside club view
            {'role': 'tab', 'aria': 'Tài khoản quỹ', 'text': 'Tài khoản quỹ'},
            # Bank account card rendered
            {'role': 'card', 'aria': '', 'text': 'VCB ĐANG DÙNG 9999000012345678'},
        ]

    def test_open_owner_bank_accepts_actual_clb_va_quy_destination(self):
        """Exported openOwnerBank must accept real label 'CLB & Quỹ' and click Clubs tab."""
        elements = self._build_valid_elements(club_tab_aria='CLB & Quỹ', club_tab_text='CLB & Quỹ')
        payload = {
            'elements': elements,
            'clubName': 'BH07 Disposable Test Club 1234',
            'bankCode': 'VCB',
        }
        code, data, stderr = run_open_owner_bank_harness(payload)
        self.assertEqual(code, 0, f"openOwnerBank failed unexpectedly (stderr={stderr}): {data}")
        self.assertTrue(data.get('ok'), f"Expected ok=true, got {data}")

        # Assert Clubs tab click occurred with the exact semantic element
        clicks = data.get('clicks', [])
        clubs_click = next((c for c in clicks if c.get('stepName') == 'Clubs tab'), None)
        self.assertIsNotNone(clubs_click, f"'Clubs tab' step not clicked in {clicks}")
        self.assertEqual(clubs_click['el']['role'], 'tab')
        self.assertEqual(clubs_click['el']['aria'], 'CLB & Quỹ')

    def test_open_owner_bank_refuses_erroneous_cau_lac_bo_label(self):
        """Exported openOwnerBank must refuse erroneous 'Câu Lạc Bộ' label (reproducing BKR8 failure)."""
        elements = self._build_valid_elements(club_tab_aria='Câu Lạc Bộ', club_tab_text='Câu Lạc Bộ')
        payload = {
            'elements': elements,
            'clubName': 'BH07 Disposable Test Club 1234',
            'bankCode': 'VCB',
        }
        code, data, stderr = run_open_owner_bank_harness(payload)
        self.assertEqual(code, 1, f"Expected openOwnerBank to fail on wrong tab label, got exit 0: {data}")
        self.assertFalse(data.get('ok'))
        self.assertIn('Could not find semantic element to click for: Clubs tab', data.get('error', ''))

    def test_open_owner_bank_accepts_aria_label_alone(self):
        """Matches destination if Flutter provides aria-label 'CLB & Quỹ' with empty inner text."""
        elements = self._build_valid_elements(club_tab_aria='CLB & Quỹ', club_tab_text='')
        payload = {
            'elements': elements,
            'clubName': 'BH07 Disposable Test Club 1234',
            'bankCode': 'VCB',
        }
        code, data, stderr = run_open_owner_bank_harness(payload)
        self.assertEqual(code, 0, f"Failed matching aria alone: {data}")
        self.assertTrue(data.get('ok'))

    def test_open_owner_bank_accepts_text_alone(self):
        """Matches destination if Flutter provides inner text 'CLB & Quỹ' with empty aria."""
        elements = self._build_valid_elements(club_tab_aria='', club_tab_text='CLB & Quỹ')
        payload = {
            'elements': elements,
            'clubName': 'BH07 Disposable Test Club 1234',
            'bankCode': 'VCB',
        }
        code, data, stderr = run_open_owner_bank_harness(payload)
        self.assertEqual(code, 0, f"Failed matching text alone: {data}")
        self.assertTrue(data.get('ok'))

    def test_open_owner_bank_refuses_non_tab_role_destination(self):
        """Refuses element with text 'CLB & Quỹ' if role is not 'tab'."""
        elements = self._build_valid_elements(club_tab_aria='CLB & Quỹ', club_tab_text='CLB & Quỹ', club_tab_role='button')
        payload = {
            'elements': elements,
            'clubName': 'BH07 Disposable Test Club 1234',
            'bankCode': 'VCB',
        }
        code, data, stderr = run_open_owner_bank_harness(payload)
        self.assertEqual(code, 1, f"Expected non-tab role to be refused, got exit 0: {data}")
        self.assertIn('Could not find semantic element to click for: Clubs tab', data.get('error', ''))


if __name__ == '__main__':
    unittest.main()
