"""Reproducible role comparison; external tools never decide production behavior."""
import argparse
from collections import Counter
import hashlib
import itertools
import json
from pathlib import Path
import re
import subprocess
import sys
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
ROLES = ('FIRST_NAME', 'LAST_NAME', 'PATRONYMIC')


def key(text):
    return unicodedata.normalize('NFC', text).casefold()


def classify(text, lookup):
    # Initials, role labels and malformed text cannot establish a full personal name.
    parts = text.split()
    if not parts or any(not re.fullmatch(r'[^\W\d_]+(?:[-’\'][^\W\d_]+)*', p) for p in parts):
        return 'UNKNOWN'
    roles = [lookup(p) for p in parts]
    if len(parts) == 1:
        return next(iter(roles[0])) if len(roles[0]) == 1 else 'AMBIGUOUS' if roles[0] else 'UNKNOWN'
    if any(not r for r in roles):
        return 'UNKNOWN'
    assignments = [combo for combo in itertools.product(*roles)
                   if combo.count('FIRST_NAME') == 1 and len(set(combo)) == len(combo)]
    if len(assignments) == 1:
        return 'FULL_NAME'
    return 'AMBIGUOUS'


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--sources', type=Path, default=ROOT / 'generated/name-sources')
    ap.add_argument('--output-dir', type=Path, required=True)
    args = ap.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=False)
    sources = args.sources.resolve()
    sys.path[:0] = [str(sources / 'russiannames'), str(sources / 'pytrovich')]
    import duckdb
    from russiannames.parser import NamesParser
    from pytrovich.detector import PetrovichGenderDetector
    from normalizer.names import analyze as production_name
    from normalizer.models import RawCell

    rn_sets = {}
    connection = duckdb.connect()
    for role, dataset in zip(ROLES, ('names', 'surnames', 'midnames')):
        rows = connection.execute('SELECT text FROM read_parquet(?)',
                                  [str(sources / 'russiannames/russiannames/data' / (dataset + '.parquet'))]).fetchall()
        rn_sets[role] = {key(row[0]) for row in rows}
    connection.close()
    sn_sets = {}
    for role, dataset in zip(ROLES, ('names', 'surnames', 'midnames')):
        path = sources / 'russian_names' / (dataset + '.jsonl')
        sn_sets[role] = {key(json.loads(line)['text']) for line in path.read_text(encoding='utf-8').splitlines() if line}
    nen = json.loads((sources / 'nen-imena-dataset/data/names.json').read_text(encoding='utf-8'))
    nen_primary = {key(r['name']) for r in nen}
    nen_forms = {key(v) for r in nen for field in ('short_forms', 'international_forms') for v in r.get(field, [])}
    parser = NamesParser()
    detector = PetrovichGenderDetector()
    gold = json.loads((ROOT / 'research/name_gold.json').read_text(encoding='utf-8'))
    rows = []
    def lookup(sets, text):
        return {role for role, words in sets.items() if key(text) in words}
    for case in gold:
        raw = parser.parse(case['text'])
        native = ('FULL_NAME' if raw.get('parsed') and any(raw.get(p) for p in ('sn', 'mn')) and raw.get('fn') else
                  'FIRST_NAME' if raw.get('parsed') and raw.get('fn') else
                  'LAST_NAME' if raw.get('parsed') and raw.get('sn') and not raw.get('fn_s') else 'UNKNOWN')
        tokens = case['text'].split()
        evidence = [{'token': token, 'russiannames': sorted(lookup(rn_sets, token)),
                     'russian_names': sorted(lookup(sn_sets, token)),
                     'nen_primary': key(token) in nen_primary, 'nen_form': key(token) in nen_forms}
                    for token in tokens]
        # Petrovich expects a role as input: collect evidence, never convert gender into a role.
        morphology = {role: str(detector.detect(**{field: case['text']})) for role, field in
                      zip(ROLES, ('firstname', 'lastname', 'middlename'))}
        predictions = {'russiannames_native': native,
                       'russiannames_membership': classify(case['text'], lambda t: lookup(rn_sets, t)),
                       'russian_names_membership': classify(case['text'], lambda t: lookup(sn_sets, t)),
                       'nen_first_names_only': classify(case['text'], lambda t: {'FIRST_NAME'} if key(t) in nen_primary | nen_forms else set()),
                       'approved_conservative_policy': production_name(RawCell(case['text'])).classification or 'UNKNOWN'}
        rows.append({**case, 'predictions': predictions, 'memberships': evidence, 'native_parse': raw,
                     'pytrovich_gender_given_role': morphology})
    parser._store.close()
    metrics = {}
    for name in rows[0]['predictions']:
        confusion = Counter((r['label'], r['predictions'][name]) for r in rows)
        matched = sum(r['label'] == r['predictions'][name] for r in rows)
        decisive = [r for r in rows if r['predictions'][name] not in ('UNKNOWN', 'AMBIGUOUS')]
        false_positive = [r['text'] for r in decisive if r['label'] != r['predictions'][name]]
        metrics[name] = {'correct': matched, 'total': len(rows), 'accuracy': matched / len(rows),
                         'decisive': len(decisive), 'decisive_correct': len(decisive) - len(false_positive),
                         'false_positive_texts': false_positive,
                         'confusion': [{'gold': a, 'predicted': b, 'count': n} for (a, b), n in sorted(confusion.items())]}
    snapshots = {}
    for repo in ('russiannames', 'russian_names', 'pytrovich', 'nen-imena-dataset'):
        sha = subprocess.check_output(['git', '-C', str(sources / repo), 'rev-parse', 'HEAD'], text=True).strip()
        snapshots[repo] = {'commit': sha}
    data_hashes = {str(p.relative_to(sources)): hashlib.sha256(p.read_bytes()).hexdigest()
                   for p in [*(sources / 'russiannames/russiannames/data').glob('*.parquet'),
                             *(sources / 'russian_names').glob('*.jsonl'), sources / 'nen-imena-dataset/data/names.json']}
    report = {'gold_sha256': hashlib.sha256((ROOT / 'research/name_gold.json').read_bytes()).hexdigest(),
              'sources': snapshots, 'data_sha256': data_hashes, 'counts': {'russiannames': {k: len(v) for k, v in rn_sets.items()},
              'russian_names': {k: len(v) for k, v in sn_sets.items()}, 'nen_primary': len(nen_primary), 'nen_forms': len(nen_forms)},
              'metrics': metrics, 'pytrovich_role_classification': 'UNSUPPORTED: role is supplied by the caller', 'examples': rows}
    (args.output_dir / 'results.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    lines = ['# Сравнение распознавания роли имени', '', '| Значение | Эталон | Parser | RN-словарь | Sorokin | НЭН | Политика 1.4 |', '|---|---|---|---|---|---|---|']
    lines += ['| ' + ' | '.join([r['text'], r['label'], *r['predictions'].values()]) + ' |' for r in rows]
    (args.output_dir / 'comparison.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(json.dumps({'output': str(args.output_dir), 'metrics': metrics}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    raise SystemExit(main())
