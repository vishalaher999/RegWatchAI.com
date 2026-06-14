"""
Tests for F2 NER — date extraction, institution type extraction, cross-validation.
All tests are fast (no API calls, no DB).
"""

import pytest
from src.f2_summarise.ner import (
    extract_dates,
    extract_institution_types,
    extract_citations,
    extract_relative_dates,
    run_ner,
    cross_validate,
)


# ── Date extraction ────────────────────────────────────────────────────────────

def test_extract_mdy_date():
    text = "The final rule is effective January 1, 2027."
    dates = extract_dates(text)
    assert len(dates) >= 1
    assert any(d.normalized == "2027-01-01" for d in dates)


def test_extract_iso_date():
    text = "Compliance required by 2027-03-15."
    dates = extract_dates(text)
    assert any(d.normalized == "2027-03-15" for d in dates)


def test_extract_month_year_only():
    text = "The compliance deadline is March 2027."
    dates = extract_dates(text)
    assert any(d.normalized == "2027-03-01" for d in dates)


def test_extract_effective_date_classified_correctly():
    text = "The rule takes effect on July 21, 2026. Banks must prepare."
    dates = extract_dates(text)
    eff = [d for d in dates if d.date_type == "effective"]
    assert len(eff) >= 1
    assert eff[0].normalized == "2026-07-21"


def test_extract_compliance_deadline_classified():
    text = "Institutions must comply by December 31, 2026 with the new requirements."
    dates = extract_dates(text)
    comp = [d for d in dates if d.date_type == "compliance"]
    assert len(comp) >= 1
    assert comp[0].normalized == "2026-12-31"


def test_ignores_old_dates():
    text = "The Bank Secrecy Act was enacted in 1970 and amended in 2001."
    dates = extract_dates(text)
    assert len(dates) == 0


def test_ignores_far_future_dates():
    text = "The policy will be reviewed in 2050."
    dates = extract_dates(text)
    assert len(dates) == 0


def test_multiple_dates_sorted_by_confidence():
    text = (
        "The final rule takes effect January 1, 2027. "
        "Prior to this, institutions should note that February 2027 "
        "was considered as a possible deadline."
    )
    dates = extract_dates(text)
    assert len(dates) >= 2
    # Higher confidence dates should come first
    assert dates[0].confidence >= dates[-1].confidence


def test_empty_text_returns_empty():
    assert extract_dates("") == []
    assert extract_dates(None) == []


def test_relative_date_extraction():
    text = "The rule becomes effective 90 days after publication in the Federal Register."
    relative = extract_relative_dates(text)
    assert len(relative) >= 1
    assert any("90" in r for r in relative)


# ── Institution type extraction ────────────────────────────────────────────────

def test_extract_community_banks():
    text = "Community banks and credit unions must comply with the new requirements."
    types = extract_institution_types(text)
    assert "community banks" in types or "community bank" in types


def test_extract_credit_unions():
    text = "Federally insured credit unions are subject to this rule."
    types = extract_institution_types(text)
    assert any("credit union" in t for t in types)


def test_extract_asset_threshold():
    text = "Banks with total assets of more than $10 billion must file additional reports."
    types = extract_institution_types(text)
    assert any("10 billion" in t or "$10" in t for t in types)


def test_extract_multiple_institution_types():
    text = (
        "National banks, state member banks, and bank holding companies "
        "are all subject to this guidance. Community banks with assets "
        "under $10 billion may request an extension."
    )
    types = extract_institution_types(text)
    assert len(types) >= 2


def test_empty_institution_text():
    assert extract_institution_types("") == []


# ── Citation extraction ────────────────────────────────────────────────────────

def test_extract_cfr_citation():
    text = "See 12 CFR Part 1002 for the complete text of Regulation B."
    citations = extract_citations(text)
    assert any("1002" in c for c in citations)


def test_extract_regulation_letter():
    text = "Regulation B governs the Equal Credit Opportunity Act."
    citations = extract_citations(text)
    assert any("Regulation B" in c or "Reg B" in c for c in citations)


def test_extract_section_symbol():
    text = "As required by § 1002.5, creditors must notify applicants."
    citations = extract_citations(text)
    assert any("1002" in c for c in citations)


# ── NER result ─────────────────────────────────────────────────────────────────

def test_run_ner_returns_best_dates():
    text = (
        "The rule takes effect on July 21, 2026. "
        "Institutions must comply by December 31, 2026. "
        "Community banks and credit unions are the primary affected entities."
    )
    result = run_ner(text)
    # Effective date from "takes effect on July 21, 2026"
    assert result.best_effective_date == "2026-07-21"
    # Compliance deadline from "must comply by December 31, 2026"
    assert result.best_compliance_deadline == "2026-12-31"
    assert len(result.institution_types) >= 1


def test_run_ner_empty_text():
    result = run_ner("")
    assert result.best_effective_date is None
    assert result.best_compliance_deadline is None
    assert result.institution_types == []


# ── Cross-validation ───────────────────────────────────────────────────────────

def test_cross_validate_agreement_boosts_confidence():
    summary = {"effective_date": "2026-07-21", "compliance_deadline": None,
               "affected_institution_types": [], "confidence_score": 80}
    result = run_ner("The rule is effective July 21, 2026. Banks must comply.")
    result.best_effective_date = "2026-07-21"
    updated, delta = cross_validate(summary, result)
    assert delta > 0  # Agreement should boost confidence


def test_cross_validate_fills_null_date():
    summary = {"effective_date": None, "compliance_deadline": None,
               "affected_institution_types": [], "confidence_score": 75}
    result = run_ner("The final rule takes effect January 1, 2027.")
    updated, delta = cross_validate(summary, result)
    assert updated["effective_date"] == "2027-01-01"


def test_cross_validate_disagreement_reduces_confidence():
    summary = {"effective_date": "2026-06-01", "compliance_deadline": None,
               "affected_institution_types": [], "confidence_score": 85}
    result = run_ner("The rule is effective July 21, 2026.")
    result.best_effective_date = "2026-07-21"
    updated, delta = cross_validate(summary, result)
    assert delta < 0  # Disagreement should penalise confidence


def test_cross_validate_fills_institution_types():
    summary = {"effective_date": None, "compliance_deadline": None,
               "affected_institution_types": [], "confidence_score": 70}
    result = run_ner("Community banks and credit unions must file reports.")
    updated, delta = cross_validate(summary, result)
    assert len(updated["affected_institution_types"]) > 0
