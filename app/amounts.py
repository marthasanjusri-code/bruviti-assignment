"""Find subtotal, tax and total in the summary lines below the item table."""

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from app import labels
from app.models import Found

PERCENT = re.compile(r"-?\d+(?:[.,]\d+)?\s*%")
# A number, possibly with separators: 1,087.94  1.234,56  1 234,56  1,23,456.00  142,480
NUMBER = re.compile(r"(?<![0-9A-Za-z/])-?\d+(?:[,.']\d+| \d{3}(?!\d))*(?![0-9A-Za-z/])")
ROLES = {"subtotal": labels.SUBTOTAL, "tax": labels.TAX, "total": labels.TOTAL}


@dataclass
class SummaryLine:
    line: object          # the Line from pdf_text
    value: Decimal
    role: str | None      # "subtotal", "tax", "total", "ignore" or None


@dataclass
class AmountsResult:
    subtotal: Found
    tax: Found
    total: Found
    total_line: object | None    # used by the currency finder
    warnings: list


def parse_number(token: str) -> Decimal:
    """The last separator is the decimal point if 1 or 2 digits follow it."""
    text = token.replace(" ", "").replace("'", "")
    negative = text.startswith("-")
    text = text.lstrip("-")
    last = max(text.rfind("."), text.rfind(","))
    if last != -1 and len(text) - last - 1 in (1, 2):
        whole = re.sub(r"[.,]", "", text[:last])
        value = Decimal(f"{whole or '0'}.{text[last + 1:]}")
    else:
        value = Decimal(re.sub(r"[.,]", "", text))
    return -value if negative else value


def numbers_in(text: str) -> list:
    text = PERCENT.sub(" ", text)
    values = []
    for token in NUMBER.findall(text):
        try:
            values.append(parse_number(token))
        except InvalidOperation:
            pass
    return values


def summary_lines(lines: list) -> list:
    """Lines below the item table that hold exactly one amount and some words."""
    start = 0
    for index, line in enumerate(lines):
        text = labels.normalise(line.text)
        header_words = sum(labels.keyword_position(text, w) is not None for w in labels.TABLE_HEADER)
        if header_words >= 2 and not numbers_in(line.text):
            start = index + 1  # the LAST table header, so page 2 headers count too

    result = []
    for line in lines[start:]:
        text = labels.normalise(line.text)
        if labels.has_any(text, labels.NOT_AMOUNT_LINES):
            continue
        values = numbers_in(line.text)
        if len(values) != 1:
            continue  # item rows have several numbers; words-only lines have none
        role = "ignore" if labels.has_any(text, labels.IGNORE_SUMMARY) else labels.first_role(text, ROLES)
        result.append(SummaryLine(line, values[0], role))
    return result


def money(value: Decimal) -> float:
    return float(round(value, 2))


def find_amounts(lines: list) -> AmountsResult:
    warnings = []
    candidates = summary_lines(lines)
    usable = [c for c in candidates if c.role != "ignore"]

    # --- Total: last labelled total, else the last amount -------------------
    totals = [c for c in usable if c.role == "total"]
    if totals:
        total_c, total_conf = totals[-1], 0.9
    elif usable:
        total_c, total_conf = usable[-1], 0.6
        warnings.append("No total label found; used the last amount on the invoice.")
    else:
        total_c, total_conf = None, 0.0

    sub_c, sub_conf, tax_cs, tax_conf = None, 0.0, [], 0.0

    # --- A "total" followed by tax lines and then a bigger, unlabelled amount
    #     is really the subtotal (e.g. "Total before tax"). Found from B evidence.
    if total_c:
        after = usable[usable.index(total_c) + 1:]
        taxes_after = [c for c in after[:-1] if c.role == "tax"]
        if after and taxes_after and after[-1].role is None and after[-1].value > total_c.value:
            sub_c, sub_conf = total_c, 0.85
            tax_cs, tax_conf = taxes_after, 0.85
            total_c, total_conf = after[-1], 0.85
            warnings.append("A line labelled as a total is followed by tax, "
                            "so it was read as the subtotal.")

    before = usable[:usable.index(total_c)] if total_c else []

    # --- Subtotal and tax by label -------------------------------------------
    if not sub_c:
        subs = [c for c in before if c.role == "subtotal"]
        sub_c, sub_conf = (subs[-1], 0.9) if subs else (None, 0.0)
        between = before[before.index(sub_c) + 1:] if sub_c else before
        tax_cs = [c for c in between if c.role == "tax"]
        tax_conf = 0.9 if tax_cs else 0.0

    # --- Arithmetic fallbacks (need no label knowledge) ----------------------
    if total_c and not sub_c:
        for c in reversed(before):  # a line that, plus the tax lines, makes the total
            others = [t for t in before if t.role == "tax" and t is not c]
            if abs(c.value + sum(t.value for t in others) - total_c.value) <= Decimal("0.01"):
                sub_c, sub_conf, tax_cs = c, 0.85, others
                tax_conf = 0.85 if others else 0.0
                break
    if total_c and sub_c and not tax_cs:
        gap = total_c.value - sub_c.value
        after_sub = before[before.index(sub_c) + 1:] if sub_c in before else []
        for c in after_sub:  # a line whose amount is exactly total - subtotal
            if abs(c.value - gap) <= Decimal("0.01"):
                tax_cs, tax_conf = [c], 0.8
                break
    if total_c and not sub_c:
        plain = [c for c in before if c.role != "tax"]
        if plain:
            sub_c, sub_conf = max(plain, key=lambda c: c.value), 0.5
            warnings.append("Subtotal guessed as the largest amount above the total.")

    total = total_c.value if total_c else None
    subtotal = sub_c.value if sub_c else None
    tax = sum((c.value for c in tax_cs), Decimal("0")) if tax_cs else None

    # --- Checks and warnings --------------------------------------------------
    if len(tax_cs) > 1:
        warnings.append(f"Tax is the sum of {len(tax_cs)} tax lines.")
    for c in candidates:
        if c.role == "ignore" and labels.has_any(labels.normalise(c.line.text), ["round off", "rounding", "round"]):
            warnings.append(f"Total includes a rounding adjustment of {money(c.value)}.")
    if total is None:
        warnings.append("No total found.")
    if subtotal is None:
        warnings.append("No subtotal found.")
    if tax is None:
        warnings.append("No tax line found.")

    if None not in (total, subtotal, tax):
        if abs(subtotal + tax - total) <= Decimal("0.01"):
            sub_conf, tax_conf, total_conf = (max(c, 0.97 if c >= 0.85 else c)
                                              for c in (sub_conf, tax_conf, total_conf))
        else:
            warnings.append(f"Subtotal plus tax ({money(subtotal + tax)}) does not equal "
                            f"total ({money(total)}).")
            sub_conf, tax_conf, total_conf = (min(c, 0.8) for c in (sub_conf, tax_conf, total_conf))

    return AmountsResult(
        subtotal=Found(money(subtotal) if subtotal is not None else None, sub_conf, "summary"),
        tax=Found(money(tax) if tax is not None else None, tax_conf, "summary"),
        total=Found(money(total) if total is not None else None, total_conf, "summary"),
        total_line=total_c.line if total_c else None,
        warnings=warnings,
    )