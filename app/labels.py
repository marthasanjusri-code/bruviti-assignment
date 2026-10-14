"""Label keywords the extractor looks for, and helpers to match them.

Written from group A wording plus general knowledge of invoices.
KEEP B HONEST: nothing here is copied from group B in data_gen/vocab.py.

All keywords are lower case without punctuation. Latin keywords must match
whole words ("tax" does not match "taxable"); CJK keywords match anywhere.
A keyword starting with "*" may also be the end of a longer word, for German
compound words ("*steuer" matches "umsatzsteuer").
"""

import re
import unicodedata

# --- Header fields ----------------------------------------------------------
INVOICE_NUMBER = ["invoice no", "invoice number", "invoice #", "inv no", "reference #",
                  "reference no", "ref no", "rechnungsnummer", "rechnung nr", "請求書番号"]
INVOICE_DATE = ["invoice date", "issue date", "dated", "date", "rechnungsdatum", "datum",
                "請求日", "発行日"]
DUE_DATE = ["due date", "payment due", "due", "fällig am", "zahlbar bis", "支払期限", "お支払期限"]
TERMS = ["payment terms", "terms"]

# Lines with these words hold numbers or dates that are NOT the answer.
NOT_INVOICE_NUMBER = ["po", "order", "customer", "account", "vat", "gst", "gstin", "tax",
                      "ein", "registration", "iban", "phone", "tel"]
NOT_INVOICE_DATE = ["order date", "delivery date", "ship date", "due"]

# --- Summary lines (subtotal, tax, total) -----------------------------------
SUBTOTAL = ["subtotal", "sub total", "net amount", "net", "zwischensumme", "nettobetrag",
            "netto", "小計"]
# "*steuer" added after measuring B: German compound words for tax.
TAX = ["vat", "tax", "gst", "cgst", "sgst", "igst", "mwst", "ust", "*steuer", "消費税"]
TOTAL = ["grand total", "amount due", "balance due", "total", "gesamtbetrag",
         "rechnungsbetrag", "合計", "ご請求金額"]
IGNORE_SUMMARY = ["round off", "rounding", "round", "discount", "paid", "in words"]

# Lines full of numbers that are never amounts.
NOT_AMOUNT_LINES = ["iban", "account", "a/c", "routing", "sort code", "ifsc", "bank",
                    "phone", "tel", "ph", "page"]

# Words in the header row of the item table.
TABLE_HEADER = ["item", "qty", "quantity", "description", "particulars", "unit price",
                "price", "amount", "rate", "total"]

DOTTED_ACRONYM = re.compile(r"\b(?:[A-Za-z]\.){2,}")


def normalise(text: str) -> str:
    """Lower case, plain characters, punctuation replaced by spaces.

    'INVOICE NO .....' -> 'invoice no'    'Sub-Total:' -> 'sub total'
    'V.A.T. @ 20%'     -> 'vat 20%'   (dotted acronyms joined; added after measuring B)
    """
    text = unicodedata.normalize("NFKC", text)
    text = DOTTED_ACRONYM.sub(lambda m: m.group().replace(".", ""), text)
    text = re.sub(r"[^\w#/%]+", " ", text.lower())
    return " ".join(text.split())


def keyword_position(text: str, keyword: str):
    """Where the keyword starts in normalised text, or None if it is absent."""
    if keyword.startswith("*"):  # may be the end of a longer (compound) word
        match = re.search(re.escape(keyword[1:]) + r"(?![a-z0-9])", text)
        return match.start() if match else None
    if keyword.isascii():
        match = re.search(r"(?<![a-z0-9])" + re.escape(keyword) + r"(?![a-z0-9])", text)
        return match.start() if match else None
    position = text.find(keyword)
    return position if position >= 0 else None


def has_any(text: str, keywords: list) -> bool:
    return any(keyword_position(text, k) is not None for k in keywords)


def first_role(text: str, roles: dict):
    """Which role's keyword appears earliest in the text.

    roles maps a role name to its keyword list. Ties go to the longer keyword,
    so 'sub total' beats 'total' in 'Sub total'.
    """
    best_key, best_role = None, None
    for role, keywords in roles.items():
        for keyword in keywords:
            position = keyword_position(text, keyword)
            if position is not None:
                key = (position, -len(keyword))
                if best_key is None or key < best_key:
                    best_key, best_role = key, role
    return best_role