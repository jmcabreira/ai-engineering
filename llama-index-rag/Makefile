.PHONY: up down logs restart status ingest serve query test test-integration test-all deploy-do destroy-do

# ── Infrastructure ──────────────────────────────────────────
up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

restart:
	docker compose down && docker compose up -d

status:
	docker compose ps

# ── App ─────────────────────────────────────────────────────
ingest:
	~/miniconda3/bin/python3.13 -m src.ingestion.run

serve:
	~/miniconda3/bin/python3.13 -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload --log-level info

query:
	@read -p "Question: " q; \
	curl -s -X POST http://localhost:8000/api/v1/query \
		-H "Content-Type: application/json" \
		-d "{\"question\": \"$$q\"}" | ~/miniconda3/bin/python3.13 -m json.tool

health:
	curl -s http://localhost:8000/health | ~/miniconda3/bin/python3.13 -m json.tool

# ── Tests ────────────────────────────────────────────────────
test:
	~/miniconda3/bin/python3.13 -m pytest tests/unit -v

test-integration:
	~/miniconda3/bin/python3.13 -m pytest tests/integration -v --timeout=120

test-all:
	~/miniconda3/bin/python3.13 -m pytest tests/ -v --timeout=120

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
