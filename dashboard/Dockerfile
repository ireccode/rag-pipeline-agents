# Use a Python base image
FROM python:3.12-slim-buster

# Set working directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt ./
RUN python -m pip install --upgrade pip setuptools wheel && \
	pip install -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose the Streamlit port
EXPOSE 8501

# Environment variables (overridden by docker-compose.yml)
ENV OPENAI_API_KEY="<OPENAI_API_KEY>"
ENV OPENAI_BASE_URL="<OPENAI_BASE_URL>"
ENV MODEL_NAME="<MODEL_NAME>"
ENV SUPABASE_URL="<SUPABASE_URL>"
ENV SUPABASE_SERVICE_KEY="<SUPABASE_SERVICE_KEY>"
ENV CORPUS_URL="<CORPUS_URL>"
ENV HOTELS_API_URL="<HOTELS_API_URL>"
ENV FLIGHTS_API_URL="<FLIGHTS_API_URL>"
ENV LLM_JUDGE_MODEL="<LLM_JUDGE_MODEL>"
ENV OLLAMA_BASE_URL="http://ollama:11434/v1"
ENV OLLAMA_MODEL_NAME="gemma3:4b"

# Command to run the Streamlit dashboard on all interfaces
CMD ["streamlit", "run", "app.py", "--server.port", "8501", "--server.address", "0.0.0.0"]
