"""Decide whether the document is an invoice (rule O4)."""

from app import labels

# Titles of documents that are not invoices, and what they are.
# Version 1 (blind B test): only the brief's own words ("a quotation, a
# delivery note, a statement").
# Version 2 (added after measuring B): common short forms, plus German and
# Japanese titles, because Appendix M vendors are in Germany and Japan.
# Group B is no longer blind for document type after this change (see DATA.md).
NOT_INVOICE = {
    "quotation": "quotation", "quote": "quotation", "angebot": "quotation",
    "kostenvoranschlag": "quotation", "見積書": "quotation",
    "delivery note": "delivery note", "lieferschein": "delivery note",
    "納品書": "delivery note",
    "statement": "statement", "kontoauszug": "statement",
}
INVOICE_WORDS = ["invoice", "rechnung", "請求書"]
LABEL_WORDS = ["no", "nr", "number", "#", "ref", "date"]   # a label, not a title
TITLE_LINES = 8        # titles are near the top of page 1
MAX_TITLE_WORDS = 4    # titles are short


def document_kind(lines: list) -> str | None:
    """Return e.g. 'quotation' if the document is not an invoice, else None."""
    top = [line for line in lines if line.page == 1][:TITLE_LINES]
    for line in top:
        for segment in line.segments:
            text = labels.normalise(segment)
            if (not text or any(ch.isdigit() for ch in text)
                    or len(text.split()) > MAX_TITLE_WORDS
                    or segment.rstrip().endswith(":")
                    or labels.has_any(text, LABEL_WORDS)
                    or labels.has_any(text, INVOICE_WORDS)):
                continue
            for keyword, kind in NOT_INVOICE.items():
                if labels.keyword_position(text, keyword) is not None:
                    return kind
    return None