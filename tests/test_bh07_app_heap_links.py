"""Link audit for the BH-07 status/handoff documents.

Review 57ec02c AH6: the status lines added for the app-profile handoff used
`docs/reviews/...` inside files that already live under `docs/`, so ten links resolved to
`docs/docs/reviews/...` and were dead. A status line that points nowhere is not evidence,
so this control fails whenever a relative link in those documents has no target.

Run: python -m unittest tests.test_bh07_app_heap_links -v
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCUMENTS = (
    'AGENTS.md',
    'README.md',
    'docs/00_START_HERE.md',
    'docs/09_IMPLEMENTATION_PLAN.md',
    'docs/25_BH07_IMPLEMENTATION_HANDOFF.md',
    'docs/26_BH07_OPERATIONS_REHEARSAL.md',
    'docs/STATUS_HISTORY.md',
    'docs/reviews/bh07/bh07_readiness.md',
    'docs/reviews/bh07/app_profile_heap_handoff.md',
)
LINK = re.compile(r'\]\(([^)]+)\)')


def broken_links(path):
    path = ROOT / path
    broken = []
    for number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
        for raw in LINK.findall(line):
            target = raw.split('#')[0].strip()
            if not target or '://' in target or target.startswith(('mailto:', 'tel:')):
                continue
            if not (path.parent / target).exists():
                broken.append({'file': path.relative_to(ROOT).as_posix(), 'line': number, 'target': target})
    return broken


class StatusLinkControls(unittest.TestCase):
    def test_status_documents_have_no_dead_relative_links(self):
        broken = [entry for document in DOCUMENTS for entry in broken_links(document)]
        self.assertEqual(broken, [], f'dead relative links: {broken}')

    def test_app_profile_status_links_resolve(self):
        # The ten links review 57ec02c reported, from the five status documents under docs/.
        for document in ('docs/00_START_HERE.md', 'docs/09_IMPLEMENTATION_PLAN.md',
                         'docs/25_BH07_IMPLEMENTATION_HANDOFF.md',
                         'docs/26_BH07_OPERATIONS_REHEARSAL.md', 'docs/STATUS_HISTORY.md'):
            text = (ROOT / document).read_text(encoding='utf-8')
            self.assertIn('](reviews/bh07/app_profile_heap_handoff.md)', text, document)
            self.assertIn('](reviews/bh07/app_profile_heap_evidence/)', text, document)

    def test_handoff_evidence_link_resolves(self):
        text = (ROOT / 'docs/reviews/bh07/app_profile_heap_handoff.md').read_text(encoding='utf-8')
        self.assertIn('](app_profile_heap_evidence/)', text)


if __name__ == '__main__':
    unittest.main()
