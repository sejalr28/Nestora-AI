"""
Database engine + session management.

Why this file exists: SQLAlchemy needs one Engine per process (connection
pooling) and a session factory that routes create one-per-request session
from. `get_db` is a FastAPI dependency — every route that touches the DB
declares `db: Session = Depends(get_db)` and gets a clean session that's
automatically closed after the request, even on error.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# All ORM models (Step 2) will inherit from this Base.
Base = declarative_base()


def get_db():
    """FastAPI dependency: yields a DB session, always closes it after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
