.PHONY: help shell install run dev frontend backend vllm stop-frontend stop-backend stop-vllm stop screens migrate-generate migrate migrate-downgrade migrate-history

# Variables
VENV = .venv
PYTHON = $(VENV)/bin/python
PIP = $(VENV)/bin/pip
PROJECT_ROOT = $(shell pwd)
SCREEN_VLLM = vllm

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
	@( cd $(PROJECT_ROOT) && source $(VENV)/bin/activate && uvicorn backend.main:app --reload ) & \
	cd $(PROJECT_ROOT)/frontend && exec npm run dev

dev: run ## Alias for run

backend: ## Run backend server (foreground)
	@cd $(PROJECT_ROOT) && source $(VENV)/bin/activate && exec uvicorn backend.main:app --reload

frontend: ## Run frontend dev server (foreground)
	@cd $(PROJECT_ROOT)/frontend && exec npm run dev

vllm: ## Start LLM spellcheck corrector via vLLM (detached screen: $(SCREEN_VLLM))
	@echo "Starting vLLM in screen session $(SCREEN_VLLM)..."
	@screen -dmS $(SCREEN_VLLM) bash -lc 'cd $(PROJECT_ROOT) && source $(VENV)/bin/activate && exec vllm serve "openfoodfacts/spellcheck-mistral-7b"'

screens: ## List vLLM GNU screen session (if any)
	@screen -ls | grep -E '$(SCREEN_VLLM)' || echo "No vLLM screen session."

stop-backend: ## Stop uvicorn backend process
	@echo "Stopping backend..."
	@-pkill -f '[u]vicorn backend.main:app' 2>/dev/null || echo "No backend process found."

stop-frontend: ## Stop Vite dev server for this project’s frontend
	@echo "Stopping frontend dev server..."
	@-pkill -f '$(PROJECT_ROOT)/frontend/node_modules/vite' 2>/dev/null || echo "No frontend dev server found."

stop-vllm: ## Stop vLLM screen session ($(SCREEN_VLLM))
	@echo "Stopping vLLM screen session..."
	@-screen -S $(SCREEN_VLLM) -X quit 2>/dev/null || echo "No session $(SCREEN_VLLM)."

stop: stop-backend stop-frontend stop-vllm ## Stop backend, frontend (processes), and vLLM screen session
	@echo "Backend, frontend, and vLLM stopped (as applicable)."

# =============================================================================
# Database migrations (Alembic)
# =============================================================================
ALEMBIC = PYTHONPATH=$(PROJECT_ROOT) $(VENV)/bin/alembic

make-migrations: ## Generate a new migration: make migrate-generate m="describe_your_change"
	@if [ -z "$(m)" ]; then echo "Usage: make migrate-generate m=\"describe_your_change\""; exit 1; fi
	$(ALEMBIC) revision --autogenerate -m "$(m)"

migrate: ## Apply all pending migrations to the database
	$(ALEMBIC) upgrade head

migrate-downgrade: ## Roll back the last migration
	$(ALEMBIC) downgrade -1

migrate-history: ## Show migration history
	$(ALEMBIC) history --verbose
