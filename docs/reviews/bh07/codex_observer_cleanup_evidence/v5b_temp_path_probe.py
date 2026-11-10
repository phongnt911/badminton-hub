import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

root = next(p for p in Path(__file__).resolve().parents if (p / '.git').exists())
sys.path.insert(0, str(root / 'tests'))
import test_v5b_runner_flaws as subject

original_directory = tempfile.TemporaryDirectory
def directory_with_db_in_name(*args, **kwargs):
    return original_directory(prefix='v5b-db-', *args, **kwargs)

suite = unittest.TestLoader().loadTestsFromName(
    'TestV5bRunnerBehavior.test_r1_owned_inventory_must_succeed_before_reset', subject)
with patch.object(subject.tempfile, 'TemporaryDirectory', side_effect=directory_with_db_in_name):
    result = unittest.TestResult()
    suite.run(result)
print(json.dumps({'kind': 'synthetic test-harness probe; no real reset/Docker',
                  'test_methods': result.testsRun, 'errors': len(result.errors),
                  'failures_with_db_temp_path': len(result.failures),
                  'all_reset_classifier_mismatches': all('True != False' in trace for _, trace in result.failures)},
                 indent=2))
