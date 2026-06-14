"""
Build the dual-index vector store for F3 — Day 23.

Builds two VectorIndex collections and saves them to data/f3_indexes/:
  - "policy_sections"    — every N.M section from fixtures/policies/*.txt
  - "regulation_chunks"  — hierarchical chunks of summarised RegulatoryDocuments

Run:
    python -m src.f3_impact.build_indexes
"""

import json
import sys
from pathlib import Path

from sqlmodel import select

from src.database import get_session
from src.models import AuditAction, AuditLog, RegulatoryDocument, DocStatus
from src.f2_summarise.chunker import chunk_hierarchical
from src.f3_impact.extractor import extract_policy_library
from src.f3_impact.vectorstore import VectorIndex

INDEX_DIR = Path(__file__).resolve().parents[2] / "data" / "f3_indexes"
FIXTURES_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "policies"


def _log_pii_redactions(sections) -> None:
    """
    Day 39 (KM #267/268): aggregate each PolicySection's pii_findings by
    policy_name and write one AuditLog(PII_REDACT) row per policy file that
    had >=1 redaction. doc_id is None -- policy files aren't
    RegulatoryDocument rows, but the audit trail still needs a record of
    what was scrubbed before embedding.
    """
    by_policy: dict[str, dict[str, int]] = {}
    for s in sections:
        if not s.pii_findings:
            continue
        totals = by_policy.setdefault(s.policy_name, {})
        for label, count in s.pii_findings.items():
            totals[label] = totals.get(label, 0) + count

    if not by_policy:
        return

    with get_session() as session:
        for policy_name, redaction_counts in by_policy.items():
            session.add(
                AuditLog(
                    action=AuditAction.PII_REDACT,
                    actor="system:f3",
                    doc_id=None,
                    payload_json=json.dumps({
                        "policy_name": policy_name,
                        "redaction_counts": redaction_counts,
                    }),
                )
            )
        session.commit()


def build_policy_index() -> VectorIndex:
    """Embed every N.M policy section from the fixture policy library."""
    sections = extract_policy_library(FIXTURES_DIR)
    _log_pii_redactions(sections)

    index = VectorIndex(name="policy_sections")
    ids = [f"{s.policy_name}::{s.section_id}" for s in sections]
    # Day 29 contextual retrieval: prepend policy/section context to the
    # EMBEDDING input only. metadata["text"] (below) stays the raw section
    # text for display/BM25 — only the vector is influenced by this context.
    texts = [
        f"{s.policy_name} — {s.parent_section}\n{s.section_title}\n{s.text}"
        for s in sections
    ]
    metadatas = [
        {
            "policy_name": s.policy_name,
            "section_id": s.section_id,
            "section_title": s.section_title,
            "parent_section": s.parent_section,
            "text": s.text,
        }
        for s in sections
    ]

    index.upsert_batch(ids, texts, metadatas)
    return index


def build_regulation_index() -> VectorIndex:
    """
    Embed hierarchical chunks of every summarised regulatory document.

    Day 29 tried prepending "Document: {title}\\nSource: {agency}\\nSection:
    {header}\\n\\n" to each chunk before embedding (contextual retrieval,
    KM #167) to give generic Federal Register notice chunks document-level
    context. Measured result: 73.3% -> 70.0% on the golden eval (fixed 2
    mismatches, broke 3 others) -- a net regression on this 30-pair set, so
    NOT applied here. See notes/Day-29-F3.md for the full before/after.
    """
    index = VectorIndex(name="regulation_chunks")

    with get_session() as session:
        docs = session.exec(
            select(RegulatoryDocument).where(
                RegulatoryDocument.status == DocStatus.SUMMARISED
            )
        ).all()

        ids: list[str] = []
        texts: list[str] = []
        metadatas: list[dict] = []

        for doc in docs:
            if not doc.raw_content:
                continue
            chunks = chunk_hierarchical(doc.raw_content)
            for chunk in chunks:
                ids.append(f"{doc.id}::chunk{chunk.index}")
                texts.append(chunk.text)
                metadatas.append(
                    {
                        "doc_id": doc.id,
                        "title": doc.title,
                        "source_agency": doc.source_agency.value,
                        "chunk_index": chunk.index,
                        "section_header": chunk.section_header,
                        "text": chunk.text,
                    }
                )

    if ids:
        index.upsert_batch(ids, texts, metadatas)
    return index


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")

    print("Building policy_sections index...")
    policy_index = build_policy_index()
    policy_index.save(INDEX_DIR)
    print(f"  {len(policy_index)} sections indexed")

    print("Building regulation_chunks index...")
    regulation_index = build_regulation_index()
    regulation_index.save(INDEX_DIR)
    print(f"  {len(regulation_index)} chunks indexed")

    print(f"\nSaved to {INDEX_DIR}")


if __name__ == "__main__":
    main()
