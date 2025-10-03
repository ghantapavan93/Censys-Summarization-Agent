from __future__ import annotations

import json
import sys
from pathlib import Path

here = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(here))  # ensure 'backend' package is importable

from backend.services.ai_check import ai_rewrite_check


def main():
    sample = json.loads((here / 'examples' / 'input.sample.json').read_text(encoding='utf-8'))
    res = ai_rewrite_check(sample)
    print(json.dumps(res, indent=2))


if __name__ == '__main__':
    main()
