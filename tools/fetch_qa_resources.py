"""Download pinned QA resources once; production normalization never uses this module."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from research.resource_sources import fetch_sources


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output-dir', type=Path, required=True)
    args=ap.parse_args()
    try:
        results=fetch_sources(args.output_dir.resolve())
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps({'downloaded':len(results),'output':str(args.output_dir)}))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
