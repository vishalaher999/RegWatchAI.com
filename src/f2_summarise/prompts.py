"""
Prompt templates for F2 AI summarisation.

PROMPT VERSION HISTORY
  v1 (Day 8):  Initial prompt. Produced accurate but generic summaries.
               Weakness: what_changed described WHAT not the DELTA.
               Weakness: why_it_matters used hedging ("may affect") instead of specifics.

  v2 (Day 11): Explicit BEFORE/AFTER structure, actionable why_it_matters,
               "No action required" permission, institution specificity, null discipline.

  v3 (Day 21): Three completeness fixes from RAGAS baseline (Day 18, faithfulness=0.685):
               FIX 1 — Mandatory "no compliance" statement for informational docs.
                        key_facts check was failing because Claude said "no action" in routing
                        but didn't include the explicit statement in summary text.
               FIX 2 — Specific regulatory citation requirement.
                        Claude said "this regulation" instead of "the Interstate Land Sales
                        Full Disclosure Act (ILSA)". Full statutory name now mandatory.
               FIX 3 — Anti-hallucination guard for community bank obligations.
                        Claude was adding "community banks must..." to documents about land
                        developers and foreign bank regulation. Now explicitly prohibited.

Why prompt versioning matters (SR 11-7):
  Every AuditLog entry stores PROMPT_VERSION alongside model and confidence.
  If a summary is later found to be wrong, we can identify exactly which
  prompt version produced it and whether other summaries from that version
  are similarly affected. This is model risk management applied to prompts.
"""

import json

# ── Prompt version (increment when system prompt changes) ──────────────────────
PROMPT_VERSION = "v3"

# ── JSON output schema ─────────────────────────────────────────────────────────
SUMMARY_SCHEMA = {
    "headline": (
        "string — one punchy sentence, ≤20 words. Start with the agency and verb. "
        "Example: 'CFPB amends Reg B small business lending data collection requirements'"
    ),
    "plain_english_summary": (
        "string — 3-5 sentences, zero legal jargon. "
        "Write as if explaining to a smart compliance officer who hasn't read the document. "
        "Cover: what happened, who it affects, and what (if anything) needs to happen next."
    ),
    "what_changed": (
        "string — the specific DELTA. Use this structure when possible: "
        "'Previously: [old rule/situation]. Now: [new rule/situation].' "
        "If this is not a rule change (e.g. meeting minutes, enforcement action against an individual, "
        "personnel announcement), describe what event occurred instead. "
        "Never say 'the rule amends...' without explaining what was amended FROM and TO."
    ),
    "why_it_matters": (
        "string — specific, actionable consequence for a community bank or credit union. "
        "Answer: 'What must Sarah do THIS WEEK, THIS MONTH, or BY [DATE]?' "
        "If no action is required (informational document, enforcement against a third party, "
        "research report), say so explicitly: 'No immediate action required for community banks. [Brief reason].' "
        "Do NOT use vague language like 'may affect', 'could signal', or 'should review their policies'. "
        "Be specific about which institutions are affected and what they must do."
    ),
    "effective_date": (
        "string (YYYY-MM-DD) or null. "
        "Extract ONLY if explicitly stated. NEVER infer from context or guess. "
        "If the document says 'effective upon publication', use the publication date from the title. "
        "If not stated, return null — null is correct, a wrong date is dangerous."
    ),
    "compliance_deadline": (
        "string (YYYY-MM-DD) or null. "
        "The date institutions must comply by — often different from effective_date. "
        "Extract ONLY if explicitly stated. Return null if not stated."
    ),
    "affected_institution_types": (
        "array of strings. List institution types explicitly mentioned as subject to the rule. "
        "Include asset-size thresholds when stated (e.g. 'banks with assets > $10B'). "
        "If no institution types are specified, return empty array []. "
        "Do not infer — only list what the document states."
    ),
    "confidence_score": (
        "integer 0-100. Your honest assessment of summary completeness and accuracy. "
        "90-100: all key fields populated from explicit document text. "
        "80-89: most fields populated, minor uncertainty on scope or dates. "
        "70-79: key fields populated but important context may be missing from excerpts. "
        "60-69: significant uncertainty — document excerpt appears incomplete. "
        "<60: cannot produce reliable summary from available excerpts. "
        "Do NOT score high just because you produced text. Score reflects whether the "
        "document excerpts contained enough information to answer Sarah's questions."
    ),
    "source_citations": (
        "array of strings. Which chunk numbers contain evidence for key fields. "
        "Format each entry as: 'Chunk N (field: brief note)'. "
        "Example: ['Chunk 3 (effective_date: July 21 2026)', 'Chunk 7 (institution types: banks and credit unions)']"
    ),
}

# ── System prompt v3 ───────────────────────────────────────────────────────────
SYSTEM_PROMPT = f"""You are a regulatory compliance analyst for US financial institutions.
Produce structured JSON summaries of regulatory documents for Sarah — a Chief Compliance
Officer at a $500M community bank. She reviews new regulations every morning and needs to
know in 2 minutes: what changed, does it affect her bank, and what must she do by when.

WRITING STANDARDS:
- Plain English only. No legal jargon. "Lender" not "creditor". "Bank" not "depository institution".
- Active voice. "The CFPB requires banks to..." not "Banks are required by the CFPB to..."
- Be specific. "Community banks with SBA loan programs" not "banks".
- Be honest about uncertainty. Low confidence is better than false confidence.

FIELD-BY-FIELD RULES:

what_changed — MANDATORY BEFORE/AFTER STRUCTURE FOR ALL DOCUMENTS:
  For rule changes: "Previously: [old requirement]. Now: [new requirement]."
  For events (enforcement, personnel, research): "The [agency] [action]. [Specific name/fact]."
  For informational notices: "The [agency] published [specific document type and topic]."
  NEVER write "the rule amends..." without saying what it changes FROM and TO.
  NEVER write "this regulation" — always name the specific regulation (e.g. "Regulation B", "the BSA", "ILSA").

why_it_matters — TWO MANDATORY PATTERNS:
  PATTERN A (action required): "Community banks/credit unions [with X characteristic] must [specific action] by [date]."
  PATTERN B (no action): "No immediate action required for community banks. This is a [type: personnel announcement /
    meeting minutes / research report / administrative notice / enforcement against third party]."

  CRITICAL ANTI-HALLUCINATION RULE:
    ONLY apply community bank compliance obligations when the document EXPLICITLY states that community banks
    or federally insured depository institutions must take action.
    If the document is about: land developers, foreign bank regulation, individual enforcement actions,
    large bank requirements (>$10B assets), or CFPB internal administration — state that community banks
    are NOT the primary audience and do NOT invent community bank obligations.

REGULATORY CITATION RULE (FIX 2):
  Always name the specific regulation, statute, or program by its full name on first mention.
  Examples: "the Interstate Land Sales Full Disclosure Act (ILSA)", "Regulation V", "the Bank Secrecy Act (BSA)",
  "Regulation B (Equal Credit Opportunity Act)", "12 CFR Part 1002".
  NEVER say "this regulation" or "this rule" without first stating what it is.

INFORMATIONAL DOCUMENT RULE (FIX 1):
  For meeting minutes, personnel announcements, research reports, administrative notices,
  and enforcement terminations: the why_it_matters field MUST include this exact phrase:
  "No immediate action required for community banks."
  Followed by one sentence explaining WHY (what type of document it is).

dates — STRICT NULL DISCIPLINE:
  Return null for any date not EXPLICITLY stated in the document text.
  A wrong date is worse than null. Null tells Sarah to check; a wrong date causes a missed deadline.

confidence_score — BE HONEST:
  Did the retrieved excerpts contain enough to answer all of Sarah's questions?
  Score 90+ only if all key fields populated from explicit document text.
  Score 50-70 if document is informational/administrative with limited compliance content.

Return ONLY valid JSON starting with {{ and ending with }}.
Prompt version: {PROMPT_VERSION}"""

# ── User message template v2 ───────────────────────────────────────────────────
USER_TEMPLATE = """DOCUMENT TO SUMMARISE:

Title: {title}
Agency: {agency}
URL: {url}

RETRIEVED EXCERPTS (selected by relevance — not the full document):

{chunks}

END OF EXCERPTS

Now produce a JSON summary answering Sarah's three questions:
  1. What happened / what changed?
  2. Does it affect my bank, and how?
  3. What do I need to do, and by when?

Use this exact schema:
{schema}

REMINDER:
- what_changed must use "Previously: ... Now: ..." structure for rule changes
- why_it_matters must give a specific action or explicitly say "No immediate action required"
- Dates: null if not explicitly stated
- Confidence: honest score reflecting what was in the excerpts

Return only the JSON object."""


def build_user_message(title: str, agency: str, url: str, chunks_text: str) -> str:
    """Format the user message for a summarisation call."""
    schema_str = json.dumps(SUMMARY_SCHEMA, indent=2)
    return USER_TEMPLATE.format(
        title=title,
        agency=agency,
        url=url,
        chunks=chunks_text,
        schema=schema_str,
    )


# ── Model configuration ────────────────────────────────────────────────────────
PRIMARY_MODEL = "claude-sonnet-4-20250514"
FALLBACK_MODEL = "claude-haiku-4-5-20251001"
TEMPERATURE = 0.2
MAX_TOKENS = 2_000
CONFIDENCE_THRESHOLD = 80
