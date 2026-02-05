.PHONY: help install test test-cov lint format format-check clean build pre-commit

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies
	uv sync --dev

test: ## Run tests
	uv run pytest

test-cov: ## Run tests with coverage report
	uv run pytest --cov=planhub --cov-report=html --cov-report=term

lint: ## Run linting checks
	uv run ruff check .

format: ## Format code
	uv run ruff format .

format-check: ## Check code formatting without modifying files
	uv run ruff format --check .

clean: ## Clean build artifacts and cache files
	rm -rf dist/
	rm -rf build/
	rm -rf *.egg-info
	find . -type d -name __pycache__ -exec rm -r {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf .pytest_cache/
	rm -rf .ruff_cache/

build: ## Build the package
	uv build

pre-commit: ## Run pre-commit hooks on all files
	uv run pre-commit run --all-files
