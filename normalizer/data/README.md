# Локальный справочник ролей

`name_lexicon.json.gz` — детерминированное сжатие только написаний и ролей из двух
зафиксированных источников. Происхождение/пол не используются для определения роли.
`manifest.json` хранит commits, SHA-256 исходных файлов и самого справочника, количества.
Справочник проверяется по хешу при загрузке, сеть во время обработки не используется.

- [russiannames](https://github.com/datacoon/russiannames), Иван Бегтин, BSD-3-Clause:
  тексты из names/surnames/midnames Parquet. Лицензия в russiannames-LICENSE.txt.
- [НЭН — сервис «Имена»](https://n-e-n.ru/imena/), [датасет](https://github.com/mdanina/nen-imena-dataset),
  CC BY 4.0: name, short_forms, international_forms. Лицензия в nen-imena-dataset-LICENSE.txt.

Изменения: NFC/casefold, удаление повторов, сохранение только написаний, объединение
основных и кратких/международных форм НЭН. Редакционные тексты, пол и частоты не включены.
Проверенные исключения и сомнительные слова определены спецификацией и name_roles.py.
Отсутствие в справочнике означает проверку, не недействительность имени.

Сборка: `python tools/build_name_lexicon.py --sources generated/name-sources --output-dir NEW_DIRECTORY`.
Нужен duckdb из отдельного QA requirements; рабочему CLI достаточно корневых зависимостей.
