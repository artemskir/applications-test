"""Targeted fault injections in memory; production files are never edited."""
from datetime import date
from io import StringIO
import json
from pathlib import Path
import re
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from normalizer import phone,dates,names,models,deduplicate,report
from test_normalizer import FieldTests,PipelineTests
from test_regressions import ReviewRegressions


def main():
    import argparse
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output-dir',type=Path,required=True)
    args=ap.parse_args(); args.output_dir.mkdir(parents=True,exist_ok=False)
    old_shape=phone.shape; old_date=dates.analyze; old_apply=deduplicate.apply
    old_write=report.Writer.audit
    def strip_eights(candidate):
        token=re.sub('['+phone.SEPARATORS+']','',candidate)
        return old_shape(token.lstrip('8')) if token.startswith('8') else old_shape(candidate)
    def partial(candidate):
        token=re.sub('['+phone.SEPARATORS+']','',candidate)
        return old_shape(token[:12] if token.startswith('+') else token[:11])
    def wrong_day(cell,parsed,context=None,order=None):
        return models.success(cell,f'{parsed.year:04d}-{parsed.day:02d}-{parsed.month:02d}')
    def no_calendar(cell):
        if isinstance(cell.value,str) and cell.value=='31.04.2026':
            return models.success(cell,'2026-04-31')
        return old_date(cell)
    def missing_disabled(cell,field):
        if cell.value is None:
            return models.success(cell,'invented')
        return None
    def last_representative(rows):
        reversed_rows=list(reversed(rows))
        return old_apply(reversed_rows)
    def no_row_audit(self,kind,*args,**kwargs):
        if kind!='ROW':
            return old_write(self,kind,*args,**kwargs)
    def erase_original(self,name,values):
        if name=='Оригинал' and values and values[0]!='row_id':
            values=list(values); values[3]='overwritten'
        return original_put(self,name,values)
    original_put=report.Writer.put
    def merge_empty_phones(rows):
        for row in rows:
            if row.fields[1].canonical is None:
                row.fields[1].canonical='+70000000001'
        return old_apply(rows)
    cases=[
        ('M01-strip-all-leading-eights',phone,'shape',strip_eights,FieldTests,'test_all_catalog_oracles'),
        ('M02-accept-partial-phone',phone,'shape',partial,FieldTests,'test_all_catalog_oracles'),
        ('M03-swap-day-month',dates,'output',wrong_day,FieldTests,'test_all_catalog_oracles'),
        ('M04-disable-calendar-check',dates,'analyze',no_calendar,FieldTests,'test_all_catalog_oracles'),
        ('M05-incorrect-missing',models,'common',missing_disabled,FieldTests,'test_all_catalog_oracles'),
        ('M06-last-duplicate',deduplicate,'apply',last_representative,PipelineTests,'test_actual_suite_valid_inputs_and_structural_refusals'),
        ('M07-drop-ROW-audit',report.Writer,'audit',no_row_audit,ReviewRegressions,'test_clean_sheet_and_plain_review_preserve_every_problem'),
        ('M08-overwrite-original',report.Writer,'put',erase_original,ReviewRegressions,'test_clean_sheet_and_plain_review_preserve_every_problem'),
        ('M09-merge-missing-phones',deduplicate,'apply',merge_empty_phones,PipelineTests,'test_actual_suite_valid_inputs_and_structural_refusals'),
    ]
    results=[]
    for label,target,attribute,replacement,test_class,test_method in cases:
        log=StringIO()
        # common/analyze/apply were imported into consumer modules; patch the real callsites.
        contexts=[patch.object(target,attribute,replacement)]
        if label=='M05-incorrect-missing':
            contexts += [patch.object(module,'common',replacement) for module in (phone,dates,names)]
        if label in ('M06-last-duplicate','M09-merge-missing-phones'):
            import normalizer.pipeline as pipeline
            contexts += [patch.object(pipeline,'apply',replacement)]
        from contextlib import ExitStack
        with ExitStack() as stack:
            for context in contexts:
                stack.enter_context(context)
            result=unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.TestSuite([test_class(test_method)]))
        detected=not result.wasSuccessful()
        (args.output_dir/(label+'.log')).write_text(log.getvalue(),encoding='utf-8')
        results.append({'id':label,'detected':detected,'failures':len(result.failures),'errors':len(result.errors),
                        'test':test_class.__name__+'.'+test_method})
    passed=all(r['detected'] for r in results)
    (args.output_dir/'results.json').write_text(json.dumps({'passed':passed,'mutations':results},indent=2),encoding='utf-8')
    print(json.dumps({'passed':passed,'detected':sum(r['detected'] for r in results),'total':len(results)}))
    return 0 if passed else 1


if __name__=='__main__':
    raise SystemExit(main())
