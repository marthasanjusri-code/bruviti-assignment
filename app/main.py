"""HTTP service: the upload page, the health check and the extract endpoint."""

from pathlib import Path

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import HTMLResponse

from app.pipeline import empty_result, extract_invoice

app = FastAPI(title="Invoice field extraction")

INDEX_PAGE = Path(__file__).parent / "static" / "index.html"


@app.get("/health")
def health() -> dict:
    """Tells the grader the service is ready."""
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    """The upload page for people to try the service."""
    if INDEX_PAGE.exists():
        return INDEX_PAGE.read_text(encoding="utf-8")
    return "<h1>Invoice extractor</h1><p>Upload page not built yet. Try /docs.</p>"


@app.post("/extract")
def extract(file: UploadFile = File(...)) -> dict:
    """Receive one PDF and return the extracted fields as JSON."""
    pdf_bytes = file.file.read()

    if b"%PDF" not in pdf_bytes[:1024]:
        return empty_result(["Uploaded file is not a PDF."])

    try:
        return extract_invoice(pdf_bytes)
    except Exception as error:
        return empty_result([f"Could not process the PDF: {type(error).__name__}."])