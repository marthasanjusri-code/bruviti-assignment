"""Find the invoice currency as an ISO 4217 code."""

import re
from collections import Counter

from app import labels
from app.models import Found

CODE = re.compile(r"(?<![A-Z])(GBP|USD|EUR|JPY|INR)(?![A-Z])")
SYMBOLS = [("US$", "USD"), ("£", "GBP"), ("€", "EUR"), ("¥", "JPY"), ("円", "JPY"),
           ("₹", "INR"), ("$", "USD")]
RUPEES = re.compile(r"(?<![A-Za-z])Rs\.?(?=[\s\d])")
WORDS = {"rupees": "INR", "pounds": "GBP", "dollars": "USD", "euros": "EUR",
         "euro": "EUR", "yen": "JPY"}
BANK_WORDS = ["iban", "account", "bank", "routing", "ifsc", "a/c", "sort code"]


def currencies_in(text: str) -> list:
    found = [m.group(1) for m in CODE.finditer(text.upper())]
    found += [code for symbol, code in SYMBOLS if symbol in text]
    if RUPEES.search(text):
        found.append("INR")
    return found


def find_currency(lines: list, total_line, vendor_currency: str | None) -> Found:
    warnings = []
    usable = [l for l in lines if not labels.has_any(labels.normalise(l.text), BANK_WORDS)]

    everywhere = Counter(code for line in usable for code in currencies_in(line.text))
    if len(everywhere) > 1:
        warnings.append(f"More than one currency on the invoice: {', '.join(sorted(everywhere))}.")

    near_total = currencies_in(total_line.text) if total_line else []
    if near_total:
        code, conf, source = Counter(near_total).most_common(1)[0][0], 0.95, "next to total"
    elif everywhere:
        code, conf, source = everywhere.most_common(1)[0][0], 0.85, "printed on invoice"
    else:
        words = [WORDS[w] for line in usable for w in labels.normalise(line.text).split() if w in WORDS]
        if words:
            code, conf, source = Counter(words).most_common(1)[0][0], 0.75, "amount in words"
        elif vendor_currency:
            code, conf, source = vendor_currency, 0.6, "vendor default"
            warnings.append(f"No currency printed; used vendor currency {vendor_currency}.")
        else:
            return Found(None, 0.0, "not found", warnings + ["No currency found."])

    if vendor_currency and code != vendor_currency:
        warnings.append(f"Currency {code} differs from the vendor's usual {vendor_currency}.")
    return Found(code, conf, source, warnings)