.PHONY: help shell install run dev frontend backend

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

backend: ## Run backend server
	@echo "Starting backend server..."
	@cd $(PROJECT_ROOT) && \
		source $(VENV)/bin/activate && \
		uvicorn main:app --reload


frontend: ## Run frontend development server
	@echo "Starting frontend server..."
	@cd frontend && npm run dev


