"""
Generate styled PDF study notes from F1-AUDIT.md
Run: python scripts/generate_f1_audit_pdf.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether, PageBreak
)
from reportlab.platypus import Flowable
from reportlab.lib.colors import HexColor

# ── Colours ───────────────────────────────────────────────────────────────────
NAVY       = HexColor("#1a3a5c")
BLUE       = HexColor("#2980b9")
LIGHT_BLUE = HexColor("#eaf4fb")
YELLOW_BG  = HexColor("#fff9c4")
GREEN_BG   = HexColor("#e8f5e9")
ORANGE_BG  = HexColor("#fff3e0")
RED_BG     = HexColor("#ffebee")
CODE_BG    = HexColor("#f5f5f5")
WHITE      = colors.white
DARK_TEXT  = HexColor("#212121")
GREY_TEXT  = HexColor("#555555")
BORDER     = HexColor("#bbdefb")
GREEN_SCORE = HexColor("#388e3c")
ORANGE_SCORE = HexColor("#f57c00")
RED_SCORE   = HexColor("#c62828")

# ── Page setup ────────────────────────────────────────────────────────────────
OUTPUT_PATH = r"C:\Users\visha\OneDrive\Documents\Senior AI\RegWatch AI\RegWatchAI.com\notes\F1-AUDIT.pdf"
MD_PATH     = r"C:\Users\visha\OneDrive\Documents\Senior AI\RegWatch AI\RegWatchAI.com\notes\F1-AUDIT.md"

def make_styles():
    base = getSampleStyleSheet()

    styles = {}

    styles["cover_title"] = ParagraphStyle(
        "cover_title",
        fontName="Helvetica-Bold",
        fontSize=26,
        textColor=WHITE,
        alignment=TA_CENTER,
        spaceAfter=6,
        leading=32,
    )
    styles["cover_sub"] = ParagraphStyle(
        "cover_sub",
        fontName="Helvetica",
        fontSize=12,
        textColor=HexColor("#bbdefb"),
        alignment=TA_CENTER,
        spaceAfter=4,
        leading=16,
    )
    styles["section_header"] = ParagraphStyle(
        "section_header",
        fontName="Helvetica-Bold",
        fontSize=16,
        textColor=WHITE,
        spaceAfter=8,
        spaceBefore=18,
        leading=20,
    )
    styles["subsection"] = ParagraphStyle(
        "subsection",
        fontName="Helvetica-Bold",
        fontSize=13,
        textColor=NAVY,
        spaceAfter=6,
        spaceBefore=14,
        leading=16,
    )
    styles["h3"] = ParagraphStyle(
        "h3",
        fontName="Helvetica-Bold",
        fontSize=11,
        textColor=BLUE,
        spaceAfter=4,
        spaceBefore=10,
        leading=14,
    )
    styles["body"] = ParagraphStyle(
        "body",
        fontName="Helvetica",
        fontSize=9.5,
        textColor=DARK_TEXT,
        leading=14,
        spaceAfter=4,
        alignment=TA_JUSTIFY,
    )
    styles["body_bold"] = ParagraphStyle(
        "body_bold",
        fontName="Helvetica-Bold",
        fontSize=9.5,
        textColor=DARK_TEXT,
        leading=14,
        spaceAfter=2,
    )
    styles["file_label"] = ParagraphStyle(
        "file_label",
        fontName="Helvetica-Bold",
        fontSize=10,
        textColor=NAVY,
        leading=14,
        spaceAfter=2,
    )
    styles["code"] = ParagraphStyle(
        "code",
        fontName="Courier",
        fontSize=8,
        textColor=HexColor("#263238"),
        leading=12,
        spaceAfter=2,
        leftIndent=8,
    )
    styles["label"] = ParagraphStyle(
        "label",
        fontName="Helvetica-Bold",
        fontSize=8.5,
        textColor=NAVY,
        leading=12,
        spaceAfter=1,
    )
    styles["value"] = ParagraphStyle(
        "value",
        fontName="Helvetica",
        fontSize=9,
        textColor=DARK_TEXT,
        leading=13,
        spaceAfter=3,
        leftIndent=12,
    )
    styles["bullet"] = ParagraphStyle(
        "bullet",
        fontName="Helvetica",
        fontSize=9.5,
        textColor=DARK_TEXT,
        leading=14,
        spaceAfter=2,
        leftIndent=16,
        bulletIndent=4,
    )
    styles["good_label"] = ParagraphStyle(
        "good_label",
        fontName="Helvetica-Bold",
        fontSize=9.5,
        textColor=HexColor("#1b5e20"),
        leading=13,
        spaceAfter=2,
    )
    styles["weak_label"] = ParagraphStyle(
        "weak_label",
        fontName="Helvetica-Bold",
        fontSize=9.5,
        textColor=HexColor("#e65100"),
        leading=13,
        spaceAfter=2,
    )
    styles["missing_label"] = ParagraphStyle(
        "missing_label",
        fontName="Helvetica-Bold",
        fontSize=9.5,
        textColor=HexColor("#b71c1c"),
        leading=13,
        spaceAfter=2,
    )
    styles["qa_q"] = ParagraphStyle(
        "qa_q",
        fontName="Helvetica-Bold",
        fontSize=10,
        textColor=NAVY,
        leading=14,
        spaceAfter=3,
        spaceBefore=10,
    )
    styles["qa_a"] = ParagraphStyle(
        "qa_a",
        fontName="Helvetica",
        fontSize=9.5,
        textColor=DARK_TEXT,
        leading=14,
        spaceAfter=6,
        leftIndent=12,
        alignment=TA_JUSTIFY,
    )
    styles["caption"] = ParagraphStyle(
        "caption",
        fontName="Helvetica-Oblique",
        fontSize=8,
        textColor=GREY_TEXT,
        leading=11,
        spaceAfter=2,
        alignment=TA_CENTER,
    )

    return styles


def ColorBox(content_flowables, bg_color, border_color=None, padding=6, radius=3):
    """Return a Table that acts as a coloured background box."""
    border = border_color or bg_color
    inner = Table(
        [[f] for f in content_flowables],
        colWidths=[6.1 * inch],
    )
    inner.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg_color),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    outer = Table(
        [[inner]],
        colWidths=[6.1 * inch],
    )
    outer.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg_color),
        ("BOX", (0, 0), (-1, -1), 0.5, border),
        ("TOPPADDING", (0, 0), (-1, -1), padding),
        ("BOTTOMPADDING", (0, 0), (-1, -1), padding),
        ("LEFTPADDING", (0, 0), (-1, -1), padding),
        ("RIGHTPADDING", (0, 0), (-1, -1), padding),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return outer


class SectionBanner(Flowable):
    """Full-width navy banner for section headers."""
    def __init__(self, text, style, width=None):
        super().__init__()
        self.text = text
        self.style = style
        self._width = width or (letter[0] - 1.4 * inch)
        self._height = 32

    def wrap(self, availWidth, availHeight):
        self._width = availWidth
        return availWidth, self._height

    def draw(self):
        c = self.canv
        c.setFillColor(NAVY)
        c.roundRect(0, 0, self._width, self._height, 4, fill=1, stroke=0)
        c.setFillColor(WHITE)
        c.setFont("Helvetica-Bold", 14)
        c.drawString(10, 10, self.text)


def page_footer(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(NAVY)
    canvas.setFont("Helvetica", 8)
    canvas.drawString(inch * 0.7, 0.4 * inch, "RegWatch AI — F1 Deep Audit Study Notes")
    canvas.drawRightString(letter[0] - inch * 0.7, 0.4 * inch, f"Page {doc.page}")
    canvas.setStrokeColor(BORDER)
    canvas.setLineWidth(0.5)
    canvas.line(inch * 0.7, 0.55 * inch, letter[0] - inch * 0.7, 0.55 * inch)
    canvas.restoreState()


def build_cover(story, styles):
    # Cover banner
    class CoverBanner(Flowable):
        def __init__(self, w):
            super().__init__()
            self._width = w
            self._height = 140

        def wrap(self, aw, ah):
            self._width = aw
            return aw, self._height

        def draw(self):
            c = self.canv
            # Gradient-like effect with two rectangles
            c.setFillColor(NAVY)
            c.roundRect(0, 0, self._width, self._height, 8, fill=1, stroke=0)
            c.setFillColor(HexColor("#0d2137"))
            c.roundRect(0, 0, self._width, 10, 0, fill=1, stroke=0)
            # Title
            c.setFillColor(WHITE)
            c.setFont("Helvetica-Bold", 22)
            c.drawCentredString(self._width / 2, self._height - 44, "F1 Deep Audit")
            c.setFont("Helvetica", 13)
            c.setFillColor(HexColor("#90caf9"))
            c.drawCentredString(self._width / 2, self._height - 66, "Everything I Need to Know as an AI PM")
            c.setFont("Helvetica", 10)
            c.setFillColor(HexColor("#bbdefb"))
            c.drawCentredString(self._width / 2, self._height - 88, "Feature: F1 — Regulatory Feed Monitoring")
            c.drawCentredString(self._width / 2, self._height - 104, "Status: Complete  |  Audited: 2026-06-01")
            c.drawCentredString(self._width / 2, self._height - 120, "RegWatch AI Build Session")

    story.append(CoverBanner(letter[0] - 1.4 * inch))
    story.append(Spacer(1, 14))

    intro = ("This is a permanent reference document for F1, written by reading every line "
             "of every file in the codebase — not from memory. Use it to understand what "
             "was built, every decision that was made, and how to explain it.")
    story.append(Paragraph(intro, styles["body"]))
    story.append(Spacer(1, 8))

    # Contents table
    toc_data = [
        [Paragraph("<b>Section</b>", styles["body"]), Paragraph("<b>Topic</b>", styles["body"])],
        ["1", "Project File Map — every file, what it does, what breaks if deleted"],
        ["2", "Data Flow — one real document traced end to end through every function"],
        ["3", "Every AI/ML Decision — technique, input, output, failure modes"],
        ["4", "Every Architectural Decision — chosen path, alternative, risk level"],
        ["5", "What Is Good, Weak, and Missing — honest assessment"],
        ["6", "8 Interview-Ready PM Answers — with specific code references"],
        ["7", "Architecture Diagram — full ASCII system map"],
        ["—", "Summary Scorecard — Engineering, AI/ML, Production, PM Explainability"],
    ]
    toc_style = TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_BLUE]),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ])
    toc = Table(toc_data, colWidths=[0.4 * inch, 5.6 * inch])
    toc.setStyle(toc_style)
    story.append(toc)
    story.append(PageBreak())


def add_section_banner(story, text, styles):
    story.append(Spacer(1, 6))
    story.append(SectionBanner(text, styles["section_header"]))
    story.append(Spacer(1, 8))


def add_file_entry(story, filename, does, key, connects, breaks, why, styles):
    items = [
        Paragraph(f"FILE: <font color='#1a3a5c'><b>{filename}</b></font>", styles["file_label"]),
    ]

    def add_row(label, text, label_style="label", value_style="value"):
        items.append(Paragraph(label, styles[label_style]))
        items.append(Paragraph(text, styles[value_style]))

    add_row("DOES:", does)
    add_row("KEY FUNCTION / CLASS:", key)

    # KEY highlighted in yellow
    key_box = ColorBox(
        [Paragraph(f"<b>KEY:</b> {key}", styles["body"])],
        bg_color=YELLOW_BG,
        border_color=HexColor("#f9a825"),
        padding=5,
    )

    add_row("CONNECTS TO:", connects)
    add_row("BREAKS IF DELETED:", breaks)
    add_row("WHY THIS WAY:", why)

    entry_data = []
    for label, text in [
        ("DOES", does),
        ("KEY", key),
        ("CONNECTS TO", connects),
        ("BREAKS IF DELETED", breaks),
        ("WHY THIS WAY", why),
    ]:
        entry_data.append([
            Paragraph(label, styles["label"]),
            Paragraph(text, styles["value"]),
        ])

    entry_table = Table(entry_data, colWidths=[1.1 * inch, 5.2 * inch])
    entry_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("BACKGROUND", (0, 1), (0, 1), YELLOW_BG),   # KEY row
        ("BACKGROUND", (1, 1), (1, 1), YELLOW_BG),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [LIGHT_BLUE, YELLOW_BG, WHITE, WHITE, WHITE]),
        ("GRID", (0, 0), (-1, -1), 0.3, BORDER),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
    ]))

    file_header = Paragraph(f"FILE: <b>{filename}</b>", styles["file_label"])

    block = KeepTogether([
        file_header,
        Spacer(1, 3),
        entry_table,
        Spacer(1, 8),
    ])
    story.append(block)


def build_section1(story, styles):
    add_section_banner(story, "SECTION 1 — Project File Map", styles)
    story.append(Paragraph(
        "Every file in the F1 codebase. For each file: what it does, its most important function, "
        "what connects to it, what breaks if deleted, and why it was built this way.",
        styles["body"]
    ))
    story.append(Spacer(1, 8))

    files = [
        ("src/models.py",
         "Defines all three database tables as Python classes — Agency, RegulatoryDocument, AuditLog.",
         "RegulatoryDocument — the atomic unit of the product. Every feature F1-F5 reads/writes here.",
         "Every file in the project imports from here. database.py creates tables. f1_ingest/*.py all import RegulatoryDocument.",
         "Everything stops. No tables, no imports, no pipeline.",
         "SQLModel merges SQLAlchemy (DB engine) and Pydantic (validation) into one class — eliminates drift risk between DB schema and Python schema."),

        ("src/database.py",
         "Creates the DB engine, provides get_session() context manager, exposes create_db_and_tables().",
         "get_session() — context manager that yields a DB session and guarantees cleanup even on exceptions.",
         "Imported by every file that touches the DB: agencies.py, dedup.py, anomaly.py, fulltext.py, ingest.py, health.py, query.py, dashboard/app.py.",
         "All DB operations fail. No reads, no writes.",
         "Separating connection management from models means models can be imported in tests without a live DB connection. DATABASE_URL from .env — swap SQLite to Postgres with one env var change."),

        ("src/f1_ingest/agencies.py",
         "Defines the 6 agency feed configs as Python dicts and provides seed_agencies() to write them to DB.",
         "seed_agencies() — idempotent insert: checks slug uniqueness before inserting, safe to run many times.",
         "scripts/setup_db.py calls seed_agencies(). ingest.py uses FR_API_SLUGS to route agencies to correct fetcher.",
         "setup_db.py fails. Agency table empty. Ingest pipeline finds no agencies and exits immediately.",
         "Storing in DB (not YAML) means a future UI can toggle agencies without a code deploy. active=False disables without deleting."),

        ("src/f1_ingest/fetcher.py",
         "Two fetchers — fetch_feed() for RSS (Fed), fetch_fr_api() for FR JSON API (CFPB, OCC, FDIC, FinCEN).",
         "fetch_fr_api() — handles 4 agencies whose RSS feeds block automated requests using the public FR JSON API.",
         "Called by ingest.py. Imports classifier.py, dedup.py, models.py.",
         "Ingest pipeline cannot fetch any documents. 0 documents per run.",
         "FR RSS feeds return HTML gate pages (200 but no XML). FR JSON API is public and stable. Two focused fetchers beats one complex adaptive fetcher."),

        ("src/f1_ingest/classifier.py",
         "Keyword-matches a document title against ordered rule lists and returns a DocType enum value.",
         "classify_doc_type(title: str) -> DocType — loops _RULES in priority order, first match wins, falls back to OTHER.",
         "Called inside fetch_feed() and fetch_fr_api() for every document parsed. Tested in test_f1_classifier.py.",
         "Every document ingested as DocType.OTHER. Dashboard doc type filtering useless. F4 task priority breaks in Week 5.",
         "Rule-based: zero cost, zero latency, explainable, no training data needed Day 1. F2 LLM reclassifies with full text."),

        ("src/f1_ingest/dedup.py",
         "Computes SHA-256(title + url) as a content fingerprint and checks if that hash exists in the DB.",
         "is_duplicate(content_hash: str) -> bool — single DB lookup, returns True/False.",
         "Called in ingest.py before every save. compute_hash() called inside fetcher.py when building each document.",
         "Every document saved every run, including re-runs. 9 duplicates appear. F2 summarises same doc twice.",
         "SHA-256(title+url) handles both failure modes: same doc at different URLs AND same URL cross-posted. Proved Day 2: 9 caught."),

        ("src/f1_ingest/fulltext.py",
         "Fetches complete regulation text. FR API raw_text_url for Federal Register docs; BeautifulSoup for Fed HTML.",
         "run_fulltext_enrichment(limit) — batch enriches docs with short raw_content, oldest first, 1 sec rate limit.",
         "Called in ingest.py after new docs saved. Called directly by scripts/enrich_fulltext.py.",
         "raw_content stays as 1-2 sentence abstracts. F2 quality collapses. Near-duplicate detection lost.",
         "Two strategies because two source types: FR has clean raw_text_url endpoint; Fed is HTML requiring BeautifulSoup parsing."),

        ("src/f1_ingest/anomaly.py",
         "Runs Z-score volume + off-schedule day-of-week anomaly detection on newly ingested documents.",
         "run_anomaly_check(new_docs) -> int — orchestrates both detectors, flags docs, writes AuditLog, returns count.",
         "Called in ingest.py after save and enrichment. Writes is_anomaly=True to RegulatoryDocument. Dashboard reads is_anomaly.",
         "No anomaly detection. is_anomaly stays False. Sarah never gets proactive alerts about publication spikes.",
         "Z-score over Isolation Forest: we have 1 day of history (IF needs weeks), Z-score is explainable, required for compliance."),

        ("src/f1_ingest/ingest.py",
         "The pipeline orchestrator. Loads agencies, routes to fetcher, deduplicates, saves, enriches, anomaly checks, logs.",
         "run_ingest(agency_slugs=None) -> dict — runs complete pipeline for all active agencies, returns summary dict.",
         "Imports and calls every other F1 component. Called by scripts/run_daily.py and daily_validate.py.",
         "Pipeline cannot run. All components exist but nothing coordinates them.",
         "Separation of orchestration from business logic: ingest.py has no logic of its own — it only coordinates. Each component independently testable."),

        ("src/f1_ingest/health.py",
         "Two read-only checks per agency: reachability (feed reachable + >=1 entry?) and freshness (docs within 3 days?).",
         "AgencyHealth dataclass with healthy, status_label, last_doc_date properties.",
         "Called by scripts/run_daily.py and daily_validate.py. Does not write to DB.",
         "No feed monitoring. Silent failures go undetected. 0 docs ingested and nobody knows.",
         "Two checks because a feed can return 200 with empty content (exactly what FR RSS feeds did). Freshness catches silent failures."),

        ("src/f1_ingest/query.py",
         "CLI tool to inspect DB contents — summary stats by agency/doc type, recent docs, anomaly-flagged view.",
         "show_summary() — prints total documents, agency/type breakdown, anomaly/review counts.",
         "Reads RegulatoryDocument from DB. No writes. Standalone — not called by any other file.",
         "No CLI inspection tool. Must use DB Browser for SQLite to see data.",
         "Alternative was waiting for Streamlit. Query tool gives immediate visibility during development."),

        ("dashboard/app.py",
         "Streamlit browser dashboard. Loads all docs, applies agency/doc-type/anomaly filters, renders document cards.",
         "load_documents() — @st.cache_data(ttl=300) cached DB query returning docs as plain dicts for Streamlit.",
         "Imports database.py, models.py, dashboard/components.py. Reads RegulatoryDocument. No writes.",
         "No browser UI. Week 1 exit gate unmet — Mike cannot view filtered feeds.",
         "Streamlit over React: React needs npm, build tooling, API layer, CORS — weeks of work. Streamlit is one Python file."),

        ("dashboard/components.py",
         "Reusable UI helpers — colour-coded doc type badges, anomaly badge, KPI metric row, document card renderer.",
         "render_document_card(doc) — expandable Streamlit card with badges, content preview, source link.",
         "Imported by dashboard/app.py. No other dependencies.",
         "app.py cannot render anything — all display imports fail.",
         "Separating display from data logic means React replacement in Week 6 only changes this file, not app.py."),

        ("fixtures/golden/f1_golden_set.json",
         "10 hand-labeled regulatory documents with ground-truth fields. The acceptance test for F2.",
         "eval_instructions field — defines faithfulness, relevance, and passing threshold (RAGAS >=0.85/0.80).",
         "Will be read by F2 eval harness in Week 3. Currently standalone.",
         "F2 has no ground truth. Cannot objectively say F2 is done.",
         "Hand-labeled from real document content, not LLM-generated. LLM labels would measure self-consistency, not accuracy."),

        ("docs/FP-FN-Risk-Matrix.md",
         "Quantifies business cost of false negatives (missed regs = $500K-$5M fines) vs false positives (wasted time).",
         "Asymmetry Summary — FN costs millions, FP costs 30 minutes. Drives every threshold decision.",
         "Referenced in design decisions for anomaly threshold, confidence threshold, HITL gate. Not imported by code.",
         "Design decisions lose their written rationale. Future threshold changes made without understanding cost asymmetry.",
         "Written before F2 is built — eval-first principle. Defining failure costs before building ensures correct thresholds."),
    ]

    for f in files:
        add_file_entry(story, f[0], f[1], f[2], f[3], f[4], f[5], styles)


def build_section2(story, styles):
    add_section_banner(story, "SECTION 2 — Data Flow: One Document End to End", styles)
    story.append(Paragraph(
        "Document: <b>Federal Reserve Board issues enforcement actions with former employee of Atlantic Union Bank "
        "and former employee of Frost Bank</b> (May 28, 2026)",
        styles["body"]
    ))
    story.append(Spacer(1, 8))

    steps = [
        ("STEP 1 — Entry (fetcher.py: fetch_feed, line 113)",
         "scripts/run_daily.py calls run_ingest() in ingest.py. The Fed slug 'fed' is NOT in FR_API_SLUGS "
         "so fetch_feed() is called. It makes an HTTP GET to federalreserve.gov/feeds/press_all.xml, "
         "passes the response to feedparser.parse(), loops through entries. For this document it extracts: "
         "title, url, date (via _parse_date()), calls classify_doc_type(title) — finds 'enforcement action' "
         "keyword — returns DocType.ENFORCEMENT. Calls compute_hash(title, url) in dedup.py. "
         "Constructs a RegulatoryDocument object (not yet saved)."),
        ("STEP 2 — Deduplication (dedup.py: is_duplicate)",
         "ingest.py checks is_duplicate(doc.content_hash). Runs: SELECT * FROM regulatorydocument "
         "WHERE content_hash = '<hash>' LIMIT 1. If duplicate: skip, increment counter. If new: proceed to save."),
        ("STEP 3 — Save to DB (ingest.py lines 62-67)",
         "session.add(doc) then session.commit(). Fields written: id=UUID, source_agency='fed', "
         "doc_type='enforcement', title, url, published_date=2026-05-28, fetched_at=now(), "
         "content_hash=SHA256hex, raw_content=short RSS abstract, summary_json=None, "
         "status='new', review_flag=False, is_anomaly=False."),
        ("STEP 4 — Full-text enrichment (fulltext.py: enrich_document)",
         "run_fulltext_enrichment() called. SourceAgency.FED is NOT in FR_AGENCIES so routes to "
         "_fetch_html_text(doc.url). BeautifulSoup fetches the HTML page, removes script/nav/footer tags, "
         "finds <main> content container, extracts and collapses text. Returns 817 chars. "
         "Written back to DB: db_doc.raw_content = '...Crystal Moore...CARES Act loan fraud...Jesse Romo...Embezzlement...'"),
        ("STEP 5 — Anomaly check (anomaly.py: run_anomaly_check)",
         "Groups docs by agency. For Fed: today_count=20. detect_volume_anomaly() queries 30-day baseline. "
         "len(baseline) < 7 → returns (False, 'insufficient history'). detect_off_schedule() also returns "
         "False (insufficient history). is_anomaly stays False."),
        ("STEP 6 — AuditLog written (ingest.py line 78)",
         "One AuditLog row written per agency run (not per document): action=INGEST, actor='system', "
         "payload_json={agency:'fed', fetched:20, new:20, duplicates:0, anomalies_flagged:0}."),
        ("STEP 7 — Dashboard display (dashboard/app.py: load_documents)",
         "@st.cache_data(ttl=300) loads all 111 docs as dicts. This enforcement action appears with "
         "doc_type='enforcement' (purple badge), is_anomaly=False (no red flag), raw_content=817 chars preview, "
         "summary_json=None (shows 'AI summary coming soon'). Filter by Enforcement in sidebar shows it."),
    ]

    for step_title, step_text in steps:
        step_data = [
            [Paragraph(step_title, styles["body_bold"]),
             Paragraph(step_text, styles["body"])],
        ]
        t = Table(step_data, colWidths=[1.8 * inch, 4.5 * inch])
        t.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BACKGROUND", (0, 0), (0, 0), LIGHT_BLUE),
            ("BACKGROUND", (1, 0), (1, 0), WHITE),
            ("GRID", (0, 0), (-1, -1), 0.3, BORDER),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(t)
        story.append(Spacer(1, 4))


def build_section3(story, styles):
    add_section_banner(story, "SECTION 3 — Every AI/ML Decision", styles)

    components = [
        {
            "name": "Document Type Classifier",
            "technique": "Rule-based keyword matching (NOT ML)",
            "problem": "Categorise publications into Final Rule / Proposed Rule / Guidance / Enforcement / FAQ / Other",
            "input": "doc.title (string from RSS or FR API)",
            "output": "DocType enum stored in RegulatoryDocument.doc_type",
            "why": "Zero cost, zero latency at ingest time. Vocabulary is predictable. Explainable to regulators. No training data needed Day 1.",
            "failure": "Title has no keywords → DocType.OTHER. Currently 104/111 (94%) classified as Other because FR documents use administrative titles without regulatory action keywords.",
            "score": "6% non-Other accuracy (7/111). Intentionally simple — F2 LLM will reclassify with full text.",
            "flag": "RULE-BASED",
        },
        {
            "name": "Deduplication — Content Hash",
            "technique": "SHA-256 cryptographic hash, exact DB match",
            "problem": "Same regulation appearing in multiple agency feeds (joint OCC/FDIC rules in both feeds)",
            "input": "title (str) + url (str) → concatenated → UTF-8 encoded",
            "output": "64-char hex string in content_hash (UNIQUE DB constraint)",
            "why": "Deterministic, collision-resistant, microseconds per doc, zero false positives.",
            "failure": "In-place update: same URL, same title, changed content → hash unchanged → stale content stays in DB.",
            "score": "9 cross-feed duplicates caught Day 2. Zero false positives.",
            "flag": "DETERMINISTIC",
        },
        {
            "name": "Deduplication — Title Similarity",
            "technique": "difflib.SequenceMatcher — longest common subsequence ratio",
            "problem": "Near-duplicates with slightly different URLs (e.g., 'Final Rule on BSA' and 'Final Rule on BSA (Correction)')",
            "input": "Two title strings from the same agency",
            "output": "Float 0.0–1.0. Near-duplicate flagged if ≥ 0.85.",
            "why": "Python stdlib — no dependency. Equivalent accuracy to Levenshtein for title-length strings.",
            "failure": "O(n²) comparisons. Fine for 20 docs/agency. Needs MinHash LSH at 2,000+ docs.",
            "score": "Threshold 0.85 not yet calibrated on real data. No confirmed cases.",
            "flag": "RULE-BASED",
        },
        {
            "name": "Volume Anomaly Detection",
            "technique": "Z-score on rolling 30-day daily publication counts",
            "problem": "Detecting when an agency publishes unusually many documents in one day",
            "input": "today_count (int) + baseline: list of daily counts for prior 29 days (zeros included)",
            "output": "(is_anomaly: bool, explanation: str). Sets is_anomaly=True on doc. Formula: Z = (today - mean) / std. Flag if Z > 2.0.",
            "why": "Isolation Forest (roadmap spec) needs training data — we have 1 day of history. Z-score works with 7+ days. Z-score is explainable: 'published 3x 30-day average'.",
            "failure": "FN: high baseline variance → Z stays < 2.0 even for real spike. FP: new agency + small baseline → Z inflated. SILENT: len(baseline) < 7 → returns False with no alert.",
            "score": "0 anomalies detected (expected — all agencies in 'insufficient history' state). Effective after 7+ days of real operation.",
            "flag": "STATISTICAL",
        },
        {
            "name": "Off-Schedule Detection",
            "technique": "Day-of-week frequency baseline (90-day window)",
            "problem": "Documents published on unusual weekdays — FinCEN on Sunday when they never publish Sunday",
            "input": "doc.published_date.weekday() + historical weekday distribution for that agency",
            "output": "(is_anomaly: bool, explanation: str). Flag if < 10% of historical docs fall on that weekday.",
            "why": "Regulators follow predictable schedules. Off-schedule publication is a signal regardless of volume.",
            "failure": "len(historical_docs) < 20 → returns False silently. All agencies currently in this state.",
            "score": "0 anomalies detected (expected). Active after ~4 weeks of daily ingestion.",
            "flag": "STATISTICAL",
        },
    ]

    for comp in components:
        rows = [
            [Paragraph("<b>Technique</b>", styles["label"]), Paragraph(comp["technique"], styles["value"])],
            [Paragraph("<b>Problem</b>", styles["label"]), Paragraph(comp["problem"], styles["value"])],
            [Paragraph("<b>Input</b>", styles["label"]), Paragraph(comp["input"], styles["value"])],
            [Paragraph("<b>Output</b>", styles["label"]), Paragraph(comp["output"], styles["value"])],
            [Paragraph("<b>Why this way</b>", styles["label"]), Paragraph(comp["why"], styles["value"])],
            [Paragraph("<b>Failure mode</b>", styles["label"]), Paragraph(comp["failure"], styles["value"])],
            [Paragraph("<b>Current score</b>", styles["label"]), Paragraph(comp["score"], styles["value"])],
        ]
        t = Table(rows, colWidths=[1.2 * inch, 5.1 * inch])
        t.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BLUE),
            ("BACKGROUND", (0, 5), (-1, 5), HexColor("#fff8e1")),  # failure row
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.3, BORDER),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ]))

        flag_color = {"RULE-BASED": HexColor("#e3f2fd"), "DETERMINISTIC": GREEN_BG,
                      "STATISTICAL": HexColor("#f3e5f5")}.get(comp["flag"], LIGHT_BLUE)
        flag_p = Paragraph(
            f"<b>Type: {comp['flag']}</b>",
            ParagraphStyle("flag", fontName="Helvetica-Bold", fontSize=8.5,
                           textColor=NAVY, leading=12)
        )

        story.append(KeepTogether([
            Paragraph(f"<b>{comp['name']}</b>", styles["subsection"]),
            t,
            Spacer(1, 6),
        ]))


def build_section4(story, styles):
    add_section_banner(story, "SECTION 4 — Every Decision Made and Why", styles)

    decisions = [
        ("SQLite for dev, Postgres for prod",
         "SQLite (file-based dev), Postgres (server prod). Switch via DATABASE_URL in .env.",
         "Postgres from Day 1 — more realistic, avoids migration edge cases.",
         "Zero infrastructure. No Docker, no Postgres install. Solo builder runs full pipeline with pip install only.",
         "SQLite with Postgres: extra hour of setup Day 1, more complex.",
         "MEDIUM — SQLite lacks JSON column type and concurrent writes. summary_json stored as TEXT workaround. Migration planned Week 6."),
        ("SHA-256 content hash as dedup key",
         "Dedup key = SHA-256(title + url). UNIQUE DB constraint.",
         "URL-only, title-only, or fuzzy matching only.",
         "Title alone misses different-URL duplicates. URL alone misses cross-posted. Combined handles both. Zero false positives.",
         "URL-only would have missed 9 cross-feed duplicates on Day 2.",
         "LOW — One gap: in-place updates (same URL+title, changed content). Acceptable for MVP."),
        ("Rule-based keyword classifier",
         "Keyword matching in ordered rule list. First match wins, falls back to OTHER.",
         "Fine-tuned classifier (DistilBERT, logistic regression on TF-IDF), or LLM classification.",
         "Must run on every document at ingest time — free and instant. No training data Day 1. Explainable.",
         "85%+ accuracy vs 6% — but requires labeled data, training pipeline, model versioning.",
         "LOW — F2 LLM reclassifies with full text. Keyword classifier is routing hint, not final decision."),
        ("Z-score over Isolation Forest",
         "Z-score on rolling 30-day counts, threshold Z > 2.0.",
         "Isolation Forest (roadmap-specified), LSTM, moving average with fixed threshold.",
         "Isolation Forest needs training data — we have 1 day of history. Z-score works with 7+ days. Explainable output.",
         "Isolation Forest on 1 day of data = meaningless scores. Fixed threshold fails per-agency adaptation.",
         "LOW — Z-score correct for current volume. Revisit Isolation Forest in Week 3 with 3 weeks of data."),
        ("Two fetchers (RSS + FR JSON API)",
         "fetch_feed() for Fed (RSS). fetch_fr_api() for CFPB/OCC/FDIC/FinCEN/FR (JSON API).",
         "FR API for all agencies, or one generic adaptive fetcher.",
         "FR RSS feeds block automated requests (discovered Day 2 — return HTML gate page at HTTP 200). FR JSON API is public and stable.",
         "FR API for Fed too would work but miss Fed-specific press releases not in Federal Register.",
         "LOW — If Fed changes RSS URL, one-line fix in agencies.py."),
        ("Streamlit for dashboard, not React",
         "Streamlit browser dashboard (Python-only). React deferred to Week 6.",
         "React + FastAPI from Day 1 (Word PRD specified), or no UI until Week 6.",
         "React needs npm, build tooling, component libraries, API layer, CORS, state management — weeks of work. Streamlit: one file, one command.",
         "React app on Day 7 = table of document titles with 10x build cost. Not meaningfully better than Streamlit at this stage.",
         "LOW — Streamlit is explicitly a pilot tool. Data layer unchanged when React replaces it Week 6."),
        ("Windows Task Scheduler",
         "Task Scheduler via schtasks CLI. Runs run_daily.py at 7:00 AM.",
         "APScheduler (in-process), Celery (distributed), manual cron.",
         "Built into Windows, survives reboots without background process, visible in Windows UI.",
         "APScheduler: process must stay running. Celery: requires Redis/RabbitMQ broker.",
         "LOW — Windows-specific. Mac/Linux deployment (Week 6) uses cron or cloud scheduler."),
        ("Full-text enrichment as post-ingest step",
         "Fetch → dedup → save → THEN enrich. Separate pass, 1 req/sec rate limit.",
         "Fetch full text during initial HTTP call, or skip full text (abstracts only).",
         "Full text during fetch: 40+ seconds for 20 docs, rapid government server requests. Keeping steps separate keeps ingest fast.",
         "Abstracts only: F2 quality collapses. Full text during fetch: slow and brittle ingest.",
         "LOW — Enrichment catches up over multiple daily runs (20 docs/run)."),
    ]

    for i, (title, decided, alt, why, consequence, risk) in enumerate(decisions):
        risk_color = {"LOW": GREEN_BG, "MEDIUM": ORANGE_BG, "HIGH": RED_BG}.get(
            risk.split(" ")[0], LIGHT_BLUE)
        rows = [
            [Paragraph("<b>Decided</b>", styles["label"]), Paragraph(decided, styles["value"])],
            [Paragraph("<b>Alternative</b>", styles["label"]), Paragraph(alt, styles["value"])],
            [Paragraph("<b>Why chosen</b>", styles["label"]), Paragraph(why, styles["value"])],
            [Paragraph("<b>Consequence of other path</b>", styles["label"]), Paragraph(consequence, styles["value"])],
            [Paragraph("<b>Risk if wrong</b>", styles["label"]), Paragraph(risk, styles["value"])],
        ]
        t = Table(rows, colWidths=[1.4 * inch, 4.9 * inch])
        t.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [WHITE, LIGHT_BLUE, WHITE, LIGHT_BLUE, risk_color]),
            ("GRID", (0, 0), (-1, -1), 0.3, BORDER),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(KeepTogether([
            Paragraph(f"Decision {i+1}: {title}", styles["subsection"]),
            t,
            Spacer(1, 8),
        ]))


def build_section5(story, styles):
    add_section_banner(story, "SECTION 5 — What Is Good, Weak, and Missing", styles)

    good_items = [
        ("Content hash deduplication",
         "Zero false positives. Mathematically guaranteed. 9 cross-feed duplicates caught Day 2. "
         "UNIQUE DB constraint means even if Python check fails, DB rejects the insert."),
        ("Full-text enrichment pipeline",
         "111/111 documents enriched (100%). Two-strategy approach handles both source types. "
         "Rate limiting protects against IP blocks. Idempotent — re-running skips already-enriched."),
        ("AuditLog architecture",
         "INSERT-only design correct for SR 11-7. UUID keys. Every ingest logged with payload JSON. "
         "LangSmith trace ID field ready for F2."),
        ("Health checker",
         "Two-signal approach catches obvious failures (404) and silent failures (200 + empty content "
         "— exactly what FR RSS feeds returned). Proved Day 2."),
        ("Test suite",
         "44 unit + 7 integration tests. Fast unit tests (2 sec) run every change. Integration tests "
         "verify zero-missed-publications metric against live feeds. Clean slow/fast separation via pytest.ini."),
        ("Golden evaluation set",
         "10 hand-labeled docs. Labels from real document content, not LLM-generated. Edge cases included. "
         "This is rare — most projects build eval after the model."),
    ]

    story.append(Paragraph("GOOD — Solid and Production-Ready", styles["h3"]))
    for name, desc in good_items:
        block = ColorBox(
            [Paragraph(f"<b>✓ {name}</b>", styles["good_label"]),
             Paragraph(desc, styles["body"])],
            bg_color=GREEN_BG,
            border_color=HexColor("#a5d6a7"),
            padding=6,
        )
        story.append(block)
        story.append(Spacer(1, 4))

    story.append(Spacer(1, 8))
    story.append(Paragraph("WEAK — Works But Has Known Limitations", styles["h3"]))

    weak_items = [
        ("Classifier accuracy: 94% classified as OTHER",
         "Impact: Dashboard doc type filter mostly useless. F4 task prioritisation wrong for most docs.\n"
         "Fix: Expand keyword lists → ~50% (Easy, 2 hrs). LLM classifier → 90%+ (Medium).\n"
         "Blocks F2: No. F2 LLM produces its own doc_type classification."),
        ("Anomaly detection has no history",
         "Impact: Both volume and off-schedule detectors return 'insufficient history'. Anomaly detection is effectively OFF.\n"
         "Fix: Cannot be fixed by code — requires 7+ days of real daily ingestion.\n"
         "Blocks F2: No."),
        ("20-document cap per agency per run",
         "Impact: On high-volume days, overflow publications are missed. Federal Register often publishes 50+ daily.\n"
         "Fix: Easy. FR API supports pagination (page parameter). Fetch until published_date < last_run_date.\n"
         "Blocks F2: No for current 111 docs. Critical risk before first pilot client."),
        ("Title similarity dedup is O(n²)",
         "Impact: 190 comparisons for 20 docs/agency — fine now. 2M comparisons for 2,000 docs — slow.\n"
         "Fix: Medium. MinHash LSH reduces to O(n).\n"
         "Blocks F2: No."),
        ("utcnow() deprecation warnings",
         "Impact: Cosmetic Python 3.12 warnings. No runtime failure.\n"
         "Fix: Easy. 5-minute find-and-replace: datetime.utcnow() → datetime.now(UTC).\n"
         "Blocks F2: No."),
    ]

    for name, desc in weak_items:
        block = ColorBox(
            [Paragraph(f"⚠ {name}", styles["weak_label"]),
             Paragraph(desc.replace("\n", "<br/>"), styles["body"])],
            bg_color=ORANGE_BG,
            border_color=HexColor("#ffcc80"),
            padding=6,
        )
        story.append(block)
        story.append(Spacer(1, 4))

    story.append(Spacer(1, 8))
    story.append(Paragraph("MISSING — Roadmap Specified, Not Built", styles["h3"]))

    missing_items = [
        ("Onboarding flow — 'Set up your regulatory watchlist'",
         "Impact: Mike cannot self-configure agencies/doc types on first login. Shows everything by default.\n"
         "Fix: Medium. Streamlit Settings page + user preferences table.\n"
         "Blocks F2: No. Deferred to Week 6."),
        ("Notification preferences UX",
         "Impact: No email/Slack alerts when anomalies detected. Sarah must check dashboard manually.\n"
         "Fix: Medium. SMTP/SendGrid + preferences table. Slack webhook is easier.\n"
         "Blocks F2: No. Deferred to Week 6."),
        ("7-day fixture dataset",
         "Impact: Only 4-entry sample_feed.json. Offline development requires live internet.\n"
         "Fix: Easy. Export 7 days of real docs to JSON fixtures (1 hour).\n"
         "Blocks F2: No."),
        ("Isolation Forest implementation",
         "Impact: Z-score correct for now but won't handle multi-dimensional anomaly patterns at scale.\n"
         "Fix: Medium. Requires scikit-learn, training pipeline, model serialisation.\n"
         "Blocks F2: No. Revisit Week 3 when sufficient data exists."),
    ]

    for name, desc in missing_items:
        block = ColorBox(
            [Paragraph(f"✗ {name}", styles["missing_label"]),
             Paragraph(desc.replace("\n", "<br/>"), styles["body"])],
            bg_color=RED_BG,
            border_color=HexColor("#ef9a9a"),
            padding=6,
        )
        story.append(block)
        story.append(Spacer(1, 4))


def build_section6(story, styles):
    add_section_banner(story, "SECTION 6 — 8 Interview-Ready PM Answers", styles)

    qas = [
        ("Q1: What does F1 do and why does it matter to a compliance officer?",
         "F1 is the regulatory intelligence radar for community banks. It watches 6 regulatory sources — "
         "Federal Reserve, CFPB, OCC, FDIC, FinCEN, and the Federal Register — every day at 7 AM, "
         "pulls every new publication, classifies it by type, and stores the full text. Without F1, "
         "Sarah (CCO) spends 15-20 hours per week manually checking agency websites and downloading PDFs. "
         "F1 compresses that to zero manual monitoring time. The business consequence of missing a regulation "
         "is a $500K-$5M fine and examination finding — F1 is the first line of defence against that."),

        ("Q2: How does the document classifier work, and how accurate is it?",
         "The classifier uses keyword matching on the document title — ordered rule lists where the first match wins. "
         "'enforcement action', 'consent order' → Enforcement; 'final rule' → Final Rule; 'proposed rule' → Proposed Rule; etc. "
         "Currently 94% of documents (104/111) are classified as Other because Federal Register documents use administrative "
         "titles that don't contain regulatory action keywords. This is intentional — F2's LLM will produce accurate "
         "classifications using full document text as part of its structured summary output."),

        ("Q3: How do you prevent the same regulation from being ingested twice?",
         "SHA-256 hashing. For every document, we compute SHA-256(title + url) — a 64-character fingerprint unique to "
         "that specific title-URL combination. Before saving, we query the DB: if that hash exists, we skip entirely. "
         "We also enforce a UNIQUE constraint on content_hash so even if the Python check fails, the DB rejects the insert. "
         "This caught 9 joint-agency rules that appeared in both agency-specific feeds and the Federal Register catch-all "
         "feed during the Day 2 ingestion run."),

        ("Q4: What happens when a feed goes down — does the system fail silently?",
         "No. Two-signal health check runs before every ingest. Signal one: reachability — can we reach the URL and "
         "get at least one parseable entry? Signal two: freshness — do we have documents from this agency within the "
         "last 3 days? Freshness catches silent failures — a feed can return HTTP 200 with empty content (exactly what "
         "the FR RSS feeds did, returning an HTML gate page), and reachability alone would have passed. "
         "The daily runner exits with code 1 on any health failure, detectable by any monitoring tool."),

        ("Q5: How does anomaly detection work, and what is the consequence of FN vs FP?",
         "Two checks: (1) Volume Z-score — today's publication count vs 30-day rolling baseline. Flag if Z > 2.0 "
         "(top 2.5% of historical days). (2) Off-schedule — publication on a weekday representing < 10% of "
         "historical publications. A false negative (missed anomaly) could mean Sarah doesn't investigate an "
         "emergency publication with a 48-hour compliance window → $500K-$5M fine. A false positive (false alarm) "
         "costs 30 minutes. Chronic false positives erode trust until Sarah ignores alerts entirely — equivalent to "
         "no detection. Z=2.0 balances both; FP/FN asymmetry documented in FP-FN-Risk-Matrix.md."),

        ("Q6: What would you build differently in F1 if starting over?",
         "Three things. First, LLM-based classifier from day one — with 111 real documents, labeling 30 in an "
         "afternoon would yield a simple classifier at 90%+ accuracy vs our 6%. Second, feed pagination from "
         "the start — the 20-document cap means we miss overflow publications on high-volume days, the exact "
         "failure the product prevents. Third, a 7-day fixture dataset immediately rather than a 4-entry sample "
         "— offline development dependency on live government websites introduces brittleness."),

        ("Q7: How does F1 connect to F2 — what does F2 depend on F1 getting right?",
         "F2 reads directly from RegulatoryDocument.raw_content to generate summaries. Three F1 properties bound "
         "F2's quality. (1) Content completeness: if raw_content is a 1-sentence abstract, the best LLM cannot "
         "extract an effective date that isn't in the text — we achieved 100% enrichment before starting F2. "
         "(2) Deduplication: if F1 allows the same document twice, F2 summarises it twice, doubling costs. "
         "(3) Status tracking: F2 queries for status='new' — if F1 doesn't set status correctly, F2 re-summarises "
         "or misses documents."),

        ("Q8: What is the biggest technical risk in F1 right now?",
         "The 20-document per agency cap. The Federal Register publishes 50-200 documents per day. "
         "Our pipeline fetches the 20 most recent per agency per run. If important regulations are published on "
         "a high-volume day and fall outside the top 20, we miss them entirely — the exact failure the product "
         "promises to prevent. This risk is masked because we only have 1 day of data and the 111 documents are "
         "the newest 20 from each feed. Fix: track last-seen publication date per agency, fetch everything after it. "
         "One-to-two day fix. Must be done before the first pilot client."),
    ]

    for q, a in qas:
        story.append(KeepTogether([
            Paragraph(q, styles["qa_q"]),
            Paragraph(a, styles["qa_a"]),
        ]))


def build_section7(story, styles):
    add_section_banner(story, "SECTION 7 — Architecture Diagram", styles)

    diagram = """EXTERNAL SOURCES
──────────────────────────────────────────────────────────────────────
  [Fed RSS Feed]    federalreserve.gov/feeds/press_all.xml  (RSS/XML)
  [FR JSON API]     federalregister.gov/api/v1/documents.json  (JSON)
                    └─ Used for: CFPB, OCC, FDIC, FinCEN, FedRegister

SCHEDULED TRIGGER
──────────────────────────────────────────────────────────────────────
  [Windows Task Scheduler] "RegWatch-AI-Daily" @ 07:00 AM
         |
         v
  scripts/run_daily.py
         |-- STEP 1: health.py -> run_health_check()
         |           |-- reachability: HTTP + parse >= 1 entry
         |           `-- freshness: DB docs within 3 days?
         |           Output: [OK / UNREACHABLE / STALE] per agency
         |-- STEP 2: ingest.py -> run_ingest()
         `-- STEP 3: fulltext.py -> run_fulltext_enrichment(limit=20)

INGESTION PIPELINE
──────────────────────────────────────────────────────────────────────
  agencies.py                    fetcher.py
  [AGENCY_SEEDS]                 [fetch_feed()]          <- Fed (RSS)
  fed / cfpb / occ / fdic  -->   [fetch_fr_api()]        <- Others
  fincen / federal_register
                                        |
                                 classifier.py
                                 [classify_doc_type()]
                                 keyword match -> DocType enum
                                 * WEAK: 94% OTHER
                                        |
                                  dedup.py
                                 [is_duplicate(hash)]
                                 SHA-256(title+url) -> DB lookup
                                 DUPLICATE? -> skip
                                 NEW? -> proceed
                                        |
                             ┌─────────────────────────┐
                             │    SQLite (regwatch.db)  │
                             │  TABLE: agency (6 rows)  │
                             │  TABLE: regulatorydocument│
                             │    111 rows, all enriched │
                             │    summary_json = NULL    │
                             │    status = 'new'         │
                             │  TABLE: auditlog          │
                             │    INSERT ONLY            │
                             └─────────────────────────┘
                                        |
                                  fulltext.py
                                 [run_fulltext_enrichment]
                                 FR docs: raw_text_url -> plain text
                                 Fed docs: HTML -> BeautifulSoup
                                 1 req/sec rate limit
                                        |
                                  anomaly.py
                                 [run_anomaly_check]
                                 Z-score volume (Z > 2.0)
                                 Off-schedule (< 10% weekday)
                                 * INACTIVE: insufficient history

DASHBOARD (separate process)
──────────────────────────────────────────────────────────────────────
  $ streamlit run dashboard/app.py -> http://localhost:8501
  |-- load_documents() @cache_data(ttl=300)
  |-- Sidebar: agency filter, doc type filter, anomaly toggle, sort
  |-- KPI row: total, final rules, proposed, enforcement, anomalies
  |-- Anomaly banner (red) if is_anomaly=True docs exist
  `-- 111 expandable document cards -> preview + source link

LEGEND: * = Weak/inactive component"""

    diag_style = ParagraphStyle(
        "diag", fontName="Courier", fontSize=7.5,
        leading=11, textColor=HexColor("#1a237e"),
        backColor=HexColor("#f8f9fa"),
        leftIndent=8, rightIndent=8,
        spaceAfter=2,
    )
    # Split diagram into lines so it flows naturally across pages
    for line in diagram.split("\n"):
        safe = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        safe = safe.replace(" ", "&nbsp;") if safe.strip() else "&nbsp;"
        story.append(Paragraph(safe, diag_style))


def build_scorecard(story, styles):
    add_section_banner(story, "SUMMARY SCORECARD", styles)

    scores = [
        ("Engineering completeness", "7/10",
         "Core pipeline solid. Missing: pagination (20-doc cap), notifications, Isolation Forest, 7-day fixtures. "
         "AuditLog, dedup, health check, enrichment are production-grade.",
         "7"),
        ("AI/ML quality", "4/10",
         "Classifier rule-based with 6% accuracy. Anomaly detection inactive (no history). "
         "Both are known limitations with clear upgrade paths. No trained ML models yet — intentional.",
         "4"),
        ("Production readiness", "6/10",
         "Scheduler, logs, health check, tests working. Not ready: no pagination, no alerting, "
         "SQLite not prod-grade, no authentication, no multi-tenancy.",
         "6"),
        ("PM explainability", "8/10",
         "Can explain every major decision with specific code references. "
         "Gaps: 20-doc cap acceptance, near-duplicate calibration.",
         "8"),
    ]

    def score_color(s):
        v = int(s)
        if v >= 7: return GREEN_BG, HexColor("#1b5e20")
        if v >= 5: return ORANGE_BG, HexColor("#e65100")
        return RED_BG, HexColor("#b71c1c")

    rows = [[
        Paragraph("<b>Dimension</b>", styles["body_bold"]),
        Paragraph("<b>Score</b>", styles["body_bold"]),
        Paragraph("<b>Rationale</b>", styles["body_bold"]),
    ]]

    for dim, score, rationale, num in scores:
        bg, fg = score_color(num)
        rows.append([
            Paragraph(dim, styles["body"]),
            Paragraph(f"<b>{score}</b>", ParagraphStyle(
                "sc", fontName="Helvetica-Bold", fontSize=14,
                textColor=fg, alignment=TA_CENTER)),
            Paragraph(rationale, styles["body"]),
        ])

    t = Table(rows, colWidths=[1.8 * inch, 0.7 * inch, 3.8 * inch])
    row_colors = [NAVY] + [score_color(s[3])[0] for s in scores]
    ts = TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 0), (1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
    ])
    for i, (_, _, _, num) in enumerate(scores):
        bg, _ = score_color(num)
        ts.add("BACKGROUND", (0, i+1), (-1, i+1), bg)

    t.setStyle(ts)
    story.append(t)
    story.append(Spacer(1, 12))

    # F2 blockers
    story.append(Paragraph("F2 Blockers", styles["subsection"]))
    blockers_text = (
        "NONE. F2 can start immediately.<br/><br/>"
        "• raw_content is 100% populated — F2 has full text to summarise<br/>"
        "• summary_json field exists and is NULL — F2 writes here<br/>"
        "• review_flag field exists — F2 sets True when confidence &lt; 0.80<br/>"
        "• status field exists — F2 advances 'new' → 'summarised'<br/>"
        "• Golden eval set exists with 10 labeled documents"
    )
    story.append(ColorBox(
        [Paragraph(blockers_text, styles["body"])],
        bg_color=GREEN_BG, border_color=HexColor("#a5d6a7"), padding=8,
    ))
    story.append(Spacer(1, 12))

    # Recommended pre-pilot fixes
    story.append(Paragraph("Recommended Fixes Before First Pilot Client (not before F2)", styles["subsection"]))
    fixes = [
        ("1", "Fix 20-doc cap → implement pagination", "Medium", "1 day"),
        ("2", "Fix classifier accuracy → expand keyword lists to ~50%", "Easy", "2 hours"),
        ("3", "Fix utcnow() warnings → datetime.now(UTC)", "Easy", "30 minutes"),
        ("4", "Build 7-day fixture dataset", "Easy", "1 hour"),
    ]
    fix_data = [[
        Paragraph("<b>#</b>", styles["body_bold"]),
        Paragraph("<b>Fix</b>", styles["body_bold"]),
        Paragraph("<b>Effort</b>", styles["body_bold"]),
        Paragraph("<b>Time</b>", styles["body_bold"]),
    ]] + [[Paragraph(f[0], styles["body"]), Paragraph(f[1], styles["body"]),
           Paragraph(f[2], styles["body"]), Paragraph(f[3], styles["body"])]
          for f in fixes]

    ft = Table(fix_data, colWidths=[0.3*inch, 3.5*inch, 0.9*inch, 1.0*inch])
    ft.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_BLUE]),
        ("GRID", (0, 0), (-1, -1), 0.3, BORDER),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(ft)


def main():
    print(f"Generating PDF: {OUTPUT_PATH}")

    doc = SimpleDocTemplate(
        OUTPUT_PATH,
        pagesize=letter,
        leftMargin=0.7 * inch,
        rightMargin=0.7 * inch,
        topMargin=0.8 * inch,
        bottomMargin=0.8 * inch,
    )

    styles = make_styles()
    story = []

    build_cover(story, styles)
    build_section1(story, styles)
    story.append(PageBreak())
    build_section2(story, styles)
    story.append(PageBreak())
    build_section3(story, styles)
    story.append(PageBreak())
    build_section4(story, styles)
    story.append(PageBreak())
    build_section5(story, styles)
    story.append(PageBreak())
    build_section6(story, styles)
    story.append(PageBreak())
    build_section7(story, styles)
    story.append(PageBreak())
    build_scorecard(story, styles)

    doc.build(story, onFirstPage=page_footer, onLaterPages=page_footer)
    print(f"Done! PDF saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
