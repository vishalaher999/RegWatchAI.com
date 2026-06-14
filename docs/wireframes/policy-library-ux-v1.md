# Policy Library Management UX — F3 Policy Impact Mapping
# Version 1 | Day 22 | Upload, Organise, Version

## Why This Screen Exists

F3 only works if Sarah's policy library is in the system.
This is the front door to the "moat" feature: without policies uploaded
and parsed into sections, there is nothing for regulations to map against.

The UX has three jobs:
  1. Get policies in (upload PDF/DOCX/TXT, parse into sections)
  2. Let Sarah see what's there (library list, section counts, last updated)
  3. Handle versioning (banks update policies yearly — old mappings must
     not silently point at stale text)

─────────────────────────────────────────────────────────────────────
SCREEN 1: POLICY LIBRARY (default view)
─────────────────────────────────────────────────────────────────────

┌────────────────────────────────────────────────────────────────────┐
│  Policy Library                                  [+ Upload Policy]  │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │ BSA-AML-Policy                          v2  Updated Jun 1 2026│ │
│  │ 26 sections parsed   |   Last mapped: Jun 10 2026             │ │
│  │ [View Sections]  [Re-upload new version]  [Download original] │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │ Fair-Lending-ECOA-Policy                v1  Updated Mar 14 2026│ │
│  │ 23 sections parsed   |   Last mapped: never                   │ │
│  │ [View Sections]  [Re-upload new version]  [Download original] │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │ TRID-Mortgage-Disclosure-Policy         v1  Updated Mar 14 2026│ │
│  │ 23 sections parsed   |   Last mapped: never                   │ │
│  │ [View Sections]  [Re-upload new version]  [Download original] │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  Total: 3 policies, 72 sections indexed for impact mapping          │
└────────────────────────────────────────────────────────────────────┘

─────────────────────────────────────────────────────────────────────
SCREEN 2: UPLOAD FLOW
─────────────────────────────────────────────────────────────────────

┌────────────────────────────────────────────────────────────────────┐
│  Upload Policy Document                                             │
│                                                                      │
│  Drop file here, or [Browse Files]                                  │
│  Accepted: PDF, DOCX, TXT                                           │
│                                                                      │
│  Policy name: [BSA-AML-Policy______________]                        │
│  (auto-filled from filename, editable)                              │
│                                                                      │
│  [Upload & Parse]                                                   │
└────────────────────────────────────────────────────────────────────┘

After upload — parse result shown immediately (uses extractor.py):

┌────────────────────────────────────────────────────────────────────┐
│  ✓ Parsed successfully                                              │
│                                                                      │
│  BSA-AML-Policy — 26 sections found                                 │
│                                                                      │
│  SECTION 4: TRANSACTION MONITORING                                  │
│    4.1  Suspicious Activity Identification                          │
│    4.2  Currency Transaction Reporting (CTR)                        │
│    4.3  Monitoring System Requirements                              │
│    ...                                                              │
│                                                                      │
│  [Looks good — Save to Library]  [Re-upload]                        │
└────────────────────────────────────────────────────────────────────┘

If 0 sections found (e.g. scanned PDF, no SECTION/N.M headers detected):

┌────────────────────────────────────────────────────────────────────┐
│  ⚠ Could not detect section structure                              │
│                                                                      │
│  This file may be a scanned/image PDF, or doesn't use the           │
│  "SECTION N: TITLE" / "N.M Title" format RegWatch AI expects.        │
│                                                                      │
│  Future (KM #210, OCR/multimodal): RegWatch AI will OCR scanned      │
│  PDFs automatically. For now:                                        │
│    [Upload a text-based version]  [Contact support]                 │
└────────────────────────────────────────────────────────────────────┘

─────────────────────────────────────────────────────────────────────
SCREEN 3: VIEW SECTIONS (drill-in from library card)
─────────────────────────────────────────────────────────────────────

┌────────────────────────────────────────────────────────────────────┐
│  BSA-AML-Policy v2 — Sections                    [← Back to Library]│
│                                                                      │
│  SECTION 4: TRANSACTION MONITORING                                  │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │ 4.2  Currency Transaction Reporting (CTR)                     │ │
│  │ The Bank shall file a Currency Transaction Report (CTR) for   │ │
│  │ any cash transaction exceeding $10,000...                     │ │
│  │                                                                │ │
│  │ Mapped regulations: none yet                                   │ │
│  └──────────────────────────────────────────────────────────────┘ │
│  (one card per N.M section — this is where impact results from      │
│   Day 24-25 will appear: "2 regulations mapped — 1 High impact")     │
└────────────────────────────────────────────────────────────────────┘

─────────────────────────────────────────────────────────────────────
VERSIONING RULES
─────────────────────────────────────────────────────────────────────

  - Re-uploading a policy with the same name creates a new version
    (v1 -> v2). The old version is kept (not deleted) for audit history.
  - Existing impact mappings stay attached to the version they were
    computed against. If Sarah re-uploads a policy, mappings show
    "Computed against v1 — re-run mapping for v2" until she re-runs F3.
  - AuditLog records every upload: action=INGEST (reuse existing enum),
    payload = {policy_name, version, section_count, uploaded_by}.

─────────────────────────────────────────────────────────────────────
IMPLEMENTATION NOTE
─────────────────────────────────────────────────────────────────────

Day 22 scope: extractor.py only (parsing logic, tested against the
3 .txt fixtures). This wireframe describes the target UX for when
F3 gets a UI (Week 6, React frontend per CLAUDE.md).

For now (Days 22-28), F3 work happens against the fixture policies
directly — no upload UI needed yet. This wireframe exists so the
data model (policy_name, version, section_id, section_title,
parent_section, text) is designed with the eventual UI in mind,
per build rule: "check ALL 4 roadmap columns" — Product deliverable
for Day 22 is this UX design, not a working upload screen.
