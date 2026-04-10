.DEFAULT_GOAL := help

PYTHON   ?= python
VENV     ?= .venv
ACTIVATE := source $(VENV)/bin/activate &&

.PHONY: help venv install install-dev lint typecheck test test-cov smoke clean build

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

venv: ## Create virtual environment
	$(PYTHON) -m venv $(VENV)
	$(ACTIVATE) pip install --upgrade pip setuptools wheel

install: ## Install package (runtime only)
	$(ACTIVATE) pip install -e .

install-dev: ## Install package with dev dependencies
	$(ACTIVATE) pip install -e ".[dev]"

lint: ## Run ruff linter
	$(ACTIVATE) ruff check .

lint-fix: ## Run ruff linter with auto-fix
	$(ACTIVATE) ruff check . --fix

format: ## Run ruff formatter
	$(ACTIVATE) ruff format .

typecheck: ## Run pyright type checker
	$(ACTIVATE) pyright

test: ## Run full test suite
	$(ACTIVATE) python -m pytest tests/

test-cov: ## Run tests with coverage report
	$(ACTIVATE) python -m pytest tests/ --cov=rl_developer_memory --cov-report=term-missing --cov-report=html

test-unit: ## Run unit tests only
	$(ACTIVATE) python -m pytest tests/unit/

test-integration: ## Run integration tests only
	$(ACTIVATE) python -m pytest tests/integration/

smoke: ## Run smoke tests
	$(ACTIVATE) python -m rl_developer_memory.maintenance smoke

quality: lint typecheck test ## Run all quality checks (lint + typecheck + test)

ci: quality smoke ## Full CI pipeline locally

build: ## Build distribution artifacts
	$(ACTIVATE) python -m build

clean: ## Remove build artifacts and caches
	rm -rf build/ dist/ *.egg-info src/*.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov/ .coverage
