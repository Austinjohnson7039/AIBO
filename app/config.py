import os
from dotenv import load_dotenv

load_dotenv(override=True)

# ─── Groq API ─────────────────────────────────────────────────────────────────
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")

# ─── Database ─────────────────────────────────────────────────────────────────
DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./cafe.db")

# ─── App Meta ─────────────────────────────────────────────────────────────────
APP_TITLE: str = "AI Cafe Manager"
APP_VERSION: str = "1.0.0"
DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
