import math
import re
import unicodedata
from .models import common, digits, failure, success

SEPARATORS = r'\s().\-‐‑‒–—−'
CANDIDATES = re.compile(r'[+0-9(][0-9()' + SEPARATORS + r']*')
EXT = re.compile(r'(?i);ext=|(?<!\w)(?:добавочный|extension|доб\.?|вн\.|доп\.|ext\.?)(?!\w)|[#*]|(?<![A-Za-zА-Яа-яЁё])[xх](?=[0-9\s])')
AFTER = r'(?:звонить\s+)?после\s+[0-9]{1,2}:[0-9]{2}'
RANGE = r'с\s+[0-9]{1,2}\s+до\s+[0-9]{1,2}'
COMMENTS = re.compile(r'(?i)\(' + AFTER + r'\)|' + AFTER + r'|\(' + RANGE + r'\)')
UNSAFE = re.compile(r'(?i)(?<!\w)(?:заказ|order|id|инн|огрн|паспорт|счёт|счет)(?![A-Za-zА-Яа-яЁё])')


def shape(candidate):
    candidate = candidate.strip()
    depth, group_digits = 0, 0
    for char in candidate:
        if char == '(':
            if depth:
                return None
            depth, group_digits = 1, 0
        elif char == ')':
            if depth != 1 or not group_digits:
                return None
            depth = 0
        elif char in '0123456789' and depth:
            group_digits += 1
    if depth or '+' in candidate[1:]:
        return None
    token = re.sub('[' + SEPARATORS + ']', '', candidate)
    if re.fullmatch(r'\+7[0-9]{10}', token):
        return token
    if token.startswith(('00', '810')):
        return None
    if re.fullmatch(r'[78][0-9]{10}', token):
        return '+7' + token[1:]
    if re.fullmatch(r'[0-9]{10}', token):
        return '+7' + token
    return None


def scans(text):
    return [m for m in CANDIDATES.finditer(text) if re.search('[0-9]', m[0])]


def has_main(text):
    return any(shape(m[0]) for m in scans(text))


def analyze(cell):
    issue = common(cell, 'PHONE')
    if issue:
        return issue
    value = cell.value
    if isinstance(value, bool):
        return failure(cell, 'PHONE_INVALID')
    if isinstance(value, (int, float)):
        if value < 0 or isinstance(value, float) and (not math.isfinite(value) or not value.is_integer() or value > 2**53 - 1):
            return failure(cell, 'PHONE_INVALID')
        text = str(int(value))
    elif isinstance(value, str):
        text = digits(value).replace('＋', '+')
    else:
        return failure(cell, 'PHONE_INVALID')
    if re.fullmatch(r'[0-9]+(?:\.[0-9]+)?[eE][+-]?[0-9]+', text.strip()):
        return failure(cell, 'PHONE_INVALID')
    if any(unicodedata.category(c).startswith('C') and not c.isspace() for c in text):
        return failure(cell, 'PHONE_INVALID')
    original = text
    context = []
    # Remove only recognized suffix contexts, retaining literal original fragments.
    for match in reversed(list(COMMENTS.finditer(text))):
        if not has_main(text[:match.start()]):
            continue
        numbers = [int(v) for v in re.findall('[0-9]+', match[0])]
        valid = numbers[0] <= 23 and numbers[1] <= (59 if ':' in match[0] else 23)
        if not valid:
            continue
        context.append({'start': match.start(), 'end': match.end(), 'value': str(value)[match.start():match.end()]})
        text = text[:match.start()] + ' ' * len(match[0]) + text[match.end():]
    marker = EXT.search(text)
    if marker and not has_main(text[:marker.start()]):
        return failure(cell, 'PHONE_CONTEXT_UNSAFE')
    if marker:
        tail = text[marker.end():].strip()
        if re.fullmatch(r'[0-9]{1,6}(?:\s*[-‐‑‒–—−,;]\s*[0-9]{1,6})*', tail):
            context.append({'start': marker.start(), 'end': len(text), 'value': str(value)[marker.start():]})
            text = text[:marker.start()] + ' ' * (len(text) - marker.start())
    candidates = scans(text)
    keys, complete = [], []
    invalid, adjacency = False, False
    for match in candidates:
        token = re.sub('[' + SEPARATORS + ']', '', match[0])
        key = shape(match[0])
        if key:
            keys.append(key)
            complete.append(key)
        elif re.fullmatch(r'\+[0-9]{8,15}', token) and not token.startswith('+7'):
            complete.append(token)
            invalid = True
        else:
            invalid = True
        start, end = match.start(), match.end()
        while end > start and text[end - 1].isspace():
            end -= 1
        adjacent = (start > 0 and text[start - 1].isalpha()) or (end < len(text) and text[end].isalpha())
        if adjacent:
            invalid = True
            if len(re.sub('[^0-9]', '', match[0])) >= 10:
                adjacency = True
    if len(set(complete)) > 1:
        return failure(cell, 'PHONE_MULTIPLE')
    if adjacency or UNSAFE.search(text):
        return failure(cell, 'PHONE_CONTEXT_UNSAFE')
    # Foreign prefixes remain foreign even when their suffix contains letters.
    if re.search(r'\+(?!7)[0-9]', text) or any(re.sub('[' + SEPARATORS + ']', '', m[0]).startswith(('00', '810')) for m in candidates):
        return failure(cell, 'PHONE_UNSUPPORTED_PREFIX')
    residue = list(text)
    for match in candidates:
        residue[match.start():match.end()] = ' ' * len(match[0])
    outside = ''.join(residue)
    if '+' in outside or any(c.isnumeric() for c in outside) or invalid or not keys:
        return failure(cell, 'PHONE_INVALID')
    extra = bool(context or outside.strip(' \t\r\n/,;:'))
    actions = [{'kind': 'PHONE_CONTEXT_EXTRACTED', 'details': {'original': value, 'contexts': context, 'remaining_text': outside,
                                                             'candidate_spans': [[m.start(), m.end()] for m in candidates]}}] if extra else []
    return success(cell, keys[0], ['PHONE_EXTRA_CONTEXT'] if extra else [], actions)
