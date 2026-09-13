.PHONY: help \ 
	build up down restart logs logs-api logs-qdrant logs-ollama \
	shell test clean ollama-pull ollama-list \
	docs-install docs-start docs-build docs-serve docs-clean \
	docs-index
 

help:
	@echo "Available commands:"
	@echo "  make build       - Build or rebuild images"
	@echo "  make up          - Start all services"
	@echo "  make down        - Stop all services"
	@echo "  make restart     - Restart all services"
	@echo "  make logs        - View logs from all services"
	@echo "  make logs-api    - View logs from API service"
	@echo "  make logs-qdrant - View logs from Qdrant service"
	@echo "  make logs-ollama - View logs from Ollama service"
	@echo "  make shell       - Open bash shell in API container"
	@echo "  make test        - Run tests in API container"
	@echo ""
	@echo "Ollama:"
	@echo "  make ollama-pull - Pull Ollama model (default: llama3.1:8b)"
	@echo "  make ollama-list - List downloaded Ollama models"
	@echo "  make clean       - Stop services and remove volumes"
	@echo ""
	@echo "Documentation:"
	@echo "  make docs-install - Install Docusaurus dependencies"
	@echo "  make docs-start   - Start the Docusaurus development server"
	@echo "  make docs-build   - Build the production documentation site"
	@echo "  make docs-serve   - Serve the production documentation locally"
	@echo "  make docs-clean   - Remove Docusaurus generated files"
	@echo "  make docs-index   - Build the local documentation retrieval index" 

# --------------------------------------------------------------------
# Assistant services
# --------------------------------------------------------------------

build:
	podman compose build

up:
	podman compose up -d

down:
	podman compose down

restart:
	podman compose restart

logs:
	podman compose logs -f

logs-api:
	podman compose logs -f api

logs-qdrant:
	podman compose logs -f qdrant

logs-ollama:
	podman compose logs -f ollama

shell:
	podman compose exec api bash

test:
	podman compose exec api pytest

ollama-pull:
	podman compose exec ollama ollama pull llama3.1:8b

ollama-list:
	podman compose exec ollama ollama list

clean:
	podman compose down -v

# --------------------------------------------------------------------
# Docusaurus documentation
# --------------------------------------------------------------------

docs-install:
	cd website && npm install

docs-start:
	cd website && npm run start

docs-build:
	cd website && npm run build

docs-serve:
	cd website && npm run serve

docs-clean:
	rm -rf website/build website/.docusaurus

# --------------------------------------------------------------------
# Local AI documentation retrieval
# --------------------------------------------------------------------

docs-index:
	python scripts/index_docs.py \
		--source website/docs \
		--output data/vector-store
