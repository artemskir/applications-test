"""Read-only verification of fixture hashes, labels and experiment summaries."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from fixtures.scenarios import CASES
from tools.generate_data import SPEC_VERSION


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def verify_hashes(directory, entries):
    for entry in entries:
        path = (directory / entry['file']).resolve()
        if not path.is_relative_to(directory.resolve()):
            raise ValueError('Artifact path outside its directory')
        if hashlib.sha256(path.read_bytes()).hexdigest() != entry['sha256']:
            raise ValueError('Hash mismatch: ' + str(path))


def verify_suite(directory):
    manifest = read(directory / 'manifest.json')
    if manifest['spec_version'] != SPEC_VERSION:
        raise ValueError('Suite belongs to another specification version')
    verify_hashes(directory, manifest['files'])
    if read(directory / 'cases.json') != CASES:
        raise ValueError('Catalog snapshot differs from the current catalog')
    if manifest['mode'] == 'suite':
        dirty = next(item for item in manifest['files'] if item['file'] == 'dirty.xlsx')
        if {label['case_id'] for label in dirty['labels']} != {case['id'] for case in CASES}:
            raise ValueError('Dirty suite does not cover every case')
        if len(manifest['files']) != 14:
            raise ValueError('Incomplete suite')
    return {'directory': str(directory), 'verified_files': len(manifest['files']), 'cases': len(CASES)}


def verify_experiment(directory):
    result = read(directory / 'results.json')
    checks = result['checks']
    if not checks or any(check['passed'] is not True for check in checks):
        raise ValueError('Experiment contains failed checks: ' + str(directory))
    if result['failed'] != 0 or result['passed'] != len(checks):
        raise ValueError('Invalid check summary')
    expected_spec_hash = result.get('spec_sha256', result.get('source_sha256', {}).get('docs\\SPECIFICATION.md'))
    expected_spec_hash = expected_spec_hash or result.get('source_sha256', {}).get('docs/SPECIFICATION.md')
    if expected_spec_hash != hashlib.sha256((ROOT / 'docs/SPECIFICATION.md').read_bytes()).hexdigest():
        raise ValueError('Experiment tested another specification snapshot')
    if 'research_sha256' in result and result['research_sha256'] != hashlib.sha256((ROOT / 'research/deep-research-report.md').read_bytes()).hexdigest():
        raise ValueError('Deep Research source changed')
    for name, expected in result.get('source_sha256', {}).items():
        source = (ROOT / name).resolve()
        if not source.is_relative_to(ROOT) or hashlib.sha256(source.read_bytes()).hexdigest() != expected:
            raise ValueError('Research/plan source changed: ' + name)
    inventory = directory / 'artifacts.json'
    if inventory.exists():
        verify_hashes(directory, read(inventory))
    return {'directory': str(directory), 'verified_checks': len(checks)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--suite', type=Path)
    parser.add_argument('--experiment', type=Path, action='append', default=[])
    args = parser.parse_args()
    if not args.suite and not args.experiment:
        parser.error('Supply --suite or --experiment')
    try:
        summaries = ([verify_suite(args.suite)] if args.suite else [])
        summaries.extend(verify_experiment(directory) for directory in args.experiment)
    except (OSError, ValueError, KeyError, StopIteration) as exc:
        print('Verification failed: ' + str(exc), file=sys.stderr)
        return 1
    print(json.dumps(summaries, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
