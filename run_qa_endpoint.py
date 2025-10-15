#!/usr/bin/env python3
"""
Wrapper script to run QA endpoint with proper environment setup.

This script ensures:
1. Environment variables are loaded from .env
2. Python path is set correctly
3. All dependencies are available
"""

import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Verify required environment variables
required_vars = ['SUPABASE_URL', 'SUPABASE_SERVICE_KEY', 'OPENAI_API_KEY']
missing_vars = [var for var in required_vars if not os.getenv(var)]

if missing_vars:
    print(f"❌ Error: Missing required environment variables: {', '.join(missing_vars)}")
    print(f"\nPlease set them in your .env file:")
    for var in missing_vars:
        print(f"  {var}=your-value-here")
    sys.exit(1)

# Now import and run the QA endpoint
import time
import json
from src.utils import get_supabase_client, search_documents


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
    print("🔍 Testing QA Endpoint with Retrieval-Augmented Generation\n")
    print("=" * 70)
    
    # Test query
    query = "What is Pydantic AI?"
    print(f"Query: {query}\n")
    
    try:
        result = perform_qa_with_citations(query)
        
        print("✅ Results:")
        print("-" * 70)
        print(f"\n📝 Answer:\n{result['answer']}\n")
        print(f"📚 Citations:")
        for citation in result['citations']:
            print(f"  {citation}")
        print(f"\n⏱️  Retrieval Latency: {result['latency_ms']:.2f} ms")
        
        # Check if latency meets requirement
        if result['latency_ms'] <= 300:
            print(f"✅ Latency requirement met (≤ 300 ms)")
        else:
            print(f"⚠️  Latency exceeds requirement: {result['latency_ms']:.2f} ms > 300 ms")
        
        print("\n" + "=" * 70)
        print("\n📊 Full JSON Response:")
        print(json.dumps(result, indent=2))
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
