.PHONY: help build up down test test-integration clean deploy logs logs-chat logs-order logs-product shell-chat shell-order shell-product health bootstrap-chroma bootstrap-chroma-smoke ci

help:
	@echo "Available commands:"
	@echo "  make build               - Build Docker images"
	@echo "  make up                  - Start all services"
	@echo "  make down                - Stop all services"
	@echo "  make test                - Run all unit tests"
	@echo "  make test-integration    - Run integration tests"
	@echo "  make clean               - Clean up volumes and images"
	@echo "  make logs                - Follow service logs"
	@echo "  make logs-chat           - Follow chat service logs"
	@echo "  make logs-order          - Follow order service logs"
	@echo "  make logs-product        - Follow product service logs"
	@echo "  make health              - Check service health"
	@echo "  make shell-chat          - Shell into chat service"
	@echo "  make shell-order         - Shell into order service"
	@echo "  make shell-product       - Shell into product service"
	@echo "  make bootstrap-chroma    - Initialize ChromaDB (if needed)"
	@echo "  make bootstrap-chroma-smoke - Fast-path ChromaDB bootstrap"
	@echo "  make ci                  - Run full CI suite locally"

build:
	docker compose build

up:
	docker compose up -d
	@echo "Waiting for services to be healthy..."
	@sleep 5
	@make health

down:
	docker compose down

test:
	# Run unit tests for each service
	cd services/order   && uv run pytest
	cd services/product && uv run pytest
	cd services/chat    && uv run pytest

test-integration:
	# Bring up services and run integration tests
	docker compose up -d
	@sleep 30
	@make health
	@echo "🔍 Running integration smoke tests…"
	@echo "- Chat service /health" && curl -sf http://localhost:8001/health || exit 1
	@echo "- Product service /health" && curl -sf http://localhost:8003/health || exit 1
	@echo "- Order service /health" && curl -sf http://localhost:8002/health || exit 1

	@echo "- Chat endpoint test" && \
	  curl -sf -X POST http://localhost:8001/chat \
	    -H "Content-Type: application/json" \
	    -d '{"message":"What tools do you have access to?"}' | jq .

	@echo "- Product semantic search test" && \
	  curl -sf -X POST http://localhost:8003/search/semantic \
	    -H "Content-Type: application/json" \
	    -d '{"query":"headphones","limit":5}' | jq .

	@echo "- Order lookup test" && \
	  curl -sf http://localhost:8002/orders/customer/12345?limit=5 | jq .
	docker compose down

clean:
	docker compose down -v
	docker system prune -f
	rm -rf data/chroma/*
	rm -rf data/sessions/*

logs:
	docker compose logs -f

logs-chat:
	docker compose logs -f chat-service

logs-order:
	docker compose logs -f order-service

logs-product:
	docker compose logs -f product-service

health:
	@echo "Checking service health..."
	@curl -f http://localhost:8001/health && echo "✅ Chat service healthy"   || echo "❌ Chat service not healthy"
	@curl -f http://localhost:8002/health && echo "✅ Order service healthy"  || echo "❌ Order service not healthy"
	@curl -f http://localhost:8003/health && echo "✅ Product service healthy"|| echo "❌ Product service not healthy"

shell-chat:
	docker compose exec chat-service bash

shell-order:
	docker compose exec order-service bash

shell-product:
	docker compose exec product-service bash

# Only needed if ChromaDB wasn't created during build
bootstrap-chroma:
	docker compose exec product-service python /app/scripts/bootstrap/load_vectors.py \
		--csv /app/data/products_cleaned.csv \
		--persist-dir /app/data/chroma \
		--collection products \
		--model all-MiniLM-L6-v2

# Fast-path bootstrap for CI caching
bootstrap-chroma-smoke:
	@echo "🔄 Fast-path ChromaDB bootstrap"
	@make bootstrap-chroma

# Run entire CI suite locally
ci:
	@echo "▶️ Running local CI suite (unit + integration)"
	@make test
	@make test-integration

# Quick test of the chat functionality
test-chat:
	curl -X POST http://localhost:8001/chat \
		-H "Content-Type: application/json" \
		-d '{"message": "What products do you have?"}' | jq .

# Development workflow helpers
dev: down clean build up
	@echo "Fresh development environment ready!"

restart: down up
	@echo "Services restarted!"

# Check what's running
ps:
	docker compose ps

# Remove old images to save space
prune:
	docker image prune -f
	docker container prune -f
	docker volume prune -f
