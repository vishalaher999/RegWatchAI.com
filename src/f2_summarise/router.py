"""
Confidence router for F2 — Day 13.

KM concept: #115 System Prompts / Routing Logic

Determines what happens to each summary after generation:
  APPROVED  — high confidence, all signals agree, ready for Sarah to act on
  REVIEW    — moderate confidence, needs a 2-minute human check before acting
  ESCALATE  — low confidence or conflicting signals, needs expert review
  DISMISS   — document is informational only (no action doc), auto-approved

The router is smarter than a simple threshold because it weighs multiple
signals: LLM confidence, NER cross-validation, doc type urgency, and
field completeness. A Final Rule with a missing compliance deadline is
routed differently from an FOMC statement with low confidence.

Why routing matters for the product:
  The review queue is Sarah's morning action list. If it contains 50 items,
  she ignores it. If it contains 3 high-priority items, she acts on them.
  Good routing = the right items in the queue = the queue gets used.

Target: review queue holds < 20% of summaries (roadmap metric).
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class RoutingDecision(str, Enum):
    APPROVED = "approved"    # Ready to act on
    REVIEW = "review"        # Needs 2-min human check
    ESCALATE = "escalate"    # Needs expert / compliance officer review
    DISMISS = "dismiss"      # Informational only — auto-approved, no action


# ── Doc type urgency weights ───────────────────────────────────────────────────
# How urgently Sarah needs to review a document of this type.
# Final Rules have the highest urgency — they have compliance deadlines.
DOC_TYPE_URGENCY = {
    "final_rule":    1.0,   # Must comply — highest urgency
    "proposed_rule": 0.7,   # Comment opportunity — medium urgency
    "enforcement":   0.8,   # Risk signal — high urgency
    "guidance":      0.5,   # Supervisory expectations — medium
    "faq":           0.3,   # Clarification — low urgency
    "other":         0.2,   # Informational — lowest
}

# Doc types where missing dates are a critical problem
DATE_CRITICAL_DOC_TYPES = {"final_rule", "proposed_rule", "enforcement"}

# Doc types that are almost always informational (no action required)
INFORMATIONAL_DOC_TYPES = {"other", "faq"}


@dataclass
class RouterInput:
    """All inputs the router needs to make a decision."""
    summary: dict                    # The full summary JSON dict
    doc_type: str                    # e.g. "final_rule"
    base_confidence: int             # LLM-reported confidence (0-100)
    ner_delta: int                   # NER confidence adjustment (can be negative)
    ner_date_conflict: bool          # True if NER and LLM disagree on a date
    ner_filled_date: bool            # True if NER filled a date LLM returned null
    why_it_matters_says_no_action: bool  # True if "No immediate action required" in text


@dataclass
class RouterOutput:
    """The routing decision and its rationale."""
    decision: RoutingDecision
    adjusted_confidence: int         # base + NER delta, capped 0-100
    urgency_score: float             # 0-1, combines confidence + doc type
    reasons: list[str]               # Human-readable rationale for the decision
    review_priority: int             # 1=highest, 5=lowest, for queue ordering


def _compute_adjusted_confidence(base: int, ner_delta: int) -> int:
    """Apply NER delta to base confidence, capped between 0 and 100."""
    return max(0, min(100, base + ner_delta))


def _check_field_completeness(summary: dict, doc_type: str) -> tuple[bool, list[str]]:
    """
    Check if critical fields are populated.
    Returns (is_complete, list_of_missing_fields).
    """
    missing = []
    critical_fields = ["headline", "plain_english_summary", "what_changed", "why_it_matters"]
    for field in critical_fields:
        val = summary.get(field)
        if not val or (isinstance(val, str) and len(val.strip()) < 10):
            missing.append(field)

    # Date fields are only critical for certain doc types
    if doc_type in DATE_CRITICAL_DOC_TYPES:
        if not summary.get("effective_date") and not summary.get("compliance_deadline"):
            missing.append("dates (both null for rule document)")

    return len(missing) == 0, missing


def route(inp: RouterInput) -> RouterOutput:
    """
    Apply the routing logic and return a decision.

    Decision tree:
      1. If doc type is informational AND "no action" in why_it_matters → DISMISS
      2. If NER date conflict → ESCALATE (two sources disagree = unreliable)
      3. If adjusted confidence < 60 → ESCALATE
      4. If critical fields missing → ESCALATE
      5. If adjusted confidence < 80 → REVIEW
      6. Otherwise → APPROVED
    """
    reasons: list[str] = []
    adjusted = _compute_adjusted_confidence(inp.base_confidence, inp.ner_delta)
    urgency = DOC_TYPE_URGENCY.get(inp.doc_type, 0.3)
    is_complete, missing_fields = _check_field_completeness(inp.summary, inp.doc_type)

    # ── Rule 1: Informational documents with explicit "no action" ──────────────
    if (inp.doc_type in INFORMATIONAL_DOC_TYPES and
            inp.why_it_matters_says_no_action and
            adjusted >= 70):
        reasons.append(f"Informational document ({inp.doc_type}) with no action required")
        return RouterOutput(
            decision=RoutingDecision.DISMISS,
            adjusted_confidence=adjusted,
            urgency_score=urgency * (adjusted / 100),
            reasons=reasons,
            review_priority=5,
        )

    # ── Rule 2: NER date conflict — two sources disagree ──────────────────────
    if inp.ner_date_conflict:
        reasons.append("NER and LLM disagree on date — verify against source document")
        return RouterOutput(
            decision=RoutingDecision.ESCALATE,
            adjusted_confidence=adjusted,
            urgency_score=urgency * 1.2,  # Boost urgency for conflicts
            reasons=reasons,
            review_priority=1,
        )

    # ── Rule 3: Very low confidence ────────────────────────────────────────────
    if adjusted < 60:
        reasons.append(f"Very low confidence ({adjusted}/100) — summary may be incomplete")
        return RouterOutput(
            decision=RoutingDecision.ESCALATE,
            adjusted_confidence=adjusted,
            urgency_score=urgency * (adjusted / 100),
            reasons=reasons,
            review_priority=2,
        )

    # ── Rule 4: Critical fields missing ───────────────────────────────────────
    if not is_complete:
        reasons.append(f"Missing critical fields: {', '.join(missing_fields)}")
        priority = 1 if inp.doc_type == "final_rule" else 2
        return RouterOutput(
            decision=RoutingDecision.ESCALATE if inp.doc_type in DATE_CRITICAL_DOC_TYPES
                     else RoutingDecision.REVIEW,
            adjusted_confidence=adjusted,
            urgency_score=urgency * 1.1,
            reasons=reasons,
            review_priority=priority,
        )

    # ── Rule 5: Moderate confidence — needs a quick check ─────────────────────
    if adjusted < 80:
        reasons.append(f"Moderate confidence ({adjusted}/100) — 2-minute review recommended")
        if inp.ner_filled_date:
            reasons.append("NER filled a date the AI missed — verify date is correct")
        priority = 1 if inp.doc_type == "final_rule" else (
            2 if inp.doc_type in {"proposed_rule", "enforcement"} else 3
        )
        return RouterOutput(
            decision=RoutingDecision.REVIEW,
            adjusted_confidence=adjusted,
            urgency_score=urgency * (adjusted / 100),
            reasons=reasons,
            review_priority=priority,
        )

    # ── Rule 6: High confidence — approved ────────────────────────────────────
    reasons.append(f"High confidence ({adjusted}/100) — ready to act on")
    if inp.ner_delta > 0:
        reasons.append(f"NER confirmed dates (+{inp.ner_delta} confidence)")
    return RouterOutput(
        decision=RoutingDecision.APPROVED,
        adjusted_confidence=adjusted,
        urgency_score=urgency * (adjusted / 100),
        reasons=reasons,
        review_priority=5,
    )


def build_router_input(
    summary: dict,
    doc_type: str,
    ner_delta: int = 0,
) -> RouterInput:
    """
    Build a RouterInput from a summary dict and metadata.
    Extracts signals from the summary automatically.
    """
    base_confidence = summary.get("confidence_score", 0)
    if not isinstance(base_confidence, (int, float)):
        base_confidence = 0

    ner_date_conflict = bool(
        summary.get("_ner_effective_date_conflict") or
        summary.get("_ner_deadline_conflict")
    )
    ner_filled_date = bool(
        summary.get("_ner_filled_effective_date") or
        summary.get("_ner_filled_compliance_deadline")
    )

    why_it_matters = (summary.get("why_it_matters") or "").lower()
    no_action = "no immediate action" in why_it_matters or "no action required" in why_it_matters

    return RouterInput(
        summary=summary,
        doc_type=doc_type,
        base_confidence=int(base_confidence),
        ner_delta=ner_delta,
        ner_date_conflict=ner_date_conflict,
        ner_filled_date=ner_filled_date,
        why_it_matters_says_no_action=no_action,
    )


def routing_label(decision: RoutingDecision) -> str:
    """Human-readable label for the dashboard."""
    return {
        RoutingDecision.APPROVED: "Approved",
        RoutingDecision.REVIEW: "Needs Review",
        RoutingDecision.ESCALATE: "Escalate",
        RoutingDecision.DISMISS: "No Action",
    }.get(decision, decision.value)


def routing_colour(decision: RoutingDecision) -> str:
    """Hex colour for dashboard display."""
    return {
        RoutingDecision.APPROVED: "#27ae60",
        RoutingDecision.REVIEW: "#e67e22",
        RoutingDecision.ESCALATE: "#e74c3c",
        RoutingDecision.DISMISS: "#95a5a6",
    }.get(decision, "#7f8c8d")
