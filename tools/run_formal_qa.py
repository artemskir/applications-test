"""Run independent finite-model, preservation, stateful and mutation checks locally."""
import argparse
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,required=True)
    parser.add_argument('--seed',type=int,default=20261008)
    parser.add_argument('--examples',type=int,default=200)
    parser.add_argument('--symbolic',action='store_true',help='Requires optional symbolic-qa-requirements.txt')
    args=parser.parse_args()
    if args.examples < 1: parser.error('--examples must be positive')
    output=args.output_dir.resolve(); output.mkdir(parents=True,exist_ok=False)
    from verification import exhaustive, practical, stateful, name_quality, reconciliation
    results={}; failed=[]
    def run(label,operation):
        started=time.perf_counter()
        try:
            value=operation(); value['seconds']=round(time.perf_counter()-started,3)
            if not value['passed']: failed.append(label)
        except Exception as exc:
            import traceback
            value={'passed':False,'error':type(exc).__name__,'detail':str(exc),'traceback':traceback.format_exc()}; failed.append(label)
        results[label]=value
        (output/(label+'.json')).write_text(json.dumps(value,ensure_ascii=True,indent=2),'utf-8')
        print(json.dumps({'step':label,'passed':value['passed']}),flush=True)
    def exhaustive_check():
        value=exhaustive.check()
        if not value['passed'] and value.get('counterexample'):
            # Lengths are enumerated in increasing order: first failure has minimal row count.
            rows=[(r['name'],r['telephone'],r['date'],r['source']) for r in value['counterexample']]
            practical.save_book(output/'counterexample-minimal.xlsx',rows)
            value['minimality']='first counterexample by increasing sequence length, then alphabet order'
        return value
    run('exhaustive',exhaustive_check)
    run('fields',practical.fields)
    run('stateful',lambda:stateful.check(args.seed,args.examples))
    run('preservation',lambda:practical.cli_preservation(output/'xlsx'))
    run('critical-conditions',practical.critical_conditions)
    run('publication-faults',lambda:practical.publication_faults(output/'publication-faults'))
    run('names',name_quality.check)
    run('reconciliation',lambda:reconciliation.check(output/'reconciliation'))
    if results['preservation']['passed']:
        run('mutations',lambda:practical.mutations(output/'mutants',output/'xlsx/user-5-input.xlsx',output/'xlsx/user-5-output.xlsx'))
    else:
        results['mutations']={'passed':False,'status':'SKIPPED','reason':'positive control failed'}; failed.append('mutations')
    if args.symbolic:
        def symbolic():
            runs=[]
            for name,expected_exit in [('first_index',0),('deliberately_last_index',1)]:
                command=[sys.executable,'-X','utf8','-m','crosshair','check','verification.symbolic_contracts.'+name,
                         '--analysis_kind','PEP316','--report_all','--per_condition_timeout','10','--per_path_timeout','2']
                completed=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,encoding='utf-8',timeout=60)
                (output/('symbolic-'+name+'.log')).write_text(completed.stdout+completed.stderr,'utf-8')
                ok=completed.returncode==expected_exit and ('Confirmed over all paths' in completed.stdout if expected_exit==0 else 'false when calling' in completed.stdout)
                runs.append({'function':name,'command':command,'exit_code':completed.returncode,'passed':ok})
            return {'passed':all(r['passed'] for r in runs),'runs':runs,'scope':'bounded three-key arithmetic; no XLSX or name completeness proof'}
        run('symbolic',symbolic)
    else:
        results['symbolic']={'status':'NOT_REQUESTED','reason':'optional dependency, use --symbolic'}
    evidence={str(p.relative_to(ROOT)):sha256(p.read_bytes()).hexdigest()
              for folder in ('normalizer','verification') for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    evidence['docs/SPECIFICATION.md']=sha256((ROOT/'docs/SPECIFICATION.md').read_bytes()).hexdigest()
    for folder in ('fixtures','tests','tests_qa'):
        for p in (ROOT/folder).glob('*.py'): evidence[str(p.relative_to(ROOT))]=sha256(p.read_bytes()).hexdigest()
    for name in ('tools/run_formal_qa.py','tools/run_qa.py','tools/verify_artifacts.py','tools/generate_data.py','research/local-qa-requirements.txt','research/symbolic-qa-requirements.txt'):
        evidence[name]=sha256((ROOT/name).read_bytes()).hexdigest()
    summary={'passed':not failed,'status':'P0 PASS' if not failed else 'P0 FAIL','seed':args.seed,'failed':failed,
             'steps':{k:v.get('passed',v.get('status')) for k,v in results.items()},'source_sha256':evidence}
    summary['artifact_sha256']={str(p.relative_to(output)):sha256(p.read_bytes()).hexdigest() for p in output.rglob('*') if p.is_file()}
    (output/'results.json').write_text(json.dumps(summary,indent=2),'utf-8'); print(json.dumps(summary['steps']))
    return 0 if summary['passed'] else 1


if __name__=='__main__':
    raise SystemExit(main())
