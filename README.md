# AI Cafe Manager 🚀

A production-grade AI system that helps a café owner analyse sales,
manage inventory, and answer customer queries.

---

## Project Structure

```
ai-cafe-manager/
├── app/
│   ├── main.py              # FastAPI entry point + lifespan hooks
│   ├── config.py            # Environment variable loading
│   ├── api/
│   │   └── routes.py        # API route definitions
│   ├── agents/
│   │   ├── manager.py       # Manager agent (placeholder)
│   │   ├── analyst.py       # Analyst agent (placeholder)
│   │   └── support.py       # Support agent (placeholder)
│   ├── rag/
│   │   ├── ingest.py        # Document ingestion (placeholder)
│   │   ├── retriever.py     # Vector search retrieval (placeholder)
│   │   └── embeddings.py    # OpenAI embeddings wrapper (placeholder)
│   ├── db/
│   │   ├── database.py      # SQLAlchemy engine + session factory
│   │   └── models.py        # ORM models: Sale, Inventory
│   ├── services/
│   │   └── orchestrator.py  # Pipeline coordinator (placeholder)
│   └── utils/
│       └── helpers.py       # init_db(), load_data()
├── data/
│   ├── sales.csv
│   ├── inventory.csv
│   └── faq.txt
├── requirements.txt
├── .env.example
└── README.md
```

---

## Quick Start

### 1. Create and activate a virtual environment

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

```bash
copy .env.example .env   # Windows
# cp .env.example .env   # macOS / Linux
# Edit .env and add your OPENAI_API_KEY
```

### 4. Run the server

```bash
uvicorn app.main:app --reload
```

### 5. Verify it works

```
GET http://localhost:8000/
→ {"message": "AI Cafe Manager Running 🚀"}

Interactive docs:
http://localhost:8000/docs
```

---

## Tech Stack

| Layer       | Technology                        |
|-------------|-----------------------------------|
| Web server  | FastAPI + Uvicorn                 |
| Database    | SQLite via SQLAlchemy ORM         |
| Data        | Pandas CSV ingestion              |
| Vector DB   | FAISS (placeholder)               |
| LLM         | OpenAI API (placeholder)          |
| Config      | python-dotenv                     |

---

## Roadmap

- [x] Step 1 — Foundation (this PR)
- [ ] Step 2 — RAG pipeline (FAISS + OpenAI embeddings)
- [ ] Step 3 — AI agents (Manager, Analyst, Support)
- [ ] Step 4 — Orchestration layer
- [ ] Step 5 — Production hardening (auth, caching, async DB)
