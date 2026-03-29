import logging
from app.rag.ingest import ingest_documents
from app.rag.retriever import Retriever

logging.basicConfig(level=logging.INFO)

print("Starting ingestion...")
ingest_documents(force=True)
print("Ingestion complete.")

retriever = Retriever()
retriever.load_index()
print("Retriever loaded successfully.")
print(f"Chunks: {retriever.num_chunks}")
