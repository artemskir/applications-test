"""Restore exact original XLSX bytes from a four-sheet normalization result."""
import argparse
import json
from pathlib import Path
import sys
from normalize import positive
from normalizer.models import NormalizationError
from normalizer.pipeline import restore


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--max-input-bytes', type=positive, default=104857600)
    parser.add_argument('--max-uncompressed-bytes', type=positive, default=536870912)
    args = parser.parse_args()
    try:
        result = restore(args.input, args.output, args.max_input_bytes, args.max_uncompressed_bytes)
    except NormalizationError as exc:
        print(f'{exc.code}: {exc}', file=sys.stderr)
        return exc.exit_code
    except OSError:
        print('IO_ERROR: Восстановленный файл не опубликован; перезапись запрещена.', file=sys.stderr)
        return 3
    except Exception:
        print('INTERNAL_ERROR: Не удалось восстановить исходник.', file=sys.stderr)
        return 4
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8')
    raise SystemExit(main())
