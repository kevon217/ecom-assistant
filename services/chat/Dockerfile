# services/chat/Dockerfile
FROM python:3.11-slim AS base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Set working directory
WORKDIR /app

# Copy dependency files first (better caching)
COPY services/chat/pyproject.toml /app/services/chat/

# Install dependencies
WORKDIR /app/services/chat
RUN uv pip install --system -e .

# Copy application code
COPY libs /app/libs
COPY services/chat/src /app/services/chat/src


# Create directories and set permissions
RUN mkdir -p /app/data/sessions /app/logs && \
    useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

USER appuser

# Set environment variables
ENV PYTHONPATH="/app/services/chat/src:/app/libs:/app" \
    PYTHONUNBUFFERED=1 \
    PORT=8001 \
    CHAT_SESSION_STORE_PATH="data/sessions"

# Health check with longer start period for MCP discovery
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Expose port
EXPOSE ${PORT}

# Set working directory for runtime to match relative paths
WORKDIR /app

# Run the service
CMD ["python", "-m", "uvicorn", "chat.app:app", "--host", "0.0.0.0", "--port", "8001"]
