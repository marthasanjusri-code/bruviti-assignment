"""Amounts: number formats, summary lines and rule O2."""

from decimal import Decimal

import pytest

from app.amounts import find_amounts, parse_number
from tests.helpers import make_lines

HEADER = "Item || Qty || Price || Amount"


@pytest.mark.parametrize("text, expected", [
    ("1,087.94", "1087.94"),      # English
    ("1.234,56", "1234.56"),      # German
    ("1 234,56", "1234.56"),      # German with spaces
    ("142,480", "142480"),        # Japanese yen, no decimals
    ("1,23,456.00", "123456.00"), # Indian lakh grouping
    ("361,60", "361.60"),         # decimal comma, no thousands
])
def test_parse_number_formats(text, expected):
    assert parse_number(text) == Decimal(expected)


def test_labelled_summary_lines():
    lines = make_lines([HEADER, "Pallet wrap || 12 || 18.50 || 222.00",
                        "Subtotal || 361.60", "VAT 20% || 72.32", "Amount Due || GBP 433.92"])
    result = find_amounts(lines)
    assert (result.subtotal.value, result.tax.value, result.total.value) == (361.6, 72.32, 433.92)


def test_split_indian_tax_is_summed():
    lines = make_lines([HEADER, "Subtotal || 12,000.00", "CGST 9% || 1,080.00",
                        "SGST 9% || 1,080.00", "Grand Total || Rs. 14,160.00"])
    result = find_amounts(lines)
    assert result.tax.value == 2160.0
    assert any("sum of 2 tax lines" in w for w in result.warnings)


def test_total_before_tax_is_read_as_subtotal():
    # Regression: found in group B, where "Total before tax" was taken as the total.
    lines = make_lines([HEADER, "Total before tax || 1438.90", "Value Added Tax || 287.78",
                        "Amount Payable || GBP £ 1726.68"])
    result = find_amounts(lines)
    assert (result.subtotal.value, result.tax.value, result.total.value) == (1438.9, 287.78, 1726.68)


def test_rule_o2_mismatch_keeps_printed_values_and_warns():
    lines = make_lines([HEADER, "Subtotal || 100.00", "VAT 20% || 20.00", "Total || 121.00"])
    result = find_amounts(lines)
    assert result.total.value == 121.0  # printed value, not corrected
    assert any("does not equal" in w for w in result.warnings)


def test_round_off_bank_and_words_lines_are_not_amounts():
    lines = make_lines([HEADER, "Subtotal || 12,000.40", "IGST 18% || 2,160.07",
                        "Round Off || -0.47", "Total || 14,160.00",
                        "Amount in words: Rupees Fourteen Thousand One Hundred Sixty Only",
                        "HDFC Bank A/c 50100234567812 IFSC HDFC0001234"])
    result = find_amounts(lines)
    assert result.total.value == 14160.0
    assert any("rounding adjustment" in w for w in result.warnings)