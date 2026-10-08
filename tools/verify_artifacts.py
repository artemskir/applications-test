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


def verify_resource_qa(directory):
    result = read(directory / 'results.json')
    if result['spec_version'] != SPEC_VERSION or result['passed'] is not True or result['failed']:
        raise ValueError('Resource QA failed or belongs to another specification')
    if not result['checks'] or any(type(n) is not int or n < 1 for n in result['checks'].values()):
        raise ValueError('Empty/invalid resource QA counters')
    for name, expected in result['source_hashes'].items():
        path = (ROOT / name).resolve()
        if not path.is_relative_to(ROOT) or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError('Resource QA source changed: ' + name)
    lock = ROOT / 'research/resource_sources.lock.json'
    if hashlib.sha256(lock.read_bytes()).hexdigest() != result['resource_lock_sha256']:
        raise ValueError('Resource lock changed')
    if read(lock)['sources'] != result['resources']:
        raise ValueError('Resource manifest differs')
    verify_hashes(directory, result['artifacts'])
    return {'directory':str(directory), 'checks':sum(result['checks'].values()),
            'verified_artifacts':len(result['artifacts'])}


def verify_formal_qa(directory):
    result = read(directory / 'results.json')
    if result.get('passed') is not True or result.get('status') != 'P0 PASS' or result.get('failed'):
        raise ValueError('Formal QA is incomplete or failed')
    required = ('exhaustive', 'fields', 'stateful', 'preservation', 'critical-conditions', 'publication-faults', 'names', 'mutations')
    if any(result['steps'].get(name) is not True for name in required):
        raise ValueError('Missing formal QA steps')
    for name, expected in result['source_sha256'].items():
        path = (ROOT / name).resolve()
        if not path.is_relative_to(ROOT) or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError('Formal QA source changed: ' + name)
    verify_hashes(directory, [{'file':name, 'sha256':value} for name,value in result['artifact_sha256'].items()])
    exhaustive = read(directory / 'exhaustive.json')
    if exhaustive['counts'] != {'0':1, '1':48, '2':2304, '3':110592} or exhaustive['total_sequences'] != 112945:
        raise ValueError('Incomplete ordered enumeration')
    for name in required:
        if read(directory / (name + '.json')).get('passed') is not True:
            raise ValueError('Failed formal step: ' + name)
    return {'directory':str(directory), 'sequences':112945, 'verified_artifacts':len(result['artifact_sha256'])}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--suite', type=Path)
    parser.add_argument('--experiment', type=Path, action='append', default=[])
    parser.add_argument('--resource-qa', type=Path, action='append', default=[])
    parser.add_argument('--formal-qa', type=Path, action='append', default=[])
    args = parser.parse_args()
    if not args.suite and not args.experiment and not args.resource_qa and not args.formal_qa:
        parser.error('Supply --suite, --experiment, --resource-qa or --formal-qa')
    try:
        summaries = ([verify_suite(args.suite)] if args.suite else [])
        summaries.extend(verify_experiment(directory) for directory in args.experiment)
        summaries.extend(verify_resource_qa(directory) for directory in args.resource_qa)
        summaries.extend(verify_formal_qa(directory) for directory in args.formal_qa)
    except (OSError, ValueError, KeyError, TypeError, StopIteration) as exc:
        print('Verification failed: ' + str(exc), file=sys.stderr)
        return 1
    print(json.dumps(summaries, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
