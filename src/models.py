"""
Central data models for RegWatch AI.

Every feature (F1–F5) reads from and writes to these three tables.
SQLModel gives us one class that serves as both the DB table definition
and a Pydantic validation schema — so we never have duplicate class definitions.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlmodel import Field, Relationship, SQLModel


# ── Enumerations ──────────────────────────────────────────────────────────────

class SourceAgency(str, Enum):
    FED = "fed"                          # Federal Reserve
    CFPB = "cfpb"                        # Consumer Financial Protection Bureau
    OCC = "occ"                          # Office of the Comptroller of the Currency
    FDIC = "fdic"                        # Federal Deposit Insurance Corporation
    FINCEN = "fincen"                    # Financial Crimes Enforcement Network
    FEDERAL_REGISTER = "federal_register"


class DocType(str, Enum):
    FINAL_RULE = "final_rule"
    PROPOSED_RULE = "proposed_rule"
    GUIDANCE = "guidance"
    ENFORCEMENT = "enforcement"
    FAQ = "faq"
    OTHER = "other"


class DocStatus(str, Enum):
    NEW = "new"              # Ingested, not yet summarised
    SUMMARISED = "summarised"  # F2 complete
    MAPPED = "mapped"        # F3 complete
    REVIEWED = "reviewed"    # Human reviewed


class AuditAction(str, Enum):
    INGEST = "ingest"
    SUMMARISE = "summarise"
    MAP = "map"
    TASK_CREATE = "task_create"
    OVERRIDE = "override"
    PII_REDACT = "pii_redact"


class TaskStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


# ── Agency ────────────────────────────────────────────────────────────────────

class Agency(SQLModel, table=True):
    """
    Configuration record for each monitored regulatory agency.

    We store feed config in the DB (not just a config file) so a future UI
    can let compliance officers toggle feeds without a code deploy.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)           # "Federal Reserve"
    slug: str = Field(unique=True)          # "fed"
    feed_url: str                           # RSS URL
    active: bool = Field(default=True)      # Toggle without deleting

    # One agency → many documents
    documents: list["RegulatoryDocument"] = Relationship(back_populates="agency")


# ── RegulatoryDocument ────────────────────────────────────────────────────────

class RegulatoryDocument(SQLModel, table=True):
    """
    The atomic unit of RegWatch AI. Every downstream feature (F2–F5) operates
    on records in this table.

    content_hash is SHA-256(title + url) — used for deduplication in F1.
    summary is a JSON blob written by F2. It is nullable so we can store
    documents before summarisation completes.
    """
    id: Optional[str] = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
    )
    agency_id: Optional[int] = Field(default=None, foreign_key="agency.id")
    agency: Optional[Agency] = Relationship(back_populates="documents")

    # Core fields from the RSS feed
    source_agency: SourceAgency
    doc_type: DocType = Field(default=DocType.OTHER)
    title: str
    url: str = Field(index=True)
    published_date: Optional[datetime] = None
    fetched_at: datetime = Field(default_factory=datetime.utcnow)

    # Deduplication
    content_hash: str = Field(unique=True, index=True)

    # Content
    raw_content: Optional[str] = None      # Full text (populated later)

    # F2 output — stored as a JSON string; None until summarised
    summary_json: Optional[str] = Field(default=None)

    # Lifecycle
    status: DocStatus = Field(default=DocStatus.NEW)
    review_flag: bool = Field(default=False)  # True if F2 confidence < 0.80
    is_anomaly: bool = Field(default=False)   # Flagged by anomaly detector

    # Audit
    audit_logs: list["AuditLog"] = Relationship(back_populates="document")


# ── Task ──────────────────────────────────────────────────────────────────────

class Task(SQLModel, table=True):
    """
    A compliance task drafted by F4's ReAct agent from an F3 impact finding.

    source_* fields are kept alongside the generated content (not just a
    foreign key to impact_results.json, which is a regenerable file, not a
    DB table) so a Task remains traceable back to the exact (policy section,
    regulation) pair that produced it even if F3's matches/classifications
    are later regenerated.
    """
    id: Optional[str] = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Source F3 finding (traceability)
    source_policy_name: str
    source_section_id: str
    source_regulation_doc_id: str
    source_regulation_title: str
    source_impact_level: str

    # Agent-drafted content
    title: str
    description: str
    owner: str
    due_date: str  # YYYY-MM-DD
    status: TaskStatus = Field(default=TaskStatus.OPEN)

    # Additional regulations linked after creation (Day 33's link_regulation
    # tool) -- JSON list of {"regulation_doc_id": ..., "regulation_title": ...}.
    # Separate from source_regulation_* (the ONE pair that produced the task)
    # because a task can turn out to be relevant to more than one regulation.
    linked_regulations_json: Optional[str] = Field(default=None)


# ── AuditLog ──────────────────────────────────────────────────────────────────

class AuditLog(SQLModel, table=True):
    """
    Immutable record of every AI action. Never update or delete rows here.

    This table is the foundation of F5 and SR 11-7 compliance. Every call to
    an LLM, every human override, every document status change writes a row.
    langsmith_trace_id links to the full LLM trace for AI actions.
    """
    id: Optional[str] = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    action: AuditAction
    actor: str = Field(default="system")    # "system" or a user identifier
    doc_id: Optional[str] = Field(default=None, foreign_key="regulatorydocument.id")
    document: Optional[RegulatoryDocument] = Relationship(back_populates="audit_logs")
    payload_json: Optional[str] = Field(default=None)  # JSON: before/after or AI output
    langsmith_trace_id: Optional[str] = None
