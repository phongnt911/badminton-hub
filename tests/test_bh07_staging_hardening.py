"""Static syntax and boundary tests for BH-07 staging candidate hardening.

IMPORTANT BOUNDARY NOTE:
These tests are strictly static text, syntax, and whole-statement assertions on the
candidate SQL file. They verify exact statement count, helper signatures, anchored
principals, search_path pins, negative boundaries, and mutant rejections.
They do NOT verify runtime PostgreSQL permissions, live RLS policy enforcement,
caller isolation, or staging baseline behavior. Those runtime properties require
execution within a PostgreSQL environment (see staging_hardening_local_probe_20261112.py).
"""

from pathlib import Path
import re
import unittest

REPO_ROOT = Path(__file__).resolve().parents[1]
CANDIDATE_SQL_PATH = REPO_ROOT / 'scripts' / 'bh07_staging' / 'role_helper_hardening.sql'
CANONICAL_INIT_MIGRATION = (
    REPO_ROOT / 'supabase' / 'migrations' / '20261015051808_init_schema_v1_1.sql'
)

EXPECTED_HELPERS = [
    ('is_app_admin', ['UUID']),
    ('is_club_owner', ['UUID', 'UUID']),
    ('is_club_member_active', ['UUID', 'UUID']),
    ('has_club_role', ['UUID', 'UUID', 'TEXT[]']),
    ('is_session_host', ['UUID', 'UUID']),
    ('has_session_staff_role', ['UUID', 'UUID', 'TEXT[]']),
    ('has_session_management_access', ['UUID', 'UUID']),
    ('has_session_finance_access', ['UUID', 'UUID']),
    ('is_session_participant', ['UUID', 'UUID']),
    ('has_session_player_finance_access', ['UUID', 'UUID']),
]

EXPECTED_TRIGGERS = [
    'sync_legacy_session_columns',
    'sync_legacy_session_player_columns',
]


def extract_statements(sql_text: str) -> list[str]:
    """Extract individual executable statements stripped of SQL comments and excess whitespace."""
    lines = []
    for line in sql_text.splitlines():
        line_clean = re.sub(r'--.*$', '', line).strip()
        if line_clean:
            lines.append(line_clean)
    combined = ' '.join(lines)
    return [re.sub(r'\s+', ' ', s.strip()) for s in combined.split(';') if s.strip()]


def validate_exact_statements(statements: list[str]) -> None:
    """Strict whole-statement validation enforcing exact principals, triggers, and count."""
    if len(statements) != 22:
        raise AssertionError(f'Expected exactly 22 statements, got {len(statements)}')

    for func_name, arg_types in EXPECTED_HELPERS:
        args_pattern = r'\s*,\s*'.join(re.escape(a) for a in arg_types)

        # Anchored full statement match: exactly REVOKE ALL ON FUNCTION public.<func>(<args>) FROM PUBLIC, anon
        revoke_pattern = (
            rf'^REVOKE\s+ALL\s+ON\s+FUNCTION\s+public\.{re.escape(func_name)}\s*\(\s*{args_pattern}\s*\)'
            rf'\s+FROM\s+PUBLIC\s*,\s*anon$'
        )
        if not any(re.fullmatch(revoke_pattern, s, re.IGNORECASE) for s in statements):
            raise AssertionError(f'Missing exact REVOKE statement for public.{func_name}({", ".join(arg_types)})')

        # Anchored full statement match: exactly GRANT EXECUTE ON FUNCTION public.<func>(<args>) TO authenticated
        grant_pattern = (
            rf'^GRANT\s+EXECUTE\s+ON\s+FUNCTION\s+public\.{re.escape(func_name)}\s*\(\s*{args_pattern}\s*\)'
            rf'\s+TO\s+authenticated$'
        )
        if not any(re.fullmatch(grant_pattern, s, re.IGNORECASE) for s in statements):
            raise AssertionError(f'Missing exact GRANT statement for public.{func_name}({", ".join(arg_types)})')

    for trig_name in EXPECTED_TRIGGERS:
        # Anchored full statement match: exactly ALTER FUNCTION public.<trig>() SET search_path = public, pg_temp
        alter_pattern = (
            rf'^ALTER\s+FUNCTION\s+public\.{re.escape(trig_name)}\s*\(\s*\)'
            rf'\s+SET\s+search_path\s*=\s*public\s*,\s*pg_temp$'
        )
        if not any(re.fullmatch(alter_pattern, s, re.IGNORECASE) for s in statements):
            raise AssertionError(f'Missing exact ALTER FUNCTION statement for public.{trig_name}()')


class StagingCandidateHardeningStaticTests(unittest.TestCase):
    """Static verification of the SQL candidate's structural properties, boundaries, and mutants."""

    def setUp(self):
        self.assertTrue(
            CANDIDATE_SQL_PATH.exists(),
            f'Candidate SQL must exist at {CANDIDATE_SQL_PATH}',
        )
        self.sql_content = CANDIDATE_SQL_PATH.read_text(encoding='utf-8')
        self.statements = extract_statements(self.sql_content)

    def test_exact_twenty_two_sql_statements(self):
        """Candidate must contain exactly 22 executable statements (10 revokes, 10 grants, 2 alters)."""
        self.assertEqual(len(self.statements), 22)
        revokes = [s for s in self.statements if re.match(r'^REVOKE\b', s, re.IGNORECASE)]
        grants = [s for s in self.statements if re.match(r'^GRANT\b', s, re.IGNORECASE)]
        alters = [s for s in self.statements if re.match(r'^ALTER\s+FUNCTION\b', s, re.IGNORECASE)]
        self.assertEqual(len(revokes), 10)
        self.assertEqual(len(grants), 10)
        self.assertEqual(len(alters), 2)
        validate_exact_statements(self.statements)

    def test_ten_helpers_signatures_and_grants(self):
        """Verify all 10 helpers match exact whole statements (no extra grantees or permissive regex match)."""
        for func_name, arg_types in EXPECTED_HELPERS:
            args_pattern = r'\s*,\s*'.join(re.escape(a) for a in arg_types)
            revoke_pattern = (
                rf'^REVOKE\s+ALL\s+ON\s+FUNCTION\s+public\.{re.escape(func_name)}\s*\(\s*{args_pattern}\s*\)'
                rf'\s+FROM\s+PUBLIC\s*,\s*anon$'
            )
            grant_pattern = (
                rf'^GRANT\s+EXECUTE\s+ON\s+FUNCTION\s+public\.{re.escape(func_name)}\s*\(\s*{args_pattern}\s*\)'
                rf'\s+TO\s+authenticated$'
            )
            self.assertTrue(
                any(re.fullmatch(revoke_pattern, s, re.IGNORECASE) for s in self.statements),
                f'Statement mismatch for REVOKE public.{func_name}',
            )
            self.assertTrue(
                any(re.fullmatch(grant_pattern, s, re.IGNORECASE) for s in self.statements),
                f'Statement mismatch for GRANT public.{func_name}',
            )

    def test_two_legacy_triggers_alterations(self):
        """Verify the two legacy column sync triggers match exact whole-statement search_path pin."""
        for trig_name in EXPECTED_TRIGGERS:
            alter_pattern = (
                rf'^ALTER\s+FUNCTION\s+public\.{re.escape(trig_name)}\s*\(\s*\)'
                rf'\s+SET\s+search_path\s*=\s*public\s*,\s*pg_temp$'
            )
            self.assertTrue(
                any(re.fullmatch(alter_pattern, s, re.IGNORECASE) for s in self.statements),
                f'Statement mismatch for ALTER FUNCTION public.{trig_name}',
            )

    def test_strict_negative_boundaries(self):
        """Candidate must not contain function bodies, view definitions, table DDL, or data modifications."""
        forbidden_checks = [
            (r'CREATE\s+OR\s+REPLACE\s+FUNCTION', 'CREATE OR REPLACE FUNCTION is forbidden'),
            (r'\$\$.*?\$\$', 'Function body ($$...$$) is forbidden'),
            (r'\bBEGIN\b', 'Function body block (BEGIN) is forbidden'),
            (r'\bRETURNS\b', 'Function signature (RETURNS) is forbidden'),
            (r'CREATE\s+(?:OR\s+REPLACE\s+)?VIEW', 'Creating or modifying views is forbidden'),
            (r'ALTER\s+VIEW', 'ALTER VIEW is forbidden'),
            (r'CREATE\s+TABLE', 'CREATE TABLE is forbidden'),
            (r'ALTER\s+TABLE', 'ALTER TABLE is forbidden'),
            (r'DROP\s+TABLE', 'DROP TABLE is forbidden'),
            (r'INSERT\s+INTO', 'INSERT INTO is forbidden'),
            (r'UPDATE\s+\w+\s+SET', 'UPDATE is forbidden'),
            (r'DELETE\s+FROM', 'DELETE FROM is forbidden'),
            (r'TRUNCATE', 'TRUNCATE is forbidden'),
        ]
        full_clean_sql = ' '.join(self.statements)
        for pattern, err_msg in forbidden_checks:
            matches = re.findall(pattern, full_clean_sql, re.IGNORECASE)
            self.assertFalse(matches, f'{err_msg}; matched: {matches}')

    def test_canonical_signature_cross_check(self):
        """Cross-check helper and trigger signatures against canonical 20261015051808_init_schema_v1_1.sql."""
        self.assertTrue(CANONICAL_INIT_MIGRATION.exists())
        canonical_content = CANONICAL_INIT_MIGRATION.read_text(encoding='utf-8')

        for func_name, arg_types in EXPECTED_HELPERS:
            args_pat = r'\s*,\s*'.join([rf'p_\w+\s+{re.escape(a)}' for a in arg_types])
            pattern = rf'CREATE\s+OR\s+REPLACE\s+FUNCTION\s+public\.{re.escape(func_name)}\s*\(\s*{args_pat}\s*\)'
            self.assertRegex(
                canonical_content,
                re.compile(pattern, re.IGNORECASE),
                f'Function public.{func_name} with args {arg_types} not found in canonical migration',
            )

        for trig_name in EXPECTED_TRIGGERS:
            pattern = rf'CREATE\s+OR\s+REPLACE\s+FUNCTION\s+public\.{re.escape(trig_name)}\s*\(\s*\)'
            self.assertRegex(
                canonical_content,
                re.compile(pattern, re.IGNORECASE),
                f'Trigger function public.{trig_name}() not found in canonical migration',
            )

    def test_mutant_controls_reject_permissive_modifications(self):
        """Mutant controls: verify that added grantees, extra schemas, or appended clauses FAIL validation."""
        # Baseline check passes
        validate_exact_statements(self.statements)

        # Mutant 1: extra grantee added to GRANT (e.g. TO authenticated, anon)
        mutant_grant = [
            s.replace('TO authenticated', 'TO authenticated, anon')
            if s.startswith('GRANT EXECUTE ON FUNCTION public.is_app_admin') else s
            for s in self.statements
        ]
        with self.assertRaises(AssertionError) as ctx1:
            validate_exact_statements(mutant_grant)
        self.assertIn('Missing exact GRANT statement for public.is_app_admin', str(ctx1.exception))

        # Mutant 2: extra schema added to search_path
        mutant_search_path = [
            s.replace('SET search_path = public, pg_temp', 'SET search_path = public, pg_temp, attacker')
            if 'sync_legacy_session_columns' in s else s
            for s in self.statements
        ]
        with self.assertRaises(AssertionError) as ctx2:
            validate_exact_statements(mutant_search_path)
        self.assertIn('Missing exact ALTER FUNCTION statement for public.sync_legacy_session_columns', str(ctx2.exception))

        # Mutant 3: appended clause on grant (e.g. WITH GRANT OPTION)
        mutant_clause = [
            s + ' WITH GRANT OPTION'
            if s.startswith('GRANT EXECUTE ON FUNCTION public.is_app_admin') else s
            for s in self.statements
        ]
        with self.assertRaises(AssertionError) as ctx3:
            validate_exact_statements(mutant_clause)
        self.assertIn('Missing exact GRANT statement for public.is_app_admin', str(ctx3.exception))

        # Mutant 4: extra statement added (statement count violation)
        mutant_count = self.statements + ['SELECT 1']
        with self.assertRaises(AssertionError) as ctx4:
            validate_exact_statements(mutant_count)
        self.assertIn('Expected exactly 22 statements', str(ctx4.exception))


if __name__ == '__main__':
    unittest.main()
