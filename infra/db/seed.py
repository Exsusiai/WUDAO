"""Seed script: creates default AppSettings row in the database."""
import os
import sys

# Ensure project root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from sqlmodel import Session, select

from python.core.database import engine, init_db
from python.core.models import AppSettings


def seed_app_settings(session: Session) -> None:
    """Create default AppSettings if none exist."""
    existing = session.exec(select(AppSettings)).first()
    if existing:
        print("AppSettings already seeded, skipping.")
        return

    session.add(AppSettings(current_mode="sandbox"))
    print("Seeded default AppSettings (mode=sandbox).")


def run_seed() -> None:
    """Run all seed functions."""
    init_db()
    with Session(engine) as session:
        seed_app_settings(session)
        session.commit()
    print("Seeding complete.")


if __name__ == "__main__":
    run_seed()
