"""Word lists and formats for the synthetic invoice generator.

Every list is split into two groups:
  "A" -- used while building and tuning the extractor.
  "B" -- held out. Used only to measure how we handle unseen wording.

RULE: never copy anything from group B into app/labels.py.
"""

BUYER = "Bruviti Services Pvt Ltd"

# ---------------------------------------------------------------------------
# The six vendors from Appendix M.
# "names" are the ways the name is printed: upper case, with or without
# Ltd/Inc/GmbH/KK, British and American spellings, and misspellings.
# ---------------------------------------------------------------------------
VENDORS = {
    "Northwind Traders": {
        "country": "GB",
        "currency": "GBP",
        "names": {
            "A": ["NORTHWIND TRADERS LTD", "Northwind Traders Ltd", "Northwind Traders Limited"],
            "B": ["Northwind Traders", "NORTHWIND TRADERS LIMITED", "Nortwind Traders Ltd"],
        },
        "address": "14 Quay Street, Bristol BS1 4DB, United Kingdom",
        "tax_id": "VAT No. GB 123 4567 89",
        "items": [
            ("Pallet wrap, 500mm", 18.50),
            ("Corrugated boxes, large", 2.35),
            ("Packing tape, brown", 1.90),
            ("Bubble wrap roll, 750mm", 24.00),
            ("Kraft paper, 50m", 12.75),
        ],
    },
    "Blue Harbour Logistics": {
        "country": "GB",
        "currency": "GBP",
        "names": {
            "A": ["BLUE HARBOUR LOGISTICS LTD", "Blue Harbour Logistics Ltd", "Blue Harbour Logistics"],
            "B": ["Blue Harbor Logistics Ltd", "BLUE HARBOR LOGISTICS", "Blue Harbour Logistic Ltd"],
        },
        "address": "Unit 7, Dock Road, Southampton SO14 3TJ, UK",
        "tax_id": "VAT Reg GB 987 6543 21",
        "items": [
            ("Freight, Southampton to Pune", 840.00),
            ("Customs clearance fee", 95.00),
            ("Fuel surcharge", 42.50),
            ("Container handling", 120.00),
            ("Warehouse storage (per week)", 65.00),
        ],
    },
    "Kestrel Components": {
        "country": "US",
        "currency": "USD",
        "names": {
            "A": ["Kestrel Components Inc.", "KESTREL COMPONENTS INC", "Kestrel Components, Inc."],
            "B": ["Kestrel Components", "KESTRAL COMPONENTS INC.", "Kestrel Components Incorporated"],
        },
        "address": "880 Industrial Pkwy, Dayton OH 45402, USA",
        "tax_id": "EIN 31-1234567",
        "items": [
            ("Bearing kit 6204-2RS (x10)", 14.50),
            ("Drive belt A-42", 15.70),
            ("Shipping", 18.00),
            ("Hex bolt M8 (box of 100)", 9.25),
            ("Shaft coupling 12mm", 22.40),
        ],
    },
    "Meridian Industrial": {
        "country": "DE",
        "currency": "EUR",
        "names": {
            "A": ["Meridian Industrial GmbH", "MERIDIAN INDUSTRIAL GMBH", "Meridian Industrial"],
            "B": ["Meridian Industrie GmbH", "MERIDAIN INDUSTRIAL GMBH", "Meridian Industrial G.m.b.H."],
        },
        "address": "Hafenstrasse 12, 20457 Hamburg, Deutschland",
        "tax_id": "USt-IdNr. DE123456789",
        "items": [
            ("Hydraulikschlauch DN10", 34.80),
            ("Pneumatic valve 5/2", 78.50),
            ("Steel flange DN50", 19.90),
            ("Sensor cable 5m", 12.40),
            ("Servicepauschale", 150.00),
        ],
    },
    "Sakura Precision": {
        "country": "JP",
        "currency": "JPY",
        "names": {
            "A": ["Sakura Precision KK", "SAKURA PRECISION K.K.", "Sakura Precision Co., Ltd."],
            "B": ["Sakura Precision", "SAKURA PRECISON KK", "Sakura Precision Kabushiki Kaisha"],
        },
        "address": "2-5-1 Shiba, Minato-ku, Tokyo 105-0014, Japan",
        "tax_id": "Registration No. T1234567890123",
        "items": [
            ("Precision gauge block set", 48000),
            ("Micrometer 0-25mm", 12500),
            ("Calibration service", 30000),
            ("Dial indicator", 8800),
            ("Shipping and handling", 2500),
        ],
    },
    "Pinecrest Packaging": {
        "country": "IN",
        "currency": "INR",
        "names": {
            "A": ["Pinecrest Packaging Pvt Ltd", "PINECREST PACKAGING PRIVATE LIMITED", "Pinecrest Packaging"],
            "B": ["Pine Crest Packaging Pvt. Ltd.", "PINECREST PACKGING PVT LTD", "Pinecrest Packaging (P) Ltd"],
        },
        "address": "Plot 22, MIDC Bhosari, Pune 411026, Maharashtra, India",
        "tax_id": "GSTIN 27AABCP1234Q1Z5",
        "items": [
            ("Corrugated cartons 5-ply", 42.00),
            ("Stretch film roll", 380.00),
            ("Printed labels (1000)", 650.00),
            ("Foam inserts", 18.50),
            ("Strapping roll", 520.00),
        ],
    },
}

# Vendors NOT in Appendix M. Expected output: vendor = "unknown".
UNKNOWN_VENDORS = {
    "A": [("Acme Office Supplies Pvt Ltd", "IN", "INR"), ("Orbit Tools Ltd", "GB", "GBP")],
    "B": [("Greenfield Agro Co.", "US", "USD"), ("Zenith Werkzeuge GmbH", "DE", "EUR")],
}

# ---------------------------------------------------------------------------
# Field labels in English. German and Japanese labels are further below.
# ---------------------------------------------------------------------------
LABELS = {
    "title": {
        "A": ["INVOICE", "Invoice", "TAX INVOICE"],
        "B": ["Commercial Invoice", "BILL", "Invoice / Bill"],
    },
    "invoice_number": {
        "A": ["Invoice No:", "Invoice Number:", "Invoice #", "Reference #", "Inv No."],
        "B": ["Invoice Ref:", "Document No.", "Bill No:", "Our Ref."],
    },
    "invoice_date": {
        "A": ["Invoice Date:", "Date:", "Dated", "Issue Date:"],
        "B": ["Date of Issue:", "Invoice Dt:", "Billing Date:", "Tax Point:"],
    },
    "due_date": {
        "A": ["Due Date:", "Payment Due:", "Due:"],
        "B": ["Pay By:", "Please pay by", "Due On:", "Payment Date:"],
    },
    "terms": {
        "A": ["Terms", "Payment Terms:"],
        "B": ["Conditions:", "Credit Terms:"],
    },
    "subtotal": {
        "A": ["Subtotal", "Sub total", "Net Amount"],
        "B": ["Total before tax", "Net Total", "Goods Value", "Taxable Value"],
    },
    "total": {
        "A": ["Total", "Amount Due", "Balance Due", "Grand Total"],
        "B": ["Total Payable", "Amount Payable", "Invoice Total", "Please Pay"],
    },
    "bill_to": {
        "A": ["Bill to:", "Sold to"],
        "B": ["Customer:", "Invoice to:"],
    },
}

# Local-language labels. Real German and Japanese invoices often mix
# the local label with English, so the generator may use either.
LOCAL_LABELS = {
    "DE": {
        "title": {"A": ["RECHNUNG", "Rechnung / Invoice"], "B": ["Rechnung"]},
        "invoice_number": {"A": ["Rechnungsnummer:", "Rechnung Nr.:"], "B": ["Rechnungs-Nr.", "Beleg-Nr.:"]},
        "invoice_date": {"A": ["Rechnungsdatum:", "Datum:"], "B": ["Belegdatum:", "Ausstellungsdatum:"]},
        "due_date": {"A": ["Fällig am:", "Zahlbar bis:"], "B": ["Fälligkeitsdatum:", "Fällig:"]},
        "subtotal": {"A": ["Zwischensumme", "Nettobetrag"], "B": ["Summe netto", "Warenwert"]},
        "total": {"A": ["Gesamtbetrag", "Rechnungsbetrag"], "B": ["Endbetrag", "Zu zahlen"]},
    },
    "JP": {
        "title": {"A": ["請求書", "請求書 INVOICE"], "B": ["御請求書"]},
        "invoice_number": {"A": ["請求書番号", "Invoice No. / 請求書番号"], "B": ["請求番号", "伝票番号"]},
        "invoice_date": {"A": ["請求日", "発行日"], "B": ["請求年月日", "日付"]},
        "due_date": {"A": ["支払期限", "お支払期限"], "B": ["支払期日", "振込期限"]},
        "subtotal": {"A": ["小計"], "B": ["税抜合計"]},
        "total": {"A": ["合計", "ご請求金額"], "B": ["請求金額合計", "総額"]},
    },
}

# ---------------------------------------------------------------------------
# Tax line labels per country. {rate} is replaced by the tax rate.
# ---------------------------------------------------------------------------
TAX_RATES = {"GB": [20], "US": [6.25, 7.25, 8.25], "DE": [19, 7], "JP": [10], "IN": [18, 12]}

TAX_LABELS = {
    "GB": {"A": ["VAT {rate}%", "VAT"], "B": ["V.A.T. @ {rate}%", "Value Added Tax"]},
    "US": {"A": ["Sales tax {rate}%", "Tax"], "B": ["State Tax", "Sales Tax ({rate}%)"]},
    "DE": {"A": ["MwSt. {rate}%", "USt. {rate}%"], "B": ["Umsatzsteuer {rate}%", "zzgl. {rate}% MwSt."]},
    "JP": {"A": ["消費税 {rate}%", "消費税"], "B": ["消費税等 ({rate}%)", "Consumption Tax"]},
    "IN": {"A": ["GST {rate}%", "IGST {rate}%"], "B": ["Integrated GST @ {rate}%", "Tax (GST)"]},
}

# Indian invoices often split tax into two lines, each at half the rate.
# The correct "tax" output is the SUM of both lines.
INDIA_SPLIT_TAX = {
    "A": [("CGST {rate}%", "SGST {rate}%")],
    "B": [("Central GST @ {rate}%", "State GST @ {rate}%")],
}

# ---------------------------------------------------------------------------
# Date formats per country. Placeholders:
#   {d} day 3       {dd} day 03      {m} month 9     {mm} month 09
#   {yyyy} 2026     {yy} 26          {mon} Sep       {month} September
#   {month_de} September (German)    {suffix} st/nd/rd/th
# Day-first for GB, DE, JP and IN; month-first for US (Appendix M).
# ---------------------------------------------------------------------------
DATE_FORMATS = {
    "GB": {
        "A": ["{dd}/{mm}/{yyyy}", "{d} {month} {yyyy}", "{dd}-{mon}-{yyyy}"],
        "B": ["{d}/{m}/{yy}", "{d}{suffix} {month} {yyyy}", "{dd}.{mm}.{yyyy}", "{yyyy}-{mm}-{dd}"],
    },
    "US": {
        "A": ["{mm}/{dd}/{yyyy}", "{m}/{d}/{yy}", "{month} {d}, {yyyy}"],
        "B": ["{mon} {d} {yyyy}", "{mm}-{dd}-{yyyy}", "{mon}. {d}, {yyyy}"],
    },
    "DE": {
        "A": ["{dd}.{mm}.{yyyy}", "{yyyy}.{mm}.{dd}", "{d}. {month_de} {yyyy}"],
        "B": ["{d}.{m}.{yy}", "{dd}/{mm}/{yyyy}", "{yyyy}-{mm}-{dd}"],
    },
    "JP": {
        "A": ["{yyyy}.{mm}.{dd}", "{yyyy}年{m}月{d}日", "{yyyy}/{mm}/{dd}"],
        "B": ["{dd}.{mm}.{yyyy}", "{yyyy}-{mm}-{dd}", "{yyyy}年{mm}月{dd}日"],
    },
    "IN": {
        "A": ["{dd}/{mm}/{yyyy}", "{dd}-{mm}-{yyyy}", "{dd}-{mon}-{yyyy}"],
        "B": ["{d}/{m}/{yy}", "{dd}.{mm}.{yyyy}", "{d} {mon} {yyyy}"],
    },
}

MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]
MONTHS_DE = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli",
             "August", "September", "Oktober", "November", "Dezember"]

# ---------------------------------------------------------------------------
# Payment terms. {n} is the number of days.
# ---------------------------------------------------------------------------
TERM_DAYS = [7, 14, 15, 30, 45, 60]

TERMS = {
    "A": ["Net {n}", "{n} days", "Due in {n} days"],
    "B": ["Payment within {n} days", "{n} days net", "Net {n} days"],
}
LOCAL_TERMS = {
    "DE": {"A": ["Zahlbar innerhalb {n} Tagen"], "B": ["Zahlungsziel {n} Tage"]},
    "JP": {"A": ["支払条件 {n}日"], "B": ["{n}日以内にお支払いください"]},
}

# ---------------------------------------------------------------------------
# How numbers are printed.
#   en        1,234.56      en_plain  1234.56
#   de        1.234,56      de_space  1 234,56
#   jp        12,000 (no decimals, rule O5)
#   in_lakh   1,23,456.00 (Indian grouping)
# ---------------------------------------------------------------------------
AMOUNT_STYLES = {
    "GB": {"A": ["en"], "B": ["en_plain"]},
    "US": {"A": ["en"], "B": ["en_plain"]},
    "DE": {"A": ["de"], "B": ["de_space", "en"]},
    "JP": {"A": ["jp"], "B": ["jp"]},
    "IN": {"A": ["en"], "B": ["in_lakh"]},
}

# ---------------------------------------------------------------------------
# How the currency is shown next to the total.
# "none" prints no currency at all, which tests rule O3.
# ---------------------------------------------------------------------------
CURRENCY_SYMBOLS = {"GBP": "£", "USD": "$", "EUR": "€", "JPY": "¥", "INR": "Rs."}
CURRENCY_ALT_SYMBOLS = {"GBP": "GBP £", "USD": "US$", "EUR": "EUR", "JPY": "円", "INR": "INR"}

CURRENCY_STYLES = {
    "A": ["symbol_before", "code_before", "none"],
    "B": ["code_after", "alt_symbol"],
}

# ---------------------------------------------------------------------------
# Documents that are NOT invoices (rule O4): (printed title, kind).
# Expected output: every field null, vendor as found, a warning naming the kind.
# ---------------------------------------------------------------------------
NON_INVOICE_TITLES = {
    "A": [("QUOTATION", "quotation"), ("Delivery Note", "delivery note"),
          ("Statement of Account", "statement")],
    "B": [("Quote", "quotation"), ("Lieferschein", "delivery note"),
          ("Angebot", "quotation"), ("見積書", "quotation"), ("Account Statement", "statement")],
}

# ---------------------------------------------------------------------------
# Extra real-world anomalies (second version of the generator).
# These appear in BOTH groups. Groups A and B differ in wording and layout,
# not in which anomalies they contain.
# ---------------------------------------------------------------------------

# "2/10 Net 30" means a 2% discount if paid in 10 days; the due date is still +30.
EXTRA_TERMS = {
    "A": ["2/10 Net {n}"],
    "B": ["1% 10 days, net {n}"],
}

# Dates with the weekday in front. {wday} is Mon, Tue, ...
EXTRA_DATE_FORMATS = {
    "GB": {"A": ["{wday}, {d} {mon} {yyyy}"], "B": ["{wday} {dd}/{mm}/{yyyy}"]},
    "US": {"A": ["{wday}, {mon} {d}, {yyyy}"], "B": ["{wday} {mm}/{dd}/{yy}"]},
    "IN": {"A": ["{wday}, {dd}-{mon}-{yyyy}"], "B": ["{wday} {dd}/{mm}/{yyyy}"]},
}

# Tax lines on zero-rated or exempt invoices. The correct tax is 0.00.
ZERO_TAX_LABELS = {
    "GB": ["VAT 0% (reverse charge)", "Zero-rated VAT"],
    "US": ["Sales tax (exempt)", "Tax 0%"],
    "DE": ["USt. 0% (Reverse Charge)", "Steuerfrei"],
    "JP": ["消費税 0%", "Tax exempt"],
    "IN": ["IGST 0% (export under LUT)", "GST exempt"],
}

# Footer lines full of numbers that are NOT amounts or invoice numbers.
PHONE_LINES = {
    "GB": "Tel +44 117 496 0123",
    "US": "Phone (937) 555-0142",
    "DE": "Tel. +49 40 1234567",
    "JP": "TEL 03-1234-5678",
    "IN": "Ph: +91 20 2712 3456",
}
BANK_LINES = {
    "GB": ["Bank: Barclays  Sort code 20-45-77  Account 43127788",
           "IBAN GB29 NWBK 6016 1331 9268 19"],
    "US": ["Bank: Chase  Routing 021000021  Account 483920175"],
    "DE": ["IBAN DE89 3704 0044 0532 0130 00  BIC COBADEFFXXX"],
    "JP": ["Mizuho Bank, Shiba Branch 123, Account 1234567"],
    "IN": ["HDFC Bank  A/c 50100234567812  IFSC HDFC0001234"],
}

WATERMARKS = ["PAID", "COPY", "ORIGINAL", "DUPLICATE"]

SHIP_TO_LABELS = ["Ship to:", "Deliver to:", "Delivery address:"]
SHIP_TO_ADDRESS = "Bruviti Services Pvt Ltd, Plot 14, Hinjewadi Phase 2, Pune 411057"

CURRENCY_WORDS = {"INR": "Rupees", "GBP": "Pounds", "USD": "US Dollars", "EUR": "Euros"}