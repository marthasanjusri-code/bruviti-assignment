"""Runs the extraction steps in order."""

from app.amounts import find_amounts
from app.currency import find_currency
from app.dates import find_dates
from app.doctype import document_kind
from app.invoice_number import find_invoice_number
from app.models import FIELDS, Found
from app.pdf_text import MAX_PAGES, read_pdf
from app.vendors import CURRENCY_COUNTRY, find_vendor

MIN_CHARS = 30   # fewer characters than this suggests a scanned PDF


def empty_result(warnings=None) -> dict:
    """A valid response with every field empty.

    Used when nothing can be extracted, so the API always returns
    the same JSON shape, even on errors.
    """
    result = {name: None for name in FIELDS}
    result["vendor"] = "unknown"
    result["confidence"] = {name: 0.0 for name in FIELDS}
    result["warnings"] = list(warnings or [])
    return result


def put(result: dict, name: str, found: Found) -> None:
    """Copy one Found into the response: value, confidence and warnings."""
    result[name] = found.value
    result["confidence"][name] = round(max(found.confidence, 0.0), 2)
    result["warnings"].extend(found.warnings)


def extract_invoice(pdf_bytes: bytes) -> dict:
    """Extract the 8 invoice fields from a PDF."""
    text = read_pdf(pdf_bytes)
    result = empty_result()

    if text.char_count < MIN_CHARS:
        result["warnings"].append("Very little text found; the PDF may be scanned.")
    if text.skipped_pages:
        result["warnings"].append(
            f"Only the first {MAX_PAGES} of {text.page_count} pages were read.")

    vendor = find_vendor(text.lines)
    put(result, "vendor", vendor.found)

    # Rule O4: not an invoice -> every field null, vendor as found, and say what it is.
    kind = document_kind(text.lines)
    if kind:
        result["warnings"].append(f"Document is a {kind}, not an invoice.")
        return result

    put(result, "invoice_number", find_invoice_number(text.lines))

    amounts = find_amounts(text.lines)
    currency = find_currency(text.lines, amounts.total_line, vendor.currency)

    # The country decides day/month order. Unknown vendor: guess it from the currency.
    if vendor.country:
        country, note = vendor.country, f"{vendor.country} vendor"
    elif currency.value in CURRENCY_COUNTRY:
        country = CURRENCY_COUNTRY[currency.value]
        note = f"country guessed from currency {currency.value}"
    else:
        country, note = None, "country unknown"
    invoice_date, due_date = find_dates(text.lines, country, note)
    put(result, "invoice_date", invoice_date)
    put(result, "due_date", due_date)

    put(result, "currency", currency)
    put(result, "subtotal", amounts.subtotal)
    put(result, "tax", amounts.tax)
    put(result, "total", amounts.total)
    result["warnings"].extend(amounts.warnings)

    return result