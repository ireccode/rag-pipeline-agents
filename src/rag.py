import os
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from collections import deque
import re
import hashlib

from supabase import create_client, Client
from openai import OpenAI
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

load_dotenv( )

# Configuration from environment variables
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1" )
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4.1-mini")
CORPUS_URL = os.getenv("CORPUS_URL")

# RAG Advanced Strategies
USE_HYBRID_SEARCH = os.getenv("USE_HYBRID_SEARCH", "False").lower() == "true"
USE_RERANKING = os.getenv("USE_RERANKING", "False").lower() == "true"

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# Initialize OpenAI client for RAG QA
openai_client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)

# Initialize embedding model
# Using a local sentence-transformer for embeddings for efficiency and offline capability
# For production, consider a hosted embedding service or a more robust model.
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

# --- Supabase Vector Store Setup ---
async def setup_supabase_vector_store():
    # This function would typically create the `documents` table with a `vector` column
    # and enable the `pg_vector` extension. For simplicity, we assume it's already set up.
    # In a real scenario, you'd run SQL commands like:
    # CREATE EXTENSION IF NOT EXISTS vector;
    # CREATE TABLE IF NOT EXISTS documents (
    #     id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    #     content TEXT,
    #     metadata JSONB,
    #     embedding VECTOR(384) -- 384 is the dimension for all-MiniLM-L6-v2
    # );
    print("Supabase vector store assumed to be set up. Ensure 'vector' extension is enabled and 'documents' table exists.")

# --- Web Crawler and Ingestion ---
async def fetch_page(session, url):
    try:
        async with session.get(url, timeout=10) as response:
            response.raise_for_status()  # Raise an exception for HTTP errors
            return await response.text()
    except aiohttp.ClientError as e:
        print(f"Error fetching {url}: {e}" )
        return None

def extract_text_from_html(html_content):
    if not html_content: return ""
    soup = BeautifulSoup(html_content, 'html.parser')
    # Remove script and style elements
    for script_or_style in soup(['script', 'style']):
        script_or_style.decompose()
    text = soup.get_text()
    # Break into lines and remove leading/trailing space on each
    lines = (line.strip() for line in text.splitlines())
    # Break multi-headlines into a single line
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    # Drop blank lines
    text = '\n'.join(chunk for chunk in chunks if chunk)
    return text

def intelligent_chunking(text, chunk_size=500, chunk_overlap=50):
    # Simple chunking for now. Advanced chunking would consider semantic boundaries.
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size - chunk_overlap):
        chunk = " ".join(words[i:i + chunk_size])
        if chunk:
            chunks.append(chunk)
    return chunks

def generate_embedding(text):
    return embedding_model.encode(text).tolist()

async def ingest_document(url, content, metadata=None):
    text = extract_text_from_html(content)
    chunks = intelligent_chunking(text)
    if not chunks:
        print(f"No content to chunk for {url}")
        return

    documents_to_insert = []
    for i, chunk in enumerate(chunks):
        embedding = generate_embedding(chunk)
        doc_metadata = {"url": url, "chunk_index": i}
        if metadata: doc_metadata.update(metadata)
        documents_to_insert.append({
            "content": chunk,
            "metadata": doc_metadata,
            "embedding": embedding
        })

    if documents_to_insert:
        try:
            response = supabase.from_('documents').insert(documents_to_insert).execute()
            if response.data:
                print(f"Ingested {len(response.data)} chunks from {url}")
            elif response.error:
                print(f"Error ingesting {url}: {response.error}")
        except Exception as e:
            print(f"Supabase ingestion error for {url}: {e}")

async def crawl_and_ingest(start_url, max_pages=50, max_depth=2, min_content_size_mb=50):
    if not start_url: return

    visited_urls = set()
    queue = deque([(start_url, 0)])
    total_ingested_size = 0
    page_count = 0

    async with aiohttp.ClientSession( ) as session:
        while queue and page_count < max_pages and total_ingested_size < min_content_size_mb * 1024 * 1024:
            current_url, depth = queue.popleft()

            if current_url in visited_urls or depth > max_depth:
                continue

            print(f"Crawling: {current_url} (Depth: {depth})")
            visited_urls.add(current_url)

            html_content = await fetch_page(session, current_url)
            if html_content:
                await ingest_document(current_url, html_content)
                total_ingested_size += len(html_content.encode('utf-8'))
                page_count += 1

                soup = BeautifulSoup(html_content, 'html.parser')
                for link in soup.find_all('a', href=True):
                    href = link.get('href')
                    absolute_url = urljoin(current_url, href)
                    parsed_absolute_url = urlparse(absolute_url)
                    # Only follow links within the same domain
                    if parsed_absolute_url.netloc == urlparse(start_url).netloc:
                        queue.append((absolute_url, depth + 1))

    print(f"Crawling finished. Ingested {page_count} pages, total size: {total_ingested_size / (1024*1024):.2f} MB")

# --- RAG Querying ---
async def retrieve_documents(query_embedding, top_k=5):
    try:
        # Supabase vector search
        response = supabase.rpc(
            'match_documents',
            {
                'query_embedding': query_embedding,
                'match_threshold': 0.78, # Adjust as needed
                'match_count': top_k
            }
        ).execute()

        if response.data:
            return response.data
        elif response.error:
            print(f"Error retrieving documents: {response.error}")
            return []
    except Exception as e:
        print(f"Supabase retrieval error: {e}")
        return []

async def rag_qa(query: str):
    start_time = time.time()
    query_embedding = generate_embedding(query)
    retrieved_docs = await retrieve_documents(query_embedding)

    if USE_HYBRID_SEARCH:
        # Implement keyword search and combine with vector search results
        # For simplicity, this is a placeholder. A real implementation would use a search index.
        print("Hybrid search enabled, but not fully implemented.")

    if USE_RERANKING and retrieved_docs:
        # Implement a reranking step using a cross-encoder model or LLM
        # For simplicity, this is a placeholder.
        print("Reranking enabled, but not fully implemented.")

    context = "\n\n".join([doc['content'] for doc in retrieved_docs])
    citations = [doc['metadata']['url'] for doc in retrieved_docs if 'url' in doc['metadata']]
    citations = list(set(citations)) # Unique citations

    if not context:
        return "I couldn't find relevant information for your query.", [], (time.time() - start_time) * 1000, []

    messages = [
        {"role": "system", "content": "You are a helpful assistant. Answer the user's question based *only* on the provided context. Cite your sources by URL."},
        {"role": "user", "content": f"Context: {context}\n\nQuestion: {query}\n\nAnswer:"}
    ]

    try:
        response = openai_client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=0.0,
            stream=False # For endpoint, we return full response
        )
        answer = response.choices[0].message.content
        # Add citations to the answer
        if citations:
            answer += "\n\nSources: " + ", ".join(citations)
        latency_ms = (time.time() - start_time) * 1000
        return answer, citations, latency_ms, [doc['content'] for doc in retrieved_docs]
    except Exception as e:
        print(f"Error during RAG QA: {e}")
        return "An error occurred while processing your request.", [], (time.time() - start_time) * 1000, []

# Example usage (for testing)
async def main():
    # Ensure Supabase is set up with pg_vector extension and 'documents' table
    await setup_supabase_vector_store()

    # Crawl and ingest data if CORPUS_URL is provided
    if CORPUS_URL:
        print(f"Starting crawl and ingestion from {CORPUS_URL}")
        await crawl_and_ingest(CORPUS_URL, max_pages=10, min_content_size_mb=1) # Reduced for quick testing
    else:
        print("CORPUS_URL not set. Skipping crawling.")

    # Example QA
    if CORPUS_URL:
        query = "What is the main topic of the crawled documents?"
        print(f"\nQuery: {query}")
        answer, sources, latency, _ = await rag_qa(query)
        print(f"Answer: {answer}")
        print(f"Latency: {latency:.2f} ms")
        print(f"Sources: {sources}")

if __name__ == "__main__":
    asyncio.run(main())
