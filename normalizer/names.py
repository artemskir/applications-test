import re
import unicodedata
from .models import common, failure, success
from .name_roles import classify, roles, key

BREAKS = r"[-‐‑‒–—'’]"


def analyze(cell):
    issue = common(cell, 'NAME')
    if issue:
        return issue
    if not isinstance(cell.value, str):
        return failure(cell, 'NAME_INVALID')
    value = unicodedata.normalize('NFC', cell.value)
    letters = [c for c in value if unicodedata.category(c).startswith('L')]
    latin = any('LATIN' in unicodedata.name(c, '') for c in letters)
    cyrillic = any('CYRILLIC' in unicodedata.name(c, '') for c in letters)
    if latin:
        return failure(cell, *(['NAME_MIXED_SCRIPT', 'NAME_LATIN_SCRIPT'] if cyrillic else ['NAME_LATIN_SCRIPT']))
    if not letters or any(not (unicodedata.category(c)[0] in 'LM' or c.isspace() or c in "-‐‑‒–—'’." ) for c in value):
        return failure(cell, 'NAME_INVALID')
    parts = []
    for word in value.split():
        for compound in re.split(BREAKS, word):
            segments = compound.split('.')
            if not compound or any(not segment or sum(c.isalpha() for c in segment) != 1 for segment in segments[:-1]):
                return failure(cell, 'NAME_INVALID')
            if segments[-1]:
                parts.append(segments[-1])
            parts.extend(segments[:-1])
            if not all(any(c.isalpha() for c in segment) for segment in segments if segment):
                return failure(cell, 'NAME_INVALID')
    for part in parts:
        characters = ''.join(c for c in part if c.isalpha())
        if any('CYRILLIC' in unicodedata.name(c, '') for c in characters):
            if not (characters.islower() or characters.isupper() or characters[0].isupper() and characters[1:].islower() or len(characters) == 1):
                return failure(cell, 'NAME_CASE_REVIEW')
    value = ' '.join(value.split())
    pieces = re.split('(' + BREAKS + r'|[ .])', value)
    for index, part in enumerate(pieces):
        if part and any(c.isalpha() for c in part):
            position = next(i for i, c in enumerate(part) if c.isalpha())
            pieces[index] = part[:position] + part[position].upper() + part[position + 1:].lower()
    normalized = ''.join(pieces)
    if '.' in normalized:
        result = failure(cell, 'NAME_INCOMPLETE')
        result.classification = 'UNKNOWN'
        return result
    classification, components = classify(normalized)
    # DEC-29 confirms the personal name, not the ambiguous remaining role.
    tokens = normalized.split()
    if classification == 'AMBIGUOUS' and len(tokens) == 3 and sum(key(t) == 'петрович' for t in tokens) == 1:
        evidence = [roles(t) if key(t) != 'петрович' else ({'AMBIGUOUS'}, True) for t in tokens]
        confirmed = [next(iter(r)) for r, uncertain in evidence if not uncertain and len(r) == 1]
        if sorted(confirmed) == ['FIRST_NAME', 'LAST_NAME']:
            components = [{'text': t, 'role': next(iter(r))} for t, (r, _) in zip(tokens, evidence)]
            personal = next(c['text'] for c in components if c['role'] == 'FIRST_NAME')
            result = success(cell, personal, codes=['NAME_AMBIGUOUS'], actions=[{
                'kind': 'NAME_COMPONENTS_EXTRACTED', 'details': {'original': cell.value,
                'normalized_full_name': normalized, 'components': components, 'first_name': personal,
                'review_required': True, 'rule_id': 'DEC-29'}}])
            result.classification, result.components = classification, components
            return result
    if classification not in ('FIRST_NAME', 'FULL_NAME'):
        code = {'UNKNOWN':'NAME_UNKNOWN', 'AMBIGUOUS':'NAME_AMBIGUOUS',
                'LAST_NAME':'NAME_NOT_FIRST', 'PATRONYMIC':'NAME_NOT_FIRST'}[classification]
        result = failure(cell, code)
    else:
        personal = next(component['text'] for component in components if component['role'] == 'FIRST_NAME')
        actions = [{'kind':'NAME_COMPONENTS_EXTRACTED', 'details':{'original':cell.value,
                    'normalized_full_name':normalized, 'components':components, 'first_name':personal}}] if classification == 'FULL_NAME' else []
        result = success(cell, personal, actions=actions)
    result.classification, result.components = classification, components
    return result
