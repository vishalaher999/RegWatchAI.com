"""
Full-text document fetcher for F1.

Enriches RegulatoryDocument records whose raw_content is too short to be
useful for F2 summarisation (typically feed abstracts < 500 chars).

Two extraction strategies:
  1. Federal Register documents — fetch the raw_text_url from the FR API,
     which returns clean plain text with no HTML to parse.
  2. All other documents — fetch the HTML source page and extract body text
     using BeautifulSoup, targeting semantic content containers.

Rate limiting: 1-second delay between requests to avoid IP blocks on
government sites. This is a courtesy delay, not a legal requirement.
"""

import re
import time
from difflib import SequenceMatcher

from bs4 import BeautifulSoup
import httpx
from sqlmodel import select

from src.database import get_session
from src.models import RegulatoryDocument, SourceAgency

# Documents with raw_content shorter than this are treated as "abstract only"
# and will be fetched for full text.
MIN_CONTENT_LENGTH = 500

# Federal Register agencies — these have a raw_text_url available via API
FR_AGENCIES = {
    SourceAgency.CFPB,
    SourceAgency.OCC,
    SourceAgency.FDIC,
    SourceAgency.FINCEN,
    SourceAgency.FEDERAL_REGISTER,
}

# Title similarity threshold for near-duplicate detection (0–1 scale)
SIMILARITY_THRESHOLD = 0.85

HTTP_TIMEOUT = 30
RATE_LIMIT_SECONDS = 1.0

# HTML tags whose content we discard entirely (nav, scripts, ads, etc.)
_DISCARD_TAGS = {
    "script", "style", "nav", "header", "footer", "aside",
    "noscript", "form", "button", "iframe", "svg",
}

# Semantic content containers — we prefer these over generic <div>/<span>
_CONTENT_TAGS = ["article", "main", "section", "div.content", "div#content"]


def _clean_text(raw: str) -> str:
    """Collapse whitespace and remove boilerplate markers."""
    text = re.sub(r"\s+", " ", raw)
    text = text.strip()
    return text


def _extract_text_from_html(html: str) -> str:
    """
    Extract readable body text from an HTML page.

    Strategy:
    1. Remove discard tags entirely (scripts, nav, footer, etc.)
    2. Try to find a semantic content container (article, main, etc.)
    3. Fall back to the full body if no container found
    4. Extract text, collapse whitespace
    """
    soup = BeautifulSoup(html, "html.parser")

    # Remove noise elements
    for tag in soup.find_all(_DISCARD_TAGS):
        tag.decompose()

    # Try semantic containers first
    content = None
    for selector in ["article", "main", "[role='main']", ".content", "#content", "#main-content"]:
        content = soup.select_one(selector)
        if content:
            break

    # Fall back to body
    if not content:
        content = soup.find("body")

    if not content:
        return ""

    return _clean_text(content.get_text(separator=" "))


def _fetch_fr_raw_text(doc_url: str) -> str:
    """
    Fetch plain text from Federal Register API for a given document HTML URL.

    The FR API raw text URL follows a predictable pattern:
    HTML:     https://www.federalregister.gov/documents/2026/06/01/2026-12345/title
    Raw text: https://www.federalregister.gov/documents/full_text/text/2026/06/01/2026-12345.txt

    We use the API endpoint instead, which is more reliable.
    """
    # Extract document number from URL — pattern: /documents/YYYY/MM/DD/DOCNUM/
    match = re.search(r"/documents/\d{4}/\d{2}/\d{2}/([^/]+)/", doc_url)
    if not match:
        return ""

    doc_number = match.group(1)
    api_url = f"https://www.federalregister.gov/api/v1/documents/{doc_number}.json?fields[]=raw_text_url&fields[]=abstract"

    try:
        response = httpx.get(
            api_url,
            timeout=HTTP_TIMEOUT,
            headers={"User-Agent": "RegWatch-AI/1.0 (compliance monitoring)"},
            follow_redirects=True,
        )
        response.raise_for_status()
        data = response.json()

        raw_text_url = data.get("raw_text_url")
        if raw_text_url:
            text_response = httpx.get(
                raw_text_url,
                timeout=HTTP_TIMEOUT,
                headers={"User-Agent": "RegWatch-AI/1.0"},
                follow_redirects=True,
            )
            text_response.raise_for_status()
            return _clean_text(text_response.text)

        # Fall back to abstract if no raw text URL
        return data.get("abstract") or ""

    except Exception:
        return ""


def _fetch_html_text(url: str) -> str:
    """Fetch a page and extract body text."""
    try:
        response = httpx.get(
            url,
            timeout=HTTP_TIMEOUT,
            follow_redirects=True,
            headers={"User-Agent": "RegWatch-AI/1.0 (compliance monitoring)"},
        )
        response.raise_for_status()
        return _extract_text_from_html(response.text)
    except Exception:
        return ""


def enrich_document(doc: RegulatoryDocument) -> str:
    """
    Fetch full text for a single document. Returns the extracted text
    (empty string if fetching failed). Does NOT write to DB — caller does that.
    """
    if doc.source_agency in FR_AGENCIES:
        return _fetch_fr_raw_text(doc.url)
    return _fetch_html_text(doc.url)


def run_fulltext_enrichment(limit: int = 20) -> dict:
    """
    Enrich up to `limit` documents that have short raw_content.

    Processes documents in order of fetched_at (oldest first) so we don't
    keep re-processing the same newest documents on each run.

    Returns a summary dict: {enriched, skipped, failed}.
    """
    with get_session() as session:
        candidates = session.exec(
            select(RegulatoryDocument)
            .where(RegulatoryDocument.raw_content == None)  # noqa: E711
        ).all()

        # Also include docs with very short content (feed abstracts)
        short_content = session.exec(
            select(RegulatoryDocument)
            .where(
                RegulatoryDocument.raw_content != None,  # noqa: E711
            )
        ).all()
        short_content = [d for d in short_content if len(d.raw_content or "") < MIN_CONTENT_LENGTH]

    all_candidates = candidates + short_content
    # Deduplicate by id and sort oldest first
    seen = set()
    to_enrich = []
    for doc in sorted(all_candidates, key=lambda d: d.fetched_at or ""):
        if doc.id not in seen:
            seen.add(doc.id)
            to_enrich.append(doc)

    to_enrich = to_enrich[:limit]

    enriched = 0
    skipped = 0
    failed = 0

    print(f"  Enriching {len(to_enrich)} documents (limit={limit})...")

    for i, doc in enumerate(to_enrich):
        print(f"  [{i+1}/{len(to_enrich)}] {doc.source_agency.value}: {doc.title[:60]}...")

        text = enrich_document(doc)

        if not text:
            print(f"    [failed] No text extracted")
            failed += 1
        elif len(text) < 100:
            print(f"    [skip]   Text too short ({len(text)} chars) — likely a page error")
            skipped += 1
        else:
            with get_session() as session:
                db_doc = session.get(RegulatoryDocument, doc.id)
                if db_doc:
                    db_doc.raw_content = text
                    session.add(db_doc)
                    session.commit()
            print(f"    [ok]     {len(text):,} chars extracted")
            enriched += 1

        # Rate limit — be a good citizen to government servers
        if i < len(to_enrich) - 1:
            time.sleep(RATE_LIMIT_SECONDS)

    return {"enriched": enriched, "skipped": skipped, "failed": failed}


# ── Title Similarity Deduplication ────────────────────────────────────────────

def title_similarity(a: str, b: str) -> float:
    """Return similarity ratio between two titles (0.0–1.0)."""
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


def find_near_duplicates(docs: list[RegulatoryDocument]) -> list[tuple[RegulatoryDocument, RegulatoryDocument, float]]:
    """
    Find pairs of documents from the same agency with similar titles.

    Returns list of (doc_a, doc_b, similarity_score) tuples where
    similarity > SIMILARITY_THRESHOLD.

    Uses O(n²) comparison — acceptable for batches of 20 docs per agency.
    For large sets, switch to MinHash LSH.
    """
    near_dupes = []
    for i, doc_a in enumerate(docs):
        for doc_b in docs[i + 1:]:
            if doc_a.source_agency != doc_b.source_agency:
                continue
            score = title_similarity(doc_a.title, doc_b.title)
            if score >= SIMILARITY_THRESHOLD:
                near_dupes.append((doc_a, doc_b, score))
    return near_dupes
