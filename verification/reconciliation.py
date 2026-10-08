"""Independent literal examples for spec 1.7, real CLI, and new mutation controls."""
from pathlib import Path
from collections import Counter
import json
import subprocess
import sys
from unittest.mock import patch
from openpyxl import load_workbook
from fixtures.reconciliation_cases import ROWS, EXPECTED
from tools.generate_data import write_workbook
from normalizer import deduplicate, names
from normalizer.models import RawCell
from .inventory import reconcile
from .adapter import make_rows, observe, actual
from .reference import Record, evaluate

ROOT = Path(__file__).resolve().parents[1]


def check(folder):
    folder.mkdir()
    source, output = folder/'user-input.xlsx',folder/'user-output.xlsx'
    write_workbook(source, ROWS)
    raw = source.read_bytes()
    command = [sys.executable,'-X','utf8',str(ROOT/'normalize.py'),'--input',str(source),'--output',str(output)]
    run = subprocess.run(command,cwd=ROOT,capture_output=True,text=True,encoding='utf-8',timeout=60)
    (folder/'cli.log').write_text(run.stdout+run.stderr,'utf-8')
    assert run.returncode==0 and source.read_bytes()==raw, run.stderr
    inventory = reconcile(raw,output.read_bytes())
    book = load_workbook(output,read_only=True)
    try:
        assert list(book['Данные'].values)[1:]==EXPECTED
        assert len(list(book['Проблемы'].values)[1:])==1
        (folder/'expected.json').write_text(json.dumps(EXPECTED,ensure_ascii=True,indent=2),'utf-8')
    finally:
        book.close()
    records = [Record(None,'+79174005219','broken_date','first'),
               Record('Иван','+79174005219','2026-09-06','second'),
               Record('Кирилл','+79174005219','2026-09-07','third')]
    expected = evaluate(records)
    def matches():
        return actual(records)==expected
    def pair_matches(values):
        rows = make_rows([Record(n,'+79174005219','2026-09-06','сайт') for n in values],analyze=True)
        deduplicate.apply(rows)
        return rows[0].admitted and not rows[0].conflicts
    def wrong_selection(rows):
        original_apply(rows)
        rows[0].resolved_fields[0]=rows[-1].fields[0]
    original_apply = deduplicate.apply
    mutation_cases = [
        ('last-confirmed-name', matches, patch.object(deduplicate,'apply',wrong_selection)),
        ('lose-name-conflict', matches, patch.object(deduplicate,'compatible_names',lambda a,b:True)),
        ('fio-order-conflict',lambda:pair_matches(['Борисова Алёна','Алёна Борисова']),
            patch.object(deduplicate,'name_identity',lambda r:(r.raw.value,Counter()))),
        ('yo-spelling-conflict',lambda:pair_matches(['Королёва Дарья','Королева Дарья']),
            patch.object(deduplicate,'name_identity',lambda r:(r.raw.value,Counter()))),
        ('wrong-first-component',lambda:names.analyze(RawCell('Макарова Нина')).canonical=='Нина',
            patch.object(names,'classify',lambda text:('FULL_NAME',[{'text':'Макарова','role':'FIRST_NAME'},
                                                                {'text':'Нина','role':'LAST_NAME'}]))),
        ('erase-inside-word',lambda:names.analyze(RawCell('Смирнов Ол\u200bег')).canonical is None,
            patch.object(names,'strip_boundary_invisibles',lambda text:(text.replace('\u200b',''),[]))),
    ]
    results=[]
    for label, positive, context in mutation_cases:
        assert positive(), ('positive control',label)
        with context:
            detected = not positive()
        assert detected, ('surviving mutant',label)
        results.append({'id':label,'detected':detected})
    return {'passed':True,'cli':command,'exit_code':run.returncode,'user_inventory':inventory,
            'expected_rows':len(EXPECTED),'user_cases':len(ROWS),'mutations':results,
            'detected':len(results),'total':len(results),
            'scope':'user-labelled examples, group choices, contextual names and narrow Unicode boundary policy'}
