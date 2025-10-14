# Use a Python base image
FROM python:3.11-slim-buster

# Set working directory
WORKDIR /app

# Copy pyproject.toml and uv.lock for dependency management
COPY pyproject.toml uv.lock ./ 

# Install uv and then install dependencies
RUN pip install uv && uv sync

# Copy the rest of the application code
COPY . .

# Expose the port for the main application (if it were a web service)
EXPOSE 8000

# Set environment variables (these will be overridden by docker-compose.yml)
ENV OPENAI_API_KEY="<OPENAI_API_KEY>"
ENV OPENAI_BASE_URL="<OPENAI_BASE_URL>"
ENV MODEL_NAME="<MODEL_NAME>"
ENV SUPABASE_URL="<SUPABASE_URL>"
ENV SUPABASE_SERVICE_KEY="<SUPABASE_SERVICE_KEY>"
ENV CORPUS_URL="<CORPUS_URL>"
ENV EXTERNAL_API_URL="<EXTERNAL_API_URL>"
ENV LLM_JUDGE_MODEL="<LLM_JUDGE_MODEL>"
ENV OLLAMA_BASE_URL="http://ollama:11434/v1" # Assuming Ollama runs in a separate container
ENV OLLAMA_MODEL_NAME="deepseek-coder:latest"

# Command to run the application (e.g., a FastAPI/Flask app or a script )
# This will be overridden by the command in docker-compose.yml for specific services
CMD ["python3.11", "src/chat.py"]
