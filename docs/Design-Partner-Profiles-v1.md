# Design Partner Profiles — v1 (Day 27)

**Status:** Drafts only. No outreach has been sent. Per build rules, Claude
does not send emails on the user's behalf — these are templates for the user
to review, edit, and send manually (or decide not to).

**Why now:** F3 (the core/moat feature) is at 73.3% on its eval — not yet at
the 80% gate, but far enough along to show a real demo: upload a policy PDF,
get back impact-mapped regulation matches with HIGH/MEDIUM/LOW/N/A labels and
plain-English rationale. A design partner conversation now can shape Week 5-6
(F4 task generation, React UI) around what a real compliance officer actually
needs — before those are built, not after.

---

## What "design partner" means here

Not a sale. An offer: free early access in exchange for 30 minutes of
feedback on whether the impact-mapping output is *useful and trustworthy* to
a compliance officer — and a willingness to be a reference/case study later
if it goes well. The ask is small and the value (free compliance-monitoring
tool, early input into the roadmap) is real even at this stage.

---

## Candidate Profile Criteria

Target: **community banks, $100M-$2B in assets**, no in-house compliance
software team (so an early tool has room to add value rather than compete
with an existing vendor relationship), and a named compliance officer or risk
manager (the Sarah/Mike personas) who is reachable.

---

## 5 Design Partner Profiles

### 1. Small Mutual Savings Bank (~$300M assets)
- **Why a fit:** Mutuals are often under-resourced for compliance — typically
  1-2 person compliance function wearing many hats. BSA/AML and Fair Lending
  (ECOA/HMDA) are exactly the regulation areas F3's fixtures cover.
- **Pain point:** Compliance officer manually checks Federal Register and
  agency emails, then re-reads policy manually to see what needs updating —
  the exact F1→F3 pipeline.
- **How to find:** State banking association member directories list mutuals
  by asset size; many publish compliance contact info on their "About"
  pages for CRA purposes.

### 2. De Novo / Recently Chartered Community Bank (<5 years old, ~$150-500M)
- **Why a fit:** Newly chartered banks are actively building out policy
  libraries from scratch and are more likely to be open to new tools (less
  entrenched vendor relationships, leaner ops).
- **Pain point:** Building a BSA/AML and Fair Lending policy library for the
  first time, with no historical "what changed" tracking — F3's
  policy-to-regulation mapping is directly useful for "did we cover this?"
  checks during exam prep.
- **How to find:** FDIC's "Establishing and Planning a New Bank" list /
  recent charter announcements (public FDIC data).

### 3. Bank Holding Company with Multiple Small Subsidiary Banks (~$500M-$1B combined)
- **Why a fit:** Multi-bank holding companies often run ONE compliance
  function across several charters with different (sometimes inconsistent)
  policy documents — a natural fit for F3's multi-policy upload + per-policy
  impact mapping.
- **Pain point:** Keeping N separate policy manuals in sync with the same
  regulatory changes; today this is manual cross-referencing.
- **How to find:** SEC/FDIC holding company filings list subsidiary banks and
  often a group risk/compliance officer contact.

### 4. Credit Union (Community Charter, ~$200-800M assets)
- **Why a fit:** Credit unions face largely the same consumer-protection
  regulation set (TILA/RESPA/ECOA/HMDA via NCUA rather than the bank
  regulators) — F3's hybrid search + impact classifier logic transfers with
  minimal change, and it's a useful test of whether the approach generalizes
  beyond the 3 bank-specific fixtures.
- **Pain point:** Same "manual cross-reference" pain, but also a useful
  signal for whether RegWatch's agency coverage (Fed/CFPB/OCC/FDIC/FinCEN)
  needs an NCUA feed added — a real roadmap input.
- **How to find:** NCUA's credit union directory by asset size and charter
  type.

### 5. Independent Community Bank with a Recent Consent Order / MRA (Matters Requiring Attention)
- **Why a fit:** A bank that has recently been cited for a compliance gap
  (publicly disclosed via FDIC/OCC enforcement action databases) has the
  strongest immediate motivation — leadership is actively looking for tools
  that demonstrate proactive monitoring to examiners.
- **Pain point:** Needs to show examiners a documented, auditable process for
  "we saw this regulatory change and assessed its impact on our policies" —
  which is precisely F3 + F5's audit trail value proposition.
- **How to find:** FDIC/OCC/Fed public enforcement action databases (public
  data — consistent with the "public regulatory data only" constraint).
- **Caution:** Approach respectfully — frame as "we built something that
  might help with exactly this kind of documentation," not as exploiting a
  sensitive public record.

---

## Outreach Email Draft #1 — Cold Intro (General)

**Subject:** Early access to a compliance monitoring tool for community banks

> Hi [Name],
>
> I'm building RegWatch AI — a tool that monitors federal banking regulators
> (Fed, CFPB, OCC, FDIC, FinCEN), summarizes new and amended rules in plain
> English, and maps each change against a bank's own policy library to flag
> which specific policy sections may need review (and how urgently).
>
> I'm looking for 2-3 community banks to try an early version and give honest
> feedback — specifically, whether the impact mapping (which policy section,
> which regulation, why it matters, how urgent) is something a compliance
> officer would actually trust and use day-to-day.
>
> It's free during this phase — the ask is about 30 minutes of your time to
> walk through the output together and tell me where it's useful and where
> it's wrong. No commitment beyond that.
>
> Would you be open to a short call in the next couple of weeks?
>
> Thanks,
> [Your name]

---

## Outreach Email Draft #2 — Warmer / Referral or Known Contact

**Subject:** Quick favor — feedback on a compliance tool I'm building

> Hi [Name],
>
> [Optional: "[Mutual connection] suggested I reach out" / context for how you
> know them.]
>
> I've been building a tool aimed at the compliance monitoring workload —
> tracking Fed/CFPB/OCC/FDIC/FinCEN rule changes, summarizing them, and
> flagging which of a bank's existing policies (BSA/AML, Fair Lending, TRID,
> etc.) might need updating because of a specific new rule.
>
> Given your role, I'd really value 30 minutes to show you what it produces
> for a sample policy and get your read on whether it's the kind of thing
> that would actually save time — or whether I'm solving the wrong problem.
> Completely free, no sales pitch — genuinely looking for feedback from
> someone who lives this.
>
> Let me know if you have time in the next couple of weeks — happy to work
> around your schedule.
>
> Thanks,
> [Your name]

---

## PM Note

Both drafts intentionally avoid over-promising on the 73.3% eval number or
any specific accuracy claim — design partners should see the actual output
and judge usefulness themselves, not a marketing stat. If/when F3 clears the
80% gate, that's a good moment to follow up with partners who said "not yet."
