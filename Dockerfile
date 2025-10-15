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
# Also install Playwright browsers (chromium) during build so runtime can launch them
RUN pip install --upgrade pip && pip install . && \
    python -m playwright install --with-deps chromium

FROM python:3.12-slim as final
WORKDIR /app

# Install runtime dependencies required by Chromium / Playwright
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpangocairo-1.0-0 \
    libxss1 \
    libxshmfence1 \
    libglib2.0-0 \
    libgtk-3-0 \
    libx11-xcb1 \
    libxcb1 \
    libx11-6 \
    lsb-release \
    fonts-liberation \
    --no-install-recommends && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd --create-home --shell /bin/bash appuser

# Copy installed packages from builder layer
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
# Copy Playwright browser artifacts downloaded during build so they are available at runtime
COPY --from=builder /root/.cache/ms-playwright /home/appuser/.cache/ms-playwright

# Copy application code
COPY . /app

RUN chown -R appuser:appuser /app /home/appuser/.cache && \
    chown -R appuser:appuser /home/appuser
USER appuser

EXPOSE ${PORT}

ENV PORT=${PORT}

CMD ["python", "src/crawl4ai_mcp.py"]
