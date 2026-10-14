"""Vendor matching against Appendix M."""

import pytest

from app.vendors import find_vendor
from tests.helpers import make_lines


@pytest.mark.parametrize("printed, expected", [
    ("NORTHWIND TRADERS LTD", "Northwind Traders"),
    ("Sakura Precision Co., Ltd.", "Sakura Precision"),
    ("SAKURA PRECISION K.K.", "Sakura Precision"),
    ("Meridian Industrial G.m.b.H.", "Meridian Industrial"),
    ("Pine Crest Packaging Pvt. Ltd.", "Pinecrest Packaging"),
    ("Nortwind Traders Ltd", "Northwind Traders"),          # typo
    ("Blue Harbor Logistics", "Blue Harbour Logistics"),    # American spelling
])
def test_name_variants(printed, expected):
    result = find_vendor(make_lines([printed, "Invoice No: 1001"]))
    assert result.found.value == expected


def test_unknown_vendor():
    result = find_vendor(make_lines(["Orbit Tools Ltd", "Invoice No: 1001"]))
    assert result.found.value == "unknown"
    assert result.found.confidence == 0.2
    assert result.country is None


def test_vendor_on_same_line_as_delivery_note_title():
    # Regression: "Delivery Note" on the vendor's line used to hide the vendor.
    result = find_vendor(make_lines(["Northwind Traders Limited || Delivery Note"]))
    assert result.found.value == "Northwind Traders"


def test_country_and_currency_come_from_appendix_m():
    result = find_vendor(make_lines(["Kestrel Components Inc."]))
    assert (result.country, result.currency) == ("US", "USD")