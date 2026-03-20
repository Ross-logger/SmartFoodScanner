.PHONY: help shell install run dev frontend backend vllm stop-frontend stop-backend stop-vllm stop screens

# Variables
VENV = .venv
PYTHON = $(VENV)/bin/python
PIP = $(VENV)/bin/pip
PROJECT_ROOT = $(shell pwd)
SCREEN_BACKEND = backend
SCREEN_FRONTEND = frontend
SCREEN_VLLM = vllm

shell: ## Start Python shell with project imports enabled
	@cd $(PROJECT_ROOT) && \
		source $(VENV)/bin/activate && \
		export PYTHONPATH=$(PROJECT_ROOT) && \
		python

install:
	@echo "Installing dependencies..."
	@if [ ! -d "$(VENV)" ]; then \
		python3 -m venv $(VENV); \
	fi
	@$(PIP) install --upgrade pip
	@$(PIP) install -r requirements.txt

run: ## Start backend and frontend in detached GNU screen sessions
	@echo "Starting backend and frontend in screen sessions ($(SCREEN_BACKEND), $(SCREEN_FRONTEND))..."
	@$(MAKE) backend
	@$(MAKE) frontend
	@echo "Attach with: screen -r $(SCREEN_BACKEND)   or   screen -r $(SCREEN_FRONTEND)"

dev: run ## Alias for run

backend: ## Run backend server (detached screen: $(SCREEN_BACKEND))
	@echo "Starting backend in screen session $(SCREEN_BACKEND)..."
	@screen -dmS $(SCREEN_BACKEND) bash -lc 'cd $(PROJECT_ROOT) && source $(VENV)/bin/activate && exec uvicorn backend.main:app --reload'

frontend: ## Run frontend dev server (detached screen: $(SCREEN_FRONTEND))
	@echo "Starting frontend in screen session $(SCREEN_FRONTEND)..."
	@screen -dmS $(SCREEN_FRONTEND) bash -lc 'cd $(PROJECT_ROOT)/frontend && exec npm run dev'

vllm: ## Start LLM spellcheck corrector via vLLM (detached screen: $(SCREEN_VLLM))
	@echo "Starting vLLM in screen session $(SCREEN_VLLM)..."
	@screen -dmS $(SCREEN_VLLM) bash -lc 'cd $(PROJECT_ROOT) && source $(VENV)/bin/activate && exec vllm serve "openfoodfacts/spellcheck-mistral-7b"'

screens: ## List SmartFoodScanner screen sessions
	@screen -ls | grep -E '$(SCREEN_BACKEND)|$(SCREEN_FRONTEND)|$(SCREEN_VLLM)' || echo "No sfs-* screen sessions."

stop-backend: ## Stop backend screen session ($(SCREEN_BACKEND))
	@echo "Stopping backend screen session..."
	@-screen -S $(SCREEN_BACKEND) -X quit 2>/dev/null || echo "No session $(SCREEN_BACKEND)."

stop-frontend: ## Stop frontend screen session ($(SCREEN_FRONTEND))
	@echo "Stopping frontend screen session..."
	@-screen -S $(SCREEN_FRONTEND) -X quit 2>/dev/null || echo "No session $(SCREEN_FRONTEND)."

stop-vllm: ## Stop vLLM screen session ($(SCREEN_VLLM))
	@echo "Stopping vLLM screen session..."
	@-screen -S $(SCREEN_VLLM) -X quit 2>/dev/null || echo "No session $(SCREEN_VLLM)."

stop: stop-backend stop-frontend stop-vllm ## Stop backend, frontend, and vLLM screen sessions
	@echo "All service screen sessions stopped."
