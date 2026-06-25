.PHONY: install up down logs logs-app logs-generator restart status \
        ingest ingest-limit serve query health \
        test test-integration test-all \
        deploy-do destroy-do \
        prod-up prod-down prod-logs prod-restart prod-status prod-ingest

PYTHON := ~/miniconda3/bin/python3.13

# ── Setup ────────────────────────────────────────────────────
install:
	$(PYTHON) -m pip install -e ".[dev]"

# ── Infrastructure ───────────────────────────────────────────
up:
	docker compose up -d

down:
	docker compose down

down-v:
	docker compose down -v

logs:
	docker compose logs -f

logs-app:
	docker compose logs -f app

logs-generator:
	docker compose logs -f data-generator

restart:
	docker compose down && docker compose up -d

status:
	docker compose ps

# ── App ──────────────────────────────────────────────────────
ingest:
	$(PYTHON) -m src.ingestion.run

ingest-limit:
	$(PYTHON) -m src.ingestion.run --limit 20

serve:
	$(PYTHON) -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload --log-level info

query:
	@read -p "Question: " q; \
	curl -s -X POST http://localhost:8000/api/v1/query \
		-H "Content-Type: application/json" \
		-d "{\"question\": \"$$q\"}" | $(PYTHON) -m json.tool

health:
	curl -s http://localhost:8000/health | $(PYTHON) -m json.tool

# ── Tests ────────────────────────────────────────────────────
test:
	$(PYTHON) -m pytest tests/unit -v

test-integration:
	$(PYTHON) -m pytest tests/integration -v --timeout=120

test-all:
	$(PYTHON) -m pytest tests/ -v --timeout=120

# ── Production (DigitalOcean) ────────────────────────────────
deploy-do:
	bash scripts/deploy-digitalocean.sh

destroy-do:
	bash scripts/destroy-digitalocean.sh

prod-up:
	docker compose -f docker-compose.production.yml up -d

prod-down:
	docker compose -f docker-compose.production.yml down

prod-logs:
	docker compose -f docker-compose.production.yml logs -f app

prod-restart:
	docker compose -f docker-compose.production.yml restart app

prod-status:
	docker compose -f docker-compose.production.yml ps

prod-ingest:
	docker compose -f docker-compose.production.yml exec -T app python -m src.ingestion.run
