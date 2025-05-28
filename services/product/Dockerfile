FROM python:3.11-slim AS base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Set working directory
WORKDIR /app

# Copy only the service's pyproject.toml first
COPY services/product/pyproject.toml /app/services/product/

# Install service dependencies first
WORKDIR /app/services/product
RUN uv pip install --system -e .

# Now copy the actual code
COPY libs /app/libs
COPY services/product/src /app/services/product/src

COPY data/products_cleaned.csv /app/data/products_cleaned.csv
COPY scripts/bootstrap/load_vectors.py /app/scripts/bootstrap/load_vectors.py

# Set environment variables BEFORE bootstrap
ENV PYTHONPATH="/app/services/product/src:/app/libs:/app" \
    PYTHONUNBUFFERED=1 \
    PORT=8003 \
    CHROMA_PERSIST_DIR="data/chroma"

# Create directories for ChromaDB and set permissions
RUN mkdir -p /app/data/chroma && \
    useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

# Change to correct working directory for bootstrap
WORKDIR /app

# Initialize ChromaDB during build with smart caching
RUN if [ -f /app/data/products_cleaned.csv ]; then \
        if [ -f /app/data/chroma/chroma.sqlite3 ] && [ -d /app/data/chroma ]; then \
            echo "ChromaDB already exists, skipping bootstrap (use 'docker compose build --no-cache product-service' to force rebuild)"; \
        else \
            echo "Starting ChromaDB bootstrap during build..."; \
            python /app/scripts/bootstrap/load_vectors.py \
                --csv /app/data/products_cleaned.csv \
                --persist-dir /app/data/chroma && \
            echo "Bootstrap completed successfully!"; \
        fi; \
    else \
        echo "Warning: products_cleaned.csv not found, skipping bootstrap"; \
    fi

USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Expose port
EXPOSE ${PORT}

# Set working directory for runtime to match relative paths
WORKDIR /app

# Run the service
CMD ["python", "-m", "uvicorn", "product.app:app", "--host", "0.0.0.0", "--port", "8003"]
