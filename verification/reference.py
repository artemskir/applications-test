"""Specification oracle. No production imports or production-derived expectations.

The phone/date languages here are deliberately smaller than the application grammar.
REVIEW means outside this oracle's scope, not that a real person's data is invalid.
"""
from dataclasses import dataclass
from itertools import product, permutations
import re


@dataclass(frozen=True)
class Decision:
    value: str | None
    status: str


def phone(value):
    if value is None or value == '':
        return Decision(None, 'MISSING')
    if not isinstance(value, str):
        return Decision(None, 'REVIEW')
    text = value.strip()
    if any(c not in '0123456789+ ()-.' for c in text):
        return Decision(None, 'REVIEW')
    token = ''.join(c for c in text if c not in ' ()-.')
    if token.startswith(('00', '810')):
        return Decision(None, 'UNSUPPORTED_PREFIX')
    if token.startswith('+'):
        if not token.startswith('+7'):
            return Decision(None, 'UNSUPPORTED_PREFIX')
        return Decision(token, 'NORMALIZED') if len(token) == 12 and token[1:].isdigit() else Decision(None, 'INVALID')
    if not token.isdigit():
        return Decision(None, 'INVALID')
    if len(token) == 10:
        return Decision('+7' + token, 'NORMALIZED')
    if len(token) == 11 and token[0] in '78':
        return Decision('+7' + token[1:], 'NORMALIZED')
    return Decision(None, 'INVALID')


def calendar_valid(year: int, month: int, day: int) -> bool:
    if not 1 <= year <= 9999 or not 1 <= month <= 12:
        return False
    leap = year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
    lengths = (31, 29 if leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
    return 1 <= day <= lengths[month - 1]


def calendar(value):
    if value is None or value == '':
        return Decision(None, 'MISSING')
    if not isinstance(value, str):
        return Decision(None, 'REVIEW')
    match = re.fullmatch(r'\s*([0-9]+)\s*([./-]|\s+)\s*([0-9]+)\s*\2\s*([0-9]+)\s*', value)
    if not match:
        return Decision(None, 'REVIEW')
    left, middle, right = match[1], match[3], match[4]
    if len(left) == 4 and len(middle) in (1, 2) and len(right) in (1, 2):
        candidate = (int(left), int(middle), int(right))
    elif len(right) == 4 and len(left) in (1, 2) and len(middle) in (1, 2):
        candidate = (int(right), int(middle), int(left))
        if not calendar_valid(*candidate):
            candidate = (int(right), int(left), int(middle))
    else:
        return Decision(None, 'REVIEW')
    if not calendar_valid(*candidate):
        return Decision(None, 'INVALID')
    y, m, d = candidate
    return Decision(f'{y:04d}-{m:02d}-{d:02d}', 'NORMALIZED')


def role_assignments(evidence):
    """All assignments, without first-match dictionary priority."""
    if not evidence or len(evidence) > 3 or any(not roles for roles in evidence):
        return ()
    if len(evidence) == 1:
        return tuple((r,) for r in sorted(evidence[0]))
    allowed = set(permutations(('FIRST_NAME', 'LAST_NAME', 'PATRONYMIC'), len(evidence)))
    return tuple(c for c in product(*(sorted(r) for r in evidence)) if c in allowed and 'FIRST_NAME' in c)


# Explicit finite alphabet from the verification plan; not sampled from production.
PHONES = ('+79174005219', '8 (917) 400-52-19', '+79174005220', None)
NAMES = ('Кирилл', 'Дарья', None)
DATES = ('2026-09-06', 'broken_date')
CONFIRMED_DATES = ('2026-09-06', '2026-09-07')
SOURCES = ('сайт', 'звонок')


@dataclass(frozen=True)
class Record:
    name: str | None
    telephone: str | None
    date: str
    source: str


ALPHABET = tuple(Record(n, p, d, s) for p, n, d, s in product(PHONES, NAMES, DATES, SOURCES))


@dataclass(frozen=True)
class Outcome:
    representative: int
    disposition: str
    codes: frozenset
    output_row: int | None
    selected_values: tuple | None = None
    donors: tuple | None = None


def evaluate(records):
    """Relational definition: representative is min index of equal nonempty keys."""
    keys = [phone(r.telephone).value for r in records]
    answer = []
    admitted_count = 0
    for i, r in enumerate(records):
        group = [j for j, k in enumerate(keys) if keys[i] is not None and k == keys[i]] or [i]
        representative = min(group)
        disposition = 'UNGROUPED' if keys[i] is None else 'REPRESENTATIVE' if i == representative else 'DUPLICATE'
        codes = set()
        if r.name is None:
            codes.add('NAME_MISSING')
        if keys[i] is None:
            codes.add('PHONE_MISSING')
        if r.date not in CONFIRMED_DATES:
            codes.add('DATE_UNSUPPORTED')
        if len({records[j].name for j in group if records[j].name is not None}) > 1:
            codes.add('DUPLICATE_NAME_CONFLICT')
        if len({records[j].date for j in group if records[j].date in CONFIRMED_DATES}) > 1:
            codes.add('DUPLICATE_DATE_CONFLICT')
        name_donor = next((j for j in group if records[j].name is not None), None)
        date_donor = next((j for j in group if records[j].date in CONFIRMED_DATES), None)
        admitted = (disposition == 'REPRESENTATIVE' and name_donor is not None and date_donor is not None)
        output = 2 + admitted_count if admitted else None
        admitted_count += admitted
        values = donors = None
        if disposition == 'REPRESENTATIVE':
            values = (records[name_donor].name if name_donor is not None else r.name, keys[i],
                      records[date_donor].date if date_donor is not None else r.date, r.source)
            donors = (name_donor, representative, date_donor, representative)
        answer.append(Outcome(representative, disposition, frozenset(codes), output, values, donors))
    return tuple(answer)
