"""
Agency seed data and database writer for F1.

AGENCY_SEEDS is the single source of truth for which feeds we monitor.
To add a new agency: add an entry here and re-run scripts/setup_db.py.
"""

from sqlmodel import select

from src.database import get_session
from src.models import Agency

# Federal Register JSON API base — used for CFPB, OCC, FDIC, FinCEN
# The FR RSS feeds block automated requests; the JSON API is public and stable.
_FR_API_BASE = "https://www.federalregister.gov/api/v1/documents.json"

AGENCY_SEEDS = [
    {
        "name": "Federal Reserve",
        "slug": "fed",
        # Direct Fed press feed — reliable for Fed-specific releases
        "feed_url": "https://www.federalreserve.gov/feeds/press_all.xml",
    },
    {
        "name": "Consumer Financial Protection Bureau",
        "slug": "cfpb",
        # FR JSON API filtered by agency — use fetch_fr_api() not fetch_feed()
        "feed_url": _FR_API_BASE + "?conditions[agencies][]=consumer-financial-protection-bureau&order=newest&per_page=20",
    },
    {
        "name": "Office of the Comptroller of the Currency",
        "slug": "occ",
        "feed_url": _FR_API_BASE + "?conditions[agencies][]=comptroller-of-the-currency&order=newest&per_page=20",
    },
    {
        "name": "Federal Deposit Insurance Corporation",
        "slug": "fdic",
        "feed_url": _FR_API_BASE + "?conditions[agencies][]=federal-deposit-insurance-corporation&order=newest&per_page=20",
    },
    {
        "name": "Financial Crimes Enforcement Network",
        "slug": "fincen",
        "feed_url": _FR_API_BASE + "?conditions[agencies][]=financial-crimes-enforcement-network&order=newest&per_page=20",
    },
    {
        "name": "Federal Register (Financial Agencies)",
        "slug": "federal_register",
        # Catch-all for joint rules spanning multiple agencies
        "feed_url": _FR_API_BASE + "?conditions[agencies][]=federal-reserve-system&conditions[agencies][]=consumer-financial-protection-bureau&conditions[agencies][]=federal-deposit-insurance-corporation&order=newest&per_page=20",
    },
]

# Slugs that use the Federal Register JSON API instead of RSS
FR_API_SLUGS = {"cfpb", "occ", "fdic", "fincen", "federal_register"}


def seed_agencies() -> None:
    """
    Insert agency records if they don't already exist.
    Safe to call multiple times — uses slug as the uniqueness check.
    """
    with get_session() as session:
        for data in AGENCY_SEEDS:
            existing = session.exec(
                select(Agency).where(Agency.slug == data["slug"])
            ).first()

            if existing:
                print(f"  [skip] {data['name']} already seeded")
                continue

            agency = Agency(**data)
            session.add(agency)
            session.commit()
            print(f"  [ok]   Seeded {data['name']}")
