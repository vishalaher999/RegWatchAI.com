"""Tests for src/f3_impact/classifier.py."""

from src.f3_impact.classifier import ImpactLevel, classify_impact, classify_matches


def test_classify_impact_thresholds_without_named_match():
    """named_regulation_match=False applies NO_MATCH_PENALTY (-0.20) before thresholding."""
    assert classify_impact(0.80, named_regulation_match=False) == ImpactLevel.HIGH   # 0.60
    assert classify_impact(0.75, named_regulation_match=False) == ImpactLevel.HIGH   # 0.55
    assert classify_impact(0.70, named_regulation_match=False) == ImpactLevel.MEDIUM  # 0.50
    assert classify_impact(0.65, named_regulation_match=False) == ImpactLevel.MEDIUM  # 0.45
    assert classify_impact(0.60, named_regulation_match=False) == ImpactLevel.LOW     # 0.40
    assert classify_impact(0.55, named_regulation_match=False) == ImpactLevel.LOW     # 0.35
    assert classify_impact(0.40, named_regulation_match=False) == ImpactLevel.NOT_APPLICABLE  # 0.20
    assert classify_impact(0.0, named_regulation_match=False) == ImpactLevel.NOT_APPLICABLE


def test_classify_impact_thresholds_with_named_match():
    """named_regulation_match=True applies NAMED_MATCH_BOOST (+0.10) before thresholding."""
    assert classify_impact(0.50, named_regulation_match=True) == ImpactLevel.HIGH    # 0.60
    assert classify_impact(0.45, named_regulation_match=True) == ImpactLevel.HIGH    # 0.55
    assert classify_impact(0.40, named_regulation_match=True) == ImpactLevel.MEDIUM  # 0.50
    assert classify_impact(0.36, named_regulation_match=True) == ImpactLevel.MEDIUM  # 0.46
    assert classify_impact(0.30, named_regulation_match=True) == ImpactLevel.LOW     # 0.40
    assert classify_impact(0.25, named_regulation_match=True) == ImpactLevel.LOW     # 0.35
    assert classify_impact(0.10, named_regulation_match=True) == ImpactLevel.NOT_APPLICABLE  # 0.20


def test_classify_matches_adds_impact_level_and_named_match_without_mutating_input():
    sections = [
        {
            "policy_name": "Fair-Lending-ECOA-Policy",
            "section_id": "2.1",
            "section_title": "Prohibited Bases Under ECOA/Regulation B",
            "parent_section": "SECTION 2: PROHIBITED BASES FOR DISCRIMINATION",
            "matches": [
                {
                    "regulation_doc_id": "docA",
                    "regulation_title": "Equal Credit Opportunity Act (Regulation B)",
                    "dense_score": 0.60,  # 0.60 + 0.10 boost = 0.70 -> high
                    "score": 0.03,
                },
                {
                    "regulation_doc_id": "docB",
                    "regulation_title": "Agencies issue host state loan-to-deposit ratios",
                    "dense_score": 0.30,  # not named, 0.30 - 0.20 = 0.10 -> not_applicable
                    "score": 0.02,
                },
            ],
        }
    ]

    results = classify_matches(sections)

    assert results[0]["matches"][0]["named_regulation_match"] is True
    assert results[0]["matches"][0]["impact_level"] == "high"

    assert results[0]["matches"][1]["named_regulation_match"] is False
    assert results[0]["matches"][1]["impact_level"] == "not_applicable"

    # Original input untouched
    assert "impact_level" not in sections[0]["matches"][0]
    assert "named_regulation_match" not in sections[0]["matches"][0]


def test_classify_matches_handles_section_with_no_matches():
    sections = [
        {
            "policy_name": "BSA-AML-Policy",
            "section_id": "1.1",
            "section_title": "Purpose",
            "parent_section": "SECTION 1",
            "matches": [],
        }
    ]

    results = classify_matches(sections)

    assert results[0]["matches"] == []
