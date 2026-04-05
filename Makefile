.PHONY: help shell install run dev frontend backend vllm-mistral7B stop-frontend stop-backend stop migrate-generate migrate migrate-downgrade migrate-history run-unit-test run-integration-test run-performance-test run-all-tests training evaluation training-filter-jsonl training-keep-only-text

# Variables
VENV = .venv
# Repo-root venv (paths must work after recipe `cd` into training/ or frontend/)
PROJECT_ROOT = $(shell pwd)
PYTHON = $(PROJECT_ROOT)/$(VENV)/bin/python
PIP = $(PROJECT_ROOT)/$(VENV)/bin/pip
# Detached GNU screen session name for vLLM (must be non-empty; override: make vllm-mistral7B SCREEN_VLLM=myname)
SCREEN_VLLM ?= smartfood-vllm

shell: ## Start Python shell with project imports and backend.services pre-loaded
	@cd $(PROJECT_ROOT) && \
		source $(VENV)/bin/activate && \
		export PYTHONPATH=$(PROJECT_ROOT) && \
		export PYTHONSTARTUP=$(PROJECT_ROOT)/scripts/python_startup_services.py && \
		$(PYTHON)

install:
	@echo "Installing dependencies..."
	@if [ ! -d "$(VENV)" ]; then \
		python3 -m venv $(VENV); \
	fi
	@$(PIP) install --upgrade pip
	@$(PIP) install -r requirements.txt

run: ## Start backend in background, then frontend in foreground (same terminal)
	@echo "Backend in background; frontend in foreground. Ctrl+C stops frontend; run make stop-backend if needed."
	@( cd $(PROJECT_ROOT) && source $(VENV)/bin/activate && uvicorn backend.main:app) & \
	cd $(PROJECT_ROOT)/frontend && exec npm run dev

backend: ## Run backend server (foreground)
	@cd $(PROJECT_ROOT) && source $(VENV)/bin/activate && exec uvicorn backend.main:app

backend-dev:
	@cd $(PROJECT_ROOT) && source $(VENV)/bin/activate && exec uvicorn backend.main:app --reload
frontend: ## Run frontend dev server (foreground)
	@cd $(PROJECT_ROOT)/frontend && exec npm run dev

vllm-mistral7B: ## Start Mistral-7B via vLLM in detached screen (needs: pip install -r requirements-vllm.txt)
	@echo "Starting vLLM in screen session $(SCREEN_VLLM)..."
	@screen -dmS "$(SCREEN_VLLM)" bash -lc 'cd $(PROJECT_ROOT) && source $(VENV)/bin/activate && exec vllm serve "mistralai/Mistral-7B-Instruct-v0.2" --tool-call-parser mistral --enable-auto-tool-choice --port 1234'

stop-backend: ## Stop uvicorn backend process
	@echo "Stopping backend..."
	@-pkill -f '[u]vicorn backend.main:app' 2>/dev/null || echo "No backend process found."

stop-frontend: ## Stop Vite dev server for this project’s frontend
	@echo "Stopping frontend dev server..."
	@-pkill -f '$(PROJECT_ROOT)/frontend/node_modules/vite' 2>/dev/null || echo "No frontend dev server found."

stop: stop-backend stop-frontend ## Stop backend and frontend dev processes
	@echo "Backend and frontend stopped (as applicable)."

# =============================================================================
# Database migrations (Alembic)
# =============================================================================
ALEMBIC = PYTHONPATH=$(PROJECT_ROOT) $(PROJECT_ROOT)/$(VENV)/bin/alembic

make-migrations: ## Generate a new migration: make migrate-generate m="describe_your_change"
	@if [ -z "$(m)" ]; then echo "Usage: make migrate-generate m=\"describe_your_change\""; exit 1; fi
	$(ALEMBIC) revision --autogenerate -m "$(m)"

migrate: ## Apply all pending migrations to the database
	$(ALEMBIC) upgrade head

migrate-downgrade: ## Roll back the last migration
	$(ALEMBIC) downgrade -1

migrate-history: ## Show migration history
	$(ALEMBIC) history --verbose

# =============================================================================
# Tests (pytest; pytest.ini sets testpaths and markers)
# =============================================================================
PYTEST = cd $(PROJECT_ROOT) && PYTHONPATH=$(PROJECT_ROOT) $(PYTHON) -m pytest

run-unit-test: ## Run unit tests (tests/unit)
	$(PYTEST) tests/unit

run-integration-test: ## Run integration tests (tests/integration)
	$(PYTEST) tests/integration

run-performance-test: ## Run performance tests (tests/performance)
	$(PYTEST) tests/performance

run-all-tests: ## Run unit, integration, and performance tests in order
	$(PYTEST) tests/unit tests/integration tests/performance

# =============================================================================
# Training (ingredient box classifier + merge evaluation)
# =============================================================================
# Run from repo root. Uses .venv; evaluate.py needs PYTHONPATH for backend imports.
TRAINING_RUN = cd $(PROJECT_ROOT)/training && PYTHONPATH=$(PROJECT_ROOT) $(PYTHON)

training: ## Train box classifier (training/training_code.py → models/, outputs/)
	$(TRAINING_RUN) training_code.py

evaluation: ## Evaluate merge vs ground truth (training/evaluate.py); optional ARGS="--flag ..."
	$(TRAINING_RUN) evaluate.py $(ARGS)

training-filter-jsonl: ## Keep English JSONL rows (utils/filter_jsonl_english.py); ARGS="in.jsonl [-o out.jsonl]"
	@if [ -z "$(ARGS)" ]; then echo 'Usage: make training-filter-jsonl ARGS="input.jsonl [-o out.jsonl]"'; exit 1; fi
	@cd $(PROJECT_ROOT)/training && $(PYTHON) utils/filter_jsonl_english.py $(ARGS)

training-keep-only-text: ## JSONL → text-only JSONL (utils/keep_only_text.py); ARGS="in.jsonl out.jsonl"
	@if [ -z "$(ARGS)" ]; then echo 'Usage: make training-keep-only-text ARGS="input.jsonl output.jsonl"'; exit 1; fi
	@cd $(PROJECT_ROOT)/training && $(PYTHON) utils/keep_only_text.py $(ARGS)
