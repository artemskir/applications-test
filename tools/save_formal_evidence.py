"""Freeze checked local QA evidence for review in Git; no generated XLSX is committed."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.verify_artifacts import verify_formal_qa, verify_resource_qa, verify_suite
from verification.test_driver import validate
from normalizer import SPEC_VERSION


def read(path):
    return json.loads(path.read_text('utf-8'))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--formal',type=Path,required=True)
    parser.add_argument('--qa',type=Path,required=True)
    parser.add_argument('--resource',type=Path,required=True)
    parser.add_argument('--suite',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists(): parser.error('Output evidence already exists')
    checks=[verify_formal_qa(args.formal),verify_resource_qa(args.resource),verify_suite(args.suite)]
    qa=read(args.qa/'results.json')
    registry=read(ROOT/'verification/p0_registry.json')
    assert qa['passed'] is True and qa['mode']=='all'
    for label in ('p0','generated'):
        assert validate(read(args.qa/(label+'-tests.json')),registry[label])['passed']
    assert len(qa['adversarial_test_ids'])==len(registry['adversarial'])
    formal=read(args.formal/'results.json')
    steps={k:read(args.formal/(k+'.json')) for k,v in formal['steps'].items() if v is True}
    stats=read(args.qa/'generated-statistics.json')
    assert stats['seed']==qa['seed'] and sum(stats['calls'].values())>0
    artifacts={}
    for folder in (args.formal,args.qa,args.resource,args.suite):
        for p in folder.rglob('*'):
            if p.is_file() and not p.name.startswith('.coverage'):
                artifacts[str(p.resolve().relative_to(ROOT)).replace('\\','/')]=sha256(p.read_bytes()).hexdigest()
    result={'status':'P0 PASS','spec_version':SPEC_VERSION,'baseline_commit':'0d9c203','verifications':checks,
            'formal_summary':formal,'formal_steps':steps,'qa_summary':qa,
            'executed_tests':{label:read(args.qa/(label+'-tests.json')) for label in ('p0','generated')},
            'generation_statistics':stats,'coverage_totals':read(args.qa/'coverage.json')['totals'],
            'resource_summary':read(args.resource/'results.json'),
            'prior_publication_defects':read(ROOT/'generated/publication-baseline-1.6/results.json')
                if (ROOT/'generated/publication-baseline-1.6/results.json').exists() else {'status':'NOT_AVAILABLE'},
            'boolean_before_fix':read(ROOT/'generated/publication-boolean-before-fix/results.json')
                if (ROOT/'generated/publication-boolean-before-fix/results.json').exists() else {'status':'NOT_AVAILABLE'},
            'evidence_tool_sha256':sha256(Path(__file__).read_bytes()).hexdigest(),
            'artifact_sha256':artifacts,
            'limitations':'Finite model and concrete fixtures only; no population precision or whole-program proof'}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=True,indent=2)+'\n','utf-8')
    print(json.dumps({'status':result['status'],'output':str(args.output),'artifacts':len(artifacts)}))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
