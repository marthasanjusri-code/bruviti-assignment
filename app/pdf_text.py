"""Read a PDF's text layer into a clean list of lines.

Handles, before any other code sees the text:
  - multi-page PDFs (every page is read, up to MAX_PAGES)
  - watermarks such as PAID or COPY (rotated characters are dropped)
  - full-width digits and odd spaces (normalised to plain characters)
  - two columns printed on one line (wide gaps are kept as segments)
  - labels above their values (each segment keeps its x position)
"""

import io
import unicodedata
from dataclasses import dataclass, field

import pdfplumber

LINE_TOLERANCE = 3   # words whose tops differ by 3 points or less are on the same line
COLUMN_GAP = 15      # a gap wider than this (in points) separates two columns
GAP_MARK = "    "    # how a wide gap appears inside line text
MAX_PAGES = 20       # invoices are short; this keeps every request well under 1 second


@dataclass
class Line:
    text: str            # the whole line, with wide gaps shown as 4 spaces
    segments: list       # the line split at wide gaps
    starts: list         # left x position of each segment, same order as segments
    page: int            # page number, starting at 1
    top: float           # distance from the top of the page, in points
    x0: float            # left edge of the first word


@dataclass
class PdfText:
    lines: list = field(default_factory=list)
    page_count: int = 0
    char_count: int = 0
    skipped_pages: int = 0   # pages beyond MAX_PAGES that were not read

    @property
    def text(self) -> str:
        return "\n".join(line.text for line in self.lines)


def clean(text: str) -> str:
    """Make look-alike characters identical.

    NFKC turns full-width digits (１２３) into normal ones (123) and odd
    spaces (like the no-break space) into normal spaces.
    """
    text = unicodedata.normalize("NFKC", text)
    return text.replace("\u2212", "-").replace("\u2013", "-").strip()


def _is_upright(obj) -> bool:
    """Keep everything except rotated characters (watermarks like PAID or COPY).

    Each character has a matrix (a, b, c, d, e, f). For normal horizontal
    text, b and c are zero. Rotated text has non-zero b or c.
    """
    if obj.get("object_type") != "char":
        return True
    a, b, c, d, e, f = obj.get("matrix", (1, 0, 0, 1, 0, 0))
    return abs(b) < 0.001 and abs(c) < 0.001


def _group_into_lines(words: list, page_number: int) -> list:
    """Group words into lines by their vertical position, then split at wide gaps."""
    words = sorted(words, key=lambda w: (w["top"], w["x0"]))
    rows = []
    for word in words:
        if rows and abs(word["top"] - rows[-1][0]["top"]) <= LINE_TOLERANCE:
            rows[-1].append(word)
        else:
            rows.append([word])

    lines = []
    for row in rows:
        row.sort(key=lambda w: w["x0"])
        segments, starts, current, last_x1 = [], [], [], None
        for word in row:
            if last_x1 is not None and word["x0"] - last_x1 > COLUMN_GAP:
                segments.append(" ".join(current))
                current = []
            if not current:
                starts.append(word["x0"])  # a new segment begins here
            current.append(word["text"])
            last_x1 = word["x1"]
        segments.append(" ".join(current))

        pairs = [(clean(text), x) for text, x in zip(segments, starts)]
        pairs = [(text, x) for text, x in pairs if text]
        if pairs:
            lines.append(Line(
                text=GAP_MARK.join(text for text, _ in pairs),
                segments=[text for text, _ in pairs],
                starts=[x for _, x in pairs],
                page=page_number, top=row[0]["top"], x0=row[0]["x0"],
            ))
    return lines


def read_pdf(pdf_bytes: bytes) -> PdfText:
    """Turn PDF bytes into lines, page by page, top to bottom."""
    result = PdfText()
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        result.page_count = len(pdf.pages)
        result.skipped_pages = max(0, result.page_count - MAX_PAGES)
        for number, page in enumerate(pdf.pages[:MAX_PAGES], start=1):
            page = page.filter(_is_upright)
            words = page.extract_words()
            result.char_count += sum(len(word["text"]) for word in words)
            result.lines.extend(_group_into_lines(words, number))
    return result