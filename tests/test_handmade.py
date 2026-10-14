"""Invoices made by hand in Microsoft Word, not by our generator.

They test PDF text produced by a different tool, with labels and wording
the extractor does not list. The expected answers were written down
before running the extractor.
"""

from pathlib import Path

import pytest

from app.models import FIELDS
from app.pipeline import extract_invoice

FIXTURES = Path(__file__).parent / "fixtures"

EXPECTED = {
    "handmade_meridian.pdf": {
        "vendor": "Meridian Industrial", "invoice_number": "MI/26/0457",
        "invoice_date": "2026-05-04", "due_date": "2026-05-25", "currency": "EUR",
        "subtotal": 447.5, "tax": 85.03, "total": 532.53,
    },
    # The printed total is 43, which does not add up. Rule O2: return the
    # printed value and warn; do not correct the arithmetic.
    "handmade_northwind_o2.pdf": {
        "vendor": "Northwind Traders", "invoice_number": "NW-1042",
        "invoice_date": "2026-09-03", "due_date": "2026-10-03", "currency": "GBP",
        "subtotal": 361.6, "tax": 72.32, "total": 43.0,
    },
}


@pytest.mark.parametrize("name", EXPECTED)
def test_handmade_invoice_fields(name):
    result = extract_invoice((FIXTURES / name).read_bytes())
    assert {f: result[f] for f in FIELDS} == EXPECTED[name]


def test_handmade_unknown_labels_lower_confidence():
    # "Document number" and "In No:" are not known labels: found by the
    # general fallback, so confidence must be lower and a warning given.
    for name in EXPECTED:
        result = extract_invoice((FIXTURES / name).read_bytes())
        assert result["confidence"]["invoice_number"] <= 0.6
        assert "Invoice number found without a known label." in result["warnings"]


def test_handmade_o2_mismatch_warns():
    result = extract_invoice((FIXTURES / "handmade_northwind_o2.pdf").read_bytes())
    assert any("does not equal total" in w for w in result["warnings"])