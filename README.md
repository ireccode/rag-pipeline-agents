# MCP Crawl4AI RAG Extended Repository

This repository extends the `mcp-crawl4ai-rag` project with several advanced AI capabilities, including a conversational core, a high-performance Retrieval-Augmented Generation (RAG) system, an autonomous planning agent, a self-healing code assistant, and automated retrieval accuracy testing. It also includes a Docker Compose setup for containerization and a Streamlit dashboard for performance monitoring.

## Features

1.  **Conversational Core (`src/chat.py`)**
    *   Streaming chat CLI for incremental token display.
    *   Persistence of the last N=10 messages in SQLite.
    *   Logging and display of prompt tokens, completion tokens, cost (USD), and latency (ms) per turn.

2.  **High-Performance Retrieval-Augmented QA (`src/rag.py`)**
    *   Web crawling and ingestion for a minimum of 50MB from a configurable `<CORPUS_URL>`.
    *   Intelligent chunking, embedding (using `sentence-transformers`), and vector storage in Supabase (or pgvector).
    *   Configurable advanced strategies: `USE_HYBRID_SEARCH` and `USE_RERANKING`.
    *   QA endpoint with inline citations, aiming for ≤300ms median retrieval time.
    *   Automated QA script (`tests/test_rag_accuracy.py`) with ≥20 graded question-answer pairs and top-5 retrieval accuracy reporting.

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

5.  **Automated Retrieval Accuracy Testing (`tests/test_deepeval_rag.py`)**
    *   Integrates Confident-AI DeepEval framework for evaluation.
    *   Uses placeholder `<LLM_JUDGE_MODEL>` for the judge, defaulting to Ollama `deepseek-r1:8B`.
    *   Outputs markdown/HTML reports in the `/reports/` directory.


6.  **Containerization and Streamlit Dashboard (Stretch Goal)**
    *   `docker-compose.yml` for all backend services (DB, APIs, dashboard).
    *   Streamlit dashboard (`dashboard/app.py`) for visualizing latency/cost, retrieval curves, and agent performance.
    *   All configurations as `.env.sample` with placeholders.

## Getting Started

### Prerequisites

*   Docker and Docker Compose
*   Python 3.11+
*   `uv` (recommended for dependency management)

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/coleam00/mcp-crawl4ai-rag.git
    cd mcp-crawl4ai-rag
    ```

2.  **Configure Environment Variables:**
    Copy the example environment file and fill in your credentials and URLs. **Do not commit this file with actual credentials.**
    ```bash
    cp .env.sample .env
    ```
    Edit the `.env` file:
    ```ini
    OPENAI_API_KEY=
    OPENAI_BASE_URL=
    MODEL_NAME=
    SUPABASE_URL=
    SUPABASE_SERVICE_KEY=
    CORPUS_URL=
    # EXTERNAL_API_URL=
    FLIGHTS_API_URL=
    HOTELS_API_URL=
    LLM_JUDGE_MODEL=
    ```

3.  **Build and Run with Docker Compose:**
    This will set up the Supabase database (Postgres with `pgvector` ), the main application, and the Streamlit dashboard.
    ```bash
    docker-compose up --build -d
    ```
    *Note: If you plan to use Ollama for the LLM Judge or Code Assistant, uncomment the `ollama` service in `docker-compose.yml` and ensure you pull the necessary models (e.g., `ollama pull deepseek-coder:latest`).*

### Manual Installation (without Docker)

1.  **Install dependencies:**
    ```bash
    uv sync
    ```

2.  **Set up Supabase/pgvector:**
    Ensure you have a PostgreSQL database with the `pgvector` extension enabled. You will need to create a `documents` table as described in `src/rag.py` comments.

## Usage

### Conversational Core

Run the chat CLI:
```bash
python3.11 src/chat.py
