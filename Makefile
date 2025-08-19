.PHONY: help install dev-install test lint format clean docker-up docker-down migrate

help: ## Show this help message
	@echo "Usage: make [target]"
	@echo ""
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'

install: ## Install production dependencies
	pip install -r requirements.txt

dev-install: ## Install development dependencies
	pip install -r requirements-dev.txt

test: ## Run tests
	pytest tests/ -v --cov=src --cov-report=term-missing

lint: ## Run linting
	ruff check src/ tests/
	mypy src/

format: ## Format code
	black src/ tests/
	ruff check --fix src/ tests/

clean: ## Clean up cache and build files
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type f -name ".coverage" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true

docker-up: ## Start all services with Docker Compose
	docker-compose up -d

docker-down: ## Stop all services
	docker-compose down

docker-logs: ## Show logs from all services
	docker-compose logs -f

docker-build: ## Build Docker images
	docker-compose build

docker-restart: ## Restart all services
	docker-compose restart

migrate: ## Run database migrations
	alembic upgrade head

migration: ## Create a new migration
	@read -p "Enter migration message: " msg; \
	alembic revision --autogenerate -m "$$msg"

rollback: ## Rollback last migration
	alembic downgrade -1

db-reset: ## Reset database (WARNING: deletes all data)
	alembic downgrade base
	alembic upgrade head

run: ## Run the application locally
	uvicorn src.app.main:app --reload --port 8000

celery-worker: ## Run Celery worker
	celery -A src.app.tasks.celery_app worker --loglevel=info

celery-beat: ## Run Celery beat scheduler
	celery -A src.app.tasks.celery_app beat --loglevel=info

celery-flower: ## Run Celery Flower monitoring
	celery -A src.app.tasks.celery_app flower