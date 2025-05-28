#!/bin/bash
# scripts/bootstrap/init_vectors.sh

set -e

echo "🚀 Starting vector initialization..."

# Use paths that match container
DATA_DIR="/app/data"
CHROMA_DIR="/app/data/chroma"
CSV_FILE="${DATA_DIR}/products_cleaned.csv"

# Check if data directory exists
if [ ! -d "${DATA_DIR}" ]; then
    echo "❌ Error: ${DATA_DIR} directory not found"
    echo "Make sure data cleaning has completed first"
    exit 1
fi

# Check if products CSV exists
if [ ! -f "${CSV_FILE}" ]; then
    echo "❌ Error: ${CSV_FILE} not found"
    echo "Run data cleaning first"
    exit 1
fi

# Create chroma directory
mkdir -p ${CHROMA_DIR}

echo "📊 CSV file info:"
wc -l ${CSV_FILE}

echo "🔄 Loading products into ChromaDB..."
# Already in correct location
cd /app
python -m scripts.bootstrap.load_vectors \
    --csv ${CSV_FILE} \
    --persist-dir ${CHROMA_DIR} \
    --collection products \
    --model all-MiniLM-L6-v2

echo "✅ Vector initialization complete!"

# Verify ChromaDB was created
if [ -d "${CHROMA_DIR}" ] && [ "$(ls -A ${CHROMA_DIR})" ]; then
    echo "✅ ChromaDB created successfully"
    echo "📁 ChromaDB contents:"
    ls -la ${CHROMA_DIR}/
else
    echo "❌ ChromaDB creation failed"
    exit 1
fi

echo "🎉 Vector store ready for use!"
