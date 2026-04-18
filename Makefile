.PHONY: dev install install-api install-web migrate seed clean help

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

dev: ## Start full dev environment (API + Frontend)
	bash infra/scripts/dev.sh

install: install-api install-web ## Install all dependencies

install-api: ## Install Python dependencies
	python3 -m venv .venv
	. .venv/bin/activate && pip install -e ".[dev]"

install-web: ## Install frontend dependencies
	cd apps/web && npm install

migrate: ## Run database migrations
	. .venv/bin/activate && alembic -c alembic.ini upgrade head

seed: ## Seed database with defaults
	. .venv/bin/activate && python infra/db/seed.py

api: ## Start API server only
	. .venv/bin/activate && uvicorn services.api.main:app --host 0.0.0.0 --port 8000 --reload

web: ## Start frontend only
	cd apps/web && npm run dev

clean: ## Remove generated files
	rm -rf .venv apps/web/node_modules apps/web/.next data/*.db
