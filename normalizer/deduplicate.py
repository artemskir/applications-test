from collections import defaultdict
import unicodedata
from .models import dumps


def compare(result, is_name=False):
    if result.status == 'MISSING':
        return ('missing',)
    value = result.canonical if result.canonical is not None else result.raw.value
    if is_name and result.canonical is not None:
        for action in result.actions:
            if action['kind'] == 'NAME_COMPONENTS_EXTRACTED':
                value = action['details']['normalized_full_name']
                break
    if is_name and isinstance(value, str):
        value = unicodedata.normalize('NFC', value)
    return ('canonical' if result.canonical is not None else result.raw.kind, dumps(value))


def apply(rows):
    groups = defaultdict(list)
    for row in rows:
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
            variants = {}
            for row in group:
                key = compare(row.fields[index], is_name=index == 0)
                variants.setdefault(key, {'value': row.fields[index].display, 'row_ids': []})['row_ids'].append(row.raw.row_id)
            if len(variants) > 1:
                conflict = {'code': code, 'field': index, 'variants': list(variants.values())}
                for row in group:
                    row.conflicts.append(conflict)
    output_number = 2
    for row in rows:
        if row.admitted:
            row.output_row = output_number
            output_number += 1
    return groups
