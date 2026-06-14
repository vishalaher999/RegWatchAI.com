"""
F1 feed health checker.

Two checks per agency:
  1. REACHABILITY — can we reach the feed URL and get ≥ 1 parseable entry?
  2. FRESHNESS — do we have documents from this agency in the last N days?

Both checks are read-only: no DB writes, no document processing.
Designed to run fast (< 30s for all agencies) as a daily pre-flight check.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta

import feedparser
import httpx
from sqlmodel import select

from src.database import get_session
from src.f1_ingest.agencies import FR_API_SLUGS
from src.models import Agency, RegulatoryDocument

FRESHNESS_DAYS = 3      # Flag if no new docs from agency in this many days
HTTP_TIMEOUT = 20       # Seconds before giving up on a feed request


@dataclass
class AgencyHealth:
    slug: str
    name: str
    reachable: bool = False
    entry_count: int = 0        # Entries returned by feed on this check
    fresh: bool = False         # True if recent docs exist in DB
    last_doc_date: datetime | None = None
    error: str = ""

    @property
    def healthy(self) -> bool:
        return self.reachable and self.fresh

    @property
    def status_label(self) -> str:
        if self.healthy:
            return "OK"
        if not self.reachable:
            return "UNREACHABLE"
        if not self.fresh:
            return "STALE"
        return "UNKNOWN"


def _check_reachability_rss(agency: Agency) -> tuple[bool, int, str]:
    """Return (reachable, entry_count, error)."""
    try:
        response = httpx.get(
            agency.feed_url,
            timeout=HTTP_TIMEOUT,
            follow_redirects=True,
            headers={"User-Agent": "RegWatch-AI/1.0 (health-check)"},
        )
        response.raise_for_status()
        feed = feedparser.parse(response.text)
        count = len(feed.entries)
        if count == 0:
            return False, 0, "feed returned 0 entries (may be blocked or empty)"
        return True, count, ""
    except httpx.TimeoutException:
        return False, 0, f"timeout after {HTTP_TIMEOUT}s"
    except httpx.HTTPStatusError as exc:
        return False, 0, f"HTTP {exc.response.status_code}"
    except Exception as exc:
        return False, 0, str(exc)[:120]


def _check_reachability_fr_api(agency: Agency) -> tuple[bool, int, str]:
    """Return (reachable, entry_count, error) for Federal Register JSON API."""
    try:
        response = httpx.get(
            agency.feed_url,
            timeout=HTTP_TIMEOUT,
            follow_redirects=True,
            headers={"User-Agent": "RegWatch-AI/1.0 (health-check)"},
        )
        response.raise_for_status()
        data = response.json()
        count = len(data.get("results", []))
        if count == 0:
            return False, 0, "API returned 0 results"
        return True, count, ""
    except httpx.TimeoutException:
        return False, 0, f"timeout after {HTTP_TIMEOUT}s"
    except httpx.HTTPStatusError as exc:
        return False, 0, f"HTTP {exc.response.status_code}"
    except Exception as exc:
        return False, 0, str(exc)[:120]


def _check_freshness(agency: Agency, freshness_days: int = FRESHNESS_DAYS) -> tuple[bool, datetime | None]:
    """
    Return (is_fresh, last_doc_date).
    Fresh = we have at least one document from this agency fetched in the last N days.
    """
    cutoff = datetime.utcnow() - timedelta(days=freshness_days)

    with get_session() as session:
        # Map agency slug to source_agency enum value
        from src.models import SourceAgency
        try:
            source_agency = SourceAgency(agency.slug)
        except ValueError:
            source_agency = SourceAgency.FEDERAL_REGISTER

        docs = session.exec(
            select(RegulatoryDocument)
            .where(RegulatoryDocument.source_agency == source_agency)
            .order_by(RegulatoryDocument.fetched_at.desc())  # type: ignore[arg-type]
        ).all()

    if not docs:
        # No documents at all — not fresh, but don't fail if DB is brand new
        return False, None

    most_recent = docs[0].fetched_at
    is_fresh = most_recent >= cutoff
    return is_fresh, most_recent


def run_health_check(verbose: bool = True) -> list[AgencyHealth]:
    """
    Run health checks for all active agencies.
    Returns a list of AgencyHealth results.
    """
    with get_session() as session:
        agencies = session.exec(select(Agency).where(Agency.active == True)).all()

    results: list[AgencyHealth] = []

    for agency in agencies:
        health = AgencyHealth(slug=agency.slug, name=agency.name)

        # Reachability
        checker = _check_reachability_fr_api if agency.slug in FR_API_SLUGS else _check_reachability_rss
        health.reachable, health.entry_count, health.error = checker(agency)

        # Freshness
        health.fresh, health.last_doc_date = _check_freshness(agency)

        results.append(health)

        if verbose:
            status = health.status_label
            date_str = health.last_doc_date.strftime("%Y-%m-%d %H:%M") if health.last_doc_date else "never"
            entry_str = f"{health.entry_count} entries" if health.reachable else health.error
            print(f"  [{status:<11}] {agency.slug:<22} feed:{entry_str}  last_doc:{date_str}")

    return results


def health_summary(results: list[AgencyHealth]) -> dict:
    """Return a summary dict suitable for the AuditLog payload."""
    return {
        "total": len(results),
        "healthy": sum(1 for r in results if r.healthy),
        "unreachable": sum(1 for r in results if not r.reachable),
        "stale": sum(1 for r in results if r.reachable and not r.fresh),
        "agencies": [
            {
                "slug": r.slug,
                "status": r.status_label,
                "entry_count": r.entry_count,
                "last_doc_date": r.last_doc_date.isoformat() if r.last_doc_date else None,
                "error": r.error,
            }
            for r in results
        ],
    }
