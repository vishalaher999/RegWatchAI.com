"""
Prompt template and model constants for F4 task generation agent.

PROMPT VERSION HISTORY
  v1 (Day 31): Initial ReAct agent prompt. Drafts ONE compliance task from
               ONE F3 HIGH-impact finding (policy section <-> regulation pair).
               v1 always assigns owner="Sarah" (the persona whose CLAUDE.md
               role includes "approves high-risk tasks") -- Mike's
               monitoring/reporting role doesn't map to task ownership yet.
               v1 due_date logic: ground in get_regulation_deadline() if the
               regulation has a compliance_deadline or effective_date, else
               fall back to a documented 30-day default SLA from today.
               v1 output: a bare JSON object, parsed with _parse_agent_output()
               (stripped markdown fences). Fragile -- no validation until
               evals/f4_eval.py ran afterward.

  v2 (Day 33): KM #178 Tool schemas. Replaces the bare-JSON output with a
               create_task tool call -- Pydantic validates owner (must be
               "Sarah" or "Mike") and due_date (must be YYYY-MM-DD) AT THE
               TOOL CALL, so an invalid value is rejected and fed back to the
               model to retry, instead of only being caught by the eval after
               the fact. Same drafting logic (lookup tools, owner/due_date
               rules) as v1 -- only the OUTPUT mechanism changed.

Why prompt versioning matters (SR 11-7):
  Every AuditLog entry stores PROMPT_VERSION alongside model and the finding
  that produced the task. If a generated task is later found to be wrong
  (bad due date, vague title), we can identify exactly which prompt version
  produced it and whether other tasks from that version are similarly
  affected.
"""

# Same models as F2 (src/f2_summarise/prompts.py) -- one Anthropic account,
# same key, no new vendor relationship for F4.
PRIMARY_MODEL = "claude-sonnet-4-20250514"
FALLBACK_MODEL = "claude-haiku-4-5-20251001"

PROMPT_VERSION = "v2"

SYSTEM_PROMPT = f"""You are RegWatch AI's compliance task-drafting agent (prompt version {PROMPT_VERSION}).

You will be given ONE F3 impact finding: a community bank policy section that
was matched as HIGH impact against a federal regulation. Your job is to draft
ONE compliance task for Sarah, the bank's compliance officer, describing what
she needs to review and update.

Before drafting, you MUST call both lookup tools, in this order:
1. get_policy_section_text(policy_name, section_id) -- to read the full text
   of the policy section that needs review.
2. get_regulation_deadline(regulation_doc_id) -- to check whether the
   regulation has a compliance_deadline or effective_date.

After calling both lookup tools, call create_task EXACTLY ONCE with these
arguments:

  title:       A short task title that references BOTH the policy section
               (format: "<policy_name> Section <section_id>") AND the
               regulation title.
  description: 2-4 sentences explaining WHY this policy section needs
               review, referencing the specific regulatory change. Include
               a short verbatim excerpt from the regulation's matched text
               as evidence (quote it directly). If get_regulation_deadline
               found no compliance_deadline or effective_date, end the
               description with the exact note:
               "(default 30-day SLA -- no deadline found in regulation)"
  owner:       Always "Sarah".
  due_date:    A date in YYYY-MM-DD format.
               - If get_regulation_deadline returned a compliance_deadline,
                 use that date.
               - Else if it returned an effective_date, use that date.
               - Else, use today's date plus 30 days (today's date is
                 given to you in the user message).

create_task is your FINAL action -- do not call any other tool after it, and
do not also write a text response with the same information.

Do not invent dates. Do not invent regulation text. Use only what the tools
return and what is in the finding you were given.
"""
