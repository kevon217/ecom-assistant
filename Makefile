.PHONY: help build up down test clean deploy

help:
 @echo "Available commands:"
 @echo "  make build    - Build Docker images"
 @echo "  make up       - Start services"
 @echo "  make down     - Stop services"
 @echo "  make test     - Run all tests"
 @echo "  make clean    - Clean up volumes and images"
 @echo "  make deploy   - Deploy to Render"

build:
 docker-compose build

up:
 docker-compose up -d
 ./scripts/wait-for-healthy.sh

down:
 docker-compose down

test:
 docker-compose -f docker-compose.test.yml build
 docker-compose -f docker-compose.test.yml up --abort-on-container-exit
 docker-compose -f docker-compose.test.yml down -v

clean:
 docker-compose down -v
 docker system prune -f

deploy:
 @echo "Deploying to Render..."
 @echo "Make sure you've set up render.yaml and connected your GitHub repo"
 @echo "Deployment will trigger automatically on push to main"

logs:
 docker-compose logs -f

shell-chat:
 docker-compose exec chat-service bash

shell-order:
 docker-compose exec order-service bash

shell-product:
 docker-compose exec product-service bash

bootstrap-chroma:
 docker-compose exec product-service bash /app/scripts/bootstrap/init_vectors.sh
