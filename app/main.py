"""
main.py
───────
FastAPI application entry point.

Start the server:
    uvicorn app.main:app --reload
"""

import logging

from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.api.routes import router
from app.config import APP_TITLE, APP_VERSION, DEBUG
from app.utils.helpers import init_db, load_data

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ─── Lifespan (startup / shutdown) ────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Modern FastAPI lifespan context manager.
    Replaces the deprecated @app.on_event("startup") pattern.
    """
    logger.info("Starting up %s v%s …", APP_TITLE, APP_VERSION)
    
    # 1. Run migrations (idempotent)
    from migrate_db import migrate
    try:
        migrate()
    except Exception as e:
        logger.warning("Migration notice: %s", e)

    # 2. Init DB and load data
    init_db()
    load_data()
    logger.info("Startup complete. Server is ready.")
    yield
    logger.info("Shutting down %s.", APP_TITLE)


from fastapi.middleware.cors import CORSMiddleware

# ─── App Factory ──────────────────────────────────────────────────────────────
app = FastAPI(
    title=APP_TITLE,
    version=APP_VERSION,
    description="Production-grade AI system for café operations management.",
    lifespan=lifespan,
)

# Enable CORS for cross-origin access (Streamlit <-> FastAPI)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For production, we can refine this to specific domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routers ──────────────────────────────────────────────────────────────────
app.include_router(router)
