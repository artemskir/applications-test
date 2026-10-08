import base64
from collections import Counter
from datetime import date, datetime, time, timedelta
import hashlib
from pathlib import Path
from openpyxl import Workbook
from openpyxl.cell import WriteOnlyCell
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
from . import SPEC_VERSION, SOFTWARE_VERSION
from .models import HEADERS, SHEETS, DIAGNOSTIC, NormalizationError, dumps

AUDIT_HEADERS = ['record_kind', 'row_id', 'input_cell', 'output_row', 'representative_id', 'field', 'rule_id',
                 'old_value_json', 'new_value_json', 'details_json', 'chunk_index', 'chunk_payload']
ORIGINAL_HEADERS = ['row_id', 'Лист входа', 'Строка входа', *HEADERS, 'Метаданные ячеек JSON']
PROBLEM_HEADERS = ['row_id', 'Лист входа', 'Строка входа', 'Строка в Данных', 'Представитель row_id', 'Статус',
                   'Коды', 'Описание', 'Имя исходное', 'Имя результат', 'Телефон исходный', 'Телефон результат',
                   'Дата исходная', 'Дата результат', 'Источник исходный', 'Источник результат']
REVIEW_HEADERS = [*HEADERS, 'Лист входа', 'Строка входа', 'Что не так']
KINDS = {'RUN', 'ROW', 'FIELD_CHANGE', 'PHONE_CONTEXT_EXTRACTED', 'DATE_TIME_PRESERVED', 'FIELD_ISSUE',
         'DUPLICATE_LINKED', 'DUPLICATE_CONFLICT', 'INPUT_CHUNK', 'CELL_METADATA_CHUNK', 'VALUE_CHUNK',
         'DATE_ORDER_RESOLVED', 'NAME_COMPONENTS_EXTRACTED'}
MESSAGES = {
    'CELL_NUMERIC_INVALID': 'Неконечное числовое значение Excel; исходная запись сохранена',
    'PHONE_MISSING': 'Нет телефона', 'PHONE_INVALID': 'Телефон не соответствует допустимой структуре',
    'PHONE_UNSUPPORTED_PREFIX': 'Неподдерживаемый префикс телефона', 'PHONE_MULTIPLE': 'Несколько разных телефонов',
    'PHONE_CONTEXT_UNSAFE': 'Нельзя однозначно отделить телефон от другого значения',
    'PHONE_EXTRA_CONTEXT': 'Основной номер извлечён; дополнительный контекст сохранён в аудите',
    'DATE_MISSING': 'Нет даты', 'DATE_INVALID': 'Некорректная дата, время или Excel serial',
    'DATE_INCOMPLETE': 'Дата неполная', 'DATE_UNSUPPORTED': 'Неподдерживаемый формат даты',
    'DATE_NUMERIC_AMBIGUOUS': 'Число не подтверждено как Excel-дата', 'DATE_MULTIPLE': 'Несколько дат или интервал',
    'NAME_MISSING': 'Нет имени', 'NAME_INVALID': 'Неподдерживаемая запись имени',
    'NAME_LATIN_SCRIPT': 'Латинские буквы: имя сохранено для проверки', 'NAME_CASE_REVIEW': 'Спорный регистр: имя сохранено',
    'NAME_MIXED_SCRIPT': 'Смешаны латинские и кириллические буквы', 'FIELD_FORMULA': 'Формула сохранена текстом, не вычислялась',
    'NAME_UNKNOWN': 'Не удалось подтвердить личное имя; нужна проверка',
    'NAME_AMBIGUOUS': 'Неоднозначная роль имени или несколько имён; нужна проверка',
    'NAME_NOT_FIRST': 'Указана фамилия или отчество, личного имени нет',
    'NAME_INCOMPLETE': 'Инициалы не определяют полное личное имя',
    'FIELD_EXCEL_ERROR': 'Ошибка Excel сохранена текстом', 'DUPLICATE_NAME_CONFLICT': 'Разные имена у одного телефона',
    'DUPLICATE_DATE_CONFLICT': 'Разные даты у одного телефона',
}


def visible(value):
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, timedelta):
        return str(value)
    if isinstance(value, int) and not isinstance(value, bool) and abs(value) > 2**53 - 1:
        return str(value)
    if isinstance(value, float) and float(format(value, '.16g')) != value:
        return repr(value)
    return value


class Writer:
    def __init__(self):
        self.workbook = Workbook(write_only=True)
        self.sheets = {name: self.workbook.create_sheet(name) for name in SHEETS}
        self.counts = Counter()
        self.value_number = 0
        for name, headers in zip(SHEETS, [HEADERS, PROBLEM_HEADERS, ORIGINAL_HEADERS, AUDIT_HEADERS, REVIEW_HEADERS]):
            self.sheets[name].freeze_panes = 'A2'
            self.put(name, headers)

    def put(self, name, values):
        if self.counts[name] >= 1048576:
            raise NormalizationError('OUTPUT_LIMIT', 'Результат превышает предел строк Excel.', 5)
        cells = []
        for value in values:
            value = visible(value)
            if isinstance(value, str) and (len(value) > 32767 or ILLEGAL_CHARACTERS_RE.search(value)):
                raise NormalizationError('OUTPUT_LIMIT', 'Значение нельзя сохранить в ячейке XLSX без изменения.', 5)
            cell = WriteOnlyCell(self.sheets[name], value=value)
            if value is None:
                # Explicit empty cells retain row width in streaming readers as well.
                cell.number_format = '@'
            if isinstance(value, str):
                cell.data_type = 's'
            cells.append(cell)
        self.sheets[name].append(cells)
        self.counts[name] += 1

    def audit(self, kind, row_id=None, coordinate=None, output_row=None, representative=None, field=None,
              rule=None, old=None, new=None, details=None, index=None, payload=None):
        packed = [self.pack(dumps(value), row_id=row_id) if value is not None else None for value in (old, new, details)]
        self.put('Аудит', [kind, row_id, coordinate, output_row, representative, field, rule, *packed, index, payload])

    def pack(self, text, kind='VALUE_CHUNK', row_id=None):
        if len(text) <= 30000:
            return text
        self.value_number += 1
        ident = f'v{self.value_number}'
        chunks = [text[start:start + 30000] for start in range(0, len(text), 30000)]
        info = {'value_id': ident, 'chunk_count': len(chunks), 'sha256': hashlib.sha256(text.encode('utf-8')).hexdigest()}
        for index, payload in enumerate(chunks):
            self.put('Аудит', [kind, row_id, None, None, None, None, None, None, None, dumps(info), index, payload])
        return dumps({'chunk_ref': ident, **info})

    def close(self):
        # Close generators even on failure, and remove only openpyxl-owned temp XML.
        for sheet in self.sheets.values():
            if not sheet.closed and sheet._writer is not None:
                sheet.close()
            if sheet._writer is not None and Path(sheet._writer.out).exists():
                sheet._writer.cleanup()
        self.workbook.close()


def write_report(path, rows, groups, snapshot, source, selection):
    kept = [row for row in rows if row.admitted]
    problems = [row for row in rows if row.codes]
    codes = Counter(code for row in rows for result in row.fields for code in result.codes)
    codes.update(c['code'] for row in rows for c in row.conflicts)
    counts = {'input_rows': len(rows), 'data_rows': len(kept), 'duplicates': sum(row.disposition == 'DUPLICATE' for row in rows),
              'problem_rows': len(problems), 'phone_groups': len(groups), 'codes': dict(codes)}
    encoded = base64.b64encode(snapshot).decode('ascii')
    chunks = [encoded[i:i + 30000] for i in range(0, len(encoded), 30000)]
    run = {'spec_version': SPEC_VERSION, 'software_version': SOFTWARE_VERSION, 'input_name': source.name,
           'sha256': hashlib.sha256(snapshot).hexdigest(), 'byte_count': len(snapshot), 'chunk_count': len(chunks),
           'encoding': 'base64', **selection, **counts}
    writer = Writer()
    try:
        writer.audit('RUN', details=run)
        for index, chunk in enumerate(chunks):
            writer.audit('INPUT_CHUNK', index=index, payload=chunk)
        for row in rows:
            raw = row.raw
            displays = [result.display for result in row.fields]
            if row.admitted:
                writer.put('Данные', displays)
            meta = {HEADERS[i]: cell.metadata for i, cell in enumerate(raw.cells)}
            metadata_json = writer.pack(dumps(meta), 'CELL_METADATA_CHUNK', raw.row_id)
            writer.put('Оригинал', [raw.row_id, raw.sheet, raw.number, *[cell.value for cell in raw.cells], metadata_json])
            descriptions = [f'{HEADERS[i]}: {MESSAGES[code]}' for i, result in enumerate(row.fields) for code in result.codes]
            descriptions.extend(f"{MESSAGES[item['code']]}; группа {row.representative_id}, детали в DUPLICATE_CONFLICT" for item in row.conflicts)
            if row.codes:
                pairs = [value for i, result in enumerate(row.fields) for value in (raw.cells[i].value, result.display)]
                writer.put('Проблемы', [raw.row_id, raw.sheet, raw.number, row.output_row, row.representative_id, row.disposition,
                                       ';'.join(row.codes), writer.pack('; '.join(descriptions), row_id=raw.row_id), *pairs])
                simple = [f'{HEADERS[i]}: {MESSAGES[code]}' for i, result in enumerate(row.fields) for code in result.codes]
                simple.extend(MESSAGES[item['code']] for item in row.conflicts)
                writer.put('Проверить', [*[cell.value for cell in raw.cells], raw.sheet, raw.number, '; '.join(simple)])
            writer.audit('ROW', raw.row_id, output_row=row.output_row, representative=row.representative_id,
                         details={'disposition': row.disposition, 'canonical_phone': row.fields[1].canonical, 'codes': row.codes})
            for index, result in enumerate(row.fields):
                cell = raw.cells[index]
                if type(cell.value) is not type(visible(result.display)) or cell.value != visible(result.display) or cell.kind in ('f', 'e', 'd') or cell.metadata.get('parse_issue'):
                    writer.audit('FIELD_CHANGE', raw.row_id, cell.coordinate, row.output_row, row.representative_id, HEADERS[index],
                                 'SAFE_LITERAL' if cell.kind in ('f', 'e', 'd') or cell.metadata.get('parse_issue') else 'NORMALIZE_' + ['NAME', 'PHONE', 'DATE', 'SOURCE'][index],
                                 old={'type': cell.kind, 'value': cell.value}, new={'type': type(visible(result.display)).__name__, 'value': visible(result.display)})
                for code in result.codes:
                    writer.audit('FIELD_ISSUE', raw.row_id, cell.coordinate, row.output_row, row.representative_id, HEADERS[index],
                                 code, details={'severity': 'diagnostic' if code in DIAGNOSTIC else 'error', 'message': MESSAGES[code]})
                for action in result.actions:
                    writer.audit(action['kind'], raw.row_id, cell.coordinate, row.output_row, row.representative_id, HEADERS[index], details=action['details'])
            for item in row.conflicts:
                writer.audit('FIELD_ISSUE', raw.row_id, raw.cells[item['field']].coordinate, row.output_row, row.representative_id,
                             HEADERS[item['field']], item['code'], details={'severity': 'error', 'group': row.representative_id})
            if row.disposition == 'DUPLICATE':
                writer.audit('DUPLICATE_LINKED', raw.row_id, output_row=None, representative=row.representative_id,
                             details={'source': raw.cells[3].value,
                                      'representative_source': groups[row.fields[1].canonical][0].raw.cells[3].value,
                                      'canonical_phone': row.fields[1].canonical})
        for group in groups.values():
            if len(group) < 2:
                continue
            first = group[0]
            for conflict in first.conflicts:
                writer.audit('DUPLICATE_CONFLICT', first.raw.row_id, representative=first.raw.row_id,
                             field=HEADERS[conflict['field']], rule=conflict['code'], details=conflict)
        writer.workbook.save(path)
    finally:
        writer.close()
    return counts
