# MCP Crawl4AI RAG Extended Repository

This repository extends the `mcp-crawl4ai-rag` project with several advanced AI capabilities, including a conversational core, a high-performance Retrieval-Augmented Generation (RAG) system, an autonomous planning agent, a self-healing code assistant, and automated retrieval accuracy testing. It also includes a Docker Compose setup for containerization and a Streamlit dashboard for performance monitoring.

## Features

1.  **Conversational Core (`src/chat.py`)**
    *   Streaming chat CLI for incremental token display.
    *   Persistence of the last N=10 messages in SQLite.
    *   Logging and display of prompt tokens, completion tokens, cost (USD), and latency (ms) per turn.

2.  **High-Performance Retrieval-Augmented QA (`src/crawl4ai_mcp.py`)**
    *   Web crawling and ingestion for a minimum of 50MB from a configurable `<CORPUS_URL>`.
    *   Intelligent chunking, embedding (using `sentence-transformers`), and vector storage in Supabase (or pgvector).
    *   Configurable advanced strategies: `USE_HYBRID_SEARCH` and `USE_RERANKING` etc.
    *   QA endpoint with inline citations, aiming for ≤300ms median retrieval time.
    *   Automated QA script (`tests/test_accuracy.py`) with ≥20 graded question-answer pairs and top-5 retrieval accuracy reporting.

3.  **Autonomous Planning Agent (`src/agent.py`)**
    *   Accepts natural language prompts (e.g., "Plan a 2-day trip to...").
    *   Calls ≥2 external tools/APIs (mock or real, with `<EXTERNAL_API_URL>` placeholders).
    *   Logs reasoning steps (scratchpad).
    *   Outputs results as JSON in a documented schema, enforcing user constraints.

4.  **Self-Healing Code Assistant (`src/code_assistant.py`)**
    *   Accepts natural-language coding tasks, generates code, writes to disk, and runs tests (pytest).
    *   Captures errors and retries on failure (up to three times).
    *   Streams progress and shows final pass/fail to console.
    *   Compatible with Ollama (code/config placeholders for model use).    

5.  **Containerization and Streamlit Dashboard (`src/dashboard.py` and `docker-compose.yml`)**
    *   `docker-compose.yml` for all backend services (DB, APIs, dashboard).
    *   `src/dashboard.py` for visualizing latency/cost, retrieval curves, and agent performance.
    *   All configurations as `.env.sample` with placeholders.
    *   Access at `http://localhost:8501` when running with Docker Compose

## Tools

The server provides essential web crawling and search tools:

### Core Tools (Always Available)

1. **`crawl_single_page`**: Quickly crawl a single web page and store its content in the vector database
2. **`smart_crawl_url`**: Intelligently crawl a full website based on the type of URL provided (sitemap, llms-full.txt, or a regular webpage that needs to be crawled recursively)
3. **`get_available_sources`**: Get a list of all available sources (domains) in the database
4. **`perform_rag_query`**: Search for relevant content using semantic search with optional source filtering

### Conditional Tools

5. **`search_code_examples`** (requires `USE_AGENTIC_RAG=true`): Search specifically for code examples and their summaries from crawled documentation. This tool provides targeted code snippet retrieval for AI coding assistants.

### Knowledge Graph Tools (requires `USE_KNOWLEDGE_GRAPH=true`, see below)

6. **`parse_github_repository`**: Parse a GitHub repository into a Neo4j knowledge graph, extracting classes, methods, functions, and their relationships for hallucination detection
7. **`check_ai_script_hallucinations`**: Analyze Python scripts for AI hallucinations by validating imports, method calls, and class usage against the knowledge graph
8. **`query_knowledge_graph`**: Explore and query the Neo4j knowledge graph with commands like `repos`, `classes`, `methods`, and custom Cypher queries

## Getting Started

### Prerequisites

* Docker/Docker Desktop if running the MCP server as a container (recommended)
* Python 3.12+ if running the MCP server directly through uv
* Supabase (database for RAG)
* OpenAI API key (for generating embeddings)
* Neo4j (optional, for knowledge graph functionality) - see Knowledge Graph Setup section

## Installation

#### Using Docker (Recommended)

1.  **Clone the repository:**
    To clone this project, use the following command to get the latest changes from the rag-agents branch.
    ```bash
    git clone -b rag-agents https://github.com/ireccode/rag-pipeline-agents.git
    cd rag-pipeline-agents
    ```

2.  **Build the Docker image for crawl4ai-rag MCP server:**
    ```bash
    docker build -t crawl4ai-rag --build-arg PORT=8051 .
    ```

3.  **Create a `.env` file:**
    Copy the example environment file and fill in your credentials and URLs. **Do not commit this file with actual credentials.**
    ```bash
    cp .env.sample .env
    ```
    Edit the `.env` file with your configuration (see Configuration section below).

4.  **Run the server:**
    ```bash
    docker run --env-file .env -p 8051:8051 --rm --name rag-dev-run crawl4ai-rag
    ```
## Database Setup

Before running the server, you need to set up the database with the pgvector extension:

1. Go to the SQL Editor in your Supabase dashboard (create a new project first if necessary)

2. Create a new query and paste the contents of `crawled_pages.sql`

3. Run the query to create the necessary tables and functions

## Knowledge Graph Setup (Optional)

To enable AI hallucination detection and repository analysis features, you need to set up Neo4j.

Also, the knowledge graph implementation isn't fully compatible with Docker yet, so I would recommend right now running directly through uv if you want to use the hallucination detection within the MCP server!

### Manual Neo4j Installation (Optional)

1. **Install Neo4j Desktop**: Download from [neo4j.com/download](https://neo4j.com/download/)

2. **Create a new database**:
   - Open Neo4j Desktop
   - Create a new project and database
   - Set a password for the `neo4j` user
   - Start the database

3. **Note your connection details**:
   - URI: `bolt://localhost:7687` (default)
   - Username: `neo4j` (default)
   - Password: Whatever you set during creation

## Configuration

### Environment Variables

Create a `.env` file in the project root with the following variables:

```ini
# MCP Server Configuration
HOST=0.0.0.0
PORT=8051
TRANSPORT=sse

# OpenAI API Configuration
OPENAI_API_KEY=your_openai_api_key

# LLM for summaries and contextual embeddings
MODEL_CHOICE=gpt-4.1-nano

# RAG Strategies (set to "true" or "false", default to "false")
USE_CONTEXTUAL_EMBEDDINGS=false
USE_HYBRID_SEARCH=false
USE_AGENTIC_RAG=false
USE_RERANKING=false
USE_KNOWLEDGE_GRAPH=false

# Supabase Configuration
SUPABASE_URL=your_supabase_project_url
SUPABASE_SERVICE_KEY=your_supabase_service_key

# Neo4j Configuration (required for knowledge graph functionality)
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_neo4j_password
```

### RAG Strategy Options

The Crawl4AI RAG MCP server supports four powerful RAG strategies that can be enabled independently:

1. **USE_CONTEXTUAL_EMBEDDINGS**
   - **Description:** When enabled, this strategy enhances each chunk's embedding with additional context from the entire document. The system passes both the full document and the specific chunk to an LLM (configured via `MODEL_CHOICE`) to generate enriched context that gets embedded alongside the chunk content.
   - **When to use:** Enable this when you need high-precision retrieval where context matters, such as technical documentation where terms might have different meanings in different sections.
   - **Trade-offs:** Slower indexing due to LLM calls for each chunk, but significantly better retrieval accuracy.
   - **Cost:** Additional LLM API calls during indexing.

2. **USE_HYBRID_SEARCH**
   - **Description:** Combines traditional keyword search with semantic vector search to provide more comprehensive results. The system performs both searches in parallel and intelligently merges results, prioritizing documents that appear in both result sets.
   - **When to use:** Enable this when users might search using specific technical terms, function names, or when exact keyword matches are important alongside semantic understanding.
   - **Trade-offs:** Slightly slower search queries but more robust results, especially for technical content.
   - **Cost:** No additional API costs, just computational overhead.

3. **USE_AGENTIC_RAG**
   - **Description:** Enables specialized code example extraction and storage. When crawling documentation, the system identifies code blocks (≥300 characters), extracts them with surrounding context, generates summaries, and stores them in a separate vector database table specifically designed for code search.
   - **When to use:** Essential for AI coding assistants that need to find specific code examples, implementation patterns, or usage examples from documentation.
   - **Trade-offs:** Significantly slower crawling due to code extraction and summarization, requires more storage space.
   - **Cost:** Additional LLM API calls for summarizing each code example.
   - **Benefits:** Provides a dedicated `search_code_examples` tool that AI agents can use to find specific code implementations.

4. **USE_RERANKING**
   - **Description:** Applies cross-encoder reranking to search results after initial retrieval. Uses a lightweight cross-encoder model (`cross-encoder/ms-marco-MiniLM-L-6-v2`) to score each result against the original query, then reorders results by relevance.
   - **When to use:** Enable this when search precision is critical and you need the most relevant results at the top. Particularly useful for complex queries where semantic similarity alone might not capture query intent.
   - **Trade-offs:** Adds ~100-200ms to search queries depending on result count, but significantly improves result ordering.
   - **Cost:** No additional API costs - uses a local model that runs on CPU.
   - **Benefits:** Better result relevance, especially for complex queries. Works with both regular RAG search and code example search.

5. **USE_KNOWLEDGE_GRAPH**
   - **Description:** Enables AI hallucination detection and repository analysis using Neo4j knowledge graphs. When enabled, the system can parse GitHub repositories into a graph database and validate AI-generated code against real repository structures. (NOT fully compatible with Docker yet, I'd recommend running through uv)
   - **When to use:** Enable this for AI coding assistants that need to validate generated code against real implementations, or when you want to detect when AI models hallucinate non-existent methods, classes, or incorrect usage patterns.
   - **Trade-offs:** Requires Neo4j setup and additional dependencies. Repository parsing can be slow for large codebases, and validation requires repositories to be pre-indexed.
   - **Cost:** No additional API costs for validation, but requires Neo4j infrastructure (can use free local installation or cloud AuraDB).
   - **Benefits:** Provides three powerful tools: `parse_github_repository` for indexing codebases, `check_ai_script_hallucinations` for validating AI-generated code, and `query_knowledge_graph` for exploring indexed repositories.


### Recommended Configurations

**For general documentation RAG:**
```
USE_CONTEXTUAL_EMBEDDINGS=false
USE_HYBRID_SEARCH=true
USE_AGENTIC_RAG=false
USE_RERANKING=true
```

**For AI coding assistant with code examples:**
```
USE_CONTEXTUAL_EMBEDDINGS=true
USE_HYBRID_SEARCH=true
USE_AGENTIC_RAG=true
USE_RERANKING=true
USE_KNOWLEDGE_GRAPH=false
```

**For AI coding assistant with hallucination detection:**
```
USE_CONTEXTUAL_EMBEDDINGS=true
USE_HYBRID_SEARCH=true
USE_AGENTIC_RAG=true
USE_RERANKING=true
USE_KNOWLEDGE_GRAPH=true
```

**For fast, basic RAG:**
```
USE_CONTEXTUAL_EMBEDDINGS=false
USE_HYBRID_SEARCH=true
USE_AGENTIC_RAG=false
USE_RERANKING=false
USE_KNOWLEDGE_GRAPH=false
```

## MCP Integration

### Integration with MCP Clients

#### SSE Configuration

Once you have the server running with SSE transport, you can connect to it using this configuration:

```json
{
  "mcpServers": {
    "crawl4ai-rag": {
      "transport": "sse",
      "url": "http://localhost:8051/sse"
    }
  }
}
```

**Note for Windsurf users:** Use `serverUrl` instead of `url` in your configuration:
```json
{
  "mcpServers": {
    "crawl4ai-rag": {
      "transport": "sse",
      "serverUrl": "http://localhost:8051/sse"
    }
  }
}
```

**Note for Docker users:** Use `host.docker.internal` instead of `localhost` if your client is running in a different container.

**Note for Claude Code users**: 
```
claude mcp add-json crawl4ai-rag '{"type":"http","url":"http://localhost:8051/sse"}' --scope user
```

Cited from:
https://github.com/coleam00/mcp-crawl4ai-rag