"""
Tests for the F1 document type classifier.

These tests are fast (no network, no DB) and should always pass.
They are the first line of defense against classifier regressions.
"""

import pytest
from src.f1_ingest.classifier import classify_doc_type
from src.models import DocType


@pytest.mark.parametrize("title,expected", [
    # Final rules
    ("Federal Reserve Issues Final Rule on Capital Requirements", DocType.FINAL_RULE),
    ("Interim Final Rule Amending Regulation E", DocType.FINAL_RULE),
    # Proposed rules
    ("Notice of Proposed Rulemaking: Amendments to Regulation Z", DocType.PROPOSED_RULE),
    ("Request for Comment on Proposed Rule for Community Banks", DocType.PROPOSED_RULE),
    ("Advance Notice of Proposed Rulemaking on Climate Risk", DocType.PROPOSED_RULE),
    # Guidance
    ("Supervisory Guidance on Model Risk Management", DocType.GUIDANCE),
    ("OCC Bulletin 2026-01: Third-Party Risk Management", DocType.GUIDANCE),
    ("Advisory on Cybersecurity Practices for Community Banks", DocType.GUIDANCE),
    # Enforcement
    ("Enforcement Action: Consent Order Issued to Regional Bank", DocType.ENFORCEMENT),
    ("Civil Money Penalty Assessed for BSA Violations", DocType.ENFORCEMENT),
    # Other
    ("Annual Report on the Economic Well-Being of US Households", DocType.OTHER),
    ("Federal Reserve Chair Testimony Before Senate Banking Committee", DocType.OTHER),
])
def test_classify_doc_type(title: str, expected: DocType) -> None:
    assert classify_doc_type(title) == expected


def test_classify_is_case_insensitive() -> None:
    assert classify_doc_type("FINAL RULE ON CAPITAL") == DocType.FINAL_RULE
    assert classify_doc_type("final rule on capital") == DocType.FINAL_RULE


def test_enforcement_takes_priority_over_guidance() -> None:
    # A title containing both "guidance" and "enforcement" should be ENFORCEMENT
    title = "Enforcement Action Following Violations of Supervisory Guidance"
    assert classify_doc_type(title) == DocType.ENFORCEMENT
