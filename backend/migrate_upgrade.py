"""
Upgrade migration — adds all new tables and columns introduced by the
platform upgrade (risk intelligence, duplicate detection, smart alerts,
multi-level review workflow, final decisions).

Idempotent: safe to run multiple times — checks existence before every
ALTER / CREATE so it skips work already done.

Run with:  python migrate_upgrade.py
"""
from sqlalchemy import inspect, text

from app.database import Base, engine
import app.models  # noqa: F401  registers all models with Base.metadata

# ---------------------------------------------------------------------------
# New columns to add to EXISTING tables
# (table, column, postgres_type, nullable_default)
# ---------------------------------------------------------------------------
NEW_COLUMNS = [
    # bidders — risk intelligence
    ("bidders", "risk_score", "FLOAT", "NULL"),
    ("bidders", "risk_level", "VARCHAR(20)", "NULL"),
    ("bidders", "risk_factors", "TEXT", "NULL"),
    ("bidders", "risk_summary", "TEXT", "NULL"),
    ("bidders", "risk_analyzed_at", "TIMESTAMP", "NULL"),

    # bidder_documents — duplicate detection
    ("bidder_documents", "file_hash", "VARCHAR(64)", "NULL"),
    ("bidder_documents", "document_fingerprint", "TEXT", "NULL"),

    # compliance_results — explainable compliance
    ("compliance_results", "evidence_chain", "TEXT", "NULL"),
    ("compliance_results", "risk_breakdown", "TEXT", "NULL"),

    # compliance_results — Day 6 columns (may already exist from migrate_day6.py)
    ("compliance_results", "ai_recommendation", "TEXT", "NULL"),
    ("compliance_results", "ai_recommendation_generated_at", "TIMESTAMP", "NULL"),
]

# ---------------------------------------------------------------------------
# New indexes on existing tables
# ---------------------------------------------------------------------------
NEW_INDEXES = [
    # idx name, table, column
    ("ix_bidder_documents_file_hash", "bidder_documents", "file_hash"),
]


def migrate():
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    # 1. Create brand-new tables
    print("Creating new tables (if not exist)...")
    Base.metadata.create_all(bind=engine)
    print("  Done.")

    # 2. Re-inspect after create_all
    inspector = inspect(engine)

    # 3. Add missing columns to existing tables
    print("Adding missing columns to existing tables...")
    with engine.begin() as conn:
        for table, column, coltype, default in NEW_COLUMNS:
            if table not in existing_tables:
                print(f"  [skip] {table} is a new table — column already created above")
                continue
            existing_cols = {c["name"] for c in inspector.get_columns(table)}
            if column in existing_cols:
                print(f"  [skip] {table}.{column} already exists")
                continue
            print(f"  [add]  {table}.{column} {coltype}")
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {coltype}"))

    # 4. Create missing indexes
    print("Creating missing indexes...")
    existing_indexes = {}
    for tname in inspector.get_table_names():
        existing_indexes[tname] = {idx["name"] for idx in inspector.get_indexes(tname)}

    with engine.begin() as conn:
        for idx_name, table, column in NEW_INDEXES:
            if idx_name in existing_indexes.get(table, set()):
                print(f"  [skip] index {idx_name} already exists")
                continue
            # Check column exists first
            col_names = {c["name"] for c in inspector.get_columns(table)}
            if column not in col_names:
                print(f"  [skip] column {table}.{column} does not exist yet — skipping index")
                continue
            print(f"  [create] index {idx_name} on {table}({column})")
            conn.execute(text(
                f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table} ({column})"
            ))

    print("\nUpgrade migration complete.")
    print("New tables added:")
    new_table_names = [
        "document_risk_analyses",
        "duplicate_document_matches",
        "alerts",
        "review_cases",
        "review_actions",
        "final_decisions",
    ]
    for t in new_table_names:
        print(f"  - {t}")


if __name__ == "__main__":
    migrate()
