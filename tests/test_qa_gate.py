import subprocess
import os
import sys
import unittest
from unittest.mock import patch
from verification.test_driver import validate, LedgerResult
from tools.run_qa import execute
from io import StringIO


class QAGate(unittest.TestCase):
    def test_real_subprocess_crash_is_recorded_as_failure(self):
        result, log = execute([sys.executable, '-X', 'utf8', '-c', 'raise SystemExit(4)'], dict(os.environ), 30)
        self.assertEqual(result['exit_code'], 4)

    def test_empty_missing_duplicate_and_skip_fail_gate(self):
        required = ['critical']
        for rows in ([], [{'id':'critical', 'outcome':'SKIP'}], [{'id':'other', 'outcome':'PASS'}],
                     [{'id':'critical', 'outcome':'PASS'}]*2):
            self.assertFalse(validate({'tests':rows}, required)['passed'])
        self.assertTrue(validate({'tests':[{'id':'critical', 'outcome':'PASS'}]}, required)['passed'])

    def test_timeout_and_cli_failure_fail_gate(self):
        with patch('tools.run_qa.subprocess.run', side_effect=subprocess.TimeoutExpired(['test'], 1)):
            result, _ = execute(['test'], {}, 1)
            self.assertIsNone(result['exit_code']); self.assertEqual(result['error'], 'TimeoutExpired')
        with patch('tools.run_qa.subprocess.run', return_value=subprocess.CompletedProcess(['test'], 4, '', 'crash')):
            result, _ = execute(['test'], {}, 1)
            self.assertEqual(result['exit_code'], 4)

    def test_subtest_failure_cannot_be_reported_as_success(self):
        class Broken(unittest.TestCase):
            def runTest(self):
                with self.subTest(): self.assertEqual(1, 2)
        result = unittest.TextTestRunner(stream=StringIO(), resultclass=LedgerResult).run(unittest.TestSuite([Broken()]))
        self.assertEqual(result.records[0]['outcome'], 'FAIL')
