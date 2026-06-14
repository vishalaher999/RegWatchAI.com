"""
Deduplication logic for F1.

Uses SHA-256(title + url) as a content fingerprint.
A document is a duplicate if its hash already exists in the database.
"""

import hashlib

from sqlmodel import select

from src.database import get_session
from src.models import RegulatoryDocument


def compute_hash(title: str, url: str) -> str:
    """Return SHA-256 hex digest of (title + url)."""
    raw = f"{title.strip()}{url.strip()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def is_duplicate(content_hash: str) -> bool:
    """Return True if a document with this hash already exists in the DB."""
    with get_session() as session:
        existing = session.exec(
            select(RegulatoryDocument).where(
                RegulatoryDocument.content_hash == content_hash
            )
        ).first()
        return existing is not None
