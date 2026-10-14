"""Score the extractor on generated invoices.

Usage (from the project folder):
    python -m eval.evaluate data_gen/output/A
    python -m eval.evaluate data_gen/output/A --by layout
    python -m eval.evaluate data_gen/output/A --by anomalies
    python -m eval.evaluate data_gen/output/A --failures 15 --field invoice_date
"""

import argparse
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

from app.models import FIELDS
from app.pipeline import extract_invoice

AMOUNT_FIELDS = {"subtotal", "tax", "total"}
SHORT_NAMES = {"vendor": "ven", "invoice_number": "num", "invoice_date": "date",
               "due_date": "due", "currency": "cur", "subtotal": "sub",
               "tax": "tax", "total": "tot"}

# Which meta details help explain a failure in each field.
HINTS = {
    "vendor": ["printed_name"],
    "invoice_number": ["labels.number"],
    "invoice_date": ["labels.date", "date_format"],
    "due_date": ["due_mode", "labels.due", "date_format"],
    "currency": ["currency_style"],
    "subtotal": ["labels.subtotal", "amount_style"],
    "tax": ["amount_style"],
    "total": ["labels.total", "amount_style", "scenario"],
}


def same(field_name, expected, got) -> bool:
    """Exact match after normalisation, as the brief defines it."""
    if expected is None or got is None:
        return expected is None and got is None
    if field_name in AMOUNT_FIELDS:
        try:
            return abs(float(expected) - float(got)) < 0.005
        except (TypeError, ValueError):
            return False
    return str(expected) == str(got)


def meta_value(meta: dict, key: str):
    """Read 'labels.date' style keys from the nested meta dict."""
    value = meta
    for part in key.split("."):
        value = value.get(part) if isinstance(value, dict) else None
    return value


def percent(right: int, total: int) -> float:
    return 100.0 * right / total if total else 0.0


def main() -> None:
    # Always print UTF-8, so Japanese text works even when piped (| head, | tee).
    sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Score the extractor on generated invoices.")
    parser.add_argument("folder", help="Folder with PDF + JSON pairs, e.g. data_gen/output/A")
    parser.add_argument("--by", help="Break results down by a meta key, e.g. layout, "
                                     "country, scenario or anomalies")
    parser.add_argument("--failures", type=int, default=0, help="Show this many failures")
    parser.add_argument("--field", choices=FIELDS, help="Only show failures for this field")
    args = parser.parse_args()

    folder = Path(args.folder)
    truth_files = sorted(folder.glob("*.json"))
    if not truth_files:
        print(f"No JSON files found in {folder}")
        return

    correct = defaultdict(int)
    by_group = defaultdict(lambda: defaultdict(lambda: [0, 0]))  # group -> field -> [right, total]
    failures, errors, times = [], [], []

    for truth_path in truth_files:
        truth = json.loads(truth_path.read_text(encoding="utf-8"))
        meta = truth.get("meta", {})
        pdf_bytes = truth_path.with_suffix(".pdf").read_bytes()

        start = time.perf_counter()
        try:
            result = extract_invoice(pdf_bytes)
        except Exception as error:  # shown below; the service itself never crashes
            result = {}
            errors.append((truth_path.stem, f"{type(error).__name__}: {error}"))
        times.append(time.perf_counter() - start)

        for name in FIELDS:
            ok = same(name, truth[name], result.get(name))
            correct[name] += ok

            if args.by:
                value = meta_value(meta, args.by)
                # A meta value can be a list (e.g. anomalies): count the invoice
                # under each item. An empty list is counted under "none".
                keys = value if isinstance(value, list) else [value]
                for key in keys or ["none"]:
                    cell = by_group[str(key)][name]
                    cell[0] += ok
                    cell[1] += 1

            if not ok and (args.field is None or args.field == name):
                hints = {key: meta_value(meta, key) for key in HINTS[name]}
                failures.append((truth_path.stem, name, truth[name], result.get(name), hints))

    count = len(truth_files)
    overall = sum(correct.values())

    print(f"\nInvoices: {count}    Overall field accuracy: "
          f"{percent(overall, count * len(FIELDS)):.1f}%\n")
    print(f"{'Field':<16}{'Correct':>10}{'Accuracy':>11}")
    for name in FIELDS:
        print(f"{name:<16}{correct[name]:>6}/{count:<4}{percent(correct[name], count):>9.1f}%")

    print(f"\nTime per invoice: average {1000 * sum(times) / count:.0f} ms, "
          f"slowest {1000 * max(times):.0f} ms (limit 1000 ms)")

    if errors:
        print(f"\nERRORS in {len(errors)} invoices (first 5):")
        for stem, message in errors[:5]:
            print(f"  {stem}: {message}")

    if args.by:
        print(f"\nAccuracy by {args.by}:")
        for group in sorted(by_group):
            cells = by_group[group]
            n = cells[FIELDS[0]][1]
            parts = " ".join(f"{SHORT_NAMES[f]}:{percent(*cells[f]):>4.0f}%" for f in FIELDS)
            print(f"  {group:<36} n={n:<4} {parts}")

    if args.failures:
        if folder.name.upper().startswith("B"):
            print("\nNOTE: you are looking at group B failures. Use them to measure, "
                  "not to tune labels.py (keep B honest).")
        print(f"\nFirst {min(args.failures, len(failures))} of {len(failures)} failures:")
        for stem, name, expected, got, hints in failures[:args.failures]:
            hint_text = ", ".join(f"{k}={v!r}" for k, v in hints.items())
            print(f"  {stem}  {name}: expected {expected!r}, got {got!r}   [{hint_text}]")


if __name__ == "__main__":
    main()