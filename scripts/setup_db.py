"""
One-time database setup script.

Creates all tables and seeds agency records.
Safe to run multiple times — existing data is not overwritten.

Usage:
    python scripts/setup_db.py
"""

import sys
from pathlib import Path

# Ensure the project root is on sys.path so `src` imports work
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import create_db_and_tables
from src.f1_ingest.agencies import seed_agencies

if __name__ == "__main__":
    print("Creating database tables...")
    create_db_and_tables()
    print("Done.\n")

    print("Seeding agencies...")
    seed_agencies()
    print("\nSetup complete. Database is ready.")
