# Notes

## Decisions

- **Rules, not machine learning.** There is no real training data. A model
  trained on my own synthetic invoices would learn my generator's habits.
  Rules based on labels, positions and arithmetic generalise better, run in
  about 50 ms, and are easy to explain and test.
- **General patterns over per-vendor templates.** The hidden invoices use
  layouts I have not seen, so nothing depends on where a vendor puts a field.
  The vendor is only used for its country (date order) and currency (rule O3).
- **Arithmetic as a second opinion.** When labels are missing or unknown,
  subtotal, tax and total are found from subtotal + tax = total and from
  their order on the page. Printed values are never corrected (rule O2).
- **Small, safe stack.** FastAPI, uvicorn, python-multipart and pdfplumber
  (MIT licence). Vendor matching uses Python's built-in `difflib`. No
  compiled extras, no network, no GPU. One command installs and starts.
- **Never crash.** Bad uploads, broken PDFs and internal errors still return
  the full JSON shape with a warning, and HTTP 200.
- **Confidence** follows how a value was found: a labelled value on the same
  line about 0.95, below its label 0.85, arithmetic fallback 0.85, guesses
  0.5–0.6, vendor default currency 0.6; ambiguous dates are capped at 0.8 and
  totals that add up get 0.97, matching the brief's examples.
- **Warnings** are added whenever the code guessed, used a fallback or saw
  something odd. I also warn about ambiguous dates when the vendor's country
  decided them. Example 1 in the brief shows no warning for 03/09/2026, but
  the metric section asks for one, and warnings are not scored.
- **Honest testing.** Data was split into groups A and B; the blind B score
  is reported separately from the score after B-guided fixes (see DATA.md).

## What I cut, and why

- **Scanned PDFs / OCR**: out of scope in the brief, and a large install.
- **Machine learning**: no real data to learn from (see above).
- **Separate `rules.py` and `confidence.py`**: planned at the start, but the
  rules and scores ended up living next to the code that finds each field,
  which was simpler to test.
- **Ambiguous cases the brief does not define**: discounts (is subtotal
  before or after?), "amount paid / balance", "due on receipt", pro forma
  invoices and credit notes. I chose not to guess silently.
- **Docker**: the reviewer may not have it; a plain script is safer.

## Known issues

- In blind group B: invoice numbers with unknown labels far from their value,
  due dates with unusual labels, and non-invoices in other languages.
- Values are searched only beside a label or on the next line.
- Non-invoice detection knows English, German and Japanese titles only.

## What I would do next

1. Test on **real invoices** from these vendors; record every correction.
2. With enough corrected invoices, train a small classifier that labels each
   line (number, date, total, ...), using today's rules as features.
3. Use word positions to read **tables and key-value grids** properly.
4. **Calibrate confidence** so that 0.9 really means 90% correct, and use it
   to send only low-confidence fields to a human.
5. Add a second fresh, blind test group with new wording before each release.