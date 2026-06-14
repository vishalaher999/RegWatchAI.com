# Partner Outreach Follow-Up — v1 (Day 35)

**Status:** Drafts only. Per build rules, RegWatch/Claude does not send
emails on the user's behalf. As of Day 35, no outreach from
`docs/Design-Partner-Profiles-v1.md` (Day 27) has been confirmed sent — these
are templates ready to use, whether as a first outreach or a follow-up to one
already sent.

**Why now:** Day 27's drafts described F3's impact-mapping output (policy
section <-> regulation, HIGH/MEDIUM/LOW/N/A) at 73.3% eval. Since then, F4
(Days 31-35) added the next visible step: an auto-drafted compliance task
with owner/due date, a human-approval gate, and a full audit trail. That's a
materially bigger demo than Day 27 had — "here's what changed and here's the
task it generated for you" is a more concrete pitch than "here's an impact
classification."

---

## Template A — First Outreach (if Day 27's drafts were never sent)

Use Day 27's "Outreach Email Draft #1 / #2" as-is (`docs/Design-Partner-Profiles-v1.md`)
— they're still accurate and don't need the F4 update for a first contact.
The F4 demo is a strong thing to show *during* the 30-minute conversation,
not something to lead with in a cold email.

---

## Template B — Follow-Up (if a Day 27 draft was sent and there's been no reply, or partner said "maybe later")

**Subject:** Quick update — the tool now goes one step further

> Hi [Name],
>
> Following up on my note from a couple weeks back about the compliance
> monitoring tool I'm building. Since then I've added the next piece: when a
> new rule is flagged as high-impact against one of your policies, the tool
> now drafts an actual task — what to review, who owns it, and a due date
> tied to the regulation's compliance deadline — and nothing gets created
> without a human approving it first. There's also a full audit trail
> (model version, who approved, any later edits) for exam prep.
>
> Still genuinely just looking for 30 minutes of "would this be useful or am
> I solving the wrong problem" feedback — no pitch, free to use either way.
>
> Let me know if a quick call still makes sense on your end.
>
> Thanks,
> [Your name]

---

## Template C — Follow-Up (partner said yes / scheduled, confirming before the call)

**Subject:** Confirming our chat — what I'll show you

> Hi [Name],
>
> Looking forward to our conversation on [date/time]. To make the most of
> the 30 minutes, I'll walk through:
>
> 1. A sample regulation update (Fed/CFPB/OCC/FDIC/FinCEN) and its 2-minute
>    summary.
> 2. How it maps to a sample policy section (BSA/AML or Fair Lending) and
>    why it's flagged High/Medium/Low impact.
> 3. The compliance task it drafts from that — owner, due date, and the
>    approval step before anything becomes "live."
>
> If there's a specific regulation or policy area that's top of mind for
> your team right now, let me know and I can try to use something close to
> that as the example.
>
> Thanks,
> [Your name]

---

## PM Note

The Day 27 note about not over-promising the eval number still applies —
none of these templates cite the 80% F3 accuracy gate or F4's structural
eval pass rate. The F4 addition (task + approval + audit trail) is described
by *what it does*, which is demonstrable live, rather than by a metric the
partner has no context to evaluate.

**Open item carried into Day 35's exit-gate check:** the Week 5 exit gate
calls for "at least 1 design partner reply or follow-up sent." As of this
writing, that hasn't happened yet — these templates exist so it *can* happen,
but sending one is a decision for the user, not something done as part of
this build session.
