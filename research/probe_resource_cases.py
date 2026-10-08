"""Run independent minimal cases; persist evidence before or after fixes."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from fixtures.resource_cases import CASES
from normalizer import dates, names, phone, SPEC_VERSION
from normalizer.models import RawCell


def probe():
    results = []
    for case in CASES:
        result = {'id': case.ident, 'category': case.category, 'value':case.value,
                  'expected': {'canonical':case.canonical, 'codes':list(case.codes)}}
        try:
            actual = {'phone':phone, 'dates':dates, 'names':names}[case.field_name].analyze(RawCell(case.value, **case.kwargs))
            result['actual'] = {'canonical':actual.canonical, 'codes':actual.codes, 'display':actual.display}
            result['passed'] = actual.canonical == case.canonical and actual.codes == list(case.codes)
        except Exception as exc:
            result['exception'] = repr(exc)
            result['passed'] = False
        results.append(result)
    return results


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    results = probe()
    hashes = {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
              for p in sorted((ROOT / 'normalizer').glob('*.py'))}
    report = {'spec_version':SPEC_VERSION, 'source_hashes':hashes, 'cases':results,
              'passed':sum(r['passed'] for r in results), 'total':len(results)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, ensure_ascii=True, indent=2)
    print(json.dumps({'passed':report['passed'], 'total':report['total'],
                      'failed':[r['id'] for r in results if not r['passed']]}))
    return int(report['passed'] != len(results))


if __name__ == '__main__':
    raise SystemExit(main())
