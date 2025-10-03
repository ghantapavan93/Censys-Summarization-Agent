.PHONY: help dev up down logs clean test build

# Default target
help:
	@echo "Censys Summarization Agent - Development Commands"
	@echo ""
	@echo "Available commands:"
	@echo "  dev     - Start development environment with hot reloading"
	@echo "  up      - Start production environment"
	@echo "  down    - Stop all services"
	@echo "  logs    - View logs from all services"
	@echo "  clean   - Remove all containers and volumes"
	@echo "  test    - Run all tests"
	@echo "  build   - Build all containers"

# Development environment with hot reloading
dev:
	docker-compose -f docker-compose.dev.yml up --build

# Production environment
up:
	docker-compose up --build -d

# Stop all services
down:
	docker-compose down
	docker-compose -f docker-compose.dev.yml down

# View logs
logs:
	docker-compose logs -f

# Clean up containers and volumes
clean:
	docker-compose down -v --remove-orphans
	docker-compose -f docker-compose.dev.yml down -v --remove-orphans
	docker system prune -f

# Run tests
test:
	@echo "Running backend tests..."
	docker-compose exec backend pytest tests/ -v || docker-compose run --rm backend pytest tests/ -v
	@echo "Backend tests completed."

# Build all containers
build:
	docker-compose build
	docker-compose -f docker-compose.dev.yml build

# Install frontend dependencies locally (for development)
install-frontend:
	cd frontend && npm install

# Install backend dependencies locally (for development)
install-backend:
	cd backend && pip install -r requirements.txt

# Run backend locally (development)
run-backend:
	cd backend && uvicorn app:app --reload --host 0.0.0.0 --port 8000

# Run frontend locally (development)
run-frontend:
	cd frontend && npm run dev