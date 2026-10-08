from collections import Counter
from datetime import date
from io import BytesIO
import re
from openpyxl import load_workbook
from .models import HEADERS, SHEETS, NormalizationError
from .report import ORIGINAL_HEADERS, PROBLEM_HEADERS, REVIEW_HEADERS, visible
from .preservation import restore_bytes


def require(condition, message):
    if not condition:
        raise NormalizationError('INVARIANT_FAILED', message, 4)


def validate_rows(rows):
    identities = {row.raw.row_id: row for row in rows}
    require(len(identities) == len(rows), 'Неуникальные исходные row_id.')
    phones = []
    for row in rows:
        require(row.representative_id in identities, 'Нет представителя строки.')
        representative = identities[row.representative_id]
        require(representative.disposition != 'DUPLICATE', 'Представитель оказался дублем.')
        if row.disposition == 'DUPLICATE':
            require(row.output_row is None and representative.raw.number < row.raw.number, 'Нарушен выбор первого дубля.')
        else:
            require(row.representative_id == row.raw.row_id, 'Неверная ссылка представителя.')
        require((row.output_row is not None) == row.admitted, 'Не совпал допуск в Данные.')
        phone = row.fields[1].canonical
        if phone is not None:
            require(isinstance(phone, str) and re.fullmatch(r'\+7[0-9]{10}', phone) is not None, 'Неверный canonical телефона.')
            if row.disposition != 'DUPLICATE':
                phones.append(phone)
        else:
            require(row.disposition == 'UNGROUPED', 'Строка без телефона попала в дубли.')
        normalized_date = row.fields[2].canonical
        if normalized_date is not None:
            require(re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', normalized_date) is not None, 'Неверный формат canonical даты.')
            date.fromisoformat(normalized_date)
    require(len(phones) == len(set(phones)), 'Повторяющиеся canonical телефоны представителей.')


def comparable(value):
    value = visible(value)
    return None if value == '' else value


def verify_report(path, rows, snapshot, counts):
    output_snapshot = path.read_bytes()
    original, run = restore_bytes(output_snapshot)
    require(original == snapshot, 'Не восстановились точные байты входа.')
    require(all(run[key] == value for key, value in counts.items()), 'Не совпали счётчики RUN.')
    workbook = load_workbook(BytesIO(output_snapshot), read_only=True, data_only=False, keep_links=False)
    try:
        require(workbook.sheetnames == SHEETS, 'Неверный список выходных листов.')
        for name in SHEETS:
            workbook[name].reset_dimensions()
        original_rows = workbook['Оригинал'].iter_rows(max_col=len(ORIGINAL_HEADERS), values_only=True)
        require(list(next(original_rows)) == ORIGINAL_HEADERS, 'Неверный заголовок Оригинала.')
        actual_ids = []
        for actual, expected in zip(original_rows, rows, strict=True):
            actual_ids.append(actual[0])
            require(actual[:3] == (expected.raw.row_id, expected.raw.sheet, expected.raw.number), 'Неверная исходная идентичность.')
            require(actual[3:7] == tuple(comparable(c.value) for c in expected.raw.cells), 'Изменены исходные значения в Оригинале.')
        require(actual_ids == [row.raw.row_id for row in rows], 'Нарушена инвентаризация Оригинала.')
        data_rows = workbook['Данные'].iter_rows(max_col=len(HEADERS), values_only=True)
        require(list(next(data_rows)) == HEADERS, 'Неверный заголовок Данных.')
        for actual, expected in zip(data_rows, (row for row in rows if row.admitted), strict=True):
            require(actual == tuple(comparable(r.display) for r in expected.fields), 'Неверное значение в Данных.')
        problem_rows = workbook['Проблемы'].iter_rows(max_col=len(PROBLEM_HEADERS), values_only=True)
        require(list(next(problem_rows)) == PROBLEM_HEADERS, 'Неверный заголовок Проблем.')
        problems = list(problem_rows)
        require([row[0] for row in problems] == [r.raw.row_id for r in rows if r.codes], 'Неполный список проблемных строк.')
        require(all(row[6] == ';'.join(expected.codes) for row, expected in zip(problems, (r for r in rows if r.codes), strict=True)), 'Не совпали коды проблем.')
        review = workbook['Проверить'].iter_rows(max_col=len(REVIEW_HEADERS), values_only=True)
        require(list(next(review)) == REVIEW_HEADERS, 'Неверный заголовок Проверить.')
        for actual, expected in zip(review, (row for row in rows if row.codes), strict=True):
            require(actual[:4] == tuple(comparable(c.value) for c in expected.raw.cells), 'Потеря исходных полей в Проверить.')
            require(actual[4:6] == (expected.raw.sheet, expected.raw.number) and isinstance(actual[6], str) and bool(actual[6]), 'Неверная идентичность или причина в Проверить.')
        records = workbook['Аудит'].iter_rows(max_col=12, values_only=True)
        next(records)
        row_records, changes, links = {}, set(), set()
        for record in records:
            if record[0] == 'ROW':
                require(record[1] not in row_records, 'Повторяющаяся запись ROW.')
                row_records[record[1]] = record
            elif record[0] == 'FIELD_CHANGE':
                changes.add((record[1], record[5]))
            elif record[0] == 'DUPLICATE_LINKED':
                links.add(record[1])
        require(Counter(row_records.keys()) == Counter(actual_ids), 'Не совпала инвентаризация ROW.')
        for row in rows:
            record = row_records[row.raw.row_id]
            require(record[3] == row.output_row and record[4] == row.representative_id, 'Неверная судьба ROW.')
            if row.disposition == 'DUPLICATE':
                require(row.raw.row_id in links, 'Нет связи дубля.')
            for i, result in enumerate(row.fields):
                cell = row.raw.cells[i]
                if type(cell.value) is not type(visible(result.display)) or cell.value != visible(result.display) or cell.kind in ('f', 'e', 'd') or cell.metadata.get('parse_issue'):
                    require((row.raw.row_id, HEADERS[i]) in changes, 'Нет аудита изменения поля.')
    except ValueError as exc:
        raise NormalizationError('INVARIANT_FAILED', 'Не совпали длины или значения выходных строк.', 4) from exc
    finally:
        workbook.close()
