"""The full pipeline on one generated invoice per rule and anomaly."""

import json
from pathlib import Path

import pytest

from app.models import FIELDS
from app.pipeline import extract_invoice
from eval.evaluate import same

FIXTURES = Path(__file__).parent / "fixtures"
GENERATED = sorted(FIXTURES.glob("gen_*.json"))

# Each rule fixture must also produce the right kind of warning.
EXPECTED_WARNINGS = {
    "gen_o1_due_and_terms_disagree": "differs from terms",
    "gen_o1_terms_only": "derived from terms",
    "gen_o2_mismatch": "does not equal",
    "gen_o3_no_currency": "No currency printed",
    "gen_o4_not_invoice": "not an invoice",
}


def run(truth_path: Path):
    truth = json.loads(truth_path.read_text(encoding="utf-8"))
    return truth, extract_invoice(truth_path.with_suffix(".pdf").read_bytes())


def test_fixtures_exist():
    assert len(GENERATED) == 10, "Run: python -m tests.fixtures.collect"


@pytest.mark.parametrize("truth_path", GENERATED, ids=lambda p: p.stem)
def test_every_field_is_correct(truth_path):
    truth, result = run(truth_path)
    wrong = {n: (truth[n], result[n]) for n in FIELDS if not same(n, truth[n], result[n])}
    assert not wrong, f"expected vs got: {wrong}"


@pytest.mark.parametrize("stem, phrase", EXPECTED_WARNINGS.items())
def test_rule_warnings(stem, phrase):
    _, result = run(FIXTURES / f"{stem}.json")
    assert any(phrase in w for w in result["warnings"]), result["warnings"]