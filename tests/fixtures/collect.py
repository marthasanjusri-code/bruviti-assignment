"""Copy a few generated group A invoices into tests/fixtures, one per rule or anomaly.

Run after generating group A:  python -m tests.fixtures.collect
"""

import json
import shutil
from pathlib import Path

from eval.evaluate import meta_value

SOURCE = Path("data_gen/output/A")
HERE = Path(__file__).parent

# fixture name -> (meta key, value it must have)
WANTED = {
    "o1_due_and_terms_disagree": ("due_mode", "both_disagree"),
    "o1_terms_only": ("due_mode", "terms_only"),
    "o2_mismatch": ("scenario", "mismatch"),
    "o3_no_currency": ("currency_style", "none"),
    "o4_not_invoice": ("scenario", "non_invoice"),
    "o5_japan": ("country", "JP"),
    "unknown_vendor": ("scenario", "unknown_vendor"),
    "multi_page": ("anomalies", "multi_page"),
    "watermark": ("anomalies", "watermark"),
    "india_round_off": ("anomalies", "round_off"),
}


def matches(meta: dict, key: str, wanted: str) -> bool:
    value = meta_value(meta, key)
    return wanted in value if isinstance(value, list) else value == wanted


def main() -> None:
    truths = sorted(SOURCE.glob("*.json"))
    for name, (key, wanted) in WANTED.items():
        for truth_path in truths:
            meta = json.loads(truth_path.read_text(encoding="utf-8"))["meta"]
            if matches(meta, key, wanted):
                shutil.copy(truth_path, HERE / f"gen_{name}.json")
                shutil.copy(truth_path.with_suffix(".pdf"), HERE / f"gen_{name}.pdf")
                print(f"gen_{name}  <-  {truth_path.stem}")
                break
        else:
            print(f"gen_{name}  NOT FOUND")


if __name__ == "__main__":
    main()