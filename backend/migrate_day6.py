"""
Day 6 migration - adds the new compliance_results columns (ai_recommendation,
ai_recommendation_generated_at) to an EXISTING database.

Why this is needed: init_db.py uses SQLAlchemy's create_all(), which only
creates tables that don't exist yet - it never ALTERs a table that's already
there. If you ran init_db.py before the Day 6 changes, your `compliance_results`
table is missing the two new columns and every /api/dashboard/... or
/api/compliance/... query that touches that table will fail with something
like:  column compliance_results.ai_recommendation does not exist

This script is idempotent - safe to run multiple times, and safe to run even
if the columns already exist (it checks first and skips them).

Run with: python migrate_day6.py
"""
from sqlalchemy import inspect, text

from app.database import Base, engine, SessionLocal
import app.models  # noqa: F401  (import so Base.metadata knows about every model)


COLUMNS_TO_ADD = [
    ("compliance_results", "ai_recommendation", "TEXT"),
    ("compliance_results", "ai_recommendation_generated_at", "TIMESTAMP"),
]


def migrate():
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    # 1. Create any brand-new tables (e.g. `notifications`) that don't exist yet.
    print("Creating any missing tables (e.g. notifications)...")
    Base.metadata.create_all(bind=engine)
    print("Done.")

    # 2. ALTER existing tables that are missing newly-added columns.
    inspector = inspect(engine)  # re-inspect after create_all
    with engine.begin() as conn:
        for table, column, coltype in COLUMNS_TO_ADD:
            if table not in existing_tables:
                # Table itself was just created above with the column already
                # in place - nothing to ALTER.
                continue
            existing_columns = {c["name"] for c in inspector.get_columns(table)}
            if column in existing_columns:
                print(f"  [skip] {table}.{column} already exists")
                continue
            print(f"  [add]  {table}.{column} {coltype}")
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {coltype}"))

    print("Migration complete.")


if __name__ == "__main__":
    migrate()
