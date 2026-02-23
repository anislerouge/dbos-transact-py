.PHONY: help install install-web dev server dashboard example test lint clean all

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

# ── Installation ──────────────────────────────────────────────

install: ## Install Python dependencies (server + dev)
	pdm install -G dev -G db

install-web: ## Install Node dependencies (dashboard)
	cd web && npm install

install-all: install install-web ## Install everything

# ── Run ───────────────────────────────────────────────────────

server: ## Start the Open Conductor server (port 8080)
	python -m open_conductor

dashboard: ## Start the React dashboard dev server (port 5173)
	cd web && npm run dev

example-app: ## Start the example DBOS app
	python examples/connect_app.py

dev: ## Start server + dashboard in parallel
	@echo "Starting Open Conductor server and dashboard..."
	@trap 'kill 0' INT TERM; \
		python -m open_conductor & \
		cd web && npm run dev & \
		wait

example: ## Start server + example DBOS app in parallel
	@echo "Starting Open Conductor server + example app..."
	@trap 'kill 0' INT TERM; \
		python -m open_conductor & \
		sleep 2 && python examples/connect_app.py & \
		wait

# ── Test ──────────────────────────────────────────────────────

test: ## Run all Python tests
	python -m pytest tests/ -v

test-watch: ## Run tests in watch mode (requires pytest-watch)
	python -m pytest tests/ -v --tb=short -x

# ── Build ─────────────────────────────────────────────────────

build-web: ## Build the React dashboard for production
	cd web && npm run build

# ── Clean ─────────────────────────────────────────────────────

clean: ## Remove caches and build artifacts
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf web/dist web/node_modules/.vite

# ── All ───────────────────────────────────────────────────────

all: install-all test dev ## Install everything, run tests, then start dev
