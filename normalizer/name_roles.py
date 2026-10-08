"""Offline role evidence; a miss means review, never proof of an invalid person."""
from functools import lru_cache
import gzip
import hashlib
import itertools
import json
from pathlib import Path
import unicodedata

FIRST_NAME = 'FIRST_NAME'
LAST_NAME = 'LAST_NAME'
PATRONYMIC = 'PATRONYMIC'
REVIEWED_FIRST = set('Андрей Александр Любовь Роман Влад Иван Мария Ирина Егор Анастасия Кирилл Анна Пётр Семён Елена Ольга Дмитрий Сергей Алексей Наталья Михаил Павел Игорь Юлия Николай Владимир Екатерина Татьяна Анна-Мария Жан-Поль Саша'.casefold().split())
REVIEWED_LAST = set('Волков Волкова Зайцев Зайцева Павлов Павлова Иванов Иванова Петров Петрова Белоусов Белоусова Ёлкин Ёлкина'.casefold().split())
REVIEWED_MIDDLE = set('Андреевич Андреевна Львович Львовна Иванович Ивановна Петровна Сергеевич Сергеевна'.casefold().split())
AMBIGUOUS_WORDS = set('Ким Али Ли Нгуен Петрович'.casefold().split())


def key(text):
    return unicodedata.normalize('NFC', text).casefold()


@lru_cache(maxsize=1)
def lexicon():
    folder = Path(__file__).parent / 'data'
    payload = (folder / 'name_lexicon.json.gz').read_bytes()
    manifest = json.loads((folder / 'manifest.json').read_text(encoding='utf-8'))
    if hashlib.sha256(payload).hexdigest() != manifest['bundle_sha256']:
        raise ValueError('Name reference hash mismatch')
    result = {k: set(v) for k, v in json.loads(gzip.decompress(payload)).items()}
    if {k: len(v) for k,v in result.items()} != manifest['counts']:
        raise ValueError('Name reference count mismatch')
    return result


def roles(token):
    normalized = key(token)
    if normalized in AMBIGUOUS_WORDS:
        return set(), True
    for reviewed, role in ((REVIEWED_FIRST,FIRST_NAME), (REVIEWED_LAST,LAST_NAME), (REVIEWED_MIDDLE,PATRONYMIC)):
        if normalized in reviewed:
            return {role}, False
    reference = lexicon()
    result = {role for role in (FIRST_NAME,LAST_NAME,PATRONYMIC) if normalized in reference[role]}
    if FIRST_NAME in result and normalized not in reference['NEN_FIRST_NAME']:
        # A lone unsupported first-name membership is not a surname inference.
        if len(result) > 1:
            return set(), True
        return set(), False
    return result, len(result) > 1


def classify(text):
    tokens = text.split()
    if len(tokens) > 3 or not tokens:
        return 'UNKNOWN', []
    evidence = [roles(token) for token in tokens]
    if any(uncertain for _,uncertain in evidence):
        return 'AMBIGUOUS', []
    if any(not role_set for role_set,_ in evidence):
        return 'UNKNOWN', []
    if len(tokens) == 1:
        return next(iter(evidence[0][0])), [{'text':tokens[0],'role':next(iter(evidence[0][0]))}]
    assignments = [combo for combo in itertools.product(*(entry[0] for entry in evidence))
                   if combo.count(FIRST_NAME) == 1 and len(set(combo)) == len(combo)]
    if len(assignments) != 1:
        return 'AMBIGUOUS', []
    return 'FULL_NAME', [{'text':token,'role':role} for token,role in zip(tokens,assignments[0])]
