# Day 22 — F3 Begins: Policy Parser v1

**Date:** 2026-06-13
**Feature:** F3 — Policy Impact Mapping (Week 4, Day 1 of 7)
**KM:** #210 OCR / Multimodal (M3) — study topic, not built today
**Status:** Engineering deliverable complete and tested. Product wireframe done.

---

## What Was Built

| File | Change |
|------|--------|
| `src/f3_impact/__init__.py` | New package for F3 |
| `src/f3_impact/extractor.py` | Policy section extractor — parses `SECTION N: TITLE` / `N.M Title` structure into `PolicySection` objects |
| `tests/test_f3_extractor.py` | 3 tests: synthetic sample parsing, multiline body text, all 3 real fixtures |
| `docs/wireframes/policy-library-ux-v1.md` | Product deliverable — upload/organise/version UX for policy library |
| `docs/ARCHITECTURE.md` | New entry for `extractor.py` |

---

## Roadmap v2.2 — Day 22 Columns

| Column | Target | Delivered |
|--------|--------|-----------|
| KM | #210 OCR, M3 | Studied — flagged as future fallback if real client policies are scanned PDFs (not needed for current `.txt` fixtures) |
| Engineering | Policy upload pipeline: PDF/DOCX parsing, section extraction | Section extraction done against `.txt` fixtures (already committed from Day 14B, substitute for "synthetic PDFs" per roadmap note) |
| Product | Policy library management UX (upload, organise, version) | `docs/wireframes/policy-library-ux-v1.md` — 3-screen wireframe + versioning rules |
| Deliverable | Policy parser v1 | `src/f3_impact/extractor.py`, verified on all 3 fixtures |

---

## What the Extractor Does

Parses bank policy text files into `PolicySection` objects — one per `N.M` numbered subsection (e.g. "4.2 Currency Transaction Reporting (CTR)"), each tagged with:
- `policy_name` (filename stem)
- `section_id` ("4.2")
- `section_title` ("Currency Transaction Reporting (CTR)")
- `parent_section` ("SECTION 4: TRANSACTION MONITORING")
- `text` (body content)

This is the granularity Sarah will see in F3's output: "BSA Policy §4.2 needs review" — specific enough to act on, not so granular that every sentence is its own match candidate for Day 23-24 hybrid search.

### Verified Results

```
BSA-AML-Policy: 26 sections
Fair-Lending-ECOA-Policy: 23 sections
TRID-Mortgage-Disclosure-Policy: 23 sections

Total: 72 sections across 3 policies
```

All 3 tests pass:
```
tests/test_f3_extractor.py::test_extract_policy_sections_basic PASSED
tests/test_f3_extractor.py::test_extract_policy_sections_multiline_body PASSED
tests/test_f3_extractor.py::test_extract_policy_library_fixtures PASSED
```

---

## Design Decision: Regex, Not LLM

The extractor uses regex (`^SECTION\s+(\d+):\s*(.+)$` and `^(\d+\.\d+)\s+(.+)$`), not an LLM call.

**Why:** All 3 synthetic policy fixtures follow a consistent, predictable structure. A deterministic parser is free, instant, and fully testable — no eval needed for something that's either correct or not.

**Risk flagged:** Real client policies may not follow this exact format (different numbering schemes, scanned PDFs with no extractable text). The wireframe (`policy-library-ux-v1.md`) includes a "0 sections found" failure state that points to KM #210 (OCR/multimodal) as the future fix. This is a known gap, not a blocker — F3's eval (Days 26-28) runs against the fixtures we control.

---

## A Small Bug Along the Way

First run of `python -m src.f3_impact.extractor` crashed on Windows with:
```
UnicodeEncodeError: 'charmap' codec can't encode character '≥'
```

Cause: TRID Section 5.3 ("Surplus, Shortage, Deficiency") contains "Surplus ≥ $50" — the `≥` character. Windows' default console encoding (cp1252) can't print it.

**Fix:** Added `sys.stdout.reconfigure(encoding="utf-8")` at the top of the `__main__` block. Re-ran — all 72 sections printed cleanly, including the `≥` character.

This is a one-line fix, but worth noting: it's the kind of thing that would silently corrupt output (or crash) in any CLI tool on Windows when policy text contains non-ASCII characters (≥, ≤, §, –, ", "). Worth keeping in mind for Day 23+ when section text gets passed to embedding calls and printed in eval reports.

---

## PM Insight: Why Day 22 Is "Just" Parsing

Day 22 looks small next to Days 23-25 (embedding, matching, classification) — but it's the foundation every later step depends on. If section boundaries are wrong here, every downstream impact mapping points Sarah to the wrong part of her policy. Getting `section_id` and `section_title` right at N.M granularity — tested against all 3 real fixtures, not just one — means Days 23-28 build on solid ground.

The Product wireframe matters too: it forces the data model (`policy_name`, `version`, `section_id`, `parent_section`) to be designed with the eventual UI in mind, including versioning — banks update policies yearly, and F3's mappings need to know which version they were computed against. That's a decision that's much cheaper to make now than to retrofit after Day 28.

---

## Next: Day 23 (when user says "next")

Per roadmap v2.2: Embed policy sections + regulation sections separately (dual-index Pinecone). KM #157 Dense retrieval. Product: Impact dashboard wireframe (High/Med/Low/N/A heatmap). Deliverable: Dual-index vector store.
