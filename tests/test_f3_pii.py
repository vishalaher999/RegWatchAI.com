"""
Day 39 (KM #267/268 PII) tests for src/f3_impact/pii.py and its hook into
extract_policy_sections.

v1 is regex-only -- structured PII (SSN, EIN, card numbers, emails, phones,
labeled account/routing numbers) is redacted before policy text is embedded.
Free-text PII (names, addresses) is NOT covered -- see
docs/Enterprise-Pilot-Program-v1.md for the v2 plan.
"""

from src.f3_impact.extractor import extract_policy_sections
from src.f3_impact.pii import redact_text


def test_redacts_ssn():
    text = "Employee SSN: 123-45-6789 on file."
    redacted, findings = redact_text(text)
    assert "123-45-6789" not in redacted
    assert "[REDACTED-SSN]" in redacted
    assert findings == {"SSN": 1}


def test_redacts_ein():
    text = "The Bank's EIN is 12-3456789 for tax purposes."
    redacted, findings = redact_text(text)
    assert "12-3456789" not in redacted
    assert "[REDACTED-EIN]" in redacted
    assert findings == {"EIN": 1}


def test_redacts_card_number():
    text = "Card on file: 4111 1111 1111 1111."
    redacted, findings = redact_text(text)
    assert "4111 1111 1111 1111" not in redacted
    assert "[REDACTED-CARD_NUMBER]" in redacted
    assert findings == {"CARD_NUMBER": 1}


def test_redacts_email_and_phone():
    text = "Contact compliance@examplebank.com or (555) 123-4567."
    redacted, findings = redact_text(text)
    assert "compliance@examplebank.com" not in redacted
    assert "(555) 123-4567" not in redacted
    assert findings == {"EMAIL": 1, "PHONE": 1}


def test_redacts_labeled_account_and_routing_numbers():
    text = "Account Number: 123456789012 / Routing Number: 021000021"
    redacted, findings = redact_text(text)
    assert "123456789012" not in redacted
    assert "021000021" not in redacted
    assert "Account Number: [REDACTED-ACCOUNT_NUMBER]" in redacted
    assert "Routing Number: [REDACTED-ROUTING_NUMBER]" in redacted
    assert findings == {"ACCOUNT_NUMBER": 1, "ROUTING_NUMBER": 1}


def test_clean_text_passes_through_unchanged():
    text = "The Bank shall file a Currency Transaction Report within 15 days."
    redacted, findings = redact_text(text)
    assert redacted == text
    assert findings == {}


def test_extract_policy_sections_redacts_body_text():
    text = (
        "SECTION 4: TRANSACTION MONITORING\n\n"
        "4.2 Currency Transaction Reporting (CTR)\n"
        "Contact compliance@examplebank.com with questions. "
        "Customer SSN 123-45-6789 was flagged for review.\n"
    )
    sections = extract_policy_sections(text, "Test-Policy")
    assert len(sections) == 1

    section = sections[0]
    assert "compliance@examplebank.com" not in section.text
    assert "123-45-6789" not in section.text
    assert section.pii_findings == {"EMAIL": 1, "SSN": 1}


def test_extract_policy_sections_no_pii_has_empty_findings():
    text = (
        "SECTION 4: TRANSACTION MONITORING\n\n"
        "4.2 Currency Transaction Reporting (CTR)\n"
        "The Bank shall file a Currency Transaction Report within 15 days.\n"
    )
    sections = extract_policy_sections(text, "Test-Policy")
    assert sections[0].pii_findings == {}
