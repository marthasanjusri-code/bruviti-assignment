"""Build the two example invoices from Appendix N of the brief as PDFs.

Run once (needs reportlab):  python -m tests.fixtures.make_brief_examples
The PDFs are committed, so the tests themselves do not need reportlab.
"""

from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

HERE = Path(__file__).parent

# Each row is a list of (x position, text, align). Align "R" means right-aligned.
NORTHWIND = [
    [(50, "NORTHWIND TRADERS LTD", "")],
    [(50, "14 Quay Street, Bristol BS1 4DB, United Kingdom", "")],
    [(50, "VAT No. GB 123 4567 89", "")],
    [(545, "INVOICE", "R")],
    [(50, "Invoice No: NW-1042", "")],
    [(50, "Invoice Date: 03/09/2026", "")],
    [(50, "Due Date: 03/10/2026", "")],
    [(50, "Bill to: Bruviti Services Pvt Ltd", "")],
    [(50, "Item", ""), (330, "Qty", "R"), (430, "Unit Price", "R"), (545, "Amount", "R")],
    [(50, "Pallet wrap, 500mm", ""), (330, "12", "R"), (430, "18.50", "R"), (545, "222.00", "R")],
    [(50, "Corrugated boxes, large", ""), (330, "40", "R"), (430, "2.35", "R"), (545, "94.00", "R")],
    [(50, "Packing tape, brown", ""), (330, "24", "R"), (430, "1.90", "R"), (545, "45.60", "R")],
    [(360, "Subtotal", ""), (545, "361.60", "R")],
    [(360, "VAT 20%", ""), (545, "72.32", "R")],
    [(360, "Amount Due", ""), (545, "GBP 433.92", "R")],
]

KESTREL = [
    [(50, "Kestrel Components Inc. | 880 Industrial Pkwy, Dayton OH 45402, USA", "")],
    [(50, "Reference # KC-0311   Dated 9/3/26", "")],
    [(50, "Terms Net 30", "")],
    [(50, "Sold to Bruviti Services Pvt Ltd", "")],
    [(50, "Particulars", ""), (545, "Total", "R")],
    [(50, "Bearing kit 6204-2RS (x10)", ""), (545, "145.00", "R")],
    [(50, "Drive belt A-42 (x4)", ""), (545, "62.80", "R")],
    [(50, "Shipping", ""), (545, "18.00", "R")],
    [(50, "------------------------", "")],
    [(360, "Sub total", ""), (545, "225.80", "R")],
    [(360, "Sales tax 7.25%", ""), (545, "16.37", "R")],
    [(360, "Balance Due", ""), (545, "$ 242.17", "R")],
]


def build(rows: list, path: Path) -> None:
    pdf = canvas.Canvas(str(path), pagesize=A4, invariant=1)
    pdf.setFont("Helvetica", 10)
    y = 790
    for row in rows:
        for x, text, align in row:
            if align == "R":
                pdf.drawRightString(x, y, text)
            else:
                pdf.drawString(x, y, text)
        y -= 18
    pdf.showPage()
    pdf.save()


if __name__ == "__main__":
    build(NORTHWIND, HERE / "northwind_1042.pdf")
    build(KESTREL, HERE / "kestrel_0311.pdf")
    print("Wrote northwind_1042.pdf and kestrel_0311.pdf")