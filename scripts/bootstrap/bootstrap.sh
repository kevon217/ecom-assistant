# 1. Build your services
docker compose build

# 2. Start just the product service to bootstrap ChromaDB
docker compose run --rm product-service bash /app/scripts/bootstrap/init_vectors.sh

# 3. Now start all services normally
docker compose up

# Alternative: Bootstrap during build (add to Dockerfile)
# RUN python -m scripts.bootstrap.load_vectors_v2 --csv /app/data/processed/latest/products_cleaned.csv --persist-dir /app/data/chroma
