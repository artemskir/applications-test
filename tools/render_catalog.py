"""Refresh the specification appendix from declarative acceptance examples."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fixtures.scenarios import CASES


def display(value):
    if value is None:
        return "пустая ячейка"
    result = json.dumps(value, ensure_ascii=False, sort_keys=True)
    for char, escape in [("\u00a0", r"\u00a0"), ("\u202f", r"\u202f"), ("\u200b", r"\u200b"),
                         ("\u202e", r"\u202e"), ("\u202c", r"\u202c")]:
        result = result.replace(char, escape)
    return "`" + result.replace("|", "&#124;").replace("`", "&#96;") + "`"


def main():
    path = Path(__file__).resolve().parents[1] / "docs" / "SPECIFICATION.md"
    document = path.read_text(encoding="utf-8")
    begin, end = "<!-- CASE_CATALOG_BEGIN -->", "<!-- CASE_CATALOG_END -->"
    if document.count(begin) != 1 or document.count(end) != 1:
        raise ValueError("Catalog markers must occur exactly once")
    rows = ["| ID | Поле | Вход | Ожидаемое значение | Canonical | Статус | Коды | Примечание |",
            "|---|---|---|---|---|---|---|---|"]
    for case in CASES:
        codes = ", ".join(case["codes"]) or "—"
        note = case["note"].replace("|", "&#124;")
        if case["origin"] != "synthetic":
            note = (note + "; " if note else "") + "источник: " + case["origin"]
        rows.append(f"| {case['id']} | {case['field']} | {display(case['input'])} | {display(case['expected'])} | {display(case.get('canonical'))} | {case.get('status', '—')} | {codes} | {note} |")
    left, rest = document.split(begin)
    _, right = rest.split(end)
    path.write_text(left + begin + "\n\n" + "\n".join(rows) + "\n\n" + end + right, encoding="utf-8")
    print(f"Rendered {len(CASES)} cases")


if __name__ == "__main__":
    main()
