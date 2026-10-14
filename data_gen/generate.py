"""Generate synthetic invoice PDFs, each with a JSON file of correct answers.

Usage (from the project folder):
    python -m data_gen.generate --group A --count 300
    python -m data_gen.generate --group B --count 300

Group A uses layouts and wording for building the extractor.
Group B uses held-out layouts and wording, only for measuring it.
Both groups contain the same kinds of real-world anomalies.
"""

import argparse
import json
import random
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfgen import canvas

from data_gen import vocab

# Fonts. Helvetica covers English and German (including the € and £ signs).
# Japanese text needs a CJK font; reportlab has this one built in.
pdfmetrics.registerFont(UnicodeCIDFont("HeiseiKakuGo-W5"))
LATIN, LATIN_BOLD, CJK = "Helvetica", "Helvetica-Bold", "HeiseiKakuGo-W5"

# Page positions in points. An A4 page is 595 wide and 842 tall.
LEFT, RIGHT, TOP, BOTTOM = 50, 545, 790, 70
CENTER = (LEFT + RIGHT) / 2

LAYOUTS = {"A": ["classic", "grid"], "B": ["side", "compact"]}

# (name, weight): higher weight means more common.
SCENARIOS = [("normal", 76), ("mismatch", 6), ("unknown_vendor", 10), ("non_invoice", 8)]
DUE_MODES = [("due_only", 30), ("terms_only", 30), ("both_agree", 15),
             ("both_disagree", 10), ("neither", 15)]

# Chance of each extra real-world anomaly on one invoice.
CHANCES = {
    "footer": 0.60,               # phone and bank details full of numbers
    "ship_to": 0.30,              # a second address block with a postcode
    "label_noise": 0.30,          # INVOICE NO / no colon / "Total ....."
    "currency_everywhere": 0.20,  # currency on every amount, not just the total
    "watermark": 0.12,            # big rotated PAID / COPY stamp
    "multi_page": 0.08,           # many items, totals on page 2
    "zero_tax": 0.05,             # exempt or reverse charge, tax 0.00
    "round_off_india": 0.40,      # INR total rounded to whole rupees
    "words_india": 0.50,          # "Amount in words" line on Indian invoices
    "words_other": 0.10,          # ... and on other invoices
    "fullwidth_japan": 0.30,      # full-width digits on Japanese invoices
}

UNKNOWN_ADDRESSES = {
    "IN": "12 MG Road, Bengaluru 560001, India",
    "GB": "3 Mill Lane, Leeds LS1 4AB, United Kingdom",
    "US": "45 Main Street, Austin TX 78701, USA",
    "DE": "Industriestrasse 5, 70565 Stuttgart, Deutschland",
}
GENERIC_ITEMS = [("Office chairs", 85.00), ("Printer toner", 42.50),
                 ("A4 paper (box)", 18.00), ("Desk lamp", 24.90),
                 ("Installation service", 120.00)]

CENT = Decimal("0.01")
YEN = Decimal("1")
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
FULLWIDTH_DIGITS = str.maketrans("0123456789", "０１２３４５６７８９")
ONES = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine",
        "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen",
        "Seventeen", "Eighteen", "Nineteen"]
TENS = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]


@dataclass
class Invoice:
    group: str
    scenario: str
    layout: str
    kind: str                 # "invoice", or e.g. "quotation"
    title: str
    canonical: str            # Appendix M name, or "unknown"
    printed_name: str
    country: str
    currency: str
    address: str
    tax_id: str
    number: str
    invoice_date: date
    date_format: str
    due_mode: str
    due_printed: date | None
    show_terms: bool
    terms_text: str
    due_expected: date | None
    items: list               # (description, qty, unit price, amount)
    subtotal: Decimal
    tax_lines: list           # (label, amount)
    tax: Decimal
    total: Decimal
    amount_style: str
    currency_style: str
    labels: dict
    decoys: list              # (label, value) pairs that are NOT answers
    extra_total_lines: list = field(default_factory=list)  # e.g. Round Off
    anomalies: list = field(default_factory=list)
    ship_to: str = ""
    footer: list = field(default_factory=list)
    watermark: str = ""
    words: str = ""
    currency_everywhere: bool = False
    fullwidth: bool = False


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def weighted(rng, options):
    """Pick one name from (name, weight) pairs."""
    names = [name for name, _ in options]
    weights = [weight for _, weight in options]
    return rng.choices(names, weights=weights, k=1)[0]


def pick_label(rng, group, country, field_name):
    """Pick a label, sometimes in the vendor's local language."""
    english = vocab.LABELS[field_name][group]
    local = vocab.LOCAL_LABELS.get(country, {}).get(field_name, {}).get(group, [])
    if local and rng.random() < 0.5:
        return rng.choice(local)
    return rng.choice(english)


def noisy_label(label: str, style: str) -> str:
    if style == "upper":
        return label.upper()
    if style == "no_colon":
        return label.rstrip(":").rstrip()
    if style == "dots":
        return label.rstrip(":").rstrip() + " ....."
    return label


def ordinal_suffix(day):
    if 11 <= day <= 13:
        return "th"
    return {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")


def format_date(value: date, pattern: str) -> str:
    return pattern.format(
        d=value.day, dd=f"{value.day:02d}", m=value.month, mm=f"{value.month:02d}",
        yyyy=value.year, yy=f"{value.year % 100:02d}",
        mon=vocab.MONTHS[value.month - 1][:3], month=vocab.MONTHS[value.month - 1],
        month_de=vocab.MONTHS_DE[value.month - 1], suffix=ordinal_suffix(value.day),
        wday=WEEKDAYS[value.weekday()],
    )


def group_thousands(digits: str, separator: str) -> str:
    """'1234567' -> '1,234,567' (with the given separator)."""
    parts = []
    while len(digits) > 3:
        parts.insert(0, digits[-3:])
        digits = digits[:-3]
    parts.insert(0, digits)
    return separator.join(parts)


def group_lakh(digits: str) -> str:
    """Indian grouping: '123456' -> '1,23,456'."""
    if len(digits) <= 3:
        return digits
    head, tail = digits[:-3], digits[-3:]
    parts = []
    while len(head) > 2:
        parts.insert(0, head[-2:])
        head = head[:-2]
    if head:
        parts.insert(0, head)
    return ",".join(parts + [tail])


def format_amount(value: Decimal, style: str) -> str:
    sign = "-" if value < 0 else ""
    value = abs(value)
    if style == "jp":
        return sign + group_thousands(str(int(value)), ",")
    whole, cents = f"{value:.2f}".split(".")
    if style == "en":
        text = group_thousands(whole, ",") + "." + cents
    elif style == "en_plain":
        text = whole + "." + cents
    elif style == "de":
        text = group_thousands(whole, ".") + "," + cents
    elif style == "de_space":
        text = group_thousands(whole, " ") + "," + cents
    elif style == "in_lakh":
        text = group_lakh(whole) + "." + cents
    else:
        raise ValueError(f"Unknown amount style: {style}")
    return sign + text


def words_below_thousand(n: int) -> str:
    parts = []
    if n >= 100:
        parts.append(ONES[n // 100] + " Hundred")
        n %= 100
    if n >= 20:
        parts.append(TENS[n // 10] + ("-" + ONES[n % 10] if n % 10 else ""))
        n = 0
    if n:
        parts.append(ONES[n])
    return " ".join(parts)


def number_to_words(n: int) -> str:
    if n == 0:
        return "Zero"
    parts = []
    for size, name in ((1_000_000, "Million"), (1_000, "Thousand"), (1, "")):
        if n >= size:
            chunk, n = divmod(n, size)
            parts.append((words_below_thousand(chunk) + " " + name).strip())
    return " ".join(parts)


def amount_in_words(total: Decimal, currency: str) -> str:
    whole = int(total)
    cents = int((total - whole) * 100)
    text = f"Amount in words: {vocab.CURRENCY_WORDS[currency]} {number_to_words(whole)}"
    if cents:
        text += f" and {cents:02d}/100"
    return text + " Only"


def make_invoice_number(rng, canonical):
    n = rng.randint(1, 9999)
    patterns = {
        "Northwind Traders": f"NW-{n:04d}",
        "Blue Harbour Logistics": f"BHL/2026/{n:04d}",
        "Kestrel Components": f"KC-{n:04d}",
        "Meridian Industrial": f"RE-2026-{n:05d}",
        "Sakura Precision": f"SP{n:06d}",
        "Pinecrest Packaging": f"PP/26-27/{n:04d}",
    }
    return patterns.get(canonical, str(rng.randint(1000, 99999)))


# ---------------------------------------------------------------------------
# Step 1: decide everything about one invoice
# ---------------------------------------------------------------------------

def build_invoice(rng, group) -> Invoice:
    scenario = weighted(rng, SCENARIOS)
    anomalies = []

    def chance(name, key=None):
        """Roll for an anomaly, and remember it if it happens."""
        hit = rng.random() < CHANCES[key or name]
        if hit:
            anomalies.append(name)
        return hit

    if scenario == "unknown_vendor":
        printed_name, country, currency = rng.choice(vocab.UNKNOWN_VENDORS[group])
        canonical, address, tax_id = "unknown", UNKNOWN_ADDRESSES[country], ""
        catalogue = GENERIC_ITEMS
    else:
        canonical = rng.choice(sorted(vocab.VENDORS))
        info = vocab.VENDORS[canonical]
        printed_name = rng.choice(info["names"][group])
        country, currency = info["country"], info["currency"]
        address, tax_id, catalogue = info["address"], info["tax_id"], info["items"]

    kind, title = "invoice", pick_label(rng, group, country, "title")
    if scenario == "non_invoice":
        title, kind = rng.choice(vocab.NON_INVOICE_TITLES[group])

    # Amounts. Decimal avoids float rounding errors like 0.1 + 0.2.
    unit = YEN if currency == "JPY" else CENT

    def money(value):
        return Decimal(value).quantize(unit, rounding=ROUND_HALF_UP)

    if chance("multi_page"):
        chosen = rng.choices(catalogue, k=rng.randint(38, 46))
        picks = [(f"{description} - lot {n}", price)
                 for n, (description, price) in enumerate(chosen, start=1)]
    else:
        picks = rng.sample(catalogue, k=rng.randint(1, 4))
    items = []
    for description, price in picks:
        qty = rng.randint(1, 40)
        price = Decimal(str(price))
        items.append((description, qty, price, money(price * qty)))
    subtotal = sum((amount for *_, amount in items), Decimal("0"))

    rate = Decimal(str(rng.choice(vocab.TAX_RATES[country])))
    if chance("zero_tax"):
        tax_lines = [(rng.choice(vocab.ZERO_TAX_LABELS[country]), money(0))]
    elif country == "IN" and rng.random() < 0.5:
        half = rate / 2
        first, second = rng.choice(vocab.INDIA_SPLIT_TAX[group])
        part = money(subtotal * half / 100)
        tax_lines = [(first.format(rate=f"{half:g}"), part),
                     (second.format(rate=f"{half:g}"), part)]
    else:
        label = rng.choice(vocab.TAX_LABELS[country][group])
        tax_lines = [(label.format(rate=f"{rate:g}"), money(subtotal * rate / 100))]
    tax = sum((amount for _, amount in tax_lines), Decimal("0"))

    total = subtotal + tax
    extra_total_lines = []
    if scenario == "mismatch":
        total += Decimal("100") if currency == "JPY" else rng.choice(
            [Decimal("0.05"), Decimal("1.00"), Decimal("10.00")])
    elif currency == "INR" and chance("round_off", "round_off_india"):
        rounded = total.quantize(YEN, rounding=ROUND_HALF_UP)
        if rounded == total:
            anomalies.remove("round_off")
        else:
            extra_total_lines.append((rng.choice(["Round Off", "Rounding"]), rounded - total))
            total = rounded

    # Dates and payment terms.
    invoice_date = date(2026, 1, 1) + timedelta(days=rng.randint(0, 364))
    date_pool = (vocab.DATE_FORMATS[country][group]
                 + vocab.EXTRA_DATE_FORMATS.get(country, {}).get(group, []))
    date_format = rng.choice(date_pool)
    days = rng.choice(vocab.TERM_DAYS)
    local_terms = vocab.LOCAL_TERMS.get(country, {}).get(group, [])
    if local_terms and rng.random() < 0.5:
        terms_text = rng.choice(local_terms).format(n=days)
    else:
        terms_text = rng.choice(vocab.TERMS[group] + vocab.EXTRA_TERMS[group]).format(n=days)

    due_mode = weighted(rng, DUE_MODES)
    from_terms = invoice_date + timedelta(days=days)
    due_printed, show_terms, due_expected = None, False, None
    if due_mode == "due_only":
        due_printed = due_expected = from_terms
    elif due_mode == "terms_only":
        show_terms, due_expected = True, from_terms
    elif due_mode == "both_agree":
        due_printed, show_terms, due_expected = from_terms, True, from_terms
    elif due_mode == "both_disagree":
        due_printed = from_terms + timedelta(days=rng.choice([1, 2, 5, 10]))
        show_terms, due_expected = True, due_printed  # rule O1: printed date wins

    # Decoys: numbers and dates that look like answers but are not.
    decoys = []
    if rng.random() < 0.4:
        decoys.append((rng.choice(["PO No:", "Order No.", "Customer PO:"]),
                       f"PO-{rng.randint(10000, 99999)}"))
    if rng.random() < 0.3:
        decoys.append((rng.choice(["Customer No:", "Account:"]), f"C-{rng.randint(100, 9999)}"))
    if rng.random() < 0.25:
        order_date = invoice_date - timedelta(days=rng.randint(3, 20))
        decoys.append(("Order Date:", format_date(order_date, date_format)))

    currency_style = rng.choice(vocab.CURRENCY_STYLES[group])
    if canonical == "unknown" and currency_style == "none":
        currency_style = "code_before"  # no vendor table to fall back on

    labels = {
        "number": pick_label(rng, group, country, "invoice_number"),
        "date": pick_label(rng, group, country, "invoice_date"),
        "due": pick_label(rng, group, country, "due_date"),
        "terms": rng.choice(vocab.LABELS["terms"][group]),
        "subtotal": pick_label(rng, group, country, "subtotal"),
        "total": pick_label(rng, group, country, "total"),
        "bill_to": rng.choice(vocab.LABELS["bill_to"][group]),
    }
    if chance("label_noise"):
        style = rng.choice(["upper", "no_colon", "dots"])
        anomalies[-1] = f"label_noise_{style}"
        for key in ("number", "date", "due", "subtotal", "total"):
            labels[key] = noisy_label(labels[key], style)

    ship_to = ""
    if chance("ship_to"):
        ship_to = f"{rng.choice(vocab.SHIP_TO_LABELS)} {vocab.SHIP_TO_ADDRESS}"
    footer = []
    if chance("footer"):
        footer = [vocab.PHONE_LINES[country], rng.choice(vocab.BANK_LINES[country])]
    watermark = rng.choice(vocab.WATERMARKS) if chance("watermark") else ""
    currency_everywhere = currency_style != "none" and chance("currency_everywhere")
    words_key = "words_india" if country == "IN" else "words_other"
    words = ""
    if currency != "JPY" and chance("amount_in_words", words_key):
        words = amount_in_words(total, currency)
    fullwidth = country == "JP" and chance("fullwidth_digits", "fullwidth_japan")

    return Invoice(
        group=group, scenario=scenario, layout=rng.choice(LAYOUTS[group]),
        kind=kind, title=title, canonical=canonical, printed_name=printed_name,
        country=country, currency=currency, address=address, tax_id=tax_id,
        number=make_invoice_number(rng, canonical), invoice_date=invoice_date,
        date_format=date_format, due_mode=due_mode, due_printed=due_printed,
        show_terms=show_terms, terms_text=terms_text, due_expected=due_expected,
        items=items, subtotal=subtotal, tax_lines=tax_lines, tax=tax, total=total,
        amount_style=rng.choice(vocab.AMOUNT_STYLES[country][group]),
        currency_style=currency_style, labels=labels, decoys=decoys,
        extra_total_lines=extra_total_lines, anomalies=anomalies, ship_to=ship_to,
        footer=footer, watermark=watermark, words=words,
        currency_everywhere=currency_everywhere, fullwidth=fullwidth,
    )


# ---------------------------------------------------------------------------
# Step 2: the correct answer, following the brief's rules
# ---------------------------------------------------------------------------

def expected_output(inv: Invoice) -> dict:
    meta = {
        "group": inv.group, "scenario": inv.scenario, "layout": inv.layout,
        "kind": inv.kind, "printed_name": inv.printed_name, "country": inv.country,
        "date_format": inv.date_format, "due_mode": inv.due_mode,
        "amount_style": inv.amount_style, "currency_style": inv.currency_style,
        "labels": inv.labels, "anomalies": inv.anomalies,
    }
    if inv.kind != "invoice":  # rule O4
        fields = {name: None for name in
                  ["invoice_number", "invoice_date", "due_date", "currency",
                   "subtotal", "tax", "total"]}
        return {"vendor": inv.canonical, **fields, "meta": meta}
    return {
        "vendor": inv.canonical,
        "invoice_number": inv.number,
        "invoice_date": inv.invoice_date.isoformat(),
        "due_date": inv.due_expected.isoformat() if inv.due_expected else None,
        "currency": inv.currency,
        "subtotal": float(inv.subtotal),
        "tax": float(inv.tax),
        "total": float(inv.total),  # printed value, even if wrong (rule O2)
        "meta": meta,
    }


# ---------------------------------------------------------------------------
# Step 3: draw the PDF
# ---------------------------------------------------------------------------

class Writer:
    """A thin wrapper around reportlab's canvas."""

    def __init__(self, path: Path, cjk: bool, page_numbers: bool):
        # invariant=1 makes the same input give the same PDF bytes.
        self.canvas = canvas.Canvas(str(path), pagesize=A4, invariant=1)
        self.regular = CJK if cjk else LATIN
        self.bold = CJK if cjk else LATIN_BOLD
        self.page = 1
        self.page_numbers = page_numbers

    def text(self, x, y, value, size=10, bold=False, align="left"):
        self.canvas.setFont(self.bold if bold else self.regular, size)
        if align == "right":
            self.canvas.drawRightString(x, y, value)
        elif align == "center":
            self.canvas.drawCentredString(x, y, value)
        else:
            self.canvas.drawString(x, y, value)

    def rule(self, y):
        self.canvas.line(LEFT, y, RIGHT, y)

    def watermark(self, word):
        c = self.canvas
        c.saveState()
        c.setFillGray(0.85)
        c.setFont(LATIN_BOLD, 80)
        c.translate(CENTER, 420)
        c.rotate(35)
        c.drawCentredString(0, 0, word)
        c.restoreState()

    def _page_number(self):
        if self.page_numbers:
            self.text(RIGHT, 30, f"Page {self.page}", 8, align="right")

    def new_page(self):
        self._page_number()
        self.canvas.showPage()
        self.page += 1

    def save(self):
        self._page_number()
        self.canvas.showPage()
        self.canvas.save()


def fullwidth(inv: Invoice, text: str) -> str:
    return text.translate(FULLWIDTH_DIGITS) if inv.fullwidth else text


def with_currency(inv: Invoice, value: str) -> str:
    style, code = inv.currency_style, inv.currency
    if style == "symbol_before":
        symbol = vocab.CURRENCY_SYMBOLS[code]
        return f"{symbol} {value}" if symbol.endswith(".") else f"{symbol}{value}"
    if style == "code_before":
        return f"{code} {value}"
    if style == "code_after":
        return f"{value} {code}"
    if style == "alt_symbol":
        alt = vocab.CURRENCY_ALT_SYMBOLS[code]
        return f"{value}{alt}" if alt == "円" else f"{alt} {value}"
    return value  # "none": no currency printed (rule O3)


def amount_text(inv: Invoice, value: Decimal, currency=False) -> str:
    text = fullwidth(inv, format_amount(value, inv.amount_style))
    return with_currency(inv, text) if currency else text


def date_text(inv: Invoice, value: date) -> str:
    return fullwidth(inv, format_date(value, inv.date_format))


def meta_pairs(inv: Invoice) -> list:
    pairs = [(inv.labels["number"], inv.number),
             (inv.labels["date"], date_text(inv, inv.invoice_date))]
    if inv.due_printed:
        pairs.append((inv.labels["due"], date_text(inv, inv.due_printed)))
    if inv.show_terms:
        pairs.append((inv.labels["terms"], inv.terms_text))
    return pairs + inv.decoys


def totals_pairs(inv: Invoice) -> list:
    every = inv.currency_everywhere
    pairs = [(inv.labels["subtotal"], amount_text(inv, inv.subtotal, every))]
    pairs += [(label, amount_text(inv, amount, every)) for label, amount in inv.tax_lines]
    pairs += [(label, amount_text(inv, amount)) for label, amount in inv.extra_total_lines]
    pairs.append((inv.labels["total"], amount_text(inv, inv.total, currency=True)))
    return pairs


def buyer_lines(inv: Invoice) -> list:
    lines = [f"{inv.labels['bill_to']} {vocab.BUYER}"]
    if inv.ship_to:
        lines.append(inv.ship_to)
    return lines


def split_address(address: str) -> list:
    parts = address.split(", ")
    middle = (len(parts) + 1) // 2
    return [line for line in (", ".join(parts[:middle]), ", ".join(parts[middle:])) if line]


def draw_vendor_block(w: Writer, inv: Invoice, y: float) -> float:
    w.text(LEFT, y, inv.printed_name, 14, bold=True)
    w.text(LEFT, y - 15, inv.address, 9)
    if inv.tax_id:
        w.text(LEFT, y - 28, inv.tax_id, 9)
    return y - 50


def draw_items(w: Writer, inv: Invoice, y: float, compact=False) -> float:
    def header(y):
        if compact:
            w.text(LEFT, y, "Particulars", 10, bold=True)
            w.text(RIGHT, y, "Total", 10, bold=True, align="right")
        else:
            w.text(LEFT, y, "Item", 10, bold=True)
            w.text(330, y, "Qty", 10, bold=True, align="right")
            w.text(430, y, "Unit Price", 10, bold=True, align="right")
            w.text(RIGHT, y, "Amount", 10, bold=True, align="right")
        return y - 16

    y = header(y)
    for description, qty, price, amount in inv.items:
        if y < BOTTOM + 40:  # page full: continue on a new page
            w.new_page()
            y = header(TOP)
        if compact:
            w.text(LEFT, y, f"{description} (x{qty})", 10)
            w.text(RIGHT, y, amount_text(inv, amount), 10, align="right")
        else:
            w.text(LEFT, y, description, 10)
            w.text(330, y, str(qty), 10, align="right")
            w.text(430, y, amount_text(inv, price), 10, align="right")
            w.text(RIGHT, y, amount_text(inv, amount), 10, align="right")
        y -= 14
    w.rule(y + 6)
    return y - 14


def draw_totals(w: Writer, inv: Invoice, y: float, label_x: float) -> float:
    pairs = totals_pairs(inv)
    if y - 15 * len(pairs) < BOTTOM + 20:  # not enough room: totals go on a new page
        w.new_page()
        y = TOP
    for index, (label, value) in enumerate(pairs):
        is_total = index == len(pairs) - 1
        w.text(label_x, y, label, 10, bold=is_total)
        w.text(RIGHT, y, value, 10, bold=is_total, align="right")
        y -= 15
    return y


def layout_classic(w: Writer, inv: Invoice, rng) -> float:
    w.text(RIGHT, TOP, inv.title, 16, bold=True, align="right")
    y = draw_vendor_block(w, inv, TOP)
    for label, value in meta_pairs(inv):
        w.text(LEFT, y, f"{label} {value}", 10)
        y -= 14
    y -= 10
    for line in buyer_lines(inv):
        w.text(LEFT, y, line, 10)
        y -= 14
    y = draw_items(w, inv, y - 16)
    return draw_totals(w, inv, y - 6, label_x=360)


def layout_grid(w: Writer, inv: Invoice, rng) -> float:
    w.text(LEFT, TOP, inv.title, 18, bold=True)
    y = draw_vendor_block(w, inv, TOP - 30)
    pairs = meta_pairs(inv)
    columns = [LEFT, 180, 310, 440]
    for start in range(0, len(pairs), 4):
        for x, (label, value) in zip(columns, pairs[start:start + 4]):
            w.text(x, y, label.rstrip(":"), 8, bold=True)
            w.text(x, y - 13, value, 10)
        y -= 34
    w.text(LEFT, y, inv.labels["bill_to"].rstrip(":"), 8, bold=True)
    w.text(LEFT, y - 13, vocab.BUYER, 10)
    y -= 26
    if inv.ship_to:
        w.text(LEFT, y, inv.ship_to, 9)
        y -= 14
    y = draw_items(w, inv, y - 20)
    return draw_totals(w, inv, y - 6, label_x=300)


def layout_side(w: Writer, inv: Invoice, rng) -> float:
    w.text(CENTER, TOP, inv.title, 18, bold=True, align="center")
    y = TOP - 35
    left = [inv.printed_name] + split_address(inv.address) + ([inv.tax_id] if inv.tax_id else [])
    right = meta_pairs(inv)
    for row in range(max(len(left), len(right))):
        if row < len(left):
            w.text(LEFT, y, left[row], 12 if row == 0 else 9, bold=(row == 0))
        if row < len(right):
            label, value = right[row]
            w.text(330, y, label, 10)
            w.text(RIGHT, y, value, 10, align="right")
        y -= 15
    y -= 15
    for line in buyer_lines(inv):
        w.text(LEFT, y, line, 10)
        y -= 14
    y = draw_items(w, inv, y - 16)
    return draw_totals(w, inv, y - 6, label_x=330)


def layout_compact(w: Writer, inv: Invoice, rng) -> float:
    y = TOP
    w.text(LEFT, y, f"{inv.printed_name} | {inv.address}", 9)
    y -= 30
    if inv.kind != "invoice" or rng.random() < 0.5:  # real invoices sometimes have no title
        w.text(LEFT, y, inv.title, 12, bold=True)
        y -= 20
    pairs = meta_pairs(inv)
    for start in range(0, len(pairs), 2):
        line = "    ".join(f"{label} {value}" for label, value in pairs[start:start + 2])
        w.text(LEFT, y, line, 10)
        y -= 15
    y -= 5
    for line in buyer_lines(inv):
        w.text(LEFT, y, line, 10)
        y -= 14
    y = draw_items(w, inv, y - 16, compact=True)
    return draw_totals(w, inv, y - 6, label_x=330)


LAYOUT_FUNCTIONS = {"classic": layout_classic, "grid": layout_grid,
                    "side": layout_side, "compact": layout_compact}


def needs_cjk(inv: Invoice) -> bool:
    texts = [inv.title, inv.terms_text, *inv.labels.values()]
    return inv.country == "JP" or any("\u3000" <= ch <= "\u9fff" for t in texts for ch in t)


def render(inv: Invoice, path: Path, rng) -> None:
    w = Writer(path, cjk=needs_cjk(inv), page_numbers=bool(inv.footer) or len(inv.items) > 20)
    if inv.watermark:
        w.watermark(inv.watermark)
    y = LAYOUT_FUNCTIONS[inv.layout](w, inv, rng)
    if inv.words:
        w.text(LEFT, y - 10, inv.words, 9)
    for offset, line in enumerate(inv.footer):
        w.text(LEFT, BOTTOM - 12 * offset, line, 8)
    w.save()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic invoice PDFs.")
    parser.add_argument("--group", choices=["A", "B"], required=True)
    parser.add_argument("--count", type=int, default=300)
    parser.add_argument("--seed", type=int, default=None,
                        help="Random seed. Defaults to 1 for group A and 2 for group B.")
    parser.add_argument("--out", default=None, help="Output folder.")
    args = parser.parse_args()

    seed = args.seed if args.seed is not None else (1 if args.group == "A" else 2)
    rng = random.Random(seed)
    out_dir = Path(args.out or f"data_gen/output/{args.group}")
    out_dir.mkdir(parents=True, exist_ok=True)

    counts = Counter()
    for index in range(1, args.count + 1):
        inv = build_invoice(rng, args.group)
        stem = f"{args.group}_{index:04d}"
        render(inv, out_dir / f"{stem}.pdf", rng)
        (out_dir / f"{stem}.json").write_text(
            json.dumps(expected_output(inv), indent=2, ensure_ascii=False), encoding="utf-8")

        counts.update([
            f"scenario: {inv.scenario}",
            f"due mode: {inv.due_mode}",
            f"layout: {inv.layout}",
            f"country: {inv.country}",
            f"currency style: {inv.currency_style}",
            f"amount style: {inv.amount_style}",
        ])
        counts.update(f"anomaly: {name}" for name in inv.anomalies)
        if inv.decoys:
            counts["has decoys (PO / customer no. / order date)"] += 1

    print(f"Wrote {args.count} invoices to {out_dir}\n")
    for key in sorted(counts):
        print(f"  {key:<48}{counts[key]:>5}")


if __name__ == "__main__":
    main()