"""Declarative acceptance examples. No production normalization logic here."""
from datetime import datetime

HEADERS = ["Имя", "Телефон", "Дата заявки", "Источник"]


def typed(kind, value, number_format=None):
    result = {"type": kind, "value": value}
    if number_format:
        result["number_format"] = number_format
    return result


def case(case_id, field, value, expected, codes=(), note="", origin="synthetic"):
    return {"id": case_id, "field": field, "input": value,
            "expected": expected, "codes": list(codes), "note": note,
            "origin": origin}


CASES = []


def add(prefix, field, examples):
    for index, example in enumerate(examples, 1):
        CASES.append(case(f"{prefix}{index:02}", field, *example))


add("P", "Телефон", [
    ("+79174005219", "+79174005219"),
    ("8 917 400 52 19", "+79174005219"),
    ("тел.: 8 917 400 52 19 (после 18:00)", "+79174005219", (), "Время не входит в номер", "user"),
    ("8 (800) 707-46-19", "+78007074619", (), "Принимаем 800", "user"),
    ("79174005219", "+79174005219"),
    ("9174005219", "+79174005219"),
    ("+7 (917) 400-52-19", "+79174005219"),
    ("8\u00a0917\u202f400\t52\n19", "+79174005219"),
    ("8–917–400–52–19", "+79174005219"),
    ("8.917.400.52.19", "+79174005219"),
    ("tel:+79174005219", "+79174005219"),
    ("8 (917) 400-52-19 доб. 123", "+79174005219", (), "Добавочный сохраняется в оригинале и аудите"),
    ("+79174005219; +7 (917) 400-52-19", "+79174005219", (), "Один уникальный номер"),
    ("+79174005219 / +79174005220", "+79174005219 / +79174005220", ("PHONE_MULTIPLE",)),
    (None, None, ("PHONE_MISSING",)),
    ("  ", "  ", ("PHONE_MISSING",)),
    ("нет", "нет", ("PHONE_MISSING",)),
    ("8 917 4OO 52 19", "8 917 4OO 52 19", ("PHONE_INVALID",), "O не заменяется на 0"),
    ("+7 917 400 5l 19", "+7 917 400 5l 19", ("PHONE_INVALID",)),
    ("917400521", "917400521", ("PHONE_INVALID",)),
    ("891740052199", "891740052199", ("PHONE_INVALID",), "Не брать подстроку длинной последовательности"),
    ("+380671234567", "+380671234567", ("PHONE_UNSUPPORTED_PREFIX",)),
    ("+89174005219", "+89174005219", ("PHONE_UNSUPPORTED_PREFIX",)),
    ("0079174005219", "0079174005219", ("PHONE_UNSUPPORTED_PREFIX",)),
    (typed("number", 89174005219), "+79174005219"),
    (typed("number", 89174005219.5), typed("number", 89174005219.5), ("PHONE_INVALID",)),
    (typed("boolean", True), typed("boolean", True), ("PHONE_INVALID",)),
    ("8.9174005219E10", "8.9174005219E10", ("PHONE_INVALID",)),
    ("＋７９１７４００５２１９", "+79174005219", (), "Полноширинный плюс и Unicode Nd"),
    ("+٧٩١٧٤٠٠٥٢١٩", "+79174005219"),
    ("+7⑨174005219", "+7⑨174005219", ("PHONE_INVALID",), "Только Unicode Nd; не все isdigit"),
    ("8 (917) 400-52-19 (с 9 до 18)", "+79174005219"),
    ("заказ 89174005219", "заказ 89174005219", ("PHONE_CONTEXT_UNSAFE",), "Явный чужой идентификатор"),
    ("8 (917 400-52-19", "8 (917 400-52-19", ("PHONE_INVALID",), "Несбалансированные скобки"),
    ("89174005219 123", "89174005219 123", ("PHONE_INVALID",), "Нет маркера добавочного"),
    ("+1 412 535 abcd", "+1 412 535 abcd", ("PHONE_UNSUPPORTED_PREFIX",), "Не применять vanity parsing", "google-faq"),
    ("+7 917 400 c5219", "+7 917 400 c5219", ("PHONE_INVALID",), "Адаптация кейса с лишней буквой", "google-faq-adapted"),
    (typed("formula", '=CONCAT("+7","9174005219")'), typed("formula", '=CONCAT("+7","9174005219")'), ("FIELD_FORMULA",)),
    (typed("error", "#VALUE!"), typed("error", "#VALUE!"), ("FIELD_EXCEL_ERROR",)),
    ("+70000000000", "+70000000000", (), "Структура корректна; существование не подтверждается"),
    ("+7 917 400 52 19; запасной +380671234567", "+7 917 400 52 19; запасной +380671234567", ("PHONE_MULTIPLE",)),
    ("номер: +7 917 400 52 19", "+79174005219"),
    ("8/917/400/52/19", "8/917/400/52/19", ("PHONE_INVALID",), "Slash разделяет кандидаты"),
    ("abc89174005219xyz", "abc89174005219xyz", ("PHONE_CONTEXT_UNSAFE",)),
    ("8\u200b9174005219", "8\u200b9174005219", ("PHONE_INVALID",), "Не стирать невидимые символы внутри"),
    ("89174005219, звонить после 18:00", "+79174005219"),
    (typed("number", 8.9174005219e10, "0.00E+00"), "+79174005219", (), "Число хранится точно, отображение научное"),
    ("доб. 123; +79174005219", "доб. 123; +79174005219", ("PHONE_CONTEXT_UNSAFE",), "Добавочный только после основного"),
])

add("D", "Дата заявки", [
    ("09/03/2026", "2026-03-09", (), "Всегда DMY", "user"),
    ("09.03.2026", "2026-03-09"),
    ("03.09.2026", "2026-09-03"),
    ("09/05/2026", "2026-05-09", (), "Не ориентироваться на легенду про сентябрь", "user"),
    ("2026-09-06", "2026-09-06"),
    ("9/3/2026", "2026-03-09"),
    ("9-3-2026", "2026-03-09"),
    ("2026/09/06", "2026-09-06"),
    ("2026.09.06", "2026-09-06"),
    (" 09 . 03 . 2026 ", "2026-03-09"),
    ("6 сентября 2026", "2026-09-06", (), "Русские месяцы", "user"),
    ("6 СЕНТЯБРЯ 2026 г.", "2026-09-06"),
    ("6 сен. 2026", "2026-09-06"),
    ("6 September 2026", "2026-09-06"),
    ("September 6, 2026", "2026-09-06"),
    ("2026-09-06T23:15:45+03:00", "2026-09-06", (), "Локальная календарная дата без конвертации зоны"),
    ("06.09.2026 18:00", "2026-09-06"),
    (typed("datetime", "2026-09-06T18:00:00", "dd/mm/yyyy hh:mm"), "2026-09-06"),
    (typed("serial", 46271, "yyyy-mm-dd"), "2026-09-06", (), "Windows epoch 1900"),
    (typed("number", 46271), typed("number", 46271), ("DATE_NUMERIC_AMBIGUOUS",)),
    ("46271", "46271", ("DATE_NUMERIC_AMBIGUOUS",)),
    ("29.02.2024", "2024-02-29"),
    ("29.02.2026", "29.02.2026", ("DATE_INVALID",)),
    ("31.04.2026", "31.04.2026", ("DATE_INVALID",)),
    ("00.09.2026", "00.09.2026", ("DATE_INVALID",)),
    ("13/31/2026", "13/31/2026", ("DATE_INVALID",)),
    ("09/03/26", "09/03/26", ("DATE_INCOMPLETE",)),
    ("6 сентября", "6 сентября", ("DATE_INCOMPLETE",)),
    ("сентябрь 2026", "сентябрь 2026", ("DATE_INCOMPLETE",)),
    ("сегодня", "сегодня", ("DATE_UNSUPPORTED",)),
    ("2026-09-01 — 2026-09-03", "2026-09-01 — 2026-09-03", ("DATE_MULTIPLE",)),
    ("O9.O3.2026", "O9.O3.2026", ("DATE_UNSUPPORTED",)),
    (None, None, ("DATE_MISSING",)),
    ("неизвестно", "неизвестно", ("DATE_MISSING",)),
    (typed("boolean", False), typed("boolean", False), ("DATE_UNSUPPORTED",)),
    ("09.03/2026", "09.03/2026", ("DATE_UNSUPPORTED",)),
    ("2026-09-06T25:00:00", "2026-09-06T25:00:00", ("DATE_INVALID",)),
    (typed("serial", 60, "yyyy-mm-dd"), typed("serial", 60, "yyyy-mm-dd"), ("DATE_INVALID",), "Excel 1900-02-29 не существует"),
    (typed("number", 0.75, "hh:mm"), typed("number", 0.75, "hh:mm"), ("DATE_INCOMPLETE",)),
    ("0001-01-01", "0001-01-01", (), "В итоговом XLSX это текст"),
    ("9999-12-31", "9999-12-31"),
    ("0000-01-01", "0000-01-01", ("DATE_INVALID",)),
    ("20260906", "20260906", ("DATE_NUMERIC_AMBIGUOUS",)),
    ("2026-09-06 комментарий", "2026-09-06 комментарий", ("DATE_UNSUPPORTED",)),
    (typed("formula", '=DATE(2026,9,6)'), typed("formula", '=DATE(2026,9,6)'), ("FIELD_FORMULA",)),
    (typed("error", "#N/A"), typed("error", "#N/A"), ("FIELD_EXCEL_ERROR",)),
    ("23/12/2019", "2019-12-23", (), "Адаптировано из официального примера", "openrefine"),
    ("09/03/2026 18:00:30.123", "2026-03-09"),
    ("2006", "2006", ("DATE_INCOMPLETE",), "Публичный грязный CSV: строка 2450 содержит только год", "goodreads-dirty"),
    ("2026-09-06T23:15:45Z", "2026-09-06"),
    ("2026-09-06T23:15:45+25:00", "2026-09-06T23:15:45+25:00", ("DATE_INVALID",)),
])

add("N", "Имя", [
    ("андрей волков", "Андрей Волков", (), "user example", "user"),
    ("ПАВЛОВА анастасия", "Павлова Анастасия", (), "user example", "user"),
    (" Павлов  Андрей ", "Павлов Андрей", (), "user example", "user"),
    ("анна-мария", "Анна-Мария"),
    ("o'connor", "O'Connor"),
    ("сёмен ёлкин", "Сёмен Ёлкин", (), "Не исправлять орфографию и ё"),
    ("  егор\u00a0\u00a0волков\n", "Егор Волков"),
    ("и. и. иванов", "И. И. Иванов"),
    ("лИ ан", "Ли Ан"),
    (None, None, ("NAME_MISSING",)),
    ("   ", "   ", ("NAME_MISSING",)),
    ("N/A", "N/A", ("NAME_MISSING",)),
    ("иван123", "иван123", ("NAME_INVALID",)),
    (typed("number", 123), typed("number", 123), ("NAME_INVALID",)),
    (typed("boolean", True), typed("boolean", True), ("NAME_INVALID",)),
    ("123", "123", ("NAME_INVALID",)),
    ("Ивaн", "Ивaн", ("NAME_MIXED_SCRIPT",), "Латинская a внутри кириллицы"),
    ("Иван Smith", "Иван Smith", ("NAME_MIXED_SCRIPT",)),
    ("Иван (менеджер)", "Иван (менеджер)", ("NAME_INVALID",)),
    ("Иван\u200bов", "Иван\u200bов", ("NAME_INVALID",)),
    ("=?", "=?", ("NAME_INVALID",)),
    ("Jean-Luc", "Jean-Luc"),
    ("élodie dupont", "Élodie Dupont"),
    ("Пётр", "Пётр", (), "Имя без фамилии допустимо"),
    (typed("formula", '="Иван"'), typed("formula", '="Иван"'), ("FIELD_FORMULA",)),
    (typed("error", "#REF!"), typed("error", "#REF!"), ("FIELD_EXCEL_ERROR",)),
    ("иван—петров", "Иван—Петров", (), "Unicode дефис сохраняется"),
    ("Иван1 Иванов", "Иван1 Иванов", ("NAME_INVALID",)),
])

add("S", "Источник", [
    ("сайт", "сайт"),
    (" Telegram ", " Telegram ", (), "Источник сохраняется буквально"),
    ("партнёр / CRM", "партнёр / CRM"),
    (None, None, (), "Не обязательное поле"),
    (typed("number", 42), typed("number", 42)),
    ('=HYPERLINK("https://example.invalid","сайт")', '=HYPERLINK("https://example.invalid","сайт")', (), "Строка, не формула"),
    (typed("formula", '=1+1'), typed("formula", '=1+1'), ("FIELD_FORMULA",)),
    (typed("error", "#VALUE!"), typed("error", "#VALUE!"), ("FIELD_EXCEL_ERROR",)),
])

# Spec 1.1: confirmed user decisions after Deep Research. Original input stays intact.
for entry in CASES:
    if entry["id"] in {"P03", "P11", "P12", "P32", "P42", "P46"}:
        entry["codes"] = ["PHONE_EXTRA_CONTEXT"]
        entry["note"] += "; основной номер извлекается, дополнительный контекст в аудите и проблемах"
    if entry["id"] in {"N05", "N22", "N23"}:
        entry["expected"] = entry["input"]
        entry["codes"] = ["NAME_LATIN_SCRIPT"]
        entry["note"] += "; латинские буквы: сохранить и проверить вручную"
    if entry["id"] in {"N17", "N18"}:
        entry["codes"].append("NAME_LATIN_SCRIPT")
    if entry["id"] == "N09":
        entry["expected"] = entry["input"]
        entry["codes"] = ["NAME_CASE_REVIEW"]

CASES.extend([
    case("P49", "Телефон", "+7 (495) 587-88-89, доб. 10-17, 10-13", "+74955878889", ["PHONE_EXTRA_CONTEXT"], "Не обрезать добавочный до 10", "deep-research"),
    case("P50", "Телефон", "+7 495 123-45-67 x123", "+74951234567", ["PHONE_EXTRA_CONTEXT"], "x-маркер только вне основного номера", "deep-research"),
    case("P51", "Телефон", "+7 915 145-17-80 после 18:00, доб. 42", "+79151451780", ["PHONE_EXTRA_CONTEXT"], "Весь хвост сохраняется", "deep-research"),
    case("P52", "Телефон", "+77710009998", "+77710009998", (), "KZ из локальных metadata; регион не gate", "deep-research-specialization"),
    case("P53", "Телефон", "+7 915 145-17-80 / 123", "+7 915 145-17-80 / 123", ["PHONE_INVALID"], "Второй повреждённый фрагмент не игнорируется", "deep-research"),
    case("D52", "Дата заявки", "2026-13-10", "2026-13-10", ["DATE_INVALID"], "Strict dateparser меняет порядок; whitelist запрещает", "deep-research"),
    case("D53", "Дата заявки", "1780000000", "1780000000", ["DATE_NUMERIC_AMBIGUOUS"], "Не угадывать timestamp", "deep-research"),
    case("D54", "Дата заявки", "09/2026", "09/2026", ["DATE_INCOMPLETE"], "Нет дня", "deep-research"),
    case("D55", "Дата заявки", "03.09.2026 / 04.09.2026", "03.09.2026 / 04.09.2026", ["DATE_MULTIPLE"], "Две даты", "deep-research"),
    case("D56", "Дата заявки", "31.09.2026", "31.09.2026", ["DATE_INVALID"], "В сентябре нет 31 дня", "deep-research"),
    case("D57", "Дата заявки", "03-05.09.2026", "03-05.09.2026", ["DATE_MULTIPLE"], "Интервал, не 3 мая", "deep-research"),
    case("D58", "Дата заявки", "03.09.2026 г.", "03.09.2026 г.", ["DATE_UNSUPPORTED"], "Новый suffix для числовой даты не добавлен автоматически", "deep-research"),
    case("N29", "Имя", "McDONALD John", "McDONALD John", ["NAME_LATIN_SCRIPT"], "Сохранить спорный регистр", "deep-research"),
    case("N30", "Имя", "de Gaulle", "de Gaulle", ["NAME_LATIN_SCRIPT"], "Не поднимать регистр частицы", "deep-research"),
    case("N31", "Имя", "е\u0308лкина анна", "Ёлкина Анна", (), "NFC перед регистром", "deep-research"),
    case("N32", "Имя", "И.И. ИВАНОВ", "И.И. Иванов", (), "Инициалы сохраняются", "deep-research"),
    case("N33", "Имя", "Иван\u200bИванов", "Иван\u200bИванов", ["NAME_INVALID"], "ZWSP не стирать", "deep-research"),
    case("N34", "Имя", "Иван / Мария", "Иван / Мария", ["NAME_INVALID"], "Не разделять людей", "deep-research"),
])

# Spec 1.2: approved clarifications from the additional gap research.
CASES.extend([
    case("P54", "Телефон", "8 (495) 123-45-67 вн. 123", "+74951234567", ["PHONE_EXTRA_CONTEXT"], "Весь добавочный в аудит и проблемы", "gap-research"),
    case("P55", "Телефон", "8 (495) 123-45-67 доп. 123", "+74951234567", ["PHONE_EXTRA_CONTEXT"], "Не интерпретировать добавочный", "gap-research"),
    case("P56", "Телефон", "8 (495) 123-45-67*1001", "+74951234567", ["PHONE_EXTRA_CONTEXT"], "Явный маркер после полного номера", "gap-research"),
    case("P57", "Телефон", "+74951234567;ext=123", "+74951234567", ["PHONE_EXTRA_CONTEXT"], "Хвост сохраняется буквально", "gap-research"),
    case("P58", "Телефон", "+ 7 (495) 123-45-67", "+74951234567", (), "Пробел после плюса — форматирование", "gap-research"),
    case("P59", "Телефон", "０９１７４００５２１９", "０９１７４００５２１９", ["PHONE_INVALID"], "11 цифр с 0, а не 10 цифр; не обрезать", "gap-research-correction"),
    case("P60", "Телефон", "8 (917) 40О-52-19", "8 (917) 40О-52-19", ["PHONE_INVALID"], "Кириллическую О внутри кандидата не удалять", "gap-research"),
    case("P61", "Телефон", "+7\u202e9174005219\u202c", "+7\u202e9174005219\u202c", ["PHONE_INVALID"], "Bidi control не стирать", "additional-research"),
    case("D59", "Дата заявки", "2026-09-06T18:00", "2026-09-06", (), "Время сохранить в аудите", "gap-research"),
    case("D60", "Дата заявки", "2026-09-06T18:00+03:00", "2026-09-06", (), "Локальная дата, offset в аудите", "gap-research"),
    case("D61", "Дата заявки", "2026-09-06T23:30:00-12:00", "2026-09-06", (), "В UTC уже 7 сентября; преобразование не нужно", "gap-research-correction"),
    case("D62", "Дата заявки", "2026-09-06T24:00", "2026-09-06T24:00", ["DATE_INVALID"], "Проверять время до извлечения даты", "gap-research"),
    case("D63", "Дата заявки", "2026-10-01", "2026-10-01", (), "Сентябрь в легенде не фильтр", "additional-research"),
    case("N35", "Имя", "анна - мария", "анна - мария", ["NAME_INVALID"], "Отдельный дефис — ошибка; правило подтверждено заказчиком", "gap-research"),
    case("P62", "Телефон", "0000000000", "0000000000", ["PHONE_UNSUPPORTED_PREFIX"], "00 запрещён даже при 10 цифрах; подтверждено заказчиком", "user-clarification"),
    case("P63", "Телефон", "81012345678", "81012345678", ["PHONE_UNSUPPORTED_PREFIX"], "810 запрещён даже при 11 цифрах с 8; подтверждено заказчиком", "user-clarification"),
])

# Spec 1.4: DEC-25 changes name semantics; old IDs retained, old snapshots preserved.
name_changes = {
    'N01': ('Андрей', []), 'N02': ('Анастасия', []), 'N03': ('Андрей', []),
    'N06': ('сёмен ёлкин', ['NAME_UNKNOWN']), 'N07': ('Егор', []),
    'N08': ('и. и. иванов', ['NAME_INCOMPLETE']),
    'N27': ('иван—петров', ['NAME_UNKNOWN']), 'N31': ('Анна', []),
    'N32': ('И.И. ИВАНОВ', ['NAME_INCOMPLETE']),
}
for entry in CASES:
    if entry['id'] in name_changes:
        entry['expected'], entry['codes'] = name_changes[entry['id']]
        entry['note'] += '; DEC-25, личное имя; полный исходник сохраняется'
CASES.extend([
    case('D64','Дата заявки',typed('serial',46271,'mm'),typed('serial',46271,'mm'),['DATE_INCOMPLETE'],'Нет дня/года в формате','user-review'),
    case('D65','Дата заявки',typed('serial',46271,'yyyy'),typed('serial',46271,'yyyy'),['DATE_INCOMPLETE'],'Нет дня/месяца в формате','user-review'),
    case('D66','Дата заявки','09/25/2026','2026-09-25',(), 'Однозначный запасной MDY, DEC-23','user-review'),
    case('D67','Дата заявки','хх.09.2026','хх.09.2026',['DATE_UNSUPPORTED'],'Буквы не угадывать','user-review'),
    case('P64','Телефон','не знаю','не знаю',['PHONE_INVALID'],'Текст не является телефоном','user-review'),
    case('N36','Имя','Влад','Влад',(), 'Подтверждённое личное имя','user-review'),
    case('N37','Имя','Зайцев Кирилл','Кирилл',(), 'Имя не зависит от позиции','user-review'),
    case('N38','Имя','Кирилл Зайцев','Кирилл',(), 'ФИО сохраняется в оригинале','user-review'),
    case('N39','Имя','К. Белоусов','К. Белоусов',['NAME_INCOMPLETE'],'Не раскрывать инициал','user-review'),
    case('N40','Имя','Ким','Ким',['NAME_AMBIGUOUS'],'Имя или фамилия','user-review'),
    case('N41','Имя','Волков','Волков',['NAME_NOT_FIRST'],'Фамилия без личного имени','user-review'),
    case('N42','Имя','не знаю','не знаю',['NAME_UNKNOWN'],'Нет подтверждения личного имени','user-review'),
])

# Resource QA 1.5: independent expectations are shared by the small regressions and XLSX generator.
from fixtures.resource_cases import CASES as RESOURCE_CASES
for item in RESOURCE_CASES:
    raw = typed('serial', item.value, item.kwargs['number_format']) if item.kwargs else item.value
    CASES.append(case('RQA-' + item.ident, {'phone':'Телефон','dates':'Дата заявки','names':'Имя'}[item.field_name],
                      raw, raw if item.canonical is None else item.canonical, list(item.codes),
                      'Resource QA 1.5; ' + item.category, 'resource-qa'))

# Explicitly distinguish a field failure from diagnostics with a usable phone key.
for entry in CASES:
    entry["problem_list"] = bool(entry["codes"])
    entry["diagnostic_codes"] = [c for c in entry["codes"] if c in {"PHONE_EXTRA_CONTEXT", "NAME_LATIN_SCRIPT", "NAME_CASE_REVIEW", "NAME_MIXED_SCRIPT"}]
    usable_phone = entry["field"] == "Телефон" and all(c == "PHONE_EXTRA_CONTEXT" for c in entry["codes"])
    if usable_phone or not entry["codes"]:
        entry["canonical"] = entry["expected"]
        entry["status"] = "UNCHANGED" if entry["input"] == entry["expected"] else "NORMALIZED"
    else:
        entry["canonical"] = None
        entry["status"] = "MISSING" if any(c.endswith("_MISSING") for c in entry["codes"]) else "UNCHANGED" if entry["diagnostic_codes"] else "PROBLEM"


# DEC-29: usable personal-name projection with unresolved remaining components.
partial_name = case('N43', 'Имя', 'Иван Иванов Петрович', 'Иван', ['NAME_AMBIGUOUS'],
                    'Имя подтверждено; остальные компоненты на проверку; полный ФИО сохраняется', 'user-formal-review')
partial_name.update(canonical='Иван', status='NORMALIZED', problem_list=True, diagnostic_codes=[])
CASES.append(partial_name)


def materialize(value):
    if not isinstance(value, dict):
        return value
    if value["type"] == "datetime":
        return datetime.fromisoformat(value["value"])
    return value["value"]
