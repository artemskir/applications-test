"""Role quality and policy overrides are measured separately from resource integrity."""
from collections import Counter
import gzip
from hashlib import sha256
import itertools
import json
from pathlib import Path
import unicodedata
from normalizer import names, name_roles
from normalizer.models import RawCell
from .reference import role_assignments

ROOT = Path(__file__).resolve().parents[1]


def key(s):
    return unicodedata.normalize('NFC', s).casefold()


def check():
    # Read data directly; never use production.roles() to create reference role sets.
    payload = (ROOT/'normalizer/data/name_lexicon.json.gz').read_bytes()
    lexicon = {k:set(v) for k,v in json.loads(gzip.decompress(payload)).items()}
    labels = ('FIRST_NAME', 'LAST_NAME', 'PATRONYMIC')
    source = json.loads((ROOT/'verification/name_benchmark.json').read_text('utf-8'))
    old = json.loads((ROOT/'research/name_gold.json').read_text('utf-8'))
    overrides = []; miss_first = []; measurements = []
    reviewed = name_roles.REVIEWED_FIRST | name_roles.REVIEWED_LAST | name_roles.REVIEWED_MIDDLE
    for token in sorted(reviewed):
        raw_roles = {r for r in labels if token in lexicon[r]}
        effective, _ = name_roles.roles(token)
        if raw_roles-effective:
            overrides.append({'token':token, 'raw_roles':sorted(raw_roles), 'policy_roles':sorted(effective),
                              'raw_assignments': role_assignments([raw_roles])})
    unsupported = lexicon['FIRST_NAME']-lexicon['NEN_FIRST_NAME']-reviewed
    misses = Counter()
    for token in sorted(unsupported):
        effective, ambiguous = name_roles.roles(token)
        misses['AMBIGUOUS' if ambiguous else 'UNKNOWN' if not effective else 'ROLE_RETAINED'] += 1
        if len(miss_first)<20: miss_first.append({'token':token, 'roles':sorted(r for r in labels if token in lexicon[r]), 'ambiguous':ambiguous})
    for title, data in [('external_author_roles',source['examples']), ('development_gold',old)]:
        rows = []; confusion = Counter(); false_accept = false_reject = wrong_role = 0
        for e in data:
            result = names.analyze(RawCell(e['text']))
            predicted = result.classification or 'UNKNOWN'
            wanted = e['label']; confusion[(wanted,predicted)] += 1
            confident = predicted in labels+('FULL_NAME',)
            false_accept += result.canonical is not None and wanted not in ('FIRST_NAME','FULL_NAME')
            false_reject += result.canonical is None and wanted in ('FIRST_NAME','FULL_NAME')
            wrong_role += confident and predicted != wanted
            row = {'text':e['text'], 'expected':wanted, 'predicted':predicted, 'canonical':result.canonical, 'codes':result.codes,
                   'raw_roles': {t:sorted(r for r in labels if key(t) in lexicon[r]) for t in e['text'].split()}}
            rows.append(row)
        measurements.append({'dataset':title, 'n':len(rows), 'correct_role':sum(e['expected']==e['predicted'] for e in rows),
                             'confusion':[{'expected':a,'predicted':b,'count':n} for (a,b),n in sorted(confusion.items())],
                             'false_first_name_acceptance':false_accept, 'first_name_abstention':false_reject,
                             'wrong_confident_role':wrong_role, 'unknown':sum(e['predicted']=='UNKNOWN' for e in rows),
                             'ambiguous':sum(e['predicted']=='AMBIGUOUS' for e in rows), 'examples':rows})
    extended = ['Иван Иванов Петрович', 'Иван Иванов Кирилл', 'Арзу Лутфияр кызы', 'Рамиз Рустам оглы',
                'Иван Иванов Петрович Старший', 'Нгуен', 'Эдвард', 'Нурлан', 'Оглы', 'Клиент Кирилл', 'ООО Ромашка']
    boundary = []
    for value in extended:
        result = names.analyze(RawCell(value))
        boundary.append({'text':value, 'classification':result.classification, 'canonical':result.canonical, 'codes':result.codes})
    # Quality misses are disclosed, not relabelled as successes or used to change the policy.
    return {'passed': True, 'lexicon_sha256':sha256(payload).hexdigest(), 'external_provenance':source['provenance'],
            'policy_overrides':overrides, 'nen_missing_first_members':len(unsupported), 'nen_missing_decisions':dict(misses),
            'nen_missing_examples':miss_first, 'measurements':measurements, 'boundary_examples':boundary,
            'quality_gate': 'descriptive; no population precision claim; no dictionary changes'}
