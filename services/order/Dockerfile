# services/order/Dockerfile
FROM python:3.11-slim AS base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Set working directory
WORKDIR /app

# Copy only the service's pyproject.toml first
COPY ./services/order/pyproject.toml /app/services/order/

# Install dependencies
WORKDIR /app/services/order
RUN uv pip install --system -e .

# Copy application code
COPY ./libs /app/libs
COPY ./services/order/src /app/services/order/src

COPY ./data/orders_cleaned.csv /app/data/orders_cleaned.csv


# Create non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Set environment variables
ENV PYTHONPATH="/app/services/order/src:/app/libs:/app" \
    PYTHONUNBUFFERED=1 \
    PORT=8002

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Expose port (can be overridden by PORT env var)
EXPOSE ${PORT}

# Set working directory for runtime to match relative paths
WORKDIR /app

# Run the service
CMD ["python", "-m", "uvicorn", "order.app:app", "--host", "0.0.0.0", "--port", "8002"]
