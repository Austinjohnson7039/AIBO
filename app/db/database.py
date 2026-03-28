from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.config import DATABASE_URL

# ─── Engine ───────────────────────────────────────────────────────────────────
# connect_args is required for SQLite to allow multi-threaded access (FastAPI)
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)

# ─── Session Factory ──────────────────────────────────────────────────────────
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ─── Declarative Base ─────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    """All ORM models inherit from this base."""
    pass


# ─── Dependency ───────────────────────────────────────────────────────────────
def get_db():
    """FastAPI dependency that yields a DB session and ensures cleanup."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
