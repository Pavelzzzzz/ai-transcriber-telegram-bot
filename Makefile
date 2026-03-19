.PHONY: install lint test validate-requirements docker-build docker-build-all clean help

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies
	pip install ruff pre-commit
	pre-commit install

lint: ## Run linter
	ruff check .
	ruff format --check .

fix: ## Fix linting issues
	ruff check --fix .
	ruff format .

test: ## Run tests
	pytest tests/ -v

validate-requirements: ## Validate requirements.txt files
	python scripts/validate_requirements.py

docker-build: ## Build specific service (use SERVICE=name)
	docker-compose build $(SERVICE)

docker-build-all: ## Build all services
	docker-compose build

docker-up: ## Start all services
	docker-compose up -d

docker-down: ## Stop all services
	docker-compose down

docker-logs: ## Show logs (use SERVICE=name)
	docker-compose logs -f $(SERVICE)

docker-prune: ## Remove unused Docker images
	docker image prune -a -f

clean: ## Clean up Python cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
