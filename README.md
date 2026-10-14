# Invoice field extraction

A small offline service that reads a supplier invoice PDF (with a text layer)
and returns eight header fields as JSON, each with a confidence score and
warnings for anything a person should check.

## Install and run (one command)

Requires Python 3.10 or newer.

```bash
bash run.sh
```

This creates a virtual environment in `.venv`, installs the libraries from
`requirements.txt`, and starts the service on port 8000.

- Upload page: http://localhost:8000/
- Health check: http://localhost:8000/health
- API docs: http://localhost:8000/docs

If `bash` is not available, run the same steps by hand:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

On Windows, use `.venv\Scripts\python` instead of `.venv/bin/python`.

## Use the API

```bash
curl -F "file=@invoice.pdf" http://localhost:8000/extract
```

Returns `vendor`, `invoice_number`, `invoice_date`, `due_date`, `currency`,
`subtotal`, `tax`, `total`, a `confidence` per field (0 to 1), and `warnings`.

## Run the tests (no network needed)

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pytest -v
```

79 tests cover number and date formats, vendor matching, every business
rule (O1 to O5), the two example invoices from the brief, the HTTP
endpoints, ten generated invoices (one per rule or anomaly) and two
hand-made Word invoices. All test PDFs are stored in `tests/fixtures/`.

## Recreate the test data and the scores

```bash
.venv/bin/python -m data_gen.generate --group A --count 300
.venv/bin/python -m data_gen.generate --group B --count 300
.venv/bin/python -m eval.evaluate data_gen/output/A
.venv/bin/python -m eval.evaluate data_gen/output/B --by layout
```

Fixed seeds (1 for A, 2 for B) give the same invoices every time.
Saved results are in `eval/results/`. See DATA.md for details.

## Project layout

```
app/          the service: main.py (HTTP), pipeline.py (runs the steps),
              pdf_text, vendors, doctype, invoice_number, dates, amounts,
              currency, labels; static/index.html (upload page)
data_gen/     synthetic invoice generator (vocab.py = word lists, groups A and B)
eval/         evaluate.py (scores), find.py and show.py (debugging), results/
tests/        pytest tests and fixture PDFs
```

## Documents

- DATA.md: where the test data came from, how it was used, results, risks
- NOTES.md: decisions, what was cut, what comes next
- AI.md: AI tools used and for what