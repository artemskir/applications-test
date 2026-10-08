from datetime import date, datetime, time, timedelta
import math
import re
from openpyxl.styles.numbers import is_date_format, is_timedelta_format
from openpyxl.utils.datetime import CALENDAR_MAC_1904, CALENDAR_WINDOWS_1900, from_excel
from .models import common, digits, failure, success

RU = ['январь января янв', 'февраль февраля фев февр', 'март марта мар', 'апрель апреля апр', 'май мая',
      'июнь июня июн', 'июль июля июл', 'август августа авг', 'сентябрь сентября сен сент',
      'октябрь октября окт', 'ноябрь ноября ноя нояб', 'декабрь декабря дек']
EN = ['january jan', 'february feb', 'march mar', 'april apr', 'may', 'june jun', 'july jul', 'august aug',
      'september sep sept', 'october oct', 'november nov', 'december dec']
MONTHS = {word: i for forms in (RU, EN) for i, names in enumerate(forms, 1) for word in names.split()}
TIME = r'([0-9]{2}):([0-9]{2})(?::([0-9]{2})(?:\.([0-9]+))?)?'
NUMERIC_DATE = r'(?:[0-9]{4}[./-][0-9]{1,2}[./-][0-9]{1,2}|[0-9]{1,2}[./-][0-9]{1,2}[./-][0-9]{4})'


def output(cell, parsed, context=None, order=None):
    actions = [{'kind': 'DATE_TIME_PRESERVED', 'details': context}] if context is not None else []
    if order is not None:
        actions.append({'kind': 'DATE_ORDER_RESOLVED', 'details': order})
    return success(cell, f'{parsed.year:04d}-{parsed.month:02d}-{parsed.day:02d}', actions=actions)


def full_calendar_format(number_format):
    # Literals, spacing/repetition directives and bracket metadata are not date components.
    fmt = re.sub(r'"[^"]*"|\\.|\[[^\]]*\]|[_*].', '', number_format).split(';', 1)[0].lower()
    tokens = re.findall(r'd+|m+|y+|h+|s+', fmt)
    month = any(t.startswith('m') and not (i > 0 and tokens[i-1].startswith('h'))
                and not (i+1 < len(tokens) and tokens[i+1].startswith('s')) for i,t in enumerate(tokens))
    return any(t in ('d', 'dd') for t in tokens) and month and any(t.startswith('y') for t in tokens)


def valid_time(match):
    return int(match[1]) <= 23 and int(match[2]) <= 59 and (match[3] is None or int(match[3]) <= 59)


def analyze(cell):
    issue = common(cell, 'DATE')
    if issue:
        return issue
    value = cell.value
    if isinstance(value, bool):
        return failure(cell, 'DATE_UNSUPPORTED')
    if isinstance(value, (datetime, date)):
        return output(cell, value, {'original': value, 'time': value.isoformat()} if isinstance(value, datetime) else None)
    if isinstance(value, (time, timedelta)):
        return failure(cell, 'DATE_INCOMPLETE')
    if isinstance(value, (int, float)):
        calendar = is_date_format(cell.number_format) and not is_timedelta_format(cell.number_format) and full_calendar_format(cell.number_format)
        if not calendar:
            return failure(cell, 'DATE_INCOMPLETE' if is_date_format(cell.number_format) or is_timedelta_format(cell.number_format) else 'DATE_NUMERIC_AMBIGUOUS')
        if isinstance(value, float) and not math.isfinite(value) or value < 0 or cell.epoch == 1900 and (value < 1 or 60 <= value < 61):
            return failure(cell, 'DATE_INVALID')
        try:
            if cell.epoch == 1904 and value < 1:
                parsed = datetime(1904, 1, 1)
            else:
                parsed = from_excel(math.floor(value), CALENDAR_MAC_1904 if cell.epoch == 1904 else CALENDAR_WINDOWS_1900)
            if not isinstance(parsed, datetime):
                return failure(cell, 'DATE_INCOMPLETE')
        except (ValueError, OverflowError):
            return failure(cell, 'DATE_INVALID')
        return output(cell, parsed, {'serial': value, 'fraction_of_day': value % 1, 'epoch': cell.epoch} if value % 1 else None)
    if not isinstance(value, str):
        return failure(cell, 'DATE_UNSUPPORTED')
    text = digits(value).strip()
    if len(re.findall(NUMERIC_DATE, text)) > 1 or re.fullmatch(r'[0-9]{1,2}[-–—][0-9]{1,2}[./][0-9]{1,2}[./][0-9]{4}', text):
        return failure(cell, 'DATE_MULTIPLE')
    context = None
    iso = re.fullmatch(r'([0-9]{4}-[0-9]{2}-[0-9]{2})T(' + TIME + r')((?:Z|[+-][0-9]{2}:[0-9]{2})?)', text)
    if iso:
        time_match = re.fullmatch(TIME, iso[2])
        zone = iso[7]
        if not valid_time(time_match) or zone not in ('', 'Z') and (int(zone[1:3]) > 23 or int(zone[4:6]) > 59):
            return failure(cell, 'DATE_INVALID')
        try:
            datetime.fromisoformat(text)
        except ValueError:
            return failure(cell, 'DATE_INVALID')
        context, text = {'original': value, 'time_and_offset': text.split('T', 1)[1]}, iso[1]
    else:
        suffix = re.fullmatch(r'(.+?)\s+(' + TIME + r')', text)
        if suffix:
            if not valid_time(re.fullmatch(TIME, suffix[2])):
                return failure(cell, 'DATE_INVALID')
            context, text = {'original': value, 'time': suffix[2]}, suffix[1]
    allow_mdy = False
    order = None
    match = re.fullmatch(r'([0-9]{1,2})\s*([./-])\s*([0-9]{1,2})\s*\2\s*([0-9]{4})', text)
    if match:
        day, _, month, year = match.groups()
        allow_mdy = True
    else:
        match = re.fullmatch(r'([0-9]{4})\s*([./-])\s*([0-9]{1,2})\s*\2\s*([0-9]{1,2})', text)
        if match:
            year, _, month, day = match.groups()
        else:
            match = re.fullmatch(r'([0-9]{1,2})\s+([^\W\d_]+)\.?\s+([0-9]{4})(?:\s+(?:г\.|года))?', text.casefold())
            if match and match[2] in MONTHS:
                day, word, year = match.groups()
                month = MONTHS[word]
            else:
                match = re.fullmatch(r'([^\W\d_]+)\.?\s+([0-9]{1,2}),\s*([0-9]{4})', text.casefold())
                if match and match[1] in MONTHS and match[1] in {w for names in EN for w in names.split()}:
                    word, day, year = match.groups()
                    month = MONTHS[word]
                else:
                    incomplete = (re.fullmatch(r'[0-9]{4}', text) or
                                  re.fullmatch(r'[0-9]{1,2}[./-][0-9]{1,2}[./-][0-9]{1,3}', text) or
                                  re.fullmatch(r'[0-9]{1,2}[./-][0-9]{4}', text) or
                                  re.fullmatch(TIME, text))
                    words = text.casefold().replace('.', '').split()
                    if len(words) == 2 and (words[0] in MONTHS or words[1] in MONTHS) and any(w.isdecimal() for w in words):
                        incomplete = True
                    return failure(cell, 'DATE_INCOMPLETE' if incomplete else 'DATE_NUMERIC_AMBIGUOUS' if text.isdecimal() else 'DATE_UNSUPPORTED')
    try:
        parsed = date(int(year), int(month), int(day))
    except ValueError:
        if not allow_mdy:
            return failure(cell, 'DATE_INVALID')
        try:
            parsed = date(int(year), int(day), int(month))
        except ValueError:
            return failure(cell, 'DATE_INVALID')
        order = {'original': value, 'order': 'MDY', 'reason': 'DMY is not a calendar date; MDY is uniquely valid'}
    return output(cell, parsed, context, order)
