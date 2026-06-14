"""
Rule-based document type classifier for F1.

Classifies regulatory documents by matching keywords in the title.
Intentionally simple — accuracy is good enough for Day 2.
F2 (AI summarisation) will refine this classification using an LLM.

Keyword lists are ordered: more specific phrases first so "proposed rule"
doesn't accidentally match before "advance notice of proposed rulemaking".
"""

from src.models import DocType

# Each tuple: (DocType, list of lowercase keywords to match)
# Order matters — first match wins
_RULES: list[tuple[DocType, list[str]]] = [
    (DocType.ENFORCEMENT, [
        "enforcement action",
        "consent order",
        "civil money penalty",
        "cease and desist",
        "enforcement",
        "penalty",
        "violation",
    ]),
    (DocType.FINAL_RULE, [
        "final rule",
        "final regulations",
        "interim final rule",
        "final guidance",  # treated as final for action purposes
    ]),
    (DocType.PROPOSED_RULE, [
        "advance notice of proposed rulemaking",
        "anpr",
        "notice of proposed rulemaking",
        "proposed rule",
        "proposed regulation",
        "request for comment",
        "request for information",
    ]),
    (DocType.GUIDANCE, [
        "supervisory guidance",
        "guidance",
        "bulletin",
        "circular",
        "advisory",
        "frequently asked questions",
        "faq",
        "statement",
        "interpretive letter",
    ]),
    (DocType.FAQ, [
        "frequently asked questions",
        "faq",
    ]),
]


def classify_doc_type(title: str) -> DocType:
    """
    Return the DocType that best matches the given title.
    Falls back to DocType.OTHER if no keywords match.
    """
    lower = title.lower()
    for doc_type, keywords in _RULES:
        if any(kw in lower for kw in keywords):
            return doc_type
    return DocType.OTHER
