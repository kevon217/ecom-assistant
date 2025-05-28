.PHONY: help build up down test clean deploy logs shell-chat shell-order shell-product health bootstrap-chroma

help:
	@echo "Available commands:"
	@echo "  make build         - Build Docker images"
	@echo "  make up            - Start all services"
	@echo "  make down          - Stop all services"
	@echo "  make test          - Run all tests"
	@echo "  make clean         - Clean up volumes and images"
	@echo "  make logs          - Follow service logs"
	@echo "  make health        - Check service health"
	@echo "  make shell-chat    - Shell into chat service"
	@echo "  make shell-order   - Shell into order service"
	@echo "  make shell-product - Shell into product service"
	@echo "  make bootstrap-chroma - Initialize ChromaDB (if needed)"

build:
	docker-compose build

up:
	docker-compose up -d
	@echo "Waiting for services to be healthy..."
	@sleep 5
	@make health

down:
	docker-compose down

test:
	# Run unit tests for each service
	cd services/order && uv run pytest
	cd services/product && uv run pytest
	cd services/chat && uv run pytest

test-integration:
	# Run with services up
	docker-compose up -d
	@sleep 30
	@make health
	# Add integration test commands here
	docker-compose down

clean:
	docker-compose down -v
	docker system prune -f
	rm -rf data/chroma/*
	rm -rf data/sessions/*

logs:
	docker-compose logs -f

logs-chat:
	docker-compose logs -f chat-service

logs-order:
	docker-compose logs -f order-service

logs-product:
	docker-compose logs -f product-service

health:
	@echo "Checking service health..."
	@curl -f http://localhost:8001/health && echo "✅ Chat service healthy" || echo "❌ Chat service not healthy"
	@curl -f http://localhost:8002/health && echo "✅ Order service healthy" || echo "❌ Order service not healthy"
	@curl -f http://localhost:8003/health && echo "✅ Product service healthy" || echo "❌ Product service not healthy"

shell-chat:
	docker-compose exec chat-service bash

shell-order:
	docker-compose exec order-service bash

shell-product:
	docker-compose exec product-service bash

# Only needed if ChromaDB wasn't created during build
bootstrap-chroma:
	docker-compose exec product-service python /app/scripts/bootstrap/load_vectors.py \
		--csv /app/data/products_cleaned.csv \
		--persist-dir /app/data/chroma \
		--collection products \
		--model all-MiniLM-L6-v2

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
	docker-compose ps

# Remove old images to save space
prune:
	docker image prune -f
	docker container prune -f
	docker volume prune -f
