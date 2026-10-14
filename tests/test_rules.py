"""Business rules O3, O4 and O5. (O1 is in test_dates.py, O2 in test_amounts.py.)"""

import pytest

from app.amounts import find_amounts
from app.currency import find_currency
from app.doctype import document_kind
from tests.helpers import make_lines


def test_rule_o3_no_currency_uses_vendor_currency_with_lower_confidence():
    result = find_currency(make_lines(["Total || 433.92"]), None, "GBP")
    assert result.value == "GBP"
    assert result.confidence < 0.9
    assert any("No currency printed" in w for w in result.warnings)


def test_rule_o3_printed_currency_wins():
    lines = make_lines(["Total || EUR 1.234,56"])
    result = find_currency(lines, lines[0], "GBP")
    assert result.value == "EUR"


# Rule O4 names three document types: a quotation, a delivery note, a statement.
@pytest.mark.parametrize("title, kind", [
    ("QUOTATION", "quotation"),
    ("Delivery Note", "delivery note"),
    ("Statement of Account", "statement"),
])
def test_rule_o4_document_types_from_the_brief(title, kind):
    assert document_kind(make_lines([f"NORTHWIND TRADERS LTD || {title}"])) == kind


def test_rule_o4_label_is_not_a_title():
    # "Delivery Note No:" is a field on an invoice, not a delivery note title.
    lines = make_lines(["NORTHWIND TRADERS LTD || INVOICE", "Delivery Note No: || DN-55"])
    assert document_kind(lines) is None


def test_rule_o5_jpy_amounts_become_numbers():
    result = find_amounts(make_lines(["Item || Qty || Amount", "合計 || ¥1,567,280"]))
    assert result.total.value == 1567280.0
    assert isinstance(result.total.value, float)