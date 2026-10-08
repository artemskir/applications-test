"""Production bridge; expected answers live only in reference.py."""
from normalizer.models import RawCell, RawRow, FieldResult, RowResult
from normalizer import names, phone, dates, deduplicate
from normalizer.pipeline import source_result
from .reference import PHONES, Outcome


def make_rows(records, analyze=False):
    result = []
    for i, r in enumerate(records):
        values = (r.name, r.telephone, r.date, r.source)
        cells = [RawCell(v, 'n' if v is None else 's', f'{chr(65+j)}{i+2}') for j, v in enumerate(values)]
        if analyze:
            fields = [f(c) for f, c in zip((names.analyze, phone.analyze, dates.analyze, source_result), cells)]
        else:
            # Hand-built specification states isolate grouping from field parsing.
            canonicals = (r.name, '+79174005219' if r.telephone in PHONES[:2] else r.telephone,
                          r.date if r.date in ('2026-09-06','2026-09-07') else None, r.source)
            fields = []
            for j, (cell, canonical) in enumerate(zip(cells, canonicals)):
                codes = (['NAME_MISSING'] if j == 0 and canonical is None else
                         ['PHONE_MISSING'] if j == 1 and canonical is None else
                         ['DATE_UNSUPPORTED'] if j == 2 and canonical is None else [])
                fields.append(FieldResult(cell, canonical, canonical if canonical is not None else cell.value,
                                          codes=codes, status='MISSING' if cell.value is None else 'PROBLEM' if codes else 'NORMALIZED'))
        result.append(RowResult(RawRow(f'Test!{i+2}', 'Test', i+2, cells), fields))
    return result


def observe(rows):
    lookup = {r.raw.row_id: i for i, r in enumerate(rows)}
    return tuple(Outcome(lookup[r.representative_id], r.disposition, frozenset(r.codes), r.output_row,
                         tuple(f.display for f in r.data_fields) if r.resolution is not None else None,
                         tuple(lookup[f['donor_row_id']] if f['donor_row_id'] is not None else None
                               for f in r.resolution['fields']) if r.resolution is not None else None)
                 for r in rows)


def actual(records, analyze=False):
    rows = make_rows(records, analyze)
    deduplicate.apply(rows)
    return observe(rows)
