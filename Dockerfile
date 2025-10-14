FROM python:3.12-slim as base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

ARG PORT=8051
WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# Install pip-tools and pip
RUN python -m pip install --upgrade pip setuptools wheel

FROM base as builder
WORKDIR /app
# Copy only dependency files first for better layer caching
COPY pyproject.toml pyproject.toml
COPY . /app

# Install project in editable mode (allows local imports) and deps
RUN pip install --upgrade pip && pip install .

FROM python:3.12-slim as final
WORKDIR /app

# Create non-root user
RUN useradd --create-home --shell /bin/bash appuser

# Copy installed packages from builder layer
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY . /app

RUN chown -R appuser:appuser /app
USER appuser

EXPOSE ${PORT}

ENV PORT=${PORT}

CMD ["python", "src/crawl4ai_mcp.py"]
