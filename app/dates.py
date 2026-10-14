"""Find the invoice date and due date, and return them as ISO dates.

Understands numeric dates (03/09/2026, 9/3/26, 03.09.2026, 2026-09-03),
written months (3 September 2026, Sep 3, 2026, 3. März 2026), Japanese
dates (2026年9月3日) and payment terms (Net 30, 30 days, 30 Tagen, 30日).
"""

import re
from dataclasses import dataclass
from datetime import date, timedelta

from app import labels
from app.invoice_number import table_start
from app.models import Found

# Appendix M: day-first for UK, Germany, Japan and India; month-first for the US.
DAY_FIRST = {"GB": True, "DE": True, "JP": True, "IN": True, "US": False}
COLUMN_MATCH = 20   # points: a value below a label starts within this distance

# Words just before "date" that mean it is NOT the invoice date.
NOT_INVOICE_DATE_BEFORE = {"order", "delivery", "ship", "shipping", "due", "payment",
                           "expiry", "valid", "po"}

# Fallback for due dates with an unknown label (added after measuring B):
# a date next to a word starting with one of these stems.
DUE_STEM = re.compile(r"(?i)(?<![A-Za-z])(pay|due|fällig)\w*")

MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
    "januar": 1, "februar": 2, "märz": 3, "maerz": 3, "mai": 5, "juni": 6,
    "juli": 7, "oktober": 10, "dezember": 12,
}

YMD = re.compile(r"(?<!\d)(\d{4})\s*[-./年]\s*(\d{1,2})\s*[-./月]\s*(\d{1,2})\s*日?(?!\d)")
NUMERIC = re.compile(r"(?<!\d)(\d{1,2})([-./])(\d{1,2})\2(\d{4}|\d{2})(?!\d)")
DAY_MONTH_YEAR = re.compile(
    r"(?<!\d)(\d{1,2})(?:st|nd|rd|th)?\.?[\s-]+([A-Za-zÄÖÜäöü]{3,9})\.?,?[\s-]+(\d{4}|\d{2})(?!\d)")
MONTH_DAY_YEAR = re.compile(
    r"(?<![A-Za-z])([A-Za-zÄÖÜäöü]{3,9})\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})(?!\d)")

TERMS = [
    re.compile(r"(?i)\bnet\s*(\d{1,3})\b"),
    re.compile(r"(?i)\bdue\s+in\s+(\d{1,3})\s*days?\b"),
    re.compile(r"(?i)(?<![\d/])(\d{1,3})\s*days?\b"),
    re.compile(r"(?i)(?<!\d)(\d{1,3})\s*tag(?:e|en)?\b"),
    re.compile(r"(?<![月\d])(\d{1,3})\s*日(?!\d)"),
]


@dataclass
class ParsedDate:
    value: date
    raw: str              # the text as printed
    ambiguous: bool       # day and month could be swapped
    short_year: bool      # printed with a 2-digit year
    start: int
    end: int


def month_number(word: str):
    word = word.lower().rstrip(".")
    if len(word) < 3:
        return None
    for name, number in MONTHS.items():
        if name.startswith(word):
            return number
    return None


def make_year(text: str) -> int:
    return int(text) if len(text) == 4 else 2000 + int(text)


def parse_dates(text: str, day_first: bool) -> list:
    """All dates in the text, left to right, without overlaps."""
    found = []

    def add(match, year, month, day, ambiguous=False, short_year=False):
        try:
            found.append(ParsedDate(date(year, month, day), match.group().strip(),
                                    ambiguous, short_year, match.start(), match.end()))
        except ValueError:
            pass  # e.g. 31/02/2026 is not a real date

    for m in YMD.finditer(text):
        add(m, int(m[1]), int(m[2]), int(m[3]))
    for m in NUMERIC.finditer(text):
        a, b, year = int(m[1]), int(m[3]), make_year(m[4])
        short = len(m[4]) == 2
        if a > 12 and b <= 12:
            add(m, year, b, a, short_year=short)
        elif b > 12 and a <= 12:
            add(m, year, a, b, short_year=short)
        elif a <= 12 and b <= 12:
            day, month = (a, b) if day_first else (b, a)
            add(m, year, month, day, ambiguous=(a != b), short_year=short)
    for m in DAY_MONTH_YEAR.finditer(text):
        month = month_number(m[2])
        if month:
            add(m, make_year(m[3]), month, int(m[1]), short_year=len(m[3]) == 2)
    for m in MONTH_DAY_YEAR.finditer(text):
        month = month_number(m[1])
        if month:
            add(m, int(m[3]), month, int(m[2]))

    found.sort(key=lambda d: (d.start, -(d.end - d.start)))
    result, last_end = [], -1
    for d in found:
        if d.start >= last_end:
            result.append(d)
            last_end = d.end
    return result


def label_regex(keyword: str):
    parts = [re.escape(part) for part in keyword.split()]
    body = r"[\s.]*".join(parts)
    if keyword.isascii():
        body = r"(?<![A-Za-z0-9])" + body + r"(?![A-Za-z0-9])"
    return re.compile(body, re.IGNORECASE)


def find_terms(text: str):
    """(days, printed text) for terms like 'Net 30', or None."""
    for pattern in TERMS:
        m = pattern.search(text)
        if m and 0 < int(m[1]) <= 180:
            return int(m[1]), m.group().strip()
    return None


def date_near(lines, index, seg_index, after_label, day_first):
    """The date after a label: same segment, next segment, or directly below."""
    found = parse_dates(after_label, day_first)
    if found:
        return found[0], 0.95
    line = lines[index]
    if seg_index + 1 < len(line.segments):
        found = parse_dates(line.segments[seg_index + 1], day_first)
        if found:
            return found[0], 0.9
    if index + 1 < len(lines) and lines[index + 1].page == line.page:
        below = lines[index + 1]
        for text, x in zip(below.segments, below.starts):
            if abs(x - line.starts[seg_index]) <= COLUMN_MATCH:
                found = parse_dates(text, day_first)
                if found:
                    return found[0], 0.85
    return None


def find_labelled_date(lines, keywords, day_first, skip_before=frozenset()):
    for pattern in [label_regex(k) for k in sorted(keywords, key=len, reverse=True)]:
        for index, line in enumerate(lines):
            for seg_index, segment in enumerate(line.segments):
                for match in pattern.finditer(segment):
                    before = labels.normalise(segment[:match.start()]).split()[-1:]
                    if before and before[0] in skip_before:
                        continue  # e.g. "Order Date", "Due Date"
                    after = segment[match.end():]
                    if find_terms(after) and not parse_dates(after, day_first):
                        continue  # "Due in 30 days" is terms, not a date
                    result = date_near(lines, index, seg_index, after, day_first)
                    if result:
                        return result
    return None


def find_due_by_stem(lines, day_first, invoice_date):
    """Fallback: a date next to a word like pay, payable, payment, due, fällig."""
    for index, line in enumerate(lines):
        for seg_index, segment in enumerate(line.segments):
            match = DUE_STEM.search(segment)
            if not match:
                continue
            after = segment[match.end():]
            if find_terms(after) and not parse_dates(after, day_first):
                continue  # payment terms, not a date
            result = date_near(lines, index, seg_index, after, day_first)
            if result and result[0].value != invoice_date:
                return result[0], 0.7
    return None


def find_dates(lines: list, country: str | None, country_note: str) -> tuple:
    """Return (invoice_date Found, due_date Found)."""
    day_first = DAY_FIRST.get(country, True)
    order = "day-first" if day_first else "month-first"
    header = lines[:table_start(lines)] or lines
    inv_warnings, due_warnings = [], []

    def describe(parsed, confidence, warnings):
        if parsed.ambiguous:
            warnings.append(f"Date {parsed.raw} read as {order} ({country_note}).")
            confidence = min(confidence, 0.8)
        if parsed.short_year:
            warnings.append(f"Year in {parsed.raw} read as {parsed.value.year}.")
            confidence -= 0.05
        return confidence

    # --- Invoice date --------------------------------------------------------
    invoice = find_labelled_date(header, labels.INVOICE_DATE, day_first, NOT_INVOICE_DATE_BEFORE)
    if invoice is None:
        for line in header:  # fallback: first date on a line that is not about another date
            if labels.has_any(labels.normalise(line.text), labels.NOT_INVOICE_DATE):
                continue
            found = parse_dates(line.text, day_first)
            if found:
                invoice = (found[0], 0.6)
                inv_warnings.append("Invoice date found without a label.")
                break

    if invoice:
        inv_parsed, inv_conf = invoice
        inv_conf = describe(inv_parsed, inv_conf, inv_warnings)
        invoice_found = Found(inv_parsed.value.isoformat(), inv_conf, "date", inv_warnings)
        invoice_date = inv_parsed.value
    else:
        invoice_found = Found(None, 0.0, "not found", ["No invoice date found."])
        invoice_date = None

    # --- Due date (rule O1) ----------------------------------------------------
    printed = find_labelled_date(header, labels.DUE_DATE, day_first)
    if printed is None:
        printed = find_due_by_stem(header, day_first, invoice_date)
        if printed:
            due_warnings.append("Due date found without a known label.")
    terms = None
    for line in header + [l for l in lines if l not in header]:
        terms = find_terms(line.text)
        if terms:
            break

    if printed:
        due_parsed, due_conf = printed
        due_conf = describe(due_parsed, due_conf, due_warnings)
        due_value = due_parsed.value
        if terms and invoice_date and invoice_date + timedelta(days=terms[0]) != due_value:
            due_warnings.append(f"Printed due date differs from terms {terms[1]}; "
                                f"used the printed date.")
            due_conf = min(due_conf, 0.7)
    elif terms and invoice_date:
        due_value, due_conf = invoice_date + timedelta(days=terms[0]), 0.85
        due_warnings.append(f"Due date derived from terms {terms[1]}.")
    elif terms:
        due_value, due_conf = None, 0.0
        due_warnings.append(f"Payment terms {terms[1]} found but no invoice date to count from.")
    else:
        due_value, due_conf = None, 0.0
        due_warnings.append("No due date or payment terms found.")

    if due_value and invoice_date and due_value < invoice_date:
        due_warnings.append("Due date is before the invoice date.")

    due_found = Found(due_value.isoformat() if due_value else None, due_conf, "due", due_warnings)
    return invoice_found, due_found