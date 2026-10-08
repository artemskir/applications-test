"""Run reproducible QA with a mandatory test registry and subprocess coverage."""
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from verification.test_driver import validate


def execute(command, env, timeout):
    started = time.perf_counter()
    try:
        run = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True, encoding='utf-8', timeout=timeout)
        return {'command': command, 'exit_code': run.returncode, 'seconds': round(time.perf_counter()-started, 3)}, run.stdout+run.stderr
    except (subprocess.TimeoutExpired, OSError) as exc:
        return {'command': command, 'exit_code': None, 'seconds': round(time.perf_counter()-started, 3),
                'error': type(exc).__name__, 'detail': str(exc)}, str(exc)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--mode', choices=['smoke', 'p0', 'generated', 'adversarial', 'all'], default='all')
    ap.add_argument('--seed', type=int, default=42)
    ap.add_argument('--examples', type=int, default=300)
    ap.add_argument('--timeout', type=float, default=600)
    ap.add_argument('--output-dir', type=Path, required=True)
    args = ap.parse_args()
    if args.examples < 1 or args.timeout <= 0:
        ap.error('--examples and --timeout must be positive')
    output = args.output_dir.resolve(); output.mkdir(parents=True, exist_ok=False)
    rcfile = output/'coverage.ini'
    rcfile.write_text('[run]\nbranch = True\npatch = subprocess\nparallel = True\n'
                      'core = ctrace\ninclude =\n    */normalizer/*\n    */normalize.py\n    */restore.py\n', 'utf-8')
    env = dict(os.environ, QA_EXAMPLES=str(args.examples), QA_SEED=str(args.seed),
               COVERAGE_FILE=str(output/'.coverage'), COVERAGE_RCFILE=str(rcfile))
    labels = ['p0', 'generated'] if args.mode == 'all' else [args.mode]
    registry = json.loads((ROOT/'verification/p0_registry.json').read_text('utf-8'))
    records = []
    for label in labels:
        env['QA_STATS_PATH'] = str(output/(label+'-statistics.json'))
        ledger_path = output/(label+'-tests.json')
        command = [sys.executable, '-X', 'utf8', '-m', 'coverage', 'run', '-m', 'verification.test_driver',
                   '--suite', label, '--ledger', str(ledger_path)]
        record, log = execute(command, env, args.timeout)
        record['label'] = label
        if ledger_path.exists():
            ledger = json.loads(ledger_path.read_text('utf-8'))
            record['gate'] = validate(ledger, registry[label])
            record['tests_run'] = ledger['tests_run']
        else:
            record['gate'] = {'passed': False, 'reason': 'Executed-test ledger missing'}
        (output/(label+'.log')).write_text(log, 'utf-8')
        if label == 'generated':
            stats_path = output/(label+'-statistics.json')
            stats = json.loads(stats_path.read_text('utf-8')) if stats_path.exists() else {}
            record['generation_verified'] = stats.get('seed') == args.seed and bool(stats.get('calls')) and all(n > 0 for n in stats.get('calls', {}).values())
            if not record['generation_verified']: record['gate']['passed'] = False
        records.append(record)
    coverage_steps = []
    for name, command in [('combine', [sys.executable, '-m', 'coverage', 'combine', str(output)]),
                          ('json', [sys.executable, '-m', 'coverage', 'json', '-o', str(output/'coverage.json')])]:
        record, log = execute(command, env, args.timeout)
        (output/(name+'.log')).write_text(log, 'utf-8'); coverage_steps.append(record)
    coverage = json.loads((output/'coverage.json').read_text('utf-8')) if (output/'coverage.json').exists() else {}
    cli = {p: len(f.get('executed_lines', [])) for p, f in coverage.get('files', {}).items()
           if Path(p).name in ('normalize.py', 'restore.py')}
    cli_verified = bool(cli) if args.mode in ('p0', 'adversarial', 'generated', 'all') else True
    passed = all(r['exit_code'] == 0 and r['gate']['passed'] for r in records) and all(r['exit_code'] == 0 for r in coverage_steps) and cli_verified
    actual_ids = [t['id'] for label in labels if (output/(label+'-tests.json')).exists()
                  for t in json.loads((output/(label+'-tests.json')).read_text('utf-8'))['tests']]
    report = {'mode': args.mode, 'seed': args.seed, 'examples_per_property_limit': args.examples, 'passed': passed,
              'runs': records, 'coverage_steps': coverage_steps, 'cli_executed_lines': cli,
              'coverage_limitation': 'Parent and Python subprocess coverage; branch coverage is not MC/DC',
              'adversarial_included': args.mode in ('p0', 'all', 'adversarial'),
              'adversarial_test_ids': sorted(set(registry['adversarial']) & set(actual_ids)),
              'registry_sha256': sha256((ROOT/'verification/p0_registry.json').read_bytes()).hexdigest()}
    (output/'results.json').write_text(json.dumps(report, indent=2), 'utf-8')
    print(json.dumps(report))
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
