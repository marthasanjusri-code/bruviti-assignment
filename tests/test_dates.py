"""Dates: every supported format, day/month order, terms and rule O1."""

from datetime import date

import pytest

from app.dates import find_dates, find_terms, parse_dates
from tests.helpers import make_lines


@pytest.mark.parametrize("text, day_first, expected", [
    ("03/09/2026", True, date(2026, 9, 3)),          # UK: day first
    ("9/3/26", False, date(2026, 9, 3)),             # US: month first, 2-digit year
    ("03.09.2026", True, date(2026, 9, 3)),          # German
    ("2026.09.03", True, date(2026, 9, 3)),          # year first
    ("2026年9月3日", True, date(2026, 9, 3)),         # Japanese
    ("3 September 2026", True, date(2026, 9, 3)),
    ("Sep. 3, 2026", False, date(2026, 9, 3)),
    ("Thu, 3 Sep 2026", True, date(2026, 9, 3)),
    ("3rd September 2026", True, date(2026, 9, 3)),
    ("3. März 2026", True, date(2026, 3, 3)),        # German month name
    ("25/03/2026", False, date(2026, 3, 25)),        # 25 cannot be a month
])
def test_date_formats(text, day_first, expected):
    assert parse_dates(text, day_first)[0].value == expected


def test_ambiguity_flag():
    assert parse_dates("03/09/2026", True)[0].ambiguous is True
    assert parse_dates("03/03/2026", True)[0].ambiguous is False   # same either way
    assert parse_dates("25/03/2026", True)[0].ambiguous is False


def test_impossible_date_is_rejected():
    assert parse_dates("31/02/2026", True) == []


# Rule O1 names three forms: "Net N", "N days" and "due in N days".
@pytest.mark.parametrize("text, days", [
    ("Net 30", 30), ("2/10 Net 30", 30), ("Due in 45 days", 45),
    ("30 days", 30), ("Payment: within 21 days", 21),
    ("Zahlbar innerhalb 14 Tagen", 14), ("支払条件 30日", 30),
])
def test_payment_terms(text, days):
    assert find_terms(text)[0] == days


def test_discount_terms_are_not_a_date():
    assert parse_dates("2/10 Net 30", True) == []


def test_rule_o1_terms_only_derive_due_date():
    invoice, due = find_dates(make_lines(["Invoice Date: 03/09/2026", "Terms: Net 30"]),
                              "GB", "GB vendor")
    assert (invoice.value, due.value) == ("2026-09-03", "2026-10-03")
    assert "Due date derived from terms Net 30." in due.warnings


def test_rule_o1_printed_due_date_wins_over_terms():
    lines = make_lines(["Invoice Date: 03/09/2026", "Due Date: 10/10/2026", "Terms: Net 30"])
    _, due = find_dates(lines, "GB", "GB vendor")
    assert due.value == "2026-10-10"
    assert any("differs from terms" in w for w in due.warnings)


def test_order_date_is_not_the_invoice_date():
    lines = make_lines(["Order Date: 20/08/2026", "Invoice Date: 03/09/2026"])
    invoice, _ = find_dates(lines, "GB", "GB vendor")
    assert invoice.value == "2026-09-03"


def test_us_vendor_reads_month_first_and_warns():
    invoice, _ = find_dates(make_lines(["Dated 9/3/26"]), "US", "US vendor")
    assert invoice.value == "2026-09-03"
    assert any("month-first (US vendor)" in w for w in invoice.warnings)