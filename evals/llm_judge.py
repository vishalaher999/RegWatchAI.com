"""
LLM-as-judge for F2 summary quality — Day 20.

KM concept: #255 LLM-as-judge

Uses claude-haiku to score summary quality on 4 compliance-specific criteria.
Calibrated against hand-labeled golden set entries to verify judge reliability.

Why LLM-as-judge vs keyword matching (Day 18)?
  Keyword matching: fast, free, deterministic.
    Miss: "Regulation B is amended" contains "amend" → PASS
    Pass: "Regulation B requires action" doesn't contain "amend" → FAIL
    But both are saying the same thing. Keywords miss semantic equivalents.

  LLM judge: slower, costs money, probabilistic.
    Understands: "The Bureau updated Regulation B" = same as "Regulation B was amended"
    Understands: "No immediate action needed" = same as "No compliance required"
    More accurate for nuanced quality — especially BEFORE/AFTER structure quality.

The calibration step (calibrate_judge.py) verifies that the LLM judge
agrees with human labels >= 80% of the time. Below that, the judge
is not trustworthy for automation.

Model: claude-haiku-4-5-20251001
  - 10x cheaper than Sonnet — right tool for evaluation calls
  - Temperature 0.1 — near-deterministic scoring
  - Structured JSON output — scores are machine-parseable
"""

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

_ENV_PATH = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH, override=True)

JUDGE_MODEL = "claude-haiku-4-5-20251001"
JUDGE_TEMPERATURE = 0.1    # Near-deterministic for consistent scoring
JUDGE_MAX_TOKENS = 800


# ── Scoring rubric ─────────────────────────────────────────────────────────────

JUDGE_SYSTEM_PROMPT = """You are a compliance quality evaluator for community bank regulatory summaries.
Your job is to score AI-generated regulatory summaries on 4 criteria.
Be strict and consistent. Use the scoring rubric exactly as specified.
Return ONLY valid JSON — no preamble, no explanation outside the JSON."""

JUDGE_RUBRIC = """
SCORING RUBRIC (each criterion: 0.0, 0.5, or 1.0)

1. FAITHFULNESS (0-1)
   Does the summary only state facts supported by the source document?
   1.0 = All claims have clear support in the document text
   0.5 = Most claims supported, 1-2 minor unsupported inferences
   0.0 = Summary invents facts not in the document (dates, institution types, obligations)

   EXAMPLE 0.0 (hallucination): Document says "Fed issued meeting minutes."
   Summary says "Community banks must update their rate risk models by Q3."
   → 0.0 (no compliance obligation stated in document)

   EXAMPLE 1.0: Document says "Rule takes effect July 21, 2026."
   Summary says "Effective date: July 21, 2026."
   → 1.0 (directly supported)

2. ACTION_CLARITY (0-1)
   Does why_it_matters clearly state what compliance officers must do (or not do)?
   1.0 = Specific action with timeline, OR explicit "no action required + reason"
   0.5 = Action implied but not explicit, or action stated without timeline
   0.0 = Vague ("may affect banks") or generic ("review your policies")

   EXAMPLE 0.0: "New Fed leadership may signal changes in monetary policy."
   EXAMPLE 1.0: "Community banks must evaluate SPCP programs by July 21, 2026."
   EXAMPLE 1.0: "No immediate action required. This is a personnel announcement."

3. DATE_PRECISION (0-1)
   Are dates correctly extracted or correctly left null?
   1.0 = Correct date extracted from document, OR null when no date in document
   0.5 = Date format incorrect, or date extracted from wrong context
   0.0 = Date hallucinated (date stated but not in document), or null when date IS in document

4. WHAT_CHANGED_QUALITY (0-1)
   Does what_changed describe the actual delta (before → after)?
   1.0 = Clear BEFORE/AFTER or "Previously: X. Now: Y." structure
   0.5 = Describes the change but without explicit before state
   0.0 = Only describes the current state ("Regulation B requires...") with no delta
   N/A = Document is not a rule change (meeting minutes, personnel, research) → score 1.0 by default
"""

JUDGE_USER_TEMPLATE = """Rate this regulatory summary on the 4 criteria.

DOCUMENT TITLE: {title}
AGENCY: {agency}

DOCUMENT EXCERPT (what the AI had available):
{context}

AI-GENERATED SUMMARY:
Headline: {headline}
Plain English: {plain_english}
What Changed: {what_changed}
Why It Matters: {why_it_matters}
Effective Date: {effective_date}
Compliance Deadline: {compliance_deadline}
Affected Institutions: {institutions}

{rubric}

Return JSON with this exact structure:
{{
  "faithfulness": 0.0 or 0.5 or 1.0,
  "action_clarity": 0.0 or 0.5 or 1.0,
  "date_precision": 0.0 or 0.5 or 1.0,
  "what_changed_quality": 0.0 or 0.5 or 1.0,
  "faithfulness_reason": "one sentence explaining the score",
  "action_clarity_reason": "one sentence explaining the score",
  "overall_quality": 0.0 to 1.0,
  "biggest_issue": "the single most important thing to fix, or null if none"
}}"""


# ── Dataclasses ────────────────────────────────────────────────────────────────

@dataclass
class JudgeScore:
    """Scores from the LLM judge for one summary."""
    faithfulness: float
    action_clarity: float
    date_precision: float
    what_changed_quality: float
    overall_quality: float
    faithfulness_reason: str = ""
    action_clarity_reason: str = ""
    biggest_issue: Optional[str] = None
    judge_model: str = JUDGE_MODEL
    cost_estimate_usd: float = 0.0

    @property
    def composite(self) -> float:
        """Weighted composite matching our RAGAS eval weights."""
        return (
            self.faithfulness * 0.40 +
            self.action_clarity * 0.30 +
            self.date_precision * 0.20 +
            self.what_changed_quality * 0.10
        )


# ── Judge runner ───────────────────────────────────────────────────────────────

def _get_client():
    """Return Anthropic client with API key from .env."""
    import anthropic
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key or "your_" in api_key:
        raise ValueError("ANTHROPIC_API_KEY not set in .env")
    return anthropic.Anthropic(api_key=api_key)


def judge_summary(
    title: str,
    agency: str,
    context_text: str,  # The chunks that were passed to Claude
    summary: dict,
) -> JudgeScore:
    """
    Run the LLM judge on one summary.
    Returns a JudgeScore with all 4 criteria scored.
    """
    client = _get_client()

    institutions = ", ".join(summary.get("affected_institution_types") or []) or "Not specified"

    user_message = JUDGE_USER_TEMPLATE.format(
        title=title,
        agency=agency,
        context=context_text[:3000],  # Limit context to keep prompt manageable
        headline=summary.get("headline", "N/A"),
        plain_english=summary.get("plain_english_summary", "N/A")[:500],
        what_changed=summary.get("what_changed", "N/A")[:400],
        why_it_matters=summary.get("why_it_matters", "N/A")[:400],
        effective_date=summary.get("effective_date") or "null",
        compliance_deadline=summary.get("compliance_deadline") or "null",
        institutions=institutions[:200],
        rubric=JUDGE_RUBRIC,
    )

    t0 = time.time()
    response = client.messages.create(
        model=JUDGE_MODEL,
        max_tokens=JUDGE_MAX_TOKENS,
        temperature=JUDGE_TEMPERATURE,
        system=JUDGE_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )
    elapsed = time.time() - t0

    raw = response.content[0].text.strip()

    # Parse JSON response
    try:
        # Strip markdown fences if present
        import re
        raw = re.sub(r'^```(?:json)?\s*', '', raw)
        raw = re.sub(r'\s*```$', '', raw).strip()
        data = json.loads(raw)
    except json.JSONDecodeError:
        # Fallback if JSON is malformed
        return JudgeScore(
            faithfulness=0.5, action_clarity=0.5,
            date_precision=0.5, what_changed_quality=0.5,
            overall_quality=0.5,
            faithfulness_reason="JSON parse error",
            biggest_issue="Judge response was not valid JSON",
        )

    # Estimate cost: Haiku is ~$0.25/1M input + $1.25/1M output tokens
    input_tokens = len(user_message) // 4
    output_tokens = len(raw) // 4
    cost = (input_tokens * 0.00000025) + (output_tokens * 0.00000125)

    def _safe_float(val, default: float = 0.5) -> float:
        """Robustly extract a float 0-1 from a value that may be a string with explanation."""
        if isinstance(val, (int, float)):
            return max(0.0, min(1.0, float(val)))
        if isinstance(val, str):
            try:
                return max(0.0, min(1.0, float(val.strip())))
            except ValueError:
                pass
            import re
            # Look for explicit score values in the string
            matches = re.findall(r'\b(0\.0|0\.5|1\.0)\b', val)
            if matches:
                return float(matches[0])
            matches = re.findall(r'\b([01]\.\d+|\d+\.\d+)\b', val)
            if matches:
                return max(0.0, min(1.0, float(matches[0])))
        return default

    return JudgeScore(
        faithfulness=_safe_float(data.get("faithfulness", 0.5)),
        action_clarity=_safe_float(data.get("action_clarity", 0.5)),
        date_precision=_safe_float(data.get("date_precision", 0.5)),
        what_changed_quality=_safe_float(data.get("what_changed_quality", 0.5)),
        overall_quality=_safe_float(data.get("overall_quality", 0.5)),
        faithfulness_reason=str(data.get("faithfulness_reason", "")),
        action_clarity_reason=str(data.get("action_clarity_reason", "")),
        biggest_issue=data.get("biggest_issue"),
        judge_model=JUDGE_MODEL,
        cost_estimate_usd=round(cost, 5),
    )
