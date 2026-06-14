"""
Named Entity Recognition (NER) for F2 — Day 12.

KM concept: #82 NER
Extracts structured entities from regulatory text:
  - Dates (effective dates, compliance deadlines, publication dates)
  - Institution types (community banks, credit unions, asset thresholds)
  - Regulation citations (Reg B, 12 CFR Part 1002, etc.)

Two-layer approach:
  Layer 1: Regex — fast, free, deterministic. Handles standard date formats.
  Layer 2: Context analysis — uses surrounding text to classify dates
           (is this an effective date or a compliance deadline?)

Why regex for dates instead of an LLM?
  "January 1, 2027" is a completely predictable pattern. Regex finds it
  in microseconds with zero cost and zero hallucination risk. The LLM is
  used for SEMANTIC understanding (what does this date mean?) not for
  PATTERN MATCHING (is this text a date?).

Cross-validation:
  NER results are compared against LLM summary output in summariser.py.
  Agreement → confidence boost. Disagreement → confidence penalty.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

# ── Date patterns ──────────────────────────────────────────────────────────────

# Month names and abbreviations
_MONTHS = (
    r'(?:January|February|March|April|May|June|July|August|September|October|November|December'
    r'|Jan\.?|Feb\.?|Mar\.?|Apr\.?|Jun\.?|Jul\.?|Aug\.?|Sep\.?|Oct\.?|Nov\.?|Dec\.?)'
)

# Date formats found in regulatory text:
_DATE_PATTERNS = [
    # "January 1, 2027" or "January 1, 2027,"
    (re.compile(rf'\b({_MONTHS})\s+(\d{{1,2}}),?\s+(202[4-9]|203[0-9])\b'), 'mdy'),
    # "1 January 2027"
    (re.compile(rf'\b(\d{{1,2}})\s+({_MONTHS})\s+(202[4-9]|203[0-9])\b'), 'dmy'),
    # "2027-01-01" or "2027/01/01"
    (re.compile(r'\b(202[4-9]|203[0-9])[-/](\d{2})[-/](\d{2})\b'), 'iso'),
    # "January 2027" (month + year only — used for deadlines)
    (re.compile(rf'\b({_MONTHS})\s+(202[4-9]|203[0-9])\b'), 'my'),
]

# Context phrases that signal EFFECTIVE DATE
_EFFECTIVE_DATE_CONTEXT = re.compile(
    r'(?i)(?:effective\s+(?:date|on|as\s+of)|takes?\s+effect|effective\s+upon|'
    r'effective\s+immediately|in\s+effect\s+on|becomes?\s+effective)',
    re.IGNORECASE,
)

# Context phrases that signal COMPLIANCE DEADLINE
_COMPLIANCE_DEADLINE_CONTEXT = re.compile(
    r'(?i)(?:compliance\s+(?:date|deadline|by)|must\s+comply\s+(?:by|no\s+later\s+than)|'
    r'no\s+later\s+than|by\s+which\s+(?:institutions?|banks?|creditors?)\s+must|'
    r'comply\s+by|implementation\s+(?:date|deadline)|required\s+to\s+comply\s+by)',
    re.IGNORECASE,
)

# Relative date phrases (can't be resolved without publication date)
_RELATIVE_DATE = re.compile(
    r'(?i)(\d+)\s+days?\s+(?:after|following|from)\s+(?:publication|the\s+effective\s+date|'
    r'the\s+date\s+of\s+publication)',
)

# ── Institution type patterns ──────────────────────────────────────────────────

_INSTITUTION_PATTERNS = [
    re.compile(r'\b(community\s+banks?)\b', re.IGNORECASE),
    re.compile(r'\b(credit\s+unions?)\b', re.IGNORECASE),
    re.compile(r'\b(national\s+banks?)\b', re.IGNORECASE),
    re.compile(r'\b(state\s+(?:member\s+)?banks?)\b', re.IGNORECASE),
    re.compile(r'\b(federally\s+(?:chartered|insured)\s+(?:banks?|credit\s+unions?))\b', re.IGNORECASE),
    re.compile(r'\b(FDIC[- ]supervised\s+(?:institutions?|banks?))\b', re.IGNORECASE),
    re.compile(r'\b(federal\s+(?:savings\s+banks?|thrifts?))\b', re.IGNORECASE),
    re.compile(r'\b(bank\s+holding\s+compan(?:y|ies))\b', re.IGNORECASE),
    re.compile(r'\b(savings\s+(?:associations?|institutions?|banks?))\b', re.IGNORECASE),
    re.compile(r'\b(mortgage\s+(?:servicers?|lenders?))\b', re.IGNORECASE),
    re.compile(r'\b((?:non-?bank|nonbank)\s+(?:lenders?|financial\s+institutions?))\b', re.IGNORECASE),
    # Asset threshold patterns
    re.compile(
        r'\b((?:banks?|institutions?|creditors?)\s+with\s+(?:total\s+)?assets\s+(?:of\s+)?'
        r'(?:greater\s+than|more\s+than|at\s+least|exceeding|of)\s+\$[\d,.]+\s*(?:billion|million|B|M)?)',
        re.IGNORECASE,
    ),
    re.compile(
        r'\b((?:banks?|institutions?)\s+with\s+\$[\d,.]+\s*(?:billion|million)\s+or\s+more\s+in\s+(?:total\s+)?assets)',
        re.IGNORECASE,
    ),
]

# ── Regulation citation patterns ───────────────────────────────────────────────

_CITATION_PATTERNS = [
    re.compile(r'\b(\d+\s+CFR\s+(?:Part\s+)?\d+(?:\.\d+)?)\b', re.IGNORECASE),
    re.compile(r'\b(Reg(?:ulation)?\s+[A-Z])\b'),
    re.compile(r'\b(section\s+\d+(?:\([a-z]\))?(?:\(\d+\))?)\b', re.IGNORECASE),
    re.compile(r'(§+\s*\d+(?:\.\d+)?(?:\([a-z]\))?)'),
]


# ── Data structures ────────────────────────────────────────────────────────────

@dataclass
class ExtractedDate:
    raw_text: str           # the exact text matched
    normalized: str         # YYYY-MM-DD or YYYY-MM (if day unknown)
    date_type: str          # "effective", "compliance", "general", "relative"
    context_before: str     # 100 chars before the date
    context_after: str      # 100 chars after the date
    confidence: float       # 0.0–1.0


@dataclass
class NERResult:
    effective_dates: list[ExtractedDate] = field(default_factory=list)
    compliance_deadlines: list[ExtractedDate] = field(default_factory=list)
    institution_types: list[str] = field(default_factory=list)
    regulation_citations: list[str] = field(default_factory=list)
    relative_dates: list[str] = field(default_factory=list)
    best_effective_date: Optional[str] = None      # YYYY-MM-DD, highest-confidence pick
    best_compliance_deadline: Optional[str] = None  # YYYY-MM-DD, highest-confidence pick


# ── Date parsing ───────────────────────────────────────────────────────────────

_MONTH_MAP = {
    'january': 1, 'jan': 1,
    'february': 2, 'feb': 2,
    'march': 3, 'mar': 3,
    'april': 4, 'apr': 4,
    'may': 5,
    'june': 6, 'jun': 6,
    'july': 7, 'jul': 7,
    'august': 8, 'aug': 8,
    'september': 9, 'sep': 9,
    'october': 10, 'oct': 10,
    'november': 11, 'nov': 11,
    'december': 12, 'dec': 12,
}


def _normalize_date(match: re.Match, fmt: str) -> Optional[str]:
    """Convert a regex match to YYYY-MM-DD string."""
    try:
        groups = match.groups()
        if fmt == 'mdy':
            month_str, day, year = groups[0], groups[1], groups[2]
            month = _MONTH_MAP.get(month_str.lower().rstrip('.'), 0)
            if not month:
                return None
            return f"{year}-{month:02d}-{int(day):02d}"
        elif fmt == 'dmy':
            day, month_str, year = groups[0], groups[1], groups[2]
            month = _MONTH_MAP.get(month_str.lower().rstrip('.'), 0)
            if not month:
                return None
            return f"{year}-{month:02d}-{int(day):02d}"
        elif fmt == 'iso':
            year, month, day = groups[0], groups[1], groups[2]
            return f"{year}-{month}-{day}"
        elif fmt == 'my':
            month_str, year = groups[0], groups[1]
            month = _MONTH_MAP.get(month_str.lower().rstrip('.'), 0)
            if not month:
                return None
            return f"{year}-{month:02d}-01"  # Use first of month when day unknown
    except (ValueError, IndexError):
        return None
    return None


def _classify_date(context_before: str, context_after: str) -> str:
    """
    Classify a date as effective, compliance, general, or relative.

    Strategy: context_before is the primary signal (what leads into the date).
    context_after is only used as a tiebreaker if before context is ambiguous.

    "takes effect on [DATE]" → before = "takes effect on" → effective
    "must comply by [DATE]" → before = "must comply by" → compliance
    """
    # Use a 40-char window immediately before the date.
    # "takes effect on [DATE]" → before[-40:] = "takes effect on"  ✓
    # "must comply by [DATE]"  → before[-40:] = "must comply by"   ✓
    # "The rule takes effect on [D1]. Must comply by [D2]"
    #   D2 before[-40:] = "2026. Institutions must comply by" (no "effect on")  ✓
    before_close = context_before[-40:].lower()
    after_close = context_after[:40].lower()

    if _EFFECTIVE_DATE_CONTEXT.search(before_close):
        return "effective"
    if _COMPLIANCE_DEADLINE_CONTEXT.search(before_close):
        return "compliance"
    if _EFFECTIVE_DATE_CONTEXT.search(after_close):
        return "effective"
    if _COMPLIANCE_DEADLINE_CONTEXT.search(after_close):
        return "compliance"

    return "general"


def _date_confidence(date_type: str, normalized: str) -> float:
    """Base confidence score for an extracted date."""
    base = 0.7
    if date_type == "effective":
        base = 0.90
    elif date_type == "compliance":
        base = 0.88
    elif date_type == "general":
        base = 0.65
    # Penalise month-only dates (day unknown)
    if normalized.endswith('-01') and 'day' not in normalized:
        base -= 0.10
    return round(base, 2)


# ── Main extractors ────────────────────────────────────────────────────────────

def extract_dates(text: str) -> list[ExtractedDate]:
    """
    Extract all dates from regulatory text.

    Scans the full document text for date patterns, classifies each date
    using surrounding context, and returns a list sorted by confidence.
    """
    if not text:
        return []

    found: list[ExtractedDate] = []
    seen_normalized: set[str] = set()

    for pattern, fmt in _DATE_PATTERNS:
        for match in pattern.finditer(text):
            normalized = _normalize_date(match, fmt)
            if not normalized or normalized in seen_normalized:
                continue

            # Only care about regulatory-relevant years
            year = int(normalized[:4])
            if year < 2020 or year > 2035:
                continue

            seen_normalized.add(normalized)

            start = match.start()
            end = match.end()
            context_before = text[max(0, start - 120):start]
            context_after = text[end:min(len(text), end + 120)]

            date_type = _classify_date(context_before, context_after)
            confidence = _date_confidence(date_type, normalized)

            found.append(ExtractedDate(
                raw_text=match.group(0),
                normalized=normalized,
                date_type=date_type,
                context_before=context_before.strip(),
                context_after=context_after.strip(),
                confidence=confidence,
            ))

    # Check for relative dates
    return sorted(found, key=lambda d: d.confidence, reverse=True)


def extract_relative_dates(text: str) -> list[str]:
    """Extract relative date phrases that can't be resolved without context."""
    return [m.group(0) for m in _RELATIVE_DATE.finditer(text)]


def extract_institution_types(text: str) -> list[str]:
    """
    Extract institution type mentions from regulatory text.
    Returns deduplicated list, normalised to title case.
    """
    if not text:
        return []

    found: set[str] = set()
    for pattern in _INSTITUTION_PATTERNS:
        for match in pattern.finditer(text):
            inst = match.group(1).strip()
            # Normalise: collapse whitespace, title case for display
            inst = ' '.join(inst.split())
            inst = inst.lower()
            found.add(inst)

    # Sort by length (shorter/more general first)
    return sorted(found, key=len)


def extract_citations(text: str) -> list[str]:
    """Extract regulation citation references."""
    if not text:
        return []
    found: set[str] = set()
    for pattern in _CITATION_PATTERNS:
        for match in pattern.finditer(text):
            found.add(match.group(1).strip())
    return sorted(found)


# ── Main NER runner ────────────────────────────────────────────────────────────

def run_ner(text: str) -> NERResult:
    """
    Run all NER extractors on a document's full text.
    Returns a NERResult with best picks for effective_date and compliance_deadline.
    """
    result = NERResult()

    if not text:
        return result

    all_dates = extract_dates(text)

    for d in all_dates:
        if d.date_type == "effective":
            result.effective_dates.append(d)
        elif d.date_type == "compliance":
            result.compliance_deadlines.append(d)

    result.relative_dates = extract_relative_dates(text)
    result.institution_types = extract_institution_types(text)
    result.regulation_citations = extract_citations(text)

    # Best picks: highest confidence date of each type
    if result.effective_dates:
        result.best_effective_date = result.effective_dates[0].normalized
    if result.compliance_deadlines:
        result.best_compliance_deadline = result.compliance_deadlines[0].normalized

    return result


# ── Cross-validation ───────────────────────────────────────────────────────────

def cross_validate(
    llm_summary: dict,
    ner_result: NERResult,
) -> tuple[dict, int]:
    """
    Compare LLM summary output against NER extraction results.

    Returns (updated_summary, confidence_adjustment):
      - If NER and LLM agree on a date → +5 confidence
      - If NER finds a date but LLM returned null → fill from NER, +0
      - If NER finds a different date than LLM → -5 confidence (flag for review)
      - If both return null → no change

    The updated_summary has NER-filled fields where LLM returned null.
    """
    summary = dict(llm_summary)
    confidence_delta = 0

    # ── Effective date ─────────────────────────────────────────────────────────
    llm_eff = summary.get("effective_date")
    ner_eff = ner_result.best_effective_date

    if llm_eff and ner_eff:
        if llm_eff == ner_eff:
            confidence_delta += 5  # Both agree — strong evidence
        else:
            confidence_delta -= 5  # Disagreement — flag uncertainty
            # Keep LLM date but note disagreement
            summary["_ner_effective_date_conflict"] = ner_eff
    elif ner_eff and not llm_eff:
        # NER found a date that LLM missed — use NER result
        summary["effective_date"] = ner_eff
        summary["_ner_filled_effective_date"] = True
        confidence_delta += 0  # Neutral — one source, not verified

    # ── Compliance deadline ────────────────────────────────────────────────────
    llm_dead = summary.get("compliance_deadline")
    ner_dead = ner_result.best_compliance_deadline

    if llm_dead and ner_dead:
        if llm_dead == ner_dead:
            confidence_delta += 5
        else:
            confidence_delta -= 5
            summary["_ner_deadline_conflict"] = ner_dead
    elif ner_dead and not llm_dead:
        summary["compliance_deadline"] = ner_dead
        summary["_ner_filled_compliance_deadline"] = True

    # ── Institution types — merge NER with LLM ─────────────────────────────────
    llm_inst = summary.get("affected_institution_types") or []
    ner_inst = ner_result.institution_types

    if ner_inst and not llm_inst:
        # NER found institutions that LLM missed
        summary["affected_institution_types"] = ner_inst[:5]  # top 5
        confidence_delta += 2
    elif ner_inst and llm_inst:
        # Merge: keep LLM's list but add any NER finds not already included
        llm_lower = {i.lower() for i in llm_inst}
        additions = [i for i in ner_inst if i.lower() not in llm_lower]
        if additions:
            summary["affected_institution_types"] = llm_inst + additions[:3]
            confidence_delta += 2

    return summary, confidence_delta
