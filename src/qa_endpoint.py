import time
import json
import os
from dotenv import load_dotenv
from src.utils import get_supabase_client, search_documents

# Load environment variables from .env file
load_dotenv()

def perform_qa_with_citations(query, match_count=5):
    """
    Perform RAG QA with inline citations for the given query.
    """
    start_time = time.time()

    # Get Supabase client
    client = get_supabase_client()

    # Perform vector search
    results = search_documents(client, query, match_count=match_count)

    retrieval_time = (time.time() - start_time) * 1000  # ms

    if not results:
        return {"answer": "No relevant information found.", "citations": [], "latency_ms": retrieval_time}

    # Generate answer with citations (simplified; in real scenario, use LLM)
    citations = []
    context_parts = []
    for i, result in enumerate(results):
        url = result.get("url", "Unknown")
        content = result.get("content", "")
        citations.append(f"[{i+1}] {url}")
        context_parts.append(f"From {url}: {content[:500]}...")  # Truncate for brevity

    context = "\n".join(context_parts)
    # Simplified answer generation (replace with LLM call in production)
    answer = f"Based on the provided context, here's an answer to '{query}': {context[:1000]}..."  # Mock answer

    return {
        "answer": answer,
        "citations": citations,
        "latency_ms": retrieval_time
    }

if __name__ == "__main__":
    query = "What is Pydantic AI?"
    result = perform_qa_with_citations(query)
    print(json.dumps(result, indent=2))
