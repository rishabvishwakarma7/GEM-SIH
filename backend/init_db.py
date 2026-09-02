"""
Database initialization script (Day 1, still valid for Day 2+).

For the hackathon MVP we use SQLAlchemy's create_all() instead of a full
Alembic migration history — this is faster to iterate on for 5-6 days.
(Alembic can be introduced later if the schema needs versioned migrations
post-hackathon; the models are already structured to support that.)

Day 2 added new columns to tenders/tender_requirements — if you already
ran this on Day 1 and your database still has the OLD schema, drop and
recreate the database (see README "Day 2 setup" section) before rerunning
this script. create_all() only creates missing TABLES, it does not alter
existing ones.

Run with: python init_db.py
"""
import uuid

from app.database import Base, engine, SessionLocal
from app.models.user import User, UserRole
from app.core.security import hash_password


def init_db():
    print("Creating all tables...")
    Base.metadata.create_all(bind=engine)
    print("Tables created.")

    db = SessionLocal()
    try:
        existing_admin = db.query(User).filter(User.email == "admin@cpcl.gem").first()
        if not existing_admin:
            print("Seeding default admin user...")
            admin = User(
                id=uuid.uuid4(),
                full_name="System Administrator",
                email="admin@cpcl.gem",
                hashed_password=hash_password("Admin@123"),
                role=UserRole.ADMIN,
                is_active=True,
            )
            db.add(admin)
            db.commit()
            print("Default admin created: admin@cpcl.gem / Admin@123  (CHANGE THIS PASSWORD)")
        else:
            print("Admin user already exists, skipping seed.")
    finally:
        db.close()


if __name__ == "__main__":
    init_db()
