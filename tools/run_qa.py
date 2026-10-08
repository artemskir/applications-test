"""Run bounded, reproducible QA modes and save real logs and coverage."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--mode',choices=['smoke','p0','generated','adversarial','all'],default='all')
    ap.add_argument('--seed',type=int,default=42)
    ap.add_argument('--examples',type=int,default=300)
    ap.add_argument('--output-dir',type=Path,required=True)
    args=ap.parse_args()
    if args.examples<1:
        ap.error('--examples must be positive')
    output=args.output_dir.resolve(); output.mkdir(parents=True,exist_ok=False)
    env=dict(os.environ,QA_EXAMPLES=str(args.examples),QA_SEED=str(args.seed),COVERAGE_FILE=str(output/'.coverage'))
    steps=[]
    if args.mode=='smoke':
        steps.append(('smoke',['discover','-s','tests','-p','test_regressions.py','-v']))
    if args.mode in ('p0','all'):
        steps.append(('p0',['discover','-s','tests','-v']))
    if args.mode in ('generated','all'):
        steps.append(('generated',['discover','-s','tests_qa','-v']))
    if args.mode=='adversarial':
        # Includes actual CRC/ZIP/XML corruption, write failures, limits and two CLI processes.
        steps.append(('adversarial',['discover','-s','tests','-p','test_normalizer.py','-v']))
    records=[]
    for index,(label,tests) in enumerate(steps):
        env['QA_STATS_PATH']=str(output/(label+'-statistics.json'))
        command=[sys.executable,'-m','coverage','run','--branch','--source=normalizer']
        if index:
            command+=['--append']
        command+=['-m','unittest',*tests]
        started=time.perf_counter()
        run=subprocess.run(command,cwd=ROOT,env=env,capture_output=True,text=True,encoding='utf-8',timeout=600)
        (output/(label+'.log')).write_text(run.stdout+run.stderr,encoding='utf-8')
        records.append({'label':label,'command':command,'exit_code':run.returncode,'seconds':round(time.perf_counter()-started,3)})
    cov=subprocess.run([sys.executable,'-m','coverage','json','-o',str(output/'coverage.json')],cwd=ROOT,env=env,capture_output=True,text=True,encoding='utf-8')
    passed=all(step['exit_code']==0 for step in records) and cov.returncode==0
    report={'mode':args.mode,'seed':args.seed,'examples_per_property_limit':args.examples,'passed':passed,'runs':records,
            'coverage_limitation':'Parent-process coverage only; subprocess CLI not instrumented'}
    (output/'results.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report))
    return 0 if passed else 1


if __name__=='__main__':
    raise SystemExit(main())
