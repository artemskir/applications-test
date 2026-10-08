from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
import json
import unicodedata

HEADERS = ['Имя', 'Телефон', 'Дата заявки', 'Источник']
SHEETS = ['Данные', 'Проблемы', 'Оригинал', 'Аудит', 'Проверить']
DIAGNOSTIC = {'PHONE_EXTRA_CONTEXT', 'NAME_LATIN_SCRIPT', 'NAME_CASE_REVIEW', 'NAME_MIXED_SCRIPT'}
MISSING = {'-', '—', 'нет', 'неизвестно', 'не указано', 'n/a', 'null', 'none', 'nan'}


class NormalizationError(Exception):
    def __init__(self, code, message, exit_code=2):
        super().__init__(message)
        self.code, self.exit_code = code, exit_code


def jsonable(value):
    if isinstance(value, (datetime, date, time)):
        return {'type': type(value).__name__, 'value': value.isoformat()}
    if isinstance(value, timedelta):
        return {'type': 'timedelta', 'seconds': value.total_seconds()}
    if isinstance(value, dict):
        return {key: jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(item) for item in value]
    return value


def dumps(value):
    # ASCII JSON preserves illegal XML controls as escapes and counts actual cell length.
    return json.dumps(jsonable(value), ensure_ascii=True, allow_nan=False, separators=(',', ':'))


def digits(value):
    return ''.join(str(unicodedata.decimal(c)) if unicodedata.category(c) == 'Nd' else c for c in value)


@dataclass(slots=True)
class RawCell:
    value: object
    kind: str = 's'
    coordinate: str = ''
    number_format: str = 'General'
    epoch: int = 1900
    metadata: dict = field(default_factory=dict)


@dataclass(slots=True)
class FieldResult:
    raw: RawCell
    canonical: object = None
    display: object = None
    codes: list = field(default_factory=list)
    actions: list = field(default_factory=list)
    status: str = 'UNCHANGED'
    classification: str | None = None
    components: list = field(default_factory=list)

    @property
    def diagnostic_codes(self):
        return [code for code in self.codes if code in DIAGNOSTIC]

    @property
    def error_codes(self):
        return [code for code in self.codes if code not in DIAGNOSTIC]


def failure(cell, *codes):
    status = 'MISSING' if any(c.endswith('_MISSING') for c in codes) else 'UNCHANGED' if all(c in DIAGNOSTIC for c in codes) else 'PROBLEM'
    return FieldResult(cell, display=cell.value, codes=list(codes), status=status)


def success(cell, value, codes=(), actions=()):
    changed = type(value) is not type(cell.value) or value != cell.value
    return FieldResult(cell, canonical=value, display=value, codes=list(codes), actions=list(actions),
                       status='NORMALIZED' if changed else 'UNCHANGED')


def common(cell, field_prefix):
    if cell.metadata.get('parse_issue') == 'CELL_NUMERIC_INVALID':
        return failure(cell, 'CELL_NUMERIC_INVALID')
    if cell.kind == 'f':
        return failure(cell, 'FIELD_FORMULA')
    if cell.kind == 'e':
        return failure(cell, 'FIELD_EXCEL_ERROR')
    if cell.value is None or isinstance(cell.value, str) and (not cell.value.strip() or cell.value.strip().casefold() in MISSING):
        return failure(cell, field_prefix + '_MISSING')
    return None


@dataclass(slots=True)
class RawRow:
    row_id: str
    sheet: str
    number: int
    cells: list


@dataclass(slots=True)
class RowResult:
    raw: RawRow
    fields: list
    disposition: str = 'UNGROUPED'
    representative_id: str = ''
    output_row: int | None = None
    conflicts: list = field(default_factory=list)
    resolved_fields: list | None = None
    resolution: dict | None = None

    @property
    def data_fields(self):
        return self.resolved_fields if self.resolved_fields is not None else self.fields

    @property
    def codes(self):
        return list(dict.fromkeys([code for result in self.fields for code in result.codes] + [item['code'] for item in self.conflicts]))

    @property
    def admitted(self):
        return (self.disposition != 'DUPLICATE' and not any(r.codes for r in self.data_fields)
                and all(r.canonical is not None for r in self.data_fields[:3]))
