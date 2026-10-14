"""List generated invoices whose meta matches all the given filters.

Usage:
    python -m eval.find data_gen/output/A country=JP
    python -m eval.find data_gen/output/A anomalies=watermark
    python -m eval.find data_gen/output/A layout=grid scenario=mismatch
"""

import json
import sys
from pathlib import Path

from eval.evaluate import meta_value


def matches(meta: dict, key: str, wanted: str) -> bool:
    value = meta_value(meta, key)
    if isinstance(value, list):
        return wanted in value
    return str(value) == wanted


def main() -> None:
    folder, filters = Path(sys.argv[1]), [arg.split("=", 1) for arg in sys.argv[2:]]
    for truth_path in sorted(folder.glob("*.json")):
        meta = json.loads(truth_path.read_text(encoding="utf-8")).get("meta", {})
        if all(matches(meta, key, wanted) for key, wanted in filters):
            print(truth_path.with_suffix(".pdf").as_posix())


if __name__ == "__main__":
    main()