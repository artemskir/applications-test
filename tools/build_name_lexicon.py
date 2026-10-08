"""Build offline, deterministic role evidence from the researched source snapshots."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import unicodedata


def key(text):
    return unicodedata.normalize('NFC', text).casefold()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--sources', type=Path, required=True)
    ap.add_argument('--output-dir', type=Path, required=True)
    args = ap.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=False)
    import duckdb
    conn = duckdb.connect()
    lexicon = {}
    source_hashes = {}
    for role, dataset in [('FIRST_NAME', 'names'), ('LAST_NAME', 'surnames'), ('PATRONYMIC', 'midnames')]:
        path = args.sources / 'russiannames/russiannames/data' / (dataset + '.parquet')
        lexicon[role] = sorted({key(row[0]) for row in conn.execute('SELECT text FROM read_parquet(?)', [str(path)]).fetchall()})
        source_hashes[str(path.relative_to(args.sources))] = hashlib.sha256(path.read_bytes()).hexdigest()
    conn.close()
    path = args.sources / 'nen-imena-dataset/data/names.json'
    nen = json.loads(path.read_text(encoding='utf-8'))
    lexicon['NEN_FIRST_NAME'] = sorted({key(v) for record in nen for v in [record['name'], *record.get('short_forms', []), *record.get('international_forms', [])]})
    source_hashes[str(path.relative_to(args.sources))] = hashlib.sha256(path.read_bytes()).hexdigest()
    payload = json.dumps(lexicon, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    bundle = gzip.compress(payload, mtime=0)
    (args.output_dir / 'name_lexicon.json.gz').write_bytes(bundle)
    manifest = {'format_version': 1, 'sources': {}, 'source_sha256': source_hashes,
                'bundle_sha256': hashlib.sha256(bundle).hexdigest(), 'counts': {k:len(v) for k,v in lexicon.items()}}
    for name, license_name in [('russiannames','BSD-3-Clause'), ('nen-imena-dataset','CC-BY-4.0')]:
        repo = args.sources / name
        commit = subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()
        manifest['sources'][name] = {'commit':commit,'license':license_name}
        (args.output_dir / (name + '-LICENSE.txt')).write_bytes((repo/'LICENSE').read_bytes())
    (args.output_dir/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(manifest))


if __name__ == '__main__':
    main()
