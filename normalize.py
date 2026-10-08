"""Normalize a user XLSX into Данные, Проблемы, Оригинал, Аудит, Проверить."""
import argparse
import json
from pathlib import Path
import sys
from normalizer.models import NormalizationError
from normalizer.pipeline import normalize


def positive(value):
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError('Limit must be positive')
    return number


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--sheet')
    parser.add_argument('--max-input-bytes', type=positive, default=104857600)
    parser.add_argument('--max-uncompressed-bytes', type=positive, default=536870912)
    parser.add_argument('--max-rows', type=positive, default=1048575)
    args = parser.parse_args()
    try:
        result = normalize(args.input, args.output, args.sheet, args.max_input_bytes, args.max_uncompressed_bytes, args.max_rows)
    except NormalizationError as exc:
        print(f'{exc.code}: {exc}', file=sys.stderr)
        return exc.exit_code
    except OSError:
        print('IO_ERROR: Не удалось прочитать или опубликовать файл; перезапись запрещена.', file=sys.stderr)
        return 3
    except Exception:
        print('INTERNAL_ERROR: Обработка прервана; итоговый файл не опубликован.', file=sys.stderr)
        return 4
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8')
    raise SystemExit(main())
