"""The HTTP service, including the brief's own Examples 1 and 2."""

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.models import FIELDS

client = TestClient(app)
FIXTURES = Path(__file__).parent / "fixtures"


def extract(name: str) -> dict:
    with open(FIXTURES / name, "rb") as handle:
        response = client.post("/extract", files={"file": (name, handle, "application/pdf")})
    assert response.status_code == 200
    return response.json()


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_upload_page():
    response = client.get("/")
    assert response.status_code == 200
    assert "Invoice field extraction" in response.text


def test_brief_example_1_northwind():
    result = extract("northwind_1042.pdf")
    assert {f: result[f] for f in FIELDS} == {
        "vendor": "Northwind Traders", "invoice_number": "NW-1042",
        "invoice_date": "2026-09-03", "due_date": "2026-10-03", "currency": "GBP",
        "subtotal": 361.6, "tax": 72.32, "total": 433.92,
    }


def test_brief_example_2_kestrel():
    result = extract("kestrel_0311.pdf")
    assert {f: result[f] for f in FIELDS} == {
        "vendor": "Kestrel Components", "invoice_number": "KC-0311",
        "invoice_date": "2026-09-03", "due_date": "2026-10-03", "currency": "USD",
        "subtotal": 225.8, "tax": 16.37, "total": 242.17,
    }
    assert "Date 9/3/26 read as month-first (US vendor)." in result["warnings"]
    assert "Due date derived from terms Net 30." in result["warnings"]


def test_response_shape():
    result = extract("northwind_1042.pdf")
    assert set(result) == set(FIELDS) | {"confidence", "warnings"}
    assert set(result["confidence"]) == set(FIELDS)
    assert all(0.0 <= value <= 1.0 for value in result["confidence"].values())


def test_not_a_pdf_gives_a_warning_not_a_crash():
    response = client.post("/extract", files={"file": ("note.txt", b"hello", "text/plain")})
    assert response.status_code == 200
    result = response.json()
    assert result["vendor"] == "unknown"
    assert "Uploaded file is not a PDF." in result["warnings"]