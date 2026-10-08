"""Executed-test ledger for unittest. Empty, missing or skipped tests fail the gate."""
import argparse
from collections import Counter
import json
from pathlib import Path
import time
import unittest


def validate(ledger, required):
    rows = ledger.get('tests', [])
    ids = [r['id'] for r in rows]
    return {'passed': bool(rows) and Counter(ids) == Counter(required) and all(r['outcome'] == 'PASS' for r in rows),
            'missing': sorted((Counter(required)-Counter(ids)).elements()),
            'unexpected': sorted((Counter(ids)-Counter(required)).elements()),
            'nonpassing': [r for r in rows if r['outcome'] != 'PASS']}


class LedgerResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs); self.records = []; self.active = None
    def startTest(self, test):
        super().startTest(test)
        self.active = {'id': test.id(), 'outcome': 'INCOMPLETE', 'started': time.perf_counter()}
        self.records.append(self.active)
    def mark(self, outcome):
        if self.active is not None: self.active['outcome'] = outcome
    def addSuccess(self, test):
        if self.active['outcome'] == 'INCOMPLETE': self.mark('PASS')
        super().addSuccess(test)
    def addFailure(self, test, err):
        self.mark('FAIL'); super().addFailure(test, err)
    def addError(self, test, err):
        self.mark('ERROR'); super().addError(test, err)
    def addSkip(self, test, reason):
        self.mark('SKIP'); self.active['reason'] = reason; super().addSkip(test, reason)
    def addExpectedFailure(self, test, err):
        self.mark('EXPECTED_FAILURE'); super().addExpectedFailure(test, err)
    def addUnexpectedSuccess(self, test):
        self.mark('UNEXPECTED_SUCCESS'); super().addUnexpectedSuccess(test)
    def addSubTest(self, test, subtest, err):
        if err: self.mark('FAIL')
        super().addSubTest(test, subtest, err)
    def stopTest(self, test):
        self.active['seconds'] = round(time.perf_counter()-self.active.pop('started'), 6)
        self.active = None; super().stopTest(test)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--suite', choices=['smoke', 'p0', 'generated', 'adversarial'], required=True)
    parser.add_argument('--ledger', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    registry = json.loads((root/'verification/p0_registry.json').read_text('utf-8'))
    folder = 'tests_qa' if args.suite == 'generated' else 'tests'
    pattern = {'smoke':'test_regressions.py', 'adversarial':'test_normalizer.py'}.get(args.suite, 'test*.py')
    suite = unittest.defaultTestLoader.discover(str(root/folder), pattern=pattern)
    result = unittest.TextTestRunner(verbosity=2, resultclass=LedgerResult).run(suite)
    report = {'suite': args.suite, 'tests': result.records, 'tests_run': result.testsRun}
    report['gate'] = validate(report, registry[args.suite])
    args.ledger.write_text(json.dumps(report, ensure_ascii=True, indent=2), 'utf-8')
    return 0 if result.wasSuccessful() and report['gate']['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
