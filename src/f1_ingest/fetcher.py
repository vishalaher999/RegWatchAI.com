"""
RSS feed fetcher and parser for F1.

Fetches a feed URL, parses each entry with feedparser, and returns a list
of RegulatoryDocument instances ready to be deduped and saved.

feedparser normalises date formats, encoding, and field names across all
agency feeds so downstream code never has to deal with raw RSS differences.
"""

from datetime import datetime
from typing import Optional

import feedparser
import httpx

from src.f1_ingest.classifier import classify_doc_type
from src.f1_ingest.dedup import compute_hash
from src.models import Agency, RegulatoryDocument, SourceAgency

# Slug → SourceAgency enum mapping
_SLUG_TO_ENUM: dict[str, SourceAgency] = {
    "fed": SourceAgency.FED,
    "cfpb": SourceAgency.CFPB,
    "occ": SourceAgency.OCC,
    "fdic": SourceAgency.FDIC,
    "fincen": SourceAgency.FINCEN,
    "federal_register": SourceAgency.FEDERAL_REGISTER,
}


def _parse_date(entry: feedparser.FeedParserDict) -> Optional[datetime]:
    """
    Extract a datetime from a feed entry.
    feedparser normalises most date formats into a time.struct_time.
    We prefer published_parsed, fall back to updated_parsed.
    """
    for field in ("published_parsed", "updated_parsed"):
        value = getattr(entry, field, None)
        if value:
            try:
                return datetime(*value[:6])
            except (TypeError, ValueError):
                continue
    return None


def fetch_fr_api(agency: Agency, timeout: int = 30) -> list[RegulatoryDocument]:
    """
    Fetch documents from the Federal Register JSON API.

    Used for CFPB, OCC, FDIC, FinCEN, and the Federal Register catch-all.
    The FR RSS feeds block automated requests; the JSON API is fully public.

    The API returns a `results` array. Each result has: title, html_url,
    publication_date, type, abstract.
    """
    source_agency = _SLUG_TO_ENUM.get(agency.slug, SourceAgency.FEDERAL_REGISTER)
    documents: list[RegulatoryDocument] = []

    try:
        response = httpx.get(
            agency.feed_url,
            timeout=timeout,
            follow_redirects=True,
            headers={"User-Agent": "RegWatch-AI/1.0 (compliance monitoring)"},
        )
        response.raise_for_status()
        data = response.json()
    except httpx.HTTPError as exc:
        print(f"  [error] {agency.name}: HTTP error — {exc}")
        return documents
    except Exception as exc:
        print(f"  [error] {agency.name}: unexpected error — {exc}")
        return documents

    for result in data.get("results", []):
        title = (result.get("title") or "").strip()
        url = (result.get("html_url") or "").strip()

        if not title or not url:
            continue

        content_hash = compute_hash(title, url)
        doc_type = classify_doc_type(title)

        # FR API uses ISO date strings like "2026-06-01"
        pub_date_str = result.get("publication_date")
        published_date: Optional[datetime] = None
        if pub_date_str:
            try:
                published_date = datetime.strptime(pub_date_str, "%Y-%m-%d")
            except ValueError:
                pass

        raw_content = (result.get("abstract") or "").strip()

        doc = RegulatoryDocument(
            agency_id=agency.id,
            source_agency=source_agency,
            doc_type=doc_type,
            title=title,
            url=url,
            published_date=published_date,
            content_hash=content_hash,
            raw_content=raw_content,
        )
        documents.append(doc)

    return documents


def fetch_feed(agency: Agency, timeout: int = 30) -> list[RegulatoryDocument]:
    """
    Fetch the agency's RSS feed and parse all entries.

    Returns a list of unsaved RegulatoryDocument instances.
    Duplicates are NOT filtered here — that happens in the orchestrator
    so the caller can decide what to log.

    Args:
        agency:  The Agency record containing feed_url and slug.
        timeout: HTTP timeout in seconds. Government feeds can be slow.
    """
    source_agency = _SLUG_TO_ENUM.get(agency.slug, SourceAgency.FEDERAL_REGISTER)
    documents: list[RegulatoryDocument] = []

    try:
        # Fetch the raw feed content first so we control the HTTP layer
        # (feedparser's built-in fetcher doesn't respect timeouts reliably)
        response = httpx.get(
            agency.feed_url,
            timeout=timeout,
            follow_redirects=True,
            headers={"User-Agent": "RegWatch-AI/1.0 (compliance monitoring)"},
        )
        response.raise_for_status()
        feed = feedparser.parse(response.text)
    except httpx.HTTPError as exc:
        print(f"  [error] {agency.name}: HTTP error — {exc}")
        return documents
    except Exception as exc:
        print(f"  [error] {agency.name}: unexpected error — {exc}")
        return documents

    for entry in feed.entries:
        title = getattr(entry, "title", "").strip()
        url = getattr(entry, "link", "").strip()

        # Skip entries with no title or URL — we can't deduplicate them
        if not title or not url:
            continue

        content_hash = compute_hash(title, url)
        published_date = _parse_date(entry)
        doc_type = classify_doc_type(title)

        # Raw content: prefer summary, fall back to description
        raw_content = (
            getattr(entry, "summary", None)
            or getattr(entry, "description", None)
            or ""
        )

        doc = RegulatoryDocument(
            agency_id=agency.id,
            source_agency=source_agency,
            doc_type=doc_type,
            title=title,
            url=url,
            published_date=published_date,
            content_hash=content_hash,
            raw_content=raw_content,
        )
        documents.append(doc)

    return documents
