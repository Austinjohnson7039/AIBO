"""
generator.py
────────────
RAG Answer Generator layer.
Combines the FAISS Retriever with OpenAI's Chat API to ground answers in the retrieved context.

Design decisions:
- The context injection strictly instructs the LLM to only use the provided context,
  halting hallucinations.
- Uses temperature=0.0 to ensure deterministic, factual responses.
- Handles API errors gracefully so the application won't crash when OpenAI is down
  or the API key is missing.
"""

from __future__ import annotations

import logging
from typing import Optional

from openai import OpenAI, OpenAIError

from app.config import GROQ_API_KEY
from app.rag.retriever import Retriever

logger = logging.getLogger(__name__)

# ─── Constants ────────────────────────────────────────────────────────────────

LLM_MODEL = "openai/gpt-oss-120b"
GROQ_BASE_URL = "https://api.groq.com/openai/v1"


# ─── Internal helpers ─────────────────────────────────────────────────────────

def _build_client(api_key: Optional[str] = None) -> OpenAI:
    """Return an OpenAI client, preferring an explicitly passed key."""
    key = api_key or GROQ_API_KEY
    if not key:
        raise EnvironmentError(
            "GROQ_API_KEY is not set. "
            "Add it to your .env file or set the environment variable."
        )
    return OpenAI(api_key=key, base_url=GROQ_BASE_URL)


# ─── Generator ────────────────────────────────────────────────────────────────

class RAGGenerator:
    """
    RAG Answer Generator.
    
    Responsibilities:
    1. Retrieves context using the Retriever.
    2. Constructs a strict prompt to prevent hallucination.
    3. Calls the OpenAI Chat API.
    4. Returns the generated answer alongside the sources used.
    """

    def __init__(self, retriever: Optional[Retriever] = None):
        """
        Initialise generator with a retriever. 
        If none is provided, creates and loads a default one.
        """
        if retriever is None:
            self.retriever = Retriever()
            # Attempt to load, but swallow missing index errors gracefully 
            # so the application can start (useful if ingestion hasn't run yet).
            try:
                self.retriever.load_index()
            except FileNotFoundError as e:
                logger.warning(
                    f"RAGGenerator created but index could not be loaded: {e}. "
                    "Make sure to run the ingestion pipeline."
                )
        else:
            self.retriever = retriever

    def generate_answer(self, query: str, top_k: int = 3, api_key: Optional[str] = None, memory_context: str = "") -> dict:
        """
        Generate an answer to the query based purely on retrieved context.
        
        Args:
            query: Natural-language question or statement.
            top_k: Number of retrieved chunks to use as context.
            api_key: Optional override for the OpenAI API key.
            memory_context: Formatted string of conversation history.
            
        Returns:
            A dictionary with the "answer" and a list of "sources" (original text chunks).
        """
        logger.info("Generating answer for query: %r", query[:50])
        
        if not self.retriever.is_loaded:
            try:
                self.retriever.load_index()
            except FileNotFoundError:
                pass
                
            if not self.retriever.is_loaded:
                return {
                    "answer": "System is not fully initialized. Pending knowledge base indexing.",
                    "sources": []
                }
        
        # 1. Retrieve context
        try:
            results = self.retriever.search(query, top_k=top_k)
        except Exception as e:
            logger.error("Failed to retrieve context: %s", e)
            return {
                "answer": "I'm sorry, I encountered an error while searching the knowledge base.",
                "sources": []
            }
            
        if not results:
            return {
                "answer": "I don't know based on available data.",
                "sources": []
            }

        # 2. Extract and format context
        context_texts = []
        sources = []
        for res in results:
            context_texts.append(f"- {res.text}")
            sources.append(res.text)
            
        context_str = "\n".join(context_texts)
        
        # 3. Construct prompt
        system_prompt = (
            "You are an AI assistant for a cafe business.\n"
            "Answer ONLY using the provided context.\n"
            "If the answer is not in the context, say 'I don't know based on available data.'\n"
            "Expert Examples: If there's an 'Expert Examples' section in the context, "
            "emulate the tone, formatting, and high precision used in those successful answers."
        )
        
        user_prompt = f"Question: {query}\n\nRetrieved Context:\n{context_str}"
        if memory_context:
            user_prompt = f"Conversation History & Memory:\n{memory_context}\n\n{user_prompt}"
        
        # 4. Call LLM
        try:
            client = _build_client(api_key)
            response = client.chat.completions.create(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.0  # Keep it deterministic and strict about grounding
            )
            answer = response.choices[0].message.content.strip()
        except EnvironmentError as e:
            logger.error(str(e))
            return {
                "answer": "Configuration error: Groq API key is missing.",
                "sources": sources
            }
        except OpenAIError as e:
            logger.error("OpenAI API Error: %s", e)
            return {
                "answer": "I'm sorry, the language model service is currently unavailable.",
                "sources": sources
            }
        except Exception as e:
            logger.exception("Unexpected error during generation: %s", e)
            return {
                "answer": "I'm sorry, an unexpected error occurred while generating the answer.",
                "sources": sources
            }
            
        logger.info("Answer generated successfully.")
        return {
            "answer": answer,
            "sources": sources
        }


# ─── Quick test ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    
    test_query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Do you deliver?"
    
    rag = RAGGenerator()
    if rag.retriever.is_loaded:
        print(f"\n🔍 Query: {test_query!r}\n")
        response = rag.generate_answer(test_query)
        
        print(f"🤖 Answer : {response['answer']}")
        print(f"📚 Sources ({len(response['sources'])}):")
        for i, source in enumerate(response['sources'], start=1):
            print(f"  [{i}] {source}")
        print()
    else:
        print("Cannot run test: Index not loaded. Run ingest.py first with a valid OPENAI_API_KEY.")
