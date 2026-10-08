"""Inspect pinned source records, including their frequencies; no business decisions."""
import argparse
from hashlib import sha256
import itertools
import json
from pathlib import Path
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
TOKENS = ['Иван','Андрей','Мария','Павел','Вера','Нина','Денис','Виктор','Олег',
          'Николаев','Степанова','Макарова','Григорьев','Романов','Смирнов','Ким','Али','Ли']


def key(value):
    return unicodedata.normalize('NFC', value).casefold()


def inspect(sources, output):
    import duckdb
    sources = sources.resolve()
    output.mkdir(parents=True,exist_ok=False)
    manifest = json.loads((ROOT/'normalizer/data/manifest.json').read_text('utf-8'))
    for name, digest in manifest['source_sha256'].items():
        assert sha256((sources/Path(name)).read_bytes()).hexdigest()==digest, ('source hash',name)
    connection=duckdb.connect()
    evidence={t:{'russiannames':{},'russian_names':{},'nen':[]} for t in TOKENS}
    sets={}
    try:
        for role, table in [('FIRST_NAME','names'),('LAST_NAME','surnames'),('PATRONYMIC','midnames')]:
            file=sources/'russiannames/russiannames/data'/(table+'.parquet')
            connection.read_parquet(str(file)).create_view('evidence',replace=True)
            columns=[entry[0] for entry in connection.execute('DESCRIBE evidence').fetchall()]
            sets[role]={key(row[0]) for row in connection.execute('SELECT text FROM evidence').fetchall()}
            for token in TOKENS:
                rows=connection.execute('SELECT * FROM evidence WHERE lower(text)=?',[key(token)]).fetchall()
                evidence[token]['russiannames'][role]=[dict(zip(columns,row)) for row in rows]
            sorokin=sources/'russian_names'/(table+'.jsonl')
            for line in sorokin.read_text('utf-8').splitlines():
                record=json.loads(line)
                for token in TOKENS:
                    if key(record['text'])==key(token):
                        evidence[token]['russian_names'].setdefault(role,[]).append(record)
        for record in json.loads((sources/'nen-imena-dataset/data/names.json').read_text('utf-8')):
            values={key(v) for v in [record['name'],*record.get('short_forms',[]),*record.get('international_forms',[])]}
            for token in TOKENS:
                if key(token) in values:
                    evidence[token]['nen'].append({k:record[k] for k in ('name','url','short_forms','international_forms') if k in record})
    finally:
        connection.close()
    intersections={'+'.join(combo):len(set.intersection(*(sets[r] for r in combo)))
                   for size in (2,3) for combo in itertools.combinations(sets,size)}
    result={'source_manifest':manifest,'intersections':intersections,'tokens':evidence,
            'limitations':'Source membership/frequency is evidence, never a proof of role for an arbitrary individual.'}
    (output/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,default=str)+'\n','utf-8')
    print(json.dumps({'output':str(output),'intersections':intersections},ensure_ascii=True))
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sources',type=Path,default=ROOT/'generated/name-sources')
    parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args()
    inspect(args.sources,args.output_dir)
