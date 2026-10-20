# app/database.py
# Creates the database connection and gives each request its own session.

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import settings


def normalize_url(url: str) -> str:
    """Hosting providers give URLs like postgres://... ; SQLAlchemy needs
    postgresql+psycopg://... to know which driver to use."""
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


# The engine manages a pool of connections to the database.
# pool_pre_ping checks a connection is alive before using it
# (cloud databases close idle connections).
engine = create_engine(normalize_url(settings.database_url), pool_pre_ping=True)

# A session = one "conversation" with the database (one per request).
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    """Every table class inherits from this, so SQLAlchemy knows about it."""


def get_db():
    """FastAPI dependency: open a session for the request, always close it after.
    'yield' hands the session to the route; the code after yield runs when the
    request finishes, even if it crashed."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
