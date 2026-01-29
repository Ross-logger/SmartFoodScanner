.PHONY: help shell install run dev frontend backend stop-frontend stop-backend stop

# Variables
VENV = .venv
PYTHON = $(VENV)/bin/python
PIP = $(VENV)/bin/pip
PROJECT_ROOT = $(shell pwd)

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

run: ## Run both backend and frontend servers
	@echo "Starting both backend and frontend servers..."
	@make backend & make frontend

backend: ## Run backend server
	@echo "Starting backend server..."
	@cd $(PROJECT_ROOT) && \
		source $(VENV)/bin/activate && \
		uvicorn backend.main:app --reload

frontend: ## Run frontend development server
	@echo "Starting frontend server..."
	@cd frontend && npm run dev

stop-backend: ## Stop backend server (port 8000)
	@echo "Stopping backend server..."
	@-lsof -t -i:8000 | xargs kill -9 2>/dev/null || echo "No backend process found on port 8000"

stop-frontend: ## Stop frontend server (port 3000)
	@echo "Stopping frontend server..."
	@-lsof -t -i:3000 | xargs kill -9 2>/dev/null || echo "No frontend process found on port 3000"

stop: stop-backend stop-frontend ## Stop both backend and frontend servers
	@echo "All servers stopped."

