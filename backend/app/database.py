"""
Database engine + session management.

Why this file exists: SQLAlchemy needs one Engine per process (connection
pooling) and a session factory that routes create one-per-request session
from. `get_db` is a FastAPI dependency — every route that touches the DB
declares `db: Session = Depends(get_db)` and gets a clean session that's
automatically closed after the request, even on error. `session_scope` is
the same idea for callers that aren't FastAPI routes (the MCP server,
scripts) and so can't use a `Depends`-based generator.
"""

from contextlib import contextmanager

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


@contextmanager
def session_scope():
    """Context-manager version of the same session lifecycle, for callers
    outside FastAPI's dependency injection (the MCP server's tool
    functions). Same SessionLocal as get_db -- just a different way to get
    one and have it reliably closed afterward."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()