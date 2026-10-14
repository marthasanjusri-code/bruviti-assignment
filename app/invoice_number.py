"""Find the invoice number, printed as-is."""

import re

from app import labels
from app.models import Found

# An ID: letters, digits and / - _ . with at least one digit.
ID_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9/_.\-]*")
# General labels like "Document No.", "Bill No:", "Ref." (used only as a fallback).
GENERIC_LABEL = re.compile(r"(?i)(?<![A-Za-z])(no|nr|number|num|#|ref)(?![A-Za-z])\.?[\s:.#]*")
FALLBACK_WORDS = ("ref", "no", "nr", "number", "num", "id", "#")
COLUMN_MATCH = 20   # points: a value below a label starts within this distance
FALLBACK_WARNING = "Invoice number found without a known label."


def label_regex(keyword: str):
    if keyword.isascii():
        parts = [re.escape(part) for part in keyword.split()]
        return re.compile(r"(?i)(?<![A-Za-z0-9])" + r"[\s.]*".join(parts) + r"(?![A-Za-z0-9])")
    return re.compile(re.escape(keyword))


# Longer keywords first, so "invoice number" is tried before "invoice no".
LABELS = [label_regex(k) for k in sorted(labels.INVOICE_NUMBER, key=len, reverse=True)]


def first_id(text: str) -> str | None:
    for match in ID_TOKEN.finditer(text):
        token = match.group().rstrip(".-/")
        if any(ch.isdigit() for ch in token):
            return token
    return None


def table_start(lines: list) -> int:
    """Index of the item table header, or the number of lines if there is none."""
    for index, line in enumerate(lines):
        text = labels.normalise(line.text)
        words = sum(labels.keyword_position(text, w) is not None for w in labels.TABLE_HEADER)
        if words >= 2 and not any(ch.isdigit() for ch in line.text):
            return index
    return len(lines)


def value_near(lines, index, seg_index, after_label) -> tuple:
    """Look for the ID after a label: same segment, next segment, then below."""
    line = lines[index]
    value = first_id(after_label)
    if value:
        return value, 0.95, "label, same segment"
    if seg_index + 1 < len(line.segments):
        value = first_id(line.segments[seg_index + 1])
        if value:
            return value, 0.9, "label, next segment"
    label_x = line.starts[seg_index]
    for below in lines[index + 1:index + 3]:
        if below.page != line.page:
            break
        for text, x in zip(below.segments, below.starts):
            if abs(x - label_x) <= COLUMN_MATCH:
                value = first_id(text)
                if value:
                    return value, 0.85, "label, value below"
    return None, 0.0, ""


def find_invoice_number(lines: list) -> Found:
    header = lines[:table_start(lines)]

    # 1. Known labels.
    for pattern in LABELS:
        for index, line in enumerate(header):
            for seg_index, segment in enumerate(line.segments):
                match = pattern.search(segment)
                if match:
                    value, conf, source = value_near(header, index, seg_index, segment[match.end():])
                    if value:
                        return Found(value, conf, source)

    # 2. General fallbacks. These now search the same segment, the next segment
    #    AND the line below, like known labels do (fixed after measuring B).
    for index, line in enumerate(header):
        for seg_index, segment in enumerate(line.segments):
            words = labels.normalise(segment).split()

            # "Invoice Ref: X", "Invoice ID X", "Invoice 7781"
            if len(words) > 1 and words[0] == "invoice":
                rest = re.sub(r"(?i)^invoice\W*", "", segment)
                rest_words = labels.normalise(rest).split()
                if any(ch.isdigit() for ch in rest) or (rest_words and rest_words[0] in FALLBACK_WORDS):
                    value, _, source = value_near(header, index, seg_index, rest)
                    if value:
                        return Found(value, 0.6, "fallback: invoice word, " + source,
                                     [FALLBACK_WARNING])

            # "Document No. X", "Bill No: X", "Our Ref. X" -- unless it is a PO, customer...
            for match in GENERIC_LABEL.finditer(segment):
                before = labels.normalise(segment[:match.start()]).split()[-2:]
                if labels.has_any(" ".join(before), labels.NOT_INVOICE_NUMBER):
                    continue
                value, _, source = value_near(header, index, seg_index, segment[match.end():])
                if value:
                    return Found(value, 0.6, "fallback: generic label, " + source,
                                 [FALLBACK_WARNING])

    return Found(None, 0.0, "not found", ["No invoice number found."])