FROM python:3.12-slim

ARG PORT=8051

WORKDIR /app

# Install uv and MCP Lambda adapter
RUN pip install uv aws-mcp-lambda

# Copy server files and code into the container
COPY . .

# Install application dependencies (system-wide, without venv)
RUN uv pip install --system -e . && \
    crawl4ai-setup

# Add AWS Lambda Web Adapter extension for HTTP/SSE
COPY --from=public.ecr.aws/awsguru/aws-lambda-adapter:0.9.1 /lambda-adapter /opt/extensions/lambda-adapter

# Expose the server port (default ARG, can be overridden)
EXPOSE ${PORT}

# CMD—Startup command; nothing hardcoded about invocation mode or ports
CMD ["python", "src/crawl4ai_mcp.py"]
