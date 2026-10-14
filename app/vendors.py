"""Match the printed vendor name to the six canonical vendors in Appendix M.

Names are printed inconsistently (upper case, with or without Ltd/Inc/GmbH/KK,
British or American spelling, typos), so we normalise and fuzzy-match.
"""

import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher

from app.models import Found

# Appendix M: canonical name -> (country, currency).
VENDORS = {
    "Northwind Traders": ("GB", "GBP"),
    "Blue Harbour Logistics": ("GB", "GBP"),
    "Kestrel Components": ("US", "USD"),
    "Meridian Industrial": ("DE", "EUR"),
    "Sakura Precision": ("JP", "JPY"),
    "Pinecrest Packaging": ("IN", "INR"),
}

# For vendors not in Appendix M, guess the country from the currency.
CURRENCY_COUNTRY = {"GBP": "GB", "USD": "US", "EUR": "DE", "JPY": "JP", "INR": "IN"}

# Words that vary between printings of the same name and carry no identity.
SUFFIXES = {"LTD", "LIMITED", "INC", "INCORPORATED", "GMBH", "KK", "CO", "COMPANY",
            "PVT", "PRIVATE", "P", "LLC", "PLC", "CORP", "CORPORATION",
            "KABUSHIKI", "KAISHA"}

# Text about the buyer, never the vendor. Checked per segment, so a vendor name
# sharing a line with other text is not skipped. "DELIVER" was too broad: it also
# matched "Delivery Note" titles (found in group A failures).
BUYER_WORDS = ("BRUVITI", "BILL TO", "SOLD TO", "SHIP TO", "DELIVER TO",
               "DELIVERY ADDRESS", "INVOICE TO", "CUSTOMER")

MATCH_THRESHOLD = 0.82   # below this, the vendor is "unknown"
TOP_LINES = 15           # the vendor name is near the top of page 1


@dataclass
class VendorResult:
    found: Found
    country: str | None    # None when the vendor is unknown
    currency: str | None
    printed: str           # the text that matched best


def normalise(text: str) -> list:
    """'Sakura Precision Co., Ltd.' -> ['SAKURA', 'PRECISION']"""
    text = unicodedata.normalize("NFKC", text).upper().replace(".", "")
    text = re.sub(r"[^A-Z0-9 ]+", " ", text)
    return [word for word in text.split() if word not in SUFFIXES]


CANONICAL_TOKENS = {name: normalise(name) for name in VENDORS}


def similarity(tokens: list, target: list) -> float:
    """Compare without spaces, so 'PINE CREST' matches 'PINECREST'."""
    a, b = "".join(tokens), "".join(target)
    return SequenceMatcher(None, a, b).ratio() if a and b else 0.0


def best_score(text: str, target: list) -> float:
    """Best similarity of the whole text, or of any run of words inside it."""
    tokens = normalise(text)
    best = similarity(tokens, target)
    for size in (len(target), len(target) + 1):
        for start in range(0, len(tokens) - size + 1):
            best = max(best, similarity(tokens[start:start + size], target))
    return best


def find_vendor(lines: list) -> VendorResult:
    best_value, best_name, best_text = 0.0, None, ""
    top_lines = [line for line in lines if line.page == 1][:TOP_LINES]

    for line in top_lines:
        for segment in line.segments:
            if any(word in segment.upper() for word in BUYER_WORDS):
                continue
            for part in segment.split("|"):
                for name, target in CANONICAL_TOKENS.items():
                    score = best_score(part, target)
                    if score > best_value:
                        best_value, best_name, best_text = score, name, part.strip()

    if best_name and best_value >= MATCH_THRESHOLD:
        country, currency = VENDORS[best_name]
        if best_value >= 0.97:
            confidence, warnings = 0.98, []
        elif best_value >= 0.90:
            confidence, warnings = 0.9, []
        else:
            confidence = 0.8
            warnings = [f"Vendor '{best_text}' matched to {best_name} "
                        f"(similarity {best_value:.2f})."]
        found = Found(best_name, confidence, f"name match {best_value:.2f}", warnings)
        return VendorResult(found, country, currency, best_text)

    found = Found("unknown", 0.2, "no match", ["Vendor name not in the canonical list."])
    return VendorResult(found, None, None, best_text)