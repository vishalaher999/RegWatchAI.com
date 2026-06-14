"""
PII redaction for F3 policy ingestion (Day 39, KM #267/268).

The fixture policies in /fixtures/policies/ are synthetic and PII-free, but a
real client's uploaded policy library can contain customer/employee SSNs,
account numbers, emails, and phone numbers in example text. Anything that
reaches Pinecone (multi-tenant — one namespace per client) or an LLM prompt
must be scrubbed first, per CLAUDE.md's "Public regulatory data only — no
Moody's internal or client data" constraint.

v1 is regex-only. It catches structured PII (SSN/EIN/account-style numbers,
emails, phone numbers, card numbers) but NOT free-text PII like names or
street addresses, which need NER/NLP — documented as a v2 gap in
docs/Enterprise-Pilot-Program-v1.md.
"""

import re

# Order matters: more specific patterns (SSN, EIN, card numbers) run before
# the generic account/routing-number patterns so a hyphenated SSN isn't
# double-counted as an "account number".
_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("SSN", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("EIN", re.compile(r"\b\d{2}-\d{7}\b")),
    ("CARD_NUMBER", re.compile(r"\b\d{4}[ -]?\d{4}[ -]?\d{4}[ -]?\d{4}\b")),
    ("EMAIL", re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")),
    ("PHONE", re.compile(r"\b\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}\b")),
    # Context-anchored: only redact digit runs that follow "account"/"routing"
    # number labels -- a bare 8-17 digit number elsewhere (e.g. a regulation
    # citation) is not PII.
    ("ACCOUNT_NUMBER", re.compile(
        r"(?i)\b(?:account|acct)\s*(?:number|no\.?|#)\s*[:#]?\s*(\d{6,17})\b"
    )),
    ("ROUTING_NUMBER", re.compile(
        r"(?i)\brouting\s*(?:number|no\.?|#)\s*[:#]?\s*(\d{9})\b"
    )),
]


def redact_text(text: str) -> tuple[str, dict[str, int]]:
    """
    Redact PII from `text`, returning (redacted_text, findings).

    findings maps PII type -> number of matches redacted. An empty dict
    means no PII was found.
    """
    findings: dict[str, int] = {}

    for label, pattern in _PATTERNS:
        if label in ("ACCOUNT_NUMBER", "ROUTING_NUMBER"):
            # Replace only the captured digit group, keeping the "Account
            # Number:" label intact for readability.
            matches = pattern.findall(text)
            if matches:
                findings[label] = findings.get(label, 0) + len(matches)
                text = pattern.sub(
                    lambda m: m.group(0).replace(m.group(1), f"[REDACTED-{label}]"),
                    text,
                )
        else:
            matches = pattern.findall(text)
            if matches:
                findings[label] = findings.get(label, 0) + len(matches)
                text = pattern.sub(f"[REDACTED-{label}]", text)

    return text, findings
