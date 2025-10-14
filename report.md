
### `report.md`
```markdown
# Design Decisions Report

This report outlines the key design decisions made during the extension of the `mcp-crawl4ai-rag` repository to incorporate new AI capabilities and meet the specified assessment requirements. The goal was to create a modular, extensible, and assessment-compliant system with clear configuration for various components.

## 1. Conversational Core (`src/chat.py`)

**Objective:** Implement a streaming chat CLI with message persistence and performance metrics.

**Design Decisions:**

*   **Streaming Output:** The `openai` library's `stream=True` parameter was utilized to enable incremental token display, providing a more responsive user experience. This is crucial for interactive CLI applications where users expect immediate feedback.
*   **Message Persistence:** SQLite was chosen for message persistence due to its lightweight nature and ease of integration, making it suitable for local development and testing. A `deque` (double-ended queue) was considered for in-memory persistence, but SQLite offers better durability across sessions. The `MAX_MESSAGES` constant ensures that only the last 10 messages are stored, preventing the database from growing indefinitely.
*   **Metrics Logging:** Key metrics such as prompt tokens, completion tokens, estimated cost, and latency are calculated and displayed after each turn. Token counting is implemented using `tiktoken` for accuracy, which is more robust than simple word counts. Cost estimation uses placeholder values that can be updated with actual model pricing.
*   **Environment Variables:** All sensitive information and configurable parameters (API keys, base URLs, model names) are loaded from environment variables using `python-dotenv`, ensuring secure and flexible deployment.
