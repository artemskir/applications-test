from collections import Counter, defaultdict
from itertools import combinations
import unicodedata
from .models import HEADERS, dumps


def name_key(text):
    # DEC-33 is a comparison operation, never an output spelling correction.
    return unicodedata.normalize('NFC', text).casefold().replace('ё', 'е')


def name_identity(result):
    personal = name_key(result.canonical)
    components = Counter(name_key(c['text']) for c in result.components if c['role'] != 'FIRST_NAME')
    return personal, components


def compatible_names(left, right):
    ln, lc = name_identity(left)
    rn, rc = name_identity(right)
    return ln == rn and (lc <= rc or rc <= lc)


def compare(result, is_name=False):
    if result.status == 'MISSING':
        return ('missing',)
    if is_name and result.canonical is not None:
        personal, components = name_identity(result)
        return ('canonical', dumps([personal, sorted(components.elements())]))
    value = result.canonical if result.canonical is not None else result.raw.value
    return ('canonical' if result.canonical is not None else result.raw.kind, dumps(value))


def resolution_details(first, selected, donors):
    return {'rule_id':'DEC-31', 'admitted':first.admitted,
            'conflict_codes':[c['code'] for c in first.conflicts],
            'fields':[{'field':HEADERS[i], 'donor_row_id':donor.raw.row_id if donor else None,
                       'input_cell':donor.raw.cells[i].coordinate if donor else None,
                       'canonical':result.canonical, 'value':result.display,
                       'rule_id':'KEEP_FIRST_SOURCE' if i == 3 else
                                 'FIRST_CONFIRMED_VALUE' if donor else 'NO_CONFIRMED_VALUE'}
                      for i, (result, donor) in enumerate(zip(selected, donors))]}


def apply(rows):
    groups = defaultdict(list)
    for row in rows:
        row.disposition, row.output_row = 'UNGROUPED', None
        row.conflicts = []
        row.resolved_fields, row.resolution = None, None
        row.representative_id = row.raw.row_id
        key = row.fields[1].canonical
        if key is not None:
            groups[key].append(row)
    for group in groups.values():
        first = group[0]
        for row in group:
            row.representative_id = first.raw.row_id
            row.disposition = 'REPRESENTATIVE' if row is first else 'DUPLICATE'
        for index, code in [(0, 'DUPLICATE_NAME_CONFLICT'), (2, 'DUPLICATE_DATE_CONFLICT')]:
            confirmed = [row for row in group if row.fields[index].canonical is not None]
            distinct = {}
            for row in confirmed:
                distinct.setdefault(compare(row.fields[index], is_name=index == 0), row)
            mismatch = (any(not compatible_names(a.fields[0], b.fields[0]) for a,b in combinations(distinct.values(), 2))
                        if index == 0 else len(distinct) > 1)
            if mismatch:
                variants = {}
                for row in confirmed:
                    result = row.fields[index]
                    key = compare(result, is_name=index == 0)
                    full = next((a['details']['normalized_full_name'] for a in result.actions
                                 if a['kind'] == 'NAME_COMPONENTS_EXTRACTED'), result.display)
                    variants.setdefault(key, {'value':full, 'row_ids':[]})['row_ids'].append(row.raw.row_id)
                conflict = {'code':code, 'field':index, 'variants':list(variants.values())}
                for row in group:
                    row.conflicts.append(conflict)
        donors = [next((row for row in group if row.fields[i].canonical is not None and not row.fields[i].codes), None)
                  for i in range(3)] + [first]
        first.resolved_fields = [(donor or first).fields[i] for i, donor in enumerate(donors)]
        first.resolution = resolution_details(first, first.resolved_fields, donors)
    output_number = 2
    for row in rows:
        if row.admitted:
            row.output_row = output_number
            output_number += 1
    return groups
