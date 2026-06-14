"""
Database engine and session management for RegWatch AI.

Uses SQLModel (which wraps SQLAlchemy) to provide:
- A single engine connected to the URL in .env (SQLite for dev, Postgres for prod)
- A session factory for safe, scoped DB access
- create_db_and_tables() to initialise the schema on first run

Usage:
    from src.database import get_session, create_db_and_tables

    create_db_and_tables()          # run once at startup

    with get_session() as session:
        session.add(some_record)
        session.commit()
"""

import os
from contextlib import contextmanager

from dotenv import load_dotenv
from sqlmodel import Session, SQLModel, create_engine

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./regwatch.db")

# connect_args is SQLite-specific: allows the same connection to be used
# across threads (needed for async frameworks and testing). Safe for SQLite;
# not needed for Postgres.
_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=_connect_args, echo=False)


def create_db_and_tables() -> None:
    """Create all tables defined in SQLModel metadata. Safe to call multiple times."""
    SQLModel.metadata.create_all(engine)


@contextmanager
def get_session():
    """
    Context manager that yields a DB session and auto-commits or rolls back.

    Always use this instead of creating a Session directly — it ensures the
    connection is returned to the pool even if an exception is raised.
    """
    with Session(engine) as session:
        yield session
