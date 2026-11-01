"""Database setup for Gati.

SQLite is used by default. Set the DATABASE_URL environment variable to use
another database (for example PostgreSQL). Only PostgreSQL-compatible column
types are used, so the dialect can be swapped in later without schema changes.
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./gati.db")

connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    # Needed so multiple FastAPI request threads can share one SQLite connection
    connect_args["check_same_thread"] = False

engine = create_engine(DATABASE_URL, connect_args=connect_args, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency that yields a request-scoped SQLAlchemy session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables. Idempotent and safe to run on every startup."""
    Base.metadata.create_all(bind=engine)