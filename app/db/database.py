from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.config import DATABASE_URL

# ─── Engine ───────────────────────────────────────────────────────────────────

# Handle SQLite specific arguments (not needed for Postgres)
engine_args = {}
if DATABASE_URL.startswith("sqlite"):
    engine_args["connect_args"] = {"check_same_thread": False}
elif DATABASE_URL.startswith("postgres"):
    engine_args["pool_size"] = 10
    engine_args["max_overflow"] = 20
    engine_args["pool_recycle"] = 3600
    engine_args["pool_pre_ping"] = True

engine = create_engine(
    DATABASE_URL,
    **engine_args
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
